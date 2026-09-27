#!/usr/bin/env python3
"""Turn the SUMO run (traffic/sim/, run_sumo.py) into the viewer's traffic files, in the model frame (glTF X, Z) through
the scene's georeference (UTM net coordinates -> lon/lat -> model):

    traffic/roads.json               drivable lane ribbons {lanes: [{world_xyz, width_m}]}
    traffic/signal_layer.json        {movements, poles, heads} at the SUMO stop lines (near-side kerb, left-hand traffic)
    traffic/replay/traffic_flow.i16  per second, int16 records [id, x*10, z*10, yaw*10000, speed*100, lane] (world frame)
    traffic/replay/frame_counts.json records per second
    traffic/replay/tls_changes.json  {tls: [[t, state], ...]} signal state change points
    traffic/replay.json              manifest

    cd scenes/white_city && uv run --with eclipse-sumo,numpy,pyproj python3 tools/build_traffic.py
"""
import json, math, os, sys, time
import numpy as np
import sumo
sys.path.append(os.path.join(sumo.SUMO_HOME, 'tools'))
import sumolib
HERE = os.path.dirname(os.path.abspath(__file__)); SCENE = os.path.abspath(os.path.join(HERE, '..')); T = os.path.join(SCENE, 'traffic')
geo = json.load(open(os.path.join(SCENE, 'georef.json')))
R = 6378137.0; lat0, lon0 = geo['lat0'], geo['lon0']; s = geo['scale']; Rm = geo['R']; tt = geo['t']
def ll_to_model(lon, lat):
    e = (lon - lon0) * math.pi / 180 * R * math.cos(lat0 * math.pi / 180); n = (lat - lat0) * math.pi / 180 * R
    x = s * (Rm[0][0] * e + Rm[0][1] * n) + tt[0]; y = s * (Rm[1][0] * e + Rm[1][1] * n) + tt[1]
    return x, -y
net = sumolib.net.readNet(os.path.join(T, 'white_city.net.xml'), withInternal=True)
def to_model(x, y):
    lon, lat = net.convertXY2LonLat(x, y); return ll_to_model(lon, lat)
X0, X1, Z0, Z1 = -1492 - 60, 2092 + 60, -1036 - 60, 2548 + 60
inside = lambda p: X0 <= p[0] <= X1 and Z0 <= p[1] <= Z1
GROUND_Y = 0.26
t0 = time.time()

# ---- lanes (external, passenger) -> ribbons
lanes = []
for e in net.getEdges(withInternal=False):
    for l in e.getLanes():
        if not l.allows('passenger'): continue
        pts = [to_model(x, y) for x, y in l.getShape()]
        if not any(inside(p) for p in pts): continue
        eid = e.getID().lstrip('-').split('#')[0]   # netconvert edge ids carry the OSM way id
        lanes.append({'id': l.getID(), 'way': eid if eid.isdigit() else None, 'width_m': round(l.getWidth(), 2), 'world_xyz': [[round(x, 2), GROUND_Y, round(z, 2)] for x, z in pts]})
json.dump({'schema': 'UWM_WHITE_CITY_TRAFFIC_ROADS_V1', 'coordinate_frame': 'glTF world XYZ (X east, Z south, Y up); lanes drawn at Y=0.26 m', 'source': 'OSM highways (Overpass 2026-09-16) -> netconvert 1.27.1', 'counts': {'lanes': len(lanes)}, 'lanes': lanes}, open(os.path.join(T, 'roads.json'), 'w'), separators=(',', ':'))
print('lanes', len(lanes), f'{time.time() - t0:.0f} s')

# ---- signals: one head per controlled link at the stop line of its incoming lane; one pole per incoming lane (near-side kerb)
# controlled links straight from the net: {tls: [(fromLane, toLane, viaLane) per link index]}
links = {}
for tls in net.getTrafficLights():
    lk = {}
    for in_lane, out_lane, idx in tls.getConnections():
        via = next((c.getViaLaneID() for c in in_lane.getOutgoing() if c.getToLane().getID() == out_lane.getID()), None)
        lk.setdefault(idx, (in_lane.getID(), out_lane.getID(), via or None))
    links[tls.getID()] = [lk.get(i) for i in range(max(lk) + 1)] if lk else []
