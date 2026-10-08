from pathlib import Path
import json,sys
from shapely.geometry import box,shape
from shapely.ops import unary_union
sys.path.insert(0,str(Path('src/urban_geometry/region_authoring').resolve()));from prepare_peripheral_overture import polygon_parts,write_glb
p=Path('project/tower_hamlets/input/expanded4km_20261008');exclude=box(-499.96295166015625,-500.63592529296875,499.96295166015625,500.68548583984375);g=box(-2000,-2000,2000,2000).difference(exclude);water=unary_union([shape(x['geometry'])for x in json.load(open(p/'water/water_enu.geojson'))['features']]).difference(exclude)
for name,geom,z0,z1,color in [('outer-ground',g,-.12,-.1,[.34,.37,.35,1]),('outer-water',water,0,.01,[.12,.32,.39,1])]:
 row={'id':'site-support','name':name,'parent_id':None,'kind':'site','height_basis':'Estimated flat visual support, not terrain survey','min_height_m':z0,'height_m':z1,'boundary_crossing':False,'geometry':polygon_parts(geom)};write_glb([row],p/'outer'/f'{name}.glb',color)
(p/'outer/context-report.json').write_text(json.dumps({'ground_area_m2':g.area,'water_area_m2':water.area,'core_ground_bounds_excluded':list(exclude.bounds),'ground_z':-.1,'water_z':.01,'overlap_with_core_ground':0,'limitation':'Flat visual site surfaces, no surveyed elevation/depth'},indent=2))
