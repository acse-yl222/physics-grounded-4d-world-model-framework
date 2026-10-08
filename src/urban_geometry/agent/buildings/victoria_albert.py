"""V&A mapped wings and photo-informed portal. All authored dimensions estimated."""

import math


def _inside(point, ring):
    x, y = point
    odd = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            odd = not odd
    return odd


def _roof_uv(p):
    dx, dy = p[0] - 1068.9481244096287, p[1] + 437.093373966678
    return (
        dx * 0.9567214489567577 + dy * 0.29100527333036774,
        -dx * 0.29100527333036774 + dy * 0.9567214489567577,
    )


def _ramp(x, a, b):
    return max(0.0, min(1.0, (x - a) / (b - a)))


def _wall_uv(u, v):
    # Rounded EA DSM-DTM surfaces interpreted as roof zones, not raw raster extrusion.
    h = 13.5
    h = max(h, 24.0 - 10.5 * _ramp(v, 14.0, 20.0))
    if u < -94 and v < 82:
        h = max(h, 22.0)
    if u < -44:
        h = max(h, 16.0)
    if 20 < u < 40 and v < 135:
        h = max(h, 16.0)
    h = max(h, 13.5 + 2.5 * _ramp(v, 160.0, 166.0))
    court = min(
        _ramp(u, 40.0, 42.0),
        1 - _ramp(u, 87.0, 89.0),
        _ramp(v, 39.0, 41.0),
        1 - _ramp(v, 84.0, 86.0),
    )
    h = max(h, 13.5 + 12.5 * court)
    west = min(1 - _ramp(u, -65.0, -61.0), _ramp(v, 111.0, 115.0))
    h = max(h, 13.5 + 16.5 * west)
    hall = min(
        _ramp(u, -27.0, -24.0),
        1 - _ramp(u, 5.0, 8.0),
        _ramp(v, 125.0, 128.0),
        1 - _ramp(v, 150.0, 153.0),
    )
    h = max(h, 13.5 + 6.5 * hall)
    return h


def _roof_h(u, v):
    def tent(x, c, r, h):
        return max(0.0, 1.0 - abs(x - c) / r) * h

    h = _wall_uv(u, v)
    if v < 17:
        h += tent(v, 7.0, 10.0, 2.5)
    if 41 < v < 84:
        end = min(1.0, (v - 41.0) / 2.0, (84.0 - v) / 2.0)
        if 42 < u < 87:
            h += (
                max(
                    5.0 * math.sqrt(max(0.0, 1 - ((u - c) / 11.0) ** 2)) if abs(u - c) < 11 else 0
                    for c in (53.0, 76.0)
                )
                * end
            )
    # West rotunda is centred farther north than the initial oblique estimate.
    du, dv = u + 70.0, v - 53.0
    norm = max(abs(du), abs(dv), (abs(du) + abs(dv)) / 1.41421356237)
    h = max(h, 14.0 + 11.0 * max(0.0, 1.0 - max(0.0, norm - 3.0) / 21.0))
    if 22 < v < 80 and -55 < u < 30:
        h += max(tent(u, c, 8.0, 4.0) for c in (-41.0, -15.0, 13.0)) * min(
            1.0, (v - 22.0) / 4.0, (80.0 - v) / 4.0
        )
    if v > 90 and u > 40:
        h += max(tent(v, c, 7.0, 2.7) for c in (101.0, 119.0, 137.0, 155.0, 170.0))
    if -43 < u < 25 and v > 160:
        h += tent(v, 168.0, 9.0, 3.5)
    if u < -62 and v > 115:
        h += 3.0 * min(1.0, (v - 115.0) / 4.0)
    q = ((u + 9.5) / 15.0) ** 2 + ((v - 139.0) / 13.0) ** 2
    h += 7.0 * math.sqrt(max(0.0, 1.0 - q))
    return h


