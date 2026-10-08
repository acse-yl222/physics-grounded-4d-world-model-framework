"""Move inspection camera into unobstructed dock space; never move scene geometry."""
from pathlib import Path
import bpy
from mathutils import Vector
R = Path(__file__).resolve().parent/'input/canary_wharf_20261007'
O = R/'exports/appearance-crossrail-cargo-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'))
s = bpy.context.scene
s.cycles.samples = 32
s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.68,.75,.83,1)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
cam = s.camera
cam.location = (-98,143,25)
target = Vector((-54,113,17))
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'PERSP'
cam.data.lens = 25
s.render.resolution_x = 1600
s.render.resolution_y = 1000
s.render.filepath = str(O/'west-terminal-context.png')
bpy.ops.render.render(write_still=True)
