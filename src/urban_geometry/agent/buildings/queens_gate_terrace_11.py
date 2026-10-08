"""11 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material(
        "11 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85
    )
    trim = ctx.material("11 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("11 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("11 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "11 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("11 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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
                        door = front and row == 0 and k == 2
                        if z + 2.5 < H - 0.3:
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
                            "name": "11 Queens Gate Terrace estimated east entry",
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
                for z, h, dep in [(4.2, 0.14, 0.18), (22.72, 0.15, 0.23), (22.98, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [23.0, 13.0],
            "levels": 5,
            "true_openings": count,
            "roof_status": "EA23.3m main and14m rear, estimated transition",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "11 Queens Gate Terrace residential5levels complete12point narrow notched footprint; adjacent western bulk excluded fromthisID, not merged.",
            "EA1.5m inset11pixels samples rear only median13.061m. Actualmap narrow main strip20–25m; main23m estimated, rear13m, depth22m transition estimated.",
            "Northfive-storey3bay facade/door and opticalvalues estimated, no directtargetlicensedphoto.",
            "Shared westernboundariesblank,unknown rearblank; no invented equipment/interior.",
        ],
    }


DATA = [
    {
        "height": 23.0,
        "triangles": [
            [
                [415.6983229977777, -193.88892144709826],
                [418.99972000633556, -213.19281397312815],
                [420.26802710427376, -212.95765687085884],
            ],
            [
                [415.6983229977777, -193.88892144709826],
                [420.26802710427376, -212.95765687085884],
                [419.1504612126155, -206.28256640210748],
            ],
            [
                [415.6983229977777, -193.88892144709826],
                [419.1504612126155, -206.28256640210748],
                [420.861631677486, -205.9605266759172],
            ],
            [
                [415.6983229977777, -193.88892144709826],
                [420.861631677486, -205.9605266759172],
                [418.21266849373933, -190.9637901019305],
            ],
            [
                [415.6983229977777, -193.88892144709826],
                [418.21266849373933, -190.9637901019305],
                [412.75429590337444, -191.97582818288356],
            ],
            [
                [415.6983229977777, -193.88892144709826],
                [412.75429590337444, -191.97582818288356],
                [413.14309596957173, -194.3102928493172],
            ],
        ],
        "edges": [
            {
                "a": [418.99972000633556, -213.19281397312815],
                "b": [420.26802710427376, -212.95765687085884],
                "bottom": 13.0,
                "outer": False,
            },
            {
                "a": [420.26802710427376, -212.95765687085884],
                "b": [419.1504612126155, -206.28256640210748],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [419.1504612126155, -206.28256640210748],
                "b": [420.861631677486, -205.9605266759172],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [420.861631677486, -205.9605266759172],
                "b": [418.21266849373933, -190.9637901019305],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [418.21266849373933, -190.9637901019305],
                "b": [412.75429590337444, -191.97582818288356],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [412.75429590337444, -191.97582818288356],
                "b": [413.14309596957173, -194.3102928493172],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [413.14309596957173, -194.3102928493172],
                "b": [415.6983229977777, -193.88892144709826],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [415.6983229977777, -193.88892144709826],
                "b": [418.99972000633556, -213.19281397312815],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 23.0,
        "triangles": [
            [
                [414.8097113710828, -211.04851132817566],
                [411.59298442921136, -211.61785410996526],
                [412.0956130332961, -214.4729059888369],
            ],
            [
                [414.8097113710828, -211.04851132817566],
                [412.0956130332961, -214.4729059888369],
                [415.2942226831096, -213.87985105934575],
            ],
        ],
        "edges": [
            {
                "a": [412.0956130332961, -214.4729059888369],
                "b": [415.2942226831096, -213.87985105934575],
                "bottom": 13.0,
                "outer": False,
            },
            {
                "a": [415.2942226831096, -213.87985105934575],
                "b": [414.8097113710828, -211.04851132817566],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [414.8097113710828, -211.04851132817566],
                "b": [411.59298442921136, -211.61785410996526],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [411.59298442921136, -211.61785410996526],
                "b": [412.0956130332961, -214.4729059888369],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 13.0,
        "triangles": [
            [
                [415.3927420299733, -214.45556876529008],
                [415.2942226831096, -213.87985105934575],
                [412.0956130332961, -214.4729059888369],
            ],
            [
                [415.3927420299733, -214.45556876529008],
                [412.0956130332961, -214.4729059888369],
                [412.9987642240012, -219.6030229041353],
            ],
            [
                [415.3927420299733, -214.45556876529008],
                [412.9987642240012, -219.6030229041353],
                [421.15462620637845, -218.25320969708264],
            ],
            [
                [421.15462620637845, -218.25320969708264],
                [420.26802710427376, -212.95765687085884],
                [418.99972000633556, -213.19281397312815],
            ],
            [
                [421.15462620637845, -218.25320969708264],
                [418.99972000633556, -213.19281397312815],
                [419.10740982647985, -213.82249671313912],
            ],
            [
                [421.15462620637845, -218.25320969708264],
                [419.10740982647985, -213.82249671313912],
                [415.3927420299733, -214.45556876529008],
            ],
        ],
        "edges": [
            {
                "a": [415.2942226831096, -213.87985105934575],
                "b": [412.0956130332961, -214.4729059888369],
                "bottom": 23.0,
                "outer": False,
            },
            {
                "a": [412.0956130332961, -214.4729059888369],
                "b": [412.9987642240012, -219.6030229041353],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [412.9987642240012, -219.6030229041353],
                "b": [421.15462620637845, -218.25320969708264],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [421.15462620637845, -218.25320969708264],
                "b": [420.26802710427376, -212.95765687085884],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [420.26802710427376, -212.95765687085884],
                "b": [418.99972000633556, -213.19281397312815],
                "bottom": 23.0,
                "outer": False,
            },
            {
                "a": [418.99972000633556, -213.19281397312815],
                "b": [419.10740982647985, -213.82249671313912],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [419.10740982647985, -213.82249671313912],
                "b": [415.3927420299733, -214.45556876529008],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [415.3927420299733, -214.45556876529008],
                "b": [415.2942226831096, -213.87985105934575],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
]
