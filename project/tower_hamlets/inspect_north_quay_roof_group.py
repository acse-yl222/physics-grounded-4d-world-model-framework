"""Shared-boundary graph: mapping partitions are not roof terminations."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((r/'geometry.json').read_text());items={}
for b in g['buildings']:
 if 'height_m' not in b:continue
 p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])
 if p.bounds[0]>-430 and p.bounds[2]<-100 and p.bounds[1]>180 and p.bounds[3]<285:items[b['id']]=(b,p)
seed='overture-building-dbe8f73e-e036-48c5-9059-bb6350356575';seen={seed};edges=[];todo=[seed]
while todo:
 a=todo.pop()
 for b in items:
  if a==b:continue
  length=items[a][1].boundary.intersection(items[b][1].boundary).length
  if length>1:
   if sorted([a,b]) not in [e['ids'] for e in edges]:edges.append({'ids':sorted([a,b]),'shared_boundary_m':length})
   if b not in seen:seen.add(b);todo.append(b)
report={'scope':'Geographic ownership adjacency only, not proof of architectural continuity. Bounded local corridor.','features':[{'id':id,'name':items[id][0].get('name'),'bounds_xy_m':list(items[id][1].bounds)} for id in sorted(seen)],'edges':edges};(r/'references/north_quay_roof_group.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
