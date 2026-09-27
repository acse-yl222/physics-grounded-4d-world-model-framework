"""REFERENCE_DONOR_REPLICA_V1 — the frozen CNNJacobiSolver.solve loop (jacobi_cnn.py:232-277)
re-expressed op-for-op with per-sweep bookkeeping only (E2 plan section 1.4; CD ruling Q3).

Guarantees (proved by `bitwise_proof`): identical x and dx to raw `CNNJacobiSolver.solve` for the
same inputs, because the update op sequence and every reduction are unchanged; bookkeeping reads
tensors that the raw loop already materialises (dxb, inner_done, theta) and never feeds back.

Optional candidate-B behaviour (`host_read_every=n>1`, CD ruling Q3 ALLOWED list): the residual
and the inner_done/active masks are still computed EVERY sweep on device; only the host read of
`active.any()` happens every n sweeps.  Sweeps after all lanes are done are strict masked no-ops
(cond is False everywhere), so x is bitwise unchanged; the extra sweep count is recorded.
FORBIDDEN (never implemented here): skipping residual computation, updating converged lanes,
delaying cooling, changing tol/schedule/max_inner.
"""
import hashlib
import numpy as np
import torch

BACKEND_ID_REFERENCE = "REFERENCE_DONOR_REPLICA_V1"
BACKEND_ID_CANDIDATE_B = "CANDIDATE_B_HOST_READ_DECIMATED_V1"


def _sha(t):
    return hashlib.sha256(np.ascontiguousarray(t.detach().cpu().numpy()).tobytes()).hexdigest()


def initial_state(sol, seeds, x_init):
    """Verbatim jacobi_cnn.py:232-247 (seed initialiser + birth row + pins)."""
    N, K, M = sol.N, sol.K, sol.M
    if x_init is not None:
        x_np = np.array(x_init, float)
        B = x_np.shape[0]
        seeds = list(seeds)[:B] if seeds else list(range(B))
    else:
        seeds = list(seeds)
        B = len(seeds)
        x_np = np.empty((B, N, K, M))
        for b, sd in enumerate(seeds):
            rng = np.random.default_rng(sd)
            xb = rng.uniform(0.9, 1.1, (N, K, M))
            xb[:, 1:, :] /= xb[:, 1:, :].sum(2, keepdims=True)
            x_np[b] = xb
    x_np[:, :, 0, :] = sol.x0s[None]
    for (pi, pk), pmu in sol.pins.items():
        x_np[:, pi, pk, :] = 0.0
        x_np[:, pi, pk, pmu] = 1.0
    return x_np, seeds, B


