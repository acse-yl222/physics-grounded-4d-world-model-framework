"""Sensitivity of measured roof coverage to envelope distance; no inferred holes."""
from pathlib import Path
import runpy,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
scene=Path(__file__).resolve().parent
ns=runpy.run_path(str(scene/'build_crossrail_roof_candidate.py'))
valid=ns['valid'];distance=np.abs(np.asarray(ns['z'])-ns['envelope']);along=ns['along'];cross=ns['cross'];refs=ns['refs']
thresholds=[.5,1.,1.5,2.];rows=[]
for threshold in thresholds:
 mask=valid&(distance<=threshold)
 rows.append({'distance_threshold_m':threshold,'supported_cells':int(mask.sum()),'fraction_of_valid_cells':float(mask.sum()/valid.sum())})
# Broad gaps stable across thresholds are evidence for further investigation,
# not final opening boundaries. Transparent roof and poor returns remain possible.
bins=[]
for left in np.arange(-150,150,5):
 region=valid&(along>=left)&(along<left+5)
 if region.sum():bins.append({'long_axis_interval_m':[float(left),float(left+5)],'valid_cells':int(region.sum()),'fractions':[float(np.sum(region&(distance<=t))/region.sum()) for t in thresholds]})
fig,ax=plt.subplots(figsize=(13,4),layout='constrained')
for i,t in enumerate(thresholds):ax.plot([sum(b['long_axis_interval_m'])/2 for b in bins],[b['fractions'][i] for b in bins],label=f'Within {t:g} m')
ax.set(xlabel='Long axis (m)',ylabel='Fraction near upper envelope',ylim=(0,1),title='Crossrail roof support: sensitivity to distance threshold\nLow support is not proof of an architectural opening');ax.legend();ax.grid(alpha=.2)
fig.savefig(refs/'crossrail_roof_sensitivity.png',dpi=150)
report={'thresholds':rows,'longitudinal_bins':bins,'geometry_modified':False,'interpretation':'Central low-support region persists across thresholds; exact boundaries and physical opening semantics unresolved','limitations':['Distance to fitted circle confounds roof material returns with true gaps','Upper envelope fit and classifications use same raster, not independent validation']}
(refs/'crossrail_roof_sensitivity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
