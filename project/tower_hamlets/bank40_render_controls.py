from pathlib import Path
import bpy
from mathutils import Vector
R=Path('project/tower_hamlets/input/canary_wharf_20261007');O=R/'exports/bank40-massing-002'
for n in ['001','002']:
 bpy.ops.wm.open_mainfile(filepath=str((R/f'exports/bank40-massing-{n}/bank40.blend').resolve()));s=bpy.context.scene;t=Vector((-49,-305,157));s.camera.location=t+Vector((-30,-40,50));s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=48;s.render.filepath=str(O/f'roof-control-{n}.png');bpy.ops.render.render(write_still=True)
