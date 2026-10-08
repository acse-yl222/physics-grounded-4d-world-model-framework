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
    crown_face=q['name']=='Credit_Main_main_south' and n[0]<-.65
    crownbase=87.82200098018555
    bodytop=crownbase if crown_face else h
    bays=max(1,round((t1-t0)/2.5));fh=bodytop/max(1,round(bodytop/3.5))
    # Discrete, recessed two-pane windows; pale fine surround with projecting sill.
    for k in range(math.floor(cover/fh),math.ceil(bodytop/fh)):
     z=k*fh;zlo=max(cover,z);zhi=min(bodytop,z+fh)
     if zhi<=zlo:continue
     for low,high,d0,d1,kind in [(z,z+.20,.03,.10,'shadow'),(z+.20,z+1.15,.07,.18,'panel'),(z+1.15,z+1.30,.07,.30,'panel')]:
      low=max(cover,low);high=min(bodytop,high)
      if high>low:prism(a,b,n,t0,t1,d0,d1,low,high,kind,owner)
     for j in range(bays):
      u=t0+(t1-t0)*j/bays;v=t0+(t1-t0)*(j+1)/bays
      lo=max(cover,z+1.30);hi=min(bodytop,z+fh)
      if hi<=lo:continue
      # Pale piers are localized window surrounds, not a thick continuous grid.
      prism(a,b,n,u,min(u+.32,v),.04,.18,lo,hi,'panel',owner)
      x0=u+.32;x1=v-.04
      if x1<=x0+.15:continue
      prism(a,b,n,x0,x1,.015,.045,lo,hi,'glass',owner)
      for xx in [x0,x1-.06,(x0+x1)/2-.025]:prism(a,b,n,xx,xx+.055,.05,.115,lo,hi,'frame',owner)
      for zz in [lo,min(hi-.055,lo+.48),hi-.055]:
       if zz>=lo:prism(a,b,n,x0,x1,.05,.115,zz,min(zz+.055,hi),'frame',owner)
    if crown_face:
     intervals[-1]['photo_crown']={'source':'pexels_ollie_11491155','z':[crownbase,h],'orientation':'west outward normal','normal':n,'mapping':'Higher south roof aligns qualitatively with taller right-hand crown in west-looking-east photo; not calibrated.'}
     c0=t0+.30*(t1-t0)
     prism(a,b,n,t0,c0,.06,.22,crownbase,h-.40,'panel',owner)
     nc=max(1,round((t1-c0)/3.8))
     # A distinct tall dark recessed crown, with deep pale piers and fine louvers.
     for j in range(nc):
      u=c0+(t1-c0)*j/nc;v=c0+(t1-c0)*(j+1)/nc
      prism(a,b,n,u+.38,v-.06,.018,.055,crownbase+.40,h-.55,'shadow',owner)
      prism(a,b,n,u,u+.38,.06,.30,crownbase,h-.40,'panel',owner)
      for zz in range(1,15):
       z=crownbase+.40+zz*(h-crownbase-.95)/15
       prism(a,b,n,u+.38,v-.06,.055,.13,z,z+.035,'louver',owner)
     prism(a,b,n,t0,t1,.06,.38,crownbase,crownbase+.35,'panel',owner)
    # Stepped, shallow cornice profile stays entirely below preserved mapped top.
    for dz0,dz1,dep in [(.65,.42,.24),(.42,.22,.42),(.22,0,.34)]:
     if h-dz0>=cover:prism(a,b,n,t0,t1,.05,dep,h-dz0,h-dz1,'panel',owner)

merged={}
for q in rows:
 key=(q['building_id'],q['kind']);d=merged.setdefault(key,dict(name='Credit_'+q['building_id'].split('-')[-1]+'_'+q['kind'],building_id=q['building_id'],kind=q['kind'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(d['vertices']);d['vertices']+=q['vertices'];d['roof_faces'] +=[[i+off for i in f] for f in q['roof_faces']+q['wall_faces']+q['bottom_faces']]
r['objects']=list(merged.values());r['exposed_wall_intervals']=intervals;r['scope']='002: Photo west-crown correspondence is qualitative: highest south93.797m versus north87.822m shoulder. Only higher south west-facing wall receives tall dark crown inside existing top5.975m. Crown south30percent pale blank signage wall and north70percent approximately3.8m tall dark bays estimated from photo proportions; no logo, exact count/location uncalibrated. Fine inner frames/two-pane windows/lowtransom and profiled bands/cornice estimate observations; other facades extrapolated. Photo-informed Credit Suisse facade appearance hypothesis, source pexels_ollie_11491155. Pale horizontal bands/dark discrete glazing from visible upper facade; lower and reverse facades extrapolated, no entrance reconstruction. Original6owners and8estimated height zones retained; roof elevations remain uncertain DSM hypotheses. Facadeapprox3.5m rhythm fitted evenly to each existing height zone,1.3m profiled horizontal bands,2.5m bays,0.32m pale separators and depths artistically estimated, not measured. Neighbor-covered wall intervals excluded; touching internal body walls remain. No logo/photo textures.'
(R/'references/credit_photo_study_002.json').write_text(json.dumps(r,indent=2)+'\n');print(len(merged),'objects',len(intervals),'exposed intervals')
