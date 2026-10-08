from pathlib import Path
import runpy,json,collections
import numpy as np
from shapely.geometry import MultiPoint
P=Path(__file__).resolve().parent;ns=runpy.run_path(str(P/'prepare_credit_photo_study_003.py'));R=ns['R'];new=ns['ns'];zones=new['_external_zones'];collisions=[];bad=[]
for i,q in enumerate(new['rows']):
 if q['kind']=='backing':continue
 v=np.array(q['vertices']);poly=MultiPoint(v[:,:2]).convex_hull;lo=v[:,2].min();hi=v[:,2].max()
 for j,(pp,top) in enumerate(zones):
  height=min(hi,top)-max(lo,0)
  if height<=1e-8 or not poly.intersects(pp):continue
  inter=poly.intersection(pp)
  if inter.area>1e-8:collisions.append(dict(index=i,name=q['name'],owner=q['building_id'],zone=j,area_m2=inter.area,overlap_z=[float(max(lo,0)),float(min(hi,top))],volume_m3=inter.area*height,xy_bounds=list(inter.bounds)))
 edges=collections.Counter()
 for f in q['roof_faces']:
  vv=v[f];area=sum(np.linalg.norm(np.cross(vv[k]-vv[0],vv[k+1]-vv[0]))/2 for k in range(1,len(vv)-1))
  if area<1e-12:bad.append([i,'zero_area'])
  for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
 if any(n!=2 for n in edges.values()):bad.append([i,'nonmanifold'])
r=json.loads((R/'references/credit003_interface_review.json').read_text());r['remaining_ornament_3d_intersections']=collisions;r['per_ornament_geometry_failures']=bad;r['intersection_method']='Convex rectangular prism plan intersection with every actualneighborroofzone and exact zinterval overlap; all remaining ornaments incl adjacent-end edges. Tolerance1e-8m2 reported. Backingtouchingwalls preserved, not tested as union.';(R/'references/credit003_interface_review.json').write_text(json.dumps(r,indent=2)+'\n');print('COLLISIONS',json.dumps(collisions)[:5000]);print('bad',len(bad))

merged={}
for q in ns['ns0']['rows']:
 key=(q['building_id'],q['kind']);dd=merged.setdefault(key,dict(name='Credit_'+q['building_id'].split('-')[-1]+'_'+q['kind'],building_id=q['building_id'],kind=q['kind'],vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));off=len(dd['vertices']);dd['vertices']+=q['vertices'];dd['roof_faces'] +=[[i+off for i in f] for f in q['roof_faces']+q['wall_faces']+q['bottom_faces']]
old=json.loads((R/'references/credit_photo_study_002.json').read_text());assert list(merged.values())==old['objects'];r['original_replay_matches_retained002_objects']=True
(R/'references/credit003_interface_review.json').write_text(json.dumps(r,indent=2)+'\n')
