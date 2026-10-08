"""Applied small bevels and explicit estimated metal finish; preserves001."""
from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';I=R/'exports/wardian-facade-study-001';O=R/'exports/wardian-facade-study-002';O.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(I/'wardian.blend'));obs=[o for o in bpy.data.objects if o.type=='MESH'];expected={}
for ob in obs:
 bpy.context.view_layer.objects.active=ob
 kind=next(k for k in ['stone','metal','cladding','backing','glass','guard'] if '_'+k+'_' in ob.name)
 m=ob.data.materials[0];bs=m.node_tree.nodes['Principled BSDF']
 if kind=='metal':bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.28
 if kind=='cladding':bs.inputs['Metallic'].default_value=.35;bs.inputs['Roughness'].default_value=.4
 if kind=='stone':bs.inputs['Roughness'].default_value=.65
 if kind in ['metal','stone']:
  mod=ob.modifiers.new('Applied estimated micro bevel','BEVEL');mod.width=.005 if kind=='metal' else .01;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.523599;mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.calc_loop_triangles();vs=[tuple(ob.matrix_world@v.co) for v in ob.data.vertices];expected[ob.name]={'building_id':ob['building_id'],'triangles':len(ob.data.loop_triangles),'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'material':m.name,'metallic':bs.inputs['Metallic'].default_value,'roughness':bs.inputs['Roughness'].default_value};assert len(ob.modifiers)==0
s=bpy.context.scene;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
for ob in bpy.data.objects:
 if ob.type=='LIGHT':ob.data.energy=1.5;ob.data.angle=.12;ob.rotation_euler=(.55,-.4,-.65)
s.cycles.samples=64;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=1100
allv=[ob.matrix_world@v.co for ob in obs for v in ob.data.vertices];target=Vector(tuple((min(v[i] for v in allv)+max(v[i] for v in allv))/2 for i in range(3)))
bpy.ops.object.light_add(type='AREA',location=target+Vector((-80,-150,70)));fill=bpy.context.object;fill.name='Review soft fill';fill.data.energy=90000;fill.data.shape='DISK';fill.data.size=100;fill.rotation_euler=(target-fill.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'wardian.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in obs:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'wardian.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
west=[ob.matrix_world@v.co for ob in obs if 'West' in ob.name for v in ob.data.vertices];cx=(min(v.x for v in west)+max(v.x for v in west))/2;cy=(min(v.y for v in west)+max(v.y for v in west))/2
target=Vector((cx,cy,90));s.camera.location=target+Vector((-65,-90,25));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=38;s.render.filepath=str(O/'detail.png');bpy.ops.render.render(write_still=True)
corner=min(west,key=lambda v:v.x+v.y);target=Vector((corner.x+1,corner.y+1,90));s.camera.location=target+Vector((-40,-55,14));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=12;s.render.filepath=str(O/'corner.png');bpy.ops.render.render(write_still=True)
(O/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
