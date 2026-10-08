"""Spatially bounded central surface hypothesis; diagnostic only."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;ns={'__file__':str(S/'analyze_carpark_lidar.py')};exec(compile((S/'analyze_carpark_lidar.py').read_text().split('rep=')[0],str(S/'analyze_carpark_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','masks']:globals()[k]=ns[k]
region=masks['3']&(x>-339)&(x<-262)&(y<320.5-.32*(x+340));sel=region&(z>24)&(z<28);cx=float(x[sel].mean());cy=float(y[sel].mean());B=np.column_stack([np.ones(sel.sum()),x[sel]-cx,y[sel]-cy]);zz=z[sel];fold=np.floor((x[sel]-x[sel].min())/10).astype(int)%3
def fit(m):return least_squares(lambda c:B[m]@c-zz[m],[26,0,.05],loss='soft_l1',f_scale=.05).x
errors=[]
for k in range(3):
 test=fold==k;errors.extend(zz[test]-B[test]@fit(~test))
c=fit(np.ones(len(zz),bool));pred=c[0]+c[1]*(x-cx)+c[2]*(y-cy);e=np.array(errors);fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained');m=masks['0'];axs[0].scatter(x[m],y[m],c='.85',s=4);axs[0].scatter(x[region],y[region],c=z[region],vmin=24,vmax=28,s=8);axs[0].set(title='Spatial central-platform hypothesis',aspect='equal');im=axs[1].scatter(x[sel],y[sel],c=(z-pred)[sel],cmap='RdBu_r',vmin=-.3,vmax=.3,s=8);fig.colorbar(im,ax=axs[1],label='DSM minus plane (m)');axs[1].set(title='Conditional residuals',aspect='equal');fig.savefig(ROOT/'references/carpark_main_plane.png',dpi=150)
r={'spatial_selection':'3m footprint inset; -339<x<-262; y<320.5-0.32*(x+340). Estimated spatial window from inspected DSM, not measured structural edge.','height_selection':'24<DSM<28ODN','all_window_cells':int(region.sum()),'selected_cells':int(sel.sum()),'center_xy_m':[cx,cy],'coefficients_odn_m':c.tolist(),'slope_percent':float(np.linalg.norm(c[1:])*100),'holdout':'Threefold10m east strips; no residual rejection','rmse_m':float(np.sqrt(np.mean(e**2))),'p95_abs_m':float(np.percentile(abs(e),95)),'geometry_modified':False,'limitations':['Spatial window was selected from same observations; conditional validation only.','Excluded levels/edges remain native data.','Slope does not identify a vehicle ramp or prove continuous traversability.'],'visual_reviewed':False};(ROOT/'references/carpark_main_plane.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