def build(ctx, feature):
    base = float(feature.get("base_m", 0))
    height = 24.0
    stone = ctx.material("VA Portland stone", (0.68, 0.63, 0.52), 0.8)
    brick = ctx.material("VA rear estimated brick", (0.40, 0.17, 0.11), 0.85)
    glass = ctx.material("VA recessed glazing", (0.055, 0.095, 0.12), 0.27)
    lead = ctx.material("VA estimated roof lead", (0.30, 0.34, 0.35), 0.65, 0.15)
    wood = ctx.material("VA entrance dark doors", (0.095, 0.060, 0.038), 0.65)
    shell = ctx.mesh("mapped perforated museum wings")
    detail = ctx.mesh("frames cornices and carved portal abstraction")
    parts = feature["geometry"]
    ep = feature.get("detail_parameters", {}).get(
        "entrance_xy", [1066.87111731607, -444.78926682751626]
    )
    candidate = None
    for pi, p in enumerate(parts):
        r = p["outer"]
        for si, (a, b) in enumerate(zip(r, r[1:] + r[:1])):
            L = math.dist(a, b)
            if L < 10:
                continue
            u = max(4.6, min(L - 4.6, sum((ep[i] - a[i]) * (b[i] - a[i]) for i in (0, 1)) / L))
            score = math.dist([a[i] + u * (b[i] - a[i]) / L for i in (0, 1)], ep)
            if candidate is None or score < candidate[0]:
                candidate = (score, pi, si, u)
    entrance = None
    entrances = []
    opening_count = 0
    for pi, p in enumerate(parts):
        for ri, r in enumerate([p["outer"]] + p.get("holes", [])):
            signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:] + r[:1]))
            for si, (a, b) in enumerate(zip(r, r[1:] + r[:1])):
                L = math.dist(a, b)
                if L < 0.001:
                    continue
                tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                sign = (1 if signed > 0 else -1) * (1 if ri == 0 else -1)
                nx, ny = ty * sign, -tx * sign
                angle = math.atan2(ty, tx)

                def P(u, z, d=0):
                    return (a[0] + tx * u - nx * d, a[1] + ty * u - ny * d, base + z)

                def B(u, z, w, h, d=0.22, offset=-0.10, mat=stone):
                    if not is_south and not isdoor:
                        ns = max(1, math.ceil(w))
                        cap = min(
                            _wall_uv(*_roof_uv(P(u + w * (j / ns - 0.5), 0))) for j in range(ns + 1)
                        )
                        if z - h / 2 >= cap - 0.03:
                            return
                        if z + h / 2 > cap:
                            bottom = z - h / 2
                            h = cap - bottom
                            z = bottom + h / 2
                    x, y, zz = P(u, z, offset)
                    detail.box(x, y, zz, w, d, h, mat, angle)

                is_south = ri == 0 and ny < -0.75 and (a[1] + b[1]) / 2 < -390
                isdoor = bool(ri == 0 and candidate and (pi, si) == candidate[1:3])
                door_u = candidate[3] if isdoor else None
                openings = []
                bays = max(1, int(L / (5.4 if is_south else 4.8)))
                if L >= 3:
                    for k in range(bays):
                        u = (k + 0.5) * L / bays
                        if isdoor and abs(u - door_u) < 5.6:
                            continue
                        for z0, z1 in (
                            [(2.0, 8.3), (10.0, 17.2)]
                            if is_south
                            else [(2.0, 6.3), (9.0, 14.8), (17.6, 20.8)]
                        ):
                            half = 1.55 if is_south else 1.0
                            cap = min(_wall_uv(*_roof_uv(P(q, 0))) for q in (u - half, u, u + half))
                            if z0 < cap - 1.0:
                                openings.append((u - half, u + half, z0, min(z1, cap - 0.6)))
                xs = {0.0, L}
                # Share integer UV cuts with the roof height field.
                uv0, uv1 = _roof_uv(a), _roof_uv(b)
                for q0, q1 in zip(uv0, uv1):
                    if abs(q1 - q0) > 1e-9:
                        for k in range(math.floor(min(q0, q1)) + 1, math.ceil(max(q0, q1))):
                            xx = L * (k - q0) / (q1 - q0)
                            if 0.0001 < xx < L - 0.0001:
                                xs.add(xx)
                for lo, hi, z0, z1 in openings:
                    xs.update([lo, hi])
                arch_x = []
                if isdoor:
                    arch_x = [door_u - 4.0 + 8 * j / 48 for j in range(49)]
                    xs.update(arch_x)
                xs = sorted(xs)

                def arch_top(u):
                    return 9.0 + math.sqrt(max(0.0, 16.0 - (u - door_u) ** 2))

                for lo, hi in zip(xs, xs[1:]):
                    if hi - lo < 1e-8:
                        continue
                    mid = (lo + hi) / 2
                    voids = [(z0, z0, z1, z1) for x0, x1, z0, z1 in openings if x0 < mid < x1]
                    if isdoor and door_u - 4 < mid < door_u + 4:
                        voids.append((0.0, 0.0, arch_top(lo), arch_top(hi)))
                    voids.sort(key=lambda v: v[0])
                    low_l = low_r = 0.0
                    hl = _wall_uv(*_roof_uv(P(lo, 0)))
                    hr = _wall_uv(*_roof_uv(P(hi, 0)))
                    for bottom_l, bottom_r, top_l, top_r in voids + [(hl, hr, hl, hr)]:
                        if bottom_l - low_l > 1e-8 or bottom_r - low_r > 1e-8:
                            shell.face(
                                [P(lo, low_l), P(hi, low_r), P(hi, bottom_r), P(lo, bottom_l)],
                                stone if ri == 0 else brick,
                            )
                        low_l, low_r = top_l, top_r
                for lo, hi, z0, z1 in openings:
                    shell.face(
                        [P(lo, z0, 0.32), P(hi, z0, 0.32), P(hi, z1, 0.32), P(lo, z1, 0.32)], glass
                    )
                    for aa, bb in [
                        ((lo, z0), (hi, z0)),
                        ((hi, z0), (hi, z1)),
                        ((hi, z1), (lo, z1)),
                        ((lo, z1), (lo, z0)),
                    ]:
                        shell.face([P(*aa), P(*bb), P(*bb, 0.32), P(*aa, 0.32)], stone)
                    u = (lo + hi) / 2
                    for z in (z0, z1):
                        B(u, z, hi - lo + 0.25, 0.16)
                    for v in (lo, u, hi):
                        B(v, (z0 + z1) / 2, 0.12, z1 - z0, 0.18)
                    B(u, (z0 + z1) / 2, hi - lo, 0.10, 0.16)
                    if is_south:
                        for f in (0.25, 0.75):
                            B(lo + (hi - lo) * f, (z0 + z1) / 2, 0.055, z1 - z0, 0.075, 0.26, wood)
                        for zz in [z0 + (z1 - z0) * j / 6 for j in range(1, 6)]:
                            B(u, zz, hi - lo, 0.045, 0.075, 0.26, wood)
                        # Thick paired stone pilasters and framed heads, unlike generic windows.
                        for v in (lo - 0.22, hi + 0.22):
                            B(v, (z0 + z1) / 2, 0.26, z1 - z0 + 0.5, 0.34, -0.16)
                            B(v, z1 + 0.15, 0.48, 0.30, 0.50, -0.18)
                    opening_count += 1
                for z, h in (
                    [(0.9, 0.35), (9.0, 0.45), (18.1, 0.65), (21.4, 0.50), (23.7, 0.45)]
                    if is_south
                    else [(1.0, 0.45), (7.7, 0.35), (16.1, 0.5), (23.7, 0.65)]
                ):
                    intervals = [(0.0, L)]
                    if isdoor and z < 20:
                        intervals = [(0.0, door_u - 4.7), (door_u + 4.7, L)]
                    for lo, hi in intervals:
                        if hi - lo > 0.05:
                            B((lo + hi) / 2, z, hi - lo, h, 0.45)
                if is_south:
                    # Upper red-brick fascia, deep dentils, parapet piers and masonry joints.
                    intervals = (
                        [(0.0, L)]
                        if not isdoor
                        else [(0.0, max(0.0, door_u - 6.0)), (min(L, door_u + 6.0), L)]
                    )
                    for lo, hi in intervals:
                        if hi - lo < 0.15:
                            continue
                        B((lo + hi) / 2, 19.65, hi - lo, 2.25, 0.04, -0.025, brick)
                        for j in range(max(1, int((hi - lo) / 0.48))):
                            v = lo + (j + 0.5) * (hi - lo) / max(1, int((hi - lo) / 0.48))
                            B(v, 21.0, 0.22, 0.65, 0.65, -0.22)
                        count = max(1, int((hi - lo) / 2.7))
                        for j in range(count + 1):
                            B(lo + j * (hi - lo) / count, 22.7, 0.32, 1.6, 0.45, -0.12)
                        B((lo + hi) / 2, 22.0, hi - lo, 0.20, 0.40, -0.12)
                    for zz in [j * 0.48 for j in range(1, 38)]:
                        spans = [(0.0, L)]
                        for x0, x1, z0, z1 in openings:
                            if z0 - 0.15 < zz < z1 + 0.15:
                                spans = [
                                    v
                                    for aa, bb in spans
                                    for v in [(aa, min(bb, x0 - 0.4)), (max(aa, x1 + 0.4), bb)]
                                    if v[1] - v[0] > 0.02
                                ]
                        if isdoor and zz < 20.0:
                            spans = [
                                v
                                for aa, bb in spans
                                for v in [(aa, min(bb, door_u - 4.8)), (max(aa, door_u + 4.8), bb)]
                                if v[1] - v[0] > 0.02
                            ]
                        for lo, hi in spans:
                            B((lo + hi) / 2, zz, hi - lo, 0.018, 0.02, -0.012, lead)
                if isdoor:
                    u = door_u
                    depth = 0.85
                    for side in (-1, 1):
                        q = u + side * 4
                        shell.face([P(q, 0), P(q, 9), P(q, 9, depth), P(q, 0, depth)], stone)
                    shell.face(
                        [P(u - 4, 0.9), P(u + 4, 0.9), P(u + 4, 0.9, depth), P(u - 4, 0.9, depth)],
                        stone,
                    )
                    for lo, hi in zip(arch_x, arch_x[1:]):
                        za, zb = arch_top(lo), arch_top(hi)
                        shell.face(
                            [P(lo, za), P(hi, zb), P(hi, zb, depth), P(lo, za, depth)], stone
                        )
                        shell.face(
                            [
                                P(lo, 5.4, depth),
                                P(hi, 5.4, depth),
                                P(hi, zb, depth),
                                P(lo, za, depth),
                            ],
                            glass,
                        )
                    for index, (lo, hi) in enumerate([(u - 3.8, u - 0.3), (u + 0.3, u + 3.8)]):
                        shell.face(
                            [
                                P(lo, 0.9, depth),
                                P(hi, 0.9, depth),
                                P(hi, 5.4, depth),
                                P(lo, 5.4, depth),
                            ],
                            wood,
                        )
                        for v in (lo, (lo + hi) / 2, hi):
                            B(v, 3.15, 0.09, 4.5, 0.1, depth - 0.06, stone)
                        B((lo + hi) / 2, 4.0, hi - lo, 0.10, 0.1, depth - 0.06, stone)
                        entrances.append(
                            {
                                "id": "cromwell_door_" + str(index + 1),
                                "threshold_xyz": list(P((lo + hi) / 2, 0.9)),
                                "outward_normal": [nx, ny, 0.0],
                                "door_leaf_position": list(P((lo + hi) / 2, 3.15, depth)),
                                "door_leaf_depth_m": depth,
                                "clear_width_m": 3.5,
                                "opening_width_m": 3.5,
                                "dimensions_status": "estimated",
                                "stair_treads": 6,
                                "riser_m": 0.15,
                                "tread_m": 0.35,
                                "landing_depth_m": 0.8,
                                "landing_top_m": base + 0.9,
                                "approach_bottom_m": base - 0.05,
                                "stairs_extent_xyz": [
                                    list(P(u - 4.9, -0.05, 0)),
                                    list(P(u + 4.9, -0.05, 0)),
                                    list(P(u + 4.9, -0.05, -2.9)),
                                    list(P(u - 4.9, -0.05, -2.9)),
                                ],
                                "bottom_approach_xyz": list(P(u, 0.0, -3.05)),
                                "stairs_width_m": 9.8,
                                "supporting_surface": "authored six estimated photo-informed treads and landing; external ground and accessible route coordinator validation",
                            }
                        )
                    for v, w in [(u - 3.9, 0.2), (u, 0.6), (u + 3.9, 0.2)]:
                        B(v, 2.7, w, 5.4, 0.90, -0.03)
                    B(u, 5.4, 8.0, 0.30, 0.65, -0.1)
                    for j in range(-5, 6):
                        v = u + j * 0.6
                        top = arch_top(v) - 0.12
                        B(v, (5.6 + top) / 2, 0.055, top - 5.6, 0.07, depth - 0.04, stone)
                    for z in (6.1, 6.9, 7.7, 8.5, 9.3, 10.1, 10.9, 11.7, 12.4):
                        half = 4 if z <= 9 else math.sqrt(max(0.0, 16 - (z - 9) ** 2))
                        B(u, z, half * 2 - 0.14, 0.055, 0.07, depth - 0.04, stone)
                    for layer in range(4):
                        inner = 4.0 + layer * 0.19
                        outer = inner + 0.14
                        d = -0.10 - layer * 0.12
                        for j in range(64):
                            t0 = math.pi * j / 64
                            t1 = math.pi * (j + 1) / 64
                            detail.face(
                                [
                                    P(u + rad * math.cos(t), 9 + rad * math.sin(t), dd)
                                    for rad, t, dd in [
                                        (inner, t0, d),
                                        (outer, t0, d),
                                        (outer, t1, d),
                                        (inner, t1, d),
                                    ]
                                ],
                                stone,
                            )
                            detail.face(
                                [
                                    P(u + outer * math.cos(t0), 9 + outer * math.sin(t0), d),
                                    P(u + outer * math.cos(t1), 9 + outer * math.sin(t1), d),
                                    P(u + outer * math.cos(t1), 9 + outer * math.sin(t1), d + 0.14),
                                    P(u + outer * math.cos(t0), 9 + outer * math.sin(t0), d + 0.14),
                                ],
                                stone,
                            )
                        for side in (-1, 1):
                            B(u + side * (inner + outer) / 2, 4.5, outer - inner, 9.0, 0.28, d)
                    B(u, 16.0, 11.0, 0.45, 0.65, -0.32)
                    for j in range(40):
                        t0 = math.pi * 0.23 + math.pi * 0.54 * j / 40
                        t1 = math.pi * 0.23 + math.pi * 0.54 * (j + 1) / 40
                        detail.beam(
                            P(u + 7.2 * math.cos(t0), 11.7 + 7.2 * math.sin(t0), -0.4),
                            P(u + 7.2 * math.cos(t1), 11.7 + 7.2 * math.sin(t1), -0.4),
                            0.16,
                            stone,
                            8,
                        )
                    for side in (-1, 1):
                        B(u + side * 4.95, 9.0, 0.45, 17.0, 0.5, -0.25)
                    # Source-visible stair flight; absolute dimensions remain estimated.
                    x, y, zz = P(u, 0.425, -0.4)
                    detail.box(x, y, zz, 9.8, 0.8, 0.95, stone, angle)
                    for step in range(1, 7):
                        out = 0.8 + (6 - step + 0.5) * 0.35
                        top = step * 0.15
                        x, y, zz = P(u, (top - 0.05) / 2, -out)
                        detail.box(x, y, zz, 9.8, 0.35, top + 0.05, stone, angle)
                    entrance = {
                        "threshold_xyz": list(P(u, 0)),
                        "outward_normal": [nx, ny, 0.0],
                        "opening_width_m_estimated": 8.0,
                        "anchor_snap_distance_m": candidate[0],
                        "role": "portal center for tower placement; central pier is not traversable",
                    }
                    opening_count += 1
    roof_parameters = _authored_roofs(ctx, parts, base, stone, lead, glass)
    for p in parts:
        for tri in p["triangles"]:
            shell.face([(x, y, base) for x, y in reversed(tri)], stone)
    objects = [shell.done(), detail.done()] + roof_parameters.pop("objects")
    tower_status = "not placed"
    tower_center = None
    if entrance:
        ex, ey, _ = entrance["threshold_xyz"]
        nx, ny, _ = entrance["outward_normal"]
        for setback in (12.0, 14.0, 16.0, 18.0, 20.0):
            cx, cy = ex - nx * setback, ey - ny * setback
            samples = [
                (cx + 10.8 * math.cos(j * math.tau / 32), cy + 10.8 * math.sin(j * math.tau / 32))
                for j in range(32)
            ] + [(cx, cy)]
            if any(
                all(
                    _inside(q, p["outer"]) and not any(_inside(q, h) for h in p.get("holes", []))
                    for q in samples
                )
                for p in parts
            ):
                tower_center = (cx, cy)
                break
        if tower_center:
            cx, cy = tower_center
            tower = ctx.mesh("estimated open octagonal entrance tower")

            def ring(radius, z, width=0.42, h=0.4):
                pts = [
                    (
                        cx + radius * math.cos(j * math.tau / 8 + math.pi / 8),
                        cy + radius * math.sin(j * math.tau / 8 + math.pi / 8),
                    )
                    for j in range(8)
                ]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    tower.box(
                        (a[0] + b[0]) / 2,
                        (a[1] + b[1]) / 2,
                        base + z,
                        math.dist(a, b) + 0.12,
                        width,
                        h,
                        stone,
                        math.atan2(b[1] - a[1], b[0] - a[0]),
                    )
                return pts

            # Photo-supported broad plinth, two open colonnaded tiers and shallow dome.
            pts = ring(9.1, 26.0, 0.8, 0.6)
            # Socket extends to the local front roof rather than floating after tower scaling.
            for a, b in zip(pts, pts[1:] + pts[:1]):
                tower.face(
                    [
                        (a[0], a[1], base + 24.0),
                        (b[0], b[1], base + 24.0),
                        (b[0], b[1], base + 26.2),
                        (a[0], a[1], base + 26.2),
                    ],
                    stone,
                )
            for a, b in zip(pts, pts[1:] + pts[:1]):
                tower.box(
                    (a[0] + b[0]) / 2,
                    (a[1] + b[1]) / 2,
                    28.2,
                    math.dist(a, b),
                    0.8,
                    4.4,
                    stone,
                    math.atan2(b[1] - a[1], b[0] - a[0]),
                )
            for radius, z0, z1 in [(8.8, 30.3, 36.0), (8.0, 36.7, 41.0)]:
                pts = ring(radius, z0, 0.65, 0.5)
                ring(radius, z1, 0.85, 0.55)
                for x, y in pts:
                    tower.box(x, y, base + (z0 + z1) / 2, 0.68, 0.68, z1 - z0, stone)
                    tower.box(x, y, base + z1 + 0.45, 0.84, 0.84, 0.65, stone)
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    for f in (0.2, 0.4, 0.6, 0.8):
                        x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                        tower.lathe(
                            x,
                            y,
                            base + z0,
                            [
                                (0.34, 0),
                                (0.34, 0.25),
                                (0.23, 0.45),
                                (0.22, z1 - z0 - 0.45),
                                (0.34, z1 - z0 - 0.20),
                                (0.34, z1 - z0),
                            ],
                            stone,
                            12,
                        )
            pts = ring(8.0, 41.4, 0.55, 0.50)
            # Low closed dome with seams; no invented third open storey.
            profile = [(7.5, 0), (7.15, 0.65), (6.5, 1.4), (5.3, 2.2), (3.5, 2.85), (0.7, 3.3)]
            tower.lathe(cx, cy, base + 41.7, profile, lead, 64)
            for j, (x, y) in enumerate(pts):
                tower.box(x, y, base + 42.4, 0.9, 0.9, 2.0, stone)
                tower.lathe(x, y, base + 43.4, [(0.62, 0), (0.62, 0.2), (0.12, 0.95)], stone, 8)
            tower.lathe(cx, cy, base + 45.0, [(0.48, 0), (0.48, 0.3), (0.15, 1.4)], stone, 16)
            tower_object = tower.done()
            # Broad tower ROI p90=55.04, p95=56.76, p99=59.81m; ignore isolated67m spike.
            for vertex in tower_object.data.vertices:
                vertex.co.z = base + 24.0 + (vertex.co.z - base - 24.0) * 1.55
            objects.append(tower_object)
            tower_status = (
                "photo-informed broad plinth, two open tiers and shallow dome; estimated dimensions"
            )
        else:
            tower_status = "omitted: estimated tower conflicts with mapped boundary"
    return {
        "created": [o.name for o in objects if o],
        "parameters": {
            "wall_height_range_m": [13.5, 30.0],
            "height_status": "EA1m DSM-DTM interpreted variable regions; no survey accuracy",
            "recessed_opening_count": opening_count,
            "portal_radius_m_estimated": 4.0,
            "portal_spring_height_m_estimated": 9.0,
            "tower_status": tower_status,
            "tower_center_xy": tower_center,
            "roof_partition": roof_parameters,
        },
        "interfaces": {"entrances": entrances, "cromwell_portal_anchor": entrance},
        "uncertainty": [
            "Mapped footprint and courtyard holes preserved; window grammar/counts/depths/heights estimated.",
            "Entrance photograph personally inspected; sculptures and inscriptions omitted; pediment and open tower abstracted.",
            "Roof partitions and barrel/skylight forms interpreted from 2011 PD aerials; hidden junctions and heights estimated; not current orthophoto.",
            "Six photo-informed stairs authored at estimated .15m rise; actual dimensions and accessible route unverified.",
        ],
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + [
                    "va-praefcke-aerial-a-2011",
                    "va-praefcke-aerial-b-2011",
                    "va-chohan-facade-2007",
                    "ea-lidar-composite-2022-tq27ne",
                ]
            )
        ),
    }


