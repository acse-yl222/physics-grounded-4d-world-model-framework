"""OpenStreetMap railway subset of a scene from the planet ORC (AWS Open Data).

Reuses the stripe reader of ``traffic.corridor_sumo.osm_extract`` (``Planet``: binary
search over stripe first keys, retries, per-stripe cache):

1. **Overture ids.** OSM way ids of Overture transportation segments with
   ``subtype = rail`` in the buffered bbox (``sources[].record_id``), and OSM ids of
   Overture base ``infrastructure`` transit features (``subway_station``,
   ``railway_station``, ``platform``).
2. **Relations** (all relation stripes): ``route`` = subway/train/light_rail with a
   member among the Overture rail ways, their ``route_master`` relations, and
   ``public_transport=stop_area`` relations with a member among those ids or ways.
3. **Ways**: the Overture rail ways, the ways of those route relations and the
   platform / station ways referenced by stop areas, routes or Overture.
4. **Nodes** (all node stripes, one pass): coordinates of every node referenced by the
   kept ways, plus every node inside the bbox tagged as a station, entrance, platform
   or stop (``railway``/``public_transport``/``station``/``subway``/``train`` keys).
   Entrances are usually standalone nodes, so this full scan is needed (~40 min).

Writes ``project/<scene>/input/underground/osm/osm_rail.json.gz`` and ``index.json``
(planet object ETag/LastModified, rules, counts, sha256, licence ODbL 1.0); per-stripe
intermediates go to ``cache/<scene>/underground/osm/`` (resume after interruption).

  PYTHONPATH=src python3 -m transit.underground.osm imperial_corridor
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from traffic.corridor_sumo.osm_extract import (
    LICENCE,
    Planet,
    _cached,
    _parallel,
    _tags,
    buffered_bbox,
    extract_ways,
    sha256,
    type_range,
)

from .config import load_scene, log

ROUTES = {"subway", "train", "light_rail", "railway", "tram"}
RAILWAYS = {"subway", "rail", "light_rail", "narrow_gauge", "construction", "disused"}
FEATURE_KEYS = ("railway", "public_transport", "station", "subway", "train")
INFRA_CLASSES = {"subway_station", "railway_station", "platform"}


def feature_tags(tags: dict) -> bool:
    """Whether a node's tags make it a railway station/entrance/platform/stop feature."""
    if not tags:
        return False
    if tags.get("railway") in {
        "subway_entrance",
        "train_station_entrance",
        "station",
        "halt",
        "platform",
        "stop",
        "tram_stop",
    }:
        return True
    if tags.get("public_transport") in {"station", "platform", "stop_position", "stop_area"}:
        return bool(
            tags.get("railway")
            or tags.get("train") == "yes"
            or tags.get("subway") == "yes"
            or tags.get("light_rail") == "yes"
            or tags.get("station")
        )
    return tags.get("entrance") is not None and tags.get("railway") is not None


def id_key(ids) -> str:
    return hashlib.sha1(",".join(map(str, sorted(ids))).encode()).hexdigest()[:10]


# ---------------------------------------------------------------- Overture ids


def overture_ids(release: str, bbox: tuple[float, float, float, float]) -> dict:
    """OSM ids of Overture rail segments and transit infrastructure in ``bbox``."""
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    from pyarrow import fs

    s3 = fs.S3FileSystem(anonymous=True, region="us-west-2")
    xmin, ymin, xmax, ymax = bbox
    in_box = (
        (pc.field("bbox", "xmin") < xmax)
        & (pc.field("bbox", "xmax") > xmin)
        & (pc.field("bbox", "ymin") < ymax)
        & (pc.field("bbox", "ymax") > ymin)
    )

    def table(theme, kind, columns, flt):
        dataset = ds.dataset(
            f"overturemaps-us-west-2/release/{release}/theme={theme}/type={kind}",
            filesystem=s3,
            format="parquet",
        )
        return dataset.to_table(columns=columns, filter=in_box & flt)

    def osm_refs(sources):
        for s in sources or []:
            rec = (s or {}).get("record_id") or ""
            if s.get("dataset") == "OpenStreetMap" and rec[:1] in "nwr":
                yield rec[0], int(rec[1:].partition("@")[0])

    seg = table("transportation", "segment", ["class", "sources"], pc.field("subtype") == "rail")
    ways: dict[int, str] = {}
    for cls, sources in zip(
        seg.column("class").to_pylist(), seg.column("sources").to_pylist(), strict=True
    ):
        for kind, ref in osm_refs(sources):
            if kind == "w":
                ways[ref] = cls
    infra = table(
        "base", "infrastructure", ["class", "sources", "names"], pc.field("subtype") == "transit"
    )
    features = []
    for cls, sources, names in zip(
        infra.column("class").to_pylist(),
        infra.column("sources").to_pylist(),
        infra.column("names").to_pylist(),
        strict=True,
    ):
        if cls not in INFRA_CLASSES:
            continue
        for kind, ref in osm_refs(sources):
            features.append(
                {"type": kind, "ref": ref, "class": cls, "name": (names or {}).get("primary")}
            )
    return {
        "release": release,
        "bbox_wgs84": list(bbox),
        "rail_segments": seg.num_rows,
        "rail_ways": {str(k): v for k, v in sorted(ways.items())},
        "transit_features": features,
    }


