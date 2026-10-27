"""Retain rebuilt SUMO trajectories with a protocol manifest and web replay."""

import argparse
import gzip
import hashlib
import json
import math
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from common.contract import validate
from traffic.rebuild_corridor import VEHICLES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(source, destination, period):
    config = json.loads((source / f"{period}.config.json").read_text())
    collisions = ET.parse(source / f"{period}.collisions.xml").getroot().findall("collision")
    if collisions:
        raise ValueError(f"Refusing publication: {len(collisions)} collisions in {period}")
    summary = ET.parse(source / f"{period}.summary.xml").getroot().findall("step")
    if any(int(step.get("teleports", "0")) > 0 for step in summary):
        raise ValueError("Teleport detected")
    log = (source / f"{period}.sumo.log").read_text()
    if "collision with" in log or "Teleporting" in log:
        raise ValueError("Unsafe simulation log")
    t0 = {"am_peak": 31800, "inter_peak": 49800, "pm_peak": 64200}[period]
    destination.mkdir(parents=True, exist_ok=False)
    vehicles = []
    lookup = {}
    frames = []
    binary = bytearray()
    samples = []
    max_speed = 0
    with gzip.open(source / f"{period}.fcd.xml.gz", "rb") as stream:
        for _, element in ET.iterparse(stream, events=["end"]):
            if element.tag != "timestep":
                continue
            time = float(element.get("time"))
            if t0 <= time <= t0 + 599:
                rows = []
                ids = []
                positions = []
                for vehicle in element:
                    attrs = vehicle.attrib
                    identity = attrs["id"]
                    kind = attrs["type"]
                    if identity not in lookup:
                        lookup[identity] = len(vehicles)
                        vehicles.append({"id": identity, "type": kind})
                    x, y, z, speed = map(
                        float, (attrs["x"], attrs["y"], attrs["z"], attrs["speed"])
                    )
                    heading = math.radians(90 - float(attrs["angle"]))
                    rows.append(struct.pack("<Ifffff", lookup[identity], x, y, heading, z, speed))
                    ids.append("v" + str(lookup[identity]))
                    positions.append([x, y, z])
                    max_speed = max(max_speed, speed)
                binary.extend(struct.pack("<I", len(rows)))
                binary.extend(b"".join(rows))
                frames.append({"ids": ids, "positions": positions})
                samples.append(time - t0)
            element.clear()
    if samples != [i * 0.5 for i in range(1199)]:
        raise ValueError("Incomplete rebuilt timeline")
    binary_path = destination / "traffic.wasm"
    binary_path.write_bytes(binary)
    specs = {key: dict(length=v[1], width=v[2], height=v[3]) for key, v in VEHICLES.items()}
    report = {
        "collisions": len(collisions),
        "teleports": 0,
        "source_route_selection": config["counts"],
        "vehicles_recorded": len(vehicles),
        "max_speed_m_s": max_speed,
        "final_summary": summary[-1].attrib,
        "simulation_step_s": 0.1,
        "recording_step_s": 0.5,
        "limitations": config["assumptions"],
    }
    (destination / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    meta = {
        "schema": "corridor-micro-v1",
        "t0": t0,
        "dt": 0.5,
        "frames": len(frames),
        "synthetic": True,
        "coordinate_frame": "ENU",
        "units": "m",
        "heading": "radians counter-clockwise from east",
        "binary": {
            "asset": "traffic.wasm",
            "record_bytes": 24,
            "bytes": len(binary),
            "sha256": digest(binary_path),
            "frame_layout": "uint32 count; count * (uint32 id, float32 east,north,heading,up,speed)",
        },
        "vehicles": vehicles,
        "vehicle_specs": specs,
        "provenance": {
            "sumo_version": "1.28.0",
            "rebuilt": True,
            "demand_fraction": config["fraction"],
            "validated": report,
            "observed": False,
        },
    }
    (destination / "traffic.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n")
    (destination / "trajectories.json").write_text(
        json.dumps({"frames": frames[::2]}, separators=(",", ":")) + "\n"
    )
    # Retain all inputs needed to reproduce this experiment independently of scratch.
    for original, target in [
        ("network.net.xml", "network.net.xml.gz"),
        (f"{period}.rou.xml", "routes.rou.xml.gz"),
    ]:
        with (
            (source / original).open("rb") as incoming,
            gzip.open(destination / target, "wb") as outgoing,
        ):
            shutil.copyfileobj(incoming, outgoing)
    root = Path(__file__).resolve().parents[2]
    with zipfile.ZipFile(destination / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("rebuild_corridor.py", "export_corridor_micro.py", "corridor_reservations.py"):
            archive.write(root / "src/traffic" / name, "src/traffic/" + name)
    command = config["command"]
    portable = []
    for value in command:
        if value.endswith("/sumo"):
            value = "sumo"
        elif value.endswith("network.net.xml"):
            value = "network.net.xml.gz"
        elif value.endswith(f"{period}.rou.xml"):
            value = "routes.rou.xml.gz"
        elif "/" in value and value.startswith(str(source)):
            value = Path(value).name
        portable.append(value)
    (destination / "reproduce.json").write_text(
        json.dumps(
            {
                "controller": "traffic.corridor_reservations",
                "command": portable,
                "sumo_version": "1.28.0",
                "assumptions": config["assumptions"],
            },
            indent=2,
        )
        + "\n"
    )
    spatial = {
        "frame": "ENU",
        "units": "m",
        "origin": {
            "longitude": -0.200473,
            "latitude": 51.506427,
            "height_m": 0,
            "vertical_datum": "Inherited exported lane elevation; original survey datum unknown",
        },
        "bounds_m": {"min": [-5000, -5000, -100], "max": [5000, 5000, 500]},
    }
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": "imperial_corridor",
        "simulation": "traffic",
        "run_id": f"micro_v7_{period}",
        "status": "complete",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "code_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            "dirty": True,
            "parameters": {
                "microscopic": True,
                "illustrative": True,
                "seed": 42,
                "demand_fraction": config["fraction"],
                "original_signal_timings_available": False,
            },
            "inputs": [
                {"id": name, "sha256": digest(destination / name)}
                for name in ["network.net.xml.gz", "routes.rou.xml.gz"]
            ],
        },
        "spatial": spatial,
        "time": {"unit": "s", "samples": samples[::2]},
        "layers": [
            {
                "id": "traffic",
                "kind": "trajectories",
                "format": "trajectory_frames",
                "asset": "trajectories.json",
                "sampling": "linear",
                "display": {"widget": "trajectories", "capabilities": ["pick", "opacity"]},
            }
        ],
        "artifacts": [
            {
                "id": "source_snapshot"
                if name == "source_snapshot.zip"
                else name.replace(".", "_"),
                "asset": name,
                "sha256": digest(destination / name),
                "media_type": media,
            }
            for name, media in [
                ("source_snapshot.zip", "application/zip"),
                ("network.net.xml.gz", "application/gzip"),
                ("routes.rou.xml.gz", "application/gzip"),
                ("traffic.wasm", "application/octet-stream"),
                ("traffic.json", "application/json"),
                ("validation.json", "application/json"),
                ("reproduce.json", "application/json"),
            ]
        ],
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    validate(destination / "manifest.json")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("period")
    args = parser.parse_args()
    export(args.source, args.destination, args.period)
