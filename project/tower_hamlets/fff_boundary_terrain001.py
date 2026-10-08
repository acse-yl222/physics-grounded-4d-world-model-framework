from pathlib import Path
import json,numpy as np,rasterio
from pyproj import Transformer
from shapely.geometry import shape,Point
from shapely.ops import unary_union,transform
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-evidence-002';g=json.load(open(R/'geometry.json'));tr=Transformer.from_crs(g['crs'],27700,always_xy=True)
a=json.load(open(O/'fff_boundary-audit.json'));pair=unary_union([shape(q['geometry_local']) for q in a['nearby_raw_owners'] if q['id'].startswith(('fff95900','02ed5509'))]);s=json.load(open(O/'fff_boundary-terrain-site-samples.json'))['samples']
with rasterio.open(R/'references/fff_boundary_ea_dtm_1m_001.tif') as ds:
 for p,v in zip(s,ds.sample([tr.transform(p['x'],p['y']) for p in s],masked=True)):
  p['dtm_scene_z']=None if np.ma.is_masked(v[0]) else float(v[0])-4.28000021
  p['outside_ring_2m']=pair.buffer(2).contains(Point(p['x'],p['y'])) and not pair.contains(Point(p['x'],p['y']))
 bbox=list(pair.buffer(2).bounds);bng=transform(tr.transform,pair.buffer(2)).bounds;grid=[float(np.floor(bng[0])),float(np.floor(bng[1])),float(np.ceil(bng[2])),float(np.ceil(bng[3]))]
v=[p for p in s if p['dtm_scene_z'] is not None];ring=[p['dtm_scene_z'] for p in v if p['outside_ring_2m']];diff=[p['site_z']-p['dtm_scene_z'] for p in v if p['site_z'] is not None]
fig,ax=plt.subplots(figsize=(8,7));im=ax.scatter([p['x'] for p in v],[p['y'] for p in v],c=[p['dtm_scene_z'] for p in v],marker='s',s=85);fig.colorbar(im,label='DTM ODN − 4.28000021 m');hit=[p for p in v if p['site_z'] is not None];ax.scatter([p['x'] for p in hit],[p['y'] for p in hit],facecolors='none',edgecolors='black',s=100,label='Existing site hit')
for q in a['nearby_raw_owners']:
 if q['id'].startswith(('fff95900','02ed5509')):ax.plot(*shape(q['geometry_local']).exterior.xy,'r')
ax.set(aspect='equal',xlabel='ENU east m',ylabel='ENU north m',title='Measured terrain context; no patch authored');ax.legend();fig.savefig(O/'fff_boundary-terrain.png',dpi=150)
out={'datum':'ODN minus 4.28000021','capture_vintage':'unresolved','minimum_footprint_bbox_enu':list(pair.bounds),'suggested_2m_context_bbox_enu':bbox,'aligned_1m_context_bbox_epsg27700':grid,'margin_note':'2m is a display/context choice, not a surveyed required boundary. Entire bbox has licensed DTM coverage.','ring_dtm_scene_quantiles':np.percentile(ring,[0,25,50,75,100]).tolist(),'site_minus_dtm_quantiles':np.percentile(diff,[0,25,50,75,100]).tolist(),'site_comparison_count':len(diff),'samples':s,'limitation':'Existing site is simplified; terrain extension would require non-flat DTM geometry and explicit seam treatment. No ground created.'};(O/'fff_boundary-terrain-report.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='samples'})
