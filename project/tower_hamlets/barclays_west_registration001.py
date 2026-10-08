from pathlib import Path
import json,numpy as np,hashlib,struct
from PIL import Image,ImageDraw
from scipy.optimize import least_squares
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/barclays-west-registration-001';O.mkdir(exist_ok=True);C=P.parent.parent/'cache/tower_hamlets/barclays_west_registration001';C.mkdir(parents=True,exist_ok=True);W,H=1280,1920
G=json.loads((R/'geometry.json').read_text())['buildings'];b=next(b for b in G if 'fcc7f76d' in b['id']);ring=np.array(b['geometry'][0]['outer']);old=json.loads((R/'references/cargo_photo_identity_002.json').read_text());a0=np.array(old['parameters_xy_yaw_pitch_roll_logf'])
def proj(p,a):
 cam=np.array([a[0],a[1],6]);yaw,pitch,roll=a[2:5];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);r=np.array([np.sin(yaw),-np.cos(yaw),0]);u=np.cross(r,fw);rr=r*np.cos(roll)+u*np.sin(roll);uu=-r*np.sin(roll)+u*np.cos(roll);d=np.asarray(p)-cam;return np.c_[W/2+np.exp(a[5])*(d@rr)/(d@fw),H/2-np.exp(a[5])*(d@uu)/(d@fw)]
im=Image.open(R/'references/pexels-tom-whyte-10391373.jpeg').resize((W,H));d=ImageDraw.Draw(im);px=proj(np.c_[ring,np.full(len(ring),156)],a0)
for i,p in enumerate(px):d.text(tuple(p),str(i),fill='red');d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill='red')
im.crop((140,800,420,1100)).resize((840,900)).save(C/'initial-corners.png')
(O/'initial-projection.json').write_text(json.dumps({'old_camera':a0.tolist(),'roof_vertices':px.tolist(),'owner':b['id'],'warning':'Initial sparse camera only; full ring roof at baseline156m, not measured roofcorners'},indent=2))
for key,name,z,box in [('e96252ed','hsbc',199.5,(350,380,710,620)),('12b707fc','citi',200,(790,590,990,760))]:
 q=next(b for b in G if key in b['id']);rr=np.array(q['geometry'][0]['outer']);pp=proj(np.c_[rr,np.full(len(rr),z)],a0);ii=Image.open(R/'references/pexels-tom-whyte-10391373.jpeg').resize((W,H));dd=ImageDraw.Draw(ii)
 for i,p in enumerate(pp):dd.text(tuple(p),str(i),fill='red')
 ii.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3)).save(C/(name+'-corners.png'))
 print(name,[(i,xy.tolist(),p.tolist()) for i,(xy,p) in enumerate(zip(rr,pp))])
# Read the retained GLB directly; no Blender process or geometry mutation.
from scipy.spatial.transform import Rotation
asset=P/'runs/canary_wharf_appearance_norwood_001/region.glb';raw=asset.read_bytes();jl=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+jl]);binstart=20+jl+8;blob=raw[binstart:];parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])}
def mat(i):
 n=doc['nodes'][i]
 if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
 else:
  m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
 return mat(parents[i])@m if i in parents else m
def access(k):
 a=doc['accessors'][k];v=doc['bufferViews'][a['bufferView']];offset=v.get('byteOffset',0)+a.get('byteOffset',0);dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];nc={'VEC3':3,'SCALAR':1}[a['type']];return np.ndarray((a['count'],nc),dtype=dt,buffer=blob,offset=offset,strides=(v.get('byteStride',np.dtype(dt).itemsize*nc),np.dtype(dt).itemsize))
rows=[]
for i,n in enumerate(doc['nodes']):
 if 'mesh' not in n or not any(k in str(n.get('extras',{})) for k in ['fcc7f76d','e96252ed','12b707fc']) and not any(k in n.get('name','') for k in ['HSBC','Citi']):continue
 vs=np.concatenate([access(p['attributes']['POSITION']) for p in doc['meshes'][n['mesh']]['primitives']]);v=(np.c_[vs,np.ones(len(vs))]@mat(i).T)[:,:3];v=np.c_[v[:,0],-v[:,2],v[:,1]];rows.append({'name':n.get('name'),'extras':n.get('extras'),'bounds_enu':[v.min(0).tolist(),v.max(0).tolist()],'unique_vertices':np.unique(np.round(v,5),axis=0).tolist()})
