from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';d=json.loads((R/'references/north_quay_owner_interfaces.json').read_text());g=json.loads((R/'geometry.json').read_text());ids={i for r in d['interfaces'] for i in r['owners']};fig,ax=plt.subplots(figsize=(13,5));good=[];missing=[]
for b in g['buildings']:
 if b['id'] not in ids:continue
 for p in b['geometry']:
  xy=p['outer']+[p['outer'][0]];ax.plot([v[0] for v in xy],[v[1] for v in xy],color='.65',lw=.8)
for row in d['interfaces']:
 for q in row['samples']:(good if q['difference_m'] is not None else missing).append(q['xy_m'])
for points,c,label in [(good,'#197a65',f'Both roofs supported: {len(good)} samples'),(missing,'#d67922',f'Missing support on one/both sides: {len(missing)} samples')]:
 ax.scatter([p[0] for p in points],[p[1] for p in points],s=8,c=c,label=label)
ax.set_aspect('equal');ax.set_xlabel('Local east (m)');ax.set_ylabel('Local north (m)');ax.set_title('North Quay — mapped ownership interfaces, 0.25 m sampling\nAgreement measures model continuity, not survey accuracy');ax.legend(loc='lower left',fontsize=8);fig.tight_layout();fig.savefig(R/'references/north_quay_owner_interfaces.png',dpi=180)
print('supported',len(good),'missing',len(missing))
