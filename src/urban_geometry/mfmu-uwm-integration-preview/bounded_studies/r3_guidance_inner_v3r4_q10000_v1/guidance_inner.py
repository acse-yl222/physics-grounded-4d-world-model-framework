"""R3_DERIVED_SHARED_INITIALIZER_GUIDANCE_INNER — the single Inner of this card.

The engine is the Released-R3 mean-field Inner with two changes, both authorised:

1. the two fixed travel contractions, which the donor writes as nn.Conv1d(M, M, kernel_size=3)
   weights carrying exactly one nonzero tap, are explicit adjacent-time-layer matmuls
   (the prior card's B1 form, re-checked here rather than inherited as VERIFIED);
2. the initializer is a SHARED future template. One z_seed[k,m] per field seed is drawn from the
   candidate-independent registry, row-normalised over the station axis and broadcast to every
   UAV; only then does each UAV get its own real current/birth Hub row, its own committed pins
   and history, and its own hard-fixed cells written over the top.

Change 2 is the point of this card. The prior card drew an INDEPENDENT random row per UAV, so
four physically identical UAVs started from different random states and the anneal amplified that
difference into an arbitrary near-one-hot owner. With a shared template, physically identical
UAVs start bitwise identical and can only be separated by real physics.

Every UAV keeps its own probability matrix: x.shape stays [N, K, M]. "Shared" refers to the
starting template only; the N matrices are never merged.

Energy is F_TBC + F_CAP only. No F_assign, no F_charge, no trainable parameter, no optimizer,
no training epoch. FP64 on CUDA, fail-closed.
"""
import dataclasses
import json
import statistics
import time

import numpy as np
import torch

from src.ai4pde.jacobi_cnn import CNNJacobiSolver
from src.core.costs import CostConfig
from src.core._frozen import theta_c_scalar_multi

INNER_CLASS = "R3_DERIVED_SHARED_INITIALIZER_GUIDANCE_INNER"
THETA_N, THETA_SEED, THETA_TOL, THETA_CHUNK = 15, 0, 1e-9, 5
THETA_MAX_INNER = 3000


@dataclasses.dataclass(frozen=True)
class Config:
    """The candidate's science configuration. Every field is inside the GO 8.3 envelope."""
    candidate_id: str = "C0_BASELINE"
    a_init: float = 0.10
    theta0_factor: float = 0.95
    theta_min_factor: float = 0.02
    gamma: float = 0.95
    alpha: float = 0.10
    beta: float = 1.0
    refresh_orders: int = 2500
    max_inner: int = 300
    max_outer: int = 400
    sat_stop: float = 0.95
    tol: float = 1e-9
    note: str = "GO 6.3 baseline"

    def sha(self):
        import hashlib
        return hashlib.sha256(json.dumps(dataclasses.asdict(self), sort_keys=True).encode()).hexdigest()

    def as_dict(self):
        return dataclasses.asdict(self)


ENVELOPE = {  # GO 8.3 default allowed values; continuous interior values are permitted
    "a_init": (0.05, 0.30), "theta0_factor": (0.25, 0.95), "theta_min_factor": (0.005, 0.02),
    "gamma": (0.90, 0.97), "alpha": (0.05, 0.25), "beta": (0.5, 32.0),
    "max_inner": (1, 1200), "max_outer": (1, 600), "refresh_orders": (500, 2500)}


def check_envelope(cfg):
    bad = []
    for k, (lo, hi) in ENVELOPE.items():
        v = getattr(cfg, k)
        if not (lo <= v <= hi):
            bad.append({"param": k, "value": v, "allowed": [lo, hi]})
    return {"in_envelope": not bad, "violations": bad}


def require_cuda(device):
    """GO 10.2: fail-closed. A silent CPU fallback is never taken."""
    if device is None or not str(device).startswith("cuda"):
        raise ValueError(f"OUTSIDE_AUTHORISED_SCIENCE_ENVELOPE: native CUDA required, got {device!r}")
    if not torch.cuda.is_available():
        raise RuntimeError("OUTSIDE_AUTHORISED_SCIENCE_ENVELOPE: CUDA requested but unavailable")
    return device


def make_solver(a, device="cuda"):
    require_cuda(device)
    return CNNJacobiSolver(a["D"], a["Ccap"], a["lam_cap"], a["x0s"], s=a["s"], pins=a["pins"],
                           gamma_s=0.0, costs=CostConfig(eps_time=0.0, mu_conc=0.0),
                           update="redblack", dtype="float64", device=device)


