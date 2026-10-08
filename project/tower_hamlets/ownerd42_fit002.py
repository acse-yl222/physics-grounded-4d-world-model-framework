from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/ownerd42_diagnostic.json').read_text());c=a['center'];e=a['east_axis'];n=a['north_axis'];u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];full=mask(ps[0]);models={
'plane':(lambda p:p[0]+p[1]*u+p[2]*v,[29,0,0],([-100,-2,-2],[100,2,2])),
'hip':(lambda p:p[0]-np.maximum(p[3]*abs(u-p[1]),p[4]*abs(v-p[2])),[32,3,-1,.4,.4],([27,-5,-8,.05,.05],[36,10,6,1,1])),
'hip_flat_ridge':(lambda p:p[0]-np.maximum.reduce([p[3]*np.maximum(abs(u-p[1])-p[5],0),p[4]*np.maximum(abs(v-p[2])-p[6],0),np.zeros(u.shape)]),[32,3,-1,.4,.4,1,1],([27,-5,-8,.05,.05,0,0],[36,10,6,1,1,5,5])),
'gable_u':(lambda p:p[0]-p[2]*abs(u-p[1])+p[3]*v,[32,3,.4,0],([27,-5,.05,-.2],[36,10,1,.2])),
'gable_v':(lambda p:p[0]-p[2]*abs(v-p[1])+p[3]*u,[32,-1,.4,0],([27,-8,.05,-.2],[36,6,1,.2]))}
regions={'central':full&(u>-8)&(u<14)&(v>-11)&(v<10),'southwest':full&(u>-22)&(u<-18)&(v>-14)&(v<-8),'east_notch':full&(u>11)&(u<13.5)&(v>-5)&(v<3),'main_north':full&(v>13)&mask(ps[0].buffer(-2)),'main_south':full&(v<-15)&(u>-12)&mask(ps[0].buffer(-2))}
results={};fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for name,m in regions.items():
 results[name]={'cells':int(m.sum()),'dsm_stats':stats(z[m]),'models':{}}
 for label,(fn,start,bounds) in models.items():
  if name!='central' and label!='plane':continue
  fit=least_squares(lambda p:(fn(p)-z)[m],start,bounds=bounds,loss='soft_l1',f_scale=.25).x;record={'parameters':fit.tolist(),'all_domain':metric((fn(fit)-z)[m]),'holdout':{}}
  for axis,arr in [('u',u),('v',v)]:
   folds=np.floor((arr-arr[m].min())/(3 if name=='central' else 1)).astype(int)%3;errs=[];ff=[]
   for k in range(3):
    tr=m&(folds!=k);te=m&(folds==k)
    if te.sum()==0 or tr.sum()<10:continue
    p=least_squares(lambda p:(fn(p)-z)[tr],start,bounds=bounds,loss='soft_l1',f_scale=.25).x;err=(fn(p)-z)[te];errs.extend(err);ff.append({'fold':k,'parameters':p.tolist(),**metric(err)})
   record['holdout'][axis]={'pooled':metric(np.array(errs)) if errs else {'rmse_m':None,'unavailable':True},'folds':ff}
  results[name]['models'][label]=record
  if name=='central' and label in ['plane','hip','hip_flat_ridge']:
   aa=ax[['plane','hip','hip_flat_ridge'].index(label)];im=aa.scatter(u[m],v[m],c=(z-fn(fit))[m],cmap='coolwarm',vmin=-3,vmax=3,s=25,marker='s');fig.colorbar(im,ax=aa);aa.set(aspect='equal',title=f'{label}: DSM - prediction (m)')
fig.savefig(R/'references/ownerd42_fit002.png',dpi=150);report={'regions':results,'selection':'All valid cells in declared geographic rectangles; robust estimation weights but no elevation rejection. Domain boundaries selected from diagnostic and thus not independent architectural evidence.','limitation':'Model family comparison only, not authorization to create roof topology. Core rectangles do not cover full footprint.'};(R/'references/ownerd42_fit002.json').write_text(json.dumps(report,indent=2));print(json.dumps({n:{l:{'params':r['parameters'],'rmse':r['all_domain']['rmse_m'],'holdout':{k:rr['pooled']['rmse_m'] for k,rr in r['holdout'].items()}} for l,r in d['models'].items()} for n,d in results.items()},indent=2))
