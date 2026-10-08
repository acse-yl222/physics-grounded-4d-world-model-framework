from pathlib import Path
import json,numpy as np
from shapely.geometry import shape,Point
from scipy.optimize import least_squares
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-evidence-002';a=json.load(open(O/'fff_boundary-audit.json'));fs=[q for q in a['nearby_raw_owners'] if q['id'].startswith(('fff95900','02ed5509'))];ps=[shape(q['geometry_local']) for q in fs];p=ps[0].union(ps[1]);s=np.load(O/'fff_boundary-samples.npz');x,y,z,valid=[s[k] for k in ['x','y','z','valid']];v=np.array(ps[0].exterior.coords);e=v[1]-v[0];e/=np.linalg.norm(e);n=np.array([-e[1],e[0]]);u=x*e[0]+y*e[1];w=x*n[0]+y*n[1];r=np.array(p.exterior.coords);lo=np.array([(r@e).min(),(r@n).min()]);hi=np.array([(r@e).max(),(r@n).max()]);center=(lo+hi)/2
mask=lambda q:valid&np.array([q.contains(Point(xx,yy)) for xx,yy in zip(x.flat,y.flat)]).reshape(x.shape)
full=mask(p);m=mask(p.buffer(-1))
def predict(c):
 cu,cv=center+c[2:];h=np.minimum.reduce([(u-lo[0])/(cu-lo[0]),(hi[0]-u)/(hi[0]-cu),(w-lo[1])/(cv-lo[1]),(hi[1]-w)/(hi[1]-cv)]);return c[0]+c[1]*h

def fit(mm,free=True):
 if free:return least_squares(lambda c:(predict(c)-z)[mm],[7.5,2,0,0],bounds=([4,.1,-2.5,-2.5],[11,6,2.5,2.5]),loss='soft_l1',f_scale=.15).x
 q=least_squares(lambda c:(predict(np.r_[c,0,0])-z)[mm],[7.5,2],bounds=([4,.1],[11,6]),loss='soft_l1',f_scale=.15).x;return np.r_[q,0,0]
def metric(r):return {'n':len(r),'rmse_m':float(np.sqrt(np.mean(r*r))),'median_m':float(np.median(r)),'mae_m':float(np.mean(abs(r))),'p95_abs_m':float(np.percentile(abs(r),95)),'within0_5m':int((abs(r)<=.5).sum())}
c=fit(m);fixed=fit(m,False);hold={}
for name,arr in [('across',u),('along',w)]:
 folds=np.floor(arr/2).astype(int)%3;rr=[];ff=[];ccs=[]
 for k in range(3):
  train=m&(folds!=k);test=m&(folds==k);cc=fit(train);ccs.append(cc.tolist());rr.extend((z-predict(cc))[test]);ff.extend((z-predict(fit(train,False)))[test])
 hold[name]={'free':metric(np.array(rr)),'fixed':metric(np.array(ff)),'free_fold_parameters':ccs}
sensitivity={}
for inset in [.5,1,1.5,2]:
 mm=mask(p.buffer(-inset));cc=fit(mm);sensitivity[str(inset)]={'fit_count':int(mm.sum()),'parameters':cc.tolist(),'all_pair':metric((z-predict(cc))[full])}
ind=np.full(x.shape,np.nan)
for q in ps:
 qq=np.array(q.exterior.coords);l=np.array([(qq@e).min(),(qq@n).min()]);h=np.array([(qq@e).max(),(qq@n).max()]);ct=(l+h)/2;tent=1-np.maximum(abs((u-ct[0])/((h-l)[0]/2)),abs((w-ct[1])/((h-l)[1]/2)));mm=mask(q.buffer(-1));cc=least_squares(lambda c:(c[0]+c[1]*tent-z)[mm],[7.5,2],loss='soft_l1',f_scale=.15).x;ind[mask(q)]=(cc[0]+cc[1]*tent)[mask(q)]
D={'owner_ids':[q['id'] for q in fs],'axis_u':e.tolist(),'axis_v':n.tolist(),'uv_lo':lo.tolist(),'uv_hi':hi.tolist(),'center_uv':center.tolist(),'free_parameters_eave_rise_du_dv':c.tolist(),'apex_xy':((center+c[2:])[0]*e+(center+c[2:])[1]*n).tolist(),'apex_odn_m':float(c[0]+c[1]),'fit_inset1m':metric((z-predict(c))[m]),'all_pair_cells':metric((z-predict(c))[full]),'fixed_center_inset1m':metric((z-predict(fixed))[m]),'independent_owner_centered_peaks_in_sample':metric((z-ind)[m]),'spatial_holdout_2m_strips':hold,'inset_sensitivity':sensitivity,'limitations':['Robustfit includes all chosen insetcells; no residual mask deletion. All footprint returns separately reported.','Spatial holdout tests interpolation, not current epoch or absolute survey accuracy.','1m DSM limits apex/eaves precision; allowed apexoffset bounds±2.5m.','Outer ring slightly nonrectangular; projected-bounding-box common-eave hypothesis is approximate.','Context owner is outside regional439inventory.']};(O/'fff_boundary-fit.json').write_text(json.dumps(D,indent=2))
fig,axs=plt.subplots(1,3,figsize=(14,5),layout='constrained')
for ax,arr,title,lim in zip(axs,[z,predict(c),z-predict(c)],['DSM all full-pair cells','Joint free-apex hypothesis ODN','All-cell residual ODN'],[(3,10),(3,10),(-2,2)]):
 im=ax.scatter(x[full],y[full],c=arr[full],s=75,marker='s',vmin=lim[0],vmax=lim[1],cmap='coolwarm' if 'residual' in title else 'viridis');fig.colorbar(im,ax=ax)
 for q in ps:ax.plot(*q.exterior.xy,'k');ax.scatter(*D['apex_xy'],c='red',marker='+')
 ax.set(aspect='equal',title=title)
fig.savefig(O/'fff_boundary-fit.png',dpi=150);print(json.dumps(D,indent=2))
