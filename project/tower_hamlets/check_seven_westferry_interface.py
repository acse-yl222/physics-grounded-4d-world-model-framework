from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,Point,LineString
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';q=json.loads((R/'references/seven_westferry_photo_study.json').read_text());old=json.loads((R/'references/westferry_roof_fit.json').read_text());other=json.loads((R/'exports/westferry-house-massing-002/westferry_house_roof_study_002.json').read_text());edge=LineString(q['untouched_shared_edge']);dist=[]
for ob in q['objects'][1:]:dist.extend(edge.distance(Point(v[:2])) for v in ob['vertices'])
a,b=np.array(edge.coords);u=(b-a)/np.linalg.norm(b-a);n=np.array([-u[1],u[0]]);checks=[]
for f in [.05,.25,.5,.75,.95]:
 mid=a+(b-a)*f
 def height(rows,pt,shift=0):return max([r['height_scene_m']+shift for r in rows if Polygon(r['outer'],r.get('holes',[])).buffer(.001).covers(Point(pt))]+[0])
 h7=height(old['partitions'],mid+n*.05,q['roof_shift_m']);h26=height(other['partitions'],mid-n*.05);checks.append({'fraction':f,'7_height':h7,'26b_height':h26,'difference':h7-h26})
res={'shared_edge_xy':q['untouched_shared_edge'],'minimum_added_component_distance_to_edge_m':min(dist),'shared_roof_samples':checks,'neighbor_26b_modified':False,'note':'Geometric roofstep differences retained; no forcedheightmatching across separateowners. Seven has datum normalization;26b alreadyshared regionaldatum. Bodysharedwallkept;lowerfacade cutouts at leastmarginaway.'};(R/'references/seven_westferry_interface_check.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
