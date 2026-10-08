from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/appearance-quay1-recess-001';O.mkdir(exist_ok=False);src=P/'runs/canary_wharf_appearance_ownerd42_001/region.blend';asset=R/'exports/facade-detail-pilot-001/quay1-detail.blend';sourcehash=hashlib.sha256(src.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src))
def plain(v):
 if hasattr(v,'to_dict'):return plain(v.to_dict())
 if hasattr(v,'to_list'):return plain(v.to_list())
 if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [plain(x) for x in v]
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 try:return list(v)
 except:return str(v)
def mat(m):
 return {'name':m.name,'diffuse':list(m.diffuse_color),'roughness':m.roughness,'metallic':m.metallic,'use_nodes':m.use_nodes,'props':plain(dict(m.items())),'nodes':[{'name':n.name,'type':n.bl_idname,'inputs':{i.identifier:plain(i.default_value) for i in n.inputs if hasattr(i,'default_value')}} for n in m.node_tree.nodes] if m.use_nodes else [],'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in m.node_tree.links] if m.use_nodes else []}
def fingerprint(o):
 d={'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'material_indices':[p.material_index for p in o.data.polygons],'smooth':[p.use_smooth for p in o.data.polygons],'matrix':[list(r) for r in o.matrix_world],'props':plain(dict(o.items())),'meshprops':plain(dict(o.data.items())),'materials':[mat(m) for m in o.data.materials]};return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
ID='overture-building-a6a8ac29-204a-43a7-b4d0-af0fa65a47dc'
replace=[ID,'Quay1 visible upper glass']
newnames=replace+['Quay1 visible upper horizontal rear returns','Quay1 visible upper vertical rear returns']
prior={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH' and o.name not in replace}
material_cache={}
for m in bpy.data.materials:
 q=mat(m);q.pop('name');material_cache[json.dumps(q,sort_keys=True)]=m
for name in replace:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
with bpy.data.libraries.load(str(asset),link=False) as (a,b):b.objects=newnames.copy()
col=bpy.data.collections.new('Quay1 shallow recess pilot');bpy.context.scene.collection.children.link(col)
for o in b.objects:
 col.objects.link(o)
 for i,m in enumerate(o.data.materials):
  q=mat(m);q.pop('name');key=json.dumps(q,sort_keys=True)
  if key in material_cache:o.data.materials[i]=material_cache[key]
assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior.items())
(O/'preexisting-fingerprints.json').write_text(json.dumps(prior,indent=2));s=bpy.context.scene;s.cycles.samples=16;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);expected={};bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':
  o.select_set(True);o.data.calc_loop_triangles();key=o.get('research_object_id',o.name);assert key not in expected;expected[key]={'triangles':len(o.data.loop_triangles),'owner':o.get('building_id'),'aliases':plain(o.get('source_owner_ids',[])),'materials':sorted(set(o.data.materials[p.material_index].name for p in o.data.polygons))}
bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
cam=s.camera
for name,target,offset,scale in [('detail-context',(-178,199,85),(-30,-30,8),23),('front-context',(-166,203,75),(-100,-70,45),100)]:
 c=Vector(target);cam.location=c+Vector(offset);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;s.render.resolution_x=1300;s.render.resolution_y=1000
 fw=cam.rotation_euler.to_quaternion()@Vector((0,0,-1));dep=[(o.matrix_world@Vector(v)-cam.location).dot(fw) for o in s.objects if o.type=='MESH' for v in o.bound_box];shift=max(0,cam.data.clip_start+10-min(dep));cam.location-=fw*shift;cam.data.clip_end=max(cam.data.clip_end,max(dep)+shift+100);s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));ms=[o for o in bpy.data.objects if o.type=='MESH'];actual={o.get('research_object_id',o.name):{'triangles':len(o.data.polygons),'owner':o.get('building_id'),'aliases':plain(o.get('source_owner_ids',[])),'materials':sorted(set(o.data.materials[p.material_index].name for p in o.data.polygons))} for o in ms};assert actual==expected;assert hashlib.sha256(src.read_bytes()).hexdigest()==sourcehash
(O/'checks.json').write_text(json.dumps({'source':str(src),'source_sha256':sourcehash,'asset_sha256':hashlib.file_digest(asset.open('rb'),'sha256').hexdigest(),'source_unchanged':True,'added':newnames[2:],'replaced':replace,'unrelated_meshes_exact_geometry_properties_materials':len(prior),'native_reopened':True,'glb_reimported':True,'mesh_count':len(ms),'triangles':sum(v['triangles'] for v in actual.values()),'visual_reviewed':False},indent=2))
