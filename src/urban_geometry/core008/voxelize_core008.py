"""Blender background Python: direct plain GLB -> 1, 2 or 4 m occupancy.

Uses roof samples at 1 m spacing and ground-to-roof solidification.
This is a sampled 2.5D exterior approximation, not exact mesh-volume voxelization.
"""
import json
import math
import mmap
import struct
import time
import argparse
import sys
from pathlib import Path

import numpy as np
from mathutils import Matrix, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]/'output/core008/geometry'
parser = argparse.ArgumentParser()
parser.add_argument('--spacing', type=int, choices=[1,2,4], default=4)
parser.add_argument('--domain', type=int, default=0, help='Padded square domain in metres; zero retains source XY extent')
parser.add_argument('--height', type=int, default=256)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE = ROOT / 'south_kensington_core008.glb'
OUT = ROOT / (f'south_kensington_core008_voxel_{args.spacing}m' + (f'_domain{args.domain}' if args.domain else ''))
OUT.mkdir(exist_ok=True)
start = time.time()
def log(s):
    print(f'[{time.time()-start:.1f}s] {s}', flush=True)

f = SOURCE.open('rb')
magic, version, length = struct.unpack('<4sII', f.read(12))
assert magic == b'glTF' and version == 2 and length == SOURCE.stat().st_size
n, kind = struct.unpack('<II', f.read(8))
assert kind == 0x4e4f534a
doc = json.loads(f.read(n))
bin_length, kind = struct.unpack('<II', f.read(8))
assert kind == 0x004e4942
bin_offset = f.tell()
mapped = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
assert not doc.get('extensionsRequired'), 'Use the plain GLB, not compressed web GLB'

def accessor(i):
    a = doc['accessors'][i]
    assert not a.get('sparse')
    v = doc['bufferViews'][a['bufferView']]
    assert v.get('buffer',0) == 0
    dtype = np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
    width = {'SCALAR':1,'VEC3':3}[a['type']]
    offset = bin_offset + v.get('byteOffset',0) + a.get('byteOffset',0)
    return np.ndarray((a['count'],width),dtype=dtype,buffer=mapped,offset=offset,
                      strides=(v.get('byteStride',width*dtype.itemsize),dtype.itemsize))

def local(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4,4).T
    x,y,z,w = node.get('rotation',[0,0,0,1])
    m = Matrix.LocRotScale(node.get('translation',[0,0,0]),Quaternion((w,x,y,z)),node.get('scale',[1,1,1]))
    return np.array(m)

world = {}
def visit(i, parent):
    node = doc['nodes'][i]
    world[i] = parent @ local(node)
    for child in node.get('children',[]): visit(child,world[i])
for i in doc['scenes'][doc.get('scene',0)]['nodes']: visit(i,np.eye(4))
# Explicit glTF Y-up -> east/north/up: (x, -z, y).
basis = np.array([[1,0,0],[0,0,-1],[0,1,0]])
provenance = json.loads((ROOT/'south_kensington_core008.json').read_text())
bounds = np.array(provenance['merged']['bounds'])
spacing = float(args.spacing)
assert args.height>0 and args.height % args.spacing == 0
if args.domain:
    assert args.domain % args.spacing == 0
    # Align both new resolutions to the same 4m source origin for exact nesting.
    xy = np.floor(((bounds[0,:2]+bounds[1,:2])/2-args.domain/2)/4)*4
    origin = np.array([*xy,0.])
    nx = ny = args.domain // args.spacing
else:
    origin = np.array([math.floor(bounds[0,0]/spacing)*spacing, math.floor(bounds[0,1]/spacing)*spacing,0.])
    nx,ny = np.ceil((bounds[1,:2]-origin[:2])/spacing).astype(int)
