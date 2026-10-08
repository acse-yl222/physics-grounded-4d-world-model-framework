#!/usr/bin/env python3
"""Overlay explicitly selected city display assets onto an existing Pages checkout.

Never copies raw API responses, solver source snapshots, local storage configuration,
or unrelated scene changes. Original runs remain intact; these are derived display
exports with original manifest hashes and solver provenance retained.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import numpy as np
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def export_run(scene, run_id, target):
    source = ROOT / 'project' / scene / 'runs' / run_id
    m = read(source / 'manifest.json')
    export_id = run_id + '_display_v1'
    dest = target / 'project' / scene / 'runs' / export_id
    tracked = subprocess.check_output(['git', 'ls-files', '--', str(dest.relative_to(target))], cwd=target, text=True)
    if tracked.strip():
        raise ValueError(f'Refusing to overwrite a committed display version: {export_id}; select a new version.')
    dest.mkdir(parents=True, exist_ok=True)
    assets = set()
    for layer in m['layers']:
        assets.add(layer['asset'])
        enc = layer.get('encoding', {})
        if layer['format'] == 'npy' and layer['kind'] == 'scalar_field':
            values = np.load(source / layer['asset'], mmap_mode='r')
            valid = np.isfinite(values)
            if enc.get('mask_asset'):
                valid &= np.load(source / enc['mask_asset']) == 0
            finite = values[valid]
            layer['display']['range'] = [float(finite.min()), float(finite.max())]
        assets.update(enc.get('frame_assets', []))
        for key in ('height_asset', 'mask_asset'):
            if key in enc:
                assets.add(enc[key])
    for asset in assets:
        p = Path(asset)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('Unsafe asset path')
        (dest / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / p, dest / p)
    original_provenance = copy.deepcopy(m['provenance'])
    m['run_id'] = export_id
    m['created_at'] = datetime.now(timezone.utc).isoformat()
    m['provenance'] = {
        'code_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty': True,
        'parameters': {
            'operation': 'Display-only extraction; original layer bytes, coordinates and times unchanged. No solver recomputation.',
            'source_run_id': run_id,
            'source_provenance': original_provenance,
            'reproducibility_scope': 'Snapshot contains display exporter only. Original solver source/input bundles are retained locally and are not part of this public display export.',
        },
        'inputs': [{'id': 'source_manifest', 'sha256': sha(source / 'manifest.json')}],
    }
    snapshot = dest / 'display_export_source.tar.gz'
    with tarfile.open(snapshot, 'w:gz') as archive:
        archive.add(__file__, arcname='tools/build_city_publication.py')
    m['artifacts'] = [{'id': 'source_snapshot', 'asset': snapshot.name, 'sha256': sha(snapshot), 'media_type': 'application/gzip'}]
    write(dest / 'manifest.json', m)
    return f'runs/{export_id}/manifest.json'

def build(target):
    # Shared protocol widgets; leave the existing portal and windfarm untouched.
    for folder in ('widgets', 'shared', 'vendor'):
        shutil.copytree(ROOT / 'src/visualization' / folder, target / 'src/visualization' / folder, dirs_exist_ok=True)
    for name in ('main.js', 'style.css', 'city-tools.js'):
        shutil.copy2(ROOT / 'src/visualization/legacy/viewer/3d' / name, target / 'viewer/3d' / name)
    for scene, legacy in [('south_ken', 'south_kensington'), ('white_city', 'white_city')]:
        config = ROOT / 'project' / scene / 'configs'
        traffic = read(config / 'traffic_result.json')['run_id']
        selections = {
            'traffic': ('SUMO traffic · baseline', traffic, '300 s, 100 synthetic departures; left-hand traffic on OSM roads. Uncalibrated demand and inferred signals, not observed traffic. Road/signal availability follows each network.'),
            'diurnal': ('Day cycle · controlled experiment', read(config / 'diurnal_result.json')['run_id'], 'Solar-coupled air and surface temperature; constant 20 °C ambient, uniform materials and a frozen wind field. Controlled experiment, not measured weather. Air values use the declared invalid-cell mask.'),
            'transport': ('Public transport · TfL snapshot', read(config / 'transport_snapshot.json')['run_id'], 'TfL stop and route snapshot, September 2026; individual responses were collected at different times. Not a live service or a calibrated passenger-demand model.'),
        }
        modules = {}
        for key, (title, run, note) in selections.items():
            modules[key] = {'title': title, 'manifest': export_run(scene, run, target), 'note': note}
        write(target / 'project' / scene / 'city-tools.json', {'scene_id': scene, 'modules': modules})
        scene_file = target / 'scenes' / legacy / 'scene.json'
        published = read(scene_file)
        published['city_tools'] = f'project/{scene}/city-tools.json'
        write(scene_file, published)
    catalogue_file = target / 'src/visualization/public-scenes.json'
    catalogue = read(catalogue_file)
    for item in catalogue['scenes']:
        if item['scene_id'] in ('south_ken', 'white_city'):
            legacy = 'south_kensington' if item['scene_id'] == 'south_ken' else 'white_city'
            item['viewer_url'] = f'viewer/3d/?scene={legacy}&module=traffic'
            item['description'] = 'City geometry and environmental fields, with shared SUMO traffic, controlled day-cycle temperature and TfL transport tools. Traffic demand is synthetic and uncalibrated.'
    write(catalogue_file, catalogue)
    for name in ('city-tools.md', 'city-parity-20260930.md'):
        path = target / 'docs/framework' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'docs/framework' / name, path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site_checkout', type=Path)
    args = parser.parse_args()
    build(args.site_checkout.resolve())
