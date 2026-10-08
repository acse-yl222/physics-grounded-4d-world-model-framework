from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/cabot-west-roof-study-001';d=json.loads((O/'boundary-study.json').read_text());src=R/'exports/cabot-place-photo-study-001/cabot_place.blend';sourcehash=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src))
def sig(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'p':[list(p.vertices) for p in o.data.polygons],'m':[m.name for m in o.data.materials]},sort_keys=True).encode()).hexdigest()
base={o.name:sig(o) for o in bpy.data.objects if o.type=='MESH'};ring=d['candidate_outer_xy'];N=len(ring);z0=d['baseline_odn']-4.28000021;z1=d['high_seed_odn_median']-4.28000021;vs=[(*p,z) for z in [z0,z1] for p in ring];fs=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)];me=bpy.data.meshes.new('Cabot inset curved roof diagnostic');me.from_pydata(vs,[],fs);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(f.calc_area()>1e-10 for f in bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new('Cabot inset curved roof estimated candidate',me);bpy.context.collection.objects.link(ob);ob['building_id']=d['owner_id'];ob['source_owner_ids']=[d['owner_id']];ob['scope']='Raster-supported high patch; estimated ellipse boundary, independent candidate only';mat=bpy.data.materials.new('Cabot high patch stone estimate');mat.diffuse_color=(.58,.53,.42,1);me.materials.append(mat)
assert all(sig(bpy.data.objects[n])==v for n,v in base.items());bpy.context.view_layer.update();trees=[]
for o in bpy.data.objects:
 if o.type=='MESH':trees.append((o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])))
# Actual frozen mesh DSM projection across all original west-strip cells.
res=[]
for cell in d['all_strip_cells']:
 hits=[]
 for name,tree in trees:
  loc,normal,idx,dist=tree.ray_cast(Vector((cell['x'],cell['y'],100)),Vector((0,0,-1)),200)
  if loc is not None:hits.append((loc.z,name))
 top=max(hits);res.append({'xy':[cell['x'],cell['y']],'observed_odn':cell['dsm_odn'],'dtm_odn':cell['dtm_odn'],'predicted_odn':top[0]+4.28000021,'object':top[1],'error_m':top[0]+4.28000021-cell['dsm_odn']})
# Real local rays from existing stored camera to exterior curved wall, keep limitations.
camdata=json.loads((R/'references/cabot_place_anna_camera.json').read_text());a=camdata['parameters_xy_yaw_pitch_logf'];C=Vector((a[0],a[1],2));rays=[]
for p in ob.data.polygons:
 if len(p.vertices)!=4:continue
 target=ob.matrix_world@p.center;delta=target-C
 if p.normal.dot(-delta)<=0:continue
 hits=[]
 for name,tree in trees:
  loc,normal,idx,dist=tree.ray_cast(C,delta.normalized(),delta.length-.005)
  if loc is not None:hits.append({'object':name,'before_target_m':delta.length-dist})
 rays.append({'target':list(target),'blockers':hits})
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;cam=s.camera
for label,target,offset,scale in [('overview',(-206,-12,14),(-80,-70,55),90),('front',(-233,-8,15),(-75,0,18),48),('roof',(-233,-8,20),(-25,-10,75),35)]:
 target=Vector(target);cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;s.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'cabot-west.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'cabot-west.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
expected={}
for o in bpy.data.objects:
 if o.type=='MESH':o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
bpy.ops.wm.open_mainfile(filepath=str(O/'cabot-west.blend'));assert all(sig(bpy.data.objects[n])==v for n,v in base.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'cabot-west.glb'));actual={o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
(O/'checks.json').write_text(json.dumps({'source_sha256':sourcehash,'source_unchanged':sourcehash==hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'all_original_meshes_unchanged':list(base),'mesh_triangles':actual,'native_reopened':True,'glb_independently_imported':True,'candidate_manifold':True,'dsm_projection':res,'local_camera_wall_rays':rays,'limitations':['Local wall rays only; neighbor geometry absent.','Original camera remains uncalibrated in foreground.','Candidate elevation from existing raster; boundary ellipse and vertical wall are estimated, not measured.']},indent=2));print('DONE',expected)
