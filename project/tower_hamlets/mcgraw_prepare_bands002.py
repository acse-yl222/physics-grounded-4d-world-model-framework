from pathlib import Path
s=Path('project/tower_hamlets/prepare_water8_study.py').read_text().split('from shapely.geometry import box')[0].replace('36beb80b-ced9-4f18-a461-04680502f52e','ff07dd7f-5449-4cc5-9f8f-d115a85a11d4');exec(s)
from shapely.geometry import shape,box
from shapely.ops import unary_union
r=json.loads((R/'references/mcgraw_study.json').read_text());r['objects']=[];bands=unary_union([box(171,c-1,192,c+1) for c in [-124.8,-131.1]])
for reg in r['regions']:
 q=shape(reg['geometry_uv']);q=q.difference(bands) if reg['name']=='upper_main' else q;c0,cu,cv=reg['plane_odn_c0_cu_cv'];r['objects'].append(make(set_precision(q,.000001),[c0-180*cu+130*cv,cu,cv],'McGraw002_'+reg['name']))
for i,q in enumerate(bands.geoms):r['objects'].append(make(q,[71.95,0,0],f'McGraw002_low_band_{i}'))
r['scope']='Exploratory closed stepped surface comparison002: two geometric central low bands at71.95ODN,2m wide and21m long; no holes/equipment asserted. Other central and southern low returns remain unresolved. Not current as-built verified.';r['limitations']+=['Band widths/boundaries estimated and tested ±0.5m. Vertical transition walls are a stepped-surface hypothesis, not observed facade geometry.','Two bands not connected to outside ledge in DSM threshold connectivity. Southern low band remains unmodeled due stronger boundary sensitivity.'];r['band_evidence']='references/mcgraw_low_bands.json';(R/'references/mcgraw_study002.json').write_text(json.dumps(r,indent=2))
