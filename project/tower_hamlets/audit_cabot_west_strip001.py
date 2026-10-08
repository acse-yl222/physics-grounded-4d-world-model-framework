from pathlib import Path
import json,numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/cabot-facade-correspondence-002';g=json.loads((R/'geometry.json').read_text());d=json.loads((R/'references/dfbe_authoring003.json').read_text());p=Polygon(d['source_geometry']['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(3)).bounds,ds.transform).round_offsets().round_lengths();Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
zone=d['zones'][2];poly=Polygon(zone['geometry'][0]['outer']);mask=~np.ma.getmaskarray(Z)&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z);ground=np.asarray(G);fig,axs=plt.subplots(1,2,figsize=(13,8));im=axs[0].scatter(x[mask],y[mask],c=z[mask],s=35,vmin=5,vmax=33);fig.colorbar(im,ax=axs[0],label='DSM ODN m');axs[0].plot(*poly.exterior.xy,c='black');axs[0].set_aspect('equal');axs[0].set_title('All valid west-strip cells; no roof-height filtering');axs[1].scatter(y[mask],z[mask],s=12,label='DSM');axs[1].scatter(y[mask],ground[mask],s=10,label='DTM');axs[1].axhline(zone['roof_median_odn_m'],c='red',label='retained strip plane');axs[1].legend();axs[1].set(xlabel='scene northing m',ylabel='ODN m');fig.tight_layout();fig.savefig(O/'west_strip_returns.png',dpi=150)
report={'all_strip_count':int(mask.sum()),'odn_quantiles':np.percentile(z[mask],[0,10,25,50,75,90,100]).tolist(),'near_dtm_10cm':int(np.sum(abs(z[mask]-ground[mask])<=.1)),'bands':[]}
for name,a,b in [('south',-34,-14),('curve',-14,-3),('north',-3,17)]:
 m=mask&(y>=a)&(y<b);report['bands'].append({'name':name,'count':int(m.sum()),'odn_quantiles':np.percentile(z[m],[0,10,25,50,75,90,100]).tolist(),'low15_19':int(np.sum((z[m]>15)&(z[m]<19))),'high_above25':int(np.sum(z[m]>25))})
(O/'west_strip_returns.json').write_text(json.dumps(report,indent=2));print(report)
