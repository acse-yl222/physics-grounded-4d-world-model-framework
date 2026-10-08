import json,numpy as np,rasterio
from pathlib import Path
from rasterio.windows import from_bounds
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';rows=[]
for kind in ['dsm','dtm']:
 with rasterio.open(R/f'ea_{kind}_1m.tif') as a,rasterio.open(R/f'leyland_ea_{kind}_1m_001.tif') as b:
  bounds=[max(a.bounds.left,b.bounds.left),max(a.bounds.bottom,b.bounds.bottom),min(a.bounds.right,b.bounds.right),min(a.bounds.top,b.bounds.top)];wa=from_bounds(*bounds,a.transform).round_offsets().round_lengths();wb=from_bounds(*bounds,b.transform).round_offsets().round_lengths();aa=a.read(1,window=wa,masked=True);bb=b.read(1,window=wb,masked=True);m=~np.ma.getmaskarray(aa)&~np.ma.getmaskarray(bb);delta=np.asarray(bb-aa)[m]
  rows.append({'product':kind,'overlap_bounds':bounds,'same_crs':a.crs==b.crs,'same_resolution':a.res==b.res,'overlap_transform_equal':a.window_transform(wa)==b.window_transform(wb),'overlap_valid_count':int(m.sum()),'exact_equal_count':int((delta==0).sum()),'max_abs_difference_m':float(abs(delta).max()),'mean_difference_m':float(delta.mean()),'new_shape':[b.height,b.width],'new_valid_cells':int(b.read(1,masked=True).count()),'old_bounds':list(a.bounds),'new_bounds':list(b.bounds)})
out={'comparison':rows,'mosaic_created':False,'capture_date':None,'basis':'Exact overlap supports grid/elevation consistency only; local flight vintage unknown.'}
(R/'leyland-raster-check001.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
