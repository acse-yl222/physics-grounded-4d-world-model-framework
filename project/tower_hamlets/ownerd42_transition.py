"""Explicit d42 roof transition hypotheses; no elevation filtering."""
from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/ownerd42_diagnostic.json').read_text());c=np.array(a['center']);e=np.array(a['east_axis']);n=np.array(a['north_axis']);u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];q=ps[0];full=mask(q);central=full&(u>-11)&(u<18)&(v>-15)&(v<14)
h=float(np.median(z[mask(q.buffer(-2))&(u>18)&(v>-10)&(v<10)]))
# 5 hip parameters, outer rectangle, edge slope, notch limit, notch v interval,
# ledge elevation, ledge outer x, notch transition slope.
start=[32.1,2.8,-.5,.39,.4,-9,15.5,-12.5,11,4,9.8,-6.5,4.5,27,12.5,3]
low=[31,-1,-3,.2,.2,-11,13,-14,9,1,8,-9,2,25.5,11,1]
high=[34,6,2,.7,.7,-7,18,-10,13,8,12,-4,7,28,15,8]
def model(p,U=u,V=v):
 hip=p[0]-np.maximum(p[3]*abs(U-p[1]),p[4]*abs(V-p[2]))
 outer=np.minimum.reduce([hip,h+p[9]*(U-p[5]),h+p[9]*(p[6]-U),h+p[9]*(V-p[7]),h+p[9]*(p[8]-V)])
 # Notch is union of eastward halfspace and finite v span; slopes estimated.
 cap=p[13]+p[15]*np.maximum.reduce([p[10]-U,p[11]-V,V-p[12],np.zeros(np.shape(U))])
 ledgecap=h+p[15]*np.maximum.reduce([p[14]-U,p[11]-V,V-p[12],np.zeros(np.shape(U))])
 return np.maximum(h,np.minimum.reduce([outer,cap,ledgecap]))
fit=least_squares(lambda p:(model(p)-z)[central],start,bounds=(low,high),loss='soft_l1',f_scale=.2,max_nfev=2000).x
res={'parameters':fit.tolist(),'main_odn_m':h,'domain':'All valid cells −11<u<18,−15<v<14; no elevation filtering','in_sample':metric((model(fit)-z)[central]),'holdout':{}}
for axis,arr in [('u',u),('v',v)]:
 folds=np.floor((arr-arr[central].min())/3).astype(int)%3;errs=[];rows=[]
 for k in range(3):
  tr=central&(folds!=k);te=central&(folds==k);pfit=least_squares(lambda p:(model(p)-z)[tr],fit,bounds=(low,high),loss='soft_l1',f_scale=.2,max_nfev=1200).x;ee=(model(pfit)-z)[te];errs.extend(ee);rows.append({'fold':k,'parameters':pfit.tolist(),**metric(ee)})
 res['holdout'][axis]={'pooled':metric(np.array(errs)),'folds':rows}
fig,ax=plt.subplots(1,3,figsize=(16,6),layout='constrained')
for aa,val,title in zip(ax,[z,model(fit),z-model(fit)],['DSM ODN','Hip + eastern notch hypothesis','DSM minus hypothesis']):
 im=aa.scatter(u[central],v[central],c=val[central],marker='s',s=18,cmap='coolwarm' if aa==ax[2] else 'viridis',**({'vmin':-2,'vmax':2} if aa==ax[2] else {'vmin':24,'vmax':33}));fig.colorbar(im,ax=aa);aa.set(aspect='equal',title=title)
fig.savefig(R/'references/ownerd42_transition.png',dpi=150)
(R/'references/ownerd42_transition.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
