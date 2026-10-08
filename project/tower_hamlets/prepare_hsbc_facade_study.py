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
from shapely.geometry import Point
features=[f for f in g['buildings'] if f.get('parent_id')=='44d6fcce-172b-4d76-a1c9-013d90c0a0fa'];main=next(f for f in features if f['height_m']==186.3);alias='overture-building-e96252ed-33f8-446c-a5f0-debd8627db8e'
for i,f in enumerate(features):
 p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);kind='backing' if f==main else 'metal';prism(p,f['min_height_m'],f['height_m'],'HSBC_part_'+str(i),kind,f['id'])
 if f!=main:continue
 pts=list(p.exterior.coords)
 for edge,(a,b) in enumerate(zip(pts,pts[1:])):
  dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);dx/=length;dy/=length;nx,ny=-dy,dx
  if not p.contains(Point((a[0]+b[0])/2+nx*.02,(a[1]+b[1])/2+ny*.02)):nx,ny=-nx,-ny
  def strip(t0,t1,depth0,depth1):return Polygon([(a[0]+dx*t+nx*d,a[1]+dy*t+ny*d) for t,d in [(t0,depth0),(t1,depth0),(t1,depth1),(t0,depth1)]])
  n=max(1,round(length/1.5));fh=186.3/42
  for j in range(n):
   t0=length*j/n;t1=length*(j+1)/n
   prism(strip(t0+.035,t1-.035,-.035,-.005),.05,186.25,'HSBC_glass','glass',main['id'])
   prism(strip(t0,min(t0+.06,t1),-.09,.005),0,186.3,'HSBC_mullion','frame',main['id'])
  for k in range(42):
   z=k*fh;prism(strip(0,length,-.06,-.001),z,min(z+.78,186.3),'HSBC_spandrel','spandrel',main['id'])
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name='HSBC_'+q['building_id'].split('-')[-1]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+off for i in face] for face in q['roof_faces']]
for q in merged.values():
 if q['building_id']==main['id']:q['aggregate_alias_id']=alias
r={'objects':list(merged.values()),'scope':'HSBC mapped7part envelope preserved, named duplicate aggregate excluded and recorded as alias. Main0–186.3 facade uses42estimated equal bands(source42floors), primary45storeys includesroof/plant convention unresolved. Four mapped186.3–199.5 metalparts retained without invented halo outline. Glass/spandrel/mullion rhythm/materials and depths estimated; no logo,podium or entrance inferred.','removed_duplicate_aggregate_id':alias,'kept_neighbor_parent_id':'overture-building-44d6fcce-172b-4d76-a1c9-013d90c0a0fa'}
(R/'references/hsbc_facade_study.json').write_text(json.dumps(r,indent=2)+'\n');print(len(merged))
