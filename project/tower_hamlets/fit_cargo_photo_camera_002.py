from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fs=g['buildings'];W,H=1280,1920
def f(key):return next(f for f in fs if key in f['id'])
def center(key):return np.array(Polygon(f(key)['geometry'][0]['outer']).centroid.coords[0])
# Rooftop centers are approximate; OCS nearest mapped northcorner is a stronger corner correspondence.
xyz=np.array([[*center('fcc7f76d'),156],[*center('e96252ed'),199.5],[*center('12b707fc'),200],[-68.3910748,-7.4093183,210]])
pix=np.array([[286,858],[531,463],[888,656],[1133,145]])
def project(p,a):
 C=np.array([a[0],a[1],6]);yaw,pitch,roll=a[2:5];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);rr=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(rr,fw);right=rr*np.cos(roll)+up*np.sin(roll);u=-rr*np.sin(roll)+up*np.cos(roll);d=np.array(p)-C;return np.column_stack([W/2+np.exp(a[5])*(d@right)/(d@fw),H/2-np.exp(a[5])*(d@u)/(d@fw)])
sol=least_squares(lambda a:(project(xyz,a)-pix).ravel(),[-127,233,-.87,.4,0,np.log(1100)],bounds=([-300,100,-1.7,-.3,-.2,np.log(300)],[0,500,-.1,1,.2,np.log(4000)]),max_nfev=2000)
fig,ax=plt.subplots(figsize=(9,13));ax.imshow(Image.open(R/'references/pexels-tom-whyte-10391373.jpeg').resize((W,H)));ax.scatter(*pix.T,c='red');ax.scatter(*project(xyz,sol.x).T,c='yellow');candidates=[]
for f1 in fs:
 p=Polygon(f1['geometry'][0]['outer']);x,y=p.centroid.coords[0]
 if not(-170<x<0 and -30<y<130) or p.area<150:continue
 color='cyan' if '2e7e0c13' in f1['id'] else 'magenta';h=f1['height_m'];rr=f1['geometry'][0]['outer'];uv=project([[*xy,h] for xy in rr+[rr[0]]],sol.x);ax.plot(*uv.T,c=color,lw=1);cen=project([[x,y,h]],sol.x)[0];ax.text(*cen,f1['id'].split('-')[2],color=color,fontsize=8)
 if color=='cyan':
  for j,xy in enumerate(rr):
   pv=project([[*xy,0],[*xy,h]],sol.x);ax.plot(*pv.T,c=color,lw=.6);ax.text(*pv[1],str(j),color='blue',fontsize=9)
 candidates.append({'id':f1['id'],'world_centroid':[x,y,h],'projected_centroid_px':cen.tolist(),'roof_vertices_projected_px':uv.tolist()})
ax.set(xlim=(0,W),ylim=(H,0),title='Cargo cyan;othernearbyfootprints magenta;approximatecamera notsurvey');fig.savefig(R/'references/cargo_photo_projection_002.png',dpi=140);out={'parameters_xy_yaw_pitch_roll_logf':sol.x.tolist(),'fixed_camera_z_m':6,'landmarks_xyz':xyz.tolist(),'manually_observed_px':pix.tolist(),'projected_landmarks_px':project(xyz,sol.x).tolist(),'residual_rms_px':float(np.sqrt(np.mean(sol.fun**2))),'candidates':candidates,'limitations':['Approximate roofcenters notsurveyedpoints; OCSnorthcornerz210 hypothesized from mappedtier, notconfirmedphotogrammetry.','Fixedcameraheight6m andprincipalcenter1280x1920; lensdistortion/cropunknown.','Use comparativeidentityonly; do notextractexactfacadegeometry.']};(R/'references/cargo_photo_identity_002.json').write_text(json.dumps(out,indent=2));print(sol.x,'RMSE',out['residual_rms_px'])
