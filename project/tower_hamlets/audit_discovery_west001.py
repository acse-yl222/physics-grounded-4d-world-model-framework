import json
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(x for x in g['buildings'] if '9846b4f7' in x['id']);p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True);ll=Transformer.from_crs(g['crs'],4326,always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(80)).bounds,ds.transform).round_offsets().round_lengths();w=w.intersection(rasterio.windows.Window(0,0,ds.width,ds.height));Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z);neighbors=[]
fig,ax=plt.subplots(figsize=(10,10));im=ax.scatter(x.flat,y.flat,c=(z-4.28000021).flat,s=2,vmin=0,vmax=160);fig.colorbar(im,ax=ax,label='DSM ODN minus shared4.28000021m')
for feat in g['buildings']:
 if feat['id']=='site-support':continue
 pp=unary_union([Polygon(t['outer'],t.get('holes',[])) for t in feat['geometry']])
 if pp.distance(p)>65:continue
 neighbors.append({'id':feat['id'],'name':feat['name'],'height_m':feat.get('height_m'),'parent_id':feat.get('parent_id'),'overlap_m2':pp.intersection(p).area,'centroid':list(pp.centroid.coords)[0]})
 for part in feat['geometry']:
  v=np.array(part['outer']+[part['outer'][0]]);ax.plot(v[:,0],v[:,1],color='red' if feat['id']==f['id'] else 'black',lw=2 if feat['id']==f['id'] else .7)
 ax.text(pp.centroid.x,pp.centroid.y,feat['name'][:14]+'\n'+feat['id'][-8:],fontsize=6)
ax.set_aspect('equal');fig.savefig(R/'references/discovery_west_identity_dsm.png',dpi=150)
report={'source_geometry':f,'centroid_lonlat':ll.transform(p.centroid.x,p.centroid.y),'neighbors':neighbors,'roof_odn_quantiles':np.percentile(z[mask],[5,25,50,75,95]).tolist(),'scene_roof_quantiles':np.percentile(z[mask]-4.28000021,[5,25,50,75,95]).tolist(),'ground_odn_median':float(np.median(np.asarray(G)[mask]))};(R/'references/discovery_west_identity_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='source_geometry'},indent=2))
