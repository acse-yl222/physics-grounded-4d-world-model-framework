import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/owner87aa-massing-001';bpy.ops.wm.open_mainfile(filepath=str(O/'owner87aa.blend'));rows=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 ob.data.calc_loop_triangles()
 for t in ob.data.loop_triangles:
  vv=[list(ob.matrix_world@ob.data.vertices[i].co) for i in t.vertices];rows.append({'object':ob.name,'vertices':vv})
(R/'references/owner87aa_final_triangles.json').write_text(json.dumps(rows))
