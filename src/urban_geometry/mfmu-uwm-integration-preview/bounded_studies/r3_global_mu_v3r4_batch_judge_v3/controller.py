"""Global Multiple Update controller (GO 4.1-4.4, 5, 6, 7; plan sections 2.3, 2.5, 2.8).

One global Inner solve per round; frozen proposals; release-and-replace provisional occupancy;
claim materialisation from the immutable round-start snapshot; conflict groups + frozen uniform
capacity lottery; disposable-ledger hard dry-run; one round-end writeback; closure on the eight frozen
GO 9.1 conditions (+ redraw==0); final atomic production commit + independent replay only after closure.

The Inner backend is injected: backend(inputs) -> {"x": (N,K,M) float64, "x_tail": [x8,x14,x20],
"x_perm_tail": x_perm_inverse_mapped, "record": {...}}.  x_null is supplied once per scale by the
caller (exact-null control).  Everything else is pure CPU bookkeeping.

Post-review corrections (2026-08-31 adversarial review of the CD-ruling remediation):
  B2  UAV identity no longer contains the ban digest (stable identities -> bans resolvable across rounds);
  R-4 canonical station identities (coordinate digests) replace raw station indices in fingerprints,
      UAV identities and claim footprints (raw c/d/hub index never decides a winner);
  M4  observer stability is evaluated for carried orders too (diagnostics only) and certified per round;
  M8  final commit cross-checks the closure round's frozen dry-run decision digest and journey set;
  M5  state()/load_state() for checkpoint resume; m4 rejected classification by ban evidence class;
  m5  writeback mask == provisional-pin projection (documented); m6 strict redraw condition;
  m8  physical-response noise floor on demanded cells; M10e PRODUCTION_COMMIT_COUNT_BEFORE_FINAL measured.
"""
import hashlib
import json
import os
import time

import numpy as np

from . import batch_judge as BJ
from . import readout as RO
from . import resource_lottery as RL
from .rng import ResourceLotteryRegistry, assign_slots, candidate_universe_digest, digest_of, station_identity, uav_identity

K_STATE = 241
CONDITIONAL_BAN_CLASSES = ("RESOURCE_LOTTERY_CONDITIONAL_BAN", "R3_CHAIN_CONDITIONAL_BAN", "BLOCKED_BY_FAILED_PREFIX")


def dig(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def fingerprint(fx, o):
    """Physical request fingerprint: (k_p, canonical pickup-station identity, k_d, canonical drop-station
    identity).  Raw station indices are NOT part of it (CD R-4)."""
    return (int(o["k_p"]), station_identity(fx, int(o["c"])), int(o["k_d"]), station_identity(fx, int(o["d"])))


def duplicate_slots(fx):
    """GO 475 / CD R-4: freeze multiplicity per physical request fingerprint; unique fingerprint -> slot 0;
    exact duplicates -> exchangeable instance slots 0..m-1 assigned by ascending oid.  The dup slot DOES enter the
    owner variate key, the service-tuple key, the claim key and the ban key (it distinguishes the exchangeable
    instances); the oid itself never does.  Returns (oid->slot, fingerprint->m)."""
    groups = {}
    for o in fx["orders"]:
        groups.setdefault(fingerprint(fx, o), []).append(int(o["order_id"]))
    slot = {}
    for fp, oids in groups.items():
        for i, oid in enumerate(sorted(oids)):
            slot[oid] = i
    return slot, {fp: len(oids) for fp, oids in groups.items() if len(oids) > 1}


def duplicate_slot_collisions(fx, slot):
    """Detection (not a constant): (fingerprint, slot) pairs must be unique across all orders."""
    pairs = [(fingerprint(fx, o), slot[int(o["order_id"])]) for o in fx["orders"]]
    return len(pairs) - len(set(pairs))


# ----------------------------------------------------------------------------- static tuple universe
def v3r4_rows(fx, o, k_serv):
    """V3R4 ABSTRACT SERVICE-RESERVATION FOOTPRINT of one order served at k_serv (CD ruling 2026-08-31 X1,
    CONDITIONALLY_RATIFIED_AS_EXPLICIT_MECHANISM_AMENDMENT): {k_p} ∪ [arr, k_serv], mirroring the frozen V3R4
    uav_tails semantics (sh64_v3_outer.py:126-128).  It is NOT a complete-journey footprint: the object frozen before
    the resource lottery is the (order, owner, k_serv) proposal plus this abstract footprint; survivors' complete
    chain-true journeys are rebuilt afterwards in the disposable BatteryLedger on the accepted provisional prefix
    (owner / k_serv / C-D pairing unchanged; no refill, no second draw, no resample, no same-round Inner re-solve)."""
    arr = int(o["k_p"]) + int(fx["T_steps"][int(o["c"]) - 1, int(o["d"]) - 1])
    return {int(o["k_p"])} | set(range(arr, int(k_serv) + 1))


def base_tails_rows(fx, committed_journeys):
    """(tail_station, tail_time) and occupied rows per UAV from the immutable base snapshot
    (production journeys).  Semantics = frozen V3R4 uav_tails (sh64_v3_outer.py:113-128)."""
    tails = {i: (int(fx["births"][i]), 0) for i in range(int(fx["N"]))}
    rows = {}
    for j in sorted(committed_journeys, key=lambda j: (int(fx["orders"][j["order_id"] - 1]["k_p"]), j["order_id"])):
        i = int(j["owner"]); o = fx["orders"][j["order_id"] - 1]
        tails[i] = (int(j["post_state"]["tail_location"]), int(j["post_state"]["tail_slot"]))
        rr = rows.setdefault(i, set())
        rr.update(v3r4_rows(fx, o, j["k_serv"]))
    return tails, rows


def feasible_tuples(fx, o, tails, rows, banned_targets, ident_slot, dup_slot=0):
    """T_o under immutable base physics + audited bans (frozen V3R4 feasible_tuples semantics:
    tail-append chain time, row overlap, bans).  Battery admissibility is exact-checked at claim
    materialisation (GO 4.2 step 5).  excl["banned_keys"] lists the ban targets that excluded tuples."""
    T = fx["T_steps"]
    arr = o["k_p"] + int(T[o["c"] - 1, o["d"] - 1])
    if arr != o["k_d"] - 4:
        raise RuntimeError(f"CD_TIMING_CONTRACT oid={o['order_id']}")
    fp = fingerprint(fx, o)
    out, excl = [], {"banned": 0, "chain": 0, "overlap": 0, "banned_keys": []}
    need = {o["k_p"]} | set(range(arr, o["k_d"] + 1))
    for i in o["U_base"]:
        stn, tt = tails[i]
        Tt = int(T[stn - 1, o["c"] - 1]) if stn != o["c"] else 0
        if o["k_p"] - Tt < tt:
            excl["chain"] += 1; continue
        if rows.get(i, set()) & need:
            excl["overlap"] += 1; continue
        ident, slot = ident_slot[i]
        for k in o["W_D"]:
            key = (fp, dup_slot, ident, slot, int(k))
            if key in banned_targets:
                excl["banned"] += 1; excl["banned_keys"].append(key); continue
            out.append((i, int(k)))
    return out, excl


# ----------------------------------------------------------------------------- Inner inputs
def inner_inputs(fx, unresolved, provisional, base_journeys, provisional_pins=None):
    """GO 297 allowed inputs only: anonymous station-time demand, real current stations (birth or
    base tail), previous provisional pins as s/pins.  Provisional orders' D demand relocates to
    their provisional k_serv (mirrors commit_tokens relocation)."""
    N, K, M = int(fx["N"]), K_STATE, int(fx["M"])
    L = np.zeros((K, M), float)
    for oid in unresolved:
        o = fx["orders"][oid - 1]
        L[int(o["k_p"]), int(o["c"]) - 1] += 1.0
        kd = int(provisional[oid]["k_serv"]) if oid in provisional else int(o["k_d"]) - 4
        L[kd, int(o["d"]) - 1] += 1.0
    D = np.asarray(fx["D_cost"], float)
    Ccap = L.copy()
    lam = np.zeros((K, M), float); lam[Ccap > 0] = np.broadcast_to(2.0 * D.sum(0), (K, M))[Ccap > 0]
    tails, _ = base_tails_rows(fx, base_journeys)
    x0s = np.zeros((N, M), float)
    for u in range(N):
        x0s[u, tails[u][0] - 1] = 1.0
    s = np.zeros((N, K, M), float)
    pins = dict(provisional_pins or {})
    for (u, k), m in pins.items():
        s[u, k, m] = 1.0
    return {"N": N, "K": K, "M": M, "D": D, "L": L, "Ccap": Ccap, "lam_cap": lam, "x0s": x0s, "s": s, "pins": pins}


def physical_response_certificate(x, x_null, x_tail8, x_tail14, L, pins=None):
    """Round-level physical-response certificate (frozen formula, EFFECTIVE_READOUT_SEAL_V2): the field must
    respond to demand: mean|x - x_null| over demanded cells (L>0) must exceed the same statistic over
    non-demanded service cells by more than the tail noise floor mean|x8 - x14| taken over the SAME demanded
    cells (review m8).  Pinned (u,k) rows are excluded from all three means (review z19: pins are one-hot in x
    and absent from x_null, so they would certify a 'response' by construction).  No demanded cells -> PASS=False."""
    dem = L > 0
    dem[0, :] = False; nod = ~dem; nod[0, :] = False
    if int(dem.sum()) == 0:
        return {"PASS": False, "reason": "no demanded cells", "response_demanded": None, "response_non_demanded": None, "tail_noise": None}
    keep = np.ones(x.shape[:2], bool)                 # (N, K) rows kept
    for (u, k) in (pins or {}):
        keep[int(u), int(k)] = False
    diff = np.abs(x - x_null)
    m_dem = keep[:, :, None] & dem[None, :, :]; m_nod = keep[:, :, None] & nod[None, :, :]
    if int(m_dem.sum()) == 0:
        return {"PASS": False, "reason": "all demanded cells pinned", "response_demanded": None, "response_non_demanded": None, "tail_noise": None, "pinned_rows_excluded": int((~keep).sum())}
    resp_dem = float(diff[m_dem].mean()); resp_nod = float(diff[m_nod].mean()) if int(m_nod.sum()) else 0.0
    noise = float(np.abs(x_tail8 - x_tail14)[m_dem].mean())
    return {"PASS": bool(resp_dem > resp_nod + noise), "response_demanded": resp_dem, "response_non_demanded": resp_nod, "tail_noise": noise,
            "demanded_cells": int(dem.sum()), "pinned_rows_excluded": int((~keep).sum())}


def provisional_pins_bulk(fx, journeys):
    """ONE materialize pass over all provisional journeys (O(N*K) once per round, not per order);
    canonical single-write-per-row semantics enforced by the frozen kernel itself."""
    if not journeys:
        return {}
    from experiments import sh64_bat3_journey as J
    return dict(J.materialize_journeys(fx, list(journeys))["pins"])


def slot_table_digest(ident_slot):
    return dig([[int(u), i, int(s)] for u, (i, s) in sorted(ident_slot.items())])


def slot_table_for_fx(fx, auth):
    """Run-start instance slot table for a fixture (CPU, no controller needed): raw_u -> (identity, slot)."""
    tails, _ = base_tails_rows(fx, [])
    ids = {u: uav_identity(station_identity(fx, int(fx["births"][u])), (station_identity(fx, tails[u][0]), tails[u][1], int(auth.B_init), 0)) for u in range(int(fx["N"]))}
    t = assign_slots(ids)
    return t, slot_table_digest(t)


def writeback_digest(new_bans, new_prov, pins_digest):
    """Pure function (testable): the round-end writeback digest covers ban targets, ban evidence, the whole
    provisional plan (owner, k_serv, journey digest, provenance, origin round), the provisional-pin digest and
    the anonymous mask digest.  Masks ARE the projection of the provisional pins (NEW_UNIVERSAL_ANONYMOUS_MASKS
    is empty by construction, review m5), so the mask component equals the pin digest."""
    return dig({"ban_targets": sorted(map(list, new_bans.keys())),
                "ban_evidence": sorted(json.dumps(v, sort_keys=True, default=str) for v in new_bans.values()),
                "prov": {oid: [p["owner"], p["k_serv"], p["journey_digest"], p["provenance"], p.get("origin_round")] for oid, p in sorted(new_prov.items())},
                "pins": pins_digest, "mask": pins_digest})


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k) if not isinstance(k, str) else k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


