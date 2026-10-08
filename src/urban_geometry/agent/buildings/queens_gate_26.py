"""26 Queens Gate. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material("26 Queens Gate estimated pale render", (0.76, 0.735, 0.66), 0.85)
    trim = ctx.material("26 Queens Gate pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("26 Queens Gate white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("26 Queens Gate grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material("26 Queens Gate recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24)
    metal = ctx.material("26 Queens Gate dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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

            front = ed["outer"] and nx > 0.9
            holes = []
            if front:
                for row, z in enumerate([0.9, 5.4, 9.9, 14.4, 18.9, 23.4]):
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
                            "name": "26 Queens Gate estimated east entry",
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
                for z, h, dep in [(4.2, 0.14, 0.18), (27.02, 0.15, 0.23), (27.28, 0.16, 0.32)]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
            if front:
                # Listing-supported balconies and orders, simplified dimensions estimated.
                for z in [5.12, 9.62, 18.62]:
                    box(detail, L / 2, z, L, 0.16, trim, -0.30, 0.75)
                    box(detail, L / 2, z + 1.0, L, 0.10, metal, -0.58, 0.08)
                    for j in range(18):
                        box(detail, (j + 0.5) * L / 18, z + 0.5, 0.045, 1.0, metal, -0.58, 0.06)
                for z in [6.65, 11.15]:
                    for f in [0.04, 0.34, 0.66, 0.96]:
                        box(detail, L * f, z, 0.18, 2.6, trim, -0.13, 0.25)
                        box(detail, L * f, z + 1.3, 0.34, 0.18, trim, -0.16, 0.32)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [27.3, 13.0],
            "levels": 6,
            "true_openings": count,
            "roof_status": "EA27.3m main roof and13m rear;18m depth transition estimated",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "Mapped independent residential26, complete6point footprint; no neighboring25/27 merged.",
            "EA183 inset pixels bimodal:lowerrear~13m and main~27.3m. Exact18m inland step and planar roofs estimated.",
            "HE1266042 OGL text confirms26 terrace stucco/orders/balconies. Simple rails and rectangular pilasters approximate these; precise facade bays,door,dimensions and optics estimated.",
            "No direct licensed target street photo; rear hidden unknown, no plant or interior invented.",
        ],
    }


DATA = [
    {
        "height": 27.3,
        "triangles": [
            [
                [470.5431526245217, -145.19591509607304],
                [471.9909332611219, -154.6646371401338],
                [489.7783304307377, -151.90601779147983],
            ],
            [
                [470.5431526245217, -145.19591509607304],
                [489.7783304307377, -151.90601779147983],
                [488.3379666240653, -142.4858030276373],
            ],
        ],
        "edges": [
            {
                "a": [470.5431526245217, -145.19591509607304],
                "b": [471.9909332611219, -154.6646371401338],
                "bottom": 13.0,
                "outer": False,
            },
            {
                "a": [471.9909332611219, -154.6646371401338],
                "b": [489.7783304307377, -151.90601779147983],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [489.7783304307377, -151.90601779147983],
                "b": [488.3379666240653, -142.4858030276373],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [488.3379666240653, -142.4858030276373],
                "b": [470.5431526245217, -145.19591509607304],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
    {
        "height": 13.0,
        "triangles": [
            [
                [457.86911156761926, -147.3347362317145],
                [459.4912158836378, -156.60319857671857],
                [463.572027400136, -146.35775984451175],
            ],
            [
                [463.572027400136, -146.35775984451175],
                [459.4912158836378, -156.60319857671857],
                [471.9909332611219, -154.6646371401338],
            ],
            [
                [463.572027400136, -146.35775984451175],
                [471.9909332611219, -154.6646371401338],
                [470.2287400661735, -145.2437994554639],
            ],
            [
                [470.2287400661735, -145.2437994554639],
                [471.9909332611219, -154.6646371401338],
                [470.5431526245217, -145.19591509607304],
            ],
        ],
        "edges": [
            {
                "a": [471.9909332611219, -154.6646371401338],
                "b": [470.5431526245217, -145.19591509607304],
                "bottom": 27.3,
                "outer": False,
            },
            {
                "a": [470.5431526245217, -145.19591509607304],
                "b": [470.2287400661735, -145.2437994554639],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [470.2287400661735, -145.2437994554639],
                "b": [463.572027400136, -146.35775984451175],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [463.572027400136, -146.35775984451175],
                "b": [457.86911156761926, -147.3347362317145],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [457.86911156761926, -147.3347362317145],
                "b": [459.4912158836378, -156.60319857671857],
                "bottom": 0,
                "outer": True,
            },
            {
                "a": [459.4912158836378, -156.60319857671857],
                "b": [471.9909332611219, -154.6646371401338],
                "bottom": 0,
                "outer": True,
            },
        ],
    },
]
