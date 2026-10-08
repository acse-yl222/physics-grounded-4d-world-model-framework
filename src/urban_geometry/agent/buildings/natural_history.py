"""Mapped NHM exterior; inspected 2020 south photograph, estimated detail dimensions."""

import math

# All roof partitions are estimates fitted inside the unchanged mapped polygon.
ROOF_ORIGIN = (756.6008934095735, -480.7700479021296)
ROOF_AXIS = (31.1328305, 5.3438015)
GALLERY_BOUNDS = [
    -104.0,
    -75.0,
    -70.0,
    -54.0,
    -50.0,
    -34.0,
    -30.0,
    -16.0,
    16.0,
    20.0,
    36.0,
    40.0,
    56.0,
    60.0,
    74.0,
    88.0,
    104.0,
]
LOW_GALLERY_RANGES = [
    (-70.0, -54.0),
    (-50.0, -34.0),
    (-30.0, -16.0),
    (20.0, 36.0),
    (40.0, 56.0),
    (60.0, 74.0),
]
U_BOUNDS = sorted(
    set([-10000.0, 10000.0, -42.0, -28.0, -7.0, 0.0, 7.0, 30.0, 43.0, 154.0] + GALLERY_BOUNDS)
)
V_BOUNDS = [-10000.0, 25.0, 35.0, 48.0, 60.0, 62.0, 88.0, 96.0, 122.0, 10000.0]
TERMINAL_TOWERS = [(-95.0, 15.0, 13.5), (97.0, 15.0, 13.5)]


def roof_frame():
    scale = math.hypot(*ROOF_AXIS)
    return ROOF_AXIS[0] / scale, ROOF_AXIS[1] / scale


def roof_zone(u, v):
    # Height tiers are constrained by EA 2022 DSM-DTM sampled in this frame.
    # Layout uses mapped polygon + inspected 2011 photographs; low service
    # strips are conservative roof envelopes, not claimed exact courtyard plans.
    if u < -104:
        return ("flat", 0.0, 1.0, 22.0, 0.0)
    if v >= 88:
        if u < -75:
            return ("gallery", -104.0, -75.0, 29.0, 4.0)
        if -42 <= u < -28 or 30 <= u < 43:
            return ("flat", 0.0, 1.0, 32.5, 0.0)
        if u >= 104:
            return ("north", 62.0, 96.0, 26.0, 3.0)
        return ("flat", 0.0, 1.0, 12.0, 0.0)
    if u >= 104:
        if 48 <= v < 62 and u < 154:
            return ("flat", 0.0, 1.0, 6.0, 0.0)
        if v >= 62:
            return ("north", 62.0, 96.0, 26.0, 3.0)
        return ("flat", 0.0, 1.0, 21.0, 0.0)
    if v < 25:
        if -16 <= u < 16:
            return ("central_front", -7.0, 7.0, 22.0, 7.0)
        return ("front", 6.0, 25.0, 23.0, 4.0)
    if u < -75:
        return ("gallery", -104.0, -75.0, 28.0, 4.0)
    if u >= 88:
        return ("gallery", 88.0, 104.0, 23.0, 4.0)
    if -16 <= u < 16:
        return (
            ("gallery", -16.0, 16.0, 23.0, 5.5) if v < 60 else ("gallery", -16.0, 16.0, 16.0, 6.0)
        )
    if v < 35:
        return ("flat", 0.0, 1.0, 9.0, 0.0)
    for a, b in LOW_GALLERY_RANGES:
        if a <= u < b:
            return ("gallery", a, b, 10.8, 5.8)
    return ("flat", 0.0, 1.0, 10.8, 0.0)


def roof_level(zone, u, v):
    kind, a, b, eave, rise = zone
    if kind == "flat":
        return eave
    c = 16.0 if kind == "front" else (a + b) / 2
    q = v if kind in ("front", "north") else u
    t = (q - a) / (c - a) if q <= c else (b - q) / (b - c)
    return eave + rise * max(0.0, t)


def roof_clip(poly, axis, limit, positive):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da = (a[axis] - limit) * (1 if positive else -1)
        db = (b[axis] - limit) * (1 if positive else -1)
        if da >= -1e-9:
            out.append(a)
        if da * db < 0 and abs(da) > 1e-9 and abs(db) > 1e-9:
            t = da / (da - db)
            out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(2)))
    clean = []
    for p in out:
        if not clean or math.dist(p, clean[-1]) > 1e-8:
            clean.append(p)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-8:
        clean.pop()
    return clean


