"""10a Jay Mews. EA main roof, uncertain low rear strip preserved.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material("10a Jay Mews estimated pale render", (0.76, 0.735, 0.66), 0.85)
    trim = ctx.material("10a Jay Mews pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("10a Jay Mews white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("10a Jay Mews grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material("10a Jay Mews recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24)
    metal = ctx.material("10a Jay Mews dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
    wall = ctx.mesh("Partitioned mapped shell with real openings")
    roof = ctx.mesh("EA high main roof and estimated low rear")
    detail = ctx.mesh("Estimated frames and cornice")
    entry = ctx.mesh("Estimated single entry leaf and threshold")
    base = feature.get("base_m", 0)
    entrances = []
    count = 0

    def face(m, ps, mat):
        for i in range(1, len(ps) - 1):
            m.face([ps[0], ps[i], ps[i + 1]], mat)

    for zone in DATA:
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

            front = ed["outer"] and nx > 0.9
            holes = []
            if front:
                holes = [(0.45, 3.20, 0.85, 2.75, False), (L - 1.75, L - 0.60, 0.10, 2.50, True)]
                for c in [L * 0.25, L * 0.73]:
                    holes.append((c - 0.65, c + 0.65, 5.40, 7.70, False))
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
                            "name": "10a Jay Mews estimated east entry",
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
                for z, h, dep in [(3.2, 0.14, 0.18), (9.87, 0.15, 0.23), (10.13, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [10.15, 7.5],
            "levels": 2,
            "true_openings": count,
            "rear_roof_status": "estimated lower strip; low/zero EA returns unresolved",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "Full original footprint retained. Main EA roof tightly10.15m; western low/zero returns may indicate footprint or survey mismatch. Rear strip7.5m is conservative low-return interpretation, not measured roof.",
            "Exact facade, entrance and window rhythm not established by licensed close photo. Local pale-mews family context only; all openings and optical values estimated.",
            "South10b and north8 shared boundaries closed; no hidden equipment, interior or school geometry added.",
        ],
    }


DATA = [
    {
        "height": 10.15,
        "triangles": [
            [
                [525.4974913199735, 61.44494389734393],
                [526.4521898057786, 55.93846479623332],
                [530.9235824409407, 62.3444905616343],
            ],
            [
                [530.9235824409407, 62.3444905616343],
                [526.4521898057786, 55.93846479623332],
                [531.8709300615592, 56.88040954340249],
            ],
        ],
        "edges": [
            {
                "a": [525.4974913199735, 61.44494389734393],
                "b": [526.4521898057786, 55.93846479623332],
                "bottom": 7.5,
                "outer": False,
            },
            {
                "a": [526.4521898057786, 55.93846479623332],
                "b": [531.8709300615592, 56.88040954340249],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [531.8709300615592, 56.88040954340249],
                "b": [530.9235824409407, 62.3444905616343],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [530.9235824409407, 62.3444905616343],
                "b": [525.4974913199735, 61.44494389734393],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 7.5,
        "triangles": [
            [
                [523.3966662831372, 61.09666553046554],
                [523.9467762539862, 57.643807341344655],
                [525.4974913199735, 61.44494389734393],
            ],
            [
                [525.4974913199735, 61.44494389734393],
                [523.9467762539862, 57.643807341344655],
                [526.4521898057786, 55.93846479623332],
            ],
            [
                [526.4521898057786, 55.93846479623332],
                [523.9467762539862, 57.643807341344655],
                [524.2980032250052, 55.56400050409138],
            ],
        ],
        "edges": [
            {
                "a": [526.4521898057786, 55.93846479623332],
                "b": [525.4974913199735, 61.44494389734393],
                "bottom": 10.15,
                "outer": False,
            },
            {
                "a": [525.4974913199735, 61.44494389734393],
                "b": [523.3966662831372, 61.09666553046554],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [523.3966662831372, 61.09666553046554],
                "b": [523.9467762539862, 57.643807341344655],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [523.9467762539862, 57.643807341344655],
                "b": [524.2980032250052, 55.56400050409138],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [524.2980032250052, 55.56400050409138],
                "b": [526.4521898057786, 55.93846479623332],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
]
