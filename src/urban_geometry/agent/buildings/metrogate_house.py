"""Metrogate House Embassy only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (443.0382411616156, -188.99382617603987, 22.2),
        (463.14991330867633, -185.71336426399648, 22.2),
        (463.6560179445588, -188.87310193047972, 23.099999999999998),
    ],
    [
        (463.6560179445588, -188.87310193047972, 23.099999999999998),
        (443.52330014262793, -192.15699664854296, 23.099999999999998),
        (443.0382411616156, -188.99382617603987, 22.2),
    ],
    [
        (443.52330014262793, -192.15699664854296, 23.099999999999998),
        (463.6560179445588, -188.87310193047972, 23.099999999999998),
        (464.41517489838253, -193.61270843020452, 23.099999999999998),
    ],
    [
        (464.41517489838253, -193.61270843020452, 23.099999999999998),
        (444.25088861414633, -196.90175235729754, 23.099999999999998),
        (443.52330014262793, -192.15699664854296, 23.099999999999998),
    ],
    [
        (444.25088861414633, -196.90175235729754, 23.099999999999998),
        (464.41517489838253, -193.61270843020452, 23.099999999999998),
        (464.88964799452236, -196.57496249253253, 22.499999999999996),
    ],
    [
        (464.88964799452236, -196.57496249253253, 22.499999999999996),
        (444.7056314088454, -199.86722467526914, 22.499999999999996),
        (444.25088861414633, -196.90175235729754, 23.099999999999998),
    ],
    [
        (447.34931587125175, -200.22973652090874, 22.499999999999996),
        (444.8205601834925, -200.6166991116479, 22.499999999999996),
        (444.7056314088454, -199.86722467526914, 22.499999999999996),
    ],
    [
        (447.34931587125175, -200.22973652090874, 22.499999999999996),
        (464.88964799452236, -196.57496249253253, 22.499999999999996),
        (465.2850422413056, -199.04350754447256, 22.499999999999996),
    ],
    [
        (465.2850422413056, -199.04350754447256, 22.499999999999996),
        (447.6100818871957, -201.92651169323543, 22.499999999999996),
        (447.34931587125175, -200.22973652090874, 22.499999999999996),
    ],
    [
        (464.88964799452236, -196.57496249253253, 22.499999999999996),
        (447.34931587125175, -200.22973652090874, 22.499999999999996),
        (444.7056314088454, -199.86722467526914, 22.499999999999996),
    ],
    [
        (466.34405745367985, -205.65520405676216, 9.0),
        (466.7891737750033, -208.187922376208, 9.0),
        (463.2931534816744, -208.7235239557922, 9.0),
    ],
    [
        (447.84095119684935, -203.42875235620886, 9.0),
        (455.48566393426154, -209.91522691119462, 9.0),
        (446.50357752572745, -211.2858040900901, 9.0),
    ],
    [
        (446.50357752572745, -211.2858040900901, 9.0),
        (445.360771207721, -203.81384301185608, 9.0),
        (447.84095119684935, -203.42875235620886, 9.0),
    ],
    [
        (455.48566393426154, -209.91522691119462, 9.0),
        (447.6100818871957, -201.92651169323543, 9.0),
        (465.2850422413056, -199.04350754447256, 9.0),
    ],
    [
        (465.2850422413056, -199.04350754447256, 9.0),
        (466.34405745367985, -205.65520405676216, 9.0),
        (463.2931534816744, -208.7235239557922, 9.0),
    ],
    [
        (447.6100818871957, -201.92651169323543, 9.0),
        (455.48566393426154, -209.91522691119462, 9.0),
        (447.84095119684935, -203.42875235620886, 9.0),
    ],
    [
        (455.48566393426154, -209.91522691119462, 9.0),
        (465.2850422413056, -199.04350754447256, 9.0),
        (463.2931534816744, -208.7235239557922, 9.0),
    ],
]
STEP = [[(465.2850422130341, -199.04350754908398), (447.6100819779804, -201.92651167842732)]]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[10], ring[0]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 22.2 + 0.9 * max(0, min(1, v / 3.2)) - 0.6 * max(0, min(1, (v - 8) / 3))

    plaster = ctx.material("Metrogate pale stucco", (0.73, 0.71, 0.65), 0.86)
    trimat = ctx.material("Metrogate pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("Metrogate dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("Metrogate blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("Metrogate painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("Metrogate estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("Metrogate estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
    wall = ctx.mesh("complete footprint party walls and real openings")
    roof = ctx.mesh("EA layered continuous roof")
    windows = ctx.mesh("estimated sash windows")
    details = ctx.mesh("simplified frontage bands and portico")
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
        if ei in [10]:
            count = 9 if ei == 10 else 1
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([1.05, 5.45, 9.85, 14.25, 18.65]):
                    hi = lo + (2.8 if row < 3 else 2.5)
                    door = ei == 10 and k == 4 and row == 0
                    if hi > (9.0 if ei == 2 else min(rh(*A), rh(*B))) - 0.4:
                        continue
                    apertures.append(
                        (
                            c - (0.79 if door else 0.67),
                            c + (0.79 if door else 0.67),
                            0.45 if door else lo,
                            3.4 if door else hi,
                            door,
                        )
                    )
        xs = [0, ll] + [xx for op in apertures for xx in op[:2]]
        # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
        va = -(A[0] - a[0]) * uy + (A[1] - a[1]) * ux
        vb = -(B[0] - a[0]) * uy + (B[1] - a[1]) * ux
        if abs(vb - va) > 1e-8:
            for cut in [3.2, 8, 11, 13.5]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
            vm = va + (vb - va) * (l + r) / (2 * ll)
            localrh = lambda pt: 9.0 if vm > 13.5 else rh(*pt)
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
                bx(entry, c, 0.31, 0.225, w + 0.25, 0.94, 0.45, stone)
                bx(entry, c, 0.93, 0.15, w + 0.25, 0.30, 0.30, stone)
                bx(entry, c, 1.23, 0.075, w + 0.25, 0.30, 0.15, stone)
                bx(details, c, 0.32, 3.73, w + 0.58, 0.9, 0.24, trimat)
                # Plain rectangular portico pilasters sit outside the door approach width.
                for ss in [l - 0.24, r + 0.24]:
                    bx(details, ss, 0.25, 1.79, 0.20, 0.34, 3.58, trimat)
                entrances.append(
                    {
                        "name": "EstimatedMetrogate House Embassy street entrance",
                        "threshold_xyz": p(c, 0, 0.45),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.925),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .45m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 10:
            for zz in [4.65, 9.05, 13.45, 13.55, 21.85, 22.13]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
    for A, B in STEP:
        wall.face(
            [
                (A[0], A[1], base + 9.0),
                (B[0], B[1], base + 9.0),
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
            "front_eaves_m": 22.2,
            "main_roof_m": 23.1,
            "rear_roof_m": 22.5,
            "rear_low_mass_m": 9.0,
            "full_mapped_outline": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "ea-lidar-composite-2022-tq27ne",
            "va-praefcke-aerial-a-2011",
            "fie-metrogate-official-text",
        ],
        "uncertainty": [
            "Whole3-7MetrogateHouse footprint not split. FIEofficialtext confirms formerthree19thcenturytownhouses, studentresidence and steppedstreetaccess. It is not Imperial property geometry.",
            "EA328inset median19.649,p9523.030; main23.1/rear22.5 and9m lowerrear estimate. Rear raster2-14m variability may include courtyards/lowroofs; no extra mapped holes invented.",
            "Ninebay five-row pale facade, exact entryposition/threshold and materials are estimates. No licensedtargetstreetphoto acquired. PD aerial viewed only for regionalcontext.",
            "NorthfrontQueenGateTerrace, west9/east1/rearMews shared walls kept blank. One estimated northern central entrance.",
            "Tiny capital/sculpture/basement omitted. Three.15m entryrises approximate officialfewstairs; fullscene approach/ground remains coordinator review.",
        ],
    }
