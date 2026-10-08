"""Yi Qi's 2-D temperature label model (south_kensington_temperature.py, unchanged) driven by the SCALED wind
of output/core008/physics/scaled_latent_1024 instead of DIGIT.

The model reads a 'shared velocity cache' directory when its summary matches the velocity config, so this script
builds that cache from SCALED outputs and core008 geometry, then calls run_temperature_label_pipeline():
  - u, v: horizontal slice at 12-16 m (4 m layer 3) of wind steps 41..100 (statistically steady), 100 s per frame
  - building_mask / height_field: 4 m max-pooled core008 voxels and roof heights
  - vegetation_mask: core008 grass + tree-canopy meshes; urban_mask: everything else that is ground inside the
    building extent (WorldCover 'built-up' proxy); study_area_mask: building extent x 625..3474, y 754..3348 m
  - the model's grid is image-like (row 0 = north, column 0 = west): arrays are flipped in y and v is negated.
Scenario: the model's default summer-afternoon settings (ambient 31.5 C, 2025-07-25 13:00 UTC solar position ...).
Outputs: output/core008/physics/scaled_latent_1024/temperature2d/
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
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = repo_root()
RUN = ROOT / (
    sys.argv[sys.argv.index("--dir") + 1]
    if "--dir" in sys.argv
    else "output/core008/physics/scaled_latent_1024"
)
OUT = RUN / "temperature2d"
CACHE = OUT / "velocity_cache"
MODEL_DIR = (
    ROOT
    / "src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/physical_model"
)
LANDCOVER = ROOT / "output/core008/geometry/south_kensington_core008_landcover_4m"
GEOM_1M = ROOT / "output/core008/geometry/south_kensington_core008_voxel_1m_domain4096"
for d in (OUT, CACHE):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MODEL_DIR))
sys.path.insert(0, str(MODEL_DIR.parent / "velocity_calculation"))
spec = importlib.util.spec_from_file_location(
    "south_kensington_temperature", MODEL_DIR / "south_kensington_temperature.py"
)
M = importlib.util.module_from_spec(spec)
sys.modules["south_kensington_temperature"] = M
spec.loader.exec_module(M)
from south_kensington_jupyter import SouthKensingtonConfig  # noqa: E402

CELL = 4.0
LAYER = 3  # 12-16 m
FIRST_STEP, LAST_STEP = 41, 100
_run_cfg = json.loads((RUN / "run_config.json").read_text())
IS_1024 = int(_run_cfg.get("cell_m", 1)) == 4
FRAME_SECONDS = 100.0 if IS_1024 else 25.0  # one SCALED step: 4 m cells -> 100 s, 1 m cells -> 25 s
DOMAIN_LOWER = tuple(_run_cfg["domain_lower_xyz_m"][:2])  # domain metres of this run's origin
EXTENT_M = ((625, 3474), (754, 3348))  # building extent in domain metres (x, y)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def to_image(a):
    """domain array (row 0 = south) -> model array (row 0 = north)."""
    return np.ascontiguousarray(a[::-1])


def build_cache():
    solid = (
        np.load(RUN / "wind/solid_4m_full_zyx.npy")
        if IS_1024
        else np.load(RUN / "temperature/solid_4m_zyx.npy")
    )
    building = solid[1]  # footprint (4-8 m layer)
    ny, nx = building.shape
    oy, ox = (
        int(DOMAIN_LOWER[1] // CELL),
        int(DOMAIN_LOWER[0] // CELL),
    )  # offset of this run inside the 1024 domain grid
    h1 = np.load(GEOM_1M / "height_m.npy", mmap_mode="r")  # [4096,4096] roof heights, 1 m
    h1 = np.asarray(h1[oy * 4 : (oy + ny) * 4, ox * 4 : (ox + nx) * 4])
    height = h1.reshape(ny, 4, nx, 4).max(axis=(1, 3)).astype(np.float32)
    height[~building] = 0.0
    vegetation = np.load(LANDCOVER / "vegetation_4m_yx.npy")[oy : oy + ny, ox : ox + nx] & ~building
    study = np.zeros_like(building)
    (x0, x1), (y0, y1) = EXTENT_M
    study[
        max(0, int((y0 - DOMAIN_LOWER[1]) // CELL)) : int(np.ceil((y1 - DOMAIN_LOWER[1]) / CELL)),
        max(0, int((x0 - DOMAIN_LOWER[0]) // CELL)) : int(np.ceil((x1 - DOMAIN_LOWER[0]) / CELL)),
    ] = True
    urban = study & ~building & ~vegetation
    frames = []
    for k in range(FIRST_STEP, LAST_STEP + 1):
        w = np.load(RUN / f"wind/wind4m_{k:03d}.npy", mmap_mode="r")[
            :, LAYER
        ]  # [3,1024,1024] m/s, +x east, +y north
        frames.append((np.asarray(w[0], np.float32), np.asarray(w[1], np.float32)))
    u = np.stack([to_image(f[0]) for f in frames])
    v = np.stack([to_image(-f[1]) for f in frames])
    np.save(CACHE / "velocity_u_slice.npy", u)
    np.save(CACHE / "velocity_v_slice.npy", v)
    np.save(CACHE / "velocity_speed_slice.npy", np.sqrt(u**2 + v**2))
    np.save(CACHE / "building_mask.npy", to_image(building))
    np.save(CACHE / "study_area_mask.npy", to_image(study))
    np.save(CACHE / "vegetation_mask.npy", to_image(vegetation))
    np.save(CACHE / "urban_mask.npy", to_image(urban))
    np.save(CACHE / "height_field.npy", to_image(height))
    stats = {
        "frames": len(frames),
        "grid_yx": list(building.shape),
        "building_cells": int(building.sum()),
        "vegetation_cells": int(vegetation.sum()),
        "urban_cells": int(urban.sum()),
        "study_cells": int(study.sum()),
        "mean_speed_m_s": float(np.sqrt(u**2 + v**2)[:, to_image(study & ~building)].mean()),
    }
    return stats


def main():
    velocity_config = SouthKensingtonConfig(
        timesteppings=LAST_STEP - FIRST_STEP + 1,
        model_resolution_m=CELL,
        z_dim=16,
        height_scale_m=CELL,
        output_dir=str(OUT / "velocity_unused"),
    )
    temp_config = M.TemperatureScenarioConfig(
        output_dir=str(OUT),
        reuse_velocity_output_dir=str(CACHE),
        slice_idx=LAYER,
        frame_duration_s=FRAME_SECONDS,
        save_animation=False,
    )
    stats = build_cache()
    (CACHE / "velocity_cache_summary.json").write_text(
        json.dumps(
            {
                "velocity_config": asdict(velocity_config),
                "slice_idx": LAYER,
                "velocity_shape": [stats["frames"], *stats["grid_yx"]],
            },
            indent=2,
        )
    )
    log(f"cache built: {stats}")
    t0 = time.time()
    outputs = M.run_temperature_label_pipeline(velocity_config, temp_config)
    summary = outputs["summary"]
    summary.update(
        {
            "wind_source": f"SCALED {RUN.name} steps {FIRST_STEP}..{LAST_STEP}, layer {LAYER} (12-16 m), {FRAME_SECONDS:g} s per frame",
            "cache_reused": True,
            "cache_stats": stats,
            "seconds": time.time() - t0,
            "frame_orientation": "saved arrays are model orientation: row 0 = north; flip rows for domain frame",
            "landcover_source": str(LANDCOVER),
            "note": "unchanged Yi Qi 2-D label solver; scenario values are its defaults",
        }
    )
    (OUT / "temperature_run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log(
        f"done in {summary['seconds']:.0f}s: dt {summary['dt_seconds']:.2f}s, {summary['substeps_per_frame']} substeps/frame, "
        f"T range {summary['temperature_min_c']:.2f}..{summary['temperature_max_c']:.2f} C"
    )


if __name__ == "__main__":
    main()
