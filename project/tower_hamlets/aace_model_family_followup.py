from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('aace_model_sensitivity.py').read_text().split('rows=[];')[0])
rows=[]
for name,domain,kinds in [('south',south,['asymmetric_hip','open_north_hip']),('northwest',nw,['truncated_hip'])]:
 lo=np.array(domain.bounds[:2]);hi=np.array(domain.bounds[2:]);center=(lo+hi)/2;m=mask(transform(xy,domain).buffer(-1))
 for kind in kinds:
  def pred(c):
   cu=center[0]+c[2];cross=np.minimum((u-lo[0])/(cu-lo[0]),(hi[0]-u)/(hi[0]-cu))
   if kind=='asymmetric_hip':h=np.minimum.reduce([cross,(v-lo[1])/c[3],(hi[1]-v)/c[4]])
   elif kind=='open_north_hip':h=np.minimum(cross,(v-lo[1])/c[3])
   else:
    cv=center[1]+c[3];tent=np.minimum.reduce([cross,(v-lo[1])/(cv-lo[1]),(hi[1]-v)/(hi[1]-cv)]);h=np.minimum(1,tent*c[4])
   return c[0]+c[1]*h
  if kind=='asymmetric_hip':initial=[9,5,0,5,5];bounds=([3,.1,-1.5,.5,.5],[16,15,1.5,8,8])
  elif kind=='open_north_hip':initial=[9,5,0,5];bounds=([3,.1,-1.5,.5],[16,15,1.5,8])
  else:initial=[6,5,-1,0,2];bounds=([3,.1,-2,-2,1],[14,12,2,2,4])
  def fit(mm):return least_squares(lambda c:(pred(c)-z)[mm],initial,bounds=bounds,loss='soft_l1',f_scale=.2).x
  c=fit(m);checks={}
  for label,arr in [('u',u),('v',v)]:
   folds=np.floor(arr/3).astype(int)%3;errors=[];parameters=[]
   for k in range(3):
    test=m&(folds==k);train=m&(folds!=k)
    if test.sum() and train.sum()>10:
     cc=fit(train);errors.extend((z-pred(cc))[test]);parameters.append(cc.tolist())
   checks[label]={'metrics':metric(np.array(errors)),'parameters':parameters}
  rows.append({'region':name,'model':kind,'parameters':c.tolist(),'in_sample':metric((z-pred(c))[m]),'holdout':checks})
fig,axs=plt.subplots(1,3,figsize=(14,5),layout='constrained');m=mask(transform(xy,nw).buffer(-1));
for ax,arr,title,lim in zip(axs,[z,pred(c),z-pred(c)],['NW DSM','Truncated hip diagnostic','Allcell residual'],[(5,13),(5,13),(-2,2)]):
 im=ax.scatter(u[m],v[m],c=arr[m],vmin=lim[0],vmax=lim[1],s=20,cmap='coolwarm' if 'residual' in title else 'viridis');fig.colorbar(im,ax=ax);ax.plot(*nw.exterior.xy,'k-');ax.set(aspect='equal',title=title)
fig.savefig(R/'references/aace_model_family_followup.png',dpi=150);(R/'references/aace_model_family_followup.json').write_text(json.dumps({'models':rows,'all_test_residuals_retained':True,'selection_limit':'Exploratory model comparison onsamegeometricdomains, not independent externalvalidation.'},indent=2));print([(r['region'],r['model'],r['parameters'],{k:v['metrics'] for k,v in r['holdout'].items()}) for r in rows])
