"""Rebuild an explicitly illustrative microscopic SUMO experiment from exported lanes.

Original simulation inputs and signal timings are unavailable. Recovered lane
geometry/connectivity is retained; signals are regenerated and demand is sampled.
"""

import argparse
import collections
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

from traffic.corridor_reservations import junction_groups

VEHICLES = {
    "car": ("passenger", 4.5, 1.8, 1.5),
    "taxi": ("taxi", 4.8, 1.9, 1.9),
    "bus": ("bus", 10.5, 2.55, 4.4),
    "lgv": ("delivery", 5.5, 2.0, 2.5),
    "hgv": ("truck", 10.5, 2.55, 3.6),
    "motorcycle": ("motorcycle", 2.2, 0.8, 1.4),
}


def write_xml(root, path):
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def shape(points):
    return " ".join(",".join(str(v) for v in point) for point in points)


def read_network(source):
    index = json.loads((source / "road_network.json").read_text())
    network = {key: [] for key in ("edges", "lanes", "junctions", "connections")}
    for part in index["chunks"]:
        data = (source / part["asset"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != part["sha256"]:
            raise ValueError("Network chunk checksum mismatch")
        chunk = json.loads(data)
        for key, entries in network.items():
            entries.extend(chunk[key])
    return network


def build_network(network, output, netconvert):
    lanes, edges = network["lanes"], network["edges"]
    lane_indices = {index: n for edge in edges for n, index in enumerate(edge["lanes"])}
    nodes_xml, edges_xml, connections_xml = (
        ET.Element("nodes"),
        ET.Element("edges"),
        ET.Element("connections"),
    )
    endpoints = collections.defaultdict(list)
    for edge in edges:
        for lane_index in edge["lanes"]:
            lane = lanes[lane_index]
            endpoints[edge["from"]].append(lane["shape"][0])
            endpoints[edge["to"]].append(lane["shape"][-1])
    junctions = {j["id"]: j for j in network["junctions"]}
    for node, points in endpoints.items():
        junction = junctions[node]
        center = [sum(p[i] for p in points) / len(points) for i in range(3)]
        attrs = dict(
            id=node, x=str(center[0]), y=str(center[1]), z=str(center[2]), type=junction["type"]
        )
        if len(junction["shape"]) >= 3:
            attrs["shape"] = shape(junction["shape"])
        ET.SubElement(nodes_xml, "node", attrs)
    for edge in edges:
        first = lanes[edge["lanes"][0]]
        attrs = {
            "id": edge["id"],
            "from": edge["from"],
            "to": edge["to"],
            "numLanes": str(len(edge["lanes"])),
            "speed": str(edge["speed"]),
            "priority": str(edge["priority"]),
            "shape": shape(first["shape"]),
        }
        el = ET.SubElement(edges_xml, "edge", attrs)
        for index in edge["lanes"]:
            lane = lanes[index]
            attrs = {k: str(lane[k]) for k in ("index", "speed", "width")}
            attrs["index"] = str(lane_indices[index])
            attrs["shape"] = shape(lane["shape"])
            for key in ("allow", "disallow"):
                if key in lane:
                    attrs[key] = lane[key]
            ET.SubElement(el, "lane", attrs)
    seen = set()
    for connection in network["connections"]:
        a, b = lanes[connection["from_lane"]], lanes[connection["to_lane"]]
        if a["edge"] is None or b["edge"] is None:
            continue
        key = (a["edge"], b["edge"], a["index"], b["index"])
        if key in seen:
            continue
        seen.add(key)
        ET.SubElement(
            connections_xml,
            "connection",
            {
                "from": edges[a["edge"]]["id"],
                "to": edges[b["edge"]]["id"],
                "fromLane": str(lane_indices[connection["from_lane"]]),
                "toLane": str(lane_indices[connection["to_lane"]]),
            },
        )
    for name, tree in [
        ("nodes", nodes_xml),
        ("edges", edges_xml),
        ("connections", connections_xml),
    ]:
        write_xml(tree, output / f"{name}.xml")
    command = [
        str(netconvert),
        "--node-files",
        str(output / "nodes.xml"),
        "--edge-files",
        str(output / "edges.xml"),
        "--connection-files",
        str(output / "connections.xml"),
        "--output-file",
        str(output / "network.net.xml"),
        "--lefthand",
        "--offset.disable-normalization",
        "--no-turnarounds",
        "--tls.default-type",
        "actuated",
        "--tls.yellow.time",
        "4",
        "--tls.allred.time",
        "2",
        "--junctions.corner-detail",
        "5",
        "--junctions.internal-link-detail",
        "12",
        "--internal-junctions.vehicle-width",
        "2.55",
        "--junctions.limit-turn-speed",
        "4.0",
    ]
    with (output / "netconvert.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    return command


def build_demand(network, source, output, period, fraction):
    data = json.loads((source / f"traffic_routes_{period}.json").read_text())
    lanes, edges = network["lanes"], network["edges"]
    connections = {
        (lanes[c["from_lane"]]["edge"], lanes[c["to_lane"]]["edge"])
        for c in network["connections"]
        if lanes[c["from_lane"]]["edge"] is not None and lanes[c["to_lane"]]["edge"] is not None
    }
    rebuilt = ET.parse(output / "network.net.xml").getroot()
    rebuilt_edges = {edge.get("id"): edge for edge in rebuilt.findall("edge") if edge.get("from")}
    groups = junction_groups(rebuilt)
    root = ET.Element("routes")
    for name, (cls, length, width, height) in VEHICLES.items():
        ET.SubElement(
            root,
            "vType",
            id=name,
            vClass=cls,
            length=str(length),
            width=str(width),
            height=str(height),
            accel="1.3" if name in ("bus", "hgv") else "2.0",
            decel="4.5",
            emergencyDecel="9",
            minGap="2.5",
            tau="1.2",
            sigma="0",
            carFollowModel="Krauss",
            speedFactor="1",
            jmTimegapMinor="2",
            lcStrategic="10",
            lcAssertive="0.5",
            lcCooperative="1",
            lcSpeedGain="0",
            lcKeepRight="0",
        )
    counts = collections.Counter()
    vehicles = []
    for vehicle in data["vehicles"]:
        counts["source"] += 1
        if int(hashlib.sha256(vehicle["id"].encode()).hexdigest()[:8], 16) / 2**32 >= fraction:
            counts["not_sampled"] += 1
            continue
        if vehicle.get("jumps"):
            counts["discontinuous_source_route"] += 1
            continue
        depart = vehicle["enter"][0]
        if not data["t0"] - 120 <= depart <= data["t1"]:
            counts["outside_departure_window"] += 1
            continue
        route = []
        for index in vehicle["path"]:
            edge = lanes[index]["edge"]
            if edge is not None and (not route or route[-1] != edge):
                route.append(edge)
        if len(route) < 2 or any((a, b) not in connections for a, b in pairwise(route)):
            counts["disconnected_route"] += 1
            continue
        cls = VEHICLES[vehicle["type"]][0]

        def permitted(lane, cls=cls):
            return (
                "allow" not in lane
                or cls in lane["allow"].split()
                or "all" in lane["allow"].split()
            ) and cls not in lane.get("disallow", "").split()

        if any(not any(permitted(lanes[i]) for i in edges[e]["lanes"]) for e in route):
            counts["vehicle_class_restriction"] += 1
            continue
        required = max(20, VEHICLES[vehicle["type"]][1] + 10)
        first = rebuilt_edges[edges[route[0]]["id"]]
        options = [
            int(lane.get("index"))
            for lane in first.findall("lane")
            if float(lane.get("length")) >= required
            and permitted(lanes[edges[route[0]]["lanes"][int(lane.get("index"))]])
        ]
        if not options or groups[first.get("from")] == groups[first.get("to")]:
            counts["insufficient_departure_storage"] += 1
            continue
        el = ET.Element(
            "vehicle",
            id=vehicle["id"],
            type=vehicle["type"],
            depart=str(depart),
            departLane=str(options[0]),
            departSpeed="0",
            departPos=str(VEHICLES[vehicle["type"]][1] + 2.5),
        )
        ET.SubElement(el, "route", edges=" ".join(edges[i]["id"] for i in route))
        vehicles.append((depart, el))
        counts["selected"] += 1
    for _, element in sorted(vehicles, key=lambda entry: entry[0]):
        root.append(element)
    write_xml(root, output / f"{period}.rou.xml")
    return data, dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sumo", type=Path, required=True)
    parser.add_argument("--netconvert", type=Path, required=True)
    parser.add_argument("--fraction", type=float, default=0.25)
    parser.add_argument("--period", choices=["am_peak", "inter_peak", "pm_peak"], default="am_peak")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    net = read_network(args.source)
    if not (args.output / "network.net.xml").exists():
        build_network(net, args.output, args.netconvert)
    data, counts = build_demand(net, args.source, args.output, args.period, args.fraction)
    command = [
        str(args.sumo),
        "-n",
        str(args.output / "network.net.xml"),
        "-r",
        str(args.output / f"{args.period}.rou.xml"),
        "--begin",
        str(data["t0"] - 120),
        "--end",
        str(data["t1"] + 0.5),
        "--step-length",
        ".1",
        "--seed",
        "42",
        "--time-to-teleport",
        "-1",
        "--collision.action",
        "warn",
        "--collision.check-junctions",
        "true",
        "--lateral-resolution",
        ".4",
        "--fcd-output",
        str(args.output / f"{args.period}.fcd.xml.gz"),
        "--device.fcd.period",
        ".5",
        "--fcd-output.acceleration",
        "true",
        "--fcd-output.distance",
        "true",
        "--summary-output",
        str(args.output / f"{args.period}.summary.xml"),
        "--collision-output",
        str(args.output / f"{args.period}.collisions.xml"),
        "--tripinfo-output",
        str(args.output / f"{args.period}.trips.xml"),
        "--no-step-log",
        "--duration-log.statistics",
        "true",
        "--precision",
        "4",
    ]
    (args.output / f"{args.period}.config.json").write_text(
        json.dumps(
            {
                "period": args.period,
                "fraction": args.fraction,
                "counts": counts,
                "command": command,
                "assumptions": [
                    "regenerated actuated signals; original timings unavailable",
                    "25% deterministic route sample by default, not count-calibrated",
                    "120-second empty-network warmup",
                    "bus routes without original service schedule; no timetable claims",
                    "no jam teleportation; retain congestion instead",
                    "exclusive reservations for junctions connected by links under 20 m; experimental control, not London signal operation",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(counts), flush=True)
    with (args.output / f"{args.period}.sumo.log").open("w") as log:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "traffic.corridor_reservations",
                str(args.output / f"{args.period}.config.json"),
            ],
            stdout=log,
            stderr=log,
            check=True,
        )


if __name__ == "__main__":
    main()
