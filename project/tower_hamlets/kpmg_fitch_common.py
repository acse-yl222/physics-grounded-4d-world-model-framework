"""Inspect Fitch source-name roof evidence; no scene mutation."""
from pathlib import Path
import json,warnings,hashlib
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());pid='6e7e0de2-c2a2-4a0c-9fc9-e520ffe67046';fs=[f for f in g['buildings'] if f['id'] in ['overture-building-def47cf3-2875-4e34-ae57-aad5a67e6fa1','overture-building-6e7e0de2-c2a2-4a0c-9fc9-e520ffe67046']]
def poly(f):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
ps=[poly(f) for f in fs];p=unary_union(ps);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(3)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);xx=np.array(xx).reshape(d.shape);yy=np.array(yy).reshape(d.shape);x,y=bk.transform(xx,yy)
with rasterio.open(R/'references/ea_dtm_1m.tif') as dt:t=np.array([q[0] for q in dt.sample(zip(xx.flat,yy.flat),masked=True)]).reshape(d.shape)
z=np.asarray(d,float);valid=~np.ma.getmaskarray(d)&np.isfinite(t)
def mask(p):return valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
def stats(a):return {'cells':len(a),'min':float(np.min(a)),'p10':float(np.percentile(a,10)),'median':float(np.median(a)),'p90':float(np.percentile(a,90)),'max':float(np.max(a))} if len(a) else {'cells':0}
def fitplane(m,A):
 return least_squares(lambda c:A[m]@c-z[m],np.array([np.median(z[m]),0.,0.]),loss='soft_l1',f_scale=.2).x
def metric(e):return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e*e))),'median_abs_m':float(np.median(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95))}
