from pathlib import Path
import numpy as np,json,hashlib
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-frontmost-registration-003';O.mkdir(exist_ok=True);C=P.parent.parent/'cache/tower_hamlets/morgan_frontmost_registration003';C.mkdir(parents=True,exist_ok=True);G=json.loads((R/'geometry.json').read_text())['buildings'];b=next(b for b in G if 'b317a51d' in b['id']);a=np.array(b['geometry'][0]['outer'][13]);end=np.array(b['geometry'][0]['outer'][14]);u=(end-a)/np.linalg.norm(end-a);camera=np.array(json.loads((R/'exports/photo-study-morgan-near-001/photo-study-near-landmark.json').read_text())['hypotheses'][0]['refitted_parameters']);W,H=1368,1824
def project(p,c):
 fw=np.array([np.cos(c[3])*np.cos(c[4]),np.sin(c[3])*np.cos(c[4]),np.sin(c[4])]);r=np.array([np.sin(c[3]),-np.cos(c[3]),0]);v=np.cross(r,fw);rr=r*np.cos(c[5])+v*np.sin(c[5]);vv=-r*np.sin(c[5])+v*np.cos(c[5]);q=np.array(p)-c[:3];return np.c_[W/2+np.exp(c[6])*(q@rr)/(q@fw),H/2-np.exp(c[6])*(q@vv)/(q@fw)]
def inv(p,c):
 def fun(x):return project([[*(a+u*x[0]),x[1]]],c)[0]-p
 return least_squares(fun,[5,20]).x

ring=b['geometry'][0]['outer'];im=Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((1368,1824));d=ImageDraw.Draw(im);rows=[]
for i in range(len(ring)):
 pts=[[ *ring[i],z] for z in [8,21,29.68699979]];px=project(pts,camera);rows.append({'index':i,'pixels_at_z8_21_29_687':px.tolist()});d.line([tuple(p) for p in px],fill='yellow',width=2);d.text(tuple(px[-1]),str(i),fill='red')
im.save(C/'all-edge-corner-projection.png');(O/'projected-corners.json').write_text(json.dumps(rows,indent=2));print(rows)
from scipy.optimize import least_squares
p=next(q for q in G if '33773280' in q['id'])['geometry'][0]['outer'];ctrl=np.array([[-47,-41,235],[63,-149,200],[*p[4],3],[*p[1],3],[*p[4],45.003],[*p[1],45.003]]);obs=np.array([[795,483],[1145,650],[350,1230],[1055,1210],[350,790],[1055,908]],float);rows=[]
for edge in [5,7,8,13]:
 xx=np.vstack([ctrl,[*ring[edge],29.68699979],[*ring[(edge+1)%len(ring)],29.68699979]]);yy=np.vstack([obs,[181,783],[335,835]]);sol=least_squares(lambda c:(project(xx,c)-yy).ravel(),camera,bounds=([-650,-400,0,-.3,-.1,-.15,6.2],[-280,-100,15,1.4,.7,.15,8]),max_nfev=3000);rows.append({'edge':edge,'camera':sol.x.tolist(),'residuals':np.linalg.norm(project(xx,sol.x)-yy,axis=1).tolist(),'scalar_rms_px':float(np.sqrt(np.mean(sol.fun**2))),'camera_at_height_bound':bool(sol.x[2]>14.99 or sol.x[2]<.01),'label':'Competing silhouette assignment hypothesis, not accepted.'})
(O/'hypothesis-fits.json').write_text(json.dumps(rows,indent=2));print('fits',rows)
