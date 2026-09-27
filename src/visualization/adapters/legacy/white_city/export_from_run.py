#!/usr/bin/env python3
"""Collect the viewer arrays of the White City scene from the UrbanWorldModel run output.

    python3 export_from_run.py --run ~/workspace/UrbanWorldModel/output/white_city --out <scene>/physics

Reads the 2 m voxel geometry, the SCALED 8 m wind frames, the 3-D physical temperature run, the tracer transport run,
the experimental solar and flood runs, and writes one viewer array per layer (float16 tyx, row 0 = south = local -y,
col 0 = west = local -x) plus manifest.json (frame times, sun positions, rain). Frames keep the run's own clocks:
wind / pollution 50 s per step (steps 1..100), temperature 50 s per frame (frames 0..20), sunlight every 10 min,
flood every 5 min (37 frames over 3 h).
"""
import argparse
import glob
import json
import os
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--run', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--layer', type=int, default=1, help='8 m vertical layer for wind / temperature / pollution (1 = 8-16 m)')
a = ap.parse_args()
RUN, OUT, LZ = os.path.abspath(a.run), os.path.abspath(a.out), a.layer
os.makedirs(OUT, exist_ok=True)
man = {'run': 'white_city', 'generated': time.strftime('%Y-%m-%dT%H:%M'), 'source_run': RUN, 'cell_m': 2, 'coarse_cell_m': 8,
       'local_origin_xy_m': [-1492.0, -2548.0], 'gltf_to_local_xyz': '(x, -z, y)',
       'orientation': 'row 0 = south (local -y), col 0 = west (local -x); north assumed = local +y (not georeferenced)',
       'wind_step_seconds': 50.0, 'arrays': {}, 'limits': []}


def save(rel, arr, **meta):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    np.save(p, arr)
    man['arrays'][rel] = {'shape': list(arr.shape), 'dtype': str(arr.dtype), **meta}
    print(f'{rel:50s} {str(arr.dtype):8s} {arr.shape} {os.path.getsize(p)/1e6:7.1f} MB', flush=True)


# ---- geometry masks
G = os.path.join(RUN, 'geometry', 'voxel_2m')
fp2 = np.load(os.path.join(G, 'footprint_2m_yx.npy')); h2 = np.load(os.path.join(G, 'height_m.npy'))
save('masks/building_footprint_2m_yx.npy', fp2.astype(bool), meaning='True = building column (2 m cells)')
save('masks/roof_height_m_2m_yx.npy', h2.astype(np.float16), meaning='max roof height per 2 m cell, metres')
save('masks/building_footprint_8m_yx.npy', np.load(os.path.join(G, 'footprint_8m_yx.npy')).astype(bool), meaning='True = building (8 m cells)')
solid8 = np.load(os.path.join(RUN, 'physics', 'scaled_latent', 'temperature', 'solid_8m_zyx.npy')).astype(bool)
save('masks/solid_8m_zyx.npy', solid8, meaning='True = building, 16 layers x 8 m (bottom 128 m)')
for k in ('grass', 'asphalt', 'paving', 'canopy'):
    p = os.path.join(G, f'{k}_8m_yx.npy')
    if os.path.exists(p): save(f'masks/{k}_8m_yx.npy', np.load(p).astype(bool), meaning=f'{k} (8 m cells, from the GLB materials)')
# where is the tall cluster (for the camera focus)
ys, xs = np.nonzero(h2 > 40)
if len(xs):
    print('tall cluster (>40 m) local x %.0f..%.0f, y %.0f..%.0f m; gltf Z = -y' % (-1492 + xs.min() * 2, -1492 + xs.max() * 2 + 2, -2548 + ys.min() * 2, -2548 + ys.max() * 2 + 2))
    print('tallest cell: x %.0f y %.0f (%.1f m)' % (-1492 + np.argmax(h2.max(0)) * 2, -2548 + np.argmax(h2.max(1)) * 2, h2.max()))

# ---- wind: SCALED 8 m coarse frames, one vertical layer, steps 1..100 (frame 000 is the initial state)
W = os.path.join(RUN, 'physics', 'scaled_latent', 'wind')
files = sorted(glob.glob(os.path.join(W, 'wind8m_*.npz')))[1:]
uvw = np.empty((len(files), 3, 448, 448), np.float16)
for i, f in enumerate(files): uvw[i] = np.load(f)['uvw'][:, LZ]
save(f'wind/uvw_8m_z{LZ*8}-{LZ*8+8}m_tcyx.npy', uvw, components='u local +x, v local +y (assumed north), w up (m/s); coarse_wind already restores the +x sign',
     time_s=[50.0 * (i + 1) for i in range(len(files))], note='SCALED latent surrogate, 4x block mean of the 2 m field, solid cells zero')

