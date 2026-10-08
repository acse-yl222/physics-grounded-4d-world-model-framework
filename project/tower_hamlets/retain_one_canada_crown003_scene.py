"""Retain a reviewable local regional study; no publication or default-view change."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import shutil
import zipfile

S = Path(__file__).resolve().parent
R = S/'input/canary_wharf_20261007'
O = R/'exports/appearance-one-canada-crown-003'
D = S/'runs/canary_wharf_appearance_one_canada_crown_003'
def read(p): return json.loads(p.read_text())
def write(p, v): p.write_text(json.dumps(v, indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
v = read(O/'verification.json')
assert v['native_reopened'] and v['independent_glb_verified']
assert read(O/'visual_review.json')['inspected']
for name, digest in v['source_blends'].items():
    assert sha(R/name) == digest
if D.exists():
    assert not (D/'manifest.json').exists(), 'Completed run is immutable'
    assert sha(D/'region.blend') == sha(O/'region.blend'), 'Partial run must match frozen source'
else:
    D.mkdir()
for p in O.iterdir():
    if p.is_file(): shutil.copy2(p, D/p.name)
shutil.copy2(R/'references/ATTRIBUTION.md', D/'ATTRIBUTION.md')

with zipfile.ZipFile(D/'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ['assemble_one_canada_crown003_scene.py','retain_one_canada_crown003_scene.py']:
        z.write(S/name, 'project/tower_hamlets/'+name)
    for name in v['source_blends']:
        z.write(R/name, str((R/name).resolve().relative_to(S.parent.parent)))
    for name in ['sources.json','ea_vintage_metadata_audit001.json','ea_vintage_metadata_audit001.md']:
        z.write(R/'references'/name, 'references/'+name)
    for folder in ['one_canada_detail_gap003','one_canada_roof_seam005']:
        packages=[R/'exports'/folder/n for n in ['source.zip','sources.zip'] if (R/'exports'/folder/n).exists()]
        assert len(packages)==1, folder
        package=packages[0]
        z.write(package,folder+'-source.zip')
    z.write(R/'references/one_canada_crown_coordinator_review005.json','references/one_canada_crown_coordinator_review005.json')
    for review_folder in ['one_canada_crown_independent003','one_canada_crown_independent005']:
        for evidence in sorted((R/'exports'/review_folder).iterdir()):
            if evidence.is_file(): z.write(evidence,review_folder+'/'+evidence.name)
    for script in sorted(O.glob('*.py')):
        z.write(script, 'regional-verification/'+script.name)
    z.write(R/'references/one_canada_crown_coordinator_review006.json','references/one_canada_crown_coordinator_review006.json')
    z.write(D/'ATTRIBUTION.md','ATTRIBUTION.md')
m = read(S/'runs/canary_wharf_refinement_016/manifest.json')
m.update(run_id=D.name, created_at=datetime.now(timezone.utc).isoformat())
m['provenance']['parameters'] = {
    'representation':'One Canada west crown: upright supports on original continuous five slats and metal pyramid courses/major seams; crossview spacing/relief estimated; original pyramid dimensions unchanged; Altaf five-slot discrepancy remains unresolved; unseen elevations not completed',
    'not_as_built':True, 'source_owner_ids':v['source_owner_ids']}
m['provenance']['inputs'] = [{'id':name, 'sha256':h} for name,h in v['source_blends'].items()]
m['spatial']['bounds_m'] = {'min':v['bounds_enu_m'][0], 'max':v['bounds_enu_m'][1]}
types = {'.png':'image/png','.json':'application/json','.zip':'application/zip',
         '.blend':'application/x-blender','.md':'text/markdown'}
m['artifacts'] = [{'id':'source_snapshot' if p.name=='source_snapshot.zip' else p.name.replace('-','_').replace('.','_'),
                   'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}
                  for p in sorted(D.iterdir()) if p.suffix in types]
seen=set()
for artifact in m['artifacts']:
    while artifact['id'] in seen: artifact['id'] += '_copy'
    seen.add(artifact['id'])
write(D/'manifest.json', m)
write(S/'views/canary_wharf_appearance_one_canada_crown003.json', {
    'schema_version':'1.1.0','scene_id':'tower_hamlets',
    'title':'Canary Wharf · One Canada west crown detail', 'time_alignment':'relative',
    'runs':[D.name], 'layers':[{'run_id':D.name,'layer_id':'geometry','visible':True}],
    'camera':{'position':[-170,360,205], 'target':[0,65,40]}})
print(D)
