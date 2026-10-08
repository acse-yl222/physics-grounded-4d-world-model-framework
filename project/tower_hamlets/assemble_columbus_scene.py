"""Assemble the One Bank Street western facade study while preserving other regional assets."""
from pathlib import Path
import bpy
import json
import hashlib
from mathutils import Vector

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
O = R / 'exports/appearance-columbus-001'
O.mkdir(exist_ok=False)
source = R / 'exports/appearance-bank20-001/region.blend'
west_id = 'overture-building-3a202b7c-1361-4edd-8889-67b0f5266360'
morgan_ids = {'overture-part-280011e9-a03d-3145-a0d4-b3536cec5ee3', 'overture-part-97dd8c74-072f-3702-b265-ea4b6279a593', 'overture-part-6347d66a-97d8-3d34-995d-22eaecb5cce6', 'overture-part-13471285-435f-340b-abf8-9ae68f242490', 'overture-part-5f2f16d8-dd22-3b84-9708-15d59543dc94', 'overture-building-999ceaf7-e4c6-4c09-bee4-803886ceaaec', 'overture-part-793e35a4-6a14-3b53-a6a1-5ee0e8bc06ae'}
assets = [('columbus20', R/'exports/credit3a-roof-study-001/credit3a.blend', {west_id}), ('columbus17',R/'exports/credit999-roof-study-002/credit999.blend', {'overture-building-999ceaf7-e4c6-4c09-bee4-803886ceaaec'}), ('credit_interface',R/'exports/credit-photo-study-003/credit.blend', {'overture-part-280011e9-a03d-3145-a0d4-b3536cec5ee3', 'overture-part-97dd8c74-072f-3702-b265-ea4b6279a593', 'overture-part-6347d66a-97d8-3d34-995d-22eaecb5cce6', 'overture-part-13471285-435f-340b-abf8-9ae68f242490', 'overture-part-5f2f16d8-dd22-3b84-9708-15d59543dc94', 'overture-part-793e35a4-6a14-3b53-a6a1-5ee0e8bc06ae'})]
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
        o['research_object_id'] = 'columbus::'+label+'::'+o.name
        o['coverage'] = 'Columbus roof massing or Credit shared-wall interface refinement; source uncertainties retained'
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
cam.location = (-660,260,240)
cam.rotation_euler = (Vector((-365,90,40))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 265
s.render.resolution_x = 1600
s.render.resolution_y = 1000
s.render.filepath = str(O/'columbus-context.png')
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
    scope='17 and 20 Columbus roof massing and Credit shared-wall correction; roof edges and southern connector uncertain; region incomplete.')
(O/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
