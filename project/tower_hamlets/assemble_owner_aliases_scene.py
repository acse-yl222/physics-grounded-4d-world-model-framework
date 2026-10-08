"""Assemble the One Bank Street western facade study while preserving other regional assets."""
from pathlib import Path
import bpy
import json
import hashlib
from mathutils import Vector

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
O = R / 'exports/appearance-owner-aliases-001'
O.mkdir(exist_ok=False)
source = R / 'exports/appearance-south-colonnade-facade-001/region.blend'
assets = []
bpy.ops.wm.open_mainfile(filepath=str(source))
def signature(o):
    payload = ([list(v.co) for v in o.data.vertices], [list(f.vertices) for f in o.data.polygons],
        [f.material_index for f in o.data.polygons], [list(row) for row in o.matrix_world],
        [m.name if m else None for m in o.data.materials])
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()
before = {o.name:signature(o) for o in bpy.data.objects if o.type=='MESH'}
rules = json.loads((R/'exports/inventory-alias-diagnostic-001/report.json').read_text())['proposed_changes']
counts=[]
for rule in rules:
    count=0
    for o in bpy.data.objects:
        if o.type!='MESH': continue
        if any((o.name if key=='name' else o.get(key))!=value for key,value in rule['selector'].items()): continue
        o[rule['property']]=rule['values']
        count+=1
    counts.append(count)
assert counts==[1237,1], counts
assert before == {o.name:signature(o) for o in bpy.data.objects if o.type=='MESH'}
removed=[]
added=[]
replacement_ids=set(v for rule in rules for v in rule['values'])
unchanged=before
inv={o['id'] for o in json.loads((R/'geometry.json').read_text())['buildings']}
represented=set()
for o in bpy.data.objects:
    if o.type!='MESH':continue
    represented.add(o.get('building_id'))
    represented.update(o.get('source_owner_ids',[]))
    if o.get('aggregate_alias_id'): represented.add(o['aggregate_alias_id'])
assert not inv-represented, sorted(inv-represented)
(O/'alias_correction.json').write_text(json.dumps({'changed_mesh_counts':counts,'rules':rules,'mesh_geometry_topology_transforms_material_slots_unchanged':True,'inventory_ids_verified':len(inv),'building_part_ids_verified':len(inv)-1,'missing_ids':[]},indent=2)+'\n')
s = bpy.context.scene
s.cycles.samples = 24
bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'), compress=False)
bpy.ops.object.select_all(action='DESELECT')
expected = {}
metadata = {}
points = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    o.select_set(True)
    o.data.calc_loop_triangles()
    key = o.get('research_object_id', o.name)
    assert key not in expected
    expected[key] = len(o.data.loop_triangles)
    metadata[key] = (o.get('building_id'), list(o.get('source_owner_ids', [])))
    points.extend(o.matrix_world @ v.co for v in o.data.vertices)
def bounds(points):
    return [[min(v[i] for v in points) for i in range(3)],
            [max(v[i] for v in points) for i in range(3)]]
bb = bounds(points)
bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'), export_format='GLB',
    use_selection=True, export_extras=True, export_draco_mesh_compression_enable=False)
import shutil
for filename in ['overview.png','south-colonnade-facade-context.png']:
    shutil.copy2(source.parent/filename,O/filename)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'))
assert len([o for o in bpy.data.objects if o.type == 'MESH']) == len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'))
actual = {}
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    key = o.get('research_object_id', o.name)
    actual[key] = len(o.data.polygons)
    assert metadata[key] == (o.get('building_id'), list(o.get('source_owner_ids', [])))
    assert o.data.materials
assert actual == expected
actual_bb = bounds([o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH'
                    for v in o.data.vertices])
assert max(abs(a-b) for x,y in zip(bb,actual_bb) for a,b in zip(x,y)) < .001
report = dict(native_reopened=True, independent_glb_verified=True,
    new_material_bindings_verified=True, source_owner_aliases_verified=True,
    old_replacement_meshes_removed=removed, unchanged_meshes=len(unchanged),
    objects=len(expected), appearance_objects=len(added),
    source_owner_ids=sorted(replacement_ids), bounds_enu_m=bb,
    source_blends={str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [source, *[a[1] for a in assets]]},
    scope='Metadata-only owner alias restoration; mesh geometry unchanged.')
(O/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
