"""Make an explicitly estimated one-triangle transition to unchanged native roof edges."""
from pathlib import Path
import json, hashlib
import numpy as np
from shapely.geometry import Polygon, MultiPoint, Point
from shapely.ops import triangulate, unary_union
from shapely.strtree import STRtree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references'
def obj(name):
 v=[];f=[]
 for l in (R/name).read_text().splitlines():
  if l.startswith('v '):v.append(list(map(float,l.split()[1:])))
  if l.startswith('f '):f.append([int(q)-1 for q in l.split()[1:]])
 return np.array(v),f
report=json.loads((R/'north_quay_expanded_roof_candidate.json').read_text());audit=json.loads((R/'north_quay_expanded_fit_seams.json').read_text());checks=[]
for row in report['objects']:
 if row['representation']!='fitted_supported_roof':continue
 source=row['obj'];v,faces=obj(source);owner=row['id'].removesuffix('__fitted');samples=next(q['samples'] for q in audit['owners'] if q['id']==owner)
 pts=np.array([q['position_enu_m'] for q in samples]);tree=STRtree([Point(p[:2]) for p in pts]);lookup={};outv=[];outf=[];changes=[];before=[];after=[]
 for f in faces:
  xyz=v[f];poly=Polygon(xyz[:,:2]);before.append(poly);coef=np.linalg.solve(np.column_stack([xyz[:,:2],np.ones(3)]),xyz[:,2]);inds=[int(k) for k in tree.query(poly.buffer(1e-7)) if poly.distance(Point(pts[k,:2]))<1e-7]
  values={tuple(np.round(p[:2],7)):float(p[2]) for p in pts[inds]};xy=list(xyz[:,:2])+[p[:2] for p in pts[inds]]
  xy=[pts[np.argmin(np.linalg.norm(pts[:,:2]-a,axis=1)),:2] if np.min(np.linalg.norm(pts[:,:2]-a,axis=1))<1e-6 else a for a in xy]
  for t in triangulate(MultiPoint(np.round(xy,7))):
   if t.area<1e-7 or not poly.buffer(1e-7).covers(t):continue
   face=[]
   for x,y in list(t.exterior.coords)[:-1]:
    old=float(coef@[x,y,1]);dist=np.linalg.norm(pts[:,:2]-[x,y],axis=1);nearest=int(np.argmin(dist));z=float(pts[nearest,2]) if dist[nearest]<1e-6 else old;changes.append(abs(z-old));key=(round(x,7),round(y,7),round(z,7))
    if key not in lookup:lookup[key]=len(outv);outv.append([x,y,z])
    face.append(lookup[key])
   a=np.array([outv[k] for k in face]);
   if np.cross(a[1]-a[0],a[2]-a[0])[2]<0:face.reverse()
   outf.append(face);after.append(t)
 shape=unary_union(after);delta=unary_union(before).symmetric_difference(shape).area;assert delta<1e-5
 name='north_quay_expanded_constrained_'+owner.split('-')[-1]+'.obj'
 with (R/name).open('w') as h:
  for p in outv:h.write('v '+' '.join(f'{x:.8f}' for x in p)+'\n')
  for f in outf:h.write('f '+' '.join(str(k+1) for k in f)+'\n')
 row['obj']=name;row['boundary_treatment']='Estimated transition within boundary triangles; native boundary heights fixed, interior fit vertices unchanged.'
 checks.append({'id':owner,'source_obj':source,'source_sha256':hashlib.sha256((R/source).read_bytes()).hexdigest(),'triangle_count':len(outf),'projected_area_change_m2':delta,'maximum_boundary_adjustment_m':max(changes)})
report['scope']='Partial roof candidates with estimated boundary-triangle transitions to unchanged raw DSM. This is continuity repair, not improved measured accuracy or an architectural enclosure.';report['boundary_checks']=checks
(R/'north_quay_expanded_constrained_roof_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks,indent=2))
