"""Scene terrain: compact encoding of a DEM grid and per-feature ground levels.

The prepared scene carries ``scene["terrain"]`` when a DEM is configured::

    {"x0", "y0", "dx", "nx", "ny", "base_m", "scale_m", "encoding": "int16le-base64",
     "z": "<base64>", ...provenance}

Height at node (i, j) (x = x0 + i*dx, y = y0 + j*dx, row-major from the south-west)
is ``base_m + scale_m * int16[j * nx + i]``; ``three/terrain.mjs`` samples it
bilinearly. Everything else in the scene stays relative to the ground: buildings
get ``ground_z`` / ``ground_max`` (lowest / highest terrain over the footprint;
long footprints on even slopes also ``ground_plane`` = [z at the centroid, dz/dx,
dz/dy], a plane nowhere above the terrain that the building is sheared onto),
water bodies a flat ``level`` and vessels the level of the water they float on.
"""

from __future__ import annotations

import base64
import math

import numpy as np

ENCODING = "int16le-base64"
SCALE_M = 0.01  # centimetres: +-327 m around base_m
WATER_PERCENTILE = 10
# Long footprints on an even slope (terraces) follow it instead of standing level
# at their lowest point: ground spread, plane-fit residual and gradient limits.
SLOPED_SPAN_M = 2.0
SLOPED_RMS_M = 0.75
SLOPED_MAX_GRADE = 0.25


def scene_grid(dem: np.ndarray, index: dict, dx: float, half: float):
    """Resample a DEM (index.json grid) to nodes x0 + i*dx covering [-half, half].

    A [1, 2, 1] / 4 filter per axis precedes decimation when dx is an integer
    multiple of the DEM spacing; otherwise the DEM is sampled bilinearly.
    """
    n = round(2 * half / dx) + 1
    xs = -half + dx * np.arange(n)
    src = dem.astype(np.float64)
    step = dx / index["dx"]
    if abs(step - round(step)) < 1e-9 and round(step) > 1:
        pad = np.pad(src, 1, mode="edge")
        src = (pad[:-2, 1:-1] + 2 * pad[1:-1, 1:-1] + pad[2:, 1:-1]) / 4
        pad = np.pad(src, 1, mode="edge")
        src = (pad[1:-1, :-2] + 2 * pad[1:-1, 1:-1] + pad[1:-1, 2:]) / 4
    grid = {"x0": index["x0"], "y0": index["y0"], "dx": index["dx"]}
    xx, yy = np.meshgrid(xs, xs)
    return xs[0], xs[0], dx, bilinear(src, grid, xx, yy).astype(np.float32)


def bilinear(values: np.ndarray, grid: dict, x, y):
    """Bilinear samples of a node grid (clamped to its extent)."""
    ny, nx = values.shape
    fx = np.clip((np.asarray(x, dtype=np.float64) - grid["x0"]) / grid["dx"], 0, nx - 1)
    fy = np.clip((np.asarray(y, dtype=np.float64) - grid["y0"]) / grid["dx"], 0, ny - 1)
    i = np.minimum(np.floor(fx).astype(int), nx - 2)
    j = np.minimum(np.floor(fy).astype(int), ny - 2)
    u, v = fx - i, fy - j
    return (
        values[j, i] * (1 - u) * (1 - v)
        + values[j, i + 1] * u * (1 - v)
        + values[j + 1, i] * (1 - u) * v
        + values[j + 1, i + 1] * u * v
    )


def encode(values: np.ndarray, x0: float, y0: float, dx: float) -> dict:
    """Compact JSON form: int16 centimetres above base_m, little-endian, base64."""
    base = math.floor(float(values.min()) * 10) / 10 - 0.1
    q = np.round((values.astype(np.float64) - base) / SCALE_M)
    if q.max() > np.iinfo(np.int16).max:
        raise ValueError(f"terrain range {values.min()}..{values.max()} m exceeds int16 cm")
    ny, nx = values.shape
    return {
        "x0": float(x0),
        "y0": float(y0),
        "dx": float(dx),
        "nx": int(nx),
        "ny": int(ny),
        "base_m": round(base, 2),
        "scale_m": SCALE_M,
        "encoding": ENCODING,
        "z": base64.b64encode(q.astype("<i2").tobytes()).decode("ascii"),
    }


def decode(terrain: dict) -> np.ndarray:
    """[ny, nx] float64 metres from scene["terrain"]."""
    if terrain.get("encoding", ENCODING) != ENCODING:
        raise ValueError(f"unknown terrain encoding {terrain.get('encoding')}")
    raw = np.frombuffer(base64.b64decode(terrain["z"]), dtype="<i2")
    return terrain["base_m"] + terrain["scale_m"] * raw.astype(np.float64).reshape(
        terrain["ny"], terrain["nx"]
    )


