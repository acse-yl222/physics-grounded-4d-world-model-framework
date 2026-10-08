from pathlib import Path
import bpy,json
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_seam-comparison-001';O.mkdir(exist_ok=True);src=P/'runs/canary_wharf_appearance_owner87aa_001/region.blend';bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src),link=False) as (a,b):
 names=[n for n in a.objects if any(k in n.lower() for k in ['ground','water','site'])];b.objects=names
out=[]
for o in b.objects:
 if o and o.type=='MESH':
  vv=[o.matrix_world@v.co for v in o.data.vertices];o.data.calc_loop_triangles();out.append({'name':o.name,'props':{k:str(o[k]) for k in o.keys()},'vertices':len(vv),'faces':len(o.data.polygons),'triangles':len(o.data.loop_triangles),'bounds':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'mesh_vertices':[list(v) for v in vv],'mesh_triangles':[list(t.vertices) for t in o.data.loop_triangles]})
(O/'fff_seam-site-topology.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in q.items() if not k.startswith('mesh_')} for q in out])
