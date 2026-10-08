"""Audit authored exterior topology; does not certify geographic accuracy."""
from pathlib import Path
from collections import Counter
import json
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';rows=[]
for name in ['museum_exterior_hip_hypothesis','east_exterior_hypothesis','port_east_exterior_hypothesis','munich_exterior_hypothesis','pizza_exterior_hypothesis','ledger_exterior_hypothesis']:
 data=json.loads((R/'references'/f'{name}.json').read_text())
 for q in data['objects']:
  faces=q['roof_faces']+q['wall_faces']+q['bottom_faces'];edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]));duplicate=len(faces)-len({tuple(sorted(f)) for f in faces});rows.append({'source':name,'object':q['name'],'vertices':len(q['vertices']),'faces':len(faces),'boundary_edges':sum(n==1 for n in edges.values()),'overused_edges':sum(n>2 for n in edges.values()),'duplicate_faces':duplicate})
out=R/'references/warehouse_topology_audit.json';out.write_text(json.dumps({'objects':rows,'scope':'Index topology of authored JSON meshes; no geometric self-intersection or accuracy certification.'},indent=2));print(json.dumps(rows,indent=2))
