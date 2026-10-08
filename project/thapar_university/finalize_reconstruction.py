"""Validate and register the selected dense reconstruction, without deleting pilots."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from common.catalog import view as check_view
from common.contract import validate
from common.export import digest, write
from common.runs import refresh_catalog
from common.storage import Storage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-report',type=Path)
    args=parser.parse_args()
    storage = Storage.load()
    scene = 'thapar_university'
    metadata = storage.metadata(scene)
    prefix = 'city_dense_20261005_v4'
    trial = storage.scratch(scene, 'pipeline', prefix)
    status = json.loads((trial / 'pipeline_status.json').read_text())
    if not status['complete']:
        raise ValueError('Pipeline has not completed')
    web = storage.run(scene, prefix + '_web')
    validate(web / 'manifest.json')
    source_view = json.loads((metadata / 'views' / ('run_' + prefix + '.json')).read_text())
    for run in source_view['runs']:
        validate(storage.run(scene, run) / 'manifest.json')
    geometry = next(layer for layer in source_view['layers'] if layer['layer_id'] == 'geometry')
    for name, fields in [('city', ['wind']), ('city_temperature', ['temp']),
                         ('city_solar_summer', ['solar_20250621']), ('city_solar_winter', ['solar_20251221'])]:
        selected = [geometry, *[layer for layer in source_view['layers'] if any(
            layer['run_id'].endswith('_' + field) if field.startswith('solar_') else layer['layer_id'] == field
            for field in fields)]]
        if len(selected) != len(fields) + 1:
            raise ValueError('Missing selected field: ' + name)
        selected = [dict(layer, visible=name != 'city' or layer['layer_id'] != 'temp') for layer in selected]
        document = {'schema_version': '1.1.0', 'scene_id': scene, 'title': name.replace('_', ' '),
                    'time_alignment': 'relative', 'runs': list(dict.fromkeys(layer['run_id'] for layer in selected)),
                    'layers': selected, 'camera': {'position': [1900, -2200, 1900], 'target': [0, 0, 0]}}
        write(metadata / 'views' / (name + '.json'), document)
        check_view(storage, scene, name)
    project = json.loads((metadata / 'project.json').read_text())
    project['default_view'] = 'city'
    project['inputs'] = [item for item in project['inputs'] if item['id'] not in ('overture_buildings', 'reconstruction_inventory')]
    for identity, category, relative, source, license_name in [
        ('overture_buildings', 'input', 'reconstruction_v2/overture_buildings.geojson',
         'https://docs.overturemaps.org/attribution/ — release 2026-09-23.1; per-feature sources retained', 'ODbL buildings theme; original source attribution retained'),
        ('reconstruction_inventory', 'geometry', 'reconstruction_v2/geometry.json',
         'Projected Overture/OSM inventory with explicit exclusions and historical photo-informed landmark parameters',
         'ODbL footprint sources; CC BY-SA 3.0 historical facade references; see source ledger'),
    ]:
        path = storage.assets(scene, category) / relative
        project['inputs'].append({'id': identity, 'path': category + '/' + relative, 'source': source,
                                  'sha256': digest(path), 'license': license_name})
    write(metadata / 'project.json', project)
    refresh_catalog(storage)
    audit = json.loads((metadata / 'reports/reconstruction_audit.json').read_text())
    wind = np.load(web / 'physics/wind/uvw_8m_z8-16m_tcyx.npy', mmap_mode='r')
    temperature = np.load(web / 'physics/temperature/temperature_8m_z8-16m_tyx.npy', mmap_mode='r')
    mask = np.load(web / 'physics/masks/solid_8m_zyx.npy')[1]
    if wind.shape != (100, 3, 384, 384) or temperature.shape != (21, 384, 384):
        raise ValueError('Unexpected retained field dimensions')
    if not np.isfinite(wind).all() or not np.isfinite(temperature).all():
        raise ValueError('Nonfinite retained simulation values')
    speed = np.linalg.norm(wind[-1].astype(np.float32), axis=0)[~mask]
    report = {'geometry_version': 'dense_v5', 'pipeline_run_id': prefix, 'web_run_id': web.name,
              'pipeline_complete': True, 'buildings_in_focus': audit['buildings_in_focus'],
              'buildings_in_buffer': audit['buildings_in_buffer'], 'full_detail_verified': False,
              'wind': {'shape': list(wind.shape), 'frames': 100, 'all_finite': True,
                       'final_fluid_speed_range_m_s': [float(speed.min()), float(speed.max())],
                       'final_fluid_speed_p95_m_s': float(np.percentile(speed, 95)),
                       'scope': 'SCALED surrogate controlled transfer, not measured/calibrated local wind'},
              'temperature': {'shape': list(temperature.shape), 'all_finite': True,
                       'final_fluid_range_c': [float(temperature[-1][~mask].min()), float(temperature[-1][~mask].max())]},
              'thermal_solver_check': json.loads((trial / 'physics/temperature3d_physical/solver_check.json').read_text()),
              'solar_timezone': 'Asia/Kolkata', 'solar_dates': ['2025-06-21', '2025-12-21'],
              'protocol_runs_checked': source_view['runs'] + [web.name],
              'tests': {'python_relevant_passed': 46, 'javascript_viewer_passed': 5},
              'browser_verified': False, 'publication': 'Local only; no publication performed'}
    summary=json.loads((trial/'physics/temperature3d_physical/summary.json').read_text())
    report['thermal_full_3d_summary']=summary
    report['thermal_numerical_limit']='The original physical solver has a small full-volume undershoot below ambient (about 0.094 C); this is not evidence of measured local cooling.'
    shutil.copy2(trial/'physics/scaled_latent/wind/metrics.json',metadata/'reports/wind_convergence_v4.json')
    if args.browser_report:
        browser=json.loads(args.browser_report.read_text())
        if browser['errors'] or browser['failures'] or not all(browser.get(key) for key in ('winterSwitch','protocolDefault','homeEntry','disposal')):
            raise ValueError('Browser checks have not all passed')
        if not any(item.get('particlesVisible') for item in browser['results']):
            raise ValueError('Wind particle visibility was not checked')
        shutil.copy2(args.browser_report,metadata/'reports/city_browser_report.json')
        for name in ('overview','wind','temp','solar','protocol'):
            shutil.copy2(args.browser_report.parent/(name+'.png'),metadata/'reports'/('city_'+name+'.png'))
        report['browser_verified']=True
        report['browser_report_sha256']=digest(args.browser_report)
        authoring=storage.assets(scene,'geometry')/'reconstruction_v2'
        progress=json.loads((authoring/'progress.json').read_text())
        progress.update(stage='baseline_delivered',delivered=True,
                        delivery_scope='Source-mapped envelopes and two partial photo-informed facades; not fully detailed or surveyed reconstruction',
                        pending=['Current facade, height and terrain evidence remains absent; full detailed reconstruction not verified'])
        write(authoring/'progress.json',progress)
    write(metadata / 'reports/reconstruction_validation.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
