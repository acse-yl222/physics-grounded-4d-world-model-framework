from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/appearance-morgan-south-001';O.mkdir(exist_ok=False);src=P/'runs/canary_wharf_appearance_bank40_002/region.blend';asset=R/'exports/morgan_south-facade-001/morgan_south.blend';sourcehash=hashlib.sha256(src.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src))
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
prior={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
with bpy.data.libraries.load(str(asset),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('morgan_south_')]
assert len(b.objects)==5;col=bpy.data.collections.new('Morgan south bounded new details');bpy.context.scene.collection.children.link(col);added=[]
for o in b.objects:col.objects.link(o);o['research_object_id']='morgan-south::'+o.name;o['coverage']='Only b317 edge13 two photo-informed bays; positions/depth estimated';added.append(o.name)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior.items());(O/'preexisting-fingerprints.json').write_text(json.dumps(prior,indent=2));s=bpy.context.scene;s.cycles.samples=16;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);expected={};bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':
  o.select_set(True);o.data.calc_loop_triangles();key=o.get('research_object_id',o.name);assert key not in expected;expected[key]={'triangles':len(o.data.loop_triangles),'owner':o.get('building_id')}
bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
cam=s.camera
for name,target,offset,scale in [('front-context',(-318.28645,-73.05868,24),(-35,-95,35),60),('detail-context',(-318.28645,-73.05868,23.5),(-5,-32,4),17)]:
 c=Vector(target);cam.location=c+Vector(offset);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;s.render.resolution_x=1300;s.render.resolution_y=1000
 fw=cam.rotation_euler.to_quaternion()@Vector((0,0,-1));dep=[(o.matrix_world@Vector(v)-cam.location).dot(fw) for o in s.objects if o.type=='MESH' for v in o.bound_box];shift=max(0,cam.data.clip_start+10-min(dep));cam.location-=fw*shift;cam.data.clip_end=max(cam.data.clip_end,max(dep)+shift+100);s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert all(fingerprint(bpy.data.objects[n])==h for n,h in prior.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));ms=[o for o in bpy.data.objects if o.type=='MESH'];actual={o.get('research_object_id',o.name):{'triangles':len(o.data.polygons),'owner':o.get('building_id')} for o in ms};assert actual==expected;assert hashlib.sha256(src.read_bytes()).hexdigest()==sourcehash
(O/'checks.json').write_text(json.dumps({'source':str(src),'source_sha256':sourcehash,'source_unchanged':True,'added_only':added,'removed':[],'preexisting_meshes_exact_geometry_properties_materials':len(prior),'native_reopened':True,'glb_reimported':True,'mesh_count':len(ms),'triangles':sum(v['triangles'] for v in actual.values()),'visual_reviewed':False},indent=2))
