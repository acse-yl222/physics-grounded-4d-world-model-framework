"""Inspect all five Penn Court sibling parts; no scene mutation."""
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
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());pid='eaf88800-10f1-4721-bf3f-75177412aea5';fs=[f for f in g['buildings'] if f.get('parent_id')==pid]
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
rows=[]
for i,(f,q) in enumerate(zip(fs,ps)):
 row={'label':str(i+1),'id':f['id'],'baseline_height_m':f['height_m'],'height_basis':f['height_basis'],'area_m2':q.area,'insets':{}}
 for inset in [0,2,4]:
  m=mask(q.buffer(-inset));row['insets'][str(inset)]={'dsm_odn_m':stats(z[m]),'dtm_odn_m':stats(t[m]),'dsm_minus_dtm_m':stats((z-t)[m])}
 center=np.array(q.centroid.coords[0]);A=np.stack([np.ones(x.shape),x-center[0],y-center[1]],axis=-1)
 row['center_local_xy_m']=center.tolist()
 row['plane_fits']={}
 for inset in [2,4]:
  domain=q.buffer(-inset);m=mask(domain)
  if m.sum()<20:continue
  c=fitplane(m,A);checks={}
  for axis,arr in [('x',x),('y',y)]:
   folds=np.floor((arr-arr[m].min())/3).astype(int)%3;errors=[];records=[]
   for k in range(3):
    test=m&(folds==k);train=m&~test
    if test.sum()==0 or train.sum()<10:continue
    cf=fitplane(train,A);e=z[test]-A[test]@cf;errors.extend(e);records.append({'fold':k,'train_cells':int(train.sum()),**metric(e)})
   checks[axis]={'pooled':metric(np.array(errors)),'folds':records} if errors else {'unavailable':True}
  polygons=list(domain.geoms) if hasattr(domain,'geoms') else [domain]
  row['plane_fits'][str(inset)]={'formula':'ODN=intercept+slope_x*(x-center_x)+slope_y*(y-center_y)','coefficients':c.tolist(),'in_sample':metric(z[m]-A[m]@c),'holdout':checks,'domain_area_m2':domain.area,'domain_local_xy':[{'outer':list(map(list,pp.exterior.coords)),'holes':[list(map(list,h.coords)) for h in pp.interiors]} for pp in polygons]}
 row['boundary_crossing']=f.get('boundary_crossing');row['raster_cell_area_support_fraction']=row['insets']['0']['dsm_odn_m']['cells']/q.area
 rows.append(row)
boundaries=[]
for i,a in enumerate(ps):
 for j,b in enumerate(ps):
  if j<=i:continue
  shared=a.boundary.intersection(b.boundary)
  if shared.length<.1:continue
  sides=[]
  for k,q in [(i,a),(j,b)]:
   strips={}
   for dist in [2,4,6]:
    m=mask(q.intersection(shared.buffer(dist)).difference(shared.buffer(max(0,dist-2))));strips[str(dist)]={'dsm_odn_m':stats(z[m])}
   sides.append({'label':str(k+1),'id':fs[k]['id'],'strips_distance_from_shared_boundary_m':strips})
  boundaries.append({'labels':[str(i+1),str(j+1)],'shared_length_m':shared.length,'sides':sides})
report={'parent_id':pid,'parts':rows,'shared_boundaries':boundaries,'selection':'All valid native DSM cells in geometric insets or successive 0–2, 2–4, 4–6m strips inside each mapped part; no elevation or residual rejection.','limitations':['Mixed 2017–2020 EA DSM/DTM OGL and 2026 Overture footprints. Current appearance is unverified.','DSM ODN is surface elevation; DSM-DTM is not necessarily facade height or scene-local z.','Shared-boundary strips can mix adjacent roof returns and raster interpolation; broad bands do not establish architectural breaklines.','Plane fits use all inset samples without residual rejection; inset domains are conditional sample support, not architectural roof outlines.','No image material or facade evidence; no automatic replacements performed.'],'source_hashes':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'geometry_modified':False,'visual_reviewed':False}
fig,axs=plt.subplots(1,2,figsize=(14,7),layout='constrained');m=mask(p)
im=axs[0].scatter(x[m],y[m],c=z[m],s=10,marker='s',vmin=0,vmax=70,cmap='viridis');fig.colorbar(im,ax=axs[0],label='DSM ODN (m)')
for i,q in enumerate(ps):
 xxp,yyp=q.exterior.xy;axs[0].plot(xxp,yyp,color='red',lw=1);axs[0].text(q.centroid.x,q.centroid.y,str(i+1),color='white',weight='bold',ha='center',bbox={'facecolor':'black','alpha':.5,'pad':2})
 axs[1].scatter(np.full(mask(q.buffer(-2)).sum(),i+1)+np.random.default_rng(42).uniform(-.15,.15,mask(q.buffer(-2)).sum()),z[mask(q.buffer(-2))],s=5,alpha=.4)
axs[0].set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)',title='Penn Court: mapped parent group')
axs[1].set(xlabel='Part label',ylabel='DSM ODN (m)',xticks=range(1,len(fs)+1),title='All 2m-inset cells, no height filtering')
fig.savefig(R/'references/penn_roof_review.png',dpi=150);(R/'references/penn_roof_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
