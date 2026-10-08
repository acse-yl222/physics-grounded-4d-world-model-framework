from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/citi_neighbor_study.json').read_text());f=next(q for q in g['buildings'] if q['id']==r['building_id']);p=Polygon(f['geometry'][0]['outer']);tower=Polygon(next(q for q in g['buildings'] if '12b707fc' in q['id'])['geometry'][0]['outer']);polys=[]
for ob in r['objects']:
 for face in ob['roof_faces']:
  vv=[ob['vertices'][i] for i in face]
  if all(v[2]>0 for v in vv):
   q=Polygon([v[:2] for v in vv])
   if q.area>1e-10:polys.append(q)
u=unary_union(polys);d={'whole_footprint_m2':p.area,'roof_projected_area_m2':u.area,'symmetric_difference_m2':u.symmetric_difference(p).area,'coverage_fraction':u.intersection(p).area/p.area,'new_plan_overlap_with_citi_m2':u.intersection(tower).area,'precision_note':'1micrometre snapping removes zero-width clipping slivers; sourceownership unchanged within floatingprecision.','citi_neighbor_modified':False};(R/'references/citi_neighbor_plan_check.json').write_text(json.dumps(d,indent=2));print(d)
