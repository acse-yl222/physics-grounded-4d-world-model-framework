"""Royal Thai Embassy only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (498.3406936451793, -198.24201014917344, 22.2),
        (500.7927701609442, -213.7139726933092, 22.2),
        (497.6299939560179, -214.20084876786777, 27.6),
    ],
    [
        (497.6299939560179, -214.20084876786777, 27.6),
        (495.1787336503838, -198.73403629653387, 27.6),
        (498.3406936451793, -198.24201014917344, 22.2),
    ],
    [
        (489.92072695651007, -215.38760919960427, 27.6),
        (487.4714561630698, -199.9333500307249, 27.6),
        (495.1787336503838, -198.73403629653387, 27.6),
    ],
    [
        (495.1787336503838, -198.73403629653387, 27.6),
        (497.6299939560179, -214.20084876786777, 27.6),
        (489.92072695651007, -215.38760919960427, 27.6),
    ],
    [
        (484.97888913631283, -216.148353066102, 25.400000000000002),
        (482.5308936712019, -200.70214088597555, 25.400000000000002),
        (487.4714561630698, -199.9333500307249, 27.6),
    ],
    [
        (487.4714561630698, -199.9333500307249, 27.6),
        (489.92072695651007, -215.38760919960427, 27.6),
        (484.97888913631283, -216.148353066102, 25.400000000000002),
    ],
    [
        (474.64241537381895, -217.73954429943115, 12.0),
        (472.6227249096846, -207.1725005125627, 12.0),
        (474.9302720061969, -206.81632037926465, 12.0),
    ],
    [
        (474.9302720061969, -206.81632037926465, 12.0),
        (474.08501500077546, -202.01638684421778, 12.0),
        (482.5308936712019, -200.70214088597555, 12.0),
    ],
    [
        (474.9302720061969, -206.81632037926465, 12.0),
        (484.97888913631283, -216.148353066102, 12.0),
        (474.64241537381895, -217.73954429943115, 12.0),
    ],
    [
        (484.97888913631283, -216.148353066102, 12.0),
        (474.9302720061969, -206.81632037926465, 12.0),
        (482.5308936712019, -200.70214088597555, 12.0),
    ],
]
STEP = [[(484.9788891293668, -216.14835302227465), (482.5308936755972, -200.70214091370897)]]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[4], ring[5]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 22.2 + 5.4 * max(0, min(1, v / 3.2)) - 2.2 * max(0, min(1, (v - 11) / 5))

    plaster = ctx.material("Thai pale stucco", (0.73, 0.71, 0.65), 0.86)
    trimat = ctx.material("Thai pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("Thai dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("Thai blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("Thai painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("Thai estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("Thai estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
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
        if ei in [4]:
            count = 6 if ei == 4 else 1
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([1.05, 5.45, 9.85, 14.25, 18.65]):
                    hi = lo + (2.8 if row < 3 else 2.5)
                    door = ei == 4 and k == 4 and row == 0
                    if hi > (12.0 if ei == 2 else min(rh(*A), rh(*B))) - 0.4:
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
            for cut in [3.2, 11, 16, 16.0]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
            vm = va + (vb - va) * (l + r) / (2 * ll)
            localrh = lambda pt: 12.0 if vm > 16.0 else rh(*pt)
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
                for ss in [l - 0.28, r + 0.28]:
                    details.beam(p(ss, 0.35, 0.18), p(ss, 0.35, 3.55), 0.16, trimat, 16)
                    bx(details, ss, 0.35, 0.11, 0.46, 0.48, 0.22, trimat)
                    bx(details, ss, 0.35, 3.57, 0.46, 0.48, 0.24, trimat)
                entrances.append(
                    {
                        "name": "EstimatedRoyal Thai Embassy street entrance",
                        "threshold_xyz": p(c, 0, 0.45),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.925),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .45m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 4:
            # Photo-supported first-floor semicircular window heads: solid spandrels reduce the real opening.
            for k in range(6):
                c = ll * (k + 0.5) / 6
                rad = 0.67
                spring = 8.25 - rad
                for j in range(16):
                    t0 = math.pi * j / 16
                    t1 = math.pi * (j + 1) / 16
                    x0 = c + rad * math.cos(t0)
                    x1 = c + rad * math.cos(t1)
                    z0 = spring + rad * math.sin(t0)
                    z1 = spring + rad * math.sin(t1)
                    vs = [p(x0, 0, 8.25), p(x1, 0, 8.25)]
                    if abs(z1 - 8.25) > 1e-7:
                        vs.append(p(x1, 0, z1))
                    if abs(z0 - 8.25) > 1e-7:
                        vs.append(p(x0, 0, z0))
                    wall.face(vs, plaster)
                    details.beam(p(x0, 0.06, z0), p(x1, 0.06, z1), 0.085, trimat, 8)
            bx(details, ll / 2, 0.24, 5.15, ll, 0.68, 0.18, trimat)
            bx(details, ll / 2, 0.51, 6.02, ll, 0.17, 0.14, trimat)
            for j in range(36):
                bx(details, (j + 0.5) * ll / 36, 0.51, 5.59, 0.085, 0.12, 0.76, trimat)
        if ei == 4:
            for zz in [4.65, 9.05, 13.45, 17.85, 21.85, 22.13]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
    for A, B in STEP:
        wall.face(
            [
                (A[0], A[1], base + 12.0),
                (B[0], B[1], base + 12.0),
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
            "main_roof_m": 27.6,
            "rear_roof_m": 25.4,
            "west_annexe_m": 12.0,
            "full_mapped_outline": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": ["ea-lidar-composite-2022-tq27ne", "qg27-kenyh-adjacent-2014"],
        "uncertainty": [
            "Complete29-30 single footprint. Actual licensed2014 photo shows partial northern Thai frontage to left of28: pale stucco, round-column portico and archedfirstfloor/balcony; tree obscures door and photo does not cover southernhalf.",
            "One north-half entrance position and six-bay full elevation are estimates based on partial photo/context, not exact surveyed frontage. No second unseen entrance fabricated.",
            "EA288inset median24.761,p9527.611; main27.6/rear25.4/west12 estimated layered mass. Upperroof axes and windows estimated.",
            "All north28/southhotel/westMews shared walls blank, no adjacent footprint merged.",
            "Fine capitals and basement omitted; threshold.45 and three.15rises estimated. Fullscene approach and ground remain coordinator checks.",
            "NewCommons2013photo discovery had CC BY-SA3 license but original returned429; request stopped and that image not acquired/used.",
        ],
    }
