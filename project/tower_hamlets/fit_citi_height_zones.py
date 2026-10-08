"""Two-level diagnostic along mapped Citi footprint; no raw-cell rejection."""
from pathlib import Path
import runpy,json
import numpy as np
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
a=runpy.run_path(str(Path(__file__).with_name('review_citi_roof.py')))
x,y,z,t,p,mask=a['x'],a['y'],a['z'],a['t'],a['p'],a['mask']
xy=np.array(p.exterior.coords);origin=xy[0];edges=np.diff(xy,axis=0);e=edges[np.argmax(np.linalg.norm(edges,axis=1))];e=e/np.linalg.norm(e)
if e[0]<0:e=-e
v=np.array([e[1],-e[0]])
u=(x-origin[0])*e[0]+(y-origin[1])*e[1];w=(x-origin[0])*v[0]+(y-origin[1])*v[1]
rows=[]
def fit(m):
 best=None
 for cut in np.arange(12,36,.25):
  left=m&(u<cut);right=m&(u>=cut)
  if min(left.sum(),right.sum())<30:continue
  zl=np.median(z[left]);zr=np.median(z[right]);err=np.abs(z[left]-zl).sum()+np.abs(z[right]-zr).sum()
  if best is None or err<best[0]:best=(float(err),float(cut),float(zl),float(zr))
 return best
for inset in [0,2,4,6]:
 m=mask(p.buffer(-inset));best=fit(m);left=m&(u<best[1]);right=m&~left
 row={'inset_m':inset,'cut_u_m':best[1],'median_odn_m':[best[2],best[3]],'cells':[int(left.sum()),int(right.sum())],'median_agl_m':[float(np.median((z-t)[left])),float(np.median((z-t)[right]))],'median_abs_residual_m':[float(np.median(abs(z[left]-best[2]))),float(np.median(abs(z[right]-best[3])))],'dtm_median_odn_m':[float(np.median(t[left])),float(np.median(t[right]))]}
 row['cross_axis_holdout']=[]
 for k in range(3):
  fold=(np.floor(w/5).astype(int)%3)==k;train=m&~fold;test=m&fold;f=fit(train);pred=np.where(u<f[1],f[2],f[3]);er=z[test]-pred[test]
  row['cross_axis_holdout'].append({'cut_u_m':f[1],'cells':int(test.sum()),'median_abs_m':float(np.median(abs(er))),'rmse_m':float(np.sqrt(np.mean(er*er)))})
 rows.append(row)
report={'owner_id':a['fs'][0]['id'],'origin_xy_m':origin.tolist(),'u_axis':e.tolist(),'v_axis':v.tolist(),'fits':rows,'selection':'All valid DSM cells in each geometric inset; no height/residual filter. Two-level absolute-error fit diagnostic, not accepted surveyed roofplanes.','interpretation':'Large western lowerzone contradicts whole-footprint200m extrusion. Boundarytransition/smalllowpatches may be interpolation or occlusion; no lowholes inferred.','limitations':['Mixed2017–2020DSM and2026inventory','Two-level model ignores crown/plant,transition and roofstructure','DTM10m at elevatedsite is not a surveyedbuildingfoundation','No geometry changed by this diagnostic'],'visual_reviewed':False}
fig,axs=plt.subplots(1,2,figsize=(14,6),layout='constrained');m=mask(p);im=axs[0].scatter(u[m],w[m],c=z[m],s=9,marker='s',vmin=90,vmax=215);fig.colorbar(im,ax=axs[0],label='DSM ODN m');axs[0].axvline(rows[2]['cut_u_m'],color='red',lw=1);axs[0].set(aspect='equal',xlabel='Footprint u / m',ylabel='Footprint v / m',title='Citi height zones; all footprint cells')
for lo,hi in [(5,20),(20,40),(40,56)]:
 mm=m&(w>=lo)&(w<hi);us=[];zs=[]
 for b in range(0,75):
  sel=mm&(u>=b)&(u<b+1)
  if sel.sum():us.append(b+.5);zs.append(np.median(z[sel]))
 axs[1].plot(us,zs,label=f'v {lo}–{hi}m')
axs[1].set(xlabel='Footprint u / m',ylabel='Median DSM ODN / m',title='Independent width strips: lower western volume');axs[1].legend();fig.savefig(R/'references/citi_height_zones.png',dpi=140)
(R/'references/citi_height_zones.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
