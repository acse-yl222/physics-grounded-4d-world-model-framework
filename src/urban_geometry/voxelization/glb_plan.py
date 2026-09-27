"""GLB header reading and grid planning shared by the voxeliser and the scene runner.

Only the JSON chunk is parsed here; no geometry is decoded, so this module needs
numpy only and is safe to import for --dry-run planning.
"""
import json
import struct
from pathlib import Path

import numpy as np

PAD_M = 128  # margin added around the geometry before rounding up to whole SCALED tiles


def read_glb_header(path):
    """Return (doc, base_offset) for a binary glTF 2.0 file; base is the BIN chunk start."""
    path = Path(path)
    with path.open('rb') as f:
        magic, version, length = struct.unpack('<4sII', f.read(12))
        if magic != b'glTF' or version != 2:
            raise ValueError(f'{path} is not a binary glTF 2.0 file')
        if length != path.stat().st_size:
            raise ValueError(f'{path}: header length does not match file size (truncated?)')
        size, kind = struct.unpack('<II', f.read(8))
        if kind != 0x4e4f534a:
            raise ValueError('First GLB chunk is not JSON')
        doc = json.loads(f.read(size))
        _, kind = struct.unpack('<II', f.read(8))
        if kind != 0x004e4942:
            raise ValueError('Second GLB chunk is not BIN')
        base = f.tell()
    return doc, base


def local_bounds(doc):
    """Axis-aligned bounds in local z-up metres, from POSITION accessor min/max: gltf (x,y,z) -> local (x,-z,y)."""
    for node in doc['nodes']:
        if any(k in node for k in ('matrix', 'translation', 'rotation', 'scale', 'children')):
            raise ValueError('This adapter requires baked world transforms (no node matrix/TRS/children).')
    accessors = [doc['accessors'][p['attributes']['POSITION']] for m in doc['meshes'] for p in m['primitives']]
    lo = np.min([a['min'] for a in accessors], axis=0)
    hi = np.max([a['max'] for a in accessors], axis=0)
    return np.array([[lo[0], -hi[2], lo[1]], [hi[0], -lo[2], hi[1]]], dtype=np.float64)


def plan_grid(bounds, cell, crop=None):
    """Horizontal grid for the SCALED encoder: centred padding, edge a multiple of 256 cells.

    bounds: [[x0,y0,z0],[x1,y1,z1]] local metres. crop: optional [x0,y0,x1,y1] local metres
    intersected with the geometry bounds. Returns dict(bounds, origin_xy, size_xy_m, nx, ny).
    """
    bounds = np.array(bounds, dtype=np.float64).copy()
    if crop is not None:
        crop = np.asarray(crop, dtype=np.float64)
        if crop.shape != (4,) or crop[2] <= crop[0] or crop[3] <= crop[1]:
            raise ValueError('crop must be [x0, y0, x1, y1] in local metres with x1 > x0 and y1 > y0')
        bounds[0, :2] = np.maximum(bounds[0, :2], crop[:2])
        bounds[1, :2] = np.minimum(bounds[1, :2], crop[2:])
        if np.any(bounds[1, :2] <= bounds[0, :2]):
            raise ValueError('crop does not intersect the geometry bounds')
    tile = 256 * cell
    size_xy = np.ceil((bounds[1, :2] - bounds[0, :2] + PAD_M) / tile).astype(int) * tile
    origin = np.floor(((bounds[0, :2] + bounds[1, :2] - size_xy) / 2) / 4) * 4
    nx, ny = (int(v) for v in size_xy // cell)
    return {'bounds': bounds, 'origin_xy': origin, 'size_xy_m': size_xy, 'nx': nx, 'ny': ny}
