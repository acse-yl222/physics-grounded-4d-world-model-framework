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
   # Preserve prior unobserved base treatment below80m; change only visible middle/upper study zone.
   zones=[(lo,hi,'punched' if level==0 and length>12 else 'glazed')]
   for zlo,zhi,style in zones:
    if zhi<=zlo:continue
    n=max(1,round(length/(3.0 if style=='punched' else 2.6 if level==1 else 2)));nf=max(1,round((zhi-zlo)/4));fh=(zhi-zlo)/nf
    if style=='punched':
     # Broad silver infill surrounding discrete dark apertures; ratios estimated from oblique photos.
     for j in range(n):
      t0=length*j/n;t1=length*(j+1)/n;bay=t1-t0;side=.17*bay
      for k in range(nf):
       zz=zlo+k*fh;bottom=zz+.17*fh;top=zz+.83*fh
       prism(strip(t0+.012,t0+side,-.15,.16),zz+.012,zz+fh-.012,'Canada_silver_pier','steel',owner)
       prism(strip(t1-side,t1-.012,-.15,.16),zz+.012,zz+fh-.012,'Canada_silver_pier','steel',owner)
       prism(strip(t0+side,t1-side,-.15,.16),zz+.012,bottom,'Canada_silver_spandrel','steel',owner)
       prism(strip(t0+side,t1-side,-.15,.16),top,zz+fh-.012,'Canada_silver_spandrel','steel',owner)
       prism(strip(t0+side,t1-side,-.035,.03),bottom,top,'Canada_discrete_glass','glass',owner)
       left,right=t0+side,t1-side;fw=.055;mid=(left+right)/2;lowtrans=bottom+(top-bottom)*.28
       for aa,bb in [(left,left+fw),(right-fw,right),(mid-fw/2,mid+fw/2)]:
        prism(strip(aa,bb,-.09,.045),bottom,top,'Canada_window_vertical','windowframe',owner)
       for zz0,zz1 in [(bottom,bottom+fw),(top-fw,top),(lowtrans-fw/2,lowtrans+fw/2)]:
        prism(strip(left,right,-.09,.045),zz0,zz1,'Canada_window_horizontal','windowframe',owner)
       # Horizontal panel shadow joint crosses the broad pier too, as a narrow inset dark strip.
       prism(strip(t0+.014,t1-.014,-.08,.02),max(zlo,zz-.012),zz+.012,'Canada_panel_joint','joint',owner)

    else:
     for j in range(n):
      t0=length*j/n;t1=length*(j+1)/n
      if t1-t0<.2:continue
      prism(strip(t0+.10,t1-.10,-.03,.035),zlo+.08,zhi-.08,'Canada_glass','glass',owner)
      prism(strip(t0,min(t0+.15,t1),-.12,.13),zlo,zhi,'Canada_mullion','steel',owner)
     for k in range(nf+1):
      z=zlo+k*fh;prism(strip(0,length,-.12,.13),max(zlo,z-.13),min(zhi,z+.13),'Canada_transom','steel',owner)
# Photographed horizontal roof-base louvre screen; dimensions/count estimated, no apexchange.
roofpoly=poly(roof);screen=roofpoly.buffer(.12,join_style=2).difference(roofpoly.buffer(-.10,join_style=2))
for k in range(5):prism(screen,210+k*.32,210+k*.32+.09,'Canada_roofbase_louvre','steel',roof['id'])
# Preserve roof-only mapped pyramid exactly; base210 apex235.
ring=list(poly(roof).exterior.coords)[:-1];cx=sum(a[0] for a in ring)/len(ring);cy=sum(a[1] for a in ring)/len(ring);n=len(ring);rows.append({'name':'Canada_pyramid','kind':'steel','building_id':roof['id'],'vertices':[[x,y,210] for x,y in ring]+[[cx,cy,235]],'roof_faces':[list(reversed(range(n)))]+[[i,(i+1)%n,n] for i in range(n)],'wall_faces':[],'bottom_faces':[]})
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name='Canada_'+q['building_id'].split('-')[-1]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+off for i in face] for face in q['roof_faces']]
r={'window_detail_basis':'InspectedAltafphoto shows innerwindowframe,twopanes andlowertransom.55mmframes,28%transomheight,24mmbaygrooves and16mmhorizontaljoint estimated. Geometryreal,no texture.','objects':list(merged.values()),'scope':'Photo-informed middle/upper correction: broad silver panel grid and discrete dark apertures from inspected ZakH2022 and TomWhyteviews; topglazedband and insetcornerglass retained. Approx3.0m mainbays/2.6m upperbays,66%aperturewidth/height,below80m unsupported extrapolation and4m rhythm estimated,not surveyed/countverified. Samegrammar extrapolated below80m solely for coherent appearance; entrances/base remain unresolved. Estimated stainless-steel-frame and recessed-glass architecture study. Mapped6partIDs and194/210/235heights preserved, pyramid owns only210–235. Estimated3.0m mainbays/2.6m upperbays and4m facadeintervals, finish and frame depths not actual counts or surveyed details. No window geometry on shared interior boundaries.','tier_areas_m2':{'lower_union':union.area,'upper_central':cp.area},'edge_ownership':ownership,'observation_links':[{'photo':'pexels-altaf-shah-19330277.jpeg','observation':'Blackwhite shows four upperwindowrows and narrow horizontal louvres atpyramidbase; no color inference.','action':'Upper4rows retained,nominal2.6mbays,5estimated roofbase horizontal slats at210..211.37m.'},{'photo':'pexels-anna-rynkowska-19572396.jpeg','observation':'Frontalbody has denser discrete apertures than initial3.7m hypothesis and continuous silvergrid downvisiblebody.','action':'Mainnominal3.0mbays,repeatgrammar belowobservedarea as explicit extrapolation.'},{'photo':'pexels-zak-h-36533700.jpeg','observation':'Pyramid-topped centerbackground tower has broad light panel lattice with dark square-like apertures; belowpyramid more continuous glazed band.','action':'Majorfaces0–194m use discrete66%apertures,below80m explicitly extrapolated;194–210glazedband preserved.'},{'photo':'pexels-tom-whyte-10391373.jpeg','observation':'Upperright tower shows silverpanelgrid and narrow vertical recessedcorner glazing.','action':'Shortmappedboundary segments retained glazed as estimated corner proxy.'}]}
(R/'references/one_canada_photo_study_002.json').write_text(json.dumps(r,indent=2)+'\n');print(r['tier_areas_m2'],len(merged))
