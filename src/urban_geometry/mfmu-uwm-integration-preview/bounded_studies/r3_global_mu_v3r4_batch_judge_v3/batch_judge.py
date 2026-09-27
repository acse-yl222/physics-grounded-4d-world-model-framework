"""BatchJudge: claim materialisation from the immutable round-start snapshot, canonical commit
order, disposable-ledger hard dry-run and the final atomic production commit
(GO 4.2 steps 5, 8-9, 13; plan sections 2.5-2.8).

Frozen V3R4 machinery only (pure functions + ledger classes; no V3Outer instantiation):
  evaluate_action / SwapCalendar / prefix_state_v2  (experiments.sh64_bat2_ledger)
  BatteryLedgerV3 / replay_from_journeys            (experiments.sh64_bat3_ledger)
  build_journey / journey_validate / materialize_journeys (experiments.sh64_bat3_journey)
BATCH_JUDGE_HARD_ONLY=true: variant cost never changes owner ranking; the judge only accepts or
rejects frozen (order, owner, k_serv) proposals.

Review 2026-08-31: DECISION_DIGEST is a function of the canonical decision fields (decision class,
request fingerprint, dup_slot, owner identity/slot, k_serv) PLUS the committed journey digest.  The
canonical fields themselves never carry oid, raw UAV index or any proposal side-key, but the committed
journey digest is produced by the frozen journey builder (experiments.sh64_bat3_journey.build_journey),
whose canonical journey dict contains `order_id` and the raw `owner` index: DECISION_DIGEST is therefore
LABEL-BEARING through that one component (z10) and is an information item in the relabel tests, never a
PASS criterion (gates.q_scale_relabel_tests compares physical-identity multisets).  BATCH_HARD_VIOLATION_COUNT
is never hard-coded (computed by validate_accepted_batch on the final path, and on the dry-run path when
validate=True; otherwise the caller runs validate_accepted_batch); independent_replay fails closed on any
missing evidence.

X1 (verification pass 2, 2026-08-31) - claim row semantics and same-UAV chains
-------------------------------------------------------------------------------
`journey_rows(order, journey)` mirrors the frozen V3R4 `uav_tails` EXACTLY (experiments/sh64_v3_outer.py:126-128:
`rr.add(o["k_p"]); rr.update(range(arr, ks + 1))`, arr = k_p + T[c,d] = journey k_arr = k_d-4 by the CD timing
contract):  rows = {k_p} | [k_arr, k_serv].  The donor adds nothing else: WAIT_PRE_C / INFLIGHT_TO_C rows are not
occupied rows, and a RECHARGE_THEN_ORDER journey's hub cycle (INFLIGHT_TO_HUB / WAIT_AT_HUB / BATTERY_SWAP rows,
i.e. [swap_start, swap_end]) is NOT part of uav_tails either (V3R4 has no swap rows in its reservation set; battery
service is a separate non-binding proxy), so it is not added here.  Before this correction the claim rows were the
[start, end] endpoints of every segment (WAIT_PRE_C starts at row 1 for every base-state journey), which made every
same-UAV pair conflict and capped each UAV at one provisional per round.
Chain treatment in the dry run / final commit (`_commit_sequence`, UNCHANGED by X1, documented here): survivors are
committed in canonical order into ONE disposable ledger; the second (later) order of the same UAV is judged on the
committed prefix (post-state of the first journey), so its committed journey is the chain-true one.  If the ledger
accepts it, it is ACCEPTED_HARD_VALID with `committed_journey_digest` = chain-true digest and
FOOTPRINT_CHANGED_AFTER_LOTTERY=True whenever that digest differs from the snapshot-materialised claim digest
(pre_state differs => digest differs); it is NOT rejected for the digest change.  Only a chain-infeasible second
order (ledger refuses the prepare/commit) is rejected as R3_CHAIN_CONDITIONAL_BAN, and any later order of that UAV in
the same batch is BLOCKED_BY_FAILED_PREFIX.  Counters: FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT / POST_LOTTERY_CHAIN_BAN_COUNT /
BLOCKED_BY_FAILED_PREFIX_COUNT.

X3 - ledger digests
-------------------
`ledger_digest` (BatteryLedgerV3.ledger_digest) is ORDER-SENSITIVE (events in commit order) while
replay_from_journeys rebuilds events UAV-ascending; it is kept as provenance only.  `ledger_event_multiset_digest`
= dig(sorted(map(_event_tuple, events))) is order-insensitive and is the stored-evidence comparison used by
`committed_plan_replay_verdict` (fresh-clone replay from JSON).
"""
import copy
import hashlib
import json

from experiments import sh64_bat2_ledger as L2
from experiments import sh64_bat3_journey as J
from experiments import sh64_bat3_ledger as L3

FAIL_STATIC = "STATIC_TUPLE_FAILURE"
FAIL_CHAIN = "R3_CHAIN_CONDITIONAL_BAN"
FAIL_RESOURCE = "RESOURCE_LOTTERY_CONDITIONAL_BAN"
FAIL_BLOCKED = "BLOCKED_BY_FAILED_PREFIX"
FAIL_BATCH_HARD = "BATCH_HARD_VIOLATION"
ACCEPT = "ACCEPTED_HARD_VALID"
CANONICAL_FIELDS = ("fingerprint", "dup_slot", "owner_id", "owner_slot", "k_serv")
DECISION_DIGEST_SCHEMA = ("sha256 over the canonical-commit-order list of (class, fingerprint, dup_slot, owner_id, owner_slot, k_serv, "
                          "committed_journey_digest). The five canonical fields exclude oid/raw_u/side-keys; committed_journey_digest is the frozen "
                          "journey builder's digest (sh64_bat3_journey.build_journey) whose canonical dict CONTAINS order_id and the raw owner index, "
                          "so DECISION_DIGEST is label-bearing through that component and is an information item, never a relabel-invariance PASS criterion")
ROW_SEMANTICS = "V3R4_UAV_TAILS: rows = {k_p} | [k_arr, k_serv] (sh64_v3_outer.py:126-128); no WAIT_PRE_C/INFLIGHT_TO_C rows; no hub-cycle/swap rows"


