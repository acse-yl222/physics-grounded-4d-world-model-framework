from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/appearance-twenty-cabot-001'
bpy.ops.wm.open_mainfile(filepath=str(R/'region.blend'))
s=bpy.context.scene
s.cycles.samples=24
c=s.camera
c.location=(-470,-180,240)
c.rotation_euler=(Vector((-260,-85,35))-c.location).to_track_quat('-Z','Y').to_euler()
c.data.type='ORTHO'
c.data.ortho_scale=160
s.render.resolution_x=1600
s.render.resolution_y=1000
# Back orthographic camera beyond all scene bounds without changing framing.
s.view_layers.update()
f=c.rotation_euler.to_quaternion() @ Vector((0,0,-1))
depths=[(o.matrix_world@Vector(v)-c.location).dot(f) for o in s.objects if o.type=='MESH' for v in o.bound_box]
shift=max(0, c.data.clip_start+10-min(depths))
c.location-=f*shift
c.data.clip_end=max(c.data.clip_end,max(depths)+shift+100)
s.render.filepath=str(R/'twenty-cabot-context-corrected.png')
bpy.ops.render.render(write_still=True)
