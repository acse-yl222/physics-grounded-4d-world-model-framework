from pathlib import Path
s=Path('project/tower_hamlets/prepare_water8_study.py').read_text().split('from shapely.geometry import box')[0].replace('36beb80b-ced9-4f18-a461-04680502f52e','ff07dd7f-5449-4cc5-9f8f-d115a85a11d4');exec(s)
from shapely.geometry import shape
from shapely.ops import unary_union
r=json.loads((R/'references/mcgraw_structure.json').read_text());objects=[];polys=[]
for reg in r['regions']:
 q=set_precision(shape(reg['geometry_uv']),.000001);polys.append(q);c0,cu,cv=reg['plane_odn_c0_cu_cv'];objects.append(make(q,[c0-180*cu+130*cv,cu,cv],'McGraw_'+reg['name']))
q=transform(uv,p);r.update({'objects':objects,'building_id':bid,'replacement_ids':[bid],'scope':'Exploratory McGraw Hill three-zone roof envelope; broad low perimeter, upper main and southern raised roof. Not calibrated as-built; central lower returns unresolved and bridged by coarse main surface. No facade or equipment reconstruction.','baseline_mesh':make(q,[70.95+datum,0,0],'McGraw_baseline'),'checks':{'source_area_m2':p.area,'partition_area_m2':sum(q.area for q in polys),'symmetric_difference_m2':q.symmetric_difference(unary_union(polys)).area},'limitations':r['limitations']+['Separate closed zone prisms have internal coincident walls. Exact source footprint retained; roof boundaries estimated from DSM.']});(R/'references/mcgraw_study.json').write_text(json.dumps(r,indent=2))