@torch.no_grad()
def solve_reference(sol, *, seeds=(0,), theta0=None, theta_min=None, gamma=0.95, alpha=0.1,
                    tol=1e-9, max_inner=300, max_outer=400, sat_stop=0.95, x_init=None,
                    host_read_every=1, undamped_residual_every=None, tail_sweeps=0,
                    field=None):
    """Returns (x, dx_last, record).  `field` defaults to sol.field (raw donor field); an
    equivalent fixed operator (candidate A) may be injected here and must pass the same proof."""
    if theta0 is None or theta_min is None:
        raise ValueError("explicit theta0/theta_min required (frozen engine contract)")
    if host_read_every < 1:
        raise ValueError("host_read_every must be >= 1")
    N, K, M = sol.N, sol.K, sol.M
    fld = field if field is not None else sol.field
    x_np, seeds, B = initial_state(sol, seeds, x_init)
    dev, td = sol.device, sol._td
    x = torch.tensor(x_np, dtype=td, device=dev)
    theta = torch.tensor(np.broadcast_to(np.asarray(theta0, float), (B,)).copy(), dtype=td, device=dev)
    th_min = torch.tensor(np.broadcast_to(np.asarray(theta_min, float), (B,)).copy(), dtype=td, device=dev)
    dx_last = torch.ones(B, dtype=td, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)

    rec = {"backend": BACKEND_ID_REFERENCE if host_read_every == 1 else BACKEND_ID_CANDIDATE_B,
           "host_read_every": host_read_every, "sweeps_total": 0, "sweeps_masked_noop": 0,
           "host_reads": 0, "theta_levels": 0, "theta_sequence": [],
           "first_tol_crossing": [None] * B, "per_level_sweeps": [], "undamped_residual_trace": [],
           "x_init_sha256": _sha(x)}
    # device-side bookkeeping buffers (copied to host ONCE at the end; no per-sweep syncs)
    T_MAX = max_outer * max_inner
    dxb_buf = torch.full((T_MAX, B), float("nan"), dtype=td, device=dev)
    done_buf = torch.zeros((T_MAX, B), dtype=torch.bool, device=dev)
    first_cross = torch.full((B,), -1, dtype=torch.int64, device=dev)
    level_of_sweep = torch.zeros((T_MAX,), dtype=torch.int64, device=dev)
    noop_count = torch.zeros((), dtype=torch.int64, device=dev)
    sweep_g = 0
    for _outer in range(max_outer):
        inner_done = done.clone()
        level_sweeps = 0
        for _inner in range(max_inner):
            active = ~inner_done
            if (_inner % host_read_every) == 0:
                rec["host_reads"] += 1
                if not bool(active.any()):
                    break
            xo = x.clone()
            for cmask in sol.colors:                       # redblack: odd then even rows
                f = fld(x)
                z = -f / theta.view(B, 1, 1, 1)
                z = z - z.amax(3, keepdim=True)
                e = z.exp()
                xin = (1 - alpha) * x + alpha * (e / e.sum(3, keepdim=True))
                cond = active.view(B, 1, 1, 1) & sol.updmask.view(1, N, K, 1) & cmask.view(1, 1, K, 1)
                x = torch.where(cond, xin, x)
            dxb = (x - xo).abs().reshape(B, -1).amax(1)
            dx_last = torch.where(active, dxb, dx_last)
            newly_done = active & (dxb < tol)
            inner_done = inner_done | newly_done
            # ---- bookkeeping only, on device ----
            dxb_buf[sweep_g] = dxb
            done_buf[sweep_g] = inner_done
            level_of_sweep[sweep_g] = rec["theta_levels"]
            first_cross = torch.where(newly_done & (first_cross < 0), torch.full_like(first_cross, sweep_g), first_cross)
            if host_read_every > 1:
                noop_count += (~active).all().to(torch.int64)
            rec["sweeps_total"] += 1; level_sweeps += 1
            if undamped_residual_every and (sweep_g % undamped_residual_every) == 0:
                rec["undamped_residual_trace"].append((sweep_g, undamped_residual(sol, x, theta, fld)))
            sweep_g += 1
        rec["per_level_sweeps"].append(level_sweeps)
        rec["theta_sequence"].append(theta.detach().cpu().numpy().tolist())
        rec["theta_levels"] += 1
        sat = x[:, :, 1:, :].amax(3).reshape(B, -1).mean(1) >= sat_stop
        newly = (~done) & (((dx_last < tol) & sat) | (theta <= th_min * (1 + 1e-12)))
        done = done | newly
        if bool(done.all()):
            break
        theta = torch.where(done, theta, torch.maximum(theta * gamma, th_min))
    # one host copy for all bookkeeping
    fc = first_cross.detach().cpu().numpy(); lv = level_of_sweep.detach().cpu().numpy()
    rec["first_tol_crossing"] = [None if fc[b] < 0 else (int(lv[fc[b]]), int(fc[b])) for b in range(B)]
    rec["dxb_trace"] = dxb_buf[:sweep_g].detach().cpu().numpy().tolist()
    rec["inner_done_history_sha256"] = _sha(done_buf[:sweep_g])
    rec["sweeps_masked_noop"] = int(noop_count.item())
    # fixed-theta verification tail (observation only; x is NOT updated)
    if tail_sweeps:
        tail = []
        for _ in range(tail_sweeps):
            tail.append(undamped_residual(sol, x, theta, fld))
        rec["verification_tail_undamped_residual"] = tail
    rec["x_sha256"] = _sha(x); rec["dx_sha256"] = _sha(dx_last)
    rec["saturation"] = x[:, :, 1:, :].amax(3).reshape(B, -1).mean(1).detach().cpu().numpy().tolist()
    return x, dx_last, rec


