from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/one_canada_roof_seam004';source=P/'runs/canary_wharf_appearance_quay1_recess_001/region.blend';name='Canada_317cf479fcef_steel';owner='overture-part-0c84e402-a7c0-399a-a2af-317cf479fcef'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source),link=False) as (a,b):b.objects=[name]
roof=b.objects[0];bpy.context.collection.objects.link(roof)
def signature(o):return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in o.data.vertices],'polygons':[list(f.vertices) for f in o.data.polygons]},sort_keys=True).encode()).hexdigest()
sig=signature(roof)
A=Vector((-62.78107416387453,-19.592134296625748,210));B=Vector((-68.95413888237167,-56.084654776538564,210));C=Vector((-46.981853803623025,-41.01220148699094,235));T=(B-A).normalized();N=(B-A).cross(C-A).normalized();L=(B-A).length;mid=(A+B)/2;D=C-mid
m=bpy.data.materials.new('Estimated dark major seam metal');m.diffuse_color=(.045,.052,.058,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color;m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.6
records=[]
# Five central observed seam family representatives. Positions and shallow section inferred.
for i,q in enumerate([-.30,-.15,0,.15,.30]):
 width=.10;half=width/2; vmax=1-2*(abs(q)+half/L)-.025;vmin=.04
 pts=[mid+T*(q*L-half)+D*vmin,mid+T*(q*L+half)+D*vmin,mid+T*(q*L+half)+D*vmax,mid+T*(q*L-half)+D*vmax]
 verts=[list(p+N*h) for h in [-.015,.04] for p in pts];faces=[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
 me=bpy.data.meshes.new('Major_seam_mesh');me.from_pydata(verts,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);assert all(e.is_manifold for e in bm.edges);bm.to_mesh(me);bm.free();me.materials.append(m);o=bpy.data.objects.new('Canada_conditional_west_major_seam_'+str(i+1),me);bpy.context.collection.objects.link(o);o['building_id']=owner;o['basis']='Photo-supported major seam family; compass face conditional, position/profile/width estimated';o['integration_status']='HOLD orientation unresolved';records.append({'name':o.name,'base_fraction':q+.5,'v_range':[vmin,vmax],'width_m':width,'normal_offsets_m':[-.015,.04]})
bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2.5;bpy.context.object.rotation_euler=(Vector((1,-.3,-1))).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='AREA',location=mid+Vector((-60,40,75)));bpy.context.object.data.energy=3500;bpy.context.object.data.size=30;bpy.context.object.rotation_euler=(C-bpy.context.object.location).to_track_quat('-Z','Y').to_euler();bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO';target=mid+D*.38;s.camera.location=target+Vector((-95,36,12));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=48
bpy.ops.wm.save_as_mainfile(filepath=str(O/'crown.blend'));bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'crown.glb'),export_format='GLB',use_selection=True,export_extras=True)
for nm,hide in [('before',True),('after',False)]:
 for o in bpy.data.objects:
  if o.name.startswith('Canada_conditional'):o.hide_render=hide
 s.render.filepath=str(O/(nm+'.png'));bpy.ops.render.render(write_still=True)
assert signature(roof)==sig
(O/'geometry_contract.json').write_text(json.dumps({'source':str(source),'source_mesh':name,'source_mesh_unchanged':True,'source_mesh_signature':sig,'face_compass':'conditional west edge0 NOT verified','face_vertices':[list(A),list(B),list(C)],'normal':list(N),'components':records,'no_global_changes':True},indent=2))
bpy.ops.wm.open_mainfile(filepath=str(O/'crown.blend'));native={o.name:([list(o.matrix_world@v.co) for v in o.data.vertices],o.get('building_id')) for o in bpy.data.objects if o.type=='MESH'};assert signature(bpy.data.objects[name])==sig;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'crown.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert set(native)=={o.name for o in obs};err=0
for o in obs:
 vv,bid=native[o.name];assert o.get('building_id')==bid
 for axis in range(3):
  for fn in [min,max]:err=max(err,abs(fn(v[axis] for v in vv)-fn((o.matrix_world@v.co)[axis] for v in o.data.vertices)))
assert err<.0001
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'source_mesh_unchanged':True,'independent_glb_ids_bounds':True,'bounds_error_m':err,'added_closed_seams':5,'face_geographically_verified':False},indent=2))
