from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fit=json.loads((R/'references/hipped_residential_fit.json').read_text())['groups'][1];bid=fit['ids'][0];f=next(f for f in g['buildings'] if f['id']==bid);e=np.array(fit['axis_u']);n=np.array(fit['axis_v']);c=np.array(fit['center_uv']);h=np.array(fit['half_uv']);E,su,sv,du,dv=fit['parameters_eave_odn_slope_u_slope_v_du_dv'];c+=np.array([du,dv]);datum=4.28000021
uv=lambda x,y:(x*e[0]+y*e[1],x*n[0]+y*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);p=transform(uv,Polygon(f['geometry'][0]['outer']));planes=np.array([[su,0,E+su*(h[0]-c[0])],[-su,0,E+su*(h[0]+c[0])],[0,sv,E+sv*(h[1]-c[1])],[0,-sv,E+sv*(h[1]+c[1])]])
def clip(vertices,coeff):
 out=[]
 for a,b in zip(vertices,vertices[1:]+vertices[:1]):
  da=np.dot(coeff[:2],a)+coeff[2];db=np.dot(coeff[:2],b)+coeff[2]
  if da<=0:out.append(a)
  if (da<0)!=(db<0):out.append((np.array(a)+(np.array(b)-a)*da/(da-db)).tolist())
 return out
objs=[];areas=[]
for i,plane in enumerate(planes):
 verts=[[c[0]-100,c[1]-100],[c[0]+100,c[1]-100],[c[0]+100,c[1]+100],[c[0]-100,c[1]+100]]
 for j,other in enumerate(planes):
  if i!=j:verts=clip(verts,plane-other)
 q=set_precision(p.intersection(Polygon(verts)),.000001)
 for k,part in enumerate(list(q.geoms) if hasattr(q,'geoms') else [q]):
  if part.area<1e-8:continue
  vs=[];ix={};roof=[];wall=[];bottom=[]
  def vi(u,v,z):
   xx,yy=xy(u,v);key=tuple(round(a,7) for a in (xx,yy,z))
   if key not in ix:ix[key]=len(vs);vs.append(list(key))
   return ix[key]
  def zz(u,v):return float(plane@[u,v,1]-datum)
  for tri in constrained_delaunay_triangles(part).geoms:
   rr=list(tri.exterior.coords)[:-1];roof.append([vi(u,v,zz(u,v)) for u,v in rr]);bottom.append([vi(u,v,0) for u,v in reversed(rr)])
  for ring in [part.exterior,*part.interiors]:
   for (u,v),(uu,vv) in zip(ring.coords,list(ring.coords)[1:]):wall.append([vi(u,v,0),vi(uu,vv,0),vi(uu,vv,zz(uu,vv)),vi(u,v,zz(u,v))])
  objs.append({'name':f'HippedResidential_central_sector_{i}_{k}','building_id':bid,'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':wall,'bottom_faces':bottom});areas.append(part.area)
r={'objects':objs,'replacement_ids':[bid],'fit':fit,'scope':'Central hipped residential owner only: 1m DSM supported four-plane descriptive roof with preserved mapped footprint. Adjacent four owners unchanged.','checks':[{'footprint_area_m2':p.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-p.area}],'limitations':['Facade material and flat scene-base zero illustrative; no facade openings reconstructed.','ODN scene offset4.28000021m; local ground approx2.4mODN does not set shared scene datum.','Internal sector walls intentionally coincident; optical roof evidence unavailable.','All72insetcells included,robustlossdownweights outliers;P95residual1.92m and full-footprint edge residuals remain.','Roof planes are extrapolated to mapped boundary; eaves alignment and minor steps unresolved.','Otherfourowners withheld: west lowwings incompatible with onehip; easternpair parametersunstable.','DSM capture date unknown.']}
(R/'references/hipped_residential_study.json').write_text(json.dumps(r,indent=2))
