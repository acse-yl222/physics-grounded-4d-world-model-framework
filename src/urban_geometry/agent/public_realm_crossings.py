"""Three mapped zebra marking groups, with estimated dimensions.
Authoring UTM only. No roads, curbs, islands, poles or tactile pads invented.
Caller supplies surface elevation/gradient; final master ray/dedup required.
"""

import math
from detailed_common import BuildingContext


def build(collection, records):
    ctx = BuildingContext(collection, {"name": "Mapped crossing markings"})
    paint = ctx.material("Crossing warm white road marking", (0.84, 0.84, 0.79), 0.86, 0)
    objects = []
    for rec in records:
        tags = rec["crossing_tags"]
        if not (
            tags.get("crossing:markings") == "zebra"
            or tags.get("crossing_ref") == "zebra"
            and tags.get("crossing:markings") == "yes"
        ):
            raise ValueError("Explicit zebra evidence required")
        if rec.get("layer", 0) != 0 or not rec["grade_verified_from_tags"]:
            raise ValueError("Only reviewed ground layer supported")
        if rec.get("existing_object"):
            raise ValueError("Inherited marking already present")
        x, y = rec["position_authoring_xy_m"]
        u = rec["crossing_unit_xy"]
        v = rec["road_unit_xy"]
        span = rec["road_span_m"]
        depth = rec["band_depth_m"]
        w = rec["stripe_width_m"]
        gap = rec["stripe_gap_m"]
        assert abs(u[0] * v[0] + u[1] * v[1]) < 1e-5
        gradient = rec.get("ground_gradient_xy", [0, 0])
        z = rec["ground_z"]

        def p(a, b, h):
            dx = u[0] * a + v[0] * b
            dy = u[1] * a + v[1] * b
            return (x + dx, y + dy, z + gradient[0] * dx + gradient[1] * dy + h)

        m = ctx.mesh("Crossing::" + rec["id"])
        count = max(1, int((span + gap) / (w + gap)))
        total = count * w + (count - 1) * gap
        start = -total / 2
        for i in range(count):
            a = start + i * (w + gap)
            b = a + w
            lo = [
                p(a, -depth / 2, 0.003),
                p(b, -depth / 2, 0.003),
                p(b, depth / 2, 0.003),
                p(a, depth / 2, 0.003),
            ]
            hi = [(q[0], q[1], q[2] + 0.003) for q in lo]
            m.face(list(reversed(lo)), paint)
            m.face(hi, paint)
            for k in range(4):
                m.face([lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]], paint)
        ob = m.done()
        ob["research_object_id"] = "public-realm-crossing::" + rec["id"]
        ob["osm_way_id"] = rec["way_id"]
        ob["semantic_type"] = "zebra_road_marking"
        ob["stripe_count"] = count
        ob["evidence_source_ids"] = ";".join(rec["source_ids"])
        ob["fidelity_status"] = (
            "mapped type and centre; span orientation and dimensions estimated; not surveyed"
        )
        ob["ground_status"] = rec["ground_status"]
        ob["dedup_status"] = rec["dedup_status"]
        objects.append(ob)
    return objects
