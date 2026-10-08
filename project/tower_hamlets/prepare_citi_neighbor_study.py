from pathlib import Path
import json,numpy as np,math
from shapely.geometry import Polygon
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fit=json.loads((R/'references/citi_neighbor_roof_fit.json').read_text());bid=fit['building_id'];f=next(q for q in g['buildings'] if q['id']==bid);p=Polygon(f['geometry'][0]['outer']);th=math.radians(-10);co,si=math.cos(th),math.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);datum=4.28000021
def make(poly,c,label):
 verts=[];faces=[];ids={}
 def vi(u,v,z):
  x,y=xy(u,v);k=(round(x,7),round(y,7),round(z,7))
  if k not in ids:ids[k]=len(verts);verts.append(list(k))
  return ids[k]
 def zz(u,v):return c[0]+c[1]*u+c[2]*v-datum
 for q in getattr(poly,'geoms',[poly]):
  if q.geom_type!='Polygon':continue
  for tri in constrained_delaunay_triangles(q).geoms:
   rr=list(tri.exterior.coords)[:-1];faces.append([vi(u,v,zz(u,v)) for u,v in rr]);faces.append([vi(u,v,0) for u,v in reversed(rr)])
  for ring in [q.exterior,*q.interiors]:
   for (u,v),(uu,vv) in zip(ring.coords,list(ring.coords)[1:]):faces.append([vi(u,v,0),vi(uu,vv,0),vi(uu,vv,zz(uu,vv)),vi(u,v,zz(u,v))])
 return {'name':label,'building_id':bid,'kind':'estimated','vertices':verts,'roof_faces':faces,'wall_faces':[],'bottom_faces':[]}

objs=[];areas=[]
for reg in fit['regions']:
 for i,q in enumerate(reg['support_uv']):
  poly=set_precision(Polygon(q['outer'],q['holes']),.000001);areas.append(poly.area);objs.append(make(poly,np.array(reg['plane_odn_c_a_u_b_v']),'CitiNeighbor_'+reg['name']+'_'+str(i)))
baseline=make(transform(uv,p),np.array([54+datum,0,0]),'CitiNeighbor_baseline54')
r={'objects':objs,'baseline_mesh':baseline,'building_id':bid,'scope':'WesternCitiadjacentownerf0aeb767 wholefootprint descriptive historicalDSMroofmassing, probable33CanadaSquare/currentOneEdenidentity.54m source18floors×3m baseline replacedby78.476ODNouterroof andweaklytilted87.36ODNmainroof. SharedODNminus4.28000021. Two cleanroofdomains, notpixelislands;edge/cornerlowreturns unexplained, notroofholes. Nophoto-derivedfacade, proposed2026renovation notmodeled. NeighborCititower200m anditsfacade leftforcoordinator interfaceclipping.','datum_odn_m':datum,'roof_fit':'references/citi_neighbor_roof_fit.json','shared_interface':'references/citi_neighbor_shared_interface.json','checks':{'source_area_m2':p.area,'partition_area_m2':sum(areas),'area_difference_m2':sum(areas)-p.area},'limitations':fit['limitations']+['Separateclosedprisms retaininternalcoincidentwalls; notsimulationunion.','PrimaryCWG2026OneEdenrefurbishmentmeans oldDSM notcurrentasbuiltverification.','Citi facade details alongsharededge requirepiecewisecutoff74.196/83.208–83.215m; integrationhelduntilcoordinatorfixes.']};(R/'references/citi_neighbor_study.json').write_text(json.dumps(r,indent=2));print(len(objs),r['checks'])
