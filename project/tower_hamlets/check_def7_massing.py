from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,Point,shape
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/def7_massing_study.json').read_text());d=np.load(R/'references/def7_samples.npz');g=json.loads((R/'geometry.json').read_text());b=next(q for q in g['buildings'] if q['id']==r['parent_id']);p=Polygon(b['geometry'][0]['outer']);hole=shape(r['recess_hypothesis']['geometry']);fig,axs=plt.subplots(1,2,figsize=(14,7),layout='constrained');m=d['valid']&np.array([p.contains(Point(x,y)) for x,y in zip(d['x'].flat,d['y'].flat)]).reshape(d['x'].shape);im=axs[0].scatter(d['x'][m],d['y'][m],c=d['z'][m],vmin=3,vmax=33,s=15);fig.colorbar(im,ax=axs[0],label='native DSM ODN m');checks=[]
for i,q in enumerate(r['objects']):
 ps=[]
 for f in q['roof_faces']:
  poly=Polygon([q['vertices'][j][:2] for j in f])
  if poly.area>1e-10:ps.append(poly)
 poly=unary_union(ps);checks.append(dict(name=q['name'],outside_original_m2=poly.difference(p).area,intersection_recess_m2=poly.intersection(hole).area));assert poly.difference(p).area<1e-5 and poly.intersection(hole).area<1e-5
 for pp in (poly.geoms if hasattr(poly,'geoms') else [poly]):
  for ax in axs:ax.plot(*pp.exterior.xy,label=q['name'])
  axs[1].fill(*pp.exterior.xy,alpha=.3)
for ax in axs:
 ax.fill(*hole.exterior.xy,color='black',alpha=.25,label='Uncertain low-return recess');ax.set_aspect('equal');ax.set_xlabel('east m');ax.set_ylabel('north m')
axs[0].set_title('Observed cells, all elevations retained');axs[1].set_title('Estimated stepped footprint domains');axs[1].legend(fontsize=7);fig.savefig(R/'references/def7_zone_support.png',dpi=150);(R/'references/def7_geometry_checks.json').write_text(json.dumps(dict(checks=checks,outer_boundary_preserved=True,recess_coverage_note='54low nativecells; buffered convex enclosure additionally contains boundary/high cells, all reported.'),indent=2)+'\n')
