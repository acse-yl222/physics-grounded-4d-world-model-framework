"""Science Museum: mapped plan, authored east colonnade; estimated secondary wings.
Photo evidence: A. Brady2004 and Shadowssettle2020; roof evidence PD2011 + EA OGL2022.
Other elevations and heights are explicitly estimated, not verified current fabric.
"""

import math


def build(ctx, feature):
    stone = ctx.material("Science Museum Portland stone", (0.66, 0.63, 0.54), 0.78)
    brick = ctx.material("Science historical red brick secondary wings", (0.40, 0.17, 0.11), 0.87)
    patina = ctx.material(
        "Science photographed pale green barrel covering", (0.48, 0.66, 0.55), 0.72
    )
    shadow = ctx.material("Science Museum masonry joints", (0.38, 0.37, 0.33), 0.92)
    glass = ctx.material("Science Museum recessed glazing", (0.075, 0.105, 0.115), 0.22, 0)
    bronze = ctx.material("Science Museum dark bronze frames", (0.13, 0.12, 0.095), 0.4, 0.35)
    roofmat = ctx.material("Science Museum estimated grey roof", (0.20, 0.22, 0.23), 0.85)
    walls = ctx.mesh("Science Museum | pierced masonry")
    windows = ctx.mesh("Science Museum | recessed glass and bronze frames")
    detail = ctx.mesh("Science Museum | colonnade and stone mouldings")
    roof = ctx.mesh("Science Museum | estimated roof zones")
    # Fixed in the shared UTM frame: true mapped east facade, south to north.
    a = (907.0389694146579, -328.67046609614044)
    b = (896.3357559732394, -261.7295569181442)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    tx, ty = dx / L, dy / L
    nx, ny = ty, -tx

    def station(p):
        return (p[0] - a[0]) * tx + (p[1] - a[1]) * ty

    def depth(p):
        return -(p[0] - a[0]) * nx - (p[1] - a[1]) * ny

    # EA relative-height evidence places long-gallery eaves near the 26m front datum.
    def height(p):
        return 26.0

    nopen = 0
    entries = []
    # Coalesce collinear mapped front segments before cutting the unified bays.
    # Otherwise a source segment boundary subdivides one window frame twice.
    edges = [
        e
        for e in feature["facade_edges"]
        if not (abs(depth(e["a"])) < 0.2 and abs(depth(e["b"])) < 0.2 and e["b"][1] > e["a"][1])
    ]
    edges.append({"a": a, "b": b, "neighbor_height_m": 0})
    for edge in edges:
        p0, p1 = edge["a"], edge["b"]
        ex, ey = p1[0] - p0[0], p1[1] - p0[1]
        el = math.hypot(ex, ey)
        if el < 0.02:
            continue
        ux, uy = ex / el, ey / el
        vx, vy = uy, -ux
        ang = math.atan2(ey, ex)
        # Split exterior edges at the stepped roof plane.
        cuts = [0.0, el]
        d0, d1 = depth(p0), depth(p1)
        if (d0 - 62) * (d1 - 62) < 0:
            cuts.append(el * (62 - d0) / (d1 - d0))
        cuts.sort()

        def p(s, z, out=0):
            return (p0[0] + ux * s + vx * out, p0[1] + uy * s + vy * out, z)

        def rect(s0, s1, z0, z1, mat=None, out=0, mesh=walls):
            if mat is None:
                mat = stone if isfront or depth(p((s0 + s1) / 2, 0)) > 215 else brick
            if s1 - s0 > 1e-5 and z1 - z0 > 1e-5:
                mesh.face([p(s0, z0, out), p(s1, z0, out), p(s1, z1, out), p(s0, z1, out)], mat)

        isfront = abs(depth(p0)) < 0.2 and abs(depth(p1)) < 0.2 and vx > 0.9
        for lo, hi in zip(cuts, cuts[1:]):
            h = height(p((lo + hi) / 2, 0))
            adj = float(edge.get("neighbor_height_m", 0))
            # Shared wall is retained conservatively: current neighbouring heights unverified.
            openings = []
            if isfront:
                # All segments use one common facade rhythm, preventing duplicated corner bays.
                s0, s1 = station(p(lo, 0)), station(p(hi, 0))
                span = L / 13
                for k in range(13):
                    c = (k + 0.5) * span
                    l, r = lo + max(c - 1.63, s0) - s0, lo + min(c + 1.63, s1) - s0
                    if r - l < 0.01:
                        continue
                    ss = lo + c - s0
                    door = k == 6
                    openings.extend(
                        [
                            (l, r, 0.095 if door else 1.25, 5.4, door),
                            (l, r, 8.1, 12.2, False),
                            (l, r, 13.15, 20.1, False),
                        ]
                    )
                    # 2020 whole elevation: balustrade and blank parapet, no attic windows.
                    openings.append((l, r, 22.65, 23.8, False))
                    if door and s0 <= c < s1:
                        entries.append(
                            {
                                "threshold_xyz": p(ss, 0.095),
                                "outward_normal": [vx, vy, 0],
                                "clear_width_m": 3.26,
                                "door_leaf_depth_m": 0.52,
                                "support_z": 0.095,
                                "basis": "historical photo-informed position; threshold reconciled to inherited campus paving top .095 m, not surveyed",
                            }
                        )
            elif hi - lo > 3.0:
                count = max(1, int((hi - lo) / 4.5))
                spacing = (hi - lo) / count
                for k in range(count):
                    c = lo + (k + 0.5) * spacing
                    for z0, z1 in (
                        [(1.3, 4.4), (6.1, 9.5)]
                        if h < 20
                        else [(1.3, 4.7), (7.6, 11.6), (13.6, 18.6), (22.8, 24.4)]
                    ):
                        if z0 >= adj - 0.05:
                            openings.append((c - 0.85, c + 0.85, z0, z1, False))
            # Planar wall grid subtracts rectangles; depth is genuine, not a dark decal.
            xs = sorted(set([lo, hi] + [q for op in openings for q in op[:2]]))
            zs = sorted(set([0.0, h] + [q for op in openings for q in op[2:4]]))
            for x0, x1 in zip(xs, xs[1:]):
                for z0, z1 in zip(zs, zs[1:]):
                    xc, zc = (x0 + x1) / 2, (z0 + z1) / 2
                    if not any(l < xc < r and bot < zc < top for l, r, bot, top, _ in openings):
                        rect(x0, x1, z0, z1)
            for l, r, bot, top, door in openings:
                balustrade = isfront and bot == 22.65
                if balustrade:
                    # Actual open balustrade; masonry reveals remain but no glass infill.
                    for j in range(7):
                        x, y, z = p(l + (j + 0.5) * (r - l) / 7, bot, 0.02)
                        detail.lathe(
                            x,
                            y,
                            z,
                            [
                                (0.11, 0),
                                (0.11, 0.12),
                                (0.065, 0.23),
                                (0.12, 0.40),
                                (0.105, 0.62),
                                (0.06, 0.9),
                                (0.11, 1.03),
                                (0.11, 1.15),
                            ],
                            stone,
                            n=12,
                        )
                    continue
                dep = -0.52 if door else -0.34
                walls.face([p(l, bot), p(l, top), p(l, top, dep), p(l, bot, dep)], stone)
                walls.face([p(r, top), p(r, bot), p(r, bot, dep), p(r, top, dep)], stone)
                walls.face([p(l, top), p(r, top), p(r, top, dep), p(l, top, dep)], stone)
                walls.face([p(r, bot), p(l, bot), p(l, bot, dep), p(r, bot, dep)], stone)
                rect(l, r, bot, top, glass, dep, windows)
                for s in (
                    [l + 0.055, r - 0.055, l + (r - l) / 3, l + 2 * (r - l) / 3]
                    if isfront and not door
                    else [l + 0.055, r - 0.055, (l + r) / 2]
                ):
                    x, y, z = p(s, (bot + top) / 2, dep + 0.08)
                    windows.box(x, y, z, 0.085, 0.12, top - bot, bronze, ang)
                for z in [bot + 0.05, top - 0.05] + (
                    [bot + (top - bot) * f for f in [0.25, 0.5, 0.75]] if top - bot > 3 else []
                ):
                    x, y, _ = p((l + r) / 2, z, dep + 0.08)
                    windows.box(x, y, z, r - l, 0.12, 0.07, bronze, ang)
                if not door:
                    x, y, z = p((l + r) / 2, bot - 0.09, 0.10)
                    detail.box(x, y, z, r - l + 0.22, 0.38, 0.18, stone, ang)
                nopen += 1
            for z, wid, thick in [
                (6.6, 0.55, 0.5),
                (7.2, 0.68, 0.28),
                (21.4, 0.68, 0.35),
                (22.0, 0.8, 0.3),
                (25.9, 0.45, 0.25),
            ]:
                if z > h:
                    continue
                x, y, _ = p((lo + hi) / 2, z, 0.05)
                detail.box(x, y, z, hi - lo, wid, thick, stone, ang)
            # Horizontal masonry courses on the rusticated podium, interrupted by apertures.
            for z in [i * 0.48 for i in range(1, 14)]:
                if z > h:
                    continue
                intervals = [(lo, hi)]
                for l, r, bot, top, _ in openings:
                    if bot - 0.08 < z < top + 0.08:
                        intervals = [
                            v
                            for aa, bb in intervals
                            for v in [(aa, min(bb, l - 0.08)), (max(aa, r + 0.08), bb)]
                        ]
                        intervals = [(aa, bb) for aa, bb in intervals if bb - aa > 1e-4]
                for aa, bb in intervals:
                    rect(aa, bb, z - 0.012, z + 0.012, shadow, 0.004, detail)
    angle = math.atan2(ty, tx)

    def front(s, z, out=0.5):
        return (a[0] + s * tx + out * nx, a[1] + s * ty + out * ny, z)

    # Giant paired-storey order, inspired by the inspected central-column photograph.
    for k in range(1, 13):
        s = k * L / 13
        x, y, _ = front(s, 0, 0.64)
        detail.lathe(
            x,
            y,
            7.55,
            [
                (0.78, 0),
                (0.78, 0.18),
                (0.65, 0.25),
                (0.62, 0.42),
                (0.55, 0.65),
                (0.53, 12.6),
                (0.60, 12.75),
                (0.76, 12.85),
                (0.76, 13.05),
            ],
            stone,
            n=48,
        )
        for sign in [-1, 1]:
            cx, cy, z = front(s + sign * 0.53, 20.37, 0.67)
            # Volutes are explicit simplified architectural estimates, not carved scans.
            for j in range(28):
                q0 = j * math.tau * 1.7 / 28
                q1 = (j + 1) * math.tau * 1.7 / 28
                r0 = 0.24 * (1 - 0.75 * j / 28)
                r1 = 0.24 * (1 - 0.75 * (j + 1) / 28)
                detail.beam(
                    (
                        cx + tx * r0 * math.cos(q0),
                        cy + ty * r0 * math.cos(q0),
                        z + r0 * math.sin(q0),
                    ),
                    (
                        cx + tx * r1 * math.cos(q1),
                        cy + ty * r1 * math.cos(q1),
                        z + r1 * math.sin(q1),
                    ),
                    0.055,
                    stone,
                    n=10,
                )
    # Photo-visible cornice dentils, Ionic abaci and framed flat end pilasters.
    for k in range(1, 13):
        x, y, z = front(k * L / 13, 20.8, 0.65)
        detail.box(x, y, z, 1.65, 1.35, 0.25, stone, angle)
    for k in range(int(L / 0.37)):
        x, y, z = front((k + 0.5) * L / int(L / 0.37), 21.7, 0.52)
        detail.box(x, y, z, 0.19, 0.70, 0.32, stone, angle)
    for k in range(int(L / 0.92)):
        x, y, z = front((k + 0.5) * L / int(L / 0.92), 22.3, 0.60)
        detail.box(x, y, z, 0.30, 0.95, 0.35, stone, angle)
    for s in (0.8, L - 0.8):
        x, y, z = front(s, 14.3, 0.20)
        detail.box(x, y, z, 1.05, 0.45, 13.7, stone, angle)
        for ds in (-0.55, 0.55):
            x, y, z = front(s + ds, 14.3, 0.44)
            detail.box(x, y, z, 0.075, 0.09, 12.8, stone, angle)
    # Paired window tiers separated by dark ornamental spandrel mouldings.
    for k in range(13):
        s = (k + 0.5) * L / 13
        for z, w, h in [(12.37, 3.32, 0.12), (12.63, 3.45, 0.18), (12.87, 3.32, 0.08)]:
            x, y, _ = front(s, z, 0.03)
            detail.box(x, y, z, w, 0.18, h, bronze, angle)
        for j in range(7):
            x, y, z = front(s - 1.4 + j * 0.4667, 12.76, 0.13)
            detail.lathe(x, y, z, [(0.065, 0), (0.075, 0.08), (0.035, 0.17)], bronze, 8)
    # Estimated panel divisions on closed inset door; keep approach free until leaf.
    for ds in (-1.20, -0.4, 0.4, 1.20):
        for z in (0.75, 1.70, 2.65, 3.60, 4.55):
            x, y, _ = front(L / 2 + ds, z, -0.49)
            detail.box(x, y, z, 0.61, 0.035, 0.72, bronze, angle)
    # Entrance surround: no full stone band across the opening.
    c = L / 2
    for s in [c - 2.1, c + 2.1]:
        x, y, z = front(s, 2.85, 0.27)
        detail.box(x, y, z, 0.52, 0.7, 5.7, stone, angle)
    for z, width, thick in [(5.8, 4.75, 0.5), (6.18, 5.15, 0.22)]:
        x, y, _ = front(c, z, 0.38)
        detail.box(x, y, z, width, 0.9, thick, stone, angle)
    # Shallow fan-jointed flat lintel is visible in the 2004 entrance evidence.
    for ds in (-1.65, -1.1, -0.55, 0, 0.55, 1.1, 1.65):
        detail.beam(front(c + ds, 5.52, 0.841), front(c + ds * 1.26, 6.01, 0.841), 0.012, shadow, 6)
    # Replaced legacy coarse two-flat-zone roof; see evidence-constrained helper.
    roof_parameters = _roof_ranges(
        roof, detail, feature, station, depth, a, tx, ty, nx, ny, stone, roofmat, glass, patina
    )
    made = [m.done() for m in [walls, windows, detail, roof]]
    for ob in made:
        ob["geometry_fidelity"] = (
            "OSM footprint; historical east entrance evidence; estimated heights and other elevations"
        )
    return {
        "created": [o.name for o in made],
        "parameters": {
            "openings": nopen,
            "east_height_m": 26.0,
            "gallery_eaves_m": 26.0,
            "gallery_ridge_m": 31.0,
            "western_eaves_m": 33.0,
            "western_raised_roof_m": 37.0,
            "roof_ranges": roof_parameters,
            "height_basis": "EA 2022 composite DSM minus DTM 1m interpreted roof surfaces; not measured survey accuracy",
        },
        "interfaces": {"entrances": entries},
        "evidence_source_ids": feature["evidence_source_ids"],
        "uncertainty": [
            "2004 central entrance image; not verified 2026 appearance.",
            "13 window bays and 12 shafts independently counted from licensed 2020 whole elevation; dimensions and secondary elevations estimated.",
            "Roof extents estimated from historical PD aerials and EA 1m relative height evidence; small plant omitted; no current survey claim.",
            "Ionic volutes simplified; no sculpture replication.",
        ],
    }


