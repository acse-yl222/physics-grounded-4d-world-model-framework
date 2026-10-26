"""Extract the OpenStreetMap road subset of a scene from the planet ORC on AWS Open Data.

The OSM planet is published as one ORC file (``s3://osm-pds/planet/planet-latest.orc``,
anonymous, us-east-1). Its rows are sorted by element type (nodes, ways, relations) and
by id within a type, so the stripes holding a given id set are found by binary search
over the stripes' first ``(type, id)`` keys, and only the needed columns of those
stripes are read (in parallel). Nothing like the whole planet is downloaded.

1. **Way ids** come from Overture transportation segments of the buffered domain
   (``sources[].record_id`` = ``w<id>@<version>``, dataset OpenStreetMap).
2. **Ways**: the stripes with those ids are read (``id, tags, nds``); ways whose
   ``highway`` value can carry motor vehicles or buses are kept (``keep_way``). Ways
   created after the Overture snapshot are picked up from the newest way stripes when
   they are such highways sharing a node with a kept way.
3. **Nodes**: all node refs of the kept ways (``id, tags, lat, lon``); coordinates for
   all refs, tags for tagged nodes (signals, crossings, give way, ...).
4. **Relations**: ``type=restriction`` (and ``restriction:*``) relations whose way
   members are all kept; ``route=bus`` relations go to a separate JSON for later use.
5. A standard OSM XML (``osm.xml.gz``) plus ``index.json`` (source object, ETag,
   LastModified, bbox, counts, sha256, licence ODbL 1.0) is written to
   ``project/<scene>/input/osm/``. Per-stripe intermediates are cached under
   ``cache/<scene>/traffic_sumo/osm/`` so an interrupted extraction resumes.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.osm_extract imperial_corridor
"""

from __future__ import annotations

import argparse
import bisect
import contextlib
import gzip
import hashlib
import json
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import quoteattr

BUCKET_REGION = "us-east-1"
PLANET = "osm-pds/planet/planet-latest.orc"
TYPE_RANK = {"node": 0, "way": 1, "relation": 2}
LICENCE = {
    "name": "Open Data Commons Open Database License (ODbL) 1.0",
    "url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "attribution": "© OpenStreetMap contributors",
    "copyright": "https://www.openstreetmap.org/copyright",
}
# highway values SUMO needs for motor vehicles and buses. Footways, paths, cycleways,
# steps, bridleways, corridors and proposed/abandoned/construction roads are not
# imported; a pedestrian street is kept only when buses/psv/motor vehicles may use it.
VEHICLE_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "road",
    "busway",
    "bus_guideway",
}
OPEN_VALUES = {"yes", "designated", "permissive", "destination"}


def log(message: str) -> None:
    print(message, flush=True)


def keep_way(tags: dict) -> bool:
    """Whether an OSM way belongs in the vehicle network."""
    hw = tags.get("highway")
    if hw in VEHICLE_HIGHWAYS:
        return tags.get("area") != "yes"
    if hw == "pedestrian":
        return any(tags.get(k) in OPEN_VALUES for k in ("bus", "psv", "motor_vehicle"))
    return False


# ---------------------------------------------------------------- stripe search


