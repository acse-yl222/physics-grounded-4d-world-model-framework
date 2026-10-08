"""Holy Trinity main exterior; CC BY-SA 3.0 photo-derived architectural abstraction.
David Underdown 2008; simplified and dimensioned using EA1m relative height evidence.
"""

import math


def build(ctx, feature):
    stone = ctx.material("Holy Trinity pale sandstone", (0.64, 0.60, 0.48), 0.86)
    slate = ctx.material("Holy Trinity slate roof", (0.19, 0.23, 0.24), 0.76)
    glass = ctx.material("Holy Trinity recessed glazing", (0.045, 0.067, 0.063), 0.3)
    wood = ctx.material("Holy Trinity inset timber doors", (0.16, 0.075, 0.04), 0.75)
    shell = ctx.mesh("Holy Trinity mapped stone and pointed apertures")
    roof = ctx.mesh("Holy Trinity stepped slate roofs")
    trim = ctx.mesh("Holy Trinity tracery and buttress abstraction")
    a = (558.6090313015739, -52.94698713067919)
    b = (582.8847700997721, -49.1713845487684)
    W = math.dist(a, b)
    tx, ty = (b[0] - a[0]) / W, (b[1] - a[1]) / W
    nx, ny = -ty, tx
    ang = math.atan2(ty, tx)
    base = float(feature.get("base_m", 0))

    def P(u, v, z):
        return (a[0] + u * tx + v * nx, a[1] + u * ty + v * ny, base + z)

    def UV(q):
        return ((q[0] - a[0]) * tx + (q[1] - a[1]) * ty, (q[0] - a[0]) * nx + (q[1] - a[1]) * ny)

    def B(u, v, z, w, d, h):
        x, y, zz = P(u, v, z)
        trim.box(x, y, zz, w, d, h, stone, ang)

    # Pointed head: two circular arcs, with no duplicate top corners.
    def top(x, c, r, spring):
        return spring + math.sqrt(max(0, 4 * r * r - (abs(x - c) + r) ** 2))

    def wall(u0, u1, v, z0, z1, opens):
        def cap(x):
            return 14 + 8 * (1 - abs(x - 13) / 6) if u0 == 7 and u1 == 19 and z0 == 5.2 else z1

        xs = {u0, u1}
        for c, r, bot, spr, mat in opens:
            xs.update(c - r + 2 * r * j / 32 for j in range(33))
        xs = sorted(xs)
        for lo, hi in zip(xs, xs[1:]):
            mid = (lo + hi) / 2
            op = next((o for o in opens if o[0] - o[1] < mid < o[0] + o[1]), None)
            if op:
                c, r, bot, spr, mat = op
                za, zb = top(lo, c, r, spr), top(hi, c, r, spr)
                if bot > z0:
                    shell.face([P(lo, v, z0), P(hi, v, z0), P(hi, v, bot), P(lo, v, bot)], stone)
                shell.face(
                    [P(lo, v, za), P(hi, v, zb), P(hi, v, cap(hi)), P(lo, v, cap(lo))], stone
                )
                dep = 0.6 if mat == wood else 0.32
                shell.face(
                    [
                        P(lo, v + dep, bot),
                        P(hi, v + dep, bot),
                        P(hi, v + dep, zb),
                        P(lo, v + dep, za),
                    ],
                    mat,
                )
                shell.face(
                    [P(lo, v, za), P(hi, v, zb), P(hi, v + dep, zb), P(lo, v + dep, za)], stone
                )
            else:
                shell.face(
                    [P(lo, v, z0), P(hi, v, z0), P(hi, v, cap(hi)), P(lo, v, cap(lo))], stone
                )
        for c, r, bot, spr, mat in opens:
            dep = 0.6 if mat == wood else 0.32
            for side in (-1, 1):
                x = c + side * r
                shell.face(
                    [P(x, v, bot), P(x, v, spr), P(x, v + dep, spr), P(x, v + dep, bot)], stone
                )
                trim.beam(P(x, v - 0.06, bot), P(x, v - 0.06, spr), 0.11, stone, 8)
            for j in range(32):
                x0 = c - r + 2 * r * j / 32
                x1 = c - r + 2 * r * (j + 1) / 32
                trim.beam(
                    P(x0, v - 0.06, top(x0, c, r, spr)),
                    P(x1, v - 0.06, top(x1, c, r, spr)),
                    0.11,
                    stone,
                    8,
                )
            if mat == glass and r > 1:
                for k in range(1, 6):
                    x = c - r + 2 * r * k / 6
                    trim.beam(
                        P(x, v + 0.23, bot),
                        P(x, v + 0.23, top(x, c, r, spr) - 0.06),
                        0.065,
                        stone,
                        8,
                    )
                trim.beam(
                    P(c - r, v + 0.23, spr - 0.7), P(c + r, v + 0.23, spr - 0.7), 0.06, stone, 8
                )

    r = feature["geometry"][0]["outer"]
    # Main front is the mapped south edge, keeping all detail inside the side boundaries.
    for aa, bb in zip(r, r[1:] + r[:1]):
        u0, v0 = UV(aa)
        u1, v1 = UV(bb)
        if abs(v0) < 0.01 and abs(v1) < 0.01:
            continue
        pts = [(u0, v0), (u1, v1)]
        if (v0 - 34) * (v1 - 34) < 0:
            pts.insert(1, (u0 + (u1 - u0) * (34 - v0) / (v1 - v0), 34))
        for aa, bb in zip(pts, pts[1:]):
            h = 12 if (aa[1] + bb[1]) / 2 < 34 else 8.5
            shell.face([P(*aa, 0), P(*bb, 0), P(*bb, h), P(*aa, h)], stone)
    shell.surface(feature["geometry"], base, stone)

    # Low roofs follow mapped triangles; rear drops to a low ancillary roof.
    def clip(poly, lower):
        out = []
        for aa, bb in zip(poly, poly[1:] + poly[:1]):
            ia = aa[1] <= 34 if lower else aa[1] >= 34
            ib = bb[1] <= 34 if lower else bb[1] >= 34
            if ia:
                out.append(aa)
            if ia != ib:
                out.append((aa[0] + (bb[0] - aa[0]) * (34 - aa[1]) / (bb[1] - aa[1]), 34))
        return out

    for tri in feature["geometry"][0]["triangles"]:
        poly = [UV(q) for q in tri]
        for lower, h in [(True, 12), (False, 8.5)]:
            cp = clip(poly, lower)
            if len(cp) > 2:
                roof.face([P(*q, h) for q in cp], slate)
    # Close the low-roof step exactly across the mapped footprint.
    cuts = []
    for aa, bb in zip(r, r[1:] + r[:1]):
        aa, bb = UV(aa), UV(bb)
        if (aa[1] - 34) * (bb[1] - 34) < 0:
            cuts.append(aa[0] + (bb[0] - aa[0]) * (34 - aa[1]) / (bb[1] - aa[1]))
    cuts.sort()
    for lo, hi in zip(cuts[::2], cuts[1::2]):
        shell.face([P(lo, 34, 8.5), P(hi, 34, 8.5), P(hi, 34, 12), P(lo, 34, 12)], stone)
    for lo, hi, c in [(0, 7, 3.7), (7, 19, 13), (19, W, 21.8)]:
        wall(lo, hi, 0, 0, 5.2, [(c, 1.05, 0.015, 2.6, wood)])
        wall(
            lo,
            hi,
            0,
            5.2,
            14 if lo == 7 else 12,
            [(c, 3.6 if lo == 7 else 1.7, 5.5, 11 if lo == 7 else 8.8, glass)],
        )
    # Gabled nave, approximate ridge from native DSM. Front pointed window extends into gable.
    for u in (7, 19):
        shell.face([P(u, 0, 12), P(u, 30.4, 12), P(u, 30.4, 14), P(u, 0, 14)], stone)
    roof.face([P(7, 0, 14), P(13, 0, 21), P(13, 30.4, 21), P(7, 30.4, 14)], slate)
    roof.face([P(13, 0, 21), P(19, 0, 14), P(19, 30.4, 14), P(13, 30.4, 21)], slate)
    shell.face(
        [P(7, 30.4, 12), P(19, 30.4, 12), P(19, 30.4, 14), P(13, 30.4, 21), P(7, 30.4, 14)], stone
    )
    for u in (1, 7, 19, W - 0.5):
        B(u, 0.20, 6, 0.45, 0.40, 12)
    for aa, bb in [((7, 14), (13, 22)), ((13, 22), (19, 14))]:
        trim.beam(P(aa[0], -0.08, aa[1]), P(bb[0], -0.08, bb[1]), 0.15, stone, 8)
    # Thin frontal bellcote with two actual pierced lancets, not a detached tower.
    wall(
        11.4,
        14.6,
        0.25,
        21,
        26.8,
        [(12.15, 0.43, 22.7, 24.6, glass), (13.85, 0.43, 22.7, 24.6, glass)],
    )
    # Rear face is inset glazing in these simplified belfry openings; darker than stone.
    roof.face([P(11.4, 0.25, 26.8), P(14.6, 0.25, 26.8), P(13, 0.25, 28.6)], stone)
    for u in (11.4, 14.6):
        shell.face([P(u, 0.25, 21), P(u, 1.0, 21), P(u, 1.0, 26.8), P(u, 0.25, 26.8)], stone)
    roof.face([P(11.4, 1, 26.8), P(14.6, 1, 26.8), P(13, 1, 28.6)], stone)
    for x0, x1 in [(11.4, 13), (13, 14.6)]:
        roof.face(
            [
                P(x0, 0.25, 28.6 if x0 == 13 else 26.8),
                P(x1, 0.25, 28.6 if x1 == 13 else 26.8),
                P(x1, 1, 28.6 if x1 == 13 else 26.8),
                P(x0, 1, 28.6 if x0 == 13 else 26.8),
            ],
            slate,
        )
    entries = [
        {
            "id": "front_" + str(c),
            "threshold_xyz": list(P(c, 0, 0.015)),
            "outward_normal": [-nx, -ny, 0.0],
            "clear_width_m": 2.1,
            "door_leaf_depth_m": 0.6,
            "support_z": base + 0.015,
            "basis": "Photo-informed three pointed portals; metric dimensions estimated, coordinator paving check required",
        }
        for c in (3.7, 13, 21.8)
    ]
    objects = [x.done() for x in (shell, roof, trim)]
    return {
        "created": [o.name for o in objects],
        "parameters": {
            "aisle_height_m": 12,
            "nave_eaves_m": 14,
            "nave_ridge_m": 21,
            "bellcote_top_m": 28.6,
            "rear_roof_m": 8.5,
        },
        "interfaces": {"entrances": entries},
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + [
                    "holy-trinity-underdown-2008",
                    "ea-lidar-composite-2022-tq27ne",
                    "va-praefcke-aerial-a-2011",
                ]
            )
        ),
        "uncertainty": [
            "Simplified secondary elevations, tracery and bellcote; minor sculpture omitted.",
            "The thin bellcote height is photo-estimated; native1m raster does not reliably resolve it.",
            "Module-derived contribution CC BY-SA3.0; no photographic texture exported.",
        ],
    }