KERB, HEAD_H, SPACING = 2.3, 3.3, 0.45
poles, heads, movements, pole_index = [], [], [], {}
for tls, lk in links.items():
    for link_index, group in enumerate(lk):
        if not group: continue
        from_lane, to_lane, via = group
        try: L = net.getLane(from_lane)
        except KeyError: continue
        shape = L.getShape()
        if len(shape) < 2: continue
        (ax, ay), (bx, by) = shape[-2], shape[-1]
        dx, dy = bx - ax, by - ay; n = math.hypot(dx, dy) or 1; ux, uy = dx / n, dy / n
        # left-hand traffic: the near-side kerb is on the left of the direction of travel (in SUMO x east / y north: left = (-uy, ux))
        w = L.getWidth() / 2 + KERB
        px, py = bx - uy * w, by + ux * w
        key = from_lane
        if key not in pole_index:
            X, Z = to_model(px, py)
            if not inside((X, Z)): continue
            pole_index[key] = len(poles); poles.append({'lane': from_lane, 'world_xyz': [round(X, 2), GROUND_Y, round(Z, 2)], 'height_m': HEAD_H + 0.6, 'heads': 0})
        p = poles[pole_index[key]]
        # the head hangs on the pole, facing back along the lane (towards approaching traffic): yaw about +Y so that local +Z points at -u
        HX, HZ = to_model(px - ux * 0.3, py - uy * 0.3)
        mx, mz = to_model(ax, ay); ex, ez = to_model(bx, by)
        yaw = math.atan2(mx - ex, mz - ez)   # direction from the stop line back to the approach, as a yaw about +Y (local +Z faces it)
        heads.append({'pole': pole_index[key], 'tls_id': tls, 'link_index': link_index, 'world_xyz': [round(HX, 2), round(GROUND_Y + HEAD_H - p['heads'] * SPACING, 2), round(HZ, 2)], 'yaw_rad': round(yaw, 4)})
        p['heads'] += 1
        # movement path: the internal (via) lane if present, else stop line -> start of the target lane
        path = None
        if via:
            try: path = net.getLane(via).getShape()
            except KeyError: path = None
        if not path:
            try: path = [shape[-1], net.getLane(to_lane).getShape()[0]]
            except KeyError: path = None
        if path: movements.append({'tls_id': tls, 'link_index': link_index, 'world_shape_xyz': [[round(x, 2), GROUND_Y + 0.13, round(z, 2)] for x, z in (to_model(*q) for q in path)]})
json.dump({'schema': 'UWM_WHITE_CITY_SIGNAL_LAYER_V1', 'coordinate_frame': 'glTF world XYZ (X east, Z south, Y up); ground Y=0.26 m',
           'timing_interface': 'state = latest tls_frames.jsonl row with t <= replay t, states[tls_id][link_index]; r/R red, y/Y amber, g/G green',
           'claim': 'Synthetic SUMO signal programmes (netconvert guessed signals, actuated default); pole and head positions are demo placements at SUMO stop lines, not surveyed TfL signal poles.',
           'counts': {'tls': len(links), 'poles': len(poles), 'heads': len(heads), 'movements': len(movements)}, 'movements': movements, 'poles': poles, 'heads': heads},
          open(os.path.join(T, 'signal_layer.json'), 'w'), separators=(',', ':'))
print('signals: tls', len(links), 'poles', len(poles), 'heads', len(heads), 'movements', len(movements), f'{time.time() - t0:.0f} s')

