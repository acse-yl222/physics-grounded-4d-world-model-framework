import json
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(x for x in g['buildings'] if 'c3bef968' in x['id']);p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(6)).bounds,ds.transform).round_offsets().round_lengths();w=w.intersection(rasterio.windows.Window(0,0,ds.width,ds.height));Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z);ground=float(np.median(np.asarray(G)[mask]));v=np.array(p.exterior.coords);e=np.diff(v,axis=0);u=e[np.argmax(np.linalg.norm(e,axis=1))];u/=np.linalg.norm(u);v=np.array([-u[1],u[0]]);c=np.array(p.centroid.coords[0]);a=(x-c[0])*u[0]+(y-c[1])*u[1];b=(x-c[0])*v[0]+(y-c[1])*v[1]
fig,axs=plt.subplots(1,3,figsize=(15,5));m=axs[0].scatter(a[mask],b[mask],c=z[mask]-ground,s=5,vmin=65,vmax=92);fig.colorbar(m,ax=axs[0],label='DSM minus scalar DTM (m)');axs[0].set(title='5 Canada exact footprint interior',xlabel='axis a metres',ylabel='axis b metres');axs[1].hist(z[mask]-ground,bins=80);axs[1].set(title='Elevation modes, not occupied-floor labels',xlabel='relative elevation m');axs[2].scatter(a[mask],z[mask]-ground,s=2,alpha=.3);axs[2].set(title='Axis profile',xlabel='a metres',ylabel='relative elevation m');fig.tight_layout();fig.savefig(R/'references/five_canada_roof_review.png',dpi=140)
bins=[]
for lo in np.arange(-40,40,5):
 mm=mask&(a>=lo)&(a<lo+5)
 if mm.any():bins.append({'a_range_m':[float(lo),float(lo+5)],'count':int(mm.sum()),'relative_q10_q50_q90_m':np.percentile(z[mm]-ground,[10,50,90]).tolist()})
report={'building_id':f['id'],'axis_u_xy':u.tolist(),'axis_v_xy':v.tolist(),'centroid_enu_xy':c.tolist(),'ground_scalar_m_odn':ground,'relative_percentiles_m':np.percentile(z[mask]-ground,[5,25,50,75,95]).tolist(),'axis_bins':bins,'scope':'Spatial DSM modes only; cannot distinguish trellis returns from occupied roofs without photos','source_geometry':f,'visual_reviewed':False};(R/'references/five_canada_roof_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_geometry'},indent=2))
