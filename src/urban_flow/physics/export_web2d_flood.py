"""Add the 1 m flood results to an existing 2-D web package (output/core008/physics/web2d) as a `flood/` sub-folder.

Usage: python export_web2d_flood.py [--run output/core008/physics/scaled_latent/flood/run_1m] [--out output/core008/physics/web2d]
Arrays keep the package convention: row 0 = south, col 0 = west, float16. Flood arrays are on the 1 m grid [2816, 3072]
(same origin as the 4 m arrays, 4x4 cells per 4 m cell); 4 m block means are added for light-weight playback.
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
    args[args.index("--run") + 1]
    if "--run" in args
    else "output/core008/physics/scaled_latent/flood/run_1m"
)
OUT = ROOT / (args[args.index("--out") + 1] if "--out" in args else "output/core008/physics/web2d")
TERRAIN = RUN.parent / "terrain"
(OUT / "flood").mkdir(parents=True, exist_ok=True)
manifest = json.loads((OUT / "manifest.json").read_text())
cfg = json.loads((RUN / "run_config.json").read_text())
summ = json.loads((RUN / "summary.json").read_text())
frames = json.loads((RUN / "frames/manifest.json").read_text())
cell = cfg["grid"]["cell_m"]
ny, nx = cfg["grid"]["shape_yx"]


def put(name, arr, **meta):
    arr = np.asarray(arr)
    np.save(OUT / "flood" / f"{name}.npy", arr)
    manifest["arrays"][f"flood/{name}.npy"] = {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "cell_m": meta.pop("cell_m", cell),
        **meta,
    }
    print(f"flood/{name}.npy", arr.shape, arr.dtype, f"{arr.nbytes / 1e6:.1f} MB")


def pool4(a):
    return a.reshape(ny // 4, 4, nx // 4, 4).mean(axis=(1, 3))


# static fields
dtm = np.load(TERRAIN / "dtm_1m_yx.npy")
foot = np.load(TERRAIN / "footprint_1m_yx.npy")
put(
    "dtm_1m_yx",
    dtm.astype(np.float16),
    unit="m AOD (ODN)",
    meaning="EA 2022 LIDAR composite DTM, bare earth; water surface = dtm + depth",
)
put(
    "building_footprint_1m_yx",
    foot,
    meaning="True = building (core008 1 m voxels); solid in the flood model, no water",
)
put(
    "green_1m_yx",
    np.load(TERRAIN / "grass_1m_yx.npy") | np.load(TERRAIN / "vegetation_1m_yx.npy"),
    meaning="grass / canopy: infiltration 20 mm/h, Manning 0.05",
)
hmax = np.load(RUN / "max_depth_m.npy")
put(
    "max_depth_1m_yx",
    hmax.astype(np.float16),
    unit="m",
    meaning="maximum water depth over the 3 h event",
)
put(
    "max_speed_1m_yx",
    np.load(RUN / "max_speed_m_s.npy").astype(np.float16),
    unit="m/s",
    meaning="maximum cell-centre speed; extreme values sit on DTM cliffs with sub-mm films",
)
put(
    "max_hazard_hv_1m_yx",
    np.load(RUN / "max_hazard_hv_m2_s.npy").astype(np.float16),
    unit="m^2/s",
    meaning="max of depth x speed (UK FD2320 hazard: <0.5 low, 0.5-1 moderate, >1 significant)",
)
arr = np.load(RUN / "arrival_time_gt10cm_s.npy")
put(
    "arrival_time_gt10cm_1m_yx",
    arr.astype(np.float16),
    unit="s",
    meaning="first time depth exceeds 0.10 m; NaN = never",
)
put(
    "final_depth_1m_yx",
    np.load(RUN / "final_depth_m.npy").astype(np.float16),
    unit="m",
    meaning="depth at t = 3 h",
)
put(
    "max_depth_4m_yx",
    pool4(hmax).astype(np.float16),
    cell_m=4,
    unit="m",
    meaning="4x4 block mean of max_depth_1m_yx, same grid as wind/temperature arrays",
)

# time series of depth: 1 m frames (every 10 min) stacked, plus 4 m block means
times = [f["t_s"] for f in frames]
stack1 = np.empty((len(frames), ny, nx), np.float16)
stack4 = np.empty((len(frames), ny // 4, nx // 4), np.float16)
for k, f in enumerate(frames):
    h = np.load(RUN / "frames" / f"depth_{f['index']:03d}_float16.npy")
    stack1[k] = h
    stack4[k] = pool4(h.astype(np.float32)).astype(np.float16)
put(
    "depth_1m_tyx",
    stack1,
    unit="m",
    time_s=times,
    rain_mm_h=[f["rain_mm_h"] for f in frames],
    meaning="water depth every 10 min; frame k is at time_s[k]",
)
put(
    "depth_4m_tyx",
    stack4,
    cell_m=4,
    unit="m",
    time_s=times,
    rain_mm_h=[f["rain_mm_h"] for f in frames],
    meaning="4x4 block mean of depth_1m_tyx",
)

# metadata and figures
(OUT / "metadata").mkdir(exist_ok=True)
(OUT / "figures").mkdir(exist_ok=True)
for src, dst in [
    (RUN / "run_config.json", "flood_run_config.json"),
    (RUN / "summary.json", "flood_summary.json"),
    (RUN / "series.json", "flood_series.json"),
    (RUN / "poi_depth_series.json", "flood_poi_depth_series.json"),
    (RUN.parent / "verification.json", "flood_solver_verification.json"),
    (TERRAIN / "metadata.json", "flood_terrain_metadata.json"),
]:
    shutil.copy(src, OUT / "metadata" / dst)
for p in (RUN / "figures").iterdir():
    shutil.copy(p, OUT / "figures" / f"flood_{p.name}")
shutil.copy(TERRAIN / "preview_terrain_4m.png", OUT / "figures" / "flood_terrain_preview_4m.png")

manifest["flood"] = {
    "run": str(RUN.relative_to(ROOT)),
    "cell_m": cell,
    "grid_shape_yx": [ny, nx],
    "domain_origin_xy_m": cfg["grid"]["domain_lower_xy_m"],
    "index_to_domain_m": cfg["grid"]["index_to_domain_m"],
    "orientation": manifest["orientation"],
    "relation_to_4m_arrays": "1 m cell (iy, ix) lies inside 4 m cell (iy // 4, ix // 4)",
    "scenario": cfg["scenario"],
    "summary": summ,
    "paper": cfg["paper"],
    "solver": cfg["solver"],
    "metadata": [
        "metadata/flood_run_config.json",
        "metadata/flood_summary.json",
        "metadata/flood_series.json",
        "metadata/flood_poi_depth_series.json",
        "metadata/flood_solver_verification.json",
        "metadata/flood_terrain_metadata.json",
    ],
    "figures": sorted(p.name for p in (OUT / "figures").iterdir() if p.name.startswith("flood_")),
    "display_hint": "depth <= 0.02 m is dry for display; colour 0.02-1.5 m; water surface elevation = dtm_1m_yx + depth",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
readme = OUT / "README_source_run.md"
flood_readme = (RUN.parent / "README.md").read_text()
text = readme.read_text()
marker = (
    "\n\n---\n\n# 洪水结果（flood/）— 来源 output/core008/physics/scaled_latent/flood/README.md\n\n"
)
if marker.strip() not in text:
    readme.write_text(text.rstrip() + marker + flood_readme)
print("manifest arrays:", len(manifest["arrays"]), "->", OUT)
