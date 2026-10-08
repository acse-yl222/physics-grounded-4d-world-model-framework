"""Explicit ground-support allowlist; do not accept arbitrary low objects."""

INHERITED_SURFACES = {
    "SITE-PATHS-REFERENCE-APPEARANCE",
    "MESH-Mapped roads | widths estimated",
    "MESH-Site | flat ground datum and presentation plinth",
}


def allowed(obj):
    rid = obj.get("research_object_id", "")
    return rid in INHERITED_SURFACES or (
        rid.startswith("extension::context::")
        and obj.get("semantic_type") in {"ground", "park", "road", "path"}
    )
