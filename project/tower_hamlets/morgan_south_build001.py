from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan_south-facade-001';O.mkdir(exist_ok=True);ID='overture-part-b317a51d-586a-3b78-9ee5-b685a2db94a0';src=R/'exports/morgan-photo-study-003/morgan.blend';bpy.ops.wm.open_mainfile(filepath=str(src))
for o in list(bpy.data.objects):
 if o.type=='MESH' and o.get('building_id')!=ID:bpy.data.objects.remove(o,do_unlink=True)
base=[o for o in bpy.data.objects if o.type=='MESH']
def sig(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'mat':[m.name for m in o.data.materials],'mi':[p.material_index for p in o.data.polygons],'world':[list(r) for r in o.matrix_world]},sort_keys=True).encode()).hexdigest()
sigs={o.name:sig(o) for o in base};q=next(q for q in json.load(open(R/'geometry.json'))['buildings'] if q['id']==ID);ring=q['geometry'][0]['outer'];a=Vector(ring[13]);b=Vector(ring[14]);u=(b-a).normalized();n=Vector((u.y,-u.x));groups={k:[[],[]] for k in ['dark_glass','stone_piers','black_frames','dark_spandrel','pale_stone_accents']};prims=[]
def box(k,s0,s1,z0,z1,d0,d1):
 aa=a+u*s0;bb=a+u*s1;vv=[(p.x+n.x*d,p.y+n.y*d,z) for z in [z0,z1] for p,d in [(aa,d0),(bb,d0),(bb,d1),(aa,d1)]];ff=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];v,f=groups[k];off=len(v);v.extend(vv);f.extend([tuple(off+i for i in t) for t in ff]);prims.append({'kind':k,'s':[s0,s1],'z':[z0,z1],'depth':[d0,d1]})
bays=[(.65,5.05),(5.8,10.25)]
for s0,s1 in bays:
 box('dark_glass',s0,s1,19,28.15,.018,.045);box('dark_spandrel',s0,s1,22.4,24.2,.045,.075)
 for ss in [s0+(s1-s0)*f for f in [0,.2,.5,.8,1]]:box('black_frames',ss-.035,ss+.035,19,28.15,.05,.14)
 for zz in [19,22.4,24.2,28.08]:box('black_frames',s0,s1,zz,zz+.07,.05,.15)
for s0,s1 in [(0.12,.58),(5.12,5.72),(10.32,10.73)]:
 box('stone_piers',s0,s1,18.85,28.45,.01,.25)
 for zz in [19.2,19.5,26.15,26.45,26.75]:box('pale_stone_accents',s0,s1,zz,zz+.09,.25,.262)
 # Visible short pale stone accents are evidence-supported; exact levels estimated.
for s0,s1 in [(0.12,10.73)]:box('stone_piers',s0,s1,28.23,28.48,.01,.25)
colors={'pale_stone_accents':(.55,.53,.48,1),'dark_glass':(.075,.12,.135,1),'stone_piers':(.27,.205,.18,1),'black_frames':(.035,.042,.045,1),'dark_spandrel':(.025,.04,.045,1)}
for k,(v,f) in groups.items():
 me=bpy.data.meshes.new('morgan_south_'+k);me.from_pydata(v,[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(f.calc_area()>1e-10 for f in bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new('morgan_south_'+k,me);bpy.context.scene.collection.objects.link(ob);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']='Only mappededge13 two visible bays; all dimensions estimated; roof unchanged';m=bpy.data.materials.new('morgan_south_'+k);m.diffuse_color=colors[k];me.materials.append(m)
assert all(sig(bpy.data.objects[k])==v for k,v in sigs.items());s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100
if not s.camera:
 cam=bpy.data.objects.new('QA camera',bpy.data.cameras.new('QA camera'));s.collection.objects.link(cam);s.camera=cam
cam=s.camera;cam.data.type='ORTHO';mid=(a+b)/2
for name,center,offset,scale in [('detail',(mid.x,mid.y,23.5),(n.x*30,n.y*30,5),14),('overview',(-337,-76,35),(-70,-100,60),125)]:
 c=Vector(center);cam.location=c+Vector(offset);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;s.render.filepath=str(O/('morgan_south-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'morgan_south.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
expected={}
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True);o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
bpy.ops.export_scene.gltf(filepath=str(O/'morgan_south.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);bpy.ops.wm.open_mainfile(filepath=str(O/'morgan_south.blend'));assert all(sig(bpy.data.objects[k])==v for k,v in sigs.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'morgan_south.glb'));ms=[o for o in bpy.data.objects if o.type=='MESH'];assert {o.name:len(o.data.polygons) for o in ms}==expected
report={'native_reopened':True,'glb_reimported':True,'original_meshes_roofs_materials_exact':sigs,'new_prisms_closed':True,'new_zero_area_faces':0,'owner_id':ID,'edge':13,'edge_endpoints':[list(a),list(b)],'normal':list(n),'bay_positions_estimated':bays,'primitives':prims,'mesh_count':len(ms),'triangles':sum(expected.values()),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'limitation':'Surface-mounted panels recessed relative to added piers/frames, not boolean wall openings. No inner rooms or transparent material.','visual_reviewed':False};(O/'morgan_south-checks.json').write_text(json.dumps(report,indent=2))
