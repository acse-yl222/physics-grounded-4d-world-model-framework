"""Local, non-mutating Credit Suisse roof evidence diagnostic."""
from pathlib import Path
import json, hashlib, warnings
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from shapely.geometry import Polygon, Point
from shapely.ops import transform, unary_union
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
ID='overture-part-280011e9-a03d-3145-a0d4-b3536cec5ee3'
g=json.loads((R/'geometry.json').read_text()); f=next(a for a in g['buildings'] if a['id']==ID)
def poly(a):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in a['geometry']])
p=poly(f); center=np.array(p.centroid.coords[0]); fw=Transformer.from_crs(g['crs'],27700,always_xy=True); bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(3)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height)); d=ds.read(1,window=w,masked=True); rr,cc=np.indices(d.shape); xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc); xx=np.array(xx).reshape(d.shape); yy=np.array(yy).reshape(d.shape); x,y=bk.transform(xx,yy)
with rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 t=np.array([q[0] for q in dt.sample(zip(xx.flat,yy.flat),masked=True)]).reshape(d.shape)
z=np.asarray(d,dtype=float); valid=~np.ma.getmaskarray(d)&np.isfinite(t)
inside=valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
sel=valid&np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
A=np.stack([np.ones(x.shape),x-center[0],y-center[1]],axis=-1)
def fit(m):return least_squares(lambda c:A[m]@c-z[m],np.array([np.median(z[m]),0.,0.]),loss='soft_l1',f_scale=.2).x
def stats(a):return {'cells':int(len(a)),'p10':float(np.percentile(a,10)),'median':float(np.median(a)),'p90':float(np.percentile(a,90))}
def met(a):return {'cells':len(a),'rmse_m':float(np.sqrt(np.mean(a*a))),'p95_abs_m':float(np.percentile(abs(a),95)),'median_abs_m':float(np.median(abs(a)))}
checks={}
for axis,v in [('x',x),('y',y)]:
 folds=np.floor((v-v[sel].min())/4).astype(int)%3; errors=[]; records=[]
 for k in range(3):
  test=sel&(folds==k);train=sel&~test;c=fit(train);err=z[test]-A[test]@c;errors.extend(err);records.append({'fold':k,'train_cells':int(train.sum()),**met(err)})
 checks[axis+'_4m_strips']={'folds':records,'pooled':met(np.array(errors))}
c=fit(sel);pred=A@c; near=[]
for a in g['buildings']:
 if a['id']==ID:continue
 
 if a.get('kind')=='site':continue
 q=poly(a);same=a.get('parent_id')==f['parent_id'];parent=a['id'].endswith(f['parent_id'])
 if same or parent or q.distance(p)<.5:
  near.append({'id':a['id'],'name':a.get('name'),'kind':a.get('kind'),'parent_id':a.get('parent_id'),'height_m':a.get('height_m'),'height_basis':a.get('height_basis'),'same_parent':same,'is_parent':parent,'overlap_m2':p.intersection(q).area,'boundary_overlap_m':p.boundary.intersection(q.boundary).length,'distance_m':p.distance(q)})
report={'building_id':ID,'parent_id':f['parent_id'],'baseline_height_m':f['height_m'],'baseline_height_basis':f['height_basis'],'footprint_area_m2':p.area,'selection':'All valid native 1m DSM cells inside 2m inward footprint buffer; no height or residual filtering.','interior_dsm_odn_m':stats(z[sel]),'interior_dtm_odn_m':stats(t[sel]),'interior_dsm_minus_dtm_m':stats((z-t)[sel]),'plane':{'formula':'ODN = intercept + slope_x*(x-center_x) + slope_y*(y-center_y)','center_local_xy_m':center.tolist(),'coefficients':c.tolist(),'in_sample':met((z-pred)[sel])},'spatial_holdout':checks,'relationships':near,'source_hashes':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'limitations':['EA DSM/DTM 1m mixed 2017–2020 OGL evidence vs 2026 Overture footprint; acquisitions and present condition may differ.','DSM is surface elevation in ODN, not facade height or verified clean roof; DTM is terrain, not necessarily building base.','30m baseline comes from 10 floors times assumed 3m, not measured height.','No automatic scene height replacement: shared scene datum and adjoining parent/part meshes require coordination.','Robust fit is evaluated on all held-out inset cells without residual rejection; boundary, roof equipment, materials and facade unverified.'],'geometry_modified':False,'visual_reviewed':False}
# Geometric buffer sensitivity, with no elevation or residual rejection.
report['inset_sensitivity']={}
for inset in [4,6]:
 m=valid&np.array([p.buffer(-inset).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
 cc=fit(m);evaluations={}
 for axis,v in [('x',x),('y',y)]:
  folds=np.floor((v-v[m].min())/4).astype(int)%3;errors=[]
  for k in range(3):
   test=m&(folds==k);train=m&~test;ccfold=fit(train);errors.extend(z[test]-A[test]@ccfold)
  evaluations[axis]=met(np.array(errors))
 report['inset_sensitivity'][str(inset)]={'cells':int(m.sum()),'dsm_odn_m':stats(z[m]),'coefficients':cc.tolist(),'holdout':evaluations}
report['decision']='Full mapped-part roof replacement rejected: 2m inset has western high-return band and poor unfiltered holdout. Central near-flat plane is a conditional interior candidate only; inset sensitivity reports do not independently classify roofs.'
fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for a in g['buildings']:
 if poly(a).distance(p)<15:
  for part in a['geometry']:
   xy=np.array(part['outer']+[part['outer'][0]]);axs[0].plot(xy[:,0],xy[:,1],lw=.5,color='gray')
ims=[axs[0].scatter(x[inside],y[inside],c=z[inside],s=22,marker='s'),axs[1].scatter(x[sel],y[sel],c=(z-pred)[sel],cmap='RdBu_r',s=25,marker='s',vmin=-1,vmax=1)]
for i,im in enumerate(ims):fig.colorbar(im,ax=axs[i],label=['DSM ODN (m)','DSM minus fitted plane (m)'][i]);axs[i].set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)')
axs[0].set(xlim=(p.bounds[0]-8,p.bounds[2]+8),ylim=(p.bounds[1]-8,p.bounds[3]+8),title='Credit Suisse part and mapped neighbours');axs[1].set_title('All interior cells; no residual rejection')
axs[2].scatter(x[sel],z[sel],c=y[sel],s=14);axs[2].set(xlabel='Local east (m)',ylabel='DSM ODN (m)',title='Interior surface elevation')
fig.savefig(R/'references/credit_roof_review.png',dpi=150)
(R/'references/credit_roof_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['interior_dsm_odn_m','interior_dtm_odn_m','plane','spatial_holdout','relationships']},indent=2))
