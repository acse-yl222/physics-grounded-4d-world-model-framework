from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';d=json.loads((R/'north_quay_fit_seams.json').read_text());g=json.loads((R.parent/'geometry.json').read_text());ids={r['id'] for r in json.loads((R/'north_quay_roof_group.json').read_text())['features']};fig,ax=plt.subplots(figsize=(15,5),layout='constrained')
for b in g['buildings']:
 if b['id'] not in ids:continue
 for q in b['geometry']:
  xy=q['outer']+[q['outer'][0]];ax.plot([p[0] for p in xy],[p[1] for p in xy],c='gray',lw=.7)
samples=[s for o in d['owners'] for s in o['samples']];im=ax.scatter([s['position_enu_m'][0] for s in samples],[s['position_enu_m'][1] for s in samples],c=[abs(s['raw_minus_fit_m']) for s in samples],s=11,vmin=0,vmax=.5,cmap='inferno');fig.colorbar(im,ax=ax,label='Absolute raw/fitted height mismatch m');ax.set(aspect='equal',xlabel='Local east m',ylabel='Local north m',title='North Quay: model seam audit (not physical roof steps)');fig.savefig(R/'north_quay_fit_seams.png',dpi=140)
