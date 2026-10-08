from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,Point,LineString
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if 'fe8761d9' in q['id']);ring=f['geometry'][0]['outer'];a=np.array(json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf']);C=a[:3];yaw,pitch,roll=a[3:6];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);right=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(right,fw);rr=right*np.cos(roll)+up*np.sin(roll);uu=-right*np.sin(roll)+up*np.cos(roll)
def project(xyz):
 d=np.array(xyz)-C;return np.column_stack([1921/2+np.exp(a[6])*(d@rr)/(d@fw),1280/2-np.exp(a[6])*(d@uu)/(d@fw)])
occ=[]
for z in json.loads((R/'references/morgan_massing_study_002.json').read_text())['zones']:
 for q in z['support_xy']:occ.append((z['owner'],Polygon(q['outer'],q['holes']),z['scene_z_m']))
D=json.loads((R/'references/twenty_cabot_spatial_roof002.json').read_text())
for z in D['zones']:
 for q in z['geometry']:occ.append((D['building_id'],Polygon(q['outer'],q.get('holes',[])),z['height_m']))
rows=[]
for i,pt in enumerate([*ring,list(Polygon(ring).centroid.coords[0])]):
 target=np.array([*pt,67.75]);line=LineString([C[:2],target[:2]]);blocked=[]
 for owner,p,h in occ:
  inter=line.intersection(p)
  if inter.is_empty:continue
  for q in getattr(inter,'geoms',[inter]):
   if q.geom_type!='LineString':continue
   ts=[line.project(Point(xy))/line.length for xy in q.coords];zz=[C[2]+t*(target[2]-C[2]) for t in ts]
   if min(zz)<h:blocked.append(owner)
 rows.append({'point':i,'target_xyz':target.tolist(),'pixel':project([target])[0].tolist(),'occluded_by_estimated_models':sorted(set(blocked))})
fig,ax=plt.subplots(figsize=(15,10));ax.imshow(Image.open(R/'references/pexels-ollie-craig-11491155.jpeg').resize((1921,1280)))
for height,color in [(42,'yellow'),(62.65,'cyan'),(67.75,'magenta')]:
 uv=project([[*p,height] for p in ring+[ring[0]]]);ax.plot(*uv.T,c=color,lw=1,label=str(height)+'m illustrativeoutline')
ax.set(xlim=(750,1300),ylim=(950,500),title='10SouthColonnade expected imageextent: behind25/20Cabot, notforegroundcurve');ax.legend();fig.savefig(R/'references/south_colonnade_photo_projection.png',dpi=150);rep={'source_id':'pexels_ollie_11491155','building_id':f['id'],'samples':rows,'occluded_sample_count':sum(bool(q['occluded_by_estimated_models']) for q in rows),'total_samples':len(rows),'assessment':'Roofoutline projectsbehindmiddle-ground25Cabot and20Cabot. Foregroundcurved4cf ownernotthisbuilding. Sampledlines usingestimatedmassing indicateocclusion; not surveyvisibilityproof. No reliable isolatedfacadeobservationassigned.','limitations':'Approximate5landmarkcamera, oldDSM-derivedoccluders mixedepoch; onlycorners+centertested. No completeperpixelvisibilityclaim.'};(R/'references/south_colonnade_photo_identity.json').write_text(json.dumps(rep,indent=2));print(rep['occluded_sample_count'],len(rows))
