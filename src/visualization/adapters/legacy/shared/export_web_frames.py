#!/usr/bin/env python3
"""Pre-render the field frames a scene plays into small PNGs (scenes/<id>/physics/web/), so that remote viewers stream
~100 KB per frame instead of 1-13 MB of raw float16. The viewer (viewer/frames.js) uses these when web/index.json exists
and falls back to the raw .npy Range reads otherwise; the raw arrays stay the source of truth.

    uv run --with numpy,pillow python3 scenes/tools/export_web_frames.py <scene id or scene dir> [--only wind,temp,...]

The layer list comes from the scene's scene.json (`layers`): wind -> RGB PNG (u, v, w quantised over web_range),
scalar layers -> 8-bit grey over web_range (default: the display range), pollution -> log10(max(c, 0.1)) over [-1, 4],
shadows -> 1-bit PNG (packed bit arrays are unpacked). Row 0 = south (same orientation as the arrays); nothing is flipped.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
arg = [a for a in sys.argv[1:] if not a.startswith('--')]
if not arg: sys.exit(__doc__)
SCENE = arg[0] if os.path.isdir(arg[0]) else os.path.join(HERE, '..', arg[0])
SCENE = os.path.abspath(SCENE)
scene = json.load(open(os.path.join(SCENE, 'scene.json')))
PHYS = os.path.join(SCENE, 'physics')
OUT = os.path.join(PHYS, 'web')
only = None
for a in sys.argv[1:]:
    if a.startswith('--only'): only = set(a.split('=', 1)[1].split(','))

L = scene['layers']
LAYERS = {}   # key: (array, kind, range, note); kind 'gray' | 'rgb3' | 'bit' | 'log10'
if 'wind' in L:
    w = L['wind']; LAYERS['wind'] = (w['file'], 'rgb3', w.get('web_range', [-2.5, 2.5]), 'u, v, w (m/s)')
if 'temp' in L:
    t = L['temp']; LAYERS['temp'] = (t['file'], 'gray', t.get('web_range', t['range']), 'temperature C')
if 'poll' in L:
    LAYERS['poll'] = (L['poll']['file'], 'log10', [-1.0, 4.0], 'log10 concentration, range [-1, 4] (0.1 .. 1e4); stored log10(max(c, 0.1))')
if 'flood' in L:
    f = L['flood']; r = f.get('web_range', [0.0, 2.0])
    LAYERS['flood'] = (f['file'], 'gray', r, 'water depth m (values above the range saturate)')
    if f.get('max'): LAYERS['floodMax'] = (f['max'], 'gray', r, 'maximum depth m')
if 'solar' in L:
    s = L['solar']
    for date, d in s['dates'].items():
        LAYERS['solar_' + date] = (d['ghi'], 'gray', s.get('web_range', [0.0, 1000.0]), 'GHI W/m2')
        if d.get('shadow'): LAYERS['shadow_' + date] = (d['shadow'], 'bit', None, 'shadow mask, 1 = shaded' + (' (packed bits unpacked)' if s.get('shadow_packed') else ''))
if 'diurnal' in L:
    d = L['diurnal']
    for mode, f in d['files'].items(): LAYERS['diurnal_' + mode] = (f, 'gray', d.get('web_range', [5.0, 45.0]), mode + ' C')

index = {'generated': time.strftime('%Y-%m-%dT%H:%M'), 'scene': scene['id'], 'encoding': 'png; value = lo + v/255*(hi-lo); rgb3 = (u,v,w); bit = mask', 'layers': {}}
if os.path.exists(os.path.join(OUT, 'index.json')):
    index['layers'] = json.load(open(os.path.join(OUT, 'index.json')))['layers']
os.makedirs(OUT, exist_ok=True)


def q(a, lo, hi):
    return np.clip(np.round((a.astype(np.float32) - lo) / (hi - lo) * 255), 0, 255).astype(np.uint8)


for key, (rel, kind, rng, note) in LAYERS.items():
    if only and key not in only: continue
    src = os.path.join(PHYS, rel)
    if not os.path.exists(src): print('missing', rel); continue
    arr = np.load(src, mmap_mode='r')
    static = key == 'floodMax'
    frames = 1 if static else arr.shape[0]
    d = os.path.join(OUT, key); os.makedirs(d, exist_ok=True)
    t0 = time.time(); total = 0; shape = None
    for k in range(frames):
        fr = arr if static else arr[k]
        p = os.path.join(d, f'{k:03d}.png')
        if kind == 'log10':
            img = q(np.log10(np.maximum(fr.astype(np.float32), 0.1)), rng[0], rng[1]); Image.fromarray(img, 'L').save(p, optimize=True)
        elif kind == 'gray':
            img = q(fr, rng[0], rng[1]); Image.fromarray(img, 'L').save(p, optimize=True)
        elif kind == 'rgb3':
            img = np.stack([q(fr[c], rng[0], rng[1]) for c in range(3)], axis=-1); Image.fromarray(img, 'RGB').save(p, optimize=True)
        else:
            m = np.asarray(fr)
            if m.dtype == np.uint8 and m.shape[-1] * 8 <= m.shape[-2] * 2: m = np.unpackbits(m, axis=-1)   # packed bit rows
            img = (m > 0).astype(np.uint8) * 255; Image.fromarray(img, 'L').convert('1').save(p, optimize=True)
        shape = list(img.shape[:2])
        total += os.path.getsize(p)
    rng_used = rng if rng is not None else [0, 1]
    meta = {'source': rel, 'kind': 'gray' if kind == 'log10' else kind, 'range': rng_used, 'frames': frames, 'shape_yx': shape, 'note': note, 'bytes': total, 'avg_kb': round(total / frames / 1024, 1)}
    index['layers'][key] = meta
    print(f'{key:16s} {frames:4d} frames  {total/1e6:6.1f} MB  {meta["avg_kb"]:6.1f} KB/frame  {time.time()-t0:5.1f} s', flush=True)
json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)
print('wrote', os.path.join(OUT, 'index.json'))