class Sampler:
    """Bilinear terrain heights from a scene terrain record (same rule as terrain.mjs)."""

    def __init__(self, terrain: dict):
        self.grid = terrain
        self.values = decode(terrain)

    def __call__(self, x, y):
        return bilinear(self.values, self.grid, x, y)

    def nodes_in(self, ring):
        """Grid node coordinates strictly inside a ring (even-odd scanline)."""
        g, xs, ys = self.grid, [], []
        ys_ring = [p[1] for p in ring]
        j0 = math.ceil((min(ys_ring) - g["y0"]) / g["dx"])
        j1 = math.floor((max(ys_ring) - g["y0"]) / g["dx"])
        for j in range(max(j0, 0), min(j1, g["ny"] - 1) + 1):
            y = g["y0"] + j * g["dx"]
            cuts = []
            for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
                if (ay > y) != (by > y):
                    cuts.append(ax + (y - ay) * (bx - ax) / (by - ay))
            cuts.sort()
            for a, b in zip(cuts[::2], cuts[1::2], strict=False):
                i0 = math.ceil((a - g["x0"]) / g["dx"])
                i1 = math.floor((b - g["x0"]) / g["dx"])
                for i in range(max(i0, 0), min(i1, g["nx"] - 1) + 1):
                    xs.append(g["x0"] + i * g["dx"])
                    ys.append(y)
        return xs, ys

    def polygon_samples(self, poly, step=None, points=False):
        """Heights at the densified boundary of a polygon and at grid nodes inside it
        (with ``points``: also their x and y arrays)."""
        step = step or self.grid["dx"] / 2
        px, py = [], []
        for ring in poly:
            for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
                n = max(1, math.ceil(math.hypot(bx - ax, by - ay) / step))
                for k in range(n):
                    px.append(ax + (bx - ax) * k / n)
                    py.append(ay + (by - ay) * k / n)
        nx_, ny_ = self.nodes_in(poly[0])
        holes = poly[1:]
        if holes:
            keep = [
                k
                for k in range(len(nx_))
                if not any(point_in_ring(h, nx_[k], ny_[k]) for h in holes)
            ]
            nx_, ny_ = [nx_[k] for k in keep], [ny_[k] for k in keep]
        xs, ys = np.array(px + nx_), np.array(py + ny_)
        if points:
            return self(xs, ys), len(nx_), xs, ys
        return self(xs, ys), len(nx_)


def point_in_ring(ring, x, y) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def connected_water(bodies):
    """Groups (index lists) of water polygons that share a boundary vertex.

    Mapped rivers are split into several polygons; one flat level per connected
    group avoids steps in the water surface at the seams.
    """
    parent = list(range(len(bodies)))

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    seen = {}
    for k, w in enumerate(bodies):
        for ring in w["poly"]:
            for x, y in ring:
                key = (round(x * 10), round(y * 10))
                if key in seen:
                    parent[find(k)] = find(seen[key])
                else:
                    seen[key] = k
    groups = {}
    for k in range(len(bodies)):
        groups.setdefault(find(k), []).append(k)
    return list(groups.values())


def ground_plane(c, x, y, h):
    """[z at the centroid, dz/dx, dz/dy] of a plane under a footprint, or None.

    Least-squares plane through the terrain samples, lowered so that it is nowhere
    above them; None unless the terrain is close to planar and not too steep.
    """
    cx, cy = c
    a = np.column_stack([np.ones_like(x), x - cx, y - cy])
    coef, *_ = np.linalg.lstsq(a, h, rcond=None)
    resid = h - a @ coef
    if math.sqrt(float(np.mean(resid**2))) > SLOPED_RMS_M:
        return None
    if math.hypot(coef[1], coef[2]) > SLOPED_MAX_GRADE:
        return None
    return [
        round(float(coef[0] + resid.min()), 2),
        round(float(coef[1]), 5),
        round(float(coef[2]), 5),
    ]


def apply_terrain(scene: dict, terrain: dict) -> dict:
    """Store the terrain in the scene and set ground levels in place; return counts."""
    sample = Sampler(terrain)
    scene["terrain"] = terrain
    bodies = [w for w in scene["water"] if w.get("poly")]
    samples = []
    for w in bodies:
        h, inner = sample.polygon_samples(w["poly"])
        # Interior nodes describe the surface; tiny ponds fall back to their outline.
        samples.append(h[-inner:] if inner >= 4 else h)
    levels = []
    for group in connected_water(bodies):
        level = round(
            float(np.percentile(np.concatenate([samples[k] for k in group]), WATER_PERCENTILE)), 2
        )
        for k in group:
            bodies[k]["level"] = level
            levels.append((bodies[k]["poly"], level))
    span, sloped = [], 0
    for b in scene["buildings"]:
        parts = [sample.polygon_samples(p, points=True) for p in b["polys"]]
        h = np.concatenate([q[0] for q in parts])
        b["ground_z"] = round(float(h.min()), 2)
        b["ground_max"] = round(float(h.max()), 2)
        if not b.get("vessel") and b["ground_max"] - b["ground_z"] > SLOPED_SPAN_M:
            plane = ground_plane(
                b["c"],
                np.concatenate([q[2] for q in parts]),
                np.concatenate([q[3] for q in parts]),
                h,
            )
            if plane:
                b["ground_plane"] = plane
                sloped += 1
        if b.get("vessel"):
            cx, cy = b["c"]
            for poly, level in levels:
                if point_in_ring(poly[0], cx, cy) and not any(
                    point_in_ring(r, cx, cy) for r in poly[1:]
                ):
                    b["ground_z"] = b["ground_max"] = level
                    break
        span.append(b["ground_max"] - b["ground_z"])
    values = sample.values
    return {
        "grid": [terrain["nx"], terrain["ny"]],
        "dx_m": terrain["dx"],
        "min_m": round(float(values.min()), 2),
        "max_m": round(float(values.max()), 2),
        "water_levels": len(levels),
        "sloped_buildings": sloped,
        "building_slope_p95_m": round(float(np.percentile(span, 95)), 2) if span else 0.0,
    }


def scene_terrain(dem: np.ndarray, index: dict, dx: float, half: float) -> dict:
    """Encoded scene terrain record with provenance from a DEM index."""
    x0, y0, dx, values = scene_grid(dem, index, dx, half)
    rec = encode(values, x0, y0, dx)
    src = index["source"]
    rec["source"] = {
        "dem_sha256": index["sha256"],
        "dem_dx_m": index["dx"],
        "name": src["name"],
        "zoom": src["zoom"],
        "imagery_sources": src["imagery_sources"],
        "attribution": src["attribution"],
        "license": src["license"],
    }
    rec["vertical_datum"] = index["vertical_datum"]
    return rec
