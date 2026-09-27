"""revision_02 bird geometry adapter (CO, 2026-09-11).

Builds the voxel occupancy NPZ that Akira's bird simulation expects
(birds/sim/integrator._load_geometry: keys geometry[z,y,x] bool, grid_spacing,
grid_spacing_z, grid_origin) for a bounded city sub-area, from the VERIFIED building
classification already used by the traffic work: decoded_building_hulls_v1.json
(6,681 building_id mesh nodes, world XZ convex hull + world Y range) and, where
available, exact decoded footprints. Roads, trees and street furniture are never
voxelised (they are not building_id nodes).

Coordinate contract (explicit; verified below with landmarks):
    bird (x, y, z) = (worldX, -worldZ, worldY - ground_datum)     ground_datum = 0.0 m
    viewer (X, Y, Z) = (bird_x, bird_z + ground_datum, -bird_y)
Voxel index order is (z, y, x); grid_origin is the bird-frame position of cell (0,0,0).
Conservative: convex hulls fill courtyards; the whole hull is solid from ground to
its maximum height (no overhangs/bridges).
"""
import argparse
import hashlib
import json
import pickle
import time
import numpy as np
from shapely.geometry import Polygon, Point
from shapely import wkb as _wkb
from shapely.strtree import STRtree


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hulls', required=True)
    ap.add_argument('--exact', default=None, help='pickle of exact footprints (nodes, wkb) to prefer over hulls')
    ap.add_argument('--out', required=True)
    ap.add_argument('--x0', type=float, required=True, help='world X min')
    ap.add_argument('--x1', type=float, required=True)
    ap.add_argument('--z0', type=float, required=True, help='world Z min (south is +Z)')
    ap.add_argument('--z1', type=float, required=True)
    ap.add_argument('--ceiling', type=float, default=100.0)
    ap.add_argument('--dx', type=float, default=4.0)
    ap.add_argument('--dz', type=float, default=2.0)
    ap.add_argument('--datum', type=float, default=0.0)
    args = ap.parse_args()
    t0 = time.time()
    hulls = json.load(open(args.hulls))
    exact = {}
    if args.exact:
        ex = pickle.load(open(args.exact, 'rb'))
        exact = {n: _wkb.loads(w) for n, w in zip(ex['nodes'], ex['wkb'])}
    # bird frame: x = X, y = -Z
    bx0, bx1 = args.x0, args.x1
    by0, by1 = -args.z1, -args.z0
    nx = int(np.ceil((bx1 - bx0) / args.dx))
    ny = int(np.ceil((by1 - by0) / args.dx))
    nz = int(np.ceil(args.ceiling / args.dz))
    geometry = np.zeros((nz, ny, nx), dtype=bool)
    xs = bx0 + (np.arange(nx) + 0.5) * args.dx
    ys = by0 + (np.arange(ny) + 0.5) * args.dx
    selected, skipped = [], 0
    polys, heights, names = [], [], []
    for b in hulls['buildings']:
        v = b['world_xz_convex_hull']
        if len(v) < 3:
            skipped += 1
            continue
        top = b['world_y_range_m'][1] - args.datum
        if top <= 0:
            skipped += 1
            continue
        g = exact.get(b['node_index'])
        if g is None or g.is_empty:
            g = Polygon(v)
        # to bird frame: (X, -Z)
        def flip(geom):
            from shapely.ops import transform
            return transform(lambda x, z: (x, -z), geom)
        gb = flip(g)
        if gb.bounds[2] < bx0 or gb.bounds[0] > bx1 or gb.bounds[3] < by0 or gb.bounds[1] > by1:
            continue
        polys.append(gb)
        heights.append(top)
        names.append(b['name'])
    tree = STRtree(polys)
    # rasterise: for each polygon, mark voxel centres inside up to its height
    from shapely import contains_xy
    for gb, top, nm in zip(polys, heights, names):
        minx, miny, maxx, maxy = gb.bounds
        i0, i1 = max(0, int((minx - bx0) / args.dx)), min(nx - 1, int((maxx - bx0) / args.dx))
        j0, j1 = max(0, int((miny - by0) / args.dx)), min(ny - 1, int((maxy - by0) / args.dx))
        if i1 < i0 or j1 < j0:
            continue
        gx, gy = np.meshgrid(xs[i0:i1 + 1], ys[j0:j1 + 1])
        inside = contains_xy(gb, gx.ravel(), gy.ravel()).reshape(gy.shape)
        if not inside.any():
            continue
        k1 = min(nz, int(np.ceil(top / args.dz)))
        geometry[0:k1, j0:j1 + 1, i0:i1 + 1] |= inside[None, :, :]
        selected.append({'name': nm, 'top_m': round(top, 2)})
    np.savez_compressed(args.out, geometry=geometry, grid_spacing=float(args.dx), grid_spacing_z=float(args.dz),
                        grid_origin=np.array([bx0, by0, 0.0], dtype=float))
    # landmark checks in bird frame
    def occ(bird_xyz):
        x, y, z = bird_xyz
        i, j, k = int((x - bx0) / args.dx), int((y - by0) / args.dx), int(z / args.dz)
        if 0 <= i < nx and 0 <= j < ny and 0 <= k < nz:
            return bool(geometry[k, j, i])
        return None
    landmarks = []
    for key in ["Queen's Tower | 01", 'Natural History Museum', 'Sherfield Building | 01', 'Huxley Building', 'Royal Albert Hall']:
        m = [b for b in hulls['buildings'] if key.lower() in b['name'].lower()]
        if not m:
            continue
        b = max(m, key=lambda b: b['world_y_range_m'][1])
        cx = sum(p[0] for p in b['world_xz_convex_hull']) / len(b['world_xz_convex_hull'])
        cz = sum(p[1] for p in b['world_xz_convex_hull']) / len(b['world_xz_convex_hull'])
        top = b['world_y_range_m'][1]
        bird = (cx, -cz, top / 2 - args.datum)
        landmarks.append({'name': b['name'], 'world_centre_xz': [round(cx, 1), round(cz, 1)], 'top_m': round(top, 1), 'bird_xyz_mid_height': [round(v, 1) for v in bird],
                          'occupied_at_mid_height': occ(bird), 'occupied_above_top_plus_4m': occ((cx, -cz, top - args.datum + 4.0))})
    meta = {'schema': 'UWM_DEMO_REVISION_02_BIRD_GEOMETRY_V1', 'source_hulls': {'path': args.hulls, 'sha256': sha256(args.hulls)},
            'exact_footprints_used': len(exact), 'transform': 'bird=(worldX, -worldZ, worldY-datum); viewer=(bird_x, bird_z+datum, -bird_y)', 'ground_datum_m': args.datum,
            'world_box': {'x': [args.x0, args.x1], 'z': [args.z0, args.z1], 'ceiling_m': args.ceiling},
            'bird_grid': {'origin': [bx0, by0, 0.0], 'spacing_xy_m': args.dx, 'spacing_z_m': args.dz, 'shape_zyx': list(geometry.shape),
                          'voxels': int(geometry.size), 'occupied_voxels': int(geometry.sum()), 'occupied_share': round(float(geometry.mean()), 4)},
            'buildings_selected': len(polys), 'buildings_skipped_degenerate_or_flat': skipped,
            'selection_rule': 'building_id mesh nodes only (decoded_building_hulls_v1.json); roads/trees/furniture are not building nodes and are never voxelised; hull solid from ground to its max height (conservative, fills courtyards).',
            'landmark_checks': landmarks, 'wall_s': round(time.time() - t0, 1)}
    json.dump(meta, open(args.out.replace('.npz', '_META.json'), 'w'), indent=1)
    print(json.dumps({k: meta[k] for k in ('bird_grid', 'buildings_selected', 'landmark_checks')}, indent=1))


if __name__ == '__main__':
    main()
