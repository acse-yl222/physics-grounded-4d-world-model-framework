from pathlib import Path
exec(Path('project/tower_hamlets/bank40_review.py').read_text().split('rows=[]')[0])
from scipy.ndimage import label
ang=np.deg2rad(-10);u=x*np.cos(ang)+y*np.sin(ang);v=-x*np.sin(ang)+y*np.cos(ang);m=mask(p);out={'datum':'DSM/DTM ODN; scene=ODN-4.28000021; actualcapturevintageunknown','central_sensitivity':[],'low_components':[]}
fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for ax,zz,title in [(axs[0],z,'DSM ODN,fullrange'),(axs[1],t,'DTM ODN,fullrange'),(axs[2],z-t,'DSM−DTM,fullrange')]:
 im=ax.scatter(u[m],v[m],c=zz[m],s=15,marker='s');fig.colorbar(im,ax=ax);ax.set_aspect('equal');ax.set_title(title)
fig.savefig(R/'references/bank40_fullrange.png',dpi=150)
for threshold in [25,100,148]:
 labs,n=label(m&(z<threshold),np.ones((3,3)))
 for i in range(1,n+1):
  k=labs==i
  if k.sum()<10:continue
  out['low_components'].append({'threshold_ODN':threshold,'cells':int(k.sum()),'DSM':stats(z[k]),'DTM':stats(t[k]),'AGL':stats((z-t)[k]),'equal_DTM_1cm':int((abs(z[k]-t[k])<.01).sum()),'uv_bounds':[float(u[k].min()),float(v[k].min()),float(u[k].max()),float(v[k].max())]})
fig,axs=plt.subplots(1,3,figsize=(17,5),layout='constrained');k=m&(u>=-10)&(u<=20)&(v>=-317)&(v<=-299);im=axs[0].scatter(u[k],v[k],c=z[k],s=50,marker='s',vmin=156,vmax=164);fig.colorbar(im,ax=axs[0]);axs[0].set_aspect('equal');axs[0].set_title('Centralneighborhood all nativecells')
for vv in [-313,-310,-308,-306,-303]:
 k=m&(abs(v-vv)<=.5)&(u>=-10)&(u<=20);ix=np.argsort(u[k]);axs[1].plot(u[k][ix],z[k][ix],'.-',label=f'v{vv}')
for uu in [-4,0,5,10,15]:
 k=m&(abs(u-uu)<=.5)&(v>=-317)&(v<=-299);ix=np.argsort(v[k]);axs[2].plot(v[k][ix],z[k][ix],'.-',label=f'u{uu}')
for ax in axs[1:]:ax.legend(fontsize=8);ax.set_ylabel('ODN m')
fig.savefig(R/'references/bank40_central_profiles.png',dpi=150)
for shift in [-1,-.5,0,.5,1]:
 k=m&(u>=-3-shift)&(u<=11+shift)&(v>=-311-shift)&(v<=-306+shift);level=np.median(z[k]);holds={}
 for axis,A in [('u',u),('v',v)]:
  folds=np.floor(A/2).astype(int)%3;errs=[]
  for f in range(3):
   te=k&(folds==f);tr=k&~te;errs.extend(z[te]-np.median(z[tr]))
  holds[axis]=metric(np.array(errs))
 out['central_sensitivity'].append({'expansion_m':shift,'DSM':stats(z[k]),'flat_holdout_all_cells':holds})
(R/'references/bank40_detail_audit.json').write_text(json.dumps(out,indent=2))
domain=m&(u>=-10)&(u<=20)&(v>=-317)&(v<=-299);out['raised_plateau_sensitivity']=[]
for ramp in [.75,1.25,1.75]:
 for shift in [-.5,0,.5]:
  # Plateau geometricextent varied together; no points dropped for elevation.
  L,H,B,T=-1-shift,11.5+shift,-310.25-shift,-307.5+shift;dist=np.maximum.reduce([np.zeros(u.shape),L-u,u-H,B-v,v-T]);w=np.clip(1-dist/ramp,0,1);A=np.stack([1-w,w],axis=-1);pred=159.3590087890625*(1-w)+163.38*w;hold={}
  for axis,arr in [('u',u),('v',v)]:
   folds=np.floor(arr/3).astype(int)%3;errs=[]
   for f in range(3):
    te=domain&(folds==f);tr=domain&~te;c=least_squares(lambda c:A[tr]@c-z[tr],[159.36,163.38],loss='soft_l1',f_scale=.25).x;errs.extend(z[te]-A[te]@c)
   hold[axis]=metric(np.array(errs))
  out['raised_plateau_sensitivity'].append({'ramp_width':ramp,'plateau_expansion':shift,'all_neighborhood':metric(z[domain]-pred[domain]),'conditional_holdout':hold})
out['interpretation']='Profiles support elongatedraisedplateau about163.3ODN above159.36ODN mainroof, withfiniteedge transitions. Footprint/ramps estimatedat1mresolution; othernorth/southhighlines unmodeled. Lowcomponents characterizedseparately, notforcedtoground.';(R/'references/bank40_detail_audit.json').write_text(json.dumps(out,indent=2))
