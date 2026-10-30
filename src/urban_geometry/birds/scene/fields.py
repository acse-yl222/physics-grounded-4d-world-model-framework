"""The scene's published environmental fields and sun clock, as samplers the bird model can call.

Fields come from a scene folder laid out like the city viewer's (scenes/<id>/scene.json + physics):
the raw float arrays when present (local runs), otherwise the published web frames, decoded with
the encoding recorded in physics/web/index.json (value = lo + byte / 255 * (hi - lo); rgb3 = u, v, w).
Placement follows scene.json "grid" exactly as the viewer does: column c starts at local
x = x0 + c * cell, row r (0 = south) spans local y = -z_south + r * cell (local y = -gltf z).
Each layer is mapped onto bird time with its own t0_s / step_s (the viewer's mapping) and held at
its first / last frame outside that span.

The published fields are 2-D slices at one height (e.g. wind at 8-12 m); they are applied at every
altitude. Pollution (arbitrary tracer units) is scaled to the bird model's 0-1 by the 99th percentile
over the bird domain. Temperature is used in degrees C as published.
"""

import io
import json
import math
import urllib.request
from datetime import date as Date
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

PUBLIC_SITE = "https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/"
LAYER_KEYS = {"wind": "wind", "pollution": "poll", "temperature": "temp"}


def _read_json(path_or_url):
    if str(path_or_url).startswith("http"):
        with urllib.request.urlopen(path_or_url, timeout=60) as r:
            return json.loads(r.read())
    return json.loads(Path(path_or_url).read_text())


def fetch_scene(viewer_id, dest, base_url=PUBLIC_SITE, layers=("wind", "poll", "temp")):
    """Download a published scene's scene.json, physics manifest and field frames into dest."""
    from PIL import Image  # noqa: F401  (decoding needs Pillow; fail early)

    dest = Path(dest)
    base = f"{base_url.rstrip('/')}/scenes/{viewer_id}/"
    scene = _read_json(base + "scene.json")
    scene.setdefault("id", viewer_id)  # the viewer adds it at load time; kept for fetch_model
    physics = scene.get("physics_dir", "physics/")
    (dest / physics / "web").mkdir(parents=True, exist_ok=True)
    (dest / "scene.json").write_text(json.dumps(scene, indent=1))
    for name in ("manifest.json", "web/index.json"):
        try:
            data = _read_json(base + physics + name)
        except OSError:
            continue
        (dest / physics / name).write_text(json.dumps(data, indent=1))
    index = json.loads((dest / physics / "web/index.json").read_text())
    for key in layers:
        meta = index["layers"].get(key)
        if not meta:
            continue
        ext = meta.get("extension", "png")
        (dest / physics / "web" / key).mkdir(parents=True, exist_ok=True)
        for k in range(meta["frames"]):
            target = dest / physics / "web" / key / f"{k:03d}.{ext}"
            if not target.exists():
                with urllib.request.urlopen(
                    f"{base}{physics}web/{key}/{k:03d}.{ext}", timeout=60
                ) as r:
                    target.write_bytes(r.read())
    return dest


def fetch_model(scene_dir, dest, site_url=PUBLIC_SITE, resources_url=None):
    """
    The scene's city GLB as the viewer loads it: scene.json model.parts_manifest (the resource
    catalogue's chunked GLB, each part checked against its SHA-256) reassembled into one file, plus
    model.supplement when the scene has one. Returns (glb, [supplements]).
    """
    import hashlib

    scene_dir, dest = Path(scene_dir), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    scene = json.loads((scene_dir / "scene.json").read_text())
    model = scene["model"]
    manifest_url = model["parts_manifest"]
    if resources_url:  # e.g. a local copy of the resource catalogue: same layout below /project/
        manifest_url = (
            f"{resources_url.rstrip('/')}/project/{manifest_url.split('/project/', 1)[1]}"
        )
    manifest = _read_json(manifest_url)
    glb = dest / manifest["name"]
    if not glb.exists():
        base = manifest_url.rsplit("/", 1)[0] + "/"
        with glb.with_suffix(".part").open("wb") as out:
            for part in manifest["parts"]:
                with urllib.request.urlopen(base + part["file"], timeout=600) as r:
                    data = r.read()
                if hashlib.sha256(data).hexdigest() != part["sha256"]:
                    raise ValueError(f"{part['file']}: SHA-256 does not match the parts manifest")
                out.write(data)
        glb.with_suffix(".part").rename(glb)
    supplements = []
    if model.get("supplement", {}).get("url"):
        rel = model["supplement"]["url"]
        target = dest / Path(rel).name
        if not target.exists():
            url = f"{site_url.rstrip('/')}/scenes/{scene.get('id') or scene_dir.name}/{rel}"
            with urllib.request.urlopen(url, timeout=600) as r:
                target.write_bytes(r.read())
        supplements.append(target)
    return glb, supplements


