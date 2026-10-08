"""Combine separately reviewed estimated exterior details for a timed visual sample."""
from pathlib import Path
from datetime import datetime, timezone
import bpy
import hashlib
import json
import time
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / 'input/canary_wharf_20261007/exports'
BASE = EXPORTS / 'one_canada_whole_sample001/canada.blend'
ROOF = EXPORTS / 'one_canada_roof_completion001/roof.blend'
OUT = EXPORTS / 'one_canada_visual_sample001'
OUT.mkdir(exist_ok=True)
started = datetime.now(timezone.utc).isoformat()
timer = time.monotonic()
(OUT / 'assembly-start.json').write_text(json.dumps({'start_utc': started}) + '\n')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {str(p.relative_to(ROOT)): sha(p) for p in (BASE, ROOF)}
contract = json.loads((ROOF.parent / 'contract.json').read_text())
names = [x['name'] for x in contract['added_objects']]
roof_name = 'Canada_317cf479fcef_steel'
bpy.ops.wm.open_mainfile(filepath=str(BASE))

def fingerprint(o):
    return hashlib.sha256(repr((
        [tuple(v.co) for v in o.data.vertices],
        [(tuple(p.vertices), p.material_index) for p in o.data.polygons],
        [m.name if m else None for m in o.data.materials],
        [tuple(row) for row in o.matrix_world], dict(o.items()),
        [[tuple(d.uv) for d in layer.data] for layer in o.data.uv_layers],
    )).encode()).hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects
          if o.type == 'MESH' and o.name != roof_name}
assert not set(names).intersection(bpy.data.objects.keys())
with bpy.data.libraries.load(str(ROOF), link=False) as (available, loaded):
    assert set(names).issubset(available.objects)
    loaded.objects = names.copy()
for obj in loaded.objects:
    bpy.context.collection.objects.link(obj)
roof = bpy.data.objects[roof_name]
material_index = next(i for i, m in enumerate(roof.data.materials)
                      if m and m.name == 'Estimated west gray steel')
for index in (122, 123, 124):
    assert len(roof.data.polygons[index].vertices) == 3
    roof.data.polygons[index].material_index = material_index
roof['additional_roof_faces_basis'] = 'Estimated visual completion; no source image verification'
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in before.items())
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
snapshot = {}
for obj in meshes:
    obj.data.calc_loop_triangles()
    vv = [obj.matrix_world @ v.co for v in obj.data.vertices]
    snapshot[obj.name] = {
        'triangles': len(obj.data.loop_triangles),
        'bounds': [[min(v[i] for v in vv) for i in range(3)],
                   [max(v[i] for v in vv) for i in range(3)]],
        'building_id': obj.get('building_id'),
        'research_object_id': obj.get('research_object_id'),
        'used_materials': sorted({obj.data.materials[p.material_index].name
                                 for p in obj.data.polygons if obj.data.materials}),
    }

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.render.resolution_x = 1100
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
if scene.world is None:
    scene.world = bpy.data.worlds.new('Inspection world')
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (.68, .75, .83, 1)
bg.inputs['Strength'].default_value = .8
for obj in list(bpy.data.objects):
    if obj.type in {'LIGHT', 'CAMERA'}:
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.object.light_add(type='SUN')
bpy.context.object.data.energy = 2
bpy.context.object.rotation_euler = (.4, -.3, .6)
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.type = 'ORTHO'
views = [
    ('whole-front', (-47, -41, 117), (-250, -160, 75), 285),
    ('whole-rear', (-47, -41, 117), (250, 160, 75), 285),
    ('roof', (-47, -41, 218), (55, -80, 65), 72),
]
render_times = []
for name, target, offset, scale in views:
    t = time.monotonic()
    target = Vector(target)
    cam.location = target + Vector(offset)
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = scale
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    render_times.append({'view': name, 'seconds': time.monotonic() - t})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'canada.blend'), compress=False)
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / 'canada.glb'), export_format='GLB',
                         use_selection=True, export_extras=True,
                         export_draco_mesh_compression_enable=False)
(OUT / 'native_snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
(OUT / 'assembly.json').write_text(json.dumps({
    'source_blends': inputs, 'preserved_base_meshes': len(before),
    'added_estimated_roof_objects': names,
    'changed_existing_mesh': roof_name,
    'change_scope': 'Three roof triangle materials and explanatory metadata only',
    'whole_building_photo_verified': False,
    'scope': 'Usable visual sample with estimated base, entrance and unseen roof faces',
    'native_sha256': sha(OUT / 'canada.blend'),
    'glb_sha256': sha(OUT / 'canada.glb'),
    'start_utc': started, 'end_utc': datetime.now(timezone.utc).isoformat(),
    'elapsed_seconds': time.monotonic() - timer, 'renders': render_times,
}, indent=2) + '\n')
print('VISUAL_SAMPLE_ASSEMBLED', OUT)
