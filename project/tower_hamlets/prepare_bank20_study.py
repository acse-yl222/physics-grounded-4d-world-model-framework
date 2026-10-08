from pathlib import Path
import json,numpy as np,math
from shapely.geometry import Polygon
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());bid='overture-building-7d217ccd-1004-47be-a329-334b154bc1fc';f=next(q for q in g['buildings'] if q['id']==bid);p=Polygon(f['geometry'][0]['outer']);th=math.radians(-10);co,si=math.cos(th),math.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);datum=4.28000021
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


from shapely.geometry import box
q=transform(uv,p); high=q.intersection(box(-193,-315,-178,-277));low=q.intersection(box(-250,-400,-196,-303)).difference(high);main=q.difference(high.union(low))
a=np.load(Path('cache/tower_hamlets/bank20_roof.npz'));from shapely import contains_xy
regs=[];objs=[]
for name,poly in [('main',main),('central_lower',high),('western_low',low)]:
 poly=set_precision(poly,.000001); m=a['valid']&contains_xy(poly.buffer(-1),a['u'],a['v']); z=a['z'][m];u=a['u'][m];v=a['v'][m]; level=float(np.median(z));hold=[]
 for axis in [u,v]:
  fold=np.floor(axis/4).astype(int)%3;errs=[]
  for k in range(3):
   if np.any(fold==k) and np.any(fold!=k):errs.extend((z[fold==k]-np.median(z[fold!=k])).tolist())
  hold.append({'rmse_m':float(np.sqrt(np.mean(np.square(errs)))),'median_abs_m':float(np.median(np.abs(errs))),'p90_abs_m':float(np.percentile(np.abs(errs),90))})
 regs.append({'name':name,'cells':len(z),'roof_odn_m':level,'scene_z_m':level-datum,'spatial_4m_strip_holdout_all_cells':hold,'support_uv':[{'outer':list(t.exterior.coords),'holes':[list(h.coords) for h in t.interiors]} for t in getattr(poly,'geoms',[poly])]})
 for i,t in enumerate(getattr(poly,'geoms',[poly])):objs.append(make(t,[level,0,0],'Bank20_'+name+'_'+str(i)))
limitations=['Roof boundaries are geometric interpretations of mixed 2017–2020 DSM, not surveyed edges.','Western small low patches and mixed edge returns remain unresolved; clean regions are descriptive roof levels, not measured terrace boundaries.','Ollie projection falls behind Newfoundland and 1 Bank Street; no facade assigned.','Separate closed prisms retain coincident internal walls. No facade reconstruction.','Current 2026 mapped footprint and historical raster epochs differ. Shared ODN minus 4.28000021 is an unsurveyed scene datum.']
r={'objects':objs,'baseline_mesh':make(q,[42+datum,0,0],'Bank20_baseline42'),'building_id':bid,'scope':'20 Bank Street / Morgan Stanley: historical DSM descriptive roof massing with central depressed domain and western lower strip. Source42m assumes14floors times3m. CWG2024 refurbishment announced; not current as-built verification. No image-derived facade.','datum_odn_m':datum,'regions':regs,'checks':{'source_area_m2':p.area,'partition_area_m2':sum(t.area for t in [main,high,low]),'symmetric_difference_m2':q.symmetric_difference(main.union(high).union(low)).area},'limitations':limitations};(R/'references/bank20_study.json').write_text(json.dumps(r,indent=2));print(json.dumps(regs,indent=2))
