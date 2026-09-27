"""Frozen Resource-Capacity Lottery: claim footprints -> hard-conflict groups -> per-group frozen
uniform draws -> survivors / conditional bans (GO section 6; CD ruling 2026-08-31 R-1).

EFFECTIVE_RESOURCE_LOTTERY_SCHEMA_ID = FROZEN_UNIFORM_CAPACITY_LOTTERY_V2_ROWSCAN

Same-UAV hard conflicts (GO 6.1 "same-UAV overlapping chain/time windows"):
  for each owner, scan its occupied rows; every row with >=2 claimants is an atomic simultaneous
  claimant set; windows with an identical claimant set are ONE group (dedupe by (owner, C=1,
  claimant set) - the same physical incompatibility is drawn once, whether it spans 1 row or 30 and
  whether the rows are contiguous); singletons form no group; a claim may belong to several groups
  (B in {A,B} and {B,C}) and survives only if selected in every group; transitively connected but
  non-conflicting claims (A,C in the bridge case) are NEVER merged into one group.
Other resources (station-time, swap slots) keep GO 6.1 grouping by resource key with the contract's
residual capacity; under the V3R4 contract they are non-binding (n<=C).
Capacity rule (GO 6.2) and RNG keys are unchanged from V1 (rng.ResourceLotteryRegistry).

Counters (review 2026-08-31 m1/M10f): every counter is either DETECTED from the data by the logic
named in COUNTER_DETECTION or declared structurally non-detectable in SCHEMA_NOTES (quoted by the
seal).  Legacy raw definitions are kept under *_RAW keys.
"""
import json
from collections import defaultdict

from .rng import ResourceLotteryRegistry, digest_of

SCHEMA_ID = "FROZEN_UNIFORM_CAPACITY_LOTTERY_V2_ROWSCAN"
FROZEN_DRAW_MODES = ("C_LE_0_ALL_LOSE", "N_LE_C_ALL_SURVIVE", "UNIFORM_WITHOUT_REPLACEMENT")
SAME_UAV_RESOURCE_KIND = "same_uav_window"

COUNTER_DETECTION = {
    "RESOURCE_LOTTERY_GROUP_COUNT": "len(groups) passed to run_lottery",
    "RESOURCE_LOTTERY_OVERSUBSCRIBED_GROUP_COUNT": "groups with n > C (legacy name, identical to OVERSUBSCRIBED_GROUP_COUNT)",
    "OVERSUBSCRIBED_GROUP_COUNT": "groups with n > C",
    "NONBINDING_GROUP_COUNT": "groups with n <= C (every claimant survives that group; zero RNG consumption)",
    "SAME_UAV_GROUP_COUNT": "groups whose resource kind is 'same_uav_window' (row-scan construction)",
    "RESOURCE_LOTTERY_WINNER_COUNT": "claims selected in EVERY group they belong to (survivors)",
    "RESOURCE_LOTTERY_LOSER_COUNT": "claims that lost in >= 1 group",
    "RESOURCE_LOTTERY_CONDITIONAL_BAN_COUNT": "distinct canonical ban targets after dedupe (evidence append-only)",
    "RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT": "claims belonging to >= 2 oversubscribed groups OR >= 2 same-UAV groups",
    "RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT_RAW": "legacy: claims belonging to >= 2 groups of any kind (non-binding included)",
    "RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT": "oversubscribed groups whose survivors_in_group < C (a winner lost in another group)",
    "RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT_RAW": "legacy: any group whose survivors_in_group < min(C, n)",
    "RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT": "(group_fingerprint, claim_universe_digest, C) already in `seen` with the SAME round_id (must stay 0)",
    "RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT": "(group_fingerprint, claim_universe_digest, C) first drawn under a DIFFERENT round_id (diagnostic; needs caller-persisted `seen`)",
    "RESOURCE_LOTTERY_REFILL_COUNT": "survivor that is not a winner of every group it belongs to, or group survivors_in_group > min(C, n) (must stay 0)",
    "RESOURCE_LOTTERY_OWNER_CHANGE_COUNT": "survivor whose (owner_id, owner_slot, raw_u) differs from the input claim of the same canonical key (must stay 0)",
    "RESOURCE_LOTTERY_G_WEIGHTED_COUNT": "draw record mode outside FROZEN_DRAW_MODES (no weights argument exists; see SCHEMA_NOTES)",
    "RESOURCE_LOTTERY_INPUT_PRIORITY_COUNT": "draw record universe != digest of canonically sorted claimant keys (input order leaked into a draw)",
    "RESOURCE_LOTTERY_ALL_BAN_POSITIVE_CAPACITY_COUNT": "group with C > 0 and n > 0 and zero winners",
    "GROUP_PROCESSING_ORDER_EFFECT_COUNT": "draws re-executed over reversed(sorted(groups)) with a fresh same-seed registry; per-group winner-set differences (must stay 0)",
    "FIRST_COME_CAPACITY_SELECTION_COUNT": "structurally non-detectable per draw (coincidence rate 1/C(n,C)); see SCHEMA_NOTES",
    "ASYMMETRIC_CONFLICT_KEEP_COUNT": "oversubscribed group with C > 0 whose draw mode != UNIFORM_WITHOUT_REPLACEMENT or consumed != C, or any C <= 0 group with a winner",
}

