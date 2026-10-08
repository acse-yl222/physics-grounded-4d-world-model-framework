from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/appearance-water8-park10-study-001'
bpy.ops.wm.open_mainfile(filepath=str(R/'region.blend'))
s=bpy.context.scene;c=s.camera;c.location=(440,-460,520);c.rotation_euler=(Vector((303,-279,76))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=230
f=c.rotation_euler.to_quaternion()@Vector((0,0,-1));ds=[(o.matrix_world@Vector(v)-c.location).dot(f) for o in s.objects if o.type=='MESH' for v in o.bound_box];shift=max(0,c.data.clip_start+10-min(ds));c.location-=f*shift;c.data.clip_end=max(c.data.clip_end,max(ds)+shift+100)
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;s.cycles.samples=24;s.render.resolution_x=1600;s.render.resolution_y=1200;s.render.filepath=str(R/'water8-park10-roof-context.png');bpy.ops.render.render(write_still=True)