# ---- vehicle frames
sim = np.load(os.path.join(T, 'sim', 'frames.npz')); meta = json.load(open(os.path.join(T, 'sim', 'tls.json')))
ids, xs, ys, ang, sp, off = sim['ids'], sim['x'], sim['y'], sim['angle'], sim['speed'], sim['offsets']
lane_ids = json.load(open(os.path.join(T, 'sim', 'lane_ids.json'))); lane_pos = {l['id']: i for i, l in enumerate(lanes)}
lane_map = np.array([lane_pos.get(lid, -1) for lid in lane_ids], np.int32); lane_rec = lane_map[sim['lane']]   # record -> index into roads.json lanes (-1 = unknown)
# vectorised UTM -> lon/lat via pyproj (sumolib's converter is per point)
from pyproj import Proj
proj = Proj(net.getGeoProj().srs) if hasattr(net.getGeoProj(), 'srs') else net.getGeoProj()
ox, oy = net.getLocationOffset()
lon, lat = proj(xs.astype(np.float64) - ox, ys.astype(np.float64) - oy, inverse=True)
e = (lon - lon0) * math.pi / 180 * R * math.cos(lat0 * math.pi / 180); n = (lat - lat0) * math.pi / 180 * R
X = s * (Rm[0][0] * e + Rm[0][1] * n) + tt[0]; Z = -(s * (Rm[1][0] * e + Rm[1][1] * n) + tt[1])
yaw = math.pi - np.radians(ang)   # SUMO angle: degrees clockwise from north; same convention as the South Kensington replay
# compact binary: int16 x 6 per record [id, x*10, z*10, yaw*10000, speed*100, lane index] (12 bytes, 0.1 m / 0.01 m/s resolution)
M = 200; keep = np.isfinite(X) & np.isfinite(Z) & (X > -1492 - M) & (X < 2092 + M) & (Z > -1036 - M) & (Z < 2548 + M)
counts = np.array([int(keep[off[i]:off[i + 1]].sum()) for i in range(len(off) - 1)])
print('dropped', int((~keep).sum()), 'records (no position or outside the model)')
yaw = np.arctan2(np.sin(yaw), np.cos(yaw))
rec = np.stack([ids, np.round(X * 10), np.round(Z * 10), np.round(yaw * 10000), np.round(np.clip(sp, 0, 300) * 100), lane_rec], axis=1)[keep]
assert np.abs(rec).max() < 32768, 'record field out of int16 range'
rec = rec.astype(np.int16)
os.makedirs(os.path.join(T, 'replay'), exist_ok=True)
for f in ('traffic_flow.f32', 'frames_index.json', 'tls_frames.jsonl'):
    if os.path.exists(os.path.join(T, 'replay', f)): os.remove(os.path.join(T, 'replay', f))
rec.tofile(os.path.join(T, 'replay', 'traffic_flow.i16'))
json.dump(counts.tolist(), open(os.path.join(T, 'replay', 'frame_counts.json'), 'w'))
# signal states as change points: {tls: [[t, state], ...]}; the viewer expands them
json.dump({'seconds': meta['seconds'], 'tls': meta['tls']}, open(os.path.join(T, 'replay', 'tls_changes.json'), 'w'), separators=(',', ':'))
man = {'schema': 'UWM_WHITE_CITY_TRAFFIC_REPLAY_V2', 'generated': time.strftime('%Y-%m-%dT%H:%M'), 'seconds': meta['seconds'], 'frames': len(counts), 'records': int(len(rec)),
       'binary': 'replay/traffic_flow.i16: int16 x 6 per record [id, x*10, z*10, yaw*10000, speed*100, lane_index]; frame_counts.json gives the records per second in order', 'signals': 'replay/tls_changes.json: {tls: [[t, state], ...]} change points',
       'coordinate_frame': 'glTF world XYZ; records are vehicle centres; yaw about +Y (pi - SUMO angle)',
       'vehicles_peak': meta['peak_vehicles'], 'trips_period_s': meta['period'], 'seed': meta['seed'],
       'method': 'SUMO 1.27.1 (eclipse-sumo pip), OSM highways -> netconvert (--tls.guess-signals, actuated default programmes), randomTrips (fringe factor 5, min distance 400 m), 1 s steps, TraCI recording',
       'claim': 'Synthetic demand and synthetic signal timings on the OSM network; not observed White City traffic.'}
json.dump(man, open(os.path.join(T, 'replay.json'), 'w'), indent=1)
print('frames', len(counts), 'records', len(rec), 'bytes', rec.nbytes, f'{time.time() - t0:.0f} s')