# ----------------------------------------------------------------------------- controller
class GlobalController:
    def __init__(self, fx, auth, policy, *, backend, run_uuid, run_seed, work, x_null, identity,
                 checkpoints=(4, 8, 16, 32, 64, 128, 256), hard_cap=256, log=print, on_round_end=None, round_body=None):
        self.fx, self.auth, self.policy, self.backend = fx, auth, policy, backend
        self.run_uuid, self.run_seed, self.work, self.log = run_uuid, int(run_seed), work, log
        self.x_null, self.identity = x_null, identity
        self.checkpoints, self.hard_cap = list(checkpoints), int(hard_cap)
        self.on_round_end = on_round_end
        # Gate 1 (GO section 10 / CD ruling 2026-08-31 section 6) test-only seam: when given, the legacy single-destination
        # battery-OFF round body (donor Released-R3 primitives) runs on THIS skeleton after the shared steps 1-2 (freeze inputs,
        # ONE global solve).  Never set on the science path: LEGACY_ROUND_BODY_ROUND_COUNT must be 0 in every formal record.
        self.round_body = round_body
        self.reg = ResourceLotteryRegistry(run_seed)
        self.base_journeys = []                    # production (empty until final commit)
        self.base_committed = []
        self.provisional = {}                      # oid -> {owner, k_serv, journey, journey_digest, provenance, ...}
        self.provisional_pins = {}                 # merged round-level pins (bulk materialize)
        self.bans = {}                             # target_key(tuple) -> evidence list
        self.resolved = {}                         # oid -> terminal status (ACCEPTED / REJECTED_SEARCH_EXHAUSTED / REJECTED_HARD_INFEASIBLE)
        self.lottery_seen = {}                     # (group_fingerprint, universe, C) -> round of first draw (redraw detection)
        self.dup_slot, self.dup_multiplicity = duplicate_slots(fx)
        self.history = []
        self.counters = {"INNER_SOLVE_COUNT": 0, "PER_ORDER_INNER_SOLVE_COUNT": 0, "GLOBAL_MULTIPLE_UPDATE_ROUND_COUNT": 0,
                         "OWNER_POLICY_SWITCH_AFTER_OUTCOME_COUNT": 0, "PROVENANCE_UPGRADE_ATTEMPT_COUNT": 0,
                         "RESOURCE_LOTTERY_OWNER_CHANGE_COUNT": 0, "PRODUCTION_COMMIT_COUNT_BEFORE_FINAL": 0,
                         "WEIGHTED_SAME_RNG_OWNER_DIFFERENCE_COUNT": 0, "HALF_ORDER_PROVISIONAL_PIN_COUNT": 0,
                         "FAILED_ORDER_PREFIX_PIN_COUNT": 0, "STALE_PROVISIONAL_RESERVATION_COUNT": 0,
                         "DOUBLE_COUNTED_PROVISIONAL_CAPACITY_COUNT": 0, "SELF_PIN_REINFORCEMENT_ONLY_COUNT": 0,
                         "DUPLICATE_PHYSICAL_FINGERPRINT_COUNT": len(self.dup_multiplicity),
                         "DUPLICATE_INSTANCE_SLOT_COLLISION_COUNT": duplicate_slot_collisions(fx, self.dup_slot),
                         "BAN_KEY_UNRESOLVABLE_COUNT": 0, "LEGACY_ROUND_BODY_ROUND_COUNT": 0}
        os.makedirs(f"{work}/rounds", exist_ok=True)
        self._compute_identities()
        self._refresh_universe()

    # canonical UAV identities: (canonical birth-hub identity, canonical base tail); NO ban digest (review B2).
    # X4 a-prime protocol (CD ruling 2026-08-31): same base identity => exchangeable instances; the anonymous instance
    # slot is assigned ONCE here (ascending raw index within the identity class), digested into slot_table_digest,
    # persisted with every checkpoint and verified on resume; it is run-local bookkeeping, never a physical identity,
    # and never derived from G/g, field rows, round state or outcomes.
    def _compute_identities(self):
        tails, _ = base_tails_rows(self.fx, self.base_journeys)
        ids = {u: uav_identity(station_identity(self.fx, int(self.fx["births"][u])),
                               (station_identity(self.fx, tails[u][0]), tails[u][1], int(self.auth.B_init), 0))
               for u in range(int(self.fx["N"]))}
        self.ident_slot = assign_slots(ids)
        self._identity_set = sorted(set(ids.values()))
        self.slot_table_digest = slot_table_digest(self.ident_slot)

    def slot_table(self):
        return {str(u): [i, s] for u, (i, s) in sorted(self.ident_slot.items())}

    def _refresh_universe(self):
        """Candidate universe digest = base physical state + audited hard bans (bans DO belong here)."""
        hb = dig(sorted(map(list, self.bans.keys())))
        self.universe_digest = candidate_universe_digest(self._identity_set, hb)

    def _wj(self, name, o):
        p = f"{self.work}/rounds/{name}"
        with open(p + ".tmp", "w") as f:
            json.dump(o, f, indent=1, default=str); f.flush(); os.fsync(f.fileno())
        os.replace(p + ".tmp", p)

    def _rejected_status(self, excl):
        """m4: classification by the evidence classes of the bans that excluded tuples: any conditional
        (lottery / chain / prefix) exclusion -> REJECTED_SEARCH_EXHAUSTED (search-path exclusion, not
        physical infeasibility); otherwise (static/chain-time/overlap only) -> REJECTED_HARD_INFEASIBLE."""
        for key in excl.get("banned_keys", []):
            for ev in self.bans.get(key, []):
                if ev.get("reason_class") in CONDITIONAL_BAN_CLASSES:
                    return "REJECTED_SEARCH_EXHAUSTED"
        return "REJECTED_HARD_INFEASIBLE"

    def _verify_zero_factors_pinned(self, vec_name, x, o, T_o, owners, pins, round_id):
        """Y2 rulings (2026-08-31 item 7 + TAIL_PERM_PIN_ORIGIN ruling section 4): a -inf joint readout in ANY input vector
        (x, x8, x14, x20, inverse-mapped permutation tail) is admissible ONLY when every exactly-zero factor of that vector
        sits on a cell that the round input pins to another station (pinned one-hot row); any other exact zero is a
        numerical/mapping fault -> hard fail, never NOT_EVALUABLE."""
        kp, c, d = int(o["k_p"]), int(o["c"]) - 1, int(o["d"]) - 1
        for u in owners:
            zero_cells = []
            if float(x[u, kp, c]) <= 0.0:
                zero_cells.append((u, kp, c))
            ks = [k for uu, k in T_o if uu == u]
            if ks and all(float(x[u, k, d]) <= 0.0 for k in ks):
                zero_cells.extend((u, k, d) for k in ks if float(x[u, k, d]) <= 0.0)
            if not zero_cells:
                raise RuntimeError(f"READOUT_NON_FINITE_UNEXPECTED: {vec_name} joint readout non-finite for owner u={u} but no exact-zero factor located (round {round_id}, oid {o['order_id']})")
            for (uu, k, m) in zero_cells:
                pinned = pins.get((int(uu), int(k)))
                if pinned is None or int(pinned) == int(m):
                    raise RuntimeError(f"READOUT_NON_FINITE_UNEXPECTED: {vec_name} zero factor at (u={uu},k={k},station={m + 1}) is not a pinned-elsewhere cell (round {round_id}, oid {o['order_id']})")

    def _observer_diag(self, x, x_tail, x_perm, o, T_o, owners_canon, phys_pass, self_pin_free, pins=None, round_id=None):
        order_canon = [c[2] for c in owners_canon]
        gv = RO.g_vector(x, o, T_o); g_x = [gv[u] for u in order_canon]
        g8v, g14v, g20v = (RO.g_vector(xx, o, T_o) for xx in x_tail)
        g8, g14, g20 = [g8v[u] for u in order_canon], [g14v[u] for u in order_canon], [g20v[u] for u in order_canon]
        gvp = RO.g_vector(x_perm, o, T_o); g_perm = [gvp[u] for u in order_canon]
        gvn = RO.g_vector(self.x_null, o, T_o); g_null = [gvn[u] for u in order_canon]
        if not all(np.isfinite(g_null)):                                  # the null control has no pins: a zero factor there is a fault
            raise RuntimeError(f"READOUT_NON_FINITE_UNEXPECTED: null-control readout non-finite for oid {o['order_id']}")
        # TAIL_PERM_PIN_ORIGIN ruling: EVERY vector whose joint readout is non-finite must prove its zero factors pin-legal —
        # not only the proposal field x (the earlier code checked x alone, so a tail- or permutation-only unproven zero could
        # hide behind NOT_EVALUABLE)
        pins = pins or {}
        for vec_name, arr, gvals in (("x", x, g_x), ("x8", x_tail[0], g8), ("x14", x_tail[1], g14), ("x20", x_tail[2], g20), ("x_perm", x_perm, g_perm)):
            if not all(np.isfinite(gvals)):
                self._verify_zero_factors_pinned(vec_name, arr, o, T_o, [u for u, g in zip(order_canon, gvals) if not np.isfinite(g)], pins, round_id)
        return RO.qualify_v2(g_x, g8, g14, g20, g_perm, g_null, physical_response_pass=phys_pass, self_pin_free_pass=self_pin_free)

    # ------------------------------------------------------------------ one round
    def round(self, r):
        fx = self.fx
        unresolved = [o["order_id"] for o in fx["orders"] if o["order_id"] not in self.resolved]
        slot_of = self.dup_slot
        t0 = time.time()
        # 1. freeze round inputs
        prev_prov = {oid: (p["owner"], p["k_serv"], p["journey_digest"]) for oid, p in self.provisional.items()}
        inp = inner_inputs(fx, unresolved, self.provisional, self.base_journeys, self.provisional_pins)
        start = {"RUN_UUID": self.run_uuid, "ROUND_ID": r, "BASE_IMMUTABLE_FLEET_SNAPSHOT_DIGEST": dig([j["digest"] for j in self.base_journeys]),
                 "PREVIOUS_PROVISIONAL_STATE_DIGEST": dig(prev_prov), "ANONYMOUS_DEMAND_DIGEST_IN": hashlib.sha256(inp["L"].tobytes()).hexdigest(),
                 "ANONYMOUS_CELL_MASK_DIGEST_IN": hashlib.sha256(inp["s"].tobytes()).hexdigest(),
                 "ORDER_SIDECAR_BAN_DIGEST_IN": dig(sorted(map(list, self.bans.keys()))), "RNG_REGISTRY_DIGEST": dig(self.reg.registry()),
                 "CANDIDATE_UNIVERSE_DIGEST": self.universe_digest, "unresolved": len(unresolved)}
        self._wj(f"round{r:03d}_start.json", start)
        # 2. ONE global Inner solve
        sol = self.backend(inp)
        self.counters["INNER_SOLVE_COUNT"] += 1
        x, x_tail, x_perm = sol["x"], sol["x_tail"], sol["x_perm_tail"]
        # Y2 ruling item 7: a non-finite FIELD is a numerical fault (never NOT_EVALUABLE); only exactly-zero pinned cells may
        # later produce -inf in the log-domain readout
        for nm, arr in (("x", x), ("x8", x_tail[0]), ("x14", x_tail[1]), ("x20", x_tail[2]), ("x_perm", x_perm)):
            a_ = np.asarray(arr)
            if not np.isfinite(a_).all():
                raise RuntimeError(f"FIELD_NON_FINITE_HARD_FAIL: {nm} contains NaN/inf in round {r}")
            if (a_ < 0.0).any():                                          # review M8: a negative field entry is a numerical fault, not a zero factor
                raise RuntimeError(f"FIELD_NEGATIVE_HARD_FAIL: {nm} has negative entries in round {r}")
        if self.round_body is not None:                                  # Gate 1 legacy parity seam (test-only; see __init__)
            self.counters["LEGACY_ROUND_BODY_ROUND_COUNT"] += 1
            rec = self.round_body(self, r, unresolved, inp, start, sol)
            self.history.append(rec)
            self._wj(f"round{r:03d}_end.json", rec)
            self.counters["GLOBAL_MULTIPLE_UPDATE_ROUND_COUNT"] = r + 1
            return rec
        # 3. proposals from the frozen field (previous provisional released for capacity: step 4 is implicit
        #    because provisional never enters the production ledger; base rows only)
        tails, rows = base_tails_rows(fx, self.base_journeys)
        phys = physical_response_certificate(x, self.x_null, x_tail[0], x_tail[1], inp["L"], pins=inp["pins"])
        unstable_orders, unstable_carried, observer_tested = 0, 0, 0
        not_eval_new, not_eval_carried, perm_fail_new, perm_fail_carried = 0, 0, 0, 0
        proposals, prov_table = [], {}
        carried = 0
        exhausted_now = []
        banned_excl_total = 0
        # stale-reservation detection (review z8): the pins fed to the Inner must be exactly the previous round's
        # provisional pins (digest equality with PROVISIONAL_PINS_DIGEST of the last round; round 0 -> empty)
        pins_in_digest = dig(sorted([[int(u), int(k), int(m)] for (u, k), m in inp["pins"].items()]))
        prev_pins_digest = self.history[-1]["PROVISIONAL_PINS_DIGEST"] if self.history else dig([])
        stale_in = 0 if pins_in_digest == prev_pins_digest else len(inp["pins"])
        self.counters["STALE_PROVISIONAL_RESERVATION_COUNT"] += stale_in
        for oid in unresolved:
            o = fx["orders"][oid - 1]; fp = fingerprint(fx, o)
            T_o, excl = feasible_tuples(fx, o, tails, rows, self.bans, self.ident_slot, slot_of[oid])
            banned_excl_total += excl["banned"]
            if not T_o:
                status = self._rejected_status(excl)
                prov_table[oid] = {"provenance": RO.PROV_NONE, "excl": {k: v for k, v in excl.items() if k != "banned_keys"}, "terminal": status}
                self.resolved[oid] = status; exhausted_now.append(oid); continue
            owners_raw = sorted({u for u, _k in T_o})
            owners_canon = sorted(((self.ident_slot[u][0], self.ident_slot[u][1], u) for u in owners_raw))
            self_pin_free = not any((u, k) in inp["pins"] for u, k in ((uu, int(o["k_p"])) for uu in owners_raw))
            # GO 5.5: an order that already holds a provisional proposal carries its ORIGIN certificate
            # (keep or degrade, never upgrade); it is re-proposed unchanged while its tuple is still in T_o
            # and not banned.  Own-pin readouts are diagnostics only (SELF_PIN_REINFORCEMENT_ONLY), but the
            # held-out observer is still evaluated for the round-level certificate (review M4).
            pv = self.provisional.get(oid)
            if pv is not None and (pv["owner"], pv["k_serv"]) in set(T_o):
                u_sel, k_sel, how = pv["owner"], pv["k_serv"], "CARRIED_ORIGIN"
                ident, slot = self.ident_slot[u_sel]
                if len(owners_raw) >= 2:
                    dq = self._observer_diag(x, x_tail, x_perm, o, T_o, owners_canon, phys["PASS"], self_pin_free, pins=inp["pins"], round_id=r)
                    if dq.get("observer_evaluable"):
                        observer_tested += 1
                        if dq.get("observer_unstable"):
                            unstable_carried += 1
                        if dq.get("PERM_EQUIVARIANT") is False:
                            perm_fail_carried += 1
                    else:
                        not_eval_carried += 1
                proposals.append({"oid": oid, "raw_u": u_sel, "k_serv": k_sel, "fingerprint": fp, "dup_slot": slot_of[oid],
                                  "owner_id": ident, "owner_slot": slot, "provenance": pv["provenance"], "tuple_rule": how,
                                  "QUALIFIED_G": pv.get("QUALIFIED_G", False), "TV_o": pv.get("TV_o"), "TAU_TV": pv.get("TAU_TV"),
                                  "selected_p_G": pv.get("selected_p_G"), "uniform_baseline": pv.get("uniform_baseline"),
                                  "origin_universe_digest": pv.get("origin_universe_digest"), "origin_x_sha256": pv.get("origin_x_sha256"),
                                  "origin_round": pv.get("origin_round", r - 1), "self_pin_free_origin": pv.get("self_pin_free_origin")})
                prov_table[oid] = {"provenance": pv["provenance"], "owner": u_sel, "k_serv": k_sel, "carried": True}
                carried += 1
                continue
            u_var = self.reg.owner_variate(fp, self.universe_digest, slot_of[oid])
            if len(owners_raw) >= 2:
                qual = self._observer_diag(x, x_tail, x_perm, o, T_o, owners_canon, phys["PASS"], self_pin_free, pins=inp["pins"], round_id=r)
                if qual.get("observer_evaluable"):
                    observer_tested += 1
                    if qual.get("observer_unstable"):
                        unstable_orders += 1
                    if qual.get("PERM_EQUIVARIANT") is False:
                        perm_fail_new += 1
                else:
                    not_eval_new += 1
            else:
                qual = {"QUALIFIED_G": False, "n": len(owners_raw), "observer_unstable": False, "observer_evaluable": False}
            d = RO.decide_owner(owners_canon, T_o, qual, u_var)
            if d["provenance"] in (RO.PROV_WEIGHTED, RO.PROV_UNIFORM) and d.get("WEIGHTED_SAME_RNG_OWNER_DIFFERENT"):
                self.counters["WEIGHTED_SAME_RNG_OWNER_DIFFERENCE_COUNT"] += 1
            u_sel = d["owner"]
            ident, slot = self.ident_slot[u_sel]
            tuniv = dig(sorted(k for uu, k in T_o if uu == u_sel))
            k_sel, how = RO.decide_service_tuple(x, o, u_sel, T_o, d["provenance"],
                                                 lambda n: self.reg.service_tuple_variate("tie", fp, slot_of[oid], (ident, slot), tuniv),
                                                 lambda n: self.reg.service_tuple_variate("uniform", fp, slot_of[oid], (ident, slot), tuniv))
            proposals.append({"oid": oid, "raw_u": u_sel, "k_serv": k_sel, "fingerprint": fp, "dup_slot": slot_of[oid],
                              "owner_id": ident, "owner_slot": slot, "provenance": d["provenance"], "tuple_rule": how,
                              "QUALIFIED_G": bool(qual.get("QUALIFIED_G")), "TV_o": qual.get("TV_o"), "TAU_TV": qual.get("TAU_TV"),
                              "selected_p_G": (qual["p_G"][[c[2] for c in owners_canon].index(u_sel)] if qual.get("p_G") else None),
                              "uniform_baseline": qual.get("uniform_baseline"), "observer_unstable": qual.get("observer_unstable"),
                              "observer_evaluable": bool(qual.get("observer_evaluable")), "PERM_EQUIVARIANT": qual.get("PERM_EQUIVARIANT"),
                              "origin_universe_digest": self.universe_digest, "origin_x_sha256": (sol.get("record") or {}).get("x_sha256"),
                              "origin_round": r, "self_pin_free_origin": self_pin_free})
            prov_table[oid] = {"provenance": d["provenance"], "owner": u_sel, "k_serv": k_sel, "qual": {k: qual.get(k) for k in ("QUALIFIED_G", "TV_o", "TAU_TV", "RAW_G_SPREAD", "TAU_G")}}
        self.counters["SELF_PIN_REINFORCEMENT_ONLY_COUNT"] += carried
        freeze = {"PROPOSAL_SET_DIGEST": dig([(p["oid"], p["owner_id"], p["owner_slot"], p["k_serv"]) for p in proposals]),
                  "PROPOSAL_OWNER_TIME_TABLE": {p["oid"]: [p["raw_u"], p["k_serv"]] for p in proposals},
                  "PROPOSAL_PROVENANCE_TABLE": prov_table,
                  "ROUND_MASK_DIGEST_AT_FREEZE": start["ANONYMOUS_CELL_MASK_DIGEST_IN"], "ROUND_BAN_DIGEST_AT_FREEZE": start["ORDER_SIDECAR_BAN_DIGEST_IN"],
                  "audit": {"PROPOSAL_FREEZE_UTC": time.strftime("%FT%TZ", time.gmtime())}}
        self._wj(f"round{r:03d}_proposals.json", freeze)
        # 5. claim materialisation from the immutable snapshot (base ledger)
        from experiments import sh64_bat3_ledger as L3
        base_led = L3.BatteryLedgerV3(fx, self.auth, self.policy, run_id=f"{self.run_uuid}:r{r}:base", identity=self.identity)
        BJ._seed_from_committed(base_led, fx, self.base_committed)
        claims, static_fail = [], []
        for p in proposals:
            o = fx["orders"][p["oid"] - 1]
            jn, jrows, fail = BJ.materialise_claim(fx, self.auth, self.policy, base_led, p["raw_u"], o, p["k_serv"])
            if fail:
                static_fail.append({**p, **fail}); continue
            p["journey_digest"] = jn["digest"]; p["journey"] = jn; p["rows"] = jrows
            claims.append(RL.Claim(p["fingerprint"], p["dup_slot"], p["owner_id"], p["owner_slot"], p["raw_u"], p["k_serv"], jn["digest"],
                                   BJ.claim_footprint(p["owner_id"], p["owner_slot"], o, p["k_serv"], jrows, jn, fx=fx)))
        # 6-7. groups + frozen lottery
        groups = RL.build_all_groups(claims, BJ.residual_capacity_factory(fx["hard_contract"]))
        self._wj(f"round{r:03d}_groups.json", {gf: {k: v for k, v in g.items()} for gf, g in groups.items()})
        lot = RL.run_lottery(claims, groups, self.reg, r, seen=self.lottery_seen)
        surv_keys = {json.dumps(c.key(), sort_keys=True, separators=(",", ":"), default=str) for c in lot["survivors"]}
        survivors = [p for p in proposals if "journey" in p and json.dumps(RL.Claim(p["fingerprint"], p["dup_slot"], p["owner_id"], p["owner_slot"], p["raw_u"], p["k_serv"], p["journey_digest"], []).key(), sort_keys=True, separators=(",", ":"), default=str) in surv_keys]
        # 8-9. disposable-ledger dry run
        dr = BJ.dry_run(fx, self.auth, self.policy, self.base_committed, survivors, self.run_uuid, r, identity=self.identity)
        if freeze["ROUND_BAN_DIGEST_AT_FREEZE"] != dig(sorted(map(list, self.bans.keys()))):
            raise RuntimeError("ROUND_BAN_DIGEST_CHANGED_DURING_VALIDATION")
        hard = BJ.validate_accepted_batch(fx, self.auth, dr, identity=self.identity)   # real hard validation of the accepted batch
        dr["BATCH_HARD_VIOLATION_COUNT"] = hard["hard_total"]
        # 10. one round-end writeback
        new_bans = {}
        for f in static_fail:
            new_bans.setdefault((f["fingerprint"], f["dup_slot"], f["owner_id"], f["owner_slot"], f["k_serv"]), []).append({"reason_class": "STATIC_TUPLE_FAILURE", "reason": f["reason"], "source_round": r})
        for b in lot["bans"]:
            t = b["BAN_TARGET_KEY"]; key = (tuple(t[0]), t[1], t[2][0], t[2][1], t[3])
            new_bans.setdefault(key, []).extend(b["BAN_EVIDENCE_RECORDS"])
        for rj in dr["rejected"]:
            key = (tuple(rj["fingerprint"]), rj["dup_slot"], rj["owner_id"], rj["owner_slot"], rj["k_serv"])
            new_bans.setdefault(key, []).append({"reason_class": rj["class"], "reason": rj.get("reason"), "source_round": r})
        n_new_targets = sum(1 for k in new_bans if k not in self.bans)
        # ban keys must resolve to a currently existing (identity, slot): detection of dead-letter bans (review B2)
        live = {(i, s) for i, s in self.ident_slot.values()}
        dead = sum(1 for k in new_bans if (k[2], k[3]) not in live)
        self.counters["BAN_KEY_UNRESOLVABLE_COUNT"] += dead
        if dead:
            raise RuntimeError(f"BAN_KEY_UNRESOLVABLE: {dead} new ban targets do not map to a live owner identity/slot")
        for k, ev in new_bans.items():
            self.bans.setdefault(k, []).extend(ev)
        new_prov = {}
        acc_by_oid = {a["oid"]: a for a in dr["accepted"]}
        committed_j = {int(j["order_id"]): j for j in dr["journeys"]}    # the dry-run COMMITTED journeys (chain-true)
        for p in survivors:
            if p["oid"] in acc_by_oid:
                jn = committed_j[p["oid"]]
                new_prov[p["oid"]] = {"owner": p["raw_u"], "k_serv": p["k_serv"], "journey": jn, "journey_digest": jn["digest"],
                                      "provenance": p["provenance"], "dup_slot": p["dup_slot"],
                                      "QUALIFIED_G": p["QUALIFIED_G"], "TV_o": p["TV_o"], "TAU_TV": p["TAU_TV"],
                                      "selected_p_G": p.get("selected_p_G"), "uniform_baseline": p.get("uniform_baseline"),
                                      "origin_universe_digest": p.get("origin_universe_digest"), "origin_x_sha256": p.get("origin_x_sha256"),
                                      "origin_round": p.get("origin_round", r), "self_pin_free_origin": p.get("self_pin_free_origin")}
        new_pins = provisional_pins_bulk(fx, [v["journey"] for v in new_prov.values()])
        pins_digest = dig(sorted([[int(u), int(k), int(m)] for (u, k), m in new_pins.items()]))
        # half-order detection (review z8): every provisional journey must have BOTH its pickup pin (owner, k_p) -> c
        # and its service pin (owner, k_serv) -> d present in the bulk pins; a journey missing either = half order
        half = 0
        for v in new_prov.values():
            o = fx["orders"][v["journey"]["order_id"] - 1]; u = int(v["owner"])
            if new_pins.get((u, int(o["k_p"]))) != int(o["c"]) - 1 or new_pins.get((u, int(v["k_serv"]))) != int(o["d"]) - 1:
                half += 1
        self.counters["HALF_ORDER_PROVISIONAL_PIN_COUNT"] += half
        # failed-order prefix pins (review m2, X1 ruling 2.5): a rejected proposal must leave no pins of its own — detected as its
        # pickup AND service cells both pinned to its stations on its proposed owner (identical-fingerprint duplicates may alias; reported)
        failed_prefix_pins = 0
        for rj in dr["rejected"]:
            o_rj = fx["orders"][int(rj["oid"]) - 1]; u_rj = int(rj["raw_u"]) if "raw_u" in rj else None
            if u_rj is not None and new_pins.get((u_rj, int(o_rj["k_p"]))) == int(o_rj["c"]) - 1 and new_pins.get((u_rj, int(rj["k_serv"]))) == int(o_rj["d"]) - 1:
                failed_prefix_pins += 1
        self.counters["FAILED_ORDER_PREFIX_PIN_COUNT"] += failed_prefix_pins
        # double-counted provisional capacity (review z8/X1): two provisional journeys of the SAME owner whose frozen
        # V3R4 occupancy rows intersect (a legal same-UAV chain has disjoint rows and is not double counting)
        by_owner = {}
        for v in new_prov.values():
            by_owner.setdefault(int(v["owner"]), []).append(v3r4_rows(fx, fx["orders"][v["journey"]["order_id"] - 1], v["k_serv"]))
        dbl = 0
        for rs in by_owner.values():
            for a in range(len(rs)):
                for b in range(a + 1, len(rs)):
                    if rs[a] & rs[b]:
                        dbl += 1
        self.counters["DOUBLE_COUNTED_PROVISIONAL_CAPACITY_COUNT"] += dbl
        writeback = {"NEW_BAN_TARGET_COUNT": n_new_targets, "NEW_BAN_EVIDENCE_COUNT": sum(len(v) for v in new_bans.values()),
                     "NEW_COMPLETE_ORDER_PROVISIONAL_PINS": len(new_pins), "PROVISIONAL_PINS_DIGEST": pins_digest,
                     "WRITEBACK_DIGEST": writeback_digest(new_bans, new_prov, pins_digest)}
        # 11. atomic replace of the provisional set (previous fully released)
        self.provisional = new_prov
        self.provisional_pins = new_pins
        self._refresh_universe()
        full_plan_digest = dig({oid: [p["owner"], p["k_serv"]] for oid, p in self.provisional.items()})
        state_digest = dig({"plan": full_plan_digest, "bans": sorted(map(list, self.bans.keys())), "pins": pins_digest,
                            "resolved": sorted([[o, st] for o, st in self.resolved.items()])})
        inner_state = (sol.get("record") or {}).get("closure_state")
        unstable_total = unstable_orders + unstable_carried
        not_eval_total = not_eval_new + not_eval_carried
        multi_owner_total = observer_tested + not_eval_total
        observer_cert = {"orders_multi_owner": multi_owner_total, "orders_evaluable": observer_tested, "orders_not_evaluable": not_eval_total,
                         "not_evaluable_new": not_eval_new, "not_evaluable_carried": not_eval_carried,
                         "unstable_new": unstable_orders, "unstable_carried": unstable_carried,
                         "perm_equivariance_fail_new": perm_fail_new, "perm_equivariance_fail_carried": perm_fail_carried,
                         "status": ("UNSTABLE" if unstable_total > 0 else ("PASS" if observer_tested > 0 else ("NO_MULTI_OWNER_ORDERS" if multi_owner_total == 0 else "NOT_EVALUABLE"))),
                         "scope": "all multi-owner unresolved orders incl. carried (diagnostics only for carried); non-finite joint readouts are NOT_EVALUABLE, never counted as stable"}
        observer_cert["PASS"] = observer_cert["status"] == "PASS"       # Y2: NOT_EVALUABLE / NO_MULTI_OWNER_ORDERS are never a stable pass
        inner_subtype = None
        if inner_state not in ("RAW_INNER_CLOSED", "READOUT_STABLE_RAW_UNCLOSED"):
            inner_state = None                                          # backend did not certify -> closure condition 1 fails
        elif inner_state == "READOUT_STABLE_RAW_UNCLOSED" and unstable_total > 0:
            inner_state = "RAW_UNCLOSED_UNSTABLE_WITH_UNIFORM_FAIL_CLOSED"; inner_subtype = "OBSERVER_UNSTABLE"
        elif inner_state == "READOUT_STABLE_RAW_UNCLOSED" and observer_cert["status"] != "PASS":
            # Y2 ruling item 6: raw Inner unclosed AND observer not evaluable -> never claim readout stability; uniform
            # fail-closed path with the NOT_EVALUABLE subtype disclosed (RAW_INNER_CLOSED rounds are not relabelled, item 5)
            inner_state = "RAW_UNCLOSED_UNSTABLE_WITH_UNIFORM_FAIL_CLOSED"; inner_subtype = "OBSERVER_" + observer_cert["status"]
        uniform_fail_closed = sum(1 for p in proposals if p.get("provenance") == RO.PROV_UNIFORM and p.get("tuple_rule") != "CARRIED_ORIGIN")
        unresolved_count = len(unresolved) - len(new_prov) - len(exhausted_now)
        rec = {"round": r, "unresolved": len(unresolved), "proposals": len(proposals), "static_fail": len(static_fail),
               "claims": len(claims), "groups": len(groups), "lottery": lot["counters"], "survivors": len(survivors),
               "accepted": len(dr["accepted"]), "rejected": len(dr["rejected"]), "DRY_RUN_DECISION_DIGEST": dr["DECISION_DIGEST"],
               "DRY_RUN_JOURNEY_DIGEST": dr.get("JOURNEY_DIGEST"),
               "PROPOSAL_SET_DIGEST": freeze["PROPOSAL_SET_DIGEST"], "FULL_PLAN_DIGEST": full_plan_digest,
               "UNRESOLVED_REQUEST_COUNT": unresolved_count, "BATCH_HARD_VIOLATION_COUNT": dr["BATCH_HARD_VIOLATION_COUNT"],
               "STATE_DIGEST": state_digest, "INNER_NUMERICAL_STATE": inner_state, "INNER_STATE_SUBTYPE": inner_subtype, "OBSERVER_UNSTABLE_ORDER_COUNT": unstable_total,
               "OBSERVER_UNSTABLE_PRESENT": unstable_total > 0, "OBSERVER_NOT_EVALUABLE_ORDER_COUNT": not_eval_total, "OBSERVER_CERTIFICATE": observer_cert,
               "OBSERVER_NOT_EVALUABLE_NEW_COUNT": not_eval_new, "OBSERVER_NOT_EVALUABLE_CARRIED_COUNT": not_eval_carried,
               "OBSERVER_STABLE_ORDER_COUNT": observer_tested - unstable_total, "UNIFORM_FAIL_CLOSED_COUNT": uniform_fail_closed,
               "PERM_EQUIVARIANT_FAIL_COUNT": perm_fail_new + perm_fail_carried, "SLOT_TABLE_DIGEST": self.slot_table_digest,
               "PHYSICAL_RESPONSE": phys, "REJECTED_SEARCH_EXHAUSTED_NOW": sum(1 for o in exhausted_now if self.resolved[o] == "REJECTED_SEARCH_EXHAUSTED"),
               "REJECTED_HARD_INFEASIBLE_NOW": sum(1 for o in exhausted_now if self.resolved[o] == "REJECTED_HARD_INFEASIBLE"),
               "SAME_RESOURCE_LOTTERY_UNIVERSE_REDRAW_COUNT": lot["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"],
               "FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT": dr["FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT"], "POST_LOTTERY_CHAIN_BAN_COUNT": dr["POST_LOTTERY_CHAIN_BAN_COUNT"],
               "R3_CHAIN_CONDITIONAL_BAN_COUNT": sum(1 for ev in new_bans.values() for e in ev if e.get("reason_class") == "R3_CHAIN_CONDITIONAL_BAN"),   # X1 ruling 2.7: per-round mandatory counters
               "BLOCKED_BY_FAILED_PREFIX_COUNT": dr.get("BLOCKED_BY_FAILED_PREFIX_COUNT", sum(1 for ev in new_bans.values() for e in ev if e.get("reason_class") == "BLOCKED_BY_FAILED_PREFIX")),
               "FAILED_ORDER_PREFIX_PIN_COUNT_ROUND": failed_prefix_pins,
               "BANNED_EXCLUSION_COUNT": banned_excl_total, "STALE_PIN_INPUT_COUNT": stale_in, "HALF_ORDER_PIN_COUNT_ROUND": half,
               **writeback, "inner_record": sol.get("record"), "provenance_counts": _count(p["provenance"] for p in proposals), "carried_origin": carried,
               "INNER_G_WEIGHTED_DRAW_PROVISIONAL_COUNT": sum(1 for p in new_prov.values() if p["provenance"] == RO.PROV_WEIGHTED),
               "CANDIDATE_UNIVERSE_DIGEST_OUT": self.universe_digest, "wall_s": time.time() - t0}
        self.history.append(rec)
        self._wj(f"round{r:03d}_end.json", rec)
        self.counters["GLOBAL_MULTIPLE_UPDATE_ROUND_COUNT"] = r + 1
        self.log(f"  round {r}: unresolved={len(unresolved)} proposals={len(proposals)} static_fail={len(static_fail)} "
                 f"survivors={len(survivors)} accepted={len(dr['accepted'])} new_ban_targets={n_new_targets} "
                 f"weighted_prov={rec['INNER_G_WEIGHTED_DRAW_PROVISIONAL_COUNT']} observer_unstable={unstable_total} wall={rec['wall_s']:.0f}s")
        if self.on_round_end is not None:
            self.on_round_end(self, rec)
        return rec

    # ------------------------------------------------------------------ closure / ladder
    VALID_INNER_STATES = ("RAW_INNER_CLOSED", "READOUT_STABLE_RAW_UNCLOSED", "RAW_UNCLOSED_UNSTABLE_WITH_UNIFORM_FAIL_CLOSED")

    def closure_report(self):
        """GO 9.1 closure, every condition reported explicitly (CD R-2); redraw condition strict (m6)."""
        if len(self.history) < 2:
            return {"closed": False, "reason": "fewer than two rounds"}
        a, b = self.history[-1], self.history[-2]
        cond = {"INNER_NUMERICAL_STATE_VALID": a.get("INNER_NUMERICAL_STATE") in self.VALID_INNER_STATES and a.get("OBSERVER_CERTIFICATE") is not None,
                "FULL_PLAN_DIGEST_STABLE": a["FULL_PLAN_DIGEST"] == b["FULL_PLAN_DIGEST"],
                "PROPOSAL_SET_DIGEST_STABLE": a["PROPOSAL_SET_DIGEST"] == b["PROPOSAL_SET_DIGEST"],
                "WRITEBACK_DIGEST_STABLE": a["WRITEBACK_DIGEST"] == b["WRITEBACK_DIGEST"],
                "NEW_BAN_TARGET_COUNT_ZERO": a["NEW_BAN_TARGET_COUNT"] == 0,
                "NEW_BAN_EVIDENCE_COUNT_ZERO": a["NEW_BAN_EVIDENCE_COUNT"] == 0,
                "BATCH_HARD_VIOLATION_COUNT_ZERO": a["BATCH_HARD_VIOLATION_COUNT"] == 0,
                "UNRESOLVED_REQUEST_COUNT_ZERO": a["UNRESOLVED_REQUEST_COUNT"] == 0,
                "SAME_RESOURCE_LOTTERY_UNIVERSE_REDRAW_COUNT_ZERO": a.get("SAME_RESOURCE_LOTTERY_UNIVERSE_REDRAW_COUNT") == 0}
        return {"closed": all(cond.values()), "conditions": cond, "round": a["round"]}

    def closed(self):
        return self.closure_report()["closed"]

    def cycle(self):
        """period-2/3/4 on the JOINT state digest (plan + bans + pins + terminal statuses)."""
        ds = [h["STATE_DIGEST"] for h in self.history]
        for p in (2, 3, 4):
            if len(ds) >= 2 * p and ds[-p:] == ds[-2 * p:-p] and len(set(ds[-p:])) > 1:
                return p
        return 0

    def run(self, budget_ok=lambda r: True):
        # review Y4c: a state restored AFTER the closure round (final commit pending) must not run another round
        if len(self.history) >= 2 and self.closed():
            return {"stop": "GLOBAL_CLOSURE", "rounds": len(self.history)}
        if len(self.history) >= 4 and self.cycle():
            return {"stop": f"PERIOD_{self.cycle()}_CYCLE", "rounds": len(self.history)}
        for r in range(len(self.history), self.hard_cap):          # resumes after the last completed round
            if not budget_ok(r):
                return {"stop": "RESOURCE_SAFE_ROUND_STOP", "rounds": r}
            self.round(r)
            if self.closed():
                return {"stop": "GLOBAL_CLOSURE", "rounds": r + 1}
            if self.cycle():
                return {"stop": f"PERIOD_{self.cycle()}_CYCLE", "rounds": r + 1}
        return {"stop": "HARD_CAP_EXHAUSTED", "rounds": self.hard_cap}

    # ------------------------------------------------------------------ checkpoint / resume (GO 9.3, review M5)
    def state(self):
        return _jsonable({"round_next": len(self.history),
                          "bans": [[list(k[0]), k[1], k[2], k[3], k[4], v] for k, v in sorted(self.bans.items(), key=lambda kv: json.dumps(kv[0], default=str))],
                          "provisional": {str(oid): p for oid, p in self.provisional.items()},
                          "provisional_pins": [[int(u), int(k), int(m)] for (u, k), m in sorted(self.provisional_pins.items())],
                          "resolved": {str(k): v for k, v in self.resolved.items()}, "history": self.history, "counters": self.counters,
                          "reg": self.reg.state(),
                          "lottery_seen": [[list(k), v] for k, v in self.lottery_seen.items()], "universe_digest": self.universe_digest,
                          "slot_table_digest": self.slot_table_digest, "slot_table": self.slot_table(),
                          "base_committed": self.base_committed, "base_journeys": self.base_journeys})

    def load_state(self, st):
        # X4 a-prime: the instance slot table is assigned once per run; a resumed controller must carry the identical table
        if st.get("slot_table_digest") != self.slot_table_digest or {k: [v[0], int(v[1])] for k, v in st.get("slot_table", {}).items()} != self.slot_table():
            raise RuntimeError("SLOT_TABLE_MISMATCH_ON_RESUME_HARD_STOP")
        self.bans = {(tuple(b[0]), b[1], b[2], b[3], b[4]): b[5] for b in st["bans"]}
        self.provisional = {int(k): v for k, v in st["provisional"].items()}
        self.provisional_pins = {(int(u), int(k)): int(m) for u, k, m in st["provisional_pins"]}
        self.resolved = {int(k): v for k, v in st["resolved"].items()}
        self.history = list(st["history"]); self.counters = dict(st["counters"])
        self.reg.load_state(st["reg"])
        self.lottery_seen = {tuple(k): v for k, v in st["lottery_seen"]}
        self.base_committed = list(st.get("base_committed", [])); self.base_journeys = list(st.get("base_journeys", []))
        self._compute_identities(); self._refresh_universe()
        if self.slot_table_digest != st.get("slot_table_digest"):        # re-check AFTER the recompute (review m6)
            raise RuntimeError("SLOT_TABLE_CHANGED_AFTER_RESUME_RECOMPUTE_HARD_STOP")
        if self.universe_digest != st["universe_digest"]:
            raise RuntimeError("RESUME_UNIVERSE_DIGEST_MISMATCH")
        return len(self.history)

    def final_commit(self):
        """GO 4.2 step 13 (CD R-5): ONLY after exact closure; fresh production ledger; any digest or replay
        mismatch raises (fail-closed); accepted outcomes come from the committed records.  The fresh dry run is
        cross-checked against the closure round's frozen DRY_RUN_DECISION_DIGEST and journey set (review M8)."""
        cr = self.closure_report()
        if not cr["closed"]:
            raise RuntimeError(f"FINAL_COMMIT_BEFORE_CLOSURE: {cr}")
        self.counters["PRODUCTION_COMMIT_COUNT_BEFORE_FINAL"] = len(self.base_committed)
        if self.base_committed:
            raise RuntimeError("PRODUCTION_COMMIT_BEFORE_FINAL")
        props = [{"oid": oid, "raw_u": p["owner"], "k_serv": p["k_serv"], "fingerprint": fingerprint(self.fx, self.fx["orders"][oid - 1]),
                  "dup_slot": self.dup_slot[oid], "owner_id": self.ident_slot[p["owner"]][0], "owner_slot": self.ident_slot[p["owner"]][1],
                  "journey_digest": p["journey_digest"]} for oid, p in self.provisional.items()]
        dr = BJ.dry_run(self.fx, self.auth, self.policy, self.base_committed, props, self.run_uuid, "final_dryrun", identity=self.identity)
        frozen = self.history[-1]
        if dr["DECISION_DIGEST"] != frozen["DRY_RUN_DECISION_DIGEST"]:
            raise RuntimeError(f"FROZEN_CLOSURE_DIGEST_MISMATCH final_dryrun={dr['DECISION_DIGEST'][:16]} closure_round={frozen['DRY_RUN_DECISION_DIGEST'][:16]}")
        prov_j = sorted(p["journey_digest"] for p in self.provisional.values())
        if sorted(j["digest"] for j in dr["journeys"]) != prov_j:
            raise RuntimeError("FROZEN_JOURNEY_SET_MISMATCH")
        fin = BJ.final_commit(self.fx, self.auth, self.policy, self.base_committed, props, self.run_uuid, identity=self.identity,
                              expected_decision_digest=dr["DECISION_DIGEST"])
        if fin["DECISION_DIGEST"] != dr["DECISION_DIGEST"]:
            raise RuntimeError("DRY_RUN_COMMIT_DECISION_DIGEST_MISMATCH")
        if fin["JOURNEY_DIGEST"] != dr["JOURNEY_DIGEST"]:
            raise RuntimeError("DRY_RUN_COMMIT_JOURNEY_DIGEST_MISMATCH")
        rep = BJ.independent_replay(self.fx, self.auth, fin, identity=self.identity, expected_plan={oid: (p["owner"], p["k_serv"]) for oid, p in self.provisional.items()})
        if not rep["PASS"]:
            raise RuntimeError(f"INDEPENDENT_REPLAY_FAIL: {rep}")
        committed = fin["committed_records"]
        if len(committed) != len(self.provisional) or len(fin["rejected"]) != 0:
            raise RuntimeError(f"COMMITTED_COUNT_MISMATCH committed={len(committed)} provisional={len(self.provisional)} rejected={len(fin['rejected'])}")
        if sorted(j["digest"] for j in fin["journeys"]) != prov_j:
            raise RuntimeError("COMMITTED_JOURNEY_SET_MISMATCH")
        hv = fin.get("BATCH_HARD_VIOLATION_COUNT")
        if hv is None or hv > 0:                                     # review z9: the committed batch's own hard validation is binding
            raise RuntimeError(f"COMMITTED_BATCH_HARD_VIOLATION count={hv}")
        for rcd in committed:
            self.resolved[int(rcd["oid"])] = "ACCEPTED"
        self.counters["PRODUCTION_COMMIT_COUNT"] = 1
        return {"DRY_RUN_FINAL_DECISION_DIGEST": dr["DECISION_DIGEST"], "COMMITTED_DECISION_DIGEST": fin["DECISION_DIGEST"],
                "CLOSURE_ROUND_DRY_RUN_DECISION_DIGEST": frozen["DRY_RUN_DECISION_DIGEST"],
                "DRY_RUN_FINAL_JOURNEY_DIGEST": dr["JOURNEY_DIGEST"], "COMMITTED_JOURNEY_DIGEST": fin["JOURNEY_DIGEST"], "match": True,
                "accepted": len(committed), "rejected": len(fin["rejected"]), "replay": rep, "committed_records": committed,
                "committed_journeys": fin["journeys"], "ledger_digest": fin["ledger_digest"], "ledger_event_multiset_digest": fin.get("ledger_event_multiset_digest"),
                "COMMITTED_BATCH_HARD_VIOLATION_COUNT": hv, "closure": cr}


