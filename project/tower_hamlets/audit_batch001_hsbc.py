"""Coordinator geometry audit for the fresh HSBC benchmark asset."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

E = Path(__file__).resolve().parent / 'input/canary_wharf_20261007/exports'
P = E / 'benchmark_batch001_hsbc'
O = E / 'benchmark_batch001_hsbc_independent'
O.mkdir(exist_ok=True)
started = datetime.now(timezone.utc).isoformat()
contract = json.loads((P / 'geometry-contract.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native_hash = sha(P / 'hsbc.blend')
assert native_hash == contract['native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(P / 'hsbc.blend'))

def snapshot():
    out = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        vv = [obj.matrix_world @ v.co for v in obj.data.vertices]
        assert vv and all(math.isfinite(x) for v in vv for x in v)
        assert obj.get('building_id') == contract['owner'], obj.name
        out[obj.name] = {
            'bounds': [[min(v[i] for v in vv) for i in range(3)],
                       [max(v[i] for v in vv) for i in range(3)]],
            'triangles': len(obj.data.loop_triangles),
            'owner': obj.get('building_id'), 'id': obj.get('research_object_id'),
            'materials': sorted({obj.data.materials[p.material_index].name
                                 for p in obj.data.polygons}),
        }
    return out

expected = snapshot()
assert abs(max(x['bounds'][1][2] for x in expected.values()) - 199.5) < .001
topology = {}
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    topology[obj.name] = {'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                          'zero_faces': sum(f.calc_area() < 1e-10 for f in bm.faces)}
    bm.free()
assert not any(x['nonmanifold_edges'] or x['zero_faces'] for x in topology.values()), topology
vertices, polygons = [], []
for obj in bpy.data.objects:
    if obj.type != 'MESH' or any(s in obj.name for s in
                              ('estimated_closed_door', 'estimated_door_handles')):
        continue
    offset = len(vertices)
    vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
    polygons.extend([offset+i for i in p.vertices] for p in obj.data.polygons)
tree = BVHTree.FromPolygons(vertices, polygons)
entry = contract['entry']
a = Vector((*entry['a'], 0))
t = Vector((*entry['tangent'], 0))
n = Vector((*entry['normal'], 0))
mid = sum(entry['along']) / 2
rays = []
for dx in (-.9, -.6, .6, .9):
    for z in (.08, .2, 1.1, 2.7):
        origin = a + t*(mid+dx) + n
        origin.z = z
        hit = tree.ray_cast(origin, -n, 2.45)
        rays.append({'offset': dx, 'z': z, 'clear': hit[0] is None})
assert all(x['clear'] for x in rays), rays
roof = bpy.data.objects['HSBC_inset_flat_roof']
roof_tree = BVHTree.FromPolygons([roof.matrix_world @ v.co for v in roof.data.vertices],
                                [list(p.vertices) for p in roof.data.polygons])
outline = contract['mapped_outline']
center = Vector((sum(v[0] for v in outline)/len(outline),
                 sum(v[1] for v in outline)/len(outline), 202))
roof_hits = []
for dx in (-10, 0, 10):
    for dy in (-10, 0, 10):
        hit = roof_tree.ray_cast(center + Vector((dx, dy, 0)), Vector((0, 0, -1)), 10)
        assert hit[0] is not None and abs(hit[0].z-197.5) < .001 and hit[1].z > .99
        roof_hits.append(list(hit[0]))
assert abs(expected['HSBC_mapped_inset_backing']['bounds'][1][2]-197.3) < .001
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P / 'hsbc.glb'))
actual = snapshot()
assert set(actual) == set(expected)
max_error = 0
for name, wanted in expected.items():
    got = actual[name]
    for key in ('triangles', 'owner', 'id', 'materials'):
        assert got[key] == wanted[key], (name, key)
    error = max(abs(x-y) for row, other in zip(got['bounds'], wanted['bounds'])
                for x, y in zip(row, other))
    max_error = max(max_error, error)
assert max_error < .0001
assert sha(P / 'hsbc.blend') == native_hash
(O / 'checks.json').write_text(json.dumps({
    'start_utc': started, 'end_utc': datetime.now(timezone.utc).isoformat(),
    'native_sha256': native_hash, 'glb_sha256': sha(P / 'hsbc.glb'),
    'mesh_count': len(expected), 'height_m': 199.5, 'topology': topology,
    'door_excluded_clear_rays': rays, 'roof_top_hits': roof_hits,
    'backing_top_z': 197.3, 'roof_top_z': 197.5,
    'independent_glb_verified': True, 'max_bounds_error_m': max_error,
    'source_complete': False,
}, indent=2) + '\n')
print('HSBC_COORDINATOR_GEOMETRY_PASS', len(expected), max_error)
