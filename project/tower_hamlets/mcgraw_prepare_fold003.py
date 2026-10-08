from pathlib import Path
s=Path('project/tower_hamlets/prepare_water8_study.py').read_text().split('from shapely.geometry import box')[0].replace('36beb80b-ced9-4f18-a461-04680502f52e','ff07dd7f-5449-4cc5-9f8f-d115a85a11d4');exec(s)
from shapely.geometry import shape,box
from shapely.ops import unary_union
r=json.loads((R/'references/mcgraw_study.json').read_text());r['objects']=[];centers=[-124.8,-131.1];domains=unary_union([box(171,c-2.5,192,c+2.5) for c in centers]);main=next(a for a in r['regions'] if a['name']=='upper_main');c0,cu,cv=main['plane_odn_c0_cu_cv'];C=c0-180*cu+130*cv;depth=c0-71.95
for reg in r['regions']:
 q=shape(reg['geometry_uv']);q=q.difference(domains) if reg['name']=='upper_main' else q;a,b,c=reg['plane_odn_c0_cu_cv'];r['objects'].append(make(set_precision(q,.000001),[a-180*b+130*c,b,c],'McGraw003_'+reg['name']))
for i,center in enumerate(centers):
 # additive linear depression preserves original upper plane at both transition ends
 for j,(lo,hi,a,b) in enumerate([(center-2.5,center-.5,-(center-2.5)/2,.5),(center-.5,center+.5,1,0),(center+.5,center+2.5,(center+2.5)/2,-.5)]):
  r['objects'].append(make(box(171,lo,192,hi),[C-depth*a,cu,cv-depth*b],f'McGraw003_valley{i}_panel{j}'))
r['scope']='Exploratory continuous transverse folded roof comparison003: two1m low-bottom bands with2m linear ramp each side,21m along-u extent. No functional roof identity. Southern band unresolved. Endwalls remain unvalidated, no outsideledgeconnection asserted.';r['limitations']+=['Repeated fold section estimated from native1m profiles; ±0.5m boundary sensitivity retained. Not surveyed geometry.','Along-u ends remain abruptestimated transitions; central south band and other high/low returns unmodeled.'];r['profile_parameters']={'centers_v':centers,'u_interval':[171,192],'bottom_width_m':1,'each_ramp_width_m':2,'nominal_bottom_odn':71.95,'depth_m':depth};(R/'references/mcgraw_study003.json').write_text(json.dumps(r,indent=2))
