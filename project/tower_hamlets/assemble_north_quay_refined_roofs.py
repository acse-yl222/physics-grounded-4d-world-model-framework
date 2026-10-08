"""Replace supported native patches with fitted roofs, preserving unknowns."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union,triangulate
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';refs=R/'references'
def read_obj(name):
 v=[];f=[]
 for line in (refs/name).read_text().splitlines():
  if line.startswith('v '):v.append(list(map(float,line.split()[1:])))
  if line.startswith('f '):f.append([int(q)-1 for q in line.split()[1:]])
 return np.array(v),f
native=json.loads((refs/'north_quay_roof_candidate.json').read_text())['objects'];fits={}
for file in ['museum_roof_clipped_candidate.json','north_quay_east_hip_candidate.json']:
 for q in json.loads((refs/file).read_text())['objects']:fits[q['id']]=q['obj']
fits['overture-building-67710957-baa2-4b34-9bf4-81a97bc93397']='port_east_profile_roof.obj'
rows=[]
for source in native:
 id=source['id'];v,faces=read_obj(source['obj']);nativepolys=[Polygon(v[f,:2]) for f in faces];native_union=unary_union(nativepolys)
 if id not in fits:rows.append({'id':id,'obj':source['obj'],'representation':'raw_DSM'});continue
 fv,ff=read_obj(fits[id]);fitted=unary_union([Polygon(fv[f,:2]) for f in ff]);mask=fitted;verts=[];outfaces=[];lookup={};kept=[]
 for face,tri in zip(faces,nativepolys):
  cut=tri.difference(mask)
  if cut.is_empty or cut.area<1e-9:continue
  vv=v[face];coef=np.linalg.solve(np.column_stack([vv[:,:2],np.ones(3)]),vv[:,2])
  for piece in triangulate(cut):
   if piece.area<1e-9 or not cut.buffer(1e-8).covers(piece):continue
   inds=[]
   for x,y in list(piece.exterior.coords)[:-1]:
    z=float(coef@[x,y,1]);key=(round(x,8),round(y,8),round(z,8))
    if key not in lookup:lookup[key]=len(verts);verts.append([x,y,z])
    inds.append(lookup[key])
   xyz=np.array([verts[k] for k in inds])
   if np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])[2]<0:inds.reverse()
   outfaces.append(inds);kept.append(piece)
 remainder=unary_union(kept);overlap=remainder.intersection(fitted).area;lost=native_union.difference(unary_union([remainder,fitted])).area
 assert overlap<1e-5 and lost<1e-5,(id,overlap,lost)
 name='north_quay_remainder_'+id.split('-')[-1]+'.obj'
 with (refs/name).open('w') as h:
  for vert in verts:h.write('v '+' '.join(f'{a:.8f}' for a in vert)+'\n')
  for f in outfaces:h.write('f '+' '.join(str(k+1) for k in f)+'\n')
 rows.extend([{'id':id+'__fitted','obj':fits[id],'representation':'fitted_supported_roof'},{'id':id+'__raw_remainder','obj':name,'representation':'raw_DSM_remainder','lost_native_area_m2':lost,'overlap_with_fit_m2':overlap}])
report={'objects':rows,'datum_odn_m':4.28000021,'scope':'Fitted patches replace native projected support only. Remaining native surfaces retained. Not architectural enclosure; small vertical jumps may remain at fitted/raw interfaces.','inputs':{p:hashlib.sha256((refs/p).read_bytes()).hexdigest() for p in ['north_quay_roof_candidate.json','museum_roof_clipped_candidate.json','north_quay_east_hip_candidate.json','port_east_profile_roof.json']}}
(refs/'north_quay_refined_roof_candidate.json').write_text(json.dumps(report,indent=2)+'\n');print('Objects',len(rows))
