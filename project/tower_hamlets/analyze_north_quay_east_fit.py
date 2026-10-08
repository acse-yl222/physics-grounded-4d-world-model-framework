"""Bounded eastern warehouse roof profiles; no assembly changes."""
import json,hashlib
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());meta=json.loads((R/'references/north_quay_roof_group.json').read_text())['features'];ids=['4216480f','06f82e7c','f8a7acd3'];fs=[f for f in g['buildings'] if any(i in f['id'] for i in ids)];polys=[unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]) for f in fs];p=unary_union(polys)
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(tr.transform,p.buffer(2)).bounds,ds.transform).round_offsets().round_lengths();a=ds.read(1,window=w,masked=True);rr,cc=np.indices(a.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(a.shape),np.array(yy).reshape(a.shape))
z=np.asarray(a);valid=~np.ma.getmaskarray(a);theta=np.deg2rad(-10.0);u=x*np.cos(theta)+y*np.sin(theta);v=-x*np.sin(theta)+y*np.cos(theta)
fig,axs=plt.subplots(3,3,figsize=(15,12),layout='constrained');rep={'datum_m_odn':4.28000021,'rotation_degrees':-10,'orientation':'u runs along warehouse row eastward; v crosses row northward; ridges primarily along v','source_ids':['ea_lidar_dsm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif']},'features':[],'geometry_modified':False,'limitations':['1m mixed-vintage DSM, no optical verification.','Robust four-plane hip candidate; edges, dormers and façades unresolved.','Height conversion uses common unsurveyed datum.'],'visual_review':{'inspected':False}}
for j,(f,poly) in enumerate(zip(fs,polys)):
 m=valid&np.array([poly.buffer(-2).contains(Point(q,t)) for q,t in zip(x.flat,y.flat)]).reshape(x.shape);sel=m&(z>21)&(z<26);U=u[sel];V=v[sel];Z=z[sel];uc=float(np.median(U));vc=float(np.median(V))
 # Fit separate slopes either side of ridge plus linear along-ridge trend.
 def pred(b,uu,vv):
  d=uu-b[1];main=b[0]+b[2]*np.minimum(d,0)+b[3]*np.maximum(d,0);return np.minimum(main,np.minimum(b[4]+b[5]*(vv-vc),b[6]+b[7]*(vv-vc)))
 def fit(mask):return least_squares(lambda b:pred(b,U[mask],V[mask])-Z[mask],[24.5,uc,.2,-.2,25,.2,25,-.2],bounds=([21,U.min(),0,-1,21,0,21,-1],[27,U.max(),1,0,30,1,30,0]),loss='soft_l1',f_scale=.15).x
 folds=[]
 for k in range(4):
  test=(np.floor((V-V.min())/max(np.ptp(V)+1e-6,1)*4).astype(int)==k);b=fit(~test);e=pred(b,U[test],V[test])-Z[test];folds.append({'cross_row_strip':k,'n':len(e),'rmse_m':float(np.sqrt(np.mean(e*e))),'median_abs_m':float(np.median(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95))})
 b=fit(np.ones(len(U),bool));e=pred(b,U,V)-Z;name=next(q['name'] for q in meta if q['id']==f['id']);rep['features'].append({'id':f['id'],'name':name,'selected_n':len(U),'inner_n':int(m.sum()),'selection':'2m eroded footprint, 21<DSM<26 ODN','parameters_ridge_odn_ridge_u_slope_w_slope_e_south_at_v0_south_slope_north_at_v0_north_slope':b.tolist(),'v_origin_m':vc,'spatial_holdout':folds,'fit_rmse_m':float(np.sqrt(np.mean(e*e))),'inlier_fraction_abs_residual_under_0_4m':float(np.mean(abs(e)<.4)),'integration_ready':False})
 ax=axs[j,0];im=ax.scatter(u[m],v[m],c=z[m],vmin=19,vmax=25,s=12);fig.colorbar(im,ax=ax);ax.set(title=name+' / aligned DSM',xlabel='u along row m',ylabel='v across row m');ax.set_aspect('equal');ax=axs[j,1];ax.scatter(U,Z,c=V,s=9,alpha=.6);uu=np.linspace(U.min(),U.max(),200);ax.plot(uu,pred(b,uu,vc),'r');ax.set(xlabel='u m',ylabel='ODN m',title='Hipped profile at median v');ax=axs[j,2];im=ax.scatter(U,V,c=e,cmap='coolwarm',vmin=-1,vmax=1,s=15);fig.colorbar(im,ax=ax,label='Fit minus DSM m');ax.set(title='Residual / withheld across-row strips',xlabel='u m',ylabel='v m');ax.set_aspect('equal')
fig.savefig(R/'references/north_quay_east_fit.png',dpi=130);(R/'references/north_quay_east_fit.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep,indent=2))
