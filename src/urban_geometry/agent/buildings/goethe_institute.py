"""Goethe-Institut 50–51 Princes Gate: reduced-detail evidence-informed street houses.
Uses original local UTM metres; no I/O or scene-wide mutation. Two footprint
projections are low entrance porticoes, not full-height building blocks.
"""

import math

SOURCE = "goethe-noswansofine-2023"


def build(ctx, feature):
    stone = ctx.material("Goethe warm white stucco", (0.77, 0.75, 0.67), 0.76)
    trim = ctx.material("Goethe pale stone dressings", (0.88, 0.85, 0.76), 0.66)
    brick = ctx.material("Goethe rear London stock brick", (0.35, 0.27, 0.16), 0.85)
    slate = ctx.material("Goethe recessed slate roofs", (0.10, 0.13, 0.15), 0.75)
    glass = ctx.material("Goethe inset sash glass", (0.055, 0.115, 0.14), 0.24, 0, 0.12)
    wood = ctx.material("Goethe dark entrance leaves", (0.055, 0.05, 0.04), 0.6)
    iron = ctx.material("Goethe black iron details", (0.045, 0.045, 0.04), 0.6, 0.6)
    m = ctx.mesh("Mapped main house real openings and two low porticoes")
    roof = ctx.mesh("Concealed pitched roof and observed chimney silhouettes")
    base = float(feature.get("base_m", 0))
    raw = feature["geometry"][0]["outer"]
    main = [raw[i] for i in [0, 1, 2, 3, 6, 7, 10]]
    a, b = main[3], main[0]
    L = math.dist(a, b)
    tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = ty, -tx
    ang = math.atan2(ty, tx)
    entrances = []
    apertures = 0

    def point(u, v, z):
        return (a[0] + tx * u - nx * v, a[1] + ty * u - ny * v, base + z)

    def uv(p):
        return ((p[0] - a[0]) * tx + (p[1] - a[1]) * ty, -(p[0] - a[0]) * nx - (p[1] - a[1]) * ny)

    def safe(mesh, poly, mat):
        for i in range(1, len(poly) - 1):
            p, q, r = poly[0], poly[i], poly[i + 1]
            v = [q[k] - p[k] for k in range(3)]
            w = [r[k] - p[k] for k in range(3)]
            cross = [
                v[(k + 1) % 3] * w[(k + 2) % 3] - v[(k + 2) % 3] * w[(k + 1) % 3] for k in range(3)
            ]
            if sum(x * x for x in cross) > 1e-12:
                mesh.face([p, q, r], mat)

    porches = [raw[3:7], raw[7:11]]
    centers = [sum(uv(p)[0] for p in poly) / 4 for poly in porches]
    # Six principal axes over two original street houses. Entrance axes follow
    # the two mapped portico projections; remaining axes use observed three-bay grammar.
    axes = [
        centers[0],
        centers[0] + 3.6,
        centers[0] + 7.2,
        centers[1],
        centers[1] + 3.6,
        centers[1] + 7.2,
    ]
    axes = sorted(c for c in axes if 1 < c < L - 1)

    def wall(aa, bb, front=False, rear=False, party=False):
        nonlocal apertures
        ll = math.dist(aa, bb)
        tt = ((bb[0] - aa[0]) / ll, (bb[1] - aa[1]) / ll)
        nn = (tt[1], -tt[0])
        theta = math.atan2(tt[1], tt[0])

        def p(u, z, d=0):
            return (aa[0] + tt[0] * u - nn[0] * d, aa[1] + tt[1] * u - nn[1] * d, base + z)

        holes = []
        cs = (
            [
                (point(c, 0, 0)[0] - aa[0]) * tt[0] + (point(c, 0, 0)[1] - aa[1]) * tt[1]
                for c in axes
            ]
            if front
            else [(i + 0.5) * ll / 6 for i in range(6)]
        )
        cs = [c for c in cs if 0.95 < c < ll - 0.95]
        rows = [(1.0, 4.0), (5.9, 9.5), (11.2, 14.3), (16.1, 18.7), (20.35, 22.2)]
        if not party:
            for c in cs:
                for lo, hi in rows:
                    isdoor = (
                        front and lo < 2 and min(abs(uv(p(c, 0))[0] - x) for x in centers) < 0.2
                    )
                    width = 2.10 if isdoor else 1.72 if lo < 16 else 1.5
                    holes.append(
                        (
                            c - width / 2,
                            c + width / 2,
                            0.25 if isdoor else lo,
                            3.7 if isdoor else hi,
                            isdoor,
                        )
                    )
        cuts = sorted(set([0, 23.05] + [z for o in holes for z in o[2:4]]))
        mat = stone if front else brick
        for lo, hi in zip(cuts, cuts[1:]):
            spans = sorted((o[0], o[1]) for o in holes if o[2] <= lo and o[3] >= hi)
            cursor = 0
            for left, right in spans + [(ll, ll)]:
                if left > cursor:
                    safe(m, [p(cursor, lo), p(left, lo), p(left, hi), p(cursor, hi)], mat)
                cursor = max(cursor, right)
        for left, right, lo, hi, isdoor in holes:
            apertures += 1
            c = (left + right) / 2
            dep = 0.60 if isdoor else 0.32
            safe(
                m,
                [
                    p(left, lo, dep + 0.12),
                    p(right, lo, dep + 0.12),
                    p(right, hi, dep + 0.12),
                    p(left, hi, dep + 0.12),
                ],
                glass,
            )
            for u, v in [
                ((left, lo), (right, lo)),
                ((right, lo), (right, hi)),
                ((right, hi), (left, hi)),
                ((left, hi), (left, lo)),
            ]:
                safe(m, [p(*u), p(*v), p(*v, dep), p(*u, dep)], trim if front else brick)
            for x in (left, right):
                m.box(*p(x, (lo + hi) / 2, 0.10), 0.095, 0.17, hi - lo, trim, theta)
            m.box(*p(c, hi + 0.07, -0.03), right - left + 0.25, 0.27, 0.14, trim, theta)
            if isdoor:
                leafw = (right - left - 0.10) / 2
                for sign in (-1, 1):
                    cc = c + sign * (leafw / 2 + 0.025)
                    m.box(*p(cc, (lo + 3.15) / 2, dep), leafw, 0.10, 3.15 - lo, wood, theta)
                    for z in [0.65, 1.55, 2.50]:
                        m.box(*p(cc, z, dep - 0.06), leafw - 0.20, 0.035, 0.55, wood, theta)
                    for x in (cc - leafw / 2 + 0.035, cc + leafw / 2 - 0.035):
                        m.box(
                            *p(x, (lo + 3.15) / 2, dep - 0.065), 0.07, 0.04, 3.15 - lo, trim, theta
                        )
                    m.beam(
                        p(cc - sign * 0.30, 1.1, dep - 0.09),
                        p(cc - sign * 0.30, 1.5, dep - 0.09),
                        0.025,
                        iron,
                        8,
                    )
                    entrances.append(
                        {
                            "threshold_xyz": list(p(cc, lo)),
                            "outward_normal": [nn[0], nn[1], 0],
                            "door_leaf_xyz": list(p(cc, (lo + 3.15) / 2, dep)),
                            "door_leaf_depth_m": dep - 0.05,
                            "clear_width_m": leafw - 0.15,
                            "stair_treads": 2,
                            "riser_m": 0.125,
                            "tread_m": 0.32,
                            "landing_depth_m": 2.2,
                            "landing_z_m": 0.25,
                            "ramp": "unverified",
                            "supporting_surface": "authored finite portico floor and two-level sill; coordinator ground pending",
                            "estimated": True,
                        }
                    )
                # Lintel/transom above intentional closed leaves.
                m.box(*p(c, 3.22, 0.1), right - left, 0.18, 0.10, trim, theta)
            else:
                m.box(*p(c, (lo + hi) / 2, 0.16), 0.07, 0.10, hi - lo, trim, theta)
                m.box(*p(c, lo + (hi - lo) * 0.52, 0.15), right - left, 0.12, 0.08, trim, theta)
                m.box(*p(c, lo - 0.08, -0.075), right - left + 0.28, 0.38, 0.16, trim, theta)
                if front and 5 < lo < 15:
                    # Major classical dressings only: layered lintels and alternating pediments.
                    for x in (left - 0.16, right + 0.16):
                        m.box(*p(x, (lo + hi) / 2, -0.045), 0.16, 0.22, hi - lo, trim, theta)
                    m.box(*p(c, hi + 0.22, -0.1), right - left + 0.65, 0.43, 0.18, trim, theta)
                    if 11 < lo < 12:
                        if cs.index(c) % 2:
                            m.beam(
                                p(c - 1.15, hi + 0.35, -0.12), p(c, hi + 0.98, -0.12), 0.09, trim, 8
                            )
                            m.beam(
                                p(c, hi + 0.98, -0.12), p(c + 1.15, hi + 0.35, -0.12), 0.09, trim, 8
                            )
                        else:
                            arc = [
                                p(
                                    c + 1.1 * math.cos(i * math.pi / 20),
                                    hi + 0.32 + 0.60 * math.sin(i * math.pi / 20),
                                    -0.12,
                                )
                                for i in range(21)
                            ]
                            for pp, qq in zip(arc, arc[1:]):
                                m.beam(pp, qq, 0.085, trim, 8)
        if front:
            for z, w, d, h in [
                (4.9, ll, 0.35, 0.22),
                (10.35, ll, 0.33, 0.18),
                (15.3, ll, 0.30, 0.14),
                (19.55, ll, 0.75, 0.32),
                (19.88, ll, 0.85, 0.20),
                (22.95, ll, 0.32, 0.16),
            ]:
                m.box(*p(ll / 2, z, -0.10), w, d, h, trim, theta)
            # Ground rustication omits door intervals rather than crossing clear throats.
            for z in [0.75 + i * 0.48 for i in range(8)]:
                blocked = sorted((o[0] - 0.04, o[1] + 0.04) for o in holes if o[2] < z < o[3])
                cursor = 0
                for le, ri in blocked + [(ll, ll)]:
                    if le > cursor:
                        m.box(
                            *p((le + cursor) / 2, z, -0.02), le - cursor, 0.07, 0.025, trim, theta
                        )
                    cursor = ri
            for c in [i * 0.45 + 0.2 for i in range(int(ll / 0.45))]:
                m.box(*p(c, 19.35, -0.22), 0.16, 0.48, 0.27, trim, theta)
        # Continuous parapet, including plain party elevations. No invented party-wall windows.
        m.box(*p(ll / 2, 23.45, 0), ll, 0.30, 0.80, stone if front else brick, theta)
        m.box(*p(ll / 2, 23.89, 0), ll + 0.08, 0.43, 0.13, trim, theta)

    for i, (aa, bb) in enumerate(zip(main, main[1:] + main[:1])):
        wall(aa, bb, front=i >= 3, rear=i == 1, party=i in (0, 2))
    # True low porticoes occupy the two existing mapped projections.
    for polygon, c in zip(porches, centers):
        points = list(polygon)
        poly3 = [(*p, base + 0.25) for p in points]
        # These mapped four-sided porticoes are convex.
        safe(m, poly3, trim)
        safe(m, [(*p, base + 4.9) for p in points], trim)
        for pp, qq in zip(points, points[1:] + points[:1]):
            safe(m, [(*pp, base), (*qq, base), (*qq, base + 0.25), (*pp, base + 0.25)], trim)
            safe(
                m,
                [(*pp, base + 4.6), (*qq, base + 4.6), (*qq, base + 4.9), (*pp, base + 4.9)],
                trim,
            )
        frontcorners = sorted(points, key=lambda p: uv(p)[1])[:2]
        for pp in frontcorners:
            # Bring columns slightly inside the canopy outline; conservative clear approach.
            u, v = uv(pp)
            u += 0.28 if u < c else -0.28
            v += 0.25
            for z, w, d, h in [
                (0.43, 0.65, 0.65, 0.35),
                (2.5, 0.40, 0.40, 3.8),
                (4.45, 0.63, 0.63, 0.24),
            ]:
                m.box(*point(u, v, z), w, d, h, trim, ang)
        # Source-visible balustrade around three exposed roof edges.
        for pp, qq in zip(points, points[1:] + points[:1]):
            if min(uv(pp)[1], uv(qq)[1]) > -0.15:
                continue
            ll = math.dist(pp, qq)
            theta = math.atan2(qq[1] - pp[1], qq[0] - pp[0])
            m.box(
                (pp[0] + qq[0]) / 2, (pp[1] + qq[1]) / 2, base + 5.95, ll, 0.18, 0.16, trim, theta
            )
            for k in range(1, max(2, int(ll / 0.28))):
                t = k / max(2, int(ll / 0.28))
                xx = pp[0] + t * (qq[0] - pp[0])
                yy = pp[1] + t * (qq[1] - pp[1])
                m.beam((xx, yy, base + 4.97), (xx, yy, base + 5.85), 0.04, trim, 8)
        vfront = min(uv(p)[1] for p in points)
        m.box(*point(c, vfront - 0.15, 0.0625), 2.5, 0.35, 0.125, trim, ang)

    # One roof pair behind the parapet, split exactly at a constant-depth ridge.
    def height(v):
        return 23.6 + 2.6 * (1 - abs(v - 11) / 11)

    def clip(poly, positive):
        out = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            dp = (p[1] - 11) * (1 if positive else -1)
            dq = (q[1] - 11) * (1 if positive else -1)
            if dp >= -1e-9:
                out.append(p)
            if dp * dq < 0 and abs(dp) > 1e-9 and abs(dq) > 1e-9:
                t = dp / (dp - dq)
                out.append(tuple(p[k] + t * (q[k] - p[k]) for k in range(2)))
        return out

    quad = [uv(p) for p in main]

    def earclip(poly):
        pending = list(poly)
        tris = []

        def cross(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        while len(pending) > 3:
            found = False
            for i in range(len(pending)):
                a, b, c = pending[i - 1], pending[i], pending[(i + 1) % len(pending)]
                if cross(a, b, c) <= 1e-9:
                    continue
                if any(
                    q not in (a, b, c)
                    and min(cross(a, b, q), cross(b, c, q), cross(c, a, q)) >= -1e-9
                    for q in pending
                ):
                    continue
                tris.append([a, b, c])
                pending.pop(i)
                found = True
                break
            if not found:
                raise ValueError("Cannot triangulate exact Goethe main footprint")
        tris.append(pending)
        return tris

    for tri in earclip(quad):
        for side in (True, False):
            safe(roof, [point(u, v, height(v)) for u, v in clip(tri, side)], slate)
    for pp, qq in zip(quad, quad[1:] + quad[:1]):
        cuts = [0, 1]
        if (pp[1] - 11) * (qq[1] - 11) < 0:
            cuts.append((11 - pp[1]) / (qq[1] - pp[1]))
        cuts = sorted(cuts)
        for x, y in zip(cuts, cuts[1:]):
            p = [pp[k] + x * (qq[k] - pp[k]) for k in range(2)]
            q = [pp[k] + y * (qq[k] - pp[k]) for k in range(2)]
            safe(
                roof,
                [
                    point(*p, 23.05),
                    point(*q, 23.05),
                    point(*q, height(q[1])),
                    point(*p, height(p[1])),
                ],
                brick,
            )
    for u in (4.0, 14.6):
        v = 16.5
        z = height(v)
        m.box(*point(u, v, (z + 27.7) / 2), 1.65, 0.90, 27.7 - z, stone, ang)
        m.box(*point(u, v, 27.7), 1.9, 1.12, 0.20, trim, ang)
        for du in (-0.5, 0, 0.5):
            roof.beam(point(u + du, v, 27.8), point(u + du, v, 28.45), 0.14, brick, 12)
    objs = [m.done(), roof.done()]
    return {
        "created": [ob.name for ob in objs if ob],
        "parameters": {
            "address": "50–51 Princes Gate / Exhibition Road; official institution address 50 Princes Gate",
            "main_facade_levels": 5,
            "main_wall_m": 23.05,
            "parapet_top_m": 23.955,
            "roof_eaves_m": 23.6,
            "roof_ridge_m": 26.2,
            "chimney_top_m": 28.45,
            "portico_roof_m": 4.9,
            "portico_balustrade_top_m": 6.03,
            "actual_apertures": apertures,
            "facade_axes_u_m": axes,
            "footprint_handling": "Original seven-vertex main house plus two mapped low portico polygons; adjacent houses excluded.",
            "height_basis": "EA2022 local roof p50 24.715m and p95 26.593m; dimensions estimated",
            "detail_level": "Reduced-detail five-level stucco street house, true openings and two low columned porticoes",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            SOURCE,
            "goethe-official-address-2026",
            "ea-lidar-composite-2022-tq27ne",
        ],
        "uncertainty": [
            "Institution occupies mapped 50–51 feature; official visitor address is 50 Princes Gate, not Queens Gate.",
            "Door positions follow the two mapped porticoes and visible entrance bays, while leaf dimensions and two shallow step heights are estimated.",
            "Hidden roof pitch, ridge and chimney locations are approximate within EA height envelope. Rear windows are estimated; party walls are opaque.",
            "No below-street excavation, basement interior, neighbouring property geometry, exact moulded capitals or signs reproduced. Surrounding terrain and neighbour-height transitions remain coordinator checks.",
        ],
    }
