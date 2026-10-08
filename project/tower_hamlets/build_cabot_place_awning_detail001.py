from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/cabot_place_awning_detail001';O.mkdir(exist_ok=True);src=P/'runs/canary_wharf_appearance_one_canada_crown_003/region.blend';bid='overture-building-dfbe7e30-b124-490e-88e7-e5cf6154dd27'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src),link=False) as(a,b):b.objects=[n for n in a.objects if 'CabotPlace' in n or 'dfbe' in n or 'DFBE' in n]
original=[]
for o in b.objects:
 if o and o.type=='MESH' and o.get('building_id')==bid:bpy.context.collection.objects.link(o);original.append(o)
def sig(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'f':[list(f.vertices) for f in o.data.polygons]},sort_keys=True).encode()).hexdigest()
sigs={o.name:sig(o) for o in original};A=Vector((-236.89726685,-13.93509856,0));B=Vector((-240.19617850,-32.14786703,0));T=(B-A).normalized();N=Vector((T.y,-T.x,0));new=[]
def mat(n,col,metal):
 m=bpy.data.materials.new(n);m.diffuse_color=(*col,1);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.72;bs.inputs['Metallic'].default_value=metal;return m
cloth=mat('Estimated charcoal awning cover',(.035,.04,.044),0);steel=mat('Estimated dark awning supports',(.07,.075,.08),.6)
def mesh(name,coords,faces,material):
 me=bpy.data.meshes.new(name);me.from_pydata([list(A+T*s+N*d+Vector((0,0,z))) for s,d,z in coords],[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume()>0;bm.to_mesh(me);bm.free();me.materials.append(material);o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['building_id']=bid;o['basis']='Anna observed sloped restaurant awning/valance; dimensions, section, support pattern and attachment height inferred';new.append(o);return o
faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
def box(name,s0,s1,d0,d1,z0,z1,m):return mesh(name,[(s,d,z)for z in [z0,z1] for s,d in [(s0,d0),(s1,d0),(s1,d1),(s0,d1)]],faces,m)
s0,s1=2.4,16.0
# Closed 35mm cover; back edge connects embedded wall rail.
mesh('CabotAwning_closed_sloped_cover',[(s,d,z+dz) for dz in [0,.035] for s,d,z in [(s0,0,2.94),(s1,0,2.94),(s1,1.2,2.34),(s0,1.2,2.34)]],faces,cloth)
box('CabotAwning_hanging_valance',s0,s1,1.17,1.205,2.08,2.36,cloth);box('CabotAwning_wall_rail',s0,s1,-.07,.07,2.87,2.995,steel);box('CabotAwning_front_rail',s0,s1,1.10,1.18,2.27,2.34,steel)
for i,sx in enumerate([2.55,5.8,9.2,12.5,15.85]):
 box('CabotAwning_wall_plate_'+str(i),sx-.07,sx+.07,-.05,.055,1.94,2.92,steel)
 # Solid narrow triangular bracket physically embedded in wall and meeting front rail.
 pts=[(sx-.03,-.025,1.99),(sx-.03,1.15,2.29),(sx-.03,-.025,2.9),(sx+.03,-.025,1.99),(sx+.03,1.15,2.29),(sx+.03,-.025,2.9)]
 mesh('CabotAwning_estimated_bracket_'+str(i),pts,[[0,2,1],[3,4,5],[0,1,4,3],[1,2,5,4],[2,0,3,5]],steel)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1400;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=Vector((1,-.2,-1)).to_track_quat('-Z','Y').to_euler();bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO';target=A+T*9.2+Vector((0,0,4.8))
for view,delta,scale in [('front',N*45+Vector((0,0,3)),23),('oblique',N*30+T*19+Vector((0,0,8)),23)]:
 s.camera.location=target+delta;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale
 for stage,hide in [('before',True),('after',False)]:
  for o in new:o.hide_render=hide
  s.render.filepath=str(O/(view+'-'+stage+'.png'));bpy.ops.render.render(write_still=True)
assert all(sig(o)==sigs[o.name] for o in original)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'awning.blend'));bpy.ops.object.select_all(action='DESELECT')
for o in original+new:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'awning.glb'),export_format='GLB',use_selection=True,export_extras=True)
report={'owner':bid,'source':str(src),'source_signatures':sigs,'original_geometry_unchanged':True,'added_objects':[o.name for o in new],'face_edge':0,'origin':list(A),'tangent':list(T),'outward':list(N),'along_interval_m':[s0,s1],'projection_m':1.2,'back_top_z_m':2.975,'front_top_z_m':2.375,'attachment':'Wall rail/plates embedded into existing opaque strip below z3 glazing, not attached to glass. Height and exact placement inferred; no doors modeled.','limitations':['Photo morphology supported; 13.6m length,1.2mprojection,depths and bracket count/construction estimated.','Actual canopy fabric/rigid structure cannot be distinguished; closed thin cover used.','Existing upper wall and glazedbay rhythm mismatch remain unresolved.','No mirrored unseen/copy to another frontage.']};(O/'contract.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(O/'awning.blend'));expected={o.name:([list(v.co)for v in o.data.vertices],o.get('building_id')) for o in bpy.data.objects if o.type=='MESH'};bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'awning.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert set(expected)=={o.name for o in obs};err=0
for o in obs:
 vv,owner=expected[o.name];assert o.get('building_id')==owner
 for ax in range(3):
  for fn in [min,max]:err=max(err,abs(fn(v[ax]for v in vv)-fn((o.matrix_world@v.co)[ax]for v in o.data.vertices)))
assert err<.0001
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'independent_glb_ids_bounds':True,'max_error_m':err,'added_closed_components':14,'source_geometry_unchanged':True},indent=2))
