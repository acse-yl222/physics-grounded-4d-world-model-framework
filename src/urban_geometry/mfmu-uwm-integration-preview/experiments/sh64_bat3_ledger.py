"""BatteryLedger V3 — journeys are the committed truth; ledger events are DERIVED from journeys (GO §5/§6/§8).

BatteryLedgerV3 keeps the V2 candidate evaluation (frozen semantics: DIRECT else RECHARGE over the full-chain-feasible hub
set, non-binding swap service) but on commit it builds the canonical Journey (sh64_bat3_journey.build_journey) from the
UAV's committed pre_state, derives the ledger events from the journey segments, and cross-checks them against the V2
evaluator's event chain (any mismatch -> ROUTE_LEDGER_MISMATCH, fail-closed). Prefix replay starts from journeys.
"""
import copy, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from experiments import sh64_bat2_ledger as L2
from experiments import sh64_bat3_journey as J

ROUTE_LEDGER_MISMATCH = "ROUTE_LEDGER_MISMATCH"


def _ev_key(e):
    return (e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["soc_before"], e["soc_after"], e["payload_before"], e["payload_after"])


class BatteryLedgerV3(L2.BatteryLedgerV2):
    def __init__(self, fx, auth, policy, run_id="RUN", identity=None):
        if policy.swap_service_mode != "UNBOUNDED_SWAP_SERVICE_PROXY":
            raise L2.BatteryPolicyError("V3_MAIN_SCHEDULER_REQUIRES_NON_BINDING_SWAP_SERVICE")
        super().__init__(fx, auth, policy, run_id=run_id)
        self.journeys = {}                 # oid -> Journey (committed truth)
        self.identity = identity or {"policy_digest": policy.digest(), "authority_digest": auth.authority_digest}
        self.counters["route_ledger_mismatch"] = 0

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
            return {"committed": False, "reason": L2.VERSION_OR_DIGEST_CONFLICT, "transaction_id": txn["transaction_id"]}
        if txn["oid"] in self.journeys:                       # one committed journey per order, ever (no silent overwrite)
            self.counters["rejects"] += 1; self.counters["duplicate_order_commit"] = self.counters.get("duplicate_order_commit", 0) + 1
            return {"committed": False, "reason": "DUPLICATE_ORDER_COMMIT", "transaction_id": txn["transaction_id"]}
        order = self.fx["orders"][txn["oid"] - 1]
        v = self.evaluate(i, order, txn["k_serv"])
        if not v["admissible"]:
            self.counters["rejects"] += 1
            return {"committed": False, "reason": v["reason"], "transaction_id": txn["transaction_id"]}
        pv = txn.get("verdict") or {}
        adg = L2.dig([(e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["delta_soc"]) for e in v["events"]])
        if not (pv.get("admissible") is True and pv.get("action_kind") == v["action_kind"] and int(pv.get("B_D", -1)) == int(v["B_D"]) and pv.get("certificate") == v["certificate"]
                and pv.get("hub") == v.get("hub") and pv.get("swap_start") == v.get("swap_start") and txn.get("action_digest") == adg):
            self.counters["rejects"] += 1
            return {"committed": False, "reason": L2.TRANSACTION_REPLAY_OR_IDEMPOTENCY_FAIL, "transaction_id": txn["transaction_id"]}
        # ---- canonical journey = the committed truth ----
        kind = J.DIRECT_ORDER if v["action_kind"] == L2.DIRECT_SERVE else J.RECHARGE_THEN_ORDER
        pre = {"tail_location": s["tail_location"], "tail_slot": s["tail_slot"], "soc": s["soc"], "payload": 0}
        try:
            jn = J.build_journey(self.fx, self.auth, i, pre, order, txn["k_serv"], kind, hub=v.get("hub"), swap_start=v.get("swap_start"), identity=self.identity)
        except J.JourneyError as ex:
            self.counters["rejects"] += 1
            return {"committed": False, "reason": f"JOURNEY_BUILD_FAIL:{ex}", "transaction_id": txn["transaction_id"]}
        base = sum(1 for e in self.events if e["uav_id"] == i)
        rows = J.journey_events(jn, self.auth.authority_digest, txn_id=txn["transaction_id"], plan_digest=txn["proposal_digest"], idx0=base)
        # cross-check: journey-derived events == V2 evaluator chain (structure, times, stations, SoC, payload)
        if [_ev_key(e) for e in rows] != [_ev_key(e) for e in v["events"]] or jn["post_state"]["soc"] != int(v["B_D"]) or jn["certificate"] != v["certificate"]:
            self.counters["route_ledger_mismatch"] += 1; self.counters["rejects"] += 1
            return {"committed": False, "reason": ROUTE_LEDGER_MISMATCH, "transaction_id": txn["transaction_id"]}
        snap = (copy.deepcopy(s), len(self.events), self.global_version, self.cal.snapshot(), len(self.committed), dict(self.journeys))
        try:
            if kind == J.RECHARGE_THEN_ORDER:
                self.cal.occupy(jn["hub"], jn["swap_start"], i, txn["oid"])
            self.events.extend(rows); self.journeys[txn["oid"]] = jn
            s["tail_location"] = jn["post_state"]["tail_location"]; s["tail_slot"] = jn["post_state"]["tail_slot"]; s["soc"] = jn["post_state"]["soc"]; s["payload"] = 0
            s["order_state"] = "WAITING_AT_D"; s["ledger_version"] += 1; s["orders"].append(txn["oid"]); self.global_version += 1
            self.committed.append({"oid": txn["oid"], "owner": i, "k_serv": int(txn["k_serv"]), "action_kind": v["action_kind"], "hub": v.get("hub"), "swap_start": v.get("swap_start"), "journey_digest": jn["digest"]})
            if L2.certificate(self.T, self.auth, s["tail_location"], s["tail_slot"], s["soc"])[0] is None:
                raise RuntimeError("POST_COMMIT_TAIL_NOT_HUB_REACHABLE")
        except Exception as ex:
            self.states[i] = snap[0]; del self.events[snap[1]:]; self.global_version = snap[2]; self.cal.restore(snap[3]); del self.committed[snap[4]:]; self.journeys = snap[5]
            self.counters["rollbacks"] += 1; self.counters["rejects"] += 1
            return {"committed": False, "reason": f"ROLLBACK:{ex}", "transaction_id": txn["transaction_id"]}
        self.counters["commits"] += 1; self.counters["direct_commits" if kind == J.DIRECT_ORDER else "recharge_commits"] += 1
        rc = {"committed": True, "transaction_id": txn["transaction_id"], "oid": txn["oid"], "uav_i": i, "k_serv": txn["k_serv"], "action_kind": v["action_kind"], "journey_kind": kind,
              "hub": v.get("hub"), "swap_start": v.get("swap_start"), "soc_after": jn["post_state"]["soc"], "certificate": jn["certificate"], "cost": jn["cost"],
              "journey_digest": jn["digest"], "ledger_digest": self.ledger_digest(), "idempotent_replay": False}
        self.receipts[key] = rc
        return dict(rc)

    def committed_decisions(self):
        """{oid: {"owner","k_serv","action_kind"(journey kind),"hub","swap_start","journey_digest"}} — the anchor for journey_validate,
        taken from the commit records (never from the journeys)."""
        out = {}
        for r in self.committed:
            out[int(r["oid"])] = {"owner": int(r["owner"]), "k_serv": int(r["k_serv"]), "action_kind": J.DIRECT_ORDER if r["action_kind"] == L2.DIRECT_SERVE else J.RECHARGE_THEN_ORDER,
                                  "hub": r.get("hub"), "swap_start": r.get("swap_start"), "journey_digest": r.get("journey_digest")}
        return out

    def journey_list(self):
        return [self.journeys[o] for o in sorted(self.journeys)]