# ---------------------------------------------------------------- relations


def read_relations(planet: Planet, rail_ways: set[int], cache: Path) -> list[dict]:
    """Route (subway/train/light_rail/...), route_master and stop_area relations.

    Routes are kept when a way member is in ``rail_ways``; route masters and stop areas
    are kept globally here (they are small) and filtered by the caller.
    """
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    first, last = type_range(2, planet.n_stripes, planet.first_keys)
    sub = cache / f"relations_{id_key(rail_ways)}"
    sub.mkdir(parents=True, exist_ok=True)
    way_set = pa.array(sorted(rail_ways), pa.int64())
    route_values = pa.array(sorted(ROUTES))

    def one(stripe):
        def compute():
            head = planet.read(stripe, ["type", "tags"])
            tags = head.column("tags")
            kind = pc.map_lookup(tags, "type", "first")
            route = pc.map_lookup(tags, "route", "first")
            master = pc.map_lookup(tags, "route_master", "first")
            pt = pc.map_lookup(tags, "public_transport", "first")
            is_route = pc.and_kleene(pc.equal(kind, "route"), pc.is_in(route, route_values))
            is_master = pc.and_kleene(
                pc.equal(kind, "route_master"), pc.is_in(master, route_values)
            )
            is_area = pc.equal(pt, "stop_area")
            mask = pc.and_(
                pc.equal(head.column("type"), "relation"),
                pc.fill_null(pc.or_kleene(pc.or_kleene(is_route, is_master), is_area), False),
            )
            route_mask = np.asarray(pc.fill_null(is_route, False))
            del head, tags, kind, route, master, pt
            if not pc.any(mask).as_py():
                return []
            idx = np.flatnonzero(np.asarray(mask))
            t = planet.read(stripe, ["id", "tags", "members"]).take(pa.array(idx, pa.int64()))
            members = t.column("members")
            if hasattr(members, "combine_chunks"):
                members = members.combine_chunks()
            flat = pc.list_flatten(members)
            parents = np.asarray(pc.list_parent_indices(members))
            hit = np.asarray(
                pc.fill_null(
                    pc.and_(
                        pc.equal(pc.struct_field(flat, "type"), "way"),
                        pc.is_in(pc.struct_field(flat, "ref"), way_set),
                    ),
                    False,
                )
            )
            touched = set(np.unique(parents[hit]).tolist())
            rows = []
            for k, (rid, tg, mem) in enumerate(
                zip(
                    t.column("id").to_pylist(),
                    t.column("tags").to_pylist(),
                    t.column("members").to_pylist(),
                    strict=True,
                )
            ):
                if route_mask[idx[k]] and k not in touched:
                    continue
                rows.append({"id": rid, "tags": _tags(tg), "members": mem or []})
            return rows

        return _cached(sub / f"{stripe:05d}.json.gz", compute)

    out = []
    for rows in _parallel(one, range(first, last + 1), min(planet.threads, 3), "relations"):
        out += rows
    return out


# ---------------------------------------------------------------- nodes


