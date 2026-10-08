from pathlib import Path
import json
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/credit_photo_study_002.json').read_text());src=json.loads((R/'references/credit_envelope_study.json').read_text());ps=[(q,unary_union([Polygon([q['vertices'][i][:2] for i in f]) for f in q['roof_faces']])) for q in src['objects']];checks=[]
for v in r['exposed_wall_intervals']:
 a,b=v['edge'];length=Point(a).distance(Point(b));t=sum(v['t'])/2/length;p=Point(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t);near=[q for q,pp in ps if 'Credit_'+q['name']!=v['body'] and pp.buffer(.025).covers(p)];required=max([q['height_scene_m'] for q in near],default=0);assert v['z'][0]>=required-1e-6;checks.append({'body':v['body'],'z':v['z'],'neighbor_height_max':required,'neighbor_names':[q['name'] for q in near]})
assert {q['building_id'] for q in r['objects']}=={q['building_id'] for q in src['objects']}
(R/'exports/credit-photo-study-002/exposed_wall_check.json').write_text(json.dumps({'passed':True,'interval_count':len(checks),'checks':checks,'tolerance_m':.025,'note':'Facade-support midpoint interval check; separate existing body internal walls retained.'},indent=2)+'\n');print('All',len(checks),'intervals above adjacent roofs')
