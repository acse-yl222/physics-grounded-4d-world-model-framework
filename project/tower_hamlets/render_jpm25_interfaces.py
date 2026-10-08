from pathlib import Path
import bpy
from mathutils import Vector
r=Path('/home/yl222/workspace/physics-grounded-4d-world-model-framework/project/tower_hamlets/input/canary_wharf_20261007/exports/appearance-jpm25-001')
bpy.ops.wm.open_mainfile(filepath=str(r/'region.blend'))
s=bpy.context.scene;c=s.camera;t=Vector((-150,-270,65));c.location=t+Vector((-100,-160,360));c.rotation_euler=(t-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=230
f=c.rotation_euler.to_quaternion()@Vector((0,0,-1));ds=[(o.matrix_world@Vector(v)-c.location).dot(f) for o in s.objects if o.type=='MESH' for v in o.bound_box];c.location-=f*max(0,c.data.clip_start+10-min(ds));c.data.clip_end=max(c.data.clip_end,max(ds)+2000)
s.render.resolution_x=1600;s.render.resolution_y=1000;s.cycles.samples=24;s.render.filepath=str(r/'jpm25-interface-context.png');bpy.ops.render.render(write_still=True)
