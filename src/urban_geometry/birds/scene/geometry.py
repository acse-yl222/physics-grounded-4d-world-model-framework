"""Scene geometry for the birds, built from the scene's own city GLB with the framework voxeliser.

1. bake_glb.mjs turns the published (meshopt, node-transformed) GLB into plain baked geometry;
2. urban_geometry.voxelization.prepare_glb (unchanged) writes the standard geometry directory:
   solid.npy, height_m.npy, ground rasters and 8 m canopy/grass/asphalt/paving masks;
3. landcover() adds 2 m bird land-cover masks (low vegetation, trees, water) on the same grid, using
   prepare_glb's own reader, rasteriser and classifier plus the city viewer's tree/water conventions;
4. bird_geometry() crops solid.npy to the area the birds use and writes the sim's geometry .npz.

Local frame (prepare_glb): z-up metres, local = (gltf x, -gltf z, gltf y); cell centres at
origin + (index + 0.5) * cell. The viewer shows the same GLB, so bird positions align by construction.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# city viewer tree conventions (src/visualization/legacy/viewer/3d/main.js TREE_NODE / TREE_MAT)
TREE_MAT = re.compile(
    r"broadleaf|crown|tree bark|hedge|foliage|grass|substrate|shrub|lawn|leaves|planting",
    re.IGNORECASE,
)
TREE_NODE = re.compile(
    r"simplified canopy|simplified trunk|inherited tre|\btrees?\b|hedge", re.IGNORECASE
)
WATER = re.compile(r"\bwater\b", re.IGNORECASE)
NOT_WATER = re.compile(
    r"rain ?water|waterproof|watertight|water ?tank|water ?feature pump", re.IGNORECASE
)
LOW_VEGETATION_M = (
    1.5  # vegetation whose top is within this of the ground counts as grass/low planting
)


def bake(glb, out, supplements=(), node="node"):
    """Run bake_glb.mjs (needs the @gltf-transform packages named in its header)."""
    cmd = [node, "--max-old-space-size=6000", str(HERE / "bake_glb.mjs"), str(out), str(glb)]
    cmd += [str(s) for s in supplements]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            "bake_glb.mjs failed (install: npm install --no-save @gltf-transform/core@4 "
            "@gltf-transform/extensions@4 @gltf-transform/functions@4 meshoptimizer)\n"
            + result.stderr[-3000:]
        )
    return json.loads(result.stdout.strip().splitlines()[-1])


def voxelise(baked_glb, geo_dir, cell=2):
    """The framework voxeliser, unchanged (python -m urban_geometry.voxelization.prepare_glb)."""
    cmd = [sys.executable, "-m", "urban_geometry.voxelization.prepare_glb"]
    cmd += ["--cell", str(cell), "--source", str(baked_glb), "--out", str(geo_dir)]
    subprocess.run(cmd, check=True)
    return json.loads((Path(geo_dir) / "metadata.json").read_text())


def landcover(baked_glb, geo_dir):
    """2 m bird land cover on prepare_glb's grid: low vegetation, tree crowns and water."""
    from urban_geometry.voxelization.glb_plan import local_bounds, plan_grid, read_glb_header
    from urban_geometry.voxelization.prepare_glb import category, raster, read_primitive

    geo_dir = Path(geo_dir)
    meta = json.loads((geo_dir / "metadata.json").read_text())
    cell = meta["spacing_xyz_m"][0]
    _, ny, nx = meta["shape_zyx"]
    doc, base = read_glb_header(baked_glb)
    plan = plan_grid(local_bounds(doc), cell, meta.get("crop_local_m"))
    origin = plan["origin_xy"]
    if [float(v) for v in origin] != meta["source_region_origin_xyz_m"][:2] or (
        plan["nx"],
        plan["ny"],
    ) != (nx, ny):
        raise ValueError("landcover grid differs from the prepare_glb grid; use the same baked GLB")
    maps = {k: np.full((ny, nx), -np.inf, np.float32) for k in ("vegetation", "water")}
    counts = {"vegetation": 0, "water": 0}
    materials = doc.get("materials", [])
    with Path(baked_glb).open("rb") as f:
        for node in doc["nodes"]:
            if "mesh" not in node:
                continue
            name = node.get("name", "")
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                material = (
                    materials[primitive["material"]].get("name", "")
                    if "material" in primitive
                    else ""
                )
                cls = category(name, material)
                if (
                    cls in ("canopy", "grass")
                    or TREE_MAT.search(material)
                    or TREE_NODE.search(name)
                ):
                    kind = "vegetation"
                elif (WATER.search(material) or WATER.search(name)) and not NOT_WATER.search(
                    material + " " + name
                ):
                    kind = "water"
                else:
                    continue
                points, faces = read_primitive(doc, f, base, primitive)
                vertices = points[:, [0, 2, 1]]
                vertices[:, 1] *= -1
                raster(vertices, faces, maps[kind], *origin, float(cell))
                counts[kind] += 1
    ground = np.load(geo_dir / "ground_mesh_m_yx.npy").astype(np.float32)
    building = np.load(geo_dir / "height_m.npy") > 0.5
    veg_top = maps["vegetation"]
    has_veg = np.isfinite(veg_top)
    low = has_veg & (veg_top - ground <= LOW_VEGETATION_M) & ~building
    tree = has_veg & (veg_top - ground > LOW_VEGETATION_M)
    water = np.isfinite(maps["water"]) & ~building & ~low
    out = geo_dir / f"bird_landcover_{cell}m.npz"
    np.savez_compressed(
        out,
        low_vegetation=low,
        tree=tree,
        tree_top_m=np.where(tree, veg_top, 0).astype(np.float32),
        water=water,
    )
    summary = {
        "file": out.name,
        "cell_m": cell,
        "primitives": counts,
        "low_vegetation_fraction": float(low.mean()),
        "tree_fraction": float(tree.mean()),
        "water_fraction": float(water.mean()),
        "rules": {
            "vegetation": "prepare_glb canopy/grass classes, or the city viewer's tree material/node patterns",
            "low_vegetation": f"vegetation top within {LOW_VEGETATION_M} m of the ground mesh, not under a roof",
            "water": "material or node name containing 'water' (not rainwater/waterproof)",
        },
    }
    (geo_dir / "bird_landcover.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def prepare(glb, geo_dir, supplements=(), cell=2, work_dir=None, keep_baked=False):
    """Bake + voxelise + land cover into geo_dir (a new directory)."""
    geo_dir = Path(geo_dir)
    work = Path(work_dir) if work_dir else geo_dir.parent
    work.mkdir(parents=True, exist_ok=True)
    baked = work / (geo_dir.name + "_baked.glb")
    bake_info = bake(glb, baked, supplements)
    meta = voxelise(baked, geo_dir, cell)
    cover = landcover(baked, geo_dir)
    (geo_dir / "bird_bake.json").write_text(json.dumps(bake_info, indent=2) + "\n")
    if not keep_baked:
        baked.unlink()
    return meta, cover


class SceneGeometry:
    """Read-only view of a prepared geometry directory (2-D rasters in memory, solid memory-mapped)."""

    def __init__(self, geo_dir):
        self.dir = Path(geo_dir)
        self.meta = json.loads((self.dir / "metadata.json").read_text())
        self.cell = float(self.meta["spacing_xyz_m"][0])
        self.origin = np.array(self.meta["source_region_origin_xyz_m"], dtype=float)
        self.solid = np.load(self.dir / "solid.npy", mmap_mode="r")  # (nz, ny, nx) bool
        self.nz, self.ny, self.nx = self.solid.shape
        self.height = np.load(self.dir / "height_m.npy").astype(
            np.float32
        )  # roof height per column
        self.ground = np.load(self.dir / "ground_mesh_m_yx.npy").astype(np.float32)
        cover = np.load(next(self.dir.glob("bird_landcover_*m.npz")))
        self.low_vegetation = cover["low_vegetation"]
        self.tree = cover["tree"]
        self.water = cover["water"]
        coarse = round(4 * self.cell)
        self.asphalt = self._expand(np.load(self.dir / f"asphalt_{coarse}m_yx.npy"))
        self.paving = self._expand(np.load(self.dir / f"paving_{coarse}m_yx.npy"))

    def _expand(self, mask):
        return np.repeat(np.repeat(mask, 4, axis=0), 4, axis=1)[: self.ny, : self.nx]

    @property
    def building(self):
        return self.height > 0.5

    def xy(self, rows, cols):
        """Cell-centre local coordinates of (row, col) indices."""
        return (
            self.origin[0] + (np.asarray(cols) + 0.5) * self.cell,
            self.origin[1] + (np.asarray(rows) + 0.5) * self.cell,
        )

    def index(self, x, y):
        return (
            np.floor((np.asarray(y) - self.origin[1]) / self.cell).astype(int),
            np.floor((np.asarray(x) - self.origin[0]) / self.cell).astype(int),
        )

    def bird_geometry(self, box_xy, z_top, out_npz):
        """Crop solid.npy to box_xy = (x0, y0, x1, y1) and heights below z_top; write the sim's .npz."""
        r0, c0 = self.index(box_xy[0], box_xy[1])
        r1, c1 = self.index(box_xy[2], box_xy[3])
        r0, c0 = max(0, int(r0)), max(0, int(c0))
        r1, c1 = min(self.ny, int(r1) + 1), min(self.nx, int(c1) + 1)
        k1 = min(self.nz, int(np.ceil((z_top - self.origin[2]) / self.cell)))
        geometry = np.ascontiguousarray(self.solid[:k1, r0:r1, c0:c1])
        origin = np.array(
            [
                self.origin[0] + c0 * self.cell,
                self.origin[1] + r0 * self.cell,
                self.origin[2],
            ]
        )
        np.savez_compressed(
            out_npz,
            geometry=geometry,
            grid_spacing=self.cell,
            grid_spacing_z=self.cell,
            grid_origin=origin,
        )
        return {
            "file": str(out_npz),
            "shape_zyx": list(geometry.shape),
            "origin_xyz_m": origin.tolist(),
            "cell_m": self.cell,
            "solid_fraction": float(geometry.mean()),
        }


def copy_metadata(geo_dir, dest):
    """Keep the small provenance files of a geometry directory next to a run."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("metadata.json", "bird_landcover.json", "bird_bake.json"):
        src = Path(geo_dir) / name
        if src.exists():
            shutil.copy2(src, dest / ("geometry_" + name))
