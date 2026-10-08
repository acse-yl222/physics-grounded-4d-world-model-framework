from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());rows=[]
def prism(poly,lo,hi,name,kind,owner):
 verts=[];faces=[];idx={}
 def vi(x,y,z):
  k=(round(x,7),round(y,7),round(z,7))
  if k not in idx:idx[k]=len(verts);verts.append(list(k))
  return idx[k]
 for p in [poly] if poly.geom_type=='Polygon' else poly.geoms:
  for t in constrained_delaunay_triangles(p).geoms:
   xy=list(t.exterior.coords)[:-1];faces.append([vi(x,y,hi) for x,y in xy]);faces.append([vi(x,y,lo) for x,y in reversed(xy)])
  for ring in [p.exterior,*p.interiors]:
   xy=list(ring.coords)
   for (x,y),(a,b) in zip(xy,xy[1:]):faces.append([vi(x,y,lo),vi(a,b,lo),vi(a,b,hi),vi(x,y,hi)])
 rows.append(dict(name=name,kind=kind,building_id=owner,vertices=verts,roof_faces=faces,wall_faces=[],bottom_faces=[]))
for id,height,floors,label in [('overture-building-c1aa1eca-62fe-49cc-86ac-ca2f06d625ec',170,50,'West'),('overture-building-926104a9-6e3c-4c0e-847e-4ce89ca1005e',183,55,'East')]:
 f=next(q for q in g['buildings'] if q['id']==id);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);core=p.buffer(-1.5,join_style=2);prism(core,0,height-.28,label+'_recessed_envelope','glass',id)
 band=p.difference(p.buffer(-.20,join_style=2));rail=p.buffer(-.22,join_style=2).difference(p.buffer(-.28,join_style=2))
 for floor in range(1,floors):
  z=height*floor/floors;prism(p,z-.22,z,label+f'_balcony_slab_{floor:02}','stone',id);prism(rail,z,z+1.1,label+f'_glass_guard_{floor:02}','glass',id)
 prism(p,height-.28,height,label+'_roof_slab','stone',id)
(R/'references/wardian_study.json').write_text(json.dumps({'objects':rows,'scope':'Estimated architectural study. Mapped footprints treated as balcony outer envelope;1.5m uniform recess,0.22m slabs,1.1m guards and evenly spaced levels are artistic assumptions. Contractor170/183m heights adopted for study, height convention unresolved.50/55 levels and wrap-around balconies supported by primary text. Glazing is simplified continuous envelope; no verified openings, podium or penthouse.'}));print(len(rows))
