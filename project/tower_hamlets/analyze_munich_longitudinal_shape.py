"""Test varying ridge amplitude against held-out native cells; no source mutations."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent
# Reuse only audited data-loading declarations, before its fit/output execution.
source=(S/'fit_munich_roof.py').read_text();ns={'__file__':str(S/'fit_munich_roof.py')};exec(compile(source.split('fold_index=')[0],str(S/'fit_munich_roof.py'),'exec'),ns)
for k in ['ROOT','u','v','z','sel','knots','basis','D','uc']:globals()[k]=ns[k]
B=basis(v[sel]);uu=u[sel]-uc;zz=z[sel];vv=v[sel];n=len(knots)
models={'profile':B,'varying_profile':np.column_stack([B,B*uu[:,None]])}
folds={'along_row_2m':np.floor((u[sel]-u[sel].min())/2).astype(int)%3,'across_row_3m':np.floor((vv-vv.min())/3).astype(int)%3}
def fit(X,mask):
 reg=np.zeros((len(D)*(X.shape[1]//n),X.shape[1]));reg[:len(D),:n]=.15*D
 if X.shape[1]>n:reg[len(D):,n:]=.6*D
 start=np.r_[np.full(n,20.),np.zeros(X.shape[1]-n)]
 return least_squares(lambda c:np.r_[X[mask]@c-zz[mask],reg@c],start,loss='soft_l1',f_scale=.1).x
rows={};preds={}
for name,X in models.items():
 results={}
 for direction,index in folds.items():
  errors=[];parts=[]
  for fold in range(3):
   test=index==fold;c=fit(X,~test);e=zz[test]-X[test]@c;errors.extend(e);parts.append({'fold':fold,'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e**2)))})
  results[direction]={'rmse_m':float(np.sqrt(np.mean(np.array(errors)**2))),'p95_abs_m':float(np.percentile(abs(np.array(errors)),95)),'folds':parts}
 c=fit(X,np.ones(len(zz),bool));preds[name]=X@c;rows[name]={'validation':results,'coefficients':c.tolist()}
fig,axs=plt.subplots(1,3,figsize=(14,5),layout='constrained')
for ax,name in zip(axs[:2],models):
 im=ax.scatter(uu,vv,c=zz-preds[name],cmap='RdBu_r',vmin=-.6,vmax=.6);ax.set(title=name,xlabel='Along row from centre (m)',ylabel='Across row (m)',aspect='equal');fig.colorbar(im,ax=ax,label='DSM minus model (m)')
c=np.array(rows['varying_profile']['coefficients'])
for du in [float(uu.min()),0.,float(uu.max())]:axs[2].plot(knots,c[:n]+du*c[n:],label=f'u offset {du:.1f}m')
axs[2].legend();axs[2].set(title='Estimated cross-sections',xlabel='Across row (m)',ylabel='ODN elevation (m)');fig.savefig(ROOT/'references/munich_longitudinal_shape.png',dpi=150)
r={'source_loader_sha256':hashlib.sha256(source.encode()).hexdigest(),'selected_cells':len(zz),'selection':'Same 2m inset and18<ODN<22 as prior fit; no residual-based holdout rejection','model':'Linear variation along row of every 1m cross-profile knot; second-difference regularization on profile and longitudinal variation','knots_v_m':knots.tolist(),'u_center_m':uc,'models':rows,'geometry_modified':False,'limitations':['Different spatial partitions test different interpolation/extrapolation tasks.','Conditional historical raster fit; no causal or architectural interpretation established.'],'visual_reviewed':False}
(ROOT/'references/munich_longitudinal_shape.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:q['validation'] for k,q in rows.items()},indent=2))
