from pathlib import Path
import bpy,json
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade_opportunity_audit001';src=P/'runs/canary_wharf_appearance_one_canada_crown_003/region.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=[n for n in a.objects if 'CabotPlace' in n or 'DFBE' in n or 'dfbe' in n]
obs=[]
for o in b.objects:
 if o and o.type=='MESH' and o.get('building_id')=='overture-building-dfbe7e30-b124-490e-88e7-e5cf6154dd27':bpy.context.collection.objects.link(o);obs.append(o)
assert obs
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1400;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=Vector((1,-.2,-1)).to_track_quat('-Z','Y').to_euler();target=Vector((-235,-9,10));bpy.ops.object.camera_add(location=target+Vector((-80,15,8)));s.camera=bpy.context.object;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=58;s.render.filepath=str(O/'current-retained-west-front.png');bpy.ops.render.render(write_still=True);(O/'selected_scene.json').write_text(json.dumps({'source':str(src),'owner':'overture-building-dfbe7e30-b124-490e-88e7-e5cf6154dd27','objects':[o.name for o in obs],'geometry_modified':False,'camera':'Diagnostic west front, not photo calibrated'},indent=2))
