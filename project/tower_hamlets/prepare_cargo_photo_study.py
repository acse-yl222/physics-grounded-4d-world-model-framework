from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';ID='overture-building-2e7e0c13-18cf-47a2-bca4-3dfa829260a4';g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if q['id']==ID);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);H=79.8;step=H/17;shoulder=15*step;upper=p.buffer(-2.6,join_style=2);rows=[]
def prism(poly,lo,hi,kind):
 if poly.is_empty or hi<=lo:return
 vs=[];fs=[];ix={}
 def vi(x,y,z):
  k=(round(x,7),round(y,7),round(z,7))
  if k not in ix:ix[k]=len(vs);vs.append(list(k))
  return ix[k]
 for pp in [poly] if poly.geom_type=='Polygon' else poly.geoms:
  if pp.geom_type!='Polygon':continue
  for tri in constrained_delaunay_triangles(pp).geoms:
   xy=list(tri.exterior.coords)[:-1];fs.append([vi(x,y,hi) for x,y in xy]);fs.append([vi(x,y,lo) for x,y in reversed(xy)])
  for ring in [pp.exterior,*pp.interiors]:
   xy=list(ring.coords)
   for a,b in zip(xy,xy[1:]):fs.append([vi(*a,lo),vi(*b,lo),vi(*b,hi),vi(*a,hi)])
 rows.append(dict(name='Cargo_'+kind,kind=kind,building_id=ID,vertices=vs,roof_faces=fs,wall_faces=[],bottom_faces=[]))
prism(p,0,H,'backing');baseline=rows.pop();prism(p,0,shoulder,'backing');prism(upper,shoulder,H-.65,'backing')
neighbor=next(q for q in g['buildings'] if q['id']=='overture-building-b68e746c-183b-4e6c-9124-f723ec83cae7');neighborpoly=Polygon(neighbor['geometry'][0]['outer']);observed_edges=[]
def facade(poly,lo,hi,upperzone=False):
 pts=list(poly.exterior.coords)
 for ei,(a,b) in enumerate(zip(pts,pts[1:])):
  dx=b[0]-a[0];dy=b[1]-a[1];le=math.hypot(dx,dy)
  if le<.08:continue
  dx/=le;dy/=le;nx,ny=-dy,dx
  if poly.contains(Point((a[0]+b[0])/2+nx*.02,(a[1]+b[1])/2+ny*.02)):nx,ny=-nx,-ny
  visible=nx<-.5 or ny>.5
  floorclip=3.0 if not upperzone and neighborpoly.boundary.distance(Point((a[0]+b[0])/2,(a[1]+b[1])/2))<.025 else lo
  def emit(poly,z0,z1,kind):prism(poly,max(z0,floorclip),z1,kind)
  def strip(t0,t1,d0,d1):return Polygon([(a[0]+dx*t+nx*d,a[1]+dy*t+ny*d) for t,d in [(t0,d0),(t1,d0),(t1,d1),(t0,d1)]])
  observed_edges.append({'edge':[a,b],'normal':[nx,ny],'photo_facing_north_or_west':visible,'z':[lo,hi],'neighbor_excluded_below_m':floorclip})
  nb=max(1,round(le/1.55));floors=2 if upperzone else 15;fh=(hi-lo)/floors
  for j in range(nb):
   t=le*j/nb;u=le*(j+1)/nb
   emit(strip(t+.025,u-.025,.025,.05),lo,hi,'glass')
   emit(strip(t,min(t+.055,u),.06,.135),lo,hi,'fineframe')
  for k in range(floors):
   z=lo+k*fh
   emit(strip(0,le,.055,.14),z,min(z+.80,hi),'spandrel')
   for dz in [.08,.72,fh-.10]:emit(strip(0,le,.14,.25),z+dz,min(z+dz+.065,hi),'metal')
   if visible and not upperzone:
    # Intermediate glazing transom is finer than floor edge frames.
    emit(strip(0,le,.055,.13),z+fh*.58,z+fh*.58+.055,'fineframe')
  if visible:
   nmajor=max(1,round(le/6.2))
   for j in range(nmajor+1):
    t=min(le-.18,le*j/nmajor);t=max(0,t)
    emit(strip(t,min(t+.18,le),.08,.38),max(lo,2*step if not upperzone else lo),hi,'metal')
   if not upperzone:
    for z in [5*step,10*step,shoulder-.25]:emit(strip(0,le,.08,.34),z,min(z+.18,hi),'metal')
