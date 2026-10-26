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
