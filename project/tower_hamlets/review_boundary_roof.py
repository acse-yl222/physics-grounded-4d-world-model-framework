"""Inspect spatial support before changing the largest unnamed height candidate."""
from pathlib import Path
import json,hashlib
import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((R/'geometry.json').read_text());bid='overture-building-3517b4a8-54a6-42a3-b981-90c5cafa55f4'
f=next(f for f in g['buildings'] if f['id']==bid);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);inner=p.buffer(-2)
tx=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tx.transform,p.buffer(3)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));a=ds.read(1,window=w,masked=True);b=dt.read(1,window=w,masked=True);rr,cc=np.indices(a.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.asarray(xx).reshape(a.shape),np.asarray(yy).reshape(a.shape));valid=~np.ma.getmaskarray(a)&~np.ma.getmaskarray(b)
inside=np.array([p.contains(Point(q,r)) for q,r in zip(x.flat,y.flat)]).reshape(a.shape);inset=np.array([inner.contains(Point(q,r)) for q,r in zip(x.flat,y.flat)]).reshape(a.shape);h=np.asarray(a-b);sel=inside&valid
fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained');im=axs[0].scatter(x[sel],y[sel],c=h[sel],s=4,cmap='viridis',vmin=0,vmax=15);fig.colorbar(im,ax=axs[0],label='DSM minus DTM (m)');axs[0].plot(*p.exterior.xy,'r-',lw=.8);axs[0].set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)',title='Valid raster support inside full footprint');axs[1].hist(h[sel],bins=60,alpha=.5,label='Full footprint');axs[1].hist(h[inset&valid],bins=40,alpha=.7,label='2 m inset');axs[1].set(xlabel='DSM minus DTM (m)',ylabel='Native cells');axs[1].legend();fig.savefig(R/'references/boundary_roof_support.png',dpi=150)
report={'building_id':bid,'footprint_area_m2':p.area,'inset_area_m2':inner.area,'footprint_cells':int(inside.sum()),'valid_footprint_cells':int(sel.sum()),'inset_cells':int(inset.sum()),'valid_inset_cells':int((inset&valid).sum()),'height_quantiles_m':np.quantile(h[sel],[0,.1,.5,.9,1]).tolist(),'boundary_crossing':f['boundary_crossing'],'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'geometry_modified':False,'limitations':['Native raster support may cover only a fraction of an intersecting building.','Mixed capture dates; no facade or roof classification from image evidence.','Do not apply an interior statistic to the whole building without coverage review.']}
(R/'references/boundary_roof_support.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'},indent=2))