facade(p,0,shoulder);facade(upper,shoulder,H-.8,True)
# Canopy slats lie at the preserved79.8m top, over recessed upper floor. No extension of mapped ground outline.
canopyp=unary_union([p,translate(p,xoff=-3.5,yoff=3.5)])
prism(canopyp.difference(canopyp.buffer(-.20,join_style=2)),H-.45,H,'metal')
uv=rotate(canopyp,10,origin=(0,0));xmin,ymin,xmax,ymax=uv.bounds
y=ymin
while y<=ymax:
 slab=uv.intersection(box(xmin-1,y,xmax+1,y+.115));prism(rotate(slab,-10,origin=(0,0)),H-.18,H,'canopy');y+=.9
x=xmin
while x<=xmax:
 beam=uv.intersection(box(x,ymin-1,x+.23,ymax+1));prism(rotate(beam,-10,origin=(0,0)),H-.58,H-.24,'metal');x+=5.4
# The upper facade posts continue to canopy underside, aligned to observed perimeter layers.
for a,b in zip(list(upper.exterior.coords),list(upper.exterior.coords)[1:]):
 le=Point(a).distance(Point(b));n=max(1,round(le/6.2))
 for j in range(n):
  x=a[0]+(b[0]-a[0])*j/n;y=a[1]+(b[1]-a[1])*j/n;prism(box(x-.09,y-.09,x+.09,y+.09),H-.8,H-.24,'metal')
merged={}
for q in rows:
 d=merged.setdefault(q['kind'],dict(name='Cargo_'+q['kind'],kind=q['kind'],building_id=ID,vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(d['vertices']);d['vertices']+=q['vertices'];d['roof_faces'] +=[[i+off for i in face] for face in q['roof_faces']]
r={'objects':list(merged.values()),'baseline_object':baseline,'building_id':ID,'footprint':f['geometry'],'total_height_m':H,'scope':'Cargo/25NorthColonnade photo-informed exterior study, historical/context-date unknown, not2026asbuilt. TomWhyte photo10391373 north/west-facing bluegreen glazing, layered slim frames/major fins, projecting slatted canopy and upper recess inform geometry. Mapped14vertex ground footprint and79.8m total retained. Uniform17nominal divisions merely estimated/sourcefloorcount,15main+2recess divisions not observedstorey allocation; setback2.6m,canopy-only NWprojection3.5m,slats.9m spacing,bays1.55m,major6.2m all artistically estimated. Base0–9.39m generic continuation no doors/entry claimed; south/east extrapolated.2022refurbishment texts not fused into unknown-date photo appearance.','facade_edges':observed_edges,'parameters':{'upper_recess_m':2.6,'shoulder_m':shoulder,'slat_pitch_m':.9,'slat_width_m':.115,'slat_depth_m':.18,'canopy_extent':'Estimated canopy-only projection3.5m north/west beyond body, original ground footprint unchanged; upper recess2.6m','glass_front_m':.05,'major_fin_front_m':.38},'source_hashes':{'geometry.json':hashlib.sha256((R/'geometry.json').read_bytes()).hexdigest(),'pexels_tom_10391373':hashlib.sha256((R/'references/pexels-tom-whyte-10391373.jpeg').read_bytes()).hexdigest()}}
(R/'references/cargo_photo_study.json').write_text(json.dumps(r,indent=2)+'\n');print(len(merged),'objects',p.area,upper.area)