SCHEMA_NOTES = {
    "FIRST_COME_CAPACITY_SELECTION_COUNT": ("A keep-first-C selection is indistinguishable from a uniform draw that happens to select the first C "
                                            "canonical claimants (probability 1/C(n,C) per group), so no per-round detector can count it without false "
                                            "positives.  Coverage: (a) rng.capacity_lottery is a partial Fisher-Yates over identity-sorted keys with "
                                            "no keep-first branch, (b) selftest A6 measures the first-C coincidence rate on 300 seeds and requires it to "
                                            "be far below 1 (~C(5,3)^-1 = 0.1), (c) static_audit flags any `claimants[0]` outside a lottery branch."),
    "RESOURCE_LOTTERY_G_WEIGHTED_COUNT": ("run_lottery and ResourceLotteryRegistry.capacity_lottery accept no weight/G argument; a weighted draw is "
                                          "structurally impossible.  The runtime detector counts draw records whose mode is outside FROZEN_DRAW_MODES."),
    "RESOURCE_LOTTERY_INPUT_PRIORITY_COUNT": ("The draw is a function of (RUN_SEED, group_fingerprint, claim_universe_digest, C, j); input order is not an "
                                              "argument.  Runtime detector: the recorded universe must equal the digest of the canonically sorted claimant "
                                              "keys; selftest A8 additionally shuffles claim order, group dict order and reversed group order."),
    "RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT": ("Diagnostic only: the same (group, universe, C) recurring in a later round re-uses the same "
                                                               "frozen key and therefore the same outcome by design.  Detectable only when the caller "
                                                               "persists `seen` across rounds (controller.lottery_seen); with seen=None it is 0 by "
                                                               "construction.  The caller must snapshot/restore `seen` with the round-start checkpoint, "
                                                               "otherwise a redo of an interrupted round is mis-counted as a same-round redraw."),
    "RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT": ("Detected via `seen`: a second draw of the same (group_fingerprint, universe, C) under the same "
                                                    "round_id.  With seen=None a fresh dict is used, so only in-call repeats are detectable."),
    "RESOURCE_LOTTERY_OWNER_CHANGE_COUNT": ("The lottery never constructs claims; survivors are the caller's Claim objects.  The detector compares each "
                                            "survivor's (owner_id, owner_slot, raw_u) with the snapshot taken at entry for the same canonical key."),
}


def ck(k):
    return json.dumps(k, sort_keys=True, separators=(",", ":"), default=str)


class Claim:
    __slots__ = ("fingerprint", "dup_slot", "owner_id", "owner_slot", "raw_u", "k_serv", "journey_digest", "footprint")

    def __init__(self, fingerprint, dup_slot, owner_id, owner_slot, raw_u, k_serv, journey_digest, footprint):
        self.fingerprint = tuple(fingerprint); self.dup_slot = int(dup_slot)
        self.owner_id, self.owner_slot, self.raw_u = owner_id, int(owner_slot), int(raw_u)
        self.k_serv, self.journey_digest = int(k_serv), journey_digest
        self.footprint = [tuple(r) for r in footprint]      # ("row", owner_id, owner_slot, k) / ("station_time", s, k) / ("swap_slot", hub, k)

    def key(self):
        """Canonical physical claimant key: fingerprint + duplicate slot + owner identity/slot + k_serv. Never oid or raw index."""
        return (list(self.fingerprint), self.dup_slot, self.owner_id, self.owner_slot, self.k_serv)

    def rows(self):
        """Occupied rows; every ("row", owner_id, owner_slot, k) entry must carry THIS claim's owner fields
        (review m2: a foreign row in a footprint would silently create or hide a same-UAV conflict)."""
        out = set()
        for r in self.footprint:
            if r[0] != "row":
                continue
            if r[1] != self.owner_id or int(r[2]) != self.owner_slot:
                raise RuntimeError(f"ROW_FOOTPRINT_OWNER_MISMATCH: claim owner ({self.owner_id},{self.owner_slot}) "
                                   f"carries row entry of ({r[1]},{r[2]}) k={r[3]} journey={self.journey_digest}")
            out.add(int(r[3]))
        return out


def _group(resource, C, claims):
    keys = sorted((c.key() for c in claims), key=ck)
    if len(set(map(ck, keys))) != len(keys):
        raise RuntimeError("IDENTICAL_CLAIM_KEYS_IN_GROUP: duplicate-instance slots must separate physically identical claims")
    gf = digest_of({"resource": list(resource), "C": int(C), "claimants": keys})
    return gf, {"resource": list(resource), "C": int(C), "n": len(keys), "claimants": keys, "oversubscribed": len(keys) > int(C)}


def assert_unique_claim_keys(claims):
    """CD R-4(6): physically identical claims must carry distinct duplicate-instance slots; identical
    canonical keys would otherwise fold in sets and silently escape C=1."""
    seen = {}
    for c in claims:
        k = ck(c.key())
        if k in seen:
            raise RuntimeError(f"IDENTICAL_CLAIM_KEYS_IN_GROUP: {k} (journeys {seen[k]} / {c.journey_digest})")
        seen[k] = c.journey_digest


