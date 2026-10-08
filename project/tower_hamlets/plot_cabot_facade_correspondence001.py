from pathlib import Path
import json
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/cabot-facade-correspondence-001';d=json.loads((O/'audit.json').read_text());fig,ax=plt.subplots(figsize=(10,12));ax.imshow(Image.open(R/'references/pexels-anna-rynkowska-19572396.jpeg').resize((1368,1824)))
for o in d['projected_objects']:
 if o['name'] not in ['CabotPlace_glass','CabotPlaceWest roof zone main continuous roof','CabotPlaceWest roof zone western entrance envelope estimate']:continue
 color='cyan' if 'glass' in o['name'] else ('orange' if 'main' in o['name'] else 'magenta')
 for i,j in o['edges']:
  a,b=o['pixels'][i],o['pixels'][j];ax.plot([a[0],b[0]],[a[1],b[1]],color=color,linewidth=.35,alpha=.7)
 ax.plot([],[],color=color,label=o['name'])
ax.set(xlim=(180,1320),ylim=(1450,850));ax.legend(fontsize=7);ax.set_title('Actual existing geometry with stored 3-roof camera; foreground correspondence unverified');fig.tight_layout();fig.savefig(O/'foreground_projection.png',dpi=150)
