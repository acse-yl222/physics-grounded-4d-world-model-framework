"""Modest procedural exterior baseline. OSM plans; estimated facades explicitly labelled."""

import math, hashlib


def build(ctx, feature):
    parts = feature["geometry"]
    dp = feature.get("detail_parameters", {})
    h = float(dp.get("height_m", feature["height_m"]))
    base = float(feature.get("base_m", 0))
    levels = max(1, int(dp.get("levels", feature["levels"])))
    # OSM levels count from ground; elevated parts only contain the remaining storeys.
    levels = max(1, min(levels, round((h - base) / 3.15)))
    seed = int(hashlib.sha256(feature["id"].encode()).hexdigest()[:8], 16)
    palettes = [
        (0.55, 0.40, 0.30),
        (0.65, 0.57, 0.44),
        (0.68, 0.65, 0.57),
        (0.46, 0.27, 0.18),
        (0.56, 0.49, 0.40),
        (0.72, 0.70, 0.64),
    ]
    color = dp.get("color", palettes[seed % len(palettes)])
    wall = ctx.material("urban masonry " + str(seed % len(palettes)), color, 0.87)
    trim = ctx.material("limestone trim", (0.71, 0.68, 0.59), 0.8)
    glass = ctx.material("recessed blue grey glazing", (0.08, 0.145, 0.19), 0.27, 0.25)
    roof = ctx.material("slate grey roof", (0.17, 0.20, 0.22), 0.82)
    door = ctx.material("painted entrance", (0.11, 0.15, 0.15), 0.65)
    m = ctx.mesh(feature["id"] + " exterior")
    floor = (h - base) / levels
    edges = feature.get("facade_edges", [])
    eligible = [
        e
        for e in edges
        if e.get("neighbor_height_m", 0) <= base + 0.1 and math.dist(e["a"], e["b"]) > 3
    ]
    entrance = (
        max(eligible, key=lambda e: math.dist(e["a"], e["b"]))
        if eligible and h - base > 4 and base < 0.1
        else None
    )
    entrance_bay = None
    if "entrance_override" in dp:
        override = dp["entrance_override"]
        entrance = edges[override["edge_index"]] if override is not None else None
        entrance_bay = override["bay_index"] if override is not None else None
    windows = 0
    entries = []
    for e in edges:
        a, b = e["a"], e["b"]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.03:
            continue
        tx, ty = dx / L, dy / L
        nx, ny = ty, -tx
        angle = math.atan2(dy, dx)
        low = max(base, e.get("wall_start_m", base))
        adj = e.get("neighbor_height_m", 0)

        def p(s, z, d=0):
            return (a[0] + s * tx + d * nx, a[1] + s * ty + d * ny, z)

        def rect(s0, s1, z0, z1, mat=wall, d=0):
            if s1 - s0 > 0.001 and z1 - z0 > 0.001:
                m.face([p(s0, z0, d), p(s1, z0, d), p(s1, z1, d), p(s0, z1, d)], mat)

        if low >= h - 0.001:
            continue
        n = int(L / float(dp.get("window_spacing", 3.3)))
        if n < 1 or h - base < 4:
            rect(0, L, low, h)
            continue
        spacing = L / n
        width = min(1.35, spacing * 0.46)
        wh = min(1.65, floor * 0.53)
        # Wall is tessellated around true openings, with recessed glazing and visible reveals.
        for level in range(levels):
            f0 = base + level * floor
            f1 = base + (level + 1) * floor
            bottom = max(f0, low)
            if bottom >= f1:
                continue
            if f0 < adj - 0.05:
                rect(0, L, bottom, f1)
                continue
            for k in range(n):
                s0 = k * spacing
                s1 = (k + 1) * spacing
                c = (s0 + s1) / 2
                isdoor = (
                    e is entrance
                    and level == 0
                    and k == (n // 2 if entrance_bay is None else entrance_bay)
                )
                ww = 1.05 if isdoor else width
                z0 = base if isdoor else f0 + floor * 0.24
                z1 = min(f1 - 0.25, z0 + (2.3 if isdoor else wh))
                if z0 < bottom - 0.01 or z1 <= z0:
                    rect(s0, s1, bottom, f1)
                    continue
                l, r = c - ww / 2, c + ww / 2
                rect(s0, l, bottom, f1)
                rect(r, s1, bottom, f1)
                rect(l, r, bottom, z0)
                rect(l, r, z1, f1)
                depth = -0.16
                m.face([p(l, z0), p(l, z1), p(l, z1, depth), p(l, z0, depth)], trim)
                m.face([p(r, z1), p(r, z0), p(r, z0, depth), p(r, z1, depth)], trim)
                m.face([p(l, z1), p(r, z1), p(r, z1, depth), p(l, z1, depth)], trim)
                m.face([p(r, z0), p(l, z0), p(l, z0, depth), p(r, z0, depth)], trim)
                rect(l, r, z0, z1, door if isdoor else glass, depth)
                fw = 0.075
                rect(l - fw, l, z0 - fw, z1 + fw, trim, 0.035)
                rect(r, r + fw, z0 - fw, z1 + fw, trim, 0.035)
                rect(l, r, z1, z1 + fw, trim, 0.035)
                if not isdoor:
                    rect(l, r, z0 - fw, z0, trim, 0.035)
                    rect(c - 0.03, c + 0.03, z0, z1, trim, -0.12)
                    rect(l, r, (z0 + z1) / 2 - 0.025, (z0 + z1) / 2 + 0.025, trim, -0.12)
                    windows += 1
                else:
                    entries.append(
                        {
                            "threshold_xyz": p(c, base),
                            "outward_normal": [nx, ny, 0],
                            "clear_width_m": ww,
                            "door_leaf_depth_m": 0.16,
                            "support_z": base,
                            "basis": "artistic estimate; closed leaf",
                        }
                    )
        # Cornice is above openings; no threshold obstruction.
        if adj < h - 0.1:
            m.box(
                (a[0] + b[0]) / 2 + nx * 0.035,
                (a[1] + b[1]) / 2 + ny * 0.035,
                h - 0.12,
                L,
                0.22,
                0.22,
                trim,
                angle,
            )
            m.box((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, h + 0.18, L, 0.19, 0.36, wall, angle)
    m.surface(parts, h, roof)
    for part in parts:
        for tri in part["triangles"]:
            m.face([(x, y, base) for x, y in reversed(tri)], wall)
    obj = m.done()
    obj["geometry_fidelity"] = "OSM footprint; procedural facade baseline"
    obj["height_basis"] = feature["height_basis"]
    obj["osm_id"] = feature["id"]
    obj["estimated_window_count"] = windows
    return {
        "created": [obj.name],
        "parameters": {
            "height_m": h,
            "levels": levels,
            "windows": windows,
            "height_basis": feature["height_basis"],
        },
        "interfaces": {"entrances": entries},
        "uncertainty": [
            "Generic facade rhythm and materials are artistic estimates, not building-specific image reconstruction.",
            "Flat roof with parapet is a schematic baseline where no roof evidence was reviewed.",
            "Local flat ground; no basements/interiors.",
        ],
        "evidence_source_ids": feature["evidence_source_ids"],
    }
