from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
O=R/'exports/appearance-western-facades-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'))
s=bpy.context.scene;s.cycles.samples=24
cam=s.camera;cam.location=(-640,210,290);cam.rotation_euler=(Vector((-360,0,45))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=370
s.render.resolution_x=1600;s.render.resolution_y=1100;s.render.filepath=str(O/'northwest-context.png')
bpy.ops.render.render(write_still=True)