class _Layer:
    """One field layer cropped to the bird domain: frames (T, C, rows, cols) float32 + placement."""

    def __init__(self, frames, x0, y0, cell, t0, step):
        self.frames, self.x0, self.y0, self.cell = frames, x0, y0, cell
        self.t0, self.step = float(t0), float(step)

    def sample(self, positions, time):
        n = self.frames.shape[0]
        f = 0.0 if self.step <= 0 else (time - self.t0) / self.step
        f = min(max(f, 0.0), n - 1.0)
        k0 = math.floor(f)
        k1, s = min(k0 + 1, n - 1), f - k0
        coords = np.vstack(
            [
                (positions[:, 1] - self.y0) / self.cell - 0.5,
                (positions[:, 0] - self.x0) / self.cell - 0.5,
            ]
        )
        out = np.empty((positions.shape[0], self.frames.shape[1]))
        for c in range(self.frames.shape[1]):
            a = map_coordinates(self.frames[k0, c], coords, order=1, mode="nearest")
            b = map_coordinates(self.frames[k1, c], coords, order=1, mode="nearest") if s else a
            out[:, c] = a * (1 - s) + b * s
        return out


class SceneFields:
    """Wind / pollution / temperature of one scene, cropped to box_xy = (x0, y0, x1, y1) local metres."""

    def __init__(self, scene_dir, box_xy, pad_m=200.0):
        self.dir = Path(scene_dir)
        self.scene = json.loads((self.dir / "scene.json").read_text())
        self.physics = self.dir / self.scene.get("physics_dir", "physics/")
        index_path = self.physics / "web" / "index.json"
        self.index = json.loads(index_path.read_text())["layers"] if index_path.exists() else {}
        manifest_path = self.physics / "manifest.json"
        self.manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        self.box = [box_xy[0] - pad_m, box_xy[1] - pad_m, box_xy[2] + pad_m, box_xy[3] + pad_m]
        self.layers, self.sources = {}, {}
        for name, key in LAYER_KEYS.items():
            if key in self.scene.get("layers", {}):
                self.layers[name] = self._load(key)
        if "pollution" in self.layers:
            frames = self.layers["pollution"].frames
            positive = frames[frames > 0]
            self.pollution_scale = float(np.percentile(positive, 99)) if positive.size else 1.0
            self.layers["pollution"].frames = np.clip(frames / self.pollution_scale, 0.0, 1.0)

    # ---- loading
    def _window(self, cell, rows, cols):
        g = self.scene["grid"]
        x0, y0 = float(g["x0"]), -float(g["z_south"])
        c0 = max(0, int((self.box[0] - x0) / cell))
        c1 = min(cols, math.ceil((self.box[2] - x0) / cell))
        r0 = max(0, int((self.box[1] - y0) / cell))
        r1 = min(rows, math.ceil((self.box[3] - y0) / cell))
        if c1 <= c0 or r1 <= r0:
            raise ValueError("bird domain lies outside the field grid")
        return r0, r1, c0, c1, x0 + c0 * cell, y0 + r0 * cell

    def _load(self, key):
        layer = self.scene["layers"][key]
        g = self.scene["grid"]
        cell = float(layer.get("cell_m", g["cell_m"]))
        rows = round(g["rows"] * g["cell_m"] / cell)
        cols = round(g["cols"] * g["cell_m"] / cell)
        r0, r1, c0, c1, x0, y0 = self._window(cell, rows, cols)
        raw = self.physics / layer["file"] if layer.get("file") else None
        if raw is not None and raw.exists():
            arr = np.load(raw, mmap_mode="r")
            frames = np.asarray(arr[..., r0:r1, c0:c1], dtype=np.float32)
            self.sources[key] = f"raw array {layer['file']}"
        else:
            frames = self._decode_web(key, r0, r1, c0, c1)
        if frames.ndim == 3:
            frames = frames[:, None]  # (T, 1, rows, cols)
        t0 = layer.get("t0_s", 0.0)
        step = layer.get("step_s") or 0.0
        return _Layer(frames, x0, y0, cell, t0, step)

    def _decode_web(self, key, r0, r1, c0, c1):
        from PIL import Image

        meta = self.index.get(key)
        if meta is None:
            raise FileNotFoundError(f"{key}: neither the raw array nor web frames are available")
        lo, hi = meta["range"]
        ext = meta.get("extension", "png")
        frames = []
        for k in range(meta["frames"]):
            path = self.physics / "web" / key / f"{k:03d}.{ext}"
            img = np.asarray(Image.open(io.BytesIO(path.read_bytes()))).astype(np.float32)
            img = img[r0:r1, c0:c1]
            v = lo + img / 255.0 * (hi - lo)
            frames.append(np.moveaxis(v, -1, 0) if v.ndim == 3 else v)
        frames = np.stack(frames)
        if key == "poll":  # undo the published log encoding -> tracer concentration
            if meta.get("value_transform") == "log1p":  # log10(1 + c / scale)
                frames = meta.get("value_scale", 1.0) * (10.0**frames - 1.0)
            elif "log10" in meta.get("note", ""):  # log10(max(c, 0.1))
                frames = 10.0**frames
        self.sources[key] = (
            f"web frames web/{key}/*.{ext} (8-bit over {meta['range']}; {meta.get('note', '')})"
        )
        return frames.astype(np.float32)

    # ---- samplers for SimConfig.external_fields
    def samplers(self):
        out = {}
        if "wind" in self.layers:
            out["wind"] = lambda p, t: self.layers["wind"].sample(p, t)[:, :3]
        if "pollution" in self.layers:
            out["pollution"] = lambda p, t: self.layers["pollution"].sample(p, t)[:, 0]
        if "temperature" in self.layers:
            out["temperature"] = lambda p, t: self.layers["temperature"].sample(p, t)[:, 0]
        return out

    def span_s(self, name="wind"):
        """(first, last) frame time of a layer on the bird clock."""
        layer = self.layers[name]
        return layer.t0, layer.t0 + layer.step * (layer.frames.shape[0] - 1)

    def describe(self):
        return {
            "scene": self.scene.get("id") or self.dir.name,
            "layers": {
                name: {
                    "source": self.sources.get(LAYER_KEYS[name]),
                    "frames": int(layer.frames.shape[0]),
                    "cell_m": layer.cell,
                    "t0_s": layer.t0,
                    "step_s": layer.step,
                    "height": self.scene["layers"][LAYER_KEYS[name]].get("label", ""),
                }
                for name, layer in self.layers.items()
            },
            "pollution_scale": getattr(self, "pollution_scale", None),
            "vertical": "published 2-D slices, applied at every altitude",
        }


