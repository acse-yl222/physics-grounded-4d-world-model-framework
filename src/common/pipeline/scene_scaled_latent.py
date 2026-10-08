"""Scene-configured SCALED wind and controlled temperature transfer.

Stores every latent checkpoint and 8 m wind frame with lossless NPZ compression;
latent/float16 quantisation matches the reference checkpoint convention. Live
inference stays float32. An extra float32 latest checkpoint supports exact resume.
"""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.locations import code_path
from common.layout import repo_root
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import torch

from common.pipeline.paths import ROOT, project_path


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save_npz(path, **arrays):
    path = Path(path)
    tmp = path.with_suffix(".partial")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
    tmp.replace(path)


def save_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(".partial")
    tmp.write_text(json.dumps(value, indent=2))
    tmp.replace(path)


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/white_city/scaled_latent.json")
    ap.add_argument("--stage", choices=["wind", "temperature", "all"], default="all")
    args = ap.parse_args()
    cfg = json.loads(project_path(args.config).read_text())
    geom = project_path(cfg["geometry"])
    out = project_path(cfg["output"])
    wind = out / "wind"
    temp = out / "temperature"
    lat = wind / "latent"
    for p in (wind, temp, lat):
        p.mkdir(parents=True, exist_ok=True)
    if cfg.get("scaled_repo"):
        scaled_repo = project_path(cfg["scaled_repo"])
        if not (scaled_repo / "scaled").is_dir():
            raise ValueError(f"SCALED source checkout not found: {scaled_repo}")
        # Explicit legacy source dependency; installed SCALED needs no path override.
        sys.path.insert(0, str(scaled_repo))
    from urban_flow.physics.wind import scaled_latent as kernel
    from urban_flow.physics.wind_temperature_teacher.code import cloud_workflow as cw

    if cfg.get("weights_root"):
        weights = project_path(cfg["weights_root"])
    elif cfg.get("scaled_repo"):
        weights = project_path(cfg["scaled_repo"]) / "weight"
    else:
        raise ValueError("Set wind.weights_root or wind.scaled_repo for SCALED checkpoints")
    torch.set_num_threads(8)
    torch.manual_seed(cfg["thermal"]["seed"])
    torch.backends.cudnn.benchmark = True
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")
    device = torch.device("cuda")
    factor = cfg["coarse_factor"]
    cell = cfg["cell_m"]
    coarse = cell * factor
    metadata = json.loads((geom / "metadata.json").read_text())
    assert metadata["spacing_xyz_m"] == [cell] * 3
    full = np.load(geom / "solid.npy", mmap_mode="r")
    solid = np.array(full[: cfg["wind_layers"]])
    del full
    assert solid.shape[0] == 64 and solid.shape[1] % 256 == solid.shape[2] % 256 == 0
    solid[0] = True
    geo = cw.coarse_geometry(solid, factor=factor, spacing=float(coarse))
    record = {
        "config": cfg,
        "geometry_metadata_sha256": digest(geom / "metadata.json"),
        "solid_sha256": digest(geom / "solid.npy"),
        "weights": {n: digest(weights / n) for n in ["compression.pth", "inference.pth"]},
        "temperature_weights_sha256": digest(project_path(cfg["temperature_checkpoint"])),
        "code": {
            name: digest(code_path(name))
            for name in [
                "src/common/pipeline/scene_scaled_latent.py",
                "src/urban_flow/physics/wind/scaled_latent.py",
                "src/urban_flow/physics/wind_temperature_teacher/code/cloud_workflow.py",
            ]
        },
        "shape_zyx": list(solid.shape),
        "cell_m": cell,
        "coarse_cell_m": coarse,
        "local_origin_xyz_m": metadata["source_region_origin_xyz_m"],
        "environment": {
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "gpu": torch.cuda.get_device_name(),
        },
        "limits": [
            "New-geometry surrogate transfer; no CFD or measured validation.",
            "Wind input clipped at 128 m; full GLB and 192 m geometry retained.",
            "50 seconds/step is a grid-scaled interpretation, not a calibrated clock.",
            "Horizontal compass alignment unverified without GLB coordinate metadata.",
            "8 m thermal grid differs from checkpoint training; results are transfer diagnostics.",
            "Thermal conditions are controlled assumptions, not White City measurements.",
        ],
    }
    manifest = out / "run_config.json"
    if manifest.exists() and json.loads(manifest.read_text()) != record:
        raise RuntimeError("Input/config/code changed: use a new run directory.")
    save_json(manifest, record)
    np.save(wind / f"solid_{cell}m_zyx.npy", solid)
    for key, value in geo.items():
        suffix = "yx.npy" if key == "height" else "zyx.npy"
        np.save(temp / f"{key}_{coarse}m_{suffix}", value)

    def check_space():
        if shutil.disk_usage(out).free < cfg["min_free_gib"] * 1024**3:
            raise RuntimeError(
                "Disk reserve reached; run safely stopped. Resume after freeing space."
            )

    def wind_path(k):
        return wind / f"wind{coarse}m_{k:03d}.npz"

    if args.stage in ("wind", "all"):
        enc, net = kernel.load_models(weights)
        log("Strict checkpoint loading passed; models on CUDA")
        encoded = wind / "encoded_geometry.npz"
        if encoded.exists():
            with np.load(encoded) as a:
                state = torch.from_numpy(a["initial"])
                latent_geo = torch.from_numpy(a["geometry"])
        else:
            t = time.time()
            state, latent_geo = kernel.encode_domain(solid, enc)
            state = state / 10
            latent_geo = latent_geo / 10
            save_npz(encoded, initial=state.numpy(), geometry=latent_geo.numpy())
            log(f"Geometry encoded in {time.time() - t:.1f}s")
        metrics_path = wind / "metrics.json"
        metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {"steps": []}
        resume = wind / "latest_float32.npz"
        first = 0
        if resume.exists():
            with np.load(resume) as a:
                state = torch.from_numpy(a["state"])
                first = int(a["step"])
            metrics["steps"] = [r for r in metrics["steps"] if r["step"] <= first]
            if not wind_path(first).exists():
                raise RuntimeError("Resume checkpoint has no corresponding wind frame")
            log(f"Resuming after completed step {first}")
        if not wind_path(0).exists():
            decoded = kernel.decode_domain(state, enc) * 3 * (~solid)
            prev = cw.coarse_wind(decoded, geo["solid"], factor)
            del decoded
            save_npz(wind_path(0), uvw=prev)
        else:
            with np.load(wind_path(first)) as a:
                prev = a["uvw"]
        for k in range(first + 1, cfg["wind_steps"] + 1):
            check_space()
            start = time.time()
            state = kernel.latent_step(state, latent_geo, net)
            if not torch.isfinite(state).all():
                raise RuntimeError("Non-finite latent")
            save_npz(lat / f"{k:04d}.npz", state=state.numpy().astype(np.float16))
            infer = time.time() - start
            decoded = kernel.decode_domain(state, enc) * 3 * (~solid)
            mapped = cw.coarse_wind(decoded, geo["solid"], factor)
            save_npz(wind_path(k), uvw=mapped)
            if k == cfg["wind_steps"]:
                check_space()
                # Final 2 m field remains directly loadable, with raw NN4PDEs u convention.
                final = wind / f"velocity_final_{cell}m_raw_czyx_float16.npy"
                target = np.lib.format.open_memmap(
                    final, mode="w+", dtype=np.float16, shape=decoded.shape
                )
                for c in range(3):
                    target[c] = decoded[c]
                target.flush()
                del target
            del decoded
            speed = np.linalg.norm(mapped, axis=0)[~geo["solid"]]
            row = {
                "step": k,
                "time_seconds": k * cfg["step_seconds"],
                "seconds": time.time() - start,
                "inference_seconds": infer,
                "fluid_speed_mean": float(speed.mean()),
                "fluid_speed_max": float(speed.max()),
                "fluid_speed_p95": float(np.percentile(speed, 95)),
                "change_rms": float(np.sqrt(np.mean((mapped - prev) ** 2))),
                "gpu_peak_gib": torch.cuda.max_memory_allocated() / 1024**3,
            }
            metrics["steps"].append(row)
            save_json(metrics_path, metrics)
            save_npz(resume, state=state.numpy(), step=np.array(k))
            prev = mapped
            save_json(
                out / "status.json",
                {
                    "stage": "wind",
                    "completed_steps": k,
                    "total_steps": cfg["wind_steps"],
                    "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            log(
                f"Wind {k}/{cfg['wind_steps']}: {row['seconds']:.1f}s; mean {row['fluid_speed_mean']:.4f} m/s"
            )
        del enc, net
        torch.cuda.empty_cache()

    if args.stage in ("temperature", "all"):
        thermal = cfg["thermal"]
        spin = cfg["wind_steps"] - math.ceil(450 / cfg["step_seconds"])

        def wind_at(seconds):
            t = max(seconds, 0) / cfg["step_seconds"]
            lo = math.floor(t)
            f = t - lo
            with np.load(wind_path(spin + lo)) as a:
                uvw = a["uvw"]
            if f > 1e-10:
                with np.load(wind_path(spin + lo + 1)) as a:
                    uvw = (1 - f) * uvw + f * a["uvw"]
            return uvw.astype(np.float32)

        for k in range(spin, cfg["wind_steps"] + 1):
            if not wind_path(k).is_file():
                raise FileNotFoundError(wind_path(k))
        times = [-180, -90, 0, 90, 180, 270, 360, 450]
        initial = np.full(geo["solid"].shape, thermal["ambient_c"], np.float32)
        initial[geo["roof"]] = thermal["roof_c"]
        refs = [initial]
        solver = []
        for t in times[:-1]:
            value, stats = cw.physical_step(refs[-1], wind_at(t), geo, thermal, device)
            refs.append(value)
            solver.append({"end_seconds": t + 90, **stats})
            log(f"Temperature reference {t + 90}s")
        for k, a in enumerate(refs):
            np.save(temp / f"reference_{k:03d}.npy", a)
        save_json(
            temp / "physical_solver.json",
            {"times_seconds": times, "frames": solver, "wind_start_step": spin},
        )
        model, stats, patch = cw.load_temperature(
            project_path(cfg["temperature_checkpoint"]), device
        )
        history = np.stack(refs[:3])
        persistence = history[-1].copy()
        rows = []
        for k in range(thermal["temperature_steps"]):
            check_space()
            uvw = wind_at(k * 90)
            for mode in ["recursive", "one_step"]:
                h = history if mode == "recursive" else np.stack(refs[k : k + 3])
                pred = cw.predict(
                    model,
                    cw.make_input(h, uvw, geo, thermal, stats),
                    stats,
                    patch,
                    tuple(thermal["temperature_overlap"]),
                    device,
                )
                np.save(temp / f"{mode}_{k + 1:03d}.npy", pred)
                rows.append(
                    {
                        "time_seconds": (k + 1) * 90,
                        "mode": mode,
                        **cw.metrics(pred, refs[k + 3], ~geo["solid"]),
                    }
                )
                if mode == "recursive":
                    history = np.concatenate([history[1:], pred[None]], axis=0)
            rows.append(
                {
                    "time_seconds": (k + 1) * 90,
                    "mode": "persistence",
                    **cw.metrics(persistence, refs[k + 3], ~geo["solid"]),
                }
            )
            save_json(temp / "metrics.json", rows)
            log(f"Temperature prediction {(k + 1) * 90}s complete")
        save_json(
            out / "status.json",
            {
                "stage": "wind_temperature_complete",
                "wind_steps": cfg["wind_steps"],
                "temperature_steps": thermal["temperature_steps"],
            },
        )
    log("Requested stages complete")


if __name__ == "__main__":
    main()
