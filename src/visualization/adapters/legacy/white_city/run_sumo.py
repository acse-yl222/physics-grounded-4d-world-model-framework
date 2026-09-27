#!/usr/bin/env python3
"""SUMO traffic for the White City scene: random trips on the OSM network (traffic/white_city.net.xml, netconvert with
guessed signals) simulated for one hour via TraCI; vehicle positions and every signal state are recorded once a second.

    cd scenes/white_city && uv run --with eclipse-sumo,numpy python3 tools/run_sumo.py [--period 0.6] [--seconds 3600]

Writes traffic/sim/frames.npz (per second: vehicle id, x, y, angle, speed in SUMO net coordinates) and
traffic/sim/tls.json (signal programme states per second, run-length coded). build_traffic.py turns them into the viewer files.
"""
import argparse, json, os, subprocess, sys, time
import numpy as np
import sumo
sys.path.append(os.path.join(sumo.SUMO_HOME, 'tools'))
import traci
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.abspath(os.path.join(HERE, '..', 'traffic'))
ap = argparse.ArgumentParser(); ap.add_argument('--period', type=float, default=0.6); ap.add_argument('--seconds', type=int, default=3600); ap.add_argument('--seed', type=int, default=42)
a = ap.parse_args()
os.makedirs(os.path.join(T, 'sim'), exist_ok=True)
net = os.path.join(T, 'white_city.net.xml'); trips = os.path.join(T, 'sim', 'trips.rou.xml')
py = sys.executable
subprocess.run([py, os.path.join(sumo.SUMO_HOME, 'tools', 'randomTrips.py'), '-n', net, '-o', trips.replace('.rou.xml', '.trips.xml'), '-r', trips,
                '-b', '0', '-e', str(a.seconds), '-p', str(a.period), '--fringe-factor', '5', '--min-distance', '400', '--validate', '--seed', str(a.seconds + a.seed),
                '--vehicle-class', 'passenger', '--vclass', 'passenger', '--prefix', 'v'], check=True, capture_output=True)
cfg = os.path.join(T, 'sim', 'white_city.sumocfg')
open(cfg, 'w').write(f'''<configuration><input><net-file value="{net}"/><route-files value="{trips}"/></input>
<time><begin value="0"/><end value="{a.seconds}"/><step-length value="1"/></time>
<processing><ignore-route-errors value="true"/><time-to-teleport value="120"/><collision.action value="warn"/></processing>
<report><no-warnings value="true"/><no-step-log value="true"/></report></configuration>''')
sumo_bin = os.path.join(sumo.SUMO_HOME, 'bin', 'sumo')
traci.start([sumo_bin, '-c', cfg, '--seed', str(a.seed), '--threads', '4'])
tls_ids = traci.trafficlight.getIDList()
links = {t: traci.trafficlight.getControlledLinks(t) for t in tls_ids}
json.dump({t: [[list(l[0]) if l else None for l in lk] for lk in links[t]] for t in tls_ids}, open(os.path.join(T, 'sim', 'tls_links.json'), 'w'))
traci.simulation.subscribe([traci.constants.VAR_DEPARTED_VEHICLES_IDS])
ids_all, xs, ys, angs, sps, offsets, lanes = [], [], [], [], [], [0], []
lane_index, last_lane = {}, {}   # lane id -> index; internal (junction) lanes keep the vehicle's last real lane
tls_states = {t: [] for t in tls_ids}   # run-length: [[t0, state], ...]
subs = set(); t0 = time.time(); peak = 0
for step in range(a.seconds):
    traci.simulationStep()
    for v in traci.simulation.getDepartedIDList():
        traci.vehicle.subscribe(v, [traci.constants.VAR_POSITION, traci.constants.VAR_ANGLE, traci.constants.VAR_SPEED, traci.constants.VAR_LANE_ID])
    res = traci.vehicle.getAllSubscriptionResults()
    for v, r in res.items():
        ids_all.append(int(v[1:])); x, y = r[traci.constants.VAR_POSITION]; xs.append(x); ys.append(y); angs.append(r[traci.constants.VAR_ANGLE]); sps.append(r[traci.constants.VAR_SPEED])
        lid = r[traci.constants.VAR_LANE_ID]
        if lid.startswith(':'): lid = last_lane.get(v, lid)
        else: last_lane[v] = lid
        lanes.append(lane_index.setdefault(lid, len(lane_index)))
    offsets.append(len(ids_all)); peak = max(peak, len(res))
    for t in tls_ids:
        s = traci.trafficlight.getRedYellowGreenState(t)
        if not tls_states[t] or tls_states[t][-1][1] != s: tls_states[t].append([step, s])
    if step % 300 == 0: print(f'step {step}: {len(res)} vehicles, {time.time() - t0:.0f} s', flush=True)
traci.close()
np.savez_compressed(os.path.join(T, 'sim', 'frames.npz'), ids=np.array(ids_all, np.int32), x=np.array(xs, np.float32), y=np.array(ys, np.float32), angle=np.array(angs, np.float32), speed=np.array(sps, np.float32), offsets=np.array(offsets, np.int64), lane=np.array(lanes, np.int32))
json.dump([k for k, _ in sorted(lane_index.items(), key=lambda kv: kv[1])], open(os.path.join(T, 'sim', 'lane_ids.json'), 'w'))
json.dump({'seconds': a.seconds, 'period': a.period, 'seed': a.seed, 'peak_vehicles': peak, 'tls': tls_states}, open(os.path.join(T, 'sim', 'tls.json'), 'w'))
print('done: frames', a.seconds, 'records', len(ids_all), 'peak vehicles', peak, 'tls', len(tls_ids), f'{time.time() - t0:.0f} s')
