"""Amaryllis Fleming Concert Hall: exact mapped outline and EA fitted twin roof planes.
Single authoring UTM frame. High side openings are reduced estimates; no invented external door.
"""

import math


def build(ctx, feature):
    brick = ctx.material("RCM Hall estimated red brown brick", (0.36, 0.145, 0.085), 0.88)
    stone = ctx.material("RCM Hall pale stone trim", (0.66, 0.61, 0.49), 0.83)
    slate = ctx.material("RCM Hall dark slate roof", (0.12, 0.145, 0.16), 0.82)
    frame = ctx.material("RCM Hall pale painted window frame", (0.71, 0.69, 0.62), 0.58)
    glass = ctx.material("RCM Hall recessed glass", (0.12, 0.18, 0.20), 0.20, 0, 0.28)
    metal = ctx.material("RCM Hall dark rainwater metal", (0.045, 0.048, 0.045), 0.50, 0.45)
    wall = ctx.mesh("Mapped concert hall shell with actual high openings")
    roof = ctx.mesh("Two exact EA fitted roof planes")
    detail = ctx.mesh("Estimated side window frames and cornice")
    base = feature.get("base_m", 0)
    ring = feature["geometry"][0]["outer"]
    origin = DATA["origin"]
    u = DATA["u"]
    v = DATA["v"]

    def uv(p):
        return (
            (p[0] - origin[0]) * u[0] + (p[1] - origin[1]) * u[1],
            (p[0] - origin[0]) * v[0] + (p[1] - origin[1]) * v[1],
        )

    def height(p):
        x, y = uv(p)
        return min(c["plane"][0] * x + c["plane"][1] * y + c["plane"][2] for c in DATA["data"])

    def face(m, ps, mat):
        for i in range(1, len(ps) - 1):
            a, b, c = ps[0], ps[i], ps[i + 1]
            q = [b[k] - a[k] for k in range(3)]
            r = [c[k] - a[k] for k in range(3)]
            if (
                sum(
                    (q[(k + 1) % 3] * r[(k + 2) % 3] - q[(k + 2) % 3] * r[(k + 1) % 3]) ** 2
                    for k in range(3)
                )
                > 1e-12
            ):
                m.face([a, b, c], mat)

    for zone in DATA["data"]:
        c = zone["plane"]
        for tri in zone["triangles"]:
            face(
                roof,
                [
                    (
                        origin[0] + u[0] * x + v[0] * y,
                        origin[1] + u[1] * x + v[1] * y,
                        base + c[0] * x + c[1] * y + c[2],
                    )
                    for x, y in tri
                ],
                slate,
            )
    for tri in feature["geometry"][0]["triangles"]:
        face(wall, [(x, y, base) for x, y in reversed(tri)], brick)
    count = 0
    for ei, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        L = math.dist(a, b)
        tx = (b[0] - a[0]) / L
        ty = (b[1] - a[1]) / L
        nx, ny = ty, -tx
        angle = math.atan2(ty, tx)

        def p(s, z, dep=0):
            return (a[0] + tx * s - nx * dep, a[1] + ty * s - ny * dep, base + z)

        # Only courtyard-facing long sides receive estimated clerestory windows.
        holes = []
        if ei in [2, 5]:
            n = max(1, int(L / 4.6))
            for k in range(n):
                c = (k + 0.5) * L / n
                holes.append((c - 0.75, c + 0.75, 11.55, 14.65))
        # Break boundary at roof-plane intersection so every cap remains planar.
        x0, y0 = uv(a)
        x1, y1 = uv(b)
        c0, c1 = [z["plane"] for z in DATA["data"]]
        D = lambda x, y: (c0[0] - c1[0]) * x + (c0[1] - c1[1]) * y + c0[2] - c1[2]
        da, db = D(x0, y0), D(x1, y1)
        cross = L * da / (da - db) if abs(da - db) > 1e-12 else -1
        cuts = sorted(
            set(
                [0, L]
                + [h[j] for h in holes for j in [0, 1]]
                + ([cross] if 1e-8 < cross < L - 1e-8 else [])
            )
        )
        for s, t in zip(cuts, cuts[1:]):
            z0, z1 = height(p(s, 0)[:2]), height(p(t, 0)[:2])
            hole = next((h for h in holes if h[0] <= s + 1e-8 and h[1] >= t - 1e-8), None)
            if hole:
                lo, hi = hole[2:]
                face(wall, [p(s, 0), p(t, 0), p(t, lo), p(s, lo)], brick)
                face(wall, [p(s, hi), p(t, hi), p(t, z1), p(s, z0)], brick)
            else:
                face(wall, [p(s, 0), p(t, 0), p(t, z1), p(s, z0)], brick)
        for le, ri, lo, hi in holes:
            count += 1
            dep = 0.25
            c = (le + ri) / 2
            face(wall, [p(le, lo, dep), p(ri, lo, dep), p(ri, hi, dep), p(le, hi, dep)], glass)
            for q, r in [
                ((le, lo), (ri, lo)),
                ((ri, lo), (ri, hi)),
                ((ri, hi), (le, hi)),
                ((le, hi), (le, lo)),
            ]:
                face(wall, [p(*q), p(*r), p(*r, dep), p(*q, dep)], stone)
            for s in [le, c, ri]:
                detail.box(*p(s, (lo + hi) / 2, 0.08), 0.065, 0.14, hi - lo, frame, angle)
            for z in [lo, hi, lo + 1.55]:
                detail.box(*p(c, z, 0.08), ri - le, 0.14, 0.075, frame, angle)
            detail.box(*p(c, lo - 0.11, -0.08), ri - le + 0.26, 0.34, 0.18, stone, angle)
        if ei in [2, 5]:
            for z in [11.25, 15.1]:
                detail.box(*p(L / 2, z, -0.035), L, 0.18, 0.14, stone, angle)
            # Thin gutter follows the fitted side eave, not a fabricated flat cap.
            detail.beam(
                p(0, height(a) - 0.08, -0.03), p(L, height(b) - 0.08, -0.03), 0.065, metal, 8
            )
    objs = [m.done() for m in [wall, roof, detail]]
    return {
        "created": [o.name for o in objs if o],
        "parameters": {
            "roof": "two intersecting least-squares EA2022 roof planes clipped to complete original footprint",
            "roof_ridge_m": 22.0,
            "roof_eaves_approx_m": 16.0,
            "actual_high_openings": count,
            "detail_level": "reduced; long hall volume and roof evidence prioritised",
        },
        "interfaces": {
            "entrances": [],
            "internal_connection": {
                "adjacent_id": "way-27765400",
                "boundary_authoring_xy": [ring[8], ring[0]],
                "status": "mapped shared boundary; hall access is through RCM; interior route not modelled",
            },
        },
        "evidence_source_ids": [
            "osm-20260908",
            "ea-lidar-composite-2022-tq27ne",
            "va-praefcke-aerial-a-2011",
            "va-praefcke-aerial-b-2011",
        ],
        "uncertainty": [
            "High side window count, shape, frames, cornice and optical PBR values are estimates; small-scale aerials do not resolve individual apertures.",
            "No standalone exterior door is evidenced. Shared north boundary stays closed as an exterior-only internal connection, not a claimed walkable route.",
            "Roof planes fit native1m EA measurements; approximate ridge heights and wall top positions are not a measured survey. Narrow northern connector continues the two dominant planes; local sub-metre variation simplified.",
            "2011 photographs predate later courtyard redevelopment; no hidden plant, skylights or four-storey window grid invented.",
        ],
    }


