"""Estimated low envelope only; unresolved high returns remain in source evidence."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/ledger_plane_fit.json').read_text());g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']==r['building_id']);verts=[];roof=[];walls=[];bottom=[];lookup={};area=0
c,a,b=r['plane_coefficients_odn_m'];cx,cy=r['plane_center_xy_m']
def height(x,y):return c+a*(x-cx)+b*(y-cy)-r['datum_odn_m']
def idx(p):
 key=tuple(round(float(q),8) for q in p)
 if key not in lookup:lookup[key]=len(verts);verts.append(list(key))
 return lookup[key]
for part in f['geometry']:
 p=Polygon(part['outer'],part.get('holes',[]));area+=p.area
 for t in constrained_delaunay_triangles(p).geoms:
  xy=list(t.exterior.coords)[:-1];roof.append([idx([x,y,height(x,y)]) for x,y in xy]);bottom.append([idx([x,y,0]) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  xy=list(ring.coords)
  for (x,y),(xx,yy) in zip(xy,xy[1:]):walls.append([idx([x,y,0]),idx([xx,yy,0]),idx([xx,yy,height(xx,yy)]),idx([x,y,height(x,y)])])
row=dict(name='Ledger',building_id=f['id'],vertices=verts,roof_faces=roof,wall_faces=walls,bottom_faces=bottom,area_m2=area)
(R/'references/ledger_exterior_hypothesis.json').write_text(json.dumps({'objects':[row],'scope':'Estimated low envelope only: conditional low plane extrapolated to mapped footprint, walls and palette estimated. Five multi-cell high-return groups plus isolated return are unresolved and excluded from this appearance shell; retained separately in source evidence. Not complete roof reconstruction.'}))
print(area)
