from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/newfoundland-black-patch-diagnostic-001';O.mkdir(exist_ok=True);src=R/'exports/appearance-cabot-place-west-001/region.blend';bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene;c=s.camera;c.location=(-410,-180,210);c.rotation_euler=(Vector((-200,-15,20))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=190;s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=50;s.cycles.samples=12;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
ids=[];depths=[];forward=c.rotation_euler.to_quaternion()@Vector((0,0,-1));materials={}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 keep=o.get('building_id')=='overture-building-b0939932-881e-4c5c-8797-8a0a91c38f5c';o.hide_render=not keep
 if not keep:continue
 dd=[((o.matrix_world@v.co)-c.location).dot(forward) for v in o.data.vertices];depths+=dd;ids.append(dict(name=o.name,depth_min=min(dd),depth_max=max(dd),vertices=len(o.data.vertices),polygons=len(o.data.polygons)))
 for m in o.data.materials:
  if m:materials[m.name]=dict(diffuse=list(m.diffuse_color),nodes=[dict(name=n.name,type=n.type) for n in m.node_tree.nodes] if m.use_nodes else [])
r=dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),camera_location=list(c.location),forward=list(forward),clip_start=c.data.clip_start,clip_end=c.data.clip_end,type=c.data.type,ortho_scale=c.data.ortho_scale,objects=ids,depth_range=[min(depths),max(depths)],materials=materials,tests=[])
base=c.location.copy();near=c.data.clip_start
for label,newnear,back in [('baseline',near,0),('near_0001',.001,0),('back_300',near,300)]:
 c.location=base-forward*back;c.data.clip_start=newnear;s.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True);r['tests'].append(dict(label=label,clip_start=newnear,translation_backward_m=back,location=list(c.location)))
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
