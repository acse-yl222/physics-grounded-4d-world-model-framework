from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('fit_east_pyramid_pair.py').read_text().split('c=fit(m);')[0])
lo=np.array(center)-np.array(half);hi=np.array(center)+np.array(half)
def pred(c):
 cu,cv=np.array(center)+c[2:];hh=np.minimum.reduce([(u-lo[0])/(cu-lo[0]),(hi[0]-u)/(hi[0]-cu),(v-lo[1])/(cv-lo[1]),(hi[1]-v)/(hi[1]-cv)]);return c[0]+c[1]*hh

def fitfree(mm):return least_squares(lambda c:(pred(c)-z)[mm],[7.7,2,0,0],bounds=([5,.1,-1.5,-1.5],[10,5,1.5,1.5]),loss='soft_l1',f_scale=.15).x
c=fitfree(m);hold={}
for name,arr in [('u',u),('v',v)]:
 folds=np.floor(arr/2).astype(int)%3;es=[];params=[]
 for k in range(3):
  test=m&(folds==k);train=m&(folds!=k);cc=fitfree(train);es.extend((z-pred(cc))[test]);params.append(cc.tolist())
 hold[name]={'metrics':metric(np.array(es)),'fold_parameters':params}
r={'fixed_center_uv':center,'free_parameters_eave_rise_du_dv':c.tolist(),'free_apex_xy':((np.array(center)+c[2:])[0]*e+(np.array(center)+c[2:])[1]*n).tolist(),'offset_xy_m':(c[2]*e+c[3]*n).tolist(),'in_sample':metric((z-pred(c))[m]),'holdout_all_test_cells':hold,'decision':'Sensitivity diagnostic only; compare heldout errors and parameter stability before geometry change. Fixed symmetry is not measured roof truth.'};(R/'references/east_pyramid_pair_apex_sensitivity.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,arr,title,lims in zip(axs,[z,pred(c),z-pred(c)],['DSM ODN','Free-apex pyramid ODN','Residual all1m-inset cells'],[(7.5,10),(7.5,10),(-.5,.5)]):
 im=ax.scatter(x[m],y[m],c=arr[m],s=50,marker='s',vmin=lims[0],vmax=lims[1],cmap='coolwarm' if 'Residual' in title else 'viridis');fig.colorbar(im,ax=ax)
 for q in [ps[0],ps[1]]:ax.plot(*q.exterior.xy,'k-')
 ax.set(aspect='equal',title=title)
fig.savefig(R/'references/east_pyramid_pair_apex_sensitivity.png',dpi=160)
