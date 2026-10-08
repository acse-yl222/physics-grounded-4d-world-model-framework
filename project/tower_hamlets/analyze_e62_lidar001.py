"""Bounded Owner e62 observed roof audit; does not alter assembly."""
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
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-e62e0d16-3a06-4f9c-8bb4-f56b59e7eb3f');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()} if len(v) else {'count':0}
rep={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'footprint_area_m2':p.area,'ground_scalar_m_odn':float(np.median(ground[m])),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[v]),'dtm_odn':stats(ground[v])} for k,v in masks.items()},'visual_review':{'inspected':False},'limitations':['Native 1m DSM; actual local capture vintage unknown; 2026 footprint.','Scene roof z equals ODN minus shared 4.28000021m datum; local DTM not building base.','Façades, parapets, machinery and historical changes unresolved.']}
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
for ax,sel,title in [(axs[0,0],valid,'Context; target red; other outlines white'),(axs[0,1],m,'Exact footprint DSM (masked outside raster)')]:
 im=ax.scatter(x[sel],y[sel],c=z[sel],s=20,marker='s',vmin=0,vmax=140);fig.colorbar(im,ax=ax,label='DSM m ODN')
 for nf in g['buildings']:
  for q in nf['geometry']:
   poly=Polygon(q['outer'],q.get('holes',[]))
   if poly.intersects(p.buffer(20)):
    for ring in [poly.exterior,*poly.interiors]:
     px,py=ring.xy;ax.plot(px,py,c='red' if nf['id']==f['id'] else 'white',lw=1)
 ax.set(xlim=(x.min(),x.max()) if sel is valid else (p.bounds[0]-2,p.bounds[2]+2),ylim=(y.min(),y.max()) if sel is valid else (p.bounds[1]-2,p.bounds[3]+2),title=title,xlabel='Local E m',ylabel='Local N m');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],x,'East'),(axs[1,1],y,'North')]:
 ax.scatter(c[m],z[m],s=9,alpha=.3,label='Exact footprint');ax.scatter(c[inner],z[inner],s=10,alpha=.5,label='3m inward');ax.axhline(130+4.28000021,c='red',label='Retained roof scene130 + shared datum');ax.set(xlabel=label+' local m',ylabel='DSM m ODN',title=label+' profile');ax.legend()
fig.suptitle('Owner e62 — measured roof distribution and retained mapped footprint');fig.savefig(ROOT/'references/e62_lidar_review.png',dpi=140)
(ROOT/'references/e62_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep,indent=2))

fig,axs=plt.subplots(1,2,figsize=(14,8),layout='constrained')
for ax,lo,hi,title in [(axs[0],119,130,'Roof heights, clipped 119–130 m ODN'),(axs[1],0,140,'Categorical observed roof support')]:
 values=z if ax is axs[0] else np.select([z<30,(z>=120.7)&(z<=121.3),(z>=128.4)&(z<=128.9)],[0,1,3],default=2)
 im=ax.scatter(x[m],y[m],c=values[m],s=35,marker='s',vmin=lo if ax is axs[0] else 0,vmax=hi if ax is axs[0] else 3,cmap='viridis');cb=fig.colorbar(im,ax=ax)
 if ax is axs[1]:
  cb.set_ticks([0,1,2,3]);cb.set_ticklabels(['<30 m ODN','120.7–121.3','Other returns','128.4–128.9'])
 else: cb.set_label('m ODN')
 px,py=p.exterior.xy;ax.plot(px,py,c='red');ax.set_aspect('equal');ax.set(title=title,xlabel='Local E m',ylabel='Local N m')
fig.savefig(ROOT/'references/e62_roof_detail001.png',dpi=140)
rep['support_bands']={name: {'count':int(sel.sum()), 'median_odn':float(np.median(z[sel])) if sel.any() else None} for name,sel in {'low_below30':m&(z<30),'low_roof_120_7_to121_3':m&(z>=120.7)&(z<=121.3),'upper_128_4_to128_9':m&(z>=128.4)&(z<=128.9),'intermediate_121_3_to128_4':m&(z>121.3)&(z<128.4)}.items()}
rep['source_properties']=f['source_properties']
rep['centroid_lonlat']=Transformer.from_crs(g['crs'],4326,always_xy=True).transform(p.centroid.x,p.centroid.y)
(ROOT/'references/e62_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