def dig(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def canonical_commit_order(p):
    """(k_serv physical time, request fingerprint, dup_slot, owner identity+slot) — never oid."""
    return (int(p["k_serv"]), tuple(p["fingerprint"]), int(p["dup_slot"]), str(p["owner_id"]), int(p["owner_slot"]))


def base_state_of(ledger, u):
    s = ledger.states[int(u)]
    return {"tail_location": s["tail_location"], "tail_slot": s["tail_slot"], "soc": s["soc"], "payload": 0}


def journey_rows(order, journey):
    """Occupied rows of one journey under the frozen V3R4 `uav_tails` semantics, mirrored EXACTLY from
    experiments/sh64_v3_outer.py:126-128 (`rr.add(o["k_p"]); rr.update(range(arr, ks + 1))`):
        rows = {k_p} | [k_arr, k_serv],  k_arr = k_p + T[c,d] (the journey's `k_arr`; == k_d-4 by the CD timing contract).
    The donor adds nothing else - neither the WAIT_PRE_C / INFLIGHT_TO_C rows nor, for a RECHARGE_THEN_ORDER journey,
    the hub-cycle rows [swap_start, swap_end] (V3R4 uav_tails has no swap rows; battery service is a non-binding proxy).
    Pure: reads order["k_p"] and journey["k_arr"] / journey["k_serv"] only.  Returns a sorted list of ints."""
    kp = int(order["k_p"]); ka = int(journey["k_arr"]); ks = int(journey["k_serv"])
    return sorted({kp} | set(range(ka, ks + 1)))


def materialise_claim(fx, auth, policy, base_ledger, u, order, k_serv):
    """Step 5: from the immutable round-start snapshot ONLY (other proposals of the same UAV never
    enter the chain).  Returns (journey or None, footprint rows, failure or None).
    X1: footprint rows = journey_rows(order, journey) (frozen V3R4 uav_tails semantics), no longer the
    [start, end] endpoints of every segment."""
    st = base_state_of(base_ledger, u)
    cal = L2.SwapCalendar(policy.swap_service_mode, auth.swap_slots)   # non-binding proxy in V3R4
    v = L2.evaluate_action(fx["T_steps"], fx["D_cost"], auth, cal, policy, int(u), st["tail_location"],
                           st["tail_slot"], st["soc"], order, int(k_serv))
    if not v.get("admissible"):
        return None, [], {"class": FAIL_STATIC, "reason": v.get("reason")}
    kind = J.DIRECT_ORDER if v["action_kind"] == L2.DIRECT_SERVE else J.RECHARGE_THEN_ORDER
    try:
        jn = J.build_journey(fx, auth, int(u), st, order, int(k_serv), kind, hub=v.get("hub"),
                             swap_start=v.get("swap_start"), identity=base_ledger.identity)
    except J.JourneyError as ex:
        return None, [], {"class": FAIL_STATIC, "reason": f"JOURNEY_BUILD_FAIL:{ex}"}
    rows = journey_rows(order, jn)
    return jn, rows, None


def claim_footprint(owner_id, owner_slot, order, k_serv, rows, journey, fx=None):
    """Resource keys claimed by one frozen proposal (plan section 2.6).
    With `fx` given, station-time / swap-slot keys carry the canonical physical station identity
    (rng.station_identity: coordinate-based, relabel-invariant) instead of the raw station index, so
    that group fingerprints (RNG-key inputs) never depend on station labels.  fx=None keeps raw ints
    (backward compatible)."""
    if fx is not None:
        from .rng import station_identity
        sid = lambda m: station_identity(fx, int(m))
    else:
        sid = lambda m: int(m)
    fp = [("row", owner_id, owner_slot, int(k)) for k in rows]
    fp.append(("station_time", sid(order["c"]), int(order["k_p"])))        # endpoints: non-binding under V3R4
    fp.append(("station_time", sid(order["d"]), int(k_serv)))
    if journey.get("hub") is not None and journey.get("swap_start") is not None:
        for k in range(int(journey["swap_start"]), int(journey["swap_start"]) + 2):
            fp.append(("swap_slot", sid(journey["hub"]), k))              # UNBOUNDED_SWAP_SERVICE_PROXY: non-binding
    return fp


def residual_capacity_factory(hard_contract, n_claimants_hint=10**6):
    """C per resource key after release-old-provisional. V3R4 contract: order endpoints and hubs are
    non-binding for ordinary station-time capacity, swap service is an unbounded proxy; rows are
    exclusive (C=1).  Non-binding resources are given C=n_hint so every claim survives (n<=C).
    Only the key KIND (key[0]) is inspected, so station ids may be ints or identity strings."""
    ep_nb = bool(hard_contract.get("order_endpoint_footprint_nonbinding", False))
    hubs_nb = bool(hard_contract.get("hubs_nonbinding", False))
    ordinary = int(hard_contract.get("ordinary_station_time_capacity", 1))

    def C(key):
        kind = key[0]
        if kind == "row":
            return 1
        if kind == "station_time":
            return n_claimants_hint if ep_nb else ordinary
        if kind == "swap_slot":
            return n_claimants_hint if hubs_nb else 1
        return 1
    return C


def dry_run(fx, auth, policy, base_committed, survivors, run_uuid, round_id, identity=None, validate=False):
    """Steps 8-9: fresh disposable BatteryLedgerV3 seeded with the round-start production snapshot,
    survivors committed in canonical order; classification of failures. Returns dict with
    accepted/rejected lists, DRY_RUN_FINAL_DECISION_DIGEST and journey digest.
    BATCH_HARD_VIOLATION_COUNT is present only when validate=True (computed by validate_accepted_batch);
    otherwise the caller must compute it — it is never defaulted to 0."""
    led = L3.BatteryLedgerV3(fx, auth, policy, run_id=f"{run_uuid}:r{round_id}:dryrun", identity=identity)
    _seed_from_committed(led, fx, base_committed)
    out = _commit_sequence(led, fx, survivors, tag="dryrun")
    if validate:
        hv = validate_accepted_batch(fx, auth, out, identity=identity)
        out["BATCH_HARD_VIOLATION_COUNT"] = int(hv["hard_total"]); out["hard_validation"] = hv
        out["BATCH_HARD_VIOLATION_STATUS"] = "COMPUTED_BY_validate_accepted_batch"
    else:
        out["BATCH_HARD_VIOLATION_STATUS"] = "NOT_COMPUTED_IN_DRY_RUN_CALLER_MUST_RUN_validate_accepted_batch"
    return out


def final_commit(fx, auth, policy, base_committed, accepted, run_uuid, identity=None, expected_decision_digest=None):
    """Step 13: fresh production ledger, ONE atomic serialization commit in the same canonical order;
    digests must equal the dry-run ones, else the whole batch is invalid (no retry/repair).
    BATCH_HARD_VIOLATION_COUNT is computed on the committed batch (validate_accepted_batch), never assumed."""
    led = L3.BatteryLedgerV3(fx, auth, policy, run_id=f"{run_uuid}:final", identity=identity)
    _seed_from_committed(led, fx, base_committed)
    out = _commit_sequence(led, fx, accepted, tag="final")
    out["DRY_RUN_EQUALS_COMMITTED"] = (expected_decision_digest is None or out["DECISION_DIGEST"] == expected_decision_digest)
    hv = validate_accepted_batch(fx, auth, out, identity=identity)
    out["BATCH_HARD_VIOLATION_COUNT"] = int(hv["hard_total"]); out["hard_validation"] = hv
    out["BATCH_HARD_VIOLATION_STATUS"] = "COMPUTED_BY_validate_accepted_batch"
    out["ledger"] = led
    return out


def _seed_from_committed(led, fx, base_committed):
    """Replays the production commit records into a fresh ledger in their recorded order."""
    for r in base_committed:
        order = fx["orders"][int(r["oid"]) - 1]
        txn = led.prepare(int(r["owner"]), order, int(r["k_serv"]), proposal_digest="BASE")
        rc = led.validate_and_commit(txn)
        if not rc.get("committed"):
            raise RuntimeError(f"BASE_SNAPSHOT_REPLAY_FAIL oid={r['oid']}: {rc.get('reason')}")


def _canon(p):
    """Canonical decision fields of a proposal/decision record (fail-closed if any is missing)."""
    missing = [k for k in CANONICAL_FIELDS if k not in p]
    if missing:
        raise RuntimeError(f"PROPOSAL_MISSING_CANONICAL_FIELDS {missing} (oid={p.get('oid')})")
    return [list(p["fingerprint"]), int(p["dup_slot"]), str(p["owner_id"]), int(p["owner_slot"]), int(p["k_serv"])]


def _commit_sequence(led, fx, proposals, tag):
    accepted, rejected = [], []
    failed_uav = {}
    for p in sorted(proposals, key=canonical_commit_order):
        u = int(p["raw_u"]); order = fx["orders"][int(p["oid"]) - 1]
        if u in failed_uav:
            rejected.append({**_pub(p), "class": FAIL_BLOCKED, "reason": f"prefix failed at oid {failed_uav[u]}"})
            continue
        txn = led.prepare(u, order, int(p["k_serv"]), proposal_digest=p.get("journey_digest", "NA"))
        rc = led.validate_and_commit(txn)
        if rc.get("committed"):
            jn = led.journeys[int(p["oid"])]
            # m3 (review 2026-08-31): the ledger rebuilds the journey on the committed prefix (chain-true pre_state); the digest may
            # legitimately change (FOOTPRINT_CHANGED_AFTER_LOTTERY) but the FROZEN proposal (order, owner, k_serv) must never move.
            # BATCH_JUDGE_HARD_ONLY: the judge accepts/rejects, it never repairs an owner or a time.  Fail closed, no retry.
            if int(jn["owner"]) != u or int(jn["k_serv"]) != int(p["k_serv"]) or int(jn["order_id"]) != int(p["oid"]):
                raise RuntimeError("REBUILD_CHANGED_FROZEN_PROPOSAL")
            changed = jn["digest"] != p.get("journey_digest")
            accepted.append({**_pub(p), "class": ACCEPT, "committed_journey_digest": jn["digest"],
                             "FOOTPRINT_CHANGED_AFTER_LOTTERY": bool(changed),
                             "action_kind": rc["action_kind"], "hub": rc.get("hub"), "swap_start": rc.get("swap_start")})
        else:
            rejected.append({**_pub(p), "class": FAIL_CHAIN, "reason": rc.get("reason")})
            failed_uav[u] = int(p["oid"])
    # canonical decision digest: class + canonical claim key + committed journey digest (which fixes action_kind/hub/swap_start)
    dec = [[a["class"], *_canon(a), a["committed_journey_digest"]] for a in accepted]
    rej = [[r["class"], *_canon(r)] for r in rejected]
    return {"tag": tag, "accepted": accepted, "rejected": rejected,
            "DECISION_DIGEST": dig(dec), "DECISION_DIGEST_SCHEMA": DECISION_DIGEST_SCHEMA,
            "REJECTED_DECISION_DIGEST": dig(rej),
            "JOURNEY_DIGEST": dig([a["committed_journey_digest"] for a in accepted]),
            "FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT": sum(a["FOOTPRINT_CHANGED_AFTER_LOTTERY"] for a in accepted),
            "POST_LOTTERY_CHAIN_BAN_COUNT": sum(r["class"] == FAIL_CHAIN for r in rejected),
            "BLOCKED_BY_FAILED_PREFIX_COUNT": sum(r["class"] == FAIL_BLOCKED for r in rejected),
            "ledger_digest": led.ledger_digest(),                       # order-sensitive (commit order): provenance only (X3)
            "ledger_event_multiset_digest": ledger_event_multiset_digest(led.events),   # order-insensitive: replay comparison (X3)
            "ROW_SEMANTICS": ROW_SEMANTICS,
            "committed_records": list(led.committed), "journeys": led.journey_list()}


def ledger_event_multiset_digest(events):
    """Order-insensitive digest of a ledger event list: dig(sorted(map(_event_tuple, events)))."""
    return dig(sorted(map(_event_tuple, events)))


def _anchor(out):
    return {int(r["oid"]): {"owner": int(r["owner"]), "k_serv": int(r["k_serv"]),
                            "action_kind": J.DIRECT_ORDER if r["action_kind"] == L2.DIRECT_SERVE else J.RECHARGE_THEN_ORDER,
                            "hub": r.get("hub"), "swap_start": r.get("swap_start"), "journey_digest": r.get("journey_digest")}
            for r in out["committed_records"]}


def validate_accepted_batch(fx, auth, out, identity=None):
    """Real hard validation of the accepted dry-run batch: journey_validate anchored to the disposable
    ledger's commit records (hard_total) + materialize single-write row check.  A RowConflict /
    JourneyError (or any other escape) raised by materialize is a HARD violation, never a crash."""
    jv = J.journey_validate(fx, auth, out["journeys"], committed=_anchor(out), identity=identity)
    mat_err = None
    try:
        m = J.materialize_journeys(fx, out["journeys"])
        mat_total = int(m["validation"]["hard_total"])
    except (J.RowConflict, J.JourneyError) as e:
        mat_total = 1; mat_err = f"{type(e).__name__}:{str(e)[:200]}"
    except Exception as e:                        # any escape is a hard violation, never a pass
        mat_total = 1; mat_err = f"MATERIALIZE_ERROR:{type(e).__name__}:{str(e)[:200]}"
    return {"hard_total": int(jv["hard_total"]) + mat_total, "journey_validate": int(jv["hard_total"]), "materialize": mat_total,
            "materialize_error": mat_err, "violations_head": list(jv.get("violations", []))[:10]}


def _state4(s):
    return json.dumps({"tail_location": int(s["tail_location"]), "tail_slot": int(s["tail_slot"]), "soc": int(s["soc"]), "payload": int(s["payload"])},
                      sort_keys=True, separators=(",", ":"))


def _event_tuple(e):
    """Canonical tuple of one ledger event (the 15 physical fields of the V2 event schema; transaction/plan/authority
    digests and rule_id excluded).  Same field list as BatteryLedgerV3.ledger_digest / replay_from_journeys."""
    return (e["uav_id"], e["event_index"], e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["soc_before"], e["delta_soc"],
            e["soc_after"], e["payload_before"], e["payload_after"], e["action_kind"], e["hub_id_or_NA"], e["swap_service_slot_or_NA"])


def independent_replay(fx, auth, out, identity=None, expected_plan=None):
    """CD R-5 strict replay, four checks, all fail-closed:
    (1) journey_validate hard_total == 0 anchored to the commit records;
    (2) replay_from_journeys returns a validation dict with hard_total == 0 (missing/unexpected -> FAIL);
    (3) committed owner/time equal the final plan for every order (when expected_plan given);
    (4) replay tail states == production ledger states (exact serialised equality for every UAV; UAVs without
        journeys must sit at their birth state) and the replay event multiset == production ledger events."""
    return _replay_core(fx, auth, out, identity=identity, expected_plan=expected_plan)[0]


def committed_plan_replay_verdict(fx, auth, final_dict, identity=None, expected_plan=None):
    """X3: stored-evidence replay verdict for a committed plan (safe for a JSON round-tripped `final_dict`, i.e. the
    fresh-clone replay).  Runs independent_replay and additionally compares the ORDER-INSENSITIVE replayed event
    multiset digest with final_dict["ledger_event_multiset_digest"].
    PASS iff (1) journey_validate hard_total == 0, (2) replay validation hard_total == 0, (3) committed owner/time ==
    expected_plan (when given), and (M) replayed ledger_event_multiset_digest == stored one.  The live production-ledger
    comparison (independent_replay check 4) is "NOT_AVAILABLE" when final_dict carries no `ledger` object (JSON) and is
    recorded, never failed on; when a live ledger IS present and disagrees, that is still a FAIL (real evidence is never
    tolerated).  `ledger_digest` (order-sensitive, commit order) is reported as provenance only: replay_from_journeys
    rebuilds events UAV-ascending, so its equality is NOT required."""
    rep, raw = _replay_core(fx, auth, final_dict, identity=identity, expected_plan=expected_plan)
    rep_events = raw[1] if isinstance(raw, tuple) and len(raw) > 1 and isinstance(raw[1], list) else None
    replayed_ms = None; ms_err = None
    if rep_events is not None:
        try:
            replayed_ms = ledger_event_multiset_digest(rep_events)
        except Exception as e:                    # malformed events: no digest, verdict fails below
            ms_err = f"{type(e).__name__}:{str(e)[:120]}"
    stored_ms = final_dict.get("ledger_event_multiset_digest")
    multiset_ok = stored_ms is not None and replayed_ms is not None and replayed_ms == stored_ms
    core_ok = bool(int(rep["journey_validate_hard_total"]) == 0 and rep["replay_validation_pass"] is True and rep["committed_plan_consistent"] is True)
    live_present = final_dict.get("ledger") is not None
    if live_present:
        live_ok = bool(rep["ledger_states_match"] and rep["ledger_events_match"]); states = bool(live_ok)
    else:
        live_ok = True; states = "NOT_AVAILABLE"
    return {"PASS": bool(core_ok and multiset_ok and live_ok), "core_checks_pass": core_ok,
            "journey_validate_hard_total": rep["journey_validate_hard_total"], "replay_validation_pass": rep["replay_validation_pass"],
            "committed_plan_consistent": rep["committed_plan_consistent"], "plan_mismatch_oids": rep["plan_mismatch_oids"],
            "expected_plan_size": (len(expected_plan) if expected_plan is not None else None), "committed_records": len(final_dict.get("committed_records") or []),
            "ledger_event_multiset_match": multiset_ok, "stored_ledger_event_multiset_digest": stored_ms, "replayed_ledger_event_multiset_digest": replayed_ms,
            "multiset_digest_error": ms_err,
            "ledger_states_match": states, "live_ledger_present": live_present, "ledger_state_reason": rep["ledger_state_reason"],
            "stored_ledger_digest_provenance_only": final_dict.get("ledger_digest"),
            "replayed_event_digest_order_sensitive_provenance_only": (raw[2] if isinstance(raw, tuple) and len(raw) > 2 else None),
            "independent_replay": rep,
            "rule": "PASS iff journey_validate==0 and replay validation==0 and plan consistent and ledger_event_multiset_digest equal; "
                    "live ledger states NOT_AVAILABLE from JSON is recorded, never failed on; a present live ledger must also match"}


def _replay_core(fx, auth, out, identity=None, expected_plan=None):
    """independent_replay body; returns (result_dict, raw replay tuple) so callers can reuse the replayed events."""
    anchor = _anchor(out)
    jv = J.journey_validate(fx, auth, out["journeys"], committed=anchor, identity=identity)
    rep = L3.replay_from_journeys(fx, auth, out["journeys"], committed=anchor, identity=identity)
    rep_val = rep[3] if isinstance(rep, tuple) and len(rep) > 3 else None
    if isinstance(rep_val, dict) and "hard_total" in rep_val:
        rep_ok = int(rep_val["hard_total"]) == 0; rep_reason = None
    else:
        rep_ok = False; rep_reason = "REPLAY_RETURNED_NO_VALIDATION"
    plan_ok = True; mism = []
    if expected_plan is not None:
        for oid, (u, k) in expected_plan.items():
            a = anchor.get(int(oid))
            if a is None or a["owner"] != int(u) or a["k_serv"] != int(k):
                plan_ok = False; mism.append(int(oid))
        plan_ok = plan_ok and len(anchor) == len(expected_plan)
    led = out.get("ledger")
    state_ok = False; state_mism = []; state_reason = None; events_ok = False
    rep_states = rep[0] if isinstance(rep, tuple) and len(rep) > 0 and isinstance(rep[0], dict) else None
    rep_events = rep[1] if isinstance(rep, tuple) and len(rep) > 1 and isinstance(rep[1], list) else None
    if led is None:
        state_reason = "PRODUCTION_LEDGER_ABSENT"
    elif rep_states is None or rep_events is None:
        state_reason = "REPLAY_RETURNED_NO_STATES_OR_EVENTS"
    else:
        birth = {"tail_slot": 0, "soc": int(auth.B_init), "payload": 0}
        for u in range(int(fx["N"])):
            exp = _state4(rep_states[u]) if u in rep_states else _state4({**birth, "tail_location": int(fx["births"][u])})
            if _state4(led.states[u]) != exp:
                state_mism.append(u)
        state_ok = not state_mism
        try:
            events_ok = sorted(map(_event_tuple, led.events)) == sorted(map(_event_tuple, rep_events))
        except Exception as e:                   # malformed events are a failure, never a pass
            events_ok = False; state_reason = f"EVENT_COMPARE_ERROR:{type(e).__name__}"
    res = {"journey_validate_hard_total": jv["hard_total"], "replay_validation": rep_val, "replay_validation_pass": rep_ok, "replay_reason": rep_reason,
           "committed_plan_consistent": plan_ok, "plan_mismatch_oids": mism[:20],
           "ledger_states_match": state_ok, "ledger_state_mismatch_uavs": state_mism[:20], "ledger_events_match": events_ok, "ledger_state_reason": state_reason,
           "PASS": bool(jv["hard_total"] == 0 and rep_ok and plan_ok and state_ok and events_ok)}
    return res, rep


def _pub(p):
    return {k: p[k] for k in ("oid", "raw_u", "k_serv", "fingerprint", "dup_slot", "owner_id", "owner_slot", "journey_digest") if k in p}


# ----------------------------------------------------------------------------- CPU self-test (explicit checks, no assert)
def _check(cond, msg):
    if not cond:
        raise RuntimeError("BATCH_JUDGE_TEST_FAIL: " + msg)


def _selftest():
    import os, sys
    sys.path.insert(0, os.environ.get("E2_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fixture as FX
    R = {}
    fx = FX.build_fx(6)
    auth, policy = FX.load_battery(fx)
    base = L3.BatteryLedgerV3(fx, auth, policy, run_id="base")
    props = []
    for o in fx["orders"][:6]:
        u = o["U_base"][0]
        jn, rows, fail = materialise_claim(fx, auth, policy, base, u, o, int(o["k_d"]))
        _check(fail is None and bool(rows), f"materialise {o['order_id']} {fail}")
        props.append({"oid": o["order_id"], "raw_u": u, "k_serv": int(o["k_d"]), "fingerprint": (o["k_p"], o["c"], o["k_d"], o["d"]),
                      "dup_slot": 0, "owner_id": f"id{u}", "owner_slot": 0, "journey_digest": jn["digest"], "rows": rows, "journey": jn})
    # X1: journey_rows == frozen V3R4 uav_tails ({k_p} | [arr, k_serv], arr = k_p + T[c,d] = k_d-4); no WAIT_PRE_C/INFLIGHT_TO_C rows (min row == k_p)
    T = fx["T_steps"]
    for p in props:
        o = fx["orders"][p["oid"] - 1]; jn = p["journey"]
        arr_donor = int(o["k_p"]) + (0 if o["c"] == o["d"] else int(T[o["c"] - 1, o["d"] - 1]))
        _check(int(jn["k_arr"]) == arr_donor == int(o["k_d"]) - 4, f"journey k_arr {jn['k_arr']} != donor arr {arr_donor} / k_d-4 (oid {p['oid']})")
        donor_rows = {int(o["k_p"])} | set(range(arr_donor, int(p["k_serv"]) + 1))
        _check(p["rows"] == sorted(donor_rows) == journey_rows(o, jn), f"journey_rows != V3R4 uav_tails rows (oid {p['oid']}): {p['rows'][:8]} vs {sorted(donor_rows)[:8]}")
        _check(min(p["rows"]) == int(o["k_p"]) and all(r >= int(o["k_p"]) for r in p["rows"]), "claim rows must not contain pre-collection (WAIT_PRE_C/INFLIGHT_TO_C) rows")
        _check(1 not in p["rows"] or int(o["k_p"]) == 1, "row 1 (WAIT_PRE_C start) must not be claimed")
        hub_rows = set(range(int(jn["swap_start"]) + 1, int(jn["swap_end"]) + 1)) if jn.get("hub") is not None else set()
        _check(not (hub_rows & set(p["rows"])) or hub_rows & donor_rows, "hub-cycle/swap rows are not uav_tails rows and must not be claimed")
    R["journey_rows"] = {"orders_checked": len(props), "semantics": ROW_SEMANTICS, "rows_example": props[0]["rows"][:8], "PASS": True}
    # footprint: raw ints without fx; canonical station identity with fx (if rng.station_identity is available); capacity factory by kind only
    fp_raw = claim_footprint("idX", 0, fx["orders"][0], int(fx["orders"][0]["k_d"]), props[0]["rows"], props[0]["journey"])
    st_raw = [r for r in fp_raw if r[0] == "station_time"]
    _check(len(st_raw) == 2 and all(isinstance(r[1], int) for r in st_raw), f"raw footprint station keys {st_raw}")
    _check(st_raw[0][1] == int(fx["orders"][0]["c"]) and st_raw[1][1] == int(fx["orders"][0]["d"]), "raw footprint station ints")
    Cf = residual_capacity_factory(fx["hard_contract"])
    _check(Cf(("row", "idX", 0, 5)) == 1 and Cf(("station_time", "sha256:abc", 7)) == 10**6 and Cf(("swap_slot", "sha256:def", 7)) == 10**6, "capacity factory must only look at the key kind")
    _check(residual_capacity_factory({"ordinary_station_time_capacity": 2})(("station_time", "sid", 1)) == 2, "binding capacity with string station id")
    try:
        from rng import station_identity
        fp_id = claim_footprint("idX", 0, fx["orders"][0], int(fx["orders"][0]["k_d"]), props[0]["rows"], props[0]["journey"], fx=fx)
        st_id = [r for r in fp_id if r[0] == "station_time"]
        _check(st_id[0][1] == station_identity(fx, int(fx["orders"][0]["c"])) and st_id[1][1] == station_identity(fx, int(fx["orders"][0]["d"])), "fx footprint must use station_identity")
        _check([r for r in fp_id if r[0] == "row"] == [r for r in fp_raw if r[0] == "row"], "rows unchanged by fx")
        R["footprint"] = {"raw_ok": True, "station_identity_available": True, "identity_ok": True, "PASS": True}
    except ImportError:
        R["footprint"] = {"raw_ok": True, "station_identity_available": False, "identity_ok": None, "PASS": True}
    # dry run: input order invariance
    d1 = dry_run(fx, auth, policy, [], props, "uuid", 0, identity=base.identity)
    d2 = dry_run(fx, auth, policy, [], list(reversed(props)), "uuid", 0, identity=base.identity)
    _check(d1["DECISION_DIGEST"] == d2["DECISION_DIGEST"] and d1["JOURNEY_DIGEST"] == d2["JOURNEY_DIGEST"], "input order affected the dry run")
    _check("BATCH_HARD_VIOLATION_COUNT" not in d1 and d1["BATCH_HARD_VIOLATION_STATUS"].startswith("NOT_COMPUTED"), "dry run must not default BATCH_HARD_VIOLATION_COUNT")
    d1v = dry_run(fx, auth, policy, [], props, "uuid", 0, identity=base.identity, validate=True)
    _check(d1v["DECISION_DIGEST"] == d1["DECISION_DIGEST"] and d1v["BATCH_HARD_VIOLATION_COUNT"] == 0 and d1v["BATCH_HARD_VIOLATION_STATUS"].startswith("COMPUTED"), f"validate=True path {d1v.get('hard_validation')}")
    # M8: digests depend ONLY on canonical fields - proposals carrying side keys (provenance, QUALIFIED_G, ...) give the same digests as minimal ones
    minimal = [{k: p[k] for k in ("oid", "raw_u", "k_serv", "fingerprint", "dup_slot", "owner_id", "owner_slot", "journey_digest")} for p in props]
    rich = [dict(p, provenance="INNER_G_WEIGHTED_DRAW", QUALIFIED_G=True, TV_o=0.3, TAU_TV=0.1, selected_p_G=0.5, uniform_baseline=0.25, tuple_rule="x",
                 origin_universe_digest="u", origin_x_sha256="s", origin_round=0, self_pin_free_origin=True, observer_unstable=False) for p in props]
    dm = dry_run(fx, auth, policy, [], minimal, "uuid", 0, identity=base.identity); dr_ = dry_run(fx, auth, policy, [], rich, "uuid", 0, identity=base.identity)
    _check(dm["DECISION_DIGEST"] == dr_["DECISION_DIGEST"] == d1["DECISION_DIGEST"] and dm["JOURNEY_DIGEST"] == dr_["JOURNEY_DIGEST"] and dm["REJECTED_DECISION_DIGEST"] == dr_["REJECTED_DECISION_DIGEST"],
           "side keys leaked into a digest")
    # oid / raw_u relabel with identical canonical fields: DECISION_DIGEST must not move (labels are not canonical) - emulate by renaming oid keys is
    # impossible without changing physics, so verify the digest recomputes from canonical fields only:
    recomputed = dig([[a["class"], list(a["fingerprint"]), int(a["dup_slot"]), str(a["owner_id"]), int(a["owner_slot"]), int(a["k_serv"]), a["committed_journey_digest"]] for a in d1["accepted"]])
    _check(recomputed == d1["DECISION_DIGEST"], "DECISION_DIGEST is not the documented canonical function")
    _check(all(k not in json.dumps([[a["class"], *_canon(a), a["committed_journey_digest"]] for a in d1["accepted"]]) for k in ("provenance", "QUALIFIED_G")), "canonical tuple carries side keys")
    R["digests"] = {"input_order_invariant": True, "side_key_invariant": True, "canonical_recompute_equal": True, "accepted": len(d1["accepted"]), "rejected": len(d1["rejected"]), "PASS": True}
    # final commit + independent replay (4 checks) on the accepted set
    acc = [p for p in props if p["oid"] in {a["oid"] for a in d1["accepted"]}]
    dacc = dry_run(fx, auth, policy, [], acc, "uuid", 0, identity=base.identity)
    fin = final_commit(fx, auth, policy, [], acc, "uuid", identity=base.identity, expected_decision_digest=dacc["DECISION_DIGEST"])
    _check(fin["DRY_RUN_EQUALS_COMMITTED"] and fin["JOURNEY_DIGEST"] == dacc["JOURNEY_DIGEST"] and fin["DECISION_DIGEST"] == dacc["DECISION_DIGEST"], "final != dry run on identical batch")
    _check(fin["BATCH_HARD_VIOLATION_COUNT"] == 0 and fin["BATCH_HARD_VIOLATION_STATUS"].startswith("COMPUTED"), f"final hard validation {fin.get('hard_validation')}")
    rep = independent_replay(fx, auth, fin, identity=base.identity, expected_plan={p["oid"]: (p["raw_u"], p["k_serv"]) for p in acc})
    _check(rep["PASS"] and rep["ledger_states_match"] and rep["ledger_events_match"], f"replay {rep}")
    # fail-closed: ledger absent -> FAIL; replay returning no validation -> FAIL; tampered production state -> FAIL
    fin_noled = {k: v for k, v in fin.items() if k != "ledger"}
    r_noled = independent_replay(fx, auth, fin_noled, identity=base.identity)
    _check(not r_noled["PASS"] and r_noled["ledger_state_reason"] == "PRODUCTION_LEDGER_ABSENT", "replay must fail without the production ledger")
    orig = L3.replay_from_journeys
    try:
        L3.replay_from_journeys = lambda *a, **k: orig(*a, **k)[:3]
        r_short = independent_replay(fx, auth, fin, identity=base.identity)
    finally:
        L3.replay_from_journeys = orig
    _check(not r_short["PASS"] and r_short["replay_reason"] == "REPLAY_RETURNED_NO_VALIDATION", "replay without validation dict must FAIL, never default True")
    u0 = int(acc[0]["raw_u"]); saved = copy.deepcopy(fin["ledger"].states[u0])
    fin["ledger"].states[u0]["soc"] = int(saved["soc"]) - 1
    r_tamper = independent_replay(fx, auth, fin, identity=base.identity)
    fin["ledger"].states[u0] = saved
    _check(not r_tamper["PASS"] and r_tamper["ledger_state_mismatch_uavs"] == [u0], "tampered production tail state not detected")
    _check(independent_replay(fx, auth, fin, identity=base.identity)["PASS"], "restored ledger must pass again")
    R["replay"] = {"pass": True, "no_ledger_fails": True, "no_validation_fails": True, "tampered_state_fails": True, "committed": len(fin["committed_records"]), "PASS": True}
    # validate_accepted_batch: RowConflict from materialize is a hard violation, not a crash (same journey twice writes the same rows twice)
    dup = dict(dacc); dup["journeys"] = list(dacc["journeys"]) + [dacc["journeys"][0]]
    hv = validate_accepted_batch(fx, auth, dup, identity=base.identity)
    _check(hv["hard_total"] >= 1 and hv["materialize"] == 1 and hv["materialize_error"] is not None, f"duplicate journey must be a hard violation {hv}")
    _check(validate_accepted_batch(fx, auth, dacc, identity=base.identity)["hard_total"] == 0, "clean batch must validate")
    R["hard_validation"] = {"duplicate_journey_hard": hv["hard_total"], "materialize_error": hv["materialize_error"][:60], "clean_hard_total": 0, "PASS": True}
    # same UAV, two proposals: the second one's chain must be judged on the committed prefix (CHAIN or accept), never silently reordered
    u = props[0]["raw_u"]; o2 = fx["orders"][1]
    jn2, rows2, f2 = materialise_claim(fx, auth, policy, base, u, o2, int(o2["k_d"]))
    p2 = dict(props[1], raw_u=u, owner_id=f"id{u}", journey_digest=(jn2 or {}).get("digest", "NA"))
    d3 = dry_run(fx, auth, policy, [], [props[0], p2], "uuid", 1, identity=base.identity)
    _check(len(d3["accepted"]) + len(d3["rejected"]) == 2, "same-UAV pair must be fully classified")
    R["same_uav_pair"] = {"classes": [a["class"] for a in d3["accepted"]] + [r["class"] for r in d3["rejected"]], "PASS": True}
    # X1: a same-UAV pair with DISJOINT service windows (chain-feasible: k_p2 - T[d1,c2] >= k_serv1) has disjoint claim rows and BOTH are accepted
    pair = None
    for oa in fx["orders"]:
        for ob in fx["orders"]:
            if oa["order_id"] >= ob["order_id"]:
                continue
            common = sorted(set(oa["U_base"]) & set(ob["U_base"]))
            o1, o2_ = (oa, ob) if oa["k_d"] < ob["k_d"] else (ob, oa)
            Tt = 0 if o1["d"] == o2_["c"] else int(T[o1["d"] - 1, o2_["c"] - 1])
            if common and o2_["k_p"] - Tt >= o1["k_d"] and o2_["k_d"] - 4 > o1["k_d"]:
                pair = (o1, o2_, common[0]); break
        if pair:
            break
    _check(pair is not None, "frozen fixture must contain a same-UAV chain-feasible disjoint pair")
    o1, o2_, uu = pair
    j1, r1, f1 = materialise_claim(fx, auth, policy, base, uu, o1, int(o1["k_d"]))
    j2, r2_, f2_ = materialise_claim(fx, auth, policy, base, uu, o2_, int(o2_["k_d"]))
    _check(f1 is None and f2_ is None, f"disjoint pair must materialise from the base snapshot: {f1} {f2_}")
    _check(not (set(r1) & set(r2_)), f"disjoint same-UAV pair must not share claim rows: {sorted(set(r1) & set(r2_))[:8]}")
    fp1 = claim_footprint(f"id{uu}", 0, o1, int(o1["k_d"]), r1, j1); fp2 = claim_footprint(f"id{uu}", 0, o2_, int(o2_["k_d"]), r2_, j2)
    _check(not ({k for k in fp1 if k[0] == "row"} & {k for k in fp2 if k[0] == "row"}), "row resource keys of the disjoint pair must not intersect")
    pp = [{"oid": o["order_id"], "raw_u": uu, "k_serv": int(o["k_d"]), "fingerprint": (o["k_p"], o["c"], o["k_d"], o["d"]), "dup_slot": 0, "owner_id": f"id{uu}",
           "owner_slot": 0, "journey_digest": j["digest"]} for o, j in ((o1, j1), (o2_, j2))]
    d4 = dry_run(fx, auth, policy, [], pp, "uuid", 2, identity=base.identity, validate=True)
    acc4 = {a["oid"]: a for a in d4["accepted"]}
    _check(len(d4["accepted"]) == 2 and d4["POST_LOTTERY_CHAIN_BAN_COUNT"] == 0 and d4["BLOCKED_BY_FAILED_PREFIX_COUNT"] == 0,
           f"disjoint same-UAV pair must BOTH be accepted (chain-true second journey): {[(r['oid'], r['class'], r.get('reason')) for r in d4['rejected']]}")
    _check(d4["BATCH_HARD_VIOLATION_COUNT"] == 0, f"two-order chain must validate hard: {d4.get('hard_validation')}")
    second = acc4[o2_["order_id"]]
    chain_true_changed = second["committed_journey_digest"] != j2["digest"]
    _check(chain_true_changed and second["FOOTPRINT_CHANGED_AFTER_LOTTERY"] is True and d4["FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT"] == 1,
           "second journey must be the chain-true one (digest differs from the snapshot claim) and be accepted, not rejected")
    _check(acc4[o1["order_id"]]["FOOTPRINT_CHANGED_AFTER_LOTTERY"] is False, "first journey of the chain equals its snapshot claim")
    jn_second = next(j for j in d4["journeys"] if j["order_id"] == o2_["order_id"])
    _check(jn_second["pre_state"]["tail_slot"] == int(o1["k_d"]) and jn_second["pre_state"]["tail_location"] == int(o1["d"]), "chain-true pre_state = post-state of the first journey")
    R["disjoint_same_uav_pair"] = {"oids": [o1["order_id"], o2_["order_id"]], "uav": int(uu), "rows1": r1, "rows2": r2_, "accepted": len(d4["accepted"]),
                                   "FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT": d4["FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT"], "POST_LOTTERY_CHAIN_BAN_COUNT": d4["POST_LOTTERY_CHAIN_BAN_COUNT"],
                                   "second_journey_chain_true_digest_differs": chain_true_changed, "treatment": "ACCEPTED_HARD_VALID with chain-true journey (not R3_CHAIN_CONDITIONAL_BAN)",
                                   "PASS": True}
    # X3: order-insensitive ledger_event_multiset_digest; committed_plan_replay_verdict PASS after a JSON round trip; FAIL on tampered plan / digest
    _check(fin["ledger_event_multiset_digest"] == ledger_event_multiset_digest(fin["ledger"].events) == dig(sorted(map(_event_tuple, fin["ledger"].events))),
           "ledger_event_multiset_digest must be dig(sorted(event tuples)) of the production ledger")
    fin_json = json.loads(json.dumps({k: v for k, v in fin.items() if k != "ledger"}, default=str))
    plan_json = {str(p["oid"]): (p["raw_u"], p["k_serv"]) for p in acc}
    _check(fin_json["ledger_event_multiset_digest"] == fin["ledger_event_multiset_digest"], "multiset digest must survive the JSON round trip")
    vd = committed_plan_replay_verdict(fx, auth, fin_json, identity=base.identity, expected_plan=plan_json)
    _check(vd["PASS"] and vd["ledger_event_multiset_match"] and vd["ledger_states_match"] == "NOT_AVAILABLE" and vd["core_checks_pass"], f"verdict on JSON final must PASS: {vd}")
    _check(vd["replayed_ledger_event_multiset_digest"] == fin["ledger_event_multiset_digest"], "replayed multiset digest must equal the stored one")
    vd_live = committed_plan_replay_verdict(fx, auth, fin, identity=base.identity, expected_plan={p["oid"]: (p["raw_u"], p["k_serv"]) for p in acc})
    _check(vd_live["PASS"] and vd_live["ledger_states_match"] is True and vd_live["live_ledger_present"], "verdict with the live ledger must PASS and compare states")
    bad_plan = dict(plan_json); k0 = next(iter(bad_plan)); bad_plan[k0] = (int(bad_plan[k0][0]) + 1, bad_plan[k0][1])
    vd_bad = committed_plan_replay_verdict(fx, auth, fin_json, identity=base.identity, expected_plan=bad_plan)
    _check(not vd_bad["PASS"] and vd_bad["committed_plan_consistent"] is False and vd_bad["ledger_event_multiset_match"], f"tampered plan must FAIL the verdict: {vd_bad}")
    vd_dg = committed_plan_replay_verdict(fx, auth, dict(fin_json, ledger_event_multiset_digest="0" * 64), identity=base.identity, expected_plan=plan_json)
    _check(not vd_dg["PASS"] and vd_dg["ledger_event_multiset_match"] is False and vd_dg["core_checks_pass"], "tampered multiset digest must FAIL the verdict")
    vd_nodg = committed_plan_replay_verdict(fx, auth, {k: v for k, v in fin_json.items() if k != "ledger_event_multiset_digest"}, identity=base.identity, expected_plan=plan_json)
    _check(not vd_nodg["PASS"] and vd_nodg["stored_ledger_event_multiset_digest"] is None, "missing stored multiset digest must FAIL (fail-closed)")
    order_sensitive_equal = fin["ledger_digest"] == vd["replayed_event_digest_order_sensitive_provenance_only"]
    R["multiset_digest"] = {"json_round_trip_equal": True, "verdict_pass_json": vd["PASS"], "verdict_pass_live": vd_live["PASS"], "tampered_plan_fails": not vd_bad["PASS"],
                            "tampered_digest_fails": not vd_dg["PASS"], "missing_digest_fails": not vd_nodg["PASS"],
                            "order_sensitive_ledger_digest_equal_to_replay_digest_provenance_only": order_sensitive_equal, "PASS": True}
    # m3: the frozen-proposal guard in _commit_sequence.  Positive path: every accepted journey above (incl. the chain-true second journey of the
    # disjoint same-UAV pair, whose DIGEST changed) carries owner == raw_u, k_serv == proposal k_serv, order_id == oid, so nothing raised.
    # Negative path: a ledger double whose rebuilt journey reports a different owner must make _commit_sequence raise (fail closed, no repair).
    for a in d1["accepted"] + d4["accepted"]:
        jn_a = next(j for j in (d1["journeys"] if a in d1["accepted"] else d4["journeys"]) if int(j["order_id"]) == int(a["oid"]))
        _check(int(jn_a["owner"]) == int(a["raw_u"]) and int(jn_a["k_serv"]) == int(a["k_serv"]), f"accepted journey must carry the frozen proposal (oid {a['oid']})")

    class _OwnerTamperLedger:
        """Selftest double: delegates every ledger operation to a real BatteryLedgerV3 but reports rebuilt journeys with owner+1."""
        def __init__(self, real):
            self._r = real

        def prepare(self, *a, **k):
            return self._r.prepare(*a, **k)

        def validate_and_commit(self, txn):
            return self._r.validate_and_commit(txn)

        @property
        def journeys(self):
            return {oid: dict(j, owner=int(j["owner"]) + 1) for oid, j in self._r.journeys.items()}

        def __getattr__(self, name):
            return getattr(self._r, name)
    raised = None
    try:
        _commit_sequence(_OwnerTamperLedger(L3.BatteryLedgerV3(fx, auth, policy, run_id="tamper", identity=base.identity)), fx, props, tag="tamper")
    except RuntimeError as e:
        raised = str(e)
    _check(raised == "REBUILD_CHANGED_FROZEN_PROPOSAL", f"a rebuilt journey with a different owner must raise REBUILD_CHANGED_FROZEN_PROPOSAL, got {raised!r}")
    R["frozen_proposal_guard"] = {"positive_path_unchanged": True, "accepted_checked": len(d1["accepted"]) + len(d4["accepted"]), "owner_tamper_raises": raised,
                                  "note": "m3: _commit_sequence raises REBUILD_CHANGED_FROZEN_PROPOSAL if the ledger-rebuilt journey's (owner, k_serv, order_id) differs "
                                          "from the frozen proposal; digest changes (chain-true pre_state) remain allowed and are counted by FOOTPRINT_CHANGED_AFTER_LOTTERY",
                                  "PASS": True}
    R["PASS"] = all(v.get("PASS") is True for v in R.values() if isinstance(v, dict))
    print("batch_judge selftest OK: accepted", len(d1["accepted"]), "rejected", len(d1["rejected"]),
          "| same-UAV pair ->", R["same_uav_pair"]["classes"], "| disjoint same-UAV pair accepted", R["disjoint_same_uav_pair"]["accepted"], "/2",
          "FOOTPRINT_CHANGED", R["disjoint_same_uav_pair"]["FOOTPRINT_CHANGED_AFTER_LOTTERY_COUNT"], "CHAIN_BAN", R["disjoint_same_uav_pair"]["POST_LOTTERY_CHAIN_BAN_COUNT"],
          "| replay 4-check PASS", rep["PASS"], "| JSON verdict PASS", R["multiset_digest"]["verdict_pass_json"],
          "| station_identity available", R["footprint"]["station_identity_available"], "| footprint rows e.g.", props[0]["rows"][:6])
    return R


if __name__ == "__main__":
    _selftest()