class B1Field(torch.nn.Module):
    """The force field: F_TBC (two explicit adjacent-time matmuls) + F_CAP. No learned weight."""

    def __init__(self, donor_field, D, K):
        super().__init__()
        self.f0 = donor_field
        td = donor_field.lam.dtype
        self.register_buffer("Dm", torch.tensor(np.asarray(D, float), dtype=td,
                                                device=donor_field.lam.device))
        self.K = K

    def forward(self, x):
        B, N, K, M = x.shape
        Dm = self.Dm
        f = x.new_zeros(B, N, K, M)
        f[:, :, 1:, :] = x[:, :, :-1, :] @ Dm                       # km1: contracts D[i, o]
        nxt = torch.cat([x[:, :, 1:, :], x[:, :, -1:, :]], dim=2)   # frozen Neumann right edge
        f = f + nxt @ Dm.transpose(0, 1)                            # kp1: contracts D[o, i]
        occ = torch.einsum("nkm,bnkm->bkm", self.f0.oms, x)
        f = f + self.f0.lam.view(1, 1, K, -1) * (occ.unsqueeze(1)
                                                 - self.f0.Cc.view(1, 1, K, -1)) * self.f0.oms.unsqueeze(0)
        return f


def fast_field(sol, a):
    return B1Field(sol.field, a["D"], a["K"])


# --------------------------------------------------------------------------- shared initializer
def shared_template(U, a_init):
    """GO 6.1: z[k,m] = 1 + a_init*(2U-1), then row-normalised over the station axis.

    U is the candidate-independent base draw. a_init is the only candidate-tunable quantity here,
    and it scales the template's contrast without changing the distribution family.
    """
    z = 1.0 + a_init * (2.0 * np.asarray(U, dtype=np.float64) - 1.0)
    return z / z.sum(axis=1, keepdims=True)


def shared_x_init(U, a_init, N, K, M, x0s, pins, seeds_count=1):
    """One template, broadcast to all N UAVs, then each UAV's own physical state written over it.

    The override order is fixed and asserted: (1) the real current/birth Hub row, (2) that UAV's
    own committed pins and history, (3) row normalisation. Returns [B, N, K, M] where every batch
    member b uses that seed's own template.
    """
    tpl = shared_template(U, a_init)                       # (K, M), identical for every UAV
    x = np.broadcast_to(tpl[None, :, :], (N, K, M)).copy()
    x[:, 0, :] = np.asarray(x0s, dtype=np.float64)         # 1. real current/birth Hub row
    for (u, k), m in sorted(pins.items()):                 # 2. that UAV's committed pins
        x[u, k, :] = 0.0
        x[u, k, m] = 1.0
    s = x[:, 1:, :].sum(2, keepdims=True)                  # 3. normalisation check on free rows
    if not np.all(np.isfinite(s)) or float(np.abs(s - 1.0).max()) > 1e-12:
        x[:, 1:, :] = x[:, 1:, :] / s
    return np.repeat(x[None], seeds_count, axis=0)


def prepare_x(sol, x_init):
    """Hand the initializer to the device. The solver's own row-0/pin write is idempotent here
    because shared_x_init has already applied exactly the same overrides."""
    x_np = np.array(x_init, float)
    x_np[:, :, 0, :] = sol.x0s[None]
    for (pi, pk), pmu in sol.pins.items():
        x_np[:, pi, pk, :] = 0.0
        x_np[:, pi, pk, pmu] = 1.0
    return torch.tensor(x_np, dtype=sol._td, device=sol.device)


# --------------------------------------------------------------------------- sweep / solve
def complete_sweep(field, sol, x, theta, active, alpha):
    """One COMPLETE red-black sweep: both colours, field, softmax, normalisation, under-relaxation,
    clone, mask and the dx reduction."""
    B, N, K, _M = x.shape
    xo = x.clone()
    for cmask in sol.colors:
        f = field(x)
        z = -f / theta.view(B, 1, 1, 1)
        z = z - z.amax(3, keepdim=True)
        e = z.exp()
        xin = (1 - alpha) * x + alpha * (e / e.sum(3, keepdim=True))
        cond = active.view(B, 1, 1, 1) & sol.updmask.view(1, N, K, 1) & cmask.view(1, 1, K, 1)
        x = torch.where(cond, xin, x)
    dxb = (x - xo).abs().reshape(B, -1).amax(1)
    return x, dxb


