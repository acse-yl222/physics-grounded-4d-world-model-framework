"""Pollutant transport driven by the SCALED wind of output/core008/physics/scaled_latent_1024, from wind step 0.

Physics: Yuhang's conservative first-order upwind solver (wind_pollution_code/.../physical_transport.py,
unchanged), the same code that generated the pollution surrogate's training data. Settings follow
wind_pollution_code/code/workflow.py: dt 0.5, ub 1 with u negated (increasing-index convention),
vb 0, source rate 0.1, source cells z 2:8, y 212:812, x 40:60 on the 1024 grid, tol 1e-7, max_iter 200 (tol relaxed to 1e-6 as in workflow.py).
Pairing: the original pairs one transport step with one NN4PDEs step; one SCALED step = 50 NN4PDEs steps,
so each SCALED wind step drives 50 transport sub-steps with the wind linearly interpolated between frames.
Wind: every SCALED latent frame is decoded here to the full 64-layer field (model units x3 = NN4PDEs units).
Outputs: output/core008/physics/scaled_latent_1024/pollution/
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = repo_root()
RUN = ROOT / "output/core008/physics/scaled_latent_1024"
OUT = RUN / "pollution"
OUT.mkdir(exist_ok=True)
TRANSPORT = (
    ROOT
    / "src/urban_flow/physics/wind_pollution_code/code/vendor/yuhang/data_generation/physical_transport.py"
)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


L = _load("latent1024", ROOT / "src/urban_flow/physics/run_core008_scaled_latent_1024.py")
T = _load("physical_transport", TRANSPORT)

SUBSTEPS = 50  # NN4PDEs steps per SCALED step
DT, UB, VB, RATE = 0.5, 1.0, 0.0, 0.1
SOURCE = (slice(2, 8), slice(212, 812), slice(40, 60))
MAX_ITER, TOL = 200, 1e-6  # workflow.py tolerance (1e-7 -> 1e-6, see SOURCE_INFO.json)
device = torch.device("cuda")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    solid = np.load(RUN / "wind/solid_4m_full_zyx.npy")  # [64,1024,1024], z0 forced solid
    solid_t = torch.from_numpy(solid).to(device)
    fluid = (~solid).astype(np.float32)
    source = torch.zeros(solid.shape, dtype=torch.float32, device=device)
    source[SOURCE] = 1.0
    source = source.masked_fill(solid_t, 0)
    emission = source * RATE
    np.save(OUT / "source.npy", source.cpu().numpy().astype(np.uint8))
    enc, _ = L.load_models()
    steps = sorted(RUN.glob("wind/latent/*.pt"))
    n = len(steps)
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "transport": str(TRANSPORT),
                "transport_sha256": L.sha256(TRANSPORT),
                "wind_run": str(RUN),
                "wind_steps": n,
                "substeps_per_wind_step": SUBSTEPS,
                "dt": DT,
                "ub": UB,
                "vb": VB,
                "source_rate": RATE,
                "source_cells_zyx": [[s.start, s.stop] for s in SOURCE],
                "source_domain_m": {
                    "x": [40 * 4, 60 * 4],
                    "y": [212 * 4, 812 * 4],
                    "z": [2 * 4, 8 * 4],
                },
                "velocity": "decoded SCALED latent x3 (NN4PDEs units), u negated -> increasing-index convention, zero in solid",
                "wind_in_substeps": "linear interpolation between consecutive SCALED frames; frame 0 = rest",
                "grid": "4 m cells treated as unit spacing (dx = 1 in solver units, as in the original data generation)",
                "boundaries": "x: ambient inflow ub / open outflow; y: vb; z and solids: no flux",
            },
            indent=2,
        )
        + "\n"
    )
    layer = 3  # 12-16 m slice for the animation
    done = sorted(OUT.glob("concentration_*_float16.npy"))
    if done:  # resume after the last saved wind step
        k0 = int(done[-1].stem.split("_")[1])
        c = torch.from_numpy(np.load(done[-1]).astype(np.float32)).to(device)
        with torch.no_grad():
            x = (
                L.decode_domain(torch.load(steps[k0 - 1], weights_only=True).float(), enc)
                * 3
                * fluid
            )
        prev = torch.from_numpy(x).to(device)
        prev[0].neg_()
        torch.cuda.empty_cache()
        mass_log = [m for m in json.loads((OUT / "mass.json").read_text()) if m["wind_step"] <= k0]
        slices = [np.load(f, mmap_mode="r")[layer].astype(np.float16) for f in done]
        log(f"resuming after wind step {k0} (concentration reloaded from float16)")
    else:
        k0 = 0
        c = torch.zeros(solid.shape, dtype=torch.float32, device=device)
        prev = torch.zeros((3, *solid.shape), dtype=torch.float32, device=device)
        mass_log, slices = [], []
    for k, path in enumerate(steps[k0:], start=k0 + 1):
        t0 = time.time()
        latent = torch.load(path, weights_only=True).float()
        with torch.no_grad():
            x = L.decode_domain(latent, enc) * 3 * fluid  # raw NN4PDEs units
        cur = torch.from_numpy(x).to(device)
        cur[0].neg_()
        del x
        torch.cuda.empty_cache()
        t_dec = time.time() - t0
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
                ub=UB,
                vb=VB,
                max_iter=MAX_ITER,
                tol=TOL,
            )
            c = res.concentration
            iters.append(res.iterations)
        prev = cur
        mass = float(c.sum().item())
        np.save(OUT / f"concentration_{k:03d}_float16.npy", c.cpu().numpy().astype(np.float16))
        slices.append(c[layer].cpu().numpy().astype(np.float16))
        entry = {
            "wind_step": k,
            "solver_time": k * SUBSTEPS * DT,
            "mass": mass,
            "max": float(c.max().item()),
            "mean_iterations": float(np.mean(iters)),
            "decode_seconds": t_dec,
            "seconds": time.time() - t0,
        }
        mass_log.append(entry)
        (OUT / "mass.json").write_text(json.dumps(mass_log, indent=2) + "\n")
        log(
            f"wind step {k}/{n}: {entry['seconds']:.0f}s (decode {t_dec:.0f}s)  mass {mass:.1f}  max {entry['max']:.3f}  iters {entry['mean_iterations']:.1f}"
        )
    np.save(OUT / f"slices_z{layer * 4}m_tyx_float16.npy", np.stack(slices))
    log("Pollution complete.")


if __name__ == "__main__":
    main()
