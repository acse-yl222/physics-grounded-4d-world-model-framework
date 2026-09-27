"""Inner adapter: anonymous inputs -> one global CUDA FP64 solve through the REFERENCE replica ->
field x_r plus the frozen control readouts (plan sections 2.3, 2.4; GO 4.1, 7).

Controls (all B=1, serial, counted separately from INNER_SOLVE_COUNT):
  repeat   : fixed-theta damped verification tail continued from x_r on a COPY; snapshots at tail
             sweeps 8/14/20 (x_r itself is untouched and is the proposal field);
  perm     : the same tail run on the UAV-permuted field with a consistently permuted solver
             (x0s, s, pins, updmask permuted), inverse-mapped back;
  null     : supplied once per scale by the caller (exact-null control).
Field initialisation: INIT_POLICY=FRESH_PER_ROUND with FIELD_INIT_SEED=H(ns,RUN_SEED,ROUND_ID),
constructed here (uniform(0.9,1.1) normalised, birth row, pins) and passed via x_init, so the
engine's internal np.random.default_rng(seed) initialiser is never used.
"""
import hashlib
import time

import numpy as np
import torch

from . import equiv_backend as EB
from .rng import field_init_seed, variate

TAIL_POSITIONS = (8, 14, 20)
NUMERICAL_CONTROLS = ("theta_start_ratio", "theta_min_ratio", "gamma", "alpha", "tol", "max_inner",
                      "max_outer", "sat_stop", "init_amplitude", "raw_closure_tolerance", "tail_sweeps")
C0 = dict(candidate_id="C0_DONOR_DEFAULTS", theta_start_ratio=0.95, theta_min_ratio=0.02, gamma=0.95, alpha=0.1,
          tol=1e-9, max_inner=300, max_outer=400, sat_stop=0.95, init_amplitude=0.1, raw_closure_tolerance=1e-9,
          tail_sweeps=20, backend="REFERENCE_DONOR_REPLICA_V1", host_read_every=1)


def _sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def make_solver(a, device="cuda"):
    from src.ai4pde.jacobi_cnn import CNNJacobiSolver
    from src.core.costs import CostConfig
    return CNNJacobiSolver(a["D"], a["Ccap"], a["lam_cap"], a["x0s"], s=a["s"], pins=a["pins"], gamma_s=0.0,
                           costs=CostConfig(eps_time=0.0, mu_conc=0.0), update="redblack", dtype="float64", device=device)


def field_init(a, run_seed, round_id, amplitude):
    """x_init (1,N,K,M): uniform(1-amp, 1+amp) normalised over stations for rows>=1, birth row from
    x0s, pins one-hot — same shape of initialiser as the donor, seeded from the FIELD_INIT stream."""
    N, K, M = a["N"], a["K"], a["M"]
    rng = np.random.default_rng(field_init_seed(run_seed, round_id))
    xb = rng.uniform(1.0 - amplitude, 1.0 + amplitude, (N, K, M))
    xb[:, 1:, :] /= xb[:, 1:, :].sum(2, keepdims=True)
    xb[:, 0, :] = a["x0s"]
    for (pi, pk), pmu in a["pins"].items():
        xb[pi, pk, :] = 0.0; xb[pi, pk, pmu] = 1.0
    return xb[None]


@torch.no_grad()
def damped_tail(sol, x, theta, alpha, positions, fld=None):
    """Fixed-theta damped sweeps continued from x on a copy; returns {pos: x_copy_numpy}."""
    fld = fld or sol.field
    B, N, K, M = x.shape
    y = x.clone()
    active = torch.ones(B, dtype=torch.bool, device=x.device)
    out = {}
    for s in range(1, max(positions) + 1):
        for cmask in sol.colors:
            f = fld(y)
            z = -f / theta.view(B, 1, 1, 1)
            z = z - z.amax(3, keepdim=True)
            e = z.exp()
            xin = (1 - alpha) * y + alpha * (e / e.sum(3, keepdim=True))
            cond = active.view(B, 1, 1, 1) & sol.updmask.view(1, N, K, 1) & cmask.view(1, 1, K, 1)
            y = torch.where(cond, xin, y)
        if s in positions:
            out[s] = y[0].double().cpu().numpy().copy()
    return out


def permutation(N, run_seed, round_id):
    """Fixed UAV permutation for the permutation control (FIELD_INIT namespace, tag 'perm')."""
    rng = np.random.default_rng(int(variate("FIELD_INIT", run_seed, round_id, "perm") * (2**53)))
    return rng.permutation(N)


