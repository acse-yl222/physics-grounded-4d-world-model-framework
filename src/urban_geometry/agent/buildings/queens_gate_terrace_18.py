"""18 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""

import math


def build(ctx, feature):
    wallmat = ctx.material(
        "18 Queens Gate Terrace estimated pale render", (0.76, 0.735, 0.66), 0.85
    )
    trim = ctx.material("18 Queens Gate Terrace pale trim", (0.83, 0.80, 0.72), 0.78)
    timber = ctx.material("18 Queens Gate Terrace white joinery", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("18 Queens Gate Terrace grey roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material(
        "18 Queens Gate Terrace recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24
    )
    metal = ctx.material("18 Queens Gate Terrace dark hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
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

            front = ed["outer"] and ny < -0.9 and L > 5
            holes = []
            if front:
                for row, z in enumerate([0.9, 6.4, 11.9, 17.4]):
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
                            "name": "18 Queens Gate Terrace estimated south entry",
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
                for z, h, dep in [
                    (4.2, 0.14, 0.18),
                    (H - 0.28, 0.15, 0.23),
                    (H - 0.02, 0.16, 0.32),
                ]:
                    box(detail, L / 2, z, L, h, trim, -0.04, dep)
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], wallmat)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_heights_m": [23.2, 4.5, 14.5],
            "levels": 4,
            "true_openings": count,
            "roof_status": "EA layered roof; simplified transitions14.5m northward from south facade",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay26-txllxt-bremner-2010",
        ],
        "uncertainty": [
            "Mapped independent residential fourlevel18 Queens Gate Terrace; full4point footprint retained without clipping.",
            "EA72samples median21.283,p9523.229. Viewed native map supports main23.2m and rear west4.5m/east14.5m; transition positions approximate: depth14.5m, rear west strip3.8m wide.",
            "Southfour-storey3bay windows and singleentry, opticalvalues estimated; no directtargetphoto, nearbylicensedpalettecontextonly.",
            "East shared blank; west and rear unknown blank, no hidden equipment or interior invented.",
        ],
    }


DATA = [
    {
        "height": 23.2,
        "triangles": [
            [
                (379.367118291324, -154.60305264292901),
                (381.6479701913195, -168.92273487336934),
                (388.3979369158624, -167.88323533628136),
            ],
            [
                (379.367118291324, -154.60305264292901),
                (388.3979369158624, -167.88323533628136),
                (386.16359543134905, -153.55639046973684),
            ],
        ],
        "edges": [
            {
                "a": (388.3979369158624, -167.88323533628136),
                "b": (386.16359543134905, -153.55639046973684),
                "outer": True,
                "bottom": 0,
            },
            {
                "a": (386.16359543134905, -153.55639046973684),
                "b": (379.367118291324, -154.60305264292901),
                "outer": True,
                "bottom": 0,
            },
            {
                "a": (379.367118291324, -154.60305264292901),
                "b": (381.6479701913195, -168.92273487336934),
                "outer": True,
                "bottom": 0,
            },
            {
                "a": (381.6479701913195, -168.92273487336934),
                "b": (388.3979369158624, -167.88323533628136),
                "outer": True,
                "bottom": 0,
            },
        ],
    },
    {
        "height": 4.5,
        "triangles": [
            [
                (383.19670275708535, -154.01329399050132),
                (382.1254188687888, -147.05693630053304),
                (378.2652610798832, -147.68535442184657),
            ],
            [
                (378.2652610798832, -147.68535442184657),
                (379.367118291324, -154.60305264292901),
                (382.1024400599971, -154.1818112015477),
            ],
            [
                (378.2652610798832, -147.68535442184657),
                (382.1024400599971, -154.1818112015477),
                (383.19670275708535, -154.01329399050132),
            ],
        ],
        "edges": [
            {
                "a": (378.2652610798832, -147.68535442184657),
                "b": (379.367118291324, -154.60305264292901),
                "outer": True,
                "bottom": 0,
            },
            {
                "a": (379.367118291324, -154.60305264292901),
                "b": (382.1024400599971, -154.1818112015477),
                "outer": False,
                "bottom": 23.2,
            },
            {
                "a": (382.1024400599971, -154.1818112015477),
                "b": (383.19670275708535, -154.01329399050132),
                "outer": False,
                "bottom": 23.2,
            },
            {
                "a": (383.19670275708535, -154.01329399050132),
                "b": (382.1254188687888, -147.05693630053304),
                "outer": False,
                "bottom": 14.5,
            },
            {
                "a": (382.1254188687888, -147.05693630053304),
                "b": (378.2652610798832, -147.68535442184657),
                "outer": True,
                "bottom": 0,
            },
        ],
    },
    {
        "height": 14.5,
        "triangles": [
            [
                (383.19670275708535, -154.01329399050132),
                (386.16359543134905, -153.55639046973684),
                (385.07508521713316, -146.5767425140366),
            ],
            [
                (383.19670275708535, -154.01329399050132),
                (385.07508521713316, -146.5767425140366),
                (382.1254188687888, -147.05693630053304),
            ],
        ],
        "edges": [
            {
                "a": (385.07508521713316, -146.5767425140366),
                "b": (382.1254188687888, -147.05693630053304),
                "outer": True,
                "bottom": 0,
            },
            {
                "a": (382.1254188687888, -147.05693630053304),
                "b": (383.19670275708535, -154.01329399050132),
                "outer": False,
                "bottom": 4.5,
            },
            {
                "a": (383.19670275708535, -154.01329399050132),
                "b": (386.16359543134905, -153.55639046973684),
                "outer": False,
                "bottom": 23.2,
            },
            {
                "a": (386.16359543134905, -153.55639046973684),
                "b": (385.07508521713316, -146.5767425140366),
                "outer": True,
                "bottom": 0,
            },
        ],
    },
]
