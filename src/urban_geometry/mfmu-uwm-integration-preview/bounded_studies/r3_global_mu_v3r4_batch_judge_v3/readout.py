"""Pair-aware joint C/D readout and the frozen owner policy (GO section 5; plan section 2.4).

Frozen representation (READOUT_SEAL): log-domain
    logG_o(u,k) = log x[u,k_pick(o),C_o-1] + log x[u,k,D_o-1],   x<=0 -> -inf
k_pick(o) comes from the sealed order record only.  Ties are exact equalities in this
representation.  Owner policy: QUALIFIED_G_WEIGHTED_SINGLE_DRAW_ELSE_UNIFORM with FORMAL_BETA=4.0
and the TAU_G / TAU_TV formulas below, frozen before any owner outcome is read.
All CDFs are mapped over canonical physical owner order (identity, slot), never raw UAV index.
"""
import math

import numpy as np

FORMAL_BETA = 4.0
EPS64 = np.finfo(np.float64).eps
FORMAL_OWNER_POLICY = "QUALIFIED_G_WEIGHTED_SINGLE_DRAW_ELSE_UNIFORM"
PROV_WEIGHTED = "INNER_G_WEIGHTED_DRAW"
PROV_UNIFORM = "NO_INNER_SIGNAL_UNIFORM_OWNER_LOTTERY"
PROV_SINGLETON = "HARD_SINGLETON"
PROV_NONE = "NO_FEASIBLE_TUPLE"


def k_pick(order):
    return int(order["k_p"])          # K_PICK_SOURCE=SEALED_ORDER_RECORD_ONLY


def _log(v):
    return math.log(v) if v > 0.0 else -math.inf


def logG(x, order, u, k_serv):
    """x: (N,K,M) float64 numpy.  Stations 1-based in the order record."""
    return _log(float(x[u, k_pick(order), int(order["c"]) - 1])) + _log(float(x[u, k_serv, int(order["d"]) - 1]))


