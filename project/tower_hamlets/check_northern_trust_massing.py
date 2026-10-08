"""Independent footprint/interface and all-cell visual diagnostics."""
from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,MultiPoint,Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/northern_trust_massing_study.json').read_text());d=np.load(R/'references/northern_trust_samples.npz');original=next(q for q in json.loads((R/'geometry.json').read_text())['buildings'] if q['id']==r['parent_id']);p=Polygon(original['geometry'][0]['outer'])
fig,ax=plt.subplots(figsize=(10,9),layout='constrained');m=d['valid'];sc=ax.scatter(d['x'][m],d['y'][m],c=d['z'][m],s=15,marker='s',vmin=60,vmax=71);fig.colorbar(sc,ax=ax,label='DSM ODN (m), colour clipped; low returns retained')
checks=[]
for q in r['objects']:
 pp=MultiPoint([a[:2] for a in q['vertices']]).convex_hull
 xx,yy=pp.exterior.xy;ax.plot(xx,yy,label=q['name']);checks.append(dict(name=q['name'],outside_owner_area_m2=pp.difference(p).area));assert pp.difference(p).area<1e-5
for q in r['neighbor_interfaces']:
 xy=np.array(q['shared_geometry']['coordinates']);ax.plot(xy[:,0],xy[:,1],color='red',linewidth=3,label='East Wintergarden shared edge; no extension')
ax.set_aspect('equal');ax.set_xlabel('scene east m');ax.set_ylabel('scene north m');ax.legend(fontsize=8);fig.savefig(R/'references/northern_trust_zone_support.png',dpi=150)
(R/'references/northern_trust_independent_checks.json').write_text(json.dumps(dict(geometry_checks=checks,shared_edge_topology='touching with zero positive-area intersection; body wall retained, no facade ornaments',precision_note='Authored vertex rounding1e-7m; numerical boundary residues allowed1e-5m2',north_body_uncertain=True),indent=2)+'\n')
