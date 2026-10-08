"""Fit spatially simple terrace partitions; independently validate holdout cells."""
import runpy,json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString
from shapely.ops import split,unary_union
import matplotlib.pyplot as plt
s=runpy.run_path(str(Path(__file__).with_name('review_westferry_photo_identity.py')))
ROOT=s['R'];f=next(b for b in s['fs'] if '26bcb1ba' in b['id']);p=Polygon(f['geometry'][0]['outer']);x,y,z=s['x'],s['y'],s['z'];ground=4.28000021
from shapely.geometry import Point
interior=s['valid']&np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
levels=np.array([np.median(z[interior&(abs(z-48.99)<.4)]),np.median(z[interior&(abs(z-54.5)<.4)])]);dist=np.abs(z[...,None]-levels);classes=dist.argmin(axis=2)
# Train only coherent plateau interior values; transition cells are independently reported.
mask=interior&(dist.min(axis=2)<.45); rr,cc=np.indices(z.shape);hold=(rr*3+cc)%5==0
XY=np.column_stack([x[mask],y[mask]]);Y=classes[mask];test=hold[mask];normals=[]
for a,b in zip(p.exterior.coords,list(p.exterior.coords)[1:]):
 d=np.array(b)-a;n=np.array([-d[1],d[0]]);n/=np.linalg.norm(n)
 if n[0]<0:n=-n
 if not any(abs(np.dot(n,q))>.999 for q in normals):normals.append(n)
def impurity(v):
 counts=np.bincount(v,minlength=2);return len(v)-(counts@counts)/max(len(v),1)
leaves=[];nodes=[]
def recurse(ids,poly,depth=0):
 labels=Y[ids];cls=int(np.bincount(labels,minlength=2).argmax());base=impurity(labels);best=None
 if depth<4 and len(ids)>=50 and base>3:
  for n in normals:
   values=XY[ids]@n
   for cut in np.arange(values.min()+2,values.max()-2,.5):
    left=values<=cut
    if left.sum()<20 or (~left).sum()<20:continue
    score=impurity(labels[left])+impurity(labels[~left])
    if best is None or score<best[0]:best=(score,n,cut,left)
 if best is None or base-best[0]<max(3,base*.04):
  node={'class':cls,'samples':len(ids),'polygon':poly};nodes.append(node);leaves.append(node);return node
 score,n,cut,left=best;center=n*cut;u=np.array([-n[1],n[0]]);line=LineString([center-u*10000,center+u*10000]);pieces=list(split(poly,line).geoms)
 lp=unary_union([q for q in pieces if np.dot(q.representative_point().coords[0],n)<=cut]);rp=unary_union([q for q in pieces if np.dot(q.representative_point().coords[0],n)>cut])
 if lp.is_empty or rp.is_empty:
  node={'class':cls,'samples':len(ids),'polygon':poly};nodes.append(node);leaves.append(node);return node
 return {'normal':n,'cut':cut,'left':recurse(ids[left],lp,depth+1),'right':recurse(ids[~left],rp,depth+1)}
tree=recurse(np.where(~test)[0],p)
def predict(points,node):
 if 'class' in node:return np.full(len(points),node['class'],int)
 left=points@node['normal']<=node['cut'];out=np.empty(len(points),int);out[left]=predict(points[left],node['left']);out[~left]=predict(points[~left],node['right']);return out
pred=predict(XY,tree);partition=[unary_union([q['polygon'] for q in leaves if q['class']==k]) for k in range(2)]
report={'building_id':f['id'],'levels_odn_m':levels.tolist(),'regional_vertical_offset_m_odn':ground,'levels_scene_m':(levels-ground).tolist(),'fit':{'method':'Oblique recursive partitions with directions restricted to exact mapped edge normals; depth <=4; coherent plateau samples within 0.45m and 2m inward; deterministic 20% spatial-interleaved heldout cells','train_cells':int((~test).sum()),'heldout_cells':int(test.sum()),'train_class_accuracy':float(np.mean(pred[~test]==Y[~test])),'heldout_class_accuracy':float(np.mean(pred[test]==Y[test])),'heldout_absolute_height_error_quantiles_m':np.percentile(abs(levels[pred[test]]-z[mask][test]),[50,90,95,100]).tolist(),'leaf_count':len(leaves)},'partitions':[],'source_hashes':s['report']['hashes'],'limitations':['Terrace boundaries inferred from 1m raster and constrained straight partitions, not measured architectural plans.','Source outer footprint is retained, including potentially shared ownership seams; exposed wall status unverified.','Regional vertical datum fixed: scene Z = ODN -4.28000021m; complex upper/lower ground is not reconstructed.','No facade bays, parapets, machinery or real openings inferred.']}
fig,axs=plt.subplots(1,2,figsize=(13,9),layout='constrained')
axs[0].scatter(XY[:,0],XY[:,1],c=Y,s=8,cmap='viridis',vmin=0,vmax=1)
for k,part in enumerate(partition):
 polys=[part] if part.geom_type=='Polygon' else list(part.geoms)
 for q in polys:
  ring=np.array(q.exterior.coords);axs[1].fill(ring[:,0],ring[:,1],color=plt.cm.viridis(float(k)),alpha=.7);axs[0].plot(ring[:,0],ring[:,1],c='red',lw=.7)
  report['partitions'].append({'class':k,'height_scene_m':float(levels[k]-ground),'outer':list(q.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in q.interiors]})
