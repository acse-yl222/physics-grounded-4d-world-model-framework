"""9 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material("9 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85)
    trim = ctx.material("9 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("9 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("9 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "9 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("9 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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
            if front or (ed["outer"] and nx < -0.9 and L > 5):
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
                            "name": "9 Queens Gate Terrace estimated east entry",
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
                for z, h, dep in [(4.2, 0.14, 0.18), (23.02, 0.15, 0.23), (23.28, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [23.3, 13.0],
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
            "Independent mapped fivelevel apartments9 Queens Gate Terrace. Full12point notched footprint retained.",
            "EA69 inset samples median21.773m p9523.495m; main23.3m,rear13m. Transition12m fromnorth estimated, preserving true footprint.",
            "North front5storeys3bays,exactdoor,roofshape andoptics estimated, no directtargetimage. Nearbylicensed pale-rendercontext only.",
            "Shared east boundary blank; exposed west windows estimated; unknown rear blank,no equipment/interior invented.",
        ],
    }


DATA = [
    {
        "height": 23.3,
        "triangles": [
            [
                [435.15093218837865, -190.2776543358341],
                [437.0690547137684, -202.12336680047662],
                [443.11770142032765, -200.793674104847],
            ],
            [
                [435.15093218837865, -190.2776543358341],
                [443.11770142032765, -200.793674104847],
                [443.0382411616156, -188.99382617603987],
            ],
            [
                [443.0382411616156, -188.99382617603987],
                [443.11770142032765, -200.793674104847],
                [444.8205601834925, -200.6166991116479],
            ],
            [
                [443.1720339397242, -201.12997645460487],
                [443.11770142032765, -200.793674104847],
                [437.0690547137684, -202.12336680047662],
            ],
        ],
        "edges": [
            {
                "a": [437.0690547137684, -202.12336680047662],
                "b": [443.1720339397242, -201.12997645460487],
                "bottom": 13.0,
                "outer": False,
            },
            {
                "a": [443.1720339397242, -201.12997645460487],
                "b": [443.11770142032765, -200.793674104847],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [443.11770142032765, -200.793674104847],
                "b": [444.8205601834925, -200.6166991116479],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [444.8205601834925, -200.6166991116479],
                "b": [443.0382411616156, -188.99382617603987],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [443.0382411616156, -188.99382617603987],
                "b": [435.15093218837865, -190.2776543358341],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [435.15093218837865, -190.2776543358341],
                "b": [437.0690547137684, -202.12336680047662],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 13.0,
        "triangles": [
            [
                [437.0690547137684, -202.12336680047662],
                [437.1756995188771, -202.7819710765034],
                [438.54331532283686, -202.56224365904927],
            ],
            [
                [437.0690547137684, -202.12336680047662],
                [438.54331532283686, -202.56224365904927],
                [443.1720339397242, -201.12997645460487],
            ],
            [
                [443.1720339397242, -201.12997645460487],
                [438.54331532283686, -202.56224365904927],
                [443.6379495122237, -204.01385711319745],
            ],
            [
                [445.360771207721, -203.81384301185608],
                [443.6379495122237, -204.01385711319745],
                [442.0481535025174, -210.00998550187796],
            ],
            [
                [445.360771207721, -203.81384301185608],
                [442.0481535025174, -210.00998550187796],
                [446.50357752572745, -211.2858040900901],
            ],
            [
                [446.50357752572745, -211.2858040900901],
                [442.0481535025174, -210.00998550187796],
                [442.37819050077815, -211.90132061205804],
            ],
            [
                [439.8099997920217, -210.36347620096058],
                [442.0481535025174, -210.00998550187796],
                [443.6379495122237, -204.01385711319745],
            ],
            [
                [439.8099997920217, -210.36347620096058],
                [443.6379495122237, -204.01385711319745],
                [438.54331532283686, -202.56224365904927],
            ],
        ],
        "edges": [
            {
                "a": [443.1720339397242, -201.12997645460487],
                "b": [437.0690547137684, -202.12336680047662],
                "bottom": 23.3,
                "outer": False,
            },
            {
                "a": [437.0690547137684, -202.12336680047662],
                "b": [437.1756995188771, -202.7819710765034],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [437.1756995188771, -202.7819710765034],
                "b": [438.54331532283686, -202.56224365904927],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [438.54331532283686, -202.56224365904927],
                "b": [439.8099997920217, -210.36347620096058],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [439.8099997920217, -210.36347620096058],
                "b": [442.0481535025174, -210.00998550187796],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [442.0481535025174, -210.00998550187796],
                "b": [442.37819050077815, -211.90132061205804],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [442.37819050077815, -211.90132061205804],
                "b": [446.50357752572745, -211.2858040900901],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [446.50357752572745, -211.2858040900901],
                "b": [445.360771207721, -203.81384301185608],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [445.360771207721, -203.81384301185608],
                "b": [443.6379495122237, -204.01385711319745],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [443.6379495122237, -204.01385711319745],
                "b": [443.1720339397242, -201.12997645460487],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
]
