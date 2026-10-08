"""28 Jay Mews: source-identified historic chapel entrance and EA low roof.
Full original outline, editable primary joinery; hidden upper facade estimated.
"""

import math


def build(ctx, feature):
    stucco = ctx.material("28 Jay Mews pale cream stucco", (0.76, 0.735, 0.66), 0.85)
    trim = ctx.material("28 Jay Mews light cornice", (0.83, 0.80, 0.72), 0.78)
    wood = ctx.material("28 Jay Mews historic warm timber door", (0.29, 0.105, 0.035), 0.60)
    timber = ctx.material("28 Jay Mews white painted timber", (0.79, 0.79, 0.73), 0.63)
    roofmat = ctx.material("28 Jay Mews grey flat roof", (0.22, 0.235, 0.23), 0.90)
    glass = ctx.material("28 Jay Mews recessed glazing", (0.12, 0.19, 0.20), 0.20, 0, 0.24)
    metal = ctx.material("28 Jay Mews dark door hardware", (0.035, 0.04, 0.038), 0.46, 0.60)
    wall = ctx.mesh("Full mapped shell real east openings")
    roof = ctx.mesh("EA low flat roof")
    detail = ctx.mesh("Mews joinery and restrained cornices")
    entry = ctx.mesh("Estimated pedestrian leaf and finite threshold")
    ring = feature["geometry"][0]["outer"]
    base = feature.get("base_m", 0)
    H = 8.16
    entrances = []
    count = 0

    def face(m, ps, mat):
        for i in range(1, len(ps) - 1):
            m.face([ps[0], ps[i], ps[i + 1]], mat)

    for tri in feature["geometry"][0]["triangles"]:
        face(roof, [(x, y, base + H) for x, y in tri], roofmat)
        face(wall, [(x, y, base) for x, y in reversed(tri)], stucco)
    for ei, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        L = math.dist(a, b)
        tx = (b[0] - a[0]) / L
        ty = (b[1] - a[1]) / L
        nx, ny = ty, -tx
        angle = math.atan2(ty, tx)

        def p(s, z, dep=0):
            return (a[0] + tx * s - nx * dep, a[1] + ty * s - ny * dep, base + z)

        def box(m, s, z, w, h, mat, dep=-0.04, depth=0.16):
            m.box(*p(s, z, dep), w, depth, h, mat, angle)

        holes = []
        if ei == 3:
            # Exposed Jay Mews side. Exact bay spacing and pedestrian leaf are estimates.
            holes = [
                (0.35, 3.50, 0.10, 3.60, "garage"),
                (3.65, 4.70, 0.10, 3.60, "service"),
                (5.50, 6.75, 0.10, 2.50, "entry"),
                (4.85, L - 0.20, 2.75, 3.60, "transom"),
            ]
            for c in [L * 0.27, L * 0.72]:
                holes.append((c - 0.75, c + 0.75, 5.05, 6.85, "window"))
        zcuts = sorted(set([0, H] + [h[j] for h in holes for j in [2, 3]]))
        for lo, hi in zip(zcuts, zcuts[1:]):
            intervals = sorted((h[0], h[1]) for h in holes if h[2] <= lo and h[3] >= hi)
            cursor = 0
            for le, ri in intervals + [(L, L)]:
                if le > cursor + 1e-8:
                    face(
                        wall,
                        [p(cursor, lo), p(le, lo), p(le, hi), p(cursor, hi)],
                        timber if ei == 3 and hi <= 3.60 else stucco,
                    )
                cursor = max(cursor, ri)
        for le, ri, lo, hi, kind in holes:
            count += 1
            c = (le + ri) / 2
            w = ri - le
            dep = 0.45 if kind in ["entry", "service"] else 0.27
            for q, r in [
                ((le, lo), (ri, lo)),
                ((ri, lo), (ri, hi)),
                ((ri, hi), (le, hi)),
                ((le, hi), (le, lo)),
            ]:
                face(wall, [p(*q), p(*r), p(*r, dep), p(*q, dep)], trim)
            for s in [le, ri]:
                box(detail, s, (lo + hi) / 2, 0.075, hi - lo, timber, 0.07, 0.14)
            box(detail, c, hi, w, 0.08, timber, 0.07, 0.14)
            if kind in ["window", "transom"]:
                face(wall, [p(le, lo, dep), p(ri, lo, dep), p(ri, hi, dep), p(le, hi, dep)], glass)
                box(detail, c, lo, w + 0.15, 0.10, trim, -0.07, 0.25)
                box(detail, c, (lo + hi) / 2, 0.06, hi - lo, timber, 0.13, 0.10)
                box(detail, c, (lo + hi) / 2, w, 0.065, timber, 0.13, 0.10)
            elif kind == "garage":
                face(
                    detail,
                    [p(le, lo, dep), p(ri, lo, dep), p(ri, 2.52, dep), p(le, 2.52, dep)],
                    timber,
                )
                face(
                    detail,
                    [p(le, 2.52, dep), p(ri, 2.52, dep), p(ri, hi, dep), p(le, hi, dep)],
                    glass,
                )
                for k in range(1, 12):
                    box(detail, le + w * k / 12, 1.31, 0.018, 2.42, trim, dep - 0.025, 0.028)
                for s in [le, c, ri]:
                    box(detail, s, (lo + hi) / 2, 0.075, hi - lo, timber, dep - 0.03, 0.08)
                box(detail, c, 2.52, w, 0.075, timber, dep - 0.03, 0.08)
                for k in [1, 2, 3]:
                    box(
                        detail,
                        le + w * k / 4,
                        (2.52 + hi) / 2,
                        0.045,
                        hi - 2.52,
                        timber,
                        dep - 0.03,
                        0.08,
                    )
                box(detail, c, 1.20, 0.08, 0.20, metal, dep - 0.075, 0.06)
            else:
                leafmat = wood if kind == "entry" else timber
                box(entry, c, (lo + hi) / 2, w, hi - lo, leafmat, dep, 0.07)
                for s in [le + 0.10, c, ri - 0.10]:
                    box(entry, s, 1.25, 0.035, 2.08, leafmat, dep - 0.05, 0.035)
                for z in [0.23, 0.88, 1.53, 2.30]:
                    box(entry, c, z, w - 0.18, 0.04, leafmat, dep - 0.05, 0.035)
                if kind == "service":
                    box(entry, c, 3.25, w - 0.16, 0.53, glass, dep - 0.043, 0.015)
                if kind == "entry":
                    box(detail, c, 2.68, w + 0.25, 0.28, trim, -0.035, 0.14)
                    box(detail, c, 2.69, 0.025, 0.17, metal, -0.115, 0.02)
                    box(detail, c, 2.72, 0.11, 0.025, metal, -0.115, 0.02)
                entry.beam(
                    p(ri - 0.20, 0.98, dep - 0.08), p(ri - 0.20, 1.20, dep - 0.08), 0.018, metal, 8
                )
                box(entry, c, 0.05, w + 0.30, 0.10, trim, -0.28, 0.75)
                entrances.append(
                    {
                        "name": "28 Jay Mews "
                        + (
                            "historic timber chapel leaf"
                            if kind == "entry"
                            else "number28 white service leaf"
                        ),
                        "threshold_xyz": list(p(c, 0.10)),
                        "outward_normal": [nx, ny, 0],
                        "clear_width_m": w - 0.16,
                        "door_leaf_xyz": list(p(c, (lo + hi) / 2, dep)),
                        "door_leaf_depth_m": dep,
                        "landing_depth_m": 0.75,
                        "landing_z_m": 0.10,
                        "supporting_surface": "finite .10m stone threshold; street seam requires master coordination",
                        "estimated": True,
                    }
                )
        if ei == 3:
            for z, wdepth, h in [
                (3.82, 0.18, 0.16),
                (7.77, 0.20, 0.12),
                (8.0, 0.34, 0.20),
                (8.23, 0.40, 0.12),
            ]:
                box(detail, L / 2, z, L, h, trim, -0.035, wdepth)
            # Low parapet, top8.34m, within mapped roof boundary.
            box(detail, L / 2, 8.20, L, 0.28, stucco, 0.13, 0.26)
    objs = [m.done() for m in [wall, roof, detail, entry]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof_height_m": 8.16,
            "maximum_parapet_m": 8.34,
            "levels_estimated": 2,
            "true_openings": count,
            "mapped_outline_preserved": True,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "jay28-maggie-jones-church-2008",
        ],
        "uncertainty": [
            "2008 photograph positively identifies number28 and shows white glazed carriage doors, white service leaf and adjacent warm timber chapel door. Positions within mapped east facade and all dimensions estimated.",
            "Upper floor windows and flat roof edge are reduced estimates; photograph crops above ground-level transoms. EA2022 median8.164m supports low roof; isolated taller returns unresolved, no plant invented.",
            "Door upper ornate glazing, lettering and fine religious carving simplified to panel rails and a small cross marker; no photographic textures copied.",
            "2008 doorway predates2023–25 nearby church redevelopment. Present appearance unverified; source epoch explicitly retained.",
            "North shared with26, west and south adjoining walls kept blank. No adjacent26 or mansion footprint included.",
            "PBR optics are approximate constant materials, not calibrated measurements.",
        ],
    }
