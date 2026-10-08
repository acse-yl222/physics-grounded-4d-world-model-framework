"""Full-domain model comparison: all inset cells retained in scored diagnostics."""
import runpy,json,numpy as np
from scipy.optimize import least_squares
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007/references';d=runpy.run_path(str(S/'analyze_00a65_full_lidar001.py'));x,y,z,m,p=d['x'],d['y'],d['z'],d['m'],d['p'];core=d['masks']['2'];xc,yc=p.centroid.x,p.centroid.y
X=x[core];Y=y[core];Z=z[core]
# Robust fit downweights, never removes data. Report full-domain errors below.
a=least_squares(lambda q:q[0]*(X-xc)+q[1]*(Y-yc)+q[2]-Z,[0,0,14],loss='soft_l1',f_scale=.2).x
b=least_squares(lambda q:q[0]+q[1]*np.sqrt((X-q[2])**2+(Y-q[3])**2)-Z,[12,.1,-47,520],bounds=([0,-1,-85,480],[25,1,-35,550]),loss='soft_l1',f_scale=.2).x
preds={'plane':a[0]*(x-xc)+a[1]*(y-yc)+a[2],'radial':b[0]+b[1]*np.sqrt((x-b[2])**2+(y-b[3])**2)}
def stat(v):return {'count':len(v),'rmse':float(np.sqrt(np.mean(v*v))),'median_abs':float(np.median(abs(v))),'p95_abs':float(np.percentile(abs(v),95)),'within_0_3m':int((abs(v)<.3).sum()),'within_1m':int((abs(v)<1).sum())}
report={'owner':d['f']['id'],'fit_domain':'All valid cells in2m geometric inset; soft_l1 f_scale0.2m robust fit. No height filtering. All residuals reported including low returns.','parameters':{'plane_dx_dy_intercept_at_centroid':a.tolist(),'centroid_xy':[xc,yc],'radial_base_slope_centerx_centery':b.tolist()},'scores':{name:{k:stat((v-z)[mask]) for k,mask in [('full',m),('inset2',core)]} for name,v in preds.items()},'low_returns':{'full_below8':int((m&(z<8)).sum()),'inset2_below8':int((core&(z<8)).sum())},'datum_odn_m':4.28000021,'capture_date':None,'candidate_created':False}
fig,axs=plt.subplots(1,3,figsize=(16,7),layout='constrained')
for ax,title,v,lo,hi in [(axs[0],'All observed DSM',z,4,16),(axs[1],'Plane residual: predicted minus DSM',preds['plane']-z,-2,2),(axs[2],'Radial residual: predicted minus DSM',preds['radial']-z,-2,2)]:
 im=ax.scatter(x[m],y[m],c=v[m],s=28,marker='s',vmin=lo,vmax=hi,cmap='viridis' if ax is axs[0] else 'coolwarm');fig.colorbar(im,ax=ax,label='m ODN' if ax is axs[0] else 'm; clipped ±2 for display');ax.plot(*p.exterior.xy,c='black');ax.set_aspect('equal');ax.set(title=title,xlabel='Local E m',ylabel='Local N m')
fig.savefig(R/'school_roof_model_comparison001.png',dpi=140)
report['samples']=[{'x':float(xx),'y':float(yy),'dsm_odn':float(zz),'inset2':bool(cc),'plane_pred_odn':float(pp),'radial_pred_odn':float(rr)} for xx,yy,zz,cc,pp,rr in zip(x[m],y[m],z[m],core[m],preds['plane'][m],preds['radial'][m])]
(R/'school_roof_model_comparison001.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
west=core&(x<-60);X=x[west];Y=y[west];Z=z[west]
c=least_squares(lambda q:q[0]+q[1]*np.sqrt((X-q[2])**2+(Y-q[3])**2)-Z,[11,.15,-45,520],bounds=([0,-1,-85,480],[25,1,-25,550]),loss='soft_l1',f_scale=.2).x
prediction=c[0]+c[1]*np.sqrt((x-c[2])**2+(y-c[3])**2)
report['western_radial_test']={'domain':'2m inset and local E<-60m; geometric exploratory domain, not proven roof boundary. No height rejection.','parameters':c.tolist(),'train':stat((prediction-z)[west]),'withheld_east':stat((prediction-z)[core&~west]),'full':stat((prediction-z)[m]),'low_train_below8':int((west&(z<8)).sum())}
for row,pred in zip(report['samples'],prediction[m]):row['western_radial_pred_odn']=float(pred)
(R/'school_roof_model_comparison001.json').write_text(json.dumps(report,indent=2)+'\n');print(report['western_radial_test'])
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,7),layout='constrained');res=prediction-z
im=ax.scatter(x[m],y[m],c=res[m],s=27,marker='s',vmin=-1,vmax=1,cmap='coolwarm');fig.colorbar(im,ax=ax,label='Predicted minus DSM m; clipped ±1');ax.plot(*p.exterior.xy,c='black');ax.axvline(-60,c='black',ls='--',label='Exploratory training boundary');ax.set_aspect('equal');ax.legend();ax.set(title='Western radial model over all points',xlabel='Local E m',ylabel='Local N m')
radius=np.sqrt((x-c[2])**2+(y-c[3])**2);bx.scatter(radius[m],z[m],c=np.where(west[m],0,1),cmap='coolwarm',s=12,alpha=.6);rr=np.linspace(radius[m].min(),radius[m].max(),100);bx.plot(rr,c[0]+c[1]*rr,c='black');bx.set(title='All samples: blue training / red other',xlabel='Distance to fitted center m',ylabel='DSM m ODN');fig.savefig(R/'school_radial_domain001.png',dpi=140)
report['visual_review']={'actually_inspected':False,'images':['school_roof_model_comparison001.png','school_radial_domain001.png']}
report['decision']={'candidate_created':False,'reason':'Western radial geometry is a supported surface hypothesis, but whole-building closure and east low-return topology unresolved. A closed export replacing full owner would cover unsupported domains.','supported_component':'Broad western radial surface; center and coefficient fitted, not surveyed architectural design.','next_evidence':'Resolve eastern footprint bulge and inner low zones against licensed roof image/elevation or mapped building-part semantics; retain every low return in diagnostics.'}
(R/'school_roof_model_comparison001.json').write_text(json.dumps(report,indent=2)+'\n')
