"""Diagnose terrain-like raster strips; do not interpret them as roof holes."""
from pathlib import Path
import json,warnings
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point,shape
from shapely.ops import unary_union,transform
from rasterio.features import shapes
from pyproj import Transformer
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());pid='2db83fcc-a177-4113-99ef-cd5a245f2a5a';fs=[f for f in g['buildings'] if f.get('parent_id')==pid]
def poly(f):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
ps=[poly(f) for f in fs];p=unary_union(ps);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(3)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);aff=ds.window_transform(w);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(aff,rr,cc);xx=np.array(xx).reshape(d.shape);yy=np.array(yy).reshape(d.shape);x,y=bk.transform(xx,yy)
with rasterio.open(R/'references/ea_dtm_1m.tif') as ds:t=np.array([q[0] for q in ds.sample(zip(xx.flat,yy.flat),masked=True)]).reshape(d.shape)
z=np.asarray(d,float);valid=~np.ma.getmaskarray(d)&np.isfinite(t);delta=z-t
masks=[valid&np.array([q.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for q in ps];inside=np.logical_or.reduce(masks);tall=np.logical_or.reduce([m for f,m in zip(fs,masks) if f['height_m']>20]);low=inside&(abs(delta)<=.1);lab,n=label(low,structure=np.ones((3,3),int));components=[]
for i in range(1,n+1):
 m=lab==i
 polys=[transform(bk.transform,shape(q)) for q,val in shapes(m.astype('uint8'),mask=m,transform=aff) if val==1];u=unary_union(polys)
 components.append({'label':i,'cells':int(m.sum()),'tall_part_cells':int((m&tall).sum()),'bounds_local_xy_m':list(u.bounds),'touches_parts':[{'id':f['id'],'cells':int((m&mm).sum())} for f,mm in zip(fs,masks) if (m&mm).any()],'polygons_local_xy':[{'outer':list(map(list,a.exterior.coords)),'holes':[list(map(list,h.coords)) for h in a.interiors]} for a in (list(u.geoms) if hasattr(u,'geoms') else [u])]})
rows=[]
for f,m in zip(fs,masks):
 vals=abs(delta[m]);lo=m&low;hi=m&(delta>10)
 rows.append({'id':f['id'],'baseline_height_m':f['height_m'],'footprint_cells':int(m.sum()),'exact_numeric_equal_cells':int((vals==0).sum()),'within_0_002m_cells':int((vals<=.0021).sum()),'within_0_01m_cells':int((vals<=.01).sum()),'terrain_like_within_0_1m_cells':int(lo.sum()),'terrain_like_odn_median':float(np.median(z[lo])) if lo.any() else None,'elevated_over_10m_cells':int(hi.sum()),'elevated_odn_p10_median_p90':np.percentile(z[hi],[10,50,90]).tolist() if hi.any() else []})
report={'parent_id':pid,'classification':'terrain_like = absolute DSM-DTM <=0.1m; equality tolerances also reported. Classification concerns raster agreement, not verified open space.','parts':rows,'components_8_neighbor':sorted(components,key=lambda r:-r['cells']),'sources':'Local EA DSM and DTM 1m, mixed2017–2020 OGL; mapped Overture2026 footprints','geometry_modified':False,'visual_reviewed':False,'limitations':['DSM/DTM agreement can reflect ground visibility, processing, fill, occlusion or temporal mismatch; raster comparison alone cannot choose the cause.','Components are clipped to mapped footprint union and use8-neighbour raster connectivity. Polygon boundaries are cell edges, not architecture.','Elevated >10m group is descriptive only, not semantic roof classification.','No evidence here establishes genuine roof holes or current-building changes.']}
fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for ax,vals,title,kw in [(axs[0],z,'DSM ODN',{'vmin':4,'vmax':56}),(axs[1],delta,'DSM minus DTM',{'vmin':0,'vmax':50}),(axs[2],np.where(low,lab,np.nan),'Terrain-like connected strips',{'cmap':'tab20'})]:
 mm=inside if ax!=axs[2] else low;im=ax.scatter(x[mm],y[mm],c=vals[mm],s=14,marker='s',**kw);fig.colorbar(im,ax=ax)
 for k,q in enumerate(ps):
  a,b=q.exterior.xy;ax.plot(a,b,c='red',lw=.7);ax.text(q.centroid.x,q.centroid.y,str(k+1),fontsize=9)
 ax.set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)',title=title)
fig.savefig(R/'references/britannia_low_returns.png',dpi=150);(R/'references/britannia_low_returns.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'parts':rows,'components':[{k:c[k] for k in ['label','cells','tall_part_cells','bounds_local_xy_m']} for c in report['components_8_neighbor'][:8]]},indent=2))
