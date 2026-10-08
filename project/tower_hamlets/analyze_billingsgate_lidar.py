"""Bounded Billingsgate Market observed roof audit; does not alter assembly."""
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
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-1a29bc70-0dd1-46a9-badb-e3075f6c821a');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()} if len(v) else {'count':0}
rep={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'footprint_area_m2':p.area,'ground_scalar_m_odn':float(np.median(ground[m])),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[v]),'dtm_odn':stats(ground[v])} for k,v in masks.items()},'visual_review':{'inspected':False},'limitations':['Native 1m DSM, mixed 2017–2020 dates versus 2026 footprint.','ODN minus local median DTM maps to unsurveyed flat scene.','Façades, parapets, machinery and historical changes unresolved.']}
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
for ax,sel,title in [(axs[0,0],valid,'Context; target red; other outlines white'),(axs[0,1],m,'Exact footprint DSM (masked outside raster)')]:
 im=ax.scatter(x[sel],y[sel],c=z[sel],s=20,marker='s',vmin=0,vmax=55);fig.colorbar(im,ax=ax,label='DSM m ODN')
 for nf in g['buildings']:
  for q in nf['geometry']:
   poly=Polygon(q['outer'],q.get('holes',[]))
   if poly.intersects(p.buffer(20)):
    for ring in [poly.exterior,*poly.interiors]:
     px,py=ring.xy;ax.plot(px,py,c='red' if nf['id']==f['id'] else 'white',lw=1)
 ax.set(xlim=(x.min(),x.max()) if sel is valid else (p.bounds[0]-2,p.bounds[2]+2),ylim=(y.min(),y.max()) if sel is valid else (p.bounds[1]-2,p.bounds[3]+2),title=title,xlabel='Local E m',ylabel='Local N m');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],x,'East'),(axs[1,1],y,'North')]:
 ax.scatter(c[m],z[m],s=9,alpha=.3,label='Exact footprint');ax.scatter(c[inner],z[inner],s=10,alpha=.5,label='3m inward');ax.axhline(f['height_m']+rep['ground_scalar_m_odn'],c='red',label='Baseline source height + local ground');ax.set(xlabel=label+' local m',ylabel='DSM m ODN',title=label+' profile');ax.legend()
fig.suptitle('Billingsgate Market — measured roof distribution and retained mapped footprint');fig.savefig(ROOT/'references/billingsgate_lidar_review.png',dpi=140)
(ROOT/'references/billingsgate_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep,indent=2))
# Rotate profiles into the long mapped facade axes; do not fit noisy equipment.
coords=np.asarray(p.exterior.coords);edges=np.diff(coords,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u=u/np.linalg.norm(u)
if u[0]<0:u=-u
v=np.array([-u[1],u[0]]);origin=np.array(p.centroid.coords[0]);along=(x-origin[0])*u[0]+(y-origin[1])*u[1];across=(x-origin[0])*v[0]+(y-origin[1])*v[1]
fig,axs=plt.subplots(2,1,figsize=(14,8),layout='constrained');im=axs[0].scatter(along[m],across[m],c=z[m],vmin=13,vmax=17,s=8,marker='s');fig.colorbar(im,ax=axs[0],label='DSM m ODN');axs[0].set_aspect('equal');axs[0].set(xlabel='Along mapped long edge m',ylabel='Across m',title='Billingsgate roof — rotated native returns; clipped colour scale')
axs[1].scatter(across[masks['2']],z[masks['2']],s=2,alpha=.3);axs[1].set(xlabel='Across m',ylabel='DSM m ODN',ylim=(9,21),title='Cross-roof profile: all along-axis positions overlaid');fig.savefig(ROOT/'references/billingsgate_roof_axes.png',dpi=130)
rep['roof_axes']={'origin_local_xy_m':origin.tolist(),'along_unit':u.tolist(),'across_unit':v.tolist(),'diagnostic':'billingsgate_roof_axes.png'}
rep['visual_review']={'inspected':True,'image':'billingsgate_lidar_review.png','observations':['Main footprint has two broad elevation regions and repeated structured profile returns; blanket flat roof loses measured shape.','High isolated returns on northern roof cannot be identified as machinery from LiDAR alone.','Southeast corner includes ground-level returns; full roof closure requires separate examination.']}
(ROOT/'references/billingsgate_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
# Median cross-section fit. Entire alternating 20m longitudinal strips held out.
sel=masks['2']&(z>12)&(z<17);train=sel&((np.floor((along+160)/20).astype(int)%2)==0);test=sel&~train
bins=np.arange(-28,31,.5);centers=[];levels=[];counts=[]
for lo in bins[:-1]:
 q=train&(across>=lo)&(across<lo+.5)
 if q.sum()>=5:centers.append(lo+.25);levels.append(float(np.median(z[q])));counts.append(int(q.sum()))
centers=np.array(centers);levels=np.array(levels);pred=np.interp(across,centers,levels);res=z[test]-pred[test]
rep['cross_section_candidate']={'method':'0.5m across-axis bins with training median, linear interpolation between bins; no endpoint extrapolation authorized','holdout':'alternating 20m longitudinal strips','selection_dsm_odn_m':[12,17],'inward_buffer_m':2,'train_cells':int(train.sum()),'test_cells':int(test.sum()),'across_m':centers.tolist(),'elevation_odn_m':levels.tolist(),'training_counts':counts,'heldout_rmse_m':float(np.sqrt(np.mean(res**2))),'heldout_p95_abs_m':float(np.percentile(abs(res),95)),'scope':'Conditional broad roof profile, excludes high structures, low returns and footprint margins; no full enclosure validated.'}
fig,ax=plt.subplots(figsize=(12,5),layout='constrained');ax.scatter(across[test],z[test],s=2,alpha=.2,label='Held-out strip returns');ax.plot(centers,levels,color='red',label='Training median profile');ax.set(xlabel='Across roof m',ylabel='DSM m ODN',title='Billingsgate conditional roof profile — spatial holdout');ax.legend();fig.savefig(ROOT/'references/billingsgate_profile_fit.png',dpi=140)
rep['visual_review']['additional_inspected_image']='billingsgate_roof_axes.png';rep['visual_review']['observations'].append('Rotated cross-section resolves broad shallow pitched southern strip, a lower junction valley, and shallow inclined northern roof. Heights are not a sequence of arbitrary flat tiers.')
(ROOT/'references/billingsgate_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n');print({k:v for k,v in rep['cross_section_candidate'].items() if k not in ['across_m','elevation_odn_m','training_counts']})
