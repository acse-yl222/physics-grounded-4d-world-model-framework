"""Sample actual shared mapped boundaries against retained candidate triangles."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';refs=R/'references';source=refs/'north_quay_constrained_roof_candidate.json';report=json.loads(source.read_text());geometry=json.loads((R/'geometry.json').read_text());owners={};hashes={}
for row in report['objects']:
 owner=row['id'].split('__')[0];v=[];faces=[];p=refs/row['obj'];hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 for l in p.read_text().splitlines():
  if l.startswith('v '):v.append(list(map(float,l.split()[1:])))
  if l.startswith('f '):faces.append([int(q)-1 for q in l.split()[1:]])
 v=np.array(v);owners.setdefault(owner,[]).extend(v[f] for f in faces)
for id,tris in list(owners.items()):
 b=next(b for b in geometry['buildings'] if b['id']==id);footprint=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);polys=[Polygon(t[:,:2]) for t in tris];owners[id]={'triangles':tris,'tree':STRtree(polys),'polys':polys,'footprint':footprint}
def heights(owner,point):
 o=owners[owner];values=[]
 for k in o['tree'].query(point.buffer(1e-6)):
  if o['polys'][k].distance(point)>1e-6:continue
  t=o['triangles'][k];coef=np.linalg.solve(np.column_stack([t[:,:2],np.ones(3)]),t[:,2]);values.append(float(coef@[point.x,point.y,1]))
 return values
rows=[];ids=list(owners)
for i,a in enumerate(ids):
 for b in ids[i+1:]:
  line=owners[a]['footprint'].boundary.intersection(owners[b]['footprint'].boundary)
  if line.length<.1:continue
  samples=[]
  for d in np.linspace(0,line.length,max(2,int(line.length/.25)+1)):
   p=line.interpolate(d);za=heights(a,p);zb=heights(b,p)
   samples.append({'xy_m':[p.x,p.y],'a_heights_m':za,'b_heights_m':zb,'difference_m':float(np.median(za)-np.median(zb)) if za and zb else None})
  diffs=[abs(q['difference_m']) for q in samples if q['difference_m'] is not None]
  rows.append({'owners':[a,b],'shared_boundary_m':line.length,'sample_count':len(samples),'jointly_supported_samples':len(diffs),'max_abs_height_difference_m':max(diffs) if diffs else None,'samples':samples})
out={'candidate_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'geometry_sha256':hashlib.sha256((R/'geometry.json').read_bytes()).hexdigest(),'mesh_sha256':hashes,'spacing_at_most_m':.25,'scope':'Mapped owner interfaces sampled only where both candidate roofs exist. Missing support is unknown, not a filled bridge; height differences are candidates for investigation, not architectural steps.','interfaces':rows}
(refs/'north_quay_owner_interfaces.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:print({k:v for k,v in row.items() if k!='samples'})
