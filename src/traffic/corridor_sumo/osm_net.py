"""Build the SUMO network from the scene's OpenStreetMap subset (netconvert OSM importer).

Input is ``project/<scene>/input/osm/osm.xml.gz`` written by ``osm_extract``. The
projection is an equirectangular (``+proj=eqc``) plane with true scale at the scene
origin latitude and the Earth radius of ``tfl.Enu``, so with offset normalisation
disabled SUMO x,y are exactly scene ENU metres; ``check_coordinates`` verifies this on
the unjoined OSM nodes and fails the build otherwise.

OSM tags used by netconvert: ``lanes``/``lanes:forward``/``lanes:backward``,
``turn:lanes``, ``maxspeed`` (mph is converted), ``oneway``, ``junction=roundabout``,
``access``/``motor_vehicle``/``bus``/``psv``, ``busway``/``bus:lanes``/``psv:lanes``
(lane access), traffic signal nodes (clustered onto their junction by
``--tls.guess-signals``), and turn restriction relations. Untagged speeds come from a
UK urban typemap (``default_speed_mph``) derived from SUMO's ``osmNetconvert.typ.xml``.

Hot spots can be fixed with plain-XML patch files (``.edg.xml``/``.con.xml``/
``.tll.xml``/``.nod.xml``) listed in the configuration; they are applied in a second
netconvert pass over the built net and recorded (with hashes) in the network stats.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from . import sumo_env, tfl

# Defaults for untagged maxspeed (mph) on GB urban roads; London's 20 mph is common on
# residential/unclassified roads, 30 mph on A/B roads (``maxspeed`` tags win).
DEFAULT_SPEED_MPH = {
    "motorway": 50,
    "motorway_link": 30,
    "trunk": 30,
    "trunk_link": 30,
    "primary": 30,
    "primary_link": 30,
    "secondary": 30,
    "secondary_link": 30,
    "tertiary": 30,
    "tertiary_link": 30,
    "unclassified": 20,
    "residential": 20,
    "living_street": 10,
    "service": 10,
    "busway": 30,
    "bus_guideway": 30,
}
MPH = 0.44704
EXTRA_ATTRIBUTES = [
    "ref",
    "lanes",
    "lanes:forward",
    "lanes:backward",
    "maxspeed",
    "turn:lanes",
    "busway",
    "bus:lanes",
    "psv:lanes",
    "oneway",
    "junction",
    "access",
    "motor_vehicle",
    "bus",
    "psv",
]
NETCONVERT_DEFAULTS = {
    "offset.disable-normalization": True,
    "lefthand": True,
    "osm.turn-lanes": True,
    "osm.lane-access": True,
    "osm.all-attributes": True,
    "osm.extra-attributes": ",".join(EXTRA_ATTRIBUTES),
    # GB: minor roads give way to major roads. netconvert would otherwise build
    # right-before-left (equal priority) junctions wherever all approaches are slower
    # than 13.6 m/s, i.e. almost everywhere in 20/30 mph London, which deadlocks.
    "junctions.right-before-left.speed-threshold": 0,
    "junctions.join": True,
    "junctions.join-dist": 15,
    "junctions.corner-detail": 5,
    "no-turnarounds": True,
    "no-turnarounds.except-deadend": True,
    "tls.guess-signals": True,
    "tls.guess-signals.dist": 25,
    "tls.join": True,
    "tls.join-dist": 25,
    "tls.discard-simple": True,
    "tls.default-type": "actuated",
    "tls.cycle.time": 90,
    "ramps.guess": True,
    "roundabouts.guess": True,
    "geometry.remove": True,
    "edges.join": True,
    "remove-edges.isolated": True,
    "remove-edges.by-vclass": "pedestrian,bicycle,delivery,rail,rail_urban,rail_electric,"
    "rail_fast,tram,subway,ship",
    "keep-edges.components": 1,
    "output.street-names": True,
    "output.original-names": True,
}


def proj_string(lon0: float, lat0: float, radius: float = tfl.R) -> str:
    """PROJ definition equal to ``tfl.Enu`` (equirectangular, true scale at lat0)."""
    return (
        f"+proj=eqc +lat_ts={lat0!r} +lat_0={lat0!r} +lon_0={lon0!r} +x_0=0 +y_0=0 "
        f"+R={radius!r} +units=m +no_defs"
    )


def road_class(edge_type: str | None) -> str:
    """Road class of a SUMO edge type: ``highway.primary_link`` -> ``primary``.

    Overture-built types are already plain classes. Compound OSM types
    (``highway.residential|railway.tram``) use their first highway component.
    """
    t = edge_type or ""
    parts = [p for p in t.split("|") if p.startswith("highway.")] or t.split("|")
    cls = parts[0].removeprefix("highway.")
    return cls.removesuffix("_link")


def write_typemap(source: Path, target: Path, speeds_mph: dict[str, float]) -> None:
    """Copy of ``source`` with ``speed`` of highway types replaced (mph -> m/s)."""
    tree = ET.parse(source)
    for el in tree.getroot():
        tid = el.get("id", "")
        cls = tid.removeprefix("highway.").split("|")[0]
        if tid.startswith("highway.") and cls in speeds_mph:
            el.set("speed", f"{speeds_mph[cls] * MPH:.2f}")
    tree.write(target, encoding="UTF-8", xml_declaration=True)


def osm_nodes(osm_path: Path) -> tuple[dict[str, tuple[float, float]], dict[str, dict]]:
    """(``{id: (lon, lat)}``, ``{id: tags}`` of tagged nodes) from an OSM XML file."""
    opener = gzip.open if str(osm_path).endswith(".gz") else open
    coords, tagged = {}, {}
    with opener(osm_path, "rb") as f:
        for _, el in ET.iterparse(f):
            if el.tag == "node":
                nid = el.get("id")
                coords[nid] = (float(el.get("lon")), float(el.get("lat")))
                tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
                if tags:
                    tagged[nid] = tags
                el.clear()
            elif el.tag in ("way", "relation"):
                break
    return coords, tagged


def check_coordinates(
    net, coords: dict[str, tuple[float, float]], enu, min_nodes: int = 1000, tol_m: float = 0.05
) -> dict:
    """Unjoined OSM nodes must sit at ``enu(lon, lat)`` in the SUMO net."""
    deviation, checked = 0.0, 0
    for node in net.getNodes():
        ll = coords.get(node.getID())
        if ll is None:
            continue
        x, y = node.getCoord()[:2]
        ex, ey = enu(*ll)
        deviation = max(deviation, abs(x - ex), abs(y - ey))
        checked += 1
    offset = list(net.getLocationOffset())
    out = {
        "nodes_checked": checked,
        "max_abs_deviation_m": round(deviation, 4),
        "tolerance_m": tol_m,
        "location_offset": offset,
    }
    if offset != [0.0, 0.0] or checked < min_nodes or deviation > tol_m:
        raise RuntimeError(f"SUMO network is not in scene ENU coordinates: {out}")
    return out


def _run_netconvert(args: list, flags: dict, log: Path) -> None:
    cmd = [sumo_env.binary("netconvert"), *args]
    for key, value in flags.items():
        if value is None:
            continue
        cmd += [f"--{key}", str(value).lower() if isinstance(value, bool) else str(value)]
    sumo_env.run(cmd, log=log)


def build_network(
    osm_path: Path,
    out_dir: Path,
    ncfg: dict,
    origin: dict,
    extent_m: float,
    config_dir: Path | None = None,
) -> dict:
    """netconvert the OSM subset into ``out_dir/net.net.xml``; return paths and stats.

    ``extent_m``: half side of the kept square (domain + buffer), in ENU metres.
    ``ncfg``: ``network.osm`` configuration (``netconvert`` overrides,
    ``default_speed_mph``, ``patches`` relative to ``config_dir``).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    enu = tfl.Enu(origin["longitude"], origin["latitude"])
    typemap = out_dir / "osm_uk_urban.typ.xml"
    write_typemap(
        sumo_env.sumo_home() / "data/typemap/osmNetconvert.typ.xml",
        typemap,
        {**DEFAULT_SPEED_MPH, **ncfg.get("default_speed_mph", {})},
    )
    flags = {
        **NETCONVERT_DEFAULTS,
        "proj": proj_string(origin["longitude"], origin["latitude"]),
        "type-files": typemap,
        "keep-edges.in-boundary": f"{-extent_m:g},{-extent_m:g},{extent_m:g},{extent_m:g}",
        "junctions.join-output": out_dir / "joined.xml",
        **ncfg.get("netconvert", {}),
    }
    patches = [Path(config_dir or ".") / p for p in ncfg.get("patches", [])]
    raw = out_dir / ("raw.net.xml" if patches else "net.net.xml")
    log = out_dir / "netconvert.log"
    if log.exists():
        log.unlink()
    _run_netconvert(["--osm-files", osm_path, "-o", raw], flags, log)
    target = out_dir / "net.net.xml"
    applied = []
    if patches:
        kinds = {".edg.xml": "edge-files", ".con.xml": "connection-files"}
        kinds |= {".tll.xml": "tllogic-files", ".nod.xml": "node-files"}
        args = ["--sumo-net-file", raw, "-o", target]
        for p in patches:
            kind = next((v for k, v in kinds.items() if p.name.endswith(k)), None)
            if kind is None:
                raise ValueError(f"unknown patch file type: {p}")
            args += [f"--{kind}", p]
            applied.append({"file": p.name, "sha256": _digest(p)})
        second = {
            k: flags[k]
            for k in ("offset.disable-normalization", "lefthand", "tls.default-type")
            if k in flags
        }
        _run_netconvert(args, second, log)
    coords, tagged = osm_nodes(osm_path)
    sumolib = sumo_env.sumolib()
    net = sumolib.net.readNet(str(target), withInternal=False)
    stats = {
        "source": "osm",
        "edges": len(net.getEdges()),
        "lanes": sum(len(e.getLanes()) for e in net.getEdges()),
        "junctions": len(net.getNodes()),
        "traffic_lights": len(net.getTrafficLights()),
        "edge_length_km": round(sum(e.getLength() for e in net.getEdges()) / 1000, 1),
        "location_offset": list(net.getLocationOffset()),
        "bbox_xy": [list(p) for p in net.getBBoxXY()],
        "projection": flags["proj"],
        "coordinate_check": check_coordinates(net, coords, enu),
        "netconvert": {k: str(v) for k, v in flags.items()},
        "patches": applied,
        "osm_signal_nodes": sum(
            1 for t in tagged.values() if t.get("highway") == "traffic_signals"
        ),
        "joined_junction_clusters": _joined_clusters(out_dir / "joined.xml"),
    }
    (out_dir / "network_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    return {"net": target, "stats": stats, "net_obj": net, "tagged_nodes": tagged, "coords": coords}


def _joined_clusters(path: Path) -> dict:
    if not path.is_file():
        return {}
    sizes = []
    for _, el in ET.iterparse(path):
        if el.tag == "join":
            sizes.append(len((el.get("nodes") or "").split()))
            el.clear()
    return {"clusters": len(sizes), "nodes_joined": sum(sizes)}


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# ---------------------------------------------------------------- reports


def _in_domain(edge, half: float) -> bool:
    shape = edge.getShape()
    x, y = shape[len(shape) // 2][:2]
    return abs(x) <= half and abs(y) <= half


MAIN = ("motorway", "trunk", "primary", "secondary")


def lane_km_by_class(net, half: float) -> dict:
    """Edge km and lane km per road class for edges inside the domain."""
    out: dict[str, dict] = defaultdict(lambda: {"edge_km": 0.0, "lane_km": 0.0})
    for e in net.getEdges():
        if e.getFunction() or not _in_domain(e, half) or not e.allows("passenger"):
            continue
        cls = road_class(e.getType())
        km = e.getLength() / 1000
        out[cls]["edge_km"] += km
        out[cls]["lane_km"] += km * sum(1 for ln in e.getLanes() if ln.allows("passenger"))
    return {
        k: {kk: round(vv, 1) for kk, vv in v.items()}
        | {"mean_lanes": round(v["lane_km"] / v["edge_km"], 2) if v["edge_km"] else None}
        for k, v in sorted(out.items())
    }


def tag_completeness(net, half: float, classes=MAIN + ("tertiary",)) -> dict:
    """Share of edge length per class with explicit OSM ``lanes`` / ``maxspeed`` tags."""
    acc = defaultdict(lambda: defaultdict(float))
    for e in net.getEdges():
        if e.getFunction() or not _in_domain(e, half):
            continue
        cls = road_class(e.getType())
        if cls not in classes:
            continue
        km = e.getLength() / 1000
        a = acc[cls]
        a["km"] += km
        if e.getParam("lanes") or e.getParam("lanes:forward") or e.getParam("lanes:backward"):
            a["lanes"] += km
        if e.getParam("maxspeed"):
            a["maxspeed"] += km
        if e.getParam("ref"):
            a["ref"] += km
    out = {}
    for cls in classes:
        a = acc.get(cls)
        if not a:
            continue
        out[cls] = {
            "km": round(a["km"], 1),
            "lanes_tagged_share": round(a["lanes"] / a["km"], 3),
            "maxspeed_tagged_share": round(a["maxspeed"] / a["km"], 3),
            "ref_tagged_share": round(a["ref"] / a["km"], 3),
        }
    tot = {k: sum(acc[c][k] for c in MAIN if c in acc) for k in ("km", "lanes", "maxspeed", "ref")}
    if tot["km"]:
        out["main_roads"] = {
            "classes": list(MAIN),
            "km": round(tot["km"], 1),
            "lanes_tagged_share": round(tot["lanes"] / tot["km"], 3),
            "maxspeed_tagged_share": round(tot["maxspeed"] / tot["km"], 3),
            "ref_tagged_share": round(tot["ref"] / tot["km"], 3),
        }
    return out


def tls_in_domain(net, half: float) -> int:
    n = 0
    for tls in net.getTrafficLights():
        nodes = {c[0].getEdge().getToNode() for c in tls.getConnections()}
        if any(abs(nd.getCoord()[0]) <= half and abs(nd.getCoord()[1]) <= half for nd in nodes):
            n += 1
    return n


def signal_nodes_in_domain(tagged: dict, coords: dict, enu, half: float) -> int:
    n = 0
    for nid, tags in tagged.items():
        if tags.get("highway") == "traffic_signals":
            x, y = enu(*coords[nid])
            n += abs(x) <= half and abs(y) <= half
    return n


def reachable(net, sources, vclass: str = "passenger", reverse: bool = False) -> set:
    """Edge ids reachable from ``sources`` (edges) for ``vclass`` (BFS on connections)."""
    seen = {e.getID() for e in sources}
    todo = list(sources)
    while todo:
        e = todo.pop()
        nxt = e.getIncoming() if reverse else e.getOutgoing()
        for f in nxt:
            if f.getID() not in seen and f.allows(vclass):
                seen.add(f.getID())
                todo.append(f)
    return seen


def connectivity(net, places: dict[str, tuple[float, float]], enu, radius: float = 150.0) -> dict:
    """Whether named places are reachable from / to the domain core by car and by bus."""
    core = [e for e, _ in net.getNeighboringEdges(0.0, 0.0, 400.0) if e.allows("passenger")]
    out = {}
    for vclass in ("passenger", "bus"):
        start = [e for e in core if e.allows(vclass)]
        fwd = reachable(net, start, vclass)
        back = reachable(net, start, vclass, reverse=True)
        for name, (lon, lat) in places.items():
            x, y = enu(lon, lat)
            near = [e for e, _ in net.getNeighboringEdges(x, y, radius) if e.allows(vclass)]
            ids = {e.getID() for e in near}
            out.setdefault(name, {"lonlat": [lon, lat], "xy": [round(x), round(y)]})
            out[name][vclass] = {
                "edges_near": len(ids),
                "reachable_from_core": bool(ids & fwd),
                "reaches_core": bool(ids & back),
            }
    return out


def network_report(
    net,
    half: float,
    enu,
    tagged: dict,
    coords: dict,
    stats: dict,
    places: dict,
    compare_net=None,
) -> dict:
    """Completeness, connectivity and comparison with an earlier (Overture) network."""
    rep = {
        "domain_half_m": half,
        "network": {k: v for k, v in stats.items() if k not in ("bbox_xy", "netconvert")},
        "tag_completeness": tag_completeness(net, half),
        "lane_km_by_class": lane_km_by_class(net, half),
        "signals": {
            "osm_signal_nodes_in_domain": signal_nodes_in_domain(tagged, coords, enu, half),
            "osm_signal_nodes_total": stats.get("osm_signal_nodes"),
            "sumo_tls_in_domain": tls_in_domain(net, half),
            "sumo_tls_total": len(net.getTrafficLights()),
            "note": "SUMO clusters the OSM signal nodes of a junction (approach stop lines, "
            "tls.guess-signals) and joined junctions (tls.join) into one traffic light",
        },
        "junction_join": stats.get("joined_junction_clusters"),
        "connectivity": connectivity(net, places, enu),
    }
    if compare_net is not None:
        rep["previous_network"] = {
            "lane_km_by_class": lane_km_by_class(compare_net, half),
            "sumo_tls_in_domain": tls_in_domain(compare_net, half),
            "sumo_tls_total": len(compare_net.getTrafficLights()),
            "edges": len(compare_net.getEdges()),
            "edge_length_km": round(sum(e.getLength() for e in compare_net.getEdges()) / 1000, 1),
        }
    return rep