(O/'retained-owner-coordinates.json').write_text(json.dumps({'asset':str(asset),'sha256':hashlib.sha256(raw).hexdigest(),'meshes':rows},indent=2));print('native-derived GLB owners',[(r['name'],r['bounds_enu']) for r in rows if 'fcc7f76d' in str(r['extras'])])
hs=np.array(next(q for q in G if 'e96252ed' in q['id'])['geometry'][0]['outer']);ctrl=np.array([[*hs[11],199.5],[*hs[0],199.5],[*hs[8],199.5],[51.78263,-113.69587,200.]])
obs=np.array([[479,424],[650,497],[410,529],[890,636]],float)
lo=[-300,100,-1.7,-.3,-.2,np.log(300)];hi=[0,500,-.1,1,.2,np.log(4000)]
fit=least_squares(lambda a:(proj(ctrl,a)-obs).ravel(),a0,bounds=(lo,hi),max_nfev=3000);camera=fit.x
corners=proj(np.c_[ring,np.full(len(ring),156)],camera);point=np.array([224,840]);rank=sorted([{'index':i,'pixel':p.tolist(),'error_px':float(np.linalg.norm(p-point))} for i,p in enumerate(corners)],key=lambda x:x['error_px'])
ii=Image.open(R/'references/pexels-tom-whyte-10391373.jpeg').resize((W,H));dd=ImageDraw.Draw(ii)
for i,(p,q) in enumerate(zip(obs,proj(ctrl,camera))):dd.ellipse((p[0]-4,p[1]-4,p[0]+4,p[1]+4),outline='yellow',width=2);dd.line([tuple(p),tuple(q)],fill='red',width=2);dd.text(tuple(p),str(i),fill='yellow')
for i in [17,20,21,22,23,24,0,1]:p=corners[i];dd.text(tuple(p),str(i),fill='red')
ii.save(C/'control-fit-overlay.png');ii.crop((140,800,420,1100)).resize((840,900)).save(C/'control-fit-crop.png')
(O/'control-fit.json').write_text(json.dumps({'control_names':['HSBC NW rounded crown vertex11','HSBC SW crown vertex0','HSBC NE crown vertex8','Citi NW inset upper crown actual GLB point'],'world':ctrl.tolist(),'photo_px':obs.tolist(),'parameters':camera.tolist(),'residual_per_control_px':np.linalg.norm(proj(ctrl,camera)-obs,axis=1).tolist(),'rms_scalar_px':float(np.sqrt(np.mean(fit.fun**2))),'held_out_barclays_broad_left_top_px':point.tolist(),'ranked_mapped_corner_predictions':rank,'caution':'Manually chosen rounded corners approximate; pixel coordinates at1280x1920; fixed camera height6m. Actual Citi crown inset used rather than wrong fullfootprintcorner.'},indent=2));print('FIT',camera,'residual',np.linalg.norm(proj(ctrl,camera)-obs,axis=1),'barclays',rank[:4])
# Competing assignments and leave-one-control-out predictions. Report every test.
tests=[]
for ix in [17,20,21]:
 xx=np.vstack([ctrl,[*ring[ix],156]]);yy=np.vstack([obs,point]);sol=least_squares(lambda a:(proj(xx,a)-yy).ravel(),camera,bounds=(lo,hi),max_nfev=3000);res=np.linalg.norm(proj(xx,sol.x)-yy,axis=1);leave=[]
 for j in range(len(xx)):
  keep=np.arange(len(xx))!=j;s=least_squares(lambda a:(proj(xx[keep],a)-yy[keep]).ravel(),sol.x,bounds=(lo,hi),max_nfev=3000);leave.append(float(np.linalg.norm(proj([xx[j]],s.x)[0]-yy[j])))
 tests.append({'barclays_index':ix,'parameters':sol.x.tolist(),'residuals_px':res.tolist(),'scalar_rms_px':float(np.sqrt(np.mean(sol.fun**2))),'leave_one_out_prediction_error_px':leave})
# Existing observation choice sensitivity: all three control picks shifted +/-4px independently.
rng=np.random.default_rng(741);pred=[]
for k in range(60):
 jitter=obs+rng.uniform(-4,4,obs.shape);s=least_squares(lambda a:(proj(ctrl,a)-jitter).ravel(),camera,bounds=(lo,hi),max_nfev=1000);pred.append(proj([[*ring[21],156]],s.x)[0])