nz = args.height // args.spacing
height = np.zeros((ny,nx),np.float32)
included, excluded = [],[]
sample_offsets = np.arange(.5,spacing,1.).tolist()
global_lo = np.full(3,np.inf); global_hi = -global_lo
for ordinal,(i,transform) in enumerate(world.items()):
    node=doc['nodes'][i]
    if 'mesh' not in node: continue
    name=node.get('name',str(i)); extras=node.get('extras',{})
    # Reject non-building semantic categories even when they refer to a building ID.
    semantic=extras.get('semantic_type')
    selected = bool(extras.get('building_id') or extras.get('building')) and semantic in (None,'building')
    record={'name':name,'building_id':extras.get('building_id',extras.get('building')),'semantic_type':semantic}
    if not selected:
        excluded.append(record); continue
    verts=[]; faces=[]; offset=0
    for p in doc['meshes'][node['mesh']]['primitives']:
        assert p.get('mode',4)==4
        v=accessor(p['attributes']['POSITION']).astype(np.float64)
        v=(v @ transform[:3,:3].T+transform[:3,3]) @ basis.T
        ids=accessor(p['indices']).ravel() if 'indices' in p else np.arange(len(v))
        faces.append(ids.reshape(-1,3).astype(np.int64)+offset)
        verts.append(v); offset+=len(v)
    v=np.concatenate(verts); triangles=np.concatenate(faces)
    lo=v.min(0); hi=v.max(0)
    global_lo=np.minimum(global_lo,lo); global_hi=np.maximum(global_hi,hi)
    record['bounds_xyz_m']=[lo.tolist(),hi.tolist()]
    record['sample_hits']=0
    if hi[2]>0:
        tree=BVHTree.FromPolygons(v.tolist(),triangles.tolist(),all_triangles=True)
        a=np.maximum(0,np.floor((lo[:2]-origin[:2])/spacing).astype(int))
        b=np.minimum([nx,ny],np.ceil((hi[:2]-origin[:2])/spacing).astype(int))
        for iy in range(a[1],b[1]):
            for ix in range(a[0],b[0]):
                h=float(height[iy,ix])
                if h >= hi[2]+1e-4: continue
                for dy in sample_offsets:
                    y=origin[1]+iy*spacing+dy
                    if not lo[1]<=y<=hi[1]:continue
                    for dx in sample_offsets:
                        x=origin[0]+ix*spacing+dx
                        if not lo[0]<=x<=hi[0]:continue
                        hit,normal,index,distance=tree.ray_cast((x,y,float(hi[2]+1)),(0,0,-1),float(hi[2]+2))
                        if hit is not None and hit.z>0:
                            h=max(h,hit.z);record['sample_hits']+=1
                height[iy,ix]=h
    included.append(record)
    if len(included)%400==0:log(f'Processed {len(included)} building meshes')

assert global_hi[2]<nz*spacing, 'Buildings exceed vertical domain'
assert np.all(global_lo[:2]>=origin[:2]-.1)
assert np.all(global_hi[:2]<=origin[:2]+np.array([nx,ny])*spacing+.1)
layers=np.ceil(height/spacing).astype(np.int32)
solid=np.arange(nz)[:,None,None]<layers[None]
assert solid.any() and not solid[-1].any()
np.save(OUT/'solid.npy',solid,allow_pickle=False)
np.save(OUT/'height_m.npy',height,allow_pickle=False)
grid_origin = np.zeros(3) if args.domain else origin.copy()
np.savez_compressed(OUT/'geometry.npz',geometry=solid,solid=solid,height_m=height,
                    grid_origin=grid_origin,grid_spacing=np.array(spacing),grid_spacing_z=np.array(spacing),
                    source_region_origin_xyz_m=origin,
                    spacing_xyz_m=np.full(3,spacing),axis_order=np.array('zyx'))
metadata={
    'source':str(SOURCE),'source_sha256':provenance['files'][SOURCE.name]['sha256'],
    'source_hash_note':'Recorded source hash from merge manifest; not recomputed by this script',
    'spacing_xyz_m':[spacing]*3,'shape_zyx':list(solid.shape),'origin_xyz_m':grid_origin.tolist(),
    'upper_edge_xyz_m':(grid_origin+np.array([nx,ny,nz])*spacing).tolist(),
    'frame':'east/north/up simulation domain in metres' if args.domain else 'region local EPSG:32630, x east, y north, z up; metres',
    'source_region_origin_xyz_m':origin.tolist(),
    'domain_to_region':'region_xyz = domain_xyz + source_region_origin_xyz_m' if args.domain else 'identity',
    'region_projected_origin_xy_m':[695238.304719173,5709236.965026026],
    'source_bounds_in_domain_xyz_m':(bounds-origin if args.domain else bounds).tolist(),
    'padding_xy_low_m':(bounds[0,:2]-origin[:2]).tolist(),
    'padding_xy_high_m':(origin[:2]+np.array([nx,ny])*spacing-bounds[1,:2]).tolist(),
    'cell_center':'origin_xyz_m + ([ix,iy,iz]+0.5)*spacing_xyz_m',
    'solid_semantics':'True=building; False=air. Ground at z=0 is a boundary, not an occupied bottom layer.',
    'method':f'{len(sample_offsets)**2} downward rays per {spacing}m XY cell at 1m-spaced centres; maximum sampled roof height; fill from z=0 to ceil(height/spacing).',
    'limitations':['2.5D column approximation fills overhangs and underpasses; not watertight volume reconstruction.',
                  '1m spaced samples can miss thin features; not conservative triangle-cell intersection.',
                  'Trees, vehicles, roads, presentation base and unlabelled objects excluded.',
                  'Padding contains no supplied building geometry, not evidence of physically obstacle-free surroundings.',
                  'New full-region grid is not plug-compatible with a fixed-shape pretrained wind model.'],
    'selected_meshes':len(included),'excluded_meshes':len(excluded),
    'selected_bounds_xyz_m':[global_lo.tolist(),global_hi.tolist()],
    'max_sampled_height_m':float(height.max()),'occupied_voxels':int(solid.sum()),
    'occupied_fraction':float(solid.mean()),'top_layer_empty':bool(not solid[-1].any()),
    'roundtrip_verified':bool(np.array_equal(np.load(OUT/'solid.npy'),solid)),
}
assert metadata['roundtrip_verified']
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
(OUT/'selection.json').write_text(json.dumps({'included':included,'excluded':excluded},indent=2)+'\n')
log(json.dumps(metadata))
