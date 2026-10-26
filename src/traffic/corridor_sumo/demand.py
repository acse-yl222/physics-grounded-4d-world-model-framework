"""Vehicle types and demand: synthetic randomTrips cars/taxis/buses, cached TfL buses."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from . import sumo_env

# London-typical vehicle classes (lengths: family car, TX-series taxi, double-decker bus).
VTYPES = """<additional>
    <vType id="car" vClass="passenger" length="4.5" minGap="2.5" maxSpeed="50" accel="2.6"
           decel="4.5" sigma="0.5" guiShape="passenger"/>
    <vType id="taxi" vClass="taxi" length="4.6" minGap="2.5" maxSpeed="45" accel="2.4"
           decel="4.5" sigma="0.5" guiShape="taxi"/>
    <vType id="bus" vClass="bus" length="11.2" minGap="3.0" maxSpeed="20" accel="1.2"
           decel="4.0" sigma="0.5" guiShape="bus"/>
</additional>
"""


# General traffic of the DfT-calibrated demand. The network encodes access only for
# passenger/taxi/bus (Overture), so LGVs, HGVs and motorcycles drive with passenger
# permissions; they differ in size and dynamics only.
GENERAL_VTYPES = {
    "car": '<vType id="car" vClass="passenger" length="4.5" minGap="2.5" maxSpeed="50" '
    'accel="2.6" decel="4.5" sigma="0.5" guiShape="passenger"/>',
    "lgv": '<vType id="lgv" vClass="passenger" length="5.8" minGap="2.5" maxSpeed="40" '
    'accel="2.0" decel="4.5" sigma="0.5" guiShape="delivery"/>',
    "hgv": '<vType id="hgv" vClass="passenger" length="10.0" minGap="3.0" maxSpeed="25" '
    'accel="1.0" decel="4.0" sigma="0.5" guiShape="truck"/>',
    "motorcycle": '<vType id="motorcycle" vClass="passenger" length="2.2" minGap="1.5" '
    'maxSpeed="40" accel="3.0" decel="6.0" sigma="0.5" guiShape="motorcycle"/>',
}
BUS_VTYPE = (
    '<vType id="bus" vClass="bus" length="11.2" minGap="3.0" maxSpeed="20" accel="1.2" '
    'decel="4.0" sigma="0.5" guiShape="bus"/>'
)
# DfT class column -> general vType.
DFT_CLASS_VTYPE = {
    "cars_and_taxis": "car",
    "lgvs": "lgv",
    "all_hgvs": "hgv",
    "two_wheeled_motor_vehicles": "motorcycle",
}
GENERAL_DISTRIBUTION = "general"


def write_general_vtypes(path: Path, mix: dict[str, float], include_bus: bool = True) -> Path:
    """General vTypes plus a ``general`` vTypeDistribution weighted by the DfT class mix."""
    ids = list(GENERAL_VTYPES)
    probs = [mix.get(next(c for c, v in DFT_CLASS_VTYPE.items() if v == i), 0.0) for i in ids]
    lines = ["<additional>", *(f"    {GENERAL_VTYPES[i]}" for i in ids)]
    if include_bus:
        lines.append(f"    {BUS_VTYPE}")
    lines.append(
        f'    <vTypeDistribution id="{GENERAL_DISTRIBUTION}" vTypes="{" ".join(ids)}" '
        f'probabilities="{" ".join(f"{p:.4f}" for p in probs)}"/>'
    )
    lines.append("</additional>")
    path.write_text("\n".join(lines) + "\n")
    return path


def write_vtypes(out_dir: Path) -> Path:
    path = out_dir / "vtypes.add.xml"
    path.write_text(VTYPES)
    return path


def random_trips(
    net: Path,
    out_dir: Path,
    name: str,
    vtype: str,
    vclass: str,
    begin: float,
    end: float,
    period: float,
    seed: int,
    vtypes: Path,
    *,
    fringe_factor: float = 1,
    min_distance: float = 0,
    speed_exponent: float = 0,
    log: Path | None = None,
) -> Path:
    """Run randomTrips.py with duarouter validation; return the routed ``.rou.xml``."""
    trips, routes = out_dir / f"{name}.trips.xml", out_dir / f"{name}.rou.xml"
    cmd = [sys.executable, sumo_env.tool("randomTrips.py"), "-n", net, "-a", vtypes]
    cmd += ["-o", trips, "-r", routes, "-b", begin, "-e", end, "-p", period, "--seed", seed]
    cmd += ["--prefix", f"{name}_", "--trip-attributes", f'type="{vtype}"']
    cmd += ["--edge-permission", vclass, "--fringe-factor", fringe_factor, "--validate"]
    cmd += ["--remove-loops", "--random-depart"]
    if min_distance:
        cmd += ["--min-distance", min_distance]
    if speed_exponent:
        cmd += ["--speed-exponent", speed_exponent]
    sumo_env.run(cmd, log=log, cwd=out_dir)
    _strip_vtypes(routes)
    return routes


def _strip_vtypes(routes: Path) -> None:
    """duarouter copies vType definitions into routes; SUMO loads them from vtypes.add.xml."""
    tree = ET.parse(routes)
    root = tree.getroot()
    for vtype in root.findall("vType"):
        root.remove(vtype)
    tree.write(routes, encoding="UTF-8", xml_declaration=True)


def count_vehicles(routes: Path) -> int:
    return sum(1 for _, el in ET.iterparse(routes) if el.tag in ("vehicle", "trip"))


def synthetic_buses(
    net: Path, out_dir: Path, cfg: dict, sim: dict, seed: int, vtypes: Path, log: Path
) -> tuple[Path, dict]:
    """Synthetic bus lines on fast (major) roads, run as fixed-headway flows.

    These are NOT TfL routes: randomTrips draws long bus-permitted origin/destination
    pairs weighted by speed^exponent; each routed path becomes a flow without stops.
    """
    n = int(cfg["routes"])
    routed = random_trips(
        net,
        out_dir,
        "busroute",
        "bus",
        "bus",
        0,
        n,
        1,
        seed,
        vtypes,
        fringe_factor=5,
        min_distance=cfg.get("min_distance_m", 3000),
        speed_exponent=cfg.get("speed_exponent", 4),
        log=log,
    )
    headway = float(cfg["headway_s"])
    lines = []
    for _, el in ET.iterparse(routed):
        if el.tag == "vehicle":
            route = el.find("route")
            if route is not None:
                lines.append(route.get("edges"))
    out = out_dir / "synthetic_buses.rou.xml"
    with out.open("w") as f:
        f.write("<routes>\n")
        for i, edges in enumerate(lines):
            rid = f"bus_syn{i:02d}"
            begin = sim["begin_s"] + headway * i / max(1, len(lines))
            f.write(f'    <route id="{rid}" edges="{edges}"/>\n')
            f.write(
                f'    <flow id="{rid}" type="bus" route="{rid}" begin="{begin:.1f}" '
                f'end="{sim["end_s"]}" period="{headway:.1f}" line="{rid}"/>\n'
            )
        f.write("</routes>\n")
    return out, {"lines": len(lines), "headway_s": headway, "synthetic": True}


def count_vehicles_or_routes(routes: Path) -> int:
    """Number of vehicles, trips or top-level named routes in a route file."""
    n = 0
    for _, el in ET.iterparse(routes):
        if el.tag in ("vehicle", "trip") or (el.tag == "route" and el.get("id")):
            n += 1
        el.clear()
    return n
