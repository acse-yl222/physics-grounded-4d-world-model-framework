"""Collect a compact 2-D package of one SCALED run for web visualisation.

Usage: python export_web2d.py --dir output/core008/physics/scaled_latent --out output/core008/physics/web2d
All arrays are in the domain orientation (row 0 = south, col 0 = west), 4 m cells, float16 unless noted.
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = repo_root()
args = sys.argv[1:]
RUN = ROOT / (
    args[args.index("--dir") + 1] if "--dir" in args else "output/core008/physics/scaled_latent"
)
OUT = ROOT / (args[args.index("--out") + 1] if "--out" in args else f"result/{RUN.name}_2d")
WIND_LAYERS = {"z8-12m": 2, "z40-44m": 10}
TEMP3D_LAYER = 2  # 8-12 m
LANDCOVER = ROOT / "output/core008/geometry/south_kensington_core008_landcover_4m"

cfg = json.loads((RUN / "run_config.json").read_text())
cell = int(cfg.get("cell_m", 1))
origin = cfg["domain_lower_xyz_m"][:2]
step_seconds = 100.0 if cell == 4 else 25.0
for sub in ("wind", "temperature3d", "temperature2d", "pollution", "masks", "figures", "metadata"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)
manifest = {
    "run": RUN.name,
    "cell_m": 4,
    "domain_origin_xy_m": origin,
    "orientation": "row 0 = south, col 0 = west (north up when flipped for display)",
    "domain_to_region_xy_m": "region = domain - (2116, 2124)",
    "wind_step_seconds": step_seconds,
    "arrays": {},
}


def put(sub, name, arr, **meta):
    arr = np.asarray(arr)
    np.save(OUT / sub / f"{name}.npy", arr)
    manifest["arrays"][f"{sub}/{name}.npy"] = {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        **meta,
    }


# ---- masks
solid = np.load(RUN / "temperature/solid_4m_zyx.npy")
ny, nx = solid.shape[1:]
oy, ox = int(origin[1] // 4), int(origin[0] // 4)
put(
    "masks",
    "building_footprint_yx",
    solid[1],
    meaning="True = building (4-8 m layer of the conservative 4 m voxels)",
)
put("masks", "solid_4m_zyx", solid, meaning="True = building, 16 layers x 4 m (bottom 64 m)")
h1 = np.asarray(
    np.load(
        ROOT / "output/core008/geometry/south_kensington_core008_voxel_1m_domain4096/height_m.npy",
        mmap_mode="r",
    )[oy * 4 : (oy + ny) * 4, ox * 4 : (ox + nx) * 4]
)
put(
    "masks",
    "roof_height_m_yx",
    h1.reshape(ny, 4, nx, 4).max(axis=(1, 3)).astype(np.float16),
    meaning="max roof height per 4 m cell, metres",
)
put(
    "masks",
    "vegetation_yx",
    np.load(LANDCOVER / "vegetation_4m_yx.npy")[oy : oy + ny, ox : ox + nx],
    meaning="grass / tree canopy from core008.glb",
)
put(
    "masks",
    "impervious_ground_yx",
    np.load(LANDCOVER / "impervious_ground_4m_yx.npy")[oy : oy + ny, ox : ox + nx],
    meaning="asphalt / paving from core008.glb",
)

# ---- wind slices
metrics = json.loads((RUN / "wind/metrics.json").read_text())
steps = [s["step"] for s in metrics["steps"]]
for label, k in WIND_LAYERS.items():
    frames = np.stack(
        [np.load(RUN / f"wind/wind4m_{s:03d}.npy", mmap_mode="r")[:, k] for s in steps]
    ).astype(np.float16)
    put(
        "wind",
        f"uvw_{label}_tcyx",
        frames,
        components="u east, v north, w up (m/s)",
        time_s=[s * step_seconds for s in steps],
        layer_m=[k * 4, k * 4 + 4],
        note="zero inside conservative solid cells",
    )
manifest["wind_metrics"] = "metadata/wind_metrics.json"
shutil.copy(RUN / "wind/metrics.json", OUT / "metadata/wind_metrics.json")

# ---- 3-D temperature run (U-Net vs controlled solver) at one layer
tdir = RUN / "temperature"
if (tdir / "metrics.json").exists():
    solver = json.loads((tdir / "physical_solver.json").read_text())
    refs = np.stack(
        [np.load(f)[TEMP3D_LAYER] for f in sorted(tdir.glob("reference_*.npy"))]
    ).astype(np.float16)
    put(
        "temperature3d",
        "solver_reference_tyx",
        refs,
        unit="C",
        time_s=solver["times_seconds"],
        layer_m=[TEMP3D_LAYER * 4, TEMP3D_LAYER * 4 + 4],
    )
    for mode in ("recursive", "one_step"):
        arr = np.stack(
            [np.load(f)[TEMP3D_LAYER] for f in sorted(tdir.glob(f"{mode}_*.npy"))]
        ).astype(np.float16)
        put(
            "temperature3d",
            f"unet_{mode}_tyx",
            arr,
            unit="C",
            time_s=[90 * (i + 1) for i in range(arr.shape[0])],
            layer_m=[TEMP3D_LAYER * 4, TEMP3D_LAYER * 4 + 4],
        )
    shutil.copy(tdir / "metrics.json", OUT / "metadata/temperature3d_metrics.json")
    shutil.copy(tdir / "physical_solver.json", OUT / "metadata/temperature3d_physical_solver.json")

# ---- 2-D temperature label model (model orientation row 0 = north -> flip back)
t2 = RUN / "temperature2d"
if (t2 / "temperature_run_summary.json").exists():
    summ = json.loads((t2 / "temperature_run_summary.json").read_text())
    fs = summ["temperature_config"]["frame_duration_s"]
    T = np.load(t2 / "temperature_fields_c.npy", mmap_mode="r")
    put(
        "temperature2d",
        "temperature_tyx",
        np.asarray(T)[:, ::-1].astype(np.float16),
        unit="C",
        time_s=[fs * i for i in range(T.shape[0])],
        layer_m=[12, 16],
        note="building cells hold the fixed building temperature; outside study area = ambient",
    )
    for name in (
        "source_c_per_hour",
        "initial_temperature_c",
        "study_area_mask",
        "urban_mask",
        "vegetation_mask",
    ):
        a = np.load(t2 / f"{name}.npy")[::-1]
        put("temperature2d", f"{name}_yx", a.astype(np.float16) if a.dtype.kind == "f" else a)
    shutil.copy(t2 / "temperature_run_summary.json", OUT / "metadata/temperature2d_summary.json")

# ---- pollution
p = RUN / "pollution"
if (p / "mass.json").exists():
    mass = json.loads((p / "mass.json").read_text())
    sl = np.load(p / "slices_z12m_tyx_float16.npy")
    put(
        "pollution",
        "concentration_z12-16m_tyx",
        sl,
        unit="arbitrary (source rate 0.1 per cell per s)",
        time_s=[m["solver_time"] for m in mass],
        note="log colour recommended; hotspots at windward building feet come from wind convergence, see README",
    )
    src = np.load(p / "source.npy")
    put(
        "pollution",
        "source_footprint_yx",
        src.any(axis=0),
        meaning="source cells (z 8-32 m) projected to the ground plane",
    )
    shutil.copy(p / "mass.json", OUT / "metadata/pollution_mass.json")
    shutil.copy(p / "manifest.json", OUT / "metadata/pollution_manifest.json")

# ---- figures and docs
for src_dir, dst in (
    (RUN / "figures", "wind"),
    (RUN / "temperature2d/figures", "temperature2d"),
    (RUN / "pollution/figures", "pollution"),
):
    if src_dir.exists():
        for f in src_dir.iterdir():
            shutil.copy(f, OUT / "figures" / f"{dst}_{f.name}")
shutil.copy(RUN / "run_config.json", OUT / "metadata/run_config.json")
if (RUN / "README.md").exists():
    shutil.copy(RUN / "README.md", OUT / "README_source_run.md")
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
print(f"wrote {OUT} ({total / 1e6:.0f} MB)")
for k, v in manifest["arrays"].items():
    print(f"  {k}: {v['shape']} {v['dtype']}")
