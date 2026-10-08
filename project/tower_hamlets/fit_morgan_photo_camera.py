from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from shapely.geometry import Polygon
from shapely.ops import unary_union
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'; g=json.loads((R/'geometry.json').read_text()); fs=g['buildings']; W,H=1921,1280
poly=lambda f:unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
def center(key):return np.array(poly(next(f for f in fs if key in f['id'])).centroid.coords[0])
pts=np.array([[*center('b0939932'),220],[*center('b0939932'),0],[*center('0c84e402'),235],[*center('e96252ed'),199.5],[*center('12b707fc'),200]])
obs=np.array([[1370,47],[1380,923],[880,360],[768,459],[1017,460]])
# World forward east-ish. Right vector from horizontal view azimuth; roll allowed.
def project(p,a):
 C=a[:3];yaw,pitch,roll=a[3:6];f=np.exp(a[6]);fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);r=right*np.cos(roll)+up*np.sin(roll);u=-right*np.sin(roll)+up*np.cos(roll);d=np.asarray(p)-C;z=d@fw;return np.column_stack([W/2+f*(d@r)/z,H/2-f*(d@u)/z])
best=None
for cy in [-200,0,200,400]:
 a=np.array([-850,cy,90,0,-.03,0,np.log(1500)])
 res=least_squares(lambda a:(project(pts,a)-obs).ravel(),a,max_nfev=3000,bounds=([-3000,-2000,5,-1,-.6,-.1,np.log(200)],[-460,2000,400,1,.6,.1,np.log(10000)]))
 if best is None or np.linalg.norm(res.fun)<np.linalg.norm(best.fun):best=res
a=best.x; print(a,'residual',best.fun)
fig,ax=plt.subplots(figsize=(15,10));ax.imshow(Image.open(R/'references/pexels-ollie-craig-11491155.jpeg').resize((W,H)))
m=json.loads((R/'references/morgan_massing_study_002.json').read_text());polylines=[]
for i,o in enumerate(m['objects']):
 v=np.array(o['vertices']);z=v[:,2].max();p=Polygon(v[v[:,2]==z,:2]).convex_hull # drawing uses actual faces edges below
 for face in o['roof_faces']:
  q=v[face]
  if np.allclose(q[:,2],z):
   qq=project(np.vstack([q,q[0]]),a);ax.plot(*qq.T,c='cyan',lw=.7)
 cen=v.mean(axis=0);cen[2]=z;uv=project([cen],a)[0];ax.text(*uv,str(i),color='cyan',fontsize=8)
 polylines.append({'object':o['name'],'owner':o['building_id'],'roof_center_pixel':uv.tolist()})
f=next(f for f in fs if '33773280' in f['id']);p=poly(f)
for z in [0,35,50]:
 v=np.array([[x,y,z] for x,y in p.exterior.coords]);uv=project(v,a);ax.plot(*uv.T,c='orange',lw=1)
uv=project(pts,a);ax.scatter(*obs.T,c='red',s=16);ax.scatter(*uv.T,c='yellow',s=8);ax.set(xlim=(0,W),ylim=(H,0),title='Approximate landmark camera: cyan 25 Cabot estimated roofs; orange 20 Cabot plan at illustrative 0/35/50m');fig.tight_layout();fig.savefig(R/'references/morgan_camera_projection.png',dpi=160)
d={'source_id':'pexels_ollie_11491155','image_measurement_resolution':[W,H],'parameters_xyz_yaw_pitch_roll_logf':a.tolist(),'landmark_world_xyz':pts.tolist(),'landmark_observed_pixel':obs.tolist(),'landmark_projected_pixel':uv.tolist(),'rms_pixel':float(np.sqrt(np.mean(best.fun**2))),'objects':polylines,'limitations':['Approximate manually selected roof centers; perspective roof-center displacement and lens distortion not calibrated.','Camera estimated with5landmarks/10scalar constraints and7parameters; lowresidual not independent validation.','25Cabot roof levels are estimated mixed-date DSM envelope.20Cabot illustrative levels only.']};(R/'references/morgan_photo_camera.json').write_text(json.dumps(d,indent=2))
