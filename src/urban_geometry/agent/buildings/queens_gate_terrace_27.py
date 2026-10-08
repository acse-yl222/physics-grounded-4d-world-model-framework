"""27 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material(
        "27 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85
    )
    trim = ctx.material("27 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("27 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("27 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "27 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("27 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
    wall = ctx.mesh("Partitioned mapped shell with real openings")
    roof = ctx.mesh("EA continuous simplified roof")
    detail = ctx.mesh("Estimated frames and cornice")
    entry = ctx.mesh("Estimated single entry leaf and threshold")
    base = feature.get("base_m", 0)
    entrances = []
    count = 0

    def face(m, ps, mat):
        for i in range(1, len(ps) - 1):
            m.face([ps[0], ps[i], ps[i + 1]], mat)

    for zone in DATA[feature["id"]]:
        H = zone["height"]
        for tri in zone["triangles"]:
            face(roof, [(x, y, base + H) for x, y in tri], roofmat)
        for ed in zone["edges"]:
            bottom = ed["bottom"]
            if bottom >= H:
                continue
            a, b = ed["a"], ed["b"]
            L = math.dist(a, b)
            tx = (b[0] - a[0]) / L
            ty = (b[1] - a[1]) / L
            nx, ny = ty, -tx
            angle = math.atan2(ty, tx)

            def p(s, z, d=0):
                return (a[0] + tx * s - nx * d, a[1] + ty * s - ny * d, base + z)

            def box(m, s, z, w, h, mat, d=0.06, depth=0.14):
                m.box(*p(s, z, d), w, depth, h, mat, angle)

            front = ny > 0.9 and a[1] > -205 and L > 2.5
            holes = []
            if front:
                for row, z in enumerate([0.9, 5.5, 10.1, 14.7, 19.3]):
                    for k in range(1 if L < 4 else 2):
                        c = L * (k + 0.5) / (1 if L < 4 else 2)
                        door = feature["id"] == "way-213454186" and row == 0 and k == 0
                        if z >= bottom and z + 2.5 < H - 0.2:
                            holes.append(
                                (
                                    c - 0.65,
                                    c + 0.65,
                                    0.10 if door else z,
                                    2.5 if door else z + 2.5,
                                    door,
                                )
                            )
            cuts = sorted(set([bottom, H] + [h[j] for h in holes for j in [2, 3]]))
            for lo, hi in zip(cuts, cuts[1:]):
                cursor = 0
                intervals = sorted((h[0], h[1]) for h in holes if h[2] <= lo and h[3] >= hi)
                for le, ri in intervals + [(L, L)]:
                    if le > cursor:
                        face(wall, [p(cursor, lo), p(le, lo), p(le, hi), p(cursor, hi)], wallmat)
                    cursor = max(cursor, ri)
            for le, ri, lo, hi, door in holes:
                count += 1
                c = (le + ri) / 2
                w = ri - le
                dep = 0.45 if door else 0.27
                for q, r in [
                    ((le, lo), (ri, lo)),
                    ((ri, lo), (ri, hi)),
                    ((ri, hi), (le, hi)),
                    ((le, hi), (le, lo)),
                ]:
                    face(wall, [p(*q), p(*r), p(*r, dep), p(*q, dep)], trim)
                for s in [le, ri]:
                    box(detail, s, (lo + hi) / 2, 0.065, hi - lo, timber)
                box(detail, c, hi, w, 0.075, timber)
                if door:
                    box(entry, c, (lo + hi) / 2, w, hi - lo, timber, dep, 0.07)
                    for s in [le + 0.10, ri - 0.10]:
                        box(entry, s, 1.3, 0.04, 2.1, timber, dep - 0.045, 0.04)
                    for z in [0.22, 1.03, 2.35]:
                        box(entry, c, z, w - 0.18, 0.04, timber, dep - 0.045, 0.04)
                    entry.beam(
                        p(ri - 0.18, 1.0, dep - 0.1), p(ri - 0.18, 1.22, dep - 0.1), 0.018, metal, 8
                    )
                    box(entry, c, 0.05, w + 0.30, 0.10, trim, -0.28, 0.75)
                    entrances.append(
                        {
                            "name": "27 Queens Gate Terrace estimated east entry",
                            "threshold_xyz": list(p(c, 0.10)),
                            "outward_normal": [nx, ny, 0],
                            "clear_width_m": w - 0.16,
                            "door_leaf_xyz": list(p(c, (lo + hi) / 2, dep)),
                            "door_leaf_depth_m": dep,
                            "landing_depth_m": 0.75,
                            "landing_z_m": 0.10,
                            "supporting_surface": "finite.10m threshold; master street seam pending",
                            "estimated": True,
                        }
                    )
                else:
                    face(
                        wall,
                        [p(le, lo, dep), p(ri, lo, dep), p(ri, hi, dep), p(le, hi, dep)],
                        glass,
                    )
                    box(detail, c, (lo + hi) / 2, 0.06, hi - lo, timber, 0.10, 0.12)
                    box(detail, c, (lo + hi) / 2, w, 0.065, timber, 0.10, 0.12)
                    box(detail, c, lo - 0.07, w + 0.15, 0.12, trim, -0.06, 0.25)
            if front:
                for z, h, dep in [(H - 0.28, 0.15, 0.23), (H - 0.02, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for geo in feature["geometry"]:
        for tri in geo["triangles"]:
            face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "zone_heights_m": [z["height"] for z in DATA[feature["id"]]],
            "true_openings": count,
            "five_storeys_estimated": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "27 consists parentresidual213454186 plus explicitlinkedmain809947754. EachID preservesowngeometry; root registers both.",
            "EA main63samplesmedian24.630 p9526.228; main25.8mplanarapproximation,frontportico4m/rear13.5m and far-rear4m estimated from map, far-rear split uses original edge vertices; portico height typology estimate due contaminatededge returns.",
            "Northwindows/doorposition/optics estimated; no directtargetphoto, contextuallicensedpaletteonly. Sharedpartywallsblank, no equipment/interiorinvented.",
        ],
    }


DATA = {
    "way-213454186": [
        {
            "height": 4.0,
            "triangles": [
                [
                    [358.4648392876843, -203.2425638632849],
                    [358.0695529654622, -200.91948126628995],
                    [354.75396077812184, -201.44805744010955],
                ],
                [
                    [358.4648392876843, -203.2425638632849],
                    [354.75396077812184, -201.44805744010955],
                    [355.1223437420558, -203.79444617871195],
                ],
            ],
            "edges": [
                {
                    "a": [354.75396077812184, -201.44805744010955],
                    "b": [355.1223437420558, -203.79444617871195],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [355.1223437420558, -203.79444617871195],
                    "b": [358.4648392876843, -203.2425638632849],
                    "outer": False,
                    "bottom": 25.8,
                },
                {
                    "a": [358.4648392876843, -203.2425638632849],
                    "b": [358.0695529654622, -200.91948126628995],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [358.0695529654622, -200.91948126628995],
                    "b": [354.75396077812184, -201.44805744010955],
                    "outer": True,
                    "bottom": 0,
                },
            ],
        },
        {
            "height": 13.5,
            "triangles": [
                [
                    [353.7055962762097, -221.14137879386544],
                    [355.0032491966849, -229.2086667334661],
                    [362.41350967332255, -227.9878843454644],
                ],
                [
                    [362.41350967332255, -227.9878843454644],
                    [361.7047546642134, -222.75955759827048],
                    [356.8440922294976, -223.59262008592486],
                ],
                [
                    [356.8440922294976, -223.59262008592486],
                    [356.3788137797965, -220.71549319662154],
                    [353.7055962762097, -221.14137879386544],
                ],
                [
                    [356.8440922294976, -223.59262008592486],
                    [353.7055962762097, -221.14137879386544],
                    [362.41350967332255, -227.9878843454644],
                ],
            ],
            "edges": [
                {
                    "a": [362.41350967332255, -227.9878843454644],
                    "b": [361.7047546642134, -222.75955759827048],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [361.7047546642134, -222.75955759827048],
                    "b": [356.8440922294976, -223.59262008592486],
                    "outer": False,
                    "bottom": 25.8,
                },
                {
                    "a": [356.8440922294976, -223.59262008592486],
                    "b": [356.3788137797965, -220.71549319662154],
                    "outer": False,
                    "bottom": 25.8,
                },
                {
                    "a": [356.3788137797965, -220.71549319662154],
                    "b": [353.7055962762097, -221.14137879386544],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [353.7055962762097, -221.14137879386544],
                    "b": [355.0032491966849, -229.2086667334661],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [355.0032491966849, -229.2086667334661],
                    "b": [362.41350967332255, -227.9878843454644],
                    "outer": False,
                    "bottom": 4.0,
                },
            ],
        },
        {
            "height": 4.0,
            "triangles": [
                [
                    [362.97260189731605, -231.49608104676008],
                    [362.41350967332255, -227.9878843454644],
                    [355.0032491966849, -229.2086667334661],
                ],
                [
                    [362.97260189731605, -231.49608104676008],
                    [355.0032491966849, -229.2086667334661],
                    [355.5541117890971, -232.68377652019262],
                ],
            ],
            "edges": [
                {
                    "a": [355.0032491966849, -229.2086667334661],
                    "b": [355.5541117890971, -232.68377652019262],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [355.5541117890971, -232.68377652019262],
                    "b": [362.97260189731605, -231.49608104676008],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [362.97260189731605, -231.49608104676008],
                    "b": [362.41350967332255, -227.9878843454644],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [362.41350967332255, -227.9878843454644],
                    "b": [355.0032491966849, -229.2086667334661],
                    "outer": False,
                    "bottom": 13.5,
                },
            ],
        },
    ],
    "way-809947754": [
        {
            "height": 25.8,
            "triangles": [
                [
                    [355.1223437420558, -203.79444617871195],
                    [350.50895530253183, -204.551169462502],
                    [352.52529042528477, -217.02242720592767],
                ],
                [
                    [355.1223437420558, -203.79444617871195],
                    [352.52529042528477, -217.02242720592767],
                    [355.70252880465705, -216.51031757239252],
                ],
                [
                    [355.1223437420558, -203.79444617871195],
                    [355.70252880465705, -216.51031757239252],
                    [356.3788137797965, -220.71549319662154],
                ],
                [
                    [355.1223437420558, -203.79444617871195],
                    [356.3788137797965, -220.71549319662154],
                    [356.8440922294976, -223.59262008592486],
                ],
                [
                    [355.1223437420558, -203.79444617871195],
                    [356.8440922294976, -223.59262008592486],
                    [361.7047546642134, -222.75955759827048],
                ],
                [
                    [355.1223437420558, -203.79444617871195],
                    [361.7047546642134, -222.75955759827048],
                    [358.4648392876843, -203.2425638632849],
                ],
            ],
            "edges": [
                {
                    "a": [350.50895530253183, -204.551169462502],
                    "b": [352.52529042528477, -217.02242720592767],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [352.52529042528477, -217.02242720592767],
                    "b": [355.70252880465705, -216.51031757239252],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [355.70252880465705, -216.51031757239252],
                    "b": [356.3788137797965, -220.71549319662154],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [356.3788137797965, -220.71549319662154],
                    "b": [356.8440922294976, -223.59262008592486],
                    "outer": False,
                    "bottom": 13.5,
                },
                {
                    "a": [356.8440922294976, -223.59262008592486],
                    "b": [361.7047546642134, -222.75955759827048],
                    "outer": False,
                    "bottom": 13.5,
                },
                {
                    "a": [361.7047546642134, -222.75955759827048],
                    "b": [358.4648392876843, -203.2425638632849],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [358.4648392876843, -203.2425638632849],
                    "b": [355.1223437420558, -203.79444617871195],
                    "outer": False,
                    "bottom": 4.0,
                },
                {
                    "a": [355.1223437420558, -203.79444617871195],
                    "b": [350.50895530253183, -204.551169462502],
                    "outer": True,
                    "bottom": 0,
                },
            ],
        }
    ],
}
