from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/jpm25-evidence-001';C=Path('cache/tower_hamlets/jpm25');C.mkdir(parents=True,exist_ok=True);a=np.array(json.load(open(R/'references/morgan_photo_camera_candidates.json'))['parameters_xyz_yaw_pitch_roll_logf']);W,H=1921,1280
c=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);rr=right*np.cos(roll)+up*np.sin(roll);uu=-right*np.sin(roll)+up*np.cos(roll)
def proj(p):
 d=np.array(p)-c;z=d@fw;return np.c_[W/2+np.exp(a[6])*(d@rr)/z,H/2-np.exp(a[6])*(d@uu)/z]
g=json.load(open(R/'geometry.json'));im=Image.open(R/'references/pexels-ollie-craig-11491155.jpeg').resize((W,H));dr=ImageDraw.Draw(im);rows=[]
for key,col in [('25c810fb','red'),('207561e0','cyan'),('f4658f14','yellow'),('112b6cf0','magenta')]:
 q=next(q for q in g['buildings'] if key in q['id']);p=q['geometry'][0]['outer'];v=proj([[*xy,q['height_m']] for xy in p]);dr.line([tuple(z) for z in v]+[tuple(v[0])],fill=col,width=3);dr.text(tuple(v.mean(axis=0)),key,fill=col);rows.append({'id':q['id'],'roof_pixels':v.tolist(),'baseline_height':q['height_m']})
im.save(C/'jpm25-projection.png');(O/'jpm25-photo-projection.json').write_text(json.dumps({'camera':a.tolist(),'owners':rows,'uncertainty':'Existing approximate camera ~119px cross-landmark uncertainty, not pixel-accurate measurement. Photo stays cache/reference only.'},indent=2));print(rows[0])
