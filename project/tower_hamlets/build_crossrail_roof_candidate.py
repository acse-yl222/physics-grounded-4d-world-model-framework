"""Build observed roof-envelope patches, not a completed architectural canopy.

Leaves unsupported cells open. OBJ is local ENU metres with DTM scalar removed.
Existing whole-region model is deliberately untouched pending parent interfaces.
"""
from pathlib import Path
import json,hashlib,math
import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
from pyproj import Transformer
from shapely.geometry import Polygon,Point
from shapely.ops import transform
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';refs=root/'references'
g=json.loads((root/'geometry.json').read_text());rep=json.loads((refs/'crossrail_lidar_review.json').read_text());f=next(f for f in g['buildings'] if f['id']==rep['building_id']);poly=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(refs/'ea_dsm_1m.tif') as ds:
 raw=from_bounds(*transform(tr.transform,poly).bounds,ds.transform);c0,r0=math.floor(raw.col_off),math.floor(raw.row_off);w=Window(c0,r0,math.ceil(raw.col_off+raw.width)-c0,math.ceil(raw.row_off+raw.height)-r0);z=ds.read(1,window=w,masked=True);rr,cc=np.indices(z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.asarray(xx).reshape(z.shape),np.asarray(yy).reshape(z.shape))
u=np.array(rep['axis_local_xy']);v=np.array([-u[1],u[0]]);cx,cy=rep['mapped_part_extent']['centroid_local_xy'];cross=(x-cx)*v[0]+(y-cy)*v[1];along=(x-cx)*u[0]+(y-cy)*u[1];fit=rep['upper_envelope_circle_fit'];disc=fit['radius_m']**2-(cross-fit['cross_axis_center_m'])**2;envelope=fit['circle_center_z_odn_m']+np.sqrt(np.maximum(0,disc));inside=np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);valid=inside&~np.ma.getmaskarray(z)&(disc>0);supported=valid&(np.abs(np.asarray(z)-envelope)<=1.0)
# Explicit grid connectivity; never bridge unsupported pixels or source boundary.
verts=[];faces=[];lookup={}
def vertex(i,j):
 key=(i,j)
 if key not in lookup:lookup[key]=len(verts);verts.append((float(x[i,j]),float(y[i,j]),float(z[i,j]-rep['ground_scalar_m_odn'])))
 return lookup[key]
for i in range(z.shape[0]-1):
 for j in range(z.shape[1]-1):
  for points in [((i,j),(i+1,j),(i+1,j+1)),((i,j),(i+1,j+1),(i,j+1))]:
   if not all(supported[a,b] for a,b in points):continue
   triangle=Polygon([(x[a,b],y[a,b]) for a,b in points])
   if not poly.covers(triangle):continue
   ids=[vertex(a,b) for a,b in points];a,b,c=[verts[k] for k in ids]
   if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:ids.reverse()
   faces.append(ids)
assert verts and faces and all(math.isfinite(q) for p in verts for q in p)
path=refs/'crossrail_observed_roof_candidate.obj'
with path.open('w') as file:
 file.write('# EA OGL DSM roof-envelope patches. Local ENU metres. Intentional open surface.\n# Unsupported cells are NOT verified architectural openings.\no crossrail_observed_roof_patches\n')
 for p in verts:file.write('v '+' '.join(f'{c:.8f}' for c in p)+'\n')
 for face in faces:file.write('f '+' '.join(str(i+1) for i in face)+'\n')
fig,axs=plt.subplots(2,1,figsize=(15,7),layout='constrained')
for ax,mask,title in [(axs[0],valid,'All valid footprint DSM cells'),(axs[1],supported,'Cells within ±1 m of fitted upper roof envelope; gaps remain unknown')]:
 sc=ax.scatter(along[mask],cross[mask],c=np.asarray(z)[mask],s=9,marker='s',vmin=16,vmax=30,cmap='viridis');ax.set(title=title,xlabel='Long axis (m)',ylabel='Cross axis (m)',ylim=(-17,17));ax.set_aspect('equal');fig.colorbar(sc,ax=ax,label='DSM (m ODN)',shrink=.7)
fig.suptitle('Crossrail Place — roof coverage candidate; not a verified opening plan')
fig.savefig(refs/'crossrail_roof_candidate_mask.png',dpi=150)
report={'feature_id':f['id'],'vertices':len(verts),'triangles':len(faces),'valid_footprint_cells':int(valid.sum()),'supported_roof_cells':int(supported.sum()),'envelope_tolerance_m':1.0,'ground_scalar_odn_m':rep['ground_scalar_m_odn'],'coordinate_frame':'Local AEQD east/north; elevation minus local median DTM; metres','geometry_scope':'Observed DSM mesh patches within mapped part only; no interpolation over gaps','whole_region_geometry_modified':False,'source_sha256':hashlib.sha256((refs/'ea_dsm_1m.tif').read_bytes()).hexdigest(),'obj_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checks':{'finite':True,'triangles_inside_source_outline':True,'no_bridging_missing_grid_samples':True,'intentional_open_surface':True},'limitations':['Unobserved gaps may be garden, transparent material or poor returns; not verified openings','Parent side/end geometry unresolved; do not combine with previous28m residual as finished canopy','One-metre grid cannot resolve timber lattice or ETFE panel edges','Historical mixed survey vintage']}
(refs/'crossrail_roof_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
