"""002: one mapped-axis rectangular notch, fitted on training samples only."""
from pathlib import Path
import json,hashlib,warnings
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point
from shapely import set_precision
from shapely.ops import unary_union,transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore',category=DeprecationWarning)
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';old=R/'exports/westferry-house-massing-001/westferry_house_roof_study.json';r=json.loads(old.read_text());g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']==r['building_id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 # Preserve exact001 raster sampling grid/window to keep the heldout split identical.
 owners=[b for b in g['buildings'] if any(k in b['id'] for k in ['26bcb1ba','6019910a','3a202b7c'])];bounds=unary_union([Polygon(b['geometry'][0]['outer']) for b in owners]).buffer(4)
 w=from_bounds(*transform(fw.transform,bounds).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);xx=np.array(xx).reshape(d.shape);yy=np.array(yy).reshape(d.shape);x,y=bk.transform(xx,yy)
z=np.asarray(d,float);interior=(~np.ma.getmaskarray(d))&np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);levels=np.array(r['levels_odn_m']);dist=abs(z[...,None]-levels);coherent=interior&(dist.min(axis=2)<.45);hold=(rr*3+cc)%5==0
pts=np.column_stack([x[coherent],y[coherent]]);labels=dist.argmin(axis=2)[coherent];test=hold[coherent];high=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in r['partitions'] if q['class']==1]);base=np.array([high.covers(Point(a,b)) for a,b in pts],int)
# Long source south-edge direction is the only allowed orientation.
ring=np.array(f['geometry'][0]['outer']);u=ring[0]-ring[-1];u/=np.linalg.norm(u);v=np.array([-u[1],u[0]]);uv=pts@np.column_stack([u,v]);
# Explicit reviewed north-central support window. No changes outside this region.
roi=(pts[:,0]>-477)&(pts[:,0]<-451)&(pts[:,1]>71)&(pts[:,1]<83);train=~test;candidate_low=roi&train&(labels==0)&(base==1);low_uv=uv[candidate_low]
assert len(low_uv)>=15
print('supported low training',len(low_uv),'UV extents',low_uv.min(axis=0),low_uv.max(axis=0))
# One connected rectangular recess only; search edge-aligned boundaries at0.5m.
# Assess class errors over all training cells; tie-break toward smaller new area.
best=None
for a in np.arange(low_uv[:,0].min()-1,low_uv[:,0].min()+3,.5):
 for b in np.arange(low_uv[:,0].max()-3,low_uv[:,0].max()+1,.5):
  if b-a<3 or b-a>20:continue
  for c in np.arange(low_uv[:,1].min()-1,low_uv[:,1].min()+3,.5):
   rectuv=np.array([[a,c],[b,c],[b,uv[:,1].max()+20],[a,uv[:,1].max()+20]]);rect=Polygon(rectuv@np.stack([u,v]));notch=high.intersection(rect)
   if notch.is_empty or notch.geom_type!='Polygon' or notch.area>220:continue
   inside=(uv[:,0]>=a)&(uv[:,0]<=b)&(uv[:,1]>=c)&(base==1);pred=base.copy();pred[inside]=0
   # More than a few isolated low points and real connection to the low roof.
   if ((labels==0)&inside&train).sum()<15:continue
   low= p.difference(high)
   if notch.boundary.intersection(low.boundary).length<2:continue
   score=(int((pred[train]!=labels[train]).sum()),float(notch.area))
   if best is None or score<best[0]:best=(score,notch,pred,[float(a),float(b),float(c)])
assert best is not None
score,notch,pred,cuts=best;newhigh=set_precision(high.difference(notch),1e-8);newlow=p.difference(newhigh);report={k:r[k] for k in ['building_id','levels_odn_m','levels_scene_m','regional_vertical_offset_m_odn','interfaces','limitations']};report['partitions']=[]
for k,part in [(0,newlow),(1,newhigh)]:
 for q in ([part] if part.geom_type=='Polygon' else list(part.geoms)):
  report['partitions'].append({'class':k,'height_scene_m':r['levels_scene_m'][k],'outer':list(q.exterior.coords)[:-1],'holes':[list(h.coords)[:-1] for h in q.interiors]})
