"""Frayling: complete mapped outline, stepped flat roofs and estimated garden atrium.
Authoring UTM only; offline licensed-evidence partition data embedded below.
"""

import math


def build(ctx, feature):
    brick = ctx.material("Frayling dark brown brick", (0.24, 0.205, 0.175), 0.88)
    concrete = ctx.material("Frayling grey exposed concrete", (0.43, 0.44, 0.42), 0.87)
    frame = ctx.material("Frayling black painted metal", (0.045, 0.05, 0.052), 0.48, 0.55)
    glass = ctx.material("Frayling recessed clear glazing", (0.13, 0.21, 0.23), 0.18, 0, 0.25)
    spandrel = ctx.material("Frayling pale opaque spandrel", (0.64, 0.72, 0.69), 0.53)
    roof = ctx.material("Frayling grey roof covering", (0.18, 0.19, 0.18), 0.90)
    floor = ctx.material("Frayling atrium ground estimate", (0.20, 0.19, 0.16), 0.98)
    m = ctx.mesh("Exact outer shell with real openings")
    r = ctx.mesh("Four height zones and open garden atrium")
    d = ctx.mesh("Concrete bands window frames entrance and steps")
    base = feature.get("base_m", 0)
    entrances = []
    nopen = 0

    def face(mesh, ps, mat):
        for i in range(1, len(ps) - 1):
            a, b, c = ps[0], ps[i], ps[i + 1]
            v = [b[j] - a[j] for j in range(3)]
            w = [c[j] - a[j] for j in range(3)]
            if (
                sum(
                    (v[(j + 1) % 3] * w[(j + 2) % 3] - v[(j + 2) % 3] * w[(j + 1) % 3]) ** 2
                    for j in range(3)
                )
                > 1e-12
            ):
                mesh.face([a, b, c], mat)

    for zone in DATA:
        top = zone["height"]
        courtyard = "atrium" in zone["name"]
        for tri in zone["triangles"]:
            face(r, [(x, y, base + top) for x, y in tri], floor if courtyard else roof)
        if courtyard:
            continue
        for edge in zone["edges"]:
            aa, bb = edge["a"], edge["b"]
            L = math.dist(aa, bb)
            bottom = edge["bottom"]
            tx = (bb[0] - aa[0]) / L
            ty = (bb[1] - aa[1]) / L
            nx, ny = ty, -tx
            angle = math.atan2(ty, tx)
            if bottom >= top - 1e-5:
                continue

            def p(u, z, dep=0):
                return (aa[0] + tx * u - nx * dep, aa[1] + ty * u - ny * dep, base + z)

            front = edge["outer"] and nx < -0.75 and top > 13 and L > 15
            entry = front
            north_a, north_b = feature["geometry"][0]["outer"][8:10]
            vx = north_b[0] - north_a[0]
            vy = north_b[1] - north_a[1]
            mx = (aa[0] + bb[0]) / 2
            my = (aa[1] + bb[1]) / 2
            party = (
                edge["outer"]
                and abs((mx - north_a[0]) * vy - (my - north_a[1]) * vx) / math.hypot(vx, vy) < 0.05
            )
            holes = []
            if (edge["outer"] or edge["court"]) and L > 2.5 and not party:
                levels = 4 if top > 13 else 3 if top > 10 else 2
                spacing = 3.25 if top > 13 else 3.35 if top > 10 else 3.4
                centers = (
                    [L * 0.18, L * 0.46, L * 0.77]
                    if front
                    else [(i + 0.5) * L / max(1, int(L / 3.7)) for i in range(max(1, int(L / 3.7)))]
                )
                for row in range(levels):
                    lo = 0.75 + row * spacing
                    hi = min(lo + 2.35, top - 0.65)
                    if lo < bottom + 0.25 or hi <= lo:
                        continue
                    for i, c in enumerate(centers):
                        door = entry and row == 0 and i == 0
                        width = (
                            2.45
                            if door
                            else 2.8
                            if front and row == 3 and i == 1
                            else 1.55
                            if front
                            else min(2.35, L / len(centers) - 0.8)
                        )
                        if c - width / 2 < 0.20 or c + width / 2 > L - 0.2:
                            continue
                        holes.append(
                            (
                                c - width / 2,
                                c + width / 2,
                                1.05 if door else lo,
                                3.50 if door else hi,
                                door,
                                row,
                            )
                        )
            cuts = sorted(set([bottom, top] + [z for h in holes for z in h[2:4]]))
            for lo, hi in zip(cuts, cuts[1:]):
                intervals = sorted((h[0], h[1]) for h in holes if h[2] <= lo and h[3] >= hi)
                cursor = 0
                for le, ri in intervals + [(L, L)]:
                    if le > cursor:
                        face(
                            m,
                            [p(cursor, lo), p(le, lo), p(le, hi), p(cursor, hi)],
                            brick if top > 10 else concrete,
                        )
                    cursor = max(cursor, ri)
            for le, ri, lo, hi, door, row in holes:
                nopen += 1
                c = (le + ri) / 2
                dep = 0.70 if door else 0.28
                face(
                    m,
                    [
                        p(le, lo, dep + 0.08),
                        p(ri, lo, dep + 0.08),
                        p(ri, hi, dep + 0.08),
                        p(le, hi, dep + 0.08),
                    ],
                    glass,
                )
                for q, w in [
                    ((le, lo), (ri, lo)),
                    ((ri, lo), (ri, hi)),
                    ((ri, hi), (le, hi)),
                    ((le, hi), (le, lo)),
                ]:
                    face(m, [p(*q), p(*w), p(*w, dep), p(*q, dep)], concrete)
                for u in (le, ri):
                    d.box(*p(u, (lo + hi) / 2, 0.06), 0.075, 0.17, hi - lo, frame, angle)
                for z in (hi,) if door else (lo, hi):
                    d.box(*p(c, z, 0.06), ri - le, 0.17, 0.075, frame, angle)
                if door:
                    leaf = (ri - le - 0.08) / 2
                    for sign in (-1, 1):
                        cc = c + sign * (leaf / 2 + 0.02)
                        for u in (cc - leaf / 2, cc + leaf / 2):
                            d.box(*p(u, (lo + hi) / 2, dep), 0.07, 0.1, hi - lo, frame, angle)
                        for z in (lo + 0.05, lo + 0.95, hi - 0.05):
                            d.box(*p(cc, z, dep), leaf, 0.1, 0.07, frame, angle)
                        d.beam(
                            p(cc - sign * 0.34, lo + 0.9, dep - 0.1),
                            p(cc - sign * 0.34, lo + 1.2, dep - 0.1),
                            0.022,
                            frame,
                            8,
                        )
                        entrances.append(
                            {
                                "threshold_xyz": list(p(cc, lo)),
                                "outward_normal": [nx, ny, 0],
                                "door_leaf_xyz": list(p(cc, (lo + hi) / 2, dep)),
                                "door_leaf_depth_m": 0.65,
                                "clear_width_m": leaf - 0.15,
                                "stair_treads": 7,
                                "riser_m": 0.15,
                                "tread_m": 0.32,
                                "landing_depth_m": 1.2,
                                "landing_z_m": 1.05,
                                "ramp": "not evidenced",
                                "supporting_surface": "authored seven-step stair and finite landing; terrain seam coordinator-owned",
                                "estimated": True,
                            }
                        )
                    d.box(*p(c, 0.525, -0.60), ri - le + 0.50, 1.2, 1.05, concrete, angle)
                    for k in range(7):
                        h = (k + 1) * 0.15
                        v = 1.2 + (6 - k) * 0.32 + 0.16
                        d.box(*p(c, h / 2, -v), ri - le + 0.5, 0.32, h, concrete, angle)
                    for side in (le - 0.23, ri + 0.23):
                        for v, h in [(3.28, 0.15), (2.32, 0.60), (1.36, 1.05), (0.2, 1.05)]:
                            d.beam(p(side, h, -v), p(side, h + 1, -v), 0.025, frame, 8)
                        d.beam(p(side, 1.15, -3.28), p(side, 2.05, -1.36), 0.032, frame, 8)
                        d.beam(p(side, 2.05, -1.36), p(side, 2.05, -0.2), 0.032, frame, 8)
                    d.box(*p(c, 3.75, -0.7), ri - le + 3.2, 1.9, 0.30, concrete, angle)
                else:
                    d.box(
                        *p(c, lo + 0.26, dep - 0.035), ri - le - 0.12, 0.045, 0.45, spandrel, angle
                    )
                    d.box(*p(c, hi - 0.30, 0.11), ri - le, 0.13, 0.065, frame, angle)
                    if ri - le > 2:
                        d.box(*p(c, (lo + hi) / 2, 0.11), 0.07, 0.13, hi - lo, frame, angle)
                    if front and row == 3 and ri - le > 2:
                        # Source-visible shallow projecting top bay, paired glass and side returns.
                        face(
                            d,
                            [
                                p(le, lo, -0.55),
                                p(ri, lo, -0.55),
                                p(ri, hi, -0.55),
                                p(le, hi, -0.55),
                            ],
                            glass,
                        )
                        for u in (le, ri):
                            face(d, [p(u, lo), p(u, hi), p(u, hi, -0.55), p(u, lo, -0.55)], glass)
                        for u in (le, c, ri):
                            d.box(*p(u, (lo + hi) / 2, -0.58), 0.075, 0.12, hi - lo, frame, angle)
                        for z in (lo, hi):
                            d.box(*p(c, z, -0.28), ri - le + 0.20, 0.75, 0.16, concrete, angle)
            # Beams sit in opaque strips between each photographed floor row.
            if edge["outer"] or edge["court"]:
                for z in [3.65, 6.9, 10.15]:
                    if bottom < z - 0.15 and z + 0.15 < top:
                        d.box(*p(L / 2, z, -0.055), L, 0.18, 0.25, concrete, angle)
                d.box(*p(L / 2, top + 0.28, 0.08), L, 0.27, 0.56, concrete, angle)
    objs = [m.done(), r.done(), d.done()]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "levels": 4,
            "roof_zone_heights_m": [14.1, 11.5, 7.5],
            "maximum_parapet_m": 14.66,
            "actual_apertures": nopen,
            "main_facade": "west Jay Mews",
            "garden_atrium_floor_m": 0.1,
            "roof_partition": "west common-room block; angled library; lower northern/eastern connectors; open central garden",
            "outer_footprint": "unchanged complete mapped ring",
            "detail_level": "reduced source-visible primary windows, exposed floor beams and top bay; rear rhythms estimated",
        },
        "interfaces": {"entrances": entrances},
        "evidence_source_ids": [
            "osm-20260908",
            "frayling-shadowssettle-2020",
            "frayling-garden-atrium-2021",
            "stevens-shadowssettle-jay-context-2020",
            "frayling-historic-england-description",
            "ea-lidar-composite-2022-tq27ne",
        ],
        "uncertainty": [
            "Courtyard and roof partition coordinates estimated from 1m EA map; outer footprint unchanged, no neighbouring building annexed.",
            "Entrance location supported by geotagged Jay Mews photo; stair count and dimensions estimated, not an access survey.",
            "Library and connecting-wing window rhythms are reduced estimates; garden foliage excluded from building geometry.",
            "Photo dates 2020 and 2021 and EA2022 differ from 2026 footprint; no hidden rooftop plant invented.",
        ],
    }