def _count(it):
    out = {}
    for v in it:
        out[v] = out.get(v, 0) + 1
    return out


# ----------------------------------------------------------------------------- CPU self-test with a mock Inner
def _check(cond, msg):
    if not cond:
        raise RuntimeError("CONTROLLER_SELFTEST_FAIL: " + str(msg))


def make_mock_backend(fx, seed=0, closure_state="READOUT_STABLE_RAW_UNCLOSED", tail_drift=0.0):
    """Deterministic mock Inner: random positive field normalised on rows>=1, birth row from x0s, pins honoured,
    identical tails (stable observer) unless tail_drift>0 (then tail 20 is perturbed)."""
    rng = np.random.default_rng(seed)
    N, K, M = int(fx["N"]), K_STATE, int(fx["M"])

    def backend(inp):
        x = rng.uniform(0.9, 1.1, (N, K, M)); x[:, 1:, :] /= x[:, 1:, :].sum(2, keepdims=True)
        x[:, 0, :] = inp["x0s"]
        for (u, k), m in inp["pins"].items():
            x[u, k, :] = 0.0; x[u, k, m] = 1.0
        x20 = x.copy()
        if tail_drift > 0:
            x20[:, 1:, :] = x20[:, 1:, :] * rng.uniform(1 - tail_drift, 1 + tail_drift, (N, K - 1, M)); x20[:, 1:, :] /= x20[:, 1:, :].sum(2, keepdims=True)
        return {"x": x, "x_tail": [x, x, x20], "x_perm_tail": x20, "record": {"closure_state": closure_state, "x_sha256": hashlib.sha256(x.tobytes()).hexdigest()}}
    return backend


