"""Pizza Pilgrims roof profile and evidence-limited candidate; no assembly edits."""
import json,hashlib
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-e998ecb0-c626-483c-a6ec-f516b693fd78');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']

from scipy.optimize import least_squares
theta=np.deg2rad(-10);u=x*np.cos(theta)+y*np.sin(theta);v=-x*np.sin(theta)+y*np.cos(theta);sel=masks['2']&(z>18)&(z<22);train=sel&(np.floor(u/3).astype(int)%3!=1);test=sel&~train;knots=np.arange(np.ceil(v[train].min()),np.floor(v[train].max())+1)
def basis(a):return np.array([np.interp(a,knots,q) for q in np.eye(len(knots))]).T
B=basis(v[train]);D=np.diff(np.eye(len(knots)),2,axis=0);fit=least_squares(lambda c:np.r_[B@c-z[train],.15*D@c],np.full(len(knots),20.5),loss='soft_l1',f_scale=.1);pred=(basis(v.flat)@fit.x).reshape(v.shape);err=z[test]-pred[test]
fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained');axs[0].scatter(v[sel],z[sel],s=8,alpha=.25);axs[0].plot(knots,fit.x,c='red');axs[0].set(title='Pizza Pilgrims: repeated roof profile',xlabel='Across row m',ylabel='ODN m');im=axs[1].scatter(u[sel],v[sel],c=(z-pred)[sel],vmin=-.5,vmax=.5,cmap='RdBu_r');fig.colorbar(im,ax=axs[1],label='Observed minus predicted m');axs[1].set(title='Spatial residuals',xlabel='Along row m',ylabel='Across row m',aspect='equal');fig.savefig(ROOT/'references/pizza_profile_fit.png',dpi=140)
d={'selection':'2m inward footprint,18<DSM<22ODN','holdout':'Every third3m longitudinal strip','train_cells':int(train.sum()),'test_cells':int(test.sum()),'rmse_m':float(np.sqrt(np.mean(err**2))),'p95_abs_m':float(np.percentile(abs(err),95)),'knots_v_m':knots.tolist(),'height_odn_m':fit.x.tolist(),'rotation_deg':-10,'datum_odn_m':4.28000021,'limitations':['Conditional interior fit, not whole roof validation.','Boundary highs may belong to neighbors; low edge cells excluded.','Spline knots not independently measured architectural breaklines.'],'visual_reviewed':False};(ROOT/'references/pizza_profile_fit.json').write_text(json.dumps(d,indent=2)+'\n');print({k:d[k] for k in ['train_cells','test_cells','rmse_m','p95_abs_m']})

supported=masks['2']&(v>=knots[0])&(v<=knots[-1])&(np.abs(z-pred)<=.3)
vertices=[];faces=[];lookup={};area=0
for row in range(z.shape[0]-1):
 for col in range(z.shape[1]-1):
  for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
   if not all(supported[i,j] for i,j in ij):continue
   poly=Polygon([(x[i,j],y[i,j]) for i,j in ij])
   if not p.covers(poly):continue
   inds=[]
   for i,j in ij:
    if (i,j) not in lookup:
     lookup[i,j]=len(vertices);vertices.append([float(x[i,j]),float(y[i,j]),float(pred[i,j]-4.28000021)])
    inds.append(lookup[i,j])
   vv=np.array([vertices[k] for k in inds])
   if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
   faces.append(inds);area+=poly.area
out=ROOT/'references/pizza_profile_roof.obj'
with out.open('w') as handle:
 handle.write('# Fitted roof profile at observed supported cells; open gaps unknown; ENU metres\n')
 for vertex in vertices:handle.write('v '+' '.join(f'{q:.8f}' for q in vertex)+'\n')
 for face in faces:handle.write('f '+' '.join(str(k+1) for k in face)+'\n')
report={'building_id':f['id'],'method':'Cross-section interpolated fit, limited to native cells within0.3m observed residual and2m inward boundary; no walls or extrapolation','vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'footprint_area_m2':p.area,'ground_offset_odn_m':4.28000021,'all_triangles_inside_outline':True,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'limitations':['Conditional fitted surface, not raw DSM or independently surveyed architecture.','Gaps mean unsupported observations, not actual openings.','Neighboring high returns and low boundary returns excluded.','Shared North Quay datum 4.28000021 ODN; scene terrain remains flat.']}
(ROOT/'references/pizza_profile_roof.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

# Keep the original conditional holdout result, including coherent edge residuals.
core=test&(v>=181)&(v<=199)
core_err=(z-pred)[core]
d.update({'building_id':f['id'],'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'visual_reviewed':True,'visual_observations':['Three ridge bands are supported by native DSM.','Coherent low returns at across-row 178–181m and a localized mismatch around 200–202m remain unresolved.','Geometry excludes residuals above 0.3m; this residual filtering is not independent validation.'],'posthoc_core_diagnostic':{'selection':'Previously held-out cells with 181<=v<=199, selected after viewing residuals; not independent model selection','cells':int(core.sum()),'rmse_m':float(np.sqrt(np.mean(core_err**2))),'p95_abs_m':float(np.percentile(abs(core_err),95))},'decision':'Partial interior candidate only; do not extrapolate across coherent edge mismatches or replace complete native roof.'})
(ROOT/'references/pizza_profile_fit.json').write_text(json.dumps(d,indent=2)+'\n')
report['fit_report']='pizza_profile_fit.json'
report['source_ids']=d['source_ids'];report['source_hashes']=d['source_hashes'];report['conditional_holdout_rmse_m']=d['rmse_m'];report['status']='partial_candidate_only'
(ROOT/'references/pizza_profile_roof.json').write_text(json.dumps(report,indent=2)+'\n')
