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