def scan_nodes(
    planet: Planet, bbox: tuple[float, float, float, float], refs: set[int], cache: Path
) -> tuple[dict[int, list], dict[int, list]]:
    """One pass over all node stripes.

    Returns ``(ref_nodes, features)``: ``{id: [lat, lon, tags]}`` (7-decimal strings as
    stored) for every id in ``refs`` and for every node inside ``bbox`` whose tags pass
    ``feature_tags``.
    """
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    first, last = type_range(0, planet.n_stripes, planet.first_keys)
    sub = cache / f"nodes_{id_key(refs)}"
    sub.mkdir(parents=True, exist_ok=True)
    wanted = pa.array(sorted(refs), pa.int64())
    lon0, lat0, lon1, lat1 = bbox
    log(f"  node scan: stripes {first}..{last}, {len(refs)} way node refs")

    def one(stripe):
        def compute():
            t = planet.read(stripe, ["type", "id", "lat", "lon"])
            lat = pc.cast(t.column("lat"), pa.float64())
            lon = pc.cast(t.column("lon"), pa.float64())
            node = pc.equal(t.column("type"), "node")
            box = pc.and_(
                pc.and_(pc.greater_equal(lat, lat0), pc.less_equal(lat, lat1)),
                pc.and_(pc.greater_equal(lon, lon0), pc.less_equal(lon, lon1)),
            )
            ref = pc.is_in(t.column("id"), wanted)
            box = np.asarray(pc.fill_null(pc.and_(node, box), False))
            ref = np.asarray(pc.fill_null(pc.and_(node, ref), False))
            idx = np.flatnonzero(box | ref)
            del t, lat, lon
            if not len(idx):
                return {"refs": {}, "features": {}}
            sel = planet.read(stripe, ["id", "lat", "lon", "tags"]).take(pa.array(idx, pa.int64()))
            refs_out, feats = {}, {}
            for k, (nid, la, lo, tg) in enumerate(
                zip(
                    sel.column("id").to_pylist(),
                    pc.cast(sel.column("lat"), pa.string()).to_pylist(),
                    pc.cast(sel.column("lon"), pa.string()).to_pylist(),
                    sel.column("tags").to_pylist(),
                    strict=True,
                )
            ):
                tags = _tags(tg)
                if ref[idx[k]]:
                    refs_out[str(nid)] = [la, lo, tags]
                if box[idx[k]] and feature_tags(tags):
                    feats[str(nid)] = [la, lo, tags]
            return {"refs": refs_out, "features": feats}

        return _cached(sub / f"{stripe:05d}.json.gz", compute)

    ref_nodes: dict[int, list] = {}
    features: dict[int, list] = {}
    for res in _parallel(one, range(first, last + 1), planet.threads, "node scan"):
        ref_nodes.update({int(k): v for k, v in res["refs"].items()})
        features.update({int(k): v for k, v in res["features"].items()})
    return ref_nodes, features


# ---------------------------------------------------------------- driver


def keep_rail_way(tags: dict) -> bool:
    return tags.get("railway") in RAILWAYS or tags.get("disused:railway") is not None


def platform_like(tags: dict) -> bool:
    return (
        tags.get("railway") in {"platform", "station"}
        or tags.get("public_transport") in {"platform", "station"}
        or tags.get("building") == "train_station"
    )


