from pathlib import Path
import json,hashlib,numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import shape,Polygon,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-evidence-002';O.mkdir(exist_ok=True);g=json.loads((R/'geometry.json').read_text());f=next(x for x in g['buildings'] if 'fff95900' in x['id']);p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True);ll=Transformer.from_crs(4326,g['crs'],always_xy=True)
raw=json.loads((R/'references/fff_boundary-buildings001.geojson').read_text());near=[]
for q in raw['features']:
 poly=transform(ll.transform,shape(q['geometry']))
 if poly.distance(p)<15:near.append({'id':q.get('id',q['properties'].get('id')),'properties':q['properties'],'geometry_local':poly.__geo_interface__,'gap_m':poly.distance(p),'shared_m':poly.boundary.intersection(p.boundary).length,'overlap_m2':poly.intersection(p).area})
with rasterio.open(R/'references/fff_boundary_ea_dsm_1m_001.tif') as ds,rasterio.open(R/'references/fff_boundary_ea_dtm_1m_001.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(18)).bounds,ds.transform).round_offsets().round_lengths();Z=ds.read(1,window=w,masked=True,boundless=True);G=dt.read(1,window=w,masked=True,boundless=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
valid=~np.ma.getmaskarray(Z);inside=np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);sel=valid&inside;z=np.asarray(Z);fig,axs=plt.subplots(1,2,figsize=(12,6),layout='constrained')
for ax,mask,title in [(axs[0],valid,'Full native raster context (blank=unavailable)'),(axs[1],sel,'Full owner roof support')]:
 im=ax.scatter(x[mask],y[mask],c=z[mask],s=45,marker='s',vmin=4,vmax=13);fig.colorbar(im,ax=ax,label='DSM ODN m');ax.plot(*p.exterior.xy,'r',lw=2)
 for n in near:
  q=shape(n['geometry_local']);ax.plot(*q.exterior.xy,'k',lw=.6)
 ax.set(aspect='equal',title=title,xlabel='AEQD east m',ylabel='AEQD north m')
axs[1].set(xlim=(p.bounds[0]-1,p.bounds[2]+1),ylim=(p.bounds[1]-1,p.bounds[3]+1));fig.savefig(O/'fff_boundary-dsm.png',dpi=150)
d={'source_geometry':f,'area_m2':p.area,'full_footprint_cell_count':int(inside.sum()),'valid_dsm_cell_count':int(sel.sum()),'dsm_odn_quantiles':np.percentile(z[sel],[0,25,50,75,100]).tolist() if sel.any() else [],'nearby_raw_owners':near,'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/fff_boundary-buildings001.geojson','references/fff_boundary_ea_dsm_1m_001.tif']},'datum':'ODN minus4.28000021; local vintage unresolved'};(O/'fff_boundary-audit.json').write_text(json.dumps(d,indent=2));print({k:v for k,v in d.items() if k not in ['source_geometry','nearby_raw_owners','source_hashes']});print([(n['id'],n['gap_m'],n['shared_m']) for n in near]);np.savez(O/'fff_boundary-samples.npz',x=x,y=y,z=z,valid=valid,inside=inside)
