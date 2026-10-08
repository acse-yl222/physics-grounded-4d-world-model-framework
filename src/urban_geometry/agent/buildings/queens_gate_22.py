"""22 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (479.5193156739025, -109.58519777806977, 25.8),
        (484.04703492391855, -117.53103865217417, 22.2),
        (480.89137746021686, -118.06229702402071, 25.8),
    ],
    [
        (484.04703492391855, -117.53103865217417, 22.2),
        (479.5193156739025, -109.58519777806977, 25.8),
        (482.6786696094787, -109.0767775606364, 22.2),
    ],
    [
        (471.8183904559355, -110.8244720580636, 25.8),
        (480.89137746021686, -118.06229702402071, 25.8),
        (473.19946239244405, -119.35723930539662, 25.8),
    ],
    [
        (480.89137746021686, -118.06229702402071, 25.8),
        (471.8183904559355, -110.8244720580636, 25.8),
        (479.5193156739025, -109.58519777806977, 25.8),
    ],
    [
        (466.8818999315977, -111.61887864780324, 25.0),
        (473.19946239244405, -119.35723930539662, 25.8),
        (468.26874760541017, -120.18733051140681, 25.0),
    ],
    [
        (473.19946239244405, -119.35723930539662, 25.8),
        (466.8818999315977, -111.61887864780324, 25.0),
        (471.8183904559355, -110.8244720580636, 25.8),
    ],
    [
        (465.5496537069557, -116.70743786450475, 25.0),
        (468.26874760541017, -120.18733051140681, 25.0),
        (466.20451519079506, -120.53484628722072, 25.0),
    ],
    [
        (465.5496537069557, -116.70743786450475, 25.0),
        (465.1830867773815, -116.76991475632303, 25.0),
        (464.41365466942875, -112.01608194267305, 25.0),
    ],
    [
        (468.26874760541017, -120.18733051140681, 25.0),
        (465.5496537069557, -116.70743786450475, 25.0),
        (466.8818999315977, -111.61887864780324, 25.0),
    ],
    [
        (465.5496537069557, -116.70743786450475, 25.0),
        (464.41365466942875, -112.01608194267305, 25.0),
        (466.8818999315977, -111.61887864780324, 25.0),
    ],
    [
        (459.97776521614287, -117.65709874872118, 12.0),
        (459.0223539295839, -112.88367903698236, 12.0),
        (464.41365466942875, -112.01608194267305, 12.0),
    ],
    [
        (464.41365466942875, -112.01608194267305, 12.0),
        (465.1830867773815, -116.76991475632303, 12.0),
        (459.97776521614287, -117.65709874872118, 12.0),
    ],
]
STEP = [[(465.18308676403643, -116.76991467387234), (464.4136546708765, -112.01608195161793)]]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[-1], ring[0]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 22.2 + 3.6 * max(0, min(1, v / 3.2)) - 0.8 * max(0, min(1, (v - 11) / 5))

    plaster = ctx.material("22 pale stucco", (0.73, 0.71, 0.65), 0.86)
    trimat = ctx.material("22 pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("22 dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("22 blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("22 painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("22 estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("22 estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
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
        if ei in [5, 3]:
            count = 3 if ei == 5 else 1
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([1.05, 5.45, 9.85, 14.25, 18.65]):
                    hi = lo + (2.8 if row < 3 else 2.5)
                    door = ei == 5 and k == 0 and row == 0
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
            for cut in [3.2, 11, 16, 18.5]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
            vm = va + (vb - va) * (l + r) / (2 * ll)
            localrh = lambda pt: 12.0 if vm > 18.5 else rh(*pt)
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
                        "name": "Estimated22 Queen Gate street entrance",
                        "threshold_xyz": p(c, 0, 0.08),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.74),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .08m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 5:
            for zz in [4.65, 9.05, 13.45, 17.85, 21.85, 22.13]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
        if ei == 5:
            # Listed facade balconies and crowning balustrade, simple estimated rail geometry.
            for zz in [5.18, 9.58, 18.38, 22.35]:
                bx(details, ll / 2, 0.24, zz, ll, 0.65, 0.15, trimat)
                bx(details, ll / 2, 0.48, zz + 0.92, ll, 0.17, 0.13, trimat)
                for j in range(18):
                    bx(details, (j + 0.5) * ll / 18, 0.48, zz + 0.47, 0.075, 0.10, 0.80, trimat)
            for zz in [7.0, 11.4]:
                for frac in [0.04, 0.35, 0.65, 0.96]:
                    bx(details, ll * frac, 0.08, zz, 0.16, 0.22, 3.1, trimat)
                    bx(details, ll * frac, 0.08, zz + 1.5, 0.31, 0.28, 0.18, trimat)
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
            "main_roof_m": 25.8,
            "rear_roof_m": 25.0,
            "west_annexe_m": 12.0,
            "full_mapped_outline": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "ea-lidar-composite-2022-tq27ne",
            "va-praefcke-aerial-a-2011",
            "he-queensgate20-24-1266042-text",
        ],
        "uncertainty": [
            "EA99inset samples median24.965,p9525.964 supports25.8main and12m western annexe. Eaves and plane axes estimated.",
            "HE OGL listing confirms stucco five-storey terrace, orders at first/second floors, balconies and22crowningbalustrade. Simple pilasters and square rails stand in for carved capitals and balusters.",
            "Exact threebay window count, dimensions, east entrance position/threshold, colours and rear windows estimated. No licensed target photograph acquired.",
            "North21/Iraq and westIraq shared boundaries and south23 common wall blank. Only rear exposed inset edge has estimated windows. No footprints merged.",
            "PD aerial viewed at regional scale only. Full-scene ground and doorway clearance remains coordinator review.",
        ],
    }
