"""Review height discrepancies; no automatic geometry changes."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references'
d=json.loads((r/'lidar_building_height_evidence.json').read_text())
rows=[b for b in d['buildings'] if 'relative_height_percentiles_m' in b]
fig,ax=plt.subplots(figsize=(9,8),layout='constrained')
for guessed,color,label in [(False,'#386cb0','Source/floor-based height'),(True,'#e07020','Default 9 m height')]:
 s=[b for b in rows if (b['old_height_basis']=='assumed_9m_unknown_height')==guessed]
 ax.scatter([b['old_height_m'] for b in s],[b['relative_height_percentiles_m'][2] for b in s],s=18,alpha=.55,label=label,color=color)
ax.plot([0,250],[0,250],color='gray',linestyle='--',linewidth=1)
ax.set(xlim=(0,250),ylim=(-5,250),xlabel='Current model height (m)',ylabel='LiDAR DSM − DTM, interior 95th percentile (m)',title=f'Canary Wharf: {len(rows)} sampled building/part footprints\nDiscrepancies require individual review; survey dates differ')
ax.legend();ax.grid(alpha=.15)
fig.get_layout_engine().set(rect=(0,.045,1,.955))
fig.text(.5,.012,'Environment Agency OGL data. Percentiles are not measured apex/eave heights.',ha='center',fontsize=9)
fig.savefig(r/'lidar-model-height-comparison.png',dpi=150)
