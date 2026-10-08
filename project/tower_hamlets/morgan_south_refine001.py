from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan_south-evidence-001';C=Path('cache/tower_hamlets/morgan_south');W,H=1368,1824
obs=np.array([[795,483],[1145,650],[350,1230],[1055,1210],[350,790],[1055,908]],float)
# Uncertain near endpoints tested explicitly, not assumed surveyed matches.
nearA=np.array([-281.84492285,-84.27006611]);nearB=np.array([-236.24239166,-115.81400984])
def proj(p,a):
 c=np.array([a[0],a[1],a[2]]);yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);r=np.array([np.sin(yaw),-np.cos(yaw),0]);u=np.cross(r,fw);rr=r*np.cos(roll)+u*np.sin(roll);uu=-r*np.sin(roll)+u*np.cos(roll);d=np.asarray(p)-c;dep=d@fw;return np.c_[W/2+np.exp(a[6])*(d@rr)/dep,H/2-np.exp(a[6])*(d@uu)/dep]
fits=[]
for roof in [45.003,57.70,62.63]:
 for ground in [0,3,6]:
  xyz=np.array([[-47,-41,235],[63,-149,200],[*nearA,ground],[*nearB,ground],[*nearA,roof],[*nearB,roof]])
  x0=[-385,-200,3,.546,.188,0,6.983];lo=[-600,-400,0,-.3,-.1,-.15,6.2];hi=[-300,-130,15,1.4,.7,.15,8.0]
  sol=least_squares(lambda a:(proj(xyz,a)-obs).ravel(),x0,bounds=(lo,hi),max_nfev=1500)
  pp=proj(xyz,sol.x);fits.append({'roof_hypothesis':roof,'ground_hypothesis':ground,'parameters':sol.x.tolist(),'rms_scalar_px':float(np.sqrt(np.mean((pp-obs)**2))),'landmark_residual_distances_px':np.linalg.norm(pp-obs,axis=1).tolist(),'projected':pp.tolist(),'landmarks':xyz.tolist(),'near_bounds':bool(np.any(abs(sol.x-lo)<.01)|np.any(abs(sol.x-hi)<.01))})
fits.sort(key=lambda q:q['rms_scalar_px']);best=np.array(fits[0]['parameters']);im=Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((W,H));dr=ImageDraw.Draw(im)
for i,(o,p) in enumerate(zip(obs,np.array(fits[0]['projected']))):dr.ellipse((o[0]-5,o[1]-5,o[0]+5,o[1]+5),outline='yellow',width=2);dr.line([tuple(o),tuple(p)],fill='red',width=3);dr.text(tuple(o),str(i),fill='yellow')
m=json.load(open(R/'references/morgan_photo_study_003.json'));zones=[]
for q in m['zones']:
 if not any(k in q['owner'] for k in ['39303788','3ae95773','b317a51d']):continue
 p=q['support_xy'][0]['outer'];xyz=[[v[0],v[1],q['scene_z_m']] for v in p];uv=proj(xyz,best);color='red' if '3930' in q['owner'] else ('cyan' if '3ae9' in q['owner'] else 'lime');dr.line([tuple(v) for v in uv],fill=color,width=3);zones.append({'zone':q['name'],'owner':q['owner'],'roof_projection':uv.tolist(),'alternatives':[proj(xyz,np.array(f['parameters'])).tolist() for f in fits]})
im.save(C/'refined-projection.png');out={'observed_landmarks_px':obs.tolist(),'fits':fits,'zones':zones,'limitations':['Near landmarks are hypothesized curved facade endpoints, not independently identified exact points.','Source roof heights are estimated and physical top-row identification ambiguous.','Two distant landmarks and four near endpoints constrain camera conditionally; residual is not independent accuracy.','Existing original camera used baseline3ae33/b31715 whereas retained roofs are55.383/29.687+; corrected projection uses actual authored zones.'],'decision':'No facade authorized from this diagnostic alone; inspect residual/alternate envelopes.'};(O/'morgan_south-refined-camera.json').write_text(json.dumps(out,indent=2));print([(f['roof_hypothesis'],f['ground_hypothesis'],round(f['rms_scalar_px'],2),f['near_bounds']) for f in fits])
