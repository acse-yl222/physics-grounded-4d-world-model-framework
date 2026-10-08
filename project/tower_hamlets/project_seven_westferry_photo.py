from pathlib import Path
import json,numpy as np
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());a=np.array(json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf']);W,H=1921,1280
C=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);rr=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(rr,fw);right=rr*np.cos(roll)+up*np.sin(roll);u=-rr*np.sin(roll)+up*np.cos(roll)
def project(p):
 d=np.array(p)-C;return np.column_stack([W/2+np.exp(a[6])*(d@right)/(d@fw),H/2-np.exp(a[6])*(d@u)/(d@fw)])
fig,ax=plt.subplots(figsize=(15,10));ax.imshow(Image.open(R/'references/pexels-ollie-craig-11491155.jpeg').resize((W,H)));rows=[]
for key,color in [('6019910a','cyan'),('26bcb1ba','orange')]:
 f=next(f for f in g['buildings'] if key in f['id']);ring=f['geometry'][0]['outer'];p=project([[*xy,43.5] for xy in ring])
 for i,(aa,bb) in enumerate(zip(p,np.roll(p,-1,axis=0))):
  ax.plot([aa[0],bb[0]],[aa[1],bb[1]],c=color,lw=2);ax.text(*((aa+bb)/2),str(i),color=color,fontsize=10)
 rows.append({'building_id':f['id'],'illustrative_height':43.5,'vertices_projected':p.tolist()})
ax.set(xlim=(0,850),ylim=(1150,650),title='Approximate photo-owner check: cyan7Westferry,orange26b;43.5m line is illustrative only');fig.savefig(R/'references/seven_westferry_photo_projection.png',dpi=150);(R/'references/seven_westferry_photo_projection.json').write_text(json.dumps({'owners':rows,'source_id':'pexels_ollie_11491155','limitations':'Camera approximate. Pixel heights not used to establish roof. Sourcecurve mapped aspolygon remainsfaceted; only edges3/4/5partiallysupported.'},indent=2))
