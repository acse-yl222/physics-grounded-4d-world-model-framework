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
main=next(f for f in g['buildings'] if f['id']=='overture-building-12b707fc-a45c-4558-98fc-88e1146fd0ad');whole=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in main['geometry']])
evidence=json.loads((R/'references/citi_height_zones.json').read_text());origin=evidence['origin_xy_m'];eu=evidence['u_axis'];ev=evidence['v_axis']
def rect(u0,u1,v0,v1):return Polygon([(origin[0]+u*eu[0]+v*ev[0],origin[1]+u*eu[1]+v*ev[1]) for u,v in [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]])
annex=whole.intersection(rect(-10,22.5,-10,80));tower=whole.difference(annex);crown=tower.intersection(rect(27.5,72.5,2.5,57.5))
assert abs(annex.area+tower.area-whole.area)<1e-6 and annex.intersection(tower).area<1e-6
neighbor=next(f for f in g['buildings'] if f['id']=='overture-building-f0aeb767-683f-4d29-8a43-85f4b8faf711');np=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in neighbor['geometry']])
zones=[('annex',annex,0,101.3),('tower',tower,0,177.5),('crown',crown,177.5,200.)];edge_records=[]
for zone,p,zbase,ztop in zones:
 prism(p,zbase,ztop,'Citi_'+zone+'_backing','backing',main['id'])
 pts=list(p.exterior.coords)
 for a,b in zip(pts,pts[1:]):
  line=LineString([a,b]);length=line.length
  if length<1e-6:continue
  low=zbase;blockers=[]
  for other,q,qlo,qhi in zones+[('neighbor',np,0,54)]:
   if other==zone:continue
   shared=line.intersection(q.boundary).length
   assert shared<1e-5 or abs(shared-length)<1e-5,(zone,other,shared,length)
   if shared>1e-5 and qlo<=zbase:low=max(low,min(ztop,qhi));blockers.append(other)
  edge_records.append({'zone':zone,'edge':[a,b],'visible_z_interval':[low,ztop],'blockers':blockers})
  if low>=ztop:continue
  dx=(b[0]-a[0])/length;dy=(b[1]-a[1])/length;nx,ny=-dy,dx
  if not p.contains(Point((a[0]+b[0])/2+nx*.02,(a[1]+b[1])/2+ny*.02)):nx,ny=-nx,-ny
  def strip(t0,t1,d0,d1):return Polygon([(a[0]+dx*t+nx*d,a[1]+dy*t+ny*d) for t,d in [(t0,d0),(t1,d0),(t1,d1),(t0,d1)]])
  n=max(1,round(length/4.6));fh=200/45
  for j in range(n):
   t0=length*j/n;t1=length*(j+1)/n;bay=t1-t0
   for pane in range(3):
    aa=t0+bay*pane/3;bb=t0+bay*(pane+1)/3
    prism(strip(aa+.025,bb-.025,-.04,-.008),low+.02,ztop-.02,'Citi_'+zone+'_glass','topglass' if zone=='crown' else 'glass',main['id'])
    prism(strip(aa,min(aa+.035,bb),-.075,-.005),low,ztop,'Citi_minor_mullion','frame',main['id'])
   if zone!='crown':prism(strip(t0,min(t0+.24,t1),-.21,.005),low,ztop,'Citi_major_vertical_profile','metal',main['id'])
  for k in range(46):
   zz=k*fh;aa=max(low,zz);bb=min(ztop,zz+.64)
   if bb>aa:prism(strip(0,length,-.055,-.002),aa,bb,'Citi_shadowbox','spandrel',main['id'])
   aa=max(low,zz-.045);bb=min(ztop,zz+.045)
   if bb>aa:prism(strip(0,length,-.10,.005),aa,bb,'Citi_fine_transom','frame',main['id'])
  for zz in [zbase,ztop-.2]:
   if zz>=low:prism(strip(0,length,-.15,.005),zz,min(ztop,zz+.2),'Citi_zone_border','metal',main['id'])
merged={}
for q in rows:
 key=(q['building_id'],q['kind']);dest=merged.setdefault(key,dict(name='Citi_'+q['building_id'].split('-')[-1]+'_'+q['kind'],kind=q['kind'],building_id=q['building_id'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dest['vertices']);dest['vertices']+=q['vertices'];dest['roof_faces'] += [[i+off for i in face] for face in q['roof_faces']]
r={'objects':list(merged.values()),'edge_intervals':edge_records,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923','pexels_anna_19572396','pexels_zak_36533700'],'lidar_support_files':['citi_roof_review.json','citi_height_zones.json','citi_crown_support.json'],'scope':'Historical Citi estimated stepped envelope replacing invalid full-footprint200m extrusion. Westernannex101.3m,body177.5m and insetcrown200m.0localground maintained to agreeexistingmapped200m tower; localDTM~10mODN is not surveyedbase. Heights describe DSM-DTM levels not absoluteODN conversion. Widthcut22.5m stablewithin~0.75m acrossinsets/holdouts, notsurveyedbreakline. CrownrectangleU27.5..72.5,V2.5..57.5 estimated fromheight-conditioned200mODN support. No exact roofequipment/entrance recovered. Major/minor facadehierarchy fromphotographs;dimensions/materials estimated,annexfacade unobservedextrapolation. Not2026asbuilt.','height_zones':[{'name':name,'base_m':lo,'top_m':hi,'area_m2':p.area,'outer':list(map(list,p.exterior.coords))} for name,p,lo,hi in zones],'ground_reference_warning':'Otherregionmodules use common4.28mODNillustrativeground; thisasset retains reported200mrelativeheight. No survey-gradeverticalregistration asserted.','roof_planes_verified':False,'whole_building_complete':False,'mapped_footprint_area_m2':whole.area,'shared_neighbor_id':neighbor['id']}
(R/'references/citi_envelope_photo_study.json').write_text(json.dumps(r,indent=2)+'\n');print([(z[0],z[1].area) for z in zones])
