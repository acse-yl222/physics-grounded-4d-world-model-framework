"""31 Elvaston Mews only: EA-informed flat roof, explicitly estimated residential elevation."""

import math

ROOF = [
    [
        (451.4705121462466, -237.19439980573952, 10.2),
        (454.5668140270642, -240.58692714938613, 13.399999999999995),
        (452.5119628132088, -243.4788404563442, 10.2),
    ],
    [
        (454.5668140270642, -240.58692714938613, 13.399999999999995),
        (451.4705121462466, -237.19439980573952, 10.2),
        (454.3474066186282, -239.26295388751186, 13.399999999999999),
    ],
    [
        (460.6448955691885, -242.07417540624738, 10.2),
        (452.5119628132088, -243.4788404563442, 10.2),
        (454.5668140270642, -240.58692714938613, 13.399999999999995),
    ],
    [
        (459.6415613217978, -235.87734529096633, 10.2),
        (454.3474066186282, -239.26295388751186, 13.399999999999999),
        (451.4705121462466, -237.19439980573952, 10.2),
    ],
    [
        (460.6448955691885, -242.07417540624738, 10.2),
        (454.5668140270642, -240.58692714938613, 13.399999999999995),
        (457.781637160149, -240.03168467624917, 13.399999999999967),
    ],
    [
        (454.3474066186282, -239.26295388751186, 13.399999999999999),
        (459.6415613217978, -235.87734529096633, 10.2),
        (457.5729909951198, -238.74303650914732, 13.399999999999975),
    ],
    [
        (457.5729909951198, -238.74303650914732, 13.399999999999975),
        (460.6448955691885, -242.07417540624738, 10.2),
        (457.781637160149, -240.03168467624917, 13.399999999999967),
    ],
    [
        (460.6448955691885, -242.07417540624738, 10.2),
        (457.5729909951198, -238.74303650914732, 13.399999999999975),
        (459.6415613217978, -235.87734529096633, 10.2),
    ],
    [
        (454.3474066186282, -239.26295388751186, 13.399999999999999),
        (457.5729909951198, -238.74303650914732, 13.399999999999975),
        (457.781637160149, -240.03168467624917, 13.399999999999967),
    ],
    [
        (457.781637160149, -240.03168467624917, 13.399999999999967),
        (454.5668140270642, -240.58692714938613, 13.399999999999995),
        (454.3474066186282, -239.26295388751186, 13.399999999999999),
    ],
]


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    ring = feature["geometry"][0]["outer"]
    a, b = ring[:2]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L

    def rh(x, y):
        return 10.2

    plaster = ctx.material("Elvaston31 estimated buff brick", (0.48, 0.40, 0.29), 0.86)
    trimat = ctx.material("Elvaston31 estimated pale dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("Elvaston31 dark slate roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("Elvaston31 blue grey glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    iron = ctx.material("Elvaston31 painted black metal", (0.025, 0.03, 0.03), 0.44, 0.65)
    timber = ctx.material("Elvaston31 estimated dark timber", (0.025, 0.027, 0.026), 0.69)
    stone = ctx.material("Elvaston31 estimated threshold stone", (0.52, 0.50, 0.45), 0.87)
    panel = ctx.material("Elvaston31 estimated lighter timber panels", (0.065, 0.069, 0.065), 0.70)
    wall = ctx.mesh("complete footprint party walls and real openings")
    roof = ctx.mesh("EA estimated shallow pitched roof")
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
        if ei in [2]:
            count = 3
            for k in range(count):
                c = ll * (k + 0.5) / count
                for row, lo in enumerate([0.8, 3.9, 7.0]):
                    hi = lo + 2.05
                    door = ei == 2 and k == 0 and row == 0
                    if hi > min(rh(*A), rh(*B)) - 0.4:
                        continue
                    apertures.append(
                        (
                            c - (0.79 if door else 0.67),
                            c + (0.79 if door else 0.67),
                            0.15 if door else lo,
                            2.7 if door else hi,
                            door,
                        )
                    )
        xs = [0, ll] + [xx for op in apertures for xx in op[:2]]
        # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
        va = -(A[0] - a[0]) * uy + (A[1] - a[1]) * ux
        vb = -(B[0] - a[0]) * uy + (B[1] - a[1]) * ux
        if abs(vb - va) > 1e-8:
            for cut in [3.2, 10, 16]:
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
                bx(entry, c, 0.35, 0.05, w + 0.25, 0.9, 0.20, stone)
                for zz in [0.6, 1.35, 2.1]:
                    for ss in [c - 0.34, c + 0.34]:
                        bx(entry, ss, -0.365, zz, 0.52, 0.04, 0.54, panel)
                bx(entry, c + 0.51, -0.33, 1.25, 0.055, 0.08, 0.26, iron)
                bx(details, c, 0.10, 2.9, w + 0.58, 0.35, 0.24, trimat)
                entrances.append(
                    {
                        "name": "Estimated31 Elvaston Mews street entrance",
                        "threshold_xyz": p(c, 0, 0.15),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": 1.4,
                        "door_leaf_xyz": p(c, -0.43, 1.74),
                        "door_leaf_depth_m": 0.4,
                        "estimated": True,
                        "stair_treads": 1,
                        "riser_m": 0.15,
                        "tread_m": 0.3,
                        "landing_depth_m": 0.8,
                        "supporting_surface": "one estimated .15m riser; finite approach bottom-.05",
                    }
                )
        if ei in [2]:
            for zz in [3.4, 6.6, 9.65]:
                bx(details, ll / 2, 0.025, zz, ll - 0.08, 0.20, 0.20, trimat)
    roof.surface(feature["geometry"], base, plaster)
    obs = [m.done() for m in [wall, roof, windows, details, entry]]
    return {
        "created": [o.name for o in obs if o],
        "parameters": {
            "wall_height_m": 10.2,
            "main_roof_m": 13.4,
            "full_mapped_outline": True,
            "facade_confidence": "low: exact31not confirmed in licensedmewscontext",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "elvaston-ignavy-entrance-2023",
        ],
        "uncertainty": [
            "Independent4cornerunnumberedresidential810154047 apartment footprint and3OSMlevels; north/south/westsharedsegmentsblank;eastdoor/windowsestimated.",
            "EA16insetpixels median12.2745/p9513.3783 support13.4m shallowraisedroof, eaves10.2 andhip/plateauformestimated. No courtyard inferred. Noequipmentinferred.",
            "Previously actuallyviewed2023CCBYSA2MrIgnavy mewsentrance photo usedonlyforlocalbuffbrick/paletrimcontext; target31notidentified. Windowcount,doorplacement,palette androofbreaks estimated.",
            "Realeastdoorandwindowapertures;hiddenpartyfaces no openings; finite.15m step.",
            "Masterground/accesschecks remaincoordinator.",
        ],
    }
