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


def write_meandata(path: Path, out_dir: Path, begin: float, end: float, general: list[str]) -> dict:
    """edgeData outputs over the measured hour: 300 s and 3600 s (all vehicles) and
    3600 s for general traffic only (``general`` vTypes, the calibration check)."""
    files = {
        "edge_300s": (out_dir / "edgedata_300s.xml", 300, ""),
        "edge_3600s": (out_dir / "edgedata_3600s.xml", 3600, ""),
        "general_3600s": (out_dir / "edgedata_general_3600s.xml", 3600, " ".join(general)),
    }
    lines = ["<additional>"]
    for key, (file, period, vtypes) in files.items():
        extra = f' vTypes="{vtypes}"' if vtypes else ""
        lines.append(
            f'    <edgeData id="{key}" file="{file.resolve()}" period="{period}" '
            f'begin="{begin:g}" end="{end:g}" excludeEmpty="true"{extra}/>'
        )
    lines.append("</additional>")
    path.write_text("\n".join(lines) + "\n")
    return {k: v[0] for k, v in files.items()}


def run_period(
    net: Path,
    routes: list[Path],
    additional: list[Path],
    out_dir: Path,
    window: dict,
    sim: dict,
    *,
    stop_output: bool = False,
) -> dict:
    """Simulate ``window['sim_begin_s']``..``window['end_s']`` (seconds since midnight).

    FCD is written from ``window['fcd_begin_s']`` to the end (gzip); edgeData covers the
    measured hour ``start_s``..``end_s``; ``stop_output`` adds ``stopinfos.xml``. The
    vehicle routes with edge exit times (``vehroutes.xml.gz``, vehicles still driving
    at the end included) and SUMO's warnings (``sumo_warnings.log``: teleports) feed the
    lane-path playback (``lane_routes``).
    """
    fcd = out_dir / "fcd.xml.gz"
    vehroutes = out_dir / "vehroutes.xml.gz"
    warnings = out_dir / "sumo_warnings.log"
    stats = out_dir / "statistics.xml"
    cfg = out_dir / "run.sumocfg"
    rel = lambda paths: ",".join(str(Path(p).resolve()) for p in paths)
    meso = sim.get("mesosim", False)
    stop = f'\n        <stop-output value="{(out_dir / "stopinfos.xml").resolve()}"/>'
    # Mesoscopic queues (junction control via extra_options "meso-junction-control");
    # positions interpolated for the FCD.
    meso_opts = (
        '\n        <meso-overtaking value="true"/>\n        <meso-interpolate-pos value="true"/>'
        if meso
        else ""
    )
    extra = "".join(
        f'\n        <{k} value="{str(v).lower() if isinstance(v, bool) else v}"/>'
        for k, v in sim.get("extra_options", {}).items()
    )
    cfg.write_text(
        f"""<configuration>
    <input>
        <net-file value="{net.resolve()}"/>
        <route-files value="{rel(routes)}"/>
        <additional-files value="{rel(additional)}"/>
    </input>
    <time>
        <begin value="{window["sim_begin_s"]:g}"/>
        <end value="{window["end_s"]:g}"/>
        <step-length value="{sim["step_s"]}"/>
    </time>
    <processing>
        <time-to-teleport value="{sim.get("time_to_teleport_s", 120)}"/>
        <ignore-route-errors value="true"/>
        <collision.action value="warn"/>
        <threads value="{sim.get("threads", 1)}"/>
        <max-depart-delay value="{sim.get("max_depart_delay_s", -1)}"/>{extra}
    </processing>
    <mesoscopic>
        <mesosim value="{str(meso).lower()}"/>{meso_opts}
    </mesoscopic>
    <random_number>
        <seed value="{sim.get("seed", 42)}"/>
    </random_number>
    <output>
        <fcd-output value="{fcd.resolve()}"/>
        <fcd-output.attributes value="x,y,angle,type"/>
        <device.fcd.begin value="{window["fcd_begin_s"]:g}"/>
        <device.fcd.period value="{sim["step_s"]}"/>
        <statistic-output value="{stats.resolve()}"/>{stop if stop_output else ""}
        <vehroute-output value="{vehroutes.resolve()}"/>
        <vehroute-output.exit-times value="true"/>
        <vehroute-output.write-unfinished value="true"/>
    </output>
    <report>
        <no-step-log value="true"/>
        <error-log value="{warnings.resolve()}"/>
        <duration-log.statistics value="true"/>
    </report>
</configuration>
"""
    )
    sumo_env.run([sumo_env.binary("sumo"), "-c", cfg], log=out_dir / "sumo.log")
    out = {
        "fcd": fcd,
        "config": cfg,
        "statistics": read_statistics(stats),
        "vehroutes": vehroutes,
        "warnings": warnings,
    }
    if stop_output:
        out["stopinfos"] = out_dir / "stopinfos.xml"
    return out
