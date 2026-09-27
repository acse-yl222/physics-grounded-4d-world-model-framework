"""
glb_to_geo.py = convert a GLB city model (watertight building solids) into an .npz with voxel occupancy

output shape is:
    geometry: bool array of shape (NZ, NY, NX) = (depth, height, width) = (z, y, x)

Voxelization method = vertical ray intersection per (x,y) column to find roof heights, then ground-to-roof fill (when SOLIDIFY_COLUMNS=True, which is the default)
- falls back to point-in-solid containment at each voxel center when disabled
- both use standard computational geometry (ray-mesh intersection)

Grid constants below must match config.py (scaled_grid_origin, grid_spacing, grid_spacing_z)
Optionally, must match generate_wind.ipynb (width, height, depth), if using SCALED wind

Setup:
    pip install trimesh rtree numpy
    # place the .glb file you want to convert into the root directory

Run with:
    # default functionality (generates .npz geometry)
    python3 scripts/glb_to_geo.py southken_solids_scene.glb

    # report, no write
    python3 scripts/glb_to_geo.py southken_solids_scene.glb --inspect-only

    # using file extension .npy (for legacy connection to SCALED or others models)
    python3 glb_to_geo.py model.glb -o geo_southken.npy

"""

import argparse
import numpy as np
import trimesh

# ----------------------------------------------------------------------------
# SCALED GRID CONSTANTS  (must match config.py + generate_wind.ipynb -- do not
# change unless you are deliberately re-scaling the whole pipeline)
# ----------------------------------------------------------------------------
NX, NY, NZ = 128, 128, 64  # width, height, depth  -> array (NZ, NY, NX)
SPACING_XY = 8.0  # meters per voxel in x and y
SPACING_Z = 1.0  # meters per voxel in z (height)
ORIGIN = (
    -512.0,
    -512.0,
    0.0,
)  # world coord of voxel (0,0,0); matches config.scaled_grid_origin

# ----------------------------------------------------------------------------
# ORIENTATION / SELECTION CONFIG  (edit these if the ASCII preview looks wrong)
# ----------------------------------------------------------------------------
BUILDINGS_NAME_SUBSTR = (
    "SB_"  # this GLB names its 252 building solids SB_* (not "Buildings_solid")
)
DROP_NAME_SUBSTR = (
    "g.001"  # the g.001* meshes are the infrastructure (roads/trees/furniture)
)
# BUILDINGS_NAME_SUBSTR = "building"   # case-insensitive substring to select the buildings mesh
# DROP_NAME_SUBSTR      = "infrastructure"  # meshes containing this are ignored (roads/trees/furniture)

UP_AXIS = "auto"  # "auto" (shortest bbox extent = height) | "x" | "y" | "z"
SWAP_XY = False  # swap the two ground axes (fixes a 90-degree-rotated city)
FLIP_X = False  # mirror east-west
FLIP_Y = False  # mirror north-south
RECENTER = "origin"  # "origin": trust model (0,0) = area center (email says so)
# "bbox":   force-center on the footprint bbox midpoint instead
SOLIDIFY_COLUMNS = (
    True  # fill each occupied column ground->roof (buildings are extruded solids)
)


# ----------------------------------------------------------------------------
def extract_world_mesh(scene, want_substr=None, drop_substr=None):
    """Concatenate geometries (in world coordinates) matching the name filters.

    want_substr : if given, keep only geometries whose name contains it
    drop_substr : drop any geometry whose name contains it
    Returns a single Trimesh or None.
    """
    if isinstance(scene, trimesh.Trimesh):
        return scene  # already a single mesh (no scene graph / names)

    parts, names = [], []
    for node in scene.graph.nodes_geometry:
        transform, gname = scene.graph[node]
        if drop_substr and drop_substr.lower() in gname.lower():
            continue
        if want_substr and want_substr.lower() not in gname.lower():
            continue
        m = scene.geometry[gname].copy()
        m.apply_transform(transform)
        parts.append(m)
        names.append(gname)
    if not parts:
        return None, []
    return trimesh.util.concatenate(parts), names


