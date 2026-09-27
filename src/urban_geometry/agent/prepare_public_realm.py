"""Prepare mapped public-space candidates; never silently accept them as geometry."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
R=authoring_path()
P=R/'references/public_realm'
g=json.loads((R/'geometry.json').read_text())
c=json.loads((R/'coordinate_contract.json').read_text())
tr=Transformer.from_crs(4326,g['crs'],always_xy=True)
origin=g['origin_projected_m']; matrix=c['source_xy_to_campus_affine']
polys=[Polygon(p['outer'],p.get('holes',[])) for b in g['buildings'] for p in b.get('geometry',[]) if len(p['outer'])>=3]
footprints=unary_union([p if p.is_valid else p.buffer(0) for p in polys])
rows=[]
for e in json.loads((P/'osm_nodes.json').read_text())['elements']:
 t=e.get('tags',{}); xy=tr.transform(e['lon'],e['lat']); x,y=xy[0]-origin[0],xy[1]-origin[1]
 pt=Point(x,y); dist=pt.distance(footprints); inside=footprints.covers(pt)
 k=t.get('natural') or t.get('highway') or t.get('barrier')
 rows.append({'id':f"node-{e['id']}",'kind':k,'tags':t,'position_wgs84':[e['lon'],e['lat']],'position_authoring_xy_m':[x,y],'position_campus_xy_m':[r[0]*x+r[1]*y+r[2] for r in matrix],'building_distance_m':round(dist,3),'inside_mapped_building':inside,'source_id':'osm-public-realm-20260909','status':'needs_inherited_dedup_ground_and_visual_review','uncertainty':'Mapped point is not survey accuracy; signal nodes may denote controlled junctions rather than poles. Tree species, crown and height remain unknown unless independently supported.'})
result={'crs':g['crs'],'origin_projected_m':origin,'source_id':'osm-public-realm-20260909','geometry_authored':False,'counts':{k:sum(r['kind']==k for r in rows) for k in sorted(set(r['kind'] for r in rows))},'inside_building_count':sum(r['inside_mapped_building'] for r in rows),'records':rows}
(P/'candidates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print({k:v for k,v in result.items() if k!='records'})
