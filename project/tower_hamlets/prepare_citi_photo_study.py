from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());rows=[]
def prism(poly,lo,hi,name,kind,owner):
 assert hi>lo, (name,lo,hi)
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
from shapely.geometry import Point,LineString
import math
from shapely.geometry import Point,LineString
main=next(f for f in g['buildings'] if f['id']=='overture-building-12b707fc-a45c-4558-98fc-88e1146fd0ad');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in main['geometry']]);prism(p,0,200,'Citi_backing','backing',main['id']);pts=list(p.exterior.coords)
neighbor=next(f for f in g['buildings'] if f['id']=='overture-building-f0aeb767-683f-4d29-8a43-85f4b8faf711');np=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in neighbor['geometry']]);shared=p.boundary.intersection(np.boundary);edge_records=[]
for edge,(a,b) in enumerate(zip(pts,pts[1:])):
 line=LineString([a,b]);overlap=line.intersection(shared).length;assert overlap<1e-6 or abs(overlap-line.length)<1e-6;low=54 if overlap>1e-6 else 0;edge_records.append({'edge':[a,b],'shared_length_m':overlap,'facade_min_z_m':low})
 dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);dx/=length;dy/=length;nx,ny=-dy,dx
 if not p.contains(Point((a[0]+b[0])/2+nx*.02,(a[1]+b[1])/2+ny*.02)):nx,ny=-nx,-ny
 def strip(t0,t1,d0,d1):return Polygon([(a[0]+dx*t+nx*d,a[1]+dy*t+ny*d) for t,d in [(t0,d0),(t1,d0),(t1,d1),(t0,d1)]])
 # Hierarchical vertical ribs below a visually distinct upper glazing zone.
 # Photo-supported composition, estimated dimensions, no change to mapped envelope.
 n=max(1,round(length/4.6));fh=200/45
 for j in range(n):
  t0=length*j/n;t1=length*(j+1)/n;bay=t1-t0
  for pane in range(3):
   aa=t0+bay*pane/3;bb=t0+bay*(pane+1)/3
   prism(strip(aa+.025,bb-.025,-.04,-.008),max(.05,low),180,'Citi_body_glass','glass',main['id'])
   prism(strip(aa+.025,bb-.025,-.04,-.008),180,199.95,'Citi_top_glass','topglass',main['id'])
   prism(strip(aa,min(aa+.035,bb),-.075,-.005),low,200,'Citi_minor_mullion','frame',main['id'])
  prism(strip(t0,min(t0+.24,t1),-.21,.005),low,180,'Citi_major_vertical_profile','metal',main['id'])
 for k in range(45):
  z=k*fh
  if z+.64<=low:continue
  prism(strip(0,length,-.055,-.002),max(z,low),min(z+.64,200),'Citi_shadowbox','spandrel',main['id'])
  if z+.045>low:prism(strip(0,length,-.10,.005),max(low,z-.045),min(200,z+.045),'Citi_fine_transom','frame',main['id'])
 # Continuous upper-zone border keeps crown articulation readable without signage.
 for z in [180,199.8]:prism(strip(0,length,-.15,.005),z,min(200,z+.2),'Citi_crown_border','metal',main['id'])

merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name='Citi_'+q['building_id'].split('-')[-1]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+off for i in face] for face in q['roof_faces']]
r={'edge_intervals':edge_records,'shared_neighbor_id':neighbor['id'],'shared_length_m':shared.length,'objects':list(merged.values()),'scope':'Historical photo-informed Citi facade study, NOT2026asbuilt. Mapped200m flatroof,footprint and54mneighbor sharedwall retained. PhotoAnna and Zak show prominent verticalbody lines and differentiated upperglazingzone. Nominal4.6mmajorbays,3minorpanes perbay,0.24mmajorribs,180m upperzone start and materialcolors estimated. Pattern repeated around hiddenfaces is extrapolation. No exact setbacks,entrance,podium,signage or equipment reconstructed.','observation_links':[{'source_id':'pexels_anna_19572396','visible':'Citi body has strongly emphasized vertical divisions; top signzone is visually distinct and less vertically emphasized.','action':'Added major/minor rib hierarchy and distinct upperglazingzone; no logo.'},{'source_id':'pexels_zak_36533700','visible':'Oblique2022view supports differentiatedtopzone but hides most body andbase.','action':'Historicalenvelope only;180mcut is estimated,not measured.'}],'neighbor_review':'Adjacent54m building sharesboundary but zeroarea overlap. No facade components added on coveredwall0..54.'}

(R/'references/citi_photo_study.json').write_text(json.dumps(r,indent=2)+'\n');print(len(merged))
