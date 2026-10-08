import json,math,numpy as np
from pathlib import Path
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';a=json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf'];c=np.array(a[:3]);yaw,pitch,roll=a[3:6];fw=np.array([math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)]);right=np.array([math.sin(yaw),-math.cos(yaw),0]);up=np.cross(right,fw);r=right*math.cos(roll)+up*math.sin(roll);u=-right*math.sin(roll)+up*math.cos(roll);f=math.exp(a[6]);g=json.loads((R/'geometry.json').read_text());im=Image.open(R/'references/pexels-ollie-craig-11491155.jpeg');im.thumbnail((1921,1280));fig,ax=plt.subplots(figsize=(15,9));ax.imshow(im);rows=[]
for prefix,color,height in [('999ceaf7','red',50),('3a202b7c','orange',51),('6019910a','cyan',50)]:
 feat=next(t for t in g['buildings'] if prefix in t['id']);p=feat['geometry'][0]['outer'];p=p+[p[0]]
 for z in [height,15]:
  d=np.array([[x,y,z] for x,y in p])-c;xy=np.column_stack((960.5+f*(d@r)/(d@fw),640-f*(d@u)/(d@fw)));ax.plot(xy[:,0],xy[:,1],color=color,label=prefix+f' illustrative z{z}')
 rows.append({'id':feat['id'],'illustrative_roof_z':height,'camera_depth_m':float(np.mean(d@fw))})
ax.set(xlim=(0,950),ylim=(1130,650));ax.legend(fontsize=8);fig.savefig(R/'references/credit999_photo_projection001.png',dpi=150);(R/'references/credit999_photo_visibility001.json').write_text(json.dumps({'view':'Ollie11491155 existing fitted camera; illustrativeheight50 not measuredfaçade','candidates':rows,'interpretation':'Target north block projects behind foreground Westferry frontage. No confidently separable exposed facade sufficient to reconstruct window cadence. Red lines are projection hypotheses, not traced photographic features.','source_photo_distributable':False},indent=2))
