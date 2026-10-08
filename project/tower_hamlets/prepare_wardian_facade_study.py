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
import math
from shapely.geometry import LineString
for id,height,floors,label in [('overture-building-c1aa1eca-62fe-49cc-86ac-ca2f06d625ec',170,50,'West'),('overture-building-926104a9-6e3c-4c0e-847e-4ce89ca1005e',183,55,'East')]:
 f=next(q for q in g['buildings'] if q['id']==id);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);core=p.buffer(-1.5,join_style=2)
 prism(core.buffer(-.16,join_style=2),0,height-.30,label+'_dark_backing','backing',id)
 glassring=core.difference(core.buffer(-.045,join_style=2));prism(glassring,.15,height-.30,label+'_recessed_glass','glass',id)
 guard=p.buffer(-.22,join_style=2).difference(p.buffer(-.25,join_style=2));rail=p.buffer(-.19,join_style=2).difference(p.buffer(-.27,join_style=2))
 frame=core.buffer(.045,join_style=2).difference(core.buffer(-.045,join_style=2))
 for floor in range(1,floors):
  z=height*floor/floors;prism(p,z-.22,z,label+'_slab','stone',id);prism(guard,z+.06,z+1.06,label+'_guard','guard',id);prism(rail,z+1.06,z+1.11,label+'_rail','metal',id);prism(frame,z+.03,z+.14,label+'_transom','metal',id)
 prism(p,height-.28,height,label+'_roof','stone',id)
 # Estimated bay spacing on each mapped edge, no individual apartment inference.
 for ring,spacing,width,kind in [(core.exterior,1.65,.065,'mullion'),(p.buffer(-.23,join_style=2).exterior,2.4,.045,'post')]:
  coords=list(ring.coords)
  for a,b in zip(coords,coords[1:]):
   length=math.dist(a,b);n=max(1,round(length/spacing));dx=(b[0]-a[0])/length;dy=(b[1]-a[1])/length
   for j in range(n):
    x=a[0]+(b[0]-a[0])*j/n;y=a[1]+(b[1]-a[1])*j/n
    rect=Polygon([(x-dx*width/2-dy*width/2,y-dy*width/2+dx*width/2),(x+dx*width/2-dy*width/2,y+dy*width/2+dx*width/2),(x+dx*width/2+dy*width/2,y+dy*width/2-dx*width/2),(x-dx*width/2+dy*width/2,y-dy*width/2-dx*width/2)])
    if kind=='mullion':
     #55% nominal opaque span per estimated bay, translated outward from glass.
     span=length/n*.55;cx=x+dx*span/2;cy=y+dy*span/2;dep=.10
     panel=Polygon([(cx-dx*span/2-dy*dep/2,cy-dy*span/2+dx*dep/2),(cx+dx*span/2-dy*dep/2,cy+dy*span/2+dx*dep/2),(cx+dx*span/2+dy*dep/2,cy+dy*span/2-dx*dep/2),(cx-dx*span/2+dy*dep/2,cy-dy*span/2-dx*dep/2)])
     prism(panel,.15,height-.30,label+'_opaque_cladding','cladding',id)
    if kind=='mullion':prism(rect,.15,height-.3,label+'_mullions','metal',id)
    else:
     for floor in range(1,floors):
      z=height*floor/floors;prism(rect,z+.03,z+1.11,label+'_posts','metal',id)
# Combine disconnected pieces by tower/material. Editable geometry remains explicit.
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name=q['name'].split('_')[0]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));offset=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+offset for i in face] for face in q['roof_faces']]
(R/'references/wardian_facade_study.json').write_text(json.dumps({'objects':list(merged.values()),'scope':'Architectural appearance hypothesis. Source text supports50/55floors,170/183m study heights,wrap-around balconies and glazed guards. Mapped footprint balcony envelope,1.5m recess,even floor spacing,1.65m window bays,2.4m guard post spacing and nominal55%opaque aluminum/45%glazed bay arrangement and all frames/materials artistically estimated; no verified entrances,podium or apartment layout. Separated glass and dark backing avoid coincident envelope layers.'}));print(len(merged))
