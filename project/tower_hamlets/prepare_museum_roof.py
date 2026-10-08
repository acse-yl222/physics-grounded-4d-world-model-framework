"""Shared-datum Museum roof candidate, clipped to separate source ownership."""
from pathlib import Path
import json,hashlib,runpy
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
s=Path(__file__).resolve().parent;r=s/'input/canary_wharf_20261007';fit=json.loads((r/'references/museum_roof_fit.json').read_text());ns=runpy.run_path(str(s/'analyze_museum_lidar.py'));x,y,z=ns['x'],ns['y'],ns['z'];g=ns['g'];origin=fit['origin_local_m'];u=(x-origin[0])*fit['long_axis'][0]+(y-origin[1])*fit['long_axis'][1];v=(x-origin[0])*fit['cross_axis'][0]+(y-origin[1])*fit['cross_axis'][1];split=fit['longitudinal_step_u_m'];pred=np.zeros(z.shape);support=ns['valid']&(abs(u-split)>1)
for side,name in [(False,'west'),(True,'east')]:
 q=(u>=split)==side;profile=fit['independent_profiles']['profiles'][name];pred[q]=np.interp(v[q],fit['cross_profile_knots_v_m'],profile['profile_odn_m']);lo,hi=profile['training_v_range_m'];support[q]&=(v[q]>=max(lo,fit['cross_profile_knots_v_m'][0]))&(v[q]<=min(hi,fit['cross_profile_knots_v_m'][-1]))
support&=abs(z-pred)<=.5
records=[]
for id,name in [(fit['building_id'],'parent'),(fit['child_id'],'part')]:
 b=next(b for b in g['buildings'] if b['id']==id);poly=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);m=support&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);verts=[];faces=[];lookup={};area=0
 for row in range(z.shape[0]-1):
  for col in range(z.shape[1]-1):
   for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
    if not all(m[i,j] for i,j in ij):continue
    tri=Polygon([(x[i,j],y[i,j]) for i,j in ij])
    if not poly.covers(tri):continue
    inds=[]
    for i,j in ij:
     if (i,j) not in lookup:lookup[i,j]=len(verts);verts.append([float(x[i,j]),float(y[i,j]),float(pred[i,j]-fit['ground_m_odn'])])
     inds.append(lookup[i,j])
    vv=np.array([verts[k] for k in inds])
    if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
    faces.append(inds);area+=tri.area
 path=r/'references'/('museum_'+name+'_roof.obj')
 with path.open('w') as f:
  f.write('# Conditional fitted partial surface, common datum, gaps unknown\n')
  for vert in verts:f.write('v '+' '.join(f'{v:.8f}' for v in vert)+'\n')
  for face in faces:f.write('f '+' '.join(str(k+1) for k in face)+'\n')
 records.append({'id':id,'obj':path.name,'vertices':len(verts),'triangles':len(faces),'projected_area_m2':area,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(r/'references/museum_roof_candidate.json').write_text(json.dumps({'objects':records,'common_ground_m_odn':fit['ground_m_odn'],'fit_sha256':hashlib.sha256((r/'references/museum_roof_fit.json').read_bytes()).hexdigest(),'scope':'Separate west/east fitted profiles within0.5m observed residual; excludes1m either side of inferred step; no profile endpoint extrapolation. All triangles clipped to owner. No walls or gap closure.'},indent=2)+'\n');print(records)
