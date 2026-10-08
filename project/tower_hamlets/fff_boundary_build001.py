from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-roof-study-001';O.mkdir(exist_ok=True);d=json.load(open(R/'references/fff_boundary-authoring001.json'));bpy.ops.wm.read_factory_settings(use_empty=True);cols={};obs=[];checks=[]
for name in ['fff_boundary_original_owner','fff_boundary_outside_AOI_context_only']:
 col=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(col);cols[name]=col
m=bpy.data.materials.new('fff_boundary unknown roof body neutral');m.diffuse_color=(.32,.46,.49,1)
for q in d['objects']:
 me=bpy.data.meshes.new(q['name']);me.from_pydata(q['vertices'],[],q['faces']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(f.calc_area()>1e-9 for f in bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(q['name'],me);cols['fff_boundary_outside_AOI_context_only' if q['context_only'] else 'fff_boundary_original_owner'].objects.link(ob);me.materials.append(m);ob['building_id']=q['building_id'];ob['source_owner_ids']=[q['building_id']];ob['context_only']=q['context_only'];ob['inventory_scope']='outside_AOI_not_in_original439' if q['context_only'] else 'original_inventory_replacement';ob['shared_owner_cut']='Internal partition closure; not exterior facade';obs.append(ob);me.calc_loop_triangles();checks.append({'name':ob.name,'triangles':len(me.loop_triangles),'context_only':q['context_only']})
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('QA Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.68,.74,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;ld=bpy.data.lights.new('QA Sun','SUN');ld.energy=2;lo=bpy.data.objects.new('QA Sun',ld);s.collection.objects.link(lo);lo.rotation_euler=(.3,-.6,-.5);cam=bpy.data.objects.new('QA Camera',bpy.data.cameras.new('QA Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=23;C=Vector((-503,362,2.7));cam.location=C+Vector((-24,-30,22));cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler();bpy.ops.wm.save_as_mainfile(filepath=str(O/'fff_boundary-pair-context.blend'),compress=False)
def export(name,items):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in items:ob.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(O/name),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
export('fff_boundary-pair-context.glb',obs);export('fff_boundary-target.glb',[o for o in obs if not o['context_only']])
for name,off in [('overview',(-24,-30,22)),('roof',(0,0,50)),('rear',(24,30,19))]:
 cam.location=C+Vector(off);cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/('fff_boundary-'+name+'.png'));bpy.ops.render.render(write_still=True)
for o in list(obs):
 if o['context_only']:bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'fff_boundary-target.blend'),compress=False)
verification={}
for name,subset in [('pair-context',checks),('target',[q for q in checks if not q['context_only']])]:
 bpy.ops.wm.open_mainfile(filepath=str(O/('fff_boundary-'+name+'.blend')));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(subset);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/('fff_boundary-'+name+'.glb')));ms=[o for o in bpy.data.objects if o.type=='MESH'];assert {o.name:len(o.data.polygons) for o in ms}=={q['name']:q['triangles'] for q in subset};vv=[o.matrix_world@v.co for o in ms for v in o.data.vertices];verification[name]={'mesh_count':len(ms),'triangles':sum(len(o.data.polygons) for o in ms),'owner_ids':sorted(set(o['building_id'] for o in ms)),'bounds_enu':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'native_reopened':True,'glb_reimported':True}
(O/'fff_boundary-checks.json').write_text(json.dumps({'assets':verification,'closed_per_sector':True,'zero_area_faces':0,'internal_caps':'Coincident owner/sector closures, not global booleanunion or external party facade.','visual_reviewed':False},indent=2));print(verification)
