"""Bounded read-only tower483 elevation audit; no geometry mutation."""
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
g=json.loads((ROOT/'geometry.json').read_text()); f=next(f for f in g['buildings'] if f['id']=='overture-building-48368bf5-55ba-41c3-a258-75d51b54dc60');p=Polygon(f['geometry'][0]['outer'])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(35)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm);nh=z-ground
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4,5]}
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()}
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u/=np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1];m=masks['0'];inner=masks['3']
rep={'building_id':f['id'],'geometry_modified':False,'current_height_m':f['height_m'],'source_num_floors':f['source_properties']['num_floors'],'height_source':'Microsoft ML Buildings property in Overture; height label source_reported does not mean survey measurement','source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'axis_local_xy':u.tolist(),'centroid_local_xy':[cx,cy],'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[mask]),'dtm_odn':stats(ground[mask]),'relative':stats(nh[mask]),'fraction_dsm_above_220_odn':float(np.mean(z[mask]>220))} for k,mask in masks.items()},'ground_scalar_m_odn':float(np.median(ground[m])),'neighbour_overlap':[],'bins':[],'visual_review':{'inspected':True,'image':'tower483_lidar_review.png','observations':['High roof returns occupy most target footprint with no neighbouring building overlap; this is not merely neighbouring tower contamination.','Low scattered returns concentrate near north end and edges; these do not establish physical roof openings.','Central higher roof region and lower perimeter band are visible, but 1m raster does not establish actual parapet or plant boundaries.','Current 26.666m top is strongly contradicted by coherent returns around 231–240m ODN and source 75 floors.'],'recommendation':'Correct dominant tower height using corroborated architectural height once identity is confirmed. Do not fit all dropouts into a corrugated roof or infer facade openings. Roof massing may use explicitly estimated upper central region only after separate boundary review.'},'uncertainties':['Mixed 2017–2020 survey compared to 2026 source footprints; per-pixel vintage unresolved.','Native 1m raster cannot resolve facade bays, parapets or roof machinery.','Ground scalar maps ODN to unsurveyed flat scene convention; not foundation survey.','Source 75 floors supports a tall tower but does not fix height.']}
for nf in g['buildings']:
 if nf['id'] in [f['id'],'site-support']:continue
 for geom in nf['geometry']:
  q=Polygon(geom['outer'],geom.get('holes',[]));area=p.intersection(q).area
  if area>.01:rep['neighbour_overlap'].append({'id':nf['id'],'name':nf['name'],'intersection_area_m2':area})
for left in np.arange(-25,25,2):
 mm=inner&(a>=left)&(a<left+2)
 if mm.any():rep['bins'].append({'long_axis_range_m':[float(left),float(left+2)],'dsm_odn':stats(z[mm])})
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
ax=axs[0,0];im=ax.scatter(x,y,c=nh,s=12,marker='s',vmin=0,vmax=250,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM − DTM (m)')
for nf in g['buildings']:
 for geom in nf['geometry']:
  q=Polygon(geom['outer'])
  if q.intersects(p.buffer(35)):
   px,py=q.exterior.xy;ax.plot(px,py,color='red' if nf['id']==f['id'] else 'white',lw=2 if nf['id']==f['id'] else .8)
ax.set(xlim=(x.min(),x.max()),ylim=(y.min(),y.max()),title='Target red; current footprint context white',xlabel='Local E (m)',ylabel='Local N (m)');ax.set_aspect('equal')
ax=axs[0,1];im=ax.scatter(a[m],b[m],c=z[m],marker='s',s=35,vmin=210,vmax=245,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM m ODN');ax.set(title='Exact footprint; low returns clipped to purple',xlabel='Long axis (m)',ylabel='Cross axis (m)');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],a,'Long axis'),(axs[1,1],b,'Cross axis')]:
 ax.scatter(c[m],z[m],s=7,alpha=.3,label='All footprint DSM');ax.scatter(c[inner],z[inner],s=9,alpha=.5,label='3m interior DSM');ax.axhline(f['height_m']+rep['ground_scalar_m_odn'],c='red',label='Current model top + local ground');ax.set(xlabel=label+' (m)',ylabel='DSM m ODN',title=label+' profile');ax.legend(fontsize=8)
fig.suptitle('Tower 48368bf5 — ML 26.7m height versus EA elevation evidence')
fig.savefig(ROOT/'references/tower483_lidar_review.png',dpi=150)
(ROOT/'references/tower483_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({k:v for k,v in rep.items() if k not in ['bins','source_hashes']},indent=2))
