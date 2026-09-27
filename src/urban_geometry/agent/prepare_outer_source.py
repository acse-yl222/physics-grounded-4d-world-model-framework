"""Reprepare selected outer blocks using inherited OSM plus one bounded east-strip query."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json,hashlib,subprocess
from pathlib import Path
r=authoring_path();old=r.parents[1]/'south_kensington';stage=r/'references/outer_source'
for p in ['src','references']:(stage/p).mkdir(parents=True,exist_ok=True)
a=json.loads((old/'references/osm_raw.json').read_text());b=json.loads((r/'references/east_extension_osm.json').read_text());assert not b.get('remark')
combined={(e['type'],e['id']):e for e in a['elements']};added=[]
for e in b['elements']:
 if (e['type'],e['id']) not in combined:combined[e['type'],e['id']]=e;added.append(f"{e['type']}-{e['id']}")
a['elements']=list(combined.values());a['expansion_note']='Mixed 2026-09-08 inherited snapshot plus 2026-09-09 east-strip new identities; existing features unchanged.'
(stage/'references/osm_raw.json').write_text(json.dumps(a));(stage/'region.json').write_text('{}')
s=(old/'src/prepare.py').read_text().replace("box(-.205,51.490,-.169,51.511)","box(-.1821,51.4938,-.1680,51.5029)")
(stage/'src/prepare.py').write_text(s)
subprocess.run([str(old/'.venv/bin/python'),str(stage/'src/prepare.py')],check=True)
d=json.loads((stage/'geometry.json').read_text());existing={f['id']:f for f in json.loads((old/'geometry.json').read_text())['buildings']}
for f in d['buildings']:
 f['evidence_source_ids']=existing[f['id']]['evidence_source_ids'] if f['id'] in existing else ['osm-east-20260909']
(stage/'geometry.json').write_text(json.dumps(d,indent=2))
record={'id':'osm-east-20260909','provider':'OpenStreetMap contributors / Overpass','url':'https://overpass-api.de/api/interpreter','kind':'vector','accessed_at':'2026-09-09','capture_date':b.get('osm3s',{}).get('timestamp_osm_base'),'viewpoint':None,'license_url':'https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors, ODbL 1.0','rights_review':'Official OSM copyright page inspected 2026-09-09; derivative database retained under ODbL','geometry_derivation':'allowed','export_texture_use':False,'status':'retrieved','local_file':'east_extension_osm.json','sha256':hashlib.sha256((r/'references/east_extension_osm.json').read_bytes()).hexdigest()}
(stage/'east_source_record.json').write_text(json.dumps(record,indent=2));(stage/'merge_audit.json').write_text(json.dumps({'added_ids':added,'added_count':len(added),'old_features_preserved':True,'mixed_epoch':True},indent=2))
print('OUTER_SOURCE_READY',len(d['buildings']),len(added))
