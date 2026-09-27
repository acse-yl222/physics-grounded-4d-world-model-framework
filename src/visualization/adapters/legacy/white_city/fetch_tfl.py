"""Snapshot of TfL Unified API data around White City (no app key: keep the request rate modest).

    python3 scenes/white_city/tools/fetch_tfl.py      # writes transport/raw/*.json; then run build_transport.py
"""
import json, time, urllib.request, urllib.parse, os, sys
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "transport", "raw"), exist_ok=True)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'transport', 'raw')
LAT, LON, RADIUS = 51.5145, -0.224, 2000
BBOX = (51.492, -0.252, 51.538, -0.192)   # s, w, n, e (a little beyond the 3.6 km grid)
def get(path, **params):
    url = 'https://api.tfl.gov.uk' + path + ('?' + urllib.parse.urlencode(params) if params else '')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'urban-world-model-visualiser'}), timeout=60) as r: return json.loads(r.read())
        except Exception as e:
            print('retry', url, e, file=sys.stderr); time.sleep(3 + 5 * attempt)
    return None
def save(name, obj): json.dump(obj, open(os.path.join(OUT, name), 'w')); print(name, len(obj) if hasattr(obj, '__len__') else '')
snap = {'taken_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'centre': [LAT, LON], 'radius_m': RADIUS, 'bbox_swne': BBOX}
stops = get('/StopPoint', lat=LAT, lon=LON, radius=RADIUS, stopTypes='NaptanPublicBusCoachTram,NaptanMetroStation,NaptanRailStation', returnLines='true') or get('/StopPoint', lat=LAT, lon=LON, radius=1500, stopTypes='NaptanPublicBusCoachTram,NaptanMetroStation,NaptanRailStation')
sp = stops.get('stopPoints', []); save('stops.json', sp)
lines = {}
for s in sp:
    for l in s.get('lines', []): lines.setdefault(l['id'], {'id': l['id'], 'name': l['name']})
for s in sp:
    for m in s.get('modes', []): pass
modes = get('/Line/Mode/tube,overground,elizabeth-line,national-rail,dlr,tram/Status'); save('line_status.json', modes or [])
for l in (modes or []): lines.setdefault(l['id'], {'id': l['id'], 'name': l['name']})['modeName'] = l.get('modeName')
# route geometry of every line serving the area (tube / rail first, then buses)
routes = {}
ids = sorted(lines, key=lambda i: (lines[i].get('modeName') is None, i))
for i, lid in enumerate(ids):
    r = get(f'/Line/{lid}/Route/Sequence/all', serviceTypes='Regular', excludeCrowding='true')
    if not r: continue
    routes[lid] = {'id': lid, 'name': r.get('lineName'), 'mode': r.get('mode'), 'lineStrings': r.get('lineStrings', []), 'stations': [{'id': st['id'], 'name': st['name'], 'lat': st['lat'], 'lon': st['lon']} for st in r.get('stations', [])]}
    lines[lid]['modeName'] = r.get('mode'); time.sleep(0.4)
    if i % 10 == 9: print('routes', i + 1, '/', len(ids), file=sys.stderr)
save('routes.json', routes); save('lines.json', lines)
road = get('/Road/all/Disruption', stripContent='false') or []
def inbox(lat, lon): return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]
def geo_points(g):
    if not g: return []
    c = g.get('coordinates'); t = g.get('type')
    if t == 'Point': return [c]
    if t in ('LineString', 'MultiPoint'): return c
    if t in ('Polygon', 'MultiLineString'): return [p for ring in c for p in ring]
    if t == 'MultiPolygon': return [p for poly in c for ring in poly for p in ring]
    return []
road_in = [d for d in road if any(inbox(p[1], p[0]) for p in geo_points(d.get('geography') or d.get('point') and {'type': 'Point', 'coordinates': json.loads(d['point'])} if isinstance(d.get('point'), str) else d.get('geography')))]
save('road_disruptions.json', road_in); print('road disruptions total', len(road))
cams = get('/Place/Type/JamCam') or []
save('jamcams.json', [c for c in cams if inbox(c['lat'], c['lon'])])
arrivals = {}
for s in sp:
    if s['stopType'] in ('NaptanMetroStation', 'NaptanRailStation'):
        a = get(f"/StopPoint/{s['naptanId']}/Arrivals"); arrivals[s['naptanId']] = a or []; time.sleep(0.3)
save('arrivals.json', arrivals)
save('snapshot.json', snap)
