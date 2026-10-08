from pathlib import Path
import bpy
from mathutils import Vector
p=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/refinement-015'
bpy.ops.wm.open_mainfile(filepath=str(p/'region.blend'));s=bpy.context.scene;c=s.camera;t=Vector((-295,290,17));c.location=t+Vector((-60,-150,170));c.rotation_euler=(t-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=260;s.render.resolution_x=1000;s.render.resolution_y=1000;s.cycles.samples=32;s.render.filepath=str(p/'carpark-north-quay-context.png');bpy.ops.render.render(write_still=True)
