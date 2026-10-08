"""Test whether mapped museum edge is shared with adjacent building polygons."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((r/'geometry.json').read_text());fit=json.loads((r/'references/museum_roof_fit.json').read_text());ids=[fit['building_id'],fit['child_id']]
def poly(b):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])
p=unary_union([poly(b) for b in g['buildings'] if b['id'] in ids]);rows=[]
for b in g['buildings']:
 if b['id'] in ids or 'height_m' not in b:continue
 q=poly(b);distance=p.distance(q)
 if distance<1:
  rows.append({'id':b['id'],'name':b.get('name'),'distance_m':distance,'shared_boundary_length_m':p.boundary.intersection(q.boundary).length,'overlap_m2':p.intersection(q).area,'bounds_xy_m':list(q.bounds),'current_height_m':b['height_m']})
(r/'references/museum_neighbors.json').write_text(json.dumps({'neighbors':rows,'scope':'Geometric adjacency only; no inference that separately mapped features are physically separate roofs.'},indent=2)+'\n');print(rows)