@torch.no_grad()
def undamped_residual(sol, x, theta, fld):
    """||T_theta(x) - x||_inf per lane with T_theta = one complete undamped red-black sweep on a
    clone (full-update rows only). Never writes x."""
    B, N, K, M = x.shape
    y = x.clone()
    for cmask in sol.colors:
        f = fld(y)
        z = -f / theta.view(B, 1, 1, 1)
        z = z - z.amax(3, keepdim=True)
        e = z.exp()
        xin = e / e.sum(3, keepdim=True)
        cond = sol.updmask.view(1, N, K, 1) & cmask.view(1, 1, K, 1)
        y = torch.where(cond, xin, y)
    return (y - x).abs().reshape(B, -1).amax(1).detach().cpu().numpy().tolist()


@torch.no_grad()
def bitwise_proof(sol, **kw):
    """Run raw CNNJacobiSolver.solve and the replica with identical arguments; compare sha256 of x
    and dx. `kw` must not contain replica-only keys."""
    raw = sol.solve(**kw)
    x_ref, dx_ref, rec = solve_reference(sol, **kw)
    rx = hashlib.sha256(np.ascontiguousarray(raw.x).tobytes()).hexdigest()
    rdx = hashlib.sha256(np.ascontiguousarray(raw.dx).tobytes()).hexdigest()
    ex = hashlib.sha256(np.ascontiguousarray(x_ref.double().cpu().numpy()).tobytes()).hexdigest()
    edx = hashlib.sha256(np.ascontiguousarray(dx_ref.double().cpu().numpy()).tobytes()).hexdigest()
    return {"x_equal": rx == ex, "dx_equal": rdx == edx, "raw_x_sha256": rx, "replica_x_sha256": ex,
            "raw_dx_sha256": rdx, "replica_dx_sha256": edx, "replica_record_head":
            {k: rec[k] for k in ("backend", "sweeps_total", "host_reads", "theta_levels", "first_tol_crossing")}}


EQUIVALENCE_EVIDENCE_SCHEMA = {   # CD ruling section six: the 12 items every candidate must cover
    "first_tolerance_crossing_sweep": "NOT_EXECUTED",
    "per_sweep_inner_done_active_mask": "NOT_EXECUTED",
    "theta_transition_and_cooling_sequence": "NOT_EXECUTED",
    "residual_energy_closure_classification": "NOT_EXECUTED",
    "readout_and_tie_universe": "NOT_EXECUTED",
    "rng_consumption_state": "NOT_EXECUTED",
    "checkpoint_resume": "NOT_EXECUTED",
    "final_x": "NOT_EXECUTED",
    "owner_time_journey_plan": "NOT_EXECUTED",
    "hard_validation_and_independent_replay": "NOT_EXECUTED",
    "same_seed_repeat": "NOT_EXECUTED",
    "B1_vs_permitted_partitioned_execution": "NOT_EXECUTED",
}


# ----------------------------------------------------------------------------- CPU self-test
def _check(cond, msg):
    """Explicit test assertion: never a bare `assert` (python -O must not hollow the selftest out)."""
    if not cond:
        raise RuntimeError("EQUIV_BACKEND_SELFTEST_FAIL: " + str(msg))