def solve_round(a, cfg, run_seed, round_id, *, device="cuda", theta_c=None, log=print):
    """One global solve + controls.  Returns the controller backend contract."""
    from src.core._frozen import theta_c_scalar_multi
    t0 = time.time()
    tcs = float(theta_c if theta_c is not None else theta_c_scalar_multi(a["D"], a["Ccap"], a["lam_cap"], a["N"]))
    theta0, theta_min = cfg["theta_start_ratio"] * tcs, cfg["theta_min_ratio"] * tcs
    sol = make_solver(a, device)
    fld = sol.field
    if cfg.get("backend") == "CANDIDATE_A_B1_EXPLICIT_ADJACENT_MATMUL":
        from bounded_studies.r3_guidance_inner_v3r4_q10000_v1.guidance_inner import B1Field
        fld = B1Field(sol.field, a["D"], a["K"])
    x_init = field_init(a, run_seed, round_id, cfg["init_amplitude"])
    x, dx, rec = EB.solve_reference(sol, seeds=(0,), theta0=theta0, theta_min=theta_min, gamma=cfg["gamma"], alpha=cfg["alpha"],
                                    tol=cfg["tol"], max_inner=cfg["max_inner"], max_outer=cfg["max_outer"], sat_stop=cfg["sat_stop"],
                                    x_init=x_init, host_read_every=cfg.get("host_read_every", 1), tail_sweeps=cfg["tail_sweeps"],
                                    field=fld)
    theta_final = torch.tensor([rec["theta_sequence"][-1][0]], dtype=sol._td, device=sol.device)
    x_r = x[0].double().cpu().numpy().copy()
    tails = damped_tail(sol, x, theta_final, cfg["alpha"], TAIL_POSITIONS, fld=fld)
    # permutation control: permuted solver + permuted field, tail, inverse map
    perm = permutation(a["N"], run_seed, round_id); inv = np.argsort(perm)
    ap = dict(a); ap["x0s"] = a["x0s"][perm]; ap["s"] = a["s"][perm]
    ap["pins"] = {(int(inv[u]), k): m for (u, k), m in a["pins"].items()}
    solp = make_solver(ap, device)
    fldp = solp.field
    if cfg.get("backend") == "CANDIDATE_A_B1_EXPLICIT_ADJACENT_MATMUL":
        from bounded_studies.r3_guidance_inner_v3r4_q10000_v1.guidance_inner import B1Field
        fldp = B1Field(solp.field, ap["D"], ap["K"])
    xp = torch.tensor(x_r[perm][None], dtype=sol._td, device=sol.device)
    tp = damped_tail(solp, xp, theta_final, cfg["alpha"], (max(TAIL_POSITIONS),), fld=fldp)[max(TAIL_POSITIONS)]
    x_perm_tail = tp[inv]
    tail_res = rec.get("verification_tail_undamped_residual", [])
    r_max = max((t[0] for t in tail_res), default=None)
    raw_closed = r_max is not None and r_max <= cfg["raw_closure_tolerance"]
    record = {"backend": cfg.get("backend", rec["backend"]), "loop_variant": rec["backend"], "field_class": type(fld).__name__, "sweeps_total": rec["sweeps_total"], "theta_levels": rec["theta_levels"],
              "JACOBI_COMPLETE_SWEEPS_PER_TEMPERATURE": cfg["max_inner"], "ANNEALING_TEMPERATURE_LEVEL_COUNT": rec["theta_levels"],
              "theta_c_scalar_multi": tcs, "theta0": theta0, "theta_min": theta_min, "theta_final": float(theta_final.item()),
              "TEMPERATURE_FLOOR_REACHED": bool(abs(float(theta_final.item()) - theta_min) <= 1e-12 * max(1.0, theta_min)),
              "DAMPED_SWEEP_DX": float(dx[0].item()), "UNDAMPED_FIXED_POINT_RESIDUAL_MAX_TAIL": r_max,
              "VERIFICATION_TAIL_SWEEPS": cfg["tail_sweeps"], "RAW_INNER_CLOSED": bool(raw_closed),
              "closure_state": "RAW_INNER_CLOSED" if raw_closed else "READOUT_STABLE_RAW_UNCLOSED",   # refined by the controller's observer test
              "saturation": rec["saturation"][0], "x_sha256": _sha(x_r), "x_init_sha256": rec["x_init_sha256"],
              "first_tol_crossing": rec["first_tol_crossing"], "CONTROL_TAIL_COUNT": 2, "NULL_CONTROL_SOLVE_COUNT": 0,
              "wall_s": time.time() - t0, "peak_vram_gib": (torch.cuda.max_memory_reserved() / 2**30) if device == "cuda" else None}
    log(f"    inner: sweeps={rec['sweeps_total']} levels={rec['theta_levels']} sat={record['saturation']:.4f} "
        f"r_tail={r_max if r_max is None else f'{r_max:.2e}'} dx={record['DAMPED_SWEEP_DX']:.2e} wall={record['wall_s']:.0f}s")
    del sol, solp, x, xp
    if device == "cuda":
        torch.cuda.empty_cache()
    return {"x": x_r, "x_tail": [tails[p] for p in TAIL_POSITIONS], "x_perm_tail": x_perm_tail, "record": record}