def _selftest():
    import os, sys, tempfile
    sys.path.insert(0, os.environ.get("E2_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fixture as FX
    fx = FX.build_fx(12)
    auth, policy = FX.load_battery(fx)
    N, K, M = int(fx["N"]), K_STATE, int(fx["M"])
    x_null = np.full((N, K, M), 1.0 / M)
    work = tempfile.mkdtemp()
    identity = {"policy_digest": policy.digest(), "authority_digest": auth.authority_digest}
    C = GlobalController(fx, auth, policy, backend=make_mock_backend(fx), run_uuid="uuid-test", run_seed=0, work=work, x_null=x_null,
                         identity=identity, hard_cap=6, log=lambda *a: print(*a))
    out = C.run()
    print("run:", out, "| counters INNER_SOLVE", C.counters["INNER_SOLVE_COUNT"], "rounds", C.counters["GLOBAL_MULTIPLE_UPDATE_ROUND_COUNT"])
    _check(C.counters["INNER_SOLVE_COUNT"] == C.counters["GLOBAL_MULTIPLE_UPDATE_ROUND_COUNT"], "one Inner solve per round")
    _check(out["stop"] == "GLOBAL_CLOSURE", f"mock must close: {out}")
    st = json.loads(json.dumps(C.state()))                                     # state must be pure JSON
    fc = C.final_commit()
    print("final commit match:", fc["match"], "accepted", fc["accepted"], "replay PASS", fc["replay"]["PASS"])
    _check(fc["match"] and fc["replay"]["PASS"] and fc["accepted"] == len(fc["committed_records"]), "final commit")
    _check(all(v == "ACCEPTED" for v in C.resolved.values()) and len(C.resolved) == 12, "all resolved ACCEPTED")
    # resume: a fresh controller loaded from the pre-commit state must reproduce the closure report and commit identically
    C2 = GlobalController(fx, auth, policy, backend=make_mock_backend(fx), run_uuid="uuid-test", run_seed=0, work=tempfile.mkdtemp(), x_null=x_null,
                          identity=identity, hard_cap=6, log=lambda *a: None)
    n = C2.load_state(st); _check(n == len(C.history) and C2.closed(), "resume must restore closure")
    fc2 = C2.final_commit(); _check(fc2["COMMITTED_DECISION_DIGEST"] == fc["COMMITTED_DECISION_DIGEST"], "resume commit digest")
    print("controller selftest OK; round files:", sorted(os.listdir(f"{work}/rounds"))[:4])
    return {"PASS": True, "stop": out, "accepted": fc["accepted"], "replay": fc["replay"]["PASS"], "resume_rounds": n,
            "observer_certificate_last": C.history[-1]["OBSERVER_CERTIFICATE"]}


if __name__ == "__main__":
    _selftest()
