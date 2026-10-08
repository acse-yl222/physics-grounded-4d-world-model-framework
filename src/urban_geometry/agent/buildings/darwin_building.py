"""RCA Darwin Building only. CC BY-SA4.0 photo-supported simplified exterior.
Mapped footprint and EA roof heights; authoring UTM, affine belongs to caller.
"""

import math


def build(ctx, feature):
    brick = ctx.material("Darwin RCA dark brown brick", (0.20, 0.16, 0.12), 0.91)
    concrete = ctx.material("Darwin RCA aggregate concrete", (0.43, 0.44, 0.40), 0.89)
    white = ctx.material("Darwin RCA entrance render", (0.80, 0.80, 0.75), 0.82)
    pale = ctx.material("Darwin RCA pale spandrels", (0.58, 0.66, 0.65), 0.57)
    glass = ctx.material("Darwin RCA glazing", (0.065, 0.125, 0.15), 0.22, 0, 0.24)
    metal = ctx.material("Darwin RCA black window metal", (0.024, 0.029, 0.026), 0.44, 0.6)
    roofmat = ctx.material("Darwin RCA roof membrane", (0.23, 0.25, 0.23), 0.9)
    shell = ctx.mesh("exact footprint masonry with recessed windows")
    trim = ctx.mesh("concrete frame and window metal")
    roof = ctx.mesh("EA principal stepped roof levels")
    entry = ctx.mesh("white entry glazing and supported approach")
    base = float(feature.get("base_m", 0))
    origin = (522.7313317976659, 118.00343984831125)
    dx, dy = 60.3324926873902, 6.92538978811353
    length = math.hypot(dx, dy)
    tx, ty = dx / length, dy / length
    nx, ny = ty, -tx

    def P(u, v, z):
        return (origin[0] + tx * u + nx * v, origin[1] + ty * u + ny * v, base + z)

    def UV(p):
        return (
            (p[0] - origin[0]) * tx + (p[1] - origin[1]) * ty,
            (p[0] - origin[0]) * nx + (p[1] - origin[1]) * ny,
        )

    cuts = [-10.0, 16.0, 30.0, length, 100.0]
    heights = [37.2, 35.7, 35.3, 5.4]

    def H(u):
        for lo, hi, h in zip(cuts, cuts[1:], heights):
            if lo - 1e-8 <= u < hi - 1e-8:
                return h
        return 5.4

    def F(mesh, points, mat):
        clean = []
        for p in points:
            if not clean or math.dist(clean[-1], p) > 1e-8:
                clean.append(p)
        if len(clean) > 2 and math.dist(clean[0], clean[-1]) < 1e-8:
            clean.pop()
        if len(clean) > 2:
            mesh.face(clean, mat)

    rings = [[UV(p) for p in q["outer"]] for q in feature["geometry"]]
    door_edge = None
    interfaces = []
    for ri, ring in enumerate(rings):
        for ei, (aa, bb) in enumerate(zip(ring, ring[1:] + ring[:1])):
            L = math.dist(aa, bb)
            du, dv = (bb[0] - aa[0]) / L, (bb[1] - aa[1]) / L

            # UV basis is reflected; interior lies to the right of an edge.
            def Q(s, z, d=0):
                return P(aa[0] + du * s + dv * d, aa[1] + dv * s - du * d, z)

            angle = math.atan2(ty * du + ny * dv, tx * du + nx * dv)

            def B(s, z, w, h, depth=0.2, offset=-0.08, mat=concrete, mesh=trim):
                x, y, zz = Q(s, z, offset)
                mesh.box(x, y, zz, w, depth, h, mat, angle)

            split = {0.0, L}
            if abs(du) > 1e-8:
                for cut in cuts:
                    s = (cut - aa[0]) / du
                    if 1e-6 < s < L - 1e-6:
                        split.add(s)
            splits = sorted(split)
            for lo, hi in zip(splits, splits[1:]):
                cap = H(aa[0] + du * (lo + hi) / 2)
                width = hi - lo
                if width < 1e-6:
                    continue
                # Main rear faces adjoining Frayling get no ground openings. Higher
                # windows are estimated continuations of the visible frame grammar.
                bands = [(0, 2.0), (2.0, 3.6), (3.6, 6.0)] if ei == 1 else [(0, 2.0), (2.0, 6.0)]
                for z0, z1 in bands + [
                    (6.0, 10.0),
                    (10.0, 14.0),
                    (14.0, 18.0),
                    (18.0, 22.0),
                    (22.0, 26.0),
                    (26.0, 30.0),
                    (30.0, 34.4),
                    (34.4, cap),
                ]:
                    z1 = min(z1, cap)
                    if z1 <= z0 + 0.01:
                        continue
                    openings = []
                    if width > 2.0 and z0 < 34.4:
                        count = max(1, round(width / (2.65 if ei == 0 else 2.15)))
                        for k in range(count):
                            center = lo + (k + 0.5) * width / count
                            w = min(1.55, width / count - 0.48)
                            if ei == 4 and z0 < 14:
                                continue
                            if ei not in (0, 1, 4, 11) and cap > 10 and z0 < 6:
                                continue
                            if ei == 1 and z0 < 6 and 5.1 < center < 14.8:
                                continue
                            bot = z0 + 0.18
                            top = z1 - 0.36
                            if top - bot > 0.8:
                                openings.append((center - w / 2, center + w / 2, bot, top, glass))
                    if ei == 1 and z0 == 0 and lo < 9.5 < hi:
                        # Door cut continues into next floor band; no wall crosses it at2m.
                        openings.append((8.25, 10.75, 0.45, 2.0, glass))
                    if ei == 1 and z0 == 2 and lo < 9.5 < hi:
                        openings.append((8.25, 10.75, 2.0, 3.3, glass))
                    if ei == 1 and z0 == 3.6 and lo < 9.5 < hi:
                        openings.append((5.4, 12.8, 3.9, 5.8, glass))
                    xs = {lo, hi}
                    for l, h, bot, top, mat in openings:
                        xs.update((l, h))
                    for l, h in zip(sorted(xs), sorted(xs)[1:]):
                        op = next((o for o in openings if o[0] < (l + h) / 2 < o[1]), None)
                        if op:
                            _, _, bot, top, mat = op
                            if bot > z0:
                                F(
                                    shell,
                                    [Q(l, z0), Q(h, z0), Q(h, bot), Q(l, bot)],
                                    white if ei == 1 and z0 < 6 else brick,
                                )
                            if top < z1:
                                F(
                                    shell,
                                    [Q(l, top), Q(h, top), Q(h, z1), Q(l, z1)],
                                    white if ei == 1 and z0 < 6 else brick,
                                )
                            dep = 0.62 if ei == 1 and l == 8.25 else 0.30
                            F(
                                shell,
                                [Q(l, bot, dep), Q(h, bot, dep), Q(h, top, dep), Q(l, top, dep)],
                                mat,
                            )
                        else:
                            F(
                                shell,
                                [Q(l, z0), Q(h, z0), Q(h, z1), Q(l, z1)],
                                white if ei == 1 and z0 < 6 else brick,
                            )
                    for l, h, bot, top, mat in openings:
                        isdoor = ei == 1 and l == 8.25
                        dep = 0.62 if isdoor else 0.30
                        for a0, b0 in [((l, bot), (l, top)), ((h, top), (h, bot))]:
                            F(shell, [Q(*a0), Q(*b0), Q(*b0, dep), Q(*a0, dep)], concrete)
                        if not isdoor:
                            for zz in (bot, top):
                                F(
                                    shell,
                                    [Q(l, zz), Q(h, zz), Q(h, zz, dep), Q(l, zz, dep)],
                                    concrete,
                                )
                            B((l + h) / 2, bot + 0.27, h - l, 0.5, 0.055, 0.255, pale)
                            for s in (l, h):
                                B(s, (bot + top) / 2, 0.10, top - bot + 0.15, 0.16, 0.21, metal)
                            for zz in (bot + 0.55, top):
                                B((l + h) / 2, zz, h - l, 0.07, 0.16, 0.21, metal)
                            B((l + h) / 2, top - 0.45, h - l, 0.055, 0.12, 0.23, metal)
                    # Bands are split around entry at2m to retain true doorway.
                    if z0 > 0 and not (ei == 1 and z0 == 2):
                        B((lo + hi) / 2, z0, width, 0.20, 0.30, -0.06, concrete)
                B((lo + hi) / 2, cap - 0.22, width, 0.44, 0.28, -0.04, concrete)
                if ei in (0, 11) and cap > 10:
                    count = max(1, round(width / (2.65 if ei == 0 else 2.15)))
                    for k in range(count + 1):
                        B(lo + k * width / count, 19.8, 0.17, 28.0, 0.36, -0.10, concrete)
            if ei == 1:
                # White horizontal canopy and upper entry glazing, matching2020 image.
                B(9.5, 3.55, 7.2, 0.55, 1.35, -0.35, white, entry)
                for center in (6.1, 7.6, 9.1, 10.6, 12.1):
                    F(
                        entry,
                        [
                            Q(center - 0.68, 3.9, -0.10),
                            Q(center + 0.68, 3.9, -0.10),
                            Q(center + 0.68, 5.8, -0.10),
                            Q(center - 0.68, 5.8, -0.10),
                        ],
                        glass,
                    )
                    for s in (center - 0.7, center + 0.7):
                        B(s, 4.85, 0.06, 1.9, 0.12, -0.18, metal, entry)
                B(9.5, 5.98, 7.2, 0.30, 0.28, -0.12, white, entry)
                # Actual two door panels share an intentional centre mullion. Interfaces
                # describe each clear leaf separately, never ray-test through centrebar.
                for s in (8.25, 9.5, 10.75):
                    B(s, 1.87, 0.065, 2.84, 0.11, 0.54, metal, entry)
                B(9.5, 3.3, 2.5, 0.10, 0.11, 0.54, metal, entry)
                for s in (9.36, 9.64):
                    B(s, 1.5, 0.032, 0.45, 0.14, 0.43, metal, entry)
                outx, outy = Q(9.5, 0, -1)[0] - Q(9.5, 0)[0], Q(9.5, 0, -1)[1] - Q(9.5, 0)[1]
                for j, s in enumerate((8.875, 10.125)):
                    interfaces.append(
                        {
                            "id": "jay_mews_leaf_" + str(j + 1),
                            "threshold_xyz": list(Q(s, 0.45)),
                            "outward_normal": [outx, outy, 0],
                            "clear_width_m": 1.12,
                            "door_leaf_depth_m": 0.62,
                            "stair_treads": 3,
                            "tread_m": 0.32,
                            "riser_m": 0.15,
                            "landing_depth_m": 0.96,
                            "basis": "2020 photo double door; threshold/3riser approach and exact XY estimated",
                        }
                    )
                # Finite full-width landing and three treads down to coordinator pavement.
                B(9.5, 0.2, 3.3, 0.50, 0.96, -0.48, concrete, entry)
                for j in range(3):
                    top = 0.15 * (j + 1)
                    B(
                        9.5,
                        (top - 0.05) / 2,
                        3.3,
                        top + 0.05,
                        0.32,
                        -1.76 + j * 0.32,
                        concrete,
                        entry,
                    )
                for side in (-1, 1):
                    for d in (0.15, 0.8, 1.5):
                        B(9.5 + side * 1.7, 0.72, 0.055, 1.05, 0.055, -d, metal, entry)
                    entry.beam(
                        Q(9.5 + side * 1.7, 1.24, -0.05),
                        Q(9.5 + side * 1.7, 0.94, -1.82),
                        0.035,
                        metal,
                        8,
                    )
    shell.surface(feature["geometry"], base, brick)

    def clip(ps, cut, greater):
        out = []
        for a, b in zip(ps, ps[1:] + ps[:1]):
            ia = a[0] >= cut - 1e-9 if greater else a[0] <= cut + 1e-9
            ib = b[0] >= cut - 1e-9 if greater else b[0] <= cut + 1e-9
            if ia:
                out.append(a)
            if ia != ib:
                t = (cut - a[0]) / (b[0] - a[0])
                out.append((cut, a[1] + t * (b[1] - a[1])))
        return out

    for part in feature["geometry"]:
        for tri in part["triangles"]:
            for lo, hi, h in zip(cuts, cuts[1:], heights):
                pts = clip(clip([UV(p) for p in tri], lo, True), hi, False)
                if len(pts) >= 3:
                    F(roof, [P(u, v, h) for u, v in pts], roofmat)
    # Vertical roofstep closure only above the lower adjacent roof; no full
    # internal dividing walls and no additional footprint over Frayling.
    for k, cut in enumerate(cuts[1:-1]):
        vals = []
        for ring in rings:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if min(a[0], b[0]) <= cut < max(a[0], b[0]):
                    vals.append(a[1] + (b[1] - a[1]) * (cut - a[0]) / (b[0] - a[0]))
        vals = sorted(vals)
        for v0, v1 in zip(vals[::2], vals[1::2]):
            F(
                roof,
                [
                    P(cut, v0, heights[k + 1]),
                    P(cut, v1, heights[k + 1]),
                    P(cut, v1, heights[k]),
                    P(cut, v0, heights[k]),
                ],
                concrete,
            )
    obs = [m.done() for m in (shell, trim, roof, entry)]
    return {
        "created": [o.name for o in obs if o],
        "parameters": {
            "roof_zones_m": heights,
            "main_height_status": "EA native1m western37.2/middle35.7/east35.3;loweast5.4m interpreted",
            "facade_levels": "semibasement + tall lower floor +7upper tiers, dimensions estimated",
        },
        "interfaces": {"entrances": interfaces},
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + [
                    "darwin-rca-front-shadowssettle-2020",
                    "darwin-rca-entry-shadowssettle-2020",
                    "ea-lidar-composite-2022-tq27ne",
                ]
            )
        ),
        "uncertainty": [
            "Complete original Darwin footprint retained; Frayling footprint and atrium not duplicated.",
            "Main dark brick/concrete vertical-window grammar photo-supported; rear and loweast openings estimated.",
            "EA elevation bands interpreted as main roof levels, not detailed surveyed rooftop plant; no equipment invented.",
            "Exact window count, upper roof furniture, door XY and stairs estimated. Existing public paving and step interfaces require master check.",
            "Photo-derived CC BY-SA4.0 contribution; retain Shadowssettle attribution.",
        ],
    }
