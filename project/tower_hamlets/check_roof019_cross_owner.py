"""Conservative inter-owner oriented physical roof cluster volume overlap gate."""
from pathlib import Path
import json,itertools
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';targets=[]
for i in range(3):
 d=json.loads((R/f'exports/roof019_shard{i}/summary.json').read_text());targets.extend(t for t in d['targets']if t['status']=='built')
def corners(p):
 c=p['center'];t=p['t'];n=p['n'];w,h=p['cluster_footprint_m'];return [(c[0]+t[0]*x+n[0]*y,c[1]+t[1]*x+n[1]*y)for x in [-w/2,w/2]for y in [-h/2,h/2]]
hits=[];pairs=0
for a,b in itertools.combinations(targets,2):
 if a['owner_id']==b['owner_id']:continue
 pairs+=1;p,q=a['support'],b['support']
 if min(p['roof_z']+p['height_above_roof'],q['roof_z']+q['height_above_roof'])<=max(p['roof_z'],q['roof_z'])+1e-6:continue
 ca,cb=corners(p),corners(q);separate=False
 for axis in [p['t'],p['n'],q['t'],q['n']]:
  pa=[x*axis[0]+y*axis[1]for x,y in ca];pb=[x*axis[0]+y*axis[1]for x,y in cb]
  if min(max(pa),max(pb))<=max(min(pa),min(pb))+1e-6:separate=True;break
 if not separate:hits.append({'a':a['id'],'b':b['id'],'owners':[a['owner_id'],b['owner_id']]})
out={'passed':not hits,'built_clusters':len(targets),'cross_owner_pairs_checked':pairs,'method':'Separating axis test on oriented physical cluster bounding rectangles and vertical intervals; conservative envelope, intentional same-owner components excluded.','intersections_requiring_review':hits}
(R/'references/roof019_cross_owner_overlap.json').write_text(json.dumps(out,indent=2));print(json.dumps(out));assert not hits,'Coordinator review required before integration'
