from pathlib import Path
import json,hashlib,zipfile
import numpy as np
from shapely.geometry import Polygon,Point
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent; R=P/'input/canary_wharf_20261007'; O=R/'exports/morgan-west-south002'; O.mkdir(exist_ok=True)
a=np.load(R/'exports/morgan-west-south-roof-study-001/zone-samples.npz');u,v,z=[a[k] for k in ['u','v','z_odn']]
src=json.loads((R/'references/morgan_massing_study_002.json').read_text());zone=next(q for q in src['zones'] if q['name']=='podium_west_south');poly=Polygon(zone['support_xy'][0]['outer'])
def stats(e):
 return {'n':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'mae_m':float(np.mean(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95)),'within1m':int((abs(e)<=1).sum())}
def label(u,v,cu,cv):return np.where((u<cu)&(v>=cv),0,np.where((u>=cu)&(v<cv),2,1))
# Training-only grid search: every training return contributes absolute residual; no low-return mask.
candidates=[]
for cu in np.arange(-340,-336.99,.25):
 for cv in np.arange(-152,-148.99,.25):candidates.append((float(cu),float(cv),label(u,v,cu,cv)))
def fit(train):
 best=None
 for cu,cv,l in candidates:
  groups=[z[train&(l==k)] for k in range(3)]
  if min(map(len,groups))<3:continue
  hs=np.array([np.median(g) for g in groups]);pred=hs[l];loss=float(np.mean(abs(z[train]-pred[train])))
  if best is None or loss<best[0]:best=(loss,cu,cv,hs,pred)
 return best
allfit=fit(np.ones(len(z),bool));_,cu,cv,hs,pred=allfit
foldreports=[]
for axis,coord in [('u',u),('v',v)]:
 for width in [1.,2.,3.]:
  folds=np.floor((coord-coord.min())/width).astype(int)%3;errs=[];baseerrs=[];rows=[]
  for f in range(3):
   train=folds!=f;test=~train;sol=fit(train)
   if sol is None:continue
   loss,bu,bv,h,p=sol;e=z[test]-p[test];errs.extend(e);baseerrs.extend(z[test]-59.6635)
   rows.append({'fold':f,'train_n':int(train.sum()),'test_n':int(test.sum()),'u_break':bu,'v_break':bv,'levels_odn':h.tolist(),'test':stats(e)})
  foldreports.append({'axis':axis,'strip_width_m':width,'folds':rows,'all_test':stats(np.array(errs)),'baseline_all_test':stats(np.array(baseerrs))})
d=np.array([poly.boundary.distance(Point(x,y)) for x,y in zip(a['x'],a['y'])]);subsets=[]
for t in [0,.5,1,1.5,2]:
 m=d>=t;subsets.append({'inset':t,'inside':stats(z[m]-pred[m]),'outside':stats(z[~m]-pred[~m]) if (~m).any() else None})
# Context uses all archived DSM cells, including outside selected zone; do not infer ownership from heights.
b=np.load(R/'exports/morgan-roof-visibility-audit-001/samples.npz');ang=np.deg2rad(-10);U=b['x']*np.cos(ang)+b['y']*np.sin(ang);V=-b['x']*np.sin(ang)+b['y']*np.cos(ang);ZZ=b['z_odn'];m=b['valid']&(U>=u.min()-3)&(U<=u.max()+3)&(V>=v.min()-3)&(V<=v.max()+5)
fig,axs=plt.subplots(1,2,figsize=(16,9),layout='constrained')
for ax,vals,title in [(axs[0],ZZ,'Native DSM context: all valid returns'),(axs[1],ZZ-b['dtm_odn'],'DSM minus DTM (not scene z)')]:
 im=ax.scatter(U[m],V[m],c=vals[m],s=125,marker='s',vmin=0,vmax=80);fig.colorbar(im,ax=ax)
 for q in src['zones']:
  if q['owner']!=zone['owner']:continue
  for ring in q['support_xy']:
   xy=np.array(ring['outer']);uv=xy@np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]]);ax.plot(*uv.T,'k-',lw=1)
 ax.axvline(cu,c='red',ls='--');ax.axhline(cv,c='red',ls='--');ax.set(xlim=(u.min()-3,u.max()+3),ylim=(v.min()-3,v.max()+5),aspect='equal',title=title,xlabel='u m',ylabel='v m')
 for x,y,h in zip(U[m],V[m],vals[m]):ax.text(x,y,f'{h:.0f}',fontsize=5,ha='center',va='center')
fig.savefig(O/'context.png',dpi=160);plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(16,7),layout='constrained')
for ax,val,title in [(axs[0],z,'All 111 native returns'),(axs[1],pred,'Three-level fitted diagnostic'),(axs[2],z-pred,'Residual: no exclusions')]:
 im=ax.scatter(u,v,c=val,s=150,marker='s',cmap='coolwarm' if ax==axs[2] else 'viridis');fig.colorbar(im,ax=ax);ax.axvline(cu,color='k');ax.axhline(cv,color='k');ax.set(aspect='equal',title=title,xlabel='u m',ylabel='v m')
fig.savefig(O/'partition.png',dpi=160);plt.close(fig)
# Boundary strip: actual DSM medians at interfaces; no projection to new roof surfaces.
interface=[]
for q in src['zones']:
 if q['owner']!=zone['owner'] or q['name']==zone['name']:continue
 pp=Polygon(q['support_xy'][0]['outer']);contact=poly.boundary.intersection(pp.boundary.buffer(1e-5))
 if contact.length<.01:continue
 near=np.array([contact.distance(Point(x,y))<1.1 for x,y in zip(a['x'],a['y'])]);interface.append({'neighbor_zone':q['name'],'contact_m':contact.length,'neighbor_existing_odn':q['odn_m'],'selected_side_cell_xyz_odn':np.c_[a['x'][near],a['y'][near],z[near]].tolist(),'selected_candidate_levels':pred[near].tolist(),'note':'Within 1.1 m on selected side only; height differences do not alone establish wall topology.'})
files=['references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/morgan_massing_study_002.json','exports/morgan-roof-visibility-audit-001/samples.npz','exports/morgan-west-south-roof-study-001/zone-samples.npz']
out={'scope':zone,'method':'Three levels with shared middle plateau, mapped -10 degree axes. Breaks selected on training-only absolute residual grid; every return retained. Spatial folds refit boundaries and levels. Conditional model-family validation, not independent roof-edge survey.','datum_odn_m':4.28000021,'capture_date':None,'fit':{'u_break':cu,'v_break':cv,'levels_odn':hs.tolist(),'baseline':stats(z-59.6635),'full':stats(z-pred)},'nested_spatial_holdout':foldreports,'boundary_subsets':subsets,'interfaces':interface,'sources':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in files},'geometry_changed':False}
(O/'evaluation.json').write_text(json.dumps(out,indent=2));np.savez(O/'predictions.npz',u=u,v=v,z_odn=z,predicted_odn=pred,boundary_distance_m=d)
print(json.dumps({'fit':out['fit'],'holdouts':[{k:r[k] for k in ['axis','strip_width_m','all_test']} for r in foldreports],'subsets':subsets},indent=2))