allpts=np.column_stack([x[interior],y[interior]]);allpred=np.array([newhigh.covers(Point(a,b)) for a,b in allpts],int);allerr=abs(levels[allpred]-z[interior]);excluded=interior&~coherent;expts=np.column_stack([x[excluded],y[excluded]]);expred=np.array([newhigh.covers(Point(a,b)) for a,b in expts],int);exerr=abs(levels[expred]-z[excluded]);inside=np.array([notch.covers(Point(a,b)) for a,b in pts]);notch_all=np.array([notch.covers(Point(a,b)) for a,b in allpts]);
report['fit']={'method':'Retain001 mapped-axis terraces; add exactly one north-central mapped-axis rectangular notch connected to existing northern low terrace. Boundaries searched at0.5m using training coherent samples only; minimum15lowtraining support; maximum220m2. No tree complexity increase.','train_cells':int(train.sum()),'heldout_cells':int(test.sum()),'baseline_train_class_accuracy':float(np.mean(base[train]==labels[train])),'train_class_accuracy':float(np.mean(pred[train]==labels[train])),'baseline_heldout_class_accuracy':float(np.mean(base[test]==labels[test])),'heldout_class_accuracy':float(np.mean(pred[test]==labels[test])),'heldout_absolute_height_error_quantiles_m':np.percentile(abs(levels[pred[test]]-z[coherent][test]),[50,90,95,100]).tolist()}
report['support']={'interior_cells_total':int(interior.sum()),'coherent_plateau_cells':int(coherent.sum()),'coherent_fraction':float(coherent.sum()/interior.sum()),'excluded_transition_or_other_cells':int(excluded.sum()),'excluded_abs_residual_quantiles_p50_p90_p95_p100_m':np.percentile(exerr,[50,90,95,100]).tolist(),'all_interior_abs_residual_quantiles_p50_p90_p95_p100_m':np.percentile(allerr,[50,90,95,100]).tolist(),'all_interior_outliers_gt2m_count':int((allerr>2).sum()),'notch':{'polygon_enu_m':list(notch.exterior.coords)[:-1],'area_m2':float(notch.area),'orientation_u':u.tolist(),'orientation_v':v.tolist(),'cuts_u_left_u_right_v_lower_m':cuts,'coherent_training_low_count':int((inside&train&(labels==0)).sum()),'coherent_training_high_count':int((inside&train&(labels==1)).sum()),'coherent_heldout_low_count':int((inside&test&(labels==0)).sum()),'coherent_heldout_high_count':int((inside&test&(labels==1)).sum()),'all_interior_notch_cells':int(notch_all.sum()),'all_interior_notch_dsm_quantiles_p10_p50_p90_m_odn':np.percentile(z[interior][notch_all],[10,50,90]).tolist()},'caution':'Notch shape/edges inferred at1mDSM scale, not surveyed. Excluded cells and shallow residuals not smoothed away. Unmodeled roof details and raised-ground interface remain.'}
report['source_hashes']={str(q.relative_to(R)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [old,R/'geometry.json',R/'references/ea_dsm_1m.tif']}
# Solids and exact outer-boundary restoration as001.
import trimesh
from shapely.ops import nearest_points
solids=[trimesh.creation.extrude_polygon(p,height=report['levels_scene_m'][0],engine='earcut')]
for q in ([newhigh] if newhigh.geom_type=='Polygon' else list(newhigh.geoms)):
 top=trimesh.creation.extrude_polygon(q,height=report['levels_scene_m'][1]-report['levels_scene_m'][0],engine='earcut');top.apply_translation([0,0,report['levels_scene_m'][0]]);solids.append(top)
mesh=trimesh.boolean.union(solids,engine='manifold');coords=mesh.vertices.copy();corners=np.array(list(p.exterior.coords)[:-1]);exactlevels=np.r_[0,report['levels_scene_m']]
for pt in coords:
 dd=np.linalg.norm(corners-pt[:2],axis=1)
 if dd.min()<.0001:pt[:2]=corners[dd.argmin()]
 elif p.boundary.distance(Point(pt[:2]))<.0001:pt[:2]=nearest_points(p.boundary,Point(pt[:2]))[0].coords[0]
 pt[2]=exactlevels[np.argmin(abs(exactlevels-pt[2]))]
mesh.vertices=coords;normals=mesh.face_normals;report['vertices']=mesh.vertices.tolist();report['faces']=mesh.faces.tolist();report['materials']=[1 if n[2]>.99 else 0 for n in normals];roofarea=float(mesh.area_faces[normals[:,2]>.99].sum());report['checks']={'finite':bool(np.isfinite(coords).all()),'watertight':bool(mesh.is_watertight),'consistent_winding':bool(mesh.is_winding_consistent),'volume_m3':float(mesh.volume),'source_footprint_area_m2':float(p.area),'roof_projected_area_m2':roofarea,'area_difference_m2':roofarea-p.area,'partition_area_difference_m2':newhigh.area+newlow.area-p.area,'notch_area_removed_from_high_roof_m2':float(high.area-newhigh.area),'internal_polygon_precision_m':1e-8,'solid_construction':'Whole exact-footprint lower body plus upper terrace solid; final outer boundary snapped to source below0.1mm' };assert mesh.is_watertight and mesh.is_winding_consistent and abs(roofarea-p.area)<.001
fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained');axs[0].scatter(pts[:,0],pts[:,1],c=labels,cmap='viridis',s=9);axs[1].scatter(allpts[:,0],allpts[:,1],c=allerr,cmap='magma',s=8,vmin=0,vmax=6)
for k,part in [(0,newlow),(1,newhigh)]:
 for q in ([part] if part.geom_type=='Polygon' else list(part.geoms)):
  xx,yy=q.exterior.xy;axs[2].fill(xx,yy,color=plt.cm.viridis(float(k)),alpha=.75)
for ax in axs:
 ax.plot(*p.exterior.xy,color='black',lw=.7);ax.plot(*notch.exterior.xy,color='red',lw=1.8);ax.set(aspect='equal',xlabel='Local east(m)',ylabel='Local north(m)')
axs[0].set_title('Plateau support; red = constrained notch');axs[1].set_title('All interior residual; scale0–6m, higher clipped');axs[2].set_title('002 roof partitions, exact outer footprint');fig.savefig(R/'references/westferry_house_roof_study_002.png',dpi=170)
report['visual_review']={'plot_inspected':False,'render_inspected':False};report['limitations']=[q for q in report['limitations'] if 'north' not in q.lower()];report['limitations']+=['002 resolves supported north-central notch with one constrained rectangle; exact returns/ledge offsets remain inferred.']
(R/'references/westferry_house_roof_study_002.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'fit':report['fit'],'support':report['support'],'checks':report['checks']},indent=2))
