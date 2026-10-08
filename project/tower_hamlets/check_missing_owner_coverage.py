from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/inventory-alias-diagnostic-001';r=json.loads((O/'native_diagnostic.json').read_text());tri=json.loads((O/'projected_triangles.json').read_text());g=json.loads((R/'geometry.json').read_text());out={}
for group,owner in [('carpark','e79bdc61'),('museum','97b6bbeb')]:
 b=next(q for q in g['buildings'] if owner in q['id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);old=r[group+'_original']['objects'];cur=[q for q in r['current']['objects'] if q['properties'].get('building_id')==('overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c' if group=='carpark' else 'overture-building-dbe8f73e-e036-48c5-9059-bb6350356575')];oldhash={q['geometry_sha256']:q for q in old};comparison=[dict(current=q['name'],exact_original_geometry_match=q['geometry_sha256'] in oldhash,original=oldhash.get(q['geometry_sha256'],{}).get('name')) for q in cur];polys=[];per=[]
 for q in tri['current']:
  if q['group']!=group:continue
  ps=[Polygon(t) for t in q['triangles_xy']];pp=unary_union([p for p in ps if p.area>1e-10]);polys.append(pp);per.append(dict(name=q['name'],owner_footprint_intersection_m2=pp.intersection(p).area,mesh_projected_area_m2=pp.area))
 union=unary_union(polys);out[group]=dict(missing_owner=b['id'],original_mesh_count=len(old),current_mesh_count=len(cur),all_current_geometry_exact_original=all(q['exact_original_geometry_match'] for q in comparison),original_geometry_hashes_missing=[q['name'] for q in old if q['geometry_sha256'] not in {c['geometry_sha256'] for c in cur}],comparison=comparison,owner_area_m2=p.area,projected_geometry_covered_m2=union.intersection(p).area,uncovered_m2=p.difference(union).area,covered_fraction=union.intersection(p).area/p.area,per_mesh_coverage=sorted(per,key=lambda a:-a['owner_footprint_intersection_m2']),custom_property_keys=sorted({k for q in cur for k in q['properties']}))
(O/'coverage_report.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:{a:b for a,b in v.items() if a not in ['comparison','per_mesh_coverage']} for k,v in out.items()},indent=2));print('BEST', {k:v['per_mesh_coverage'][:5] for k,v in out.items()})
