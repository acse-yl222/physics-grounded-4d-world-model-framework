import json
from scipy.ndimage import distance_transform_edt, generic_filter
from rasterio.features import shapes
from shapely import constrained_delaunay_triangles, set_precision
from shapely.geometry import shape
from shapely.ops import unary_union
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(x for x in g['buildings'] if '33773280' in x['id']);p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(6)).bounds,ds.transform).round_offsets().round_lengths();w=w.intersection(rasterio.windows.Window(0,0,ds.width,ds.height));Z=ds.read(1,window=w,masked=True);G=dt.read(1,window=w,masked=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z);ground=float(np.median(np.asarray(G)[mask]));v=np.array(p.exterior.coords);e=np.diff(v,axis=0);u=e[np.argmax(np.linalg.norm(e,axis=1))];u/=np.linalg.norm(u);v=np.array([-u[1],u[0]]);c=np.array(p.centroid.coords[0]);a=(x-c[0])*u[0]+(y-c[1])*u[1];b=(x-c[0])*v[0]+(y-c[1])*v[1]

# Four spatially coherent roof bands observed in histogram/profile, in ODN.
centres=np.array([49.3,62.05,66.9,72.05]);labels=np.argmin(abs(z[:,:,None]-centres),axis=2);error=abs(z-centres[labels]);seeds=mask&(error<1.25)
indices=distance_transform_edt(~seeds,return_distances=False,return_indices=True);filled=labels[tuple(indices)].astype('uint8');filtered=generic_filter(filled,lambda q:np.bincount(q.astype(int),minlength=4).argmax(),size=3).astype('uint8')
window_transform=ds.window_transform(w) if False else rasterio.transform.from_origin(0,0,1,1)
# Reopen to retain exact raster-window affine transform.
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:window_transform=ds.window_transform(w)
regions=[]
for label in range(4):
 pieces=[transform(back.transform,shape(geom)).intersection(p) for geom,val in shapes(filtered,transform=window_transform) if int(val)==label];poly=unary_union(pieces);poly=poly.simplify(.55,preserve_topology=True).intersection(p)
 parts=[poly] if poly.geom_type=='Polygon' else list(poly.geoms)
 if label==3:
  poly=max(parts,key=lambda p:p.area).minimum_rotated_rectangle.intersection(p)
 else:
  poly=unary_union([q for q in parts if q.area>=8]).buffer(.65).buffer(-.65).simplify(.8).intersection(p)
 regions.append(poly)
# Resolve simplification overlaps deterministically, preserving complete source footprint.
claimed=Polygon();clean=[]
for label in reversed(range(4)):
 poly=regions[label].difference(claimed);claimed=claimed.union(poly);clean.append((label,poly))
missing=p.difference(claimed)
# Small boundary slivers inherit dominant adjoining band rather than inventing holes.
clean=[(lab,pol.union(missing) if lab==2 else pol) for lab,pol in clean]
records=[]
for label,poly in clean:
 geometries=[]
 for pp in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
  if pp.geom_type!='Polygon' or pp.area<1e-6:continue
  pp=set_precision(pp,1e-5).simplify(1e-6,preserve_topology=True)
  geometries.append({'outer':list(pp.exterior.coords)[:-1],'holes':[list(h.coords)[:-1] for h in pp.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(pp).geoms]})
 sample=seeds&(labels==label);median=float(np.median(z[sample]));records.append({'label':label,'geometry':geometries,'roof_median_odn_m':median,'height_m':median-4.28000021,'stable_sample_count':int(sample.sum()),'stable_residual_p95_m':float(np.percentile(abs(z[sample]-median),95)),'area_m2':poly.area})
fig,axs=plt.subplots(1,2,figsize=(13,6));im=axs[0].scatter(x[mask],y[mask],c=z[mask],s=5,vmin=48,vmax=73);fig.colorbar(im,ax=axs[0],label='DSM ODN metres')
for label,poly in clean:
 for pp in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
  if pp.geom_type!='Polygon' or pp.area<1e-6:continue
  xx,yy=pp.exterior.xy;axs[1].fill(xx,yy,alpha=.65,color=['#a8b8c8','#72ae9c','#aeb995','#caab8a'][label],label=str(label));axs[0].plot(xx,yy,lw=.7,color='black')
for ax in axs:ax.set_aspect('equal');ax.set(xlabel='ENU east m',ylabel='ENU north m')
axs[0].set_title('20 Cabot spatial roof modes and derived boundaries');axs[1].set_title('Estimated roof zones; source footprint preserved');fig.tight_layout();fig.savefig(R/'references/twenty_cabot_spatial_roof001.png',dpi=140)
report={'building_id':f['id'],'source_geometry':f,'zones':records,'shared_scene_origin_odn_m':4.28000021,'method':'Stable DSM seeds within1.25m of four observed ODN modes, spatial nearest-seed fill,3x3majority,0.55m boundary simplification, minor islands<8m2 omitted,0.65m opening/closing and top dominant patch rotated-rectangle fit. These are estimated architectural regularization steps. Exact full mapped outline retained. Missing-data edges inferred, not measured wall coordinates.','unverified':['No photo facade transferred from foreground western group','Mixed-vintage DSM and mapped footprint','Roof boundaries resolved only at1m data scale; minor slivers merged to middle roof'],'geometry_scope':'Roof massing only; no doors/windows/equipment','visual_reviewed':False};(R/'references/twenty_cabot_spatial_roof001.json').write_text(json.dumps(report,indent=2)+'\n');print([(r['label'],r['height_m'],r['area_m2']) for r in records])