def theta_c_shared(a, cfg, reg, field_seed, refresh_start, device="cuda"):
    """measure_theta_c_full(n=15, seed=0, tol=1e-9, chunk=5) evaluated with THIS engine and THIS
    initializer protocol. GO 6.2 forbids quietly reusing the old per-UAV initializer here."""
    sol = make_solver(a, device)
    field = fast_field(sol, a)
    thresh = (1.0 / a["M"] + 1.0) / 2.0
    tcs = float(theta_c_scalar_multi(a["D"], a["Ccap"], a["lam_cap"], a["N"]))
    ladder = np.geomspace(3.0 * tcs, 0.005 * tcs, THETA_N)
    U = reg.base_U(field_seed, refresh_start, a["K"], a["M"])
    parts, pos = [], 0
    sizes = [min(THETA_CHUNK, THETA_N - i) for i in range(0, THETA_N, THETA_CHUNK)]
    for b in sizes:
        rungs = ladder[pos:pos + b]
        x = prepare_x(sol, shared_x_init(U, cfg.a_init, a["N"], a["K"], a["M"], a["x0s"],
                                         a["pins"], seeds_count=b))
        th = torch.tensor(np.asarray(rungs, float), dtype=sol._td, device=sol.device)
        done = torch.zeros(b, dtype=torch.bool, device=sol.device)
        for _ in range(THETA_MAX_INNER):
            act = ~done
            if not bool(act.any()):
                break
            x, dxb = complete_sweep(field, sol, x, th, act, cfg.alpha)
            done = done | (act & (dxb < THETA_TOL))
        parts.append(x[:, :, 1:, :].amax(3).reshape(b, -1).mean(1).double().cpu().numpy())
        pos += b
    mp = np.concatenate(parts)
    tc, crossed = float(ladder[-1]), False
    for j in range(1, THETA_N):
        if (mp[j - 1] - thresh) * (mp[j] - thresh) < 0:
            tc = float(ladder[j - 1] + (thresh - mp[j - 1]) * (ladder[j] - ladder[j - 1])
                       / (mp[j] - mp[j - 1]))
            crossed = True
            break
    return {"theta_c": tc, "ladder": ladder.tolist(), "sat_curve": mp.tolist(),
            "threshold": thresh, "tcs_analytic": tcs, "ladder_crossed": crossed,
            "theta_c_is_ladder_floor_fallback": not crossed}


def solve(a, cfg, reg, field_seed, refresh_start, theta_c, device="cuda", seeds_count=1):
    """The annealing solve. Raw closure is reported in three separate fields, never merged."""
    sol = make_solver(a, device)
    field = fast_field(sol, a)
    U = reg.base_U(field_seed, refresh_start, a["K"], a["M"])
    B = seeds_count
    x = prepare_x(sol, shared_x_init(U, cfg.a_init, a["N"], a["K"], a["M"], a["x0s"], a["pins"],
                                     seeds_count=B))
    th = torch.full((B,), cfg.theta0_factor * theta_c, dtype=sol._td, device=sol.device)
    tmin = torch.full((B,), cfg.theta_min_factor * theta_c, dtype=sol._td, device=sol.device)
    dx_last = torch.ones(B, dtype=sol._td, device=sol.device)
    done = torch.zeros(B, dtype=torch.bool, device=sol.device)
    floor = torch.zeros(B, dtype=torch.bool, device=sol.device)
    closed = torch.zeros(B, dtype=torch.bool, device=sol.device)
    th_term = torch.full((B,), float("nan"), dtype=sol._td, device=sol.device)
    sat = torch.zeros(B, dtype=sol._td, device=sol.device)
    sweeps = 0
    outer = 0
    for o in range(cfg.max_outer):
        outer = o + 1
        inner_done = done.clone()
        for _ in range(cfg.max_inner):
            act = ~inner_done
            if not bool(act.any()):
                break
            x, dxb = complete_sweep(field, sol, x, th, act, cfg.alpha)
            sweeps += 1
            dx_last = torch.where(act, dxb, dx_last)
            inner_done = inner_done | (act & (dxb < cfg.tol))
        sat = x[:, :, 1:, :].amax(3).reshape(B, -1).mean(1)
        at_floor = th <= tmin * (1 + 1e-12)
        rc = (dx_last < cfg.tol) & (sat >= cfg.sat_stop)
        newly = (~done) & (rc | at_floor)
        th_term = torch.where(newly, th, th_term)
        floor = floor | (newly & at_floor)
        closed = closed | (newly & rc)
        done = done | newly
        if bool(done.all()):
            break
        th = torch.where(done, th, torch.maximum(th * cfg.gamma, tmin))
    dxf = [bool(v) for v in (dx_last < cfg.tol).cpu().numpy()]
    pol = [bool(v) for v in (sat >= cfg.sat_stop).cpu().numpy()]
    fl = [bool(v) for v in floor.cpu().numpy()]
    return {"x": x.double().cpu().numpy(),
            "DX_LAST": dx_last.double().cpu().numpy().tolist(),
            "SAT": sat.double().cpu().numpy().tolist(),
            "theta_terminal": th_term.double().cpu().numpy().tolist(),
            "DX_FIXED_POINT": dxf, "POLARISED": pol, "THETA_FLOOR_REACHED": fl,
            "outer_levels_executed": outer, "sweeps": sweeps,
            "forwards": sweeps * 2, "theta_c_used": theta_c, "field_seed": field_seed,
            "refresh_start": refresh_start}


