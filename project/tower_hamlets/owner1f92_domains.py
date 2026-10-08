from pathlib import Path
exec(Path(__file__).with_name('owner1f92_review.py').read_text().split('rows=[]')[0])
q=ps[0]; center=np.array(q.centroid.coords[0]); ring=np.array(q.exterior.coords);delta=np.diff(ring,axis=0); k=np.argmax(np.linalg.norm(delta,axis=1)); e=delta[k]/np.linalg.norm(delta[k]);e=e if e[0]>0 else -e;n=np.array([-e[1],e[0]]);u=(x-center[0])*e[0]+(y-center[1])*e[1];v=(x-center[0])*n[0]+(y-center[1])*n[1];m=mask(q.buffer(-2));vp=(ring-center)@n
# Piecewise constants with two boundaries, unrestricted all inset observations.
best=None
for b1 in np.arange(vp.min()+5,vp.max()-10,.25):
 for b2 in np.arange(b1+3,vp.max()-4,.25):
  zones=[m&(v<b1),m&(v>=b1)&(v<b2),m&(v>=b2)];hs=[np.median(z[a]) for a in zones]
  if min(a.sum() for a in zones)<25:continue
  loss=sum(np.sum(np.minimum(abs(z[a]-h),1.5)) for a,h in zip(zones,hs))
  if best is None or loss<best[0]:best=(loss,b1,b2,hs)
_,b1,b2,hs=best; full=mask(q);zone=np.digitize(v,[b1,b2]);
# Observed west recess in the middle tier: estimate one bounded lateral breakline.
choices=[]
for cut in np.arange(-9,-3,.25):
 zz=zone.copy();zz[(zone==1)&(u<cut)]=2;pp=np.choose(zz,hs);choices.append((float(np.minimum(abs(z[m]-pp[m]),1.5).sum()),float(cut)))
west_cut=min(choices)[1];zone[(zone==1)&(u<west_cut)]=2;pred=np.choose(zone,hs); records=[]
for k in range(3):
 core=m&(zone==k)&(abs(v-b1)>1)&(abs(v-b2)>1); folds=np.floor((u-u[core].min())/3).astype(int)%3; hold=[]
 for f in range(3):
  train=core&(folds!=f);test=core&(folds==f);h=float(np.median(z[train]));hold.append({'fold':f,'height_odn_m':h,**metric(z[test]-h)})
 records.append({'zone':k,'height_odn_m':float(hs[k]),'core_metrics':metric(z[core]-hs[k]),'spatial_holdout':hold,'full_zone':metric(z[full&(zone==k)]-hs[k])})
report={'id':fs[0]['id'],'center':center.tolist(),'east_axis':e.tolist(),'north_axis':n.tolist(),'boundaries_v_m':[b1,b2],'middle_west_boundary_u_m':west_cut,'heights_odn_m':list(map(float,hs)),'domains':records,'full_valid':metric(z[full]-pred[full]),'baseline_full':metric(z[full]-(fs[0]['height_m']+4.28000021)),'inner2':metric(z[m]-pred[m]),'full_cells':int(full.sum()),'footprint_area_m2':q.area,'selection':'All valid DSM samples; tier boundaries minimize capped absolute residual at 0.25 m search spacing in 2 m inset. No full-domain cells omitted from metrics. Core holdout excludes 1 m transition band, spatially withheld east-axis stripes.','limitations':['Boundaries are raster-estimated, not architectural surveyed edges.','Exterior boundary mixed returns remain included in full metric; coherent narrow north/east ~11.7 m ODN edge strip remains unresolved and is not authored as a fourth tier.','Roof evidence only; no windows, doors or equipment authored.']}
fig,ax=plt.subplots(1,3,figsize=(17,5),layout='constrained');a=ax[0].scatter(u[full],v[full],c=z[full],s=15,marker='s');fig.colorbar(a,ax=ax[0]);pr=(ring-center)@np.stack([e,n],axis=1);ax[0].plot(pr[:,0],pr[:,1],'r-');ax[0].axhline(b1,color='black');ax[0].axhline(b2,color='black');ax[0].plot([west_cut,west_cut],[b1,b2],'k-');ax[0].set(aspect='equal',title='Native DSM; estimated tier boundaries',xlabel='East-axis m',ylabel='North-axis m');ax[1].scatter(v[full],z[full],s=5,label='All cells');ax[1].scatter(v[m],z[m],s=5,label='2 m inset');ax[1].plot(sorted(v[full]),np.choose(np.digitize(sorted(v[full]),[b1,b2]),hs),'r-',label='3-tier candidate');ax[1].legend();ax[1].set(xlabel='North-axis m',ylabel='DSM ODN m',title='Full-domain profile, no elevation filtering');im=ax[2].scatter(u[full],v[full],c=z[full]-pred[full],vmin=-5,vmax=5,cmap='coolwarm',s=15,marker='s');fig.colorbar(im,ax=ax[2]);ax[2].set(aspect='equal',title='DSM minus candidate (m)');fig.savefig(R/'references/owner1f92_domains.png',dpi=150);(R/'references/owner1f92_domains.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
