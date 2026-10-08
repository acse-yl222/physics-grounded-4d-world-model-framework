"""Assemble independent Owner1f92 regional comparison over the retained Morgan south scene."""
from pathlib import Path
import bpy
import json
import hashlib
import os
from mathutils import Vector

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
O = R / 'exports/appearance-morgan-visibility-correction-001'
O.mkdir(exist_ok=False)
source = Path(__file__).resolve().parent / 'runs/canary_wharf_appearance_owner1f92_001/region.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
removed=[]
def plain(v):
    if hasattr(v,'to_dict'): return {k:plain(x) for k,x in v.to_dict().items()}
    if hasattr(v,'to_list'): return v.to_list()
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    try:return list(v)
    except:return str(v)
def material(m):
    if m is None:return None
    d={'name':m.name,'properties':{k:plain(v) for k,v in m.items()},'diffuse':list(m.diffuse_color),'metallic':m.metallic,'roughness':m.roughness,'use_nodes':m.use_nodes}
    if m.node_tree:
        d['nodes']=[{'name':n.name,'type':n.bl_idname,'inputs':{i.name:plain(i.default_value) for i in n.inputs if hasattr(i,'default_value')},'image':getattr(getattr(n,'image',None),'filepath',None),'operation':getattr(n,'operation',None),'blend_type':getattr(n,'blend_type',None)} for n in m.node_tree.nodes]
        d['links']=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]
    return d
def fingerprint(o):
    d={'matrix':[list(r) for r in o.matrix_world],'vertices':[list(v.co) for v in o.data.vertices],'polygons':[(list(p.vertices),p.material_index,p.use_smooth) for p in o.data.polygons],'properties':{k:plain(v) for k,v in o.items()},'mesh_properties':{k:plain(v) for k,v in o.data.items()},'materials':[material(m) for m in o.data.materials],'uv_layers':[[list(x.uv) for x in l.data] for l in o.data.uv_layers]}
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
source_hash_before=hashlib.sha256(source.read_bytes()).hexdigest()
prior_geometry={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('morgan_south_')}
unchanged = {o.name: o.get('building_id') for o in bpy.data.objects
             if o.type == 'MESH' and not o.name.startswith('morgan_south_')}
target_pts=[]
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name.startswith('morgan_south_'):
        o.data.calc_loop_triangles()
        removed.append({'name':o.name,'building_id':o.get('building_id'),'triangles':len(o.data.loop_triangles)})
        target_pts.extend(o.matrix_world@v.co for v in o.data.vertices)
        bpy.data.objects.remove(o,do_unlink=True)
assert len(removed)==5,removed
assert sum(r['triangles'] for r in removed)==492,removed
assert all(n in bpy.data.objects and bpy.data.objects[n].get('building_id') == bid
           for n, bid in unchanged.items())
assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior_geometry.items())
s = bpy.context.scene
s.cycles.samples = 24
bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'), compress=False)
bpy.ops.object.select_all(action='DESELECT')
expected = {}
metadata = {}
per_object_bounds={}
used_materials={}
points = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    o.select_set(True)
    o.data.calc_loop_triangles()
    key = o.get('research_object_id', o.name)
    assert key not in expected
    expected[key] = len(o.data.loop_triangles)
    metadata[key] = (o.get('building_id'), list(o.get('source_owner_ids', [])),o.get('aggregate_alias_id'))
    vv=[o.matrix_world @ v.co for v in o.data.vertices]
    per_object_bounds[key]=[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]]
    used_materials[key]=sorted({o.data.materials[p.material_index].name for p in o.data.polygons})
    points.extend(vv)
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
target_bb = bounds(target_pts)
target = Vector([(target_bb[0][i]+target_bb[1][i])/2 for i in range(3)])
cam.location = target + Vector((-95,-125,65))
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 120
s.render.resolution_x = 1600
s.render.resolution_y = 1000
f=cam.rotation_euler.to_quaternion() @ Vector((0,0,-1))
depths=[(o.matrix_world@Vector(v)-cam.location).dot(f) for o in s.objects if o.type=='MESH' for v in o.bound_box]
shift=max(0,cam.data.clip_start+10-min(depths))
cam.location-=f*shift
cam.data.clip_end=max(cam.data.clip_end,max(depths)+shift+100)
s.render.filepath = str(O/'morgan-corrected-context.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'))
assert len([o for o in bpy.data.objects if o.type == 'MESH']) == len(expected)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior_geometry.items())
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash_before
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'))
actual = {}
max_object_bounds_error=0.0
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    key = o.get('research_object_id', o.name)
    actual[key] = len(o.data.polygons)
    assert metadata[key] == (o.get('building_id'), list(o.get('source_owner_ids', [])),o.get('aggregate_alias_id'))
    assert o.data.materials
    vv=[o.matrix_world@v.co for v in o.data.vertices]
    obb=bounds(vv)
    error=max(abs(a-b) for aa,bb in zip(per_object_bounds[key],obb) for a,b in zip(aa,bb))
    assert error<.001,(key,error)
    max_object_bounds_error=max(max_object_bounds_error,error)
    actual_materials=sorted({o.data.materials[p.material_index].name for p in o.data.polygons})
    assert actual_materials==used_materials[key],(key,actual_materials,used_materials[key])
assert actual == expected
actual_bb = bounds([o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH'
                    for v in o.data.vertices])
assert max(abs(a-b) for x,y in zip(bb,actual_bb) for a,b in zip(x,y)) < .001
report = dict(native_reopened=True, independent_glb_verified=True, unrelated_geometry_fingerprints_preserved=True, unrelated_properties_materials_uv_fingerprints_preserved=True, source_file_unchanged=True,
    source_owner_aliases_verified=True, per_object_used_material_names_verified=True,
    removed_meshes=removed, removed_mesh_count=len(removed), removed_triangles=sum(r['triangles'] for r in removed), unchanged_meshes=len(unchanged), objects=len(expected),
    bounds_enu_m=bb, per_object_bounds_max_error_m=max_object_bounds_error,
    source_blends={os.path.relpath(source,R):hashlib.sha256(source.read_bytes()).hexdigest()},
    scope='Remove only five unsupported Morgan south edge13 facade meshes,492triangles. Visibility evidence shows20/24sampled rays occluded by own body. All building bodies/roofs and other retained refinements preserved. Historical versions untouched. Comparison only, no retention.')
report['artifact_sha256']={n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in ['region.blend','region.glb']}
(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