def locate(
    keys: Iterable[tuple[int, int]],
    n_stripes: int,
    first_keys: Callable[[list[int]], dict[int, tuple[int, int]]],
) -> dict[int, list[tuple[int, int]]]:
    """Stripes holding ``keys`` in a file whose rows are sorted by key.

    ``first_keys(indices)`` returns the first ``(type_rank, id)`` key of each stripe
    asked for (it may fetch them in parallel). The search splits the sorted key list
    by the first key of the middle stripe of each open interval, one level at a time,
    so only O(touched stripes x log) first keys are read. Keys before the first
    stripe are dropped. Returns ``{stripe: [keys]}``; a key that is absent from the file
    is still assigned to the only stripe that could hold it.
    """
    wanted = sorted(set(keys))
    if not wanted or n_stripes <= 0:
        return {}
    known: dict[int, tuple[int, int]] = dict(first_keys([0]))
    wanted = wanted[bisect.bisect_left(wanted, known[0]) :]
    open_ = [(0, n_stripes, wanted)] if wanted else []
    done: dict[int, list[tuple[int, int]]] = {}
    while open_:
        mids = sorted({(lo + hi) // 2 for lo, hi, _ in open_ if hi - lo > 1} - set(known))
        if mids:
            known.update(first_keys(mids))
        nxt = []
        for lo, hi, ks in open_:
            if hi - lo == 1:
                done[lo] = ks
                continue
            mid = (lo + hi) // 2
            cut = bisect.bisect_left(ks, known[mid])
            if ks[:cut]:
                nxt.append((lo, mid, ks[:cut]))
            if ks[cut:]:
                nxt.append((mid, hi, ks[cut:]))
        open_ = nxt
    return dict(sorted(done.items()))


def type_range(
    rank: int, n_stripes: int, first_keys: Callable[[list[int]], dict[int, tuple[int, int]]]
) -> tuple[int, int]:
    """[first, last] stripe index that can hold rows of type ``rank``."""
    lo = locate([(rank, -(2**62))], n_stripes, first_keys)
    hi = locate([(rank, 2**62)], n_stripes, first_keys)
    first = min(lo) if lo else 0
    return first, max(hi) if hi else n_stripes - 1


class Planet:
    """Thread-safe stripe reader for the planet ORC (one ORCFile per thread)."""

    def __init__(self, path: str = PLANET, region: str = BUCKET_REGION, threads: int = 24):
        from pyarrow import fs, orc

        self._orc = orc
        self.fs = fs.S3FileSystem(anonymous=True, region=region)
        self.path = path
        self.threads = threads
        self._local = threading.local()
        self.n_stripes = self.file().nstripes
        self.n_rows = self.file().nrows
        self._first: dict[int, tuple[int, int]] = {}
        self.reads = 0

    def file(self):
        if not hasattr(self._local, "orc"):
            self._local.orc = self._orc.ORCFile(self.fs.open_input_file(self.path))
        return self._local.orc

    def object_info(self) -> dict:
        """Size, ETag and LastModified of the planet object (S3 HEAD via boto-free HTTP)."""
        import urllib.request

        bucket, key = self.path.split("/", 1)
        url = f"https://{bucket}.s3.{BUCKET_REGION}.amazonaws.com/{key}"
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as resp:
            headers = dict(resp.headers)
        return {
            "uri": f"s3://{self.path}",
            "https": url,
            "bytes": int(headers.get("Content-Length", 0)),
            "etag": headers.get("ETag", "").strip('"'),
            "last_modified": headers.get("Last-Modified"),
            "stripes": self.n_stripes,
            "rows": self.n_rows,
        }

    def read(self, stripe: int, columns: list[str]):
        for attempt in range(6):
            try:
                table = self.file().read_stripe(stripe, columns=columns)
                break
            except OSError as exc:  # transient S3 errors: reopen and retry with back-off
                if attempt == 5:
                    raise
                log(f"  stripe {stripe}: {exc}; retrying")
                del self._local.orc
                time.sleep(2 * (attempt + 1))
        self.reads += 1
        return table

    def first_keys(self, indices: list[int]) -> dict[int, tuple[int, int]]:
        todo = [i for i in indices if i not in self._first]

        def one(i):
            if i >= self.n_stripes:
                return i, (99, 0)
            t = self.read(i, ["type", "id"])
            return i, (TYPE_RANK[t.column("type")[0].as_py()], t.column("id")[0].as_py())

        if todo:
            with ThreadPoolExecutor(self.threads) as ex:
                self._first.update(ex.map(one, todo))
        return {i: self._first[i] for i in indices}


# ---------------------------------------------------------------- stripe extraction


def _parallel(fn, items, threads: int, label: str):
    """Run ``fn`` over ``items`` in a thread pool with progress logging."""
    items = list(items)
    out, t0 = [], time.monotonic()
    with ThreadPoolExecutor(threads) as ex:
        for k, res in enumerate(ex.map(fn, items), 1):
            out.append(res)
            if k == len(items) or k % max(1, len(items) // 20) == 0:
                rate = k / max(time.monotonic() - t0, 1e-9)
                eta = (len(items) - k) / rate if rate else 0
                log(f"  {label}: {k}/{len(items)} stripes, {rate:.2f}/s, eta {eta / 60:.1f} min")
    return out


def _cached(path: Path, compute):
    """JSON-gz cache of one stripe's extracted rows (resume after a crash)."""
    if path.is_file():
        with gzip.open(path, "rt") as f:
            return json.load(f)
    data = compute()
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump(data, f, separators=(",", ":"))
    tmp.rename(path)
    return data


def _tags(value) -> dict:
    return dict(value) if value else {}


def extract_ways(planet: Planet, way_ids: set[int], cache: Path) -> dict[int, dict]:
    """``{id: {tags, nds}}`` for the wanted ways that ``keep_way`` accepts."""
    import pyarrow as pa
    import pyarrow.compute as pc

    stripes = locate([(1, w) for w in way_ids], planet.n_stripes, planet.first_keys)
    (cache / "ways").mkdir(parents=True, exist_ok=True)
    wanted = pa.array(sorted(way_ids), pa.int64())

    def one(item):
        stripe, _keys = item

        def compute():
            t = planet.read(stripe, ["type", "id", "tags", "nds"])
            mask = pc.and_(pc.equal(t.column("type"), "way"), pc.is_in(t.column("id"), wanted))
            t = t.filter(mask)
            rows = {}
            for wid, tags, nds in zip(
                t.column("id").to_pylist(),
                t.column("tags").to_pylist(),
                t.column("nds").to_pylist(),
                strict=True,
            ):
                rows[str(wid)] = {"tags": _tags(tags), "nds": [n["ref"] for n in nds or []]}
            return rows

        return _cached(cache / "ways" / f"{stripe:05d}.json.gz", compute)

    found: dict[int, dict] = {}
    for rows in _parallel(one, stripes.items(), planet.threads, "ways"):
        found.update({int(k): v for k, v in rows.items()})
    return found


def newest_ways(
    planet: Planet, after_id: int, nodes: set[int], cache: Path, max_stripes: int = 40
) -> dict[int, dict]:
    """Vehicle highways with id > ``after_id`` that share a node with ``nodes``.

    Covers ways created (e.g. by splitting) after the Overture snapshot that supplied
    the way ids. Only the newest way stripes are read (at most ``max_stripes``).
    """
    import pyarrow as pa
    import pyarrow.compute as pc

    lo = min(locate([(1, after_id + 1)], planet.n_stripes, planet.first_keys))
    _, hi = type_range(1, planet.n_stripes, planet.first_keys)
    if hi - lo + 1 > max_stripes:
        log(
            f"  newest ways: {hi - lo + 1} stripes after way {after_id}; reading the last {max_stripes}"
        )
        lo = hi - max_stripes + 1
    node_set = pa.array(sorted(nodes), pa.int64())
    (cache / "ways_new").mkdir(parents=True, exist_ok=True)

    def one(stripe):
        def compute():
            t = planet.read(stripe, ["type", "id", "tags", "nds"])
            t = t.filter(
                pc.and_(pc.equal(t.column("type"), "way"), pc.greater(t.column("id"), after_id))
            )
            hw = pc.map_lookup(t.column("tags"), "highway", "first")
            t = t.filter(pc.is_valid(hw))
            rows = {}
            for wid, tags, nds in zip(
                t.column("id").to_pylist(),
                t.column("tags").to_pylist(),
                t.column("nds").to_pylist(),
                strict=True,
            ):
                tags = _tags(tags)
                refs = [n["ref"] for n in nds or []]
                if keep_way(tags) and refs:
                    rows[str(wid)] = {"tags": tags, "nds": refs}
            return rows

        return _cached(cache / "ways_new" / f"{stripe:05d}.json.gz", compute)

    out = {}
    for rows in _parallel(one, range(lo, hi + 1), planet.threads, "newest ways"):
        for k, v in rows.items():
            out[int(k)] = v
    member = set(node_set.to_pylist())
    return {k: v for k, v in out.items() if member.intersection(v["nds"])}


def extract_nodes(planet: Planet, node_ids: set[int], cache: Path) -> dict[int, list]:
    """``{id: [lat, lon, tags]}`` (lat/lon as 7-decimal strings, exactly as stored)."""
    import pyarrow as pa
    import pyarrow.compute as pc

    stripes = locate([(0, n) for n in node_ids], planet.n_stripes, planet.first_keys)
    (cache / "nodes").mkdir(parents=True, exist_ok=True)
    wanted = pa.array(sorted(node_ids), pa.int64())
    log(f"  nodes: {len(node_ids)} ids in {len(stripes)} stripes")

    def one(item):
        stripe, _ = item

        def compute():
            ids = planet.read(stripe, ["type", "id"])
            mask = pc.and_(pc.equal(ids.column("type"), "node"), pc.is_in(ids.column("id"), wanted))
            if not pc.any(mask).as_py():
                return {}
            t = planet.read(stripe, ["id", "lat", "lon", "tags"]).filter(mask)
            rows = {}
            for nid, lat, lon, tags in zip(
                t.column("id").to_pylist(),
                pc.cast(t.column("lat"), pa.string()).to_pylist(),
                pc.cast(t.column("lon"), pa.string()).to_pylist(),
                t.column("tags").to_pylist(),
                strict=True,
            ):
                rows[str(nid)] = [lat, lon, _tags(tags)]
            return rows

        return _cached(cache / "nodes" / f"{stripe:05d}.json.gz", compute)

    found: dict[int, list] = {}
    for rows in _parallel(one, stripes.items(), planet.threads, "nodes"):
        found.update({int(k): v for k, v in rows.items()})
    return found


def extract_relations(planet: Planet, ways: set[int], cache: Path) -> tuple[list, list]:
    """(turn restriction relations, bus route relations) touching the kept ways."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    first, last = type_range(2, planet.n_stripes, planet.first_keys)
    (cache / "relations").mkdir(parents=True, exist_ok=True)

    way_set = pa.array(sorted(ways), pa.int64())

    def one(stripe):
        def compute():
            head = planet.read(stripe, ["type", "tags"])
            kind = pc.map_lookup(head.column("tags"), "type", "first")
            route = pc.map_lookup(head.column("tags"), "route", "first")
            restr = pc.or_kleene(
                pc.equal(kind, "restriction"), pc.starts_with(kind, "restriction:")
            )
            bus = pc.and_kleene(pc.equal(kind, "route"), pc.equal(route, "bus"))
            mask = pc.and_(
                pc.equal(head.column("type"), "relation"),
                pc.fill_null(pc.or_kleene(restr, bus), False),
            )
            del head, kind, route, restr, bus
            if not pc.any(mask).as_py():
                return []
            t = planet.read(stripe, ["id", "tags", "members"]).filter(mask)
            # Only relations with a way member in the kept set (memory: global bus routes).
            members = t.column("members")
            if hasattr(members, "combine_chunks"):
                members = members.combine_chunks()
            flat = pc.list_flatten(members)
            parents = pc.list_parent_indices(members)
            hit = pc.and_(
                pc.equal(pc.struct_field(flat, "type"), "way"),
                pc.is_in(pc.struct_field(flat, "ref"), way_set),
            )
            rows_hit = np.unique(np.asarray(parents.filter(hit)))
            t = t.take(pa.array(rows_hit, pa.int64()))
            rows = []
            for rid, tags, mem in zip(
                t.column("id").to_pylist(),
                t.column("tags").to_pylist(),
                t.column("members").to_pylist(),
                strict=True,
            ):
                rows.append({"id": rid, "tags": _tags(tags), "members": mem or []})
            return rows

        return _cached(cache / "relations" / f"{stripe:05d}.json.gz", compute)

    restrictions, buses = [], []
    # Relation stripes decode to large member lists: few at a time (memory).
    for rows in _parallel(one, range(first, last + 1), min(planet.threads, 3), "relations"):
        for r in rows:
            way_members = [m["ref"] for m in r["members"] if m["type"] == "way"]
            if not way_members:
                continue
            if r["tags"].get("type") == "route":
                if any(w in ways for w in way_members):
                    buses.append(r)
            elif all(w in ways for w in way_members):
                restrictions.append(r)
    return restrictions, buses


# ---------------------------------------------------------------- Overture way ids


def overture_way_ids(release: str, bbox: tuple[float, float, float, float]) -> dict:
    """OSM way ids (and versions) of Overture road segments intersecting ``bbox``."""
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    from pyarrow import fs

    s3 = fs.S3FileSystem(anonymous=True, region="us-west-2")
    dataset = ds.dataset(
        f"overturemaps-us-west-2/release/{release}/theme=transportation/type=segment",
        filesystem=s3,
        format="parquet",
    )
    xmin, ymin, xmax, ymax = bbox
    flt = (
        (pc.field("bbox", "xmin") < xmax)
        & (pc.field("bbox", "xmax") > xmin)
        & (pc.field("bbox", "ymin") < ymax)
        & (pc.field("bbox", "ymax") > ymin)
        & (pc.field("subtype") == "road")
    )
    table = dataset.to_table(columns=["id", "class", "sources"], filter=flt)
    ways: dict[int, int] = {}
    versions = set()
    for sources in table.column("sources").to_pylist():
        for s in sources or []:
            rec = (s or {}).get("record_id") or ""
            if s.get("dataset") == "OpenStreetMap" and rec.startswith("w"):
                wid, _, ver = rec[1:].partition("@")
                ways[int(wid)] = int(ver) if ver.isdigit() else 0
                versions.add(s.get("version"))
    return {
        "release": release,
        "bbox_wgs84": list(bbox),
        "segments": table.num_rows,
        "ways": ways,
        "osm_versions": sorted(v for v in versions if v),
    }


# ---------------------------------------------------------------- OSM XML


def write_osm_xml(
    path: Path,
    nodes: dict[int, list],
    ways: dict[int, dict],
    relations: list[dict],
    bounds: tuple[float, float, float, float],
    generator: str = "p4d corridor_sumo osm_extract",
) -> None:
    """Standard OSM XML 0.6 (gzip when ``path`` ends with .gz), sorted by id.

    ``nodes``: ``{id: [lat, lon, tags]}`` with lat/lon as numbers or decimal strings;
    ``ways``: ``{id: {tags, nds}}``; relations: ``[{id, tags, members:[{type, ref,
    role}]}]``. Output is deterministic (gzip mtime 0).
    """

    @contextlib.contextmanager
    def opener(p: Path):
        with open(p, "wb") as f:
            if p.suffix != ".gz":
                yield f
                return
            # No file name or time in the gzip header: equal content gives equal bytes.
            with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as z:
                yield z

    def tag_lines(tags: dict) -> str:
        return "".join(
            f"    <tag k={quoteattr(str(k))} v={quoteattr(str(v))}/>\n"
            for k, v in sorted(tags.items())
        )

    def coord(v) -> str:
        return v if isinstance(v, str) else f"{v:.7f}"

    with opener(path) as raw:
        out = []
        out.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        out.append(f'<osm version="0.6" generator={quoteattr(generator)}>\n')
        lon0, lat0, lon1, lat1 = bounds
        out.append(
            f'  <bounds minlat="{lat0:.7f}" minlon="{lon0:.7f}" '
            f'maxlat="{lat1:.7f}" maxlon="{lon1:.7f}"/>\n'
        )
        raw.write("".join(out).encode())
        buf = []
        for nid in sorted(nodes):
            lat, lon, tags = nodes[nid]
            head = f'  <node id="{nid}" lat="{coord(lat)}" lon="{coord(lon)}"'
            buf.append(f"{head}>\n{tag_lines(tags)}  </node>\n" if tags else f"{head}/>\n")
            if len(buf) > 50000:
                raw.write("".join(buf).encode())
                buf = []
        for wid in sorted(ways):
            w = ways[wid]
            nds = "".join(f'    <nd ref="{r}"/>\n' for r in w["nds"])
            buf.append(f'  <way id="{wid}">\n{nds}{tag_lines(w["tags"])}  </way>\n')
            if len(buf) > 20000:
                raw.write("".join(buf).encode())
                buf = []
        for r in sorted(relations, key=lambda r: r["id"]):
            mem = "".join(
                f'    <member type="{m["type"]}" ref="{m["ref"]}" role={quoteattr(m.get("role") or "")}/>\n'
                for m in r["members"]
            )
            buf.append(f'  <relation id="{r["id"]}">\n{mem}{tag_lines(r["tags"])}  </relation>\n')
        buf.append("</osm>\n")
        raw.write("".join(buf).encode())


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# ---------------------------------------------------------------- driver


def buffered_bbox(origin: dict, half_m: float, buffer_m: float) -> tuple[float, ...]:
    from .tfl import Enu

    enu = Enu(origin["longitude"], origin["latitude"])
    lon0, lat0 = enu.inverse(-(half_m + buffer_m), -(half_m + buffer_m))
    lon1, lat1 = enu.inverse(half_m + buffer_m, half_m + buffer_m)
    return lon0, lat0, lon1, lat1


def extract(scene: str, buffer_m: float | None = None, threads: int = 24) -> dict:
    from common.storage import Storage

    storage = Storage.load()
    meta = storage.metadata(scene)
    cfg = json.loads((meta / "configs/traffic_sumo.json").read_text())
    ocfg = cfg.get("osm", {})
    geo = json.loads(
        (meta / cfg.get("geometry_config", "configs/image_to_threejs.json")).read_text()
    )
    buffer_m = ocfg.get("buffer_m", 1500.0) if buffer_m is None else buffer_m
    half = geo["domain_m"] / 2
    bbox = buffered_bbox(geo["origin"], half, buffer_m)
    cache = storage.cache_root / scene / "traffic_sumo" / "osm"
    cache.mkdir(parents=True, exist_ok=True)
    out_dir = storage.assets(scene, "input") / ocfg.get("dir", "osm")
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    timings = {}

    release = ocfg.get("overture_release") or geo["overture_release"]
    ids_path = cache / f"overture_way_ids_{release}_{int(buffer_m)}.json"
    if ids_path.is_file():
        ow = json.loads(ids_path.read_text())
    else:
        log(f"Overture {release}: road segment OSM way ids in {bbox} ...")
        ow = overture_way_ids(release, bbox)
        ids_path.write_text(json.dumps(ow))
    way_ids = {int(k) for k in ow["ways"]}
    timings["overture_s"] = round(time.monotonic() - t0, 1)
    log(f"  {ow['segments']} segments -> {len(way_ids)} OSM way ids")

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
    raw_ways = extract_ways(planet, way_ids, cache)
    ways = {k: v for k, v in raw_ways.items() if keep_way(v["tags"])}
    missing_ways = sorted(way_ids - set(raw_ways))
    log(f"ways: {len(raw_ways)} of {len(way_ids)} found, {len(ways)} vehicle highways kept")
    node_refs = {n for w in ways.values() for n in w["nds"]}
    new = newest_ways(planet, max(way_ids), node_refs, cache, ocfg.get("newest_way_stripes", 40))
    new = {k: v for k, v in new.items() if k not in ways}
    ways.update(new)
    log(f"  {len(new)} newer vehicle highways sharing nodes added")
    timings["ways_s"] = round(time.monotonic() - t, 1)

    t = time.monotonic()
    node_refs = {n for w in ways.values() for n in w["nds"]}
    nodes = extract_nodes(planet, node_refs, cache)
    missing_nodes = node_refs - set(nodes)
    if missing_nodes:
        # A way referencing a node absent from the planet cannot be drawn; drop the refs.
        for w in ways.values():
            w["nds"] = [n for n in w["nds"] if n in nodes]
        ways = {k: v for k, v in ways.items() if len(v["nds"]) >= 2}
    timings["nodes_s"] = round(time.monotonic() - t, 1)
    log(
        f"nodes: {len(nodes)} of {len(node_refs)} refs, {sum(1 for n in nodes.values() if n[2])} tagged"
    )

    t = time.monotonic()
    restrictions, bus_routes = extract_relations(planet, set(ways), cache)
    restrictions = [
        r
        for r in restrictions
        if all(m["ref"] in nodes for m in r["members"] if m["type"] == "node")
    ]
    timings["relations_s"] = round(time.monotonic() - t, 1)
    log(f"relations: {len(restrictions)} turn restrictions, {len(bus_routes)} bus routes")

    xml_path = out_dir / "osm.xml.gz"
    write_osm_xml(xml_path, nodes, ways, restrictions, bbox)
    bus_path = out_dir / "bus_route_relations.json.gz"
    with (
        open(bus_path, "wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as f,
    ):
        f.write(
            json.dumps(sorted(bus_routes, key=lambda r: r["id"]), separators=(",", ":")).encode()
        )
    tag_counts: dict[str, int] = {}
    for n in nodes.values():
        for key in ("highway", "crossing", "junction"):
            if key in n[2]:
                v = f"{key}={n[2][key]}"
                tag_counts[v] = tag_counts.get(v, 0) + 1
    hw_counts: dict[str, int] = {}
    for w in ways.values():
        hw_counts[w["tags"]["highway"]] = hw_counts.get(w["tags"]["highway"], 0) + 1
    timings["total_s"] = round(time.monotonic() - t0, 1)
    index = {
        "schema": "corridor-osm-subset-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": obj,
        "licence": LICENCE,
        "selection": {
            "bbox_wgs84": [round(v, 7) for v in bbox],
            "domain_half_m": half,
            "buffer_m": buffer_m,
            "origin": geo["origin"],
            "way_ids_from": {k: v for k, v in ow.items() if k != "ways"},
            "way_rule": "Overture road segments' OSM way ids; kept when highway is one of "
            f"{sorted(VEHICLE_HIGHWAYS)} (not area=yes), or pedestrian with bus/psv/"
            "motor_vehicle allowed; plus newer such ways sharing a node with a kept way",
            "relation_rule": "type=restriction / restriction:* with all way members kept "
            "(in osm.xml.gz); route=bus touching a kept way (bus_route_relations.json.gz)",
        },
        "counts": {
            "overture_way_ids": len(way_ids),
            "ways_found": len(raw_ways),
            "ways_missing_in_planet": len(missing_ways),
            "ways_kept": len(ways),
            "ways_newer_than_overture": len(new),
            "ways_by_highway": dict(sorted(hw_counts.items())),
            "nodes": len(nodes),
            "nodes_missing_in_planet": len(missing_nodes),
            "nodes_tagged": sum(1 for n in nodes.values() if n[2]),
            "node_tags": dict(sorted(tag_counts.items())),
            "turn_restrictions": len(restrictions),
            "bus_route_relations": len(bus_routes),
        },
        "stripes_read": planet.reads,
        "timings_s": timings,
        "files": {
            p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in (xml_path, bus_path)
        },
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    log(json.dumps(index["counts"], indent=2))
    return index


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--buffer-m", type=float, help="buffer around the domain (default config/1500)")
    p.add_argument("--threads", type=int, default=24)
    args = p.parse_args(argv)
    extract(args.scene, args.buffer_m, args.threads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
