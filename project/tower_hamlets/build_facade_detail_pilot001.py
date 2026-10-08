from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade-detail-pilot-001';O.mkdir(exist_ok=True);src=P/'runs/canary_wharf_appearance_ownerd42_001/region.blend';ID='overture-building-a6a8ac29-204a-43a7-b4d0-af0fa65a47dc';names=[ID,'Quay1 visible upper glass','Quay1 visible upper horizontal','Quay1 visible upper vertical'];bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src),link=False) as (a,b):
 assert all(n in a.objects for n in names);b.objects=names.copy()
for ob in b.objects:bpy.context.collection.objects.link(ob)
def signature(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'p':[list(p.vertices) for p in o.data.polygons],'materials':[m.name for m in o.data.materials],'mi':[p.material_index for p in o.data.polygons]},sort_keys=True).encode()).hexdigest()
base=bpy.data.objects[ID];glass=bpy.data.objects[names[1]];original={n:signature(bpy.data.objects[n]) for n in names};g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if q['id']==ID);ring=[Vector(p) for p in f['geometry'][0]['outer']];edges=[]
for i in range(9,16):
 a=ring[i];b=ring[(i+1)%len(ring)];t=(b-a).normalized();a=a+t*.04;b=b-t*.04;n=Vector((t.y,-t.x));edges.append((i,a,b,t,n))
