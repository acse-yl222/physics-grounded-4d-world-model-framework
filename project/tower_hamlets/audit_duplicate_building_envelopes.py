"""Read-only planar duplicate candidates; never automatically suppress geometry."""
from pathlib import Path
import json,hashlib
from shapely.geometry import Polygon
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';p=R/'geometry.json';g=json.loads(p.read_text())
def poly(f):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
fs=[(f,poly(f)) for f in g['buildings']];bs=[q for q in fs if q[0]['kind']=='building'];ps=[q for q in fs if q[0]['kind']=='part'];rows=[]
for b,pb in bs:
 for part,pp in ps:
  if not pb.intersects(pp):continue
  ratio=pb.symmetric_difference(pp).area/max(pb.area,pp.area)
  if ratio>.001:continue
  rows.append({'aggregate_id':b['id'],'name':b['name'],'part_id':part['id'],'part_parent':part.get('parent_id'),'symmetric_difference_fraction':ratio,'aggregate_height_m':b['height_m'],'part_min_m':part['min_height_m'],'part_max_m':part['height_m'],'needs_manual_review':True,'reason':'Near-identical XY does not alone prove duplicate occupied volume. Review vertical extent, ownership and current scene before suppression.'})
out={'geometry_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'candidates':rows,'geometry_modified':False,'criterion':'symmetric_difference / max area <=0.001; building-vs-part only'};(R/'references/duplicate_envelope_audit.json').write_text(json.dumps(out,indent=2)+'\n');print('Candidate pairs',len(rows));print('\n'.join(q['name']+' / '+q['part_id'] for q in rows))
