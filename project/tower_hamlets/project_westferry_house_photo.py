"""Approximate landmark-only camera check. No source photograph exported."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());features={f['id']:f for f in g['buildings']}
def center(prefix):
 f=next(f for k,f in features.items() if prefix in k);return np.array(Polygon(f['geometry'][0]['outer']).centroid.coords[0])
# Manually read roof-top centers/tip from the actual inspected photo displayed at1921x1280.
# Centers are approximate, not homologous survey features. Fit is identity guidance only.
landmarks=[('OneCanada tip',[-46.9818538,-41.0122015,235],[880,361]),('Newfoundland roof',list(center('b0939932'))+[220],[1370,45]),('HSBC roof',list(center('e96252ed'))+[199.5],[768,456]),('Citi roof',list(center('12b707fc'))+[200],[1017,458]),('Newfoundland base approximate',list(center('b0939932'))+[7],[1375,920])]
xyz=np.array([q[1] for q in landmarks]);pix=np.array([q[2] for q in landmarks]);w,h=1921,1280
def project(points,a):
 c=a[:3];yaw,pitch,roll=a[3:6];f=a[6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);rr=right*np.cos(roll)+up*np.sin(roll);uu=up*np.cos(roll)-right*np.sin(roll);d=points-c;depth=d@fw;return np.column_stack([w/2+f*(d@rr)/depth,h/2-f*(d@uu)/depth])
def residual(a):return (project(xyz,a)-pix).ravel()
sol=least_squares(residual,[-660,45,75,0,-.1,0,1300],bounds=([-1100,-250,20,-.5,-.6,-.15,500],[-530,220,180,.5,.3,.15,4500]),max_nfev=3000)
f=features['overture-building-26bcb1ba-c69d-4699-9515-e7bf20012506'];ring=np.array(f['geometry'][0]['outer']);corners=[]
for i,xy in enumerate(ring):
 p=project(np.array([list(xy)+[44.692],list(xy)+[12]]),sol.x);corners.append({'index':i,'enu_xy':xy.tolist(),'roof_pixel_1921':p[0].tolist(),'lower_pixel_1921':p[1].tolist()})
report={'purpose':'Landmark-consistent approximate owner projection, not calibrated photogrammetry','photo_id':'pexels_ollie_11491155','working_image_dimensions_px':[w,h],'raw_image_dimensions_px':[5389,3590],'landmarks':[{'label':q[0],'xyz_scene_m':q[1],'manually_observed_pixel_1921':q[2],'fitted_pixel_1921':p.tolist()} for q,p in zip(landmarks,project(xyz,sol.x))],'camera_parameters_xyz_yaw_pitch_roll_focal':sol.x.tolist(),'residual_rms_px':float(np.sqrt(np.mean(sol.fun**2))),'owner_corners':corners,'caution':'Five approximate landmarks, including an estimated base height; strong parameter ambiguity and feature center/height errors. Used to distinguish adjoining owners, not derive dimensional facade accuracy.'}
rng=np.random.default_rng(26);trials=[]
for _ in range(40):
 xp=xyz+rng.normal(0,[3,3,2],xyz.shape);pp=pix+rng.normal(0,4,pix.shape)
 fit=least_squares(lambda a:(project(xp,a)-pp).ravel(),sol.x,bounds=([-1100,-250,20,-.5,-.6,-.15,500],[-530,220,180,.5,.3,.15,4500]),max_nfev=500)
 trials.append(project(np.column_stack([ring,np.full(len(ring),44.692)]),fit.x))
trials=np.array(trials);report['sensitivity']={'method':'40seeded perturbations: landmarkXY3m,Z2m and manuallyreadpixels4pxGaussian. This is sensitivity, not measured confidence interval.','owner_roof_pixel_p05':np.percentile(trials,5,axis=0).tolist(),'owner_roof_pixel_p95':np.percentile(trials,95,axis=0).tolist(),'max_corner_p05_p95_span_px':float(np.max(np.percentile(trials,95,axis=0)-np.percentile(trials,5,axis=0))),'unmodelled':'Lens distortion, cropped principal point, approximate rooftop centers and uncertain base datum not fully represented.'}
(R/'references/westferry_house_photo_projection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
