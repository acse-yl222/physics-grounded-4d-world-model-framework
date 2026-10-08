"""Insert existing collinear vertices into face edges; preserve all coordinates."""
from pathlib import Path
from collections import Counter
import json,numpy as np
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';audit=json.loads((R/'references/warehouse_topology_audit.json').read_text());objects=[];reports=[]
for name in dict.fromkeys(q['source'] for q in audit['objects']):
 d=json.loads((R/'references'/f'{name}.json').read_text())
 for q in d['objects']:
  v=np.array(q['vertices']);insertions=0
  for group in ['roof_faces','wall_faces','bottom_faces']:
   revised=[]
   for face in q[group]:
    new=[]
    for a,b in zip(face,face[1:]+face[:1]):
     delta=v[b]-v[a];length2=delta@delta
     assert length2>1e-15
     t=(v-v[a])@delta/length2;dist=np.linalg.norm(v-(v[a]+t[:,None]*delta),axis=1)
     ids=np.where((t>1e-7)&(t<1-1e-7)&(dist<2e-7))[0];ids=sorted(ids,key=lambda i:t[i]);new.extend([a,*map(int,ids)]);insertions+=len(ids)
    revised.append(new)
   q[group]=revised
  faces=q['roof_faces']+q['wall_faces']+q['bottom_faces'];edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]));counts=Counter(edges.values());report={'source':name,'object':q['name'],'inserted_edge_vertices':insertions,'edge_incidence':dict(counts)};reports.append(report)
  assert all(n==2 for n in edges.values()),report
  q['basis']=d['scope'];objects.append(q)
(R/'references/warehouse_junctions_repaired.json').write_text(json.dumps({'objects':objects,'scope':'Existing estimated appearance models with collinear edge junctions connected. Coordinates unchanged. Geographic uncertainties, absent openings and missing high returns remain.'}))
(R/'references/warehouse_junctions_repair_report.json').write_text(json.dumps({'objects':reports,'coordinates_changed':False,'checks':'Every undirected face edge occurs twice. Does not test geometric intersections or real-world accuracy.'},indent=2));print(json.dumps(reports,indent=2))
