"""Canonical committed journey layer — single source of truth for the battery-aware Scheduler (GO §5).

SH64_BAT3_COMMITTED_JOURNEY_V1. One Journey per committed action:
  DIRECT_ORDER        : tail -> Collection -> Dropoff
  RECHARGE_THEN_ORDER : tail -> Hub -> BATTERY_SWAP(2 slots) -> Collection -> Dropoff
Route rows (phase/station), pins, timeline, L/service rows, BatteryLedger events, validator, cost and the export
adapter are all pure functions of the Journey list. For plans without recharge actions the materialization is
BITWISE identical to the sealed kernel sh64_v3r3_route.canonical_replay_and_materialize (equivalence gate).
Phase ids 0..7 are the sealed ids; 8/9/10 are the hub-cycle phases.
"""
import hashlib, json
import numpy as np

PH_FREE, PH_WAIT_PRE_C, PH_INFLIGHT_TO_C, PH_C_SERVICE, PH_INFLIGHT_C_TO_D, PH_WAIT_D_WINDOW, PH_D_SERVICE, PH_ABSORB = range(8)
PH_INFLIGHT_TO_HUB, PH_WAIT_AT_HUB, PH_BATTERY_SWAP = 8, 9, 10
PHASE_NAMES = ["FREE_UNCOMMITTED", "WAIT_PRE_C", "INFLIGHT_TO_C", "C_SERVICE", "INFLIGHT_C_TO_D", "WAIT_D_WINDOW", "D_SERVICE",
               "TERMINAL_ABSORB_AT_LAST_D", "INFLIGHT_TO_HUB", "WAIT_AT_HUB", "BATTERY_SWAP"]
A_SERVICE_V3R4_EXT = np.array([0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], np.int8)     # V3R4 mask (FREE=0), hub phases 0
A_SERVICE_KERNEL_EXT = np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], np.int8)   # sealed kernel table (FREE=1) for equivalence
J_FLIGHT_EXT = np.array([0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0], np.int8)
E_ABSORB_EXT = np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], np.int8)
PHYS_EXT = np.array([0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1], np.int8)
DIRECT_ORDER, RECHARGE_THEN_ORDER = "DIRECT_ORDER", "RECHARGE_THEN_ORDER"
SCHEMA = "SH64_BAT3_COMMITTED_JOURNEY_V1"
SEG_TO_EVENT = {"WAIT_PRE_C": "WAIT", "INFLIGHT_TO_HUB": "REPOSITION_TO_HUB", "WAIT_AT_HUB": "WAIT_AT_HUB", "BATTERY_SWAP": "BATTERY_SWAP",
                "INFLIGHT_TO_C": "FLIGHT_EMPTY", "C_SERVICE": "COLLECTION_SERVICE", "INFLIGHT_C_TO_D": "FLIGHT_LOADED", "WAIT_D_WINDOW": "WAIT", "D_SERVICE": "DROPOFF_SERVICE"}
SEG_PHASE = {"WAIT_PRE_C": PH_WAIT_PRE_C, "INFLIGHT_TO_HUB": PH_INFLIGHT_TO_HUB, "WAIT_AT_HUB": PH_WAIT_AT_HUB, "BATTERY_SWAP": PH_BATTERY_SWAP,
             "INFLIGHT_TO_C": PH_INFLIGHT_TO_C, "C_SERVICE": PH_C_SERVICE, "INFLIGHT_C_TO_D": PH_INFLIGHT_C_TO_D, "WAIT_D_WINDOW": PH_WAIT_D_WINDOW, "D_SERVICE": PH_D_SERVICE}


class JourneyError(RuntimeError):
    pass


class RowConflict(RuntimeError):
    pass


