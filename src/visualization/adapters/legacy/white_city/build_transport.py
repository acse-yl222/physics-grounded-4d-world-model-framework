#!/usr/bin/env python3
"""Turn the TfL snapshot in transport/raw/ (fetch_tfl.py) into transport/transport.json in the model frame (glTF x, z),
using georef.json (similarity fit of 939 named OSM buildings to the GLB, median residual 1.6 m).

    python3 scenes/white_city/tools/build_transport.py
"""
import json, math, os, re, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCENE = os.path.abspath(os.path.join(HERE, '..'))
RAW = os.path.join(SCENE, 'transport', 'raw')
geo = json.load(open(os.path.join(SCENE, 'georef.json')))
R = 6378137.0; lat0, lon0 = geo['lat0'], geo['lon0']; s = geo['scale']; Rm = geo['R']; t = geo['t']
def to_model(lon, lat):
    e = (lon - lon0) * math.pi / 180 * R * math.cos(lat0 * math.pi / 180); n = (lat - lat0) * math.pi / 180 * R
    x = s * (Rm[0][0] * e + Rm[0][1] * n) + t[0]; y = s * (Rm[1][0] * e + Rm[1][1] * n) + t[1]
    return round(x, 1), round(-y, 1)   # glTF z = -local y
X0, X1, Z0, Z1 = -1492 - 250, 2092 + 250, -1036 - 250, 2548 + 250   # grid plus a margin
inside = lambda p: X0 <= p[0] <= X1 and Z0 <= p[1] <= Z1
def clip(poly):
    """pieces of a polyline whose points fall inside the box (one point of slack at each end so lines leave the frame)"""
    out, cur = [], []
    for i, p in enumerate(poly):
        if inside(p) or (i + 1 < len(poly) and inside(poly[i + 1])) or (i > 0 and inside(poly[i - 1])): cur.append(p)
        elif cur: out.append(cur); cur = []
    if cur: out.append(cur)
    return [c for c in out if len(c) > 1]
COLOURS = {'central': '#DC241F', 'circle': '#FFD300', 'hammersmith-city': '#F3A9BB', 'district': '#007229', 'piccadilly': '#003688', 'bakerloo': '#B36305', 'jubilee': '#A0A5A9',
           'metropolitan': '#9B0056', 'northern': '#000000', 'victoria': '#0098D4', 'elizabeth': '#6950A1', 'mildmay': '#4C7FAE', 'lioness': '#F2A000', 'windrush': '#DC241F', 'weaver': '#9B0056', 'suffragette': '#5BB77A', 'liberty': '#676767'}
MODE_COLOUR = {'tube': '#0019A8', 'overground': '#EE7C0E', 'elizabeth-line': '#6950A1', 'national-rail': '#8F8F8F', 'dlr': '#00A4A7', 'bus': '#E32017', 'tram': '#84B817'}
stops = json.load(open(os.path.join(RAW, 'stops.json'))); routes = json.load(open(os.path.join(RAW, 'routes.json'))); lines = json.load(open(os.path.join(RAW, 'lines.json')))
status = {l['id']: l for l in json.load(open(os.path.join(RAW, 'line_status.json')))}
out = {'snapshot': json.load(open(os.path.join(RAW, 'snapshot.json'))), 'georeference': {k: geo[k] for k in ('method', 'median_residual_m', 'n_pairs', 'rotation_deg', 'scale')},
       'source': 'Transport for London Unified API (https://api.tfl.gov.uk), Powered by TfL Open Data; contains OS data © Crown copyright and database rights', 'stops': [], 'routes': [], 'road_disruptions': [], 'jamcams': [], 'line_status': [], 'arrivals': {}}
seen = set()
for sp in stops:
    x, z = to_model(sp['lon'], sp['lat'])
    if not inside((x, z)) or sp['naptanId'] in seen: continue
    seen.add(sp['naptanId'])
    out['stops'].append({'id': sp['naptanId'], 'name': sp['commonName'], 'type': sp['stopType'], 'modes': sp.get('modes', []), 'lines': [l['id'] for l in sp.get('lines', [])],
                         'indicator': sp.get('indicator'), 'letter': sp.get('stopLetter'), 'towards': next((p['value'] for p in sp.get('additionalProperties', []) if p.get('key') == 'Towards'), None), 'x': x, 'z': z})
