from pathlib import Path
exec(Path('project/tower_hamlets/mcgraw_review_roof.py').read_text().split('rows=[]')[0])
a=np.deg2rad(-10);u=x*np.cos(a)+y*np.sin(a);v=-x*np.sin(a)+y*np.cos(a);m=mask(p.buffer(-2));U=u[m];V=v[m];Z=z[m]
print('UV bounds',U.min(),U.max(),V.min(),V.max())
fig,ax=plt.subplots(figsize=(11,8));im=ax.scatter(U,V,c=Z,s=13,marker='s',vmin=71,vmax=81);fig.colorbar(im,ax=ax,label='DSM ODN m');ax.set_aspect('equal');ax.set_title('McGraw Hill all 2m inset cells; aligned roof evidence');fig.savefig(R/'references/mcgraw_aligned.png',dpi=160)
for axis,A in [('u',U),('v',V)]:
 print(axis)
 for lo in np.arange(np.floor(A.min()/2)*2,A.max(),2):
  k=(A>=lo)&(A<lo+2);print(round(lo,1),len(Z[k]),np.round(np.percentile(Z[k],[10,50,90]),2).tolist())
from shapely.geometry import box
from shapely.ops import transform as st
PU=st(lambda x,y:(np.asarray(x)*np.cos(a)+np.asarray(y)*np.sin(a),-np.asarray(x)*np.sin(a)+np.asarray(y)*np.cos(a)),p)
upper=box(149,-152,215,-104).difference(box(140,-111,155,-99)).union(box(170,-160,192,-138)).intersection(PU)
south=upper.intersection(box(170,-160,192,-138));core=upper.difference(south);outer=PU.difference(upper)
regs=[('outer_ledge',outer),('upper_main',core),('south_upper',south)];report={'owner':fs[0]['id'],'datum':'ODN minus 4.28000021; raster capture vintage unresolved','angle_deg':-10,'selection':'Boundaries estimated from whole DSM spatial structure. No residual/height exclusions. Holdout conditional on exploratory boundary selection.','regions':[]}
fig,axs=plt.subplots(1,2,figsize=(14,7),layout='constrained');pred=np.zeros_like(Z)
for i,(name,q) in enumerate(regs):
 k=np.array([q.contains(Point(uu,vv)) for uu,vv in zip(U,V)]);A=np.stack([np.ones(len(U)),U-180,V+130],axis=-1)
 def ft(k):return least_squares(lambda c:A[k]@c-Z[k],[np.median(Z[k]),0,0],loss='soft_l1',f_scale=.25).x
 c=ft(k);pred[k]=A[k]@c;checks={}
 for axis,arr in [('u',U),('v',V)]:
  folds=np.floor(arr/3).astype(int)%3;errors=[]
  for f in range(3):
   te=k&(folds==f);tr=k&~te;cf=ft(tr);errors.extend(Z[te]-A[te]@cf)
  checks[axis]=metric(np.array(errors))
 row={'name':name,'cells':int(k.sum()),'plane_odn_c0_cu_cv':c.tolist(),'formula':'c0+cu*(u-180)+cv*(v+130)','holdout':checks,'in_sample':metric(Z[k]-A[k]@c),'geometry_uv':q.__geo_interface__};report['regions'].append(row)
 for poly0 in list(q.geoms) if hasattr(q,'geoms') else [q]:
  for ax in axs:ax.plot(*poly0.exterior.xy,c='black',lw=1)
for ax,C,lim,cm,title in [(axs[0],Z,(71,81),'viridis','All inset DSM and estimated continuous domains'),(axs[1],Z-pred,(-4,4),'coolwarm','All residuals, ODN metres; central returns unresolved')]:
 im=ax.scatter(U,V,c=C,s=9,marker='s',vmin=lim[0],vmax=lim[1],cmap=cm);fig.colorbar(im,ax=ax);ax.set_aspect('equal');ax.set_title(title)
report['boundary_sensitivity']={}
for offset in [-1,0,1]:
 q=upper.buffer(offset);k=np.array([q.contains(Point(uu,vv)) for uu,vv in zip(U,V)]);report['boundary_sensitivity'][str(offset)]={'inner':stats(Z[k]),'outer':stats(Z[~k])}
report['limitations']=['Central rectangular low-return structure unresolved; coarse upper envelope bridges this area rather than interpreting it as plant or openings.','Boundary variation is geometric sensitivity, not independent holdout of model selection.','Lower ledge and upper main are descriptive levels; no optical roof attribution or facade reconstruction.','Source-reported OSM70.95m is distinct from measured datum-referenced DSM.']
(R/'references/mcgraw_structure.json').write_text(json.dumps(report,indent=2));fig.savefig(R/'references/mcgraw_structure.png',dpi=150)
print(json.dumps([{k:v for k,v in r.items() if k!='geometry_uv'} for r in report['regions']],indent=2))
