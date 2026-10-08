from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-george10-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));s=bpy.context.scene;s.cycles.samples=24
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
c=s.camera;c.location=(640,-610,240);c.rotation_euler=(Vector((379,-353,65))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=210
s.render.resolution_x=1400;s.render.resolution_y=1100;s.render.filepath=str(O/'george10-south-context.png');bpy.ops.render.render(write_still=True)
