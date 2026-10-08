"""Four independent hash-counter RNG streams and the frozen uniform resource-capacity lottery
(E2 plan section 2.2; GO 308-313, 473-475, 547-565; CD ruling Q4).

Streams (namespaces):
  OWNER_COMMON_VARIATE   key = (RUN_SEED, request_fingerprint, candidate_universe_digest, dup_slot)
  SERVICE_TUPLE          key = (RUN_SEED, fingerprint, dup_slot, owner_identity_slot, tuple_universe_digest)
  RESOURCE_LOTTERY       key = (RUN_SEED, group_fingerprint, claim_universe_digest, residual_C, 'draw', j)
  FIELD_INIT             key = (RUN_SEED, ROUND_ID)
No key ever contains a round index (except FIELD_INIT by design), loop counter, dict order, order
id or raw UAV index.  Variates are stateless functions of their key, so resume recomputes them
bitwise and the registry only counts consumption.
"""
import hashlib
import json
import struct

GO_TOKEN = "CW_R3_GLOBAL_MULTIPLE_UPDATE_V3R4_BATCH_HARD_JUDGE_DEVELOP_AND_VALIDATE_V3"
NAMESPACES = ("OWNER_COMMON_VARIATE", "SERVICE_TUPLE_TIE", "SERVICE_TUPLE_UNIFORM",
              "RESOURCE_LOTTERY", "FIELD_INIT")


def _enc(parts):
    """Length-prefixed canonical encoding (rng_registry.py:24-40 style, own token prefix)."""
    h = hashlib.sha256()
    h.update(struct.pack(">I", len(GO_TOKEN)) + GO_TOKEN.encode())
    for p in parts:
        if isinstance(p, (list, tuple)):
            b = json.dumps(list(p), sort_keys=True, separators=(",", ":")).encode()
        elif isinstance(p, (bytes, bytearray)):
            b = bytes(p)
        else:
            b = str(p).encode()
        h.update(struct.pack(">I", len(b)) + b)
    return h.digest()


def variate(ns, *key):
    """Uniform double in [0,1) from 53 bits of sha256(ns || key)."""
    if ns not in NAMESPACES:
        raise KeyError(ns)
    d = _enc((ns,) + key)
    return (int.from_bytes(d[:8], "big") >> 11) / float(1 << 53)


def digest_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# ----------------------------------------------------------------------------- identities
def station_identity(fx, m):
    """Canonical PHYSICAL identity of station m (1-based index): sha256 of its planar coordinates
    (coords_xz_m from the sealed euclidean_geometry.npz, rounded to 1 mm).  Raw station index is NOT
    part of it, so station/hub relabelling leaves every fingerprint, footprint and RNG key unchanged
    (CD ruling R-4: raw c/d/hub index must not decide winners).  Cached per fixture dict."""
    cache = fx.get("_station_canon")
    if cache is None:
        xz = fx.get("station_xz")
        if xz is None:
            raise RuntimeError("STATION_COORDS_MISSING: fixture has no station_xz (needed for canonical station identity)")
        cache = {}
        for i in range(len(xz)):
            cache[i + 1] = digest_of({"xz_mm": [int(round(float(xz[i][0]) * 1000.0)), int(round(float(xz[i][1]) * 1000.0))]})[:24]
        if len(set(cache.values())) != len(cache):
            raise RuntimeError("STATION_IDENTITY_COLLISION: two stations share coordinates")
        fx["_station_canon"] = cache
    return cache[int(m)]


def uav_identity(birth_hub_identity, base_tail):
    """Canonical physical identity of a UAV: (birth hub canonical station identity, base tail
    (tail station canonical identity, k, soc, payload)).  Raw UAV index is NOT part of it, and NEITHER is
    the ban table (review B2: identities must be stable across rounds so that ban targets keyed by owner
    identity stay resolvable; the audited hard-ban digest belongs to candidate_universe_digest only)."""
    return digest_of({"hub": birth_hub_identity, "tail": list(base_tail)})


def assign_slots(identities):
    """identities: dict raw_index -> identity digest.  Returns dict raw_index -> (identity, slot) where equal
    identities get anonymous exchangeable-instance slots 0..m-1 assigned ONCE per run in ascending raw-index order
    (CD ruling 2026-08-31 X4, OPTION_A_PRIME_EXCHANGEABLE_INSTANCE_PROTOCOL).  The slot is run-local per-instance
    bookkeeping: it enters the canonical owner enumeration order, the SERVICE_TUPLE RNG key, the claim key and the
    ban key; it is NOT a physical identity and NOT a relabel invariant; it is never derived from G/g, field rows,
    round-varying state or outcomes, and never re-assigned within a run (checkpoint/resume verify the table)."""
    groups = {}
    out = {}
    for u in sorted(identities):
        ident = identities[u]
        slot = groups.get(ident, 0)
        groups[ident] = slot + 1
        out[u] = (ident, slot)
    return out


def candidate_universe_digest(base_state_digests, hard_ban_digest):
    """Digest of the candidate universe from base/production physical state + audited hard bans.
    Provisional pins are deliberately NOT an input (GO 473/422/388)."""
    return digest_of({"base": sorted(base_state_digests), "bans": hard_ban_digest})


def field_init_seed(run_seed, round_id):
    return int.from_bytes(_enc(("FIELD_INIT", run_seed, round_id))[:8], "big")


# ----------------------------------------------------------------------------- inverse CDF
def inverse_cdf(u, weights):
    """Single draw: index i with cumulative weight crossing u. weights must be non-negative and sum>0."""
    tot = float(sum(weights))
    if tot <= 0:
        raise ValueError("non-positive total weight")
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w / tot
        if u < acc:
            return i
    return len(weights) - 1


