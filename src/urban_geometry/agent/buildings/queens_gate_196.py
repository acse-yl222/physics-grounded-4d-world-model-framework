"""196 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (488.3082831361098, 52.98500339500606, 2.0),
        (487.8494496794883, 55.873506245203316, 2.0),
        (489.48755976175215, 56.13471491329986, 2.0),
    ],
    [
        (489.48755976175215, 56.13471491329986, 2.0),
        (490.0145658296533, 53.251209675334394, 2.0),
        (488.3082831361098, 52.98500339500606, 2.0),
    ],
    [
        (490.0145658296533, 53.251209675334394, 21.8),
        (492.65414116495424, 56.60758742738753, 26.0),
        (494.8289109184448, 44.70836964317153, 26.0),
    ],
    [
        (494.8289109184448, 44.70836964317153, 26.0),
        (491.66154051886406, 44.23981411010027, 21.8),
        (490.0145658296533, 53.251209675334394, 21.8),
    ],
    [
        (490.0145658296533, 53.251209675334394, 21.8),
        (489.48755976175215, 56.13471491329986, 21.8),
        (489.507156593143, 56.137839771807194, 21.82603910839114),
    ],
    [
        (492.65414116495424, 56.60758742738753, 26.0),
        (490.0145658296533, 53.251209675334394, 21.8),
        (489.507156593143, 56.137839771807194, 21.82603910839114),
    ],
    [
        (500.37276991844476, 57.75974044196694, 26.0),
        (502.5493762674229, 45.85047375503275, 26.0),
        (494.8289109184448, 44.70836964317153, 26.0),
    ],
    [
        (494.8289109184448, 44.70836964317153, 26.0),
        (492.65414116495424, 56.60758742738753, 26.0),
        (500.37276991844476, 57.75974044196694, 26.0),
    ],
    [
        (504.19049711176194, 58.329609266482294, 22.52782304305459),
        (505.3217937501517, 58.49181697561892, 21.5),
        (507.4983925167678, 46.582591775456606, 21.5),
    ],
    [
        (504.19049711176194, 58.329609266482294, 22.52782304305459),
        (502.5493762674229, 45.85047375503275, 26.0),
        (500.37276991844476, 57.75974044196694, 26.0),
    ],
    [
        (502.5493762674229, 45.85047375503275, 26.0),
        (504.19049711176194, 58.329609266482294, 22.52782304305459),
        (507.4983925167678, 46.582591775456606, 21.5),
    ],
    [
        (511.2654256706324, 59.3440275144434, 21.5),
        (511.92479693485535, 55.736288230296374, 21.5),
        (511.6172143940348, 55.68748432211578, 21.5),
    ],
    [
        (511.6172143940348, 55.68748432211578, 21.5),
        (512.9379747475032, 47.38728021737188, 21.5),
        (507.4983925167678, 46.582591775456606, 21.5),
    ],
    [
        (511.6172143940348, 55.68748432211578, 21.5),
        (505.3217937501517, 58.49181697561892, 21.5),
        (511.2654256706324, 59.3440275144434, 21.5),
    ],
    [
        (505.3217937501517, 58.49181697561892, 21.5),
        (511.6172143940348, 55.68748432211578, 21.5),
        (507.4983925167678, 46.582591775456606, 21.5),
    ],
    [
        (521.4349210092332, 60.78719322569668, 6.5),
        (523.3966662831372, 61.09666553046554, 6.5),
        (523.9467762539862, 57.643807341344655, 6.5),
    ],
    [
        (513.1130679097259, 59.608946373686194, 6.5),
        (511.92479693485535, 55.736288230296374, 6.5),
        (511.2654256706324, 59.3440275144434, 6.5),
    ],
    [
        (511.92479693485535, 55.736288230296374, 6.5),
        (513.1130679097259, 59.608946373686194, 6.5),
        (519.1613378110342, 60.454563241451986, 6.5),
    ],
    [
        (519.1613378110342, 60.454563241451986, 6.5),
        (521.4349210092332, 60.78719322569668, 6.5),
        (523.9467762539862, 57.643807341344655, 6.5),
    ],
    [
        (511.92479693485535, 55.736288230296374, 6.5),
        (519.1613378110342, 60.454563241451986, 6.5),
        (523.9467762539862, 57.643807341344655, 6.5),
    ],
]
STEPS = [
    ([(489.4875598024712, 56.134714690506414), (490.01456578289265, 53.25120993118446)], 2),
    ([(511.2654257396312, 59.34402713691744), (511.92479689275376, 55.73628846065442)], 6.5),
]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[9:11]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 21.8 + 4.2 * max(0, min(1, v / 3.2)) - 4.5 * max(0, min(1, (v - 11) / 5))

    plaster = ctx.material("196 red brick", (0.43, 0.145, 0.085), 0.86)
    trimat = ctx.material("196 brick dressings", (0.57, 0.255, 0.15), 0.72)
    slate = ctx.material("196 dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("196 blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("196 painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("196 estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("196 estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
    wall = ctx.mesh("complete footprint party walls and real openings")
    roof = ctx.mesh("EA layered continuous roof")
    windows = ctx.mesh("estimated sash windows")
    details = ctx.mesh("simplified frontage bands arches and gable")
    entry = ctx.mesh("estimated street door and low threshold")
    for tr in ROOF:
        roof.face([(x, y, base + z) for x, y, z in tr], slate)
    entrances = []
    for ei, (A, B) in enumerate(zip(ring, ring[1:] + ring[:1])):
        ll = math.dist(A, B)
        tx, ty = (B[0] - A[0]) / ll, (B[1] - A[1]) / ll
        nx, ny = ty, -tx

        def p(s, d, z):
            return (A[0] + tx * s + nx * d, A[1] + ty * s + ny * d, base + z)

        def bx(m, s, d, z, w, dep, hh, mat):
            m.box(*p(s, d, z), w, dep, hh, mat, math.atan2(ty, tx))

        apertures = []
        if ei in [9, 11]:
            count = 4 if ei == 9 else 2
            for row, lo in enumerate([1.05, 5.45, 9.85, 14.25, 18.65]):
                count = (3 if row >= 3 else 4) if ei == 9 else 2
                for k in range(count):
                    c = ll * (k + 0.5) / count
                    hi = lo + (2.8 if row < 3 else 2.5)
                    door = ei == 9 and k == 0 and row == 0
                    if hi > min(rh(*A), rh(*B)) - 0.4:
                        continue
                    apertures.append(
                        (
                            c - (0.79 if door else 0.67),
                            c + (0.79 if door else 0.67),
                            0.08 if door else lo,
                            3.4 if door else hi,
                            door,
                        )
                    )
        xs = [0, ll] + [xx for op in apertures for xx in op[:2]]
        # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
        va = -(A[0] - a[0]) * uy + (A[1] - a[1]) * ux
        vb = -(B[0] - a[0]) * uy + (B[1] - a[1]) * ux
        if abs(vb - va) > 1e-8:
            for cut in [0, 3.2, 11, 16, 22]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
            vm = va + (vb - va) * (l + r) / (2 * ll)
            localrh = lambda pt: 6.5 if vm > 22 else 2.0 if vm < 0 else rh(*pt)
            aps = sorted(
                [op for op in apertures if op[0] < (l + r) / 2 < op[1]], key=lambda x: x[2]
            )
            z = 0
            for op in aps:
                if op[2] > z:
                    wall.face([p(l, 0, z), p(r, 0, z), p(r, 0, op[2]), p(l, 0, op[2])], plaster)
                z = op[3]
            wall.face(
                [
                    p(l, 0, z),
                    p(r, 0, z),
                    p(r, 0, localrh(p(r, 0, 0)[:2])),
                    p(l, 0, localrh(p(l, 0, 0)[:2])),
                ],
                plaster,
            )
        for l, r, lo, hi, door in apertures:
            c = (l + r) / 2
            w = r - l
            d = 0.43 if door else 0.22
            bx(
                entry if door else windows,
                c,
                -d,
                (lo + hi) / 2,
                w,
                0.06,
                hi - lo,
                timber if door else glass,
            )
            for ss in [l, r]:
                wall.face([p(ss, 0, lo), p(ss, -d, lo), p(ss, -d, hi), p(ss, 0, hi)], trimat)
            for zz in [lo, hi]:
                wall.face([p(l, 0, zz), p(r, 0, zz), p(r, -d, zz), p(l, -d, zz)], trimat)
            for ss in [l - 0.055, r + 0.055]:
                bx(windows, ss, 0.005, (lo + hi) / 2, 0.11, 0.16, hi - lo + 0.14, trimat)
            bx(windows, c, 0.035, hi + 0.08, w + 0.26, 0.24, 0.16, trimat)
            if not door:
                bx(windows, c, 0.04, lo - 0.07, w + 0.28, 0.26, 0.14, trimat)
                bx(windows, c, -d + 0.05, (lo + hi) / 2, 0.045, 0.05, hi - lo, trimat)
                bx(windows, c, -d + 0.05, (lo + hi) / 2, w, 0.05, 0.05, trimat)
            else:
                bx(entry, c, 0.31, 0.04, w + 0.25, 0.94, 0.08, stone)
                entrances.append(
                    {
                        "name": "Estimated196 Queen Gate street entrance",
                        "threshold_xyz": p(c, 0, 0.08),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.74),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .08m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 9:
            for zz in [4.65, 9.05, 13.45, 17.85, 21.65]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
            # Text-evidenced central gable; deliberately simple curved silhouette, estimated dimensions.
            profile = [
                (-2.4, 21.8),
                (-2.2, 22.25),
                (-1.65, 22.45),
                (-1.45, 23.3),
                (-0.8, 23.9),
                (0, 25.15),
                (0.8, 23.9),
                (1.45, 23.3),
                (1.65, 22.45),
                (2.2, 22.25),
                (2.4, 21.8),
            ]
            center = ll / 2
            for (ss, z), (tt, zz) in zip(profile, profile[1:]):
                vs = [p(center + ss, 0, 21.8), p(center + tt, 0, 21.8)]
                if zz > 21.8:
                    vs.append(p(center + tt, 0, zz))
                if z > 21.8:
                    vs.append(p(center + ss, 0, z))
                wall.face(vs, plaster)
                details.beam(p(center + ss, 0.05, z), p(center + tt, 0.05, zz), 0.09, trimat, 8)
            # A simple brick arch moulding over the two left ground openings, geometry shape estimated.
            for c in [ll / 8, 3 * ll / 8]:
                for j in range(12):
                    t0 = math.pi * j / 12
                    t1 = math.pi * (j + 1) / 12
                    details.beam(
                        p(c + 0.84 * math.cos(t0), 0.07, 3.42 + 0.84 * math.sin(t0)),
                        p(c + 0.84 * math.cos(t1), 0.07, 3.42 + 0.84 * math.sin(t1)),
                        0.08,
                        trimat,
                        8,
                    )
    # Close both actual roof-height steps along mapped polygon intersections, precomputed below.
    for line, zlo in STEPS:
        A, B = line
        wall.face(
            [
                (A[0], A[1], base + zlo),
                (B[0], B[1], base + zlo),
                (B[0], B[1], base + rh(*B)),
                (A[0], A[1], base + rh(*A)),
            ],
            plaster,
        )
    roof.surface(feature["geometry"], base, plaster)
    obs = [m.done() for m in [wall, roof, windows, details, entry]]
    return {
        "created": [o.name for o in obs if o],
        "parameters": {
            "front_eaves_m": 21.8,
            "main_roof_m": 26.0,
            "rear_roof_m": 21.5,
            "east_annexe_roof_m": 6.5,
            "west_mapping_projection_m": 2.0,
            "full_mapped_outline": True,
            "facade_confidence": "moderate typology from listed text; precise dimensions and unseen sides estimated",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "ea-lidar-composite-2022-tq27ne",
            "va-praefcke-aerial-a-2011",
            "he-196-queensgate-1227416-text",
        ],
        "uncertainty": [
            "EA176inset samples median22.028,p9526.190: main26.0/rear21.5/eastwing6.5. Roof-break axes and small west mapped projection height2m estimated.",
            "Historic England OGL listing supports red brick, five storeys, four bays narrowing to three, left entrance and central scrolled gable. Source photos do not have confirmed reuse rights and were not downloaded or traced.",
            "Listed elaborate door, oriels, leaded lights and carved brickwork are simplified or omitted. Exact opening dimensions, gable contour and rear fenestration are estimates. Ground arches represented by simplified arch surrounds above rectangular actual apertures.",
            "North197 and south195 common walls remain blank. East low annexe remains inside original boundary. No neighbour merged.",
            "PD aerial actually inspected at regional roof scale, not sufficient for target street details. Full-scene approach/ground validation remains coordinator responsibility.",
        ],
    }
