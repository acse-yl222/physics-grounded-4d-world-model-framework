from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;ns={'__file__':str(P/'review_wintergarden_roof.py')};exec((P/'review_wintergarden_roof.py').read_text().split('rows=[]')[0],ns);R=ns['R'];x,y,z=ns['x'],ns['y'],ns['z'];p=ns['ps'][1];xy=np.array(p.exterior.coords);edges=np.diff(xy,axis=0);v=edges[np.argmax(np.linalg.norm(edges,axis=1))];v/=np.linalg.norm(v)
if v[1]<0:v=-v
u=np.array([v[1],-v[0]]);o=np.array(p.centroid.coords[0]);U=(x-o[0])*u[0]+(y-o[1])*u[1];V=(x-o[0])*v[0]+(y-o[1])*v[1]
m=ns['mask'](p);mi=ns['mask'](p.buffer(-2));a=U[mi];b=V[mi];zz=z[mi]
# Elliptical barrel hypothesis with whole mapped central width; fit crown and vertical radius and small lateral offset.
uv=(xy-o)@np.column_stack([u,v]);half=max(abs(uv[:,0].min()),abs(uv[:,0].max()))
# Circle-like elliptic roof: crown - vertical_radius*(1-sqrt(1-(u-offset)^2/halfwidth^2)). No residual sample rejection.
def model(c,a,b):return c[0]-c[1]*(1-np.sqrt(np.maximum(0,1-((a-c[2])/(half+abs(c[2])+c[3]))**2)))+c[4]*b
fit=least_squares(lambda c:model(c,a,b)-zz,[35.55,24,-.8,.1,0],bounds=([30,1,-2,.001,-.2],[40,50,2,8,.2]),loss='soft_l1',f_scale=.25).x
err=z[m]-model(fit,U[m],V[m]);folds=np.floor(V[mi]/3).astype(int)%3;hold=[]
for k in range(3):
 train=folds!=k;test=~train;c=least_squares(lambda c:model(c,a[train],b[train])-zz[train],fit,bounds=([30,1,-2,.001,-.2],[40,50,2,8,.2]),loss='soft_l1',f_scale=.25).x;e=zz[test]-model(c,a[test],b[test]);hold.append(dict(fold=k,train_cells=int(train.sum()),test_cells=int(test.sum()),rmse_m=float(np.sqrt(np.mean(e*e))),median_abs_m=float(np.median(abs(e))),within_1m=int((abs(e)<=1).sum()),coefficients=c.tolist()))
fig,axs=plt.subplots(1,2,figsize=(14,6),layout='constrained');s=axs[0].scatter(U[m],V[m],c=z[m],s=15,vmin=7,vmax=36);fig.colorbar(s,ax=axs[0],label='DSM ODN m');axs[0].set_aspect('equal');axs[0].set_xlabel('cross-arch u m');axs[0].set_ylabel('longitudinal v m');axs[1].scatter(U[m],z[m],c=V[m],s=8);aa=np.linspace(uv[:,0].min(),uv[:,0].max(),200);axs[1].plot(aa,model(fit,aa,aa*0),color='red');axs[1].set_xlabel('cross-arch u m');axs[1].set_ylabel('ODN m');fig.savefig(R/'references/wintergarden_arch_fit.png',dpi=150)
r=dict(origin=o.tolist(),u=u.tolist(),v=v.tolist(),central_bounds_uv=[uv.min(0).tolist(),uv.max(0).tolist()],formula='crown - vertical_radius*(1-sqrt(max(0,1-((u-offset)/(halfwidth+abs(offset)+radius_extra))^2)))+longitudinal_slope*v',coefficients=fit.tolist(),halfwidth_m=half,parameter_order=["crown","vertical_radius","offset","radius_extra","longitudinal_slope"],fit_selection='All central2m-inset native cells; soft_l1 robustloss, no rejection. Report residuals for all central cells including boundary/mixed returns.',all_cells=int(m.sum()),all_rmse_m=float(np.sqrt(np.mean(err*err))),all_median_abs_m=float(np.median(abs(err))),all_p95_abs_m=float(np.percentile(abs(err),95)),all_within1m=int((abs(err)<=1).sum()),excluded_cells=0,holdout=hold,arch_profile_estimated=True,edge_predictions_odn_m=[float(model(fit,np.array([q]),np.array([0]))[0]) for q in [uv[:,0].min(),uv[:,0].max()]],boundary_strip_diagnostics=[dict(side=side,cells=int(mm.sum()),median_residual_m=float(np.median(z[mm]-model(fit,U[mm],V[mm]))),rmse_m=float(np.sqrt(np.mean((z[mm]-model(fit,U[mm],V[mm]))**2)))) for side,mm in [('west',m&(U<uv[:,0].min()+2)),('east',m&(U>uv[:,0].max()-2))]])
(R/'references/wintergarden_arch_fit.json').write_text(json.dumps(r,indent=2)+'\n');np.savez(R/'references/wintergarden_samples.npz',x=x,y=y,z=z,valid=ns['valid']);print(json.dumps(r,indent=2))
