import json
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());parent='3c1883b4-acfc-4c98-80c0-19b3580c3505';fs=[f for f in g['buildings'] if parent in f['id'] or f.get('parent_id')==parent];polys=[unary_union([Polygon(t['outer'],t.get('holes',[])) for t in f['geometry']]) for f in fs];p=unary_union(polys);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True);ll=Transformer.from_crs(g['crs'],4326,always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(8)).bounds,ds.transform).round_offsets().round_lengths();w=w.intersection(rasterio.windows.Window(0,0,ds.width,ds.height));Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
z=np.asarray(Z);rows=[];fig,ax=plt.subplots(figsize=(10,9));im=ax.scatter(x.flat,y.flat,c=(z-4.28000021).flat,s=8,vmin=0,vmax=85);fig.colorbar(im,ax=ax,label='Scene roof z = DSM ODN - 4.28000021')
for f,pp in zip(fs,polys):
 mask=~np.ma.getmaskarray(Z)&np.array([pp.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
 rows.append({'id':f['id'],'area_m2':pp.area,'baseline_height_m':f['height_m'],'baseline_min_height_m':f.get('min_height_m'),'sample_count':int(mask.sum()),'odn_q5_q25_q50_q75_q95':np.percentile(z[mask],[5,25,50,75,95]).tolist() if mask.any() else [],'scene_q5_q25_q50_q75_q95':np.percentile(z[mask]-4.28000021,[5,25,50,75,95]).tolist() if mask.any() else [],'source_geometry':f})
 for part in f['geometry']:
  a=np.array(part['outer']+[part['outer'][0]]);ax.plot(a[:,0],a[:,1],'k',lw=1)
 ax.text(pp.centroid.x,pp.centroid.y,f['id'].split('-')[2][:8],fontsize=8)
ax.set_aspect('equal');fig.savefig(R/'references/state_street_spatial001.png',dpi=150);report={'group_parent_id':parent,'centroid_lonlat':ll.transform(p.centroid.x,p.centroid.y),'parts':rows,'max_overlap_m2':max(a.intersection(b).area for i,a in enumerate(polys) for b in polys[i+1:])};(R/'references/state_street_spatial001.json').write_text(json.dumps(report,indent=2));print(json.dumps({**report,'parts':[{k:v for k,v in row.items() if k!='source_geometry'} for row in rows]},indent=2))