# ---- temperature: 3-D physical solver, 8 m, 21 frames over 1000 s
T = os.path.join(RUN, 'physics', 'temperature3d_physical')
tz = np.load(os.path.join(T, 'temperature_c_tzyx.npy'), mmap_mode='r')
cfg = json.load(open(os.path.join(T, 'run_config.json')))
save(f'temperature/temperature_8m_z{LZ*8}-{LZ*8+8}m_tyx.npy', np.asarray(tz[:, LZ]).astype(np.float16),
     time_s=[cfg['duration_seconds'] / (tz.shape[0] - 1) * i for i in range(tz.shape[0])], units='C', ambient_c=cfg['ambient_c'], surface_c=cfg['surface_c'],
     note='Yi Qi 3-D finite-difference solver driven by the last 20 wind frames; controlled 26 / 30 C scenario')
man['temperature3d_physical'] = {k: cfg[k] for k in ('ambient_c', 'surface_c', 'cell_m', 'duration_seconds', 'limitations') if k in cfg}

# ---- pollution: tracer transport, 8 m, 100 frames
P = os.path.join(RUN, 'physics', 'scaled_latent', 'pollution')
files = sorted(glob.glob(os.path.join(P, 'concentration_*.npz')))
conc = np.empty((len(files), 448, 448), np.float16)
for i, f in enumerate(files): conc[i] = np.load(f)['concentration'][LZ]
save(f'pollution/concentration_8m_z{LZ*8}-{LZ*8+8}m_tyx.npy', conc, time_s=[50.0 * (i + 1) for i in range(len(files))],
     note='upwind transport of an assumed line source, driven by the wind frames; arbitrary units')

# ---- sunlight: experimental run (assumed georeferencing), 8 m GHI every 10 min + 2 m shadow masks (packed bits)
S = os.path.join(RUN, 'physics', 'solar_experimental')
scfg = json.load(open(os.path.join(S, 'run_config.json')))['config']
man['solar'] = {'assumptions': scfg['assumptions'], 'dates': scfg['solar']['dates'], 'minutes': scfg['solar']['minutes']}
for date in scfg['solar']['dates']:
    d = os.path.join(S, date); tag = date.replace('-', '')
    frames = json.load(open(os.path.join(d, 'frames.json')))
    meta = dict(time_local=[f['local_time'][11:16] for f in frames], time_utc=[f['utc'] for f in frames], altitude_deg=[round(f['altitude_deg'], 2) for f in frames], azimuth_deg=[round(f['azimuth_deg'], 2) for f in frames])
    ghi = np.load(os.path.join(d, 'ghi_8m_tyx.npy'))
    save(f'solar/ghi_8m_{tag}_tyx.npy', ghi.astype(np.float16), units='W/m2', **meta)
    sh = sorted(glob.glob(os.path.join(d, 'shadow_*_packed.npy')))
    packed = np.stack([np.load(f) for f in sh])
    save(f'solar/shadow_2m_{tag}_packed_tyx.npy', packed.astype(np.uint8), packed_bits='axis 1 (columns), np.unpackbits -> 1792 columns', meaning='1 = shaded (direct beam blocked)', **meta)
    daily = os.path.join(d, 'daily_irradiation_kwh_m2.npy')
    if os.path.exists(daily): save(f'solar/daily_irradiation_kwh_m2_{tag}_yx.npy', np.load(daily).astype(np.float16), units='kWh/m2/day')
svf = os.path.join(S, 'sky_view_factor.npy')
if os.path.exists(svf): save('solar/sky_view_factor_2m_yx.npy', np.load(svf).astype(np.float16))

# ---- flood: experimental shallow-water run on the GLB ground, 2 m, every 5 min for 3 h
F = os.path.join(RUN, 'physics', 'flood_experimental')
fcfg = json.load(open(os.path.join(F, 'run_config.json')))['config']
series = json.load(open(os.path.join(F, 'series.json')))
files = sorted(glob.glob(os.path.join(F, 'depth_*.npz')))
depth = np.empty((len(files), 1792, 1792), np.float16)
for i, f in enumerate(files): depth[i] = np.load(f)['depth_m']
rain15 = fcfg['flood']['rain_mm_h_15min']
time_s = [round(s['time_seconds']) for s in series][:len(files)]
rain = [rain15[int(t // 900)] if t // 900 < len(rain15) else 0.0 for t in time_s]
save('flood/depth_2m_tyx.npy', depth, units='m', time_s=time_s, rain_mm_h=rain, max_depth_m=[round(s['max_depth_m'], 3) for s in series][:len(files)],
     note='semi-implicit shallow-water solver on the GLB ground mesh (not surveyed terrain); design storm ' + str(rain15) + ' mm/h per 15 min, sewer %s mm/h' % fcfg['flood']['sewer_mm_h'])
save('flood/max_depth_2m_yx.npy', np.load(os.path.join(F, 'max_depth_m.npy')).astype(np.float32), units='m', meaning='maximum depth over the event')
man['flood'] = {'assumptions': fcfg['assumptions'], **fcfg['flood']}
man['limits'] = ['Not georeferenced: north assumed local +y, assumed latitude %.4f / longitude %.4f for the sun.' % (scfg['assumptions']['latitude_deg'], scfg['assumptions']['longitude_deg']),
                 'Wind: SCALED surrogate transfer, no CFD or measured validation.', 'Temperature: controlled scenario.', 'Pollution: assumed line source.', 'Flood: GLB ground mesh as terrain.']
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print('wrote', os.path.join(OUT, 'manifest.json'))
