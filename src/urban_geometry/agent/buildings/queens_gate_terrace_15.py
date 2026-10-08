"""15 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material(
        "15 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85
    )
    trim = ctx.material("15 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("15 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("15 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "15 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("15 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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

            front = ny > 0.9 and a[1] > -200 and L > 3
            holes = []
            if front:
                for row, z in enumerate([0.9, 5.2, 9.5, 13.8, 18.1]):
                    for k in range(1 if L < 4 else 2):
                        c = L * (k + 0.5) / (1 if L < 4 else 2)
                        door = feature["id"] == "way-213454216" and row == 0 and k == 0
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
                            "name": "15 Queens Gate Terrace estimated east entry",
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
            "15 consists parentresidual213454216 plus explicitlinkedmain809947760. EachID preservesowngeometry; root registers both.",
            "EA main61samplesmedian23.309 p9524.844; main24mplanarapproximation,frontportico4m/rear11m estimated frommap; portico height typology estimate due contaminatededge returns.",
            "Northwindows/doorposition/optics estimated; no directtargetphoto, contextuallicensedpaletteonly. Sharedpartywallsblank, no equipment/interiorinvented.",
        ],
    }


DATA = {
    "way-213454216": [
        {
            "height": 4.0,
            "triangles": [
                [
                    [402.1067387275398, -196.11626403126866],
                    [401.6178757759044, -193.5295536024496],
                    [398.31308632856235, -194.15795582346618],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [398.31308632856235, -194.15795582346618],
                    [398.7360640602419, -196.65812652464956],
                ],
            ],
            "edges": [
                {
                    "a": [398.31308632856235, -194.15795582346618],
                    "b": [398.7360640602419, -196.65812652464956],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [398.7360640602419, -196.65812652464956],
                    "b": [402.1067387275398, -196.11626403126866],
                    "outer": False,
                    "bottom": 24.0,
                },
                {
                    "a": [402.1067387275398, -196.11626403126866],
                    "b": [401.6178757759044, -193.5295536024496],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [401.6178757759044, -193.5295536024496],
                    "b": [398.31308632856235, -194.15795582346618],
                    "outer": True,
                    "bottom": 0,
                },
            ],
        },
        {
            "height": 11.0,
            "triangles": [
                [
                    [398.6276429226855, -221.9828723659739],
                    [406.4178525394527, -220.70284589752555],
                    [405.68960637098644, -216.23244089912623],
                ],
                [
                    [398.6276429226855, -221.9828723659739],
                    [405.68960637098644, -216.23244089912623],
                    [401.3489986228524, -217.0343734147027],
                ],
                [
                    [398.6276429226855, -221.9828723659739],
                    [401.3489986228524, -217.0343734147027],
                    [400.7421597026987, -213.5502885999158],
                ],
                [
                    [398.6276429226855, -221.9828723659739],
                    [400.7421597026987, -213.5502885999158],
                    [397.2864841783885, -214.05088524892926],
                ],
            ],
            "edges": [
                {
                    "a": [406.4178525394527, -220.70284589752555],
                    "b": [405.68960637098644, -216.23244089912623],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [405.68960637098644, -216.23244089912623],
                    "b": [401.3489986228524, -217.0343734147027],
                    "outer": False,
                    "bottom": 24.0,
                },
                {
                    "a": [401.3489986228524, -217.0343734147027],
                    "b": [400.7421597026987, -213.5502885999158],
                    "outer": False,
                    "bottom": 24.0,
                },
                {
                    "a": [400.7421597026987, -213.5502885999158],
                    "b": [397.2864841783885, -214.05088524892926],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [397.2864841783885, -214.05088524892926],
                    "b": [398.6276429226855, -221.9828723659739],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [398.6276429226855, -221.9828723659739],
                    "b": [406.4178525394527, -220.70284589752555],
                    "outer": True,
                    "bottom": 0,
                },
            ],
        },
    ],
    "way-809947760": [
        {
            "height": 24.0,
            "triangles": [
                [
                    [402.1067387275398, -196.11626403126866],
                    [398.7360640602419, -196.65812652464956],
                    [394.2541102388641, -197.3986912239343],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [394.2541102388641, -197.3986912239343],
                    [396.5279187920969, -210.41675870865583],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [396.5279187920969, -210.41675870865583],
                    [400.08340221841354, -209.8009686311707],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [400.08340221841354, -209.8009686311707],
                    [400.7421597026987, -213.5502885999158],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [400.7421597026987, -213.5502885999158],
                    [401.3489986228524, -217.0343734147027],
                ],
                [
                    [402.1067387275398, -196.11626403126866],
                    [401.3489986228524, -217.0343734147027],
                    [405.68960637098644, -216.23244089912623],
                ],
            ],
            "edges": [
                {
                    "a": [394.2541102388641, -197.3986912239343],
                    "b": [396.5279187920969, -210.41675870865583],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [396.5279187920969, -210.41675870865583],
                    "b": [400.08340221841354, -209.8009686311707],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [400.08340221841354, -209.8009686311707],
                    "b": [400.7421597026987, -213.5502885999158],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [400.7421597026987, -213.5502885999158],
                    "b": [401.3489986228524, -217.0343734147027],
                    "outer": False,
                    "bottom": 11.0,
                },
                {
                    "a": [401.3489986228524, -217.0343734147027],
                    "b": [405.68960637098644, -216.23244089912623],
                    "outer": False,
                    "bottom": 11.0,
                },
                {
                    "a": [405.68960637098644, -216.23244089912623],
                    "b": [402.1067387275398, -196.11626403126866],
                    "outer": True,
                    "bottom": 0,
                },
                {
                    "a": [402.1067387275398, -196.11626403126866],
                    "b": [398.7360640602419, -196.65812652464956],
                    "outer": False,
                    "bottom": 4.0,
                },
                {
                    "a": [398.7360640602419, -196.65812652464956],
                    "b": [394.2541102388641, -197.3986912239343],
                    "outer": True,
                    "bottom": 0,
                },
            ],
        }
    ],
}
