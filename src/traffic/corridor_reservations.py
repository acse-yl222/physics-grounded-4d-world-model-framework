"""Conservative experimental junction reservations on top of SUMO car following.

Only one vehicle owns a junction until its rear has cleared it. This is an
illustrative conflict-avoidance controller, NOT a reconstruction of London signals.
"""

import gzip
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def junction_groups(root):
    """Treat junctions connected by <20 m links as one conflict area."""
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]

    for edge in root.findall("edge"):
        if edge.get("from"):
            a, b = find(edge.get("from")), find(edge.get("to"))
            if min(float(lane.get("length")) for lane in edge.findall("lane")) < 20:
                parent[a] = b
    return {node: find(node) for node in parent}


def junction_occupants(states, sizes, edge_from, internal_junction, keys):
    """Include rear overhang on short outgoing links, independently of reservations."""
    occupied = {}
    for vehicle, state in states.items():
        lane, edge = state[keys.VAR_LANE_ID], state[keys.VAR_ROAD_ID]
        junction = internal_junction.get(lane)
        if (
            junction is None
            and edge in edge_from
            and state[keys.VAR_LANEPOSITION] < sizes[vehicle] + 8
        ):
            junction = edge_from[edge]
        if junction is not None:
            occupied.setdefault(junction, set()).add(vehicle)
    return occupied


def run(config_path):
    import libsumo as sim
    from traci import constants as tc

    config = json.loads(Path(config_path).read_text())
    command = config["command"]
    network = Path(command[command.index("-n") + 1])
    opener = gzip.open if network.suffix == ".gz" else open
    with opener(network, "rb") as stream:
        root = ET.parse(stream).getroot()
    edge_to = {edge.get("id"): edge.get("to") for edge in root.findall("edge") if edge.get("to")}
    groups = junction_groups(root)
    edge_to = {edge: groups[node] for edge, node in edge_to.items()}
    edge_from = {
        edge.get("id"): edge.get("from") for edge in root.findall("edge") if edge.get("from")
    }
    internal_junction = {
        lane.get("id"): lane.get("id").rsplit("_", 2)[0][1:]
        for edge in root.findall("edge")
        if edge.get("function") == "internal"
        for lane in edge.findall("lane")
    }
    edge_from = {edge: groups[node] for edge, node in edge_from.items()}
    internal_junction = {lane: groups.get(node, node) for lane, node in internal_junction.items()}
    lengths = {
        lane.get("id"): float(lane.get("length"))
        for edge in root.findall("edge")
        for lane in edge.findall("lane")
    }
    owner = {}
    acquired = {}
    controlled = set()
    sizes = {}
    arrivals = {}
    steps = 0
    variables = [tc.VAR_ROAD_ID, tc.VAR_LANE_ID, tc.VAR_LANEPOSITION, tc.VAR_SPEED]
    sim.start(command)
    end = float(command[command.index("--end") + 1])
    try:
        while sim.simulation.getTime() < end:
            for vehicle in sim.simulation.getDepartedIDList():
                sim.vehicle.subscribe(vehicle, variables)
                sizes[vehicle] = sim.vehicle.getLength(vehicle)
            states = sim.vehicle.getAllSubscriptionResults()
            for junction, vehicle in list(owner.items()):
                state = states.get(vehicle)
                if state is None or (
                    state[tc.VAR_ROAD_ID] in edge_to
                    and edge_from[state[tc.VAR_ROAD_ID]] == junction
                    and edge_to[state[tc.VAR_ROAD_ID]] != junction
                    and state[tc.VAR_LANEPOSITION] > sizes[vehicle] + 8
                ):
                    del owner[junction]
                    acquired.pop(junction, None)
            occupied = junction_occupants(states, sizes, edge_from, internal_junction, tc)
            for vehicle, state in states.items():
                edge = state[tc.VAR_ROAD_ID]
                if edge in edge_to and edge_from[edge] == edge_to[edge]:
                    occupied.setdefault(edge_to[edge], set()).add(vehicle)
            groups = {}
            for vehicle, state in states.items():
                edge = state[tc.VAR_ROAD_ID]
                if edge not in edge_to or edge_from[edge] == edge_to[edge]:
                    continue
                distance = lengths[state[tc.VAR_LANE_ID]] - state[tc.VAR_LANEPOSITION]
                if distance < 80:
                    junction = edge_to[edge]
                    arrivals.setdefault((junction, vehicle), sim.simulation.getTime())
                    groups.setdefault(junction, []).append(
                        (
                            arrivals[(junction, vehicle)],
                            distance,
                            vehicle,
                            edge,
                            state[tc.VAR_SPEED],
                        )
                    )
            next_controlled = set()
            for junction, candidates in groups.items():
                if junction not in owner:
                    _, _, vehicle, edge, _ = min(candidates)
                    owner[junction] = vehicle
                    acquired[junction] = edge
                for _, distance, vehicle, edge, speed in candidates:
                    if owner[junction] == vehicle and not (
                        occupied.get(junction, set()) - {vehicle}
                    ):
                        continue
                    # A conservative braking envelope with 0.1-second control reaction.
                    remaining = max(0, distance - 8)
                    safe = max(0, math.sqrt((3 * 0.1) ** 2 + 2 * 3 * remaining) - 3 * 0.1)
                    sim.vehicle.setSpeed(vehicle, min(safe, sim.vehicle.getAllowedSpeed(vehicle)))
                    next_controlled.add(vehicle)
            for vehicle in controlled - next_controlled:
                if vehicle in states:
                    sim.vehicle.setSpeed(vehicle, -1)
            controlled = next_controlled
            sim.simulationStep()
            steps += 1
            if sim.simulation.getCollidingVehiclesNumber():
                print("Collision detected at", sim.simulation.getTime(), flush=True)
        print(
            json.dumps(
                {
                    "controller": "exclusive-junction-reservation",
                    "steps": steps,
                    "remaining": sim.simulation.getMinExpectedNumber(),
                }
            ),
            flush=True,
        )
    finally:
        sim.close()


if __name__ == "__main__":
    run(sys.argv[1])
