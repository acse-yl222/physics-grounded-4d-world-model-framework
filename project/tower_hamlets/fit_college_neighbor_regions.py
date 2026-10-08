"""Geometrically bounded cc2 roof patches, no residual-filtered validation."""
from pathlib import Path
import json,warnings,hashlib
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union,transform
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());ID='overture-building-d3e19a2b-b114-488d-b7d8-3b37cea9c607';f=next(a for a in g['buildings'] if a['id']==ID);p=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in f['geometry']]);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(2)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(d.shape),np.array(yy).reshape(d.shape))
z=np.asarray(d,float);valid=~np.ma.getmaskarray(d);theta=np.deg2rad(-10)
co,si=np.cos(theta),np.sin(theta)
def uv(a,b):return np.array(a)*co+np.array(b)*si,-np.array(a)*si+np.array(b)*co
def xy(a,b):return np.array(a)*co-np.array(b)*si,np.array(a)*si+np.array(b)*co
u,v=uv(x,y);pu=transform(uv,p)
# Use long-edge direction from visible footprint/roof form, then rectify low-return bounds.
inside=valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
low=inside&(z>14)&(z<20)&(x>85)&(x<120)&(y>364)&(y<384)
lo=[float(np.quantile(u[low],.02)),float(np.quantile(v[low],.02)),float(np.quantile(u[low],.98)),float(np.quantile(v[low],.98))]
central=pu.intersection(box(*lo));swcut=float(uv(90,353)[1]);southwest=pu.intersection(box(-1000,-1000,35,375)).difference(central);perimeter=pu.difference(central.union(southwest))
domains=[('central_low',central),('perimeter',perimeter),('southwest',southwest)]
rows=[];fig,axs=plt.subplots(1,2,figsize=(11,8),layout='constrained')
inside=valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
axs[0].scatter(u[inside],v[inside],c=z[inside],vmin=15,vmax=30,cmap='viridis',s=22,marker='s')
for name,q in domains:
 m=valid&np.array([q.buffer(-2).contains(Point(a,b)) for a,b in zip(u.flat,v.flat)]).reshape(u.shape);center=np.array([u[m].mean(),v[m].mean()]);A=np.stack([np.ones(x.shape),u-center[0],v-center[1]],axis=-1)
 def fit(mm):return least_squares(lambda c:A[mm]@c-z[mm],np.array([np.median(z[mm]),0.,0.]),loss='soft_l1',f_scale=.15).x
 def metrics(e):return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e*e))),'p95_abs_m':float(np.percentile(abs(e),95)),'median_abs_m':float(np.median(abs(e)))}
 c=fit(m);checks={}
 for axis,arr in [('u',u),('v',v)]:
  folds=np.floor((arr-arr[m].min())/2).astype(int)%3;err=[];records=[]
  for k in range(3):
   te=m&(folds==k);tr=m&~te
   if not te.any() or tr.sum()<8:continue
   cf=fit(tr);ee=z[te]-A[te]@cf;err.extend(ee);records.append({'fold':k,'train_cells':int(tr.sum()),**metrics(ee)})
  checks[axis]={'pooled':metrics(np.array(err)),'folds':records}
 qxy=transform(xy,q);row={'name':name,'cells':int(m.sum()),'center_uv_m':center.tolist(),'plane_odn_intercept_slope_u_slope_v':c.tolist(),'odn_median':float(np.median(z[m])),'partition_local_xy':{'outer':list(map(list,qxy.exterior.coords)),'holes':[list(map(list,h.coords)) for h in qxy.interiors]},'support_area_m2':q.area,'holdout':checks,'in_sample':metrics((z-A@c)[m])};row['candidate_status']='conditional partial plane' if max(k['pooled']['rmse_m'] for k in checks.values())<.3 else 'appearance-only hypothesis; plane not accepted';rows.append(row)
 qu,qv=q.exterior.xy;axs[0].plot(qu,qv,c='red');im=axs[1].scatter(u[m],v[m],c=(z-A@c)[m],cmap='RdBu_r',vmin=-1,vmax=1,s=25,marker='s');axs[1].plot(qu,qv,c='black')
for ax in axs:ax.set(aspect='equal',xlabel='Across u(m)',ylabel='Along v(m)')
axs[0].set_title('Geometric patches and observed ODN');axs[1].set_title('All selected-cell residuals');fig.colorbar(im,ax=axs[1],label='DSM minus plane(m)')
report={'building_id':ID,'axis_rotation_radians':float(theta),'u_formula':'x*cos(theta)+y*sin(theta)','v_formula':'-x*sin(theta)+y*cos(theta)','central_low_uv_bounds':lo,'southwest_domain_uv':'u<35,v<375; footprint clipped estimated high-extension zone','regions':rows,'partition_area_check':{'mapped_m2':p.area,'partition_sum_m2':sum(q.area for _,q in domains),'union_m2':unary_union([q for _,q in domains]).area},'source_hashes':{name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['geometry.json','references/ea_dsm_1m.tif']},'limitations':['All three partition boundaries are estimated appearance hypotheses. Central rectangle derives from2–98%quantile bounds of14–20mDSM within preselected central geographic region; this is post-observation selection, not independently detected architecture.','Validation uses all valid cells in2m-inset domains, no residual exclusions. Failing plane fits do not validate constant median levels either.','Full mapped footprint is partitioned, including estimated perimeter extrapolation. Central low roof remains elevated; no ground courtyard inferred.','EA mixed2017–2020ODN vs2026 mapped footprint; materials and current state unverified.'],'geometry_modified':False,'visual_reviewed':False}
fig.savefig(R/'references/college_neighbor_regions.png',dpi=150);(R/'references/college_neighbor_regions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps([{k:r[k] for k in ['name','cells','odn_median','holdout']} for r in rows],indent=2))
