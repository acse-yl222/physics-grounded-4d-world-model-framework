"""Retain a reviewable local regional study; no publication or default-view change."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import shutil
import zipfile

S = Path(__file__).resolve().parent
R = S/'input/canary_wharf_20261007'
O = R/'exports/appearance-citi-neighbor-001'
D = S/'runs/canary_wharf_appearance_citi_neighbor_001'
def read(p): return json.loads(p.read_text())
def write(p, v): p.write_text(json.dumps(v, indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
v = read(O/'verification.json')
assert v['native_reopened'] and v['independent_glb_verified']
assert read(O/'visual_review.json')['inspected']
for name, digest in v['source_blends'].items():
    assert sha(R/name) == digest
D.mkdir(exist_ok=False)
for p in O.iterdir():
    if p.is_file(): shutil.copy2(p, D/p.name)
shutil.copy2(R/'references/ATTRIBUTION.md', D/'ATTRIBUTION.md')
shutil.copy2(R/'exports/citi-neighbor-interface-independent-review/report.json', D/'interface_independent_review.json')
with zipfile.ZipFile(D/'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ['assemble_citi_neighbor_scene.py','retain_citi_neighbor_scene.py','render_citi_neighbor_interface.py']:
        z.write(S/name, 'project/tower_hamlets/'+name)
    for name in v['source_blends']:
        z.write(R/name, 'project/tower_hamlets/input/canary_wharf_20261007/'+name)
    for name in ['sources.json','citi_neighbor_shared_interface.json','citi_neighbor_identity.json']:
        z.write(R/'references'/name, 'references/'+name)
    z.write(R/'exports/citi-neighbor-massing-001/sources.zip','neighbor-source.zip')
    z.write(R/'exports/citi-neighbor-interface-001/source_snapshot.zip','citi-interface-source.zip')
    z.write(D/'ATTRIBUTION.md','ATTRIBUTION.md')
m = read(S/'runs/canary_wharf_refinement_016/manifest.json')
m.update(run_id=D.name, created_at=datetime.now(timezone.utc).isoformat())
m['provenance']['parameters'] = {
    'representation':'Citi neighbor historical roof study with piecewise shared-edge ornament clipping; estimates not surveyed; region incomplete',
    'not_as_built':True, 'source_owner_ids':v['source_owner_ids']}
m['provenance']['inputs'] = [{'id':name, 'sha256':h} for name,h in v['source_blends'].items()]
m['spatial']['bounds_m'] = {'min':v['bounds_enu_m'][0], 'max':v['bounds_enu_m'][1]}
types = {'.png':'image/png','.json':'application/json','.zip':'application/zip',
         '.blend':'application/x-blender','.md':'text/markdown'}
m['artifacts'] = [{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),
                   'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}
                  for p in sorted(D.iterdir()) if p.suffix in types]
write(D/'manifest.json', m)
write(S/'views/canary_wharf_appearance_citi_neighbor.json', {
    'schema_version':'1.1.0','scene_id':'tower_hamlets',
    'title':'Canary Wharf · Citi neighbor roof and shared facade', 'time_alignment':'relative',
    'runs':[D.name], 'layers':[{'run_id':D.name,'layer_id':'geometry','visible':True}],
    'camera':{'position':[-170,360,205], 'target':[0,65,40]}})
print(D)
