#!/usr/bin/env python3
"""Georeference the White City GLB. Step 1 (glb_names): bounding-box centres of the named building nodes of the GLB.
   Step 2: match them to named OSM buildings (Overpass) and fit a similarity transform -> georef.json (scene root).

    python3 georeference.py names <city.glb>      # -> glb_named.json
    uv run --with numpy python3 georeference.py fit  # -> georef.json
"""
import sys
MODE = sys.argv.pop(1) if len(sys.argv) > 1 else "fit"
if MODE == "names":
    import json, struct, sys, collections
    p = sys.argv[1]
    with open(p, 'rb') as f:
        f.read(12); clen, ctype = struct.unpack('<II', f.read(8)); js = json.loads(f.read(clen))
    acc = js['accessors']; meshes = js['meshes']
    by = collections.defaultdict(lambda: [1e9, 1e9, 1e9, -1e9, -1e9, -1e9])
    for n in js['nodes']:
        if 'mesh' not in n: continue
        name = n.get('name', '').split(' | ')[0].strip()
        b = by[name]
        for pr in meshes[n['mesh']]['primitives']:
            a = acc[pr['attributes']['POSITION']]
            for i in range(3): b[i] = min(b[i], a['min'][i]); b[3 + i] = max(b[3 + i], a['max'][i])
    generic = {'yes', 'residential', 'house', 'terrace', 'apartments', 'semidetached_house', 'school', 'retail', 'garages', 'garage', 'commercial', 'hospital', 'service', 'kindergarten', 'train_station', 'roof', 'university', 'industrial', 'office', 'church', 'detached', 'construction', 'shed', 'hotel', 'public', 'warehouse', 'civic', 'sports_centre', 'college', 'greenhouse', 'bridge', 'hut', 'stadium', 'dormitory', 'terrace_house'}
    out = {}
    for name, b in by.items():
        if not name or name.lower().replace(' ', '_') in generic or name[0].islower(): continue
        out[name] = {'cx': (b[0] + b[3]) / 2, 'cz': (b[2] + b[5]) / 2, 'top': b[4], 'dx': b[3] - b[0], 'dz': b[5] - b[2]}
    json.dump(out, open('glb_named.json', 'w'), indent=1)
    print(len(by), 'names,', len(out), 'named buildings')
    for k in list(out)[:60]: print(repr(k), {kk: round(v, 1) for kk, v in out[k].items()})
else:
    import json, math, urllib.request, urllib.parse, re, sys
    import numpy as np
    glb = json.load(open('glb_named.json'))
    q = '[out:json][timeout:90];(way["building"]["name"](51.492,-0.252,51.538,-0.192);relation["building"]["name"](51.492,-0.252,51.538,-0.192););out center tags;'
    data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'urban-world-model-visualiser/1.0 (georeferencing check)', 'Accept': 'application/json'}), timeout=120).read()
    osm = json.loads(data)['elements']
    json.dump(osm, open('osm_named.json', 'w'))
    print('osm named buildings', len(osm))
    norm = lambda s: re.sub(r'\s+', ' ', s.lower().replace('’', "'").replace('saint ', 'st ')).strip()
    byname = {}
    for e in osm:
        if 'center' not in e: continue
        n = norm(e['tags']['name'])
        byname.setdefault(n, []).append(e)
    pairs = []
    for name, b in glb.items():
        n = norm(name.split(' - ')[0])
        cands = byname.get(n)
        if not cands or len(cands) != 1: continue
        e = cands[0]
        pairs.append((name, b['cx'], b['cz'], e['center']['lon'], e['center']['lat'], e['type'], e['id']))
    print('matched', len(pairs))
    lat0, lon0 = 51.5145, -0.224
    R = 6378137.0
    def proj(lon, lat): return ((lon - lon0) * math.pi / 180 * R * math.cos(lat0 * math.pi / 180), (lat - lat0) * math.pi / 180 * R)
    A = np.array([proj(p[3], p[4]) for p in pairs]); B = np.array([[p[1], -p[2]] for p in pairs])   # local (x, y=-z)
    def fit(A, B):
        ma, mb = A.mean(0), B.mean(0); Ac, Bc = A - ma, B - mb
        U, S, Vt = np.linalg.svd(Ac.T @ Bc); d = np.sign(np.linalg.det(Vt.T @ U.T))
        Rm = Vt.T @ np.diag([1, d]) @ U.T; s = (S * [1, d]).sum() / (Ac ** 2).sum()
        t = mb - s * Rm @ ma
        return s, Rm, t
    for it in range(4):
        s, Rm, t = fit(A, B)
        res = np.linalg.norm((s * (Rm @ A.T)).T + t - B, axis=1)
        keep = res < (np.median(res) * 4 + 5)
        print(f'iter {it}: n={len(A)} scale={s:.6f} rot={math.degrees(math.atan2(Rm[1,0], Rm[0,0])):.3f} deg t={t.round(1)} median res={np.median(res):.1f} m p90={np.percentile(res,90):.1f} max={res.max():.0f}')
        A, B = A[keep], B[keep]; pairs = [p for p, k in zip(pairs, keep) if k]
    # residuals of the final fit
    worst = sorted(zip(res[keep] if len(res)==len(keep) else res, [p[0] for p in pairs]), reverse=True)[:5]
    print('worst', worst)
    # local origin (glTF x=0, z=0) in lon/lat: invert
    Ri = Rm.T / s
    def to_lonlat(x, z):
        v = Ri @ (np.array([x, -z]) - t)
        return lon0 + v[0] / (R * math.cos(lat0 * math.pi / 180)) * 180 / math.pi, lat0 + v[1] / R * 180 / math.pi
    out = {'method': 'similarity fit of %d named OSM buildings (Overpass, way/relation centres) to GLB node bounding-box centres, local equirectangular projection around (%.4f, %.4f)' % (len(pairs), lat0, lon0),
           'lat0': lat0, 'lon0': lon0, 'scale': float(s), 'rotation_deg': float(math.degrees(math.atan2(Rm[1, 0], Rm[0, 0]))), 'R': Rm.tolist(), 't': t.tolist(),
           'formula': 'east,north = equirect(lon,lat; lat0,lon0); [x, -z] = scale * R @ [east, north] + t  (glTF x, z)',
           'median_residual_m': float(np.median(res)), 'n_pairs': len(pairs),
           'origin_lonlat': to_lonlat(0, 0), 'grid_sw_corner_lonlat': to_lonlat(-1492, 2548), 'grid_ne_corner_lonlat': to_lonlat(2092, -1036)}
    json.dump(out, open('georef.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))
