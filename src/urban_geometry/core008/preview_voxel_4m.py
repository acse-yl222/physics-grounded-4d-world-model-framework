"""Validate saved occupancy and draw height / horizontal-section previews."""

import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

root = (
    Path(__file__).resolve().parents[3]
    / "output/core008/geometry/south_kensington_core008_voxel_4m"
)
m = json.loads((root / "metadata.json").read_text())
s = np.load(root / "solid.npy", allow_pickle=False)
h = np.load(root / "height_m.npy", allow_pickle=False)
with np.load(root / "geometry.npz", allow_pickle=False) as z:
    assert np.array_equal(z["geometry"], s)
    assert np.array_equal(z["solid"], s)
    assert np.array_equal(z["height_m"], h)
    assert np.array_equal(z["grid_origin"], m["origin_xyz_m"])
assert s.dtype == np.bool_ and list(s.shape) == m["shape_zyx"]
assert np.isfinite(h).all() and h.max() < s.shape[0] * 4
assert np.array_equal(s.sum(axis=0), np.ceil(h / 4).astype(int))
assert not s[-1].any()
assert 0.01 < s.mean() < 0.5
# Display north up. All panels share the original grid with nearest-neighbour scaling.
out = Image.new("RGB", (1500, 1510), "#101b29")
draw = ImageDraw.Draw(out)
draw.text((30, 20), "SOUTH KENSINGTON | 4 m building occupancy | North up", fill="white")
draw.text(
    (30, 43),
    f"Array Z,Y,X = {s.shape} | cell = 4 x 4 x 4 m | height domain = {s.shape[0] * 4} m",
    fill="#b8cad9",
)
colors = np.array(
    [[20, 34, 48], [36, 106, 132], [66, 169, 154], [224, 207, 103], [244, 136, 73]], float
)
v = np.clip(h / 96, 0, 1) * (len(colors) - 1)
low = np.minimum(v.astype(int), len(colors) - 2)
rgb = (colors[low] * (1 - (v - low)[..., None]) + colors[low + 1] * (v - low)[..., None]).astype(
    "uint8"
)
panels = [("Maximum sampled roof height (0-96 m)", rgb)]
for k in (0, 5, 12):
    a = np.zeros((*h.shape, 3), dtype="uint8")
    a[:] = [20, 34, 48]
    a[s[k]] = [95, 210, 182]
    panels.append((f"Occupied cells at z = {k * 4}-{(k + 1) * 4} m", a))
for i, (title, a) in enumerate(panels):
    x = 30 + (i % 2) * 745
    y = 95 + (i // 2) * 705
    draw.text((x, y), title, fill="white")
    im = Image.fromarray(a[::-1])
    im.thumbnail((710, 650), Image.Resampling.NEAREST)
    out.paste(im, (x, y + 26))
draw.text(
    (30, 1490),
    "Building-only column fill; excludes trees/vehicles. Not yet a wind-model inference result.",
    fill="#b8cad9",
)
out.save(root / "preview.png")
print(
    json.dumps(
        {
            "shape": s.shape,
            "occupied_voxels": int(s.sum()),
            "max_height_m": float(h.max()),
            "checks": "passed",
        }
    )
)