def _selftest():
    """Tiny fixture on CPU float64: replica vs a verbatim CPU copy of the raw loop, bitwise.  CPU only."""
    import sys, os
    sys.path.insert(0, os.environ.get("E2_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
    from src.ai4pde.jacobi_cnn import CNNJacobiSolver
    from src.core.costs import CostConfig
    rng = np.random.default_rng(1)
    N, K, M = 3, 6, 4
    D = rng.uniform(0.1, 2.0, (M, M)); np.fill_diagonal(D, 0.0); D = 0.5 * (D + D.T)
    Ccap = np.zeros((K, M)); Ccap[2, 1] = 1; Ccap[4, 3] = 1
    lam = np.zeros((K, M)); lam[Ccap > 0] = 2 * D.sum(0)[np.nonzero(Ccap)[1]]
    x0s = np.zeros((N, M)); x0s[:, 0] = 1
    sol = CNNJacobiSolver(D, Ccap, lam, x0s, gamma_s=0.0, costs=CostConfig(eps_time=0.0, mu_conc=0.0),
                          update="redblack", dtype="float64", device="cpu")
    _check(str(sol.device) == "cpu", f"selftest must run on CPU, got device {sol.device}")
    kw = dict(seeds=(0, 1), theta0=1.5, theta_min=0.03, gamma=0.9, alpha=0.1, tol=1e-9,
              max_inner=40, max_outer=60, sat_stop=0.95)
    p = bitwise_proof(sol, **kw)
    _check(p["x_equal"], f"replica x differs from raw solve: {p}")
    _check(p["dx_equal"], f"replica dx differs from raw solve: {p}")
    _check(p["replica_record_head"]["sweeps_total"] > 0 and p["replica_record_head"]["theta_levels"] > 0, f"empty solve: {p}")
    # explicit theta contract
    raised = False
    try:
        solve_reference(sol, seeds=(0,), theta0=None, theta_min=None)
    except ValueError:
        raised = True
    _check(raised, "missing theta0/theta_min must raise ValueError")
    # candidate B: decimated host read must leave x bitwise unchanged
    xB, dxB, recB = solve_reference(sol, host_read_every=7, **kw)
    _check(_sha(xB) == p["replica_x_sha256"], "candidate B changed x")
    _check(_sha(dxB) == p["replica_dx_sha256"], "candidate B changed dx")
    _check(recB["backend"] == BACKEND_ID_CANDIDATE_B, f"candidate B backend id {recB['backend']}")
    _check(recB["host_reads"] < p["replica_record_head"]["host_reads"], "candidate B must perform fewer host reads")
    # verification tail + residual trace run without touching x
    xT, _, recT = solve_reference(sol, tail_sweeps=3, undamped_residual_every=5, **kw)
    _check(_sha(xT) == p["replica_x_sha256"], "verification tail / residual trace modified x")
    _check(len(recT["verification_tail_undamped_residual"]) == 3, "tail length")
    _check(all(np.isfinite(v) for row in recT["verification_tail_undamped_residual"] for v in row), "tail residuals must be finite")
    _check(len(recT["undamped_residual_trace"]) >= 1, "residual trace empty")
    # same inputs => same init sha (deterministic initialiser), different seeds => different init
    _check(recT["x_init_sha256"] == recB["x_init_sha256"], "x_init sha must be deterministic for identical seeds")
    _, _, recS = solve_reference(sol, **dict(kw, seeds=(2, 3)))
    _check(recS["x_init_sha256"] != recT["x_init_sha256"], "different seeds must give a different x_init")
    print("equiv_backend selftest OK:", p["replica_record_head"], "| candB host_reads", recB["host_reads"],
          "masked_noop", recB["sweeps_masked_noop"])
    return {"PASS": True, "device": "cpu", "shape": [N, K, M], "bitwise_proof": p, "candidate_B_host_reads": recB["host_reads"],
            "candidate_B_masked_noop": recB["sweeps_masked_noop"], "candidate_B_x_unchanged": True,
            "tail_len": len(recT["verification_tail_undamped_residual"]), "tail_residual_last": recT["verification_tail_undamped_residual"][-1],
            "x_init_sha256": recT["x_init_sha256"], "theta_contract_raises": raised}


if __name__ == "__main__":
    _selftest()