def replay_from_journeys(fx, auth, journeys, committed=None, identity=None):
    """Incremental/prefix replay from journeys only: returns (states, events, ledger_digest, validation). `committed`/`identity`
    are the external anchors (ledger commit records / expected identity) — pass them whenever available."""
    val = J.journey_validate(fx, auth, journeys, committed=committed, identity=identity)
    states = {}; events = []
    by = {}
    for j in journeys:
        by.setdefault(int(j["owner"]), []).append(j)
    for i in sorted(by):
        js = sorted(by[i], key=lambda j: (int(fx["orders"][j["order_id"] - 1]["k_p"]), j["order_id"]))
        base = 0
        for j in js:
            ev = J.journey_events(j, auth.authority_digest, idx0=base); events.extend(ev); base += len(ev)
        p = js[-1]["post_state"]; states[i] = {"tail_location": p["tail_location"], "tail_slot": p["tail_slot"], "soc": p["soc"], "payload": 0}
    dg = L2.dig([(e["uav_id"], e["event_index"], e["phase"], e["slot_from"], e["slot_to"], e["station_from"], e["station_to"], e["soc_before"], e["delta_soc"],
                  e["soc_after"], e["payload_before"], e["payload_after"], e["action_kind"], e["hub_id_or_NA"], e["swap_service_slot_or_NA"]) for e in events])
    return states, events, dg, val
