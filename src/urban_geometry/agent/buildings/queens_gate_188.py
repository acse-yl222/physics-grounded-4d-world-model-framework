"""188 Queen Gate: complete footprint, EA layered roof and moderate evidence-limited stucco frontage."""

import math

ROOF = [
    [
        (507.9392357942707, -31.97258881192452, 26.2),
        (504.49141538259573, -32.57470935955644, 21.4),
        (507.2052175922438, -32.995401888313104, 24.965714285714284),
    ],
    [
        (507.9392357942707, -31.97258881192452, 26.2),
        (507.2052175922438, -32.995401888313104, 24.965714285714284),
        (507.53413609139113, -34.86671496231185, 24.965714285714284),
    ],
    [
        (507.9392357942707, -31.97258881192452, 26.2),
        (507.53413609139113, -34.86671496231185, 24.965714285714284),
        (507.8402520976381, -36.608298017491606, 24.965714285714284),
    ],
    [
        (507.9392357942707, -31.97258881192452, 26.2),
        (507.8402520976381, -36.608298017491606, 24.965714285714284),
        (509.8398357455727, -42.78565510808205, 26.2),
    ],
    [
        (509.8398357455727, -42.78565510808205, 26.2),
        (507.8402520976381, -36.608298017491606, 24.965714285714284),
        (508.1691705967854, -38.479611091490355, 24.965714285714284),
    ],
    [
        (509.8398357455727, -42.78565510808205, 26.2),
        (508.1691705967854, -38.479611091490355, 24.965714285714284),
        (508.4752866030324, -40.22119414667011, 24.965714285714284),
    ],
    [
        (509.8398357455727, -42.78565510808205, 26.2),
        (508.4752866030324, -40.22119414667011, 24.965714285714284),
        (508.8042051021797, -42.092507220668864, 24.965714285714284),
    ],
    [
        (509.8398357455727, -42.78565510808205, 26.2),
        (508.8042051021797, -42.092507220668864, 24.965714285714284),
        (506.3965188987786, -43.41339774709195, 21.4),
    ],
    [
        (506.3965188987786, -43.41339774709195, 21.4),
        (508.8042051021797, -42.092507220668864, 24.965714285714284),
        (506.2434608956551, -42.542606219502076, 21.4),
    ],
    [
        (505.9145423965078, -40.67129314550332, 21.4),
        (508.4752866030324, -40.22119414667011, 24.965714285714284),
        (508.1691705967854, -38.479611091490355, 24.965714285714284),
    ],
    [
        (505.9145423965078, -40.67129314550332, 21.4),
        (508.1691705967854, -38.479611091490355, 24.965714285714284),
        (505.60842639026083, -38.92971009032357, 21.4),
    ],
    [
        (504.49141538259573, -32.57470935955644, 21.4),
        (504.6444733857192, -33.445500887146316, 21.4),
        (507.2052175922438, -32.995401888313104, 24.965714285714284),
    ],
    [
        (507.53413609139113, -34.86671496231185, 24.965714285714284),
        (504.97339188486654, -35.316813961145066, 21.4),
        (505.2795078911135, -37.05839701632482, 21.4),
    ],
    [
        (507.53413609139113, -34.86671496231185, 24.965714285714284),
        (505.2795078911135, -37.05839701632482, 21.4),
        (507.8402520976381, -36.608298017491606, 24.965714285714284),
    ],
    [
        (515.3274223907171, -30.68233049557041, 26.2),
        (507.9392357942707, -31.97258881192452, 26.2),
        (517.2183718458459, -41.440492310203695, 26.2),
    ],
    [
        (517.2183718458459, -41.440492310203695, 26.2),
        (507.9392357942707, -31.97258881192452, 26.2),
        (509.8398357455727, -42.78565510808205, 26.2),
    ],
    [
        (520.450498691022, -30.946467842904134, 20.4),
        (520.2720493479865, -30.89734699577093, 20.59401172983656),
        (518.9552015551599, -31.170816312544044, 22.15340803813427),
    ],
    [
        (520.450498691022, -30.946467842904134, 20.4),
        (518.9552015551599, -31.170816312544044, 22.15340803813427),
        (517.8042799140094, -33.76506835781038, 23.989280330719254),
    ],
    [
        (520.450498691022, -30.946467842904134, 20.4),
        (517.8042799140094, -33.76506835781038, 23.989280330719254),
        (522.1373959126947, -40.54371711161812, 20.4),
    ],
    [
        (522.1373959126947, -40.54371711161812, 20.4),
        (517.8042799140094, -33.76506835781038, 23.989280330719254),
        (517.2183718458459, -41.440492310203695, 26.2),
    ],
    [
        (517.2183718458459, -41.440492310203695, 26.2),
        (517.8042799140094, -33.76506835781038, 23.989280330719254),
        (516.2163666650886, -34.03785321023315, 25.858227644668325),
    ],
    [
        (517.2183718458459, -41.440492310203695, 26.2),
        (516.2163666650886, -34.03785321023315, 25.858227644668325),
        (515.3274223907171, -30.68233049557041, 26.2),
    ],
    [
        (515.3274223907171, -30.68233049557041, 26.2),
        (516.2163666650886, -34.03785321023315, 25.858227644668325),
        (515.6193974574562, -30.631340546533462, 25.85618314487991),
    ],
    [
        (518.9552015551599, -31.170816312544044, 22.15340803813427),
        (517.4932422654238, -32.006621909327805, 23.99151684224575),
        (517.8042799140094, -33.76506835781038, 23.989280330719254),
    ],
    [
        (533.6564699810697, -27.27465593442321, 20.4),
        (530.6640732090455, -27.891106490045782, 20.4),
        (531.0378382385243, -30.01458336319774, 20.4),
    ],
    [
        (533.6564699810697, -27.27465593442321, 20.4),
        (531.0378382385243, -30.01458336319774, 20.4),
        (535.443665773375, -38.11788372788578, 20.4),
    ],
    [
        (535.443665773375, -38.11788372788578, 20.4),
        (531.0378382385243, -30.01458336319774, 20.4),
        (525.0989373825723, -33.33905899710953, 20.4),
    ],
    [
        (535.443665773375, -38.11788372788578, 20.4),
        (525.0989373825723, -33.33905899710953, 20.4),
        (522.1373959126947, -40.54371711161812, 20.4),
    ],
    [
        (522.1373959126947, -40.54371711161812, 20.4),
        (525.0989373825723, -33.33905899710953, 20.4),
        (522.1100461633177, -33.866290383040905, 20.4),
    ],
    [
        (522.1373959126947, -40.54371711161812, 20.4),
        (522.1100461633177, -33.866290383040905, 20.4),
        (520.450498691022, -30.946467842904134, 20.4),
    ],
    [
        (520.450498691022, -30.946467842904134, 20.4),
        (522.1100461633177, -33.866290383040905, 20.4),
        (521.6558256368153, -31.278252088464797, 20.4),
    ],
    [
        (531.0378382385243, -30.01458336319774, 20.4),
        (524.7078664699802, -31.127170422114432, 20.4),
        (525.0989373825723, -33.33905899710953, 20.4),
    ],
]
SOURCES = ["q188-noswan-row-2023", "ea-lidar-composite-2022-tq27ne"]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    origin = ring[1]
    tip = ring[2]
    length = math.dist(origin, tip)
    ux, uy = (tip[0] - origin[0]) / length, (tip[1] - origin[1]) / length
    vx, vy = -uy, ux

    def eave(x, y):
        v = (x - origin[0]) * vx + (y - origin[1]) * vy
        return 21.4 + 4.8 * max(0, min(1, v / 3.5)) - 5.8 * max(0, min(1, (v - 11) / 5))

    brick = ctx.material("188 Queen Gate pale stucco wall", (0.75, 0.73, 0.66), 0.86)
    stucco = ctx.material("188 Queen Gate pale stucco and trim", (0.78, 0.76, 0.68), 0.78)
    roofmat = ctx.material("188 Queen Gate dark slate roof", (0.105, 0.12, 0.135), 0.8)
    glass = ctx.material("188 Queen Gate blue-grey glazing", (0.115, 0.17, 0.19), 0.22, 0, 0.28)
    iron = ctx.material("188 Queen Gate black painted iron", (0.022, 0.025, 0.025), 0.43, 0.70)
    timber = ctx.material("188 Queen Gate dark timber door", (0.09, 0.045, 0.023), 0.65)
    stone = ctx.material("188 Queen Gate estimated stone approach", (0.52, 0.49, 0.44), 0.86)
    wall = ctx.mesh("complete mapped envelope with recessed apertures")
    windows = ctx.mesh("sash glazing and pale surrounds")
    details = ctx.mesh("estimated stucco bands pilasters and portico")
    roof = ctx.mesh("EA informed closed roof with lower rear")
    entry = ctx.mesh("estimated 188 entrance and finite steps")
    for tr in ROOF:
        roof.face([(x, y, base + z) for x, y, z in tr], roofmat)

    def face(m, vs, mat):
        for i in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[i], vs[i + 1]
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            if (
                sum(
                    (u[(k + 1) % 3] * v[(k + 2) % 3] - u[(k + 2) % 3] * v[(k + 1) % 3]) ** 2
                    for k in range(3)
                )
                > 1e-12
            ):
                m.face([a, b, c], mat)

    entrances = []
    for ei, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        L = math.dist(a, b)
        tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = ty, -tx
        angle = math.atan2(ty, tx)

        def pos(s, d, z):
            return (a[0] + tx * s + nx * d, a[1] + ty * s + ny * d, base + z)

        def bx(m, s, d, z, w, dep, h, mat):
            m.box(*pos(s, d, z), w, dep, h, mat, angle)

        def quad(s0, s1, z0, z1, mat):
            face(wall, [pos(s0, 0, z0), pos(s1, 0, z0), pos(s1, 0, z1), pos(s0, 0, z1)], mat)

        n = max(1, int(L / 3.6))
        pitch = L / n
        openings = []
        # Street front rhythm is estimated from partially obscured licensed context image.
        for j in range(n if ei not in [2, 3] else 0):
            s = (j + 0.5) * pitch
            w = min(1.50, pitch * 0.50)
            for row, z in enumerate([1.0, 5.5, 10.4, 14.5, 18.3]):
                h = 2.6 if row < 4 else 2.25
                if z + h > eave(*pos(s, 0, 0)[:2]) - 0.25:
                    continue
                door = ei == 1 and j == n // 2 and row == 0
                ww = 2.05 if door else w
                lo = 0.90 if door else z
                hi = 3.9 if door else z + h
                openings.append((s - ww / 2, s + ww / 2, lo, hi, door))
                d = -0.40 if door else -0.24
                bx(
                    entry if door else windows,
                    s,
                    d,
                    (lo + hi) / 2,
                    ww,
                    0.08,
                    hi - lo,
                    timber if door else glass,
                )
                for side in [-1, 1]:
                    bx(
                        windows,
                        s + side * (ww / 2 + 0.06),
                        0.02,
                        (lo + hi) / 2,
                        0.12,
                        0.20,
                        hi - lo + 0.18,
                        stucco,
                    )
                    face(
                        wall,
                        [
                            pos(s + side * ww / 2, 0, lo),
                            pos(s + side * ww / 2, d, lo),
                            pos(s + side * ww / 2, d, hi),
                            pos(s + side * ww / 2, 0, hi),
                        ],
                        stucco if row == 0 else brick,
                    )
                bx(windows, s, 0.06, hi + 0.1, ww + 0.26, 0.30, 0.18, stucco)
                bx(
                    windows,
                    s,
                    d + 0.06,
                    (lo + hi) / 2,
                    0.05,
                    0.06,
                    hi - lo,
                    stucco if not door else timber,
                )
                if not door:
                    bx(windows, s, 0.08, lo - 0.08, ww + 0.30, 0.32, 0.15, stucco)
                    bx(windows, s, d + 0.06, (lo + hi) / 2, ww, 0.06, 0.05, stucco)
                if ei == 1 and row in [1, 2]:
                    bx(details, s, 0.14, hi + 0.37, ww + 0.60, 0.42, 0.16, stucco)
                    if row == 1:
                        face(
                            details,
                            [
                                pos(s - ww * 0.65, 0.16, hi + 0.46),
                                pos(s + ww * 0.65, 0.16, hi + 0.46),
                                pos(s, 0.16, hi + 1.03),
                            ],
                            stucco,
                        )
                if door:
                    es = s
                    # Six low steps, measured geometry but estimated real dimensions/location.
                    for k in range(6):
                        hh = (k + 1) * 0.15
                        dd = 2.42 - k * 0.32
                        bx(entry, s, dd - 0.16, hh / 2, 2.65, 0.32, hh, stone)
                    bx(entry, s, 0.16, 0.45, 2.65, 0.72, 0.90, stone)
                    for side in [-1, 1]:
                        bx(details, s + side * 1.50, 0.27, 2.15, 0.42, 0.60, 4.30, stucco)
                        bx(details, s + side * 1.50, 0.27, 4.28, 0.66, 0.80, 0.23, stucco)
                        for dd, hh in [(2.34, 0.95), (0.60, 1.8), (-0.10, 1.8)]:
                            bx(entry, s + side * 1.20, dd, hh - 0.40, 0.04, 0.04, 0.8, iron)
                        entry.beam(
                            pos(s + side * 1.2, 2.34, 0.95),
                            pos(s + side * 1.2, 0.60, 1.8),
                            0.032,
                            iron,
                            n=8,
                        )
                        entry.beam(
                            pos(s + side * 1.2, 0.60, 1.8),
                            pos(s + side * 1.2, -0.10, 1.8),
                            0.032,
                            iron,
                            n=8,
                        )
                    bx(details, s, 0.30, 4.49, 3.7, 1.0, 0.25, stucco)
                    for side in [-1, 1]:
                        entrances.append(
                            {
                                "name": "Estimated Queen Gate 188 entrance leaf " + str(side),
                                "threshold_xyz": pos(s + side * 0.5125, 0, 0.9),
                                "outward_normal": [nx, ny, 0],
                                "door_leaf_xyz": pos(s + side * 0.5125, -0.4, 2.40),
                                "clear_width_m": 0.93,
                                "door_leaf_depth_m": 0.44,
                                "stair_treads": 6,
                                "riser_m": 0.15,
                                "tread_m": 0.32,
                                "landing_depth_m": 0.72,
                                "landing_z_m": 0.90,
                                "supporting_surface": "finite estimated stair flight and landing; coordinator paving review pending",
                                "estimated": True,
                            }
                        )
        # Segment wall at every opening and at rear roof slope changes.
        cuts = [0, L] + [x for q in openings for x in q[:2]]
        va = (a[0] - origin[0]) * vx + (a[1] - origin[1]) * vy
        dv = tx * vx + ty * vy
        if abs(dv) > 1e-8:
            cuts += [(z - va) / dv for z in [3.5, 11, 16] if 0 < (z - va) / dv < L]
        cuts = sorted(set(cuts))
        for s0, s1 in zip(cuts, cuts[1:]):
            sm = (s0 + s1) / 2
            holes = sorted([(q[2], q[3]) for q in openings if q[0] < sm < q[1]])
            zz = 0

            def panel(z0, z1):
                for aa, bb, mat in [(z0, min(z1, 4.8), stucco), (max(z0, 4.8), z1, brick)]:
                    if bb > aa:
                        quad(s0, s1, aa, bb, mat)

            for lo, hi in holes:
                if lo > zz:
                    panel(zz, lo)
                zz = max(zz, hi)
            if zz < 4.8:
                panel(zz, 4.8)
                zz = 4.8
            h0 = eave(*pos(s0, 0, 0)[:2])
            h1 = eave(*pos(s1, 0, 0)[:2])
            face(wall, [pos(s0, 0, zz), pos(s1, 0, zz), pos(s1, 0, h1), pos(s0, 0, h0)], brick)
        for z in [] if ei in [2, 3] else [0.40, 5.1, 10.0, 14.2, 18.0, 21.4]:
            if z + 0.1 > min(eave(*a), eave(*b)):
                continue
            spans = [(0, L)]
            if ei == 1 and z < 3.6:
                spans = [(0, es - 1.35), (es + 1.35, L)]
            for aa, bb in spans:
                if bb > aa:
                    bx(details, (aa + bb) / 2, 0.10, z, bb - aa, 0.30, 0.22, stucco)
        if ei == 1:
            for j in range(3):
                ss = (j + 0.5) * L / 3
                ww = 1.9
                # Dormer occupies a genuine clipped opening in the main slope.
                for aa, bb in [(ss - 0.95, ss - 0.73), (ss + 0.73, ss + 0.95)]:
                    face(
                        roof,
                        [pos(aa, 0, 21.4), pos(bb, 0, 21.4), pos(bb, 0, 25.0), pos(aa, 0, 25.0)],
                        stucco,
                    )
                for zz0, zz1 in [(21.4, 22.3), (24.5, 25.0)]:
                    face(
                        roof,
                        [
                            pos(ss - 0.73, 0, zz0),
                            pos(ss + 0.73, 0, zz0),
                            pos(ss + 0.73, 0, zz1),
                            pos(ss - 0.73, 0, zz1),
                        ],
                        stucco,
                    )
                bx(windows, ss, -0.14, 23.4, 1.46, 0.07, 2.2, glass)
                for side in [-1, 1]:
                    bx(windows, ss + side * 0.76, 0.02, 23.4, 0.06, 0.12, 2.3, stucco)
                    face(
                        roof,
                        [
                            pos(ss + side * 0.95, 0, 21.4),
                            pos(ss + side * 0.95, -2.6, 24.9657142857),
                            pos(ss + side * 0.95, -2.6, 25),
                            pos(ss + side * 0.95, 0, 25),
                        ],
                        roofmat,
                    )
                for zz in [22.26, 24.54]:
                    bx(windows, ss, 0.02, zz, 1.58, 0.16, 0.08, stucco)
                bx(windows, ss, -0.08, 23.4, 0.04, 0.06, 2.2, stucco)
                bx(windows, ss, -0.08, 23.4, 1.46, 0.06, 0.045, stucco)
                bx(roof, ss, -1.3, 25.045, 2.02, 2.7, 0.09, roofmat)
                face(
                    roof,
                    [
                        pos(ss - 0.95, -2.6, 24.9657142857),
                        pos(ss + 0.95, -2.6, 24.9657142857),
                        pos(ss + 0.95, -2.6, 25.0),
                        pos(ss - 0.95, -2.6, 25.0),
                    ],
                    roofmat,
                )
                if j == 1:
                    face(
                        details,
                        [
                            pos(ss - 1.12, 0.08, 25.04),
                            pos(ss + 1.12, 0.08, 25.04),
                            pos(ss, 0.08, 26.25),
                        ],
                        stucco,
                    )
                    for side in [-1, 1]:
                        details.beam(
                            pos(ss + side * 1.12, 0.08, 25.04),
                            pos(ss, 0.08, 26.25),
                            0.08,
                            stucco,
                            n=8,
                        )
    objs = [m.done() for m in [wall, windows, details, roof, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "street_eaves_m": 21.4,
            "main_roof_m": 26.2,
            "rear_roof_m": 20.4,
            "mapped_outline_preserved": True,
            "evidence_level": "tree_occluded licensed row photo plus native1m EA roof",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": SOURCES,
        "uncertainty": [
            "188 is the northern tree-occluded portion of the licensed 186–188 photo. Stucco/classical family is supported; precise window/dormer/entry allocation is estimated.",
            "Main/rear roof heights informed by EA, exact ridge profile and front pediment estimated.",
            "Six-step entrance and paired doors estimated; not certified surveyed or accessible.",
            "187 shared south wall and east adjoining wall closed without speculative windows or projecting trim. North rear recess windows estimated.",
            "Original concave footprint retained. Direct PBR values visually estimated, no photo textures exported.",
        ],
    }
