from pathlib import Path
import numpy as np,json,hashlib
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-facade-registration-002';O.mkdir(exist_ok=True);C=P.parent.parent/'cache/tower_hamlets/morgan_facade_registration002';C.mkdir(parents=True,exist_ok=True);G=json.loads((R/'geometry.json').read_text())['buildings'];b=next(b for b in G if 'b317a51d' in b['id']);a=np.array(b['geometry'][0]['outer'][13]);end=np.array(b['geometry'][0]['outer'][14]);u=(end-a)/np.linalg.norm(end-a);camera=np.array(json.loads((R/'exports/photo-study-morgan-near-001/photo-study-near-landmark.json').read_text())['hypotheses'][0]['refitted_parameters']);W,H=1368,1824
def project(p,c):
 fw=np.array([np.cos(c[3])*np.cos(c[4]),np.sin(c[3])*np.cos(c[4]),np.sin(c[4])]);r=np.array([np.sin(c[3]),-np.cos(c[3]),0]);v=np.cross(r,fw);rr=r*np.cos(c[5])+v*np.sin(c[5]);vv=-r*np.sin(c[5])+v*np.cos(c[5]);q=np.array(p)-c[:3];return np.c_[W/2+np.exp(c[6])*(q@rr)/(q@fw),H/2-np.exp(c[6])*(q@vv)/(q@fw)]
def inv(p,c):
 def fun(x):return project([[*(a+u*x[0]),x[1]]],c)[0]-p
 return least_squares(fun,[5,20]).x
# Explicit manually inspected original-resolution feature corners in cached crop, offset(300,1650).
features={'upper_left':[[114,108],[263,154],[239,415],[85,377]],'upper_right':[[291,170],[424,211],[402,456],[268,421]],'spandrel_left':[[101,220],[255,264],[248,313],[97,275]],'spandrel_right':[[280,274],[417,307],[412,361],[276,330]],'pale_windows_left':[[80,463],[222,498],[211,650],[63,613]],'pale_windows_right':[[261,510],[392,548],[378,668],[246,635]],'arch_outer_left':[[53,680],[210,701],[188,895],[34,879]],'arch_outer_right':[[244,704],[376,733],[360,907],[230,890]]}
rows={}
for k,pp in features.items():
 pix=(np.array(pp)+[300,1650])*np.array([1368/3000,1824/4000]);sz=np.array([inv(p,camera) for p in pix]);box=[float(sz[[0,3],0].mean()),float(sz[[1,2],0].mean()),float(sz[[2,3],1].mean()),float(sz[[0,1],1].mean())];rows[k]={'picked_original_px':(np.array(pp)+[300,1650]).tolist(),'inverse_corner_sz_m':sz.tolist(),'proposed_box_s0_s1_z0_z1_m':box}
# Keep roof/camera landmark model unchanged; quantify sensitivity to image-control perturbation.
p=next(q for q in G if '33773280' in q['id'])['geometry'][0]['outer'];xyz=np.array([[-47,-41,235],[63,-149,200],[*p[4],3],[*p[1],3],[*p[4],45.003],[*p[1],45.003],[*end,29.68699979]]);obs=np.array([[795,483],[1145,650],[350,1230],[1055,1210],[350,790],[1055,908],[335,835]],float);rng=np.random.default_rng(282);samples={k:[] for k in rows};cams=[]
for t in range(60):
 yy=obs+rng.uniform(-8,8,obs.shape);s=least_squares(lambda c:(project(xyz,c)-yy).ravel(),camera,bounds=([-650,-400,0,-.3,-.1,-.15,6.2],[-280,-100,15,1.4,.7,.15,8]),max_nfev=1500);cams.append(s.x)
 for k,r in rows.items():
  pix=np.array(r['picked_original_px'])*[1368/3000,1824/4000]+rng.uniform(-2,2,(4,2));sz=np.array([inv(q,s.x) for q in pix]);samples[k].append([sz[[0,3],0].mean(),sz[[1,2],0].mean(),sz[[2,3],1].mean(),sz[[0,1],1].mean()])
for k in rows:rows[k]['sensitivity_p05_p95_s0_s1_z0_z1_m']=np.quantile(samples[k],[.05,.95],axis=0).tolist()
# Overlay projected before and proposed rectangles; photos remain cache-only.
for mode in ['before','proposed']:
 im=Image.open(R/'references/pexels-zak-h-36533700.jpeg');d=ImageDraw.Draw(im)
 boxes={'old_upper_left':[.65,5.05,19,28.15],'old_upper_right':[5.8,10.25,19,28.15]} if mode=='before' else {k:r['proposed_box_s0_s1_z0_z1_m'] for k,r in rows.items()}
 for k,(s0,s1,z0,z1) in boxes.items():
  pts=[[*(a+u*s),z] for s,z in [(s0,z1),(s1,z1),(s1,z0),(s0,z0),(s0,z1)]];px=project(pts,camera)/[1368/3000,1824/4000];d.line([tuple(v) for v in px],fill='red' if mode=='before' else 'yellow',width=4);d.text(tuple(px[0]),k,fill='red')
 im.crop((300,1650,790,2630)).save(C/(mode+'-overlay.png'))
