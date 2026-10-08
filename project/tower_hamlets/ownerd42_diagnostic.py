from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
from scipy.ndimage import label
q=ps[0];c=np.array(q.centroid.coords[0]);ring=np.array(q.exterior.coords);deltas=np.diff(ring,axis=0);k=np.argmax(np.linalg.norm(deltas,axis=1));e=deltas[k]/np.linalg.norm(deltas[k]);e=e if e[0]>0 else -e;n=np.array([-e[1],e[0]]);u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];full=mask(q);inset=mask(q.buffer(-2));rect=(ring-c)@np.stack([e,n],axis=1);fig,ax=plt.subplots(2,3,figsize=(16,10),layout='constrained');rows=[]
for i,(values,title) in enumerate([(z,'DSM ODN (m)'),(z-t,'DSM minus DTM (m)'),(t,'DTM ODN (m)')]):
 im=ax[0,i].scatter(u[full],v[full],c=values[full],s=12,marker='s');fig.colorbar(im,ax=ax[0,i]);ax[0,i].plot(rect[:,0],rect[:,1],'r-');ax[0,i].set(aspect='equal',title=title,xlabel='Building east-axis m',ylabel='Building north-axis m')
for i,coord,along in [(0,u,v),(1,v,u)]:
 for low,high in [(-12,-8),(-4,0),(4,8)]:
  m=inset&(along>=low)&(along<high);ax[1,i].scatter(coord[m],z[m],s=10,label=f'cross {low}..{high}m')
 ax[1,i].legend();ax[1,i].set(xlabel='East-axis m' if i==0 else 'North-axis m',ylabel='DSM ODN m',title='Unfiltered spatial strip profiles')
for threshold in [25.5,26.5,28,30]:
 m=inset&(z>threshold);components,count=label(m);comps=[]
 for k in range(1,count+1):
  cc=components==k
  if cc.sum()<4:continue
  comps.append({'cells':int(cc.sum()),'u_range':[float(u[cc].min()),float(u[cc].max())],'v_range':[float(v[cc].min()),float(v[cc].max())],'dsm':stats(z[cc])})
 rows.append({'threshold_odn_m':threshold,'components_ge4_cells':sorted(comps,key=lambda a:a['cells'],reverse=True)})
 ax[1,2].scatter(u[m],v[m],s=10,label=f'>{threshold}m')
ax[1,2].plot(rect[:,0],rect[:,1],'k-');ax[1,2].set(aspect='equal',title='Threshold stability diagnostic only');ax[1,2].legend();fig.savefig(R/'references/ownerd42_diagnostic.png',dpi=150)
report={'owner':fs[0]['id'],'source_properties':fs[0]['source_properties'],'original_baseline_height_m':fs[0]['height_m'],'center':c.tolist(),'east_axis':e.tolist(),'north_axis':n.tolist(),'full_valid_cells':int(full.sum()),'inset2_cells':int(inset.sum()),'connected_domains':rows,'limitations':['Thresholds only characterize coherent elevated domains; no height-filtered fit or arbitrary equipment geometry authored.','Full-domain baseline must be compared to exact current native asset; original5floors×3m is source-floor assumption.','Geographic identity and roof function unresolved; actual flight date unknown.']};(R/'references/ownerd42_diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
