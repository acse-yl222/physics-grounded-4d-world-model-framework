"""Test a longitudinal height step with threshold selected on training cells only."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;source=(S/'fit_munich_roof.py').read_text();ns={'__file__':str(S/'fit_munich_roof.py')};exec(compile(source.split('fold_index=')[0],str(S/'fit_munich_roof.py'),'exec'),ns)
for k in ['ROOT','u','v','z','sel','knots','basis','D','uc']:globals()[k]=ns[k]
B=basis(v[sel]);uu=u[sel];vv=v[sel];zz=z[sel];n=len(knots)
def fit(mask,threshold=None):
 X=B if threshold is None else np.column_stack([B,(uu<threshold).astype(float)])
 reg=np.zeros((len(D),X.shape[1]));reg[:,:n]=.15*D
 start=np.r_[np.full(n,20.),np.zeros(X.shape[1]-n)]
 res=least_squares(lambda c:np.r_[X[mask]@c-zz[mask],reg@c],start,loss='soft_l1',f_scale=.1)
 return res.x,X,res.cost
folds={'along_row_2m':np.floor((uu-uu.min())/2).astype(int)%3,'across_row_3m':np.floor((vv-vv.min())/3).astype(int)%3};results={}
for name,index in folds.items():
 errors={'profile':[],'step':[]};parts=[]
 for fold in range(3):
  train=index!=fold;test=~train;c,X,_=fit(train);errors['profile'].extend(zz[test]-X[test]@c)
  candidates=[]
  for threshold in np.quantile(uu[train],[.2,.3,.4,.5,.6,.7,.8]):
   c,X,cost=fit(train,threshold);candidates.append((cost,threshold,c,X))
  cost,t,c,X=min(candidates,key=lambda q:q[0]);errors['step'].extend(zz[test]-X[test]@c);parts.append({'fold':fold,'train_threshold_u':float(t),'height_offset_m':float(c[-1])})
 results[name]={k:{'rmse_m':float(np.sqrt(np.mean(np.array(e)**2))),'p95_abs_m':float(np.percentile(abs(np.array(e)),95))} for k,e in errors.items()};results[name]['folds']=parts
train=np.ones(len(zz),bool);candidates=[]
for t in np.quantile(uu,[.2,.3,.4,.5,.6,.7,.8]):
 c,X,cost=fit(train,t);candidates.append((cost,t,c,X))
_,t,c,X=min(candidates,key=lambda q:q[0]);fig,axs=plt.subplots(1,2,figsize=(10,5),layout='constrained');im=axs[0].scatter(uu,vv,c=zz-X@c,cmap='RdBu_r',vmin=-.8,vmax=.8);axs[0].axvline(t,color='k',linestyle='--');fig.colorbar(im,ax=axs[0],label='DSM minus fitted step (m)');axs[0].set(xlabel='Along row u (m)',ylabel='Across row v (m)',title='Diagnostic only',aspect='equal');axs[1].plot(knots,c[:n],label='east');axs[1].plot(knots,c[:n]+c[-1],label='west');axs[1].legend();axs[1].set(xlabel='Across row v (m)',ylabel='ODN elevation (m)');fig.savefig(ROOT/'references/munich_step_diagnostic.png',dpi=150)
report={'validation':results,'selected_full_data_threshold_u':float(t),'west_offset_m':float(c[-1]),'coefficients':c.tolist(),'selection':'Existing 2m inset and18<DSM<22; no residual rejection; candidate step threshold selected using training loss separately per fold','limitations':['Exploratory comparison after prior diagnostics, not independent architectural proof.','Threshold is estimated; no optical verification.'],'geometry_modified':False};(ROOT/'references/munich_step_diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps(results,indent=2))
