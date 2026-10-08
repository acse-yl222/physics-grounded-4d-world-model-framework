"""QGT20 House only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (381.1446130007092, -165.7625494102271, 23.2),
        (374.69803892611526, -170.00333354901522, 23.2),
        (374.1908281400868, -166.84374725584266, 23.2),
    ],
    [
        (374.69803892611526, -170.00333354901522, 23.2),
        (381.1446130007092, -165.7625494102271, 23.2),
        (381.6479701913195, -168.92273487336934, 23.2),
    ],
    [
        (380.38957721479386, -161.02227121551374, 23.2),
        (374.1908281400868, -166.84374725584266, 23.2),
        (373.43001196104416, -162.10436781608382, 23.2),
    ],
    [
        (374.1908281400868, -166.84374725584266, 23.2),
        (380.38957721479386, -161.02227121551374, 23.2),
        (381.1446130007092, -165.7625494102271, 23.2),
    ],
    [
        (379.9176798485967, -158.0595973438179, 23.2),
        (373.43001196104416, -162.10436781608382, 23.2),
        (372.9545018491425, -159.14225566623452, 23.2),
    ],
    [
        (373.43001196104416, -162.10436781608382, 23.2),
        (379.9176798485967, -158.0595973438179, 23.2),
        (380.38957721479386, -161.02227121551374, 23.2),
    ],
    [
        (379.2884833603339, -154.1093655148901, 23.2),
        (372.9545018491425, -159.14225566623452, 23.2),
        (372.3204883666069, -155.1927727997688, 23.2),
    ],
    [
        (372.9545018491425, -159.14225566623452, 23.2),
        (379.2884833603339, -154.1093655148901, 23.2),
        (379.9176798485967, -158.0595973438179, 23.2),
    ],
    [
        (372.3204883666069, -155.1927727997688, 10.5),
        (378.2652610798832, -147.68535442184657, 10.5),
        (379.2884833603339, -154.1093655148901, 10.5),
    ],
    [
        (378.2652610798832, -147.68535442184657, 10.5),
        (372.3204883666069, -155.1927727997688, 10.5),
        (371.28717233333737, -148.75590027030557, 10.5),
    ],
]
STEP = [[(372.32048841526705, -155.19277279220296), (379.2884833237162, -154.10936552058354)]]


def build(ctx, feature):
    assert feature["id"] == "way-809617873"
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[3], ring[0]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 23.2

    plaster = ctx.material("QGT20 pale stucco", (0.73, 0.71, 0.65), 0.86)
    trimat = ctx.material("QGT20 pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("QGT20 dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("QGT20 blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("QGT20 painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("QGT20 estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("QGT20 estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
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
        if ei in [3]:
            count = 3 if ei == 3 else 1
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([1.15, 6.1, 11.15, 16.2]):
                    hi = lo + 3.2
                    door = ei == 3 and k == 1 and row == 0
                    if hi > (10.5 if ei == 2 else min(rh(*A), rh(*B))) - 0.4:
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
            for cut in [3.2, 8, 11, 15.0]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
            vm = va + (vb - va) * (l + r) / (2 * ll)
            localrh = lambda pt: 10.5 if vm > 15.0 else rh(*pt)
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
                bx(details, c, 0.32, 3.73, w + 0.58, 0.9, 0.24, trimat)
                # Plain rectangular portico pilasters sit outside the door approach width.
                for ss in [l - 0.24, r + 0.24]:
                    bx(details, ss, 0.25, 1.79, 0.20, 0.34, 3.58, trimat)
                entrances.append(
                    {
                        "name": "EstimatedQGT20 House street entrance",
                        "threshold_xyz": p(c, 0, 0.08),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.74),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .08m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 3:
            for zz in [5.1, 10.1, 15.2, 21.5, 23.03]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
    for A, B in STEP:
        wall.face(
            [
                (A[0], A[1], base + 10.5),
                (B[0], B[1], base + 10.5),
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
            "main_roof_m": 23.2,
            "rear_roof_m": 10.5,
            "roof_break_depth_m": 15.0,
            "osm_levels": 4,
            "modeled_window_rows": 4,
            "complete_mapped_outline": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": ["ea-lidar-composite-2022-tq27ne", "va-praefcke-aerial-a-2011"],
        "uncertainty": [
            "Original4vertex complete residential footprint, OSM4levels honored as four window rows.",
            "EA74inset samples median21.448/p9523.172. Main23.2m; northrear6–16m mixed simplified10.5m at estimated15m setback. Roof pitch/floor heights uncertain.",
            "No target licensed street photo. Three-bay stucco and one south entrance are estimates; precise material colours and hidden rear windows unresolved. Shared sides blank, rear windows omitted.",
        ],
    }
