from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-south-facade-002';O.mkdir(exist_ok=True);src=R/'exports/morgan_south-facade-001/morgan_south.blend';bpy.ops.wm.open_mainfile(filepath=str(src));ID='overture-part-b317a51d-586a-3b78-9ee5-b685a2db94a0'
def sig(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'mat':[m.name for m in o.data.materials],'mi':[p.material_index for p in o.data.polygons],'world':[list(r) for r in o.matrix_world],'properties':dict(o.items())},sort_keys=True,default=str).encode()).hexdigest()
old_details=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('morgan_south_')];assert len(old_details)==5
for o in old_details:bpy.data.objects.remove(o,do_unlink=True)
base=[o for o in bpy.data.objects if o.type=='MESH'];before={o.name:sig(o) for o in base};q=next(q for q in json.loads((R/'geometry.json').read_text())['buildings'] if q['id']==ID);a=Vector(q['geometry'][0]['outer'][13]);b=Vector(q['geometry'][0]['outer'][14]);u=(b-a).normalized();n=Vector((u.y,-u.x));L=(b-a).length
colors={'upper_glass':(.075,.12,.135,1),'upper_stone':(.27,.205,.18,1),'frames':(.035,.042,.045,1),'spandrel':(.025,.04,.045,1),'pale_stone':(.55,.53,.48,1),'lower_dark_panels':(.026,.035,.033,1),'arch_reveal':(.21,.16,.14,1)};groups={k:[[],[]] for k in colors};prims=[]
def poly(k,points,d0,d1):
 assert all(-1e-8<=s<=L+1e-8 for s,z in points);v,f=groups[k];off=len(v);N=len(points);vv=[(a.x+u.x*s+n.x*d,a.y+u.y*s+n.y*d,z) for d in [d0,d1] for s,z in points];vec=[Vector((s,z,0)) for s,z in points];tri=tessellate_polygon([vec]);idx={tuple(p):i for i,p in enumerate(vec)};ff=[]
 for tr in tri:
  t=tuple((p if isinstance(p,int) else idx[tuple(p)]) for p in tr);ff.extend([tuple(reversed(t)),tuple(i+N for i in t)])
 ff.extend([(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]);v.extend(vv);f.extend([tuple(off+i for i in face) for face in ff]);prims.append({'material':k,'profile_sz':points,'depth':[d0,d1]})
def box(k,s0,s1,z0,z1,d0,d1):poly(k,[(s0,z0),(s1,z0),(s1,z1),(s0,z1)],d0,d1)
upper=[(.34255,5.07316),(6.04414,10.87678)];z0,z1=21.53727,28.60715
for s0,s1 in upper:
 box('upper_glass',s0,s1,z0,z1,.018,.045);box('spandrel',s0,s1,24.19381,25.66926,.045,.075)
 for frac in [0,.2,.5,.8,1]:
  s=s0+(s1-s0)*frac;box('frames',max(0,s-.035),min(L,s+.035),z0,z1,.05,.14)
 for z in [z0,24.19381,25.66926,z1-.07]:box('frames',s0,s1,z,z+.07,.05,.15)
for s0,s1 in [(.02,.30),(5.15,5.97),(10.91,L)]:
 box('upper_stone',s0,s1,21.38,28.84,.01,.25)
 for z in [21.60,21.83,27.00,27.23,27.46]:box('pale_stone',s0,s1,z,z+.08,.25,.262)
box('upper_stone',.02,L,28.72,28.90,.01,.25)
# Pale tier envelope piers and cornices; panes recessed relative to added stone, opaque backing.
for s0,s1 in [(0,.50),(5.12,6.10),(10.89,L)]:box('pale_stone',s0,s1,9.02,21.30,.012,.24)
for z0,z1 in [(20.95,21.30),(19.45,19.72),(14.32,15.32),(8.90,9.10)]:box('pale_stone',0,L,z0,z1,.012,.24)
for s0,s1 in [(.62324,5.03472),(6.20945,10.85652)]:
 box('lower_dark_panels',s0,s1,15.585,19.178,.018,.045)
 for frac in [0,.14,.5,.86,1]:
  ss=s0+(s1-s0)*frac;box('pale_stone',max(0,ss-.075),min(L,ss+.075),15.50,19.28,.05,.24)
 for z in [15.50,18.54,19.18]:box('pale_stone',s0,s1,z,z+.10,.05,.24)
# Outer arch bounds: right end raw11.0064 ->10.91, a0.0964m conditional inward adjustment.
for s0,s1 in [(.70274,5.29028),(6.48265,10.91)]:
 bottom=9.17883;top=13.95768;rise=.42;spring=top-rise;segments=20
 # Segmental elliptical approximation: observed shallow arch, exact radius unknown.
 curve=[(s0+(s1-s0)*i/segments,spring+rise*math.sqrt(max(0,1-(2*i/segments-1)**2))) for i in range(segments+1)]
 poly('lower_dark_panels',[(s0,bottom),(s1,bottom)]+list(reversed(curve)),.018,.05)
 box('arch_reveal',s0,min(s0+.16,s1),bottom,spring,.05,.22);box('arch_reveal',max(s0,s1-.16),s1,bottom,spring,.05,.22)
 box('arch_reveal',s0,s1,bottom,bottom+.14,.05,.22)
 for i in range(segments):
  x0,z0=curve[i];x1,z1=curve[i+1];poly('arch_reveal',[(x0,z0),(x1,z1),(x1,z1+.14),(x0,z0+.14)],.05,.22)
 # Dark photograph does not resolve grille type/count; no repeated speculative grille.
checks=[]
for k,(v,f) in groups.items():
 me=bpy.data.meshes.new('morgan_south002_'+k);me.from_pydata(v,[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(face.calc_area()>1e-10 for face in bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(me.name,me);bpy.context.scene.collection.objects.link(ob);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['research_object_id']='morgan-south002::'+k;ob['scope']='Edge13 upper/pale/arch photo registration002; dimensions estimated; body roof unchanged';m=bpy.data.materials.new('morgan_south002_'+k);m.diffuse_color=colors[k];me.materials.append(m);checks.append({'name':ob.name,'closed_components':True,'zero_area':0})
assert all(sig(bpy.data.objects[k])==h for k,h in before.items());s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_percentage=100;cam=s.camera
# Existing model camera units/pose match projection; compare actual rendered facade to photo without using photo as texture.
reg=json.loads((R/'exports/morgan-facade-registration-002/proposal.json').read_text());cp=reg['camera_preserved'];yaw,pitch,roll=cp[3:6];fw=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)));right=Vector((math.sin(yaw),-math.cos(yaw),0));up=right.cross(fw);right2=right*math.cos(roll)+up*math.sin(roll);up2=-right*math.sin(roll)+up*math.cos(roll);from mathutils import Matrix
cam.location=cp[:3];cam.rotation_euler=Matrix((right2,up2,-fw)).transposed().to_euler();cam.data.type='PERSP';cam.data.sensor_fit='HORIZONTAL';cam.data.sensor_width=36;cam.data.lens=math.exp(cp[6])*36/1368;cam.data.shift_x=0;cam.data.shift_y=0;cam.data.clip_start=.1;cam.data.clip_end=3000;s.render.resolution_x=1368;s.render.resolution_y=1824;s.render.filepath=str(O/'same-camera.png');bpy.ops.render.render(write_still=True)
for name,target,offset,scale in [('detail',(-318.286,-73.059,19),(-5,-32,4),24),('overview',(-337,-76,35),(-70,-100,60),125)]:
 c=Vector(target);cam.location=c+Vector(offset);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;s.render.resolution_x=1100;s.render.resolution_y=1000;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'morgan_south002.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={}
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();expected[ob.name]={'triangles':len(ob.data.loop_triangles),'owner':ob.get('building_id'),'materials':[m.name for m in ob.data.materials]}
bpy.ops.export_scene.gltf(filepath=str(O/'morgan_south002.glb'),export_format='GLB',use_selection=True,export_extras=True);bpy.ops.wm.open_mainfile(filepath=str(O/'morgan_south002.blend'));assert all(sig(bpy.data.objects[k])==h for k,h in before.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'morgan_south002.glb'));actual={ob.name:{'triangles':len(ob.data.polygons),'owner':ob.get('building_id'),'materials':[m.name for m in ob.data.materials]} for ob in bpy.data.objects if ob.type=='MESH'};assert actual==expected
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'glb_reimported':True,'exact_body_roof_fingerprints':before,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'all_new_components_closed':True,'zero_area_faces':0,'new_meshes':checks,'primitives':prims,'owner':ID,'mapped_edge_length_m':L,'right_arch_inward_adjustment_m':.096403529538524,'max_right_s':max(p[0] for prim in prims for p in prim['profile_sz']),'opaque_backing_not_through_wall':True,'visual_reviewed':False},indent=2))
