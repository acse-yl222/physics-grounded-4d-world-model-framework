"""Download Overture Maps features for a square ENU domain.

Reads public GeoParquet from the Overture S3 bucket with bbox row-group
filtering and writes one compact JSON file per layer, with geometry already
projected to the scene's local ENU frame (metres, x east, y north).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

BUCKET = "overturemaps-us-west-2/release"
LAYERS = {
    "buildings": ("buildings", "building"),
    "building_parts": ("buildings", "building_part"),
    "segments": ("transportation", "segment"),
    "land_use": ("base", "land_use"),
    "land_cover": ("base", "land_cover"),
    "land": ("base", "land"),
    "water": ("base", "water"),
    "infrastructure": ("base", "infrastructure"),
}
COLUMNS = {
    "buildings": [
        "id",
        "geometry",
        "names",
        "subtype",
        "class",
        "height",
        "num_floors",
        "min_height",
        "min_floor",
        "roof_shape",
        "roof_height",
        "roof_direction",
        "roof_material",
        "roof_color",
        "facade_material",
        "facade_color",
        "is_underground",
        "has_parts",
        "sources",
    ],
    "building_parts": [
        "id",
        "geometry",
        "building_id",
        "names",
        "height",
        "num_floors",
        "min_height",
        "min_floor",
        "roof_shape",
        "roof_height",
        "roof_material",
        "roof_color",
        "facade_material",
        "facade_color",
        "is_underground",
    ],
    "segments": [
        "id",
        "geometry",
        "names",
        "subtype",
        "class",
        "subclass",
        "road_surface",
        "road_flags",
        "level_rules",
        "width_rules",
    ],
    "land_use": ["id", "geometry", "names", "subtype", "class", "surface", "level"],
    "land_cover": ["id", "geometry", "subtype"],
    "land": ["id", "geometry", "subtype", "class", "level"],
    "water": ["id", "geometry", "names", "subtype", "class", "is_intermittent", "level"],
    "infrastructure": ["id", "geometry", "names", "subtype", "class", "height", "level"],
}
R = 6378137.0


class Enu:
    """Local tangent-plane projection, accurate to centimetres over 8 km."""

    def __init__(self, lon: float, lat: float):
        self.lon0, self.lat0 = lon, lat
        self.kx = math.radians(1) * R * math.cos(math.radians(lat))
        self.ky = math.radians(1) * R

    def __call__(self, lon: float, lat: float) -> list[float]:
        return [round((lon - self.lon0) * self.kx, 2), round((lat - self.lat0) * self.ky, 2)]

    def inverse_bbox(self, half: float) -> tuple[float, float, float, float]:
        dx, dy = half / self.kx, half / self.ky
        return self.lon0 - dx, self.lat0 - dy, self.lon0 + dx, self.lat0 + dy


def project(geom, enu: Enu):
    """Shapely geometry -> nested ENU coordinate lists keyed by geometry type."""
    kind = geom.geom_type
    ring = lambda r: [enu(x, y) for x, y in r.coords]
    if kind == "Polygon":
        return {"type": kind, "rings": [ring(geom.exterior)] + [ring(i) for i in geom.interiors]}
    if kind == "MultiPolygon":
        return {"type": kind, "polygons": [project(p, enu)["rings"] for p in geom.geoms]}
    if kind == "LineString":
        return {"type": kind, "line": ring(geom)}
    if kind == "MultiLineString":
        return {"type": kind, "lines": [ring(g) for g in geom.geoms]}
    if kind == "Point":
        return {"type": kind, "point": enu(geom.x, geom.y)}
    return None


def clean(value):
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def fetch(layer: str, release: str, bbox, enu: Enu, out: Path) -> int:
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    from pyarrow import fs
    from shapely import wkb
    from shapely.geometry import box

    theme, kind = LAYERS[layer]
    s3 = fs.S3FileSystem(anonymous=True, region="us-west-2")
    dataset = ds.dataset(
        f"{BUCKET}/{release}/theme={theme}/type={kind}", filesystem=s3, format="parquet"
    )
    xmin, ymin, xmax, ymax = bbox
    flt = (
        (pc.field("bbox", "xmin") < xmax)
        & (pc.field("bbox", "xmax") > xmin)
        & (pc.field("bbox", "ymin") < ymax)
        & (pc.field("bbox", "ymax") > ymin)
    )
    cols = [c for c in COLUMNS[layer] if c in dataset.schema.names]
    table = dataset.to_table(columns=cols, filter=flt)
    clip = box(*bbox)
    features = []
    for row in table.to_pylist():
        geom = wkb.loads(row.pop("geometry"))
        if not geom.intersects(clip):
            continue
        if layer not in ("buildings", "building_parts"):
            geom = geom.intersection(clip)
            if geom.is_empty:
                continue
        g = project(geom, enu)
        if g is None:
            continue
        props = {k: clean(v) for k, v in row.items() if v is not None}
        if "names" in props:
            props["name"] = (props.pop("names") or {}).get("primary")
        if "sources" in props:
            props["sources"] = sorted({s.get("dataset") for s in props["sources"] or [] if s})
        features.append({"geometry": g, **{k: v for k, v in props.items() if v is not None}})
    out.write_text(
        json.dumps(
            {"layer": layer, "release": release, "features": features}, separators=(",", ":")
        )
    )
    return len(features)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path, help="project/<scene>/configs/image_to_threejs.json")
    p.add_argument("out", type=Path, help="output directory (e.g. project/<scene>/input/overture)")
    p.add_argument("--layers", nargs="*", default=list(LAYERS))
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    origin, half = cfg["origin"], cfg["domain_m"] / 2
    enu = Enu(origin["longitude"], origin["latitude"])
    bbox = enu.inverse_bbox(half)
    args.out.mkdir(parents=True, exist_ok=True)
    index = {
        "release": cfg["overture_release"],
        "bbox_wgs84": bbox,
        "origin": origin,
        "license": "Overture Maps (ODbL for OSM-derived features; see docs.overturemaps.org)",
        "layers": {},
    }
    for layer in args.layers:
        path = args.out / f"{layer}.json"
        n = fetch(layer, cfg["overture_release"], bbox, enu, path)
        index["layers"][layer] = {
            "path": path.name,
            "features": n,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        print(f"{layer}: {n} features -> {path}")
    (args.out / "index.json").write_text(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
