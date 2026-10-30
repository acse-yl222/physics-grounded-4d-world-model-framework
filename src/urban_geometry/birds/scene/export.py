"""Bird replay files for the city viewer (bird-layer.js), one set per scene.

bird_replay.json   manifest (schema uwm-bird-replay-2): frames, birds, clock, quantisation, sites, provenance
bird_replay.i16    int16 little-endian records per frame per bird, frame-major ((f * birds + n) * 6):
                   [viewer X, viewer Y, viewer Z] (scale 0.1 m about "offset_m"), yaw (pi / 32767 rad),
                   speed (0.01 m/s), bank (pi / 32767 rad)
bird_states.u8     uint8 per frame per bird: 0 FORAGE, 1 TRANSIT, 2 MURMURATION, 3 DESCENT, 4 ROOST

Viewer frame = the city GLB frame (Y up): X = x, Y = z, Z = -y; yaw = atan2(vX, vZ) with vX = vx,
vZ = -vy (heading 0 = +Z, pi / 2 = +X), the same transform as the South Kensington replay adapter.
The viewer interpolates linearly between frames.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

STATE_NAMES = ["FORAGE", "TRANSIT", "MURMURATION", "DESCENT", "ROOST"]
POSITION_SCALE = 0.1
ANGLE_SCALE = np.pi / 32767
SPEED_SCALE = 0.01


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def to_viewer(pos, vel, bank):
    """(F, N, 3) local z-up positions/velocities and (F, N) bank -> (F, N, 6) viewer records (float)."""
    X, Y, Z = pos[..., 0], pos[..., 2], -pos[..., 1]
    yaw = np.arctan2(vel[..., 0], -vel[..., 1])
    speed = np.linalg.norm(vel, axis=-1)
    return np.stack([X, Y, Z, yaw, speed, bank], axis=-1)


# (label, the state fraction that ends the moment): the day is scanned forward, each moment starting
# where the previous one ended, so a flock's moments are always in day order and never overlap
MOMENTS = [
    ("Roosting", lambda f: f[4] < 0.9),  # first birds leave the roost
    ("Leaving the roost", lambda f: f[0] >= 0.9),  # nearly all foraging
    ("Foraging", lambda f: f[0] < 0.9),  # first birds head home
    ("Heading home", lambda f: f[2] >= 0.5),  # most of the flock murmurating
    ("Murmuration", lambda f: f[3] + f[4] >= 0.1),  # descent to the roost begins
    ("Settling", lambda f: f[4] >= 0.9),  # nearly all roosted
]


def flock_moments(bstate, frame_times):
    """
    Named moments of one flock's day from its state counts per frame: [{label, start_s, mid_s,
    end_s}], replay time. A moment the flock never reaches (e.g. no murmuration) is left out.
    """
    t = np.asarray(frame_times, dtype=float)
    frac = np.stack([(bstate == k).mean(axis=1) for k in range(len(STATE_NAMES))], axis=1)
    out, i = [], 0
    for label, ends in MOMENTS:
        j = i
        while j < len(t) and not ends(frac[j]):
            j += 1
        if j >= len(t):
            break
        if j > i:
            out.append(
                {
                    "label": label,
                    "start_s": float(t[i]),
                    "mid_s": float((t[i] + t[j]) / 2),
                    "end_s": float(t[j]),
                }
            )
        i = j
    return out


def write_replay(out_dir, pos, vel, bank, bstate, frame_times, manifest_extra):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rec = to_viewer(pos, vel, bank)
    offset = np.round(np.nanmean(rec[..., :3].reshape(-1, 3), axis=0), 1)
    q = np.empty(rec.shape, dtype="<i2")
    q[..., :3] = np.clip(np.round((rec[..., :3] - offset) / POSITION_SCALE), -32767, 32767)
    q[..., 3] = np.round(rec[..., 3] / ANGLE_SCALE)
    q[..., 4] = np.clip(np.round(rec[..., 4] / SPEED_SCALE), 0, 32767)
    q[..., 5] = np.clip(np.round(rec[..., 5] / ANGLE_SCALE), -32767, 32767)
    span = np.abs(rec[..., :3] - offset).max()
    if span > 32767 * POSITION_SCALE:
        raise ValueError(
            f"positions span {span:.0f} m from the offset; int16 at 0.1 m holds 3276 m"
        )
    q.tofile(out / "bird_replay.i16")
    bstate.astype(np.uint8).tofile(out / "bird_states.u8")
    frames, birds = bstate.shape
    dt = float(np.median(np.diff(frame_times))) if frames > 1 else 0.0
    counts = {STATE_NAMES[k]: int((bstate == k).sum()) for k in range(len(STATE_NAMES))}
    manifest = {
        "schema": "uwm-bird-replay-2",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frames": int(frames),
        "birds": int(birds),
        "frame_dt_s": dt,
        "first_frame_t_s": float(frame_times[0]),
        "last_frame_t_s": float(frame_times[-1]),
        "record": ["worldX", "worldY", "worldZ", "yaw_rad", "speed_mps", "bank_rad"],
        "encoding": {
            "dtype": "int16 little-endian",
            "layout": "frame-major: (frame * birds + bird) * 6",
            "offset_m": offset.tolist(),
            "position_scale_m": POSITION_SCALE,
            "angle_scale_rad": ANGLE_SCALE,
            "speed_scale_mps": SPEED_SCALE,
        },
        "transform": "viewer (X, Y, Z) = (x, z, -y) of the scene's local z-up frame; yaw = atan2(vx, -vy)",
        "state_names": STATE_NAMES,
        "state_sample_counts": counts,
        "files": {
            name: {"bytes": (out / name).stat().st_size, "sha256": _sha256(out / name)}
            for name in ("bird_replay.i16", "bird_states.u8")
        },
        **manifest_extra,
    }
    (out / "bird_replay.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def write_viewer_config(config_path, replay_manifest_path, label, seed):
    """project/<scene>/configs/bird_visualization.json (mirrors uav_visualization.json)."""
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(Path(replay_manifest_path).resolve(), config_path.parent.resolve())
    config = {"replay": Path(rel).as_posix(), "label": label, "seed": seed}
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return config
