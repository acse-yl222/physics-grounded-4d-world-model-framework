"""OSM-based campus pilot using existing MAC, shadow and physical thermal solvers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
import uuid

import numpy as np
import requests

from common.catalog import view as check_view
from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote, refresh_catalog
from common.storage import Storage, within
from urban_geometry.osm_scene import footprints, height_grid, mesh, feature_collection


def read(path):
    return json.loads(Path(path).read_text())


def configuration(storage, scene):
    config = read(storage.metadata(scene) / 'configs/osm_climate.json')
    if config['schema_version'] != 'osm-climate-pilot-1' or config['scene_id'] != scene:
        raise ValueError('Scene configuration identity mismatch')
    return config


def retained_weather(storage, scene, scenario):
    target = storage.assets(scene, 'input') / 'weather' / (scenario['date'] + '_era5.json')
    metadata = target.with_suffix('.provenance.json')
    if target.exists():
        if read(metadata)['sha256'] != digest(target):
            raise ValueError('Retained weather checksum mismatch')
        return target
    origin = read(storage.metadata(scene) / 'project.json')['spatial']['origin']
    parameters = {'latitude': origin['latitude'], 'longitude': origin['longitude'],
                  'start_date': scenario['date'], 'end_date': scenario['date'],
                  'hourly': 'temperature_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation',
                  'wind_speed_unit': 'ms', 'models': 'era5', 'timezone': 'UTC'}
    response = requests.get('https://archive-api.open-meteo.com/v1/archive', params=parameters, timeout=60)
    response.raise_for_status()
    data = response.json()
    if 'hourly' not in data or data.get('utc_offset_seconds') != 0:
        raise ValueError('Invalid weather response')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(response.content)
    write(metadata, {'url': response.url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                     'sha256': digest(target), 'license': 'Open-Meteo CC BY 4.0; Copernicus ERA5 attribution',
                     'source_resolution': 'ERA5 0.25 degree, approximately 25 km; not a campus weather station',
                     'returned_grid_location': {key: data[key] for key in ('latitude', 'longitude', 'elevation')},
                     'radiation_time_semantics': 'Mean over preceding hour, held constant during controlled thermal run'})
    return target


def artifacts(folder, excluded):
    return [{'id': 'source_snapshot' if path.name == 'source_snapshot.tar.gz' else path.name,
             'asset': path.name, 'sha256': digest(path), 'media_type': 'application/octet-stream'}
            for path in sorted(folder.iterdir()) if path.is_file() and path.name not in excluded | {'manifest.json'}]


def finish(storage, scene, folder, config, revision, layers, samples, inputs):
    project = read(storage.metadata(scene) / 'project.json')
    excluded = {layer['asset'] for layer in layers}
    write(folder / 'manifest.json', {
        'schema_version': '1.1.0', 'scene_id': scene, 'simulation': 'osm_climate',
        'run_id': folder.name, 'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
        'provenance': {'code_revision': revision, 'dirty': True, 'parameters': config, 'inputs': inputs},
        'spatial': project['spatial'], 'time': {'unit': 's', 'samples': samples},
        'layers': layers, 'artifacts': artifacts(folder, excluded)})
    validate(folder / 'manifest.json')
    return promote(storage, folder)


def prepare(storage, scene):
    config = configuration(storage, scene)
    traffic = read(storage.metadata(scene) / 'configs/traffic.json')
    source = within(storage.assets(scene, 'input'), config['osm_snapshot'])
    if digest(source) != read(source.with_suffix('.provenance.json'))['sha256']:
        raise ValueError('OSM snapshot checksum mismatch')
    features, skipped = footprints(source, traffic['transform'], config['unknown_building_height_m'], config['level_height_m'])
    if not features:
        raise ValueError('No usable buildings; refusing empty-city simulation')
    roof = height_grid(features, config['domain_half_width_m'], config['cell_m'])
    if roof.max() >= config['height_m']:
        raise ValueError('Buildings intersect top boundary')
    identity = 'osm_geometry_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6]
    folder = storage.scratch(scene, 'osm_climate', identity)
    folder.mkdir(parents=True)
    revision = snapshot_sources(storage.root, folder / 'source_snapshot.tar.gz')
    shutil.copy2(source, folder / 'map.osm.xml')
    shutil.copy2(source.with_suffix('.provenance.json'), folder / 'osm_provenance.json')
    write(folder / 'config.json', config)
    write(folder / 'footprints_local.json', feature_collection(features))
    np.save(folder / 'roof.npy', roof)
    spatial = read(storage.metadata(scene) / 'project.json')['spatial']
    bounds = [*spatial['bounds_m']['min'][:2], *spatial['bounds_m']['max'][:2]]
    write(folder / 'buildings.json', mesh(features, bounds))
    from shapely.geometry import box
    focus = box(*bounds)
    selected = [feature for feature in features if feature['geometry'].intersects(focus)]
    audit = {'building_features_in_buffered_download': len(features), 'building_features_in_2km_focus': len(selected),
             'height_basis_all': dict(Counter(feature['height_basis'] for feature in features)),
             'height_basis_focus': dict(Counter(feature['height_basis'] for feature in selected)),
             'skipped': skipped, 'grid_shape_yx': list(roof.shape), 'maximum_height_m': float(roof.max()),
             'mapped_footprint_fraction_focus': unary_area(selected, focus) / focus.area,
             'coverage_status': 'OSM mapped footprints only; completeness against aerial imagery has not been established',
             'terrain': 'Assumed planar; no surveyed DTM, vegetation canopy or facade reconstruction',
             'rasterization': 'Cell-centre footprint sampling; any column height occupies intersected vertical cells; narrow buildings may be missed'}
    write(folder / 'geometry_audit.json', audit)
    layer = {'id': 'geometry', 'kind': 'mesh', 'format': 'json', 'asset': 'buildings.json', 'sampling': 'static',
             'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}
    destination = finish(storage, scene, folder, config, revision, [layer], [], [{'id': 'osm', 'sha256': digest(source)}])
    write(storage.metadata(scene) / 'configs/geometry_result.json', {'run_id': identity, 'audit': audit})
    project = read(storage.metadata(scene) / 'project.json')
    project['inputs'] = [{'id': 'osm', 'path': 'input/' + config['osm_snapshot'],
                          'source': 'OpenStreetMap API tiled map snapshot', 'sha256': digest(source),
                          'license': 'OpenStreetMap contributors, ODbL 1.0'}]
    for scenario in config['weather']:
        weather = retained_weather(storage, scene, scenario)
        project['inputs'].append({'id': 'weather_' + scenario['id'],
                                  'path': 'input/' + str(weather.relative_to(storage.assets(scene, 'input'))),
                                  'source': read(weather.with_suffix('.provenance.json'))['url'],
                                  'sha256': digest(weather), 'license': 'Open-Meteo CC BY 4.0; Copernicus ERA5'})
    write(storage.metadata(scene) / 'project.json', project)
    return destination


def unary_area(features, domain):
    from shapely.ops import unary_union
    return unary_union([feature['geometry'] for feature in features]).intersection(domain).area


def face_centres(faces, inlet):
    components = []
    for component, face in enumerate(faces):
        axis = 2 - component
        previous = np.roll(face, 1, axis)
        boundary = [slice(None)] * 3
        boundary[axis] = 0
        previous[tuple(boundary)] = inlet if component == 0 else 0
        components.append((face + previous) * .5)
    return np.asarray(components, dtype=np.float32)


def restore_wind(wind, rotation):
    restored = np.rot90(wind, -rotation, axes=(2, 3)).copy()
    east, north = restored[0].copy(), restored[1].copy()
    cosine, sine = round(math.cos(rotation * math.pi / 2)), round(math.sin(rotation * math.pi / 2))
    restored[0] = cosine * east - sine * north
    restored[1] = sine * east + cosine * north
    return restored


def wind_solve(solid, speed, config, device, folder):
    import torch
    from urban_flow.solvers.mac_torch import MAC
    fluid = torch.as_tensor(~solid, device=device)
    inlet = torch.full(fluid.shape[:2], speed, dtype=torch.float32, device=device) * fluid[:, :, 0]
    solver = MAC(fluid, config['cell_m'], inlet, open_top=True)
    solver.vel[0].fill_(speed)
    for component in range(3):
        solver.vel[component] *= solver.opened(component)
    elapsed, step, next_record = 0., 0, 0.
    records = []
    started = time.perf_counter()
    with torch.inference_mode():
        solver.project(rtol=config['pressure_rtol'], maxiter=200)
        previous = [velocity.clone() for velocity in solver.vel]
        while elapsed < config['flow_duration_s'] - 1e-9:
            timestep = min(config['flow_dt_max_s'], config['flow_cfl'] * config['cell_m'] / max(solver.maxsum(), .01),
                           config['flow_duration_s'] - elapsed)
            solver.advect(timestep)
            report = solver.project(rtol=config['pressure_rtol'], maxiter=200)
            elapsed += timestep
            step += 1
            if elapsed >= next_record or elapsed >= config['flow_duration_s'] - 1e-9:
                change = sum(float(((velocity - old) ** 2).sum()) for velocity, old in zip(solver.vel, previous)) ** .5
                norm = sum(float((velocity ** 2).sum()) for velocity in solver.vel) ** .5
                records.append(dict(report, time_s=elapsed, step=step, relative_velocity_change=change / max(norm, 1e-12)))
                previous = [velocity.clone() for velocity in solver.vel]
                write(folder / 'wind_progress.json', {'records': records})
                print(f'{folder.name}: wind {elapsed:.1f}/{config["flow_duration_s"]} s, divergence {report["divergence_rms"]:.3g}', flush=True)
                next_record = elapsed + 60
    if max(record['divergence_rms'] for record in records) > 5e-5:
        raise ValueError('Wind divergence quality gate failed')
    faces = [velocity.cpu().numpy() for velocity in solver.vel]
    boundary = inlet.cpu().numpy()
    np.savez_compressed(folder / 'wind_faces.npz', faces=np.asarray(faces), inlet=boundary)
    return face_centres(faces, boundary), {'records': records, 'wall_seconds': time.perf_counter() - started,
                                          'stationarity_established': False,
                                          'model': 'Existing inviscid upwind MAC with pressure projection; no turbulence closure or buoyancy feedback'}


def run(storage, scene, scenario_id, device):
    import torch
    from common.pipeline.scene_temperature_physical import load_solver, fields_and_boundary
    from urban_flow.physics.diurnal_solver import solve_from_state
    from urban_flow.physics.solar.model import ShadowNet, sun_position
    torch.set_num_threads(4)
    config = configuration(storage, scene)
    scenario = next(item for item in config['weather'] if item['id'] == scenario_id)
    geometry = storage.run(scene, read(storage.metadata(scene) / 'configs/geometry_result.json')['run_id'])
    validate(geometry / 'manifest.json')
    roof = np.load(geometry / 'roof.npy')
    weather_path = retained_weather(storage, scene, scenario)
    weather = read(weather_path)
    stamp = scenario['date'] + f'T{scenario["hour_utc"]:02d}:00'
    index = weather['hourly']['time'].index(stamp)
    forcing = {key: values[index] for key, values in weather['hourly'].items() if key != 'time'}
    if not all(value is not None and math.isfinite(value) for value in forcing.values()):
        raise ValueError('Missing weather values; refusing invented forcing')
    if weather['hourly_units']['wind_speed_10m'] != 'm/s' or weather['hourly_units']['temperature_2m'] != '°C':
        raise ValueError('Unexpected weather units')
    rotation = int(math.floor(((270 - forcing['wind_direction_10m']) % 360) / 90 + .5)) % 4
    direction = (270 - rotation * 90) % 360
    forcing.update(time_utc=stamp + 'Z', scenario=scenario_id, modeled_wind_from_deg=direction,
                   wind_direction_error_deg=(direction - forcing['wind_direction_10m'] + 180) % 360 - 180,
                   wind_profile='Uniform inflow at ERA5 10 m speed; nearest cardinal direction required by west-inlet solver',
                   thermal_clock='Elapsed controlled experiment; historical forcing held constant, not a weather replay')
    identity = 'climate_' + scenario_id + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6]
    folder = storage.scratch(scene, 'osm_climate', identity)
    folder.mkdir(parents=True)
    revision = snapshot_sources(storage.root, folder / 'source_snapshot.tar.gz')
    for filename in ('map.osm.xml', 'osm_provenance.json', 'roof.npy', 'geometry_audit.json', 'footprints_local.json'):
        shutil.copy2(geometry / filename, folder / filename)
    shutil.copy2(weather_path, folder / 'weather.json')
    shutil.copy2(weather_path.with_suffix('.provenance.json'), folder / 'weather_provenance.json')
    write(folder / 'config.json', config)
    write(folder / 'forcing.json', forcing)
    cell = config['cell_m']
    solid = np.arange(config['height_m'] // cell)[:, None, None] * cell < roof[None]
    rotated_solid = np.rot90(solid, rotation, axes=(1, 2)).copy()
    wind, flow_report = wind_solve(rotated_solid, forcing['wind_speed_10m'], config, device, folder)
    wind *= ~rotated_solid[None]
    date = datetime.fromisoformat(scenario['date'])
    origin = read(storage.metadata(scene) / 'project.json')['spatial']['origin']
    altitude, azimuth = sun_position(origin['latitude'], origin['longitude'], date.year, date.month, date.day, scenario['hour_utc'] - .5)
    with torch.inference_mode():
        shadow = ShadowNet(roof, cell, device)(altitude, azimuth).cpu().numpy() if altitude > 0 else np.ones_like(roof, dtype=bool)
    irradiance = (~shadow) * forcing['direct_radiation'] + forcing['diffuse_radiation']
    model, _ = load_solver()
    ambient = forcing['temperature_2m']
    excess = model.solve_surface_temperature_excess_c(
        (1 - config['albedo']) * irradiance, np.full_like(roof, config['emissivity']),
        np.zeros_like(roof), np.zeros_like(roof), np.full_like(roof, config['convective_coefficient_w_m2_k']),
        5.670374419e-8 * (ambient + 273.15) ** 4, ambient, 0.)
    fields, boundary = fields_and_boundary(rotated_solid, wind[None], ambient, 0., config['exchange_per_s'])
    rotated_excess = np.rot90(excess, rotation).copy()
    boundary['ground_surface_temperature_excess_c'] = rotated_excess
    boundary['roof_surface_temperature_excess_3d'] = fields['roof_mask_3d'] * rotated_excess[None]
    thermal = model.Temperature3DScenarioConfig(
        temperature_solver_device=device, ambient_temp_c=ambient, inflow_temp_c=ambient,
        frame_duration_s=config['thermal_output_interval_s'], diffusion_coeff_m2_s=config['diffusivity_m2_s'])
    sample = round(config['sample_height_m'] / cell - .5)
    if not math.isclose((sample + .5) * cell, config['sample_height_m']):
        raise ValueError('Requested height is not a grid-cell centre')
    state = np.full(solid.shape, ambient, dtype=np.float32)
    times = np.arange(0, config['thermal_duration_s'] + 1, config['thermal_output_interval_s']).tolist()
    temperatures = [np.rot90(state[sample], -rotation).copy()]
    thermal_reports = []
    for elapsed in times[1:]:
        state, _, report = solve_from_state(model, fields, boundary, SimpleNamespace(model_resolution_m=cell, height_scale_m=cell), thermal, state)
        if not np.isfinite(state).all():
            raise ValueError('Non-finite temperature')
        temperatures.append(np.rot90(state[sample], -rotation).copy())
        thermal_reports.append(report)
        print(f'{identity}: temperature {elapsed}/{config["thermal_duration_s"]} s', flush=True)
    restored = restore_wind(wind, rotation)
    np.savez_compressed(folder / 'volume_fields.npz', wind_enu=restored, temperature_c=np.rot90(state, -rotation, axes=(1, 2)), solid=solid)
    half = config['domain_half_width_m']
    centres = -half + (np.arange(roof.shape[0]) + .5) * cell
    focus = np.flatnonzero((centres >= -1000) & (centres < 1000))
    selection = slice(int(focus[0]), int(focus[-1]) + 1)
    lower = float(-half + focus[0] * cell)
    invalid = solid[sample, selection, selection]
    velocity = restored[:, sample, selection, selection].astype('<f4')
    air = np.asarray(temperatures, dtype='<f4')[:, selection, selection]
    surface = (ambient + excess)[selection, selection].astype('<f4')
    np.save(folder / 'wind.npy', velocity)
    np.save(folder / 'temperature.npy', air)
    np.save(folder / 'surface.npy', surface)
    np.save(folder / 'invalid.npy', invalid.astype('u1'))
    encoding = {'coordinate_frame': 'ENU', 'dtype': '<f4', 'origin_m': [lower, lower, config['sample_height_m']],
                'spacing_m': [cell, cell], 'sample_location': 'cell_center', 'byte_order': 'little', 'compression': 'none'}
    layers = []
    for name, array, kind, axes, sampling, unit in [
        ('wind', velocity, 'vector_field', 'CYX', 'static', 'm/s'),
        ('temperature', air, 'scalar_field', 'TYX', 'linear', 'degC'),
        ('surface', surface, 'scalar_field', 'YX', 'static', 'degC')]:
        layout = dict(encoding, shape=list(array.shape), axes=axes)
        if name != 'surface':
            layout.update(mask_asset='invalid.npy', mask_dtype='|u1', mask_semantics='invalid_nonzero')
        else:
            layout['origin_m'] = [lower, lower, 0.]
            layout['height_asset'] = 'surface_height.npy'
            layout['height_dtype'] = '<f4'
        valid_values = np.linalg.norm(array, axis=0)[~invalid] if name == 'wind' else array[:, ~invalid] if name == 'temperature' else array
        display_range = [float(valid_values.min()), float(valid_values.max())]
        layers.append({'id': name, 'kind': kind, 'format': 'npy', 'asset': name + '.npy', 'sampling': sampling,
                       'field': {'name': 'velocity' if name == 'wind' else name, 'unit': unit}, 'encoding': layout,
                       'display': {'widget': kind, 'capabilities': ['pick', 'legend', 'opacity'], 'range': display_range}})
    np.save(folder / 'surface_height.npy', roof[selection, selection].astype('<f4'))
    summary = {'forcing': forcing, 'flow': flow_report, 'thermal_intervals': thermal_reports,
               'air_final_range_c': [float(air[-1][~invalid].min()), float(air[-1][~invalid].max())],
               'surface_range_c': [float(surface.min()), float(surface.max())],
               'wind_speed_range_m_s': [float(np.linalg.norm(velocity, axis=0)[~invalid].min()), float(np.linalg.norm(velocity, axis=0)[~invalid].max())],
               'sample_height_m': config['sample_height_m'], 'solar_altitude_deg': altitude, 'solar_azimuth_deg': azimuth,
               'limitations': ['Incomplete OSM footprints and mostly assumed building heights; no terrain or tree drag.',
                              'ERA5 coarse-grid forcing, two selected dates; not campus measurements or climatology.',
                              'Cardinal wind approximation, uniform vertical inflow, inviscid solver; no turbulence or grid-convergence claim.',
                              '600-second finite-duration wind and thermal diagnostics; wind frozen during thermal integration.',
                              'Uniform material parameters, no evapotranspiration, no measured thermal validation.']}
    write(folder / 'summary.json', summary)
    result = finish(storage, scene, folder, dict(config, forcing=forcing), revision, layers, times,
                    [{'id': 'osm', 'sha256': digest(folder / 'map.osm.xml')}, {'id': 'weather', 'sha256': digest(weather_path)},
                     {'id': 'geometry', 'sha256': digest(folder / 'roof.npy')}])
    view_id = identity.lower()
    view = {'schema_version': '1.1.0', 'scene_id': scene, 'title': scenario_id + ' · exploratory wind and temperature',
            'time_alignment': 'relative', 'runs': [geometry.name, identity],
            'layers': [{'run_id': geometry.name, 'layer_id': 'geometry', 'visible': True},
                       *[{'run_id': identity, 'layer_id': layer['id'], 'visible': layer['id'] != 'surface'} for layer in layers]],
            'camera': {'position': [1800, -2200, 1800], 'target': [0, 0, 0]}}
    write(storage.metadata(scene) / 'views' / (view_id + '.json'), view)
    if not (storage.metadata(scene) / 'views/default.json').exists():
        write(storage.metadata(scene) / 'views/default.json', view)
    check_view(storage, scene, view_id)
    refresh_catalog(storage)
    write(storage.metadata(scene) / 'configs' / (scenario_id + '_result.json'), {'run_id': identity, 'view_id': view_id, 'summary': summary})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('scene')
    parser.add_argument('--scenario', default='summer')
    parser.add_argument('--device', default='cuda')
    arguments = parser.parse_args()
    storage = Storage.load()
    print(prepare(storage, arguments.scene) if arguments.action == 'prepare'
          else run(storage, arguments.scene, arguments.scenario, arguments.device))


if __name__ == '__main__':
    main()