def dig(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def tv(T, a, b):
    return 0 if a == b else int(T[a - 1, b - 1])


# ---------------------------------------------------------------- journey construction (pure)
def build_journey(fx, auth, uav, pre_state, order, k_serv, action_kind, hub=None, swap_start=None, identity=None, Dk=None):
    """Construct the committed Journey for one action from an explicit pre_state. Raises JourneyError on any hard violation
    (predecessor reachability, C/D timing contract, k_serv window, negative SoC, swap timing, missing certificate)."""
    if action_kind not in (DIRECT_ORDER, RECHARGE_THEN_ORDER):
        raise JourneyError("ACTION_KIND_UNKNOWN")
    if isinstance(uav, bool) or not isinstance(uav, (int, np.integer)) or not (0 <= int(uav) < int(fx["N"])):
        raise JourneyError("OWNER_OUT_OF_RANGE")
    T = fx["T_steps"]; Dk = fx["D_cost"] if Dk is None else Dk
    c, d, kp, kd, oid = int(order["c"]), int(order["d"]), int(order["k_p"]), int(order["k_d"]), int(order["order_id"])
    st, t, soc = int(pre_state["tail_location"]), int(pre_state["tail_slot"]), int(pre_state["soc"])
    if isinstance(soc, bool) or soc < 0 or soc > auth.B_max or int(pre_state.get("payload", 0)) != 0:
        raise JourneyError("PRE_STATE_INVALID")
    segs = []; seq = 0
    def seg(kind, o, de, tf, tt, dsoc, pb, pa, rows):
        nonlocal seq, soc
        s = {"seq": seq, "kind": kind, "phase": SEG_PHASE[kind], "origin": int(o), "destination": int(de), "t_from": int(tf), "t_to": int(tt),
             "rows": rows, "energy_delta": int(dsoc), "soc_before": int(soc), "soc_after": int(soc + dsoc), "payload_before": pb, "payload_after": pa}
        seq += 1; soc += dsoc; segs.append(s)
        if soc < 0:
            raise JourneyError(f"NEGATIVE_SOC_AFTER:{kind}")
        return s
    cost = {"base_service_cost": 0, "tail_to_C_cost": 0, "C_to_D_cost": tv(T, c, d), "return_to_Hub_cost": 0, "Hub_to_C_cost": 0, "wait_at_Hub_cost": 0,
            "swap_duration_cost": 0, "lateness_cost": 0}
    km = 0.0
    if action_kind == RECHARGE_THEN_ORDER:
        h = int(hub); s0 = int(swap_start)
        if h not in auth.hubs_1based:
            raise JourneyError("HUB_NOT_IN_AUTHORITY")
        t_th = tv(T, st, h); t_h = t + t_th
        if s0 < t_h or t_h > auth.K_service:
            raise JourneyError("SWAP_START_BEFORE_ARRIVAL_OR_HORIZON")
        if t_th > 0:
            seg("INFLIGHT_TO_HUB", st, h, t, t_h, -auth.E_per_slot * t_th, 0, 0, [t + 1, t_h]); km += float(Dk[st - 1, h - 1])
        if s0 > t_h:
            seg("WAIT_AT_HUB", h, h, t_h, s0, 0, 0, 0, [t_h + 1, s0]); cost["wait_at_Hub_cost"] = s0 - t_h
        seg("BATTERY_SWAP", h, h, s0, s0 + auth.swap_slots, auth.swap_soc - soc, 0, 0, [s0 + 1, s0 + auth.swap_slots])
        if soc != auth.swap_soc:
            raise JourneyError("SWAP_RESET_NOT_75")
        cost["return_to_Hub_cost"] = t_th; cost["swap_duration_cost"] = auth.swap_slots; cost["Hub_to_C_cost"] = tv(T, h, c)
        st, t = h, s0 + auth.swap_slots
    else:
        h = None; cost["tail_to_C_cost"] = tv(T, st, c)
    dt_pre, dt_cd = tv(T, st, c), tv(T, c, d); k_dep, k_arr = kp - dt_pre, kp + dt_cd
    if k_dep < t or (dt_pre == 0 and kp <= t):
        raise JourneyError("PREDECESSOR_UNREACHABLE")
    if k_arr != kd - 4:
        raise JourneyError("CD_TIMING_NOT_EXACT")
    if not (kd - 4 <= int(k_serv) <= kd):
        raise JourneyError("K_SERV_OUT_OF_WINDOW")
    if k_arr > int(k_serv):
        raise JourneyError("ARRIVAL_AFTER_K_SERV")
    last_wait_row = min(k_dep, kp - 1)
    if last_wait_row >= t + 1:
        seg("WAIT_PRE_C", st, st, t, k_dep, 0, 0, 0, [t + 1, last_wait_row])
    if dt_pre > 0:
        first_fl = max(k_dep + 1, t + 1)
        seg("INFLIGHT_TO_C", st, c, k_dep, kp, -auth.E_per_slot * dt_pre, 0, 0, [first_fl, kp - 1] if first_fl <= kp - 1 else [])
        km += float(Dk[st - 1, c - 1])
    seg("C_SERVICE", c, c, kp, kp, 0, 0, 1, [kp, kp])
    seg("INFLIGHT_C_TO_D", c, d, kp, k_arr, -auth.E_per_slot * dt_cd, 1, 1, [kp + 1, k_arr - 1] if kp + 1 <= k_arr - 1 else [])
    km += float(Dk[c - 1, d - 1])
    if int(k_serv) > k_arr:
        seg("WAIT_D_WINDOW", d, d, k_arr, int(k_serv), 0, 1, 1, [k_arr, int(k_serv) - 1])
    seg("D_SERVICE", d, d, int(k_serv), int(k_serv), 0, 1, 0, [int(k_serv), int(k_serv)])
    B_D = soc
    # post-D safe-Hub certificate (capability only; never materialised)
    best = None; any_h = False
    for hh in auth.hubs_1based:
        tt = tv(T, d, hh); arr = int(k_serv) + tt
        if arr > auth.K_service:
            continue
        any_h = True; bh = B_D - auth.E_per_slot * tt
        if bh >= 0:
            key = (arr, auth.E_per_slot * tt, hh)
            if best is None or key < best[0]:
                best = (key, {"hub": hh, "arrival_row": arr, "flight_energy": auth.E_per_slot * tt, "soc_at_hub": bh, "exact_zero": bh == 0})
    if best is None:
        raise JourneyError("HORIZON_EXCEEDED" if not any_h else "NO_SAFE_HUB_REACHABLE_AFTER_D")
    cost["total_augmented_action_cost"] = sum(v for k, v in cost.items() if k != "total_augmented_action_cost")
    cost["flight_slots"] = cost["tail_to_C_cost"] + cost["C_to_D_cost"] + cost["return_to_Hub_cost"] + cost["Hub_to_C_cost"]
    cost["flight_energy"] = auth.E_per_slot * cost["flight_slots"]; cost["flight_km"] = round(km, 3)
    j = {"schema": SCHEMA, "order_id": oid, "owner": int(uav), "k_serv": int(k_serv), "action_kind": action_kind, "hub": h,
         "swap_start": (int(swap_start) if h is not None else None), "swap_end": (int(swap_start) + auth.swap_slots if h is not None else None),
         "pre_state": {"tail_location": int(pre_state["tail_location"]), "tail_slot": int(pre_state["tail_slot"]), "soc": int(pre_state["soc"]), "payload": 0},
         "post_state": {"tail_location": d, "tail_slot": int(k_serv), "soc": int(B_D), "payload": 0},
         "segments": segs, "certificate": best[1], "cost": cost, "k_dep": k_dep, "k_arr": k_arr,
         "identity": identity or {}}
    j["digest"] = dig({k: v for k, v in j.items() if k != "digest"})
    return j


def journey_events(j, auth_digest, txn_id="NA", plan_digest="NA", idx0=0):
    """Ledger event rows (V2 schema) derived from the journey segments — the ONLY way ledger events are produced."""
    out = []
    kind = "DIRECT_SERVE" if j["action_kind"] == DIRECT_ORDER else "RETURN_SWAP_SERVE"
    for n, s in enumerate(j["segments"]):
        out.append({"transaction_id": txn_id, "uav_id": j["owner"], "order_id_or_NA": j["order_id"], "event_index": idx0 + n,
                    "slot_from": s["t_from"], "slot_to": s["t_to"], "phase": SEG_TO_EVENT[s["kind"]], "station_from": s["origin"], "station_to": s["destination"],
                    "soc_before": s["soc_before"], "delta_soc": s["energy_delta"], "soc_after": s["soc_after"], "payload_before": s["payload_before"], "payload_after": s["payload_after"],
                    "action_kind": kind, "hub_id_or_NA": j["hub"] if j["hub"] is not None else "NA",
                    "swap_service_slot_or_NA": (s["t_from"] if s["kind"] == "BATTERY_SWAP" else "NA"),
                    "source_plan_digest": plan_digest, "authority_digest": auth_digest, "rule_id": s["kind"], "journey_digest": j["digest"]})
    return out


# ---------------------------------------------------------------- materialization (single truth for rows/pins/L)
def materialize_journeys(fx, journeys, K=241, kernel_mask=False):
    """phase/station/pins/L/masks/route_ledger from a Journey list. Rows are written exactly like the sealed kernel
    (single write per (owner,row), absorb after the owner's last action). kernel_mask=True uses the sealed a_service
    table (FREE=1) for the bitwise equivalence gate; production uses A_SERVICE_V3R4_EXT (FREE=0)."""
    N, M = int(fx["N"]), int(fx["M"]); births = fx["births"]; orders = fx["orders"]
    phase = np.zeros((N, K), np.int8); station = np.full((N, K), -1, np.int64); L = np.zeros((K, M), np.int64)
    by = {}
    for j in journeys:
        by.setdefault(int(j["owner"]), []).append(j)
    route_ledger = []; viol = []
    def write(i, k, ph, st):
        if phase[i, k] != PH_FREE or station[i, k] != -1:
            raise RowConflict(f"ROUTE_ROW_CONFLICT uav{i} k{k}: {PHASE_NAMES[phase[i, k]]}@{station[i, k]} vs {PHASE_NAMES[ph]}@{st}")
        phase[i, k] = ph; station[i, k] = st
    for i in sorted(by):
        js = sorted(by[i], key=lambda j: (int(orders[j["order_id"] - 1]["k_p"]), j["order_id"]))
        st, t, soc = int(births[i]), 0, None
        for pos, j in enumerate(js):
            ps = j["pre_state"]
            if (ps["tail_location"], ps["tail_slot"]) != (st, t):
                viol.append({"oid": j["order_id"], "code": "CHAIN_PRE_STATE_MISMATCH", "expected": [st, t], "got": [ps["tail_location"], ps["tail_slot"]]})
            if soc is not None and ps["soc"] != soc:
                viol.append({"oid": j["order_id"], "code": "CHAIN_SOC_MISMATCH", "expected": soc, "got": ps["soc"]})
            for s in j["segments"]:
                if s["rows"]:
                    a, b = s["rows"]
                    for k in range(a, b + 1):
                        write(i, k, s["phase"], s["destination"])
            od = orders[j["order_id"] - 1]
            L[int(od["k_p"]), int(od["c"]) - 1] += 1; L[j["k_serv"], int(od["d"]) - 1] += 1
            row = {"oid": j["order_id"], "owner": i, "pos": pos, "predecessor": js[pos - 1]["order_id"] if pos > 0 else None,
                   "successor": js[pos + 1]["order_id"] if pos + 1 < len(js) else None, "c": int(od["c"]), "d": int(od["d"]), "k_p": int(od["k_p"]),
                   "k_serv": j["k_serv"], "k_dep": j["k_dep"], "k_arr": j["k_arr"], "tail_before": [st, t]}
            if j["action_kind"] == RECHARGE_THEN_ORDER:
                row.update({"action_kind": j["action_kind"], "hub": j["hub"], "swap_start": j["swap_start"], "swap_end": j["swap_end"], "journey_digest": j["digest"]})
            route_ledger.append(row)
            st, t, soc = j["post_state"]["tail_location"], j["post_state"]["tail_slot"], j["post_state"]["soc"]
        for k in range(t + 1, K):
            write(i, k, PH_ABSORB, st)
    pins = {(i, k): int(station[i, k]) - 1 for i in range(N) for k in range(1, K) if station[i, k] > 0}
    a_service = (A_SERVICE_KERNEL_EXT if kernel_mask else A_SERVICE_V3R4_EXT)[phase]
    j_flight = J_FLIGHT_EXT[phase]; e_absorb = E_ABSORB_EXT[phase]
    out = {"phase": phase, "station": station, "pins": pins, "L": L, "a_service": a_service, "j_flight": j_flight, "e_absorb": e_absorb,
           "route_ledger": route_ledger, "validation": {"hard_total": len(viol), "unknown_total": 0, "violations": viol},
           "physical_rows": int(PHYS_EXT[phase].sum()), "hub_cycle_rows": int(((phase == PH_INFLIGHT_TO_HUB) | (phase == PH_WAIT_AT_HUB) | (phase == PH_BATTERY_SWAP)).sum())}
    out["digests"] = {"phase_sha": sha_arr(phase), "station_sha": sha_arr(station), "pins_digest": dig(sorted(f"{k}:{v}" for k, v in pins.items())),
                      "a_service_sha": sha_arr(a_service), "j_flight_sha": sha_arr(j_flight), "e_absorb_sha": sha_arr(e_absorb), "L_sha": sha_arr(L),
                      "route_digest": dig(route_ledger), "journeys_digest": dig(sorted(j["digest"] for j in journeys))}
    return out


def journeys_from_plan(fx, auth, plan, identity=None):
    """DIRECT-only journeys for a canonical (no-battery) plan {oid:(owner,k_serv)} — used by the equivalence gate.
    pre_state is chained from births with SoC replayed by the same rules (may be negative-free or not; equivalence
    only concerns rows, so SoC is tracked but not enforced here: we build with auth.B_max as a large budget)."""
    by = {}
    for oid, (w, ks) in plan.items():
        by.setdefault(int(w), []).append((int(oid), int(ks)))
    out = []
    for i in sorted(by):
        st, t, soc = int(fx["births"][i]), 0, 10 ** 9
        for oid, ks in sorted(by[i], key=lambda x: (int(fx["orders"][x[0] - 1]["k_p"]), x[0])):
            od = fx["orders"][oid - 1]
            j = build_journey_rows_only(fx, auth, i, {"tail_location": st, "tail_slot": t, "soc": soc, "payload": 0}, od, ks, identity)
            out.append(j); st, t, soc = j["post_state"]["tail_location"], j["post_state"]["tail_slot"], j["post_state"]["soc"]
    return out


def build_journey_rows_only(fx, auth, uav, pre_state, order, k_serv, identity=None):
    """Row-equivalence helper: builds a DIRECT journey ignoring the SoC/certificate constraints (used only to prove
    row-level equivalence with the sealed kernel on canonical plans that were never battery-filtered)."""
    class _A:
        pass
    a = _A(); a.B_max = 10 ** 9; a.E_per_slot = auth.E_per_slot; a.hubs_1based = auth.hubs_1based; a.K_service = 10 ** 9; a.swap_slots = auth.swap_slots; a.swap_soc = auth.swap_soc
    return build_journey(fx, a, uav, dict(pre_state), order, k_serv, DIRECT_ORDER, identity=identity)


REQUIRED_KEYS = ("schema", "order_id", "owner", "k_serv", "action_kind", "hub", "swap_start", "pre_state", "post_state", "segments", "certificate", "cost", "identity", "digest")


def journey_validate(fx, auth, journeys, committed=None, identity=None, rebuild=True):
    """Hard checks on a journey set. Two layers:
    (1) self-consistent canonicality — chain continuity incl. SoC from birth, digest, segment SoC/continuity, flight time/energy,
        swap shape, hidden reset, horizon, post-state, certificate, single-write rows (materialize), and the canonical rebuild:
        the journey must be BITWISE the pure function of its own decision fields (closes re-signed content tampers);
    (2) anchoring to the COMMITTED decision — `committed` = {oid: {"owner","k_serv","action_kind","hub","swap_start"}} taken from
        the ledger/plan (never from the journeys): every journey must equal its committed decision (DECISION_NE_COMMITTED) and the
        journey set must be exactly the committed set (COMMITTED_SET_MISMATCH); `identity` = the expected full identity dict
        (IDENTITY_MISMATCH). Without anchors layer (2) is skipped — the caller must then anchor by other means.
    Malformed input never raises: JOURNEY_MALFORMED. Returns {hard_total, violations}."""
    viol = []
    by = {}; seen_oid = {}
    nO = len(fx["orders"]); N = int(fx["N"])
    for j in journeys:
        if not isinstance(j, dict) or any(k not in j for k in REQUIRED_KEYS) or not isinstance(j["segments"], list) or not isinstance(j["pre_state"], dict) or not isinstance(j["post_state"], dict):
            viol.append({"oid": j.get("order_id") if isinstance(j, dict) else None, "code": "JOURNEY_MALFORMED"}); continue
        oid = j["order_id"]; own = j["owner"]
        if not isinstance(oid, int) or isinstance(oid, bool) or not (1 <= oid <= nO):
            viol.append({"oid": oid, "code": "ORDER_ID_OUT_OF_RANGE"}); continue
        if not isinstance(own, int) or isinstance(own, bool) or not (0 <= own < N):
            viol.append({"oid": oid, "code": "OWNER_OUT_OF_RANGE", "owner": own}); continue
        if oid in seen_oid:
            viol.append({"oid": oid, "code": "DUPLICATE_ORDER_ID", "owners": [seen_oid[oid], own]}); continue
        seen_oid[oid] = own
        by.setdefault(own, []).append(j)
    if committed is not None:
        if set(seen_oid) != set(int(o) for o in committed):
            viol.append({"code": "COMMITTED_SET_MISMATCH", "missing": sorted(set(int(o) for o in committed) - set(seen_oid))[:10], "extra": sorted(set(seen_oid) - set(int(o) for o in committed))[:10]})
    T = fx["T_steps"]
    for i, js in by.items():
        js = sorted(js, key=lambda j: (int(fx["orders"][j["order_id"] - 1]["k_p"]), j["order_id"]))
        prev = {"tail_location": int(fx["births"][i]), "tail_slot": 0, "soc": auth.B_init, "payload": 0}
        for j in js:
          try:
            if j["pre_state"] != prev:
                viol.append({"oid": j["order_id"], "code": "PRE_STATE_NE_PREV_POST", "prev": prev, "pre": j["pre_state"]})
            if j.get("schema") != SCHEMA or dig({k: v for k, v in j.items() if k != "digest"}) != j["digest"]:
                viol.append({"oid": j["order_id"], "code": "JOURNEY_DIGEST_MISMATCH"})
            if not isinstance(j.get("identity"), dict) or j["identity"].get("authority_digest") != auth.authority_digest:
                viol.append({"oid": j["order_id"], "code": "IDENTITY_AUTHORITY_MISMATCH"})
            if identity is not None and j.get("identity") != identity:
                viol.append({"oid": j["order_id"], "code": "IDENTITY_MISMATCH"})
            if committed is not None:
                cm = committed.get(j["order_id"], committed.get(str(j["order_id"])))
                if cm is not None and (int(cm["owner"]), int(cm["k_serv"]), cm["action_kind"], cm.get("hub"), cm.get("swap_start")) != (j["owner"], j["k_serv"], j["action_kind"], j.get("hub"), j.get("swap_start")):
                    viol.append({"oid": j["order_id"], "code": "DECISION_NE_COMMITTED", "committed": cm, "journey": [j["owner"], j["k_serv"], j["action_kind"], j.get("hub"), j.get("swap_start")]})
            # canonical rebuild: the journey must be BITWISE the pure function of its decision fields
            # (owner, pre_state, order, k_serv, action_kind, hub, swap_start, identity) — closes every re-signed content tamper
            if rebuild:
                try:
                    jc = build_journey(fx, auth, i, dict(j["pre_state"]), fx["orders"][j["order_id"] - 1], int(j["k_serv"]), j["action_kind"], hub=j.get("hub"), swap_start=j.get("swap_start"), identity=j.get("identity"))
                    if jc["digest"] != j.get("digest"):
                        viol.append({"oid": j["order_id"], "code": "CANONICAL_REBUILD_MISMATCH", "keys": [k for k in jc if jc[k] != j.get(k)][:6]})
                except Exception as e:
                    viol.append({"oid": j["order_id"], "code": "CANONICAL_REBUILD_FAILED", "detail": str(e)[:120]})
            soc = j["pre_state"]["soc"]; pay = 0; t = j["pre_state"]["tail_slot"]; st = j["pre_state"]["tail_location"]
            for s in j["segments"]:
                if s["soc_before"] != soc or s["soc_after"] != soc + s["energy_delta"] or s["soc_after"] < 0:
                    viol.append({"oid": j["order_id"], "code": "SEGMENT_SOC", "seg": s["seq"]})
                if s["t_from"] != t or s["origin"] != st or s["payload_before"] != pay:
                    viol.append({"oid": j["order_id"], "code": "SEGMENT_CONTINUITY", "seg": s["seq"]})
                if s["kind"] in ("INFLIGHT_TO_HUB", "INFLIGHT_TO_C", "INFLIGHT_C_TO_D"):
                    if s["t_to"] - s["t_from"] != tv(T, s["origin"], s["destination"]) or s["energy_delta"] != -auth.E_per_slot * tv(T, s["origin"], s["destination"]):
                        viol.append({"oid": j["order_id"], "code": "FLIGHT_TIME_OR_ENERGY", "seg": s["seq"]})
                elif s["kind"] == "BATTERY_SWAP":
                    if s["t_to"] - s["t_from"] != auth.swap_slots or s["soc_after"] != auth.swap_soc or s["origin"] not in auth.hubs_1based or s["rows"] != [s["t_from"] + 1, s["t_to"]]:
                        viol.append({"oid": j["order_id"], "code": "SWAP_SHAPE", "seg": s["seq"]})
                elif s["energy_delta"] != 0:
                    viol.append({"oid": j["order_id"], "code": "NONFLIGHT_ENERGY", "seg": s["seq"]})
                if s["energy_delta"] > 0 and s["kind"] != "BATTERY_SWAP":
                    viol.append({"oid": j["order_id"], "code": "HIDDEN_RESET", "seg": s["seq"]})
                if s["t_to"] > auth.K_service:
                    viol.append({"oid": j["order_id"], "code": "HORIZON_EXCEEDED", "seg": s["seq"]})
                soc, pay, t, st = s["soc_after"], s["payload_after"], s["t_to"], s["destination"]
            if (st, t, soc, pay) != (j["post_state"]["tail_location"], j["post_state"]["tail_slot"], j["post_state"]["soc"], 0):
                viol.append({"oid": j["order_id"], "code": "POST_STATE_MISMATCH"})
            c = j["certificate"]
            if c["hub"] not in auth.hubs_1based or c["soc_at_hub"] != j["post_state"]["soc"] - auth.E_per_slot * tv(T, j["post_state"]["tail_location"], c["hub"]) or c["soc_at_hub"] < 0 or c["arrival_row"] > auth.K_service:
                viol.append({"oid": j["order_id"], "code": "CERTIFICATE_INVALID"})
            if j["action_kind"] == RECHARGE_THEN_ORDER:
                kinds = [s["kind"] for s in j["segments"]]
                if "BATTERY_SWAP" not in kinds or kinds.index("BATTERY_SWAP") > kinds.index("C_SERVICE"):
                    viol.append({"oid": j["order_id"], "code": "RECHARGE_WITHOUT_SWAP_BEFORE_C"})
            elif any(s["kind"] in ("INFLIGHT_TO_HUB", "WAIT_AT_HUB", "BATTERY_SWAP") for s in j["segments"]):
                viol.append({"oid": j["order_id"], "code": "DIRECT_WITH_HUB_SEGMENTS"})
            prev = dict(j["post_state"])
          except Exception as e:
            viol.append({"oid": j.get("order_id"), "code": "JOURNEY_MALFORMED", "detail": f"{type(e).__name__}:{str(e)[:100]}"}); prev = None
    try:
        m = materialize_journeys(fx, journeys)
        viol.extend(m["validation"]["violations"])
    except RowConflict as e:
        viol.append({"code": "ROUTE_ROW_CONFLICT", "detail": str(e)[:200]})
    except Exception as e:                       # any escape (index/type/value) is a hard violation, never a pass
        viol.append({"code": "MATERIALIZE_ERROR", "detail": f"{type(e).__name__}:{str(e)[:160]}"})
    return {"hard_total": len(viol), "unknown_total": 0, "violations": viol[:50]}


def rows_from_events(fx, events, K=241):
    """Second, EVENT-driven implementation of the row layout (independent of segments['rows']): expands BatteryLedger events
    into per-row phase/station. WAIT(payload 0): rows (from,to] then a service at row `to` overrides; FLIGHT_EMPTY/LOADED: rows
    (from,to) at the destination; REPOSITION_TO_HUB / WAIT_AT_HUB / BATTERY_SWAP: rows (from,to] at the hub; WAIT(payload 1):
    rows [from,to) at the dropoff; services: the single row; after the last event: absorb at the last station. Used as a
    bitwise cross-check against materialize_journeys (route <-> ledger equivalence at row level)."""
    N = int(fx["N"]); phase = np.zeros((N, K), np.int8); station = np.full((N, K), -1, np.int64)
    by = {}
    for e in events:
        by.setdefault(int(e["uav_id"]), []).append(e)
    for i, es in by.items():
        es = sorted(es, key=lambda e: int(e["event_index"])); last_to, last_st = None, None
        for e in es:
            a, b, ph = int(e["slot_from"]), int(e["slot_to"]), e["phase"]; sf, stt = int(e["station_from"]), int(e["station_to"])
            if ph == "WAIT" and int(e["payload_before"]) == 0:
                rows, p_, st_ = range(a + 1, b + 1), PH_WAIT_PRE_C, sf
            elif ph == "WAIT":
                rows, p_, st_ = range(a, b), PH_WAIT_D_WINDOW, sf
            elif ph == "FLIGHT_EMPTY":
                rows, p_, st_ = range(a + 1, b), PH_INFLIGHT_TO_C, stt
            elif ph == "FLIGHT_LOADED":
                rows, p_, st_ = range(a + 1, b), PH_INFLIGHT_C_TO_D, stt
            elif ph == "REPOSITION_TO_HUB":
                rows, p_, st_ = range(a + 1, b + 1), PH_INFLIGHT_TO_HUB, stt
            elif ph == "WAIT_AT_HUB":
                rows, p_, st_ = range(a + 1, b + 1), PH_WAIT_AT_HUB, sf
            elif ph == "BATTERY_SWAP":
                rows, p_, st_ = range(a + 1, b + 1), PH_BATTERY_SWAP, sf
            elif ph == "COLLECTION_SERVICE":
                rows, p_, st_ = range(a, a + 1), PH_C_SERVICE, sf
            elif ph == "DROPOFF_SERVICE":
                rows, p_, st_ = range(a, a + 1), PH_D_SERVICE, sf
            else:
                raise ValueError("UNKNOWN_EVENT_PHASE:" + str(ph))
            for k in rows:
                if not (1 <= k < K):
                    raise ValueError(f"EVENT_ROW_OUT_OF_RANGE uav{i} k{k}")
                phase[i, k] = p_; station[i, k] = st_
            last_to, last_st = b, stt
        if last_to is not None:
            for k in range(last_to + 1, K):
                phase[i, k] = PH_ABSORB; station[i, k] = last_st
    return phase, station


def journey_export(journeys):
    """Export/animation adapter: per-owner ordered segments incl. hub cycle (no animation engineering here)."""
    out = {}
    for j in sorted(journeys, key=lambda j: (j["owner"], j["pre_state"]["tail_slot"], j["order_id"])):
        out.setdefault(str(j["owner"]), []).append({"order_id": j["order_id"], "action_kind": j["action_kind"], "hub": j["hub"], "swap_start": j["swap_start"],
                                                   "segments": [{"kind": s["kind"], "from": s["origin"], "to": s["destination"], "t_from": s["t_from"], "t_to": s["t_to"], "soc_after": s["soc_after"]} for s in j["segments"]],
                                                   "certificate": j["certificate"]})
    return out
