from pathlib import Path
import json,hashlib,warnings
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union,transform
from pyproj import Transformer
from sklearn.tree import DecisionTreeRegressor
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());contract=json.loads((R/'references/morgan_replacement_interface_proposed.json').read_text());selected=['overture-part-39303788-2936-3e7c-b0d3-558b2a9bb939','overture-part-31757561-bd81-3255-a8ee-f9e6919da48f','overture-part-b317a51d-586a-3b78-9ee5-b685a2db94a0'];domains={q['owner']:unary_union([Polygon(p['outer'],p.get('holes',[])) for p in q['exclusive_domains']]) for q in contract['domains'] if q['owner'] in selected};union=unary_union(list(domains.values()));fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,union.buffer(2)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));z=ds.read(1,window=w,masked=True);rr,cc=np.indices(z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(z.shape),np.array(yy).reshape(z.shape))
valid=~np.ma.getmaskarray(z);z=np.array(z,float);theta=np.deg2rad(-10);co,si=np.cos(theta),np.sin(theta)
def uv(a,b):return np.asarray(a)*co+np.asarray(b)*si,-np.asarray(a)*si+np.asarray(b)*co
def xy(a,b):return np.asarray(a)*co-np.asarray(b)*si,np.asarray(a)*si+np.asarray(b)*co
u,v=uv(x,y);A=np.stack([u,v],axis=-1)
def mask(p):return valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
def metric(e):return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95)),'median_abs_m':float(np.median(abs(e)))}
rows=[];fig,axs=plt.subplots(1,3,figsize=(19,7),layout='constrained')
for ax,(owner,p) in zip(axs,domains.items()):
 m=mask(p.buffer(-2));X=A[m];Z=z[m];model=DecisionTreeRegressor(max_leaf_nodes=8,min_samples_leaf=35,max_depth=5,criterion='absolute_error',random_state=0).fit(X,Z);tree=model.tree_;pu=transform(uv,p);leaves=[]
 def walk(n,q):
  if tree.children_left[n]<0:
   leaves.append((n,q,float(tree.value[n,0,0])));return
  cut=tree.threshold[n];axis=tree.feature[n];lo=list(q.bounds[:2]);hi=list(q.bounds[2:]);hi[axis]=min(hi[axis],cut);left=q.intersection(box(*lo,*hi));lo=list(q.bounds[:2]);hi=list(q.bounds[2:]);lo[axis]=max(lo[axis],cut);right=q.intersection(box(*lo,*hi));walk(tree.children_left[n],left);walk(tree.children_right[n],right)
 walk(0,pu);fold_metrics={}
 for axis in [0,1]:
  folds=np.floor((X[:,axis]-X[:,axis].min())/4).astype(int)%3;err=np.zeros(len(Z))
  for k in range(3):
   train=folds!=k;test=~train;md=DecisionTreeRegressor(max_leaf_nodes=8,min_samples_leaf=25,max_depth=5,criterion='absolute_error',random_state=0).fit(X[train],Z[train]);err[test]=Z[test]-md.predict(X[test])
  fold_metrics['uv'[axis]]=metric(err)
 patches=[]
 for node,q,height in leaves:
  if q.is_empty:continue
  geographic=transform(xy,q);support=geographic.buffer(-1.5).intersection(p.buffer(-2));sel=mask(support)
  if sel.sum()<12:check={'cells':int(sel.sum()),'status':'insufficient interior'}
  else:
   zz=z[sel];checks={}
   for axis,arr in [('u',u[sel]),('v',v[sel])]:
    folds=np.floor((arr-arr.min())/3).astype(int)%3;e=[]
    for k in range(3):
     tr=folds!=k;te=~tr
     if tr.sum()<5 or te.sum()==0:continue
     e.extend(zz[te]-np.median(zz[tr]))
    checks[axis]=metric(np.array(e)) if e else None
   ok=all(c and c['rmse_m']<.35 and c['p95_abs_m']<.65 for c in checks.values());check={'cells':int(sel.sum()),'median_odn_m':float(np.median(zz)),'holdout':checks,'status':'conditional plateau support' if ok else 'mixed/sloped domain: not accepted'}
  def polygons(a):return [{'outer':list(b.exterior.coords),'holes':[list(h.coords) for h in b.interiors]} for b in getattr(a,'geoms',[a]) if b.geom_type=='Polygon']
  patches.append({'node':int(node),'full_partition_area_m2':geographic.area,'tree_median_odn_m':height,'partition_xy':polygons(geographic),'tested_support_xy':polygons(support),'tested_support_area_m2':support.area,**check})
  for poly in getattr(q,'geoms',[q]):
   if poly.geom_type=='Polygon':ax.plot(*poly.exterior.xy,color='black',lw=.8);ax.text(poly.centroid.x,poly.centroid.y,str(node),fontsize=8)
 im=ax.scatter(u[m],v[m],c=z[m],vmin=30,vmax=92,cmap='viridis',s=8,marker='s');ax.set(aspect='equal',title=owner.split('-')[2]+' exclusive domain',xlabel='u(m)',ylabel='v(m)')
 rows.append({'owner':owner,'input_area_m2':p.area,'native_inset_cells':int(m.sum()),'global_spatial_holdout_retrained_tree':fold_metrics,'patches':patches})
fig.colorbar(im,ax=axs,label='DSM ODN(m)');fig.savefig(R/'references/morgan_roof_regions.png',dpi=140)
r={'datum_odn_m':4.28000021,'regions':rows,'method':'Robust absolute-error2Daxisaligned tree on rotatedfootprint coordinates,8maxleaves,2minset. Globalholdout4mspatialstrips retrains partitions; patchchecks use3mstrips and medianfit, alltestcells retained.','limitations':['Exploratory partition/modelcomplexity selected after viewing DSM; localpatch supports additionally eroded1.5m so boundary uncertainty is not validated.','Conditional plateau checks do not validate extrapolation to fullpartitions or precise architectural roofbreaks.','Mixed2017–2020EA DSM ODN vs2026footprints; sharedscene z=ODN−4.28000021, foundationsunsurveyed.','Photo facade ownership unresolved; no facade details or globalmodelchanges.'],'source_hashes':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['references/morgan_replacement_interface_proposed.json','references/ea_dsm_1m.tif']}}
(R/'references/morgan_roof_regions.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([{'owner':r['owner'],'global':r['global_spatial_holdout_retrained_tree'],'patches':[{k:p[k] for k in ['node','cells','status','tested_support_area_m2']} for p in r['patches']]} for r in rows],indent=2))
