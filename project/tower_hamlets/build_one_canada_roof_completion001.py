from pathlib import Path
import bpy,bmesh,json,hashlib,datetime,time
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/one_canada_roof_completion001';O.mkdir(exist_ok=True);start=time.time();stamp=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();timing={'start_utc':stamp(),'scope':'Estimated remaining three pyramid faces; existing roof and west details preserved','threads':2};source=P/'runs/canary_wharf_appearance_one_canada_facade_001/region.blend';owner='overture-part-0c84e402-a7c0-399a-a2af-317cf479fcef';roofname='Canada_317cf479fcef_steel'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source),link=False) as(a,b):b.objects=[n for n in a.objects if n==roofname or n.startswith('Canada_conditional_west_major_seam_') or n.startswith('Canada_west_horizontal_course_') or n.startswith('Canada_roofbase_upright')]
original=[]
for o in b.objects:
 if o:bpy.context.collection.objects.link(o);original.append(o)
roof=bpy.data.objects[roofname]
def sig(o):return hashlib.sha256(json.dumps({'vertices':[list(v.co)for v in o.data.vertices],'faces':[list(f.vertices)for f in o.data.polygons]},sort_keys=True).encode()).hexdigest()
sigs={o.name:sig(o)for o in original};ring=[Vector((*q,210))for q in [(-62.78107416387453,-19.592134296625748),(-68.95413888237167,-56.084654776538564),(-31.18250173838673,-62.43785433057616),(-25.009700429859162,-25.934162544223287)]];C=Vector((-46.981853803623025,-41.01220148699094,235));dark=bpy.data.materials.get('Estimated dark major seam metal');steel=bpy.data.materials.get('Estimated west gray steel');assert dark and steel;steelidx=list(roof.data.materials).index(steel);new=[];records=[];faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
def strip(name,pts,N,lo,hi,edge,kind):
 me=bpy.data.meshes.new(name);me.from_pydata([list(p+N*h)for h in [lo,hi]for p in pts],[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);assert all(e.is_manifold for e in bm.edges) and bm.calc_volume()>0;bm.to_mesh(me);bm.free();me.materials.append(dark);o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['building_id']=owner;o['evidence_class']='estimated_unobserved_face_completion';o['basis']='Transferred accepted west panel grammar to unseen face for visual wholeasset benchmark; not photographically verified';new.append(o);records.append({'name':name,'edge':edge,'kind':kind,'normal_offsets':[lo,hi]})
facecontracts=[]
for e in [1,2,3]:
 A=ring[e];B=ring[(e+1)%4];T=(B-A).normalized();N=(B-A).cross(C-A).normalized();L=(B-A).length;mid=(A+B)/2;D=C-mid
 for q in roof.data.polygons:
  if len(q.vertices)==3 and max(roof.data.vertices[i].co.z for i in q.vertices)>234 and q.normal.dot(N)>.999:q.material_index=steelidx
 for i,q in enumerate([-.30,-.15,0,.15,.30]):
  half=.05;v0=.04;v1=1-2*(abs(q)+half/L)-.025;pts=[mid+T*(q*L-half)+D*v0,mid+T*(q*L+half)+D*v0,mid+T*(q*L+half)+D*v1,mid+T*(q*L-half)+D*v1];strip(f'CanadaEstimated_face{e}_major_{i+1}',pts,N,-.015,.04,e,'major_seam')
 for i in range(1,68):
  v=i/68;v0=v-.020/25;v1=v+.020/25;pts=[mid-T*(L*(1-v0)/2-.035)+D*v0,mid+T*(L*(1-v0)/2-.035)+D*v0,mid+T*(L*(1-v1)/2-.035)+D*v1,mid-T*(L*(1-v1)/2-.035)+D*v1];strip(f'CanadaEstimated_face{e}_course_{i:02}',pts,N,-.006,.012,e,'horizontal_course')
 facecontracts.append({'edge':e,'vertices':[list(A),list(B),list(C)],'normal':list(N),'basis':'Entire face grammar estimated; no new imagery','corner_treatment':'35mm horizontal course setback from each face edge; no corner wrap or coincident edge seams. Major strips end inside triangle. Apex remains original.'})
assert all(sig(o)==sigs[o.name]for o in original);timing['author_geometry_complete_utc']=stamp();s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2.5;bpy.context.object.rotation_euler=Vector((1,-.3,-1)).to_track_quat('-Z','Y').to_euler();bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=61;target=Vector((C.x,C.y,221))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'roof.blend'));bpy.ops.object.select_all(action='DESELECT')
for o in original+new:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'roof.glb'),export_format='GLB',use_selection=True,export_extras=True)
timing['render_start_utc']=stamp()
for name,delta in [('northwest',(-75,65,35)),('southeast',(75,-65,35))]:
 s.camera.location=target+Vector(delta);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
timing['render_end_utc']=stamp();bpy.ops.wm.open_mainfile(filepath=str(O/'roof.blend'));native={o.name:([list(o.matrix_world@v.co)for v in o.data.vertices],o.get('building_id'))for o in bpy.data.objects if o.type=='MESH'};assert all(sig(bpy.data.objects[n])==v for n,v in sigs.items());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'roof.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert set(native)=={o.name for o in obs};err=0
for o in obs:
 vv,bid=native[o.name];assert o.get('building_id')==bid
 for ax in range(3):
  for fn in [min,max]:err=max(err,abs(fn(v[ax]for v in vv)-fn((o.matrix_world@v.co)[ax]for v in o.data.vertices)))
assert err<.0001;timing['qa_end_utc']=stamp();timing['pipeline_elapsed_seconds']=time.time()-start;(O/'timing.json').write_text(json.dumps(timing,indent=2));(O/'contract.json').write_text(json.dumps({'source':str(source),'owner':owner,'source_geometry_signatures':sigs,'existing_geometry_unchanged':True,'added_objects':records,'face_contracts':facecontracts,'material_change':'Use existing Estimated west gray steel only for remaining3 pyramid triangles; west already unchanged','geographic_verification':False},indent=2));(O/'checks.json').write_text(json.dumps({'native_reopened':True,'GLB_independently_imported':True,'bounds_error_m':err,'new_closed_positive_components':len(new),'existing_meshes_exact':True},indent=2))