def _authored_roofs(ctx, parts, base, stone, lead, glass):
    """Licensed oblique-aerial roof grammar, clipped to original mapped triangles.

    All metre heights/partition offsets below are visual estimates. A 1 m shared
    UV grid gives consistent edges across the original footprint triangulation;
    nothing crosses its courtyard holes or outer boundary.
    """
    origin = (1068.9481244096287, -437.093373966678)
    tangent = (0.9567214489567577, 0.29100527333036774)
    inward = (-0.29100527333036774, 0.9567214489567577)
    roof = ctx.mesh("photo-informed roof ranges barrel courts rotunda and glazed ridges")
    ribs = ctx.mesh("roof ribs gutters and skylight divisions")

    def uv(p):
        d = (p[0] - origin[0], p[1] - origin[1])
        return (d[0] * tangent[0] + d[1] * tangent[1], d[0] * inward[0] + d[1] * inward[1])

    def xyz(u, v, h):
        return (
            origin[0] + u * tangent[0] + v * inward[0],
            origin[1] + u * tangent[1] + v * inward[1],
            base + h,
        )

    def tent(x, c, r, h):
        return max(0.0, 1.0 - abs(x - c) / r) * h

    def H(u, v):
        return _roof_h(u, v)

    def material(u, v):
        # Glazing strips are geometrical patches, not projected photograph textures.
        if 25 < v < 80 and any(abs(u - c) < 2.0 for c in (-41.0, -15.0, 13.0)):
            return glass
        if u > 40 and v > 90 and any(abs(v - c) < 1.0 for c in (101.0, 119.0, 137.0, 155.0, 170.0)):
            return glass
        return lead

    def clip(poly, axis, value, greater):
        out = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            da = (a[axis] - value) * (1 if greater else -1)
            db = (b[axis] - value) * (1 if greater else -1)
            if da >= -1e-9:
                out.append(a)
            if (da > 1e-9 and db < -1e-9) or (da < -1e-9 and db > 1e-9):
                t = da / (da - db)
                out.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(2)))
        clean = []
        for q in out:
            if not clean or math.dist(q, clean[-1]) > 1e-4:
                clean.append(q)
        if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-4:
            clean.pop()
        return clean

    area = 0.0
    faces = 0
    for p in parts:
        for raw in p["triangles"]:
            tri = [uv(q) for q in raw]
            for iu in range(math.floor(min(q[0] for q in tri)), math.ceil(max(q[0] for q in tri))):
                strip = clip(clip(tri, 0, iu, True), 0, iu + 1, False)
                if len(strip) < 3:
                    continue
                for iv in range(
                    math.floor(min(q[1] for q in strip)), math.ceil(max(q[1] for q in strip))
                ):
                    poly = clip(clip(strip, 1, iv, True), 1, iv + 1, False)
                    for j in range(1, len(poly) - 1):
                        a, b, c = poly[0], poly[j], poly[j + 1]
                        ar = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
                        if ar < 1e-8:
                            continue
                        roof.face(
                            [xyz(u, v, H(u, v)) for u, v in (a, b, c)],
                            material(
                                sum(q[0] for q in (a, b, c)) / 3, sum(q[1] for q in (a, b, c)) / 3
                            ),
                        )
                        faces += 1
                        area += ar
        # Roof-edge flashing closes raised slopes to inherited 24 m wall datum.
        for ring in [p["outer"]] + p.get("holes", []):
            for a, b in zip(ring, ring[1:] + ring[:1]):
                u0, v0 = uv(a)
                u1, v1 = uv(b)
                cuts = {0.0, 1.0}
                for q0, q1 in ((u0, u1), (v0, v1)):
                    if abs(q1 - q0) > 1e-10:
                        for k in range(math.floor(min(q0, q1)) + 1, math.ceil(max(q0, q1))):
                            t = (k - q0) / (q1 - q0)
                            if 1e-8 < t < 1.0 - 1e-8:
                                cuts.add(t)
                cuts = sorted(cuts)
                for t0, t1 in zip(cuts, cuts[1:]):
                    q = (u0 + (u1 - u0) * t0, v0 + (v1 - v0) * t0)
                    r = (u0 + (u1 - u0) * t1, v0 + (v1 - v0) * t1)
                    ha, hb = H(*q), H(*r)
                    points = [
                        xyz(*q, _wall_uv(*q)),
                        xyz(*r, _wall_uv(*r)),
                        xyz(*r, hb),
                        xyz(*q, ha),
                    ]
                    clean = []
                    for x in points:
                        if not clean or math.dist(x, clean[-1]) > 1e-8:
                            clean.append(x)
                    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-4:
                        clean.pop()
                    if len(clean) > 2:
                        roof.face(clean, stone)

    def contained(u, v):
        x, y, _ = xyz(u, v, 0)
        return any(
            _inside((x, y), p["outer"]) and not any(_inside((x, y), h) for h in p.get("holes", []))
            for p in parts
        )

    # Longitudinal glazing mullions and transverse barrel seams, clipped individually.
    for c in (-43.0, -39.0, -17.0, -13.0, 11.0, 15.0, 51.0, 55.0, 74.0, 78.0):
        for v in range(26, 82, 2):
            if contained(c, v) and contained(c, v + 2):
                ribs.beam(
                    xyz(c, v, H(c, v) + 0.04), xyz(c, v + 2, H(c, v + 2) + 0.04), 0.055, stone, 8
                )
    for c in (53.0, 76.0):
        for v in range(44, 82, 4):
            for j in range(22):
                u = c - 11 + j
                r = u + 1
                if contained(u, v) and contained(r, v):
                    ribs.beam(
                        xyz(u, v, H(u, v) + 0.045), xyz(r, v, H(r, v) + 0.045), 0.055, stone, 8
                    )
    return {
        "objects": [roof.done(), ribs.done()],
        "roof_faces": faces,
        "mapped_projected_area_m2": area,
        "classification": "2011 oblique-photo-informed roof grammar; authored dimensions estimated",
        "components": [
            "narrow south pitched range",
            "east twin Cast Court barrel roofs",
            "west octagonal low rotunda",
            "courtyard gallery ranges",
            "north parallel glazed pitched strips",
        ],
    }
