from pathlib import Path
import bpy
from mathutils import Vector
R=Path('project/tower_hamlets/input/canary_wharf_20261007');O=R/'exports/kpmg15-massing-003'
for n in ['001','002','003']:
 bpy.ops.wm.open_mainfile(filepath=str((R/f'exports/kpmg15-massing-{n}/kpmg15.blend').resolve()));s=bpy.context.scene;t=Vector((154,8.4,73));s.camera.location=t+Vector((-20,-25,30));s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=24;s.render.filepath=str(O/f'central-control-{n}.png');bpy.ops.render.render(write_still=True)
