"""Partition overlapping mapped owners without duplicating measured upper surfaces."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union,triangulate
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';refs=R/'references';g=json.loads((R/'geometry.json').read_text());ringid='overture-building-e79bdc61-15a7-4380-93e9-67988c7fdec6';carid='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c'
def footprint(id):
 b=next(b for b in g['buildings'] if b['id']==id);return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])
ring=footprint(ringid);car=footprint(carid);v=[];faces=[]
for l in (refs/'carpark_native_roof.obj').read_text().splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:])))
 if l.startswith('f '):faces.append([int(q)-1 for q in l.split()[1:]])
v=np.array(v);original_datum=json.loads((refs/'carpark_native_roof.json').read_text())['datum_odn_m'];v[:,2]+=original_datum-4.28000021;owners=[];allpolys=[]
for owner,mode in [(carid,'remainder'),(ringid,'ring')]:
 verts=[];outfaces=[];lookup={};polys=[]
 for f in faces:
  xyz=v[f];p=Polygon(xyz[:,:2]);cut=p.difference(ring) if mode=='remainder' else p.intersection(ring)
  if cut.is_empty or cut.area<1e-7:continue
  coef=np.linalg.solve(np.column_stack([xyz[:,:2],np.ones(3)]),xyz[:,2])
  for tri in triangulate(cut):
   if tri.area<1e-7 or not cut.buffer(1e-8).covers(tri):continue
   inds=[]
   for x,y in list(tri.exterior.coords)[:-1]:
    z=float(coef@[x,y,1]);key=(round(x,8),round(y,8),round(z,8))
    if key not in lookup:lookup[key]=len(verts);verts.append([x,y,z])
    inds.append(lookup[key])
   xyz2=np.array([verts[k] for k in inds])
   if np.linalg.det([xyz2[1,:2]-xyz2[0,:2],xyz2[2,:2]-xyz2[0,:2]])<0:inds.reverse()
   outfaces.append(inds);polys.append(tri)
 name='carpark_partition_'+mode+'.obj';(refs/name).write_text(''.join('v '+' '.join(f'{a:.8f}' for a in q)+'\n' for q in verts)+''.join('f '+' '.join(str(a+1) for a in q)+'\n' for q in outfaces));shape=unary_union(polys);allpolys.append(shape);owners.append({'id':owner,'obj':name,'triangles':len(outfaces),'projected_area_m2':shape.area})
original=unary_union([Polygon(v[f,:2]) for f in faces]);overlap=allpolys[0].intersection(allpolys[1]).area;lost=original.difference(unary_union(allpolys)).area;assert overlap<1e-5 and lost<1e-5
report={'owners':owners,'mapped_ring_area_m2':ring.area,'mapped_overlap_m2':ring.intersection(car).area,'mesh_overlap_m2':overlap,'lost_observed_area_m2':lost,'datum_odn_m':4.28000021,'source_mesh_sha256':hashlib.sha256((refs/'carpark_native_roof.obj').read_bytes()).hexdigest(),'scope':'Mapped owner partition only, not proof of separate physical buildings. Ring baseline9m is unsupported; both owners share original native observation heights. No inferred ramps or facade walls.'};(refs/'carpark_partition.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
