"""Retain a locally reviewable three-building repair, without changing defaults."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile

S = Path(__file__).resolve().parent
ROOT = S.parent.parent
R = S / 'input/canary_wharf_20261007'
O = R / 'exports/appearance-accelerated-repairs-002'
D = S / 'runs/canary_wharf_appearance_accelerated_repairs_002'

def read(p): return json.loads(p.read_text())
def write(p, v): p.write_text(json.dumps(v, indent=2) + '\n')
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

v = read(O / 'verification.json')
c = read(O / 'assembly-config.json')
assert v['native_reopened'] and v['independent_glb_verified'] and v['source_unchanged']
assert read(O / 'visual-review.json')['inspected']
assert sha(O / 'region.blend') == v['native_sha256']
assert sha(O / 'region.glb') == v['glb_sha256']
assert sha(ROOT / c['source']) == c['source_sha256']
for item in c['components']: assert sha(ROOT / item['native']) == item['sha256']
D.mkdir(exist_ok=False)
for p in O.iterdir():
    if p.is_file(): shutil.copy2(p, D / p.name)
shutil.copy2(R / 'references/ATTRIBUTION.md', D / 'ATTRIBUTION.md')
with zipfile.ZipFile(D / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ['assemble_accelerated_repairs002.py', 'retain_accelerated_repairs002.py',
                 'render_accelerated_repairs002_citi.py']:
        z.write(S / name, 'project/tower_hamlets/' + name)
    z.write(ROOT / c['source'], c['source'])
    z.write(O / 'assembly-config.json', 'assembly-config.json')
    for relative in ['geometry.json', 'references/citi_neighbor_interface_study.json',
                     'exports/facade-detail-pilot-001/quay1-detail.blend',
                     'exports/benchmark_batch001_hsbc/hsbc.blend',
                     'exports/benchmark_batch001_hsbc/geometry-contract.json']:
        p = R / relative
        z.write(p, str(p.relative_to(ROOT)))
    for item in c['components']:
        z.write(ROOT / item['native'], item['native'])
        for source in item['source_files']:
            p = ROOT / source
            z.write(p, source)
    for name in ['sources.json']:
        z.write(R / 'references' / name, 'references/' + name)
    for folder in ['quay1_repair002_independent', 'hsbc_crown_identity_independent001']:
        for p in sorted((R / 'exports' / folder).iterdir()):
            if p.is_file() and p.suffix in ('.py', '.json', '.md'):
                z.write(p, 'independent-review/' + folder + '/' + p.name)
    z.write(D / 'ATTRIBUTION.md', 'ATTRIBUTION.md')

m = read(S / 'runs/canary_wharf_appearance_one_canada_facade_001/manifest.json')
m.update(run_id=D.name, created_at=datetime.now(timezone.utc).isoformat())
m['provenance']['parameters'] = {
    'representation': 'Selective three-building exterior repair, preserving retained roof and shared interfaces',
    'not_as_built': True,
    'components': [{k: a[k] for k in ['label', 'replace_names', 'add_names', 'owners']}
                   for a in c['components']],
    'limitations': read(O / 'visual-review.json')['limitations']}
m['provenance']['inputs'] = [{'id': c['source'], 'sha256': c['source_sha256']}] + [
    {'id': item['native'], 'sha256': item['sha256']} for item in c['components']]
m['spatial']['bounds_m'] = {'min': v['bounds_enu_m'][0], 'max': v['bounds_enu_m'][1]}
types = {'.png': 'image/png', '.json': 'application/json', '.zip': 'application/zip',
         '.blend': 'application/x-blender', '.md': 'text/markdown', '.py': 'text/x-python'}
m['artifacts'] = [{'id': 'source_snapshot' if p.name == 'source_snapshot.zip' else p.name.replace('-', '_').replace('.', '_'),
                   'asset': p.name, 'sha256': sha(p), 'media_type': types[p.suffix]}
                  for p in sorted(D.iterdir()) if p.suffix in types]
write(D / 'manifest.json', m)
write(S / 'views/canary_wharf_appearance_accelerated_repairs002.json', {
    'schema_version': '1.1.0', 'scene_id': 'tower_hamlets',
    'title': 'Canary Wharf · HSBC, Citi and Quay1 details', 'time_alignment': 'relative',
    'runs': [D.name], 'layers': [{'run_id': D.name, 'layer_id': 'geometry', 'visible': True}],
    'camera': {'position': [-170, 360, 205], 'target': [0, 65, 40]}})
print(D)
