"""Conditional low roof plane; taller returns stay in native observations."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;source=(S/'analyze_ledger_lidar.py').read_text();ns={'__file__':str(S/'analyze_ledger_lidar.py')};exec(compile(source.split('rep=')[0],str(S/'analyze_ledger_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','p','masks','f']:globals()[k]=ns[k]
sel=masks['2']&(z>9.6)&(z<11);cx=float(x[sel].mean());cy=float(y[sel].mean());B=np.column_stack([np.ones(sel.sum()),x[sel]-cx,y[sel]-cy]);zz=z[sel];fold=(np.floor((x[sel]-x[sel].min())/3).astype(int)%3)
def fit(train):return least_squares(lambda c:B[train]@c-zz[train],[10.2,0,0],loss='soft_l1',f_scale=.1).x
errors=[]
for k in range(3):
 test=fold==k;errors.extend(zz[test]-B[test]@fit(~test))
c=fit(np.ones(len(zz),bool));pred=c[0]+c[1]*(x-cx)+c[2]*(y-cy);e=np.array(errors);support=sel&(abs(z-pred)<=.25);vertices=[];faces=[];lookup={};area=0
for i in range(z.shape[0]-1):
 for j in range(z.shape[1]-1):
  for tri in [[(i,j),(i,j+1),(i+1,j+1)],[(i,j),(i+1,j+1),(i+1,j)]]:
   if not all(support[q] for q in tri):continue
   xy=np.array([[x[q],y[q]] for q in tri]);a=float(np.linalg.det(np.array([xy[1]-xy[0],xy[2]-xy[0]])))
   if a<0:tri.reverse()
   inds=[]
   for q in tri:
    if q not in lookup:lookup[q]=len(vertices);vertices.append([float(x[q]),float(y[q]),float(pred[q]-4.28000021)])
    inds.append(lookup[q])
   faces.append(inds);area+=abs(a)/2
obj=ROOT/'references/ledger_plane_roof.obj';obj.write_text('# Conditional low roof plane; unsupported/tall returns retained separately\n'+''.join('v '+' '.join(f'{a:.8f}' for a in q)+'\n' for q in vertices)+''.join('f '+' '.join(str(a+1) for a in q)+'\n' for q in faces))
fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained');m=masks['0'];im=axs[0].scatter(x[m],y[m],c=z[m],vmin=9,vmax=13,s=12);fig.colorbar(im,ax=axs[0],label='DSM ODN m');axs[0].set(title='Ledger: low roof and higher returns',aspect='equal');im=axs[1].scatter(x[sel],y[sel],c=(z-pred)[sel],cmap='RdBu_r',vmin=-.5,vmax=.5,s=12);fig.colorbar(im,ax=axs[1],label='DSM minus plane m');axs[1].set(title='Conditional low-plane residuals',aspect='equal');fig.savefig(ROOT/'references/ledger_plane_fit.png',dpi=150)
r={'building_id':f['id'],'datum_odn_m':4.28000021,'plane_center_xy_m':[cx,cy],'plane_coefficients_odn_m':c.tolist(),'selection':'2m inset;9.6<DSM<11ODN, conditional low surface only','validation':'Three folds of3m east strips; no residual-based test rejection','test_cells':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95)),'candidate':{'obj':obj.name,'vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'support':'All vertices within0.25m of plane and selected interior cells'},'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif']},'limitations':['High returns are unresolved features; do not remove from full observations.','Conditional fit cannot establish full roof shape, equipment or parapets.','Common group datum is not surveyed local foundation.'],'visual_reviewed':False}
(ROOT/'references/ledger_plane_fit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
