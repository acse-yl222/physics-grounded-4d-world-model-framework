"""CPU solar calculation on the actual transformed triangles of an Img2City GLB."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import tarfile
import time

import numpy as np
import torch

from common.contract import validate
from common.runs import promote_bundle
from common.storage import Storage, identifier
from common.catalog import project
from urban_geometry.img2city_adapter import node_matrix, digest, write_json
from urban_geometry.voxelization.glb_plan import read_glb_header
from urban_geometry.voxelization.prepare_glb import read_primitive, raster
from urban_flow.physics.solar.model import ShadowNet, HorizonNet, sun_position, ground_irradiance


def raster_model(source, bounds, cell):
    """Top visible surface at cell centres, preserving glTF hierarchy and source metres."""
    doc, base = read_glb_header(source)
    origin = np.floor(np.array(bounds['min'][:2]) / cell) * cell
    size = np.ceil((np.array(bounds['max'][:2]) - origin) / cell).astype(int)
    height = np.full((size[1], size[0]), -np.inf, dtype=np.float32)
    count = 0
    # Dynamic vehicles and road markings are not part of the static solar obstruction model.
    excluded = ('Veh', 'Car_', 'Bus_', 'Arrow_', 'Dash_', 'Zeb_', 'Line_')
    with Path(source).open('rb') as stream:
        def visit(index, parent, ancestors):
            nonlocal count
            if index in ancestors:
                raise ValueError('Cyclic glTF hierarchy')
            node = doc['nodes'][index]
            matrix = parent @ node_matrix(node)
            if node.get('name', '').startswith(excluded):
                return
            if 'skin' in node:
                raise ValueError('Bake skins before solar rasterization')
            if 'mesh' in node:
                for primitive in doc['meshes'][node['mesh']]['primitives']:
                    if primitive.get('mode', 4) != 4 or primitive.get('targets'):
                        raise ValueError('Static triangle geometry is required')
                    points, faces = read_primitive(doc, stream, base, primitive)
                    world = points @ matrix[:3, :3].T + matrix[:3, 3]
                    vertices = np.column_stack((world[:, 0], -world[:, 2], world[:, 1]))
                    raster(vertices, faces, height, origin[0], origin[1], float(cell))
                    count += 1
            for child in node.get('children', []):
                visit(child, matrix, ancestors | {index})
        for index in doc['scenes'][doc.get('scene', 0)]['nodes']:
            visit(index, np.eye(4), set())
    valid = np.isfinite(height)
    if not valid.any():
        raise ValueError('No model surfaces intersect the grid')
    # Unmodelled cells cast no shadow and remain masked out of displayed results.
    height[~valid] = min(float(height[valid].min()), 0)
    return height, valid, origin.tolist(), count


def calculate(height, cell, origin, date, interval_minutes=30):
    torch.set_num_threads(4)
    sn = ShadowNet(height, cell, 'cpu')
    start = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    frames, shadows, irradiation = [], [], []
    with torch.inference_mode():
        svf, _ = HorizonNet(sn, n_azimuth=16, altitudes_deg=tuple(range(2, 90, 5)))()
        for minutes in range(0, 1441, interval_minutes):
            altitude, azimuth = sun_position(origin['latitude'], origin['longitude'], start.year, start.month, start.day, minutes / 60)
            if altitude <= 0:
                shadow = torch.ones_like(sn.H, dtype=torch.bool)
                ghi = torch.zeros_like(sn.H)
                dni = dhi = 0.0
            else:
                shadow = sn(altitude, azimuth)
                ghi, dni, dhi = ground_irradiance(shadow, svf, altitude, start.month, albedo=.2)
            frames.append({'seconds': minutes * 60, 'altitude_deg': altitude, 'azimuth_deg': azimuth,
                           'dni_w_m2': dni, 'dhi_w_m2': dhi})
            shadows.append(shadow.numpy().astype(np.float32))
            irradiation.append(ghi.numpy().astype(np.float32))
    times = np.array([f['seconds'] for f in frames])
    values = np.stack(irradiation)
    shadow = np.stack(shadows)
    lit = np.array([f['altitude_deg'] > 0 for f in frames])[:, None, None] * (1 - shadow)
    hours = np.trapezoid(lit, x=times, axis=0) / 3600
    return values, shadow, svf.numpy(), hours.astype(np.float32), frames


def run(storage, source_run, date, cell=4, interval=30, run_id=None):
    started = time.monotonic()
    run_id = identifier(run_id or 'img2city_solar_' + date.replace('-', '') + '_' + datetime.now(timezone.utc).strftime('%H%M%S'), run=True)
    source_run = Path(source_run).resolve()
    validate(source_run / 'manifest.json')
    source = json.loads((source_run / 'manifest.json').read_text())
    scene = source['scene_id']
    if cell <= 0 or interval <= 0 or 1440 % interval:
        raise ValueError('Positive cell size and interval dividing 1440 minutes required')
    view_id = identifier(run_id.lower())
    if storage.run(scene, run_id).exists() or (storage.metadata(scene)/'views'/f'{view_id}.json').exists():
        raise FileExistsError('Run/view already exists')
    model = source_run / next(layer['asset'] for layer in source['layers'] if layer['format'] == 'glb')
    trial = storage.scratch(scene, 'img2city_solar', run_id)
    trial.mkdir(parents=True, exist_ok=False)
    out = trial / run_id
    data = out / 'data'
    data.mkdir(parents=True)
    height, valid, xy, count = raster_model(model, source['spatial']['bounds_m'], cell)
    print(f'Rasterized {count} primitives: {height.shape}, {cell} m, valid {valid.mean():.1%}', flush=True)
    ghi, shadow, sky, hours, frames = calculate(height, cell, source['spatial']['origin'], date, interval)
    for name, values in [('height', height), ('irradiance', ghi), ('shadow', shadow), ('sky_view', sky), ('sunlit_hours', hours)]:
        np.save(data / f'{name}.npy', values.astype('<f4'))
    np.save(data/'invalid.npy', (~valid).astype('u1'))
    shutil.copy2(model, data/'model.glb')
    shutil.copy2(source_run/'manifest.json', data/'input_manifest.json')
    write_json(data/'frames.json', frames)
    snapshot = out/'source_snapshot.tar.gz'
    with tarfile.open(snapshot, 'w:gz') as archive:
        for rel in ['src/urban_geometry/img2city_solar.py', 'src/urban_geometry/img2city_adapter.py',
                    'src/urban_geometry/voxelization/prepare_glb.py', 'src/urban_geometry/voxelization/glb_plan.py',
                    'src/urban_flow/physics/solar/model.py', 'src/common/contract.py', 'src/common/binary.py',
                    'src/common/storage.py', 'src/common/catalog.py', 'src/common/runs.py',
                    'schemas/run-manifest-v1.schema.json', 'schemas/project-v1.schema.json', 'schemas/view-v1.schema.json']:
            archive.add(storage.root/rel, arcname=rel)
    layers = [{'id': 'img2city', 'kind': 'mesh', 'format': 'glb', 'asset': 'data/model.glb', 'sampling': 'static',
               'encoding': {'coordinate_frame': 'glTF-y-up'}, 'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}]
    for name, values, unit, limits, dynamic in [
        ('irradiance', ghi, 'W/m2', [0, 1000], True), ('shadow', shadow, '1', [0, 1], True),
        ('sky_view', sky, '1', [0, 1], False), ('sunlit_hours', hours, 'h', [0, 18], False)]:
        layers.append({'id': name, 'kind': 'scalar_field', 'format': 'npy', 'asset': f'data/{name}.npy',
                       'sampling': ('step' if name == 'shadow' else 'linear') if dynamic else 'static',
                       'field': {'name': name, 'unit': unit},
                       'encoding': {'coordinate_frame': 'ENU', 'dtype': '<f4', 'shape': list(values.shape),
                                    'axes': 'TYX' if dynamic else 'YX', 'origin_m': [*xy, .25],
                                    'spacing_m': [cell, cell], 'sample_location': 'cell_center', 'byte_order': 'little', 'compression': 'none',
                                    'height_asset': 'data/height.npy', 'height_dtype': '<f4', 'mask_asset': 'data/invalid.npy',
                                    'mask_dtype': '|u1', 'mask_semantics': 'invalid_nonzero'},
                       'display': {'widget': 'scalar_field', 'capabilities': ['pick', 'legend', 'opacity'], 'range': limits}})
    params = {'preview_title': f'Img2City · South Kensington · Solar {date}', 'date_utc': date,
              'cell_m': cell, 'interval_minutes': interval, 'device': 'cpu', 'torch_version': torch.__version__,
              'grid_rendering': 'surface', 'initially_hidden_layers': ['shadow', 'sky_view', 'sunlit_hours'],
              'initial_time_s': 12 * 3600, 'playback_rate': 900,
              'display_note': f'按当前模型重算 · 晴空假设 · {cell:g} m 网格 · UTC 时间',
              'layer_labels': {'img2city': '南肯辛顿模型', 'irradiance': '太阳辐照度', 'shadow': '阴影（1 = 遮阴）',
                               'sky_view': '天空可见度', 'sunlit_hours': '全天日照时长'},
              'assumptions': ['2.5D top-surface raster, local model heights (not survey terrain)',
                              'Vegetation and glass treated as opaque; dynamic vehicles/road markings excluded',
                              'No obstructions outside supplied geometry; boundary shadows may be underestimated',
                              'ASHRAE clear sky, albedo 0.2; no observed weather',
                              'Shadow mask uses step sampling; irradiance interpolates between calculated frames',
                              'Daily sunlit hours use trapezoidal integration of sampled binary visibility'],
              'height_shape': list(height.shape), 'valid_cells': int(valid.sum()), 'mesh_primitives': count,
              'runtime_seconds': round(time.monotonic() - started, 3)}
    manifest = {'schema_version': '1.1.0', 'scene_id': scene, 'simulation': 'img2city_solar', 'run_id': run_id,
                'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                'provenance': {'code_revision': 'local-source-snapshot', 'dirty': True, 'parameters': params,
                               'inputs': [{'id': 'aligned_img2city_glb', 'sha256': digest(model)},
                                          {'id': 'geometry_manifest', 'sha256': digest(source_run/'manifest.json')}]},
                'spatial': source['spatial'], 'time': {'unit': 's', 'epoch': date+'T00:00:00Z', 'samples': [f['seconds'] for f in frames]},
                'layers': layers,
                'artifacts': [{'id': 'source_snapshot', 'asset': snapshot.name, 'sha256': digest(snapshot), 'media_type': 'application/gzip'}]}
    for file in sorted(data.iterdir()):
        manifest['artifacts'].append({'id': 'asset_'+file.stem, 'asset': 'data/'+file.name, 'sha256': digest(file),
                                      'media_type': 'application/octet-stream'})
    write_json(out/'manifest.json', manifest)
    validate(out/'manifest.json')
    view = {'schema_version': '1.1.0', 'scene_id': scene, 'title': params['preview_title'], 'time_alignment': 'absolute',
            'runs': [run_id], 'layers': [{'run_id': run_id, 'layer_id': layer['id'],
                                        'visible': layer['id'] not in params['initially_hidden_layers']} for layer in layers]}
    write_json(trial/'bundle.json', {'scene_id': scene, 'view_id': view_id, 'runs': [run_id], 'view': view, 'project': project(storage, scene)})
    retained = promote_bundle(storage, trial)
    print(json.dumps({'view': str(retained), **params, 'peak_irradiance': float(ghi.max()),
                      'midday_shaded_fraction': float(shadow[len(frames)//2][valid].mean())}, indent=2), flush=True)
    return retained


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_run', type=Path)
    parser.add_argument('--date', default='2026-06-21')
    parser.add_argument('--cell', type=float, default=4)
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--run-id')
    args = parser.parse_args()
    run(Storage.load(), args.source_run, args.date, args.cell, args.interval, args.run_id)


if __name__ == '__main__':
    main()