DATA = {
    "origin": [685.0735302647809, -116.52558486070484],
    "u": [0.9919930286949159, 0.1262926404058756],
    "v": [-0.1262926404058756, 0.9919930286949159],
    "data": [
        {
            "plane": [0.588498516082764, 0.0210901339725072, 15.241735724837069],
            "triangles": [
                [
                    [1.7573884982496637, 43.98811998342701],
                    [1.913076732293459, 36.51290844467562],
                    [9.566815762784557, 44.248908976797885],
                ],
                [
                    [9.566815762784557, 44.248908976797885],
                    [1.913076732293459, 36.51290844467562],
                    [10.950724737565512, -1.1655327570263574e-16],
                ],
                [
                    [10.950724737565512, -1.1655327570263574e-16],
                    [1.913076732293459, 36.51290844467562],
                    [0.22711558219388714, 5.888802835598916],
                ],
                [
                    [10.950724737565512, -1.1655327570263574e-16],
                    [0.22711558219388714, 5.888802835598916],
                    [0.0, 0.0],
                ],
                [
                    [-0.1215041271652973, 36.44680648677256],
                    [0.22711558219388714, 5.888802835598916],
                    [1.913076732293459, 36.51290844467562],
                ],
            ],
        },
        {
            "plane": [-0.590982341766356, -0.015798778827933534, 28.15790593237042],
            "triangles": [
                [
                    [9.566815762784557, 44.248908976797885],
                    [10.950724737565512, -1.1655327570263574e-16],
                    [16.967922796452147, 36.390072924073095],
                ],
                [
                    [9.566815762784557, 44.248908976797885],
                    [16.967922796452147, 36.390072924073095],
                    [16.811669007395324, 44.490844514550055],
                ],
                [
                    [20.850373115339288, 36.460586502393426],
                    [16.967922796452147, 36.390072924073095],
                    [21.507629034999173, -2.2891495099196173e-16],
                ],
                [
                    [21.507629034999173, -2.2891495099196173e-16],
                    [16.967922796452147, 36.390072924073095],
                    [10.950724737565512, -1.1655327570263574e-16],
                ],
            ],
        },
    ],
    "ridge_u_at_south": 10.950724737565512,
    "ridge_u_at_north": 9.574600527988029,
}
