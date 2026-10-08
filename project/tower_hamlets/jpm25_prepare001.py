from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box,Point
from shapely.ops import transform,triangulate
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/jpm25-evidence-001';a=json.load(open(O/'jpm25-audit.json'));A=np.array(json.load(open(O/'jpm25-profile.json'))['axes']);orig=Polygon(a['source_geometry']['geometry'][0]['outer']);uvp=Polygon(np.array(orig.exterior.coords)@A.T);tower=uvp.intersection(box(-126,-288.5,1000,1000)).difference(box(-65.5,-1000,1000,-274.5));central=tower.intersection(box(-112,-274,-73,-258));d=np.load(O/'jpm25-samples.npz');m=d['inside']&d['valid'];xy=np.c_[d['x'][m],d['y'][m]];uv=xy@A.T;z=d['z'][m];tm=np.array([tower.covers(Point(q)) for q in uv]);cm=np.array([central.covers(Point(q)) for q in uv]);pm=~tm;selection=[pm&(z>45)&(z<65),tm&~cm&(z>152)&(z<156),cm&(z>158)&(z<161)];heights=[float(np.median(z[q])) for q in selection]
def metric(e):return {'n':len(e),'rmse':float(np.sqrt(np.mean(e**2))),'mae':float(np.mean(abs(e))),'p95_absolute':float(np.percentile(abs(e),95)),'within_1m':int((abs(e)<=1).sum())}
pred=np.where(cm,heights[2],np.where(tm,heights[1],heights[0]));folds=[]
for axis in [0,1]:
 fold=np.floor(uv[:,axis]/5).astype(int)%2;pp=np.zeros(len(z))
 for k in [0,1]:
  hh=[float(np.median(z[q&(fold!=k)])) for q in selection];pp[fold==k]=np.where(cm,hh[2],np.where(tm,hh[1],hh[0]))[fold==k]
 folds.append(metric(pp-z))
objects=[]
def solid(name,poly,bottom,top):
 xy2=np.array(poly.exterior.coords[:-1])@A;n=len(xy2);verts=[[float(x),float(y),bottom] for x,y in xy2]+[[float(x),float(y),top] for x,y in xy2];faces=[];pp=Polygon(xy2)
 for tri in triangulate(pp):
  if pp.covers(tri.representative_point()):
   ids=[int(np.argmin(np.linalg.norm(xy2-np.array(q),axis=1))) for q in tri.exterior.coords[:-1]];faces.extend([list(reversed(ids)),[i+n for i in ids]])
 for i in range(n):j=(i+1)%n;faces.append([i,j,j+n,i+n])
 objects.append({'name':name,'vertices':verts,'faces':faces,'building_id':a['source_geometry']['id'],'uv_polygon':list(poly.exterior.coords),'bottom_scene':bottom,'top_scene':top})
z0=4.28000021;solid('jpm25_continuous_podium_estimated_gap_cover',uvp,0,heights[0]-z0);solid('jpm25_northern_tower_estimated_breaklines',tower,heights[0]-z0,heights[1]-z0);solid('jpm25_central_raised_roof_envelope',central,heights[1]-z0,heights[2]-z0)
r={'owner_id':a['source_geometry']['id'],'datum_odn':z0,'axes':A.tolist(),'heights_odn':heights,'objects':objects,'uncertainty':['Low returns covered by continuous podium hypothesis, no invented courtyard.','Tower breaklines approximate from high-return support; no photo constraint.','Central raised block is envelope only, equipment unresolved.','Roof perimeter and small raised features omitted, not generic arrays.','Facade/base0 unresolved; all source owner footprint retained.'],'all_cells':metric(pred-z),'baseline_all_cells':metric(np.full(len(z),153+z0)-z),'spatial_holdout_all_cells':folds,'estimated_cover_low_cells':int(((z<20)&pm).sum()),'supported_fit_counts':[int(q.sum()) for q in selection]};(R/'references/jpm25-authoring001.json').write_text(json.dumps(r,indent=2));fig,axs=plt.subplots(1,3,figsize=(16,6),layout='constrained')
for ax,val,title in zip(axs,[z,pred,pred-z],['All valid DSM ODN','Candidate top ODN (includes estimated cover)','Candidate minus DSM, all cells']):
 im=ax.scatter(*uv.T,c=val,s=8,cmap='viridis' if title!='Candidate minus DSM, all cells' else 'coolwarm');fig.colorbar(im,ax=ax);ax.plot(*uvp.exterior.xy,'k');ax.plot(*tower.exterior.xy,'r');ax.plot(*central.exterior.xy,'r');ax.set(aspect='equal',title=title)
fig.savefig(O/'jpm25-candidate-fit.png',dpi=150);print({k:v for k,v in r.items() if k not in ['objects','uncertainty']})
