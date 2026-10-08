"""1 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material("1 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85)
    trim = ctx.material("1 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("1 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("1 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "1 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("1 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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

            front = ed["outer"] and ny > 0.9 and L > 5
            holes = []
            if front:
                for row, z in enumerate([0.9, 5.2, 9.5, 13.8, 18.1]):
                    for k in range(3):
                        c = L * (k + 0.5) / 3
                        door = row == 0 and k == 2
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
                            "name": "1 Queens Gate Terrace estimated east entry",
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
                for z, h, dep in [(4.2, 0.14, 0.18), (22.92, 0.15, 0.23), (23.18, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [23.2, 14.0],
            "levels": 5,
            "true_openings": count,
            "roof_status": "EA23.2m main and14m rear, estimated transition",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "Independent mapped fivelevel apartments1 Queens Gate Terrace. Full12point notched footprint retained.",
            "EA75 inset samples median21.397m p9523.356m; main23.2m,rear14m. Transition12m fromnorth estimated, preserving true footprint.",
            "North front5storeys3bays,exactdoor,roofshape andoptics estimated, no directtargetimage. Nearbylicensed pale-rendercontext only.",
            "Shared eastwest boundaries blank; unknown rear blank,no equipment/interior invented.",
        ],
    }


DATA = [
    {
        "height": 23.2,
        "triangles": [
            [
                [463.14991330867633, -185.71336426399648],
                [465.04781082224446, -197.56241253499186],
                [472.65403612249065, -193.92085196916014],
            ],
            [
                [463.14991330867633, -185.71336426399648],
                [472.65403612249065, -193.92085196916014],
                [471.14044747897424, -184.4032434085384],
            ],
            [
                [473.11379384819884, -195.75151159614325],
                [472.65403612249065, -193.92085196916014],
                [471.3870356634725, -196.02963083423674],
            ],
            [
                [471.46388479856915, -196.51043876860828],
                [471.3870356634725, -196.02963083423674],
                [465.04781082224446, -197.56241253499186],
            ],
            [
                [465.04781082224446, -197.56241253499186],
                [471.3870356634725, -196.02963083423674],
                [472.65403612249065, -193.92085196916014],
            ],
        ],
        "edges": [
            {
                "a": [465.04781082224446, -197.56241253499186],
                "b": [471.46388479856915, -196.51043876860828],
                "bottom": 14.0,
                "outer": False,
            },
            {
                "a": [471.46388479856915, -196.51043876860828],
                "b": [471.3870356634725, -196.02963083423674],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [471.3870356634725, -196.02963083423674],
                "b": [473.11379384819884, -195.75151159614325],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [473.11379384819884, -195.75151159614325],
                "b": [472.65403612249065, -193.92085196916014],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [472.65403612249065, -193.92085196916014],
                "b": [471.14044747897424, -184.4032434085384],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [471.14044747897424, -184.4032434085384],
                "b": [463.14991330867633, -185.71336426399648],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [463.14991330867633, -185.71336426399648],
                "b": [465.04781082224446, -197.56241253499186],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 14.0,
        "triangles": [
            [
                [465.04781082224446, -197.56241253499186],
                [466.34405745367985, -205.65520405676216],
                [472.2113053033827, -201.1866880012676],
            ],
            [
                [465.04781082224446, -197.56241253499186],
                [472.2113053033827, -201.1866880012676],
                [471.46388479856915, -196.51043876860828],
            ],
            [
                [473.9176749639446, -200.9204892963171],
                [472.2113053033827, -201.1866880012676],
                [474.08501500077546, -202.01638684421778],
            ],
            [
                [474.9302720061969, -206.81632037926465],
                [474.08501500077546, -202.01638684421778],
                [472.2842712261481, -204.70248019136488],
            ],
            [
                [474.9302720061969, -206.81632037926465],
                [472.2842712261481, -204.70248019136488],
                [472.6227249096846, -207.1725005125627],
            ],
            [
                [466.34405745367985, -205.65520405676216],
                [472.2842712261481, -204.70248019136488],
                [472.2113053033827, -201.1866880012676],
            ],
            [
                [472.2113053033827, -201.1866880012676],
                [472.2842712261481, -204.70248019136488],
                [474.08501500077546, -202.01638684421778],
            ],
        ],
        "edges": [
            {
                "a": [471.46388479856915, -196.51043876860828],
                "b": [465.04781082224446, -197.56241253499186],
                "bottom": 23.2,
                "outer": False,
            },
            {
                "a": [465.04781082224446, -197.56241253499186],
                "b": [466.34405745367985, -205.65520405676216],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [466.34405745367985, -205.65520405676216],
                "b": [472.2842712261481, -204.70248019136488],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [472.2842712261481, -204.70248019136488],
                "b": [472.6227249096846, -207.1725005125627],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [472.6227249096846, -207.1725005125627],
                "b": [474.9302720061969, -206.81632037926465],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [474.9302720061969, -206.81632037926465],
                "b": [474.08501500077546, -202.01638684421778],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [474.08501500077546, -202.01638684421778],
                "b": [473.9176749639446, -200.9204892963171],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [473.9176749639446, -200.9204892963171],
                "b": [472.2113053033827, -201.1866880012676],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [472.2113053033827, -201.1866880012676],
                "b": [471.46388479856915, -196.51043876860828],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
]
