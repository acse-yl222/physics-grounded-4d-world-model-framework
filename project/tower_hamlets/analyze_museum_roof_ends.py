"""Inspect longitudinal roof terminations; no extrapolated hips."""
from pathlib import Path
import json,runpy
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
s=Path(__file__).resolve().parent;r=s/'input/canary_wharf_20261007';fit=json.loads((r/'references/museum_roof_fit.json').read_text());ns=runpy.run_path(str(s/'analyze_museum_lidar.py'));x,y,z=ns['x'],ns['y'],ns['z'];g=ns['g'];polys=[]
for id in [fit['building_id'],fit['child_id']]:
 b=next(b for b in g['buildings'] if b['id']==id);polys.append(unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]))
p=unary_union(polys);m=ns['valid']&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);origin=fit['origin_local_m'];u=(x-origin[0])*fit['long_axis'][0]+(y-origin[1])*fit['long_axis'][1];v=(x-origin[0])*fit['cross_axis'][0]+(y-origin[1])*fit['cross_axis'][1]
fig,axs=plt.subplots(3,2,figsize=(14,10),layout='constrained');records=[]
for col,side in enumerate(['west','east']):
 profile=fit['independent_profiles']['profiles'][side];ridge=profile['ridge_candidates_v_m'];sel=m&((u>=fit['longitudinal_step_u_m'])==(side=='east'))
 for row,center in enumerate(ridge[:3]):
  q=sel&(abs(v-center)<.8);ax=axs[row,col];ax.scatter(u[q],z[q],s=12);ax.set(title=f'{side} ridge{row+1}, v={center:.2f}m ±0.8m',xlabel='Along roof u m',ylabel='DSM ODN m');ax.set_ylim(3,24)
  bins=[]
  for lo in np.arange(np.floor(u[q].min()),np.ceil(u[q].max()),2):
   b=q&(u>=lo)&(u<lo+2)
   if b.any():bins.append({'u_center_m':float(lo+1),'count':int(b.sum()),'dsm_p10_p50_p90_m':np.percentile(z[b],[10,50,90]).tolist()})
  records.append({'side':side,'ridge_cross_axis_m':center,'samples':int(q.sum()),'longitudinal_bins':bins})
fig.suptitle('Museum roof ends: raw ridge-strip returns, no hip assumption');fig.savefig(r/'references/museum_roof_ends.png',dpi=140)
report={'source_fit':'museum_roof_fit.json','method':'Raw DSM within0.8m of each independently fitted ridge, exact union footprint;2m along-roof bin statistics. Includes low returns.','profiles':records,'geometry_modified':False,'visual_reviewed':False,'limitations':['One metre samples and mixed survey dates.','A height drop at footprint edge may be wall/ground interpolation rather than a roof hip.','Textual hipped roof description does not locate hip ends in current raster.']};(r/'references/museum_roof_ends.json').write_text(json.dumps(report,indent=2)+'\n')
