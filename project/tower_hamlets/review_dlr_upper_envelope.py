"""Upper-return quantile diagnostic, not a ground-truth roof classification."""
from pathlib import Path
import json,numpy as np
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;ns={'__file__':str(S/'review_dlr_canopy_heights.py')};source=(S/'review_dlr_canopy_heights.py').read_text();exec(compile(source.split('sel=')[0],str(S/'review_dlr_canopy_heights.py'),'exec'),ns)
for k in ['R','x','y','z','inside','u','v','p']:globals()[k]=ns[k]
valid=inside&(z>10)&(z<60);bins=np.arange(np.floor(v[valid].min()),np.ceil(v[valid].max())+1,1.);groups=np.floor((u-u[valid].min())/5).astype(int)%3;rows=[];fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained');axs[0].scatter(v[valid],z[valid],s=3,c='0.8');curves=[]
for group in range(3):
 vals=[]
 for lo in bins[:-1]:
  m=valid&(groups==group)&(v>=lo)&(v<lo+1);vals.append(float(np.quantile(z[m],.9)) if m.sum()>=3 else None)
 curves.append(vals);axs[0].plot(bins[:-1]+.5,[np.nan if q is None else q for q in vals],label=f'5m strip group{group}')
arr=np.array([[np.nan if q is None else q for q in vals] for vals in curves]);spread=np.nanmax(arr,axis=0)-np.nanmin(arr,axis=0);centers=bins[:-1]+.5;axs[1].plot(centers,spread);axs[1].set(xlabel='Across canopy (m)',ylabel='Upper quantile spread (m)',title='Agreement of separated longitudinal strips');axs[0].set(xlabel='Across canopy (m)',ylabel='ODN height (m)',title='90th percentile within1m transverse bins');axs[0].legend();fig.savefig(R/'references/dlr_upper_envelope.png',dpi=150)
report={'bin_centers_v_m':centers.tolist(),'strip_group_q90_odn_m':curves,'group_spread_m':spread.tolist(),'median_group_spread_m':float(np.nanmedian(spread)),'p95_group_spread_m':float(np.nanpercentile(spread,95)),'scope':'Posthoc upper-return diagnostic; quantile selection does not prove roof membership or validate unseen surfaces. Missing bins remain missing.','geometry_modified':False};(R/'references/dlr_upper_envelope.json').write_text(json.dumps(report,indent=2));print({k:report[k] for k in ['median_group_spread_m','p95_group_spread_m']})
