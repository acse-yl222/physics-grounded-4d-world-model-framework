"""Neutral daylight review of authored model; no image generation or photographic textures."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/wardian-facade-study-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'wardian.blend'));s=bpy.context.scene
world=s.world;nodes=world.node_tree.nodes;bg=nodes['Background'];bg.inputs['Color'].default_value=(.68,.75,.83,1);bg.inputs['Strength'].default_value=.8
for o in bpy.data.objects:
 if o.type=='LIGHT':o.data.energy=1.5;o.data.angle=.12;o.rotation_euler=(.55,-.4,-.65)
s.cycles.samples=64;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=1100
obs=[o for o in bpy.data.objects if o.type=='MESH'];allv=[o.matrix_world@v.co for o in obs for v in o.data.vertices];target=Vector(tuple((min(v[i] for v in allv)+max(v[i] for v in allv))/2 for i in range(3)))
bpy.ops.object.light_add(type='AREA',location=target+Vector((-80,-150,70)));fill=bpy.context.object;fill.name='Review soft fill';fill.data.energy=90000;fill.data.shape='DISK';fill.data.size=100;fill.rotation_euler=(target-fill.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(O/'daylight-overview.png');bpy.ops.render.render(write_still=True)
west=[o.matrix_world@v.co for o in obs if 'West' in o.name for v in o.data.vertices];cx=(min(v.x for v in west)+max(v.x for v in west))/2;cy=(min(v.y for v in west)+max(v.y for v in west))/2
target=Vector((cx,cy,90));s.camera.location=target+Vector((-65,-90,25));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=38;s.render.filepath=str(O/'daylight-detail.png');bpy.ops.render.render(write_still=True)
