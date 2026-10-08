"""SH64 V3R4 Outer BatteryLedger V2 — reserve=0 + explicit return-to-Hub / 2-slot swap cycle.

GO: CW3_SH64_CNN3_V3R4_OUTER_BATTERYLEDGER_V2_EXPLICIT_HUB_CYCLE_Q10K_V1 · parent V1 HEAD acf776b
NEW module (sibling of sh64_bat_ledger.py, which stays untouched for the V1 compat arm).
Proxy: SH64_BATTERY_PROXY_75_4_0_SWAP2_V2 — integer SoC, flight 4*T_steps, WAIT/service/parking 0,
post-D extra reserve 0, Hub arrival boundary B >= 0 (0 PASS, -1 REJECT), BATTERY_SWAP 2 slots -> 75,
reset ONLY at BATTERY_SWAP_END, no charging before physical Hub arrival, parking unlimited.

Actions (GO §6): DIRECT_SERVE  = tail -> [WAIT] -> FLIGHT_EMPTY -> C_SERVICE -> FLIGHT_LOADED -> [WAIT] -> D_SERVICE -> cert
                 RETURN_SWAP_SERVE = tail -> REPOSITION_TO_HUB -> [WAIT_AT_HUB] -> BATTERY_SWAP(2) -> DIRECT chain from (hub, swap_end, 75)
Reactive-only: RETURN_SWAP_SERVE is generated only when DIRECT_SERVE is battery-infeasible for that owner.
The ledger is a hard feasibility filter + complete event/cost bookkeeper; never an owner optimizer; consumes no RNG.
"""
import copy, hashlib, json, os
from dataclasses import dataclass, asdict

