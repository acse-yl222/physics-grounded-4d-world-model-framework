from pathlib import Path
exec(Path(__file__).with_name('new_candidate_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pr=json.loads((R/'references/new_candidate_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);uv=lambda xx,yy:(xx*e[0]+yy*e[1],xx*n[0]+yy*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);q=ps[0];pq=transform(uv,q);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];m=mask(q.buffer(-2));domains={'base':pq.difference(box(198,279,236,285)).difference(box(235.5,-1000,252,1000)),'narrow_upper':pq.intersection(box(210,280.8,235.5,283.5)),'transition_upper':pq.intersection(box(198,280.8,210,283.5)),'wide_upper':pq.intersection(box(235.5,-1000,252,1000))};results=[];predall=np.full(x.shape,np.nan)
for name,domain in domains.items():
 mm=m&mask(transform(xy,domain));
 def pred(c):return c[0]-c[1]*abs(v-c[2])
 def fit(mm):return least_squares(lambda c:pred(c)[mm]-z[mm],[15 if name=='narrow_upper' else 13.3,.15,282],bounds=([10,0,279],[18,1,285]),loss='soft_l1',f_scale=.1).x
 c=fit(mm);checks=[]
 for axis,a in [('u',u),('v',v)]:
  folds=np.floor(a/3).astype(int)%3
  for k in range(3):
   tr=mm&(folds!=k);te=mm&(folds==k)
   if tr.sum()<10 or te.sum()==0:continue
   cc=fit(tr);checks.append({'axis':axis,'fold':k,'params':cc.tolist(),**metric((z-pred(cc))[te])})
 results.append({'name':name,'params_ridge_ODN_slope_ridge_v':c.tolist(),'fit':metric((z-pred(c))[mm]),'holdout':checks,'domain_bounds_uv':list(domain.bounds)});predall[mm]=pred(c)[mm]
fig,axs=plt.subplots(3,1,figsize=(15,9),layout='constrained')
for ax,a,title in zip(axs,[z,predall,z-predall],['DSM ODN','Three geometric fit domains (gaps not fitted)','Residual within fit domains']):
 mm=m if title=='DSM ODN' else m&np.isfinite(predall);im=ax.scatter(u[mm],v[mm],c=a[mm],s=13,marker='s',vmin=-1 if 'Residual' in title else 12,vmax=1 if 'Residual' in title else 15,cmap='coolwarm' if 'Residual' in title else 'viridis');fig.colorbar(im,ax=ax);ax.set(aspect='equal',title=title)
fig.savefig(R/'references/new_candidate_fit.png',dpi=150);(R/'references/new_candidate_fit.json').write_text(json.dumps({'fits':results,'selection':'Geometric domains from actual DSM spatial breaks, all2minset cells; no elevation selection. Three models independently fitted, not yet complete geometry.','capture_date':None},indent=2));print(json.dumps(results,indent=2))