def build_roofs(ctx, feature, z, slate, glass, stone, blue):
    roof = ctx.mesh("Partitioned pitched galleries central hall and glazed ridges")
    ux, uy = roof_frame()
    ox, oy = ROOF_ORIGIN

    def uv(p):
        return ((p[0] - ox) * ux + (p[1] - oy) * uy, -(p[0] - ox) * uy + (p[1] - oy) * ux)

    def xyz(p, h):
        return (ox + ux * p[0] - uy * p[1], oy + uy * p[0] + ux * p[1], z + h)

    triangles = [list(map(uv, t)) for part in feature["geometry"] for t in part["triangles"]]
    original_area = sum(
        abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0]))
        / 2
        for t in triangles
    )
    # Exclude four tower footprints so sloping galleries cannot cross their windows.
    a = (740.492256, -483.52966)
    b = (771.6250865, -478.1858585)
    length = math.dist(a, b)
    central = [
        uv((a[0] + ux * t - uy * 4.5, a[1] + uy * t + ux * 4.5)) for t in (4.4, length - 4.4)
    ]
    exclusions = [(u - 4, u + 4, v - 4, v + 4) for u, v in central] + [
        (u - w / 2, u + w / 2, v - w / 2, v + w / 2) for u, v, w in TERMINAL_TOWERS
    ]
    for ua, ub, va, vb in exclusions:
        remainder = []
        for polygon in triangles:
            inside = polygon
            for axis, limit, positive in [
                (0, ua, True),
                (0, ub, False),
                (1, va, True),
                (1, vb, False),
            ]:
                if not inside:
                    break
                outside = roof_clip(inside, axis, limit, not positive)
                if len(outside) >= 3:
                    remainder.append(outside)
                inside = roof_clip(inside, axis, limit, positive)
        triangles = [
            [p[0], p[i], p[i + 1]]
            for p in remainder
            for i in range(1, len(p) - 1)
            if abs(
                (p[i][0] - p[0][0]) * (p[i + 1][1] - p[0][1])
                - (p[i][1] - p[0][1]) * (p[i + 1][0] - p[0][0])
            )
            > 1e-8
        ]
    us = set(U_BOUNDS)
    vs = set(V_BOUNDS + [6.0, 16.0, 25.0, 79.0])
    for a, b in zip(GALLERY_BOUNDS, GALLERY_BOUNDS[1:]):
        if -104 <= a and b <= 104:
            c = (a + b) / 2
            us.update([c - 1.5, c, c + 1.5])
    us = sorted(us)
    vs = sorted(vs)
    area = 0.0
    facets = 0

    def face(poly, material):
        nonlocal facets
        for i in range(1, len(poly) - 1):
            a, b, c = poly[0], poly[i], poly[i + 1]
            ab = [b[k] - a[k] for k in range(3)]
            ac = [c[k] - a[k] for k in range(3)]
            cross = [
                ab[(k + 1) % 3] * ac[(k + 2) % 3] - ab[(k + 2) % 3] * ac[(k + 1) % 3]
                for k in range(3)
            ]
            if sum(v * v for v in cross) > 1e-14:
                roof.face([a, b, c], material)
                facets += 1

    for ua, ub in zip(us, us[1:]):
        for va, vb in zip(vs, vs[1:]):
            um, vm = (ua + ub) / 2, (va + vb) / 2
            zone = roof_zone(um, vm)
            glazed = zone[0] == "gallery" and abs(um - (zone[1] + zone[2]) / 2) < 1.500001
            for tri in triangles:
                poly = tri
                for axis, limit, positive in [
                    (0, ua, True),
                    (0, ub, False),
                    (1, va, True),
                    (1, vb, False),
                ]:
                    if poly:
                        poly = roof_clip(poly, axis, limit, positive)
                if len(poly) < 3:
                    continue
                pa = (
                    abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])))
                    / 2
                )
                if pa < 1e-8:
                    continue
                area += pa
                face([xyz(p, roof_level(zone, *p)) for p in poly], glass if glazed else slate)
    # Original outer and hole boundaries, split at every height-plane break.
    for part in feature["geometry"]:
        for raw in [part["outer"]] + part.get("holes", []):
            ring = list(map(uv, raw))
            for a, b in zip(ring, ring[1:] + ring[:1]):
                cuts = [0.0, 1.0]
                for axis, breaks in [(0, us), (1, vs)]:
                    if abs(b[axis] - a[axis]) > 1e-10:
                        cuts.extend(
                            (q - a[axis]) / (b[axis] - a[axis])
                            for q in breaks
                            if 0 < (q - a[axis]) / (b[axis] - a[axis]) < 1
                        )
                cuts = sorted(set(round(t, 12) for t in cuts))

                def at(t):
                    return tuple(a[k] + t * (b[k] - a[k]) for k in range(2))

                for lo, hi in zip(cuts, cuts[1:]):
                    p, q = at(lo), at(hi)
                    mid = at((lo + hi) / 2)
                    zone = roof_zone(*mid)
                    # Central gable is authored with its own true window aperture.
                    if zone[0] == "central_front" and abs(mid[0]) < 7.001 and mid[1] < 1.0:
                        continue
                    face(
                        [
                            xyz(p, min(22.0, zone[3])),
                            xyz(q, min(22.0, zone[3])),
                            xyz(q, roof_level(zone, *q)),
                            xyz(p, roof_level(zone, *p)),
                        ],
                        stone,
                    )

    # Intersect a partition line with the existing triangles and union intervals.
    # This preserves holes and non-convex footprints without a hull or flat lid.
    def intervals(axis, value):
        segments = []
        for tri in triangles:
            pts = []
            for a, b in zip(tri, tri[1:] + tri[:1]):
                if abs(a[axis] - value) < 1e-8:
                    pts.append(a[1 - axis])
                if (a[axis] - value) * (b[axis] - value) < 0:
                    t = (value - a[axis]) / (b[axis] - a[axis])
                    pts.append(a[1 - axis] + t * (b[1 - axis] - a[1 - axis]))
            if len(pts) > 1 and max(pts) - min(pts) > 1e-7:
                segments.append((min(pts), max(pts)))
        result = []
        for a, b in sorted(segments):
            if result and a <= result[-1][1] + 1e-7:
                result[-1] = (result[-1][0], max(b, result[-1][1]))
            else:
                result.append((a, b))
        return result

    for axis, lines, breaks in [(0, U_BOUNDS[1:-1], vs), (1, V_BOUNDS[1:-1], us)]:
        for value in lines:
            for start, end in intervals(axis, value):
                cuts = sorted(set([start, end] + [q for q in breaks if start < q < end]))
                for a, b in zip(cuts, cuts[1:]):
                    mid = [0.0, 0.0]
                    mid[axis] = value
                    mid[1 - axis] = (a + b) / 2
                    left = mid[:]
                    right = mid[:]
                    left[axis] -= 0.0001
                    right[axis] += 0.0001
                    zl, zr = roof_zone(*left), roof_zone(*right)
                    p = mid[:]
                    q = mid[:]
                    p[1 - axis] = a
                    q[1 - axis] = b
                    hl = [roof_level(zl, *v) for v in (p, q)]
                    hr = [roof_level(zr, *v) for v in (p, q)]
                    if max(abs(hl[i] - hr[i]) for i in range(2)) < 1e-7:
                        continue
                    face([xyz(p, hl[0]), xyz(q, hl[1]), xyz(q, hr[1]), xyz(p, hr[0])], stone)
    # Finite skylight framing, split at each height tier to avoid floating rods.
    for a, b in zip(GALLERY_BOUNDS, GALLERY_BOUNDS[1:]):
        c = (a + b) / 2
        for u in [c - 1.5, c, c + 1.5]:
            for v0, v1 in intervals(0, u):
                cuts = sorted(
                    set(
                        [max(v0, 25), min(v1, 88)]
                        + [v for v in V_BOUNDS if max(v0, 25) < v < min(v1, 88)]
                    )
                )
                for va, vb in zip(cuts, cuts[1:]):
                    if vb <= va:
                        continue
                    zone = roof_zone(u, (va + vb) / 2)
                    if zone[0] != "gallery":
                        continue
                    roof.beam(
                        xyz((u, va), roof_level(zone, u, va) + 0.045),
                        xyz((u, vb), roof_level(zone, u, vb) + 0.045),
                        0.055,
                        blue,
                        8,
                    )
                    if abs(u - c) > 1e-8:
                        continue
                    for v in [va + i * 3.6 for i in range(1, int((vb - va) / 3.6) + 1)]:
                        for aa, bb in [(c - 1.5, c), (c, c + 1.5)]:
                            roof.beam(
                                xyz((aa, v), roof_level(zone, aa, v) + 0.045),
                                xyz((bb, v), roof_level(zone, bb, v) + 0.045),
                                0.045,
                                blue,
                                8,
                            )
    obj = roof.done()
    expected = sum(
        abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0]))
        / 2
        for t in triangles
    )
    assert abs(area - expected) < 1e-5, ("Roof plan area mismatch", area, expected)
    return obj, {
        "roof_projected_area_m2": area,
        "original_footprint_area_m2": original_area,
        "tower_roof_exclusions_uv": exclusions,
        "footprint_triangle_area_m2": expected,
        "roof_surface_facets": facets,
        "roof_configuration": "east-west south and north ranges, six low north-south gallery roofs with intervening service strips, high west/east perimeter and tiered central hall, eastern later flat extension; all partitions visually estimated",
        "central_hall_eaves_m": 23,
        "central_hall_ridge_m": 28.5,
        "north_hall_eaves_m": 16,
        "north_hall_ridge_m": 22,
        "gallery_eaves_m": 10.8,
        "gallery_rise_m": 5.8,
        "low_gallery_ridges_u_m": [-62, -42, -23, 28, 48, 67],
        "west_perimeter_eaves_m": 28,
        "west_perimeter_ridge_m": 32,
        "rear_low_roof_m": 12,
        "rear_high_ranges_m": 32.5,
        "height_basis": "EA2022 DSM-DTM sampled regional tiers; photos constrain roof typology; not surveyed eaves",
        "roof_glazing_band_width_m": 3,
        "aerial_source_date": "2011-06-10",
    }