def dig(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

MODEL_ID = "SH64_BATTERY_PROXY_75_4_0_SWAP2_V2"
STOP_AUTH = "SH64_BAT2_STOP_AUTHORITY_MISSING_OR_MISMATCH"
# reason codes (V1 set retained + V2 additions)
PASS_DIRECT = "BATTERY_PASS_DIRECT_SERVE"
PASS_RECHARGE = "BATTERY_PASS_RETURN_SWAP_SERVE"
INSUFFICIENT_TO_REACH_COLLECTION = "INSUFFICIENT_TO_REACH_COLLECTION"
INSUFFICIENT_TO_REACH_DROPOFF = "INSUFFICIENT_TO_REACH_DROPOFF"
NO_SAFE_HUB_REACHABLE_AFTER_D = "NO_SAFE_HUB_REACHABLE_AFTER_D"
HORIZON_EXCEEDED = "HORIZON_EXCEEDED"
PREDECESSOR_OR_SUFFIX_BROKEN = "PREDECESSOR_OR_SUFFIX_BROKEN"
PREORDER_NO_REACHABLE_HUB_FAIL_CLOSED = "PREORDER_NO_REACHABLE_HUB_FAIL_CLOSED"
POST_SWAP_ORDER_BATTERY_INFEASIBLE = "POST_SWAP_ORDER_BATTERY_INFEASIBLE"
SWAP_WINDOW_CONFLICT = "SWAP_WINDOW_CONFLICT"
SWAP_CAPACITY_WAIT = "SWAP_CAPACITY_WAIT"
K_SERV_OUT_OF_WINDOW = "K_SERV_OUT_OF_WINDOW"
VERSION_OR_DIGEST_CONFLICT = "VERSION_OR_DIGEST_CONFLICT"
TRANSACTION_REPLAY_OR_IDEMPOTENCY_FAIL = "TRANSACTION_REPLAY_OR_IDEMPOTENCY_FAIL"
NONINTEGER_OR_NONFINITE_SOC = "NONINTEGER_OR_NONFINITE_SOC"
AUTHORITY_MISSING_OR_MISMATCH = "AUTHORITY_MISSING_OR_MISMATCH"
RECHARGE_VARIANTS_DISABLED = "RECHARGE_VARIANTS_DISABLED"

EV_WAIT = "WAIT"; EV_FLIGHT_EMPTY = "FLIGHT_EMPTY"; EV_COLLECTION_SERVICE = "COLLECTION_SERVICE"
EV_FLIGHT_LOADED = "FLIGHT_LOADED"; EV_DROPOFF_SERVICE = "DROPOFF_SERVICE"
EV_REPOSITION_TO_HUB = "REPOSITION_TO_HUB"; EV_WAIT_AT_HUB = "WAIT_AT_HUB"; EV_BATTERY_SWAP = "BATTERY_SWAP"
DIRECT_SERVE = "DIRECT_SERVE"; RETURN_SWAP_SERVE = "RETURN_SWAP_SERVE"


class BatteryAuthorityError(RuntimeError):
    pass


class BatteryPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthV2:
    model_id: str
    B_max: int
    B_init: int
    E_per_slot: int
    reserve: int
    swap_slots: int
    swap_soc: int
    hubs_1based: tuple
    K_service: int
    authority_digest: str


REQUIRED = ("BATTERY_MODEL_AUTHORITY_V2.json", "HUB_SWAP_CAPACITY_AUTHORITY_V2.json", "COST_AUTHORITY_V2.json",
            "SOURCE_PROVENANCE_V2.json", "DESIGN_FREEZE_V2.json")


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_authority_v2(auth_dir, fx):
    sums = os.path.join(auth_dir, "SHA256SUMS")
    if not os.path.isfile(sums):
        raise BatteryAuthorityError(f"{STOP_AUTH}: SHA256SUMS missing")
    pinned = {}
    for ln in open(sums):
        ln = ln.strip()
        if ln:
            h, n = ln.split(None, 1)
            pinned[n.strip()] = h
    for n in REQUIRED:
        p = os.path.join(auth_dir, n)
        if not os.path.isfile(p) or n not in pinned or _sha_file(p) != pinned[n]:
            raise BatteryAuthorityError(f"{STOP_AUTH}: {n}")
    bat = json.load(open(os.path.join(auth_dir, "BATTERY_MODEL_AUTHORITY_V2.json")))
    if bat["model_id"] != MODEL_ID or int(bat["B_max"]) != 75 or int(bat["B_init"]) != 75 or int(bat["post_D_extra_reserve"]) != 0:
        raise BatteryAuthorityError(f"{STOP_AUTH}: model numerics")
    if int(bat["swap"]["duration_slots"]) != 2 or int(bat["swap"]["completion_soc"]) != 75 or bat["swap"]["reset_only_at"] != "BATTERY_SWAP_END":
        raise BatteryAuthorityError(f"{STOP_AUTH}: swap semantics")
    hubs = tuple(sorted(int(h) for h in bat["hubs_1based"]))
    if hubs != tuple(sorted(int(h) for h in fx["hubs"])):
        raise BatteryAuthorityError(f"{STOP_AUTH}: hub set vs role authority")
    return AuthV2(MODEL_ID, 75, 75, 4, 0, 2, 75, hubs, 240, dig({n: pinned[n] for n in REQUIRED}))


@dataclass(frozen=True)
class PolicyV2:
    version: str
    model_id: str
    battery_extension_enabled: bool
    recharge_variants_enabled: bool      # False -> V2_RESERVE0_DIRECT_ONLY arm
    swap_service_mode: str               # UNBOUNDED_SWAP_SERVICE_PROXY | CAP1_SWAP_SERVICE_DIAGNOSTIC
    authority_digest: str

    def validate(self):
        if self.version != "BATTERY_POLICY_V2" or self.model_id != MODEL_ID:
            raise BatteryPolicyError("BATTERY_POLICY_V2_BAD")
        if not isinstance(self.battery_extension_enabled, bool) or not isinstance(self.recharge_variants_enabled, bool):
            raise BatteryPolicyError("BATTERY_POLICY_V2_FLAGS")
        if self.swap_service_mode not in ("UNBOUNDED_SWAP_SERVICE_PROXY", "CAP1_SWAP_SERVICE_DIAGNOSTIC"):
            raise BatteryPolicyError("BATTERY_POLICY_V2_SWAP_MODE")
        if not (isinstance(self.authority_digest, str) and len(self.authority_digest) == 64):
            raise BatteryPolicyError("BATTERY_POLICY_V2_AUTH")
        return self

    def digest(self):
        return dig(asdict(self))


def _ck(v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0 or v > 75:
        raise ValueError(NONINTEGER_OR_NONFINITE_SOC)
    return v


def tv(T, a, b):
    return 0 if a == b else int(T[a - 1, b - 1])


class SwapCalendar:
    """Independent swap-service calendar swap_service_occupancy[hub, slot] (never parking/service/ordinary capacity)."""
    def __init__(self, mode, slots=2):
        self.mode = mode
        self.slots = slots
        self.occ = {}          # (hub, slot) -> count
        self.log = []          # (hub, start, end, uav, oid)

    def cap(self):
        return None if self.mode == "UNBOUNDED_SWAP_SERVICE_PROXY" else 1

    def first_free(self, hub, t_arr, K=240):
        """Earliest start s >= t_arr with all slots s..s+1 under capacity (UNBOUNDED: s = t_arr)."""
        c = self.cap()
        if c is None:
            return t_arr
        s = t_arr
        while s + self.slots <= K + 1:
            if all(self.occ.get((hub, k), 0) < c for k in range(s, s + self.slots)):
                return s
            s += 1
        return None

    def occupy(self, hub, s, uav, oid):
        for k in range(s, s + self.slots):
            self.occ[(hub, k)] = self.occ.get((hub, k), 0) + 1
        self.log.append((int(hub), int(s), int(s + self.slots), int(uav), oid))

    def snapshot(self):
        return (dict(self.occ), list(self.log))

    def restore(self, snap):
        self.occ, self.log = dict(snap[0]), list(snap[1])

    def digest(self):
        return dig(sorted(self.log))


# ---------------------------------------------------------------- pure chain evaluation
def _row(idx, txn, uav, oid, s_from, s_to, ph, st_from, st_to, before, d, pay_b, pay_a, kind, hub, swap_slot, plan_digest, auth, rule):
    return {"transaction_id": txn, "uav_id": int(uav), "order_id_or_NA": oid if oid is not None else "NA", "event_index": idx,
            "slot_from": int(s_from), "slot_to": int(s_to), "phase": ph, "station_from": int(st_from), "station_to": int(st_to),
            "soc_before": int(before), "delta_soc": int(d), "soc_after": int(before + d), "payload_before": pay_b, "payload_after": pay_a,
            "action_kind": kind, "hub_id_or_NA": hub if hub is not None else "NA", "swap_service_slot_or_NA": swap_slot if swap_slot is not None else "NA",
            "source_plan_digest": plan_digest, "authority_digest": auth.authority_digest, "rule_id": rule}


def direct_chain(T, auth, uav, tail_st, tail_t, soc0, order, k_serv, oid=None, kind=DIRECT_SERVE, hub=None,
                 plan_digest="NA", txn="NA", idx0=0):
    """DIRECT chain from (tail_st, tail_t, soc0). reserve=0: every leg must leave soc >= 0.
    Returns (events, B_D, fail) with fail=(reason, first_failing_index) or None."""
    if isinstance(soc0, bool):
        raise ValueError(NONINTEGER_OR_NONFINITE_SOC)
    soc = _ck(int(soc0))
    c, d, k_p = int(order["c"]), int(order["d"]), int(order["k_p"])
    dt_pre, dt_cd = tv(T, tail_st, c), tv(T, c, d)
    k_dep, k_arr = k_p - dt_pre, k_p + dt_cd
    ev = []
    if k_dep < tail_t or (dt_pre == 0 and k_p <= tail_t):
        return ev, None, (PREDECESSOR_OR_SUFFIX_BROKEN, -1)
    if int(k_serv) < k_arr or int(k_serv) > int(order["k_d"]):     # canonical W_D contract: k_d-4 == k_arr <= k_serv <= k_d
        return ev, None, (K_SERV_OUT_OF_WINDOW, -1)
    i = idx0
    if k_dep > tail_t:
        ev.append(_row(i, txn, uav, oid, tail_t, k_dep, EV_WAIT, tail_st, tail_st, soc, 0, 0, 0, kind, hub, None, plan_digest, auth, "WAIT_ZERO")); i += 1
    if dt_pre > 0:
        dlt = -auth.E_per_slot * dt_pre
        ev.append(_row(i, txn, uav, oid, k_dep, k_p, EV_FLIGHT_EMPTY, tail_st, c, soc, dlt, 0, 0, kind, hub, None, plan_digest, auth, "FLIGHT_4_PER_SLOT")); i += 1
        soc += dlt
        if soc < 0:
            return ev, None, (INSUFFICIENT_TO_REACH_COLLECTION, i - 1)
    ev.append(_row(i, txn, uav, oid, k_p, k_p, EV_COLLECTION_SERVICE, c, c, soc, 0, 0, 1, kind, hub, None, plan_digest, auth, "SERVICE_ZERO")); i += 1
    dlt = -auth.E_per_slot * dt_cd
    ev.append(_row(i, txn, uav, oid, k_p, k_arr, EV_FLIGHT_LOADED, c, d, soc, dlt, 1, 1, kind, hub, None, plan_digest, auth, "FLIGHT_4_PER_SLOT")); i += 1
    soc += dlt
    if soc < 0:
        return ev, None, (INSUFFICIENT_TO_REACH_DROPOFF, i - 1)
    if k_serv > k_arr:
        ev.append(_row(i, txn, uav, oid, k_arr, k_serv, EV_WAIT, d, d, soc, 0, 1, 1, kind, hub, None, plan_digest, auth, "WAIT_D_WINDOW_ZERO")); i += 1
    ev.append(_row(i, txn, uav, oid, k_serv, k_serv, EV_DROPOFF_SERVICE, d, d, soc, 0, 1, 0, kind, hub, None, plan_digest, auth, "SERVICE_ZERO")); i += 1
    return ev, soc, None


def certificate(T, auth, d, k_serv, B_D):
    """Post-D safe-Hub reachability (GO §5.1/§6.2): B_D - 4T[d,h] >= 0 and arrival <= 240.
    Witness: earliest arrival, lowest flight energy, smallest hub_id. Capability only — never moves/debits/resets."""
    best = None
    any_in_horizon = False
    for h in auth.hubs_1based:
        t = tv(T, d, h)
        arr = k_serv + t
        if arr > auth.K_service:
            continue
        any_in_horizon = True
        bh = B_D - auth.E_per_slot * t
        if bh >= 0:
            key = (arr, auth.E_per_slot * t, h)
            if best is None or key < best[0]:
                best = (key, {"hub": h, "arrival_row": arr, "flight_energy": auth.E_per_slot * t, "soc_at_hub": bh, "exact_zero": bh == 0})
    if best is not None:
        return best[1], None
    return None, (HORIZON_EXCEEDED if not any_in_horizon else NO_SAFE_HUB_REACHABLE_AFTER_D)


def cost_decomp(T, Dk, tail_st, order, hub=None, wait_at_hub=0, swap=0):
    c, d = int(order["c"]), int(order["d"])
    if hub is None:
        parts = {"base_service_cost": 0, "tail_to_C_cost": tv(T, tail_st, c), "C_to_D_cost": tv(T, c, d), "return_to_Hub_cost": 0,
                 "Hub_to_C_cost": 0, "wait_at_Hub_cost": 0, "swap_duration_cost": 0, "lateness_cost": 0}
    else:
        parts = {"base_service_cost": 0, "tail_to_C_cost": 0, "C_to_D_cost": tv(T, c, d), "return_to_Hub_cost": tv(T, tail_st, hub),
                 "Hub_to_C_cost": tv(T, hub, c), "wait_at_Hub_cost": int(wait_at_hub), "swap_duration_cost": int(swap), "lateness_cost": 0}
    parts["total_augmented_action_cost"] = sum(parts.values())
    parts["flight_slots"] = parts["tail_to_C_cost"] + parts["C_to_D_cost"] + parts["return_to_Hub_cost"] + parts["Hub_to_C_cost"]
    parts["flight_energy"] = 4 * parts["flight_slots"]
    km = (0.0 if hub is None else (0.0 if tail_st == hub else float(Dk[tail_st - 1, hub - 1])) + (0.0 if hub == c else float(Dk[hub - 1, c - 1]))) if hub is not None \
        else (0.0 if tail_st == c else float(Dk[tail_st - 1, c - 1]))
    parts["flight_km"] = round(km + float(Dk[c - 1, d - 1]), 3)
    return parts


def evaluate_direct(T, Dk, auth, uav, tail_st, tail_t, soc, order, k_serv):
    ev, b_d, fail = direct_chain(T, auth, uav, tail_st, tail_t, soc, order, k_serv, oid=int(order["order_id"]))
    if fail:
        return {"admissible": False, "action_kind": DIRECT_SERVE, "reason": fail[0], "first_failing_event": fail[1], "prefix_witness": ev[:fail[1] + 1]}
    cert, why = certificate(T, auth, int(order["d"]), int(k_serv), int(b_d))
    if cert is None:
        return {"admissible": False, "action_kind": DIRECT_SERVE, "reason": why, "B_D": int(b_d), "first_failing_event": len(ev) - 1, "prefix_witness": ev}
    return {"admissible": True, "action_kind": DIRECT_SERVE, "reason": PASS_DIRECT, "B_D": int(b_d), "certificate": cert, "events": ev,
            "hub": None, "swap_start": None, "cost": cost_decomp(T, Dk, tail_st, order)}


def evaluate_recharge(T, Dk, auth, cal, uav, tail_st, tail_t, soc, order, k_serv):
    """RETURN_SWAP_SERVE over the FULL-chain-feasible hub set (GO §5.2). Deterministic selection:
    (action end = k_serv for all -> ) lowest total_augmented_action_cost, lowest flight energy, smallest hub_id."""
    soc = _ck(int(soc))
    c, k_p = int(order["c"]), int(order["k_p"])
    reachable = []
    feasible = []
    diag = {}
    for h in auth.hubs_1based:
        t_th = tv(T, tail_st, h)
        t_h = tail_t + t_th
        soc_h = soc - auth.E_per_slot * t_th
        if soc_h < 0 or t_h > auth.K_service:
            diag[h] = "UNREACHABLE"
            continue
        reachable.append(h)
        s = cal.first_free(h, t_h, auth.K_service)
        if s is None:
            diag[h] = SWAP_CAPACITY_WAIT + ":NO_WINDOW"
            continue
        swap_end = s + auth.swap_slots
        t_hc = tv(T, h, c)
        k_dep = k_p - t_hc
        if k_dep < swap_end or (t_hc == 0 and k_p <= swap_end):
            diag[h] = SWAP_WINDOW_CONFLICT
            continue
        ev2, b_d, fail = direct_chain(T, auth, uav, h, swap_end, auth.swap_soc, order, k_serv, oid=int(order["order_id"]), kind=RETURN_SWAP_SERVE, hub=h)
        if fail:
            diag[h] = fail[0]
            continue
        cert, why = certificate(T, auth, int(order["d"]), int(k_serv), int(b_d))
        if cert is None:
            diag[h] = why
            continue
        cost = cost_decomp(T, Dk, tail_st, order, hub=h, wait_at_hub=s - t_h, swap=auth.swap_slots)
        feasible.append(((k_serv, cost["total_augmented_action_cost"], cost["flight_energy"], h), h, t_h, soc_h, s, swap_end, ev2, b_d, cert, cost))
        diag[h] = "FULL_CHAIN_FEASIBLE"
    if not reachable:
        return {"admissible": False, "action_kind": RETURN_SWAP_SERVE, "reason": PREORDER_NO_REACHABLE_HUB_FAIL_CLOSED, "hub_diag": diag}
    if not feasible:
        vals = [diag[h] for h in reachable]
        if any(v == SWAP_WINDOW_CONFLICT for v in vals):
            r = SWAP_WINDOW_CONFLICT
        elif vals and all(str(v).startswith(SWAP_CAPACITY_WAIT) for v in vals):
            r = SWAP_CAPACITY_WAIT
        else:
            r = POST_SWAP_ORDER_BATTERY_INFEASIBLE
        return {"admissible": False, "action_kind": RETURN_SWAP_SERVE, "reason": r, "hub_diag": diag}
    feasible.sort(key=lambda x: x[0])
    _, h, t_h, soc_h, s, swap_end, ev2, b_d, cert, cost = feasible[0]
    pre = []
    i = 0
    oid = int(order["order_id"])
    if tv(T, tail_st, h) > 0:
        pre.append(_row(i, "NA", uav, oid, tail_t, t_h, EV_REPOSITION_TO_HUB, tail_st, h, soc, soc_h - soc, 0, 0, RETURN_SWAP_SERVE, h, None, "NA", auth, "REPOSITION_4_PER_SLOT")); i += 1
    if s > t_h:
        pre.append(_row(i, "NA", uav, oid, t_h, s, EV_WAIT_AT_HUB, h, h, soc_h, 0, 0, 0, RETURN_SWAP_SERVE, h, None, "NA", auth, "WAIT_AT_HUB_ZERO")); i += 1
    pre.append(_row(i, "NA", uav, oid, s, swap_end, EV_BATTERY_SWAP, h, h, soc_h, auth.swap_soc - soc_h, 0, 0, RETURN_SWAP_SERVE, h, s, "NA", auth, "SWAP_2_SLOTS_RESET_AT_END")); i += 1
    for e in ev2:
        e["event_index"] = i; i += 1
    return {"admissible": True, "action_kind": RETURN_SWAP_SERVE, "reason": PASS_RECHARGE, "B_D": int(b_d), "certificate": cert,
            "events": pre + ev2, "hub": h, "swap_start": s, "swap_end": swap_end, "wait_at_hub": s - t_h, "soc_at_hub_arrival": soc_h,
            "full_chain_feasible_recharge_hubs": [f[1] for f in feasible], "hub_diag": diag, "cost": cost}


def evaluate_action(T, Dk, auth, cal, policy, uav, tail_st, tail_t, soc, order, k_serv):
    """GO §6.4: direct feasible -> DIRECT only; else (variants enabled) recharge; else removed."""
    v = evaluate_direct(T, Dk, auth, uav, tail_st, tail_t, soc, order, k_serv)
    if v["admissible"]:
        return v
    if not policy.recharge_variants_enabled:
        v["recharge"] = RECHARGE_VARIANTS_DISABLED
        return v
    r = evaluate_recharge(T, Dk, auth, cal, uav, tail_st, tail_t, soc, order, k_serv)
    r["direct_reason"] = v["reason"]
    return r


# ---------------------------------------------------------------- prefix replay of committed actions
def prefix_state_v2(fx, auth, committed, swap_capacity=None):
    """committed: list of records {oid, owner, k_serv, action_kind, hub, swap_start} in commit order. Pure replay per owner in
    canonical (k_p, oid) order using the RECORDED hub/swap_start (calendar decisions are part of the committed record).
    Returns tails {i:(st,t)}, socs {i}, events, prefix_digest. Raises on any violation (fail-closed)."""
    T = fx["T_steps"]; Dk = fx["D_cost"]; orders = fx["orders"]
    by = {}
    for r in committed:
        by.setdefault(int(r["owner"]), []).append(r)
    tails, socs, events = {}, {}, []
    occ = {}
    for i in sorted(by):
        st, t, soc = int(fx["births"][i]), 0, auth.B_init
        for r in sorted(by[i], key=lambda r: (int(orders[int(r["oid"]) - 1]["k_p"]), int(r["oid"]))):
            od = orders[int(r["oid"]) - 1]; ks = int(r["k_serv"]); oid = int(r["oid"])
            if r["action_kind"] == DIRECT_SERVE:
                v = evaluate_direct(T, Dk, auth, i, st, t, soc, od, ks)
                if not v["admissible"]:
                    raise ValueError(f"{v['reason']}: committed DIRECT prefix illegal oid={oid} uav={i}")
                ev = v["events"]
            else:
                h, s = int(r["hub"]), int(r["swap_start"])
                t_th = tv(T, st, h); t_h = t + t_th; soc_h = soc - auth.E_per_slot * t_th
                if soc_h < 0 or t_h > auth.K_service or s < t_h:
                    raise ValueError(f"{PREORDER_NO_REACHABLE_HUB_FAIL_CLOSED}: committed RECHARGE prefix illegal oid={oid} uav={i}")
                if swap_capacity is not None and any(occ.get((h, k), 0) >= swap_capacity for k in range(s, s + auth.swap_slots)):
                    raise ValueError(f"SWAP_SERVICE_CAPACITY_VIOLATION: committed RECHARGE prefix oid={oid} uav={i} hub={h} start={s}")
                for k in range(s, s + auth.swap_slots):
                    occ[(h, k)] = occ.get((h, k), 0) + 1
                swap_end = s + auth.swap_slots
                ev2, b_d, fail = direct_chain(T, auth, i, h, swap_end, auth.swap_soc, od, ks, oid=oid, kind=RETURN_SWAP_SERVE, hub=h)
                if fail or certificate(T, auth, int(od["d"]), ks, int(b_d))[0] is None:
                    raise ValueError(f"{POST_SWAP_ORDER_BATTERY_INFEASIBLE}: committed RECHARGE prefix illegal oid={oid} uav={i}")
                pre = []
                if t_th > 0:
                    pre.append(_row(0, "NA", i, oid, t, t_h, EV_REPOSITION_TO_HUB, st, h, soc, soc_h - soc, 0, 0, RETURN_SWAP_SERVE, h, None, "NA", auth, "REPOSITION_4_PER_SLOT"))
                if s > t_h:
                    pre.append(_row(0, "NA", i, oid, t_h, s, EV_WAIT_AT_HUB, h, h, soc_h, 0, 0, 0, RETURN_SWAP_SERVE, h, None, "NA", auth, "WAIT_AT_HUB_ZERO"))
                pre.append(_row(0, "NA", i, oid, s, swap_end, EV_BATTERY_SWAP, h, h, soc_h, auth.swap_soc - soc_h, 0, 0, RETURN_SWAP_SERVE, h, s, "NA", auth, "SWAP_2_SLOTS_RESET_AT_END"))
                ev = pre + ev2
                v = {"B_D": b_d}
            events.extend(ev)
            st, t, soc = int(od["d"]), ks, int(v["B_D"])
        tails[i] = (st, t); socs[i] = soc
    key = [(e["uav_id"], e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["soc_before"], e["soc_after"]) for e in events]
    return tails, socs, events, dig(key)


# ---------------------------------------------------------------- transactional ledger
class BatteryLedgerV2:
    def __init__(self, fx, auth, policy, run_id="RUN"):
        policy.validate()
        if policy.authority_digest != auth.authority_digest:
            raise BatteryAuthorityError(f"{STOP_AUTH}: policy/authority digest")
        self.fx, self.auth, self.policy, self.run_id = fx, auth, policy, run_id
        self.T, self.Dk = fx["T_steps"], fx["D_cost"]
        self.cal = SwapCalendar(policy.swap_service_mode, auth.swap_slots)
        self.states = {i: {"uav_id": i, "tail_slot": 0, "tail_location": int(fx["births"][i]), "soc": auth.B_init, "payload": 0,
                           "order_state": "IDLE", "ledger_version": 0, "orders": []} for i in range(int(fx["N"]))}
        self.events = []
        self.committed = []            # action records (oid, owner, k_serv, action_kind, hub, swap_start)
        self.global_version = 0
        self.receipts = {}
        self.counters = {"repair": 0, "substitution": 0, "reorder": 0, "retry": 0, "commits": 0, "rejects": 0, "idempotent_replays": 0,
                         "rollbacks": 0, "cas_conflicts": 0, "direct_commits": 0, "recharge_commits": 0}

    def ledger_digest(self):
        return dig([(e["uav_id"], e["event_index"], e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"],
                     e["soc_before"], e["delta_soc"], e["soc_after"], e["payload_before"], e["payload_after"], e["action_kind"],
                     e["hub_id_or_NA"], e["swap_service_slot_or_NA"]) for e in self.events])

    def prefix_digest(self):
        return dig(sorted((s["uav_id"], s["tail_slot"], s["tail_location"], s["soc"], s["payload"], s["ledger_version"]) for s in self.states.values()))

    def evaluate(self, uav_i, order, k_serv):
        s = self.states[int(uav_i)]
        return evaluate_action(self.T, self.Dk, self.auth, self.cal, self.policy, int(uav_i), s["tail_location"], s["tail_slot"], s["soc"], order, int(k_serv))

    def prepare(self, uav_i, order, k_serv, proposal_digest):
        i = int(uav_i); s = self.states[i]; oid = int(order["order_id"])
        v = self.evaluate(i, order, k_serv)
        adg = dig([(e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["delta_soc"]) for e in v.get("events", [])]) if v["admissible"] else "NA"
        key = (self.run_id, oid, i, int(k_serv), v["action_kind"], v.get("hub"), v.get("swap_start"), adg, s["ledger_version"], self.global_version)
        return {"transaction_id": dig(key), "oid": oid, "uav_i": i, "k_serv": int(k_serv), "verdict": v, "action_digest": adg,
                "uav_state_version": s["ledger_version"], "global_resource_version": self.global_version, "proposal_digest": proposal_digest,
                "battery_authority_digest": self.auth.authority_digest, "committed_prefix_digest": self.prefix_digest(), "calendar_digest": self.cal.digest(),
                "idempotency_key": key}

    def validate_and_commit(self, txn):
        key = tuple(txn["idempotency_key"])
        if key in self.receipts:
            self.counters["idempotent_replays"] += 1
            return dict(self.receipts[key], idempotent_replay=True)
        i = txn["uav_i"]; s = self.states[i]
        if (txn["uav_state_version"] != s["ledger_version"] or txn["global_resource_version"] != self.global_version
                or txn["battery_authority_digest"] != self.auth.authority_digest or txn["committed_prefix_digest"] != self.prefix_digest()
                or txn["calendar_digest"] != self.cal.digest()):
            self.counters["rejects"] += 1; self.counters["cas_conflicts"] += 1
            return {"committed": False, "reason": VERSION_OR_DIGEST_CONFLICT, "transaction_id": txn["transaction_id"]}
        order = self.fx["orders"][txn["oid"] - 1]
        v = self.evaluate(i, order, txn["k_serv"])          # full fresh re-evaluation; txn['verdict'] is never trusted
        if not v["admissible"]:
            self.counters["rejects"] += 1
            return {"committed": False, "reason": v["reason"], "transaction_id": txn["transaction_id"]}
        pv = txn.get("verdict") or {}
        same = (pv.get("admissible") is True and pv.get("action_kind") == v["action_kind"] and int(pv.get("B_D", -1)) == int(v["B_D"])
                and pv.get("certificate") == v["certificate"] and pv.get("hub") == v.get("hub") and pv.get("swap_start") == v.get("swap_start")
                and txn.get("action_digest") == dig([(e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["delta_soc"]) for e in v["events"]]))
        if not same:
            self.counters["rejects"] += 1
            return {"committed": False, "reason": TRANSACTION_REPLAY_OR_IDEMPOTENCY_FAIL, "transaction_id": txn["transaction_id"]}
        # atomic apply with full rollback on any failure
        snap = (copy.deepcopy(s), len(self.events), self.global_version, self.cal.snapshot(), len(self.committed))
        try:
            base = sum(1 for e in self.events if e["uav_id"] == i)
            rows = copy.deepcopy(v["events"])
            for n, e in enumerate(rows):
                e["event_index"] = base + n; e["transaction_id"] = txn["transaction_id"]; e["source_plan_digest"] = txn["proposal_digest"]
            if v["action_kind"] == RETURN_SWAP_SERVE:
                self.cal.occupy(v["hub"], v["swap_start"], i, txn["oid"])
            self.events.extend(rows)
            s["tail_location"] = int(order["d"]); s["tail_slot"] = int(txn["k_serv"]); s["soc"] = int(v["B_D"]); s["payload"] = 0
            s["order_state"] = "WAITING_AT_D"; s["ledger_version"] += 1; s["orders"].append(txn["oid"])
            self.global_version += 1
            self.committed.append({"oid": txn["oid"], "owner": i, "k_serv": int(txn["k_serv"]), "action_kind": v["action_kind"], "hub": v.get("hub"), "swap_start": v.get("swap_start")})
            # post-commit invariant (GO §6.5): committed tail must remain hub-reachable
            if certificate(self.T, self.auth, s["tail_location"], s["tail_slot"], s["soc"])[0] is None:
                raise RuntimeError("POST_COMMIT_TAIL_NOT_HUB_REACHABLE")
        except Exception as ex:
            self.states[i] = snap[0]; del self.events[snap[1]:]; self.global_version = snap[2]; self.cal.restore(snap[3]); del self.committed[snap[4]:]
            self.counters["rollbacks"] += 1; self.counters["rejects"] += 1
            return {"committed": False, "reason": f"ROLLBACK:{ex}", "transaction_id": txn["transaction_id"]}
        self.counters["commits"] += 1
        self.counters["direct_commits" if v["action_kind"] == DIRECT_SERVE else "recharge_commits"] += 1
        rc = {"committed": True, "transaction_id": txn["transaction_id"], "oid": txn["oid"], "uav_i": i, "k_serv": txn["k_serv"], "action_kind": v["action_kind"],
              "hub": v.get("hub"), "swap_start": v.get("swap_start"), "soc_after": int(v["B_D"]), "certificate": v["certificate"], "cost": v["cost"],
              "ledger_digest": self.ledger_digest(), "idempotent_replay": False}
        self.receipts[key] = rc
        return dict(rc)