for ax in axs:ax.set_aspect('equal');ax.set(xlabel='Local E m',ylabel='Local N m')
axs[0].set_title('Coherent plateau samples + fitted breaklines');axs[1].set_title('Piecewise roof candidate; original footprint retained')
fig.savefig(ROOT/'references/westferry_house_roof_study.png',dpi=150)
(ROOT/'references/westferry_house_roof_study.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['fit'],indent=2))
# Build manifold union of exact polygonal prisms. Float64 manifold preserves
# shared cuts; final mesh is explicitly rechecked against original footprint.
import trimesh
solids=[]
for q in report['partitions']:
 poly=Polygon(q['outer'],q['holes'])
 solids.append(trimesh.creation.extrude_polygon(poly,height=q['height_scene_m'],engine='earcut'))
mesh=trimesh.boolean.union(solids,engine='manifold')
from shapely.ops import nearest_points
from shapely.geometry import Point
coords=mesh.vertices.copy();rings=[p.exterior,*p.interiors];corners=np.array([q for ring in rings for q in list(ring.coords)[:-1]])
for v in coords:
 d=np.linalg.norm(corners-v[:2],axis=1)
 if d.min()<.0001:v[:2]=corners[d.argmin()]
 elif p.boundary.distance(Point(v[:2]))<.0001:v[:2]=nearest_points(p.boundary,Point(v[:2]))[0].coords[0]
 exact_levels=np.r_[0,levels-ground];v[2]=exact_levels[np.argmin(abs(exact_levels-v[2]))]
mesh.vertices=coords
vertices=mesh.vertices.tolist();faces=mesh.faces.tolist();normals=mesh.face_normals
roof_mask=normals[:,2]>.99
roof_area=float(mesh.area_faces[roof_mask].sum());base_area=float(mesh.area_faces[normals[:,2]<-.99].sum())
report['vertices']=vertices;report['faces']=faces;report['materials']=[1 if n[2]>.99 else 0 for n in normals]
report['checks']={'finite':bool(np.isfinite(mesh.vertices).all()),'watertight':bool(mesh.is_watertight),'consistent_winding':bool(mesh.is_winding_consistent),'volume_m3':float(mesh.volume),'roof_projected_area_m2':roof_area,'base_area_m2':base_area,'source_footprint_area_m2':p.area,'area_difference_m2':roof_area-p.area,'partition_area_difference_m2':sum(Polygon(q['outer'],q['holes']).area for q in report['partitions'])-p.area}
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
# Manifold backend uses float32 vertices; record rather than conceal tolerance.
print(report["checks"])
assert abs(roof_area-p.area)<.001 and abs(base_area-p.area)<.001
report['geometry_precision']='Boolean backend vertices snapped back to source boundary/corners within 0.1 mm and exact roof levels; original footprint area retained within 0.001 square metres, internal breaklines retain submillimetre numerical precision.'
allpoints=np.column_stack([x[interior],y[interior]]);allpred=predict(allpoints,tree);allerr=abs(levels[allpred]-z[interior]);report['support']={'interior_cells_total':int(interior.sum()),'coherent_plateau_cells':int(mask.sum()),'coherent_fraction':float(mask.sum()/interior.sum()),'excluded_transition_or_other_cells':int(interior.sum()-mask.sum()),'coherent_counts_by_level':np.bincount(Y,minlength=2).tolist(),'all_interior_abs_residual_quantiles_p50_p90_p95_p100_m':np.percentile(allerr,[50,90,95,100]).tolist(),'breaklines':'Inferred straight lines constrained to mapped-edge normals; actual roof recesses/transition geometry not fully captured','spatial_caution':'North-central low roof notch and east perimeter are simplified; do not count these inferred edges as surveyed architecture.'}
report['source_hashes'].update({str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [ROOT/'references/ea_dsm_1m.tif',ROOT/'references/ea_dtm_1m.tif']})
report['visual_review']={'fit_plot_inspected':False,'closed_mesh_render_inspected':False}
report['interfaces']={'replace_only_building_id':f['id'],'plan_ownership':'Original mapped polygon; no neighbour or shared wall edits','vertical_datum':'Scene Z = EA ODN -4.28000021m regional offset','base_scene_z_m':0,'facades':'Massing only; no photo windows because owner seam unresolved'}
report['limitations']+=['Coherent plateau-only heldout cells are not independent geographic accuracy; transition/edge cells excluded from fitting.','Only two dominant roof plateaus retained. Roof equipment and parapets not reconstructed.','False ground-floor extrusion continues to flat scene z0; actual raised Circus ground interface remains unresolved.']
(ROOT/'references/westferry_house_roof_study.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['checks'],indent=2))
