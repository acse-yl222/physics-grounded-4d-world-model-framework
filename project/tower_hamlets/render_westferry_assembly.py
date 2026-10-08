"""Inspect Westferry stepped roof in unchanged regional context."""
from pathlib import Path
import bpy
from mathutils import Vector
p=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/refinement-011';bpy.ops.wm.open_mainfile(filepath=str(p/'region.blend'));s=bpy.context.scene;c=s.camera;t=Vector((-500,125,25));s.render.resolution_x=1200;s.render.resolution_y=1000;s.cycles.samples=32
for label,offset in [('west',(-140,-60,100)),('roof',(-20,-20,220)),('north',(-70,140,110))]:
 c.location=t+Vector(offset);c.rotation_euler=(t-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=145;s.render.filepath=str(p/('westferry-'+label+'.png'));bpy.ops.render.render(write_still=True)