def pick_buildings(scene):
    """Select the buildings mesh with graceful fallbacks."""
    if isinstance(scene, trimesh.Trimesh):
        return scene, ["<single-mesh GLB>"]

    all_names = list(scene.geometry.keys())

    # 1) by name substring, dropping infrastructure
    mesh, names = extract_world_mesh(scene, BUILDINGS_NAME_SUBSTR, DROP_NAME_SUBSTR)
    if mesh is not None and len(mesh.faces) > 0:
        return mesh, names

    # 2) everything except infrastructure
    mesh, names = extract_world_mesh(scene, None, DROP_NAME_SUBSTR)
    if mesh is not None and len(mesh.faces) > 0:
        return mesh, names

    # 3) largest single geometry by face count
    biggest = max(scene.geometry.items(), key=lambda kv: len(kv[1].faces))
    return biggest[1], [biggest[0]]


def detect_up_axis(extents):
    """Up = smallest bbox extent (a city is wide+long, short in height)."""
    if UP_AXIS in ("x", "y", "z"):
        return {"x": 0, "y": 1, "z": 2}[UP_AXIS]
    return int(np.argmin(extents))


def ascii_preview(occupied_xy, width=64):
    """Top-down footprint preview (x = columns/east, y = rows/north)."""
    ny, nx = occupied_xy.shape  # note: passed as (y, x)
    # downsample to <= width columns
    step = max(1, nx // width)
    ss = occupied_xy[::step, ::step]
    chars = " .:-=+*#%@"
    # normalize to char ramp by local density (here it's boolean, so simple)
    lines = []
    # print north at top: flip y so higher y (north) is on top
    for row in ss[::-1]:
        line = "".join("#" if v else " " for v in row)
        lines.append(line)
    return "\n".join(lines)


def convert(path, out_path=None, inspect_only=False):
    print(f"[load] {path}")
    scene = trimesh.load(path, force="scene")

    if not isinstance(scene, trimesh.Trimesh):
        print(f"[scene] geometries: {list(scene.geometry.keys())}")

    mesh, used = pick_buildings(scene)
    print(f"[mesh]  using: {used}")
    print(
        f"[mesh]  vertices={len(mesh.vertices):,}  faces={len(mesh.faces):,}  "
        f"watertight={mesh.is_watertight}"
    )

    # --- native bounding box in the GLB's own axes ---
    lo, hi = mesh.bounds
    extents = hi - lo
    print(
        f"[bbox]  x:[{lo[0]:8.2f},{hi[0]:8.2f}]  "
        f"y:[{lo[1]:8.2f},{hi[1]:8.2f}]  "
        f"z:[{lo[2]:8.2f},{hi[2]:8.2f}]  (native GLB axes)"
    )
    print(
        f"[bbox]  extents (native): "
        f"x={extents[0]:.1f}  y={extents[1]:.1f}  z={extents[2]:.1f}"
    )

    up = detect_up_axis(extents)
    ground_axes = [a for a in (0, 1, 2) if a != up]
    print(
        f"[axis]  up-axis = {'xyz'[up]} (extent {extents[up]:.1f} m); "
        f"ground plane = {'xyz'[ground_axes[0]]},{'xyz'[ground_axes[1]]}"
    )

    # --- reorient the vertices into (gx, gy, height) ---
    V = mesh.vertices.copy()
    gx = V[:, ground_axes[0]].copy()
    gy = V[:, ground_axes[1]].copy()
    gz = V[:, up].copy()

    # ground datum: subtract the model's minimum height so ground -> 0
    ground_min = gz.min()
    gz = gz - ground_min
    print(
        f"[datum] subtracted ground offset {ground_min:.2f} m "
        f"({'looks like local/above-ground' if abs(ground_min) < 5 else 'looks like a sea-level datum -> removed'})"
    )

    if SWAP_XY:
        gx, gy = gy, gx
    if FLIP_X:
        gx = -gx
    if FLIP_Y:
        gy = -gy

    # ground-plane centring
    if RECENTER == "bbox":
        gx = gx - 0.5 * (gx.min() + gx.max())
        gy = gy - 0.5 * (gy.min() + gy.max())
        print("[center] RECENTER='bbox' -> centerd on footprint midpoint")
    else:
        print("[center] RECENTER='origin' -> trusting model (0,0) = area center")

    max_h = gz.max()
    print(
        f"[height] tallest building = {max_h:.1f} m  "
        f"({int(np.ceil(max_h / SPACING_Z))} voxels of {NZ})"
        + (
            "   *** WARNING: exceeds NZ*SPACING_Z, will be clipped ***"
            if max_h > NZ * SPACING_Z
            else "   (fits)"
        )
    )

    footprint_m = (gx.max() - gx.min(), gy.max() - gy.min())
    print(
        f"[extent] footprint after reorient: "
        f"{footprint_m[0]:.0f} m x {footprint_m[1]:.0f} m"
    )

    # rebuild the reoriented mesh so we can run containment in world coords
    Vw = np.column_stack([gx, gy, gz])
    mesh_w = trimesh.Trimesh(vertices=Vw, faces=mesh.faces, process=False)

    if inspect_only:
        _preview_from_mesh(mesh_w)
        print("[inspect-only] no file written.")
        return None

    geo = voxelize(mesh_w)
    occ = int(geo.sum())
    print(
        f"[voxel] occupied voxels = {occ:,} / {geo.size:,} "
        f"({100.0 * occ / geo.size:.2f}%)"
    )

    # top-down preview from the voxel grid (any occupied voxel in a column)
    column_occ = geo.any(axis=0)  # (NY, NX)
    print("\n[preview] top-down footprint (north up, # = building):\n")
    print(ascii_preview(column_occ))
    n_cols = int(column_occ.sum())
    print(
        f"\n[preview] occupied ground columns = {n_cols} "
        f"({100.0 * n_cols / (NX * NY):.1f}% of domain)"
    )

    if out_path:
        # np.save(out_path, geo)
        if out_path:
            if out_path.endswith(".npz"):
                np.savez_compressed(
                    out_path,
                    geometry=geo,
                    grid_spacing=SPACING_XY,
                    grid_spacing_z=SPACING_Z,
                    grid_origin=np.array(ORIGIN),
                )
            else:
                np.save(out_path, geo)
            print(f"\n[save]  wrote {out_path}  shape={geo.shape} dtype={geo.dtype}")
    return geo


def _preview_from_mesh(mesh_w):
    """Cheap footprint preview without full voxelization (for --inspect-only)."""
    lo, hi = mesh_w.bounds
    # sample a coarse XY grid, mark columns whose vertical ray hits the mesh
    xs = np.linspace(
        ORIGIN[0] + SPACING_XY / 2, ORIGIN[0] + (NX - 0.5) * SPACING_XY, NX
    )
    ys = np.linspace(
        ORIGIN[1] + SPACING_XY / 2, ORIGIN[1] + (NY - 0.5) * SPACING_XY, NY
    )
    XX, YY = np.meshgrid(xs, ys)  # (NY, NX)
    pts = np.column_stack(
        [XX.ravel(), YY.ravel(), np.full(XX.size, (lo[2] + hi[2]) / 2)]
    )
    inside = mesh_w.contains(pts).reshape(NY, NX)
    print("\n[preview] mid-height slice footprint (north up):\n")
    print(ascii_preview(inside))


def voxelize(mesh_w):
    """Voxelize the mesh into the output grid.

    When SOLIDIFY_COLUMNS is True (default), uses a fast vertical-ray approach:
    one ray per (x,y) column to find the roof height, then fills ground-to-roof.
    This is ~NZ× faster than full 3D containment testing.

    When SOLIDIFY_COLUMNS is False, falls back to full 3D point-in-solid testing
    (trimesh.contains) restricted to the mesh bounding box.

    No citation required — ray–mesh intersection for voxelization is standard
    computational geometry (same ray-parity basis already used by the old path).
    """
    geo = np.zeros((NZ, NY, NX), dtype=bool)

    # voxel-center coordinate axes in world space
    xs = ORIGIN[0] + (np.arange(NX) + 0.5) * SPACING_XY
    ys = ORIGIN[1] + (np.arange(NY) + 0.5) * SPACING_XY
    zs = ORIGIN[2] + (np.arange(NZ) + 0.5) * SPACING_Z

    # restrict to voxel columns overlapping the mesh bbox
    lo, hi = mesh_w.bounds
    ix = np.where((xs >= lo[0] - SPACING_XY) & (xs <= hi[0] + SPACING_XY))[0]
    iy = np.where((ys >= lo[1] - SPACING_XY) & (ys <= hi[1] + SPACING_XY))[0]

    if len(ix) == 0 or len(iy) == 0:
        print(
            "[voxel] WARNING: mesh bbox does not overlap the grid -- check origin/units"
        )
        return geo

    if SOLIDIFY_COLUMNS:
        # ── Fast path: vertical ray scan ──────────────────────────────
        # One upward ray per (x, y) column.  The highest z-intersection
        # gives the roof; we fill every voxel from z=0 to that roof.
        # Cost: O(NX_sub * NY_sub) rays  vs  O(NX_sub * NY_sub * NZ) contains.
        sub_xs, sub_ys = xs[ix], ys[iy]
        YY, XX = np.meshgrid(sub_ys, sub_xs, indexing="ij")  # (ny_sub, nx_sub)
        n_rays = XX.size

        ray_origins = np.column_stack(
            [
                XX.ravel(),
                YY.ravel(),
                np.full(n_rays, lo[2] - 1.0),  # start just below the mesh
            ]
        )
        ray_dirs = np.tile([0.0, 0.0, 1.0], (n_rays, 1))  # shoot upward

        print(f"[voxel] casting {n_rays:,} vertical rays (column scan)...")

        # Chunked to keep peak memory reasonable on large grids
        CHUNK = 65_536
        roof_z = np.full(n_rays, -np.inf)

        for c0 in range(0, n_rays, CHUNK):
            c1 = min(c0 + CHUNK, n_rays)
            hits, ray_ids, _ = mesh_w.ray.intersects_location(
                ray_origins[c0:c1], ray_dirs[c0:c1], multiple_hits=True
            )
            if len(hits) > 0:
                # ray_ids are chunk-local; offset to global index
                np.maximum.at(roof_z, ray_ids + c0, hits[:, 2])

        # Convert world-z roof heights to voxel indices
        roof_z_grid = roof_z.reshape(len(iy), len(ix))
        roof_k = np.floor((roof_z_grid - ORIGIN[2]) / SPACING_Z).astype(int)
        roof_k = np.clip(roof_k, -1, NZ - 1)

        # Write into the full-size grid (vectorized column fill)
        full_roof = np.full((NY, NX), -1, dtype=int)
        full_roof[np.ix_(iy, ix)] = roof_k

        z_idx = np.arange(NZ)[:, None, None]
        geo = (z_idx <= full_roof[None, :, :]) & (full_roof[None, :, :] >= 0)

        n_col = int((full_roof >= 0).sum())
        print(f"[voxel] solidified {n_col:,} columns ground->roof (ray-based)")

    else:
        # ── Slow path: full 3D containment ────────────────────────────
        iz = np.where((zs >= lo[2] - SPACING_Z) & (zs <= hi[2] + SPACING_Z))[0]
        if len(iz) == 0:
            print("[voxel] WARNING: mesh bbox does not overlap the grid in z")
            return geo

        print(
            f"[voxel] testing block z={len(iz)} y={len(iy)} x={len(ix)} "
            f"= {len(iz) * len(iy) * len(ix):,} points (containment)..."
        )

        ZZ, YY, XX = np.meshgrid(zs[iz], ys[iy], xs[ix], indexing="ij")
        pts = np.column_stack([XX.ravel(), YY.ravel(), ZZ.ravel()])
        inside = mesh_w.contains(pts).reshape(len(iz), len(iy), len(ix))
        geo[np.ix_(iz, iy, ix)] = inside

    return geo


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="GLB city -> SCALED voxel grid")
    ap.add_argument("glb", help="path to the .glb (e.g. southken_solids_scene.glb)")
    ap.add_argument(
        "-o",
        "--out",
        default="geometry.npz",
        help="output path; .npz (default) includes metadata, .npy is raw array for SCALED notebook",
    )
    ap.add_argument(
        "--inspect-only",
        action="store_true",
        help="print the report + footprint preview, but do not voxelize/write",
    )
    args = ap.parse_args()
    convert(
        args.glb,
        None if args.inspect_only else args.out,
        inspect_only=args.inspect_only,
    )
