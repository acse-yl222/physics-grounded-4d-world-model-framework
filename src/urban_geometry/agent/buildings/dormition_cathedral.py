"""Dormition Cathedral: mapped exterior with PD/CC0 photo-supported Romanesque grammar.
Dimensions and hidden elevations are estimates; authoring local UTM, no scene mutation.
"""

import math


def build(ctx, feature):
    stone = ctx.material("Dormition warm brick stone", (0.55, 0.43, 0.30), 0.86)
    pale = ctx.material("Dormition pale stone courses", (0.73, 0.69, 0.59), 0.82)
    slate = ctx.material("Dormition slate roofs", (0.18, 0.22, 0.21), 0.75)
    glass = ctx.material("Dormition dark recessed glazing", (0.04, 0.065, 0.058), 0.26)
    wood = ctx.material("Dormition timber door", (0.13, 0.065, 0.028), 0.73)
    shell = ctx.mesh("Dormition mapped shell and true recessed apertures")
    roof = ctx.mesh("Dormition pitched roofs and campanile")
    trim = ctx.mesh("Dormition major stone frames and rose tracery")
    raw_face = shell.face

    def clean_face(points, mat):
        out = []
        for q in points:
            if not out or math.dist(out[-1], q) > 1e-8:
                out.append(q)
        if len(out) > 2 and math.dist(out[0], out[-1]) < 1e-8:
            out.pop()
        if len(out) > 2:
            raw_face(out, mat)

    shell.face = clean_face
    a = (1221.273135874304, 62.821720271371305)
    L = math.hypot(2.192709679017, 10)
    tx, ty = 2.192709679017 / L, -10 / L
    nx, ny = -ty, tx
    ang = math.atan2(ty, tx)
    base = float(feature.get("base_m", 0))

    def P(u, v, z):
        return (a[0] + tx * u + nx * v, a[1] + ty * u + ny * v, base + z)

    def UV(q):
        return ((q[0] - a[0]) * tx + (q[1] - a[1]) * ty, (q[0] - a[0]) * nx + (q[1] - a[1]) * ny)

    def B(u, v, z, w, d, h, mat=stone):
        x, y, zz = P(u, v, z)
        trim.box(x, y, zz, w, d, h, mat, ang)

    def wall(q0, q1, h, ops=(), bottom=0):
        length = math.dist(q0, q1)
        du, dv = (q1[0] - q0[0]) / length, (q1[1] - q0[1]) / length

        def Q(s, z, dep=0):
            return P(q0[0] + du * s - dv * dep, q0[1] + dv * s + du * dep, z)

        xs = {0.0, length}
        for c, r, bot, spr, mat in ops:
            xs.update(c - r + 2 * r * j / 32 for j in range(33))
        xs = sorted(xs)
        for lo, hi in zip(xs, xs[1:]):
            op = next((o for o in ops if o[0] - o[1] < (lo + hi) / 2 < o[0] + o[1]), None)
            if not op:
                shell.face([Q(lo, bottom), Q(hi, bottom), Q(hi, h), Q(lo, h)], stone)
                continue
            c, r, bot, spr, mat = op
            z0 = spr + math.sqrt(max(0, r * r - (lo - c) ** 2))
            z1 = spr + math.sqrt(max(0, r * r - (hi - c) ** 2))
            dep = 0.6 if mat == wood else 0.32
            if bot > bottom:
                shell.face([Q(lo, bottom), Q(hi, bottom), Q(hi, bot), Q(lo, bot)], stone)
            shell.face([Q(lo, z0), Q(hi, z1), Q(hi, h), Q(lo, h)], stone)
            if mat is not None:
                shell.face([Q(lo, bot, dep), Q(hi, bot, dep), Q(hi, z1, dep), Q(lo, z0, dep)], mat)
            shell.face([Q(lo, z0), Q(hi, z1), Q(hi, z1, dep), Q(lo, z0, dep)], pale)
            trim.beam(Q(lo, z0, -0.06), Q(hi, z1, -0.06), 0.09, pale, 8)
        for c, r, bot, spr, mat in ops:
            dep = 0.6 if mat == wood else 0.32
            for side in (-1, 1):
                x = c + side * r
                shell.face([Q(x, bot), Q(x, spr), Q(x, spr, dep), Q(x, bot, dep)], pale)
                trim.beam(Q(x, bot, -0.06), Q(x, spr, -0.06), 0.09, pale, 8)

    r = feature["geometry"][0]["outer"]
    uv = [UV(q) for q in r]
    entries = []
    for i, (aa, bb) in enumerate(zip(uv, uv[1:] + uv[:1])):
        if i in (2, 3):
            continue
        length = math.dist(aa, bb)
        ops = []
        if i in (0, 5):
            for j in range(max(1, int(length / 1.8))):
                ops.append(((j + 0.5) * length / max(1, int(length / 1.8)), 0.35, 5.5, 7.4, glass))
        elif length > 12:
            for j in range(int(length / 5)):
                ops.append(((j + 0.5) * length / int(length / 5), 0.55, 4.5, 6.5, glass))
        wall(aa, bb, 10, ops)
    # Merge the almost-collinear mapped porch front segments, retaining both endpoint anchors.
    aa, bb = uv[2], uv[4]
    length = math.dist(aa, bb)
    c = length / 2
    wall(aa, bb, 10, [(c, 1.4, 0.015, 3.6, wood)])
    du, dv = (bb[0] - aa[0]) / length, (bb[1] - aa[1]) / length
    th = P(aa[0] + du * c, aa[1] + dv * c, 0.015)
    out = [tx * dv - nx * du, ty * dv - ny * du, 0]
    entries.append(
        {
            "id": "west_main_portal",
            "threshold_xyz": list(th),
            "outward_normal": out,
            "clear_width_m": 2.8,
            "door_leaf_depth_m": 0.6,
            "support_z": base + 0.015,
            "basis": "Photo-supported recessed portal; flat approach and dimensions estimated; coordinator ground check required",
        }
    )
    # Porch gable, below nave. Fill remaining front slab above the entrance.
    trim.beam(
        P(aa[0], aa[1] - 0.1, 6.5),
        P((aa[0] + bb[0]) / 2, (aa[1] + bb[1]) / 2 - 0.1, 8),
        0.12,
        pale,
        8,
    )
    trim.beam(
        P((aa[0] + bb[0]) / 2, (aa[1] + bb[1]) / 2 - 0.1, 8),
        P(bb[0], bb[1] - 0.1, 6.5),
        0.12,
        pale,
        8,
    )
    # Mapped baseline roof with low aisles; nave covers its central band.
    shell.surface(feature["geometry"], base, stone)
    roof.surface(feature["geometry"], base + 10, slate)
    # Upper nave entirely inside principal footprint, with front circular rose aperture.
    u0, u1, uc, v0, v1 = 1.4, 12.2, 6.8, 0.4, 40.8
    for q0, q1 in [((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))]:
        ll = math.dist(q0, q1)
        ops = [((j + 0.5) * ll / 7, 0.55, 11, 12.5, glass) for j in range(7)] if ll > 20 else []
        wall(q0, q1, 14, ops, bottom=10)
    # Front rose: actual circular void, inset dark glazing and radial stone tracery.
    zc, rad = 11.8, 2.0
    xs = sorted(set([u0, u1] + [uc - rad + 2 * rad * j / 48 for j in range(49)]))
    for lo, hi in zip(xs, xs[1:]):
        if uc - rad < (lo + hi) / 2 < uc + rad:
            dl = math.sqrt(max(0, rad * rad - (lo - uc) ** 2))
            dh = math.sqrt(max(0, rad * rad - (hi - uc) ** 2))
            shell.face([P(lo, v0, 8), P(hi, v0, 8), P(hi, v0, zc - dh), P(lo, v0, zc - dl)], stone)
            shell.face(
                [P(lo, v0, zc + dl), P(hi, v0, zc + dh), P(hi, v0, 14), P(lo, v0, 14)], stone
            )
            shell.face(
                [
                    P(lo, v0 + 0.32, zc - dl),
                    P(hi, v0 + 0.32, zc - dh),
                    P(hi, v0 + 0.32, zc + dh),
                    P(lo, v0 + 0.32, zc + dl),
                ],
                glass,
            )
        else:
            shell.face([P(lo, v0, 8), P(hi, v0, 8), P(hi, v0, 14), P(lo, v0, 14)], stone)
    for j in range(64):
        t0 = j * math.tau / 64
        t1 = (j + 1) * math.tau / 64
        trim.beam(
            P(uc + rad * math.cos(t0), v0 - 0.05, zc + rad * math.sin(t0)),
            P(uc + rad * math.cos(t1), v0 - 0.05, zc + rad * math.sin(t1)),
            0.12,
            pale,
            8,
        )
    for j in range(12):
        t = j * math.tau / 12
        trim.beam(
            P(uc + 0.35 * math.cos(t), v0 + 0.18, zc + 0.35 * math.sin(t)),
            P(uc + 1.88 * math.cos(t), v0 + 0.18, zc + 1.88 * math.sin(t)),
            0.06,
            pale,
            8,
        )
    for v in (v0, v1):
        shell.face([P(u0, v, 14), P(u1, v, 14), P(uc, v, 17)], stone)
    for l, h in [(u0, uc), (uc, u1)]:
        roof.face(
            [
                P(l, v0, 17 if l == uc else 14),
                P(h, v0, 17 if h == uc else 14),
                P(h, v1, 17 if h == uc else 14),
                P(l, v1, 17 if l == uc else 14),
            ],
            slate,
        )
    for u in (u0, u1):
        B(u, 0.2, 9, 0.3, 0.35, 10, pale)
    trim.beam(P(uc, 0.25, 17), P(uc, 0.25, 18.1), 0.09, pale, 8)
    trim.beam(P(uc - 0.4, 0.25, 17.75), P(uc + 0.4, 0.25, 17.75), 0.08, pale, 8)
    # Southwest campanile, evidenced elevated patch; three real open round arches per side.
    tu, tv, tw = 13.0, 5.0, 4.8
    for q0, q1 in [
        ((tu, tv), (tu + tw, tv)),
        ((tu + tw, tv), (tu + tw, tv + tw)),
        ((tu + tw, tv + tw), (tu, tv + tw)),
        ((tu, tv + tw), (tu, tv)),
    ]:
        wall(q0, q1, 24)
        wall(
            q0,
            q1,
            29,
            [
                (0.85, 0.46, 24.4, 27.5, None),
                (2.4, 0.46, 24.4, 27.5, None),
                (3.95, 0.46, 24.4, 27.5, None),
            ],
            bottom=24,
        )
    B(tu + tw / 2, tv + tw / 2, 29.35, tw + 0.25, tw + 0.25, 0.7, pale)
    roof.face(
        [
            P(tu, tv, 29.72),
            P(tu + tw, tv, 29.72),
            P(tu + tw, tv + tw, 29.72),
            P(tu, tv + tw, 29.72),
        ],
        slate,
    )
    # Dark round clock dial on front tower, abstract hands; no lettering inferred.
    cc = tu + tw / 2
    zz = 22
    for j in range(48):
        t0 = j * math.tau / 48
        t1 = (j + 1) * math.tau / 48
        trim.face(
            [
                P(cc, tv - 0.02, zz),
                P(cc + 0.75 * math.cos(t0), tv - 0.02, zz + 0.75 * math.sin(t0)),
                P(cc + 0.75 * math.cos(t1), tv - 0.02, zz + 0.75 * math.sin(t1)),
            ],
            glass,
        )
    trim.beam(P(cc, tv - 0.06, zz), P(cc + 0.43, tv - 0.06, zz + 0.35), 0.04, pale, 8)
    trim.beam(P(cc, tv - 0.06, zz), P(cc - 0.25, tv - 0.06, zz + 0.1), 0.04, pale, 8)
    objects = [m.done() for m in (shell, roof, trim)]
    return {
        "created": [o.name for o in objects],
        "parameters": {
            "aisle_roof_m": 10,
            "nave_eaves_m": 14,
            "nave_ridge_m": 17,
            "campanile_top_m": 29.7,
            "height_basis": "EA1m relative roof regions, rounded; ornamental dimensions photo estimates",
        },
        "interfaces": {"entrances": entries},
        "evidence_source_ids": list(
            dict.fromkeys(
                feature.get("evidence_source_ids", [])
                + [
                    "dormition-lhimec-2012-cc0",
                    "dormition-manvyi-2008-pd",
                    "ea-lidar-composite-2022-tq27ne",
                ]
            )
        ),
        "uncertainty": [
            "Rear ancillary block roof heights estimated; no hidden equipment invented.",
            "Rose tracery, arcading and clock simplified; no sculptures/inscriptions.",
            "Mapped porch front joins two nearly-collinear segments; tiny endpoint-bounded simplification.",
            "Ground .015 threshold requires full-scene paving check.",
        ],
    }
