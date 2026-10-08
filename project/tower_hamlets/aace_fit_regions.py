from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('review_aace_roof.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
th=np.deg2rad(16);co,si=np.cos(th),np.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);q=transform(uv,p);u=x*co+y*si;v=-x*si+y*co
south=q.intersection(box(-330,420,-298,455));nw=q.intersection(box(-330,458,-298,480));nc=q.intersection(box(-298,457,-278,480));rest=q.difference(south.union(nw).union(nc));domains=[('south_wing',south),('northwest_wing',nw),('northcentral_wing',nc),('low_remainder',rest)]
rows=[];pred=np.full(x.shape,np.nan);fig,axs=plt.subplots(1,3,figsize=(16,6),layout='constrained')
for name,pp in domains:
 xy=transform(lambda u,v:(u*co-v*si,u*si+v*co),pp);m=mask(xy.buffer(-1));uc,vc=pp.centroid.coords[0];A=np.stack([np.ones(x.shape),abs(u-uc),abs(v-vc)],axis=-1)
 def fit(mm):return least_squares(lambda c:A[mm]@c-z[mm],[np.median(z[mm]),-.3,-.1],bounds=([0,-3,-3],[30,0,0]),loss='soft_l1',f_scale=.2).x
 c=fit(m);checks={}
 for label,arr in [('u',u),('v',v)]:
  folds=np.floor(arr/3).astype(int)%3;errs=[]
  for k in range(3):
   test=m&(folds==k);train=m&(folds!=k)
   if test.sum() and train.sum()>10:errs.extend((z-A@fit(train))[test])
  checks[label]=metric(np.array(errs)) if errs else {}
 pred[mask(xy)]=(A@c)[mask(xy)];rows.append({'name':name,'center_uv':[uc,vc],'coefficients':c.tolist(),'cells':int(m.sum()),'in_sample':metric((z-A@c)[m]),'holdout_all_cells':checks,'support_uv':[{'outer':list(t.exterior.coords),'holes':[]} for t in getattr(pp,'geoms',[pp])]})
 for ax in axs:
  for poly in getattr(pp,'geoms',[pp]):ax.plot(*poly.exterior.xy,'k-',lw=1)
for ax,arr,title,lims in zip(axs,[z,pred,z-pred],['DSM ODN','Exploratory piecewise roof','DSM minus model'],[(5,16),(5,16),(-2,2)]):
 m=mask(p);im=ax.scatter(u[m],v[m],c=arr[m],s=9,marker='s',vmin=lims[0],vmax=lims[1],cmap='coolwarm' if 'minus' in title else 'viridis');fig.colorbar(im,ax=ax);ax.set(aspect='equal',title=title)
fig.savefig(R/'references/aace_regions_fit.png',dpi=150);r={'id':fs[0]['id'],'angle_degrees':16,'formula':'ODN=c0+c1*abs(u-uc)+c2*abs(v-vc); slopes constrained nonpositive','regions':rows,'limitations':['Geometric domains selected after viewing DSM; exploratory.','Independent piecewise peaks may not join continuously; not yet approved authoring shape.','All heldout returns retained; robust trainingonly. Actual raster capture vintage unresolved.'],'datum_offset':4.28000021};(R/'references/aace_regions_fit.json').write_text(json.dumps(r,indent=2));print(json.dumps(rows,indent=2))
