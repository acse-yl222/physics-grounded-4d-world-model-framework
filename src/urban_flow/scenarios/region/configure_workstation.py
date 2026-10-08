"""Install scene configuration and narrowly scoped compatibility updates."""

import json
from pathlib import Path
import shutil

from common.layout import repo_root

root = repo_root()
env = Path("/data/yl222/workspace/UrbanWorldModel/.venv-region")
# Python 3.10 environment contains the existing CUDA 12.8 torch build. The
# pipeline's only Python 3.11-only API is hashlib.file_digest.
site = next((env / "lib").glob("python*/site-packages"))
(site / "sitecustomize.py").write_text("""import hashlib
if not hasattr(hashlib, "file_digest"):
    def file_digest(fileobj, digest, /, *, _bufsize=2**18):
        result = hashlib.new(digest) if isinstance(digest, str) else digest()
        for block in iter(lambda: fileobj.read(_bufsize), b""):
            result.update(block)
        return result
    hashlib.file_digest = file_digest
""")
# Tiling is in cell counts. 8 m retains the full 329 m terrain+turbine relief
# within the pretrained network's fixed 64-layer input (512 m).
runner = root / "pipelines/run_scene.py"
text = runner.read_text()
old = "if cell not in (1, 2, 4):"
if old in text:
    backup = runner.with_suffix(".py.before_region")
    if not backup.exists():
        shutil.copy2(runner, backup)
    text = text.replace(old, "if cell not in (1, 2, 4, 8):")
    text = text.replace("domain.cell_m must be 1, 2 or 4", "domain.cell_m must be 1, 2, 4 or 8")
    runner.write_text(text)
cfg = {
    "scene": "region",
    "source": "region_local.glb",
    "domain": {"cell_m": 8, "crop_local_m": None, "wind_layers": 64},
    "georeference": {
        "confirmed": False,
        "latitude_deg": None,
        "longitude_deg": None,
        "note": "Location and compass alignment not yet supplied. Terrain is labelled Copernicus DSM, not surveyed DTM.",
    },
    "stages": [
        "geometry",
        "wind",
        "temperature",
        "temperature3d",
        "pollution",
        "plot",
        "verify",
        "visualize",
    ],
    "wind": {"steps": 100, "step_seconds": 50, "coarse_factor": 4, "min_free_gib": 10},
    "temperature3d": {"frames": 20},
    "visualize": {
        "layer": 9,
        "title": "Region · Wind farm (experimental)",
        "description": "23 stationary turbines and Copernicus terrain. 8 m geometry / 32 m fields. Horizontal slice 288–320 m above local datum, not height above terrain. No turbine rotor or power model.",
    },
}
folder = root / "input/region"
(folder / "config.json").write_text(json.dumps(cfg, indent=2))
smoke = json.loads(json.dumps(cfg))
smoke.update(scene="region_smoke", source=str(folder / "region_local.glb"))
smoke["wind"]["steps"] = 10
smoke["temperature3d"]["frames"] = 2
smoke["stages"].remove("visualize")
(folder / "smoke.json").write_text(json.dumps(smoke, indent=2))
smoke_geom = root / "output/region_smoke/geometry"
smoke_geom.mkdir(parents=True, exist_ok=True)
link = smoke_geom / "voxel_8m"
if not link.exists():
    link.symlink_to(root / "output/region/geometry/voxel_8m", target_is_directory=True)
print("Configured", folder / "config.json")