def same_uav_window_groups(claims):
    """Row-scan construction of same-UAV hard-conflict groups (see module docstring)."""
    assert_unique_claim_keys(claims)
    by_owner = defaultdict(list)
    rows_of = {}
    for c in claims:
        rows_of[ck(c.key())] = c.rows()          # validates every footprint row owner (also singletons: a foreign row hides a conflict)
        by_owner[(c.owner_id, c.owner_slot)].append(c)
    groups = {}
    for owner, items in sorted(by_owner.items(), key=lambda kv: ck(list(kv[0]))):
        if len(items) < 2:
            continue
        row_sets = defaultdict(set)
        by_key = {}
        for c in items:
            k = ck(c.key()); by_key[k] = c
            for r in rows_of[k]:
                row_sets[r].add(k)
        seen = {}
        for r in sorted(row_sets):
            S = row_sets[r]
            if len(S) < 2:
                continue                                     # singleton row: no conflict
            seen.setdefault(tuple(sorted(S)), []).append(r)  # identical claimant set -> one physical conflict
        for sk, rows in seen.items():
            window = [min(rows), max(rows), len(rows)]
            gf, g = _group([SAME_UAV_RESOURCE_KIND, owner[0], owner[1], *window], 1, [by_key[k] for k in sk])
            g["rows"] = sorted(rows)
            groups[gf] = g
    return groups


def resource_groups(claims, residual_capacity):
    """Non-UAV resources keyed by footprint resource key (station-time, swap slots); rows are handled
    by same_uav_window_groups.  Identical (resource, C, claimant set) are one group by construction."""
    members = defaultdict(list)
    for c in claims:
        for r in dict.fromkeys(c.footprint):
            if r[0] == "row":
                continue
            members[r].append(c)
    groups = {}
    for r, cs in sorted(members.items(), key=lambda kv: ck(list(kv[0]))):
        gf, g = _group(r, residual_capacity(r), cs)
        groups[gf] = g
    return groups


def build_all_groups(claims, residual_capacity):
    assert_unique_claim_keys(claims)
    g = resource_groups(claims, residual_capacity)
    g.update(same_uav_window_groups(claims))
    return g


def _canonical_universe(claimants):
    return digest_of(sorted(ck(k) for k in claimants))