DATA = [
    {
        "name": "west common rooms",
        "height": 14.1,
        "triangles": [
            [
                [555.2416312318528, 61.04413888417184],
                [555.4851553324273, 61.16042781202078],
                [554.9896477026632, 97.43572242837399],
            ],
            [
                [555.2416312318528, 61.04413888417184],
                [554.9896477026632, 97.43572242837399],
                [546.5799121081237, 97.32071206482411],
            ],
            [
                [555.2416312318528, 61.04413888417184],
                [546.5799121081237, 97.32071206482411],
                [546.991703789332, 93.86328057479113],
            ],
            [
                [555.2416312318528, 61.04413888417184],
                [546.991703789332, 93.86328057479113],
                [540.665845792857, 89.94484227336943],
            ],
            [
                [555.2416312318528, 61.04413888417184],
                [540.665845792857, 89.94484227336943],
                [542.6725289513124, 64.57911285664886],
            ],
        ],
        "edges": [
            {
                "a": [554.9896477026632, 97.43572242837399],
                "b": [546.5799121081237, 97.32071206482411],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [546.5799121081237, 97.32071206482411],
                "b": [546.991703789332, 93.86328057479113],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [546.991703789332, 93.86328057479113],
                "b": [540.665845792857, 89.94484227336943],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [540.665845792857, 89.94484227336943],
                "b": [542.6725289513124, 64.57911285664886],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [542.6725289513124, 64.57911285664886],
                "b": [555.2416312318528, 61.04413888417184],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [555.2416312318528, 61.04413888417184],
                "b": [555.4851553324273, 61.16042781202078],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [555.4851553324273, 61.16042781202078],
                "b": [554.9896477026632, 97.43572242837399],
                "bottom": 11.5,
                "outer": False,
                "court": False,
            },
        ],
    },
    {
        "name": "angled library wing",
        "height": 11.5,
        "triangles": [
            [
                [555.2219024507795, 80.43276896327734],
                [554.9896477026632, 97.43572242837399],
                [555.4851553324273, 61.16042781202078],
            ],
            [
                [555.4851553324273, 61.16042781202078],
                [555.2416312318528, 61.04413888417184],
                [566.0984605798731, 66.228549961932],
            ],
            [
                [555.4851553324273, 61.16042781202078],
                [566.0984605798731, 66.228549961932],
                [565.3502851845697, 71.03221764881164],
            ],
            [
                [581.0014314084547, 79.84223237261176],
                [586.6302059273003, 73.54544989578426],
                [595.2532190264023, 74.59645465827946],
            ],
            [
                [581.0014314084547, 79.84223237261176],
                [595.2532190264023, 74.59645465827946],
                [587.0633090563351, 92.8725544642657],
            ],
            [
                [581.0014314084547, 79.84223237261176],
                [587.0633090563351, 92.8725544642657],
                [565.2235743693309, 80.56955033447593],
            ],
            [
                [581.0014314084547, 79.84223237261176],
                [565.2235743693309, 80.56955033447593],
                [555.2219024507795, 80.43276896327734],
            ],
            [
                [555.2219024507795, 80.43276896327734],
                [555.4851553324273, 61.16042781202078],
                [565.3502851845697, 71.03221764881164],
            ],
            [
                [555.2219024507795, 80.43276896327734],
                [565.3502851845697, 71.03221764881164],
                [581.0014314084547, 79.84223237261176],
            ],
        ],
        "edges": [
            {
                "a": [565.2235743693309, 80.56955033447593],
                "b": [555.2219024507795, 80.43276896327734],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [555.2219024507795, 80.43276896327734],
                "b": [554.9896477026632, 97.43572242837399],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [554.9896477026632, 97.43572242837399],
                "b": [555.4851553324273, 61.16042781202078],
                "bottom": 14.1,
                "outer": False,
                "court": False,
            },
            {
                "a": [555.4851553324273, 61.16042781202078],
                "b": [555.2416312318528, 61.04413888417184],
                "bottom": 14.1,
                "outer": False,
                "court": False,
            },
            {
                "a": [555.2416312318528, 61.04413888417184],
                "b": [566.0984605798731, 66.228549961932],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [566.0984605798731, 66.228549961932],
                "b": [565.3502851845697, 71.03221764881164],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [565.3502851845697, 71.03221764881164],
                "b": [581.0014314084547, 79.84223237261176],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [581.0014314084547, 79.84223237261176],
                "b": [586.6302059273003, 73.54544989578426],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [586.6302059273003, 73.54544989578426],
                "b": [595.2532190264023, 74.59645465827946],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [595.2532190264023, 74.59645465827946],
                "b": [587.0633090563351, 92.8725544642657],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [587.0633090563351, 92.8725544642657],
                "b": [565.2235743693309, 80.56955033447593],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
        ],
    },
    {
        "name": "north east connecting wings",
        "height": 7.5,
        "triangles": [
            [
                [554.9896477026632, 97.43572242837399],
                [556.0034769595368, 96.4492268441245],
                [582.0078247298952, 96.80485872738063],
            ],
            [
                [587.0633090563351, 92.8725544642657],
                [595.2532190264023, 74.59645465827947],
                [598.658942947397, 75.01155689917505],
            ],
            [
                [587.0633090563351, 92.8725544642657],
                [598.658942947397, 75.01155689917505],
                [595.2785385438474, 107.51740590669215],
            ],
            [
                [546.1798216133611, 100.67989958263934],
                [546.991703789332, 93.86328057479113],
                [546.5799121081237, 97.32071206482411],
            ],
            [
                [546.1798216133611, 100.67989958263934],
                [546.5799121081237, 97.32071206482411],
                [554.9896477026632, 97.43572242837399],
            ],
            [
                [546.1798216133611, 100.67989958263934],
                [554.9896477026632, 97.43572242837399],
                [582.0078247298952, 96.80485872738063],
            ],
            [
                [556.2084076052997, 81.44662083406001],
                [556.0034769595368, 96.4492268441245],
                [554.9896477026632, 97.43572242837399],
            ],
            [
                [556.2084076052997, 81.44662083406001],
                [554.9896477026632, 97.43572242837399],
                [555.2219024507795, 80.43276896327734],
            ],
            [
                [556.2084076052997, 81.44662083406001],
                [555.2219024507795, 80.43276896327734],
                [565.2235743693309, 80.56955033447593],
            ],
            [
                [595.2785385438474, 107.51740590669215],
                [546.1798216133611, 100.67989958263934],
                [582.0078247298952, 96.80485872738063],
            ],
            [
                [595.2785385438474, 107.51740590669215],
                [582.0078247298952, 96.80485872738063],
                [582.0761348617962, 91.8039899719879],
            ],
            [
                [565.1962503250688, 82.5698978183791],
                [556.2084076052997, 81.44662083406001],
                [565.2235743693309, 80.56955033447593],
            ],
            [
                [565.1962503250688, 82.5698978183791],
                [565.2235743693309, 80.56955033447593],
                [587.0633090563351, 92.8725544642657],
            ],
            [
                [587.0633090563351, 92.8725544642657],
                [595.2785385438474, 107.51740590669215],
                [582.0761348617962, 91.8039899719879],
            ],
            [
                [587.0633090563351, 92.8725544642657],
                [582.0761348617962, 91.8039899719879],
                [565.1962503250688, 82.5698978183791],
            ],
        ],
        "edges": [
            {
                "a": [546.1798216133611, 100.67989958263934],
                "b": [546.991703789332, 93.86328057479113],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [546.991703789332, 93.86328057479113],
                "b": [546.5799121081237, 97.32071206482411],
                "bottom": 14.1,
                "outer": False,
                "court": False,
            },
            {
                "a": [546.5799121081237, 97.32071206482411],
                "b": [554.9896477026632, 97.43572242837399],
                "bottom": 14.1,
                "outer": False,
                "court": False,
            },
            {
                "a": [554.9896477026632, 97.43572242837399],
                "b": [555.2219024507795, 80.43276896327734],
                "bottom": 14.1,
                "outer": False,
                "court": False,
            },
            {
                "a": [555.2219024507795, 80.43276896327734],
                "b": [565.2235743693309, 80.56955033447593],
                "bottom": 11.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [565.2235743693309, 80.56955033447593],
                "b": [587.0633090563351, 92.8725544642657],
                "bottom": 11.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [587.0633090563351, 92.8725544642657],
                "b": [595.2532190264023, 74.59645465827947],
                "bottom": 11.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [595.2532190264023, 74.59645465827947],
                "b": [598.658942947397, 75.01155689917505],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [598.658942947397, 75.01155689917505],
                "b": [595.2785385438474, 107.51740590669215],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [595.2785385438474, 107.51740590669215],
                "b": [546.1798216133611, 100.67989958263934],
                "bottom": 0,
                "outer": True,
                "court": None,
            },
            {
                "a": [556.2084076052997, 81.44662083406001],
                "b": [556.0034769595368, 96.4492268441245],
                "bottom": 0.1,
                "outer": False,
                "court": True,
            },
            {
                "a": [556.0034769595368, 96.4492268441245],
                "b": [582.0078247298952, 96.80485872738063],
                "bottom": 0.1,
                "outer": False,
                "court": True,
            },
            {
                "a": [582.0078247298952, 96.80485872738063],
                "b": [582.0761348617962, 91.8039899719879],
                "bottom": 0.1,
                "outer": False,
                "court": True,
            },
            {
                "a": [582.0761348617962, 91.8039899719879],
                "b": [565.1962503250688, 82.5698978183791],
                "bottom": 0.1,
                "outer": False,
                "court": True,
            },
            {
                "a": [565.1962503250688, 82.5698978183791],
                "b": [556.2084076052997, 81.44662083406001],
                "bottom": 0.1,
                "outer": False,
                "court": True,
            },
        ],
    },
    {
        "name": "estimated garden atrium floor",
        "height": 0.1,
        "triangles": [
            [
                [582.0761348617962, 91.8039899719879],
                [582.0078247298952, 96.80485872738063],
                [556.0034769595368, 96.4492268441245],
            ],
            [
                [582.0761348617962, 91.8039899719879],
                [556.0034769595368, 96.4492268441245],
                [556.2084076052997, 81.44662083406001],
            ],
            [
                [582.0761348617962, 91.8039899719879],
                [556.2084076052997, 81.44662083406001],
                [565.1962503250688, 82.5698978183791],
            ],
        ],
        "edges": [
            {
                "a": [556.0034769595368, 96.4492268441245],
                "b": [556.2084076052997, 81.44662083406001],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [556.2084076052997, 81.44662083406001],
                "b": [565.1962503250688, 82.5698978183791],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [565.1962503250688, 82.5698978183791],
                "b": [582.0761348617962, 91.8039899719879],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [582.0761348617962, 91.8039899719879],
                "b": [582.0078247298952, 96.80485872738063],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
            {
                "a": [582.0078247298952, 96.80485872738063],
                "b": [556.0034769595368, 96.4492268441245],
                "bottom": 7.5,
                "outer": False,
                "court": False,
            },
        ],
    },
]
