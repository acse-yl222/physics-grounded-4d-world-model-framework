"""Classify unsupported Billingsgate roof returns without inventing closures."""
from pathlib import Path
import runpy,json
import numpy as np
from scipy.ndimage import label
import matplotlib.pyplot as plt
ns=runpy.run_path(str(Path(__file__).with_name('analyze_billingsgate_lidar.py')))
for k in ['ROOT','x','y','z','masks','across','along','pred','centers','rep','p']:globals()[k]=ns[k]
inside=masks['1'];classes=np.zeros(z.shape,dtype=int)
classes[inside]=1
classes[inside&(z<pred-.5)]=2
classes[inside&(z>pred+.5)]=3
classes[inside&((across<centers[0])|(across>centers[-1]))]=4
reports=[]
for kind,name in [(2,'below_profile'),(3,'above_profile')]:
 labs,n=label(classes==kind)
 for index in range(1,n+1):
  q=labs==index
  if q.sum()<4:continue
  reports.append({'class':name,'cells':int(q.sum()),'along_range_m':[float(along[q].min()),float(along[q].max())],'across_range_m':[float(across[q].min()),float(across[q].max())],'dsm_odn_p10_p50_p90_m':np.percentile(z[q],[10,50,90]).tolist(),'median_profile_residual_m':float(np.median(z[q]-pred[q]))})
reports.sort(key=lambda a:-a['cells'])
fig,axs=plt.subplots(2,1,figsize=(14,8),layout='constrained');im=axs[0].scatter(along[inside],across[inside],c=classes[inside],s=8,marker='s',cmap='tab10',vmin=0,vmax=9);axs[0].set(title='Roof support: orange=within0.5m; green=below; red=above; purple=outside fitted range',xlabel='Along m',ylabel='Across m');axs[0].set_aspect('equal')
se=masks['0']&(along>55)&(across<0);im=axs[1].scatter(along[se],across[se],c=z[se],s=40,marker='s',vmin=5,vmax=17);fig.colorbar(im,ax=axs[1],label='DSM m ODN');axs[1].set(title='Southeast native returns: roof-to-ground transition',xlabel='Along m',ylabel='Across m');axs[1].set_aspect('equal');fig.savefig(ROOT/'references/billingsgate_gaps.png',dpi=140)
out={'classes':{'1':'within0.5m_profile','2':'below_profile','3':'above_profile','4':'outside_fitted_range'},'counts':{str(k):int((classes==k).sum()) for k in range(1,5)},'components':reports,'scope':'Connected raster cells are diagnostic clusters, not semantic building parts. No gap filled or roof equipment inferred.','visual_reviewed':False}
(ROOT/'references/billingsgate_gaps.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
