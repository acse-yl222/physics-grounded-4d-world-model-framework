from pathlib import Path
import json,numpy as np,math
from shapely.geometry import Polygon,box
from shapely.ops import transform,unary_union
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());bid='overture-building-f9ed6834-375f-4fac-ae5c-d363ac9b931d';f=next(q for q in g['buildings'] if q['id']==bid);p=Polygon(f['geometry'][0]['outer']);fit=json.loads((R/'references/barclays_podium_roof_fit.json').read_text());low,base,peak,vc,slope,sp,uc,ss=fit['coefficients'];th=math.radians(-10);co,si=math.cos(th),math.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);pu=transform(uv,p);datum=4.28000021

def positive(poly,c):
 d=np.array(c[1:]);norm=np.linalg.norm(d)
 if norm<1e-10:return poly if c[0]>=-1e-10 else Polygon()
 o=-c[0]*d/(norm*norm);n=d/norm;t=np.array([-n[1],n[0]]);hp=Polygon([o-t*1e4,o+t*1e4,o+t*1e4+n*2e4,o-t*1e4+n*2e4]);return poly.intersection(hp)
regions=[]
for u0,u1 in [(-1000,uc),(uc,1000)]:
 for v0,v1 in zip([-1000,12,vc,52], [12,vc,52,1000]):
  domain=pu.intersection(box(u0,v0,u1,v1));vm=(v0+v1)/2;um=(u0+u1)/2;sign=1 if vm<vc else -1
  planes=[('outerterrace' if vm<12 or vm>52 else 'innerterrace',np.array([low if vm<12 or vm>52 else base,0,0])),('main_roofslope',np.array([peak-sign*slope*vc,0,sign*slope]))]
  if vm<vc:
   sig=1 if um<uc else -1;planes.append(('south_cross_roofslope',np.array([sp-sig*ss*uc,sig*ss,0])))
  for label,c in planes:
   q=domain
   for _,other in planes:
    q=positive(q,c-other)
   if q.area>.001:regions.append((label,c,q))
assert abs(sum(q.area for _,_,q in regions)-p.area)<.001
objs=[];records=[]
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
# Union domains sharingidenticalroofplane toavoid unnecessary coplanar boundaries.
groups={}
for label,c,q in regions:groups.setdefault((label,*np.round(c,10)),[]).append(q)
for i,(key,polys) in enumerate(groups.items()):
 label=key[0];c=np.array(key[1:]);merged=set_precision(unary_union(polys),.000001)
 for j,q in enumerate(getattr(merged,'geoms',[merged])):
  if q.geom_type!='Polygon':continue
  obj=make(q,c,'BarclaysWestern_'+str(i)+'_'+str(j)+'_'+label);objs.append(obj);records.append({'object':obj['name'],'plane_odn_c_a_u_b_v':c.tolist(),'support_uv':[{'outer':list(q.exterior.coords),'holes':[list(h.coords) for h in q.interiors]}],'area':q.area})
baseline=make(pu,np.array([30+datum,0,0]),'BarclaysWestern_baseline');r={'objects':objs,'baseline_mesh':baseline,'building_id':bid,'scope':'Barclayswesternofficef9ed6834 descriptivewholefootprint roofmassing, distinctfrom156mBarclaystowerfcc7. Source10floors×3m baseline30m replacedbyspatialDSM-supported63/68mODNterraces andcontinuous longitudinal/southcross roofslopes. Planeenvelope is architecturalapproximation fittedrobustly,not acceptedexactroof; nofacade/windows/equipmentinvented. Wholemappedplanpreserved;sharedODNminus4.28000021.','datum_odn_m':datum,'regions':records,'fit_report':'references/barclays_podium_roof_fit.json','checks':{'source_area_m2':p.area,'partition_area_m2':sum(v['area'] for v in records),'area_difference_m2':sum(v['area'] for v in records)-p.area},'limitations':fit['limitations']+['Separatedclosedroofregionprisms havecoincidentinternalwalls;notbooleanunionsimulationvolume.','Lowreturns alongsouth/westedges unresolved: fullfootprint retainedusingdescriptiveouterlevel,not claiminggroundreturnsareroofgaps.','TomphotoleftBarclaystowerfcc7 not used for facade of thisbuilding.']};(R/'references/barclays_podium_study.json').write_text(json.dumps(r,indent=2));print('objects',len(objs),r['checks'])
