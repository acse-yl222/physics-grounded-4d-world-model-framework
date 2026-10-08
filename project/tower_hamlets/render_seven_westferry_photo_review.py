from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/seven-westferry-photo-study-001';cur=json.loads((R/'references/seven_westferry_current_mesh.json').read_text())[0]
for state in ['before','after']:
 bpy.ops.wm.open_mainfile(filepath=str(O/'seven_westferry.blend'))
 if state=='before':
  for ob in list(bpy.data.objects):
   if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
  me=bpy.data.meshes.new('original_authored_roof');me.from_pydata(cur['vertices'],[],cur['faces']);me.update();me.materials.append(bpy.data.materials['SevenWestferry estimated stone']);ob=bpy.data.objects.new('original_author_mesh',me);bpy.context.collection.objects.link(ob)
 s=bpy.context.scene;s.cycles.samples=96
 for name,t,off,scale in [('front',(-495,118,28),(-180,-160,15),115),('detail',(-502,103,33),(-100,-140,3),55),('roof',(-495,125,30),(0,0,200),120)]:
  t=Vector(t);s.camera.location=t+Vector(off);s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+state+'.png'));bpy.ops.render.render(write_still=True)
