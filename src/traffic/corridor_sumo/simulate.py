"""Run SUMO headless with FCD output over the recording window."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from . import sumo_env


def run_sumo(
    net: Path, routes: list[Path], additional: list[Path], out_dir: Path, sim: dict
) -> dict:
    """Simulate ``begin_s``..``end_s``; FCD is recorded from ``record_from_s`` each step."""
    fcd = out_dir / "fcd.xml"
    stats = out_dir / "statistics.xml"
    cfg = out_dir / "run.sumocfg"
    rel = lambda paths: ",".join(str(Path(p).resolve()) for p in paths)
    cfg.write_text(
        f"""<configuration>
    <input>
        <net-file value="{net.resolve()}"/>
        <route-files value="{rel(routes)}"/>
        <additional-files value="{rel(additional)}"/>
    </input>
    <time>
        <begin value="{sim["begin_s"]}"/>
        <end value="{sim["end_s"]}"/>
        <step-length value="{sim["step_s"]}"/>
    </time>
    <processing>
        <time-to-teleport value="{sim.get("time_to_teleport_s", 120)}"/>
        <ignore-route-errors value="true"/>
        <collision.action value="warn"/>
    </processing>
    <random_number>
        <seed value="{sim.get("seed", 42)}"/>
    </random_number>
    <output>
        <fcd-output value="{fcd.resolve()}"/>
        <fcd-output.attributes value="x,y,angle,type,speed,lane"/>
        <device.fcd.begin value="{sim["record_from_s"]}"/>
        <device.fcd.period value="{sim["step_s"]}"/>
        <statistic-output value="{stats.resolve()}"/>
    </output>
    <report>
        <no-step-log value="true"/>
        <duration-log.statistics value="true"/>
    </report>
</configuration>
"""
    )
    sumo_env.run([sumo_env.binary("sumo"), "-c", cfg], log=out_dir / "sumo.log")
    return {"fcd": fcd, "config": cfg, "statistics": read_statistics(stats)}


def read_statistics(path: Path) -> dict:
    """Vehicle and teleport counts from SUMO's statistic output."""
    root = ET.parse(path).getroot()
    out = {}
    for tag in ("vehicles", "teleports", "vehicleTripStatistics", "safety"):
        el = root.find(tag)
        if el is not None:
            out[tag] = {k: _num(v) for k, v in el.attrib.items()}
    return out


def _num(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v
