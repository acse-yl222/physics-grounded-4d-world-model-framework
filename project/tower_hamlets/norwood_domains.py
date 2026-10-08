from pathlib import Path
exec(Path(__file__).with_name('norwood_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
q=ps[0];zones=[('south_wing',330,349),('south_connector',349,354.8),('middle_wing',354.8,366.5),('north_connector',366.5,374),('north_wing',374,390)];rows=[];fig,ax=plt.subplots(2,3,figsize=(14,9),layout='constrained');mm=mask(q);im=ax[0,0].scatter(x[mm],y[mm],c=z[mm],s=20,marker='s',vmin=3,vmax=21);fig.colorbar(im,ax=ax[0,0]);ax[0,0].set(aspect='equal',title='DSM all validowner cells')
for k,(name,lo,hi) in enumerate(zones):
 domain=q.intersection(box(349.5 if name=='south_connector' else (342.5 if name=='north_connector' else 330),lo,370,hi));train=domain.buffer(-1.3);m=mask(train);center=np.array(domain.centroid.coords[0]);A=np.stack([np.ones(x.shape),x-center[0],y-center[1]],axis=-1);c=fitplane(m,A);checks=[]
 for axis,arr in [('x',x),('y',y)]:
  for fold in range(3):
   tr=m&(np.floor(arr/2).astype(int)%3!=fold);te=m&~tr
   if tr.sum()<10 or not te.sum():continue
   cc=fitplane(tr,A);checks.append({'axis':axis,'fold':fold,'coefficients':cc.tolist(),**metric(z[te]-A[te]@cc)})
 a=ax.flat[k+1];a.scatter(x[m],z[m],s=10,c=y[m]);a.scatter(x[m],(A@c)[m],s=3,color='red');a.set(title=name,xlabel='ENUeast m',ylabel='ODN m');rows.append({'name':name,'y_bounds':[lo,hi],'center':center.tolist(),'coefficients':c.tolist(),'all_training_residual':metric(z[m]-A[m]@c),'holdout':checks,'dtm':stats(t[m])})
fig.savefig(R/'references/norwood_domains.png',dpi=150);(R/'references/norwood_domains.json').write_text(json.dumps(rows,indent=2));print([(r['name'],r['coefficients'],r['all_training_residual']) for r in rows])
