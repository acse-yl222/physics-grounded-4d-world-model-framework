"""Rasterise core008 ground/vegetation meshes into 4 m land-cover masks on the padded 4096 m domain grid.

Source: output/core008/geometry/south_kensington_core008.glb (region frame). Materials assigned by the merge
script: 'Central preview | grass | authored tile' (park/grass), '... asphalt ...' (roads), '... paving' (ground,
paths), 'Detailed vegetation | generic broadleaf ...' (tree canopies). Output arrays are [1024,1024] on the
domain grid (row = y index, south at row 0, 4 m cells), i.e. the same frame as output/core008/physics/scaled_latent_1024.
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import json
import time
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = repo_root()
GLB = ROOT / "output/core008/geometry/south_kensington_core008.glb"
OUT = ROOT / "output/core008/geometry/south_kensington_core008_landcover_4m"
OUT.mkdir(exist_ok=True)
CELL = 4.0
N = 1024
REGION_TO_DOMAIN = np.array([2116.0, 2124.0])


def rasterise(tris_xy, canvas):
    """tris_xy: [T,3,2] domain metres -> paint into canvas (PIL 'L' image, row 0 = south)."""
    d = ImageDraw.Draw(canvas)
    for tri in tris_xy:
        pts = [(float(x / CELL), float(y / CELL)) for x, y in tri]
        d.polygon(pts, fill=255, outline=255)


def main():
    t0 = time.time()
    scene = trimesh.load(GLB, force="scene")
    print(f"loaded {len(scene.geometry)} geometries in {time.time() - t0:.0f}s", flush=True)
    classes = {
        "grass": Image.new("L", (N, N), 0),
        "asphalt": Image.new("L", (N, N), 0),
        "paving": Image.new("L", (N, N), 0),
        "canopy": Image.new("L", (N, N), 0),
    }
    counts = {k: 0 for k in classes}
    material_names = {}
    for node_name in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node_name]
        geom = scene.geometry[geom_name]
        mat = getattr(getattr(geom, "visual", None), "material", None)
        mname = getattr(mat, "name", "") or ""
        lower = mname.lower()
        if "grass" in lower:
            cls = "grass"
        elif "asphalt" in lower or "road class" in lower:
            cls = "asphalt"
        elif "paving" in lower:
            cls = "paving"
        elif "detailed vegetation" in lower or "broadleaf" in lower or "canopy" in lower:
            cls = "canopy"
        else:
            material_names[mname] = material_names.get(mname, 0) + 1
            continue
        v = trimesh.transform_points(geom.vertices, transform)
        xy = (
            np.stack([v[:, 0], -v[:, 2]], axis=1) + REGION_TO_DOMAIN
        )  # glTF y-up: east = x, north = -z
        tris = xy[geom.faces]  # [T,3,2]
        rasterise(tris, classes[cls])
        counts[cls] += len(geom.faces)
    masks = {k: (np.array(img) > 0) for k, img in classes.items()}
    vegetation = masks["grass"] | masks["canopy"]
    impervious = (masks["asphalt"] | masks["paving"]) & ~vegetation
    np.save(OUT / "vegetation_4m_yx.npy", vegetation)
    np.save(OUT / "impervious_ground_4m_yx.npy", impervious)
    for k, m in masks.items():
        np.save(OUT / f"{k}_4m_yx.npy", m)
    meta = {
        "source_glb": str(GLB),
        "cell_m": CELL,
        "grid_yx": [N, N],
        "frame": "padded domain, row 0 = south, col 0 = west",
        "region_to_domain_offset_m": REGION_TO_DOMAIN.tolist(),
        "triangles_per_class": counts,
        "cells_per_class": {k: int(m.sum()) for k, m in masks.items()},
        "vegetation_cells": int(vegetation.sum()),
        "impervious_cells": int(impervious.sum()),
        "unclassified_materials_top": sorted(material_names.items(), key=lambda kv: -kv[1])[:15],
        "seconds": time.time() - t0,
    }
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: meta[k]
                for k in (
                    "triangles_per_class",
                    "cells_per_class",
                    "vegetation_cells",
                    "impervious_cells",
                    "seconds",
                )
            },
            indent=1,
        )
    )
    print("unclassified:", meta["unclassified_materials_top"][:8])
    # preview
    rgb = np.zeros((N, N, 3), np.uint8) + 20
    rgb[impervious] = (110, 110, 110)
    rgb[vegetation] = (60, 160, 60)
    Image.fromarray(rgb[::-1]).save(OUT / "preview.png")


if __name__ == "__main__":
    main()
