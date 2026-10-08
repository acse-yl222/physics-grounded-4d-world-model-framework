from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Polygon,Point
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan_south-evidence-001';O.mkdir(exist_ok=True);C=Path('cache/tower_hamlets/morgan_south');C.mkdir(parents=True,exist_ok=True);d=json.load(open(R/'references/twenty_cabot_zak_camera.json'));c=np.array(d['camera_xyz']);yaw,pitch,logf=d['yaw_pitch_logf'];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);rr=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(rr,fw);W,H=1368,1824
# Existing camera fit uses 1368x1824 reference resolution.
def proj(p):
 delta=np.array(p)-c;depth=delta@fw;return np.c_[W/2+np.exp(logf)*(delta@rr)/depth,H/2-np.exp(logf)*(delta@up)/depth]
g=json.load(open(R/'geometry.json'))['buildings'];im=Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((W,H));dr=ImageDraw.Draw(im);rows=[]
for key,col,height in [('39303788','red',73.8605),('b317a51d','yellow',15),('3ae95773','cyan',33)]:
 q=next(q for q in g if key in q['id']);p=q['geometry'][0]['outer'];uv=proj([[*v,height] for v in p]);dr.line([tuple(v) for v in uv]+[tuple(uv[0])],fill=col,width=3);edges=[];poly=Polygon(p)
 for i,(a,b) in enumerate(zip(p,p[1:]+p[:1])):
  a,b=np.array(a),np.array(b);mid=(a+b)/2;v=c[:2]-mid;front=not poly.contains(Point(mid+.01*v/np.linalg.norm(v)));pix=proj([[*a,40],[*b,40],[*b,height],[*a,height]])
  if front and key=='39303788':dr.line([tuple(v) for v in pix]+[tuple(pix[0])],fill='orange',width=2);dr.text(tuple(pix.mean(axis=0)),str(i),fill='red')
  edges.append({'index':i,'a':a.tolist(),'b':b.tolist(),'front':front,'pixels':pix.tolist()})
 rows.append({'id':q['id'],'edges':edges})
im.save(C/'projection.png');(O/'morgan_south-projection.json').write_text(json.dumps({'camera':d,'owners':rows,'restriction':'Approximate two-landmark fit; diagnostic only, no exact photogrammetry.'},indent=2))
