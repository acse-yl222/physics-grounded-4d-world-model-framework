"""Static scope/inventory map from mapped footprints; not a completion certificate."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json
from pathlib import Path
import numpy as np
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, Patch as LegendPatch
R=authoring_path()
g=json.loads((R/'geometry.json').read_text());c=json.loads((R.parent/'references/campus/campus_geometry.json').read_text());co=json.loads((R/'coordinate_contract.json').read_text());M=np.array(co['source_xy_to_campus_affine']);origin=np.array(g['origin_projected_m'])
def xy(points):return np.asarray(points)@M[:,:2].T+M[:,2]
fig,ax=plt.subplots(figsize=(11,11));ax.set_facecolor('#faf9f6')
landmarks={'way-372860405':('1','Royal Albert Hall'),'way-27765400':('2','Royal College of Music'),'way-24436446':('3','Natural History Museum'),'way-27765411':('4','Science Museum'),'relation-29795':('5','Victoria and Albert Museum'),'way-4959880':('6','Dana Research Centre')}
for b in g['buildings']:
 for p in b['geometry']:
  ax.add_patch(Patch(xy(p['outer']),facecolor='#e1a444' if b['id'] in landmarks else '#ccd0d4',edgecolor='#626a72',linewidth=.25))
  for h in p.get('holes',[]):ax.add_patch(Patch(xy(h),facecolor='#faf9f6',edgecolor='#626a72',linewidth=.25))
for b in c['buildings']:
 for p in b['geometry']:
  ax.add_patch(Patch(p['outer'],facecolor='#4689af',edgecolor='#24556f',linewidth=.3))
  for h in p.get('holes',[]):ax.add_patch(Patch(h,facecolor='#faf9f6',edgecolor='#24556f',linewidth=.3))
for b in g['buildings']:
 if b['id'] in landmarks and b['geometry']:
  v=xy(b['geometry'][0]['outer']);p=v.mean(axis=0);ax.text(*p,landmarks[b['id']][0],ha='center',va='center',fontsize=12,fontweight='bold',bbox=dict(boxstyle='circle,pad=.22',fc='white',ec='#915d13',lw=1))
w,s,e,n=json.loads((R/'region.json').read_text())['bbox_wgs84'];t=Transformer.from_crs(4326,32630,always_xy=True);ring=np.array([t.transform(*v) for v in [(w,s),(e,s),(e,n),(w,n),(w,s)]])-origin;v=xy(ring);ax.plot(v[:,0],v[:,1],'--',color='#ac3d32',lw=1.3)
ax.set_xlim(v[:,0].min()-60,v[:,0].max()+60);ax.set_ylim(v[:,1].min()-50,v[:,1].max()+50);ax.set_aspect('equal');ax.set_xlabel('Existing campus frame X (m)');ax.set_ylabel('Existing campus frame Y (m)');ax.set_title('Fixed South Kensington expansion scope\n42 inherited campus records + 1,128 new module targets',fontsize=14)
ax.legend(handles=[LegendPatch(color='#4689af',label='Imperial Phase4 preserved'),LegendPatch(color='#e1a444',label='Current per-building refinement batch'),LegendPatch(color='#ccd0d4',label='Remaining baseline / refinement pending')],loc='upper right',fontsize=8)
fig.text(.12,.015,'  |  '.join(f'{v[0]} {v[1]}' for v in landmarks.values()),fontsize=7)
fig.text(.12,.035,'Complete intersecting buildings retained across dashed boundary. OSM-derived footprint map; not surveyed accuracy or detail acceptance.',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(R/'docs/refinement_scope_map.png',dpi=180);fig.savefig(R/'docs/refinement_scope_map.pdf');print(R/'docs/refinement_scope_map.png')
