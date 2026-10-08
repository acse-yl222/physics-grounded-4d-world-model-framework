"""RCM: mapped exterior with evidence-informed north facade; estimates labelled."""

import math

SOURCE = "rcm-julian-herzog-north-2020"
TOWER_EDGES = [
    ((666.4024973495, -59.6899618236), (656.9627111228, -61.0785909807)),
    ((718.4653462117, -50.7438453510), (706.9753060637, -52.4900699174)),
]


def tower_ring(a, b):
    L = math.dist(a, b)
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    return [a, b, (b[0] - nx * 8, b[1] - ny * 8), (a[0] - nx * 8, a[1] - ny * 8)]


def roof_triangles(triangles):
    # Exact convex half-plane subtraction: preserve original roof polygon and
    # remove the tower interiors, so lower roof cannot obstruct tower glazing.
    def half(poly, a, b, inside):
        def d(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

        result = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            dp, dq = d(p), d(q)
            ip = dp >= -1e-9 if inside else dp <= 1e-9
            iq = dq >= -1e-9 if inside else dq <= 1e-9
            if ip:
                result.append(p)
            if ip != iq and abs(dp - dq) > 1e-12:
                t = dp / (dp - dq)
                result.append(tuple(p[k] + t * (q[k] - p[k]) for k in range(2)))
        return result

    polygons = list(triangles)
    for a, b in TOWER_EDGES:
        ring = tower_ring(a, b)
        out = []
        for poly in polygons:
            remainder = poly
            for c, d in zip(ring, ring[1:] + ring[:1]):
                if len(remainder) < 3:
                    break
                outside = half(remainder, c, d, False)
                if len(outside) >= 3:
                    out.append(outside)
                remainder = half(remainder, c, d, True)
        polygons = out
    return [
        [p[0], p[i], p[i + 1]]
        for p in polygons
        for i in range(1, len(p) - 1)
        if abs(
            (p[i][0] - p[0][0]) * (p[i + 1][1] - p[0][1])
            - (p[i][1] - p[0][1]) * (p[i + 1][0] - p[0][0])
        )
        > 1e-8
    ]


def build(ctx, feature):
    brick = ctx.material("RCM red brick", (0.46, 0.18, 0.10), 0.85)
    stone = ctx.material("RCM pale stone", (0.72, 0.64, 0.50), 0.8)
    slate = ctx.material("RCM slate", (0.17, 0.20, 0.23), 0.65)
    glass = ctx.material("RCM recessed glazing", (0.055, 0.105, 0.13), 0.27)
    door_mat = ctx.material("RCM dark timber", (0.08, 0.055, 0.04), 0.65)
    if not brick.node_tree.nodes.get("RCM brick courses"):
        nodes = brick.node_tree.nodes
        links = brick.node_tree.links
        shader = nodes.get("Principled BSDF")
        tex = nodes.new("ShaderNodeTexBrick")
        tex.name = "RCM brick courses"
        tex.inputs["Color1"].default_value = (0.32, 0.09, 0.035, 1)
        tex.inputs["Color2"].default_value = (0.45, 0.15, 0.065, 1)
        tex.inputs["Mortar"].default_value = (0.23, 0.19, 0.15, 1)
        tex.inputs["Scale"].default_value = 2
        tex.inputs["Mortar Size"].default_value = 0.012
        tex.inputs["Brick Width"].default_value = 0.23
        tex.inputs["Row Height"].default_value = 0.075
        uv = nodes.new("ShaderNodeTexCoord")
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.24
        bump.inputs["Distance"].default_value = 0.012
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        links.new(tex.outputs["Color"], shader.inputs["Base Color"])
        brick["glb_fallback"] = (
            "Base brick color; procedural joints remain in native blend, no image textures downsampled."
        )
    m = ctx.mesh("mapped exterior and recessed openings")
    base = float(feature.get("base_m", 0))
    entrances = []
    masonry_joint = ctx.material("RCM masonry joints", (0.19, 0.10, 0.055), 0.95)
    metal = ctx.material("RCM ironwork", (0.055, 0.055, 0.045), 0.5, 0.65)
    # Stable north window axes from the inspected photograph, projected onto
    # each mapped edge rather than resetting the pitch at every GIS vertex.
    north_axes = [
        660.1,
        663.1,
        668.2,
        671.0,
        673.8,
        676.6,
        679.4,
        683.5,
        688.4,
        693.0,
        696.1,
        699.2,
        702.3,
        705.4,
        710.5,
        714.4,
    ]

    def wall(a, b, zmin, zmax, front=False, door=False):
        L = math.dist(a, b)
        if L < 0.001:
            return
        tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = ty, -tx
        ang = math.atan2(ty, tx)

        def p(u, z, d=0):
            return (a[0] + tx * u - nx * d, a[1] + ty * u - ny * d, base + z)

        n = max(1, round(L / 3.6))
        cs = [(i + 0.5) * L / n for i in range(n)] if L > 2.7 else []
        tower_front = front and (max(a[0], b[0]) < 667 or min(a[0], b[0]) > 706.8)
        if front and zmin < 20:
            cs = [(x - a[0]) / tx for x in north_axes if 0.95 < (x - a[0]) / tx < L - 0.95]
        if front and zmin >= 20:
            cs = [L * 0.35, L * 0.65]

        openings = []
        bands = (
            [(1.6, 4.1), (5.6, 8), (9.4, 12.5), (14, 17)] if zmin < 20 else [(21, 23.6), (25, 28.5)]
        )
        for c in cs:
            for lo, hi in bands:
                if tower_front and lo >= 14 and zmin < 20:
                    continue
                if lo >= zmin and hi <= zmax:
                    openings.append((c - 0.8, c + 0.8, lo, hi, False))
        if door:
            ends = sorted(((684.70 - a[0]) / tx, (687.34 - a[0]) / tx))
            portal_left = max(0, ends[0])
            portal_right = min(L, ends[1])
            openings = [
                o for o in openings if o[2] > 4.2 or o[1] < portal_left or o[0] > portal_right
            ]
            if portal_right > portal_left:
                openings.append((portal_left, portal_right, 0.6, 4.2, True))
        if front and zmin >= 20:
            openings = [o for o in openings if o[2] < 25] + [
                (L / 2 - 1.95, L / 2 + 1.95, 25, 28.8, False)
            ]
        cuts = sorted(set([zmin, zmax] + [v for o in openings for v in o[2:4]]))
        for lo, hi in zip(cuts, cuts[1:]):
            holes = sorted((o[0], o[1]) for o in openings if o[2] <= lo and o[3] >= hi)
            cursor = 0
            for left, right in holes + [(L, L)]:
                if left > cursor:
                    m.face([p(cursor, lo), p(left, lo), p(left, hi), p(cursor, hi)], brick)
                cursor = right
        for left, right, lo, hi, isdoor in openings:
            if isdoor:
                continue  # Shared central portal authored once across two GIS segments.
            dep = 0.45 if isdoor else 0.30
            # Main-wing upper windows alternate arched and rectangular heads.
            xcenter = p((left + right) / 2, 0)[0]
            arched = (
                isdoor
                or (
                    front
                    and zmin < 20
                    and lo >= 14
                    and min(range(len(north_axes)), key=lambda i: abs(north_axes[i] - xcenter)) % 2
                    == 0
                )
                or zmin >= 20
                and lo >= 25
            )
            radius = (right - left) / 2
            mid = (left + right) / 2
            spring = hi - radius
            arc = [
                (
                    mid + radius * math.cos(t * math.pi / 24),
                    spring + radius * math.sin(t * math.pi / 24),
                )
                for t in range(25)
            ]
            outline = (
                [(left, lo), (right, lo)] + arc
                if arched
                else [(left, lo), (right, lo), (right, hi), (left, hi)]
            )
            m.face([p(u, z, dep) for u, z in outline], door_mat if isdoor else glass)
            if arched:
                for u, v in zip(arc, arc[1:]):
                    m.face([p(*u), p(u[0], hi), p(v[0], hi), p(*v)], brick)
                    m.beam(p(*u, -0.055), p(*v, -0.055), 0.11, stone, 8)
            for u, v in zip(outline, outline[1:] + outline[:1]):
                m.face([p(*u), p(*v), p(*v, dep), p(*u, dep)], stone)
            for c in (
                [left, right, mid - 0.65, mid + 0.65]
                if front and zmin >= 20 and lo >= 25
                else [left, right, mid]
            ):
                top = (
                    (spring + math.sqrt(max(0, radius**2 - (c - mid) ** 2)))
                    if arched and left < c < right
                    else (spring if arched else hi)
                )
                m.box(*p(c, (lo + top) / 2, 0.12), 0.09, 0.16, top - lo, stone, ang)
            for zz in [lo, lo + (spring - lo) * 0.65 if arched else lo + (hi - lo) * 0.65]:
                m.box(*p(mid, zz, 0.08), right - left + 0.15, 0.20, 0.10, stone, ang)
            if not arched:
                m.box(*p(mid, hi, 0.08), right - left + 0.15, 0.20, 0.10, stone, ang)
            # Ashlar window dressings and projecting ledge, genuine mesh.
            if front:
                m.box(*p(mid, lo - 0.12, -0.13), right - left + 0.52, 0.52, 0.20, stone, ang)
                if not isdoor:
                    for c in (left - 0.14, right + 0.14):
                        for zz in (lo + 0.3, lo + 0.85, lo + 1.4, lo + 1.95):
                            if zz < spring:
                                m.box(*p(c, zz, -0.045), 0.19, 0.20, 0.44, stone, ang)
                    if 9 < lo < 10 or tower_front and 9 < lo < 10:
                        # Observed alternating triangular and curved pediments.
                        m.box(*p(mid, hi + 0.16, -0.12), 2.2, 0.35, 0.18, stone, ang)
                        if round(xcenter) % 2:
                            for side in (-1, 1):
                                m.beam(
                                    p(mid + side * 1.1, hi + 0.25, -0.12),
                                    p(mid, hi + 0.88, -0.12),
                                    0.09,
                                    stone,
                                    10,
                                )
                        else:
                            arc2 = [
                                p(
                                    mid + 1.05 * math.cos(t * math.pi / 24),
                                    hi + 0.23 + 0.56 * math.sin(t * math.pi / 24),
                                    -0.12,
                                )
                                for t in range(25)
                            ]
                            for aa, bb in zip(arc2, arc2[1:]):
                                m.beam(aa, bb, 0.09, stone, 10)
                    # Timber sash subdivision is distinct from stone mullions.
                    for offset in (-0.37, 0.37):
                        m.box(
                            *p(mid + offset, (lo + spring) / 2, 0.21),
                            0.035,
                            0.06,
                            spring - lo,
                            door_mat,
                            ang,
                        )
                else:
                    # Portal voussoirs outside the open arched aperture.
                    for i in range(17):
                        t0 = i * math.pi / 17 + 0.012
                        t1 = (i + 1) * math.pi / 17 - 0.012
                        vv = [
                            p(mid + r * math.cos(t), spring + r * math.sin(t), -0.18)
                            for r, t in [
                                (radius + 0.07, t0),
                                (radius + 0.37, t0),
                                (radius + 0.37, t1),
                                (radius + 0.07, t1),
                            ]
                        ]
                        m.face(vv, stone)
                    for side in (-1, 1):
                        c = mid + side * (radius + 0.48)
                        for k in range(8):
                            m.box(*p(c, 0.85 + k * 0.43, -0.22), 0.5, 0.6, 0.40, stone, ang)
                        m.box(*p(c, 0.75, -0.28), 0.7, 0.72, 0.30, stone, ang)
                        m.box(*p(c, 3.7, -0.28), 0.7, 0.72, 0.25, stone, ang)
                    m.box(*p(mid, hi + 0.60, -0.48), 4.0, 1.0, 0.26, stone, ang)
                    m.box(*p(mid, hi + 0.82, -0.50), 4.25, 1.06, 0.16, stone, ang)
                    # Canopy remains above clearance; handrails beside stairs.
                    for side in (-1, 1):
                        for d in (0.35, 1.6):
                            m.beam(
                                p(mid + side * 1.35, 0.15, -d),
                                p(mid + side * 1.35, 1.0, -d),
                                0.035,
                                metal,
                                10,
                            )
                        m.beam(
                            p(mid + side * 1.35, 1.0, -0.35),
                            p(mid + side * 1.35, 1.0, -1.6),
                            0.035,
                            metal,
                            10,
                        )
        for zz in [1.1, 4.8, 8.6, 13.2, 18, 19.7] if front and zmin < 20 else [zmax - 0.15]:
            # Avoid a rustication band crossing the raised entrance opening.
            if door and 0.6 < zz < 4.2:
                for aa, bb in [(0, portal_left), (portal_right, L)]:
                    if bb > aa:
                        m.box(*p((aa + bb) / 2, zz, -0.1), bb - aa, 0.36, 0.22, stone, ang)
            else:
                m.box(*p(L / 2, zz, -0.1), L, 0.36, 0.22, stone, ang)
        if front:
            # Corbel table beneath the cornice and fine lower brick coursing.
            for c in [(0.25 + i * 0.42) for i in range(max(0, int((L - 0.5) / 0.42)))]:
                m.box(*p(c, zmax - 0.55, -0.12), 0.18, 0.4, 0.32, stone, ang)
            for c in (0.18, L - 0.18):
                for k in range(max(1, int((zmax - zmin) / 0.55))):
                    zz = zmin + 0.27 + k * 0.55
                    if not (door and zz < 4.5 and 684.5 < p(c, 0)[0] < 687.5):
                        m.box(*p(c, zz, -0.06), 0.30, 0.24, 0.50, stone, ang)

    for part in feature["geometry"]:
        for idx, raw in enumerate([part["outer"]] + part.get("holes", [])):
            area = sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(raw, raw[1:] + raw[:1]))
            ring = raw if (area > 0) == (idx == 0) else list(reversed(raw))
            for a, b in zip(ring, ring[1:] + ring[:1]):
                front = idx == 0 and b[0] < a[0] and abs(b[0] - a[0]) > abs(b[1] - a[1])
                wall(
                    a,
                    b,
                    0,
                    20,
                    front,
                    front and min(a[0], b[0]) < 687.34 and max(a[0], b[0]) > 684.70,
                )
        for tri in part["triangles"]:
            m.face([(x, y, base) for x, y in reversed(tri)], brick)
        # One shared roof field, clipped into exact planar regions. Independent
        # nonlinear triangle sampling produced visible folds at GIS seams.
        # Axis follows the observed north facade; all roof dimensions estimated.
        axis = (0.989, 0.148)
        norm = math.hypot(*axis)
        ux, uy = axis[0] / norm, axis[1] / norm
        vx, vy = -uy, ux
        points = part["outer"]
        us = [x * ux + y * uy for x, y in points]
        vs = [x * vx + y * vy for x, y in points]
        u0, u1 = min(us), max(us)
        v0, v1 = min(vs), max(vs)
        slope = 0.75
        planes = [
            (slope * ux, slope * uy, -slope * u0),
            (-slope * ux, -slope * uy, slope * u1),
            (slope * vx, slope * vy, -slope * v0),
            (-slope * vx, -slope * vy, slope * v1),
            (0.0, 0.0, 5.0),
        ]

        def value(plane, p):
            return plane[0] * p[0] + plane[1] * p[1] + plane[2]

        def rise(p):
            return max(0.0, min(value(q, p) for q in planes))

        def clip(poly, fn):
            out = []
            for a, b in zip(poly, poly[1:] + poly[:1]):
                da, db = fn(a), fn(b)
                if da >= -1e-9:
                    out.append(a)
                if da * db < 0 and abs(da) > 1e-9 and abs(db) > 1e-9:
                    t = da / (da - db)
                    out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(2)))
            return out

        def triangles(poly, material):
            for i in range(1, len(poly) - 1):
                a, b, c = poly[0], poly[i], poly[i + 1]
                ab = [b[k] - a[k] for k in range(3)]
                ac = [c[k] - a[k] for k in range(3)]
                area2 = sum(
                    (ab[(k + 1) % 3] * ac[(k + 2) % 3] - ab[(k + 2) % 3] * ac[(k + 1) % 3]) ** 2
                    for k in range(3)
                )
                if area2 > 1e-14:
                    m.face([a, b, c], material)

        for tri in roof_triangles(part["triangles"]):
            for i, plane in enumerate(planes):
                poly = list(tri)
                for j, other in enumerate(planes):
                    if i != j:
                        poly = (
                            clip(poly, lambda p: value(other, p) - value(plane, p)) if poly else []
                        )
                triangles([(x, y, base + 20 + value(plane, (x, y))) for x, y in poly], slate)
        # Close every original boundary from wall eaves to the actual roof
        # height, splitting at all shared roof-plane breaks. Tower regions are
        # excluded: their existing 20–30 m walls provide the closure instead.
        towers = [tower_ring(a, b) for a, b in TOWER_EDGES]

        def in_tower(p, ring):
            return all(
                (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-8
                for a, b in zip(ring, ring[1:] + ring[:1])
            )

        for ring in [part["outer"]] + part.get("holes", []):
            for a, b in zip(ring, ring[1:] + ring[:1]):
                cuts = [0.0, 1.0]
                for i, plane in enumerate(planes):
                    for other in planes[i + 1 :]:
                        da = value(plane, a) - value(other, a)
                        db = value(plane, b) - value(other, b)
                        if da * db < 0:
                            cuts.append(da / (da - db))
                for tower in towers:
                    for c, d in zip(tower, tower[1:] + tower[:1]):
                        da = (d[0] - c[0]) * (a[1] - c[1]) - (d[1] - c[1]) * (a[0] - c[0])
                        db = (d[0] - c[0]) * (b[1] - c[1]) - (d[1] - c[1]) * (b[0] - c[0])
                        if da * db < 0:
                            cuts.append(da / (da - db))
                cuts = sorted(set(round(t, 12) for t in cuts))

                def at(t):
                    return tuple(a[k] + t * (b[k] - a[k]) for k in range(2))

                for lo, hi in zip(cuts, cuts[1:]):
                    if any(in_tower(at((lo + hi) / 2), tower) for tower in towers):
                        continue
                    p, q = at(lo), at(hi)
                    triangles(
                        [
                            (*p, base + 20),
                            (*q, base + 20),
                            (*q, base + 20 + rise(q)),
                            (*p, base + 20 + rise(p)),
                        ],
                        brick,
                    )
    for a, b in TOWER_EDGES:
        L = math.dist(a, b)
        tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = ty, -tx
        ring = [a, b, (b[0] - nx * 8, b[1] - ny * 8), (a[0] - nx * 8, a[1] - ny * 8)]
        for k, (c, d) in enumerate(zip(ring, ring[1:] + ring[:1])):
            wall(c, d, 20, 30, k == 0)
        cx = sum(p[0] for p in ring) / 4
        cy = sum(p[1] for p in ring) / 4
        for c, d in zip(ring, ring[1:] + ring[:1]):
            m.face([(*c, base + 30), (*d, base + 30), (cx, cy, base + 42)], slate)
        # Raised slate courses on the tower planes, no displacement of outline.
        for z in [30.4 + i * 0.45 for i in range(25)]:
            t = (z - 30) / 12
            corners = [(c[0] * (1 - t) + cx * t, c[1] * (1 - t) + cy * t, base + z) for c in ring]
            for c, d in zip(corners, corners[1:] + corners[:1]):
                m.beam(c, d, 0.015, slate, 6)
        # Small roof dormer visible on each steep tower roof in north photo.
        ax, ay = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2

        def rp(u, z, d=0):
            return (ax + tx * u - nx * (1.05 + d), ay + ty * u - ny * (1.05 + d), base + z)

        ww = 0.82
        z0 = 32
        z1 = 34.6
        zt = 35.8
        for side in (-1, 1):
            m.box(*rp(side * 0.71, (z0 + z1) / 2), 0.22, 0.35, z1 - z0, stone, math.atan2(ty, tx))
            m.face(
                [
                    rp(side * ww, z0),
                    rp(side * ww, z1),
                    rp(side * ww, z1, 1.2),
                    rp(side * ww, z0, 1.2),
                ],
                brick,
            )
            m.face([rp(side * ww, z1), rp(0, zt), rp(0, zt, 1.2), rp(side * ww, z1, 1.2)], slate)
            m.beam(rp(side * ww, z1, -0.12), rp(0, zt, -0.12), 0.09, stone, 10)
        m.face(
            [
                rp(-0.6, z0 + 0.1, 0.25),
                rp(0.6, z0 + 0.1, 0.25),
                rp(0.6, z1 - 0.1, 0.25),
                rp(-0.6, z1 - 0.1, 0.25),
            ],
            glass,
        )
        for zz in (z0, z0 + 1.1, z1):
            m.box(*rp(0, zz, 0.1), 1.65, 0.35, 0.12, stone, math.atan2(ty, tx))
        m.box(*rp(0, (z0 + z1) / 2, 0.1), 0.07, 0.15, z1 - z0, stone, math.atan2(ty, tx))
        m.face([rp(-ww, z1), rp(ww, z1), rp(0, zt)], brick)
        m.face(
            [rp(-ww, z0, 1.2), rp(ww, z0, 1.2), rp(ww, z1, 1.2), rp(0, zt, 1.2), rp(-ww, z1, 1.2)],
            brick,
        )
        # Metal finial at each tower apex.
        m.beam((cx, cy, base + 42), (cx, cy, base + 43.2), 0.035, metal, 12)
        m.beam((cx - 0.3, cy, base + 42.75), (cx + 0.3, cy, base + 42.75), 0.025, metal, 10)
        for c in [a, b]:
            m.lathe(
                c[0], c[1], base + 20, [(0.55, 0), (0.55, 9.4), (0.7, 9.5), (0.55, 10)], brick, 24
            )
            m.lathe(c[0], c[1], base + 30, [(0.65, 0), (0.035, 4.6)], slate, 48)
            for zz in (21, 24, 24.45, 28.8, 29.6):
                m.lathe(
                    c[0],
                    c[1],
                    base + zz,
                    [(0.59, 0), (0.63, 0.07), (0.63, 0.16), (0.59, 0.23)],
                    stone,
                    48,
                )
            m.beam((c[0], c[1], base + 34.6), (c[0], c[1], base + 35.4), 0.025, metal, 10)

    # Central portal bridges the mapped north-wall vertex, preventing the old
    # per-edge off-centre doorway. Host walls are cut over both intersected edges.
    def portal():
        tx, ty = 0.989, 0.148
        norm = math.hypot(tx, ty)
        tx /= norm
        ty /= norm
        nx, ny = -ty, tx
        ang = math.atan2(ty, tx)

        def p(u, z, d=0):
            return (
                686.0217768969 + tx * u + nx * (0.12 - d),
                -57.3517698338 + ty * u + ny * (0.12 - d),
                base + z,
            )

        rad = 1.15
        lo = 0.6
        hi = 4.2
        spring = hi - rad
        arc = [
            (rad * math.cos(i * math.pi / 32), spring + rad * math.sin(i * math.pi / 32))
            for i in range(33)
        ]
        outline = [(-rad, lo), (rad, lo)] + arc
        m.face([p(u, z, 0.45) for u, z in outline], door_mat)
        for a, b in zip(outline, outline[1:] + outline[:1]):
            m.face([p(*a), p(*b), p(*b, 0.45), p(*a, 0.45)], stone)
        for a, b in zip(arc, arc[1:]):
            m.face([p(*a), p(a[0], hi), p(b[0], hi), p(*b)], stone)
        for side in (-1, 1):
            m.box(*p(side * 1.235, (lo + hi) / 2, 0.03), 0.17, 0.30, hi - lo, stone, ang)
            m.box(*p(side * rad, (lo + spring) / 2, 0.12), 0.09, 0.16, spring - lo, stone, ang)
            for k in range(8):
                m.box(*p(side * 1.47, 0.83 + k * 0.42, -0.10), 0.46, 0.55, 0.39, stone, ang)
            m.box(*p(side * 1.47, 0.78, -0.18), 0.66, 0.72, 0.32, stone, ang)
            m.box(*p(side * 1.47, 3.65, -0.18), 0.66, 0.72, 0.24, stone, ang)
            # Recessed timber leaf panels and metal handles remain behind clear approach.
            for zz in (1.3, 2.2):
                m.box(*p(side * 0.575, zz, 0.405), 0.76, 0.055, 0.65, door_mat, ang)
            m.beam(p(side * 0.17, 1.45, 0.35), p(side * 0.17, 1.7, 0.35), 0.02, metal, 12)
        m.box(*p(0, (lo + hi) / 2, 0.12), 0.09, 0.16, hi - lo, stone, ang)
        for zz in (lo, 2.8):
            m.box(*p(0, zz, 0.08), 2.45, 0.20, 0.10, stone, ang)
        for i in range(19):
            t0 = i * math.pi / 19 + 0.008
            t1 = (i + 1) * math.pi / 19 - 0.008
            m.face(
                [
                    p(r * math.cos(t), spring + r * math.sin(t), -0.17)
                    for r, t in [
                        (rad + 0.04, t0),
                        (rad + 0.37, t0),
                        (rad + 0.37, t1),
                        (rad + 0.04, t1),
                    ]
                ],
                stone,
            )
        for zz, w, d in [(4.65, 3.95, 0.95), (4.87, 4.2, 1.08)]:
            m.box(*p(0, zz, -0.4), w, d, 0.22, stone, ang)
        for i in range(4):
            depth = 0.8 + (3 - i) * 0.32
            m.box(*p(0, 0.075 * (i + 1), -depth / 2), 2.8, depth, 0.15 * (i + 1), stone, ang)
        for side in (-1, 1):
            for d in (0.35, 1.6):
                m.beam(p(side * 1.34, 0.15, -d), p(side * 1.34, 1.0, -d), 0.035, metal, 10)
            m.beam(p(side * 1.34, 1.0, -0.35), p(side * 1.34, 1.0, -1.6), 0.035, metal, 10)
        for offset in (-0.575, 0.575):
            entrances.append(
                {
                    "threshold_xyz": list(p(offset, 0.65)),
                    "outward_normal": [nx, ny, 0],
                    "door_leaf_xyz": list(p(offset, 2.4, 0.45)),
                    "door_leaf_depth_m": 0.45,
                    "clear_width_m": 1.06,
                    "stair_treads": 4,
                    "riser_m": 0.15,
                    "tread_m": 0.32,
                    "landing_depth_m": 0.8,
                    "landing_z_m": base + 0.6,
                    "sill_step_m": 0.05,
                    "ramp": "unverified",
                    "supporting_surface": "authored stair landing and sill; estimated",
                    "estimated": True,
                }
            )

    portal()

    def dormer(x, y, w, body_top, top, central=False):
        tx, ty = 0.989, 0.148
        norm = math.hypot(tx, ty)
        tx /= norm
        ty /= norm
        nx, ny = -ty, tx
        ang = math.atan2(ty, tx)
        depth = 4.0 if central else 2.8

        # Project the visible wall 0.5 m in front of mapped eaves; its window
        # glass remains ahead of the original roof perimeter closure.
        def p(u, z, d=0):
            return (x + tx * u + nx * (0.5 - d), y + ty * u + ny * (0.5 - d), base + z)

        width = 1.50 if central else 0.68
        centers = (-1.25, 1.25) if central else (-0.62, 0.62)
        lo = 20.25
        hi = 24.8 if central else 23.7
        holes = [(c - width / 2, c + width / 2) for c in centers]
        cursor = -w / 2
        for left, right in holes + [(w / 2, w / 2)]:
            if left > cursor:
                m.face([p(cursor, 20), p(left, 20), p(left, body_top), p(cursor, body_top)], brick)
            cursor = right
        for left, right in holes:
            m.face([p(left, 20), p(right, 20), p(right, lo), p(left, lo)], brick)
            m.face([p(left, hi), p(right, hi), p(right, body_top), p(left, body_top)], brick)
            mid = (left + right) / 2
            rad = (right - left) / 2
            spring = hi - rad
            outline = [(left, lo), (right, lo)]
            if central:
                arc = [
                    (
                        mid + rad * math.cos(i * math.pi / 24),
                        spring + rad * math.sin(i * math.pi / 24),
                    )
                    for i in range(25)
                ]
                outline += arc
                for a, b in zip(arc, arc[1:]):
                    m.face([p(*a), p(a[0], hi), p(b[0], hi), p(*b)], brick)
                    m.beam(p(*a, -0.06), p(*b, -0.06), 0.075, stone, 10)
            else:
                outline += [(right, hi), (left, hi)]
            m.face([p(u, z, 0.3) for u, z in outline], glass)
            for a, b in zip(outline, outline[1:] + outline[:1]):
                m.face([p(*a), p(*b), p(*b, 0.3), p(*a, 0.3)], stone)
            for u in (left, mid, right):
                m.box(*p(u, (lo + spring) / 2, 0.13), 0.07, 0.16, spring - lo, stone, ang)
            for z in [lo, lo + 1.05, lo + 2.05, hi]:
                if z <= hi:
                    m.box(*p(mid, z, 0.1), right - left + 0.14, 0.24, 0.09, stone, ang)
        # Closed cheeks and small slate roof, real opening in front panel.
        for side in (-1, 1):
            u = side * w / 2
            m.face([p(u, 20), p(u, body_top), p(u, body_top, depth), p(u, 20, depth)], brick)
            if not central:
                m.face([p(u, body_top), p(0, top), p(0, top, depth), p(u, body_top, depth)], slate)
        if central:
            # Observed shouldered clock gable, smaller crowning pediment.
            left = [
                (-w / 2, body_top),
                (-3.85, 25.3),
                (-3.85, 25.7),
                (-2.65, 25.7),
                (-1.70, 27.0),
                (-1.70, 28.4),
                (-1.35, 28.4),
                (-1.35, 28.8),
                (-0.72, 28.8),
                (0, top),
            ]
            profile = left + [(-u, z) for u, z in reversed(left[:-1])]
            m.face([p(u, z) for u, z in reversed(profile)], brick)
            for a, b in zip(profile, profile[1:]):
                m.face([p(*a), p(*b), p(*b, depth), p(*a, depth)], slate)
                m.beam(p(*a, -0.12), p(*b, -0.12), 0.12, stone, 12)
            for zz, ww in [(28.4, 3.75), (28.8, 3.05)]:
                m.box(*p(0, zz, -0.1), ww, 0.48, 0.16, stone, ang)
        else:
            m.face([p(-w / 2, body_top), p(w / 2, body_top), p(0, top)], brick)
        m.face(
            [
                p(-w / 2, 20, depth),
                p(w / 2, 20, depth),
                p(w / 2, body_top, depth),
                p(-w / 2, body_top, depth),
            ],
            brick,
        )
        if central:
            m.face([p(u, z, depth) for u, z in profile], brick)
        else:
            m.face([p(-w / 2, body_top, depth), p(0, top, depth), p(w / 2, body_top, depth)], brick)
        # Limestone gable coping with projecting horizontal feet.
        for side in (-1, 1):
            if not central:
                m.beam(p(side * w / 2, body_top, -0.12), p(0, top, -0.12), 0.13, stone, 12)
            m.box(*p(side * w / 2, body_top, -0.12), 0.55, 0.45, 0.20, stone, ang)
            if central:
                for z in [20.3 + i * 0.6 for i in range(12)]:
                    m.box(*p(side * (w / 2 - 0.1), z, -0.12), 0.32, 0.36, 0.54, stone, ang)
                m.lathe(
                    *p(side * (w / 2 - 0.05), body_top, -0.05),
                    [(0.23, 0), (0.23, 0.6), (0.32, 0.7), (0.13, 1.3), (0.03, 1.7)],
                    stone,
                    32,
                )
        # Circular carved medallion (not a falsely claimed roof aperture).
        if not central:
            zz = body_top + 0.78
            ring = [
                p(
                    0.35 * math.cos(i * math.tau / 48),
                    zz + 0.35 * math.sin(i * math.tau / 48),
                    -0.04,
                )
                for i in range(48)
            ]
            m.face(ring, brick)
            for a, b in zip(ring, ring[1:] + ring[:1]):
                m.beam(a, b, 0.08, stone, 10)
        m.lathe(*p(0, top, -0.1), [(0.17, 0), (0.20, 0.12), (0.08, 0.55), (0.025, 0.9)], stone, 32)

    for args in [
        (670.3, -61.32, 3.1, 24.1, 26.4),
        (677.1, -60.31, 3.1, 24.1, 26.4),
        (695.5, -57.44, 3.1, 24.1, 26.4),
        (702.3, -56.42, 3.1, 24.1, 26.4),
    ]:
        dormer(*args)
    dormer(686, -57.36, 8.5, 25.3, 30, True)
    # Two chimney stacks are visible in the inspected north photograph.
    # Their setbacks and dimensions are estimates; no hidden plant added.
    for x, y in [(680.5, -63.3), (692.7, -61.5)]:
        m.box(x, y, base + 25.8, 0.85, 1.0, 5.6, brick, math.atan2(0.148, 0.989))
        for zz in (27.8, 28.1, 28.6):
            m.box(x, y, base + zz, 1.05, 1.2, 0.18, stone, math.atan2(0.148, 0.989))

    # Raised circular clock dial on the central gable, procedural materials.
    def cp(u, z, d=0):
        return (
            686 + 0.989 * u - 0.148 * (d + 0.6),
            -57.36 + 0.148 * u + 0.989 * (d + 0.6),
            base + 27.1 + z,
        )

    dial = [
        cp(1.02 * math.cos(i * math.tau / 64), 1.02 * math.sin(i * math.tau / 64), 0.10)
        for i in range(64)
    ]
    m.face(dial, stone)
    for a, b in zip(dial, dial[1:] + dial[:1]):
        m.beam(a, b, 0.085, stone, 8)
    for i in range(12):
        t = i * math.tau / 12
        m.beam(
            cp(0.81 * math.cos(t), 0.81 * math.sin(t), 0.13),
            cp(0.94 * math.cos(t), 0.94 * math.sin(t), 0.13),
            0.023,
            door_mat,
            6,
        )
    m.beam(cp(0, 0, 0.15), cp(0.18, 0.68, 0.15), 0.035, door_mat, 8)
    m.beam(cp(0, 0, 0.15), cp(-0.45, 0.1, 0.15), 0.04, door_mat, 8)
    # Arch-panel quads meeting the crown can have a repeated corner. Author
    # these as triangles, retaining every nonzero surface without zero-area
    # triangulation artifacts (no decimation or normal-only concealment).
    clean_faces = []
    clean_materials = []
    for face, material in zip(m.f, m.mi):
        clean = []
        for index in face:
            if not clean or math.dist(m.v[clean[-1]], m.v[index]) > 1e-8:
                clean.append(index)
        if len(clean) > 1 and math.dist(m.v[clean[0]], m.v[clean[-1]]) <= 1e-8:
            clean.pop()
        if len(clean) >= 3:
            clean_faces.append(tuple(clean))
            clean_materials.append(material)
    m.f = clean_faces
    m.mi = clean_materials
    obj = m.done()
    return {
        "created": [obj.name],
        "parameters": {
            "eaves_m": 20,
            "tower_apex_m": 42,
            "tower_finial_m": 43.2,
            "north_window_axes_x": north_axes,
            "phase5_detail": "stable facade axes, pediments, sash glazing, four open dormers, central double-arched gable, stone portal, clock, finials, cornice dentils and observed chimney pair",
            "dimensions_status": "visual estimates, not survey",
            "footprint": "unchanged mapped rings",
            "roof": "estimated continuous piecewise-planar hip field, 20 m eaves / 25 m cap, tower pyramids; north-facade axis (.989,.148)",
        },
        "interfaces": {"entrances": entrances},
        "uncertainty": [
            "North facade informed by inspected 2020 photograph; all heights, bay spacing and entrance dimensions are estimated. Arched upper and entrance openings use 24-segment real reveals.",
            "Hidden elevations use schematic window grammar. Clock dial, stone relief and chimney dimensions are interpreted; four dormers and the central gable now have real recessed glazing. No hidden roof equipment added.",
            "Mapped main feature has no holes; adjacent rear additions are separate inventory features. Shared walls retained pending coordinator interval verification. Roof axis, slope and 25 m capped ridge are estimates; shared planar clipping and vertical perimeter closures preserve mapped plan.",
        ],
        "evidence_source_ids": list(
            dict.fromkeys(feature.get("evidence_source_ids", []) + [SOURCE])
        ),
    }
