"""Royal Albert Hall: evidence-separated mapped volumes and editable exterior detail.

Requires the additive phase5 feature patch. Dimensions of minor architectural
profiles are visual estimates; source part plans/heights remain traceable.
"""

import math

SOURCES = [
    "royal-albert-hall-mdbeckwith-2013",
    "hall-diliff-north-2012",
    "hall-diliff-south-2013",
    "hall-farmer-entry-2012",
    "va-praefcke-aerial-a-2011",
    "va-praefcke-aerial-b-2011",
    "ea-lidar-composite-2022-tq27ne",
]


def build(ctx, feature):
    cfg = feature["detail_parameters"]["phase5"]
    base = float(feature.get("base_m", 0))
    brick = ctx.material("RAH warm red brick", (0.43, 0.17, 0.105), 0.85)
    stone = ctx.material("RAH buff terracotta", (0.76, 0.66, 0.49), 0.8)
    shadow = ctx.material("RAH terracotta recessed panels", (0.46, 0.34, 0.22), 0.88)
    metal = ctx.material("RAH lead glazing bars", (0.22, 0.25, 0.25), 0.42, 0.55)
    glass = ctx.material("RAH recessed facade glass", (0.052, 0.091, 0.105), 0.26, 0.1)
    roofglass = ctx.material("RAH opaque weathered roof glazing", (0.33, 0.39, 0.40), 0.32, 0.18)
    mosaic = ctx.material("RAH mosaic field unresolved tesserae", (0.42, 0.34, 0.24), 0.9)
    blue = ctx.material("RAH south tympanum blue field", (0.19, 0.31, 0.37), 0.8)
    meshes = {
        k: ctx.mesh(k)
        for k in [
            "mapped volume walls and real reveals",
            "classical orders and terracotta profiles",
            "turned balcony balustrades",
            "glazed elliptical dome and raised drum",
            "mapped pavilion roofs",
            "north entrance and bounded steps",
        ]
    }
    wall, detail, rail, dome, roofs, entry = meshes.values()
    entrances = []

    def face(m, vs, mat):
        # Arch endpoints can coincide at a spring or apex: author triangles,
        # rather than introducing duplicate vertices in a nominal quad.
        clean = []
        for p in vs:
            if not clean or math.dist(p, clean[-1]) > 1e-7:
                clean.append(p)
        if len(clean) > 2 and math.dist(clean[0], clean[-1]) < 1e-7:
            clean.pop()
        if len(clean) < 3:
            return
        a = clean[0]
        for b, c in zip(clean[1:], clean[2:]):
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            if (
                sum(
                    (u[(i + 1) % 3] * v[(i + 2) % 3] - u[(i + 2) % 3] * v[(i + 1) % 3]) ** 2
                    for i in range(3)
                )
                > 1e-14
            ):
                m.face([a, b, c], mat)

    def oriented(a, b):
        L = math.dist(a, b)
        tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L

        def p(u, z, out=0):
            return (a[0] + tx * u + ty * out, a[1] + ty * u - tx * out, base + z)

        return L, tx, ty, math.atan2(ty, tx), p

    def boxat(m, p, u, z, w, d, h, mat, ang, out=0):
        m.box(*p(u, z, out), w, d, h, mat, ang)

    def arch(m, p, c, r, z0, spring, mat, out=0.05, thickness=0.20):
        for j in range(32):
            t0 = j * math.pi / 32
            t1 = (j + 1) * math.pi / 32
            pts = [
                p(c + rr * math.cos(t), spring + rr * math.sin(t), out)
                for rr, t in [(r, t0), (r + thickness, t0), (r + thickness, t1), (r, t1)]
            ]
            back = [
                (
                    q[0] - (p(0, 0, 1)[0] - p(0, 0, 0)[0]) * 0.13,
                    q[1] - (p(0, 0, 1)[1] - p(0, 0, 0)[1]) * 0.13,
                    q[2],
                )
                for q in pts
            ]
            face(m, pts, mat)
            face(m, list(reversed(back)), mat)
            for k in range(4):
                face(m, [pts[k], back[k], back[(k + 1) % 4], pts[(k + 1) % 4]], mat)

    def aperture_edge(a, b, H, holes, exterior=True, low=0.0):
        L, tx, ty, ang, p = oriented(a, b)
        # Each opening has a flat sill and polygonal exact circular head.
        # Vertical cuts through each arch chord yield actual wall subtraction.
        cuts = [0.0, L]
        for c, r, z0, sp, arched, door in holes:
            cuts.extend([max(0, min(L, c - r)), max(0, min(L, c + r))])
            if arched:
                cuts.extend(max(0, min(L, c + r * math.cos(j * math.pi / 32))) for j in range(33))
        cuts = sorted(set(round(x, 9) for x in cuts))

        def top(c, r, sp, u, arched):
            return sp + math.sqrt(max(0, r * r - (u - c) ** 2)) if arched else sp

        for lo, hi in zip(cuts, cuts[1:]):
            if hi - lo < 1e-6:
                continue
            active = sorted(
                [h for h in holes if abs((lo + hi) / 2 - h[0]) < h[1] - 1e-8], key=lambda h: h[2]
            )
            zl = zr = low
            for c, r, z0, sp, arched, door in active:
                face(wall, [p(lo, zl), p(hi, zr), p(hi, z0), p(lo, z0)], brick)
                tl, tr = top(c, r, sp, lo, arched), top(c, r, sp, hi, arched)
                depth = 0.65 if door else 0.34
                face(
                    entry if door else wall,
                    [p(lo, z0, -depth), p(hi, z0, -depth), p(hi, tr, -depth), p(lo, tl, -depth)],
                    glass,
                )
                face(wall, [p(lo, tl), p(hi, tr), p(hi, tr, -depth), p(lo, tl, -depth)], stone)
                face(wall, [p(lo, z0), p(lo, z0, -depth), p(hi, z0, -depth), p(hi, z0)], stone)
                zl, zr = tl, tr
            face(wall, [p(lo, zl), p(hi, zr), p(hi, H), p(lo, H)], brick)
        for c, r, z0, sp, arched, door in holes:
            for u in [c - r, c + r]:
                if 0 <= u <= L:
                    face(
                        wall,
                        [
                            p(u, z0),
                            p(u, sp),
                            p(u, sp, -(0.65 if door else 0.34)),
                            p(u, z0, -(0.65 if door else 0.34)),
                        ],
                        stone,
                    )
        return L, tx, ty, ang, p

    def pilaster(p, u, z0, z1, ang, w=0.45):
        boxat(detail, p, u, (z0 + z1) / 2, w, 0.30, z1 - z0, stone, ang, 0.15)
        # Recessed central panel and separate raised edge fillets.
        boxat(detail, p, u, (z0 + z1) / 2, w * 0.52, 0.025, z1 - z0 - 0.5, shadow, ang, 0.314)
        for side in [-1, 1]:
            boxat(
                detail,
                p,
                u + side * w * 0.38,
                (z0 + z1) / 2,
                0.055,
                0.08,
                z1 - z0 - 0.3,
                stone,
                ang,
                0.35,
            )
        for zz, ww, hh, dd in [
            (z0, w * 1.6, 0.20, 0.48),
            (z0 + 0.22, w * 1.32, 0.16, 0.39),
            (z1 - 0.12, w * 1.35, 0.20, 0.45),
            (z1 + 0.1, w * 1.8, 0.22, 0.55),
            (z1 + 0.28, w * 2.0, 0.13, 0.60),
        ]:
            boxat(detail, p, u, zz, ww, dd, hh, stone, ang, 0.16)
        # Small bilateral volutes: circular moulding rings, not sculpture proxies.
        for side in [-1, 1]:
            c = u + side * w * 0.50
            for j in range(16):
                t0 = j * math.tau / 16
                t1 = (j + 1) * math.tau / 16
                detail.beam(
                    p(c + 0.115 * math.cos(t0), z1 + 0.03 + 0.115 * math.sin(t0), 0.48),
                    p(c + 0.115 * math.cos(t1), z1 + 0.03 + 0.115 * math.sin(t1), 0.48),
                    0.035,
                    stone,
                    6,
                )

    # Exact mapped partition; interior partition walls have no facade openings.
    for vol in cfg["volumes"]:
        name = vol["name"]
        H = float(vol["height_m"]) - (2.0 if name in ["east", "west", "south"] else 0.0)
        main = name == "main"
        edges = vol["edges"]
        ext = [e for e in edges if e["exterior"] and math.dist(e["a"], e["b"]) > 0.2]
        if not ext:
            continue
        # North portal faces away from fitted dome center, on the northern front.
        front = max(ext, key=lambda e: math.dist(e["a"], e["b"]))
        # Main arcuate bays use continuous perimeter stationing across GIS seams.
        per = sum(math.dist(e["a"], e["b"]) for e in edges)
        pitch = per / max(1, round(per / 5.2))
        station = 0
        for e in edges:
            a, b = e["a"], e["b"]
            L = math.dist(a, b)
            if L < 0.001:
                continue
            holes = []
            cs = []
            portal = False
            if e["exterior"]:
                if main:
                    cs = [
                        (k + 0.5) * pitch - station
                        for k in range(math.ceil(per / pitch))
                        if station - 1.25 < (k + 0.5) * pitch < station + L + 1.25
                    ]
                    holes = (
                        [(c, 0.83, 2.3, 7.2, False, False) for c in cs]
                        + [(c, 1.02, 9.6, 14.6, True, False) for c in cs]
                        + [(c, 0.48, 18.6, 20.0, False, False) for c in cs]
                    )
                elif L > 4:
                    cs = (
                        [L / 2 - 2.6, L / 2, L / 2 + 2.6]
                        if name in ["north", "south"] and e == front
                        else ([L / 2] if L < 10 else [L / 2 - 3.0, L / 2, L / 2 + 3.0])
                    )
                    holes = [(c, 0.85, 9.5, 16.0, False, False) for c in cs]
                    if name == "north" and e == front and L > 6:
                        portal = True
                        holes.append((L / 2, 2.55, 0.15, 4.6, True, True))
                    elif name in ["east", "west"]:
                        # Observed portico arches, threshold position not surveyed.
                        holes.append((L / 2, 1.8, 1.0, 5.3, True, False))
            if main and not e["exterior"]:
                cs = [
                    (k + 0.5) * pitch - station
                    for k in range(math.ceil(per / pitch))
                    if station - 0.48 < (k + 0.5) * pitch < station + L + 0.48
                ]
                holes = [(c, 0.48, 18.6, 20.0, False, False) for c in cs]
            _, tx, ty, ang, p = aperture_edge(a, b, H, holes, e["exterior"])
            if main and not e["exterior"]:
                # Shared pavilion boundaries become exposed above their roofs.
                # Continue the upper frieze/cornice across these circular arcs.
                for z, h, d in [(20.6, 0.25, 0.42), (24.4, 0.22, 0.58), (24.75, 0.25, 0.82)]:
                    boxat(detail, p, L / 2, z, L, d, h, stone, ang, 0.05)
                boxat(detail, p, L / 2, 22.45, L, 0.035, 2.75, mosaic, ang, 0.025)
                for z in [21.05, 23.88]:
                    boxat(detail, p, L / 2, z, L, 0.12, 0.09, stone, ang, 0.10)
            if e["exterior"]:
                bands = (
                    [
                        (0.35, 0.35, 0.32),
                        (1.9, 0.18, 0.25),
                        (8.1, 0.28, 0.34),
                        (8.5, 0.20, 0.47),
                        (16.6, 0.24, 0.48),
                        (17.0, 0.28, 0.65),
                        (20.6, 0.25, 0.42),
                        (24.4, 0.22, 0.58),
                        (24.75, 0.25, 0.82),
                    ]
                    if main
                    else [
                        (0.35, 0.35, 0.32),
                        (8.1, 0.3, 0.50),
                        (8.5, 0.2, 0.65),
                        (H - 0.55, 0.24, 0.5),
                        (H - 0.20, 0.20, 0.8),
                    ]
                )
                for z, h, d in bands:
                    if portal and z < 1.0:
                        side = (L - 5.1) / 2
                        for u in [side / 2, L - side / 2]:
                            boxat(detail, p, u, z, side, d, h, stone, ang, 0.05)
                    else:
                        boxat(detail, p, L / 2, z, L, d, h, stone, ang, 0.05)
                if main:
                    boxat(detail, p, L / 2, 22.45, L, 0.035, 2.75, mosaic, ang, 0.025)
                    # Frieze field stays undecorated where exact mosaic is unresolved.
                    for z in [21.05, 23.88]:
                        boxat(detail, p, L / 2, z, L, 0.12, 0.09, stone, ang, 0.10)
                for c in cs:
                    if not 0.12 < c < L - 0.12:
                        continue
                    if main or not (name in ["north", "south"] and e == front):
                        for u in [c - 1.55, c + 1.55]:
                            pilaster(p, u, 9.05, 16.05, ang)
                    if main:
                        for r, out, th in [
                            (1.02, 0.12, 0.14),
                            (1.19, 0.19, 0.10),
                            (1.32, 0.12, 0.08),
                        ]:
                            arch(detail, p, c, r, 9.6, 14.6, stone, out, th)
                        boxat(detail, p, c, 15.75, 0.29, 0.37, 0.40, stone, ang, 0.2)
                    for z in [2.3, 7.2, 9.6, 12.3, 18.6, 20.0] if main else [9.5, 12.5, 16.0]:
                        boxat(
                            detail,
                            p,
                            c,
                            z,
                            1.7 if z < 8 else (1.0 if z > 18 else 2.0),
                            0.13,
                            0.10,
                            stone,
                            ang,
                            -0.21,
                        )
                    boxat(detail, p, c, 12.25, 0.08, 0.12, 5.35, metal, ang, -0.22)
                    if main:
                        boxat(detail, p, c, 4.75, 0.08, 0.12, 4.8, metal, ang, -0.22)
                if name in ["north", "south"] and e == front:
                    for u in [L / 2 - 4.0, L / 2 - 1.3, L / 2 + 1.3, L / 2 + 4.0]:
                        pilaster(p, u, 9.05, 16.05, ang, 0.55)
                    if name == "south":
                        # Photograph supports blind lower niches, not an invented
                        # doorway where the monument occludes the threshold.
                        for c in [L / 2 - 2.6, L / 2 + 2.6]:
                            boxat(detail, p, c, 4.3, 1.1, 0.025, 3.1, shadow, ang, 0.04)
                            for u in [c - 0.70, c + 0.70]:
                                pilaster(p, u, 2.55, 6.0, ang, 0.23)
                            boxat(detail, p, c, 2.55, 1.6, 0.35, 0.18, stone, ang, 0.16)
                            pts = [
                                p(c - 0.88, 6.25, 0.25),
                                p(c + 0.88, 6.25, 0.25),
                                p(c, 6.8, 0.25),
                            ]
                            face(detail, pts, stone)
                            for j in range(3):
                                detail.beam(pts[j], pts[(j + 1) % 3], 0.055, stone, 6)
                # Balusters are individual turned solids, not a flat fence texture.
                rz = 17.35 if main else H + 0.1
                for z in [] if name in ["south", "east", "west"] and e == front else [rz, rz + 1.0]:
                    boxat(rail, p, L / 2, z, L, 0.33, 0.16, stone, ang, 0.23)
                for j in range(
                    0 if name in ["south", "east", "west"] and e == front else max(1, int(L / 0.48))
                ):
                    u = (j + 0.5) * L / max(1, int(L / 0.48))
                    x, y, z = p(u, rz + 0.08, 0.23)
                    rail.lathe(
                        x,
                        y,
                        z,
                        [
                            (0.10, 0),
                            (0.10, 0.10),
                            (0.065, 0.17),
                            (0.12, 0.31),
                            (0.12, 0.40),
                            (0.07, 0.62),
                            (0.065, 0.70),
                            (0.10, 0.77),
                            (0.10, 0.84),
                        ],
                        stone,
                        10,
                    )
                for j in range(max(1, int(L / 0.42))):
                    boxat(
                        detail,
                        p,
                        (j + 0.5) * L / max(1, int(L / 0.42)),
                        16.88 if main else H - 0.3,
                        0.16,
                        0.34,
                        0.18,
                        stone,
                        ang,
                        0.29,
                    )
                if portal:
                    c = L / 2
                    for rr, out, th in [(2.55, 0.15, 0.27), (2.86, 0.23, 0.12)]:
                        arch(entry, p, c, rr, 0.15, 4.6, stone, out, th)
                    for u in [c - 2.85, c + 2.85]:
                        pilaster(p, u, 0.4, 7.7, ang, 0.85)
                    # Recessed modern door leaves within the larger arched portico.
                    # Two leaves plus fixed sidelights; landing/approach stay bounded.
                    for u in [c - 1.10, c, c + 1.10]:
                        boxat(entry, p, u, 1.55, 0.07, 0.10, 2.8, metal, ang, -0.60)
                    boxat(entry, p, c, 2.95, 4.7, 0.10, 0.09, metal, ang, -0.60)
                    # Concentric fanlight frame and radial spokes, visible in
                    # the north photograph, stay within the recessed arch.
                    for rr in [1.45, 2.46]:
                        for j in range(32):
                            entry.beam(
                                p(
                                    c + rr * math.cos(j * math.pi / 32),
                                    4.6 + rr * math.sin(j * math.pi / 32),
                                    -0.60,
                                ),
                                p(
                                    c + rr * math.cos((j + 1) * math.pi / 32),
                                    4.6 + rr * math.sin((j + 1) * math.pi / 32),
                                    -0.60,
                                ),
                                0.035,
                                metal,
                                6,
                            )
                    for j in range(1, 8):
                        t = j * math.pi / 8
                        entry.beam(
                            p(c + 1.45 * math.cos(t), 4.6 + 1.45 * math.sin(t), -0.60),
                            p(c + 2.46 * math.cos(t), 4.6 + 2.46 * math.sin(t), -0.60),
                            0.032,
                            metal,
                            6,
                        )
                    boxat(entry, p, c, 4.6, 5.0, 0.09, 0.065, metal, ang, -0.60)
                    for side in [-1, 1]:
                        entry.beam(
                            p(c + side * 0.14, 1.18, -0.54),
                            p(c + side * 0.14, 1.75, -0.54),
                            0.028,
                            metal,
                            8,
                        )
                    for out, top, depth in [(-0.20, 0.15, 1.20), (0.70, 0.075, 0.60)]:
                        boxat(entry, p, c, top / 2, 5.4, depth, top, stone, ang, out)
                    for side in [-1, 1]:
                        entrances.append(
                            {
                                "name": "North portico " + ("left" if side < 0 else "right"),
                                "threshold_xyz": list(p(c + side * 0.55, 0.15)),
                                "outward_normal": [ty, -tx, 0.0],
                                "clear_width_m": 1.03,
                                "door_leaf_depth_m": 0.65,
                                "status": "visually estimated from north view and Door6 detail; not surveyed",
                            }
                        )
            station += L
        wall.surface(vol["geometry"], base, brick)
        # Upper surfaces preserve every mapped partition. Pavilion roof rise is
        # two metres from OSM; north is a flat balustraded portico in photograph.
        if main or name == "north":
            roofs.surface(vol["geometry"], base + H, metal)
        else:
            a, b = front["a"], front["b"]
            L, tx, ty, ang, p = oriented(a, b)
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            maxu = max(
                abs((x - cx) * tx + (y - cy) * ty)
                for part in vol["geometry"]
                for x, y in part["outer"]
            )

            def uz(pt):
                return (pt[0] - cx) * tx + (pt[1] - cy) * ty

            def rz(pt):
                return H + 2.0 * (1.0 - abs(uz(pt)) / maxu)

            def clip(poly, s):
                out = []
                for v, w in zip(poly, poly[1:] + poly[:1]):
                    q, r = s * uz(v), s * uz(w)
                    if q >= -1e-8:
                        out.append(v)
                    if q * r < -1e-12:
                        t = q / (q - r)
                        out.append(tuple(v[i] + t * (w[i] - v[i]) for i in range(2)))
                return out

            for part in vol["geometry"]:
                for tri in part["triangles"]:
                    for s in [-1, 1]:
                        face(roofs, [(x, y, base + rz((x, y))) for x, y in clip(tri, s)], metal)
                for ring in [part["outer"]] + part.get("holes", []):
                    for q, r in zip(ring, ring[1:] + ring[:1]):
                        for s in [-1, 1]:
                            chain = clip([q, r], s)
                            if len(chain) >= 2:
                                q1, r1 = chain[0], chain[1]
                                face(
                                    roofs,
                                    [
                                        (q1[0], q1[1], base + H),
                                        (r1[0], r1[1], base + H),
                                        (r1[0], r1[1], base + rz(r1)),
                                        (q1[0], q1[1], base + rz(q1)),
                                    ],
                                    brick,
                                )
            if name == "south":
                half = min(maxu, 7.3)
                pts = [p(L / 2 - half, H, 0.48), p(L / 2 + half, H, 0.48), p(L / 2, H + 2, 0.48)]
                face(detail, pts, blue)
                for j in range(3):
                    detail.beam(pts[j], pts[(j + 1) % 3], 0.17, stone, 8)
    # Source-mapped smaller drum and dome ellipse, not parent bounding box.
    ellipse = cfg["dome_ellipse"]
    cx, cy = ellipse["center"]
    ax, ay = ellipse["axes"]
    rx, ry = ellipse["radii"]

    def ep(t, r, z):
        return (
            cx + r * (rx * ax[0] * math.cos(t) + ry * ay[0] * math.sin(t)),
            cy + r * (rx * ax[1] * math.cos(t) + ry * ay[1] * math.sin(t)),
            base + z,
        )

    n = 192

    def skin(r0, z0, r1, z1, mat):
        for j in range(n):
            face(
                dome,
                [
                    ep(j * math.tau / n, r0, z0),
                    ep((j + 1) * math.tau / n, r0, z0),
                    ep((j + 1) * math.tau / n, r1, z1),
                    ep(j * math.tau / n, r1, z1),
                ],
                mat,
            )

    skin(1.0, 25.0, 1.0, 30.0, brick)
    for z, r in [(25.15, 1.008), (28.75, 1.012), (29.2, 1.025), (29.65, 1.03)]:
        skin(r, z, r, z + 0.2, stone)
    limit = math.acos(0.14)
    profile = [
        (math.cos(limit * j / 24), 30.0 + 13.8 * math.sin(limit * j / 24) / math.sin(limit))
        for j in range(25)
    ]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        skin(r0, z0, r1, z1, roofglass)
    # Dense radial glazing bars plus heavier principal ribs, with horizontal
    # pane divisions: their count and section are visually estimated.
    for j in range(n):
        t = j * math.tau / n
        for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
            dome.beam(
                ep(t, r0, z0 + 0.045), ep(t, r1, z1 + 0.045), 0.055 if j % 8 else 0.105, metal, 6
            )
    for r, z in profile:
        for j in range(n):
            dome.beam(
                ep(j * math.tau / n, r, z + 0.04),
                ep((j + 1) * math.tau / n, r, z + 0.04),
                0.038,
                metal,
                6,
            )
    # The photographs show a ring of pale triangular ventilator pediments
    # high on the dome, aligned with primary ribs; count remains estimated.
    for j in range(24):
        t = j * math.tau / 24
        c = ep(t, 0.57, 41.45)
        tangent = (
            -rx * ax[0] * math.sin(t) + ry * ay[0] * math.cos(t),
            -rx * ax[1] * math.sin(t) + ry * ay[1] * math.cos(t),
        )
        le = math.hypot(*tangent)
        u = (tangent[0] / le, tangent[1] / le)
        A = (c[0] - u[0] * 1.45, c[1] - u[1] * 1.45, c[2])
        B = (c[0] + u[0] * 1.45, c[1] + u[1] * 1.45, c[2])
        C = (c[0], c[1], c[2] + 1.05)
        D = ep(t, 0.46, 42.45)
        for vs in [[A, B, C], [A, C, D], [C, B, D], [A, D, B]]:
            face(dome, vs, metal)
        for q, r in [(A, B), (A, C), (C, B)]:
            dome.beam(q, r, 0.10, stone, 8)
    for j in range(24):
        t = j * math.tau / 24
        dome.beam(ep(t, 1.012, 25.2), ep(t, 1.012, 29.5), 0.12, stone, 8)
    skin(0.14, 43.0, 0.14, 45.3, glass)
    skin(0.14, 45.3, 0.045, 46.6, metal)
    face(dome, [ep(j * math.tau / n, 0.045, 46.6) for j in range(n)], metal)
    for j in range(48):
        t = j * math.tau / 48
        dome.beam(ep(t, 0.14, 43.8), ep(t, 0.14, 45.3), 0.045, metal, 6)
    for z in [43.8, 44.6, 45.3]:
        for j in range(n):
            dome.beam(
                ep(j * math.tau / n, 0.141, z),
                ep((j + 1) * math.tau / n, 0.141, z),
                0.045,
                metal,
                6,
            )
    # Mapped entrance canopies retained as thin roofs, supported at their
    # outer corners. They are not opaque four-metre infill blocks.
    for canopy in cfg.get("canopies", []):
        for part in canopy["geometry"]:
            roofs.surface([part], base + canopy["height_m"], metal)
            for q in part["outer"][:: max(1, len(part["outer"]) // 4)]:
                roofs.beam(
                    (q[0], q[1], base), (q[0], q[1], base + canopy["height_m"]), 0.07, metal, 8
                )
    created = [m.done().name for m in meshes.values() if m.v]
    return {
        "created": created,
        "parameters": {
            "wall_height_m": 25.0,
            "roof_top_m": 46.6,
            "dome_top_m": 43.8,
            "source_part_partition": True,
            "roof_style": "mapped fitted ellipse, raised brick drum, glazed curved dome with radial and transverse framing",
            "window_openings": "polygonal circular heads with actual subtraction and solid reveals",
            "detail_status": "specific architectural components improved; exact mosaic and figurative sculpture unresolved",
        },
        "interfaces": {"entrances": entrances},
        "uncertainty": [
            "Source-tagged part heights and mapped outlines are not surveyed. Dome ellipse is fitted to mapped dome part; intermediate curvature and glazing-bar count are estimated.",
            "Facade bay spacing, minor profile dimensions, balcony balusters and capitals are visually interpreted, not measured. Exact frieze mosaic tesserae, lettering and figurative sculptures remain unresolved.",
            "North portico door widths/threshold and side-portico composition are estimated from licensed views; south threshold is still occluded and has no fabricated interface.",
            "Pavilion gable axes and roof pitches are estimated from mapped projections and oblique images. These improvements do not establish full Imperial Phase4-equivalent fidelity.",
        ],
        "evidence_source_ids": list(
            dict.fromkeys(feature.get("evidence_source_ids", []) + SOURCES)
        ),
    }