out={'owner':b['id'],'edge13':[a.tolist(),end.tolist()],'roof_top_preserved_scene_m':29.68699979,'camera_preserved':camera.tolist(),'source_photo_sha256':hashlib.sha256((R/'references/pexels-zak-h-36533700.jpeg').read_bytes()).hexdigest(),'source_crop_original_px':[300,1650,790,2630],'original_upper_boxes':{'left':[.65,5.05,19,28.15],'right':[5.8,10.25,19,28.15]},'proposed_features':rows,'uncertainty':'Conditional inversion on mapped plane.60 camera fits jitter7landmarks by±8workingpx andfeaturepicks±2px; percentile ranges are sensitivity, NOT confidence intervals. Systematic camera/model/pointassignment errors may be larger. Existing fit RMS18.33px,max43.75px.','decision':'Before/after proposal only. Joint upper/pale/arch placement, no roof/body/camera adjustment, no entrance inference. Await review before geometry.'};(O/'proposal.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:r['proposed_box_s0_s1_z0_z1_m'] for k,r in rows.items()},indent=2))
# Joint shared horizontal levels across each pair, retaining independently picked s spans.
levels={};joint={}
for typ in ['upper','spandrel','pale_windows','arch_outer']:
 l=rows[typ+'_left']['proposed_box_s0_s1_z0_z1_m'];r=rows[typ+'_right']['proposed_box_s0_s1_z0_z1_m'];z0=(l[2]+r[2])/2;z1=(l[3]+r[3])/2;levels[typ]=[z0,z1]
 for side in ['left','right']:
  k=typ+'_'+side;s0,s1=rows[k]['proposed_box_s0_s1_z0_z1_m'][:2];px=project([[*(a+u*s),z] for s,z in [(s0,z1),(s1,z1),(s1,z0),(s0,z0)]],camera);observed=np.array(rows[k]['picked_original_px'])*[1368/3000,1824/4000];joint[k]={'raw_s_range':[s0,s1],'joint_z_range':[z0,z1],'fit_residual_per_corner_working_px':np.linalg.norm(px-observed,axis=1).tolist(),'within_mapped_edge':bool(s0>=0 and s1<=np.linalg.norm(end-a))}
length=float(np.linalg.norm(end-a));out['joint_level_proposal']=joint;out['mapped_edge_length_m']=length;out['edge_constraint']='Raw right arch extends0.074m past10.932m edge; camera sensitivity exceeds this. Before geometry choose explicit bounded setback/clip withinowner, not footprint extension. No right return included.';(O/'proposal.json').write_text(json.dumps(out,indent=2))
im=Image.open(R/'references/pexels-zak-h-36533700.jpeg');dr=ImageDraw.Draw(im)
for k,v in joint.items():
 s0,s1=v['raw_s_range'];z0,z1=v['joint_z_range'];px=project([[*(a+u*s),z] for s,z in [(s0,z1),(s1,z1),(s1,z0),(s0,z0),(s0,z1)]],camera)/[1368/3000,1824/4000];dr.line([tuple(p) for p in px],fill='yellow',width=4);dr.text(tuple(px[0]),k,fill='red')
im.crop((300,1650,790,2630)).save(C/'joint-level-overlay.png')
(O/'report.md').write_text('''# Morgan facade registration002 — proposal, no authored geometry

Owner b317a51d-586a-3b78-9ee5-b685a2db94a0, edge13 length10.932m. Existing candidate preserved. Fixed previous conditional camera and exact roof29.687m/body footprint; no height or camera alteration to force facade fit. Explicit original-resolution source picks jointly cover upper brown bays, spandrels, pale narrow windows and middle arches. Actual full crop, old overlay and proposed overlay inspected.

| Zone | Old z scene m | Proposed shared z scene m |
|---|---|---|
| Upper glass |19–28.15|21.54–28.61|
| Upper spandrel |22.4–24.2|24.19–25.67|
| Pale narrow-window tier |Not authored|15.59–19.18|
| Mid-level arch outer extent |Not authored|9.18–13.96|

Old upper glass starts roughly2.5m too low under the same camera, visually intersecting the pale tier. Corrected interval is shorter and shifted upward; upper roof and original body remain untouched. This diagnosis reconciles all visible tiers instead of avoiding the missing pale tier. Measured image points, raw s ranges, common z proposals and per-corner projection residuals are in proposal.json.

Raw s spans upper left0.34–5.07/right6.04–10.88, pale left0.62–5.03/right6.21–10.86, arches left0.70–5.29/right6.48–11.01m. Last raw extent exceeds mappededge by0.074m; do not extend footprint or transfer onto return. An explicit conservative bound within10.932m must be reviewed before authoring.

60 deterministic camera sensitivity trials perturb all7existing landmark picks ±8pixels at1368×1824 and feature picks ±2pixels. Typical z sensitivity is~±0.5m and s~±0.7m. Full5–95percentile ranges retained; these are NOT confidence intervals and omit possible systematic model/optical errors. Existing camera RMS18.33px/max43.75px remains material. The strong owner/roof correspondence does not certify metric facade dimensions. Upper apparent pane fractions and individual pale-tier transoms still require detailed counting at source resolution during authoring.

Proposed next geometry: corrected upper bay package plus pale narrow-window groups/transoms and two real shallow segmental arch reveals/dark panels, additive relative-depth construction with estimated depths. Lowest entrances behind railing/plants and right return remain excluded. No claim about dark arch-grid function. Current candidate/source/native untouched; no global edits. Original photo/crops/overlays remain cache-only.
''');(O/'hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='hashes.json'},indent=2))
