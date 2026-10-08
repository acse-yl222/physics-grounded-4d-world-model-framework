from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());D=json.loads((R/'references/dfbe_authoring003.json').read_text());ring=D['source_geometry']['geometry'][0]['outer'];hs=next(f for f in g['buildings'] if 'e96252ed' in f['id']);pp=hs['geometry'][0]['outer'];hxy=np.mean(pp,axis=0);world=np.array([[-47,-41,235],[*hxy,199.5],[63,-149,200]]);obs=np.array([[742,230],[428,620],[1024,619]])
def project(w,a):
 C=np.array([a[0],a[1],2]);yaw,pitch,lf=a[2:];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);d=np.array(w)-C;return np.c_[684+np.exp(lf)*(d@right)/(d@fw),912-np.exp(lf)*(d@up)/(d@fw)]
f=least_squares(lambda a:(project(world,a)-obs).ravel(),[-330,0,-.15,.3,np.log(1000)],bounds=([-450,-80,-1,0,5],[-260,80,1,1,9]));a=f.x;fig,ax=plt.subplots(figsize=(9,12));ax.imshow(Image.open(R/'references/pexels-anna-rynkowska-19572396.jpeg').resize((1368,1824)))
for z,c in [(0,'yellow'),(12.45,'cyan')]:
 ps=project([[*p,z] for p in ring+[ring[0]]],a);ax.plot(*ps.T,c=c,label=str(z)+'m mappedoutline')
ax.set(xlim=(0,1368),ylim=(1824,0));ax.legend();fig.savefig(R/'references/cabot_place_anna_projection.png',dpi=150);(R/'references/cabot_place_anna_camera.json').write_text(json.dumps({'parameters_xy_yaw_pitch_logf':a.tolist(),'fixed_camera_z_m':2,'landmarks_xyz':world.tolist(),'picked_pixels':obs.tolist(),'residual_pixels':(project(world,a)-obs).tolist(),'limitations':'Three approximate roofcentroid picks, fixed2mheight; illustrative contextualcamera, notcalibratedsurvey. Foreground plan roundedwestfront andCabotSquare context supportidentity.'},indent=2))
