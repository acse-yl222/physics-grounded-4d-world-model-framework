from pathlib import Path
import json,numpy as np,rasterio
from pyproj import Transformer
from shapely.geometry import shape,Polygon,Point
from shapely.ops import unary_union
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/dlr_transport_plan.json').read_text());g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']==r['canopy_id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);tx=Transformer.from_crs(g['crs'],27700,always_xy=True);rows=[];fig,axs=plt.subplots(3,1,figsize=(11,9),layout='constrained')
with rasterio.open(R/'references/ea_dsm_1m.tif') as dsm,rasterio.open(R/'references/ea_dtm_1m.tif') as dtm:
 for ax,q in zip(axs,[q for q in r['features'] if q['category']=='rail']):
  line=shape(q['geometry']);ds=np.arange(0,line.length,.5);pts=[line.interpolate(s) for s in ds];xy=[tx.transform(p.x,p.y) for p in pts];z=np.array([float(v[0]) for v in dsm.sample(xy,masked=True)]);ground=np.array([float(v[0]) for v in dtm.sample(xy,masked=True)]);inside=np.array([p.covers(pt) for pt in pts]);valid=np.isfinite(z)&(z>-100)&(z<300);ax.plot(ds[valid],z[valid],label='DSM surface');ax.plot(ds,ground,label='DTM ground');ax.scatter(ds[inside&valid],z[inside&valid],s=6,label='Under central canopy footprint');ax.set(xlabel='Distance along clipped source line (m)',ylabel='ODN elevation (m)',title=q['id']);ax.legend(fontsize=8)
  outside=z[valid&~inside];rows.append({'id':q['id'],'sample_spacing_m':.5,'distance_m':ds.tolist(),'xy_enu_m':[[pt.x,pt.y] for pt in pts],'dsm_odn_m':[float(t) if np.isfinite(t) else None for t in z],'dtm_odn_m':[float(t) if np.isfinite(t) else None for t in ground],'under_canopy':inside.tolist(),'outside_canopy_quantiles_odn_m':np.quantile(outside,[0,.1,.5,.9,1]).tolist() if len(outside) else []})
fig.savefig(R/'references/dlr_track_height_profiles.png',dpi=150);(R/'references/dlr_track_height_profiles.json').write_text(json.dumps({'tracks':rows,'scope':'Native1m raster sampled every0.5m: oversampling adds no resolution. DSM returns may be roof/vegetation/other structures, never assumed rail head. DTM is terrain, not bridge deck.','geometry_modified':False},indent=2));print([(q['id'],q['outside_canopy_quantiles_odn_m']) for q in rows])
