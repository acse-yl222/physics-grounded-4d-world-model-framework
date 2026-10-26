"""Build the SUMO network (plain XML + netconvert) from cached Overture data."""

from __future__ import annotations

import json
from pathlib import Path

from . import overture_net, sumo_env

NETCONVERT_DEFAULTS = {
    # Keep scene ENU: no shift of the plain-XML coordinates (SUMO x,y == scene x,y).
    "offset.disable-normalization": True,
    "lefthand": True,  # Great Britain drives on the left
    "junctions.join": True,
    "junctions.join-dist": 12,
    "junctions.corner-detail": 5,
    "no-turnarounds.except-deadend": True,
    "tls.guess": True,  # adds signals at fast multi-lane junctions besides the marked ones
    "tls.join": True,
    "tls.join-dist": 25,
    "tls.discard-simple": True,
    "tls.default-type": "static",
    "ramps.guess": True,
    "roundabouts.guess": True,
    "geometry.remove": True,
    "remove-edges.isolated": True,
    "keep-edges.components": 1,  # largest connected component, so random trips route
    "output.street-names": True,
}


def load_layer(directory: Path, name: str) -> list[dict]:
    return json.loads((directory / f"{name}.json").read_text())["features"]


def build_network(overture_dir: Path, out_dir: Path, options: dict) -> dict:
    """Write plain XML and ``net.net.xml`` into ``out_dir``; return stats and paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = load_layer(overture_dir, "segments")
    connectors = load_layer(overture_dir, "connectors")
    opts = {k: v for k, v in options.items() if k != "netconvert"}
    net = overture_net.build(segments, connectors, opts)
    nodes, edges = out_dir / "plain.nod.xml", out_dir / "plain.edg.xml"
    overture_net.write_plain_xml(net, nodes, edges)
    target = out_dir / "net.net.xml"
    flags = {**NETCONVERT_DEFAULTS, **options.get("netconvert", {})}
    cmd = [sumo_env.binary("netconvert"), "--node-files", nodes, "--edge-files", edges]
    cmd += ["-o", target, "--no-warnings", "true"]
    for key, value in flags.items():
        cmd += [f"--{key}", str(value).lower() if isinstance(value, bool) else str(value)]
    sumo_env.run(cmd, log=out_dir / "netconvert.log")
    stats = describe(target, net)
    (out_dir / "network_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    return {"net": target, "nodes": nodes, "edges": edges, "stats": stats}


def describe(path: Path, plain: overture_net.Network | None = None) -> dict:
    """Edge/junction/TLS counts and a check that SUMO kept scene coordinates."""
    sumolib = sumo_env.sumolib()
    net = sumolib.net.readNet(str(path), withInternal=False)
    offset = list(net.getLocationOffset())
    stats = {
        "edges": len(net.getEdges()),
        "lanes": sum(len(e.getLanes()) for e in net.getEdges()),
        "junctions": len(net.getNodes()),
        "traffic_lights": len(net.getTrafficLights()),
        "edge_length_km": round(sum(e.getLength() for e in net.getEdges()) / 1000, 1),
        "location_offset": offset,
        "bbox_xy": [list(p) for p in net.getBBoxXY()],
    }
    if plain is not None:
        stats["plain"] = {k: v for k, v in plain.stats.items()}
        # Nodes that netconvert kept unjoined must sit at their plain-XML coordinates.
        deviation, checked = 0.0, 0
        for node in net.getNodes():
            if node.getID() in plain.nodes:
                x, y = node.getCoord()[:2]
                px, py = plain.nodes[node.getID()]
                deviation = max(deviation, abs(x - px), abs(y - py))
                checked += 1
        stats["coordinate_check"] = {"nodes_checked": checked, "max_abs_deviation_m": deviation}
        if offset != [0.0, 0.0] or checked == 0 or deviation > 0.01:
            raise RuntimeError(f"SUMO network is not in scene ENU coordinates: {stats}")
    return stats
