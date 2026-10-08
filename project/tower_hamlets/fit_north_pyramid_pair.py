from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('review_north_pyramid_pair.py').read_text().split('rows=[]')[0])
# Fit shared pyramidal hypothesis for touching central pair, versus independent per-owner peaks.
pair=ps[0].union(ps[1]);edge=np.array(fs[0]['geometry'][0]['outer'][1])-np.array(fs[0]['geometry'][0]['outer'][0]);e=edge/np.linalg.norm(edge);n=np.array([-e[1],e[0]]);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1]
def tent(q):
 rr=np.array(q.exterior.coords);uu=rr@e;vv=rr@n;center=[(uu.min()+uu.max())/2,(vv.min()+vv.max())/2];half=[np.ptp(uu)/2,np.ptp(vv)/2];h=1-np.maximum(abs((u-center[0])/half[0]),abs((v-center[1])/half[1]));return h,center,half
h,center,half=tent(pair);m=mask(pair.buffer(-1));A=np.stack([np.ones(x.shape),h],axis=-1)
def fit(mm):return least_squares(lambda c:A[mm]@c-z[mm],[7,3],loss='soft_l1',f_scale=.15).x
c=fit(m);checks={}
for name,arr in [('u',u),('v',v)]:
 folds=np.floor(arr/2).astype(int)%3;es=[]
 for k in range(3):
  test=m&(folds==k);train=m&(folds!=k)
  if test.sum() and train.sum()>8:es.extend(z[test]-A[test]@fit(train))
 checks[name]=metric(np.array(es))
ind=np.full(x.shape,np.nan)
for q in [ps[0],ps[1]]:
 hh,_,_=tent(q);mm=mask(q.buffer(-1));aa=np.stack([np.ones(x.shape),hh],axis=-1);cc=least_squares(lambda c:aa[mm]@c-z[mm],[7,2],loss='soft_l1',f_scale=.15).x;ind[mask(q)]=(aa@cc)[mask(q)]
pred=A@c;fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,arr,title,lims in zip(axs,[z,pred,z-pred],['DSM ODN','Fitted shared pyramid','Residual: all1m inset'],[(6,10),(6,10),(-1,1)]):
 im=ax.scatter(x[m],y[m],c=arr[m],s=50,marker='s',vmin=lims[0],vmax=lims[1],cmap='viridis' if title!='Residual: all1m inset' else 'coolwarm');fig.colorbar(im,ax=ax)
 for q in [ps[0],ps[1]]:ax.plot(*q.exterior.xy,'k-')
 ax.set(aspect='equal',title=title)
fig.savefig(R/'references/north_pyramid_pair_fit.png',dpi=160)
r={'ids':[fs[i]['id'] for i in [0,1]],'center_uv':center,'half_widths_uv':half,'axis_u':e.tolist(),'axis_v':n.tolist(),'formula':'ODN=eave+rise*(1-max(abs((u-cu)/hu),abs((v-cv)/hv)))','eave_odn_m':float(c[0]),'rise_m':float(c[1]),'apex_odn_m':float(sum(c)),'shared_scene_offset':4.28000021,'cells':int(m.sum()),'fit_all_cells':metric((z-pred)[m]),'holdout2m_strips_all_test_cells':checks,'individual_pyramid_diagnostic_in_sample':metric((z-ind)[m]),'limitations':['Shared central peak is fitted to two touching mapped house owners, not one pyramid per label.','Fixed plan-centred apex hypothesis uses DSM spatial profile plus mapped roof tag; no licensed optical roof verification.','Actual raster capture vintage unknown.1mresolution limits eaves/apex location.','Both adjacentowner footprints inspected jointly.'],'native_flat_baseline_m':6};(R/'references/north_pyramid_pair_fit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