def raw_state(res, i=0, guidance_stable=None):
    """GO 11.5: the three closure facts are reported separately and never collapsed."""
    if res["DX_FIXED_POINT"][i] and res["POLARISED"][i]:
        return "RAW_CLOSED"
    if guidance_stable is None:
        return "RAW_UNCLOSED_UNKNOWN_STABILITY"
    return "RAW_UNCLOSED_GUIDANCE_STABLE" if guidance_stable else "RAW_UNSTABLE"


def observer(a, cfg, x_terminal, theta_terminal, sweeps=20, device="cuda", keep=()):
    """Fixed-theta observer sweeps. Read-only: never feeds back, never re-seeds, never replaces
    the formal terminal field."""
    sol = make_solver(a, device)
    field = fast_field(sol, a)
    B = x_terminal.shape[0]
    x = torch.tensor(np.array(x_terminal, float), dtype=sol._td, device=sol.device)
    th = torch.tensor(np.asarray(theta_terminal, float), dtype=sol._td, device=sol.device)
    act = torch.ones(B, dtype=torch.bool, device=sol.device)
    traj, dxb = [], None
    for i in range(sweeps):
        x, dxb = complete_sweep(field, sol, x, th, act, cfg.alpha)
        if (i + 1) in keep:
            traj.append({"sweep": i + 1, "x": x.double().cpu().numpy()})
    return {"x": x.double().cpu().numpy(), "sweeps": sweeps,
            "dx_last": dxb.double().cpu().numpy().tolist(), "checkpoints": traj}


def engine_counters(sol, field):
    tp = sum(p.numel() for p in field.parameters() if p.requires_grad)
    tp += sum(p.numel() for p in sol.field.parameters() if p.requires_grad)
    return {"TRAINABLE_PARAMETER_COUNT": int(tp), "OPTIMIZER_STEP_COUNT": 0,
            "TRAINING_EPOCH_COUNT": 0, "CPU_FALLBACK_COUNT": 0,
            "grad_enabled_any": bool(any(p.requires_grad for p in field.parameters()))}


def prefix_timing(a, cfg, reg, batch_size, *, sweeps=12, warmups=2, repeats=3, device="cuda"):
    sol = make_solver(a, device)
    field = fast_field(sol, a)
    tcs = float(theta_c_scalar_multi(a["D"], a["Ccap"], a["lam_cap"], a["N"]))
    U = reg.base_U(0, 0, a["K"], a["M"])
    xi = shared_x_init(U, cfg.a_init, a["N"], a["K"], a["M"], a["x0s"], a["pins"],
                       seeds_count=batch_size)
    theta = torch.full((batch_size,), cfg.theta0_factor * tcs, dtype=sol._td, device=sol.device)
    active = torch.ones(batch_size, dtype=torch.bool, device=sol.device)
    torch.cuda.reset_peak_memory_stats()
    walls = []
    for r in range(warmups + repeats):
        x = prepare_x(sol, xi)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(sweeps):
            x, _dx = complete_sweep(field, sol, x, theta, active, cfg.alpha)
        torch.cuda.synchronize()
        w = time.perf_counter() - t0
        if r >= warmups:
            walls.append(w)
    med = statistics.median(walls)
    return {"B": batch_size, "sweeps": sweeps, "walls_s": walls, "median_wall_s": med,
            "amortized_forward_equivalent_s": med / (2 * sweeps),
            "live_device": str(x.device), "live_dtype": str(x.dtype),
            "peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30,
            "timing_scope": ("complete red-black sweep end to end, synchronised only at the "
                             "prefix boundary; raw kernel time never substituted")}
