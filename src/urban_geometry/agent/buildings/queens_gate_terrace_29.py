"""29 Queen's Gate Terrace: parent/linked part remain separate inventory footprints."""

import math


def build(ctx, feature):
    fid = feature["id"]
    assert fid in ("way-213454222", "way-809947753")
    main = fid == "way-809947753"
    base = float(feature.get("base_m", 0))
    plaster = ctx.material("QGT29 estimated pale stucco", (0.73, 0.71, 0.65), 0.86)
    trim = ctx.material("QGT29 estimated stone dressings", (0.79, 0.77, 0.71), 0.72)
    slate = ctx.material("QGT29 estimated dark roof", (0.12, 0.14, 0.15), 0.84)
    glass = ctx.material("QGT29 estimated glass", (0.14, 0.20, 0.22), 0.2, 0, 0.28)
    timber = ctx.material("QGT29 estimated timber door", (0.09, 0.045, 0.027), 0.69)
    stone = ctx.material("QGT29 estimated threshold", (0.52, 0.50, 0.45), 0.87)
    wall = ctx.mesh("mapped envelope with real apertures")
    roof = ctx.mesh("EA height roof")
    win = ctx.mesh("estimated sash frames")
    detail = ctx.mesh("estimated cornice")
    entry = ctx.mesh("front porch door and approach")
    entrances = []
    for pi, part in enumerate(feature["geometry"]):
        ring = part["outer"]
        height = 26.4 if main else (4.0 if pi == 0 else 13.6)
        roof.surface([part], base + height, slate)
        roof.surface([part], base, plaster)
        for ei, (A, B) in enumerate(zip(ring, ring[1:] + ring[:1])):
            ll = math.dist(A, B)
            tx, ty = (B[0] - A[0]) / ll, (B[1] - A[1]) / ll
            nx, ny = ty, -tx

            def p(s, d, z):
                return (A[0] + tx * s + nx * d, A[1] + ty * s + ny * d, base + z)

            def bx(m, s, d, z, w, dep, h, mat):
                m.box(*p(s, d, z), w, dep, h, mat, math.atan2(ty, tx))

            # Main front behind porch starts above its roof. All other shared edges blank.
            zmin = 4.0 if main and ei == 7 else (13.6 if main and ei in [1, 2] else 0)
            if not main and ((pi == 0 and ei == 1) or (pi == 1 and ei in [1, 2, 3])):
                continue
            aps = []
            if main and ei in [6, 7]:
                for k in range(2 if ei == 6 else 1):
                    c = ll * (k + 0.5) / (2 if ei == 6 else 1)
                    for row, lo in enumerate([1.0, 5.25, 9.55, 13.85, 18.15]):
                        if lo < zmin:
                            continue
                        aps.append((c - 0.60, c + 0.60, lo, lo + 2.65, False))
            elif main and ei == 4:
                for lo in [11.3, 15.5, 19.7]:
                    aps.append((ll / 2 - 0.52, ll / 2 + 0.52, lo, lo + 2.1, False))
            elif not main and pi == 0 and ei == 3:
                aps = [(ll / 2 - 0.79, ll / 2 + 0.79, 0.45, 3.25, True)]
            elif not main and pi == 1 and ei == 4:
                for k in range(2):
                    for lo in [1.2, 4.5, 7.7]:
                        c = ll * (k + 0.5) / 2
                        aps.append((c - 0.55, c + 0.55, lo, lo + 1.8, False))
            xs = sorted(set([0, ll] + [q for op in aps for q in op[:2]]))
            for l, r in zip(xs, xs[1:]):
                z = zmin
                for op in sorted(
                    [op for op in aps if op[0] < (l + r) / 2 < op[1]], key=lambda q: q[2]
                ):
                    if op[2] > z:
                        wall.face([p(l, 0, z), p(r, 0, z), p(r, 0, op[2]), p(l, 0, op[2])], plaster)
                    z = op[3]
                if height > z:
                    wall.face([p(l, 0, z), p(r, 0, z), p(r, 0, height), p(l, 0, height)], plaster)
            for l, r, lo, hi, door in aps:
                c = (l + r) / 2
                w = r - l
                d = 0.43 if door else 0.22
                bx(
                    entry if door else win,
                    c,
                    -d,
                    (lo + hi) / 2,
                    w,
                    0.06,
                    hi - lo,
                    timber if door else glass,
                )
                for ss in [l, r]:
                    wall.face([p(ss, 0, lo), p(ss, -d, lo), p(ss, -d, hi), p(ss, 0, hi)], trim)
                for zz in [lo, hi]:
                    wall.face([p(l, 0, zz), p(r, 0, zz), p(r, -d, zz), p(l, -d, zz)], trim)
                for ss in [l - 0.055, r + 0.055]:
                    bx(win, ss, 0.005, (lo + hi) / 2, 0.11, 0.16, hi - lo + 0.14, trim)
                bx(win, c, 0.035, hi + 0.08, w + 0.26, 0.24, 0.16, trim)
                if not door:
                    bx(win, c, 0.04, lo - 0.07, w + 0.28, 0.26, 0.14, trim)
                    bx(win, c, -d + 0.05, (lo + hi) / 2, 0.045, 0.05, hi - lo, trim)
                    bx(win, c, -d + 0.05, (lo + hi) / 2, w, 0.05, 0.05, trim)
                else:
                    bx(entry, c, 0.31, 0.225, w + 0.25, 0.94, 0.45, stone)
                    bx(entry, c, 0.93, 0.15, w + 0.25, 0.30, 0.30, stone)
                    bx(entry, c, 1.23, 0.075, w + 0.25, 0.30, 0.15, stone)
                    for ss in [l - 0.24, r + 0.24]:
                        bx(detail, ss, 0.10, 1.75, 0.20, 0.25, 3.5, trim)
                    entrances.append(
                        {
                            "name": "29 Terrace estimated porch entrance",
                            "threshold_xyz": p(c, 0, 0.45),
                            "outward_normal": [nx, ny, 0],
                            "clear_width_m": 1.4,
                            "door_leaf_xyz": p(c, -0.43, 1.85),
                            "door_leaf_depth_m": 0.4,
                            "estimated": True,
                            "supporting_surface": "authored landing .45m and three .15m rises",
                        }
                    )
            if (main and ei in [6, 7]) or (not main and pi == 0 and ei == 3):
                for z in [4.65, 8.95, 13.25, 17.55, 22.8, 24.25] if main else [3.83]:
                    bx(detail, ll / 2, 0.02, z, ll, 0.18, 0.18, trim)
    obs = [m.done() for m in [wall, roof, win, detail, entry]]
    return {
        "created": [o.name for o in obs if o],
        "parameters": {
            "main_roof_m": 26.4,
            "rear_annexe_m": 13.6,
            "porch_m": 4.0,
            "full_inventory_footprint": True,
            "inventory_id": fid,
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": ["ea-lidar-composite-2022-tq27ne", "va-praefcke-aerial-a-2011"],
        "uncertainty": [
            "OSM explicitly links part809947753 with parent213454222; module branches preserve both original geometries.",
            "EA native1m whole footprint63inset samples median24.568/p9526.420; main26.4 rear13.6; flat roof simplified, small pitch unverified; rear mostly13–14m returns simplified to13.6m.",
            "No licensed target facade photograph. Three-bay five-level stucco, sash count, materials, porch4m, door and three steps are editable low-confidence estimates, not measured survey.",
            "Party walls blank; rear exposed apertures estimated. No interior or fine sculptural detail.",
        ],
    }
