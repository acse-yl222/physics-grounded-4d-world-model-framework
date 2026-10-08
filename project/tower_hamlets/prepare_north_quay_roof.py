"""Shared-datum Museum roof candidate, clipped to separate source ownership."""
from pathlib import Path
import json,hashlib,runpy
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union, triangulate
s=Path(__file__).resolve().parent;r=s/'input/canary_wharf_20261007';ns=runpy.run_path(str(s/'analyze_north_quay_lidar.py'));x,y,z=ns['x'],ns['y'],ns['z'];g=ns['g'];fit={'ground_m_odn':json.loads((r/'references/museum_interface.json').read_text())['common_ground_offset_odn_m']};pred=z
support=ns['valid']&(z-fit['ground_m_odn']>5)
group=json.loads((r/'references/north_quay_roof_group.json').read_text());owners=[]
for info in group['features']:
 b=next(b for b in g['buildings'] if b['id']==info['id']);owners.append((b['id'],b['id'].split('-')[-1],unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])))
union=unary_union([q[2] for q in owners]);inside=np.array([union.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);support &= inside
base=[]
for row in range(z.shape[0]-1):
 for col in range(z.shape[1]-1):
  for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
   if not all(support[i,j] for i,j in ij):continue
   if np.ptp([z[i,j] for i,j in ij])>1.5:continue
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
 path=r/'references'/('north_quay_'+name+'_roof.obj')
 with path.open('w') as f:
  f.write('# Conditional fitted partial surface, common datum, gaps unknown\n')
  for vert in verts:f.write('v '+' '.join(f'{v:.8f}' for v in vert)+'\n')
  for face in faces:f.write('f '+' '.join(str(k+1) for k in face)+'\n')
 records.append({'id':id,'obj':path.name,'vertices':len(verts),'triangles':len(faces),'projected_area_m2':area,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
target=unary_union([q[0] for q in base]);combined=unary_union(owner_surfaces);missing=target.difference(combined).area;overlap=owner_surfaces[0].intersection(owner_surfaces[1]).area
assert missing<1e-6 and overlap<1e-6
overlaps=[owner_surfaces[i].intersection(owner_surfaces[j]).area for i in range(len(owners)) for j in range(i)]
assert max(overlaps,default=0)<1e-6
report={'objects':records,'common_ground_m_odn':fit['ground_m_odn'],'scope':'Raw native1m DSM roof observations, height above retained museum datum>5m and triangle vertical range<=1.5m. Exact owner clipping. No inferred walls or gap closure; low structures may be excluded.','verification':{'target_area_m2':target.area,'missing_area_m2':missing,'maximum_owner_overlap_m2':max(overlaps,default=0)},'source_hashes':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']}}
(r/'references/north_quay_roof_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