pp=np.array(pred);out={'candidate_tests':tests,'control_pick_sensitivity':{'trials':60,'jitter_each_axis_px':4,'west_corner21_prediction_min_px':pp.min(0).tolist(),'max_px':pp.max(0).tolist(),'heldout_observed_px':point.tolist(),'errors_min_median_max_px':[float(v) for v in np.quantile(np.linalg.norm(pp-point,axis=1),[0,.5,1])]},'decision':'Do not author geometry. Control-fit accuracy fails withheld target corner. Local control assignment/native silhouette or optical-model mismatch remains unresolved. No supported absolute facade height interval; photo mask remains image-only.'};(O/'ambiguity.json').write_text(json.dumps(out,indent=2));print('AMBIGUITY',out)
# Keep a cache-only visible/occluded diagnostic, no photo packaged.
ii=Image.open(R/'references/pexels-tom-whyte-10391373.jpeg');dd=ImageDraw.Draw(ii);dd.line([(710,2630),(1170,2740),(1160,2840),(650,3090),(710,2630)],fill='yellow',width=5);dd.text((715,2660),'Upper broad face: image-only support',fill='yellow');ii.crop((510,2550,1180,3330)).save(C/'visible-mask.png')
ztest=[{'z_scene':z,'projected_corner21':proj([[*ring[21],z]],camera)[0].tolist(),'error_px':float(np.linalg.norm(proj([[*ring[21],z]],camera)[0]-point))} for z in [151.71999979,156,157.13,160.28]]
(O/'datum-check.json').write_text(json.dumps({'actual_retained_body_top_scene_m':156,'source_height_basis':'OSM reported height156m; base/minheight0 is assumption, not measured ODN','held_roof_candidate_top_scene_m':157.13,'held_candidate_odn_m':161.41000021,'shared_odn_offset_m':4.28000021,'tests_not_authorized_height_changes':ztest,'conclusion':'Neither~1.13m heldplateau difference nor subtracting/adding4.28 datum offset resolves withheld corner. Do not alter roofs to force camera.'},indent=2))
(O/'report.md').write_text('''# Barclays west registration: geometry held

Exact owner fcc7f76d-8a32-4c4b-93cf-528a3bdf79e3. Current retained Norwood GLB read directly with node transforms converted to ENU; source SHA and full target/control vertices retained in retained-owner-coordinates.json. Barclays remains original footprint body z0–156m. The separate roof study is explicitly HOLD, a thin north-plateau skin near157.13scene, not a replacement body. Source156m is architectural height with assumed base0; ODN datum remains4.28000021. No roof/body changes.

Actual source crop, initial projected-corner crop and corrected-control crop inspected. Broad signed face and narrow left face remain distinct. The earlier centroid camera is unsuitable. New controls use three approximate HSBC rounded crown corners and Citi's actual inset top-crown corner from retained geometry (not its outer footprint at200m). Four controls fit with scalar RMS1.96px, but a held-out Barclays visible west/north transition misses by69–80px for plausible vertices17/20/21. Nearest numeric vertex12 is on the wrong side and is NOT selected. Joint target-inclusive fits have8–9px scalar RMS but move independent controls up to22px; leave-one-out target remains69–80px.60 deterministic control-pick perturbations ±4px leave corner21 errors68.68–94.54px. All tests preserved in ambiguity.json, no best-only filtering.

Roof-candidate versus body differs only~1.13m; separate datum perturbation test also cannot resolve correspondence. These controls are model-derived/manual landmarks, not surveyed points. Camera height6m, centered principal point and zero lens distortion are assumptions. The photograph may be cropped or perspective corrected; rounded corner selection and native silhouette can also contribute. No single cause established.

Conclusion: building identity and qualitative upper-west band/mullion hierarchy are supported, but exact west edge span and absolute visible height range are NOT established. Do not author generic arrays or transfer foreground panels. Need an additional reliable near landmark or known camera/lens calibration, or a better resolved full tower corner view, before metric placement. Existing source crop preserves diagonal foreground occlusion; lower facade/entrance unverified. Photo overlays/crops stay cache-only, not deliverable source archive. No new acquisition, Blender render, global edit or regional change.
''')
(O/'hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='hashes.json'},indent=2))
