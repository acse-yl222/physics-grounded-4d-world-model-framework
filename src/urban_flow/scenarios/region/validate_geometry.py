"""Check coordinate preservation, domain clearance, and terrain occupancy."""

import json
from pathlib import Path
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path.cwd()
sys.path.insert(0, str(root))
from pipelines.geometry.voxelization.glb_plan import read_glb_header
from pipelines.geometry.voxelization.prepare_glb import read_primitive

folder = root / "input/region"
out = root / "output/region/geometry/voxel_8m"
meta = json.loads((out / "metadata.json").read_text())
original, ob = read_glb_header(folder / "region.glb")
local, lb = read_glb_header(folder / "region_local.glb")
error = 0.0
with (folder / "region.glb").open("rb") as of, (folder / "region_local.glb").open("rb") as lf:
    for om, lm in zip(original["meshes"], local["meshes"]):
        for op, lp in zip(om["primitives"], lm["primitives"]):
            ov, oi = read_primitive(original, of, ob, op)
            lv, li = read_primitive(local, lf, lb, lp)
            assert np.array_equal(oi, li)
            lv[:, 1] += meta["original_vertical_offset_m"]
            error = max(error, float(np.max(np.abs(ov - lv))))
assert error < 1e-4
solid = np.load(out / "solid.npy")
ground = np.load(out / "ground_mesh_m_yx.npy")
valid = np.load(out / "ground_mesh_valid_yx.npy")
assert solid.shape == (64, 512, 768) and solid.dtype == bool
assert np.isfinite(ground).all() and not solid[-1].any()
centres = (np.arange(64)[:, None, None] + 0.5) * 8
assert np.all(solid | ~(centres - 4 <= ground[None]))
ids = {n.get("extras", {}).get("building_id") for n in original["nodes"]}
turbines = sorted(i for i in ids if i and i.startswith("node-"))
assert len(turbines) == 23
report = {
    "passed": True,
    "original_reconstructed_vertex_max_error_m": error,
    "turbines": len(turbines),
    "mesh_count": len(local["meshes"]),
    "solid_fraction": float(solid.mean()),
    "top_layer_solid_count": int(solid[-1].sum()),
    "original_vertical_offset_m": meta["original_vertical_offset_m"],
    "limits": "Geometry and coordinate checks only; not physical model validation.",
}
(out / "validation.json").write_text(json.dumps(report, indent=2))
fig, axes = plt.subplots(1, 3, figsize=(15, 4), constrained_layout=True)
im = axes[0].imshow(np.ma.masked_where(~valid, ground), origin="lower")
fig.colorbar(im, ax=axes[0], label="m above local datum (original minus 480 m)")
axes[0].set_title("Copernicus terrain; padding hidden")
axes[1].imshow(solid[36], origin="lower", vmin=0, vmax=1)
axes[1].set_title("Static solid cells at 288–296 m")
axes[2].imshow(solid.max(axis=1), origin="lower", aspect="auto", extent=[-3072, 3072, 0, 512])
axes[2].set_title("Side projection: terrain + stationary objects")
axes[2].set_ylabel("Height above local datum (m)")
fig.savefig(out / "geometry_qa.png", dpi=140)
print(json.dumps(report, indent=2))
