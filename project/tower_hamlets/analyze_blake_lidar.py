"""Blake House held-out gable fit; no global scene edits."""
import json,hashlib
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-3b9aad91-d3b2-4f3d-bac6-fc4a664ba1d1');p=Polygon(f['geometry'][0]['outer'],f['geometry'][0]['holes']);cx,cy=p.centroid.coords[0]
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(5)).bounds,ds.transform).round_offsets().round_lengths();z=ds.read(1,window=w,masked=True);ground=dt.read(1,window=w,masked=True);rr,cc=np.indices(z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(z.shape),np.array(yy).reshape(z.shape))
valid=~np.ma.getmaskarray(z)&~np.ma.getmaskarray(ground);m=valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);inner=valid&np.array([p.buffer(-1.5).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
xy=np.column_stack([x[inner]-cx,y[inner]-cy]);zz=np.asarray(z)[inner];train=(rr[inner]+cc[inner])%2==0
v=np.array(p.minimum_rotated_rectangle.exterior.coords);ed=np.diff(v,axis=0);u=ed[np.argmax(np.linalg.norm(ed,axis=1))];theta=np.arctan2(u[1],u[0])
def pred(par,xy):
 top,slope,offset,angle=par;b=-np.sin(angle)*xy[:,0]+np.cos(angle)*xy[:,1];return top-slope*np.abs(b-offset)
fits=[]
for a in [theta,theta+np.pi/2]:
 fit=least_squares(lambda par:pred(par,xy[train])-zz[train],[float(np.percentile(zz,95)),.5,0,a],bounds=([float(zz.min()),0,-8,a-.25],[float(zz.max()+4),2,8,a+.25]),loss='soft_l1',f_scale=.3)
 residual=pred(fit.x,xy[~train])-zz[~train];fits.append((float(np.sqrt(np.mean(residual**2))),fit.x))
rmse,par=min(fits,key=lambda t:t[0]);res=pred(par,xy[~train])-zz[~train];datum=float(np.median(np.asarray(ground)[m]));cross=-np.sin(par[3])*xy[:,0]+np.cos(par[3])*xy[:,1]
report={'feature_id':f['id'],'source_ids':['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],'hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'centroid_local_xy':[cx,cy],'fit_parameters':dict(zip(['ridge_odn_m','slope','ridge_offset_m','ridge_angle_rad'],map(float,par))),'ground_scalar_odn_m':datum,'ridge_scene_m':float(par[0]-datum),'training_count':int(train.sum()),'heldout_count':int((~train).sum()),'heldout_rmse_m':rmse,'heldout_p95_abs_error_m':float(np.percentile(abs(res),95)),'footprint_area_m2':p.area,'dsm_range_m_odn':[float(zz.min()),float(zz.max())],'limitations':['1m gridded DSM, mixed 2017–2020 surveys; neighbouring holdout samples are spatially correlated.','Local DTM median subtracts datum for flat scene convention, not surveyed foundations.','Roof protrusions and fine roof boundaries unresolved.'],'geometry_modified':False}
report.update({'recommendation':'Do not integrate a closed gable yet: fitted ridge lies near northern side and systematic southern residuals suggest multiple roof levels or edge mixing. Preserve baseline pending independent roof topology evidence.', 'fit_model_accepted_for_full_building':False, 'visual_review':{'inspected':True,'image':'blake_lidar_review.png','observations':['North roof high region and long southward descending surface are visible.','Best two-plane ridge is strongly displaced from footprint centre; a centred longitudinal generic gable is contradicted.','Southern protrusion and edges have very low returns; extrapolating two planes onto the whole footprint would invent unresolved eaves.','Held-out errors are systematic, not merely random; low global RMSE does not certify roof topology.']}})
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');im=axs[0].scatter(x[m],y[m],c=np.asarray(z)[m],s=38,marker='s');axs[0].plot(*p.exterior.xy,c='red');axs[0].set_aspect('equal');fig.colorbar(im,ax=axs[0],label='DSM m ODN');axs[0].set_title('Exact mapped footprint')
axs[1].scatter(cross,zz,s=13,label='1.5m interior');bb=np.linspace(cross.min(),cross.max(),100);axs[1].plot(bb,par[0]-par[1]*abs(bb-par[2]),c='red',label='Training fit');axs[1].set(xlabel='Across fitted ridge (m)',ylabel='DSM m ODN');axs[1].legend();axs[2].scatter(cross[~train],res,s=15);axs[2].axhline(0,c='black');axs[2].set(xlabel='Across fitted ridge (m)',ylabel='Held-out prediction minus DSM (m)',title=f'RMSE {rmse:.2f} m');fig.suptitle('Blake House — gabled roof evidence test');fig.savefig(R/'references/blake_lidar_review.png',dpi=150)
(R/'references/blake_lidar_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
