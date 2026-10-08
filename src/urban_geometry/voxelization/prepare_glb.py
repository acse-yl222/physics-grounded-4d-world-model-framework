"""Stream Draco GLB primitives to a local z-up height field; no mesh re-export.

This adapter accepts baked transforms only and samples triangle surfaces at cell
centres. It creates a 2.5-D solid column approximation, not watertight voxels.
"""
import argparse
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np
from numba import njit
from PIL import Image

if __name__ == '__main__' and not __package__:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from urban_geometry.voxelization.glb_plan import read_glb_header, local_bounds, plan_grid

COMPONENT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def read_accessor(doc, f, base, index):
    acc = doc['accessors'][index]
    if 'sparse' in acc or 'bufferView' not in acc:
        raise ValueError('Sparse or bufferless accessors are not supported')
    bv = doc['bufferViews'][acc['bufferView']]
    dtype = np.dtype(COMPONENT[acc['componentType']]); width = WIDTH[acc['type']]
    item = dtype.itemsize * width; stride = bv.get('byteStride', item); count = acc['count']
    f.seek(base + bv.get('byteOffset', 0) + acc.get('byteOffset', 0))
    raw = np.frombuffer(f.read(stride * (count - 1) + item), np.uint8)
    if stride != item:
        raw = np.lib.stride_tricks.as_strided(raw, (count, item), (stride, 1)).copy().reshape(-1)
    return raw.view(dtype).reshape(count, width)


def read_primitive(doc, f, base, primitive):
    """Triangle vertices (N,3 float64) and faces (M,3 int64) for a Draco or plain glTF primitive."""
    ext = primitive.get('extensions', {}).get('KHR_draco_mesh_compression')
    if ext is not None:
        import DracoPy
        bv = doc['bufferViews'][ext['bufferView']]
        f.seek(base + bv.get('byteOffset', 0)); mesh = DracoPy.decode(f.read(bv['byteLength']))
        return mesh.points.astype(np.float64), np.asarray(mesh.faces, dtype=np.int64)
    points = read_accessor(doc, f, base, primitive['attributes']['POSITION']).astype(np.float64)
    if 'indices' in primitive:
        faces = read_accessor(doc, f, base, primitive['indices']).reshape(-1, 3).astype(np.int64)
    else:
        faces = np.arange(len(points) - len(points) % 3, dtype=np.int64).reshape(-1, 3)
    return points, faces


@njit(cache=True)
def raster(vertices, faces, height, ox, oy, cell):
    ny, nx = height.shape
    for face in faces:
        a, b, c = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        den = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(den) < 1e-10:
            continue
        x0 = max(0, int(math.ceil((min(a[0], b[0], c[0])-ox)/cell-.5)))
        x1 = min(nx-1, int(math.floor((max(a[0], b[0], c[0])-ox)/cell-.5)))
        y0 = max(0, int(math.ceil((min(a[1], b[1], c[1])-oy)/cell-.5)))
        y1 = min(ny-1, int(math.floor((max(a[1], b[1], c[1])-oy)/cell-.5)))
        for iy in range(y0, y1+1):
            y = oy+(iy+.5)*cell
            for ix in range(x0, x1+1):
                x = ox+(ix+.5)*cell
                u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
                v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
                w = 1-u-v
                if min(u,v,w) >= -1e-6:
                    z = u*a[2]+v*b[2]+w*c[2]
                    height[iy,ix] = max(height[iy,ix], z)


