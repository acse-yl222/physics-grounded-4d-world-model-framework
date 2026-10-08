from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/photo-study-morgan-near-001';O.mkdir(exist_ok=True);C=Path('cache/tower_hamlets/photo-study-morgan-near');C.mkdir(parents=True,exist_ok=True);W,H=1368,1824
old=json.load(open(R/'exports/morgan_south-evidence-001/morgan_south-corner-sensitivity.json'))['fits'][0];x0=np.array(old['parameters']);obs=np.array([[795,483],[1145,650],[350,1230],[1055,1210],[350,790],[1055,908]],float);G=json.load(open(R/'geometry.json'))['buildings'];p=next(q for q in G if '33773280' in q['id'])['geometry'][0]['outer'];xyz=np.array([[-47,-41,235],[63,-149,200],[*p[4],3],[*p[1],3],[*p[4],45.003],[*p[1],45.003]])
def proj(p,a):
 c=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);r=np.array([np.sin(yaw),-np.cos(yaw),0]);u=np.cross(r,fw);rr=r*np.cos(roll)+u*np.sin(roll);uu=-r*np.sin(roll)+u*np.cos(roll);d=np.asarray(p)-c;dep=d@fw;return np.c_[W/2+np.exp(a[6])*(d@rr)/dep,H/2-np.exp(a[6])*(d@uu)/dep]
rows=[]
for name,point in [('b317-low-east-tip',[-312.9019459,-73.999143,29.68699979]),('3ae-upper-east-tip',[-310.3529936,-61.8165567,55.38349979])]:
 pix=np.array([335,835]);xx=np.vstack([xyz,point]);yy=np.vstack([obs,pix]);sol=least_squares(lambda a:(proj(xx,a)-yy).ravel(),x0,bounds=([-650,-400,0,-.3,-.1,-.15,6.2],[-280,-100,15,1.4,.7,.15,8]),max_nfev=2000);res=np.linalg.norm(proj(xx,sol.x)-yy,axis=1)
 # Independent leave-out prediction for new point using prior six assumed landmarks.
 prediction=proj([point],x0)[0];row={'hypothesis':name,'world':point,'observed_px':pix.tolist(),'prior_camera_prediction_px':prediction.tolist(),'prior_prediction_error_px':float(np.linalg.norm(prediction-pix)),'refitted_parameters':sol.x.tolist(),'refit_scalar_rms_px':float(np.sqrt(np.mean((proj(xx,sol.x)-yy)**2))),'point_residual_px':res.tolist(),'warning':'New corner assignment is hypothesis; combined fitting is not independent evidence.'};rows.append(row)
 im=Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((W,H));dr=ImageDraw.Draw(im)
 for i,(o,q) in enumerate(zip(yy,proj(xx,sol.x))):dr.ellipse((o[0]-5,o[1]-5,o[0]+5,o[1]+5),outline='yellow',width=2);dr.line([tuple(o),tuple(q)],fill='red',width=3);dr.text(tuple(o),str(i),fill='yellow')
 im.save(C/(name+'.png'))
out={'source_photo':'pexels_zak_36533700','photo_sha256':__import__('hashlib').sha256((R/'references/pexels-zak-h-36533700.jpeg').read_bytes()).hexdigest(),'new_landmark':'Rightmost visible low dark-glass shoulder corner around(335,835), manually selected at1368x1824','hypotheses':rows,'retained_roof_source':'references/morgan_photo_study_003.json','result':'Compare candidate models, not an unambiguous landmark identification.','no_geometry_authored':True};(O/'photo-study-near-landmark.json').write_text(json.dumps(out,indent=2));print(rows)
q=next(q for q in G if 'b317a51d' in q['id']);ring=q['geometry'][0]['outer'];camera=np.array(rows[0]['refitted_parameters']);edge=[]
for i in [11,12,13,14]:
 a,b=ring[i],ring[(i+1)%len(ring)];corners=[[a[0],a[1],18],[b[0],b[1],18],[b[0],b[1],29.68699979],[a[0],a[1],29.68699979]];edge.append({'index':i,'a':a,'b':b,'z_range_diagnostic':[18,29.68699979],'pixels':proj(corners,camera).tolist()})
(O/'photo-study-visible-edge-candidates.json').write_text(json.dumps({'owner':q['id'],'edges':edge,'provisional_best':'Mapped edge13 ending at low east tip; edge14 turns away/occluded. Edge13 is distinct from existing003 west-facing393/317 facade intervals.','caution':'Only conditional correspondence; roof tip supports identity, not exact facade bay dimensions or definitive lower visibility z.'},indent=2));print(edge)
