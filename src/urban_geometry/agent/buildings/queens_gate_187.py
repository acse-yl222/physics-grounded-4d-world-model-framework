"""187 Queen's Gate only; mapped footprint, licensed photo and EA roof evidence.
Unknown rear fenestration and fine ornament deliberately simplified.
"""

import math


def build(ctx, feature):
    stone = ctx.material("187 QG cream stucco", (0.76, 0.73, 0.64), 0.83)
    trimat = ctx.material("187 QG pale carved trim", (0.83, 0.80, 0.70), 0.78)
    roofmat = ctx.material("187 QG grey slate", (0.16, 0.19, 0.20), 0.81)
    glass = ctx.material("187 QG recessed glass", (0.065, 0.105, 0.12), 0.24, 0, 0.18)
    wood = ctx.material("187 QG dark timber", (0.12, 0.061, 0.028), 0.71)
    iron = ctx.material("187 QG dark railings", (0.025, 0.029, 0.027), 0.48, 0.65)
    shell = ctx.mesh("mapped stucco and actual window apertures")
    roof = ctx.mesh("segmented main and rear roof")
    detail = ctx.mesh("major frames cornices balcony and portico")
    a = (506.3965188987786, -43.41339774709195)
    tx, ty = 1.73122899234294, -8.85225631576031
    ll = math.hypot(tx, ty)
    tx /= ll
    ty /= ll
    nx, ny = -ty, tx
    angle = math.atan2(ty, tx)
    base = float(feature.get("base_m", 0))

    def P(u, v, z):
        return (a[0] + u * tx + v * nx, a[1] + u * ty + v * ny, base + z)

    def UV(p):
        return ((p[0] - a[0]) * tx + (p[1] - a[1]) * ty, (p[0] - a[0]) * nx + (p[1] - a[1]) * ny)

    def B(u, v, z, w, d, h, mat=trimat):
        x, y, zz = P(u, v, z)
        detail.box(x, y, zz, w, d, h, mat, angle)

    profile = [(-1, 21.4), (0, 21.4), (3.5, 24.4), (9.0, 24.4), (12.0, 20.4), (40.0, 20.4)]

    def H(v):
        for (v0, z0), (v1, z1) in zip(profile, profile[1:]):
            if v0 <= v <= v1:
                return z0 + (z1 - z0) * (v - v0) / (v1 - v0)
        return 21.4

    def face(mesh, pts, mat):
        q = []
        for p in pts:
            if not q or math.dist(q[-1], p) > 1e-8:
                q.append(p)
        if len(q) > 2 and math.dist(q[0], q[-1]) < 1e-8:
            q.pop()
        if len(q) > 2:
            mesh.face(q, mat)

    def wall(aa, bb, ops, top=H, bottom=0):
        length = math.dist(aa, bb)
        du, dv = (bb[0] - aa[0]) / length, (bb[1] - aa[1]) / length

        def Q(s, z, dep=0):
            return P(aa[0] + du * s - dv * dep, aa[1] + dv * s + du * dep, z)

        def cap(s):
            return max(bottom, top(aa[1] + s * dv))

        xs = {0.0, length}
        if abs(dv) > 1e-8:
            for v, z in profile:
                s = (v - aa[1]) / dv
                if 0 < s < length:
                    xs.add(s)
            for (v0, z0), (v1, z1) in zip(profile, profile[1:]):
                if min(z0, z1) < bottom < max(z0, z1):
                    v = v0 + (bottom - z0) * (v1 - v0) / (z1 - z0)
                    s = (v - aa[1]) / dv
                    if 0 < s < length:
                        xs.add(s)
        for c, r, bot, spr, arch, mat in ops:
            xs.update(
                c - r + 2 * r * j / (24 if arch else 1) for j in range((24 if arch else 1) + 1)
            )
        for lo, hi in zip(sorted(xs), sorted(xs)[1:]):
            if hi - lo < 1e-8 or max(cap(lo), cap(hi)) <= bottom + 1e-8:
                continue
            op = next((o for o in ops if o[0] - o[1] < (lo + hi) / 2 < o[0] + o[1]), None)
            if op:
                c, r, bot, spr, arch, mat = op
                zt = lambda s: spr + (math.sqrt(max(0, r * r - (s - c) ** 2)) if arch else 0)
                z0, z1 = zt(lo), zt(hi)
                dep = 0.70 if mat == wood else 0.28
                if bot > bottom:
                    face(shell, [Q(lo, bottom), Q(hi, bottom), Q(hi, bot), Q(lo, bot)], stone)
                face(shell, [Q(lo, z0), Q(hi, z1), Q(hi, cap(hi)), Q(lo, cap(lo))], stone)
                face(shell, [Q(lo, bot, dep), Q(hi, bot, dep), Q(hi, z1, dep), Q(lo, z0, dep)], mat)
                face(shell, [Q(lo, z0), Q(hi, z1), Q(hi, z1, dep), Q(lo, z0, dep)], trimat)
                if arch:
                    detail.beam(Q(lo, z0, -0.07), Q(hi, z1, -0.07), 0.08, trimat, 8)
            else:
                face(shell, [Q(lo, bottom), Q(hi, bottom), Q(hi, cap(hi)), Q(lo, cap(lo))], stone)
        for c, r, bot, spr, arch, mat in ops:
            dep = 0.70 if mat == wood else 0.28
            for s in (c - r, c + r):
                face(shell, [Q(s, bot), Q(s, spr), Q(s, spr, dep), Q(s, bot, dep)], trimat)
                detail.beam(Q(s, bot, -0.06), Q(s, spr, -0.06), 0.075, trimat, 8)
            face(
                shell,
                [Q(c - r, bot), Q(c + r, bot), Q(c + r, bot, dep), Q(c - r, bot, dep)],
                trimat,
            )
            if mat != wood:
                detail.beam(Q(c - r, bot, -0.07), Q(c + r, bot, -0.07), 0.09, trimat, 8)
            if not arch:
                detail.beam(Q(c - r, spr, -0.07), Q(c + r, spr, -0.07), 0.09, trimat, 8)
            if mat == glass:
                detail.beam(Q(c, bot, 0.21), Q(c, spr, 0.21), 0.033, trimat, 6)
                detail.beam(
                    Q(c - r, (bot + spr) / 2, 0.21),
                    Q(c + r, (bot + spr) / 2, 0.21),
                    0.033,
                    trimat,
                    6,
                )

    # Per-floor wall bands allow multiple vertically aligned openings.
    bands = [
        (0, 5.1, 1.25, 4.45, False),
        (5.1, 10.0, 5.75, 9.35, False),
        (10.0, 14.2, 10.65, 13.65, False),
        (14.2, 18.0, 14.75, 17.35, False),
        (18.0, 21.4, 18.55, 19.9, True),
    ]
    ring = feature["geometry"][0]["outer"]
    uv = [UV(p) for p in ring]
    for i, (aa, bb) in enumerate(zip(uv, uv[1:] + uv[:1])):
        if i != 0:
            wall(aa, bb, [], top=H)
            continue
        for low, high, bot, spr, arch in bands:
            ops = []
            for c in (1.5, 4.5, 7.5):
                isdoor = low == 0 and c == 1.5
                ops.append(
                    (
                        c,
                        0.8 if isdoor else 0.65,
                        0.9 if isdoor else bot,
                        4.3 if isdoor else spr,
                        False if isdoor else arch,
                        wood if isdoor else glass,
                    )
                )
            wall(aa, bb, ops, top=lambda v, h=high: h, bottom=low)
    # Exact source bottom and roof: clip every mapped triangle at profile breaks.
    shell.surface(feature["geometry"], base, stone)

    def clip(points, cut, keep_above):
        out = []
        for a, b in zip(points, points[1:] + points[:1]):
            ia = a[1] >= cut - 1e-9 if keep_above else a[1] <= cut + 1e-9
            ib = b[1] >= cut - 1e-9 if keep_above else b[1] <= cut + 1e-9
            if ia:
                out.append(a)
            if ia != ib:
                t = (cut - a[1]) / (b[1] - a[1])
                out.append((a[0] + t * (b[0] - a[0]), cut))
        return out

    for part in feature["geometry"]:
        for tri in part["triangles"]:
            for (v0, z0), (v1, z1) in zip(profile, profile[1:]):
                points = clip(clip([UV(p) for p in tri], v0, True), v1, False)
                if len(points) >= 3:
                    face(roof, [P(u, v, H(v)) for u, v in points], roofmat)
    # Western cornices remain entirely within this nine-metre plot.
    for z, h in [(0.7, 0.22), (5.1, 0.3), (10.0, 0.24), (14.2, 0.28), (18.0, 0.55), (21.35, 0.35)]:
        if z < 4.5:
            B(0.25, -0.13, z, 0.5, 0.26, h)
            B(5.76, -0.13, z, 6.50, 0.26, h)
        else:
            B(ll / 2, -0.15, z, ll, 0.4, h)
    for u in (0.15, 3.0, 6.0, ll - 0.15):
        B(u, -0.08, 12.0, 0.14, 0.18, 12.0)
    for u in [0.3 + j * 0.43 for j in range(20)]:
        B(u, -0.25, 17.8, 0.19, 0.36, 0.42)
    # Three-window attic and triangular pediment: image shows this lower
    # centre-house crown, but foliage limits exact bay attribution.
    wall(
        (0.7, -0.05),
        (8.3, -0.05),
        [
            (1.1, 0.55, 22.0, 23.5, False, glass),
            (3.8, 0.55, 22.0, 23.5, False, glass),
            (6.5, 0.55, 22.0, 23.5, False, glass),
        ],
        top=lambda v: 23.85,
        bottom=21.4,
    )
    B(4.5, -0.07, 23.85, 7.8, 0.4, 0.24)
    face(detail, [P(2.1, -0.10, 23.95), P(6.9, -0.10, 23.95), P(4.5, -0.10, 25.15)], stone)
    detail.beam(P(2.1, -0.10, 23.95), P(4.5, -0.10, 25.15), 0.12, trimat, 8)
    detail.beam(P(4.5, -0.10, 25.15), P(6.9, -0.10, 23.95), 0.12, trimat, 8)
    # Small photo-compatible party-side chimney stacks, wholly inside own plot.
    # Locations and pot count are estimates; no long186 corner chimney wall.
    for u in (0.5, ll - 0.5):
        B(u, 3.9, 24.8, 0.65, 1.2, 1.2, stone)
        B(u, 3.9, 25.4, 0.85, 1.4, 0.22)
        for v in (3.6, 4.2):
            x, y, z = P(u, v, 25.52)
            detail.lathe(x, y, z, [(0.13, 0), (0.13, 0.40)], roofmat, 10)
    for u in (4.5, 7.5):
        face(
            detail, [P(u - 0.85, -0.15, 9.55), P(u + 0.85, -0.15, 9.55), P(u, -0.15, 10.05)], trimat
        )
        B(u, -0.15, 9.52, 1.8, 0.35, 0.12)
    # Portico at northern west bay; six finite estimated steps, first tread .15m.
    for u in (0.30, 2.70):
        B(u, -0.85, 0.425, 0.60, 0.65, 0.95)
        x, y, z = P(u, -0.85, 0.9)
        detail.lathe(
            x,
            y,
            z,
            [(0.24, 0), (0.24, 0.2), (0.17, 0.35), (0.15, 3.4), (0.27, 3.5), (0.27, 3.7)],
            trimat,
            16,
        )
    B(1.5, -0.65, 4.72, 2.95, 1.7, 0.30)
    for j in range(6):
        v = -2.7 + j * 0.32
        top = 0.15 * (j + 1)
        B(1.5, v, (-0.05 + top) / 2, 1.9, 0.32, top + 0.05, trimat)
    B(1.5, -0.47, 0.425, 1.9, 0.94, 0.95, trimat)
    for u in (3.3, 6.3, 8.7):
        B(u, -0.35, 5.0, 0.24, 0.7, 0.5)
    # Balcony rails, simplified geometric stone balusters above portico.
    for u in [0.15 + j * 0.24 for j in range(12)]:
        B(u, -1.35, 5.25, 0.09, 0.12, 0.6)
    B(1.5, -1.35, 5.6, 2.95, 0.2, 0.16)
    threshold = P(1.5, 0, 0.9)
    objects = [m.done() for m in (shell, roof, detail)]
    return {
        "created": [o.name for o in objects if o],
        "parameters": {
            "main_roof_m": 24.4,
            "rear_roof_m": 20.4,
            "chimney_pots_top_m": 25.92,
            "height_basis": "EA native1m plus licensed2023 street image; detailed heights estimated",
        },
        "interfaces": {
            "entrances": [
                {
                    "id": "west_187_door",
                    "threshold_xyz": list(threshold),
                    "outward_normal": [-nx, -ny, 0],
                    "clear_width_m": 1.6,
                    "door_leaf_depth_m": 0.7,
                    "stair_treads": 6,
                    "tread_m": 0.32,
                    "riser_m": 0.15,
                    "landing_depth_m": 0.76,
                    "stairs_authoring_extent": [list(P(0.55, -2.86, -0.05)), list(P(2.45, 0, 0.9))],
                    "support_z": base - 0.05,
                    "basis": "Western entrance bay largely tree-occluded; placement and risers are estimates",
                }
            ]
        },
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + ["gore-noswan-adjacent-2023", "ea-lidar-composite-2022-tq27ne"]
            )
        ),
        "uncertainty": [
            "Only way117010280, not186/188 or Gore; exact quadrilateral footprint retained.",
            "Cream stucco, major sash and round-head windows, attic and portico photo-supported; detail dimensions estimated.",
            "Both north/south partywalls and mapped adjacent rear blank. Roof simplified from EA surfaces; no shared-wall apertures.",
            "Fine sculpture inscriptions and complete ironwork omitted. CC BY-SA4.0 photo-derived contribution.",
            "Entrance level and stair dimensions need coordinator final paving/contact validation.",
        ],
    }
