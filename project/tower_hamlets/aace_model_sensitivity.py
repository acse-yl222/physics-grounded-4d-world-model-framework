from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('review_aace_roof.py').read_text().split('rows=[]')[0])
th=np.deg2rad(16);co,si=np.cos(th),np.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);u=x*co+y*si;v=-x*si+y*co;q=transform(uv,p);rr=np.array([uv(*a) for a in fs[0]['geometry'][0]['outer']]);south=Polygon(rr[[28,29,0,1,27]]).intersection(q);nw=Polygon(rr[[21,22,23,24]]).intersection(q)
rows=[];preds={};domains={}
for name,domain in [('south',south),('northwest',nw)]:
 lo=np.array(domain.bounds[:2]);hi=np.array(domain.bounds[2:]);center=(lo+hi)/2;m=mask(transform(xy,domain).buffer(-1));models={}
 for kind in (['gable','hip'] if name=='south' else ['fixed_pyramid','free_pyramid']):
  def predict(c):
   cu=center[0]+c[2];cv=center[1]+(c[3] if kind=='free_pyramid' else 0);cross=np.minimum((u-lo[0])/(cu-lo[0]),(hi[0]-u)/(hi[0]-cu))
   if kind=='gable':h=cross
   elif kind=='hip':h=np.minimum.reduce([cross,(v-lo[1])/c[3],(hi[1]-v)/c[3]])
   else:h=np.minimum.reduce([cross,(v-lo[1])/(cv-lo[1]),(hi[1]-v)/(hi[1]-cv)])
   return c[0]+c[1]*h
  if kind=='hip':init=[9,6,0,3];bounds=([3,.1,-1.5,.5],[16,15,1.5,8])
  elif kind=='free_pyramid':init=[7,5,0,0];bounds=([3,.1,-2,-2],[16,15,2,2])
  else:init=[8,6,0];bounds=([3,.1,-1.5],[16,15,1.5])
  # fixed model has plan centre fixed; allow only eave/rise via tiny offset bounds
  if kind=='fixed_pyramid':bounds=([3,.1,-1e-8],[16,15,1e-8])
  def fit(mm):return least_squares(lambda c:(predict(c)-z)[mm],init,bounds=bounds,loss='soft_l1',f_scale=.2).x
  c=fit(m);checks={}
  for axis,arr in [('u',u),('v',v)]:
   folds=np.floor(arr/3).astype(int)%3;errors=[];params=[]
   for k in range(3):
    test=m&(folds==k);train=m&(folds!=k)
    if test.sum() and train.sum()>10:
     cf=fit(train);errors.extend((z-predict(cf))[test]);params.append(cf.tolist())
   checks[axis]={'metrics':metric(np.array(errors)),'parameters':params}
  models[kind]={'parameters':c.tolist(),'fit':metric((z-predict(c))[m]),'holdout':checks};preds[(name,kind)]=predict(c).copy()
 domains[name]=domain;rows.append({'name':name,'support_uv':list(domain.exterior.coords),'bounds_uv':[lo.tolist(),hi.tolist()],'center_uv':center.tolist(),'cells':int(m.sum()),'models':models})
fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained')
for axs,r in zip(axs,rows):
 name=r['name'];domain=domains[name];m=mask(transform(xy,domain).buffer(-1));kind='hip' if name=='south' else 'free_pyramid';pred=preds[(name,kind)]
 for ax,arr,title,lims in zip(axs,[z,pred,z-pred],['DSM',kind,'residual'],[(5,16),(5,16),(-2,2)]):
  im=ax.scatter(u[m],v[m],c=arr[m],s=20,vmin=lims[0],vmax=lims[1],cmap='coolwarm' if title=='residual' else 'viridis');fig.colorbar(im,ax=ax);ax.plot(*domain.exterior.xy,'k-');ax.set(aspect='equal',title=name+' '+title)
fig.savefig(R/'references/aace_model_sensitivity.png',dpi=150);(R/'references/aace_model_sensitivity.json').write_text(json.dumps({'regions':rows,'domain_revision':'South sourcevertices28,29,0,1,27; NW21,22,23,24. Removes arbitraryu=-298 thinstrip; shape partitions follow mappedwing outlines.','limitations':['Exploratorydomain/modelselection; tests retain allcells.','Actual raster vintageunknown; ODNminus4.28000021 scene.','Fixedpyramid versus freepeak test uses samegeometrydomain.']},indent=2));print(json.dumps(rows,indent=2))
