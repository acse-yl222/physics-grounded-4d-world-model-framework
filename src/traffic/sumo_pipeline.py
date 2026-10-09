"""Shared, retained-input SUMO experiments for both city scenes.

python -m traffic.sumo_pipeline fetch south_ken
python -m traffic.sumo_pipeline run south_ken --retain
All demand is explicitly synthetic unless a measured demand source is supplied in
a future calibrated adapter. Historical replays are never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import numpy as np

from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote, refresh_catalog
from common.storage import Storage, scene_id, within


def configuration(storage, scene):
    scene = scene_id(scene)
    cfg = json.loads((storage.metadata(scene) / 'configs/traffic.json').read_text())
    if cfg['schema_version'] != 'city-traffic-1' or cfg['scene_id'] != scene:
        raise ValueError('Traffic configuration identity mismatch')
    if cfg['network'] != {'left_hand': True, 'signals': 'guessed_actuated'}:
        raise ValueError('This adapter requires explicit left-hand, guessed-actuated settings')
    return cfg


def lonlat_to_scene(lonlat, transform):
    points = np.asarray(lonlat, dtype=float)
    if transform.get('kind') == 'projected_affine':
        from pyproj import Transformer
        projection = Transformer.from_crs('EPSG:4326', transform['crs'], always_xy=True)
        projected = np.column_stack(projection.transform(points[:,0], points[:,1]))
        return projected @ np.asarray(transform['matrix']).T + transform['offset']
    if transform.get('kind') == 'aeqd':
        from pyproj import Transformer
        projection = Transformer.from_crs('EPSG:4326', transform['crs'], always_xy=True)
        return np.column_stack(projection.transform(points[:,0], points[:,1]))
    scale = transform['metres_per_degree']
    en = (points - [transform['lon0'], transform['lat0']]) * [
        scale * math.cos(math.radians(transform['lat0'])), scale]
    return en @ np.asarray(transform['R']).T * transform['scale'] + transform['t']


def scene_to_lonlat(xy, transform):
    if transform.get('kind') == 'projected_affine':
        from pyproj import Transformer
        points = (np.asarray(xy) - transform['offset']) @ np.linalg.inv(np.asarray(transform['matrix'])).T
        projection = Transformer.from_crs(transform['crs'], 'EPSG:4326', always_xy=True)
        return np.column_stack(projection.transform(points[:,0], points[:,1]))
    if transform.get('kind') == 'aeqd':
        from pyproj import Transformer
        points = np.asarray(xy, dtype=float)
        projection = Transformer.from_crs(transform['crs'], 'EPSG:4326', always_xy=True)
        return np.column_stack(projection.transform(points[:,0], points[:,1]))
    en = (np.asarray(xy) - transform['t']) @ np.linalg.inv(np.asarray(transform['R'])).T / transform['scale']
    scale = transform['metres_per_degree']
    return en / [scale * math.cos(math.radians(transform['lat0'])), scale] + [transform['lon0'], transform['lat0']]


def fetch_osm(storage, scene, endpoint='https://api.openstreetmap.org/api/0.6/map'):
    import requests
    cfg = configuration(storage, scene)
    target = within(storage.assets(scene, 'input'), cfg['osm_snapshot'])
    if target.exists():
        meta = json.loads(target.with_suffix('.provenance.json').read_text())
        if meta['sha256'] != digest(target):
            raise ValueError('OSM snapshot checksum changed')
        return target
    spatial = json.loads((storage.metadata(scene) / 'project.json').read_text())['spatial']
    lo, hi = spatial['bounds_m']['min'], spatial['bounds_m']['max']; b = cfg['buffer_m']
    corners = scene_to_lonlat([[x, y] for x in (lo[0]-b, hi[0]+b) for y in (lo[1]-b, hi[1]+b)], cfg['transform'])
    west, south = corners.min(axis=0); east, north = corners.max(axis=0)
    query = (f'[out:xml][timeout:180];way["highway"]({south},{west},{north},{east})->.roads;'
             '(.roads;rel(bw.roads)["type"="restriction"];);(._;>>;);out body;')
    params = {'bbox': f'{west},{south},{east},{north}'} if endpoint.endswith('/api/0.6/map') else {'data': query}
    headers = {'User-Agent': 'PhysicsGroundedUrbanResearch/0.1 (local SUMO scenario preparation)'}
    tiles = []
    if endpoint.endswith('/api/0.6/map'):
        # OSM's map endpoint limits the number of nodes per request. Small tiles
        # keep requests bounded; preserve every response and reject mixed versions.
        document = ET.Element('osm', version='0.6', generator='city-traffic-tile-merge')
        seen = {}
        target.parent.mkdir(parents=True, exist_ok=True)
        for row in range(4):
            for col in range(4):
                bbox = [west+(east-west)*col/4, south+(north-south)*row/4,
                        west+(east-west)*(col+1)/4, south+(north-south)*(row+1)/4]
                tile = target.parent/f'tile_{row}_{col}.osm.xml'
                if not tile.exists():
                    response = requests.get(endpoint, params={'bbox': ','.join(map(str,bbox))}, timeout=60, headers=headers)
                    response.raise_for_status()
                    parsed = ET.fromstring(response.content)
                    if parsed.tag != 'osm': raise ValueError('Invalid OSM tile')
                    tile.write_bytes(response.content)
                parsed = ET.parse(tile).getroot()
                tiles.append({'file':tile.name,'sha256':digest(tile),'bbox':bbox})
                for element in parsed:
                    if element.tag not in ('node','way','relation'): continue
                    key = (element.tag, element.get('id'))
                    if key in seen:
                        if seen[key].get('version') != element.get('version'):
                            raise ValueError('OSM changed during tiled fetch; use a new snapshot directory')
                    else: seen[key] = element; document.append(element)
                print(f'{scene}: OSM tile {row*4+col+1}/16',flush=True)
        content = ET.tostring(document,encoding='utf-8',xml_declaration=True)
    else:
        response = requests.get(endpoint, params=params, timeout=210, headers=headers)
        response.raise_for_status(); content=response.content; document=ET.fromstring(content)
    if document.tag != 'osm' or document.find('remark') is not None or not document.findall('way'):
        raise ValueError('Overpass did not return a complete road snapshot')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(content)
    write(target.with_suffix('.provenance.json'), {
        'url': endpoint, 'query': params, 'tiles': tiles, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
        'sha256': digest(target), 'license': 'OpenStreetMap contributors, ODbL 1.0',
        'bbox_wgs84': [west, south, east, north], 'ways': len(document.findall('way'))})
    return target


def runtime():
    import sumo
    return Path(sumo.SUMO_HOME)


def command(args, folder, name):
    with (folder / f'{name}.log').open('w') as log:
        subprocess.run([str(a) for a in args], cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)


def clip_segment(a, b, bounds):
    """Liang-Barsky clipping in scene XY; preserve roads crossing the view boundary."""
    a=np.asarray(a,float);b=np.asarray(b,float);delta=b-a;start,end=0.,1.
    for axis in (0,1):
        if abs(delta[axis])<1e-12:
            if not bounds['min'][axis]<=a[axis]<=bounds['max'][axis]:return None
        else:
            lo=(bounds['min'][axis]-a[axis])/delta[axis];hi=(bounds['max'][axis]-a[axis])/delta[axis]
            start=max(start,min(lo,hi));end=min(end,max(lo,hi))
    return (a+start*delta,a+end*delta) if start<=end else None


def network_mesh(net, to_xy, bounds):
    positions, triangles = [], []
    for edge in net.getEdges():
        for lane in edge.getLanes():
            if not lane.allows('passenger'):
                continue
            xy = to_xy(lane.getShape())
            for a, b in zip(xy[:-1], xy[1:]):
                clipped=clip_segment(a,b,bounds)
                if clipped is None:continue
                a,b=clipped
                delta = b - a; length = np.linalg.norm(delta)
                if length < 1e-6:
                    continue
                normal = np.array([-delta[1], delta[0]]) / length * lane.getWidth() / 2
                start = len(positions)
                positions.extend([[float(p[0]), float(p[1]), .15] for p in (a-normal, a+normal, b+normal, b-normal)])
                triangles.extend([[start, start+1, start+2], [start, start+2, start+3]])
    return {'positions': positions, 'triangles': triangles}


def validate_settings(cfg):
    for name in ('duration_s', 'step_s'):
        if not math.isfinite(cfg[name]) or cfg[name] <= 0:
            raise ValueError(f'{name} must be positive and finite')
    if abs(cfg['duration_s'] / cfg['step_s'] - round(cfg['duration_s'] / cfg['step_s'])) > 1e-8:
        raise ValueError('Duration must be an integer number of steps')
    factor = cfg['intervention']['speed_factor']
    if not math.isfinite(factor) or not 0 < factor <= 2:
        raise ValueError('speed_factor must be in (0, 2]')
    if not math.isfinite(cfg['demand']['period_s']) or cfg['demand']['period_s'] <= 0:
        raise ValueError('Demand period must be positive')
    if cfg['demand']['calibration_status'] != 'synthetic_uncalibrated':
        raise ValueError('Random trips cannot be labelled calibrated')


def run(storage, scene, *, duration=None, speed_factor=None, retain=False, seed=None, demand_period=None, simulation_step=None, safe_following=False, osm_snapshot=None, transform_json=None, separate_junctions=False, closures_json=None, demand_trips=None):
    import sumolib
    import traci
    cfg = configuration(storage, scene)
    cfg['separate_junctions'] = separate_junctions
    if demand_trips: cfg['fixed_demand_input']={'source':str(demand_trips),'sha256':digest(Path(demand_trips)),'note':'Same seeded origin/destination/departure requests rerouted around conservative closures; unreachable trips omitted and reported by duarouter.'}
    if closures_json: cfg['conservative_closures'] = json.loads(Path(closures_json).read_text())
    if osm_snapshot is not None: cfg['osm_snapshot'] = osm_snapshot
    if transform_json is not None: cfg['transform'] = json.loads(Path(transform_json).read_text())
    if duration is not None: cfg['duration_s'] = duration
    if speed_factor is not None: cfg['intervention']['speed_factor'] = speed_factor
    if seed is not None: cfg['seed'] = seed
    if demand_period is not None:
        cfg['demand']['period_s'] = demand_period
        cfg['limitations'] = [x for x in cfg.get('limitations',[]) if 'requested trips' not in x]
        cfg['limitations'].append(f"{cfg['duration_s']:g}s seeded passenger demand with {math.ceil(cfg['duration_s']/demand_period)} requested trips; not measured.")
    if simulation_step is not None:
        if simulation_step<=0 or simulation_step>cfg['step_s']: raise ValueError('Invalid simulation step')
        cfg['simulation_step_s']=simulation_step
    if safe_following: cfg['car_following']={'tau':'2','minGap':'3','sigma':'0.2','decel':'4.5','emergencyDecel':'9','jmTimegapMinor':'2','jmCrossingGap':'10','impatience':'0','jmAdvance':'0','jmExtraGap':'5','jmStoplineGap':'3'}
    validate_settings(cfg)
    raw = within(storage.assets(scene, 'input'), cfg['osm_snapshot'])
    raw_meta = raw.with_suffix('.provenance.json')
    if not raw.is_file() or not raw_meta.is_file():
        raise FileNotFoundError('Fetch the retained OSM snapshot before running traffic')
    source_meta=json.loads(raw_meta.read_text())
    if source_meta['sha256'] != digest(raw):
        raise ValueError('OSM snapshot checksum changed')
    rid = 'sumo_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6]
    out = storage.scratch(scene, 'traffic', rid); out.mkdir(parents=True)
    print(f'Traffic workspace: {out}', flush=True)
    shutil.copy2(raw, out/'map.osm.xml'); shutil.copy2(raw_meta, out/'osm_provenance.json')
    write(out/'config.json', cfg)
    revision = snapshot_sources(storage.root, out/'source_snapshot.tar.gz')
    home = runtime(); netfile = out/'network.net.xml'
    commands = []
    build = [home/'bin/netconvert', '--osm-files', 'map.osm.xml', '-o', netfile.name,
             '--lefthand', '--geometry.remove', '--roundabouts.guess', '--ramps.guess',
             '--junctions.join', '--tls.guess-signals', '--tls.discard-simple', '--tls.join',
             '--tls.default-type', 'actuated', '--keep-edges.by-vclass', 'passenger',
             '--keep-edges.in-geo-boundary', ','.join(map(str,source_meta['bbox_wgs84'])),
             '--remove-edges.isolated', '--no-turnarounds.except-deadend']
    if separate_junctions: build = [arg for arg in build if arg not in ('--junctions.join','--tls.join')]
    try:
        command(build, out, 'netconvert'); commands.append([str(x) for x in build])
        geometry_net = sumolib.net.readNet(str(netfile))
        if cfg.get('conservative_closures'):
            shutil.copy2(netfile,out/'network_before_closures.net.xml')
            tree=ET.parse(netfile);closed=set(cfg['conservative_closures']['edge_ids']);found=set()
            for edge in tree.getroot().findall('edge'):
                if edge.get('id') in closed:
                    found.add(edge.get('id'))
                    for lane in edge.findall('lane'): lane.attrib.pop('disallow',None);lane.set('allow','authority')
            if found != closed: raise ValueError('Closure edge IDs missing from rebuilt network')
            tree.write(netfile,encoding='utf-8',xml_declaration=True)
        net = sumolib.net.readNet(str(netfile))
        if ET.parse(netfile).getroot().get('lefthand') != 'true':
            raise ValueError('Network is not marked left-hand')
        d = cfg['demand']
        trips = [sys.executable, home/'tools/randomTrips.py', '-n', netfile.name,
                 '-o', 'trips.xml', '-r', 'routes.rou.xml', '-b', '0', '-e', str(cfg['duration_s']),
                 '-p', str(d['period_s']), '--seed', str(cfg['seed']), '--validate',
                 '--fringe-factor', str(d['fringe_factor']), '--min-distance', str(d['min_distance_m']),
                 '--vehicle-class', 'passenger', '--vclass', 'passenger', '--prefix', 'v']
        if demand_trips:
            shutil.copy2(demand_trips,out/'trips.xml')
            trips=[home/'bin/duarouter','--net-file',netfile.name,'--route-files','trips.xml','--output-file','routes.rou.xml','--seed',str(cfg['seed']),'--ignore-errors','--no-step-log']
        command(trips, out, 'demand'); commands.append([str(x) for x in trips])
        if cfg.get('car_following'):
            tree=ET.parse(out/'routes.rou.xml')
            for kind in tree.getroot().findall('vType'):
                for key,value in cfg['car_following'].items(): kind.set(key,value)
            tree.write(out/'routes.rou.xml',encoding='utf-8',xml_declaration=True)
        config = ET.Element('configuration')
        groups = {'input': {'net-file': netfile.name, 'route-files': 'routes.rou.xml'},
                  'time': {'begin': 0, 'end': cfg['duration_s'], 'step-length': cfg.get('simulation_step_s',cfg['step_s'])},
                  'random_number': {'seed': cfg['seed']},
                  'processing': {'time-to-teleport': -1, 'ignore-junction-blocker': -1, 'collision.action': 'warn', 'collision.check-junctions': 'true'},
                  'output': {'tripinfo-output': 'tripinfo.xml', 'tripinfo-output.write-unfinished': 'true',
                             'summary-output': 'summary.xml', 'statistic-output': 'statistics.xml'},
                  'report': {'no-step-log': 'true', 'error-log': 'sumo_errors.log'}}
        for group, values in groups.items():
            node = ET.SubElement(config, group)
            for key, value in values.items(): ET.SubElement(node, key, value=str(value))
        ET.ElementTree(config).write(out/'run.sumocfg', encoding='utf-8', xml_declaration=True)
        offset = np.asarray(net.getLocationOffset())
        projection = net.getGeoProj()
        def to_xy(points):
            xy = np.asarray(points) - offset
            lon, lat = projection(xy[:, 0], xy[:, 1], inverse=True)
            return lonlat_to_scene(np.column_stack((lon, lat)), cfg['transform'])
        project = json.loads((storage.metadata(scene)/'project.json').read_text())
        if 'bounds_m' in cfg:
            project['spatial']['bounds_m'] = cfg['bounds_m']
        bounds=project['spatial']['bounds_m']
        def inside(xy):return (xy[:,0]>=bounds['min'][0])&(xy[:,0]<=bounds['max'][0])&(xy[:,1]>=bounds['min'][1])&(xy[:,1]<=bounds['max'][1])
        write(out/'roads.json', network_mesh(geometry_net, to_xy,bounds))
        write(out/'project.json', project)
        frames, full_frames, times, signal_records, metrics = [], [], [], [], []
        launch = [str(home/'bin/sumo'), '-c', str(out/'run.sumocfg')]
        commands.append(launch)
        # SUMO resolves output paths relative to its configuration, including logs.
        with (out/'sumo.log').open('w') as log:
            traci.start(launch, label=rid, stdout=log)
            connection = traci.getConnection(rid)
            try:
                for edge in net.getEdges():
                    connection.edge.setMaxSpeed(edge.getID(), edge.getSpeed()*cfg['intervention']['speed_factor'])
                for edge in cfg['intervention']['closed_edges']:
                    if not net.hasEdge(edge): raise ValueError(f'Unknown closure edge: {edge}')
                    connection.edge.setDisallowed(edge, ['passenger'])
                tls_ids = sorted(connection.trafficlight.getIDList())
                signal_positions = []
                for tls in tls_ids:
                    lanes = connection.trafficlight.getControlledLanes(tls)
                    endpoints = [connection.lane.getShape(lane)[-1] for lane in sorted(set(lanes))]
                    center = to_xy(endpoints).mean(axis=0)
                    signal_positions.append([float(center[0]), float(center[1]), 3.])
                subscribed=set()
                for sample_index in range(round(cfg['duration_s']/cfg['step_s'])):
                    connection.simulationStep((sample_index+1)*cfg['step_s'])
                    t = connection.simulation.getTime(); ids = sorted(connection.vehicle.getIDList())
                    for vehicle in set(ids)-subscribed:
                        connection.vehicle.subscribe(vehicle,[traci.constants.VAR_POSITION,traci.constants.VAR_SPEED]);subscribed.add(vehicle)
                    observations=connection.vehicle.getAllSubscriptionResults()
                    xy = to_xy([observations[i][traci.constants.VAR_POSITION] for i in ids]) if ids else np.empty((0, 2))
                    full_frames.append({'ids': ids, 'positions': [[float(x), float(y), .275] for x, y in xy]})
                    keep=inside(xy)
                    frames.append({'ids':[i for i,k in zip(ids,keep) if k], 'positions':[[float(x),float(y),.275] for x,y in xy[keep]]})
                    times.append(t)
                    signal_records.append({i: connection.trafficlight.getRedYellowGreenState(i) for i in tls_ids})
                    speeds = [observations[i][traci.constants.VAR_SPEED] for i in ids]
                    metrics.append({'time_s': t, 'active': len(ids), 'halted': sum(v < .1 for v in speeds),
                                    'mean_speed_m_s': float(np.mean(speeds)) if speeds else 0.,
                                    'arrived': connection.simulation.getArrivedNumber(),
                                    'departed': connection.simulation.getDepartedNumber(),
                                    'collisions': connection.simulation.getCollidingVehiclesNumber(),
                                    'teleports': connection.simulation.getStartingTeleportNumber()})
            finally:
                connection.close()
        write(out/'trajectories.json', {'frames': frames})
        write(out/'trajectories_full.json', {'frames':full_frames,'note':'Full buffered-network recording; displayed trajectories are cropped to the scene bounds.'})
        write(out/'signals.json', {'samples': times, 'states': signal_records, 'note': 'Guessed actuated programmes, not TfL observations'})
        write(out/'metrics.json', metrics)
        visible_tls=[i for i,p in enumerate(signal_positions) if bounds['min'][0]<=p[0]<=bounds['max'][0] and bounds['min'][1]<=p[1]<=bounds['max'][1]]
        write(out/'signal_values.json', {'positions': [signal_positions[i] for i in visible_tls],
              'values': [[sum(c.lower()=='r' for c in frame[tls_ids[i]])/max(1,len(frame[tls_ids[i]])) for i in visible_tls] for frame in signal_records]})
        write(out/'counts.json', {'labels':['active','halted','arrived','departed'],
                                 'values':[[m[k] for k in ('active','halted','arrived','departed')] for m in metrics]})
        trips_xml = ET.parse(out/'tripinfo.xml').getroot().findall('tripinfo')
        finished = [x for x in trips_xml if float(x.get('arrival', '-1')) >= 0]
        generated = len(ET.parse(out/'routes.rou.xml').getroot().findall('vehicle'))
        totals = {k: sum(m[k] for m in metrics) for k in ('arrived', 'departed', 'collisions', 'teleports')}
        stats = ET.parse(out/'statistics.xml').getroot()
        totals.update(arrived=len(finished), departed=len(trips_xml), collisions=int(stats.find('safety').get('collisions')), teleports=int(stats.find('teleports').get('total')), safety_count_basis='Final SUMO aggregate across every internal step; collision events, not sampled colliding-vehicle counts')
        totals.update(generated=generated, requested=math.ceil(cfg['duration_s']/d['period_s']),
                      finished_mean_duration_s=float(np.mean([float(x.get('duration')) for x in finished])) if finished else None,
                      unfinished=sum(float(x.get('arrival', '-1')) < 0 for x in trips_xml),
                      vehicle_seconds=sum(m['active']*cfg['step_s'] for m in metrics),
                      halted_vehicle_seconds=sum(m['halted']*cfg['step_s'] for m in metrics),
                      calibration_status=d['calibration_status'])
        write(out/'summary.json', totals)
        write(out/'commands.json', {'commands': commands, 'runtime_version': subprocess.check_output([str(home/'bin/sumo'), '--version'], text=True),
                                    'reproduction': 'Install requirements-sumo.txt, restore source snapshot, use retained OSM/config; run traffic.sumo_pipeline. Interventions are applied through TraCI, not run.sumocfg alone.'})
        layers = [{'id': 'traffic', 'kind': 'trajectories', 'format': 'trajectory_frames', 'asset': 'trajectories.json', 'sampling': 'linear', 'display': {'widget': 'trajectories', 'capabilities': ['pick', 'opacity']}},
                  {'id': 'roads', 'kind': 'mesh', 'format': 'json', 'asset': 'roads.json', 'sampling': 'static', 'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}]
        if visible_tls:
            layers.append({'id':'signals','kind':'scalar_field','format':'json','asset':'signal_values.json','sampling':'step',
                           'field':{'name':'red_controlled_link_fraction','unit':'1'},'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity'],'range':[0,1]}})
        layers.append({'id':'traffic_counts','kind':'time_series','format':'json','asset':'counts.json','sampling':'step',
                       'field':{'name':'vehicle_count','unit':'1'},'display':{'widget':'time_series','capabilities':['pick']}})
        artifacts = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name not in ('trajectories.json', 'roads.json'):
                artifacts.append({'id': 'source_snapshot' if p.name == 'source_snapshot.tar.gz' else p.name,
                                  'asset': p.name, 'sha256': digest(p), 'media_type': 'application/octet-stream'})
        manifest = {'schema_version': '1.1.0', 'scene_id': scene, 'simulation': 'traffic', 'run_id': rid,
                    'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                    'provenance': {'code_revision': revision, 'dirty': True, 'parameters': cfg,
                                   'inputs': [{'id': 'osm_snapshot', 'sha256': digest(raw)}, {'id': 'configuration', 'sha256': digest(out/'config.json')}]},
                    'spatial': project['spatial'], 'time': {'unit': 's', 'samples': times}, 'layers': layers, 'artifacts': artifacts}
        write(out/'manifest.json', manifest); validate(out/'manifest.json')
        if retain:
            from common.catalog import view as check_view
            geometry_config = storage.metadata(scene)/'configs/geometry_result.json'
            geometry_run = json.loads(geometry_config.read_text())['run_id'] if geometry_config.exists() else 'legacy_web'
            geometry_manifest = json.loads((storage.run(scene, geometry_run)/'manifest.json').read_text())
            if geometry_manifest['scene_id'] != scene or 'geometry' not in {layer['id'] for layer in geometry_manifest['layers']}:
                raise ValueError('Configured traffic geometry does not belong to this scene or lacks its geometry layer')
            out = promote(storage, out)
            view = {'schema_version': '1.1.0', 'scene_id': scene, 'title': 'SUMO · synthetic demand', 'time_alignment': 'relative',
                    'runs': [geometry_run, rid], 'layers': [{'run_id': geometry_run, 'layer_id': 'geometry', 'visible': True},
                    *[{'run_id': rid, 'layer_id': x['id'], 'visible': True} for x in layers]]}
            (storage.metadata(scene)/'views').mkdir(parents=True, exist_ok=True)
            with (storage.metadata(scene)/'views'/f'{rid.lower()}.json').open('x') as f: json.dump(view, f, indent=2)
            check_view(storage, scene, rid.lower())
            refresh_catalog(storage)
            write(storage.metadata(scene)/'configs/traffic_result.json',{'run_id':rid,'view_id':rid.lower(),'summary':totals})
        return out
    except Exception as exc:
        write(out/'failure.json', {'status': 'failed', 'error': str(exc)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['fetch', 'run'])
    parser.add_argument('scene', type=scene_id)
    parser.add_argument('--duration', type=float); parser.add_argument('--speed-factor', type=float)
    parser.add_argument('--demand-period', type=float, help='Assumed seconds between requested trips; uncalibrated'); parser.add_argument('--seed', type=int); parser.add_argument('--retain', action='store_true')
    parser.add_argument('--demand-trips',help='Replay fixed seeded OD/departure requests for conservative rerouting')
    parser.add_argument('--closures-json',help='Explicit conservative traffic-only edge restrictions with diagnostic provenance')
    parser.add_argument('--separate-junctions',action='store_true',help='Preserve separate OSM junctions instead of heuristic merging')
    parser.add_argument('--transform-json', help='Explicit runtime coordinate mapping with provenance; does not mutate project configuration')
    parser.add_argument('--osm-snapshot',help='Retained relative input snapshot override; no scene config mutation')
    parser.add_argument('--simulation-step',type=float); parser.add_argument('--safe-following',action='store_true')
    parser.add_argument('--endpoint', default='https://api.openstreetmap.org/api/0.6/map')
    args = parser.parse_args(); storage = Storage.load()
    if args.action == 'fetch': result = fetch_osm(storage, args.scene, args.endpoint)
    else: result = run(storage, args.scene, duration=args.duration, speed_factor=args.speed_factor, seed=args.seed, retain=args.retain, demand_period=args.demand_period, simulation_step=args.simulation_step, safe_following=args.safe_following, osm_snapshot=args.osm_snapshot, transform_json=args.transform_json, separate_junctions=args.separate_junctions, closures_json=args.closures_json, demand_trips=args.demand_trips)
    print(result)


if __name__ == '__main__': main()
