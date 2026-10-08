"""Cross-validate a west hip plane intersecting a repeated transverse profile."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;source=(S/'fit_munich_roof.py').read_text();ns={'__file__':str(S/'fit_munich_roof.py')};exec(compile(source.split('fold_index=')[0],str(S/'fit_munich_roof.py'),'exec'),ns)
for k in ['ROOT','u','v','z','sel','knots','basis','D','uc']:globals()[k]=ns[k]
B=basis(v[sel]);uu=u[sel]-uc;vv=v[sel];zz=z[sel];n=len(knots)
def pred(c):return np.minimum(B@c[:n],c[n]+c[n+1]*uu) if len(c)>n else B@c
def fit(mask,hip):
 c=least_squares(lambda c:np.r_[B[mask]@c-zz[mask],.15*D@c],np.full(n,20.),loss='soft_l1',f_scale=.1).x
 if not hip:return c
 fits=[]
 for intercept in [21.,22.,23.]:
  r=least_squares(lambda q:np.r_[(pred(q)-zz)[mask],.15*D@q[:n]],np.r_[c,intercept,.7],bounds=(np.r_[np.full(n,15.),18.,.05],np.r_[np.full(n,27.),28.,2.]),loss='soft_l1',f_scale=.1,max_nfev=1000);fits.append(r)
 return min(fits,key=lambda r:r.cost).x
results={}
for name,index in {'along_row_2m':np.floor((uu-uu.min())/2).astype(int)%3,'across_row_3m':np.floor((vv-vv.min())/3).astype(int)%3}.items():
 results[name]={}
 for hip in [False,True]:
  errors=[];parameters=[]
  for fold in range(3):
   test=index==fold;c=fit(~test,hip);errors.extend((zz-pred(c))[test]);parameters.append(c[-2:].tolist() if hip else [])
  e=np.array(errors);results[name]['hip' if hip else 'profile']={'rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95)),'cap_parameters':parameters}
c=fit(np.ones(len(zz),bool),True);e=zz-pred(c);fig,axs=plt.subplots(1,2,figsize=(11,5),layout='constrained');im=axs[0].scatter(uu+uc,vv,c=e,cmap='RdBu_r',vmin=-.6,vmax=.6);fig.colorbar(im,ax=axs[0],label='DSM minus hip model (m)');axs[0].set(xlabel='Along row u (m)',ylabel='Across row v (m)',aspect='equal');
for du in [min(uu),0,max(uu)]:axs[1].plot(knots,np.minimum(c[:n],c[n]+c[n+1]*du),label=f'u={du+uc:.1f}')
axs[1].legend();axs[1].set(xlabel='Across row v (m)',ylabel='ODN height (m)');fig.savefig(ROOT/'references/munich_hip_end.png',dpi=150)
r={'validation':results,'coefficients':c.tolist(),'knots_v_m':knots.tolist(),'u_center_m':uc,'model':'min(transverse profile, cap intercept + positive slope*(u-u_center))','selection':'Same conditional 2m inset,18<DSM<22; each fold fitted only to training cells','limitations':['Exploratory diagnostic; no optical roof-end verification.','Owner boundaries do not establish architectural roof boundaries.'],'geometry_modified':False};(ROOT/'references/munich_hip_end.json').write_text(json.dumps(r,indent=2));print(json.dumps(results,indent=2))
