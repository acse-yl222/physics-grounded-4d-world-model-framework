"""Bounded geometric-inset planes for two Credit Suisse secondary roofs."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
S=Path(__file__).resolve().parent
ns={'__file__':str(S/'review_credit_group.py')};exec(compile((S/'review_credit_group.py').read_text().split('rows=[]')[0],str(S/'review_credit_group.py'),'exec'),ns)
for k in ['R','fs','ps','x','y','z','mask','plt']:globals()[k]=ns[k]
ids=['overture-part-793e35a4-6a14-3b53-a6a1-5ee0e8bc06ae','overture-part-5f2f16d8-dd22-3b84-9708-15d59543dc94'];results=[];fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
for ax,bid in zip(axs,ids):
 i=next(i for i,f in enumerate(fs) if f['id']==bid);p=ps[i];cx,cy=p.centroid.coords[0];A=np.stack([np.ones(x.shape),x-cx,y-cy],axis=-1);row={'id':bid,'center_xy_m':[cx,cy],'insets':{}}
 for inset in [4,6]:
  m=mask(p.buffer(-inset))
  if m.sum()<20:continue
  def fit(train):return least_squares(lambda c:A[train]@c-z[train],[np.median(z[train]),0,0],loss='soft_l1',f_scale=.2).x
  c=fit(m);checks={}
  for name,coord in [('x',x),('y',y)]:
   folds=np.floor((coord-coord[m].min())/4).astype(int)%3;errors=[]
   for j in range(3):
    test=m&(folds==j);train=m&~test
    if train.sum()<3 or test.sum()==0:continue
    errors.extend(z[test]-A[test]@fit(train))
   e=np.asarray(errors);checks[name]={'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95))}
  row['insets'][str(inset)]={'cells':int(m.sum()),'coefficients_odn':c.tolist(),'holdout':checks,'support_polygon_xy':list(p.buffer(-inset).exterior.coords)}
 m=mask(p.buffer(-4));c=np.asarray(row['insets']['4']['coefficients_odn']);im=ax.scatter(x[m],y[m],c=(z-A@c)[m],s=20,cmap='RdBu_r',vmin=-1,vmax=1);ax.plot(*p.exterior.xy,color='gray');fig.colorbar(im,ax=ax,label='DSM minus plane (m)');ax.set(aspect='equal',title=bid.split('-')[2],xlabel='Local east (m)',ylabel='Local north (m)');results.append(row)
fig.savefig(R/'references/credit_secondary_roofs.png',dpi=150)
r={'parts':results,'source_hashes':json.loads((R/'references/credit_group_review.json').read_text())['source_hashes'],'scope':'Exploratory inset planes; all geometric-inset heldout returns included. No optical roof classification, no perimeter extrapolation. 4m/6m inset comparison is posthoc and not an independent model-selection test.','geometry_modified':False};(R/'references/credit_secondary_roofs.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([{ 'id':q['id'],'insets':{k:{'cells':v['cells'],'holdout':v['holdout']} for k,v in q['insets'].items()}} for q in results],indent=2))