def extract(scene: str, threads: int = 24) -> dict:
    ctx = load_scene(scene)
    cfg, storage = ctx["cfg"], ctx["storage"]
    bbox = buffered_bbox(ctx["origin"], ctx["half"], cfg["buffer_m"])
    cache = storage.scratch(scene, "underground", "osm")
    cache.mkdir(parents=True, exist_ok=True)
    out_dir = storage.assets(scene, "input") / cfg.get("input_dir", "underground") / "osm"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    timings = {}

    release = cfg["overture_release"]
    ids_path = cache / f"overture_ids_{release}_{int(cfg['buffer_m'])}.json"
    if ids_path.is_file():
        ov = json.loads(ids_path.read_text())
    else:
        log(f"Overture {release}: rail segments and transit infrastructure in {bbox} ...")
        ov = overture_ids(release, bbox)
        ids_path.write_text(json.dumps(ov))
    rail_ways = {int(k) for k in ov["rail_ways"]}
    timings["overture_s"] = round(time.monotonic() - t0, 1)
    log(f"  {ov['rail_segments']} rail segments -> {len(rail_ways)} OSM ways")

    planet = Planet(threads=threads)
    obj = planet.object_info()
    log(f"planet: {obj['uri']} etag {obj['etag']} last modified {obj['last_modified']}")
    meta_path = cache / "planet.json"
    if meta_path.is_file():
        old = json.loads(meta_path.read_text())
        if old.get("etag") != obj["etag"]:
            raise SystemExit(
                f"planet object changed (cached {old.get('etag')}, now {obj['etag']}); "
                f"delete {cache} to restart"
            )
    meta_path.write_text(json.dumps(obj, indent=2))

    t = time.monotonic()
    relations = read_relations(planet, rail_ways, cache)
    feat_nodes = {f["ref"] for f in ov["transit_features"] if f["type"] == "n"}
    feat_ways = {f["ref"] for f in ov["transit_features"] if f["type"] == "w"}
    routes = [r for r in relations if r["tags"].get("type") == "route"]
    route_ids = {r["id"] for r in routes}
    masters = [
        r
        for r in relations
        if r["tags"].get("type") == "route_master"
        and any(m["type"] == "relation" and m["ref"] in route_ids for m in r["members"])
    ]
    route_ways = {m["ref"] for r in routes for m in r["members"] if m["type"] == "way"}
    areas_all = [r for r in relations if r["tags"].get("public_transport") == "stop_area"]
    timings["relations_s"] = round(time.monotonic() - t, 1)
    log(f"relations: {len(routes)} routes, {len(masters)} route masters")

    t = time.monotonic()
    platform_refs = {
        m["ref"]
        for r in routes
        for m in r["members"]
        if m["type"] == "way" and (m.get("role") or "").startswith("platform")
    }

    any_ways = rail_ways | feat_ways | route_ways

    def area_hit(r):
        return any(
            (m["type"] == "node" and m["ref"] in feat_nodes)
            or (m["type"] == "way" and m["ref"] in any_ways)
            for m in r["members"]
        )

    areas = [r for r in areas_all if area_hit(r)]
    area_ways = {m["ref"] for r in areas for m in r["members"] if m["type"] == "way"}
    way_ids = rail_ways | route_ways | feat_ways | platform_refs | area_ways
    raw = extract_ways(planet, way_ids, cache / f"ways_{id_key(way_ids)}")
    ways = {
        k: v
        for k, v in raw.items()
        if k in rail_ways or k in route_ways or keep_rail_way(v["tags"]) or platform_like(v["tags"])
    }
    timings["ways_s"] = round(time.monotonic() - t, 1)
    log(f"ways: {len(raw)} of {len(way_ids)} found, {len(ways)} kept")

    t = time.monotonic()
    refs = {n for w in ways.values() for n in w["nds"]}
    area_nodes = {m["ref"] for r in areas for m in r["members"] if m["type"] == "node"}
    nodes, features = scan_nodes(planet, bbox, refs | area_nodes | feat_nodes, cache)
    timings["nodes_s"] = round(time.monotonic() - t, 1)
    # stop areas found through scanned features (entrances / stations)
    have = {r["id"] for r in areas}
    extra = [
        r
        for r in areas_all
        if r["id"] not in have
        and any(m["type"] == "node" and m["ref"] in features for m in r["members"])
    ]
    areas += extra
    log(f"nodes: {len(nodes)} of {len(refs)} refs; {len(features)} tagged features in bbox")

    doc = {
        "bbox_wgs84": list(bbox),
        "ways": {str(k): v for k, v in sorted(ways.items())},
        "nodes": {str(k): v for k, v in sorted(nodes.items())},
        "features": {str(k): v for k, v in sorted(features.items())},
        "routes": sorted(routes, key=lambda r: r["id"]),
        "route_masters": sorted(masters, key=lambda r: r["id"]),
        "stop_areas": sorted(areas, key=lambda r: r["id"]),
        "overture": {k: v for k, v in ov.items() if k != "rail_ways"},
        "overture_rail_way_class": ov["rail_ways"],
    }
    path = out_dir / "osm_rail.json.gz"
    with (
        open(path, "wb") as raw_f,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw_f, mtime=0) as f,
    ):
        f.write(json.dumps(doc, separators=(",", ":")).encode())
    rail_counts: dict[str, int] = {}
    for w in ways.values():
        v = w["tags"].get("railway", "other")
        rail_counts[v] = rail_counts.get(v, 0) + 1
    feat_counts: dict[str, int] = {}
    for _, _, tags in features.values():
        v = tags.get("railway") or f"public_transport={tags.get('public_transport')}"
        feat_counts[v] = feat_counts.get(v, 0) + 1
    timings["total_s"] = round(time.monotonic() - t0, 1)
    index = {
        "schema": "underground-osm-subset-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": obj,
        "licence": LICENCE,
        "selection": {
            "bbox_wgs84": [round(v, 7) for v in bbox],
            "domain_half_m": ctx["half"],
            "buffer_m": cfg["buffer_m"],
            "origin": ctx["origin"],
            "overture": {
                "release": release,
                "rail_segments": ov["rail_segments"],
                "rail_ways": len(rail_ways),
                "transit_features": len(ov["transit_features"]),
            },
            "way_rule": "OSM ways of Overture rail segments, ways of route relations "
            f"(route in {sorted(ROUTES)}) touching them, platform/station ways of those "
            "routes, of stop areas and of Overture transit infrastructure",
            "relation_rule": "route relations with a way among the Overture rail ways; "
            "their route_master; public_transport=stop_area with a member among the "
            "Overture/route ids or among the scanned features",
            "node_rule": "all nodes of kept ways (any location) plus nodes inside the bbox "
            "with station/entrance/platform/stop railway or public_transport tags "
            "(full scan of the node stripes)",
        },
        "counts": {
            "ways": len(ways),
            "ways_missing_in_planet": len(way_ids - set(raw)),
            "ways_by_railway": dict(sorted(rail_counts.items())),
            "nodes": len(nodes),
            "node_refs_missing": len(refs - set(nodes)),
            "features": len(features),
            "features_by_kind": dict(sorted(feat_counts.items())),
            "route_relations": len(routes),
            "route_masters": len(masters),
            "stop_areas": len(areas),
        },
        "stripes_read": planet.reads,
        "timings_s": timings,
        "files": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}},
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    log(json.dumps(index["counts"], indent=2))
    return index


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--threads", type=int, default=24)
    args = p.parse_args(argv)
    extract(args.scene, args.threads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
