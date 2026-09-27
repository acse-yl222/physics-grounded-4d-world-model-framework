"""Bird voxel geometry for the South Kensington station area (2026-09-12).

Crops the viewer's own 4 m building voxels (scenes/south_kensington/physics/masks/solid_4m_zyx.npy: 16 layers x 4 m, True = building,
the conservative voxels used by the wind model) to a box around South Kensington station and writes the NPZ that
Akira's simulation expects (geometry[z, y, x] bool, grid_spacing, grid_spacing_z, grid_origin) plus a META json for
build_bird_replay_v2.py. Frame contract as in build_bird_geometry_v2.py: bird (x, y, z) = (worldX, -worldZ, worldY).
Field arrays: row 0 = south = domain y 640 -> world Z = -(640 - 2124) = +1484 (south is +Z), so row index increases
northwards = bird y increases; col 0 = west = domain x 480 -> world X = 480 - 2116 = -1636.
Usage: python build_bird_geometry_southken.py --mask scenes/south_kensington/physics/masks/solid_4m_zyx.npy --out geometry.npz --x0 640 --x1 1240 --z0 380 --z1 980
"""
import argparse, json, hashlib
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--mask', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--x0', type=float, required=True); ap.add_argument('--x1', type=float, required=True)
ap.add_argument('--z0', type=float, required=True); ap.add_argument('--z1', type=float, required=True)
ap.add_argument('--ceiling', type=float, default=100.0)
a = ap.parse_args()
CELL, X0, ZS = 4.0, 480 - 2116, -(640 - 2124)     # world X of col 0 edge, world Z of row 0 (south) edge
m = np.load(a.mask)                                # (16, 704, 768) z, row(south->north), col(west->east)
nz0, H, W = m.shape
# bird y = -Z; row r spans Z in [ZS - (r+1)*CELL, ZS - r*CELL] -> bird y in [r*CELL - ZS, (r+1)*CELL - ZS]
by0, by1 = -a.z1, -a.z0
c0, c1 = int(np.floor((a.x0 - X0) / CELL)), int(np.ceil((a.x1 - X0) / CELL))
r0, r1 = int(np.floor((by0 + ZS) / CELL)), int(np.ceil((by1 + ZS) / CELL))
sub = m[:, r0:r1, c0:c1]
nz = int(np.ceil(a.ceiling / CELL))
G = np.zeros((nz, sub.shape[1], sub.shape[2]), dtype=bool); G[:min(nz, nz0)] = sub[:min(nz, nz0)]
origin = np.array([X0 + c0 * CELL, r0 * CELL - ZS, 0.0])
np.savez_compressed(a.out, geometry=G, grid_spacing=CELL, grid_spacing_z=CELL, grid_origin=origin)
h = hashlib.sha256(open(a.mask, 'rb').read()).hexdigest()
meta = {'schema': 'UWM_VIEWER_BIRD_GEOMETRY_SOUTHKEN_V1', 'source_mask': {'path': a.mask, 'sha256': h, 'meaning': 'scenes/south_kensington/physics/masks/solid_4m_zyx.npy, 16 x 4 m layers of conservative building voxels (wind model solids)'},
        'transform': 'bird=(worldX, -worldZ, worldY); viewer=(bird_x, bird_z, -bird_y)', 'ground_datum_m': 0.0,
        'world_box': {'x': [origin[0], origin[0] + G.shape[2] * CELL], 'z': [-(origin[1] + G.shape[1] * CELL), -origin[1]], 'ceiling_m': nz * CELL},
        'bird_grid': {'origin': origin.tolist(), 'spacing_xy_m': CELL, 'spacing_z_m': CELL, 'shape_zyx': list(G.shape), 'voxels': int(G.size), 'occupied_voxels': int(G.sum()), 'occupied_share': round(float(G.mean()), 4)},
        'landmark_checks': [], 'note': 'South Kensington station is at world (937, 674); box chosen so that roost / forage sites lie around the station'}
json.dump(meta, open(a.out.replace('.npz', '_META.json'), 'w'), indent=1)
print(json.dumps(meta['world_box']), json.dumps(meta['bird_grid']))
# sanity: the station building (world ~ (920..960, 655..690)) should be occupied at low levels
sx, sz = 937.0, 674.0; i = int((sx - origin[0]) / CELL); j = int((-sz - origin[1]) / CELL)
print('station column occupied levels:', int(G[:, j, i].sum()), '| column top m:', float(G[:, j, i].sum() * CELL))
