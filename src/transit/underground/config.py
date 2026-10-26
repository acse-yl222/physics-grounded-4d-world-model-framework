"""Scene configuration, line reference table and small shared helpers."""

from __future__ import annotations

import json

from traffic.corridor_sumo.tfl import Enu

SIMULATION = "underground"

# Official TfL line colours (TfL colour standard, "Colours" issue 4 / line diagram
# palette), used as a fixed reference table; kind: sub-surface (cut-and-cover),
# deep-level tube or main-line rail.
LINES = {
    "bakerloo": {"name": "Bakerloo", "colour": "#B26300", "kind": "deep"},
    "central": {"name": "Central", "colour": "#DC241F", "kind": "deep"},
    "circle": {"name": "Circle", "colour": "#FFD329", "kind": "subsurface"},
    "district": {"name": "District", "colour": "#007D32", "kind": "subsurface"},
    "hammersmith-city": {"name": "Hammersmith & City", "colour": "#F4A9BE", "kind": "subsurface"},
    "jubilee": {"name": "Jubilee", "colour": "#A1A5A7", "kind": "deep"},
    "metropolitan": {"name": "Metropolitan", "colour": "#9B0058", "kind": "subsurface"},
    "northern": {"name": "Northern", "colour": "#000000", "kind": "deep"},
    "piccadilly": {"name": "Piccadilly", "colour": "#0019A8", "kind": "deep"},
    "victoria": {"name": "Victoria", "colour": "#0098D8", "kind": "deep"},
    "waterloo-city": {"name": "Waterloo & City", "colour": "#93CEBA", "kind": "deep"},
    "elizabeth": {"name": "Elizabeth", "colour": "#6950A1", "kind": "rail"},
    "overground": {"name": "London Overground", "colour": "#EE7C0E", "kind": "rail"},
}
COLOUR_SOURCE = (
    "TfL line colour standard (reference constants in transit.underground.config.LINES); "
    "Waterloo & City #93CEBA, Overground #EE7C0E"
)


def line_id(name: str | None) -> str | None:
    """Canonical line id from a GTFS route short name or an OSM route name/ref."""
    if not name:
        return None
    text = name.lower().replace("&", "and").replace("’", "'")
    table = [
        ("hammersmith and city", "hammersmith-city"),
        ("hammersmith & city", "hammersmith-city"),
        ("waterloo and city", "waterloo-city"),
        ("elizabeth", "elizabeth"),
        ("overground", "overground"),
        ("mildmay", "overground"),
        ("windrush", "overground"),
        ("lioness", "overground"),
        ("suffragette", "overground"),
        ("weaver", "overground"),
        ("liberty", "overground"),
    ]
    for key, lid in table:
        if key in text:
            return lid
    for lid in LINES:
        if text.startswith(LINES[lid]["name"].lower()) or f"{lid} line" in text:
            return lid
    first = text.split()[0] if text.split() else ""
    for lid, meta in LINES.items():
        if first == meta["name"].lower().split()[0] and lid not in ("hammersmith-city",):
            return lid
    return None


def log(message: str) -> None:
    print(message, flush=True)


def load_scene(scene: str, root=None) -> dict:
    """Storage, configuration, origin/half-size and the scene ``Enu`` projection."""
    from common.storage import Storage

    storage = Storage.load(root)
    meta = storage.metadata(scene)
    config_path = meta / "configs/underground.json"
    cfg = json.loads(config_path.read_text())
    geo_path = meta / cfg.get("geometry_config", "configs/image_to_threejs.json")
    geo = json.loads(geo_path.read_text())
    origin = geo["origin"]
    return {
        "storage": storage,
        "scene": scene,
        "cfg": cfg,
        "config_path": config_path,
        "geo": geo,
        "geo_path": geo_path,
        "origin": origin,
        "half": geo["domain_m"] / 2,
        "enu": Enu(origin["longitude"], origin["latitude"]),
    }
