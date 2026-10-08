from pathlib import Path
import json,math
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
r=json.loads((R/'references/credit_envelope_study.json').read_text());bodies=r['objects'];polys=[unary_union([Polygon([q['vertices'][i][:2] for i in f]) for f in q['roof_faces']]) for q in bodies];rows=[];intervals=[]
for q in bodies:q['kind']='backing';q['name']='Credit_'+q['name'];rows.append(q)
def prism(a,b,n,t0,t1,d0,d1,z0,z1,kind,owner):
 dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy);dx/=ll;dy/=ll
 xy=[(a[0]+dx*t+n[0]*d,a[1]+dy*t+n[1]*d) for t,d in [(t0,d0),(t1,d0),(t1,d1),(t0,d1)]]
 vv=[[x,y,z] for z in [z0,z1] for x,y in xy];rows.append(dict(name='Credit_'+kind,kind=kind,building_id=owner,vertices=vv,roof_faces=[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],wall_faces=[],bottom_faces=[]))
for qi,(q,p) in enumerate(zip(bodies,polys)):
 h=q['height_scene_m'];owner=q['building_id']
 for ring in [p.exterior,*p.interiors]:
  xy=list(ring.coords)
  for a,b in zip(xy,xy[1:]):
   line=LineString([a,b]);ll=line.length
   if ll<.03:continue
   cuts=[0.,ll]
   for pp in polys:
    inter=line.intersection(pp.boundary)
    for obj in getattr(inter,'geoms',[inter]):
     if obj.is_empty:continue
     for pt in obj.coords:cuts.append(line.project(Point(pt)))
   cuts=sorted(set(round(c,7) for c in cuts));dx=(b[0]-a[0])/ll;dy=(b[1]-a[1])/ll;n=(-dy,dx)
   if p.contains(Point((a[0]+b[0])/2+n[0]*.005,(a[1]+b[1])/2+n[1]*.005)):n=(-n[0],-n[1])
   for t0,t1 in zip(cuts,cuts[1:]):
    if t1-t0<.05:continue
    mid=line.interpolate((t0+t1)/2);cover=max([qq['height_scene_m'] for j,(qq,pp) in enumerate(zip(bodies,polys)) if j!=qi and pp.buffer(.025).covers(mid)],default=0)
    if cover>=h-.02:continue
    intervals.append(dict(owner=owner,body=q['name'],edge=[a,b],t=[t0,t1],z=[cover,h]))
    bays=max(1,round((t1-t0)/2.0));fh=h/max(1,round(h/3.5))
    for j in range(bays):
     u=t0+(t1-t0)*j/bays;v=t0+(t1-t0)*(j+1)/bays
     prism(a,b,n,u+.035,v-.035,.025,.055,cover,h,'glass',owner)
     prism(a,b,n,u,min(u+.40,v),.06,.14,cover,h,'frame',owner)
    for k in range(math.floor(cover/fh),math.ceil(h/fh)):
     z0=max(cover,k*fh);z1=min(h,k*fh+1.65)
     if z1>z0:prism(a,b,n,t0,t1,.06,.22,z0,z1,'panel',owner)
    # Uppermost narrow parapet band; do not alter stepped roof elevation.
    prism(a,b,n,t0,t1,.06,.23,max(cover,h-.65),h,'panel',owner)
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);d=merged.setdefault(key,dict(name='Credit_'+q['building_id'].split('-')[-1]+'_'+q['kind'],building_id=q['building_id'],kind=q['kind'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(d['vertices']);d['vertices']+=q['vertices'];d['roof_faces'] +=[[i+off for i in f] for f in q['roof_faces']+q['wall_faces']+q['bottom_faces']]
r['objects']=list(merged.values());r['exposed_wall_intervals']=intervals;r['scope']='Photo-informed Credit Suisse facade appearance hypothesis, source pexels_ollie_11491155. Pale horizontal bands/dark discrete glazing from visible upper facade; lower and reverse facades extrapolated, no entrance reconstruction. Original6owners and8estimated height zones retained; roof elevations remain uncertain DSM hypotheses. Facadeapprox3.5m rhythm fitted evenly to each existing height zone,1.65m panels,2m bays,0.4m vertical pale separators and depths artistically estimated, not measured. Neighbor-covered wall intervals excluded; touching internal body walls remain. No logo/photo textures.'
(R/'references/credit_photo_study.json').write_text(json.dumps(r,indent=2)+'\n');print(len(merged),'objects',len(intervals),'exposed intervals')