def g_vector(x, order, T_o):
    """g_o(u) = max_{k legal for u} logG_o(u,k) over the exact hard tuple universe T_o={(u,k)}.
    Vectorised; identical values to the scalar definition (log of the same float64 factors,
    x<=0 -> -inf; max over the same tuple set)."""
    if not T_o:
        return {}
    U = np.fromiter((t[0] for t in T_o), dtype=np.int64, count=len(T_o))
    Kk = np.fromiter((t[1] for t in T_o), dtype=np.int64, count=len(T_o))
    a = np.asarray(x[U, k_pick(order), int(order["c"]) - 1], dtype=np.float64)
    b = np.asarray(x[U, Kk, int(order["d"]) - 1], dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        la = np.where(a > 0.0, np.log(np.where(a > 0.0, a, 1.0)), -np.inf)
        lb = np.where(b > 0.0, np.log(np.where(b > 0.0, b, 1.0)), -np.inf)
    v = la + lb
    best = {}
    for u, val in zip(U.tolist(), v.tolist()):
        if u not in best or val > best[u]:
            best[u] = val
    return best


def center(v):
    v = np.asarray(v, float)
    return v - v.mean()


def tv(p, q):
    return 0.5 * float(np.abs(np.asarray(p, float) - np.asarray(q, float)).sum())


def p_from_g(g, tau_g):
    g = np.asarray(g, float)
    spread = float(g.max() - g.min())
    z = FORMAL_BETA * (g - g.max()) / max(spread, tau_g)
    e = np.exp(z)
    return e / e.sum(), spread


def qualify(g_repeats, g_perm_inv, g_null, *, physical_response_pass, self_pin_free_pass,
            perm_equivariant_pass):
    """g_repeats: three g vectors (same canonical owner order) from the verification tail
    positions; g_perm_inv: g from the UAV-permuted solve mapped back; g_null: exact-null control.
    Returns the frozen statistics and QUALIFIED_G."""
    G = [np.asarray(v, float) for v in g_repeats]
    n = len(G[0])
    if n < 2:
        return {"QUALIFIED_G": False, "reason": "not multi-owner", "n": n}
    finite = all(np.isfinite(v).all() for v in G) and np.isfinite(np.asarray(g_perm_inv)).all() and np.isfinite(np.asarray(g_null)).all()
    if not finite:
        return {"QUALIFIED_G": False, "reason": "non-finite g (zero factor -> -inf)", "n": n, "finite": False,
                "TV_o": None, "TAU_TV": None, "RAW_G_SPREAD": None, "TAU_G": None}
    d_repeat = max(float(np.abs(center(a) - center(b)).max()) for i, a in enumerate(G) for b in G[i + 1:])
    d_perm = float(np.abs(center(G[0]) - center(g_perm_inv)).max())
    d_null = float(np.abs(center(g_null)).max())
    gmax_abs = float(max(1.0, np.abs(G[0]).max())) if finite else 1.0
    tau_g = max(d_repeat, d_perm, d_null, 16 * EPS64 * gmax_abs)
    P = [p_from_g(v, tau_g)[0] for v in G]
    spread = p_from_g(G[0], tau_g)[1]
    unif = np.full(n, 1.0 / n)
    tv_o = tv(P[0], unif)
    tv_repeat = max(tv(a, b) for i, a in enumerate(P) for b in P[i + 1:])
    tv_perm = tv(P[0], p_from_g(g_perm_inv, tau_g)[0])
    tv_null = tv(p_from_g(g_null, tau_g)[0], unif)
    tau_tv = max(tv_repeat, tv_perm, tv_null, 16 * EPS64)
    observer_tv = tv_repeat
    observer_stable = observer_tv <= tau_tv
    q = bool(finite and spread > tau_g and tv_o > tau_tv and observer_stable and perm_equivariant_pass
             and physical_response_pass and self_pin_free_pass)
    return {"QUALIFIED_G": q, "n": n, "finite": bool(finite), "RAW_G_SPREAD": spread,
            "d_repeat_g": d_repeat, "d_perm_g": d_perm, "d_null_g": d_null, "TAU_G": tau_g,
            "TV_o": tv_o, "tv_repeat": tv_repeat, "tv_perm": tv_perm, "tv_null": tv_null, "TAU_TV": tau_tv,
            "OBSERVER_TV": observer_tv, "OBSERVER_STABLE": bool(observer_stable),
            "p_G": P[0].tolist(), "FORMAL_BETA": FORMAL_BETA}


def qualify_v2(g_x, g8, g14, g20, g_perm_inv, g_null, *, physical_response_pass, self_pin_free_pass):
    """CD ruling 2026-08-31 R-3 (EFFECTIVE_READOUT_SEAL_V2): threshold and observer are separated.
      noise floor      : tail positions 8 and 14 (d_repeat_g, tv_repeat)
      held-out observer: tail position 20 vs the proposal field x  (OBSERVER_TV <= TAU_TV)
      permutation      : inverse-mapped permuted field vs x        (perm-equivariance PASS iff <= TAU_TV, computed
                         from the 8/14 floor and the null control ONLY, i.e. before the perm statistic enters TAU)
      null             : exact-null control g_null (centred drift)
      physical_response_pass: scale-level certificate computed from x vs x_null on demanded cells (controller)
    QUALIFIED_G requires every condition; any failure -> NO_INNER_SIGNAL (uniform fail-closed).  The order's raw
    state is RAW_UNCLOSED_UNSTABLE if the held-out observer is unstable, else READOUT_STABLE (raw closure itself is
    the round-level Inner residual test)."""
    vecs = [np.asarray(v, float) for v in (g_x, g8, g14, g20, g_perm_inv, g_null)]
    n = len(vecs[0])
    base = {"n": n, "FORMAL_BETA": FORMAL_BETA}
    if n < 2:
        return {"QUALIFIED_G": False, "reason": "not multi-owner", "observer_unstable": False, "observer_evaluable": False, "PERM_EQUIVARIANT": None, **base}
    if not all(np.isfinite(v).all() for v in vecs):
        # Y2 ruling: a non-finite joint readout is NOT an observer pass (not evaluable).  Only the explicitly identified
        # zero-factor case (log of an exactly-zero pinned cell -> -inf) is admissible; NaN or +inf means a numerical fault
        # in the solver/mapping and must hard-fail instead of being hidden behind NOT_EVALUABLE (ruling item 7).
        bad = [float(x) for v in vecs for x in np.asarray(v).ravel() if not np.isfinite(x) and not (np.isneginf(x))]
        if bad:
            raise RuntimeError(f"READOUT_NON_FINITE_UNEXPECTED: {bad[:4]} (NaN/+inf in joint readout; zero-factor -inf is the only admissible non-finite value)")
        return {"QUALIFIED_G": False, "reason": "zero-factor joint readout (pinned one-hot cell -> logG=-inf) -> NO_INNER_SIGNAL, observer NOT_EVALUABLE", "finite": False,
                "observer_unstable": None, "observer_evaluable": False,
                # TAIL_PERM_PIN_ORIGIN ruling: this label is only reachable AFTER controller._observer_diag has proven, for EVERY
                # input vector (x, x8, x14, x20, inverse-mapped perm tail), that each exact-zero factor sits on a pinned-elsewhere
                # cell; qualify_v2 itself cannot see the pins and never asserts the pin origin on its own
                "not_evaluable_cause": "ZERO_FACTOR_PINNED_ROW_PROVEN_BY_CALLER", "PERM_EQUIVARIANT": None,
                "TV_o": None, "TAU_TV": None, "RAW_G_SPREAD": None, "TAU_G": None, **base}
    gx, g8, g14, g20, gp, gn = vecs
    d_repeat = float(np.abs(center(g8) - center(g14)).max())
    d_null = float(np.abs(center(gn)).max())
    gmax_abs = float(max(1.0, np.abs(gx).max()))
    tau_g_pre = max(d_repeat, d_null, 16 * EPS64 * gmax_abs)          # perm not yet included (it is being tested)
    p_x, spread = p_from_g(gx, tau_g_pre); p8 = p_from_g(g8, tau_g_pre)[0]; p14 = p_from_g(g14, tau_g_pre)[0]
    unif = np.full(n, 1.0 / n)
    tv_repeat = tv(p8, p14); tv_null = tv(p_from_g(gn, tau_g_pre)[0], unif)
    tau_tv_pre = max(tv_repeat, tv_null, 16 * EPS64)
    # CD review B3: the permuted control is a 20-step tail, so its reference is the UNpermuted 20-step tail g20
    # (same sweep count), never the position-0 field gx — otherwise d_perm/tv_perm would measure 20 steps of drift
    # and the held-out observer would be compared against a threshold that already contains its own drift.
    p20_pre = p_from_g(g20, tau_g_pre)[0]
    d_perm = float(np.abs(center(g20) - center(gp)).max()); tv_perm = tv(p20_pre, p_from_g(gp, tau_g_pre)[0])
    perm_equivariant = tv_perm <= tau_tv_pre and d_perm <= max(tau_g_pre, 16 * EPS64 * gmax_abs)
    tau_g = max(tau_g_pre, d_perm); tau_tv = max(tau_tv_pre, tv_perm)         # GO formulas incl. perm once tested
    p_x, spread = p_from_g(gx, tau_g)
    tv_o = tv(p_x, unif)
    observer_tv = tv(p_from_g(g20, tau_g)[0], p_x)                     # held-out position 20
    observer_stable = observer_tv <= tau_tv
    q = bool(spread > tau_g and tv_o > tau_tv and observer_stable and perm_equivariant and physical_response_pass and self_pin_free_pass)
    return {"QUALIFIED_G": q, "finite": True, "RAW_G_SPREAD": spread, "d_repeat_g": d_repeat, "d_perm_g": d_perm, "d_null_g": d_null, "TAU_G": tau_g,
            "TV_o": tv_o, "tv_repeat": tv_repeat, "tv_perm": tv_perm, "tv_null": tv_null, "TAU_TV": tau_tv, "TAU_TV_PRE": tau_tv_pre,
            "OBSERVER_TV": observer_tv, "OBSERVER_STABLE": bool(observer_stable), "observer_unstable": bool(not observer_stable), "observer_evaluable": True,
            "PERM_EQUIVARIANT": bool(perm_equivariant), "PHYSICAL_RESPONSE_PASS": bool(physical_response_pass), "SELF_PIN_FREE": bool(self_pin_free_pass),
            "p_G": p_x.tolist(), "uniform_baseline": 1.0 / n, **base}


def inverse_cdf(u, weights):
    tot = float(sum(weights)); acc = 0.0
    for i, w in enumerate(weights):
        acc += w / tot
        if u < acc:
            return i
    return len(weights) - 1


def decide_owner(owners_canonical, T_o, qual, variate_u):
    """owners_canonical: list of (identity, slot, raw_u) in canonical physical order.
    variate_u: the frozen OWNER_COMMON_VARIATE for this decision (read-only reuse for the
    matched uniform diagnostic).  Returns dict with provenance and the raw UAV index."""
    n = len(owners_canonical)
    if n == 0 or len(T_o) == 0:
        return {"provenance": PROV_NONE, "owner": None, "diagnostic_uniform_owner": None}
    if n == 1:
        return {"provenance": PROV_SINGLETON, "owner": owners_canonical[0][2], "diagnostic_uniform_owner": owners_canonical[0][2]}
    uniform_idx = inverse_cdf(variate_u, [1.0] * n)
    if qual.get("QUALIFIED_G"):
        idx = inverse_cdf(variate_u, qual["p_G"])
        prov = PROV_WEIGHTED
    else:
        idx = uniform_idx
        prov = PROV_UNIFORM
    return {"provenance": prov, "owner": owners_canonical[idx][2], "owner_canonical": owners_canonical[idx][:2],
            "diagnostic_uniform_owner": owners_canonical[uniform_idx][2],
            "WEIGHTED_SAME_RNG_OWNER_DIFFERENT": bool(idx != uniform_idx)}


def decide_service_tuple(x, order, owner_u, T_o, provenance, tie_variate, uniform_variate):
    """Owner fixed; qualified-G -> max joint logG among the owner's legal tuples (exact tie ->
    SERVICE_TUPLE_TIE single draw); uniform fallback -> SERVICE_TUPLE_UNIFORM single draw.
    Canonical tuple order = ascending k_serv."""
    ks = sorted(k for (u, k) in T_o if u == owner_u)
    if not ks:
        return None, "NO_LEGAL_TUPLE_FOR_OWNER"
    if provenance == PROV_WEIGHTED:
        vals = [logG(x, order, owner_u, k) for k in ks]
        m = max(vals)
        best = [k for k, v in zip(ks, vals) if v == m]
        if len(best) == 1:
            return best[0], "ARGMAX_LOGG"
        return best[inverse_cdf(tie_variate(len(best)), [1.0] * len(best))], "SERVICE_TUPLE_TIE"
    return ks[inverse_cdf(uniform_variate(len(ks)), [1.0] * len(ks))], "SERVICE_TUPLE_UNIFORM"


# ----------------------------------------------------------------------------- representation proof helper
def log_vs_product_agreement(pairs_a, pairs_b, ulps=2):
    """For two candidate tuples with factor pairs (a1,a2),(b1,b2) of representable positive doubles,
    compare the ordering under the frozen log rule with the direct product; disagreements are only
    tolerated when the products are within `ulps` ULPs (near-tie).  Returns counts."""
    agree = near = disagree = 0
    for (a1, a2), (b1, b2) in zip(pairs_a, pairs_b):
        la, lb = _log(a1) + _log(a2), _log(b1) + _log(b2)
        pa, pb = a1 * a2, b1 * b2
        sl = (la > lb) - (la < lb); sp = (pa > pb) - (pa < pb)
        if sl == sp:
            agree += 1
        elif pa == pb or abs(pa - pb) <= ulps * np.spacing(max(pa, pb)):
            near += 1
        else:
            disagree += 1
    return {"agree": agree, "near_tie_within_ulps": near, "disagree": disagree}


def _check(cond, msg):
    if not cond:
        raise RuntimeError("READOUT_SELFTEST_FAIL: " + str(msg))


def _selftest():
    rng = np.random.default_rng(0)
    ev = {}
    # 1) representation: random positive doubles incl. subnormal-scale factors
    A = [(float(a), float(b)) for a, b in rng.uniform(1e-300, 1.0, (20000, 2))]
    B = [(float(a), float(b)) for a, b in rng.uniform(1e-300, 1.0, (20000, 2))]
    r = log_vs_product_agreement(A, B)
    _check(r["disagree"] == 0, r); ev["representation"] = r
    tiny = [(5e-324, 0.5)] * 3; _check(log_vs_product_agreement(tiny, [(1e-320, 0.5)] * 3)["disagree"] == 0, "subnormal agreement")
    _check(_log(0.0) == -math.inf, "log(0)")
    # 2) TAU / p_G / qualification on a synthetic clear signal (legacy qualify)
    g = np.array([0.0, -1.0, -2.0, -3.0]); noise = 1e-12
    q = qualify([g, g + noise, g - noise], g + noise, np.zeros(4) + noise,
                physical_response_pass=True, self_pin_free_pass=True, perm_equivariant_pass=True)
    _check(q["QUALIFIED_G"] and abs(sum(q["p_G"]) - 1) < 1e-12 and q["p_G"][0] == max(q["p_G"]), q)
    # 3) null / uniform must NOT qualify
    q0 = qualify([np.zeros(4)] * 3, np.zeros(4), np.zeros(4), physical_response_pass=True, self_pin_free_pass=True, perm_equivariant_pass=True)
    _check(not q0["QUALIFIED_G"], "uniform must not qualify")
    # 4) owner decision uses the same variate for weighted and uniform; singleton/none branches
    owners = [("idA", 0, 7), ("idB", 0, 3), ("idC", 0, 9), ("idD", 0, 1)]
    d = decide_owner(owners, [(7, 5), (3, 5), (9, 5), (1, 5)], q, 0.05)
    _check(d["provenance"] == PROV_WEIGHTED and d["owner"] == 7, d)
    d2 = decide_owner(owners, [(7, 5), (3, 5), (9, 5), (1, 5)], q0, 0.05)
    _check(d2["provenance"] == PROV_UNIFORM and d2["owner"] == 7 and d2["diagnostic_uniform_owner"] == 7, d2)
    _check(decide_owner(owners[:1], [(7, 5)], q, 0.5)["provenance"] == PROV_SINGLETON, "singleton")
    _check(decide_owner([], [], q, 0.5)["provenance"] == PROV_NONE, "none")
    # 5) service tuple: argmax, exact tie draw, uniform draw
    x = np.full((10, 8, 4), 0.1); order = {"k_p": 2, "c": 1, "d": 2, "k_d": 6}
    x[7, 5, 1] = 0.9; x[7, 6, 1] = 0.9
    k, how = decide_service_tuple(x, order, 7, [(7, 4), (7, 5), (7, 6)], PROV_WEIGHTED, lambda n: 0.99, lambda n: 0.0)
    _check(how == "SERVICE_TUPLE_TIE" and k == 6, (how, k))
    k, how = decide_service_tuple(x, order, 7, [(7, 4), (7, 5), (7, 6)], PROV_UNIFORM, lambda n: 0.99, lambda n: 0.0)
    _check(how == "SERVICE_TUPLE_UNIFORM" and k == 4, (how, k))
    # 6) vectorised g_vector == scalar definition (incl. zeros)
    xt = np.abs(rng.normal(size=(6, 9, 5))); xt[2, 3, 1] = 0.0
    T_o = [(u, k) for u in range(6) for k in (3, 4, 5)]
    gv = g_vector(xt, {"k_p": 2, "c": 2, "d": 2, "k_d": 5}, T_o)
    gs = {}
    for (u, k) in T_o:
        val = logG(xt, {"k_p": 2, "c": 2, "d": 2, "k_d": 5}, u, k)
        if u not in gs or val > gs[u]: gs[u] = val
    _check(gv == gs, (gv, gs))
    # 7) qualify_v2 split controls (CD R-3 / review B3): drift between x and the 20-step tail must be caught by the
    #    held-out observer and must NOT be absorbed into TAU through the permutation statistic.
    gsig = np.array([0.0, -1.0, -2.0, -3.0]); drift = np.array([0.0, 0.0, 0.0, 3.5])     # tail drifts owner 3 into a near-tie
    g20 = gsig + drift
    qa = qualify_v2(gsig, gsig + 1e-13, gsig - 1e-13, g20, g20 + 1e-15, np.zeros(4) + 1e-13, physical_response_pass=True, self_pin_free_pass=True)
    _check(qa["PERM_EQUIVARIANT"] and qa["observer_unstable"] and not qa["QUALIFIED_G"], f"drifting tail must be observer-unstable yet perm-equivariant: {qa}")
    ev["v2_drift_case"] = {k: qa[k] for k in ("PERM_EQUIVARIANT", "OBSERVER_TV", "TAU_TV", "observer_unstable", "QUALIFIED_G")}
    qb = qualify_v2(gsig, gsig + 1e-13, gsig - 1e-13, gsig + 1e-13, gsig + 2e-13, np.zeros(4) + 1e-13, physical_response_pass=True, self_pin_free_pass=True)
    _check(qb["QUALIFIED_G"] and qb["PERM_EQUIVARIANT"] and not qb["observer_unstable"], f"stable case must qualify: {qb}")
    qc = qualify_v2(gsig, gsig + 1e-13, gsig - 1e-13, gsig + 1e-13, gsig[::-1].copy(), np.zeros(4) + 1e-13, physical_response_pass=True, self_pin_free_pass=True)
    _check(not qc["PERM_EQUIVARIANT"] and not qc["QUALIFIED_G"], f"scrambled permutation control must fail: {qc}")
    _check(abs(qa["TAU_TV_PRE"] - qb["TAU_TV_PRE"]) < 1e-9, "TAU_TV_PRE must not depend on the observer tail")
    _check(not qualify_v2(gsig, gsig, gsig, gsig, gsig, np.zeros(4), physical_response_pass=False, self_pin_free_pass=True)["QUALIFIED_G"], "physical response fail-closed")
    _check(not qualify_v2(gsig, gsig, gsig, gsig, gsig, np.zeros(4), physical_response_pass=True, self_pin_free_pass=False)["QUALIFIED_G"], "self-pin fail-closed")
    qn = qualify_v2([0.0, -math.inf, -1.0], [0.0, -math.inf, -1.0], [0.0, -math.inf, -1.0], [0.0, -math.inf, -1.0], [0.0, -math.inf, -1.0], [0.0, 0.0, 0.0], physical_response_pass=True, self_pin_free_pass=True)
    _check(qn["observer_evaluable"] is False and qn["observer_unstable"] is None and not qn["QUALIFIED_G"], f"zero-factor readout must be NOT evaluable, never a stable pass: {qn}")
    try:
        qualify_v2([0.0, math.nan, -1.0], [0.0, -1.0, -1.0], [0.0, -1.0, -1.0], [0.0, -1.0, -1.0], [0.0, -1.0, -1.0], [0.0, 0.0, 0.0], physical_response_pass=True, self_pin_free_pass=True)
        _check(False, "NaN readout must hard-fail (Y2 item 7)")
    except RuntimeError as e:
        _check("READOUT_NON_FINITE_UNEXPECTED" in str(e), e)
    ev.update({"PASS": True, "TAU_G": q["TAU_G"], "TV_o": q["TV_o"]})
    print("readout selftest OK:", r, "| TAU_G", q["TAU_G"], "TV_o", round(q["TV_o"], 4), "| v2 drift case observer_unstable", qa["observer_unstable"])
    return ev


if __name__ == "__main__":
    _selftest()
