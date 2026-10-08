from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,Point,LineString
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if '7d217ccd' in q['id']);ring=f['geometry'][0]['outer'];a=np.array(json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf']);C=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);rr=right*np.cos(roll)+up*np.sin(roll);uu=-right*np.sin(roll)+up*np.cos(roll)
def project(xyz):
 d=np.array(xyz)-C;return np.column_stack([1921/2+np.exp(a[6])*(d@rr)/(d@fw),1280/2-np.exp(a[6])*(d@uu)/(d@fw)])

fig,ax=plt.subplots(figsize=(15,10));ax.imshow(Image.open(R/'references/pexels-ollie-craig-11491155.jpeg').resize((1921,1280)))
for height,color in [(0,'yellow'),(70,'cyan')]:
 pp=project([[*q,height] for q in ring+[ring[0]]]);ax.plot(*pp.T,c=color,lw=2,label=str(height)+'m')
ax.set(xlim=(1000,1921),ylim=(1150,450),title='20 Bank Street candidate projection');ax.legend();fig.savefig(R/'references/bank20_photo_projection.png',dpi=150)
print(project([[*q,70] for q in ring]))
