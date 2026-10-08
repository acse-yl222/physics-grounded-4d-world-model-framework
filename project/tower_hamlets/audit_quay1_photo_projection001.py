from pathlib import Path
import json,hashlib,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('project/tower_hamlets/input/canary_wharf_20261007'); O=R/'exports/quay1-photo-projection-001';O.mkdir(exist_ok=True)
g=json.loads((R/'geometry.json').read_text())['buildings'];a=np.array(json.loads((R/'references/morgan_photo_camera_candidates.json').read_text())['parameters_xyz_yaw_pitch_roll_logf']);C=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);r=right*np.cos(roll)+up*np.sin(roll);u=-right*np.sin(roll)+up*np.cos(roll)
def project(p):
 d=np.array(p)-C;return np.column_stack([960.5+np.exp(a[6])*(d@r)/(d@fw),640-np.exp(a[6])*(d@u)/(d@fw)])
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,6));out=[]
for f in g:
 for q in f['geometry']:
  v=np.array(q['outer']);ax.plot(*v.T,color='.8',lw=.4)
for key,name,z,col in [('a6a8ac29','1 West India Quay',111,'tab:blue')]:
 f=next(f for f in g if key in f['id']);v=np.array(f['geometry'][0]['outer']);p=np.vstack([np.column_stack([v,np.zeros(len(v))]),np.column_stack([v,np.full(len(v),z)])]);uv=project(p);center=v.mean(axis=0);ax.fill(*v.T,color=col);ax.text(*center,name);ax.plot([C[0],center[0]],[C[1],center[1]],color=col,ls='--');lo=uv.min(0);hi=uv.max(0);bx.add_patch(plt.Rectangle(lo,*(hi-lo),fill=False,color=col));bx.text(*lo,name,color=col);out.append({'owner':f['id'],'name':name,'projection_z_envelope_illustrative':[0,z],'pixel_min':lo.tolist(),'pixel_max':hi.tolist()})
ax.scatter(*C[:2],c='red');ax.text(*C[:2],'Approx. Ollie camera');ax.set(xlim=(-800,300),ylim=(-550,450),aspect='equal',xlabel='ENU east (m)',ylabel='ENU north (m)');bx.add_patch(plt.Rectangle((0,0),1921,1280,fill=False,color='black'));bx.set(xlim=(-100,2400),ylim=(1400,-100),xlabel='Pixel x (1921-wide measurement)',ylabel='Pixel y');bx.set_title('Projected owner envelopes; no photo redistributed');fig.tight_layout();fig.savefig(O/'owner-camera-context.png',dpi=160)
d={'targets':out,'camera_source':'references/morgan_photo_camera_candidates.json','uncertainty':'Approximate landmark fit; previously observed ~119px independent discrepancy. Not a confidence interval; occlusion not solved by projection. Height envelopes are diagnostic bounds, not new roof measurements.','photo_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'references').glob('*.jp*g')}};(O/'projection.json').write_text(json.dumps(d,indent=2));print(json.dumps(out,indent=2))
