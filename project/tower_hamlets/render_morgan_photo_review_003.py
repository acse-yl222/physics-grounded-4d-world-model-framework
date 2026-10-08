from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/morgan-photo-study-003';r=json.loads((R/'references/morgan_photo_study_003.json').read_text());vs=[v for q in r['objects'] for v in q['vertices']];cx=(min(v[0] for v in vs)+max(v[0] for v in vs))/2;cy=(min(v[1] for v in vs)+max(v[1] for v in vs))/2
for version,path in [('before',R/'exports/morgan-massing-study-002/morgan.blend'),('after',O/'morgan.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
 for name,z,off,scale in [('front',48,(-240,60,15),140),('detail',70,(-200,45,5),65)]:
  t=Vector((cx,cy,z));s.camera.location=t+Vector(off);s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+version+'.png'));bpy.ops.render.render(write_still=True)
