"""Review Block Wharf raster evidence without modifying geometry."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((root/'geometry.json').read_text())
f=next(f for f in g['buildings'] if f['id']=='overture-building-112b6cf0-b1a9-4c9c-9614-f432af4d0902')
p=Polygon(f['geometry'][0]['outer']); tr=Transformer.from_crs(g['crs'],27700,always_xy=True); back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(root/'references/ea_dsm_1m.tif') as ds,rasterio.open(root/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p).buffer(12).bounds,ds.transform).round_offsets().round_lengths(); a=ds.read(1,window=w,masked=True); d=dt.read(1,window=w,masked=True); t=ds.window_transform(w)
 rr,cc=np.indices(a.shape); xx,yy=rasterio.transform.xy(t,rr,cc); x,y=back.transform(np.array(xx).reshape(a.shape),np.array(yy).reshape(a.shape))
z=np.asarray(a);ground=np.asarray(d);valid=~np.ma.getmaskarray(a)&~np.ma.getmaskarray(d)
def mask(poly):return np.array([poly.contains(Point(i,j)) for i,j in zip(x.flat,y.flat)]).reshape(a.shape)&valid
inside=mask(p);inner=mask(p.buffer(-1.5));base=float(np.median(ground[inside]));h=z-base
quant=lambda v:dict(zip(['min','p05','p10','p25','median','p75','p90','p95','max'],map(float,np.percentile(v,[0,5,10,25,50,75,90,95,100]))))
report={'building_id':f['id'],'geometry_modified':False,'source':'EA 1m DSM/DTM OGL; composite mixed survey dates, exact tile capture date unresolved','current_height_m':f['height_m'],'ground_reference_m_odn':base,'ground_reference_definition':'Median DTM cell centre inside exact footprint; roof scene z = DSM minus this scalar, matching Cabot convention. Not a surveyed foundation elevation.','ground_quantiles_m_odn':quant(ground[inside]),'full_samples':int(inside.sum()),'interior_samples':int(inner.sum()),'interior_height_quantiles_m':quant(h[inner]),'erosion_sensitivity':{str(e):{'samples':int(mask(p.buffer(-e)).sum()),'height_quantiles_m':quant(h[mask(p.buffer(-e))])} for e in [0,.5,1,1.5,2]},'limitations':['1m raster cannot resolve facade details or roof equipment dimensions.','Roof height and building state may differ between composite LiDAR acquisition and 2026 mapped footprint.','Flattened terrain convention preserves current z=0 base rather than absolute ODN ground.']}
report['visual_review']={'inspected':True,'observations':['Surrounding DSM shows spatially isolated roof matching mapped narrow footprint, separated from taller building to north by low space; neighbouring roof contamination is not the dominant interior signal.','Two coherent height plateaus around 19.65m and 22.81m are present. Upper plateau runs through central length; lower plateau occupies ends and parts of east margin. These are roof-scale bands, not a few equipment spikes.','Low returns at west recess and outer edges should not determine roof height. 1.5m erosion still contains a few low cells because footprint narrowness and recess remain.'],'recommendation':'Replacing assumed 9m with 22.8m is supported only as a coarse maximum-roof envelope. A single flat 22.8m slab across entire footprint would erase observed lower roof/terrace bands. Prefer a 19.65m base roof with inset 22.81m upper level after bounded breakline fitting; do not add parapets/facade details from raster.','conservative_envelope_height_m':22.8,'lower_plateau_height_m':19.65,'upper_plateau_height_m':22.81,'full_detail_supported':False}
report['plateau_counts_in_1_5m_interior']={'lower_19_3_to_20_0m':int(np.sum(inner&(h>19.3)&(h<20.0))),'upper_22_5_to_23_1m':int(np.sum(inner&(h>22.5)&(h<23.1))),'other':int(np.sum(inner&~(((h>19.3)&(h<20.0))|((h>22.5)&(h<23.1)))))}
fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained')
for ax,data,title in [(axs[0,0],h,'Surrounding DSM minus local DTM scalar (m)'),(axs[0,1],np.where(inside,h,np.nan),'Exact footprint heights (m)')]:
 im=ax.scatter(x,y,c=data,s=18,marker='s',vmin=0,vmax=35);ax.plot(*p.exterior.xy,'r-',lw=1.5);ax.plot(*p.buffer(-1.5).exterior.xy,'w--',lw=1);ax.set_aspect('equal');ax.set_title(title);fig.colorbar(im,ax=ax)
axs[1,0].scatter(y[inside],h[inside],s=12,c=x[inside],cmap='viridis');axs[1,0].set(xlabel='Local northing (m)',ylabel='Height above local ground (m)',title='All footprint cells, colour = easting')
axs[1,1].hist(h[inside],bins=35,alpha=.4,label='Whole footprint');axs[1,1].hist(h[inner],bins=25,alpha=.7,label='1.5m erosion');axs[1,1].set(xlabel='Height (m)',title='Interior versus edge sensitivity');axs[1,1].legend();fig.suptitle('Block Wharf: exact footprint and LiDAR evidence review')
fig.savefig(root/'references/blockwharf_lidar_review.png',dpi=150)
(root/'references/blockwharf_lidar_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

# Reproducible stepped mesh derivation after raster review.
from shapely.geometry import MultiPoint
from shapely import constrained_delaunay_triangles
hi=inner&(h>22.5)&(h<23.1)
upper=MultiPoint(list(zip(x[hi],y[hi]))).convex_hull.buffer(.5,join_style=2).intersection(p.buffer(-.5,join_style=2))
upper=upper.simplify(.35,preserve_topology=True)
lower=p.difference(upper)
verts=[];faces=[];mats=[];lookup={}
def face(points,mat):
 ids=[]
 for pt in points:
  key=tuple(round(float(c),8) for c in pt)
  if key not in lookup:lookup[key]=len(verts);verts.append(list(key))
  ids.append(lookup[key])
 faces.append(ids);mats.append(mat)
for poly,zv in [(lower,19.65),(upper,22.81)]:
 for tri in constrained_delaunay_triangles(poly).geoms:
  pts=list(tri.exterior.coords)[:-1]
  if not tri.exterior.is_ccw:pts.reverse()
  face([(*q,zv) for q in pts],1);face([(*q,0) for q in reversed(pts)],0)
for poly,lo,high in [(p,0,19.65),(upper,19.65,22.81)]:
 pts=list(poly.exterior.coords)[:-1]
 if not poly.exterior.is_ccw:pts.reverse()
 for a,b in zip(pts,pts[1:]+pts[:1]):face([(*a,lo),(*b,lo),(*b,high),(*a,high)],0)
# Bottom partition seam includes same vertices as roofs. Remove collinear T junctions by splitting all face edges at existing vertices.
for idx,fc in enumerate(faces):
 out=[]
 for ai,bi in zip(fc,fc[1:]+fc[:1]):
  a=np.array(verts[ai]);b=np.array(verts[bi]);v=b-a;vv=v@v; extra=[]
  for j,pt in enumerate(verts):
   t=((np.array(pt)-a)@v)/vv
   if 1e-8<t<1-1e-8 and np.linalg.norm(np.array(pt)-a-t*v)<1e-7:extra.append((t,j))
  out.append(ai);out.extend(j for _,j in sorted(extra))
 faces[idx]=out
from collections import Counter
edges=Counter((a,b) for f in faces for a,b in zip(f,f[1:]+f[:1]));assert all(n==1 and edges[(b,a)]==1 for (a,b),n in edges.items())
vol=sum(np.dot(verts[fc[0]],np.cross(verts[fc[i]],verts[fc[i+1]]))/6 for fc in faces for i in range(1,len(fc)-1));assert vol>0
roofarea=sum(abs(np.cross(np.array(verts[fc[i]])-np.array(verts[fc[0]]),np.array(verts[fc[i+1]])-np.array(verts[fc[0]]))[2])/2 for fc,m in zip(faces,mats) if m==1 for i in range(1,len(fc)-1));assert abs(roofarea-p.area)<1e-5
out={'building_id':f['id'] if isinstance(f,dict) else 'overture-building-112b6cf0-b1a9-4c9c-9614-f432af4d0902','vertices':verts,'faces':faces,'materials':mats,'upper_outline_local_m':list(upper.exterior.coords),'lower_height_m':19.65,'upper_height_m':22.81,'method':'Convex hull of 1.5m-eroded interior DSM cells in22.5–23.1m band, buffered0.5m and clipped to0.5m source inset; simplify0.35m. Breakline is estimated at1m raster resolution; convex hull regularizes raster stair steps.','checks':{'paired_opposite_edges':True,'positive_volume_m3':float(vol),'roof_area_m2':float(roofarea),'source_area_m2':p.area},'uncertainty':['Upper boundary approximate, not surveyed; convex hull can bridge unresolved recesses.','No equipment, parapet, facade or window detail inferred.','Roof elevations use local ground scalar2.4225m ODN; flattened base at0.']}
(root/'references/blockwharf_geometry_report.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['checks'])
