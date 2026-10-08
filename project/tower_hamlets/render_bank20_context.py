from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/appearance-bank20-001'
bpy.ops.wm.open_mainfile(filepath=str(R/'region.blend'))
s=bpy.context.scene
s.cycles.samples=24
c=s.camera
c.location=(-470,-490,230)
c.rotation_euler=(Vector((-230,-260,40))-c.location).to_track_quat('-Z','Y').to_euler()
c.data.type='ORTHO'
c.data.ortho_scale=220
s.render.resolution_x=1600
s.render.resolution_y=1000
s.render.filepath=str(R/'bank20-context-corrected.png')
bpy.ops.render.render(write_still=True)
