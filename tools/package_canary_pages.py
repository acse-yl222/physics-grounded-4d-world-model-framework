"""Explicitly package the selected Canary Wharf city run for Pages publication.

Run after build_public_site.py. Copies only browser assets, never solver inputs,
source snapshots, private configuration or recovery history. Does not push.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'city_activity025'
RESOURCE = 'tower_hamlets_geometry_' + VERSION

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def package(site, resources):
    run = ROOT / 'project/tower_hamlets/runs/canary_wharf_city_activity_025'
    destination = site / 'scenes/tower_hamlets'
    model_dir = resources / 'project/tower_hamlets/geometry' / VERSION
    if destination.exists() or model_dir.exists():
        raise ValueError('Publication version already exists; do not overwrite immutable assets')
    model_dir.mkdir(parents=True)
    model = run / 'models/canary_wharf_4km.glb'
    parts = []
    with model.open('rb') as stream:
        while data := stream.read(64 * 1024 * 1024):
            name = f'canary_wharf_4km.glb.part-{len(parts):03d}'
            (model_dir / name).write_bytes(data)
            parts.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = model_dir / 'manifest.json'
    write(manifest, {'name': model.name, 'version': VERSION, 'total_bytes': model.stat().st_size,
                     'sha256': sha(model), 'parts': parts, 'note': 'Byte-exact original GLB; glTF Y up, metres.'})
    catalogue = json.loads((resources / 'resources.json').read_text())
    entry = {'id': RESOURCE, 'scene_id': 'tower_hamlets', 'title': 'Canary Wharf 4 km geometry',
             'category': 'geometry', 'version': VERSION, 'format': 'glb_parts',
             'manifest': str(manifest.relative_to(resources)),
             'compatibility_manifest': str(manifest.relative_to(resources)),
             'total_bytes': model.stat().st_size, 'coordinate_frame': 'glTF-y-up', 'units': 'm',
             'assets': [{'path': str(p.relative_to(resources)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                        for p in sorted(model_dir.iterdir())],
             'provenance': {'repository': 'acse-yl222/physics-grounded-4d-world-model-framework',
                            'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                            'original_path': str(model.relative_to(ROOT)),
                            'run_manifest_sha256': sha(run / 'manifest.json')},
             'license': 'Contains OpenStreetMap (ODbL) and Overture Maps derived geometry. © OpenStreetMap contributors; Overture Maps Foundation. Architectural details include estimates; no Google imagery-derived geometry. Preserve source attribution; no blanket licence asserted.'}
    catalogue['resources'].append(entry)
    write(resources / 'resources.json', catalogue)
    write(resources / 'project/tower_hamlets/resources.json', {'scene_id': 'tower_hamlets', 'resource_ids': [RESOURCE]})
    destination.mkdir(parents=True)
    for name in ('physics', 'uav'):
        shutil.copytree(run / name, destination / name)
    traffic = destination / 'traffic'
    traffic.mkdir()
    for name in ('roads.json', 'signal_layer.json', 'replay.json', 'verification.json'):
        shutil.copy2(run / 'traffic' / name, traffic / name)
    shutil.copytree(run / 'traffic/replay', traffic / 'replay')
    scene = json.loads((run / 'scene.json').read_text())
    scene['model']['parts_manifest'] = catalogue['base_url'].rstrip('/') + '/' + entry['manifest']
    write(destination / 'scene.json', scene)
    write(destination / 'publication.json', {'source_run': run.name, 'source_manifest_sha256': sha(run / 'manifest.json'),
          'geometry_resource': RESOURCE, 'limits': scene['limits'],
          'assets': [{'path': str(p.relative_to(destination)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                     for p in sorted(destination.rglob('*')) if p.is_file()]})
    index = json.loads((site / 'scenes/index.json').read_text())
    index['scenes'].append({'id': 'tower_hamlets', 'title': scene['title'], 'short': 'Canary Wharf'})
    write(site / 'scenes/index.json', index)
    with (site / '.gitignore').open('a') as stream:
        stream.write('\n# Explicit Canary Wharf browser assets\n!scenes/tower_hamlets/physics/**/*.npy\n!scenes/tower_hamlets/physics/*.npy\n!scenes/tower_hamlets/uav/*.f32\n')
    print('Packaged selected browser assets and byte-exact geometry chunks.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    parser.add_argument('resources', type=Path)
    args = parser.parse_args()
    package(args.site.resolve(), args.resources.resolve())
