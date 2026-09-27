from __future__ import annotations

import json
import os
import time
from pathlib import Path

import h5py
import numpy as np
import torch

from physical_transport import upwind_step


def _sync(device: str) -> None:
    """Synchronize CUDA work before recording generation timings."""

    if str(device).startswith("cuda"):
        torch.cuda.synchronize()


def _save(path: Path, value: np.ndarray, attrs: dict) -> None:
    """Write one compressed concentration field and atomically replace its target."""

    tmp = path.with_suffix(".tmp")
    with h5py.File(tmp, "w") as file:
        file.create_dataset("C", data=value, compression="gzip")
        for key, item in attrs.items():
            file.attrs[key] = item
    os.replace(tmp, path)


def generate(
    wind_dir: Path,
    sigma_path: Path,
    out_dir: Path,
    source: torch.Tensor,
    *,
    steps: int,
    dt: float = 0.5,
    ub: float = -1.0,
    vb: float = 0.0,
    source_rate: float = 0.1,
    device: str = "cpu",
    max_iter: int = 200,
    tol: float = 1e-7,
    flip_u: bool = False,
) -> None:
    """Generate pollution states paired one-to-one with raw SCALED wind steps."""

    wind_dir = Path(wind_dir)
    sigma_path = Path(sigma_path)
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {out_dir}")
    if steps < 1 or source_rate < 0:
        raise ValueError("steps must be positive and source_rate must be non-negative")
    out_dir.mkdir(parents=True, exist_ok=True)

    solid_np = np.load(sigma_path).squeeze() != 0
    solid = torch.from_numpy(solid_np).to(device)
    source = source.to(device=device, dtype=torch.float32).masked_fill(solid, 0)
    if source.shape != solid.shape:
        raise ValueError("source and sigma shapes do not match")
    np.save(out_dir / "source.npy", source.cpu().numpy())
    emission = source * source_rate
    c = torch.zeros_like(source)

    manifest = {
        "steps": steps,
        "dt": dt,
        "ub": ub,
        "vb": vb,
        "source_rate": source_rate,
        "velocity_sign": "u_negated" if flip_u else "raw",
        "initial_state": "zero",
        "pairing": "wind[t] advances C[t] to saved pollution[t]",
        "x_boundary": "ambient inflow and open outflow",
        "y_boundary": "SCALED vb with open directional flux",
        "z_boundary": "no flux",
        "solid_boundary": "no flux",
        "wind_dir": str(wind_dir.resolve()),
        "sigma_path": str(sigma_path.resolve()),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _save(
        out_dir / "initial.h5",
        c.cpu().numpy(),
        {"state": "initial", "physical_time": 0.0, "dt": dt, "ub": ub, "vb": vb},
    )

    mass_path = out_dir / "mass.jsonl"
    for t in range(steps):
        total_start = time.perf_counter()
        read_start = total_start
        wind_path = wind_dir / f"{t:06d}.h5"
        with h5py.File(wind_path, "r") as file:
            uvw = torch.from_numpy(file["uvw"][:]).to(device=device, dtype=torch.float32)
        if flip_u:
            uvw[0].neg_()
        _sync(device)
        read_seconds = time.perf_counter() - read_start
        if uvw.shape != (3, *solid.shape):
            raise ValueError(f"unexpected wind shape at t={t}: {tuple(uvw.shape)}")

        old_mass = float(c.sum().item())
        step_start = time.perf_counter()
        result = upwind_step(
            c,
            uvw[0],
            uvw[1],
            uvw[2],
            solid,
            emission,
            dt=dt,
            ub=ub,
            vb=vb,
            max_iter=max_iter,
            tol=tol,
        )
        _sync(device)
        step_seconds = time.perf_counter() - step_start
        c = result.concentration
        new_mass = float(c.sum().item())
        injected = dt * float(emission.sum().item())
        removed = dt * float(result.outflow.item())
        balance = new_mass - old_mass - injected + removed
        attrs = {
            "t": t,
            "wind_t": t,
            "state": "post_step",
            "physical_time": (t + 1) * dt,
            "dt": dt,
            "ub": ub,
            "vb": vb,
            "velocity_sign": "u_negated" if flip_u else "raw",
            "iterations": result.iterations,
            "residual": result.residual,
            "mass_balance_error": balance,
        }
        save_start = time.perf_counter()
        _save(out_dir / f"{t:06d}.h5", c.cpu().numpy(), attrs)
        save_seconds = time.perf_counter() - save_start
        total_seconds = time.perf_counter() - total_start
        with mass_path.open("a") as file:
            file.write(json.dumps({
                "t": t,
                "mass": new_mass,
                "outflow": removed,
                "balance": balance,
                "read_seconds": read_seconds,
                "step_seconds": step_seconds,
                "save_seconds": save_seconds,
                "total_seconds": total_seconds,
            }) + "\n")