# ----------------------------------------------------------------------------- resource lottery
class ResourceLotteryRegistry:
    """Counts consumption per namespace and records every draw digest (RNG_REGISTRY.json)."""

    def __init__(self, run_seed, keep_draws=2000):
        self.run_seed = int(run_seed)
        self.counters = {ns: 0 for ns in NAMESPACES}
        self.draws = []                      # rolling tail of draw records (audit sample); the full history is the chain digest
        self.keep_draws = int(keep_draws)
        self.draw_count = 0
        self.chain = "0" * 64                # sha256 chain over every draw record in consumption order (review z6)

    def _record(self, rec):
        self.chain = hashlib.sha256((self.chain + digest_of(rec)).encode()).hexdigest()
        self.draw_count += 1
        self.draws.append(rec)
        if len(self.draws) > self.keep_draws:
            del self.draws[: len(self.draws) - self.keep_draws]

    def owner_variate(self, fingerprint, universe_digest, dup_slot):
        self.counters["OWNER_COMMON_VARIATE"] += 1
        u = variate("OWNER_COMMON_VARIATE", self.run_seed, fingerprint, universe_digest, dup_slot)
        self._record({"ns": "OWNER_COMMON_VARIATE", "key": [list(fingerprint), universe_digest, dup_slot], "u": u})
        return u

    def service_tuple_variate(self, kind, fingerprint, dup_slot, owner_identity_slot, tuple_universe_digest):
        ns = "SERVICE_TUPLE_TIE" if kind == "tie" else "SERVICE_TUPLE_UNIFORM"
        self.counters[ns] += 1
        u = variate(ns, self.run_seed, fingerprint, dup_slot, owner_identity_slot, tuple_universe_digest)
        self._record({"ns": ns, "key": [list(fingerprint), dup_slot, list(owner_identity_slot), tuple_universe_digest], "u": u})
        return u

    def state(self):
        return {"counters": dict(self.counters), "draw_count": self.draw_count, "chain": self.chain, "draws_tail": list(self.draws)}

    def load_state(self, st):
        self.counters = dict(st["counters"]); self.draw_count = int(st["draw_count"]); self.chain = st["chain"]; self.draws = list(st.get("draws_tail", []))

    def capacity_lottery(self, group_fingerprint, claimants, residual_C):
        """Frozen uniform RESOURCE_CAPACITY_LOTTERY (GO 547-565).
        claimants: list of hashable canonical claim keys (identity+slot based, no raw index).
        Returns (winners:set, losers:set, record).  Same (seed, universe, C) -> same sample.
        0 < C < n : uniform sample of exactly C without replacement (deterministic Fisher-Yates
                    partial shuffle over identity-sorted claimants; draw j keyed by ('draw', j));
        C <= 0    : all lose, zero RNG consumption;
        n <= C    : all survive, zero RNG consumption.
        Never keep-first-C, never refill, never second draw, never G-weighted."""
        n = len(claimants)
        ck = lambda c: json.dumps(c, sort_keys=True, separators=(",", ":"), default=str)
        order = sorted((ck(c) for c in claimants))          # canonical strings (hashable, label-free)
        universe = digest_of(order)
        C = int(residual_C)
        rec = {"ns": "RESOURCE_LOTTERY", "group": group_fingerprint, "universe": universe, "n": n, "C": C}
        if C <= 0:
            rec["mode"] = "C_LE_0_ALL_LOSE"; rec["consumed"] = 0
            self._record(rec)
            return set(), set(order), rec
        if n <= C:
            rec["mode"] = "N_LE_C_ALL_SURVIVE"; rec["consumed"] = 0
            self._record(rec)
            return set(order), set(), rec
        arr = list(order)
        for j in range(C):
            r = variate("RESOURCE_LOTTERY", self.run_seed, group_fingerprint, universe, C, "draw", j)
            idx = j + int(r * (n - j))
            arr[j], arr[idx] = arr[idx], arr[j]
        self.counters["RESOURCE_LOTTERY"] += C
        winners = set(arr[:C]); losers = set(order) - winners
        rec["mode"] = "UNIFORM_WITHOUT_REPLACEMENT"; rec["consumed"] = C
        rec["winner_digest"] = digest_of(sorted(winners))
        self._record(rec)
        return winners, losers, rec

    def registry(self):
        return {"GO_TOKEN": GO_TOKEN, "RUN_SEED": self.run_seed, "namespaces": list(NAMESPACES),
                "key_schema": {
                    "OWNER_COMMON_VARIATE": "(RUN_SEED, request_fingerprint, candidate_universe_digest, dup_slot)",
                    "SERVICE_TUPLE_*": "(RUN_SEED, fingerprint, dup_slot, owner_identity_slot, tuple_universe_digest)  [owner_identity_slot=(identity, exchangeable instance label)]",
                    "RESOURCE_LOTTERY": "(RUN_SEED, group_fingerprint, claim_universe_digest, residual_C, 'draw', j)",
                    "FIELD_INIT": "(RUN_SEED, ROUND_ID)"},
                "universe_digest_excludes_provisional_pins": True,
                "counters": dict(self.counters), "draw_count": self.draw_count, "draws_tail_kept": len(self.draws),
                "draws_chain_digest": self.chain}


# ----------------------------------------------------------------------------- self-test
def _check(cond, msg):
    if not cond:
        raise RuntimeError("RNG_SELFTEST_FAIL: " + str(msg))
