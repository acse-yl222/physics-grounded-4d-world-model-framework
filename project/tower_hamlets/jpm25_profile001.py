from pathlib import Path
import json,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/jpm25-evidence-001';a=json.load(open(O/'jpm25-audit.json'));p=np.array(a['source_geometry']['geometry'][0]['outer']);d=np.load(O/'jpm25-samples.npz');m=d['inside']&d['valid'];x,y,z,t=[d[k][m] for k in ['x','y','z','dtm']];edges=np.roll(p,-1,axis=0)-p;u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u=u/np.linalg.norm(u);u=u if u[0]>0 else -u;v=np.array([-u[1],u[0]]);xy=np.c_[x,y];uv=xy@np.array([u,v]).T;lo=z<20;eq=np.abs(z-t)<.01
fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained');axs[0,0].scatter(*uv.T,c=z,s=4);axs[0,0].set(title='All roof returns, rotated footprint axes',aspect='equal');axs[0,1].scatter(*uv.T,c=np.where(lo,np.where(eq,2,1),0),s=4,vmin=0,vmax=2);axs[0,1].set(title='Low returns: purple=no; green=low; yellow=DTM match',aspect='equal');axs[1,0].scatter(uv[:,1],z,s=2);axs[1,0].set(xlabel='v m',ylabel='ODN m');axs[1,1].hist(z,bins=100);axs[1,1].set(xlabel='ODN m',ylabel='cells');fig.savefig(O/'jpm25-profile.png',dpi=150)
bins=[]
for b in np.arange(np.floor(uv[:,1].min()),np.ceil(uv[:,1].max()),2):
 sel=(uv[:,1]>=b)&(uv[:,1]<b+2);bins.append({'v':[b,b+2],'n':int(sel.sum()),'median':float(np.median(z[sel])) if sel.any() else None,'low':int((sel&lo).sum()),'dtm_match':int((sel&eq).sum())})
r={'axes':[u.tolist(),v.tolist()],'all_cells':len(z),'low_lt20_count':int(lo.sum()),'low_dtm_match_count':int((lo&eq).sum()),'all_dtm_match_count':int(eq.sum()),'low_dsm_quantiles':np.percentile(z[lo],[0,25,50,75,100]).tolist(),'bands':bins,'interpretation':'Ground-like returns may be occlusion or glass dropout. Do not cut courtyard from this alone.'};(O/'jpm25-profile.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='bands'})
