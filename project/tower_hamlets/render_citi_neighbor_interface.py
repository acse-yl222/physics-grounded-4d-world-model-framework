from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-citi-neighbor-001'
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));s=bpy.context.scene;s.cycles.samples=24
ids={'overture-building-f0aeb767-683f-4d29-8a43-85f4b8faf711','overture-building-12b707fc-a45c-4558-98fc-88e1146fd0ad'}
for o in bpy.data.objects:
 if o.type=='MESH' and o.get('building_id') not in ids:o.hide_render=True
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1)
c=s.camera;c.location=(-130,-270,170);c.rotation_euler=(Vector((10,-135,80))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=170
s.render.resolution_x=1400;s.render.resolution_y=1100;s.render.filepath=str(O/'isolated-shared-roof-review.png');bpy.ops.render.render(write_still=True)
