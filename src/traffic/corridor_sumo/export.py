"""FCD -> recorded frames -> protocol sparse trajectories and the viewer binary.

``traffic.bin`` layout (little-endian), one block per frame in time order::

    uint32 count
    count x { uint32 vehicle_index; float32 x; float32 y; float32 heading_rad }

``vehicle_index`` indexes ``traffic.json`` ``vehicles``; x/y are scene ENU metres;
heading is ENU radians counter-clockwise from +x (east). SUMO's ``angle`` is
degrees clockwise from north, so ``heading = radians(90 - angle)``.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RECORD = np.dtype([("i", "<u4"), ("x", "<f4"), ("y", "<f4"), ("h", "<f4")])
SCHEMA = "corridor-traffic-v1"
# Vehicle kinds in the viewer index (prefix of the SUMO vType id); lgv/hgv/motorcycle
# come from the DfT-calibrated demand.
VEHICLE_TYPES = ("car", "taxi", "bus", "lgv", "hgv", "motorcycle")


@dataclass
class Recording:
    """Recorded samples: ``frames[k]`` is a list of (vehicle index, x, y, heading)."""

    times: list[float] = field(default_factory=list)
    vehicles: list[dict] = field(default_factory=list)  # {id, type}
    frames: list[list[tuple[int, float, float, float]]] = field(default_factory=list)


def heading_from_sumo_angle(angle_deg: float) -> float:
    """SUMO angle (deg, clockwise from north) -> ENU heading (rad, CCW from +x), (-pi, pi]."""
    h = math.radians(90.0 - angle_deg)
    return math.atan2(math.sin(h), math.cos(h))


def vehicle_type(sumo_type: str) -> str:
    for kind in VEHICLE_TYPES:
        if sumo_type.startswith(kind):
            return kind
    raise ValueError(f"Unknown SUMO vehicle type {sumo_type!r}")


def _open(path: Path):
    """Path for plain XML; a gzip stream for ``.gz`` (released when garbage collected)."""
    if str(path).endswith(".gz"):
        return gzip.open(path, "rb")
    return path


def parse_fcd(
    path: Path,
    t_from: float,
    t_to: float,
    kinds: dict[str, str] | None = None,
    half: float | None = None,
) -> Recording:
    """Read SUMO FCD XML (optionally gzipped), keeping time steps within [t_from, t_to].

    ``kinds`` maps SUMO vType ids that do not start with a known kind (e.g. buses from
    another demand source) to a kind in ``VEHICLE_TYPES``. With ``half``, only samples
    inside the square ``|x|, |y| <= half`` are kept (a network buffer beyond the scene
    domain is simulated but not recorded); vehicles never inside are omitted.
    """
    kinds = kinds or {}
    rec = Recording()
    index: dict[str, int] = {}
    for _, el in ET.iterparse(_open(path), events=("end",)):
        if el.tag != "timestep":
            continue
        t = float(el.get("time"))
        if t_from - 1e-6 <= t <= t_to + 1e-6:
            frame = []
            for v in el.iter("vehicle"):
                vid = v.get("id")
                x, y = float(v.get("x")), float(v.get("y"))
                if half is not None and (abs(x) > half or abs(y) > half):
                    continue
                if vid not in index:
                    index[vid] = len(rec.vehicles)
                    sumo_type = v.get("type", "car")
                    kind = kinds.get(sumo_type) or vehicle_type(sumo_type)
                    rec.vehicles.append({"id": vid, "type": kind})
                frame.append(
                    (
                        index[vid],
                        x,
                        y,
                        heading_from_sumo_angle(float(v.get("angle"))),
                    )
                )
            rec.times.append(round(t, 6))
            rec.frames.append(frame)
        el.clear()
    return rec


def select(rec: Recording, max_records: int, max_concurrent: int | None = None) -> Recording:
    """Keep whole vehicle trajectories (never parts) within a record/concurrency budget.

    Buses are always kept; cars and taxis are admitted in a stable hash order of
    their ids, so the subset is deterministic and unbiased by departure time.
    """
    n_frames = len(rec.frames)
    presence: dict[int, list[int]] = {}
    for k, frame in enumerate(rec.frames):
        for i, *_ in frame:
            presence.setdefault(i, []).append(k)
    order = sorted(
        presence,
        key=lambda i: (
            rec.vehicles[i]["type"] != "bus",
            hashlib.sha1(rec.vehicles[i]["id"].encode()).hexdigest(),
        ),
    )
    counts = np.zeros(n_frames, dtype=np.int64)
    budget = max_records
    keep = set()
    for i in order:
        frames = np.asarray(presence[i])
        if len(frames) > budget:
            continue
        if (
            max_concurrent
            and rec.vehicles[i]["type"] != "bus"
            and (counts[frames] + 1).max() > max_concurrent
        ):
            continue
        counts[frames] += 1
        budget -= len(frames)
        keep.add(i)
    remap = {old: new for new, old in enumerate(sorted(keep))}
    return Recording(
        times=list(rec.times),
        vehicles=[rec.vehicles[old] for old in sorted(keep)],
        frames=[[(remap[i], x, y, h) for i, x, y, h in f if i in remap] for f in rec.frames],
    )


def write_binary(rec: Recording, path: Path) -> int:
    """Write ``traffic.bin``; return its size in bytes."""
    with path.open("wb") as out:
        for frame in rec.frames:
            out.write(struct.pack("<I", len(frame)))
            if frame:
                out.write(np.array(frame, dtype=RECORD).tobytes())
    return path.stat().st_size


def read_binary(path: Path, n_frames: int) -> list[np.ndarray]:
    """Inverse of ``write_binary`` (structured arrays with fields i, x, y, h)."""
    data = path.read_bytes()
    frames, offset = [], 0
    for _ in range(n_frames):
        (count,) = struct.unpack_from("<I", data, offset)
        offset += 4
        frames.append(np.frombuffer(data, dtype=RECORD, count=count, offset=offset))
        offset += count * RECORD.itemsize
    if offset != len(data):
        raise ValueError("traffic.bin has trailing or missing bytes")
    return frames


def bin_size(rec: Recording) -> int:
    return 4 * len(rec.frames) + RECORD.itemsize * sum(len(f) for f in rec.frames)


def write_traffic_json(
    rec: Recording, path: Path, bin_path: Path, synthetic: bool, provenance: dict
) -> dict:
    times = rec.times
    dt = round(times[1] - times[0], 6) if len(times) > 1 else 0.0
    if any(abs((b - a) - dt) > 1e-6 for a, b in itertools.pairwise(times)):
        raise ValueError("Recorded frames are not evenly spaced; t0/dt cannot describe them")
    doc = {
        "schema": SCHEMA,
        "t0": times[0],
        "dt": dt,
        "frames": len(times),
        "synthetic": synthetic,
        "coordinate_frame": "ENU",
        "units": "m",
        "heading": "radians counter-clockwise from +x (east)",
        "binary": {
            "asset": bin_path.name,
            "byte_order": "little",
            "frame_layout": "uint32 count, then count x {uint32 vehicleIndex, float32 x, "
            "float32 y, float32 headingRad}",
            "bytes": bin_path.stat().st_size,
            "sha256": hashlib.sha256(bin_path.read_bytes()).hexdigest(),
        },
        "vehicles": rec.vehicles,
        "provenance": provenance,
    }
    path.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    return doc


def write_trajectory_frames(rec: Recording, path: Path, z: float = 0.0) -> None:
    """Protocol v1.1 ``trajectory_frames`` JSON (ids = SUMO vehicle ids, ENU metres)."""
    frames = [
        {
            "ids": [rec.vehicles[i]["id"] for i, *_ in frame],
            "positions": [[round(x, 2), round(y, 2), z] for _, x, y, _ in frame],
        }
        for frame in rec.frames
    ]
    path.write_text(json.dumps({"frames": frames}, separators=(",", ":"), allow_nan=False))


def heading_check(rec: Recording, min_step_m: float = 2.0) -> dict:
    """Compare exported heading with the direction of motion between frames."""
    last: dict[int, tuple[float, float, float]] = {}
    errors = []
    for frame in rec.frames:
        current = {}
        for i, x, y, h in frame:
            if i in last:
                px, py, ph = last[i]
                if math.hypot(x - px, y - py) >= min_step_m:
                    motion = math.atan2(y - py, x - px)
                    mean = math.atan2(math.sin(h) + math.sin(ph), math.cos(h) + math.cos(ph))
                    d = abs(math.atan2(math.sin(motion - mean), math.cos(motion - mean)))
                    errors.append(math.degrees(d))
            current[i] = (x, y, h)
        last = current
    if not errors:
        return {"samples": 0}
    errors.sort()
    return {
        "samples": len(errors),
        "median_deg": round(errors[len(errors) // 2], 2),
        "p95_deg": round(errors[int(len(errors) * 0.95)], 2),
    }
