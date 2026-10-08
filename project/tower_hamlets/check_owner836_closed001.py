import bpy,bmesh,json
from pathlib import Path
R=Path('project/tower_hamlets/input/canary_wharf_20261007');O=R/'exports/owner836-roof-study-001';bpy.ops.wm.open_mainfile(filepath=str(O.resolve()/'owner836.blend'));rows=[]
for o in bpy.data.objects:
 if o.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(o.data);rows.append({'object':o.name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_m3':abs(bm.calc_volume())});bm.free()
assert all(r['nonmanifold_edges']==0 and r['volume_m3']>0 for r in rows)
p=O/'review.json';d=json.loads(p.read_text());d['closed_mesh_checks']=rows;p.write_text(json.dumps(d,indent=2));print(rows)
