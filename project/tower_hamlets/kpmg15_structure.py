from pathlib import Path
exec(Path('project/tower_hamlets/kpmg15_review.py').read_text().split('rows=[]')[0])
a=np.deg2rad(-10);u=x*np.cos(a)+y*np.sin(a);v=-x*np.sin(a)+y*np.cos(a);m=mask(p.buffer(-2));U=u[m];V=v[m];Z=z[m]
print('UV bounds',U.min(),U.max(),V.min(),V.max())
fig,ax=plt.subplots(figsize=(11,8));im=ax.scatter(U,V,c=Z,s=13,marker='s',vmin=72,vmax=81);fig.colorbar(im,ax=ax,label='DSM ODN m');ax.set_aspect('equal');ax.set_title('KPMG source-name all 2m inset cells; aligned roof evidence');fig.savefig(R/'references/kpmg15_aligned.png',dpi=160)
for axis,A in [('u',U),('v',V)]:
 print(axis)
 for lo in np.arange(np.floor(A.min()/2)*2,A.max(),2):
  k=(A>=lo)&(A<lo+2);print(round(lo,1),len(Z[k]),np.round(np.percentile(Z[k],[10,50,90]),2).tolist())
from shapely.geometry import box
from shapely.ops import transform as st
PU=st(lambda x,y:(np.asarray(x)*np.cos(a)+np.asarray(y)*np.sin(a),-np.asarray(x)*np.sin(a)+np.asarray(y)*np.cos(a)),p)
south=PU.intersection(box(100,-10,200,9));nw=PU.intersection(box(100,55,146.5,100));ne=PU.intersection(box(171,46,200,100));inner=PU.intersection(box(148.5,31,152.5,40));main=PU.difference(south.union(nw).union(ne).union(inner))
regs=[('main',main),('south_lower',south),('northwest_lower',nw),('northeast_mixed',ne),('central_lower',inner)];report={'owner':fs[0]['id'],'datum':'ODN minus4.28000021; raster capture vintage unresolved','regions':[]}
fig,axs=plt.subplots(1,2,figsize=(14,7),layout='constrained');pred=np.zeros_like(Z)
for name,q in regs:
 k=np.array([q.contains(Point(uu,vv)) for uu,vv in zip(U,V)]);A=np.stack([np.ones(len(U)),U-162,V-35],axis=-1)
 def ft(k):return least_squares(lambda c:A[k]@c-Z[k],[np.median(Z[k]),0,0],loss='soft_l1',f_scale=.25).x
 c=ft(k);pred[k]=A[k]@c;checks={}
 for axis,arr in [('u',U),('v',V)]:
  folds=np.floor(arr/3).astype(int)%3;errors=[]
  for f in range(3):
   te=k&(folds==f);tr=k&~te;cf=ft(tr);errors.extend(Z[te]-A[te]@cf)
  checks[axis]=metric(np.array(errors))
 report['regions'].append({'name':name,'cells':int(k.sum()),'plane_odn':c.tolist(),'formula':'c0+cu*(u-162)+cv*(v-35)','holdout':checks,'geometry_uv':q.__geo_interface__})
 for poly0 in list(q.geoms) if hasattr(q,'geoms') else [q]:
  for ax in axs:ax.plot(*poly0.exterior.xy,c='black',lw=1)
for ax,C,lim,cm,title in [(axs[0],Z,(72,81),'viridis','All2m inset DSM; exploratory domains'),(axs[1],Z-pred,(-4,4),'coolwarm','All residuals; lowboundary returns retained')]:
 im=ax.scatter(U,V,c=C,s=8,marker='s',vmin=lim[0],vmax=lim[1],cmap=cm);fig.colorbar(im,ax=ax);ax.set_aspect('equal');ax.set_title(title)
report['limitations']=['Geometric domains selected after spatial inspection; conditional holdout is not independent roofshape validation.','Northeast has higher rectangular islands within lower domain; not modeled individually. Easternedge lowreturns unresolved.','No equipment identities asserted.']
(R/'references/kpmg15_structure.json').write_text(json.dumps(report,indent=2));fig.savefig(R/'references/kpmg15_structure.png',dpi=150)
print(json.dumps([{k:v for k,v in a.items() if k!='geometry_uv'} for a in report['regions']],indent=2))