def solid(name,a,b,n,z0,z1,d0,d1):
 vs=[(q.x+n.x*d,q.y+n.y*d,z) for z in [z0,z1] for q,d in [(a,d0),(b,d0),(b,d1),(a,d1)]];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return o
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Pilot inspection world');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.67,.75,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.35,-.7,-.6);bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO'
i,a,b,t,n=edges[3];mid=(a+b)/2;target=Vector((mid.x,mid.y,85));cam.location=target+Vector((n.x*12+t.x*10,n.y*12+t.y*10,4));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=8;s.render.filepath=str(O/'before-detail.png');bpy.ops.render.render(write_still=True)
# Cut true shallow envelope recesses; retained metal frame layout is unchanged.
for i,a,b,t,n in edges:
 cutter=solid('temporary aperture',a,b,n,52,109.45,-.18,.3);bpy.context.view_layer.objects.active=base;mod=base.modifiers.new('True observed upper glazing recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
material=glass.data.materials[0];props={k:glass[k] for k in glass.keys()};bpy.data.objects.remove(glass,do_unlink=True);pieces=[]
for i,a,b,t,n in edges:
 q=solid('pilot inset glazing '+str(i),a,b,n,52.025,109.425,-.14,-.10);pieces.append(q)
bpy.ops.object.select_all(action='DESELECT')
for q in pieces:q.select_set(True)
bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();glass=bpy.context.object;glass.name=names[1];glass.data.materials.clear();glass.data.materials.append(material)
for k,v in props.items():glass[k]=v
glass['detail_basis']='Existing inspected Ollie photo upper arc; recess depth0.10m behind footprint estimated, no new cadence';base['detail_pilot']='Seven shallow upper facade cutbacks depth0.18m; roof111 and footprint preserved';base['coverage']='Body modified only by seven upper glazing recess cuts; footprint and roof111 unchanged';base['research_object_id']='facade-detail-pilot-001::body';glass['coverage']='Upper observed arc glazing moved into10cm estimated setback; source body modified by shallowcutbacks';glass['research_object_id']='facade-detail-pilot-001::glass';bpy.context.view_layer.update()
# Boxed metal returns bridge existing slim face frames to inset glazing.
returns=[]
prior_authoring=json.loads((R/'exports/quay1-facade-study-001/authoring.json').read_text())
for source_name in names[2:]:
 source=bpy.data.objects[source_name];verts=[v.co.copy() for v in source.data.vertices];assert len(verts)%8==0
 for start in range(0,len(verts),8):
  points=verts[start:start+8];center=sum(points,Vector())/8
  kind='horizontal' if 'horizontal' in source_name else 'vertical'
  memberships=[q['edge'] for q in prior_authoring['primitives'] if q['kind']==kind]
  assert len(memberships)==len(verts)//8
  best=next(e for e in edges if e[0]==memberships[start//8])
  _,a,b,t,n=best;depths=[(Vector((q.x,q.y))-a).dot(n) for q in points];lo,hi=min(depths),max(depths);assert hi-lo<.20,(source_name,start,lo,hi)
  for k,q in enumerate(points):
   dep=depths[k];newdep=-.10+(dep-lo)/(hi-lo)*.165;verts[start+k]=q+Vector((n.x*(newdep-dep),n.y*(newdep-dep),0))
 me=bpy.data.meshes.new(source_name+' rear returns');me.from_pydata(verts,[],[list(p.vertices) for p in source.data.polygons]);me.update();ob=bpy.data.objects.new(source_name+' rear returns',me);bpy.context.collection.objects.link(ob);me.materials.append(source.data.materials[0]);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']='Estimated shallow boxed metal frame returns, unchanged cadence';ob['research_object_id']='facade-detail-pilot-001::'+ob.name;returns.append(ob)
assert all(signature(bpy.data.objects[n])==original[n] for n in names[2:]);checks=[]
for ob in [base,glass]+returns:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bad=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-10 for f in bm.faces);bm.free();assert bad==0 and zero==0,(ob.name,bad,zero);checks.append({'name':ob.name,'nonmanifold_edges':bad,'zero_area_faces':zero})
def tree(ob):return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
bt,gt=tree(base),tree(glass);rays=[]
for i,a,b,t,n in edges:
 for ratio in [.2,.5,.8]:
  p=a+(b-a)*ratio
  for z in [53.,65.,85.,105.,108.]:
   origin=Vector((p.x+n.x,p.y+n.y,z));direction=Vector((-n.x,-n.y,0));bh=bt.ray_cast(origin,direction,3);gh=gt.ray_cast(origin,direction,3);assert gh[0] is not None and bh[0] is not None;assert abs(gh[3]-1.10)<.001 and abs(bh[3]-1.18)<.002,(i,z,gh[3],bh[3]);rays.append({'edge':i,'along_fraction':ratio,'z':z,'glass_distance_m':gh[3],'backing_distance_m':bh[3]})
s.render.filepath=str(O/'after-detail.png');bpy.ops.render.render(write_still=True)
target=Vector((-166,203,58));cam.location=target+Vector((-150,-90,60));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=145;s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'quay1-detail.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
expected={}
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();expected[ob.name]={'triangles':len(ob.data.loop_triangles),'materials':[m.name for m in ob.data.materials],'owner':ob.get('building_id')}
bpy.ops.export_scene.gltf(filepath=str(O/'quay1-detail.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);bpy.ops.wm.open_mainfile(filepath=str(O/'quay1-detail.blend'));assert all(signature(bpy.data.objects[n])==original[n] for n in names[2:]);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'quay1-detail.glb'));actual={o.name:{'triangles':len(o.data.polygons),'materials':[m.name for m in o.data.materials],'owner':o.get('building_id')} for o in bpy.data.objects if o.type=='MESH'};assert actual==expected;vv=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];assert abs(max(v.z for v in vv)-111)<.0001
report={'owner_id':ID,'source_native':str(src),'source_sha256':hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'source_signatures':original,'retained_frame_meshes_unchanged':names[2:],'changed_meshes':names[:2],'bounds_enu':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'native_reopened':True,'independent_glb_import':True,'mesh_checks':checks,'mesh_inventory':actual,'opening_rays':rays,'estimated_recess_depth_m':.10,'body_cut_depth_m':.18,'source_photo_id':'pexels_ollie_11491155','limitations':['Depth is architectural estimate, not recoverable measurement from distant photo.','Same existing estimated frame cadence; no added entrances or hidden facade.','Opaque glazing appearance, no interior model/transmission claim.','Only upper exposed arc edges9..15 scene52..109.45; roof111 unchanged.']};(O/'checks.json').write_text(json.dumps(report,indent=2));print('DONE',actual)
