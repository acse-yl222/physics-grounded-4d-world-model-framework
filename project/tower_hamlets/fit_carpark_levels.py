"""Conditional plane diagnostics for distinct observed upper-level height bands."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;source=(S/'analyze_carpark_lidar.py').read_text();ns={'__file__':str(S/'analyze_carpark_lidar.py')};exec(compile(source.split('rep=')[0],str(S/'analyze_carpark_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','masks']:globals()[k]=ns[k]
rows=[];fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for ax,(name,lo,hi) in zip(axs,[('lower_observed_band',24.6,25.1),('middle_observed_band',25.2,26.8),('upper_observed_band',28.1,28.6)]):
 sel=masks['3']&(z>lo)&(z<hi);cx=float(x[sel].mean());cy=float(y[sel].mean());B=np.column_stack([np.ones(sel.sum()),x[sel]-cx,y[sel]-cy]);zz=z[sel];fold=np.floor((x[sel]-x[sel].min())/10).astype(int)%3
 def fit(m):return least_squares(lambda c:B[m]@c-zz[m],[float(np.median(zz)),0,0],loss='soft_l1',f_scale=.05).x
 errors=[];parts=[]
 for k in range(3):
  test=fold==k;c=fit(~test);e=zz[test]-B[test]@c;errors.extend(e);parts.append({'fold':k,'cells':int(test.sum()),'rmse_m':float(np.sqrt(np.mean(e**2)))})
 c=fit(np.ones(len(zz),bool));err=zz-B@c;e=np.array(errors);im=ax.scatter(x[sel],y[sel],c=err,vmin=-.3,vmax=.3,cmap='RdBu_r',s=7);fig.colorbar(im,ax=ax,label='DSM minus plane (m)');ax.set(title=name,xlabel='Local east (m)',ylabel='Local north (m)',aspect='equal');rows.append({'name':name,'selection_odn_m':[lo,hi],'cells':len(zz),'center_xy_m':[cx,cy],'coefficients_odn_m':c.tolist(),'slope_percent':float(np.linalg.norm(c[1:])*100),'spatial_holdout_rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95)),'folds':parts})
fig.savefig(ROOT/'references/carpark_level_planes.png',dpi=150);d={'source_sha256':hashlib.sha256((ROOT/'references/ea_dsm_1m.tif').read_bytes()).hexdigest(),'selection':'3m inward buffer plus reported ODN height bands; no residual-based holdout rejection','validation':'Three folds of10m east strips, each selected cell held out once','planes':rows,'geometry_modified':False,'limitations':['Height-conditioned diagnostic, not full-deck validation; band limits can truncate slopes.','Separate bands need not represent physically separate storeys.','No lower decks, ramps, vehicles or equipment inferred.'],'visual_reviewed':False};(ROOT/'references/carpark_level_planes.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(rows,indent=2))
