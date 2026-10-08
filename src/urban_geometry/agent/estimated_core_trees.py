"""User-authorised artistic tree additions in campus XY; no mapped tree claims."""

import math
import random


def build(ctx, inputs):
    bark = ctx.material("Tree estimated bark", (0.22, 0.135, 0.075), 0.94)
    foliage = [
        ctx.material("Tree estimated leaf " + str(i), c, 0.88)
        for i, c in enumerate([(0.13, 0.26, 0.055), (0.19, 0.32, 0.075), (0.25, 0.37, 0.09)])
    ]
    objects = []
    interfaces = []
    for row in inputs["trees"]:
        if row["status"] != "build":
            continue
        x, y = row["position_authoring_xy_m"]
        z = row["base_z_m"]
        h = row["height_m_estimated"]
        r = row["crown_radius_m_estimated"]
        bottom = row["crown_base_m_estimated"]
        tr = row["trunk_radius_m_estimated"]
        rng = random.Random(row["seed"])
        wood = ctx.mesh(row["id"] + " trunk and branches")
        leaves = ctx.mesh(row["id"] + " editable leaf canopy")
        wood.lathe(
            x,
            y,
            z - 0.12,
            [
                (tr * 1.22, 0),
                (tr, 0.5),
                (tr * 0.68, min(bottom + 1, h * 0.70)),
                (tr * 0.15, h * 0.87),
            ],
            bark,
            10,
        )
        mid = (bottom + h) / 2
        rz = (h - bottom) / 2
        for j in range(12):
            a = j * math.tau / 12 + rng.uniform(-0.15, 0.15)
            level = bottom + (h - bottom) * (0.16 + 0.5 * rng.random())
            end = (x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75, z + level + rz * 0.35)
            wood.beam(
                (
                    x,
                    y,
                    z
                    + max(
                        4.6 if row.get("canopy_may_cross_road") else bottom * 0.78,
                        level - rz * 0.55,
                    ),
                ),
                end,
                tr * 0.30,
                bark,
                7,
            )
            for k in (-1, 1):
                aa = a + k * 0.37
                tip = (
                    x + math.cos(aa) * r * 0.93,
                    y + math.sin(aa) * r * 0.93,
                    z + level + rz * 0.54,
                )
                wood.beam(end, tip, tr * 0.10, bark, 5)
        # Individual folded four-triangle leaves distributed in an irregular
        # crown volume; no opaque sphere surrogate and no species claim.
        count = 2200
        for j in range(count):
            az = rng.random() * math.tau
            t = rng.uniform(-1, 1)
            rr = rng.random() ** (1 / 3)
            rad = (
                (r - 0.38)
                * rr
                * math.sqrt(1 - t * t)
                * (1 + 0.035 * math.sin(az * 5 + row["seed"] % 7))
            )
            cx = x + rad * math.cos(az)
            cy = y + rad * math.sin(az)
            cz = z + mid + rz * rr * t
            angle = rng.random() * math.tau
            size = rng.uniform(0.17, 0.32)
            ux = math.cos(angle) * size
            uy = math.sin(angle) * size
            vx = -math.sin(angle) * size * 0.55
            vy = math.cos(angle) * size * 0.55
            dz = rng.uniform(-0.11, 0.11)
            corners = [
                (cx + ux, cy + uy, cz + dz),
                (cx + vx, cy + vy, cz),
                (cx - ux, cy - uy, cz - dz),
                (cx - vx, cy - vy, cz),
            ]
            peak = (cx, cy, cz + 0.045)
            mat = foliage[rng.randrange(3)]
            for a, b in zip(corners, corners[1:] + corners[:1]):
                leaves.face([a, b, peak], mat)
        for mesh, role in [(wood, "trunk_branches"), (leaves, "foliage")]:
            ob = mesh.done()
            ob["research_object_id"] = "estimated-core-tree::" + row["id"] + "::" + role
            ob["placement_status"] = "user-authorised artistic estimate"
            ob["semantic_type"] = "tree"
            ob["species_status"] = "unknown estimated generic broadleaf"
            ob["dimensions_status"] = "estimated, optional old LiDAR size cue"
            ob["authoring_frame"] = "campus local XY metres; no further transform"
            objects.append(ob.name)
        interfaces.append(
            {
                "id": row["id"],
                "root_authoring_xyz": [x, y, z],
                "buried_root_bottom_z": z - 0.12,
                "trunk_radius_m": tr,
                "estimated_canopy_bottom_z": z + bottom,
                "ground_verification": "final master downward ray pending",
            }
        )
    return {
        "created": objects,
        "interfaces": {"tree_roots": interfaces},
        "parameters": {
            "built_trees": len(interfaces),
            "held_candidates": inputs["held_count"],
            "species": "unknown; generic broadleaf estimate",
        },
        "evidence_source_ids": [
            "user-authorised-estimated-planting",
            "ea-lidar-composite-2022-tq27ne-context-only",
        ],
        "uncertainty": inputs["limitations"],
    }
