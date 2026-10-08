from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('aace_model_sensitivity.py').read_text().split('rows=[];')[0])
m=mask(transform(xy,nw).buffer(-1));bins=[]
for a in np.arange(-311,-296,1):
 mm=m&(u>=a)&(u<a+1)
 if mm.sum():bins.append({'u_interval':[float(a),float(a+1)],'cells':int(mm.sum()),'dsm_odn':stats(z[mm]),'dtm_odn':stats(t[mm]),'dsm_minus_dtm':stats((z-t)[mm])})
fig,ax=plt.subplots(figsize=(8,4),layout='constrained');xx=[np.mean(r['u_interval']) for r in bins];ax.plot(xx,[r['dsm_odn']['median'] for r in bins],'o-');ax.fill_between(xx,[r['dsm_odn']['p10'] for r in bins],[r['dsm_odn']['p90'] for r in bins],alpha=.2);ax.set(xlabel='u, rotated16degrees',ylabel='ODN m',title='NW wing: full1m-inset longitudinal bins, median and10–90%');fig.savefig(R/'references/aace_nw_low_domain.png',dpi=160);(R/'references/aace_nw_low_domain.json').write_text(json.dumps({'bins':bins,'decision':'Eastward roofdecline spatiallycoherent, but binnedreturns showgradualfall ratherthanprovenverticalstep. Couldsupportdifferentroofextent/slope; noindependentarchitecturalbreakline at u=-300. Do notcutlowdomainmerelytoimprovepeakfit. NWremainsunresolved.','geometry_modified':False},indent=2))