def null_solve(a, cfg, run_seed, *, device="cuda", theta_c=None):
    """Exact-null control once per scale: all UAVs at the same hub, same demand (rows>=1 identical
    across UAVs).  Returns x_null."""
    an = dict(a)
    x0 = np.zeros_like(a["x0s"]); x0[:, int(np.argmax(a["x0s"].sum(0)))] = 1.0
    an["x0s"] = x0; an["s"] = np.zeros_like(a["s"]); an["pins"] = {}
    out = solve_round(an, cfg, run_seed, 10**6, device=device, theta_c=theta_c, log=lambda *_: None)
    return out["x"], out["record"]


def _selftest():
    import os, sys
    sys.path.insert(0, os.environ.get("E2_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
    rng = np.random.default_rng(2)
    N, K, M = 4, 7, 5
    D = rng.uniform(0.1, 2.0, (M, M)); np.fill_diagonal(D, 0.0); D = 0.5 * (D + D.T)
    L = np.zeros((K, M)); L[2, 1] = 1; L[5, 3] = 1
    lam = np.zeros((K, M)); lam[L > 0] = 2 * D.sum(0)[np.nonzero(L)[1]]
    x0s = np.zeros((N, M)); x0s[:, 0] = 1
    a = {"N": N, "K": K, "M": M, "D": D, "L": L, "Ccap": L.copy(), "lam_cap": lam, "x0s": x0s, "s": np.zeros((N, K, M)), "pins": {(1, 3): 2}}
    cfg = dict(C0, max_inner=30, max_outer=25, tail_sweeps=5)
    def _check(cond, msg):
        if not cond:
            raise RuntimeError("INNER_SELFTEST_FAIL: " + str(msg))
    o1 = solve_round(a, cfg, 0, 3, device="cpu", theta_c=1.0, log=lambda *_: None)
    o2 = solve_round(a, cfg, 0, 3, device="cpu", theta_c=1.0, log=lambda *_: None)
    _check(o1["record"]["x_sha256"] == o2["record"]["x_sha256"], "same round must be bitwise reproducible")
    o3 = solve_round(a, cfg, 0, 4, device="cpu", theta_c=1.0, log=lambda *_: None)
    _check(o3["record"]["x_init_sha256"] != o1["record"]["x_init_sha256"], "FRESH_PER_ROUND init must differ by round")
    _check(o1["x"][1, 3].argmax() == 2 and np.allclose(o1["x"][:, 0, :], x0s), "pin/birth rows")
    _check(len(o1["x_tail"]) == 3 and o1["x_perm_tail"].shape == o1["x"].shape, "tail shapes")
    # permutation control: the inverse-mapped permuted 20-step tail must match the UNpermuted 20-step tail (operator
    # equivariance), not the position-0 field (review B3); the gap to x is the tail drift and is reported only
    d_perm20 = float(np.abs(o1["x_perm_tail"] - o1["x_tail"][2]).max()); d_perm0 = float(np.abs(o1["x_perm_tail"] - o1["x"]).max())
    _check(d_perm20 <= 1e-12, f"perm tail vs tail20 {d_perm20}")
    xn, rn = null_solve(a, cfg, 0, device="cpu", theta_c=1.0)
    _check(xn.shape == o1["x"].shape and "x_sha256" in rn, "null control shape/digest")
    print("inner selftest OK:", {k: o1["record"][k] for k in ("sweeps_total", "theta_levels", "TEMPERATURE_FLOOR_REACHED", "RAW_INNER_CLOSED", "CONTROL_TAIL_COUNT")},
          "| perm-vs-tail20 %.1e perm-vs-x %.1e" % (d_perm20, d_perm0))
    return {"PASS": True, "record": {k: o1["record"][k] for k in ("sweeps_total", "theta_levels", "RAW_INNER_CLOSED", "CONTROL_TAIL_COUNT")},
            "perm_vs_tail20": d_perm20, "perm_vs_x": d_perm0, "null_x_sha256": rn["x_sha256"]}


if __name__ == "__main__":
    _selftest()