def run_lottery(claims, groups, registry: ResourceLotteryRegistry, round_id, seen=None):
    """Frozen independent draw per group; survivor = selected in EVERY group it belongs to.
    Returns survivors, losers, canonical-deduped bans (target + append-only evidence) and counters.
    Processing order cannot matter: every draw depends only on (group fingerprint, universe, C).
    `seen` (optional, caller-persisted across rounds): dict (group_fingerprint, universe, C) -> round_id
    of the first draw; drives the SAME_UNIVERSE_REDRAW / CROSS_ROUND_UNIVERSE_RECURRENCE detectors."""
    counters = {k: 0 for k in COUNTER_DETECTION}
    counters["RESOURCE_LOTTERY_GROUP_COUNT"] = len(groups)
    if seen is None:
        seen = {}
    entry_owner = {ck(c.key()): (c.owner_id, c.owner_slot, c.raw_u) for c in claims}
    membership = defaultdict(set); lost_in = defaultdict(list); draws = {}; winners_by_group = {}
    over_groups, uav_groups = set(), set()
    for gf in sorted(groups):
        g = groups[gf]
        C, n = int(g["C"]), int(g["n"])
        winners, losers, rec = registry.capacity_lottery(gf, g["claimants"], C)
        draws[gf] = rec; winners_by_group[gf] = set(winners)
        ukey = (gf, rec.get("universe"), C)
        if ukey in seen:
            if seen[ukey] == round_id:
                counters["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] += 1
            else:
                counters["RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT"] += 1
        else:
            seen[ukey] = round_id
        over = n > C
        if over:
            over_groups.add(gf)
            counters["RESOURCE_LOTTERY_OVERSUBSCRIBED_GROUP_COUNT"] += 1; counters["OVERSUBSCRIBED_GROUP_COUNT"] += 1
        else:
            counters["NONBINDING_GROUP_COUNT"] += 1
        if g["resource"][0] == SAME_UAV_RESOURCE_KIND:
            uav_groups.add(gf); counters["SAME_UAV_GROUP_COUNT"] += 1
        if C > 0 and n > 0 and not winners:
            counters["RESOURCE_LOTTERY_ALL_BAN_POSITIVE_CAPACITY_COUNT"] += 1
        if C > 0 and len(winners) != min(C, n):
            raise RuntimeError(f"CAPACITY_RULE_VIOLATION group {gf[:12]}: C={C} n={n} winners={len(winners)}")
        if rec.get("universe") != _canonical_universe(g["claimants"]):
            counters["RESOURCE_LOTTERY_INPUT_PRIORITY_COUNT"] += 1
        mode = rec.get("mode")
        if mode not in FROZEN_DRAW_MODES:
            counters["RESOURCE_LOTTERY_G_WEIGHTED_COUNT"] += 1
        if over and C > 0 and (mode != "UNIFORM_WITHOUT_REPLACEMENT" or int(rec.get("consumed", -1)) != C):
            counters["ASYMMETRIC_CONFLICT_KEEP_COUNT"] += 1
        if C <= 0 and winners:
            counters["ASYMMETRIC_CONFLICT_KEEP_COUNT"] += 1
        for k in g["claimants"]:
            membership[ck(k)].add(gf)
        for k in losers:
            lost_in[k].append(gf)
    survivors, losers_all, bans = [], [], []
    for c in claims:
        k = ck(c.key())
        m = membership[k]
        if len(m) > 1:
            counters["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT_RAW"] += 1
        if len(m & over_groups) >= 2 or len(m & uav_groups) >= 2:
            counters["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT"] += 1
        if lost_in[k]:
            losers_all.append(c)
            for gf in lost_in[k]:
                g = groups[gf]
                bans.append({"BAN_TARGET_KEY": [list(c.fingerprint), c.dup_slot, [c.owner_id, c.owner_slot], c.k_serv],
                             "BAN_EVIDENCE_RECORDS": [{"reason_class": "RESOURCE_LOTTERY_CONDITIONAL_BAN", "source_round": round_id,
                                                       "source_proposal_digest": c.journey_digest, "source_resource_group_digest": gf,
                                                       "capacity_C": g["C"], "claimant_count_n": g["n"], "resource_lottery_draw_digest": draws[gf].get("winner_digest")}]})
        else:
            survivors.append(c)
    counters["RESOURCE_LOTTERY_WINNER_COUNT"] = len(survivors); counters["RESOURCE_LOTTERY_LOSER_COUNT"] = len(losers_all)
    surv_keys = {ck(c.key()) for c in survivors}
    for gf, g in groups.items():
        C, n = int(g["C"]), int(g["n"])
        in_group = sum(1 for k in g["claimants"] if ck(k) in surv_keys)
        if in_group < min(C, n):
            counters["RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT_RAW"] += 1
        if n > C and in_group < C:
            counters["RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT"] += 1
        if in_group > min(C, n):
            counters["RESOURCE_LOTTERY_REFILL_COUNT"] += 1
    for c in survivors:
        k = ck(c.key())
        if any(k not in winners_by_group[gf] for gf in membership[k]):
            counters["RESOURCE_LOTTERY_REFILL_COUNT"] += 1
        if entry_owner.get(k) != (c.owner_id, c.owner_slot, c.raw_u):
            counters["RESOURCE_LOTTERY_OWNER_CHANGE_COUNT"] += 1
    # group processing order: re-draw in reversed order with a throwaway same-seed registry (stateless keys)
    shadow = ResourceLotteryRegistry(registry.run_seed)
    for gf in reversed(sorted(groups)):
        w2, _l2, _r2 = shadow.capacity_lottery(gf, groups[gf]["claimants"], groups[gf]["C"])
        if set(w2) != winners_by_group[gf]:
            counters["GROUP_PROCESSING_ORDER_EFFECT_COUNT"] += 1
    merged = {}
    for b in bans:
        t = ck(b["BAN_TARGET_KEY"])
        merged.setdefault(t, {"BAN_TARGET_KEY": b["BAN_TARGET_KEY"], "BAN_EVIDENCE_RECORDS": []})["BAN_EVIDENCE_RECORDS"] += b["BAN_EVIDENCE_RECORDS"]
    counters["RESOURCE_LOTTERY_CONDITIONAL_BAN_COUNT"] = len(merged)
    return {"survivors": survivors, "losers": losers_all, "bans": list(merged.values()), "draws": draws, "counters": counters,
            "schema": SCHEMA_ID, "seen_entries": len(seen)}


# ----------------------------------------------------------------------------- explicit checks (no assert)
def _check(cond, msg):
    if not cond:
        raise RuntimeError("RESOURCE_LOTTERY_TEST_FAIL: " + msg)


def _mk(i, u, k, rows, fp=None, slot=0):
    return Claim(fp or (10, 1, 20, 2 + i), slot, f"id{u}", 0, u, k, f"j{i}", [("station_time", 5, k)] + [("row", f"id{u}", 0, r) for r in rows])


def _survivor_ids(out):
    return sorted(c.journey_digest for c in out["survivors"])


def _draw_records(out):
    return {gf: (d.get("winner_digest"), d.get("mode"), d.get("universe"), d.get("consumed")) for gf, d in out["draws"].items()}


def _compare_draws_one_by_one(ref, other, tag):
    _check(sorted(ref) == sorted(other), f"{tag}: group fingerprint sets differ")
    for gf in sorted(ref):
        _check(ref[gf] == other[gf], f"{tag}: draw record differs for group {gf[:12]}: {ref[gf]} vs {other[gf]}")


def _expect_raise(fn, needle, msg):
    try:
        fn()
    except RuntimeError as e:
        if needle in str(e):
            return str(e)
        raise RuntimeError(f"RESOURCE_LOTTERY_TEST_FAIL: {msg}: wrong error {e}")
    raise RuntimeError(f"RESOURCE_LOTTERY_TEST_FAIL: {msg}: no exception")


def _selftest():
    import random
    nb = lambda r: 10**6                                   # non-binding station-time (V3R4)
    cap3 = lambda r: 3
    R = {}
    # A1 bridge: A{1,2} B{2,3} C{3,4}: groups {A,B},{B,C}; A and C may co-survive; B never survives together with A or C
    A, B, C = _mk(0, 7, 5, (1, 2)), _mk(1, 7, 6, (2, 3)), _mk(2, 7, 7, (3, 4))
    g = same_uav_window_groups([A, B, C]); _check(len(g) == 2 and all(v["n"] == 2 for v in g.values()), f"bridge groups {len(g)}")
    both_ac = 0
    for s in range(200):
        o = run_lottery([A, B, C], build_all_groups([A, B, C], nb), ResourceLotteryRegistry(s), 1)
        ids = _survivor_ids(o); _check(not ("j1" in ids and len(ids) > 1), "B survived together with A or C")
        both_ac += ids == ["j0", "j2"]
    _check(both_ac > 0, "A and C never co-survived across 200 seeds")
    R["A1"] = {"groups": 2, "bridge_AC_cosurvive_seeds_of_200": both_ac, "PASS": True}
    # A2 full clique: all three share row 2 -> one group n=3, exactly one survivor
    A2, B2, C2 = _mk(0, 8, 5, (1, 2)), _mk(1, 8, 6, (2,)), _mk(2, 8, 7, (2, 3))
    g = same_uav_window_groups([A2, B2, C2]); _check(len(g) == 1 and list(g.values())[0]["n"] == 3, "clique group")
    o = run_lottery([A2, B2, C2], build_all_groups([A2, B2, C2], nb), ResourceLotteryRegistry(0), 1); _check(len(o["survivors"]) == 1, "clique survivors")
    R["A2"] = {"groups": 1, "n": 3, "survivors": 1, "PASS": True}
    # A3 repeated rows: same pair over 20 rows -> one group, one draw
    A3, B3 = _mk(0, 9, 5, tuple(range(40, 60))), _mk(1, 9, 6, tuple(range(40, 60)))
    g = same_uav_window_groups([A3, B3]); _check(len(g) == 1 and list(g.values())[0]["rows"] == list(range(40, 60)), "repeated rows merged")
    reg = ResourceLotteryRegistry(0); run_lottery([A3, B3], build_all_groups([A3, B3], nb), reg, 1); _check(reg.counters["RESOURCE_LOTTERY"] == 1, f"draws {reg.counters['RESOURCE_LOTTERY']} != 1")
    # A3b non-contiguous windows with the same claimant set are the same physical conflict -> one group
    A3b, B3b = _mk(0, 9, 5, (5, 9)), _mk(1, 9, 6, (5, 9)); _check(len(same_uav_window_groups([A3b, B3b])) == 1, "non-contiguous identical set not deduped")
    R["A3"] = {"rows_merged": 20, "rng_draws": 1, "non_contiguous_deduped": True, "PASS": True}
    # A4 disjoint windows: no group, all survive
    D = [_mk(i, 3, 10 + i, (i * 3, i * 3 + 1)) for i in range(5)]
    _check(not same_uav_window_groups(D), "disjoint made groups"); _check(len(run_lottery(D, build_all_groups(D, nb), ResourceLotteryRegistry(0), 1)["survivors"]) == 5, "disjoint survivors")
    R["A4"] = {"groups": 0, "survivors": 5, "PASS": True}
    # A5 multi-group membership counters (new definition + legacy RAW) and group-kind counters
    o = run_lottery([A, B, C], build_all_groups([A, B, C], nb), ResourceLotteryRegistry(0), 1)
    c5 = o["counters"]
    _check(c5["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT_RAW"] == 3, "RAW: each of A,B,C belongs to its station-time group plus >=1 same-UAV group")
    _check(c5["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT"] == 1, f"only B belongs to two oversubscribed/same-UAV groups, got {c5['RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT']}")
    _check(c5["SAME_UAV_GROUP_COUNT"] == 2 and c5["OVERSUBSCRIBED_GROUP_COUNT"] == 2 and c5["RESOURCE_LOTTERY_OVERSUBSCRIBED_GROUP_COUNT"] == 2, "same-UAV/oversubscribed counters")
    _check(c5["NONBINDING_GROUP_COUNT"] == 3 and c5["RESOURCE_LOTTERY_GROUP_COUNT"] == 5, f"non-binding station-time groups {c5['NONBINDING_GROUP_COUNT']} total {c5['RESOURCE_LOTTERY_GROUP_COUNT']}")
    gB = [g for g in same_uav_window_groups([A, B, C]).values()]; _check(sum(any(k[0] == list(B.fingerprint) for k in g["claimants"]) for g in gB) == 2, "B must be in exactly the two same-UAV groups")
    R["A5"] = {"overlap": c5["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT"], "overlap_raw": c5["RESOURCE_LOTTERY_OVERLAP_PROPOSAL_COUNT_RAW"], "same_uav_groups": 2, "nonbinding_groups": 3, "PASS": True}
    # A6 binding station capacity C=3 n=5 -> exactly 3 winners, no refill, not structurally the first 3
    E = [_mk(i, 20 + i, 7, ()) for i in range(5)]
    o = run_lottery(E, build_all_groups(E, cap3), ResourceLotteryRegistry(0), 1); _check(len(o["survivors"]) == 3 and o["counters"]["RESOURCE_LOTTERY_REFILL_COUNT"] == 0, "C=3 n=5")
    _check(o["counters"]["RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT"] == 0 and o["counters"]["ASYMMETRIC_CONFLICT_KEEP_COUNT"] == 0, "C=3 n=5 detectors")
    firsts = 0
    for s in range(300):
        Es = [_mk(i, 20 + i, 7, (), fp=(s, 1, 2, i)) for i in range(5)]
        firsts += {c.raw_u for c in run_lottery(Es, build_all_groups(Es, cap3), ResourceLotteryRegistry(0), s)["survivors"]} == {20, 21, 22}
    _check(0 < firsts < 100, f"first-3 coincidences {firsts}/300 (expected ~30)")
    R["A6"] = {"survivors": 3, "first3_coincidences_300": firsts, "PASS": True}
    # A7 same-universe redraw detection stays 0 in one call; C=0 all lose without RNG; n<=C all survive
    reg = ResourceLotteryRegistry(0); o0 = run_lottery(E, build_all_groups(E, lambda r: 0), reg, 1); _check(not o0["survivors"] and reg.counters["RESOURCE_LOTTERY"] == 0, "C=0")
    _check(o0["counters"]["ASYMMETRIC_CONFLICT_KEEP_COUNT"] == 0 and o0["counters"]["RESOURCE_LOTTERY_ALL_BAN_POSITIVE_CAPACITY_COUNT"] == 0, "C=0 is not an all-ban-positive-capacity event")
    o9 = run_lottery(E, build_all_groups(E, lambda r: 9), ResourceLotteryRegistry(0), 1); _check(len(o9["survivors"]) == 5, "n<=C")
    _check(o9["counters"]["NONBINDING_GROUP_COUNT"] == 1 and o9["counters"]["OVERSUBSCRIBED_GROUP_COUNT"] == 0, "n<=C counters")
    _check(o["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] == 0, "redraw counter")
    # A7b `seen` persistence: same round repeat -> SAME_UNIVERSE_REDRAW per group; other round -> CROSS_ROUND recurrence
    seen = {}
    gsE = build_all_groups(E, cap3)
    o1 = run_lottery(E, gsE, ResourceLotteryRegistry(0), 1, seen=seen)
    _check(o1["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] == 0 and o1["seen_entries"] == len(gsE), "first draw must populate seen")
    o1b = run_lottery(E, gsE, ResourceLotteryRegistry(0), 1, seen=seen)
    _check(o1b["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] == len(gsE), "same-round redraw not detected")
    o2 = run_lottery(E, gsE, ResourceLotteryRegistry(0), 2, seen=seen)
    _check(o2["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] == 0 and o2["counters"]["RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT"] == len(gsE), "cross-round recurrence not detected")
    _check(_survivor_ids(o2) == _survivor_ids(o1), "same universe in a later round must reproduce the frozen draw")
    o3 = run_lottery(E, gsE, ResourceLotteryRegistry(0), 2)
    _check(o3["counters"]["RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT"] == 0 and o3["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"] == 0, "seen=None must be a fresh dict")
    R["A7"] = {"C0_survivors": 0, "C0_rng": 0, "n_le_C_survivors": 5, "seen_same_round_redraws": o1b["counters"]["RESOURCE_LOTTERY_SAME_UNIVERSE_REDRAW_COUNT"],
               "seen_cross_round_recurrences": o2["counters"]["RESOURCE_LOTTERY_CROSS_ROUND_UNIVERSE_RECURRENCE_COUNT"], "PASS": True}
    # A8 group-order / claimant input-order / dict-order invariance (per-group draw records compared one by one), relabels
    base = [A, B, C] + E
    ref_groups = build_all_groups(base, cap3)
    ref_out = run_lottery(base, ref_groups, ResourceLotteryRegistry(0), 1)
    ref = _survivor_ids(ref_out); ref_draws = _draw_records(ref_out)
    _check(ref_out["counters"]["GROUP_PROCESSING_ORDER_EFFECT_COUNT"] == 0 and ref_out["counters"]["RESOURCE_LOTTERY_INPUT_PRIORITY_COUNT"] == 0, "order-effect detectors on reference")
    permuted = 0
    for s in range(5):
        sh = list(base); random.Random(s).shuffle(sh)
        gs = build_all_groups(sh, cap3)
        items = list(gs.items()); random.Random(1000 + s).shuffle(items); gs = dict(items)
        permuted += list(gs) != list(ref_groups)
        o = run_lottery(sh, gs, ResourceLotteryRegistry(0), 1)
        _check(_survivor_ids(o) == ref, f"order shuffle {s} changed survivors")
        _compare_draws_one_by_one(ref_draws, _draw_records(o), f"shuffle seed {s}")
        _check(o["counters"] == ref_out["counters"], f"shuffle seed {s} changed counters")
    _check(permuted >= 1, "dict order not actually permuted")
    gs_rev = dict(reversed(list(ref_groups.items()))); _check(list(gs_rev) != list(ref_groups), "reversed dict order identical to reference")
    o_rev = run_lottery(list(reversed(base)), gs_rev, ResourceLotteryRegistry(0), 1)
    _check(_survivor_ids(o_rev) == ref, "reversed order changed survivors"); _compare_draws_one_by_one(ref_draws, _draw_records(o_rev), "reversed order")
    # A8b LABEL relabel: bijective permutation of raw_u values + bijective rename of journey digests (neither is a key input) -> exact invariance
    raw_vals = sorted({c.raw_u for c in base}); rperm = list(raw_vals); random.Random(3).shuffle(rperm); rmap = dict(zip(raw_vals, rperm))
    jmap = {c.journey_digest: f"J{idx:02d}" for idx, c in enumerate(reversed(base))}; jinv = {v: k for k, v in jmap.items()}
    rl = [Claim(c.fingerprint, c.dup_slot, c.owner_id, c.owner_slot, rmap[c.raw_u], c.k_serv, jmap[c.journey_digest], c.footprint) for c in base]
    _check(rmap != {v: v for v in raw_vals}, "raw_u permutation is the identity")
    o_rl = run_lottery(rl, build_all_groups(rl, cap3), ResourceLotteryRegistry(0), 1)
    _check(sorted(jinv[c.journey_digest] for c in o_rl["survivors"]) == ref, "raw UAV index / journey label relabel changed survivors")
    _compare_draws_one_by_one(ref_draws, _draw_records(o_rl), "raw_u relabel")
    # A8c IDENTITY relabel (review m21): bijective rename of owner identity strings + footprint row owner fields, consistently.
    #     Group STRUCTURE must be identical after inverse mapping; the survivor multiset is reported, not asserted:
    #     owner identity is a physical RNG-key input (GO 6.2 frozen per-universe draw), so exact survivor invariance under
    #     renaming the identity itself is not a schema property.
    ids = sorted({c.owner_id for c in base}); new_ids = [f"phys-{i:03d}" for i in range(len(ids))]; random.Random(5).shuffle(new_ids)
    imap = dict(zip(ids, new_ids)); iinv = {v: k for k, v in imap.items()}

    def rename(c):
        fp = [("row", imap[r[1]], r[2], r[3]) if r[0] == "row" else r for r in c.footprint]
        return Claim(c.fingerprint, c.dup_slot, imap[c.owner_id], c.owner_slot, c.raw_u, c.k_serv, c.journey_digest, fp)

    def structure(groups, inv):
        rows = []
        for g in groups.values():
            res = list(g["resource"])
            if res[0] == SAME_UAV_RESOURCE_KIND:
                res[1] = inv.get(res[1], res[1])
            rows.append(ck([res, g["C"], g["n"], sorted(ck([k[0], k[1], inv.get(k[2], k[2]), k[3], k[4]]) for k in g["claimants"]), g.get("rows")]))
        return sorted(rows)
    rn = [rename(c) for c in base]; gs_rn = build_all_groups(rn, cap3)
    _check(structure(gs_rn, iinv) == structure(ref_groups, {}), "identity rename changed the inverse-mapped group structure")
    _check(set(gs_rn) != set(ref_groups), "identity rename must change group fingerprints (identity is a key input)")
    ident_equal_seeds = 0
    for s in range(50):
        oa = run_lottery(base, ref_groups, ResourceLotteryRegistry(s), 1); ob = run_lottery(rn, gs_rn, ResourceLotteryRegistry(s), 1)
        _check(ob["counters"]["RESOURCE_LOTTERY_GROUP_COUNT"] == oa["counters"]["RESOURCE_LOTTERY_GROUP_COUNT"]
               and ob["counters"]["OVERSUBSCRIBED_GROUP_COUNT"] == oa["counters"]["OVERSUBSCRIBED_GROUP_COUNT"]
               and ob["counters"]["SAME_UAV_GROUP_COUNT"] == oa["counters"]["SAME_UAV_GROUP_COUNT"], f"identity rename changed group counters (seed {s})")
        ma = sorted(ck([list(c.fingerprint), c.dup_slot, c.owner_id, c.owner_slot, c.k_serv]) for c in oa["survivors"])
        mb = sorted(ck([list(c.fingerprint), c.dup_slot, iinv[c.owner_id], c.owner_slot, c.k_serv]) for c in ob["survivors"])
        ident_equal_seeds += ma == mb
    R["A8"] = {"dict_order_permuted_seeds_of_5": permuted, "reversed_order_equal": True, "raw_u_journey_relabel_equal": True,
               "identity_rename_structure_equal": True, "identity_rename_group_fingerprints_changed": True,
               "identity_rename_inverse_mapped_survivor_multiset_equal_seeds_of_50": ident_equal_seeds,
               "identity_rename_note": "NOT an invariant of the schema: owner identity is a frozen RNG-key input; structure is invariant, draws are not",
               "PASS": True}
    # A9 identical claim keys (duplicate physical request without slots) are rejected; with slots they form a C=1 group
    X0, X1 = _mk(0, 30, 5, (1,), fp=(1, 1, 2, 3)), _mk(1, 30, 5, (1,), fp=(1, 1, 2, 3))
    _expect_raise(lambda: same_uav_window_groups([X0, X1]), "IDENTICAL_CLAIM_KEYS", "identical keys not rejected")
    X1s = _mk(1, 30, 5, (1,), fp=(1, 1, 2, 3), slot=1)
    _check(len(run_lottery([X0, X1s], build_all_groups([X0, X1s], nb), ResourceLotteryRegistry(0), 1)["survivors"]) == 1, "dup slots C=1")
    # A9b footprint owner mismatch (review m2): a row entry of another owner in a claim's footprint is rejected
    bad = Claim((10, 1, 20, 9), 0, "idA", 0, 1, 5, "jbad", [("row", "idA", 0, 3), ("row", "idB", 0, 4)])
    _expect_raise(bad.rows, "ROW_FOOTPRINT_OWNER_MISMATCH", "foreign owner row accepted")
    bad_slot = Claim((10, 1, 20, 9), 0, "idA", 0, 1, 5, "jbad2", [("row", "idA", 1, 3)])
    _expect_raise(bad_slot.rows, "ROW_FOOTPRINT_OWNER_MISMATCH", "foreign owner slot row accepted")
    okc = Claim((10, 1, 20, 9), 0, "idA", 0, 1, 5, "jok", [("row", "idA", 0, 3), ("station_time", 5, 5)])
    _check(okc.rows() == {3}, "own rows")
    _expect_raise(lambda: same_uav_window_groups([bad, _mk(5, 99, 5, (3,))]), "ROW_FOOTPRINT_OWNER_MISMATCH", "grouping accepted a foreign row")
    R["A9"] = {"identical_keys_rejected": True, "dup_slot_C1_survivors": 1, "row_owner_mismatch_rejected": True, "PASS": True}
    # A10 nested claimant sets: {A,B} on row 1 is a strict subset of {A,B,C} on row 2 -> two C=1 groups; at most one survivor;
    #     the empty-survivor outcome (group1 and group2 pick different members of {A,B}) is a real outcome (reference number)
    An, Bn, Cn = _mk(0, 40, 5, (1, 2)), _mk(1, 40, 6, (1, 2)), _mk(2, 40, 7, (2,))
    gn = same_uav_window_groups([An, Bn, Cn])
    _check(len(gn) == 2 and sorted(v["n"] for v in gn.values()) == [2, 3] and all(v["C"] == 1 for v in gn.values()), f"nested groups {[(v['n'], v['C']) for v in gn.values()]}")
    empty = 0; underfill = 0
    for s in range(300):
        o = run_lottery([An, Bn, Cn], build_all_groups([An, Bn, Cn], nb), ResourceLotteryRegistry(s), 1)
        _check(len(o["survivors"]) <= 1, "nested: more than one survivor")
        _check(o["counters"]["RESOURCE_LOTTERY_ALL_BAN_POSITIVE_CAPACITY_COUNT"] == 0, "nested: every group has a winner")
        empty += not o["survivors"]; underfill += o["counters"]["RESOURCE_LOTTERY_UNDERFILL_GROUP_COUNT"]
    _check(0 < empty < 300, f"nested empty-survivor outcomes {empty}/300 (expected ~100)")
    R["A10"] = {"groups": 2, "group_sizes": [2, 3], "empty_survivor_fraction_300": round(empty / 300, 4), "expected_fraction": round(1 / 3, 4),
                "underfill_group_events_300": underfill, "PASS": True}
    # A11 same owner_id, different owner_slot, same row -> distinct physical UAV instances: 0 same-UAV groups, both survive
    P = Claim((10, 1, 20, 2), 0, "idZ", 0, 50, 5, "jp", [("row", "idZ", 0, 3), ("station_time", 5, 5)])
    Qc = Claim((10, 1, 20, 3), 0, "idZ", 1, 51, 6, "jq", [("row", "idZ", 1, 3), ("station_time", 5, 6)])
    _check(not same_uav_window_groups([P, Qc]), "different owner slots grouped")
    o = run_lottery([P, Qc], build_all_groups([P, Qc], nb), ResourceLotteryRegistry(0), 1)
    _check(len(o["survivors"]) == 2 and o["counters"]["SAME_UAV_GROUP_COUNT"] == 0, "same identity/different slot must both survive")
    R["A11"] = {"same_uav_groups": 0, "survivors": 2, "PASS": True}
    # A12 zero-row claims of the same owner -> 0 same-UAV groups, both survive
    Z0, Z1 = _mk(0, 60, 5, ()), _mk(1, 60, 6, ())
    _check(not same_uav_window_groups([Z0, Z1]), "zero-row claims grouped")
    o = run_lottery([Z0, Z1], build_all_groups([Z0, Z1], nb), ResourceLotteryRegistry(0), 1)
    _check(len(o["survivors"]) == 2 and o["counters"]["SAME_UAV_GROUP_COUNT"] == 0, "zero-row same owner must both survive")
    R["A12"] = {"same_uav_groups": 0, "survivors": 2, "PASS": True}
    # schema exports
    _check(set(COUNTER_DETECTION) == set(ref_out["counters"]), "COUNTER_DETECTION must describe exactly the exported counters")
    _check(all(k in COUNTER_DETECTION for k in SCHEMA_NOTES), "SCHEMA_NOTES keys must be counters")
    R["schema"] = {"SCHEMA_ID": SCHEMA_ID, "counters": sorted(COUNTER_DETECTION), "schema_notes": sorted(SCHEMA_NOTES), "PASS": True}
    R["PASS"] = all(v.get("PASS") is True for v in R.values() if isinstance(v, dict))
    print("resource_lottery V2 selftest OK", {k: {kk: vv for kk, vv in v.items() if kk not in ("PASS", "identity_rename_note")}
                                              for k, v in R.items() if isinstance(v, dict) and k in ("A1", "A5", "A6", "A8", "A10")})
    return R


if __name__ == "__main__":
    _selftest()
