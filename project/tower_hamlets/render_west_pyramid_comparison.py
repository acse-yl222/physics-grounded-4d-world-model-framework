from pathlib import Path
import bpy,json
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/west_pyramid-massing-002';r=json.loads((R/'references/west_pyramid_study002.json').read_text())
for state in ['before','after']:
 bpy.ops.wm.open_mainfile(filepath=str(O/'west_pyramid.blend'))
 if state=='before':
  for o in list(bpy.data.objects):
   if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
  for q in r['baseline_meshes']:
   m=bpy.data.meshes.new(q['name']);m.from_pydata(q['vertices'],[],q['roof_faces']);m.materials.append(bpy.data.materials['WestPyramid estimated estimated']);ob=bpy.data.objects.new(q['name'],m);bpy.context.collection.objects.link(ob)
 s=bpy.context.scene;s.cycles.samples=32;s.render.filepath=str(O/('comparison-'+state+'.png'));bpy.ops.render.render(write_still=True)
