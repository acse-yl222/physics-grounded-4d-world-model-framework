"""Bounded roof-shape falsification, no source geometry mutation."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text())
f=next(f for f in g['buildings'] if 'fff95900' in f['id']);p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(8)).bounds,ds.transform).round_offsets().round_lengths();d=ds.read(1,window=w,masked=True);ground=dt.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.asarray(xx).reshape(d.shape),np.asarray(yy).reshape(d.shape))
mask=np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)&~np.ma.getmaskarray(d);z=np.asarray(d);v=np.asarray(p.exterior.coords)[:-1];c=np.array(p.centroid.coords[0]);e=np.roll(v,-1,axis=0)-v;u=e[np.argmax(np.linalg.norm(e,axis=1))];u/=np.linalg.norm(u);vv=np.array([-u[1],u[0]]);a=(x-c[0])*u[0]+(y-c[1])*u[1];b=(x-c[0])*vv[0]+(y-c[1])*vv[1];local=(v-c)@np.array([u,vv]).T;ha=np.ptp(local[:,0])/2;hb=np.ptp(local[:,1])/2
# Single-apex pyramid hypothesis with fixed centroid, exact mapped rectangle orientation.
t=1-np.maximum(abs(a)/ha,abs(b)/hb);interior=mask&np.array([p.buffer(-.75).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);hold=((rr+2*cc)%3)==0;train=interior&~hold;test=interior&hold
A=np.column_stack([np.ones(train.sum()),t[train]]);coef=np.linalg.lstsq(A,z[train],rcond=None)[0];prediction=coef[0]+coef[1]*t;errors=z[test]-prediction[test]
report={'building_id':f['id'],'footprint_area_m2':p.area,'full_sample_count':int(mask.sum()),'training_count':int(train.sum()),'heldout_count':int(test.sum()),'hypothesis':'Single apex above mapped centroid, constant eaves; rectangle pyramid fractions','eave_m_odn':float(coef[0]),'rise_m':float(coef[1]),'apex_m_odn':float(sum(coef)),'heldout_rmse_m':float(np.sqrt(np.mean(errors**2))),'heldout_p95_abs_m':float(np.percentile(abs(errors),95)),'ground_median_odn':float(np.median(np.asarray(ground)[mask])),'dsm_percentiles_0_25_50_75_100':np.percentile(z[mask],[0,25,50,75,100]).tolist(),'geometry_modified':False,'visual_review':{'inspected':False},'limitations':['One metre DSM across only about five cells of roof width.','Mixed 2017–2020 survey does not certify contemporary condition.','Held-out cells share raster processing and are not independent survey observations.']}
report['numerical_decision']='Reject single positive-rise pyramid hypothesis: fitted rise is negative' if coef[1] <= 0 else 'Positive rise alone does not establish roof shape; visual review required'
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');im=axs[0].scatter(x,y,c=z,s=38,marker='s');fig.colorbar(im,ax=axs[0],label='DSM ODN m');axs[0].plot(*p.exterior.xy,c='red');axs[0].set_aspect('equal');axs[0].set_title('Mapped target red; full context DSM');axs[1].scatter(t[mask],z[mask],label='All footprint');axs[1].scatter(t[train],z[train],label='Training interior');axs[1].scatter(t[test],z[test],label='Held out interior');axs[1].plot([0,1],[coef[0],sum(coef)],c='red');axs[1].legend();axs[1].set(xlabel='Normalized pyramid fraction',ylabel='DSM ODN m',title='Single pyramid hypothesis');im=axs[2].scatter(a[mask],b[mask],c=(z-prediction)[mask],s=70,cmap='coolwarm');fig.colorbar(im,ax=axs[2],label='Observed minus fit m');axs[2].set_aspect('equal');axs[2].set_title('Spatial residuals, all footprint cells');fig.savefig(R/'references/pyramid_lidar_review.png',dpi=140);(R/'references/pyramid_lidar_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
