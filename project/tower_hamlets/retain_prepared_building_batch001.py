"""Retain three fresh prepared-input exterior benchmark assets as an optional run."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, zipfile, copy

S = Path(__file__).resolve().parent
R = S / 'input/canary_wharf_20261007'
E = R / 'exports'
D = S / 'runs/canary_wharf_prepared_building_batch_001'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assets = read(R / 'references/building_timing_batch001/frozen_assets.json')['assets']
assert not D.exists(), 'Retained benchmark runs are immutable'
D.mkdir()
names = {'hsbc': 'HSBC UK', 'citi': 'Citi / 25 Canada Square', 'quay1': '1 West India Quay'}
final_images = {'whole', 'front', 'rear', 'roof', 'base', 'close', 'entry-close',
                'entrance-close', 'entrance', 'facade-close'}
for key, asset in assets.items():
    source = E / ('benchmark_batch001_' + key)
    assert sha(source / (key + '.blend')) == asset['native_sha256']
    assert sha(source / (key + '.glb')) == asset['glb_sha256']
    target = D / key
    target.mkdir()
    for p in source.iterdir():
        if p.is_file() and (p.suffix in {'.json', '.py', '.md', '.zip'}
                            or p.name in {key + '.blend', key + '.glb'}
                            or p.suffix == '.png' and p.stem in final_images):
            shutil.copy2(p, target / p.name)
    audit = E / ('benchmark_batch001_' + key + '_independent')
    shutil.copytree(audit, D / (key + '_independent'))
shutil.copy2(R / 'references/ATTRIBUTION.md', D / 'ATTRIBUTION.md')
with zipfile.ZipFile(D / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for key in assets:
        source = E / ('benchmark_batch001_' + key)
        packages = [source / n for n in ('source.zip', 'sources.zip') if (source / n).exists()]
        assert len(packages) == 1
        z.write(packages[0], key + '-source.zip')
    for name in ('inspect_batch001_assets.py', 'audit_batch001_hsbc.py',
                 'retain_prepared_building_batch001.py'):
        z.write(S / name, 'project/tower_hamlets/' + name)
    for p in (R / 'references/building_timing_batch001').glob('*.json'):
        z.write(p, 'benchmark/' + p.name)
    z.write(D / 'ATTRIBUTION.md', 'ATTRIBUTION.md')
m = read(S / 'runs/canary_wharf_appearance_one_canada_facade_001/manifest.json')
m.update(run_id=D.name, created_at=datetime.now(timezone.utc).isoformat())
layer = m['layers'][0]
m['layers'] = []
for key in assets:
    item = copy.deepcopy(layer)
    item.update(id=key, asset=key + '/' + key + '.glb')
    m['layers'].append(item)
m['spatial']['bounds_m'] = {
    'min': [min(v['bounds_m']['min'][i] for v in assets.values()) for i in range(3)],
    'max': [max(v['bounds_m']['max'][i] for v in assets.values()) for i in range(3)],
}
m['provenance']['parameters'] = {
    'representation': 'Three fresh exterior assets from prepared mapped footprints/heights and existing licensed photos',
    'not_as_built': True, 'fully_image_verified': False,
    'batch_start_utc': '2026-10-08T13:01:50Z',
    'timing_excludes': ['Prior data acquisition', 'Historical authoring tool development'],
    'reuse_restriction': 'No prior detailed building meshes loaded',
    'estimated_features': ['Source-missing base and entrances', 'Reverse elevations', 'Exact material/frame profiles', 'Unobserved roofs'],
    'sample_labels': names,
}
m['provenance']['inputs'] = [{'id': key + '.blend', 'sha256': a['native_sha256']}
                             for key, a in assets.items()]
types = {'.png': 'image/png', '.json': 'application/json', '.zip': 'application/zip',
         '.blend': 'application/x-blender', '.md': 'text/markdown'}
m['artifacts'] = []
seen = set()
for p in sorted(D.rglob('*')):
    if not p.is_file() or p.suffix not in types:
        continue
    rel = p.relative_to(D).as_posix()
    ident = 'source_snapshot' if rel == 'source_snapshot.zip' else rel.replace('/', '_').replace('-', '_').replace('.', '_')
    while ident in seen:
        ident += '_copy'
    seen.add(ident)
    m['artifacts'].append({'id': ident, 'asset': rel, 'sha256': sha(p), 'media_type': types[p.suffix]})
(D / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
print(D)