def build(ctx, feature):
    p = feature.get("detail_parameters", {})
    parts = feature["geometry"]
    h = float(p.get("height_m", 22))
    z = float(p.get("base_z_m", feature.get("base_m", 0)))
    stone = ctx.material("NHM buff terracotta", (0.72, 0.57, 0.39), 0.85)
    blue = ctx.material("NHM blue terracotta", (0.38, 0.42, 0.43), 0.8)
    slate = ctx.material("NHM slate", (0.18, 0.22, 0.25), 0.85)
    glass = ctx.material("NHM dark glazing", (0.10, 0.17, 0.21), 0.3)
    mesh = ctx.mesh("Mapped masonry with recessed Romanesque apertures")
    mesh.surface(parts, z, stone)
    apertures = 0
    entrances = []
    dormer_apertures = 0
    timber = ctx.material("NHM entrance dark timber", (0.07, 0.045, 0.026), 0.7)
    metal = ctx.material("NHM iron frame", (0.08, 0.085, 0.075), 0.5, 0.55)

    def wall(a, b, z0, z1, rows, width=1.7, spacing=4.7):
        nonlocal apertures, dormer_apertures
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 0.001:
            return
        ux, uy = dx / length, dy / length
        nx, ny = uy, -ux
        if z0 == 0:
            ru, rv = roof_frame()
            xx = (a[0] + b[0]) / 2 - ROOF_ORIGIN[0]
            yy = (a[1] + b[1]) / 2 - ROOF_ORIGIN[1]
            region = roof_zone(xx * ru + yy * rv, -xx * rv + yy * ru)
            z1 = min(z1, region[3])

        def pt(t, v, d=0):
            return (a[0] + ux * t + nx * d, a[1] + uy * t + ny * d, z + v)

        def quad(t0, t1, v0, v1, d=0, mat=stone):
            if t1 <= t0 or v1 <= v0:
                return
            if mat != stone:
                mesh.face([pt(t0, v0, d), pt(t1, v0, d), pt(t1, v1, d), pt(t0, v1, d)], mat)
                return
            # Physical alternating terracotta courses, clipped to each solid panel.
            cuts = sorted(
                set(
                    [v0, v1]
                    + [
                        q
                        for k in range(int(v0 / 0.7) - 1, int(v1 / 0.7) + 2)
                        for q in (k * 0.7, k * 0.7 + 0.15)
                        if v0 < q < v1
                    ]
                )
            )
            for low, high in zip(cuts, cuts[1:]):
                material = blue if ((low + high) / 2) % 0.7 < 0.15 else stone
                mesh.face(
                    [pt(t0, low, d), pt(t1, low, d), pt(t1, high, d), pt(t0, high, d)], material
                )

        if length < 3 or not rows:
            quad(0, length, z0, z1)
            return
        n = max(1, int(length / spacing))
        cell = length / n
        w = min(
            3.0 if ny < -0.9 and width == 1.7 else width,
            cell * (0.84 if width >= 7 else (0.72 if ny < -0.9 and width == 1.7 else 0.55)),
        )
        r = w / 2
        for k in range(n):
            lo = k * cell
            hi = (k + 1) * cell
            c = (lo + hi) / 2
            cursor = z0
            for bottom, spring in rows:
                top = spring + r
                if bottom < cursor or top >= z1:
                    continue
                quad(lo, hi, cursor, bottom)
                quad(lo, c - r, bottom, top)
                quad(c + r, hi, bottom, top)
                arc = [
                    (c + r * math.cos(j * math.pi / 32), spring + r * math.sin(j * math.pi / 32))
                    for j in range(33)
                ]
                for (t0, v0), (t1, v1) in zip(arc, arc[1:]):
                    # At the arch crown one upper corner coincides with the
                    # arc endpoint. Keep the full nonzero spandrel as a triangle
                    # instead of a quad with a repeated vertex (which exports a
                    # zero-area triangle). No coordinates or surfaces move.
                    polygon = []
                    for corner in [pt(t0, v0), pt(t1, v1), pt(t1, top), pt(t0, top)]:
                        if not polygon or math.dist(corner, polygon[-1]) > 1e-10:
                            polygon.append(corner)
                    if len(polygon) > 1 and math.dist(polygon[0], polygon[-1]) <= 1e-10:
                        polygon.pop()
                    mesh.face(polygon, stone)
                dep = 1.20 if bottom == 0 and width >= 7 else 0.42
                contour = [(c - r, bottom), (c + r, bottom)] + arc
                for q0, q1 in zip(contour, contour[1:] + contour[:1]):
                    mesh.face([pt(*q0), pt(*q1), pt(*q1, -dep), pt(*q0, -dep)], stone)
                # The glazing is behind the actual wall void, without a hidden solid facade.
                mesh.face([pt(t, v, -dep) for t, v in contour], glass)
                mesh.beam(pt(c, bottom, -dep + 0.08), pt(c, spring, -dep + 0.08), 0.055, blue, n=6)
                for (t0, v0), (t1, v1) in zip(arc, arc[1:]):
                    mesh.beam(pt(t0, v0, 0.08), pt(t1, v1, 0.08), 0.13, blue, n=6)
                # Slender attached columns and capitals lie outside the void.
                for side in (-1, 1):
                    xx, yy, _ = pt(c + side * (r + 0.19), bottom, 0.07)
                    hh = spring - bottom
                    mesh.lathe(
                        xx,
                        yy,
                        z + bottom,
                        [
                            (0.13, 0),
                            (0.13, 0.15),
                            (0.075, 0.25),
                            (0.075, max(0.26, hh - 0.2)),
                            (0.15, hh - 0.12),
                            (0.15, hh),
                        ],
                        stone,
                        n=16,
                    )
                for i in range(24):
                    t0 = i * math.pi / 24 + 0.008
                    t1 = (i + 1) * math.pi / 24 - 0.008
                    mesh.face(
                        [
                            pt(c + rr * math.cos(tt), spring + rr * math.sin(tt), 0.12)
                            for rr, tt in [
                                (r + 0.15, t0),
                                (r + 0.34, t0),
                                (r + 0.34, t1),
                                (r + 0.15, t1),
                            ]
                        ],
                        blue if i % 3 == 0 else stone,
                    )
                mesh.beam(
                    pt(c - r, bottom - 0.07, 0.1), pt(c + r, bottom - 0.07, 0.1), 0.10, stone, 10
                )
                mesh.beam(
                    pt(c - r, (bottom + spring) / 2, -dep + 0.08),
                    pt(c + r, (bottom + spring) / 2, -dep + 0.08),
                    0.038,
                    blue,
                    8,
                )
                if ny < -0.9 and w >= 2.4 and bottom > 0:
                    # Paired lights and roundel tracery observed in Herzog detail 03.
                    subr = r * 0.46
                    subspring = spring - r * 0.35
                    for side in (-1, 1):
                        cc = c + side * r * 0.5
                        points = [
                            pt(
                                cc + subr * math.cos(i * math.pi / 24),
                                subspring + subr * math.sin(i * math.pi / 24),
                                -0.24,
                            )
                            for i in range(25)
                        ]
                        for aa, bb in zip(points, points[1:]):
                            mesh.beam(aa, bb, 0.065, stone, 10)
                    mesh.beam(pt(c, bottom, -0.22), pt(c, subspring, -0.22), 0.085, stone, 12)
                    if bottom > 10:
                        points = [
                            pt(
                                c + r * 0.23 * math.cos(i * math.tau / 48),
                                spring + r * 0.5 + r * 0.23 * math.sin(i * math.tau / 48),
                                -0.22,
                            )
                            for i in range(48)
                        ]
                        for aa, bb in zip(points, points[1:] + points[:1]):
                            mesh.beam(aa, bb, 0.075, stone, 10)
                if bottom == 0 and width >= 7:
                    # Recessed masonry tympanum and five real arched lights,
                    # observed in the2020 portal closeup; retain door openings below.
                    back = -0.73

                    def fill(poly, mat=stone):
                        mesh.face([pt(t, v, back) for t, v in poly], mat)

                    fill([(c - r, 0), (c - 1.69, 0), (c - 1.69, 3.15), (c - r, 3.15)])
                    fill([(c + 1.69, 0), (c + r, 0), (c + r, 3.15), (c + 1.69, 3.15)])
                    fill([(c - r, 3.15), (c + r, 3.15), (c + r, 5.65), (c - r, 5.65)])

                    def crown(t):
                        return spring + math.sqrt(max(0.0, r * r - (t - c) ** 2))

                    for j in range(5):
                        cell_lo = c - r + 2 * r * j / 5
                        cell_hi = c - r + 2 * r * (j + 1) / 5
                        cc = (cell_lo + cell_hi) / 2
                        rr = 0.48
                        ss = 7.25 + 0.70 * (1 - abs(j - 2) / 2)
                        bt = 5.65
                        wl, wr = cc - rr, cc + rr
                        wa = [
                            (
                                cc + rr * math.cos(k * math.pi / 24),
                                ss + rr * math.sin(k * math.pi / 24),
                            )
                            for k in range(25)
                        ]
                        for aa, bb in ((cell_lo, wl), (wr, cell_hi)):
                            crown_points = [
                                (aa + (bb - aa) * k / 8, crown(aa + (bb - aa) * k / 8))
                                for k in range(9)
                            ]
                            fill([(aa, bt), (bb, bt)] + list(reversed(crown_points)))
                        upper = [
                            (wl + (wr - wl) * k / 16, crown(wl + (wr - wl) * k / 16))
                            for k in range(17)
                        ]
                        fill(wa + upper)
                        loop = [(wl, bt), (wr, bt)] + wa
                        mesh.face([pt(t, v, back - 0.18) for t, v in loop], glass)
                        for a0, b0 in zip(loop, loop[1:] + loop[:1]):
                            mesh.face(
                                [
                                    pt(*a0, back),
                                    pt(*b0, back),
                                    pt(*b0, back - 0.18),
                                    pt(*a0, back - 0.18),
                                ],
                                stone,
                            )
                        for a0, b0 in zip(wa, wa[1:]):
                            mesh.beam(pt(*a0, back + 0.04), pt(*b0, back + 0.04), 0.09, stone, 8)
                        for xx in (wl - 0.12, wr + 0.12):
                            mesh.beam(
                                pt(xx, bt, back + 0.03), pt(xx, ss, back + 0.03), 0.085, stone, 8
                            )
                    mesh.beam(
                        pt(c - r, 5.50, back + 0.08), pt(c + r, 5.50, back + 0.08), 0.15, stone, 10
                    )
                    # The portal throat is observed; paired leaves are labelled
                    # inferred because the photograph partly occludes the entrance.
                    for side in (-1, 1):
                        centre = c + side * 0.82
                        mesh.box(
                            *pt(centre, 1.55, -0.95), 1.55, 0.08, 2.9, timber, math.atan2(dy, dx)
                        )
                        for zz in (0.9, 2.05):
                            mesh.box(
                                *pt(centre, zz, -0.895),
                                1.20,
                                0.035,
                                0.85,
                                timber,
                                math.atan2(dy, dx),
                            )
                        mesh.beam(
                            pt(centre - side * 0.52, 1.25, -0.86),
                            pt(centre - side * 0.52, 1.55, -0.86),
                            0.025,
                            metal,
                            10,
                        )
                        entrances.append(
                            {
                                "threshold_xyz": list(pt(centre, 0.10)),
                                "outward_normal": [nx, ny, 0],
                                "door_leaf_xyz": list(pt(centre, 1.5, -0.95)),
                                "door_leaf_depth_m": 0.91,
                                "clear_width_m": 1.42,
                                "stair_treads": 1,
                                "riser_m": 0.10,
                                "tread_m": 0.65,
                                "landing_depth_m": 1.85,
                                "landing_z_m": z + 0.10,
                                "ramp": "unverified",
                                "supporting_surface": "finite estimated sill step; coordinator ground interface pending",
                                "estimated": True,
                            }
                        )
                    for cc in (c - 1.64, c, c + 1.64):
                        mesh.box(*pt(cc, 1.55, -0.82), 0.09, 0.15, 2.9, stone, math.atan2(dy, dx))
                    mesh.box(*pt(c, 0.05, -0.275), 3.5, 1.85, 0.10, stone, math.atan2(dy, dx))
                    for side in (-1, 1):
                        for offset in (0.20, 0.45, 0.72, 1.02):
                            xx, yy, _ = pt(c + side * (r + offset), 0, 0.15 + offset * 0.08)
                            mesh.lathe(
                                xx,
                                yy,
                                z,
                                [
                                    (0.19, 0),
                                    (0.19, 0.25),
                                    (0.13, 0.42),
                                    (0.13, spring - 0.35),
                                    (0.22, spring - 0.20),
                                    (0.22, spring),
                                ],
                                stone,
                                n=12,
                            )
                    for radial in (0.18, 0.40, 0.64, 0.89, 1.15):
                        ring = [
                            pt(
                                c + (r + radial) * math.cos(i * math.pi / 48),
                                spring + (r + radial) * math.sin(i * math.pi / 48),
                                0.15 + radial * 0.08,
                            )
                            for i in range(49)
                        ]
                        for aa, bb in zip(ring, ring[1:]):
                            mesh.beam(aa, bb, 0.075, stone, 10)
                cursor = top
                apertures += 1
            quad(lo, hi, cursor, z1)
        angle = math.atan2(dy, dx)
        for level in [5.7, 12, h - 0.5]:
            if z0 < level < z1 and not any(bottom < level < spring + r for bottom, spring in rows):
                mesh.box(
                    (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z + level, length, 0.32, 0.3, blue, angle
                )
        for level in [5.7, 12, h - 0.5]:
            if z0 < level < z1 and not any(bottom < level < spring + r for bottom, spring in rows):
                mesh.box(*pt(length / 2, level + 0.22, 0.09), length, 0.48, 0.13, stone, angle)
                for i in range(int(length / 0.65)):
                    mesh.box(
                        *pt((i + 0.5) * length / max(1, int(length / 0.65)), level - 0.3, 0.08),
                        0.15,
                        0.32,
                        0.22,
                        stone,
                        angle,
                    )
        if z0 == 0 and ny < -0.9 and length > 30:
            for k in range(n):
                c = (k + 0.5) * cell
                xx, yy, _ = pt(c, 0)
                ru, rv = roof_frame()
                uu = (xx - ROOF_ORIGIN[0]) * ru + (yy - ROOF_ORIGIN[1]) * rv
                if not 18 < abs(uu) < 86:
                    continue
                # Small paired-window roof gables visible in aerial and detail 03.
                left, right = c - 1.4, c + 1.4
                bottom, top = h, h + 3.0
                apex = h + 5.0

                def pp(t, v, d=0):
                    return pt(t, v, 0.45 - d)

                holes = [(c - 0.97, c - 0.22), (c + 0.22, c + 0.97)]
                cursor = left
                for aa, bb in holes + [(right, right)]:
                    if aa > cursor:
                        mesh.face(
                            [pp(cursor, bottom), pp(aa, bottom), pp(aa, top), pp(cursor, top)],
                            stone,
                        )
                    cursor = bb
                for aa, bb in holes:
                    low, high = h + 0.15, h + 2.7
                    cc = (aa + bb) / 2
                    rr = (bb - aa) / 2
                    spring2 = high - rr
                    mesh.face([pp(aa, bottom), pp(bb, bottom), pp(bb, low), pp(aa, low)], stone)
                    mesh.face([pp(aa, high), pp(bb, high), pp(bb, top), pp(aa, top)], stone)
                    arc = [
                        (
                            cc + rr * math.cos(i * math.pi / 24),
                            spring2 + rr * math.sin(i * math.pi / 24),
                        )
                        for i in range(25)
                    ]
                    contour = [(aa, low), (bb, low)] + arc
                    for a0, b0 in zip(arc, arc[1:]):
                        poly = [pp(*a0), pp(a0[0], high), pp(b0[0], high), pp(*b0)]
                        mesh.face(poly, stone)
                        mesh.beam(pp(*a0, -0.06), pp(*b0, -0.06), 0.065, blue, 10)
                    mesh.face([pp(t, v, 0.22) for t, v in contour], glass)
                    for a0, b0 in zip(contour, contour[1:] + contour[:1]):
                        mesh.face([pp(*a0), pp(*b0), pp(*b0, 0.22), pp(*a0, 0.22)], stone)
                    mesh.beam(pp(cc, low, 0.12), pp(cc, spring2, 0.12), 0.028, blue, 8)
                    dormer_apertures += 1
                mesh.face([pp(left, top), pp(right, top), pp(c, apex)], stone)
                mesh.face(
                    [
                        pp(left, bottom, 2.5),
                        pp(right, bottom, 2.5),
                        pp(right, top, 2.5),
                        pp(c, apex, 2.5),
                        pp(left, top, 2.5),
                    ],
                    stone,
                )
                for end in (left, right):
                    mesh.face(
                        [pp(end, bottom), pp(end, top), pp(end, top, 2.5), pp(end, bottom, 2.5)],
                        stone,
                    )
                    mesh.face(
                        [pp(end, top), pp(c, apex), pp(c, apex, 2.5), pp(end, top, 2.5)], slate
                    )
                    mesh.beam(pp(end, top, -0.10), pp(c, apex, -0.10), 0.1, blue, 10)
                circle = [
                    pp(
                        c + 0.33 * math.cos(i * math.tau / 32),
                        top + 0.65 + 0.33 * math.sin(i * math.tau / 32),
                        -0.05,
                    )
                    for i in range(32)
                ]
                for aa, bb in zip(circle, circle[1:] + circle[:1]):
                    mesh.beam(aa, bb, 0.065, blue, 10)

    def perimeter_wall(a, b, rows):
        # Split only where roof eave class changes along the mapped edge. This
        # avoids an unclosed strip when a low rear facade meets a high roof range.
        ru, rv = roof_frame()

        def uv(p):
            return (
                (p[0] - ROOF_ORIGIN[0]) * ru + (p[1] - ROOF_ORIGIN[1]) * rv,
                -(p[0] - ROOF_ORIGIN[0]) * rv + (p[1] - ROOF_ORIGIN[1]) * ru,
            )

        p, q = uv(a), uv(b)
        cuts = [0.0, 1.0]
        for axis, lines in [(0, U_BOUNDS), (1, V_BOUNDS)]:
            if abs(q[axis] - p[axis]) > 1e-9:
                cuts.extend(
                    (v - p[axis]) / (q[axis] - p[axis])
                    for v in lines
                    if 0 < (v - p[axis]) / (q[axis] - p[axis]) < 1
                )
        cuts = sorted(set(round(t, 12) for t in cuts))
        groups = []
        for lo, hi in zip(cuts, cuts[1:]):
            t = (lo + hi) / 2
            zz = min(h, roof_zone(p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))[3])
            if groups and abs(groups[-1][2] - zz) < 1e-8:
                groups[-1] = (groups[-1][0], hi, zz)
            else:
                groups.append((lo, hi, zz))

        def at(t):
            return tuple(a[k] + t * (b[k] - a[k]) for k in range(2))

        for lo, hi, zz in groups:
            wall(at(lo), at(hi), 0, zz, rows)

    for part in parts:
        for ri, ring0 in enumerate([part["outer"]] + part.get("holes", [])):
            # Merge the two near-collinear central entrance frontage edges (under 1 cm offset).
            ring = [
                v for v in ring0 if math.dist(v, (756.6008934095735, -480.7700479021296)) > 0.001
            ]
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
            if (area > 0) != (ri == 0):
                ring.reverse()
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if (
                    math.dist(a, (740.492256, -483.52966)) < 0.1
                    and math.dist(b, (771.6250865, -478.1858585)) < 0.1
                ):
                    ll = math.dist(a, b)
                    u = ((b[0] - a[0]) / ll, (b[1] - a[1]) / ll)
                    aa = (a[0] + u[0] * 8.8, a[1] + u[1] * 8.8)
                    bb = (b[0] - u[0] * 8.8, b[1] - u[1] * 8.8)
                    wall(a, aa, 0, h, [(1.75, 4.45), (7.65, 10.35), (13.65, 16.35)])
                    wall(aa, bb, 0, 13, [(0, 6.5)], width=10, spacing=20)
                    wall(aa, bb, 13, h, [(14.2, 18.3)], width=1.75, spacing=2.3)
                    wall(bb, b, 0, h, [(1.75, 4.45), (7.65, 10.35), (13.65, 16.35)])
                else:
                    perimeter_wall(a, b, [(1.75, 4.45), (7.65, 10.35), (13.65, 16.35)])

    def spire(x, y, width, eave, height, angle):
        ux, uy = math.cos(angle), math.sin(angle)
        vx, vy = -uy, ux
        profile = [
            (width * 0.55, 0),
            (width * 0.51, 0.07 * height),
            (width * 0.37, 0.36 * height),
            (width * 0.40, 0.38 * height),
            (width * 0.26, 0.65 * height),
            (width * 0.29, 0.67 * height),
            (0.12, height),
        ]
        rings = []
        for r, zz in profile:
            rings.append(
                [
                    (
                        x + ux * math.cos(t) * r + vx * math.sin(t) * r,
                        y + uy * math.cos(t) * r + vy * math.sin(t) * r,
                        z + eave + zz,
                    )
                    for t in [math.pi / 8 + i * math.tau / 8 for i in range(8)]
                ]
            )
        for k, (a, b) in enumerate(zip(rings, rings[1:])):
            for i in range(8):
                mesh.face(
                    [a[i], a[(i + 1) % 8], b[(i + 1) % 8], b[i]], blue if k in (2, 4) else slate
                )
        mesh.face(list(reversed(rings[0])), blue)
        mesh.face(rings[-1], blue)
        mesh.beam((x, y, z + eave + height), (x, y, z + eave + height + 1.6), 0.045, metal, 12)

    # Actual mapped front central segment; all tower widths/heights remain estimated.
    a = (740.492256, -483.52966)
    b = (771.6250865, -478.1858585)
    length = math.dist(a, b)
    ux = (b[0] - a[0]) / length
    uy = (b[1] - a[1]) / length
    inward = (-uy, ux)
    angle = math.atan2(uy, ux)
    positions = []
    for t in [4.4, length - 4.4]:
        x = a[0] + ux * t + inward[0] * 4.5
        y = a[1] + uy * t + inward[1] * 4.5
        positions.append([x, y])
        corners = [
            (x + ux * s + inward[0] * v, y + uy * s + inward[1] * v)
            for s, v in [(-4, -4), (4, -4), (4, 4), (-4, 4)]
        ]
        # 2025 front: triple arcade on square lower stage; eight-sided belfry above.
        for aa, bb in zip(corners, corners[1:] + corners[:1]):
            wall(aa, bb, h, 33, [(23.0, 29.2)], width=1.65, spacing=2.45)
        for level in [h + 0.3, 31.8, 32.8]:
            mesh.box(x, y, z + level, 8.6, 8.6, 0.40, blue, angle)
        chamfer = [
            (-1.6, -3.7),
            (1.6, -3.7),
            (3.7, -1.6),
            (3.7, 1.6),
            (1.6, 3.7),
            (-1.6, 3.7),
            (-3.7, 1.6),
            (-3.7, -1.6),
        ]
        octagon = [(x + ux * s + inward[0] * v, y + uy * s + inward[1] * v) for s, v in chamfer]
        for aa, bb in zip(octagon, octagon[1:] + octagon[:1]):
            wall(aa, bb, 33, 42, [(34.1, 39.2)], width=1.50, spacing=2.0)
            for level in (33.2, 40.8, 41.7):
                mesh.beam((*aa, z + level), (*bb, z + level), 0.17, blue, 8)
        # Square platform closes transition around the chamfered upper shaft.
        mesh.face([(*q, z + 33) for q in corners], stone)
        spire(x, y, 8.0, 42, 13, angle)
        for sx in [-1, 1]:
            for sy in [-1, 1]:
                xx = x + ux * sx * 3.8 + inward[0] * sy * 3.8
                yy = y + uy * sx * 3.8 + inward[1] * sy * 3.8
                mesh.lathe(
                    xx,
                    yy,
                    z + 32.9,
                    [(0.53, 0), (0.53, 3.2), (0.65, 3.3), (0.53, 3.7), (0.08, 6.3)],
                    stone,
                    n=8,
                )
        # Small open parapet arcade below the belfry, simplified from the photograph.
        for aa, bb in zip(corners, corners[1:] + corners[:1]):
            dx, dy = bb[0] - aa[0], bb[1] - aa[1]
            for i in range(11):
                xx = aa[0] + dx * (i + 0.5) / 11
                yy = aa[1] + dy * (i + 0.5) / 11
                mesh.beam((xx, yy, z + 31.8), (xx, yy, z + 32.7), 0.065, stone, 8)
    # Missing central entrance gable, with a recessed three-light arched window.
    # Estimated proportions follow the newly inspected 2025 frontal reference.
    cx = (a[0] + b[0]) / 2
    cy = (a[1] + b[1]) / 2
    half = (length - 17.6) / 2

    def gp(t, zz, d=0):
        return (cx + ux * t - inward[0] * d, cy + uy * t - inward[1] * d, z + zz)

    def gt(t):
        return 29.0 - 7.0 * abs(t) / half

    r = 2.20
    spring = 24.2
    bottom = 22.2
    arc = [
        (r * math.cos(i * math.pi / 40), spring + r * math.sin(i * math.pi / 40)) for i in range(41)
    ]
    # Separate panels leave an actual aperture; the recess is not a decal.
    for lo, hi in [(-half, -r), (r, half)]:
        mesh.face(
            [gp(lo, 22, 0.12), gp(hi, 22, 0.12), gp(hi, gt(hi), 0.12), gp(lo, gt(lo), 0.12)], stone
        )
    mesh.face([gp(-r, 22, 0.12), gp(r, 22, 0.12), gp(r, bottom, 0.12), gp(-r, bottom, 0.12)], stone)
    for q0, q1 in zip(arc, arc[1:]):
        mesh.face(
            [gp(*q0, 0.12), gp(*q1, 0.12), gp(q1[0], gt(q1[0]), 0.12), gp(q0[0], gt(q0[0]), 0.12)],
            stone,
        )
        mesh.beam(gp(*q0, 0.21), gp(*q1, 0.21), 0.15, blue, 8)
    contour = [(-r, bottom), (r, bottom)] + arc
    mesh.face([gp(t, zz, -0.3) for t, zz in contour], glass)
    for q0, q1 in zip(contour, contour[1:] + contour[:1]):
        mesh.face([gp(*q0, 0.12), gp(*q1, 0.12), gp(*q1, -0.3), gp(*q0, -0.3)], stone)
    for t in (-0.73, 0.73):
        mesh.beam(gp(t, bottom, -0.10), gp(t, 25.8, -0.10), 0.12, stone, 10)
    for side in (-1, 1):
        mesh.beam(gp(side * half, 22, 0.2), gp(0, 29, 0.2), 0.19, blue, 10)
        for i in range(1, 10):
            t = side * half * i / 10
            zz = gt(t) - 0.40
            mesh.beam(gp(t, zz - 0.38, 0.20), gp(t, zz, 0.20), 0.095, stone, 8)
    # Projecting balcony/cornice under the upper window.
    mesh.box(*gp(0, 22.0, 0.38), 5.4, 0.75, 0.25, stone, angle)
    mesh.beam(gp(-2.5, 22.9, 0.67), gp(2.5, 22.9, 0.67), 0.10, stone, 10)
    for i in range(15):
        mesh.beam(
            gp(-2.45 + i * 0.35, 22.1, 0.67), gp(-2.45 + i * 0.35, 22.85, 0.67), 0.055, stone, 8
        )
    # Two lower terminal towers are unambiguously visible in both aerial views.
    # Their mapped-plan centres and vertical proportions remain visual estimates.
    ru, rv = roof_frame()
    ox, oy = ROOF_ORIGIN
    for u, v, width in TERMINAL_TOWERS:
        x = ox + ru * u - rv * v
        y = oy + rv * u + ru * v
        corners = [
            (x + ru * a - rv * b, y + rv * a + ru * b)
            for a, b in [
                (-width / 2, -width / 2),
                (width / 2, -width / 2),
                (width / 2, width / 2),
                (-width / 2, width / 2),
            ]
        ]
        for aa, bb in zip(corners, corners[1:] + corners[:1]):
            wall(aa, bb, h, 35, [(23, 27), (29, 32)], width=1.7, spacing=3.8)
        for zz in (22.3, 28.3, 34.7):
            mesh.box(x, y, z + zz, width + 0.4, width + 0.4, 0.34, blue, math.atan2(rv, ru))
        spire(x, y, width, 35, 12.0, math.atan2(rv, ru))
    # Clean repeated crown vertices without moving any authored surface.
    clean = []
    materials = []
    for f, mi in zip(mesh.f, mesh.mi):
        ids = []
        for i in f:
            if not ids or math.dist(mesh.v[ids[-1]], mesh.v[i]) > 1e-9:
                ids.append(i)
        if len(ids) > 1 and math.dist(mesh.v[ids[0]], mesh.v[ids[-1]]) < 1e-9:
            ids.pop()
        if len(ids) >= 3:
            clean.append(tuple(ids))
            materials.append(mi)
    mesh.f = clean
    mesh.mi = materials
    obj = mesh.done()
    roof_obj, roof_report = build_roofs(ctx, feature, z, slate, glass, stone, blue)
    return {
        "created": [obj.name, roof_obj.name],
        "parameters": {
            **roof_report,
            "shell_height_m": h,
            "tower_total_height_m": 55,
            "tower_finial_m": 56.6,
            "terminal_tower_roof_top_m": 47,
            "terminal_tower_finial_m": 48.6,
            "tower_xy_estimated": positions,
            "recess_depth_m_estimated": 0.42,
            "arched_apertures": apertures,
            "additional_roof_dormer_apertures": dormer_apertures,
            "main_portal_recess_m_estimated": 1.20,
            "detail_basis": "Mapped perimeter plus inspected Herzog2020 south/detail/entrance and Daniel Lu2025 front; tower transition, gable and portal reconstructed with estimated dimensions",
            "polish_revision": "008",
            "central_tower_upper_stage": "octagonal chamfered belfry with faceted slate spire",
            "main_portal_width_m": 10,
        },
        "interfaces": {"entrances": entrances},
        "uncertainty": [
            "Facade bay counts, tower dimensions and heights are visually estimated; no survey or metric photo calibration.",
            "Main entrance is partly obscured; paired leaves and a 0.10 m sill step are explicit artistic completion within the observed portal throat; surrounding ground support remains coordinator work.",
            "2011 aerial roof partitions and 2020 south facade are mixed-date evidence. Roof dimensions, precise glazing layout, rear and side facade rhythm remain estimated; no claim of complete image-matched museum.",
        ],
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + [
                    "nhm-south-2020-herzog",
                    "va-praefcke-aerial-a-2011",
                    "va-praefcke-aerial-b-2011",
                    "nhm-herzog-detail03-2020",
                    "ea-lidar-composite-2022-tq27ne",
                    "nhm-dllu-front-2025",
                    "nhm-herzog-entrance-2020",
                ]
            )
        ),
    }
