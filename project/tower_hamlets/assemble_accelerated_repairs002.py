"""Assemble explicit per-building component contracts, preserving unrelated meshes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import sys
import time
import bpy
from mathutils import Vector

S = Path(__file__).resolve().parent
ROOT = S.parent.parent
started = time.time()

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def plain(x):
    if hasattr(x, 'to_dict'): return plain(x.to_dict())
    if hasattr(x, 'to_list'): return plain(x.to_list())
    if isinstance(x, dict): return {k: plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [plain(v) for v in x]
    if isinstance(x, (str, int, float, bool)) or x is None: return x
    try: return list(x)
    except TypeError: return str(x)

def material(m):
    return {'name': m.name, 'diffuse': list(m.diffuse_color),
            'roughness': m.roughness, 'metallic': m.metallic,
            'props': plain(dict(m.items())), 'use_nodes': m.use_nodes,
            'nodes': [{'name': n.name, 'type': n.bl_idname,
                       'inputs': {i.identifier: plain(i.default_value) for i in n.inputs
                                  if hasattr(i, 'default_value')}}
                      for n in m.node_tree.nodes] if m.use_nodes else [],
            'links': [(l.from_node.name, l.from_socket.identifier,
                       l.to_node.name, l.to_socket.identifier)
                      for l in m.node_tree.links] if m.use_nodes else []}

def fingerprint(o):
    d = {'vertices': [list(v.co) for v in o.data.vertices],
         'faces': [list(p.vertices) for p in o.data.polygons],
         'material_indices': [p.material_index for p in o.data.polygons],
         'smooth': [p.use_smooth for p in o.data.polygons],
         'matrix': [list(r) for r in o.matrix_world],
         'props': plain(dict(o.items())), 'meshprops': plain(dict(o.data.items())),
         'materials': [material(m) for m in o.data.materials],
         'uv': [[list(v.uv) for v in layer.data] for layer in o.data.uv_layers]}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

def metadata(o):
    o.data.calc_loop_triangles()
    vv = [o.matrix_world @ v.co for v in o.data.vertices]
    return {'triangles': len(o.data.loop_triangles), 'owner': o.get('building_id'),
            'aliases': plain(o.get('source_owner_ids', [])),
            'aggregate_alias_id': plain(o.get('aggregate_alias_id')),
            'bounds': [[min(v[i] for v in vv) for i in range(3)],
                       [max(v[i] for v in vv) for i in range(3)]],
            'used_materials': sorted({o.data.materials[p.material_index].name
                                      for p in o.data.polygons})}

def inventory():
    result = {}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        key = o.get('research_object_id', o.name)
        assert key not in result, key
        result[key] = metadata(o)
    return result

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main(config_path):
    config = json.loads(config_path.read_text())
    source = ROOT / config['source']
    assert sha(source) == config['source_sha256']
    out = ROOT / config['output']
    out.mkdir(exist_ok=False)
    write(out / 'assembly-config.json', config)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    replacement = [n for c in config['components'] for n in c['replace_names']]
    additions = [n for c in config['components'] for n in c['add_names']]
    assert len(set(replacement + additions)) == len(replacement + additions)
    assert all(n in bpy.data.objects for n in replacement)
    assert all(n not in bpy.data.objects for n in additions)
    identity_fields = ('building_id', 'research_object_id', 'aggregate_alias_id', 'source_owner_ids')
    replaced_ids = {n: {k: plain(bpy.data.objects[n].get(k)) for k in identity_fields}
                    for n in replacement}
    prior = {o.name: fingerprint(o) for o in bpy.data.objects
             if o.type == 'MESH' and o.name not in replacement}
    cache = {}
    for m in bpy.data.materials:
        d = material(m); d.pop('name')
        cache[json.dumps(d, sort_keys=True)] = m
    for c in config['components']:
        asset = ROOT / c['native']
        assert sha(asset) == c['sha256']
        for name in c['replace_names']:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        names = c['replace_names'] + c['add_names']
        with bpy.data.libraries.load(str(asset), link=False) as (a, b):
            assert all(n in a.objects for n in names)
            b.objects = names.copy()
        col = bpy.data.collections.new(c['label'])
        bpy.context.scene.collection.children.link(col)
        for o in b.objects:
            assert o is not None and o.type == 'MESH'
            col.objects.link(o)
            assert o.get('building_id') in c['owners'], o.name
            if o.name in replaced_ids:
                assert {k: plain(o.get(k)) for k in identity_fields} == replaced_ids[o.name]
            for i, m in enumerate(o.data.materials):
                d = material(m); d.pop('name'); key = json.dumps(d, sort_keys=True)
                if key in cache: o.data.materials[i] = cache[key]
    assert all(fingerprint(bpy.data.objects[n]) == h for n, h in prior.items())
    write(out / 'unchanged-fingerprints.json', prior)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'region.blend'), compress=False)
    expected = inventory()
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.type == 'MESH': o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out / 'region.glb'), export_format='GLB',
                             use_selection=True, export_extras=True,
                             export_draco_mesh_compression_enable=False)
    scene = bpy.context.scene
    scene.cycles.samples = 16
    scene.render.filepath = str(out / 'overview.png')
    bpy.ops.render.render(write_still=True)
    for view in config['views']:
        cam = scene.camera; target = Vector(view['target'])
        cam.location = target + Vector(view['offset'])
        cam.rotation_euler = (target-cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = view.get('camera_type', 'ORTHO')
        assert cam.data.type in {'ORTHO', 'PERSP'}
        if cam.data.type == 'PERSP':
            cam.data.angle = math.radians(view['fov_degrees'])
        else:
            cam.data.ortho_scale = view['scale']
        scene.render.resolution_x = 1400; scene.render.resolution_y = 1000
        if view.get('local_camera'):
            cam.data.clip_start = .05
            cam.data.clip_end = 3000
        else:
            forward = cam.rotation_euler.to_quaternion() @ Vector((0, 0, -1))
            depths = [(o.matrix_world @ Vector(v)-cam.location).dot(forward)
                      for o in scene.objects if o.type == 'MESH' for v in o.bound_box]
            shift = max(0, cam.data.clip_start + 10 - min(depths))
            cam.location -= forward * shift
            cam.data.clip_end = max(depths) + shift + 100
        scene.render.filepath = str(out / (view['name'] + '.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.open_mainfile(filepath=str(out / 'region.blend'))
    assert all(fingerprint(bpy.data.objects[n]) == h for n, h in prior.items())
    assert inventory() == expected
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out / 'region.glb'))
    actual = inventory(); assert actual.keys() == expected.keys()
    max_error = 0
    for k, value in expected.items():
        for field in ('triangles', 'owner', 'aliases', 'aggregate_alias_id', 'used_materials'):
            assert actual[k][field] == value[field], (k, field)
        max_error = max(max_error, max(abs(a-b) for x,y in zip(value['bounds'], actual[k]['bounds']) for a,b in zip(x,y)))
    assert max_error < .001
    assert sha(source) == config['source_sha256']
    for c in config['components']: assert sha(ROOT / c['native']) == c['sha256']
    write(out / 'per-object-verification.json', expected)
    write(out / 'verification.json', {
        'native_reopened': True, 'independent_glb_verified': True,
        'source_unchanged': True, 'unrelated_exact_geometry_properties_materials_uv': len(prior),
        'added': additions, 'replaced': replacement, 'mesh_count': len(expected),
        'triangles': sum(v['triangles'] for v in expected.values()),
        'max_perobject_bounds_error_m': max_error,
        'bounds_enu_m': [[min(v['bounds'][0][i] for v in expected.values()) for i in range(3)],
                         [max(v['bounds'][1][i] for v in expected.values()) for i in range(3)]],
        'native_sha256': sha(out / 'region.blend'), 'glb_sha256': sha(out / 'region.glb'),
        'elapsed_seconds': time.time()-started,
        'finished_utc': datetime.now(timezone.utc).isoformat(), 'visual_reviewed': False})

if __name__ == '__main__':
    main(Path(sys.argv[sys.argv.index('--')+1]).resolve())
