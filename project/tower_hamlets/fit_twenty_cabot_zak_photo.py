from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';D=json.loads((R/'references/twenty_cabot_spatial_roof002.json').read_text());ring=D['source_geometry']['geometry'][0]['outer'];C=np.array([-385.,-200.,3.]);world=np.array([[-47,-41,235],[63,-149,200]]);obs=np.array([[795,483],[1145,634]])
def project(w,a):
 yaw,pitch,lf=a;fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);d=np.array(w)-C;return np.c_[684+np.exp(lf)*(d@right)/(d@fw),912-np.exp(lf)*(d@up)/(d@fw)]
fit=least_squares(lambda a:(project(world,a)-obs).ravel(),[.5,.3,np.log(1200)]);a=fit.x
fig,ax=plt.subplots(figsize=(9,12));ax.imshow(Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((1368,1824)))
for z,c in [(0,'yellow'),(45,'orange'),(62.63,'cyan')]:
 pp=project([[*q,z] for q in ring+[ring[0]]],a);ax.plot(*pp.T,c=c,label=str(z)+'m mapped outline')
ax.scatter(*obs.T,c='red');ax.set(xlim=(0,1368),ylim=(1824,0));ax.legend();fig.savefig(R/'references/twenty_cabot_zak_projection.png',dpi=150)
(R/'references/twenty_cabot_zak_camera.json').write_text(json.dumps({'camera_xyz':C.tolist(),'yaw_pitch_logf':a.tolist(),'landmarks':world.tolist(),'picked_pixels':obs.tolist(),'residual_pixels':(project(world,a)-obs).tolist(),'limitations':'Illustrative2landmark fit with assumedcameraonwesternMiddleDockedge and3mheight. Insufficient landmarksforcalibratedcamera; identity requiresmappedcurvedoutline/locationcontext, notpixelmatchalone.'},indent=2))
