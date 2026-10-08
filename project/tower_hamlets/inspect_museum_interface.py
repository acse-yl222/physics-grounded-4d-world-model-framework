"""Record roof ownership and shared vertical reference for Museum assembly."""
from pathlib import Path
import json,hashlib
import numpy as np,rasterio
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
from rasterio.windows import from_bounds
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((r/'geometry.json').read_text());ids=['overture-building-dbe8f73e-e036-48c5-9059-bb6350356575','overture-part-97b6bbeb-83a5-3cd1-9036-e3e0e8b9c78b'];polys=[]
for id in ids:
 b=next(b for b in g['buildings'] if b['id']==id);polys.append(unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]))
u=unary_union(polys);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(r/'references/ea_dtm_1m.tif') as ds:
 w=from_bounds(*transform(tr.transform,u).bounds,ds.transform).round_offsets().round_lengths();a=ds.read(1,window=w,masked=True);rr,cc=np.indices(a.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(a.shape),np.array(yy).reshape(a.shape));m=~np.ma.getmaskarray(a)&np.array([u.contains(Point(x,y)) for x,y in zip(x.flat,y.flat)]).reshape(a.shape);vals=np.asarray(a)[m]
d={'ids':ids,'geometry_sha256':hashlib.sha256((r/'geometry.json').read_bytes()).hexdigest(),'overlap_area_m2':polys[0].intersection(polys[1]).area,'shared_boundary_length_m':polys[0].boundary.intersection(polys[1].boundary).length,'union_area_m2':u.area,'common_ground_offset_odn_m':float(np.median(vals)),'ground_p05_p50_p95_odn_m':np.percentile(vals,[5,50,95]).tolist(),'ground_sample_count':len(vals),'contract':'Preserve feature ownership; evaluate both roof surfaces in a common local axis frame. Use same DTM scalar if converted to flat scene Z. Do not create walls along internal ownership seam without a measured roof-height discontinuity.','limitations':['DTM varies across footprint; common scalar prevents artificial split but is not surveyed foundation level.','Roof fit still pending; shared outline alone does not prove identical roof surfaces.']}
assert d['overlap_area_m2']<1e-6
(r/'references/museum_interface.json').write_text(json.dumps(d,indent=2)+'\n');print(d)