def category(name, material):
    n, m = name.lower(), material.lower()
    if any(k in m for k in ('foliage', 'tree sage leaves', 'tree deep leaves', 'low planting', 'terrace planting')):
        return 'canopy'
    if any(k in m for k in ('grass', 'mowing bands', 'roof meadow', 'planting approximate')):
        return 'grass'
    if any(k in m for k in ('trees bark', 'street oak')):
        return 'excluded'
    if n.startswith('ground:') or 'extended ground' in n or 'neutral ground' in m:
        return 'ground'
    if any(k in m for k in ('asphalt', 'railway ballast', 'railway steel')):
        return 'asphalt'
    if 'paving' in m or 'public limestone' in m:
        return 'paving'
    if n.startswith('concept public realm') or n.startswith('surrounding public realm'):
        return 'excluded'
    return 'building'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cell', type=int, choices=(1,2,4), default=1)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--crop', type=float, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'),
                    help='Restrict the domain to this local-metre box (z-up frame: x east, y = -gltf_z)')
    ap.add_argument('--min-layers', type=int, default=64, help='Minimum vertical layers kept (wind uses 64)')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out/'metadata.json').exists():
        raise RuntimeError('Already prepared; use a new geometry directory.')
    start = time.time()
    cell = args.cell; coarse = 4*cell
    doc, base = read_glb_header(args.source)
    f = args.source.open('rb')
    # Centred padding; multiples of 256 cells match the SCALED encoder tiles.
    plan = plan_grid(local_bounds(doc), cell, args.crop)
    bounds = plan['bounds']; origin = plan['origin_xy']; nx, ny = plan['nx'], plan['ny']
    maps = {k: np.full((ny,nx), -np.inf, np.float32) for k in ('building','ground','canopy','grass','asphalt','paving')}
    counts = Counter(); selection = []; max_building = 0.; clipped = 0
    materials = doc.get('materials', [])
    for i, node in enumerate(doc['nodes']):
        if 'mesh' not in node:
            continue
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            assert primitive.get('mode',4) == 4
            material = materials[primitive['material']].get('name','') if 'material' in primitive else ''
            cls = category(node.get('name',''), material)
            counts[cls] += 1
            if cls == 'excluded':
                continue
            points, faces = read_primitive(doc, f, base, primitive)
            vertices = points[:,[0,2,1]]; vertices[:,1] *= -1
            if args.crop is not None and (vertices[:,0].max() < bounds[0,0] or vertices[:,0].min() > bounds[1,0]
                                          or vertices[:,1].max() < bounds[0,1] or vertices[:,1].min() > bounds[1,1]):
                continue
            if cls == 'building':
                zmax = float(vertices[:,2].max()); max_building = max(max_building,zmax)
                clipped += int(zmax > 64*cell)
            raster(vertices, faces, maps[cls], *origin, float(cell))
            if cls == 'building' and float(vertices[:,2].max()) > 64*cell:
                selection.append({'node': node.get('name'), 'material': material, 'max_z_m': float(vertices[:,2].max())})
        if i % 1000 == 0:
            print(f'{i}/{len(doc["nodes"])} nodes, {time.time()-start:.1f}s', flush=True)
    roof = np.maximum(maps['building'], 0)
    footprint = roof > .5
    # Retain supplied terrain independently: do not label an artistic ground mesh as survey DTM.
    ground_valid = np.isfinite(maps['ground'])
    ground = np.where(ground_valid, maps['ground'], 0).astype(np.float32)
    height = roof.astype(np.float32)
    nz = max(args.min_layers, int(math.ceil(max_building/(32*cell))*32))
    solid = np.lib.format.open_memmap(args.out/'solid.npy', mode='w+', dtype=bool, shape=(nz,ny,nx))
    for z in range(nz):
        solid[z] = z < np.ceil(height/cell)
    solid.flush(); del solid
    np.save(args.out/'height_m.npy',height)
    np.save(args.out/'ground_mesh_m_yx.npy',ground)
    np.save(args.out/'ground_mesh_valid_yx.npy',ground_valid)
    np.save(args.out/f'footprint_{cell}m_yx.npy',footprint)
    np.save(args.out/f'footprint_{coarse}m_yx.npy',footprint.reshape(ny//4,4,nx//4,4).any(axis=(1,3)))
    for cls in ('canopy','grass','asphalt','paving'):
        mask = np.isfinite(maps[cls])
        np.save(args.out/f'{cls}_{coarse}m_yx.npy',mask.reshape(ny//4,4,nx//4,4).any(axis=(1,3)))
    np.save(args.out/f'height_{coarse}m_yx.npy',height.reshape(ny//4,4,nx//4,4).max(axis=(1,3)))
    h4 = height.reshape(ny//4,4,nx//4,4).max(axis=(1,3))
    color = np.zeros((*h4.shape,3),np.uint8)+225
    color[h4>0] = np.stack([np.clip(80+h4[h4>0],0,255),np.clip(130-h4[h4>0]/2,0,255),np.full_like(h4[h4>0],170)],axis=-1).astype(np.uint8)
    Image.fromarray(color[::-1]).save(args.out/'height_preview.png')
    digest=hashlib.file_digest(args.source.open('rb'),'sha256').hexdigest()
    meta={'source':str(args.source.resolve()),'source_sha256':digest,'bounds_local_xyz_m':bounds.tolist(),
          'crop_local_m':args.crop,
          'source_region_origin_xyz_m':[*origin.tolist(),0.], 'shape_zyx':[nz,ny,nx], 'spacing_xyz_m':[cell]*3,
          'axis_order':'zyx','gltf_to_local_xyz':'(x,-z,y)', 'horizontal_orientation':'assumed x east, -gltf_z north; not georeferenced',
          'cell_centres':f'local_xyz = origin + (index_xyz + 0.5) * {cell} metres', 'max_building_z_m':max_building,
          'primitives_above_wind_domain':clipped,'footprint_fraction':float(footprint.mean()),'classification_counts':dict(counts),
          'ground_mesh_range_m':[float(ground.min()),float(ground.max())], 'georeferenced':False,
          'method':f'{cell} m cell-centre barycentric triangle sampling; maximum roof; solid columns from z=0; excludes foliage and ground materials',
          'limits':['Semantic classification inferred from names/materials; not supplied building labels.',
                    'Overhangs and bridges become solid columns; thin features may be missed.',
                    'Ground mesh is not a verified terrain elevation model.', f'Full geometry retained; wind workflow uses bottom {64*cell} m.'],
          'seconds':time.time()-start}
    (args.out/'above_wind_domain.json').write_text(json.dumps(selection,indent=2))
    (args.out/'metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2),flush=True)


if __name__=='__main__':
    main()
