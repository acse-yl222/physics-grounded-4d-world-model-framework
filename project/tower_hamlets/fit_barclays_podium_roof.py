from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';d=np.load('cache/tower_hamlets/barclays_podium_roof.npz');u,v,z=d['u'],d['v'],d['z'];m=d['mask']
def pred(c,u,v):
 low,base,peak,vc,slope,spurpeak,uc,spur_slope=c
 spurpeak=peak # sharedridgepeak ensures continuousjunction
 b=np.where((v>=12)&(v<=52),base,low);ridge=peak-slope*np.abs(v-vc);spur=np.where(v<vc,spurpeak-spur_slope*np.abs(u-uc),-100);return np.maximum.reduce([b,ridge,spur])
ini=[63,68.5,76,32,.45,76,-204,.8];bounds=([62.8,65,73,27,.25,73,-213,.4],[63.3,71,79,37,.9,80,-197,1.5])
def fit(mm):return least_squares(lambda c:pred(c,u[mm],v[mm])-z[mm],ini,bounds=bounds,loss='soft_l1',f_scale=.35,max_nfev=1200).x
c=fit(m);c[5]=c[2];checks={}
for name,ar in [('u',u),('v',v)]:
 fold=np.floor((ar-ar[m].min())/6).astype(int)%3;e=[]
 for k in range(3):
  test=m&(fold==k);cc=fit(m&~test);e.extend((pred(cc,u[test],v[test])-z[test]).tolist())
 e=np.array(e);checks[name]={'cells':len(e),'rmse':float(np.sqrt(np.mean(e*e))),'median_abs':float(np.median(abs(e))),'p90_abs':float(np.percentile(abs(e),90))}
res=z[m]-pred(c,u[m],v[m]);fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for ax,zz,title,lo,hi in [(axs[0],z[m],'DSM all4m-inset',60,78),(axs[1],pred(c,u[m],v[m]),'Clean descriptive crossedroof',60,78),(axs[2],res,'All residuals;no rejection',-10,10)]:
 im=ax.scatter(u[m],v[m],c=zz,s=4,vmin=lo,vmax=hi);fig.colorbar(im,ax=ax);ax.set(aspect='equal',title=title)
fig.savefig(R/'references/barclays_podium_roof_fit.png',dpi=150);report={'parameters_order':['outer_base_odn','inner_base_odn','longridge_peak_odn','ridge_center_v','ridge_slope','spur_peak_odn_equal_to_main_peak','spur_center_u','spur_slope'],'coefficients':c.tolist(),'rotation_degrees':-10,'base_domain':'inner12<=v<=52;otherwiseouter','surface':'max(base,peak-slope*abs(v-vc),spurpeak-spurslope*abs(u-uc) onlyv<vc)','holdout_all_cells':checks,'selection':'Allvalid4minsetcells,6m spatialstrips; no residualtest exclusion. FitrobustsoftL1; unsupportededges/mixedreturns retainedintest.','limitations':['Roofmodel exploratoryselected afterDSMprofileinspection; foldsnotindependentmodelselectionvalidation.','RaisedNEcorner andsmallequipmentreturns unmodeled; fullroofnotaccuratetoLiDAR.','Mixed2017–2020DSM vs2026mappedfootprint; no contemporaneousfacade identity.','Cleaning inferredroofsurfacesdescriptive, not survey.' ]};(R/'references/barclays_podium_roof_fit.json').write_text(json.dumps(report,indent=2));print(c,checks)
