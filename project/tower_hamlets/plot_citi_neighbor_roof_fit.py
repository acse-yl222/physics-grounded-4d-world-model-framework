from pathlib import Path
import json,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';d=np.load('cache/tower_hamlets/citi_neighbor_roof.npz');fit=json.loads((R/'references/citi_neighbor_roof_fit.json').read_text());u,v,z=d['u'],d['v'],d['z'];m=d['mask'];h=(u>-10)&(v>-157)&(v<-105);c=fit['regions'][1]['plane_odn_c_a_u_b_v'];pred=np.where(h,c[0]+c[1]*u+c[2]*v,fit['lower_level_odn']);fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,a,title,lo,hi in [(axs[0],z,'DSM all4m-inset',76,89),(axs[1],pred,'Clean two-domain hypothesis',76,89),(axs[2],z-pred,'Residual allcells,no rejection',-10,10)]:
 im=ax.scatter(u[m],v[m],c=a[m],s=5,vmin=lo,vmax=hi);fig.colorbar(im,ax=ax);ax.set(aspect='equal',title=title)
fig.savefig(R/'references/citi_neighbor_roof_fit.png',dpi=150)
