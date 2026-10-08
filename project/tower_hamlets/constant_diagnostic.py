from pathlib import Path
exec(Path(__file__).with_name('constant_review.py').read_text().split('rows=[]')[0])
q=ps[0];m=mask(q);fig,axs=plt.subplots(1,3,figsize=(13,6),layout='constrained')
for ax,arr,title in zip(axs,[z,t,z-t],['DSM ODN all footprint cells','Co-located DTM ODN','DSM minus DTM']):
 im=ax.scatter(x[m],y[m],c=arr[m],s=15,marker='s');fig.colorbar(im,ax=ax);ax.plot(*q.exterior.xy,'r-',lw=.6);ax.set(aspect='equal',title=title)
fig.savefig(R/'references/constant_diagnostic.png',dpi=150)
rows=[]
for inset in [0,1,2,3,4]:
 mm=mask(q.buffer(-inset));a=z[mm];b=t[mm];flat=float(least_squares(lambda c:a-c[0],[20],loss='soft_l1',f_scale=.1).x[0]);rows.append({'inset':inset,'DSM':stats(a),'DTM':stats(b),'within01m_DTM':int((abs(a-b)<.1).sum()),'robust_flat_ODN':flat,'flat_residual':metric(a-flat)})
(R/'references/constant_diagnostic.json').write_text(json.dumps({'insets':rows,'source_properties':fs[0]['source_properties'],'native':json.loads((R/'references/constant_native.json').read_text()),'decision':'No independent roof candidate: observed main surface nearlyflat; no stable secondary terrace or pitch established. Heightonly revision not authored. Lowedge geometry uncertain.','capture_epoch':None},indent=2));print(json.dumps(rows,indent=2))
