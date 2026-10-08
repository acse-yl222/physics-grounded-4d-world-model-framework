"""Retain the labelled, estimated single-building benchmark without publishing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile

S = Path(__file__).resolve().parent
R = S / 'input/canary_wharf_20261007'
E = R / 'exports'
O = E / 'one_canada_visual_sample001'
D = S / 'runs/canary_wharf_one_canada_visual_sample_001'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
v = read(O / 'verification.json')
a = read(O / 'assembly.json')
assert v['native_reopened'] and v['independent_glb_verified']
assert read(O / 'visual_review.json')['inspected']
assert sha(O / 'canada.blend') == v['native_sha256']
assert sha(O / 'canada.glb') == v['glb_sha256']
for p, h in a['source_blends'].items():
    assert sha(S / p) == h
if D.exists():
    assert not (D / 'manifest.json').exists(), 'Completed runs are immutable'
    assert sha(D / 'canada.blend') == v['native_sha256']
else:
    D.mkdir()
for p in O.iterdir():
    if p.is_file() and p.suffix in {'.blend', '.glb', '.png', '.json', '.md'}:
        shutil.copy2(p, D / p.name)
for name in ('base.png', 'entrance-close.png'):
    shutil.copy2(E / 'one_canada_whole_sample001' / name, D / name)
shutil.copy2(R / 'references/ATTRIBUTION.md', D / 'ATTRIBUTION.md')
with zipfile.ZipFile(D / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ('assemble_one_canada_visual_sample001.py',
                 'verify_one_canada_visual_sample001.py',
                 'retain_one_canada_visual_sample001.py'):
        z.write(S / name, 'project/tower_hamlets/' + name)
    for name in a['source_blends']:
        z.write(S / name, 'project/tower_hamlets/' + name)
    for folder in ('one_canada_whole_sample001', 'one_canada_roof_completion001'):
        candidates = [E / folder / n for n in ('source.zip', 'sources.zip')
                      if (E / folder / n).exists()]
        assert len(candidates) == 1, folder
        z.write(candidates[0], folder + '-source.zip')
    for folder in ('one_canada_base_independent001', 'one_canada_roof_independent006'):
        for p in (E / folder).iterdir():
            if p.is_file() and p.suffix in {'.py', '.json', '.md'}:
                z.write(p, folder + '/' + p.name)
    for p in (R / 'references/building_timing_benchmark001').glob('*.json'):
        z.write(p, 'benchmark/' + p.name)
    z.write(D / 'ATTRIBUTION.md', 'ATTRIBUTION.md')
m = read(S / 'runs/canary_wharf_appearance_one_canada_facade_001/manifest.json')
m.update(run_id=D.name, created_at=datetime.now(timezone.utc).isoformat())
m['layers'][0]['asset'] = 'canada.glb'
snapshot = read(O / 'native_snapshot.json')
m['spatial']['bounds_m'] = {
    'min': [min(x['bounds'][0][i] for x in snapshot.values()) for i in range(3)],
    'max': [max(x['bounds'][1][i] for x in snapshot.values()) for i in range(3)],
}
m['provenance']['parameters'] = {
    'representation': 'Single-building visual benchmark; estimated lobby, entrance and unseen roof faces',
    'not_as_built': True, 'fully_image_verified': False,
    'timing_mode': 'Completion of inherited detailed asset, not from-zero production',
    'source_owner_ids': sorted({x['building_id'] for x in snapshot.values() if x['building_id']}),
}
m['provenance']['inputs'] = [{'id': p, 'sha256': h} for p, h in a['source_blends'].items()]
types = {'.png': 'image/png', '.json': 'application/json', '.zip': 'application/zip',
         '.blend': 'application/x-blender', '.md': 'text/markdown'}
m['artifacts'] = [{'id': 'source_snapshot' if p.name == 'source_snapshot.zip'
                   else p.name.replace('-', '_').replace('.', '_'),
                   'asset': p.name, 'sha256': sha(p), 'media_type': types[p.suffix]}
                  for p in sorted(D.iterdir()) if p.suffix in types and p.name != 'manifest.json']
(D / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
print(D)
