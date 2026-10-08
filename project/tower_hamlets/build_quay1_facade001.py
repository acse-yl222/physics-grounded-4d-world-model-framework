from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/quay1-facade-study-001';O.mkdir(exist_ok=True);ID='overture-building-a6a8ac29-204a-43a7-b4d0-af0fa65a47dc';src=P/'runs/canary_wharf_appearance_owner836_001/region.blend';f=next(q for q in json.loads((R/'geometry.json').read_text())['buildings'] if q['id']==ID);ring=[Vector(v) for v in f['geometry'][0]['outer']];selected=list(range(9,16));bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=[ID]
base=b.objects[0];bpy.context.collection.objects.link(base)
def signature(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'p':[list(p.vertices) for p in o.data.polygons],'mi':[p.material_index for p in o.data.polygons],'materials':[m.name for m in o.data.materials],'matrix':[list(row) for row in o.matrix_world]},sort_keys=True).encode()).hexdigest()
original=signature(base);groups={k:[[],[]] for k in ['glass','horizontal','vertical']};solidchecks=[]
def prism(kind,a,b,z0,z1,d0,d1):
 t=(b-a).normalized();n=Vector((t.y,-t.x));# ring is CCW; south arc exterior on right
 vs=[(q.x+n.x*d,q.y+n.y*d,z) for z in (z0,z1) for q,d in [(a,d0),(b,d0),(b,d1),(a,d1)]];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];v,faces=groups[kind];off=len(v);v.extend(vs);faces.extend([tuple(off+i for i in face) for face in fs]);solidchecks.append({'kind':kind,'edge':edge,'z':[z0,z1],'depth':[d0,d1]})
for edge in selected:
 a=ring[edge];b=ring[(edge+1)%len(ring)];t=(b-a).normalized();a=a+t*.04;b=b-t*.04;length=(b-a).length
 # Recessed relative to metal frames. Opaque reflective material avoids invented transmission/interior.
 prism('glass',a,b,52,109.45,.025,.065)
 levels=[52+i*3.15 for i in range(17)] # last102.4
 for zz in levels:prism('horizontal',a,b,zz,zz+.12,.06,.20)
 prism('horizontal',a,b,109.25,109.45,.06,.23)
 bays=max(1,round(length/1.8))
 for i in range(bays+1):
  if i==bays and edge!=selected[-1]:continue # one jamb per shared mapped vertex
  pos=a+(b-a)*(i/bays);half=.025;aa=pos-t*half;bb=pos+t*half
  if i==0:aa=a
  if i==bays:bb=b
  prism('vertical',aa,bb,52,102.4,.06,.13)
 # Crown strip has coarser stronger vertical divisions, estimated and without roof equipment.
 upper=max(1,round(length/3.6))
 for i in range(upper+1):
  if i==upper and edge!=selected[-1]:continue # suppress duplicate segment-end jamb
  pos=a+(b-a)*(i/upper);aa=pos-t*.065;bb=pos+t*.065
  if i==0:aa=a
  if i==upper:bb=b
  prism('vertical',aa,bb,102.52,109.25,.06,.21)
created=[]
for kind,(verts,faces) in groups.items():
 me=bpy.data.meshes.new('Quay1 '+kind);me.from_pydata(verts,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(p.calc_area()>1e-9 for p in bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new('Quay1 visible upper '+kind,me);bpy.context.collection.objects.link(ob);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']='Photo-guided west/southwest upper arc only; dimensions estimated';created.append(ob)
 m=bpy.data.materials.new('Quay1 estimated '+kind);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];col=(.045,.095,.105,1) if kind=='glass' else (.28,.33,.34,1);bs.inputs['Base Color'].default_value=col;m.diffuse_color=col;bs.inputs['Roughness'].default_value=.24 if kind=='glass' else .48;bs.inputs['Metallic'].default_value=.2 if kind=='glass' else .55;me.materials.append(m)
assert signature(base)==original
D={'owner_id':ID,'source_native':str(src),'source_native_sha256':hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'baseline_geometry_materials_signature':original,'baseline_unchanged':True,'baseline_roof_z_m':111,'visible_edges':[{'index':i,'a':list(ring[i]),'b':list(ring[(i+1)%len(ring)])} for i in selected],'height_scope_scene_m':[52,109.45],'estimated_parameters':{'shaft_band_spacing_m':3.15,'shaft_mullion_target_spacing_m':1.8,'upper_mullion_target_spacing_m':3.6,'upper_zone_start_m':102.4,'max_facade_projection_m':.23,'glass_frame_recess_m':.135},'primitive_count':len(solidchecks),'primitives':solidchecks,'uncertainties':['Photo identity strongly supported; camera approximate with previously observed119px discrepancy, not confidence interval.','52m lower cutoff conservative estimated visible upper scope, not measured occlusion line.','Bay/floor cadence, upper-zone height, frame depth/materials estimated. No exact floor count inferred.','No bottom entrance/east rear/north hook decoration. No roof equipment/courtyard/roof change.','Opaque glass-like shader is exterior appearance proxy; no interior/transmission evidence.','Mapped baseline111m remains inherited datum assumption, not corrected to DSM.','Per-prism closed solids may intersect deliberately at frame joints; not global boolean-union simulation volume.'],'source_photo_id':'pexels_ollie_11491155','source_photo_sha256':hashlib.file_digest((R/'references/pexels-ollie-craig-11491155.jpeg').open('rb'),'sha256').hexdigest()};(O/'authoring.json').write_text(json.dumps(D,indent=2))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('QA studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.56,.65,.72,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;ld=bpy.data.lights.new('QA Sun','SUN');ld.energy=2;lo=bpy.data.objects.new('QA Sun',ld);s.collection.objects.link(lo);lo.rotation_euler=(.4,-.7,-.5);cam=bpy.data.objects.new('QA camera',bpy.data.cameras.new('QA camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';C=Vector((-166,203,58))
views=[('overview',C,(-150,-90,60),145),('detail',Vector((-178,199,82)),(-75,-45,20),38),('upper',Vector((-176,199,105)),(-70,-45,20),26),('rear',C,(100,110,65),145),('roof',Vector((-165,203,109)),(-20,-15,100),75)]
for idx,(name,target,off,scale) in enumerate(views):
 cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'))
 if idx==0:
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'quay1.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for ob in [base]+created:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'quay1.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 bpy.ops.render.render(write_still=True)
expected={}
for ob in [base]+created:ob.data.calc_loop_triangles();expected[ob.name]=len(ob.data.loop_triangles)
bpy.ops.wm.open_mainfile(filepath=str(O/'quay1.blend'));assert signature(bpy.data.objects[ID])==original;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'quay1.glb'));ms=[o for o in bpy.data.objects if o.type=='MESH'];assert {o.name:len(o.data.polygons) for o in ms}==expected;assert all(o.get('building_id')==ID for o in ms);vv=[o.matrix_world@v.co for o in ms for v in o.data.vertices];bounds=[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]];assert abs(bounds[1][2]-111)<.0001
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'baseline_signature_unchanged':True,'glb_reimported':True,'meshes':expected,'bounds_enu_m':bounds,'owner_ids_verified':True,'added_prisms_closed_manifold':True,'added_zero_area_faces':0,'roof_max_unchanged_111m':True,'visual_reviewed':False},indent=2));print('QUAY1 VERIFIED',bounds)
