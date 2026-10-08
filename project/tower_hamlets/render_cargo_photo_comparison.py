from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/cargo-photo-study-001';r=json.loads((R/'references/cargo_photo_study.json').read_text());q=r['baseline_object'];vs=q['vertices'];cx=(min(v[0] for v in vs)+max(v[0] for v in vs))/2;cy=(min(v[1] for v in vs)+max(v[1] for v in vs))/2
for version in ['before','after']:
 bpy.ops.wm.open_mainfile(filepath=str(O/'cargo.blend'));s=bpy.context.scene
 if version=='before':
  for ob in list(bpy.data.objects):
   if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
  me=bpy.data.meshes.new('Mapped mass');me.from_pydata(q['vertices'],[],q['roof_faces']);me.materials.append(bpy.data.materials['Estimated Cargo backing']);ob=bpy.data.objects.new('Mapped mass',me);bpy.context.collection.objects.link(ob)
 for name,z,scale in [('fullheight',40,150),('upper',72,95),('detail',64,38)]:
  t=Vector((cx,cy,z));s.camera.location=t+Vector((-110,120,-65) if name=='upper' else (-160,190,-30));s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'-'+version+'.png'));bpy.ops.render.render(write_still=True)
