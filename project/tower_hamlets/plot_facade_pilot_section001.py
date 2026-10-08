from pathlib import Path
import json,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade-detail-pilot-001';d=json.loads((O/'section.json').read_text());g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if 'a6a8ac29' in q['id']);p=np.array(f['geometry'][0]['outer'][12]);fig,ax=plt.subplots(figsize=(10,7));colors={'glass':'#2080a0','rear returns':'#aa55bb','horizontal':'#777777','vertical':'#777777'};seen=set()
for seg in d['segments']:
 name=seg['object'];color='#cf8335' if name.startswith('overture') else ('#aa55bb' if 'rear returns' in name else ('#2080a0' if 'glass' in name else '#777777'));v=np.array(seg['points'])[:,:2];ax.plot(v[:,0],v[:,1],color=color,lw=1.5,label=name if name not in seen else None);seen.add(name)
ax.set(xlim=(p[0]-1,p[0]+1),ylim=(p[1]-1,p[1]+1),aspect='equal',xlabel='scene east m',ylabel='scene north m',title='Actual mesh section z85m: shallow glazing, boxed returns and closed body');ax.legend(fontsize=6);fig.tight_layout();fig.savefig(O/'section.png',dpi=150)