def framework_sun_position():
    """
    urban_flow.physics.solar.model.sun_position. That module imports torch for its shadow networks;
    without torch (the birds extra) the pure-math function is compiled from the module's own source,
    so the sun is always the framework's NOAA implementation, never a copy.
    """
    try:
        from urban_flow.physics.solar.model import sun_position

        return sun_position
    except ImportError:
        import ast
        import builtins
        import importlib.util
        import types

        origin = importlib.util.find_spec("urban_flow.physics.solar.model").origin
        tree = ast.parse(Path(origin).read_text())
        fn = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "sun_position"
        )
        module_code = compile(ast.Module(body=[fn], type_ignores=[]), origin, "exec")
        code = next(c for c in module_code.co_consts if isinstance(c, types.CodeType))
        return types.FunctionType(code, {"math": math, "__builtins__": builtins}, "sun_position")


class SunClock:
    """
    Roost-to-roost day from the scene's sun: bird time 0..duration maps linearly onto local clock
    time from (sunrise - before_h) to (sunset + after_h). light = sin(altitude) / sin(noon altitude)
    clipped to 0-1 (1 at solar noon, 0 below the horizon), which keeps the bird model's light
    thresholds (dawn 0.1+, dusk 0.55+, roost 0.1) near sunrise / late afternoon / sunset.
    phase = 0.5 + (clock - solar noon) / 24, so morning < 0.5 < evening as the state machine expects.
    """

    def __init__(self, altitude_deg, duration_s, before_h=0.75, after_h=1.0, source=""):
        self.altitude_deg = altitude_deg  # callable(local clock hours) -> degrees
        hours = np.arange(0.0, 24.0, 1.0 / 60.0)
        alt = np.array([altitude_deg(h) for h in hours])
        up = np.nonzero(alt > 0)[0]
        if not up.size:
            raise ValueError("the sun does not rise on this date")
        self.sunrise_h, self.sunset_h = float(hours[up[0]]), float(hours[up[-1]])
        self.noon_h = float(hours[np.argmax(alt)])
        self.noon_alt = float(alt.max())
        self.start_h = self.sunrise_h - before_h
        self.end_h = self.sunset_h + after_h
        self.duration_s = float(duration_s)
        self.source = source

    def clock_h(self, time):
        f = min(max(time / self.duration_s, 0.0), 1.0)
        return self.start_h + (self.end_h - self.start_h) * f

    def phase(self, time):
        return (0.5 + (self.clock_h(time) - self.noon_h) / 24.0) % 1.0

    def light(self, time):
        alt = self.altitude_deg(self.clock_h(time))
        return float(
            np.clip(math.sin(math.radians(alt)) / math.sin(math.radians(self.noon_alt)), 0, 1)
        )

    def describe(self):
        hm = lambda h: f"{int(h):02d}:{round(h % 1 * 60):02d}"
        return {
            "source": self.source,
            "local_window": [hm(self.start_h), hm(self.end_h)],
            "sunrise": hm(self.sunrise_h),
            "sunset": hm(self.sunset_h),
            "solar_noon": hm(self.noon_h),
            "noon_altitude_deg": round(self.noon_alt, 2),
            "seconds_per_local_hour": round(self.duration_s / (self.end_h - self.start_h), 2),
            "light": "sin(altitude) / sin(noon altitude), clipped to 0-1",
        }

    @classmethod
    def from_manifest(cls, manifest, day, duration_s, **kw):
        """Sun altitudes the scene's solar run recorded (physics/manifest.json), by local time."""
        tag = day.replace("-", "")
        for name, entry in manifest.get("arrays", {}).items():
            if name.startswith("solar/ghi_") and tag in name and entry.get("altitude_deg"):
                hours = np.array([int(t[:2]) + int(t[3:5]) / 60 for t in entry["time_local"]])
                alts = np.array(entry["altitude_deg"], dtype=float)
                if len(hours) < 3 or alts.max() < 1:
                    break

                def altitude(h, hours=hours, alts=alts):
                    if h < hours[0]:  # linear extrapolation below the horizon (twilight)
                        return alts[0] + (h - hours[0]) * (alts[1] - alts[0]) / (
                            hours[1] - hours[0]
                        )
                    if h > hours[-1]:
                        return alts[-1] + (h - hours[-1]) * (alts[-1] - alts[-2]) / (
                            hours[-1] - hours[-2]
                        )
                    return float(np.interp(h, hours, alts))

                return cls(altitude, duration_s, source=f"scene solar run {name}", **kw)
        return None

    @classmethod
    def from_location(cls, latitude, longitude, day, duration_s, utc_offset_h=0.0, **kw):
        """The framework's NOAA sun position (urban_flow.physics.solar.model) for a location."""
        sun_position = framework_sun_position()
        d = Date.fromisoformat(day)

        def altitude(h):
            return sun_position(latitude, longitude, d.year, d.month, d.day, h - utc_offset_h)[0]

        src = f"urban_flow.physics.solar.model.sun_position({latitude}, {longitude}, {day})"
        return cls(altitude, duration_s, source=src, **kw)
