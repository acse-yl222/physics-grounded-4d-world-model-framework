"""Controlled upstream tracer experiment on stored scene wind frames.

Uses the same Yuhang upwind solver as core008 scaled_latent. Concentration has
arbitrary tracer units: it is not a measured or calibrated PM2.5 prediction.
"""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.locations import code_path
from common.layout import repo_root
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import torch

from common.pipeline.paths import ROOT, project_path
from common.pipeline.scene_scaled_latent import save_npz, save_json, digest, log


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/white_city/scaled_latent.json")
    args = ap.parse_args()
    cfg = json.loads(project_path(args.config).read_text())
    run = project_path(cfg["output"])
    out = run / "pollution"
    out.mkdir(exist_ok=True)
    path = code_path(
        "src/urban_flow/physics/wind_pollution_code/code/vendor/yuhang/data_generation/physical_transport.py"
    )
    spec = importlib.util.spec_from_file_location("scene_tracer_transport", path)
    transport = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = transport
    spec.loader.exec_module(transport)
    torch.set_num_threads(8)
    cell = cfg["cell_m"] * cfg["coarse_factor"]
    device = "cuda"
    solid = np.load(run / f"temperature/solid_{cell}m_zyx.npy")
    nz, ny, nx = solid.shape
    # A west-side line source inside the padding. Bounds expressed in actual metres.
    sx = slice(8, 18)
    sy = slice(int(ny * 0.1), int(ny * 0.9))
    sz = slice(max(1, int(8 / cell)), max(2, int(32 / cell)))
    source = np.zeros(solid.shape, np.float32)
    source[sz, sy, sx] = 0.1
    source[solid] = 0
    assert source.sum() > 0
    np.save(out / "source_rate.npy", source)
    solid_t = torch.as_tensor(solid, device=device)
    emission = torch.as_tensor(source, device=device)
    save_json(
        out / "manifest.json",
        {
            "solver": str(path),
            "solver_sha256": digest(path),
            "cell_m": cell,
            "wind_steps": cfg["wind_steps"],
            "step_seconds": cfg["step_seconds"],
            "substeps_per_frame": 50,
            "dt_seconds": cfg["step_seconds"] / 50,
            "source_rate": 0.1,
            "units": "arbitrary tracer concentration",
            "source_box_local_domain_xyz_m": [
                [sx.start * cell, sx.stop * cell],
                [sy.start * cell, sy.stop * cell],
                [sz.start * cell, sz.stop * cell],
            ],
            "scenario": "Assumed continuous upstream line release, not a measured White City emissions inventory.",
            "boundaries": "x inflow/outflow ub=1 m/s; y vb=0; z and solid faces no flux",
            "storage": "float32 NPZ to avoid float16 overflow; wind float32 interpolated between frames",
        },
    )

    def read(k):
        with np.load(run / f"wind/wind{cell}m_{k:03d}.npz") as f:
            return torch.as_tensor(f["uvw"], device=device) / cell

    prev = read(0)
    c = torch.zeros(solid.shape, device=device)
    rows = []
    dt = cfg["step_seconds"] / 50
    for k in range(1, cfg["wind_steps"] + 1):
        if shutil.disk_usage(out).free < cfg["min_free_gib"] * 1024**3:
            raise RuntimeError("Disk reserve reached")
        start = time.time()
        cur = read(k)
        for j in range(50):
            frac = (j + 1) / 50
            uvw = prev * (1 - frac) + cur * frac
            result = transport.upwind_step(
                c, *uvw, solid_t, emission, dt=dt, ub=1 / cell, vb=0, max_iter=200, tol=1e-6
            )
            c = result.concentration
        if not torch.isfinite(c).all():
            raise RuntimeError("Non-finite tracer field")
        save_npz(out / f"concentration_{k:03d}.npz", concentration=c.cpu().numpy())
        row = {
            "wind_step": k,
            "time_seconds": k * cfg["step_seconds"],
            "sum_concentration": float(c.sum()),
            "volume_integrated_concentration": float(c.sum()) * cell**3,
            "maximum": float(c.max()),
            "seconds": time.time() - start,
        }
        rows.append(row)
        save_json(out / "mass.json", rows)
        prev = cur
        if k % 10 == 0:
            log(f"Tracer {k}/{cfg['wind_steps']}: max {row['maximum']:.4g}")
    save_json(out / "status.json", {"complete": True, "frames": len(rows), "finite": True})


if __name__ == "__main__":
    main()
