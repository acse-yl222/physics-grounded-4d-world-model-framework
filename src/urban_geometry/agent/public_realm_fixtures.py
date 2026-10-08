"""Six mapped fixtures: photo-informed street mast and museum lantern families.
Authoring UTM; coordinator applies M once and supplies verified ground_z.
Dimensions/individual-node style correspondence remain partly estimated.
"""

import math
from detailed_common import BuildingContext

EXHIBITION_IDS = {"node-8014230168", "node-8014230169", "node-8014230170"}
MUSEUM_IDS = {"node-11049929667", "node-11049929668"}


def build(collection, records):
    ctx = BuildingContext(collection, {"name": "Public realm fixtures"})
    mast = ctx.material("Exhibition grey metal mast", (0.34, 0.36, 0.36), 0.48, 0.65)
    heritage = ctx.material("Museum dark green painted iron", (0.06, 0.105, 0.09), 0.55, 0.45)
    glass = ctx.material("Museum lantern glass", (0.47, 0.56, 0.53), 0.2, 0, 0.4)
    diffuser = ctx.material("Fixture pale optical lens", (0.72, 0.76, 0.73), 0.25)
    unknown = ctx.material(
        "Estimated bollard dark painted metal", (0.075, 0.085, 0.082), 0.48, 0.55
    )
    reflector = ctx.material("Estimated bollard reflector", (0.7, 0.71, 0.65), 0.36, 0.15)
    objects = []
    for rec in records:
        if rec["kind"] not in ("street_lamp", "bollard"):
            raise ValueError("Control nodes are not physical-pole evidence")
        if rec.get("existing_object"):
            raise ValueError("Refusing duplicate inherited fixture")
        x, y = rec["position_authoring_xy_m"]
        z = rec["ground_z"]
        m = ctx.mesh("PublicRealm::" + rec["id"])

        def profile(levels, mat, n=16, cap=True):
            rings = [
                [
                    (
                        x + rad * math.cos(2 * math.pi * k / n),
                        y + rad * math.sin(2 * math.pi * k / n),
                        z + h,
                    )
                    for k in range(n)
                ]
                for h, rad in levels
            ]
            for a, b in zip(rings, rings[1:]):
                for k in range(n):
                    m.face([a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]], mat)
            if cap:
                m.face(list(reversed(rings[0])), mat)
                m.face(rings[-1], mat)

        if rec["id"] in EXHIBITION_IDS:
            profile([(0, 0.21), (0.3, 0.205), (9, 0.145), (19.85, 0.08)], mast)
            # Compact mounted optics, no long invented cross-arm. Exact bearings estimated.
            for h, sign in [(8.2, -1), (9.0, 1)]:
                end = (x + sign * 0.34, y, z + h - 0.10)
                m.beam((x, y, z + h), end, 0.055, mast, n=12)
                m.beam(end, (x + sign * 0.49, y, z + h - 0.18), 0.16, mast, n=16)
                m.beam(
                    (x + sign * 0.49, y, z + h - 0.18),
                    (x + sign * 0.505, y, z + h - 0.188),
                    0.125,
                    diffuser,
                    n=16,
                )
            profile([(19.85, 0.08), (19.94, 0.08)], diffuser)
            profile([(19.94, 0.08), (20, 0.07)], mast)
            h = 20
            style = "Exhibition Road slender 20m mast; street-family photo and designer text; node match inferred"
            sources = [
                "osm-public-realm-20260909",
                "fixtures-lamb-exhibition-2015",
                "fixtures-projectcentre-mast-spec",
            ]
        elif rec["id"] in MUSEUM_IDS:
            profile(
                [
                    (0, 0.40),
                    (0.10, 0.40),
                    (0.16, 0.34),
                    (1.04, 0.30),
                    (1.12, 0.36),
                    (1.20, 0.31),
                    (1.32, 0.22),
                    (1.45, 0.16),
                    (4.55, 0.105),
                    (4.65, 0.20),
                    (4.76, 0.14),
                    (4.88, 0.27),
                    (5.0, 0.29),
                ],
                heritage,
                n=8,
            )
            profile([(5.0, 0.28), (6.00, 0.46)], glass, n=6)
            for k in range(6):
                angle = math.pi * k / 3
                m.beam(
                    (x + 0.28 * math.cos(angle), y + 0.28 * math.sin(angle), z + 5),
                    (x + 0.46 * math.cos(angle), y + 0.46 * math.sin(angle), z + 6),
                    0.025,
                    heritage,
                    n=8,
                )
            profile([(4.97, 0.30), (5.02, 0.30)], heritage, n=6)
            profile(
                [
                    (6.0, 0.49),
                    (6.07, 0.50),
                    (6.27, 0.20),
                    (6.32, 0.20),
                    (6.39, 0.07),
                    (6.49, 0.045),
                ],
                heritage,
                n=6,
            )
            for k in range(8):
                angle = math.pi * k / 4
                m.beam(
                    (x + 0.14 * math.cos(angle), y + 0.14 * math.sin(angle), z + 1.55),
                    (x + 0.10 * math.cos(angle), y + 0.10 * math.sin(angle), z + 4.45),
                    0.012,
                    heritage,
                    n=6,
                )
            h = 6.49
            style = "V&A entrance flared hexagonal lantern and stepped dark-green iron post; dimensions estimated"
            sources = [
                "osm-public-realm-20260909",
                "va-entrance-brown-2024",
                "fixtures-va-pair-context-2007",
            ]
        elif rec["kind"] == "bollard":
            m.beam((x, y, z), (x, y, z + 0.82), 0.075, unknown, n=16)
            m.beam((x, y, z + 0.82), (x, y, z + 0.9), 0.076, reflector, n=16)
            m.beam((x, y, z + 0.9), (x, y, z + 0.98), 0.075, unknown, n=16)
            h = 0.98
            style = "Unverified fixed bollard proxy; shape material reflector and height remain estimates"
            sources = ["osm-public-realm-20260909"]
        else:
            raise ValueError("No style evidence assigned to this lamp ID")
        ob = m.done()
        ob["research_object_id"] = "public-realm::" + rec["id"]
        ob["semantic_type"] = rec["kind"]
        ob["evidence_source_id"] = ";".join(sources)
        ob["fidelity_status"] = style
        ob["estimated_height_m"] = h
        ob["ground_status"] = rec.get(
            "ground_status", "caller supplied elevation; final master ray not certified by module"
        )
        objects.append(ob)
    return objects
