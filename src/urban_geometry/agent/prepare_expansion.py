"""Select a bounded museum/campus district from existing licensed OSM data.
Run with south_kensington/.venv/bin/python. Does not fetch or overwrite old outputs.
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import json, math, copy, hashlib, shutil
from pathlib import Path
import numpy as np
import mapbox_earcut as earcut
from pyproj import Transformer
from shapely.geometry import Polygon, box, LineString, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, transform

ROOT = authoring_path()
WORK = ROOT.parents[1]
OLD = WORK / "south_kensington"
if (ROOT / "exports").exists():
    raise SystemExit(
        "Preparation is initialization only: existing exports and locally refined modules must not be overwritten. Build from the current expansion sources."
    )


def save(p, d):
    (authoring_path(p)).parent.mkdir(parents=True, exist_ok=True)
    (authoring_path(p)).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [orient(g, sign=1)]
    return [p for q in getattr(g, "geoms", []) for p in parts(q)]


def shape(gs):
    return unary_union([Polygon(p["outer"], p.get("holes", [])) for p in gs])


def serialize(g):
    out = []
    for p in parts(g):
        rings = [list(p.exterior.coords)[:-1]] + [list(i.coords)[:-1] for i in p.interiors]
        vv = np.array([v for r in rings for v in r], dtype=np.float64)
        ends = np.cumsum([len(r) for r in rings], dtype=np.uint32)
        tris = vv[earcut.triangulate_float64(vv, ends).reshape(-1, 3)].tolist()
        area = sum(
            abs(
                (t[1][0] - t[0][0]) * (t[2][1] - t[0][1])
                - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])
            )
            / 2
            for t in tris
        )
        assert abs(area - p.area) < max(0.001, p.area * 1e-7)
        out.append({"outer": rings[0], "holes": rings[1:], "triangles": tris})
    return out


DATA = (
    ROOT / "references/outer_source"
    if (ROOT / "references/outer_source/geometry.json").exists()
    else OLD
)
source = json.loads((DATA / "geometry.json").read_text())
ox, oy = source["origin_projected_m"]
tf = Transformer.from_crs(4326, source["crs"], always_xy=True)
inv = Transformer.from_crs(source["crs"], 4326, always_xy=True)


def xy(lon, lat, z=None):
    x, y = tf.transform(lon, lat)
    return x - ox, y - oy


bbox = [-0.1821, 51.4938, -0.1680, 51.5029]
aoi = transform(xy, box(*bbox))
campus = json.loads((ROOT.parent / "references/campus/campus_geometry.json").read_text())
campus_ids = {f"{b.get('osm_type', 'way')}-{b['id']}" for b in campus["buildings"]}
rows = []
excluded = []
for f in source["buildings"]:
    g = shape(f["geometry"])
    if f["id"] in campus_ids:
        excluded.append(
            {
                "id": f["id"],
                "reason": "Inherited detailed campus object, not replaced by generic model",
            }
        )
        continue
    if not g.intersects(aoi):
        continue
    f = copy.deepcopy(f)
    f["boundary_crossing"] = not aoi.covers(g)
    rows.append(f)
# Keep required mapped parent/parts if the AOI touches any member.
kept = {f["id"] for f in rows}
lookup = {f["id"]: f for f in source["buildings"]}
for f in list(rows):
    for oid in [f.get("parent_building_id")] + f.get("part_ids", []):
        if oid in lookup and oid not in kept and oid not in campus_ids:
            extra = copy.deepcopy(lookup[oid])
            extra["boundary_crossing"] = not aoi.covers(shape(extra["geometry"]))
            rows.append(extra)
            kept.add(oid)
landmarks = {
    "way-372860405": "royal_albert_hall",
    "way-27765400": "royal_college_music",
    "way-24436446": "natural_history",
    "way-27765411": "science_museum",
    "relation-29795": "victoria_albert",
}
assert set(landmarks) <= kept
# Science gallery roof split; mapped plan conserved, elevations explicitly estimated.
f = next(f for f in rows if f["id"] == "way-27765411")
g = shape(f["geometry"])
a = np.array([907.0389694146579, -328.67046609614044])
b = np.array([896.3357559732394, -261.7295569181442])
t = (b - a) / np.linalg.norm(b - a)
n = np.array([t[1], -t[0]])
clip = Polygon(
    [a - t * 1000 + n * 10, a + t * 1000 + n * 10, a + t * 1000 - n * 62, a - t * 1000 - n * 62]
)
high = g.intersection(clip)
low = g.difference(clip)
f["detail_parameters"]["roof_zones"] = [
    {"height_m": 26.0, "geometry": serialize(high)},
    {"height_m": 12.8, "geometry": serialize(low)},
]
line = LineString([a - t * 1000 - n * 62, a + t * 1000 - n * 62]).intersection(g)
lines = [line] if line.geom_type == "LineString" else list(getattr(line, "geoms", []))
f["detail_parameters"]["roof_step_segments"] = [
    list(l.coords) for l in lines if l.geom_type == "LineString"
]
f["evidence_source_ids"].append("science-entrance-2004")
next(b for b in rows if b["id"] == "relation-29795")["detail_parameters"]["entrance_xy"] = [
    1066.87111731607,
    -444.78926682751626,
]
# Reuse the existing coordinate frame for building authoring, transform new objects at assembly.
lon0, lat0 = campus["origin_wgs84"]
kx = 111320 * math.cos(math.radians(lat0))
ky = 111320
samples = np.array(
    [
        [x, y, 1.0]
        for x in np.linspace(aoi.bounds[0], aoi.bounds[2], 5)
        for y in np.linspace(aoi.bounds[1], aoi.bounds[3], 5)
    ]
)
ll = np.array([inv.transform(x + ox, y + oy) for x, y, _ in samples])
target = np.column_stack(((ll[:, 0] - lon0) * kx, (ll[:, 1] - lat0) * ky))
coef = np.linalg.lstsq(samples, target, rcond=None)[0]
res = np.linalg.norm(samples @ coef - target, axis=1)
save(
    "coordinate_contract.json",
    {
        "authoring_crs": source["crs"],
        "authoring_origin_projected_m": [ox, oy],
        "export_frame": "Inherited campus local equirectangular approximation, not engineering CRS",
        "origin_wgs84": [lon0, lat0],
        "axes": "X east Y north Z up, metres",
        "vertical_datum": "Inherited estimated flat ground; not surveyed elevation",
        "source_xy_to_campus_affine": coef.T.tolist(),
        "max_coordinate_linearization_error_m": float(max(res)),
        "campus_transformed": False,
        "note": "New assets transformed to existing campus coordinates; original campus geometry preserved.",
    },
)
# Remove additionally mapped parts already fully represented by campus geometry.
campus_union = unary_union([shape(b["geometry"]) for b in campus["buildings"]])


def to_campus(x, y, z=None):
    return coef[0, 0] * np.asarray(x) + coef[1, 0] * np.asarray(y) + coef[2, 0], coef[
        0, 1
    ] * np.asarray(x) + coef[1, 1] * np.asarray(y) + coef[2, 1]


filtered = []
for f in rows:
    g = transform(to_campus, shape(f["geometry"]))
    overlap = g.intersection(campus_union).area
    if overlap / max(g.area, 1e-9) > 0.985:
        excluded.append(
            {
                "id": f["id"],
                "reason": "Mapped part already covered by inherited campus footprint",
                "overlap_fraction": overlap / g.area,
            }
        )
    else:
        filtered.append(f)
rows = filtered
region = {
    "bbox_wgs84": bbox,
    "scope": "Imperial campus plus Royal College of Music, Royal Albert Hall, Natural History, Science and Victoria and Albert museums and intersecting surrounding street-block buildings",
    "boundary_basis": "Coordinator operational boundary for named places and adjacent blocks, 2026-09-09; not surveyed ownership",
    "quality_target": "RSM authored geometry standard; individual evidence/visual acceptance tracked separately",
    "native_compression": False,
    "draco": False,
    "paid_request_cap": 0,
}
save("region.json", region)
save(
    "region.geojson",
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "South Kensington campus and museums expansion"},
                "geometry": mapping(box(*bbox)),
            }
        ],
    },
)
old_sources = json.loads((OLD / "references/sources.json").read_text())
photo = {
    "id": "science-entrance-2004",
    "provider": "Wikimedia Commons",
    "url": "https://commons.wikimedia.org/wiki/File:ScienceMuseum.jpg",
    "kind": "street_photo",
    "accessed_at": "2026-09-09",
    "capture_date": "2004-03-27",
    "viewpoint": "central Exhibition Road east entrance",
    "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
    "attribution": "A. Brady, ScienceMuseum.jpg, 2004; modified into estimated facade geometry",
    "rights_review": "Explicit CC BY-SA 3.0 on Commons file page inspected 2026-09-09; photo-derived component shared under same licence",
    "geometry_derivation": "allowed",
    "export_texture_use": False,
    "actually_inspected": True,
    "local_file": "science/front_2004.jpg",
    "sha256": hashlib.sha256(
        (OLD / "references/expansion_science/front_2004.jpg").read_bytes()
    ).hexdigest(),
    "observations": [
        "Rusticated podium with recessed central rectangular entrance and projecting lintel",
        "Round giant columns across two window levels; volute capitals",
        "Dark mullioned recessed windows and stone stringcourses",
    ],
    "uncertainty": [
        "Only central historic elevation covered; upper roof and other elevations unknown"
    ],
}
old_sources.append(photo)
if (DATA / "east_source_record.json").exists():
    old_sources.append(json.loads((DATA / "east_source_record.json").read_text()))
for directory in ["expansion_rcm", "expansion_nhm", "expansion_va", "expansion_hall"]:
    p = OLD / "references" / directory / "source_records.json"
    if p.exists():
        records = json.loads(p.read_text())
        records = records if isinstance(records, list) else records.get("sources", [records])
        old_sources.extend(records)
        for r in records:
            if (
                r.get("geometry_derivation") == "allowed"
                and r.get("actually_inspected")
                and r.get("kind") in ["street_photo", "image"]
            ):
                oid = {
                    "expansion_rcm": "way-27765400",
                    "expansion_nhm": "way-24436446",
                    "expansion_va": "relation-29795",
                    "expansion_hall": "way-372860405",
                }[directory]
                next(f for f in rows if f["id"] == oid)["evidence_source_ids"].append(r["id"])
unique = {r["id"]: r for r in old_sources}
used = {sid for f in rows for sid in f["evidence_source_ids"]}
save("references/sources.json", [unique[k] for k in sorted(used)])
for sid in used:
    r = unique[sid]
    name = r.get("local_file", r.get("local_filename"))
    if name:
        candidate = OLD / name
        if not candidate.exists():
            candidate = OLD / "references" / name
        if candidate.is_file():
            target = ROOT / name if name.startswith("references/") else ROOT / "references" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)
for slug in ["royal_albert_hall", "natural_history", "royal_college_music", "victoria_albert"]:
    p = OLD / "docs" / f"{slug}_expansion.md"
    if p.exists():
        shutil.copy2(p, ROOT / "docs" / p.name)

(ROOT / "references/science").mkdir(exist_ok=True)
shutil.copy2(
    OLD / "references/expansion_science/front_2004.jpg", ROOT / "references/science/front_2004.jpg"
)
for directory in ["expansion_rcm", "expansion_nhm", "expansion_va", "expansion_hall"]:
    if (OLD / "references" / directory).exists():
        shutil.copytree(
            OLD / "references" / directory, ROOT / "references" / directory, dirs_exist_ok=True
        )
# Campus bounding rectangular presentation ground is subtracted from new site layers.
# It will be refined from the recovered mesh bounds by the integration stage.
context = json.loads((DATA / "context.json").read_text())
context["ground"] = serialize(aoi)
# Preserve the existing campus scene's site surfaces inside its rectangular domain.
ci = np.linalg.inv(np.vstack([coef.T, [0, 0, 1]]))


def campus_to_source(x, y, z=None):
    return ci[0, 0] * np.asarray(x) + ci[0, 1] * np.asarray(y) + ci[0, 2], ci[1, 0] * np.asarray(
        x
    ) + ci[1, 1] * np.asarray(y) + ci[1, 2]


old_site = transform(campus_to_source, box(*campus["site_bounds"]))
context["ground"] = serialize(aoi.difference(old_site))
context["features"] = [
    dict(f, geometry=serialize(shape(f["geometry"]).intersection(aoi).difference(old_site)))
    for f in context["features"]
    if not shape(f["geometry"]).intersection(aoi).difference(old_site).is_empty
]
save("context.json", context)
save("geometry.json", dict(source, buildings=rows))
save(
    "interfaces.json",
    {
        "shared_walls": "Inherited OSM-derived wall intervals retained; site-specific landmark audit required",
        "campus_ownership": sorted(campus_ids),
        "campus_not_rebuilt": True,
    },
)
modules = {f["id"]: landmarks.get(f["id"], "urban") for f in rows if not f.get("assembly_only")}
save("src/modules.json", modules)
for filename in ["detailed_common.py", "urban_building.py", "site_context.py"]:
    shutil.copy2(OLD / "src" / filename, agent_src() / filename)
(agent_src() / "buildings").mkdir(exist_ok=True)
for slug in set(modules.values()):
    p = OLD / "src/buildings" / f"{slug}.py"
    if p.exists():
        shutil.copy2(p, agent_src() / "buildings" / p.name)
save(
    "docs/inventory.json",
    {
        "new_mapped_records": len(rows),
        "existing_campus_records": len(campus_ids),
        "landmarks": landmarks,
        "boundary_crossing": [f["id"] for f in rows if f["boundary_crossing"]],
        "excluded_duplicates": excluded,
        "generic_pending_refinement": [f["id"] for f in rows if f["id"] not in landmarks],
        "all_buildings_at_RSM_standard": False,
    },
)
save(
    "progress.json",
    {
        "status": "authoring",
        "landmarks": {
            oid: {
                "module": slug,
                "state": "module authored, integration and visual checks pending"
                if (agent_src() / "buildings" / f"{slug}.py").exists()
                else "evidence and module in progress",
            }
            for oid, slug in landmarks.items()
        },
        "inventory_total": len(rows) + len(campus_ids),
        "full_detail_delivered": False,
    },
)
print(
    "EXPANSION_INVENTORY",
    len(rows),
    "new records +",
    len(campus_ids),
    "campus; coordinate residual",
    max(res),
)
