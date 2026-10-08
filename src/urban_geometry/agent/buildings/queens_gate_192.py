"""192 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (497.440847438178, 7.717668702825906, 22.2),
        (496.19215499353595, 16.13200192525983, 22.2),
        (499.35600694353917, 16.61173406495632, 26.6),
    ],
    [
        (499.35600694353917, 16.61173406495632, 26.6),
        (500.6142529535761, 8.133023995333446, 26.6),
        (497.440847438178, 7.717668702825906, 22.2),
    ],
    [
        (500.6142529535761, 8.133023995333446, 26.6),
        (499.35600694353917, 16.61173406495632, 26.6),
        (507.06789607167184, 17.781081155466513, 26.6),
    ],
    [
        (507.06789607167184, 17.781081155466513, 26.6),
        (508.3494288973588, 9.14545252082057, 26.6),
        (500.6142529535761, 8.133023995333446, 26.6),
    ],
    [
        (508.3494288973588, 9.14545252082057, 26.6),
        (507.06789607167184, 17.781081155466513, 26.6),
        (512.0114147435519, 18.53066262374228, 23.0),
    ],
    [
        (512.0114147435519, 18.53066262374228, 23.0),
        (513.3078750151683, 9.794445165363602, 23.0),
        (508.3494288973588, 9.14545252082057, 26.6),
    ],
    [
        (520.5655167835066, 13.942817015573382, 23.0),
        (524.2409366077045, 20.275500529445708, 23.0),
        (525.2635949949035, 14.480277403257787, 23.0),
    ],
    [
        (520.5655167835066, 13.942817015573382, 23.0),
        (520.7158787267981, 10.764051329344511, 23.0),
        (513.3078750151683, 9.794445165363602, 23.0),
    ],
    [
        (513.3078750151683, 9.794445165363602, 23.0),
        (512.0114147435519, 18.53066262374228, 23.0),
        (516.8714974041795, 19.267592761665583, 23.0),
    ],
    [
        (524.2409366077045, 20.275500529445708, 23.0),
        (520.5655167835066, 13.942817015573382, 23.0),
        (516.8714974041795, 19.267592761665583, 23.0),
    ],
    [
        (520.5655167835066, 13.942817015573382, 23.0),
        (513.3078750151683, 9.794445165363602, 23.0),
        (516.8714974041795, 19.267592761665583, 23.0),
    ],
]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[:2]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        v = -(x - a[0]) * uy + (y - a[1]) * ux
        return 22.2 + 4.4 * max(0, min(1, v / 3.2)) - 3.6 * max(0, min(1, (v - 11) / 5))

    plaster = ctx.material("192 estimated pale stucco", (0.73, 0.71, 0.65), 0.86)
    trimat = ctx.material("192 estimated pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("192 dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("192 blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("192 painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("192 estimated dark timber", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("192 estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
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
        if ei in [0, 4]:
            count = 3 if ei == 0 else 2
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([1.05, 5.45, 9.85, 14.25, 18.65]):
                    hi = lo + (2.8 if row < 3 else 2.5)
                    door = ei == 0 and k == 0 and row == 0
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
            for cut in [3.2, 11, 16]:
                t = (cut - va) / (vb - va)
                if 0 < t < 1:
                    xs.append(t * ll)
        xs = sorted(set(xs))
        for l, r in zip(xs, xs[1:]):
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
                    p(r, 0, rh(*p(r, 0, 0)[:2])),
                    p(l, 0, rh(*p(l, 0, 0)[:2])),
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
                        "name": "Estimated192 Queen Gate street entrance",
                        "threshold_xyz": p(c, 0, 0.08),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.74),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "supporting_surface": "finite authored threshold .08m; precise step/entrance arrangement unverified",
                    }
                )
        if ei == 0:
            for zz in [4.65, 9.05, 13.45, 17.85, 21.85, 22.13]:
                bx(details, ll / 2, 0.025, zz, ll, 0.20, 0.20, trimat)
    roof.surface(feature["geometry"], base, plaster)
    obs = [m.done() for m in [wall, roof, windows, details, entry]]
    return {
        "created": [o.name for o in obs if o],
        "parameters": {
            "front_eaves_m": 22.2,
            "main_roof_m": 26.6,
            "rear_roof_m": 23.0,
            "full_mapped_outline": True,
            "facade_confidence": "low: exact192licensedfacade unavailable; pale residential type is neighbourhood analogy",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": ["ea-lidar-composite-2022-tq27ne", "va-praefcke-aerial-a-2011"],
        "uncertainty": [
            "EA131inset samples median25.335,p9526.720 supports26.6main roof and~23rear. Roof break axes/eaves22.2estimated.",
            "Existing licensed186–188/197–200photos actually inspected only as neighbourhood architectural analogy, not misidentified as192. Limitedtargetsearch did not obtain a verified192street photo.",
            "Three-bayfive-level pale stucco sash frontage, portico and west entrance are low-confidence editable estimates. Fine ornamental and dormer features omitted.",
            "North/south party walls left blank. Rear east openings estimated; no adjacent footprint merged.",
            "180QueensGate belongs to already-detailed Huxley; selected192urban residential instead per coordinator authorization.",
            "Full-scene ground and doorway clearance remains coordinator review.",
        ],
    }
