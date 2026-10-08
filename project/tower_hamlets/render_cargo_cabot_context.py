from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-cargo-cabot-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));s=bpy.context.scene;s.cycles.samples=24
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
for name,pos,target,scale in [('cargo-context',(-170,360,205),(0,65,40),400),('cabot-context',(-180,-350,200),(-240,-60,45),230)]:
 c=s.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale
 s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