for lid, r in routes.items():
    mode = r.get('mode') or lines.get(lid, {}).get('modeName') or 'bus'
    polys = []
    for ls in r['lineStrings']:
        coords = json.loads(ls)                       # "[[[lon,lat],...],...]" (a MultiLineString) or "[[lon,lat],...]"
        parts = coords if coords and isinstance(coords[0][0], list) else [coords]
        for part in parts: polys.extend(clip([to_model(p[0], p[1]) for p in part]))
    if not polys: continue
    # drop duplicate pieces (inbound / outbound share most of the geometry)
    uniq, keys = [], set()
    for p in polys:
        k = (p[0], p[-1], len(p)); k2 = (p[-1], p[0], len(p))
        if k in keys or k2 in keys: continue
        keys.add(k); uniq.append(p)
    st = status.get(lid, {}).get('lineStatuses', [])
    out['routes'].append({'id': lid, 'name': r.get('name') or lid, 'mode': mode, 'colour': COLOURS.get(lid, MODE_COLOUR.get(mode, '#ffffff')),
                          'status': [{'severity': x.get('statusSeverity'), 'description': x.get('statusSeverityDescription'), 'reason': x.get('reason')} for x in st] or None,
                          'stations': [dict(name=x['name'], id=x['id'], **dict(zip(('x', 'z'), to_model(x['lon'], x['lat'])))) for x in r.get('stations', []) if inside(to_model(x['lon'], x['lat']))],
                          'polylines': uniq, 'points': sum(len(p) for p in uniq)})
out['routes'].sort(key=lambda r: (r['mode'] == 'bus', r['name']))
for d in json.load(open(os.path.join(RAW, 'road_disruptions.json'))):
    g = d.get('geography') or {}; pt = d.get('point')
    if isinstance(pt, str):
        try: pt = json.loads(pt)
        except Exception: pt = None
    geom = None
    if g.get('type') == 'Point': geom = {'type': 'Point', 'xz': to_model(*g['coordinates'])}
    elif g.get('type') == 'LineString': geom = {'type': 'LineString', 'xz': [to_model(*p) for p in g['coordinates']]}
    elif g.get('type') == 'Polygon': geom = {'type': 'Polygon', 'xz': [to_model(*p) for p in g['coordinates'][0]]}
    elif pt: geom = {'type': 'Point', 'xz': to_model(pt[0], pt[1])}
    if not geom: continue
    out['road_disruptions'].append({'id': d.get('id'), 'category': d.get('category'), 'subCategory': d.get('subCategory'), 'severity': d.get('severity'), 'location': d.get('location'), 'comments': re.sub(r'<[^>]+>', '', d.get('comments') or ''),
                                    'startDateTime': d.get('startDateTime'), 'endDateTime': d.get('endDateTime'), 'status': d.get('status'), 'geometry': geom})
for c in json.load(open(os.path.join(RAW, 'jamcams.json'))):
    x, z = to_model(c['lon'], c['lat'])
    if not inside((x, z)): continue
    props = {p['key']: p['value'] for p in c.get('additionalProperties', [])}
    out['jamcams'].append({'id': c['id'], 'name': c['commonName'], 'x': x, 'z': z, 'imageUrl': props.get('imageUrl'), 'videoUrl': props.get('videoUrl'), 'view': props.get('view'), 'available': props.get('available')})
ids_here = {r['id'] for r in out['routes']}
for l in status.values():
    if l['id'] in ids_here: out['line_status'].append({'id': l['id'], 'name': l['name'], 'mode': l.get('modeName'), 'status': [x.get('statusSeverityDescription') for x in l.get('lineStatuses', [])]})
for sid, arr in json.load(open(os.path.join(RAW, 'arrivals.json'))).items():
    if sid in seen: out['arrivals'][sid] = [{'line': a.get('lineName'), 'platform': a.get('platformName'), 'destination': a.get('destinationName') or a.get('towards'), 'seconds': a.get('timeToStation'), 'expected': a.get('expectedArrival')} for a in sorted(arr, key=lambda a: a.get('timeToStation', 0))[:12]]
p = os.path.join(SCENE, 'transport', 'transport.json'); json.dump(out, open(p, 'w'), separators=(',', ':'))
print('stops', len(out['stops']), 'routes', len(out['routes']), '(tube/rail', sum(r['mode'] != 'bus' for r in out['routes']), ') points', sum(r['points'] for r in out['routes']), 'disruptions', len(out['road_disruptions']), 'jamcams', len(out['jamcams']), 'stations with arrivals', len(out['arrivals']))
print('wrote', p, os.path.getsize(p) // 1024, 'KB')
for r in out['routes'][:14]: print(' ', r['mode'], r['id'], r['name'], r['points'], 'pts', [s['name'] for s in r['stations']][:6], r['status'] and r['status'][0]['description'])