def _roof_ranges(
    roof, detail, feature, station, depth, origin, tx, ty, nx, ny, stone, lead, glass, patina
):
    """Continuous roof surfaces clipped to original mapped triangles, EA+PD aerial informed.
    Flat setbacks, long barrel and tall west pavilion are observations; coordinates
    and simplified transitions are fitted estimates, without invented roof plant.
    """

    def uv(p):
        return station(p), depth(p)

    def xyz(u, v, z):
        return (origin[0] + u * tx - v * nx, origin[1] + u * ty - v * ny, z)

    def ramp(v, lo, hi):
        return max(0.0, min(1.0, (v - lo) / (hi - lo)))

    def rectangle(u, v, u0, u1, v0, v1, h):
        return h * max(
            0.0, min(1.0, (u - u0) / 2.0, (u1 - u) / 2.0, (v - v0) / 2.0, (v1 - v) / 2.0)
        )

    def barrel(u, v, u0, r, v0, v1, h):
        if abs(u - u0) >= r or not v0 < v < v1:
            return 0.0
        return (
            h
            * math.sqrt(max(0.0, 1 - ((u - u0) / r) ** 2))
            * min(1.0, (v - v0) / 2.0, (v1 - v) / 2.0)
        )

    def H(u, v):
        base = 26.0 + 7 * ramp(v, 215.0, 220.0)
        return base + max(
            barrel(u, v, 15.0, 11.0, 10.0, 53.0, 3.0),
            rectangle(u, v, 27.0, 53.0, 6.0, 54.0, 6.0),
            barrel(u, v, 15.0, 13.0, 137.0, 212.0, 5.0),
            rectangle(u, v, 8.0, 39.0, 221.0, 265.0, 4.0),
        )

    def mat(u, v):
        # Pale weathered green barrel is visible in 2011 air photo; not glass.
        return patina if 137 < v < 212 and 2 < u < 28 else lead

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
    for part in feature["geometry"]:
        for raw in part["triangles"]:
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
                            mat(sum(q[0] for q in (a, b, c)) / 3, sum(q[1] for q in (a, b, c)) / 3),
                        )
                        faces += 1
                        area += ar
        for ring in [part["outer"]] + part.get("holes", []):
            for a, b in zip(ring, ring[1:] + ring[:1]):
                u0, v0 = uv(a)
                u1, v1 = uv(b)
                cuts = {0.0, 1.0}
                for q0, q1 in ((u0, u1), (v0, v1)):
                    if abs(q1 - q0) > 1e-10:
                        for k in range(math.floor(min(q0, q1)) + 1, math.ceil(max(q0, q1))):
                            t = (k - q0) / (q1 - q0)
                            if 1e-8 < t < 1 - 1e-8:
                                cuts.add(t)
                cuts = sorted(cuts)
                for t0, t1 in zip(cuts, cuts[1:]):
                    q = (u0 + (u1 - u0) * t0, v0 + (v1 - v0) * t0)
                    r = (u0 + (u1 - u0) * t1, v0 + (v1 - v0) * t1)
                    points = [xyz(*q, 26.0), xyz(*r, 26.0), xyz(*r, H(*r)), xyz(*q, H(*q))]
                    clean = []
                    for x in points:
                        if not clean or math.dist(x, clean[-1]) > 1e-4:
                            clean.append(x)
                    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-4:
                        clean.pop()
                    if len(clean) > 2:
                        roof.face(clean, stone)
    # Subdivided seams describe the observed continuous barrel without adding plant.
    for v in range(140, 211, 3):
        for u in range(2, 28):
            detail.beam(
                xyz(u, v, H(u, v) + 0.04), xyz(u + 1, v, H(u + 1, v) + 0.04), 0.035, stone, 6
            )
    return {
        "projected_area_m2": area,
        "roof_faces": faces,
        "evidence": "EA DSM-DTM native1m + Andreas Praefcke PD2011 oblique aerials",
        "components": [
            "26m front parapet and lower roofs",
            "29m southern east-wing barrel",
            "32m northern east-wing raised roof",
            "31m long central barrel",
            "33m west pavilion and37m raised roof",
        ],
        "uncertainty": "roof subdivisions fitted to interpreted 1m raster and historical photos; no exact survey or mechanical equipment reconstruction",
    }
