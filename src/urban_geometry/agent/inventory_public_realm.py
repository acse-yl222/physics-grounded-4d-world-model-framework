"""Inventory cached OSM public-realm evidence strictly within the agreed AOI."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json
from pathlib import Path
from shapely.geometry import Point,LineString,box
R=authoring_path()
bounds=json.loads((R/'region.json').read_text())['bbox_wgs84'];aoi=box(*bounds)
data=json.loads((R/'references/osm_raw.json').read_text());records=[]
for e in data['elements']:
 t=e.get('tags',{});kind=None
 if t.get('natural')=='tree':kind='tree'
 elif t.get('highway') in ('traffic_signals','crossing','street_lamp') or 'crossing' in t:kind='crossing_or_traffic_fixture'
 elif t.get('barrier') in ('bollard','kerb'):kind='street_fixture'
 elif 'highway' in t and t['highway'] not in ('proposed','construction','corridor','platform'):kind='road_or_path'
 if not kind:continue
 coords=[(p['lon'],p['lat']) for p in e.get('geometry',[]) if 'lon' in p and 'lat' in p]
 if e.get('type')=='node' and 'lon' in e:geom=Point(e['lon'],e['lat'])
 elif len(coords)>1:geom=LineString(coords)
 else:continue
 if not aoi.intersects(geom):continue
 clipped=geom.intersection(aoi)
 records.append({'id':f"{e['type']}-{e['id']}",'kind':kind,'tags':t,'geometry_wgs84':clipped.__geo_interface__,'source':'osm-20260908','status':'mapped_evidence_pending_geometry_and_ground_checks','grade_review_required':t.get('bridge')=='yes' or t.get('tunnel')=='yes' or t.get('layer','0')!='0'})
counts={k:sum(r['kind']==k for r in records) for k in ['tree','crossing_or_traffic_fixture','street_fixture','road_or_path']}
out={'scope_bbox_wgs84':bounds,'counts':counts,'source_note':'Existing cached vector source only; missing tagged points are a coverage gap, not evidence of absence. No geometry authored by inventory.','records':records}
(R/'references/public_realm_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(counts)
