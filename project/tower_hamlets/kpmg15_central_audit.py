from pathlib import Path
exec(Path('project/tower_hamlets/kpmg15_review.py').read_text().split('rows=[]')[0])
a=np.deg2rad(-10);u=x*np.cos(a)+y*np.sin(a);v=-x*np.sin(a)+y*np.cos(a);m=mask(p);out={'selection_issue':'001converted geometricrectangle148.5..152.5u,31..40v toarchitecturalwalls despite unstablecross-uvalidation. Lowreturns real,but exactrectangularboundary/deptharchitecture notestablished.','sensitivity':[]}
for delta in [-.5,0,.5,1]:
 k=m&(u>=148.5-delta)&(u<=152.5+delta)&(v>=31-delta)&(v<=40+delta);level=np.median(z[k]);checks={}
 for axis,A in [('u',u),('v',v)]:
  folds=np.floor(A).astype(int)%3;errs=[]
  for f in range(3):
   te=k&(folds==f);tr=k&~te;errs.extend(z[te]-np.median(z[tr]))
  checks[axis]=metric(np.array(errs))
 out['sensitivity'].append({'expansion_m':delta,'dsm':stats(z[k]),'median_flat_holdout_all_cells':checks})
fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained');k=m&(u>=143)&(u<=158)&(v>=26)&(v<=45);im=axs[0].scatter(u[k],v[k],c=z[k],s=75,marker='s',vmin=73,vmax=81);fig.colorbar(im,ax=axs[0]);axs[0].plot([148.5,152.5,152.5,148.5,148.5],[31,31,40,40,31],'r');axs[0].set_aspect('equal');axs[0].set_title('Fullneighborhood;001estimatedrectangle')
for center in [32,35,38,41]:
 k=m&(abs(v-center)<=.5)&(u>=143)&(u<=158);ix=np.argsort(u[k]);axs[1].plot(u[k][ix],z[k][ix],'.-',label=f'v{center}')
for center in [147,150,153,156]:
 k=m&(abs(u-center)<=.5)&(v>=26)&(v<=45);ix=np.argsort(v[k]);axs[2].plot(v[k][ix],z[k][ix],'.-',label=f'u{center}')
for ax in axs[1:]:ax.legend();ax.set_ylabel('ODN m')
fig.savefig(R/'references/kpmg15_central_audit.png',dpi=150);out['decision']='Preserve001ascomparisononly.002omitsunsupportedrectangulararchitecturaldepression while explicitly retaining unresolvedlowreturns. This sacrificeslocalfit,notclaimbettermeasuredroof.';(R/'references/kpmg15_central_audit.json').write_text(json.dumps(out,indent=2))
out['transition_sensitivity']=[];domain=m&(u>=143)&(u<=158)&(v>=26)&(v<=45);nominal=None
for width in [.6,1.1,1.6]:
 for du in [-.5,0,.5]:
  for dv in [-.5,0,.5]:
   dist=np.maximum.reduce([np.zeros(u.shape),148.8+du-u,u-(151.5+du),31.5+dv-v,v-(39.5+dv)]);weight=np.clip(1-dist/width,0,1);pred=79.53600311279297*(1-weight)+75.16050338745117*weight;k=domain;central=k&(u>=148.5)&(u<=152.5)&(v>=31)&(v<=40);checks={}
   if width==1.1 and du==dv==0:
    A=np.stack([1-weight,weight],axis=-1)
    for axis,arr in [('u',u),('v',v)]:
     folds=np.floor(arr/2).astype(int)%3;errs=[]
     for fold in range(3):
      te=k&(folds==fold);tr=k&~te;c=least_squares(lambda c:A[tr]@c-z[tr],[79.53,75.16],loss='soft_l1',f_scale=.2).x;errs.extend(z[te]-A[te]@c)
     checks[axis]=metric(np.array(errs))
   out['transition_sensitivity'].append({'width_m':width,'shift_u_m':du,'shift_v_m':dv,'neighborhood_all_errors':metric(z[k]-pred[k]),'central_all_errors':metric(z[central]-pred[central]),'conditional_holdout':checks})
out['decision']='001verticalwalls and002smoothsurface arecontrols. Actualfullneighborhoodprofiles establish coherentlowplateau~75.16ODN, notabsence.003compares1.1m estimatedslopedtransition with±.5m edgeuncertainty; exactboundaryunmeasured.';(R/'references/kpmg15_central_audit.json').write_text(json.dumps(out,indent=2))
