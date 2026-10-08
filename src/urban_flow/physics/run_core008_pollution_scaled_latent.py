"""Pollutant transport driven by the SCALED 1 m wind of output/core008/physics/scaled_latent (from wind step 0),
solved on that run's stored 4 m coarsened wind (bottom 64 m, [16,704,768]).

Why 4 m: the 1 m grid ([64,2816,3072], 5.5e8 cells) needs tens of GB per transport step; the 4 m frames are
already stored for every wind step (wind4m_000..100.npy, m/s, +x east, zero in conservative solid cells).
Solver: Yuhang physical_transport.upwind_step unchanged. It assumes unit spacing, so velocities are passed in
cells per second (u / 4 m) and dt in seconds. One SCALED step = 25 s -> 50 sub-steps of dt 0.5 s, wind linearly
interpolated between frames. Source: same physical placement idea as the 1024 run (line source upstream of the
city): domain x 520..600 m, y 848..3248 m, z 8..32 m; rate 0.1 per cell per second. Top boundary (64 m): no flux.
Outputs: output/core008/physics/scaled_latent/pollution/
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = repo_root()
RUN = ROOT / "output/core008/physics/scaled_latent"
OUT = RUN / "pollution"
OUT.mkdir(exist_ok=True)
TRANSPORT = (
    ROOT
    / "src/urban_flow/physics/wind_pollution_code/code/vendor/yuhang/data_generation/physical_transport.py"
)
spec = importlib.util.spec_from_file_location("physical_transport", TRANSPORT)
T = importlib.util.module_from_spec(spec)
sys.modules["physical_transport"] = T
spec.loader.exec_module(T)

CELL_M = 4.0
DOMAIN_LOWER = (480, 640)  # domain metres of this run's origin
STEP_SECONDS, SUBSTEPS, DT = 25.0, 50, 0.5
UB_MS, VB_MS, RATE = 1.0, 0.0, 0.1
SOURCE_M = {"x": (520, 600), "y": (848, 3248), "z": (8, 32)}
MAX_ITER, TOL = 200, 1e-6
device = torch.device("cuda")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    solid = np.load(RUN / "temperature/solid_4m_zyx.npy")  # [16,704,768] conservative 4 m
    solid_t = torch.from_numpy(solid).to(device)
    sl = (
        slice(SOURCE_M["z"][0] // 4, SOURCE_M["z"][1] // 4),
        slice((SOURCE_M["y"][0] - DOMAIN_LOWER[1]) // 4, (SOURCE_M["y"][1] - DOMAIN_LOWER[1]) // 4),
        slice((SOURCE_M["x"][0] - DOMAIN_LOWER[0]) // 4, (SOURCE_M["x"][1] - DOMAIN_LOWER[0]) // 4),
    )
    source = torch.zeros(solid.shape, dtype=torch.float32, device=device)
    source[sl] = 1.0
    source = source.masked_fill(solid_t, 0)
    emission = source * RATE
    np.save(OUT / "source.npy", source.cpu().numpy().astype(np.uint8))
    frames = sorted(RUN.glob("wind/wind4m_*.npy"))
    n = len(frames) - 1
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "transport": str(TRANSPORT),
                "transport_sha256": hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),
                "wind_run": str(RUN),
                "wind_grid": "4 m coarsened SCALED 1 m wind, bottom 64 m",
                "wind_steps": n,
                "step_seconds": STEP_SECONDS,
                "substeps_per_wind_step": SUBSTEPS,
                "dt_seconds": DT,
                "velocity_units": "m/s divided by 4 m -> cells per second (solver assumes unit spacing)",
                "ub_m_s": UB_MS,
                "vb_m_s": VB_MS,
                "source_rate_per_cell_per_s": RATE,
                "source_domain_m": SOURCE_M,
                "source_cells_zyx": [[s.start, s.stop] for s in sl],
                "wind_in_substeps": "linear interpolation between consecutive frames; frame 0 = rest",
                "boundaries": "x: ambient inflow ub / open outflow; y: vb; z (0 and 64 m) and solids: no flux",
            },
            indent=2,
        )
        + "\n"
    )
    c = torch.zeros(solid.shape, dtype=torch.float32, device=device)
    prev = torch.from_numpy(np.load(frames[0])).to(device) / CELL_M
    mass_log, slices = [], []
    layer = 3
    for k in range(1, n + 1):
        t0 = time.time()
        cur = torch.from_numpy(np.load(frames[k])).to(device) / CELL_M
        iters = []
        for s in range(SUBSTEPS):
            f = (s + 1) / SUBSTEPS
            uvw = (1 - f) * prev + f * cur
            res = T.upwind_step(
                c,
                uvw[0],
                uvw[1],
                uvw[2],
                solid_t,
                emission,
                dt=DT,
                ub=UB_MS / CELL_M,
                vb=VB_MS / CELL_M,
                max_iter=MAX_ITER,
                tol=TOL,
            )
            c = res.concentration
            iters.append(res.iterations)
        prev = cur
        np.save(OUT / f"concentration_{k:03d}_float16.npy", c.cpu().numpy().astype(np.float16))
        slices.append(c[layer].cpu().numpy().astype(np.float16))
        entry = {
            "wind_step": k,
            "solver_time": k * STEP_SECONDS,
            "mass": float(c.sum().item()),
            "max": float(c.max().item()),
            "mean_iterations": float(np.mean(iters)),
            "seconds": time.time() - t0,
        }
        mass_log.append(entry)
        (OUT / "mass.json").write_text(json.dumps(mass_log, indent=2) + "\n")
        log(
            f"wind step {k}/{n}: {entry['seconds']:.1f}s  mass {entry['mass']:.1f}  max {entry['max']:.3f}  iters {entry['mean_iterations']:.1f}"
        )
    np.save(OUT / f"slices_z{layer * 4}m_tyx_float16.npy", np.stack(slices))
    log("Pollution complete.")


if __name__ == "__main__":
    main()
