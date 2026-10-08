"""Shared-datum Museum roof candidate, clipped to separate source ownership."""
from pathlib import Path
import json,hashlib,runpy
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union, triangulate
s=Path(__file__).resolve().parent;r=s/'input/canary_wharf_20261007';fit=json.loads((r/'references/museum_roof_fit.json').read_text());ns=runpy.run_path(str(s/'analyze_museum_lidar.py'));x,y,z=ns['x'],ns['y'],ns['z'];g=ns['g'];origin=fit['origin_local_m'];u=(x-origin[0])*fit['long_axis'][0]+(y-origin[1])*fit['long_axis'][1];v=(x-origin[0])*fit['cross_axis'][0]+(y-origin[1])*fit['cross_axis'][1];split=fit['longitudinal_step_u_m'];pred=np.zeros(z.shape);support=ns['valid']&(abs(u-split)>1)
for side,name in [(False,'west'),(True,'east')]:
 q=(u>=split)==side;profile=fit['independent_profiles']['profiles'][name];pred[q]=np.interp(v[q],fit['cross_profile_knots_v_m'],profile['profile_odn_m']);lo,hi=profile['training_v_range_m'];support[q]&=(v[q]>=max(lo,fit['cross_profile_knots_v_m'][0]))&(v[q]<=min(hi,fit['cross_profile_knots_v_m'][-1]))
support&=abs(z-pred)<=.5
owners=[]
for id,name in [(fit['building_id'],'parent'),(fit['child_id'],'part')]:
 b=next(b for b in g['buildings'] if b['id']==id);owners.append((id,name,unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])))
union=unary_union([q[2] for q in owners]);inside=np.array([union.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);support &= inside
base=[]
for row in range(z.shape[0]-1):
 for col in range(z.shape[1]-1):
  for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
   if not all(support[i,j] for i,j in ij):continue
   xy=np.array([(x[i,j],y[i,j]) for i,j in ij]);tri=Polygon(xy)
   if not union.covers(tri):continue
   coef=np.linalg.solve(np.column_stack([xy,np.ones(3)]),np.array([pred[i,j]-fit['ground_m_odn'] for i,j in ij]));base.append((tri,coef))
records=[];owner_surfaces=[];seam_vertices=[]
shared=owners[0][2].boundary.intersection(owners[1][2].boundary)
for id,name,poly in owners:
 verts=[];faces=[];lookup={};area=0;surfaces=[]
 for tri,coef in base:
  clipped=tri.intersection(poly)
  if clipped.is_empty or clipped.area<1e-10:continue
  for piece in triangulate(clipped):
   if not clipped.buffer(1e-9).covers(piece) or piece.area<1e-10:continue
   inds=[]
   for a,b in list(piece.exterior.coords)[:-1]:
    key=(round(a,9),round(b,9));height=float(np.dot([a,b,1],coef))
    if key not in lookup:lookup[key]=len(verts);verts.append([a,b,height])
    else:assert abs(verts[lookup[key]][2]-height)<1e-7
    inds.append(lookup[key])
   vv=np.array([verts[k] for k in inds])
   if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
   faces.append(inds);area+=piece.area;surfaces.append(piece)
 owner_surfaces.append(unary_union(surfaces));seam_vertices.append([v for v in verts if shared.distance(Point(v[:2]))<1e-7])
 path=r/'references'/('museum_'+name+'_roof_clipped.obj')
 with path.open('w') as f:
  f.write('# Conditional fitted partial surface, common datum, gaps unknown\n')
  for vert in verts:f.write('v '+' '.join(f'{v:.8f}' for v in vert)+'\n')
  for face in faces:f.write('f '+' '.join(str(k+1) for k in face)+'\n')
 records.append({'id':id,'obj':path.name,'vertices':len(verts),'triangles':len(faces),'projected_area_m2':area,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
target=unary_union([q[0] for q in base]);combined=unary_union(owner_surfaces);missing=target.difference(combined).area;overlap=owner_surfaces[0].intersection(owner_surfaces[1]).area
assert missing<1e-6 and overlap<1e-6
errors=[]
for vert in seam_vertices[0]:
 matches=[v for v in seam_vertices[1] if np.linalg.norm(np.array(v[:2])-vert[:2])<1e-7]
 assert matches, 'Unmatched internal seam vertex'
 errors.append(min(abs(v[2]-vert[2]) for v in matches))
assert errors and max(errors)<1e-7
report={'objects':records,'common_ground_m_odn':fit['ground_m_odn'],'scope':'Same supported union triangles clipped at exact owner boundary with barycentric heights; no filling of unsupported areas or step transition.','verification':{'target_area_m2':target.area,'missing_area_m2':missing,'owner_overlap_m2':overlap,'matched_seam_vertices':len(errors),'maximum_seam_height_error_m':max(errors)},'fit_sha256':hashlib.sha256((r/'references/museum_roof_fit.json').read_bytes()).hexdigest()}
(r/'references/museum_roof_clipped_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
