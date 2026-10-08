import json
from shapely import constrained_delaunay_triangles
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform,unary_union,triangulate
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fs=[f for f in g['buildings'] if f.get('parent_id')=='4cf43bea-e9fe-4e14-8c21-6c480f382d5c'];polys={f['id']:unary_union([Polygon(t['outer'],t.get('holes',[])) for t in f['geometry']]) for f in fs};p=unary_union(list(polys.values()));tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(5)).bounds,ds.transform).round_offsets().round_lengths();w=w.intersection(rasterio.windows.Window(0,0,ds.width,ds.height));Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
valid=~np.ma.getmaskarray(Z);z=np.asarray(Z);mask=lambda p:valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);ground=float(np.median(np.asarray(G)[mask(p)]));entries=[]
for f in fs:
 poly=polys[f['id']];m=mask(poly.buffer(-1));zs=z[m];entries.append({'id':f['id'],'mapped_height_m':f['height_m'],'area_m2':poly.area,'dsm_quantiles_10_50_90_m_odn':np.percentile(zs,[10,50,90]).tolist(),'scene_relative_quantiles_m':np.percentile(zs-ground,[10,50,90]).tolist(),'source_geometry':f})
fig,ax=plt.subplots(figsize=(9,7));m=mask(p);im=ax.scatter(x[m],y[m],c=z[m]-ground,s=6,vmin=0,vmax=60);fig.colorbar(im,ax=ax,label='DSM minus common ground scalar (m)')
for i,(id,poly) in enumerate(polys.items()):xx,yy=poly.exterior.xy;ax.plot(xx,yy,color='black',lw=.7);ax.text(poly.centroid.x,poly.centroid.y,str(i),color='red')
ax.set_aspect('equal');ax.set(title='Western foreground six-part group: DSM evidence',xlabel='ENU east m',ylabel='ENU north m');fig.savefig(R/'references/western_curve_roof_review.png',dpi=140)
overlaps=[{'a':a,'b':b,'area_m2':pa.intersection(pb).area} for a,pa in polys.items() for b,pb in polys.items() if a<b and pa.intersection(pb).area>1e-4]
# Partition overlapping nested parts by mapped rank before estimating local roof modes.
claimed=Polygon();territories=[]
for f in sorted(fs,key=lambda f:f['height_m'],reverse=True):
 shape=polys[f['id']].difference(claimed);claimed=claimed.union(polys[f['id']]);m=mask(shape.buffer(-.6))
 qs=np.percentile(z[m]-ground,[10,50,90]).tolist() if m.any() else None
 parts=[]
 for poly in ([shape] if shape.geom_type=='Polygon' else list(shape.geoms)):
  if poly.is_empty:continue
  parts.append({'outer':list(poly.exterior.coords)[:-1],'holes':[list(h.coords)[:-1] for h in poly.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(poly).geoms]})
 territories.append({'id':f['id'],'geometry':parts,'relative_roof_quantiles_m':qs,'area_m2':shape.area,'height_m_estimated':round(qs[1],2) if qs else f['height_m']})
report={'parent_id':'4cf43bea-e9fe-4e14-8c21-6c480f382d5c','ground_scalar_odn_m':ground,'entries':entries,'plan_overlaps':overlaps,'nonoverlapping_territories':territories,'union_area_m2':p.area,'height_scope':'Local common ground scalar normalizes evidence only; scene remains flattened ground; inference not surveyed globaldatum','visual_reviewed':False};(R/'references/western_curve_roof_review.json').write_text(json.dumps(report,indent=2)+'\n');print([(e['id'],e['scene_relative_quantiles_m']) for e in entries]);print('overlaps',overlaps)
