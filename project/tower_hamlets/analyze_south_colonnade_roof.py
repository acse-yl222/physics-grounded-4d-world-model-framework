from pathlib import Path
import json,numpy as np
s=Path(__file__).with_name('review_south_colonnade_roof.py').read_text();exec(s.split('rows=[]')[0])
from scipy.ndimage import median_filter
th=np.deg2rad(-10);u=x*np.cos(th)+y*np.sin(th);v=-x*np.sin(th)+y*np.cos(th);m=mask(p.buffer(-4));fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained');im=axs[0].scatter(u[m],v[m],c=z[m],s=4,vmin=28,vmax=73);fig.colorbar(im,ax=axs[0]);axs[0].set(aspect='equal',title='NativeDSM in4m inset; rotated -10deg')
profiles={}
for ax,arr,label in [(axs[1],u,'u'),(axs[2],v,'v')]:
 bins=np.arange(np.floor(arr[m].min()),np.ceil(arr[m].max())+2,2);rows=[]
 for lo,hi in zip(bins,bins[1:]):
  mm=m&(arr>=lo)&(arr<hi)
  if mm.sum():rows.append([float((lo+hi)/2),int(mm.sum()),*np.percentile(z[mm],[10,25,50,75,90]).tolist()])
 a=np.array(rows);ax.plot(a[:,0],a[:,4]);ax.fill_between(a[:,0],a[:,2],a[:,6],alpha=.2);ax.set(title='2m bins median and10-90%',xlabel=label,ylabel='ODN');profiles[label]=rows
fig.savefig(R/'references/south_colonnade_roof_profiles.png',dpi=150);(R/'references/south_colonnade_roof_profiles.json').write_text(json.dumps(profiles,indent=2));np.savez(Path('cache/tower_hamlets/south_colonnade_roof.npz'),x=x,y=y,z=z,t=t,u=u,v=v,valid=valid,mask=m);print('rangeu',u[m].min(),u[m].max(),'v',v[m].min(),v[m].max())
