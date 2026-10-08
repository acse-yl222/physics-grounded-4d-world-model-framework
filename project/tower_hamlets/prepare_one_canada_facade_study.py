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
from shapely.geometry import Point
import math
features=[a for a in g['buildings'] if a.get('name')=='One Canada Square'];roof=next(a for a in features if a['height_m']==235);central=next(a for a in features if a['height_m']==210);bodies=[a for a in features if a!=roof]
def poly(a):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in a['geometry']])
union=unary_union([poly(a) for a in bodies]);cp=poly(central);ownership=[]
for i,f in enumerate(bodies):prism(poly(f),0,f['height_m'],'Canada_body_'+str(i),'backing',f['id'])
for level,(domain,lo,hi) in enumerate([(union,0,194),(cp,194,210)]):
 for component in getattr(domain,'geoms',[domain]):
  pts=list(component.exterior.coords)
  for edge,(a,b) in enumerate(zip(pts,pts[1:])):
   dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
   if length<.01:continue
   dx/=length;dy/=length;nx,ny=-dy,dx;mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
   if not domain.contains(Point(mid.x+nx*.02,mid.y+ny*.02)):nx,ny=-nx,-ny
   candidates=[f for f in bodies if poly(f).boundary.distance(mid)<1e-6];owner=candidates[0]['id'] if len(candidates)==1 else central['id'];ownership.append({'tier':[lo,hi],'edge':[a,b],'owner':owner,'ambiguous':len(candidates)!=1,'candidates':[q['id'] for q in candidates]})
   def strip(start,end,inset,depth):
    return Polygon([(a[0]+dx*t+nx*d,a[1]+dy*t+ny*d) for t,d in [(start,inset),(end,inset),(end,inset+depth),(start,inset+depth)]])
   n=max(1,round(length/2));nf=max(1,round((hi-lo)/4));fh=(hi-lo)/nf
   for j in range(n):
    t0=length*j/n;t1=length*(j+1)/n
    if t1-t0<.2:continue
    # Recessed glazing behind actual steel frame surfaces.
    prism(strip(t0+.10,t1-.10,-.03,.035),lo+.08,hi-.08,'Canada_glass','glass',owner)
    prism(strip(t0,min(t0+.15,t1),-.12,.13),lo,hi,'Canada_mullion','steel',owner)
   for k in range(nf+1):
    z=lo+k*fh
    prism(strip(0,length,-.12,.13),max(lo,z-.13),min(hi,z+.13),'Canada_transom','steel',owner)
# Preserve roof-only mapped pyramid exactly; base210 apex235.
ring=list(poly(roof).exterior.coords)[:-1];cx=sum(a[0] for a in ring)/len(ring);cy=sum(a[1] for a in ring)/len(ring);n=len(ring);rows.append({'name':'Canada_pyramid','kind':'steel','building_id':roof['id'],'vertices':[[x,y,210] for x,y in ring]+[[cx,cy,235]],'roof_faces':[list(reversed(range(n)))]+[[i,(i+1)%n,n] for i in range(n)],'wall_faces':[],'bottom_faces':[]})
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name='Canada_'+q['building_id'].split('-')[-1]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+off for i in face] for face in q['roof_faces']]
r={'objects':list(merged.values()),'scope':'Estimated stainless-steel-frame and recessed-glass architecture study. Mapped6partIDs and194/210/235heights preserved, pyramid owns only210–235. Estimated2m bays/4m floors, finish and frame depths not actual counts or surveyed details. No window geometry on shared interior boundaries.','tier_areas_m2':{'lower_union':union.area,'upper_central':cp.area},'edge_ownership':ownership}
(R/'references/one_canada_facade_study.json').write_text(json.dumps(r,indent=2)+'\n');print(r['tier_areas_m2'],len(merged))
