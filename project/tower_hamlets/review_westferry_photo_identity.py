"""Read-only mapped-owner and EA height checks for Ollie11491155 left frontage."""
import json,hashlib,warnings
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore',category=DeprecationWarning)
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());prefixes=['26bcb1ba','6019910a','3a202b7c'];fs=[b for b in g['buildings'] if any(k in b['id'] for k in prefixes)];ps=[unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]) for b in fs];fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,unary_union(ps).buffer(4)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);xx=np.array(xx).reshape(d.shape);yy=np.array(yy).reshape(d.shape);x,y=bk.transform(xx,yy)
with rasterio.open(R/'references/ea_dtm_1m.tif') as dt:t=np.array([q[0] for q in dt.sample(zip(xx.flat,yy.flat),masked=True)]).reshape(d.shape)
z=np.asarray(d,float);valid=~np.ma.getmaskarray(d)&np.isfinite(t)
fig,axs=plt.subplots(1,2,figsize=(14,8));rows=[]
for b,p,c in zip(fs,ps,['#c45e42','#3b83bf','#67a84f']):
 mask=valid&np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);vv=z[mask];tt=t[mask];q=[10,25,50,75,90,95];ground=float(np.median(tt));row={'building_id':b['id'],'name':b['name'],'mapped_height_m':b['height_m'],'height_basis':b['height_basis'],'mapped_centroid_enu_m':list(p.centroid.coords[0]),'roof_samples':len(vv),'dsm_odn_quantiles_m':dict(zip(q,map(float,np.percentile(vv,q)))),'dtm_median_m_odn':ground,'dsm_minus_local_dtm_quantiles_m':dict(zip(q,map(float,np.percentile(vv-tt,q)))),'height_caution':'Raw roof/terrain statistics; two-level Westferry Circus makes ground subtraction uncertain; not fitted replacement.'};rows.append(row)
 xx1,yy1=p.exterior.xy;axs[0].fill(xx1,yy1,color=c,alpha=.3);axs[0].plot(xx1,yy1,color=c);axs[0].text(p.centroid.x,p.centroid.y,b['name']+'\n'+b['id'].split('-')[2],ha='center',fontsize=9);axs[1].hist(vv,bins=70,histtype='step',color=c,label=b['name'])
# Shared boundary is mapped, not digitized from the photo or estate map.
for i,p in enumerate(ps):
 for j,q in enumerate(ps[:i]):
  seam=p.boundary.intersection(q.boundary)
  if seam.length>0:
   if seam.geom_type=='LineString':sx,sy=seam.xy;axs[0].plot(sx,sy,'k-',lw=4)
axs[0].set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)',title='Original mapped owners; black = shared boundary');axs[1].set(xlabel='EA DSM roof height (m ODN)',ylabel='Cells',title='Interior cells, >=2m from mapped edges');axs[1].legend();fig.tight_layout();fig.savefig(R/'references/westferry_photo_identity_height_review.png',dpi=170)
report={'geometry_modified':False,'source_ids':['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m','pexels_ollie_11491155','canary_wharf_alfresco_map_20210614'],'owners':rows,'interpretation':'Photo foreground-left continuous frontage spans candidate adjoining mapped owners; do not assign entire curved facade to Westferry House. 7 Westferry Circus and11WestferryCircus share mapped edge; eastern20ColumbusCourtyard has a separate footprint. Exact image seam unresolved.','hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'geometry.json',R/'references/pexels-ollie-craig-11491155.jpeg']}}
(R/'references/westferry_photo_identity_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
