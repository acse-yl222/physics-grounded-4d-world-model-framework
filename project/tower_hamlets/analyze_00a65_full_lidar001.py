"""Bounded Owner 00a65 observed roof audit; does not alter assembly."""
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
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-00a6586d-4e69-408d-b251-4fd265162eff');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/school_pair_ea_dsm_1m_001.tif') as ds,rasterio.open(ROOT/'references/school_pair_ea_dtm_1m_001.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()} if len(v) else {'count':0}
rep={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/school_pair_ea_dsm_1m_001.tif','references/school_pair_ea_dtm_1m_001.tif']},'footprint_area_m2':p.area,'ground_scalar_m_odn':float(np.median(ground[m])),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[v]),'dtm_odn':stats(ground[v])} for k,v in masks.items()},'visual_review':{'inspected':False},'limitations':['Native 1m DSM; actual local capture vintage unknown; 2026 footprint.','Scene roof z equals ODN minus shared 4.28000021m datum; local DTM not building base.','Façades, parapets, machinery and historical changes unresolved.']}
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
for ax,sel,title in [(axs[0,0],valid,'Context; target red; other outlines white'),(axs[0,1],m,'Exact footprint DSM (masked outside raster)')]:
 im=ax.scatter(x[sel],y[sel],c=z[sel],s=20,marker='s',vmin=0,vmax=25);fig.colorbar(im,ax=ax,label='DSM m ODN')
 for nf in g['buildings']:
  for q in nf['geometry']:
   poly=Polygon(q['outer'],q.get('holes',[]))
   if poly.intersects(p.buffer(20)):
    for ring in [poly.exterior,*poly.interiors]:
     px,py=ring.xy;ax.plot(px,py,c='red' if nf['id']==f['id'] else 'white',lw=1)
 ax.set(xlim=(x.min(),x.max()) if sel is valid else (p.bounds[0]-2,p.bounds[2]+2),ylim=(y.min(),y.max()) if sel is valid else (p.bounds[1]-2,p.bounds[3]+2),title=title,xlabel='Local E m',ylabel='Local N m');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],x,'East'),(axs[1,1],y,'North')]:
 ax.scatter(c[m],z[m],s=9,alpha=.3,label='Exact footprint');ax.scatter(c[inner],z[inner],s=10,alpha=.5,label='3m inward');ax.axhline(9+4.28000021,c='red',label='Retained roof scene9 + shared datum');ax.set(xlabel=label+' local m',ylabel='DSM m ODN',title=label+' profile');ax.legend()
fig.suptitle('Owner 00a65 — measured roof distribution and retained mapped footprint');fig.savefig(ROOT/'references/00a65_full_lidar_review.png',dpi=140)
(ROOT/'references/00a65_full_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep,indent=2))

