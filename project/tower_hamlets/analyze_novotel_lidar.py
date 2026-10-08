"""Bounded read-only novotel elevation audit; no geometry mutation."""
import json,hashlib
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
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text()); f=next(f for f in g['buildings'] if f['id']=='overture-building-55529b60-0de4-477d-957f-8278f55a225f');p=Polygon(f['geometry'][0]['outer'],f['geometry'][0].get('holes',[]))
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(35)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm);nh=z-ground
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4,5]}
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()}
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u/=np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1];m=masks['0'];inner=masks['3']
rep={'building_id':f['id'],'geometry_modified':False,'current_height_m':f['height_m'],'source_num_floors':f['source_properties']['num_floors'],'height_source':'Microsoft ML Buildings property in Overture; height label source_reported does not mean survey measurement','source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'axis_local_xy':u.tolist(),'centroid_local_xy':[cx,cy],'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[mask]),'dtm_odn':stats(ground[mask]),'relative':stats(nh[mask]),'fraction_dsm_above_110_odn':float(np.mean(z[mask]>110))} for k,mask in masks.items()},'ground_scalar_m_odn':float(np.median(ground[m])),'neighbour_overlap':[],'bins':[],'visual_review':{'inspected':True,'image':'novotel_lidar_review.png','observations':['Tall returns extend over the central and eastern footprint and northern lobe; no footprint overlap with neighbours was found.','Alternating strips of tall and near-ground returns run across the building, indicating severe sampling/dropout ambiguity rather than proven architectural slots.','Upper returns cluster around 119–127 m ODN; there is no clean closed boundary justifying a stepped roof from this raster.','DTM varies by several metres under the small footprint, so subtracting one scalar is only the flat-scene convention.'],'recommendation':'Replace clearly erroneous 3.829 m massing only as an explicitly approximate upper-envelope volume; do not interpret the low-return strips as courtyards or roof openings. Seek independent architectural height before fixing exact top.'},'footprint_area_m2':p.area,'hole_count':sum(len(q.get('holes',[])) for q in f['geometry']),'uncertainties':['Mixed 2017–2020 survey compared to 2026 source footprints; per-pixel vintage unresolved.','Native 1m raster cannot resolve facade bays, parapets or roof machinery.','Ground scalar maps ODN to unsurveyed flat scene convention; not foundation survey.','Source 39 floors supports a tall tower but does not fix height.']}
rep['upper_return_stats']={str(cut):{'dsm_odn':stats(z[m&(z>cut)]),'sample_count_area_m2_approx':int(np.sum(m&(z>cut)))} for cut in [110,115,120,123,125]}
rep['conservative_height_recommendation']={'method':'upper-return median with local DTM scalar, approximate massing only','dsm_sample_filter_m_odn':115,'roof_top_m_odn':float(np.median(z[m&(z>115)])),'scene_top_m':float(np.median(z[m&(z>115)])-rep['ground_scalar_m_odn']),'full_footprint_area_m2':p.area,'roof_step_boundaries_resolved':False,'height_uncertainty_not_statistical_interval_m':[114,125],'interval_basis':'Observed upper envelope about119–127 ODN minus uncertain local ground roughly2–5 ODN; no survey confidence interval.'}
for nf in g['buildings']:
 if nf['id'] in [f['id'],'site-support']:continue
 for geom in nf['geometry']:
  q=Polygon(geom['outer'],geom.get('holes',[]));area=p.intersection(q).area
  if area>.01:rep['neighbour_overlap'].append({'id':nf['id'],'name':nf['name'],'intersection_area_m2':area})
for left in np.arange(-25,25,2):
 mm=inner&(a>=left)&(a<left+2)
 if mm.any():rep['bins'].append({'long_axis_range_m':[float(left),float(left+2)],'dsm_odn':stats(z[mm])})
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
ax=axs[0,0];im=ax.scatter(x,y,c=nh,s=12,marker='s',vmin=0,vmax=135,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM − DTM (m)')
for nf in g['buildings']:
 for geom in nf['geometry']:
  q=Polygon(geom['outer'])
  if q.intersects(p.buffer(35)):
   px,py=q.exterior.xy;ax.plot(px,py,color='red' if nf['id']==f['id'] else 'white',lw=2 if nf['id']==f['id'] else .8)
ax.set(xlim=(x.min(),x.max()),ylim=(y.min(),y.max()),title='Target red; current footprint context white',xlabel='Local E (m)',ylabel='Local N (m)');ax.set_aspect('equal')
ax=axs[0,1];im=ax.scatter(a[m],b[m],c=z[m],marker='s',s=35,vmin=100,vmax=135,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM m ODN');ax.set(title='Exact footprint; low returns clipped to purple',xlabel='Long axis (m)',ylabel='Cross axis (m)');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],a,'Long axis'),(axs[1,1],b,'Cross axis')]:
 ax.scatter(c[m],z[m],s=7,alpha=.3,label='All footprint DSM');ax.scatter(c[inner],z[inner],s=9,alpha=.5,label='3m interior DSM');ax.axhline(f['height_m']+rep['ground_scalar_m_odn'],c='red',label='Current model top + local ground');ax.set(xlabel=label+' (m)',ylabel='DSM m ODN',title=label+' profile');ax.legend(fontsize=8)
fig.suptitle('Novotel — ML 3.8m height versus EA elevation evidence')
fig.savefig(ROOT/'references/novotel_lidar_review.png',dpi=150)
(ROOT/'references/novotel_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({k:v for k,v in rep.items() if k not in ['bins','source_hashes']},indent=2))
