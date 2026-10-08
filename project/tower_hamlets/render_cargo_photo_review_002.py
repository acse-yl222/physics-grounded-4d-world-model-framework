from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/cargo-photo-study-002';r=json.loads((R/'references/cargo_photo_study_002.json').read_text())
for state in ['before','after']:
 bpy.ops.wm.open_mainfile(filepath=str(O/'cargo.blend'))
 if state=='before':
  for ob in list(bpy.data.objects):
   if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
  q=r['baseline_mesh'];me=bpy.data.meshes.new('mapped_baseline');me.from_pydata(q['vertices'],[],q['faces']);me.update();me.materials.append(bpy.data.materials['Cargo estimated stone']);ob=bpy.data.objects.new('Cargo_mapped_baseline',me);bpy.context.collection.objects.link(ob)
 s=bpy.context.scene
 for name,t,off,scale in [('front',(-87,56,40),(15,170,15),105),('detail',(-74,67,52),(0,130,5),48)]:
  t=Vector(t);s.camera.location=t+Vector(off);s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+state+'.png'));bpy.ops.render.render(write_still=True)
