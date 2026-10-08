"""Assemble the One Bank Street western facade study while preserving other regional assets."""
from pathlib import Path
import bpy
import json
import hashlib
from mathutils import Vector

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
O = R / 'exports/appearance-northern-trust-001'
O.mkdir(exist_ok=False)
source = R / 'exports/appearance-columbus-001/region.blend'
west_id = 'overture-building-8a6a6456-5ff1-4be7-9a11-7a82b9ed825d'
morgan_ids = set()
assets = [('northern_trust', R/'exports/northern-trust-massing-001/northern_trust.blend', {west_id})]
bpy.ops.wm.open_mainfile(filepath=str(source))
removed = []
added = []
replacement_ids = {west_id} | morgan_ids
unchanged = {o.name: o.get('building_id') for o in bpy.data.objects
             if o.type == 'MESH' and o.get('building_id') not in replacement_ids}
for o in list(bpy.data.objects):
    if o.get('building_id') in replacement_ids:
        removed.append({'name': o.name, 'building_id': o.get('building_id')})
        bpy.data.objects.remove(o, do_unlink=True)
assert {r['building_id'] for r in removed} == replacement_ids
for label, asset, ids in assets:
    with bpy.data.libraries.load(str(asset), link=False) as (data, dest):
        dest.objects = list(data.objects)
    col = bpy.data.collections.new(label+' architectural study')
    bpy.context.scene.collection.children.link(col)
    for o in dest.objects:
        if o is None:
            continue
        if o.type != 'MESH' or o.get('building_id') not in ids:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        assert o.get('building_id') in ids, (o.name, o.get('building_id'))
        col.objects.link(o)
        o['research_object_id'] = 'northern_trust::'+label+'::'+o.name
        o['coverage'] = 'Composite DSM vintage unresolved; two supported plateau envelopes, estimated body roof; facades unfinished'
        added.append(o.name)
assert all(n in bpy.data.objects and bpy.data.objects[n].get('building_id') == bid
           for n, bid in unchanged.items())
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
s.render.filepath = str(O/'overview.png')
bpy.ops.render.render(write_still=True)
s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.68,.75,.83,1)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
cam = s.camera
cam.location = (160,-540,210)
cam.rotation_euler = (Vector((50,-322,40))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 190
s.render.resolution_x = 1600
s.render.resolution_y = 1000
s.render.filepath = str(O/'northern-trust-context.png')
bpy.ops.render.render(write_still=True)
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
    scope='Northern Trust partial roof massing; central and south plateaus supported, outer north and equipment uncertain; facade incomplete.')
(O/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
