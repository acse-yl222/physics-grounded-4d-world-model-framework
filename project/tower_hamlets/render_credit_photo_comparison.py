from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/credit-photo-study-001'
for version,asset in [('before',R/'exports/credit-envelope-study-002/credit.blend'),('after',O/'credit.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(asset));s=bpy.context.scene;v=[ob.matrix_world@v.co for ob in bpy.data.objects if ob.type=='MESH' for v in ob.data.vertices];cx=(min(a.x for a in v)+max(a.x for a in v))/2;cy=(min(a.y for a in v)+max(a.y for a in v))/2
 for name,z,scale in [('fullheight',48,190),('comparison',70,55),('roof',90,100)]:
  t=Vector((cx,cy,z));s.camera.location=t+Vector((-130,-180,60));s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+version+'.png'));bpy.ops.render.render(write_still=True)
