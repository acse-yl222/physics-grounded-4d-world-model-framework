"""Bounded read-only tower207 elevation audit; no geometry mutation."""
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
g=json.loads((ROOT/'geometry.json').read_text()); f=next(f for f in g['buildings'] if f['id']=='overture-building-207561e0-862a-4afb-9e96-615ffffec8ba');p=Polygon(f['geometry'][0]['outer'])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(35)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm);nh=z-ground
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4,5]}
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()}
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u/=np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1];m=masks['0'];inner=masks['3']
rep={'building_id':f['id'],'geometry_modified':False,'current_height_m':f['height_m'],'source_num_floors':f['source_properties']['num_floors'],'height_source':'Microsoft ML Buildings property in Overture; height label source_reported does not mean survey measurement','source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'axis_local_xy':u.tolist(),'centroid_local_xy':[cx,cy],'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[mask]),'dtm_odn':stats(ground[mask]),'relative':stats(nh[mask]),'fraction_dsm_above_130_odn':float(np.mean(z[mask]>130))} for k,mask in masks.items()},'ground_scalar_m_odn':float(np.median(ground[m])),'neighbour_overlap':[],'bins':[],'visual_review':{'inspected':True,'image':'tower207_lidar_review.png','observations':['A coherent high roof occupies approximately the eastern 54m of the 73m long mapped footprint, with stepped plateaux around 138–149m ODN.','The western strip has extensive ground-level and approximately 27m ODN returns. It is not justified to raise this entire strip to the tower roof.','High returns extend beyond the mapped south edge by several metres; footprint and historical survey alignment need independent checking.','Interior roof plateaux are coherent, but ground returns along the north edge are patchy and must not be automatically interpreted as physical holes.'],'recommendation':'Do not apply a single high extrusion or fit a closed stepped tower to the full source footprint. Retain the baseline until tower/podium boundaries or historical alignment can be corroborated. The raster is sufficient to contradict current 11.8m height over the eastern part, but insufficient to establish all exterior walls.'},'uncertainties':['Mixed 2017–2020 survey compared to 2026 source footprints; per-pixel vintage unresolved.','Native 1m raster cannot resolve facade bays, parapets or roof machinery.','Ground scalar maps ODN to unsurveyed flat scene convention; not foundation survey.','Source 26 floors supports a tall tower but does not fix height.']}
for nf in g['buildings']:
 if nf['id'] in [f['id'],'site-support']:continue
 for geom in nf['geometry']:
  q=Polygon(geom['outer'],geom.get('holes',[]));area=p.intersection(q).area
  if area>.01:rep['neighbour_overlap'].append({'id':nf['id'],'name':nf['name'],'intersection_area_m2':area})
for left in np.arange(-40,40,2):
 mm=inner&(a>=left)&(a<left+2)
 if mm.any():rep['bins'].append({'long_axis_range_m':[float(left),float(left+2)],'dsm_odn':stats(z[mm])})
# Axis strips expose footprint/roof disagreement rather than hiding it in a median.
rep['axis_strip_statistics']=[]
for left,right in [(-37,-20),(-20,0),(0,16),(16,20),(20,25),(25,37)]:
 mm=m&(a>=left)&(a<right)
 rep['axis_strip_statistics'].append({'long_axis_range_m':[left,right],'dsm_odn':stats(z[mm]),'ground_return_fraction_below_10m_odn':float(np.mean(z[mm]<10)),'high_roof_fraction_above_130m_odn':float(np.mean(z[mm]>130))})
rep['coherent_upper_returns']={'count':int(np.sum(m&(z>130))),'dsm_odn':stats(z[m&(z>130)]),'scene_z_quantiles_after_local_ground_subtraction_m':stats(z[m&(z>130)]-rep['ground_scalar_m_odn'])}
rep['module_readiness']={'ready':False,'reason':'Mapped footprint includes low western strip and roof extends beyond southern boundary; full exterior partition requires further evidence. No geometry or module registration altered.'}
rep['axis_definition']='Long axis follows longest source edge (approximately westwards); positive long axis is western strip.'
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
ax=axs[0,0];im=ax.scatter(x,y,c=nh,s=12,marker='s',vmin=0,vmax=160,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM − DTM (m)')
for nf in g['buildings']:
 for geom in nf['geometry']:
  q=Polygon(geom['outer'])
  if q.intersects(p.buffer(35)):
   px,py=q.exterior.xy;ax.plot(px,py,color='red' if nf['id']==f['id'] else 'white',lw=2 if nf['id']==f['id'] else .8)
ax.set(xlim=(x.min(),x.max()),ylim=(y.min(),y.max()),title='Target red; current footprint context white',xlabel='Local E (m)',ylabel='Local N (m)');ax.set_aspect('equal')
ax=axs[0,1];im=ax.scatter(a[m],b[m],c=z[m],marker='s',s=35,vmin=0,vmax=150,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM m ODN');ax.set(title='Exact footprint; low returns clipped to purple',xlabel='Long axis (m)',ylabel='Cross axis (m)');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],a,'Long axis'),(axs[1,1],b,'Cross axis')]:
 ax.scatter(c[m],z[m],s=7,alpha=.3,label='All footprint DSM');ax.scatter(c[inner],z[inner],s=9,alpha=.5,label='3m interior DSM');ax.axhline(f['height_m']+rep['ground_scalar_m_odn'],c='red',label='Current model top + local ground');ax.set(xlabel=label+' (m)',ylabel='DSM m ODN',title=label+' profile');ax.legend(fontsize=8)
fig.suptitle('Tower 207561e0 — ML 11.8m height versus EA elevation evidence')
fig.savefig(ROOT/'references/tower207_lidar_review.png',dpi=150)
(ROOT/'references/tower207_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({k:v for k,v in rep.items() if k not in ['bins','source_hashes']},indent=2))
