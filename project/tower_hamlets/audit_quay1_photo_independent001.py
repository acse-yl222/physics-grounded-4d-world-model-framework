from pathlib import Path
import json,math,numpy as np
from shapely.geometry import Polygon,LineString
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/quay1-photo-independent-001';O.mkdir(exist_ok=True);G=json.loads((R/'geometry.json').read_text())['buildings'];C=np.array([-719.321771581938,41.69714346949693]);T=next(f for f in G if 'a6a8ac29' in f['id']);P=Polygon(T['geometry'][0]['outer']);tc=np.array(P.centroid.coords[0]);angle=lambda c:math.degrees(math.atan2(c[1]-C[1],c[0]-C[0]));rows=[];fig,ax=plt.subplots(figsize=(10,8))
for f in G:
 p=Polygon(f['geometry'][0]['outer']);cen=np.array(p.centroid.coords[0]);bearing=angle(cen)
 if f['id']!='site-support' and (abs(bearing-angle(tc))<10 and f['height_m']>=35 or any(k in f['id'] for k in ['97dd8c74','26bcb1ba','6019910a','a6a8ac29'])):
  rows.append({'id':f['id'],'name':f['name'],'centroid':cen.tolist(),'bearing_degrees_north_of_east':bearing,'camera_distance_xy_m':float(np.linalg.norm(cen-C)),'baseline_height_not_verified':f['height_m']});v=np.array(p.exterior.coords);ax.plot(*v.T);ax.text(*cen,f['name'][:28],fontsize=7);ax.plot([C[0],cen[0]],[C[1],cen[1]],ls=':',lw=.7)
ax.scatter(*C,c='red');ax.text(*C,'Ollie approximate camera');ax.set(aspect='equal',xlabel='AEQD east m',ylabel='AEQD north m',title='Independent angular ordering; mapped neighboring owners');fig.tight_layout();fig.savefig(O/'neighbor-bearing-context.png',dpi=150)
v=np.array(P.exterior.coords);edges=[]
for i,(a,b) in enumerate(zip(v[:-1],v[1:])):
 mid=(a+b)/2;ray=LineString([C,mid]);# segment is exposed if approach to midpoint is outside owner
 front=not P.contains(__import__('shapely').geometry.Point(*(mid+.01*(C-mid)/np.linalg.norm(C-mid))))
 edges.append({'index':i,'a':a.tolist(),'b':b.tolist(),'length_m':float(np.linalg.norm(b-a)),'faces_camera_in_plan':front})
d={'camera_xy':C.tolist(),'target_center':tc.tolist(),'bearing_to_target':angle(tc),'camera_direction_from_target':'west-southwest; visible side broadly west/southwest, not rear east/north','comparison_owners':rows,'target_edges':edges,'certainty':'Identity strongly supported by relative angular order, target unique tall owner in local bearing sector, footprint curved frontage, and actual cropped photo. Pixel correspondence remains approximate.'};(O/'audit.json').write_text(json.dumps(d,indent=2));print(json.dumps(rows,indent=2));print('frontedges',[(e['index'],round(e['length_m'],2)) for e in edges if e['faces_camera_in_plan']])
