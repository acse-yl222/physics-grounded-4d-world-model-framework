"""Exploratory spatial roof partitions, fitted without residual test rejection."""
from pathlib import Path
import json,warnings
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
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());ID='overture-part-97dd8c74-072f-3702-b265-ea4b6279a593';f=next(q for q in g['buildings'] if q['id']==ID);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(2)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(d.shape),np.array(yy).reshape(d.shape))
z=np.asarray(d,float);valid=~np.ma.getmaskarray(d);theta=np.deg2rad(-10);u=x*np.cos(theta)+y*np.sin(theta);v=-x*np.sin(theta)+y*np.cos(theta)
def uvpoly(q):return transform(lambda x,y:(np.array(x)*np.cos(theta)+np.array(y)*np.sin(theta),-np.array(x)*np.sin(theta)+np.array(y)*np.cos(theta)),q)
pu=uvpoly(p);sel=valid&np.array([p.buffer(-4).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);A=np.stack([np.ones(x.shape),u,v],axis=-1)
def fit(m):return least_squares(lambda c:A[m]@c-z[m],np.array([np.median(z[m]),0.,0.]),loss='soft_l1',f_scale=.25).x
def metric(e):return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e*e))),'median_abs_m':float(np.median(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95))}
# Train thresholds by robust capped absolute loss; no cells deleted in validation.
def train(m):
 best=None
 for cut in np.arange(pu.bounds[0]+5,pu.bounds[0]+19,.5):
  low=m&(u<cut);high=m&~low
  if min(low.sum(),high.sum())<60:continue
  cl=fit(low);ch=fit(high);e=np.r_[z[low]-A[low]@cl,z[high]-A[high]@ch];loss=np.minimum(abs(e),5).mean()
  if best is None or loss<best[0]:best=(loss,cut,cl,ch)
 return best
b=train(sel);cut=b[1];hi=sel&(u>=cut)
# Split high roof north/south; robust constant-loss selection then independent per-fold re-selection.
def highsplit(m):
 best=None
 for vc in np.arange(np.percentile(v[m],20),np.percentile(v[m],80),1):
  a=m&(v<vc);bb=m&~a
  if min(a.sum(),bb.sum())<60:continue
  ca=fit(a);cb=fit(bb);e=np.r_[z[a]-A[a]@ca,z[bb]-A[bb]@cb];loss=np.minimum(abs(e),5).mean()
  if best is None or loss<best[0]:best=(loss,vc,ca,cb)
 return best
h=highsplit(hi);vc=h[1];regions=[sel&(u<cut),sel&(u>=cut)&(v<vc),sel&(u>=cut)&(v>=vc)];cs=[fit(m) for m in regions];pred=sum(np.where(m,A@c,0) for m,c in zip(regions,cs));checks={}
for axis,arr in [('u',u),('v',v)]:
 folds=np.floor((arr-arr[sel].min())/5).astype(int)%3;errs=[];records=[]
 for k in range(3):
  test=sel&(folds==k);tr=sel&~test;bt=train(tr);ht=highsplit(tr&(u>=bt[1]));rt=[test&(u<bt[1]),test&(u>=bt[1])&(v<ht[1]),test&(u>=bt[1])&(v>=ht[1])];err=np.concatenate([z[m]-A[m]@c for m,c in zip(rt,[bt[2],ht[2],ht[3]])]);errs.extend(err);records.append({'fold':k,'u_cut':bt[1],'v_cut':ht[1],**metric(err)})
 checks[axis]={'pooled':metric(np.array(errs)),'folds':records}
polys=[pu.buffer(-4).intersection(box(-1000,-1000,cut,1000)),pu.buffer(-4).intersection(box(cut,-1000,1000,vc)),pu.buffer(-4).intersection(box(cut,vc,1000,1000))]
rows=[]
for name,m,c,q in zip(['west_low','main_south','main_north'],regions,cs,polys):
 xy=transform(lambda u,v:(np.array(u)*np.cos(theta)-np.array(v)*np.sin(theta),np.array(u)*np.sin(theta)+np.array(v)*np.cos(theta)),q)
 rows.append({'name':name,'cells':int(m.sum()),'plane_odn_coefficients_intercept_u_v':c.tolist(),'in_sample':metric((z-A@c)[m]),'support_polygon_local_xy':list(map(list,xy.exterior.coords)),'support_area_m2':xy.area,'dsm_median_odn_m':float(np.median(z[m]))})
report={'building_id':ID,'coordinate_rotation_deg':-10,'u_formula':'x*cos(theta)+y*sin(theta)','v_formula':'-x*sin(theta)+y*cos(theta)','u_cut':cut,'v_cut':vc,'regions':rows,'spatial_holdout':checks,'selection':'4m geometrical footprint inset, all native valid cells; no height or residual filtering. Cut positions selected by training-only capped absolute residual loss; validation includes all held-out cells.','geometry_modified':False,'limitations':['Exploratory partition family and scan range chosen after prior DSM plan inspection; held-out errors do not cover this initial selection.','Piecewise planes cannot resolve equipment, parapets or raster mixing; support polygons are geometric domains, not verified architectural boundaries.','Mixed2017–2020 EA DSM ODN vs2026 Overture footprint; no ground conversion, no facade height inference.','No scene integration authorized by this diagnostic; coordinator must inspect metrics before building patches.'],'visual_reviewed':False}
fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for ax,cmap,vals,title in [(axs[0],'viridis',z,'Observed DSM ODN'),(axs[1],'viridis',pred,'Exploratory piecewise planes'),(axs[2],'RdBu_r',z-pred,'All-cell residual')]:
 im=ax.scatter(u[sel],v[sel],c=vals[sel],s=12,marker='s',cmap=cmap,**({'vmin':-3,'vmax':3} if ax==axs[2] else {'vmin':50,'vmax':101}));fig.colorbar(im,ax=ax);ax.axvline(cut,c='red');ax.axhline(vc,c='red');ax.set(aspect='equal',xlabel='u (m)',ylabel='v (m)',title=title)
fig.savefig(R/'references/credit_main_regions.png',dpi=150);(R/'references/credit_main_regions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cuts':[cut,vc],'regions':[{k:r[k] for k in ['name','cells','in_sample','dsm_median_odn_m']} for r in rows],'holdout':checks},indent=2))
