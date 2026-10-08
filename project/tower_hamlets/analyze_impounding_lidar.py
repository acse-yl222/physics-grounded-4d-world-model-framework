"""Bounded EA raster inspection and robust gable fit; no global geometry edits."""
import json, hashlib
from pathlib import Path
import numpy as np
import rasterio
from shapely.geometry import Polygon, Point
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text()); f=next(f for f in g['buildings'] if f['id']=='overture-building-0741fd47-87f3-49ff-918c-e37ae2390289'); p=Polygon(f['geometry'][0]['outer'])
back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds, rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 z=ds.read(1,masked=True); ground=dt.read(1,masked=True); rr,cc=np.indices(z.shape); xx,yy=rasterio.transform.xy(ds.transform,rr,cc); x,y=back.transform(np.array(xx).reshape(z.shape),np.array(yy).reshape(z.shape))
near=(x>p.bounds[0]-12)&(x<p.bounds[2]+12)&(y>p.bounds[1]-12)&(y<p.bounds[3]+12);x=x[near];y=y[near];z=z[near];ground=ground[near];rr=rr[near];cc=cc[near]
valid=~np.ma.getmaskarray(z)&~np.ma.getmaskarray(ground);z=np.asarray(z);ground=np.asarray(ground)
m=np.array([p.contains(Point(a,b)) for a,b in zip(x,y)])&valid; inner=np.array([p.buffer(-1.5).contains(Point(a,b)) for a,b in zip(x,y)])&valid
v=np.asarray(p.exterior.coords); e=np.diff(v,axis=0); u=e[np.argmax(np.linalg.norm(e,axis=1))];u/=np.linalg.norm(u); v=np.array([-u[1],u[0]]);center=np.array(p.centroid.coords[0]);a=(np.column_stack([x,y])-center)@u;b=(np.column_stack([x,y])-center)@v
train=inner&((rr+cc)%2==0);test=inner&~train
# Ridge constrained inside footprint, slopes positive; robust fit does not discard residuals.
def pred(q,b):return q[0]-q[1]*np.abs(b-q[2])
fit=least_squares(lambda q:pred(q,b[train])-z[train],[float(np.percentile(z[train],85)),.4,0],bounds=([0,0,-3],[100,3,3]),loss='soft_l1',f_scale=.25);q=fit.x
err=pred(q,b[test])-z[test]; datum=float(np.median(ground[m])); plan=(np.array(p.exterior.coords)-center)@v
report={'building_id':f['id'],'name':f['name'],'footprint_area_m2':p.area,'valid_footprint_cells':int(m.sum()),'expected_approximate_cells':p.area,'interior_cells':int(inner.sum()),'original_height_m':f['height_m'],'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_sha256':{n:hashlib.sha256((ROOT/'references'/n).read_bytes()).hexdigest() for n in ['ea_dsm_1m.tif','ea_dtm_1m.tif']},'axis_local_xy':u.tolist(),'cross_axis_local_xy':v.tolist(),'centroid_xy':center.tolist(),'ground_scalar_odn_m':datum,'fit':{'ridge_odn_m':float(q[0]),'slope':float(q[1]),'ridge_cross_offset_m':float(q[2]),'ridge_scene_m':float(q[0]-datum),'edge_scene_m':(pred(q,np.array([plan.min(),plan.max()]))-datum).tolist(),'heldout_count':int(test.sum()),'heldout_rmse_m':float(np.sqrt(np.mean(err**2))),'heldout_p95_abs_m':float(np.percentile(abs(err),95)),'heldout_median_abs_m':float(np.median(abs(err)))},'dsm_quantiles_m_odn':np.percentile(z[m],[0,5,25,50,75,95,100]).tolist(),'visual_review':False,'limitations':['EA mixed 2017–2020 surveys versus 2026 footprint; historic roof state.','Scalar footprint DTM is a local height convention, not surveyed foundation.','One metre raster does not establish facade details or exact eaves.','Checkerboard heldout cells are spatially adjacent, not independent survey validation.']}

# Contiguous north-west low-return patch is evidence against blindly sealing a full roof.
low=inner & (z < pred(q,b)-3)
spatial_train=inner & (a<0); spatial_test=inner & (a>=0)
sf=least_squares(lambda t:pred(t,b[spatial_train])-z[spatial_train],q,bounds=([0,0,-3],[100,3,3]),loss='soft_l1',f_scale=.25)
se=pred(sf.x,b[spatial_test])-z[spatial_test]
report['spatial_holdout']={'train_rule':'Interior south half (long axis < 0); evaluate all north-half cells without trimming','train_count':int(spatial_train.sum()),'test_count':int(spatial_test.sum()),'ridge_odn_m':float(sf.x[0]),'slope':float(sf.x[1]),'offset_m':float(sf.x[2]),'rmse_m':float(np.sqrt(np.mean(se**2))),'p95_abs_m':float(np.percentile(abs(se),95))}
report['low_return_patch']={'interior_cells_more_than_3m_below_gable':int(low.sum()),'fraction_of_interior':float(low.sum()/inner.sum()),'xy_bounds_m':[float(x[low].min()),float(y[low].min()),float(x[low].max()),float(y[low].max())],'dsm_range_odn_m':[float(z[low].min()),float(z[low].max())],'interpretation':'Contiguous north-west patch reaches ground level. Actual aperture/roof damage, temporal mosaic, and return failure are unresolved alternatives; do not fill as measured roof or declare an opening.'}
report['visual_review']={'inspected':True,'image':'impounding_lidar_review.png','observations':['Most footprint returns trace two coherent roof planes, supporting the mapped along-axis gable.','North-west quadrant contains a contiguous near-ground patch extending well inside the footprint.','Upper surface has approximate ridge 9m above local DTM; source ML20.65m is not consistent with this historical raster.'],'recommendation':'Retain this as historical candidate evidence. A closed full-footprint pitched roof would fill an unresolved patch; await imagery or coordinator explicit estimated completion. No module authored.'}

fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');im=axs[0].scatter(x,y,c=z,s=30,marker='s',vmin=5,vmax=25);px,py=p.exterior.xy;axs[0].plot(px,py,'r');axs[0].set_aspect('equal');fig.colorbar(im,ax=axs[0],label='DSM m ODN');axs[0].set_title('Mapped footprint and DSM')
axs[1].scatter(b[m],z[m],s=12,label='All footprint');axs[1].scatter(b[inner],z[inner],s=8,label='Interior 1.5m');bb=np.linspace(plan.min(),plan.max(),100);axs[1].plot(bb,pred(q,bb),'r',label='Robust gable');axs[1].legend();axs[1].set(xlabel='Cross axis m',ylabel='ODN m',title='Cross roof profile')
axs[2].scatter(a[inner],z[inner]-pred(q,b[inner]),s=12);axs[2].axhline(0,color='r');axs[2].set(xlabel='Long axis m',ylabel='DSM minus fit m',title='Unfiltered interior residuals');fig.savefig(ROOT/'references/impounding_lidar_review.png',dpi=130)
(ROOT/'references/impounding_lidar_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
