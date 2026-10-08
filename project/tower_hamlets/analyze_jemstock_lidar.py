"""Bounded Jemstock 2 roof evidence; deliberately does not edit geometry."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-2e1384be-3161-4326-a35d-d0ba1327dc7c')
p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(35)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm);nh=z-ground
masks={str(erosion):valid&np.array([p.buffer(-erosion).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for erosion in [0,1,2,3,4]}
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist(),'mean_m':float(np.mean(v)),'std_m':float(np.std(v))}
# Axis along the longest original footprint edge, preserving mapped orientation.
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u=u/np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1]
rep={'building_id':f['id'],'name':f['name'],'geometry_modified':False,'source':'EA 1m DSM/DTM OGL, mixed 2017–2020; footprint release 2026-09-23','current_assumed_height_m':f['height_m'],'axis_local_xy':u.tolist(),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[m]),'dtm_odn':stats(ground[m]),'cellwise_dsm_minus_dtm':stats(nh[m])} for k,m in masks.items()},'visual_review':{'inspected':False},'caveats':['Mixed 2017–2020 LiDAR versus 2026 footprint can reflect historical state.','DTM scalar is relative height convention, not surveyed foundation.','One metre DSM cannot resolve parapets or facade details.']}
# Two broad plateaus are visually distinct; report both instead of unstable pooled median.
inner=masks['2']; lower=inner&(z>=58)&(z<60); upper=inner&(z>=62)&(z<63)
terrain_scalar=float(np.median(ground[masks['0']]))
rep['roof_plateaus']={'classification':'Visually reviewed broad lower roof and raised rectangular roof block; semantic function unknown','lower_dsm_odn':stats(z[lower]),'upper_dsm_odn':stats(z[upper]),'ground_scalar_m_odn':terrain_scalar,'conservative_main_roof_scene_z_m':float(np.median(z[lower])-terrain_scalar),'raised_roof_scene_z_m':float(np.median(z[upper])-terrain_scalar),'selection_rule':'Interior 2m cells within observed distinct 58–60 and 62–63m ODN modes; all raw percentiles separately retained.'}
rep['visual_review']={'inspected':True,'image':'jemstock_lidar_review.png','observations':['High roof surface aligns with complete target footprint and neighbouring separate footprints; no isolated neighbouring-tower intrusion explains the height.','Roof has two broad discrete levels: lower flat level around 58.8m ODN and raised rectangular block around 62.35m ODN.','Low returns are concentrated at boundary and disappear with 2m erosion.','Pooled median changes with erosion because relative areas of two roof levels change; it is not an appropriate single roof estimate.'],'recommendation':'Replace unsupported 9m massing height with conservative lower plateau DSM minus median footprint DTM (around 53.2m), preserving exact footprint. Raised block is separately evidenced but extent/function needs bounded roof modelling; do not set full building to upper plateau or add assumed equipment.'}
# Coarse axis-aligned raised block from coherent high plateau cell centres.
from shapely import constrained_delaunay_triangles
high=inner&(z>62.1)&(z<63)
lo_a,hi_a=float(a[high].min()-.5),float(a[high].max()+.5)
lo_b,hi_b=float(b[high].min()-.5),float(b[high].max()+.5)
rect=Polygon([(cx+aa*u[0]+bb*vv[0],cy+aa*u[1]+bb*vv[1]) for aa,bb in [(lo_a,lo_b),(hi_a,lo_b),(hi_a,hi_b),(lo_a,hi_b)]])
assert p.contains(rect)
def tris(poly):
 return [[list(q) for q in list(t.exterior.coords)[:-1]] for t in constrained_delaunay_triangles(poly).geoms]
rep['raised_block_model']={'axis_bounds_m':[lo_a,hi_a,lo_b,hi_b],'polygon_local_xy':[list(q) for q in list(rect.exterior.coords)[:-1]],'area_m2':rect.area,'lower_roof_triangles':tris(p.difference(rect)),'upper_roof_triangles':tris(rect),'boundary_basis':'Extrema of 2m-interior high plateau cells DSM 62.1–63m ODN, expanded 0.5m; coarse axis-aligned rectangle, not surveyed wall line','boundary_uncertainty_m':1.5,'semantic_identity':'unknown raised roof volume; not identified as equipment'}
fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained')
ax=axs[0,0];im=ax.scatter(x,y,c=nh,s=10,marker='s',vmin=0,vmax=90,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM − DTM (m)')
for nf in g['buildings']:
 for geom in nf['geometry']:
  poly=Polygon(geom['outer'])
  if poly.intersects(p.buffer(35)):
   px,py=poly.exterior.xy;ax.plot(px,py,color='red' if nf['id']==f['id'] else 'white',lw=2 if nf['id']==f['id'] else .6)
rx,ry=rect.exterior.xy;ax.plot(rx,ry,color='orange',lw=1.5)
ax.set(xlim=(x.min(),x.max()),ylim=(y.min(),y.max()),title='Context plan: target red; mapped neighbours white',xlabel='Local E (m)',ylabel='Local N (m)');ax.set_aspect('equal')
ax=axs[0,1];m=masks['0'];im=ax.scatter(a[m],b[m],c=z[m],marker='s',s=20,vmin=50,vmax=65);fig.colorbar(im,ax=ax,label='DSM m ODN');ax.set(title='All target roof cells; mapped long/cross axes',xlabel='Long axis (m)',ylabel='Cross axis (m)');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],a,'Long axis'),(axs[1,1],b,'Cross axis')]:
 ax.scatter(c[m],z[m],s=8,alpha=.35,label='All footprint DSM');inner=masks['2'];ax.scatter(c[inner],z[inner],s=8,alpha=.5,label='Interior 2m DSM');ax.axhline(float(np.median(z[inner])),color='red',label='Interior median');ax.set(xlabel=label+' (m)',ylabel='DSM m ODN',title=label+' profile: full roof, no trimmed returns');ax.legend(fontsize=8)
fig.suptitle('Jemstock 2 — bounded roof height review; geometry unchanged');fig.savefig(ROOT/'references/jemstock_lidar_review.png',dpi=150)
(ROOT/'references/jemstock_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep,indent=2))
