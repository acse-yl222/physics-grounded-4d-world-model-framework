from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/barclays-western-massing-001';r=json.loads((R/'references/barclays_podium_study.json').read_text())
for state in ['before','after']:
 bpy.ops.wm.open_mainfile(filepath=str(O/'barclays_western.blend'))
 if state=='before':
  for ob in list(bpy.data.objects):
   if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
  q=r['baseline_mesh'];me=bpy.data.meshes.new('baseline30m');me.from_pydata(q['vertices'],[],q['roof_faces']);me.update();me.materials.append(bpy.data.materials['BarclaysWestern estimated estimated']);ob=bpy.data.objects.new('baseline30m',me);bpy.context.collection.objects.link(ob)
 s=bpy.context.scene
 for name,t,off,scale in [('front',(-207,64,36),(-90,-180,15),155),('roof',(-207,64,50),(0,0,200),150)]:
  t=Vector(t);s.camera.location=t+Vector(off);s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+state+'.png'));bpy.ops.render.render(write_still=True)
