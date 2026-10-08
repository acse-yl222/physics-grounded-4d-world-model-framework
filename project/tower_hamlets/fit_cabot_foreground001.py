from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/cabot-facade-correspondence-002';O.mkdir(exist_ok=True)
old=json.loads((R/'references/cabot_place_anna_camera.json').read_text());ring=json.loads((R/'references/dfbe_authoring003.json').read_text())['source_geometry']['geometry'][0]['outer']
# Hypothesis, not accepted correspondence: existing western envelope top is photo parapet.
indices=[14,15,0,1];near=np.array([[*ring[i],12.4520015717] for i in indices]);nearobs=np.array([[340,979],[557,979],[847,981],[1090,981]])
far=np.array(old['landmarks_xyz']);farobs=np.array(old['picked_pixels']);world=np.vstack([far,near]);pixels=np.vstack([farobs,nearobs])
def project(w,a):
 C=np.array([a[0],a[1],2]);yaw,pitch,lf=a[2:];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);d=np.array(w)-C;return np.c_[684+np.exp(lf)*(d@right)/(d@fw),912-np.exp(lf)*(d@up)/(d@fw)]
fits=[]
for mode,keep in [('joint',list(range(7))),('holdout_curve', [0,1,2,3,6]),('foreground_only',[3,4,5,6])]:
 best=None
 for x in [-270,-300,-370]:
  f=least_squares(lambda a:(project(world[keep],a)-pixels[keep]).ravel(),[x,0,-.1,.2,7],bounds=([-500,-100,-1,-.2,4],[-245,100,1,1,9]),max_nfev=3000)
  if best is None or np.sum(f.fun**2)<np.sum(best.fun**2):best=f
 pp=project(world,best.x);fits.append({'mode':mode,'parameters':best.x.tolist(),'fit_indices':keep,'predicted_pixels':pp.tolist(),'residual_pixels':(pp-pixels).tolist(),'per_point_error_px':np.linalg.norm(pp-pixels,axis=1).tolist()})
# Diagnose height hypothesis without authoring: free common near elevation.
free=least_squares(lambda a:(project(np.vstack([far,np.c_[near[:,:2],np.full(4,a[5])]]),a[:5])-pixels).ravel(),[-320,0,-.1,.2,7,20],bounds=([-500,-100,-1,-.2,4,0],[-245,100,1,1,9,40]),max_nfev=3000)
free_world=np.vstack([far,np.c_[near[:,:2],np.full(4,free.x[5])]])
free_report={'parameters':free.x.tolist(),'near_height_m':float(free.x[5]),'residual_pixels':(project(free_world,free.x[:5])-pixels).tolist(),'per_point_error_px':np.linalg.norm(project(free_world,free.x[:5])-pixels,axis=1).tolist(),'warning':'Estimated diagnostic height on original XY, not actual current mesh; cannot authorize geometry change.'}
(O/'height_hypothesis.json').write_text(json.dumps(free_report,indent=2))
print('free height',free_report)
fig,axs=plt.subplots(1,3,figsize=(18,9));im=Image.open(R/'references/pexels-anna-rynkowska-19572396.jpeg').resize((1368,1824))
for ax,f in zip(axs,fits):
 ax.imshow(im);pp=np.array(f['predicted_pixels']);ax.scatter(*pixels.T,c='lime',s=25);ax.scatter(*pp.T,c='red',s=25)
 for i,(a,b) in enumerate(zip(pixels,pp)):ax.plot([a[0],b[0]],[a[1],b[1]],c='yellow');ax.text(*a,str(i),color='blue')
 ax.set(xlim=(0,1368),ylim=(1824,0),title=f['mode'])
fig.tight_layout();fig.savefig(O/'controls.png',dpi=140)
(O/'fit.json').write_text(json.dumps({'hypothesis':'West envelope top z12.452 corresponds to photographed parapet side top. NOT accepted unless independent controls and physical visibility support it.','world_points':world.tolist(),'observed_pixels':pixels.tolist(),'near_ring_indices':indices,'fits':fits,'source_photo':'pexels_anna_19572396'},indent=2))
print([(f['mode'],np.round(f['per_point_error_px'],1).tolist()) for f in fits])
