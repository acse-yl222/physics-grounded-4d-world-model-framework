"""Download terrain tiles for a scene and resample them to a scene ENU DEM grid.

Source: AWS Terrain Tiles (Tilezen/Mapzen Joerd), Terrarium PNG in Web Mercator,
``height = R * 256 + G + B / 256 - 32768`` metres. Tiles are cached under
``cache/<scene>/terrain/<zoom>/``; the DEM is written as ``dem.npy`` (float32
metres, rows = y from south to north, columns = x from west to east, sample
centres at ``x0 + i * dx``, ``y0 + j * dx``) with ``index.json`` describing the
grid, projection, vertical reference, attribution and per-tile SHA-256.

  PYTHONPATH=src python3 -m urban_geometry.image_to_threejs.fetch_terrain \\
      project/imperial_corridor/configs/image_to_threejs.json \\
      cache/imperial_corridor/terrain project/imperial_corridor/input/terrain
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

try:  # imported as part of the package (tests) or run as a script (build_run)
    from .fetch_overture import Enu
except ImportError:
    from fetch_overture import Enu

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
DOCS = "https://github.com/tilezen/joerd/tree/master/docs"
ATTRIBUTION_DOC = "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"
# Required attribution for the sources used in Great Britain (docs/attribution.md).
ATTRIBUTION = {
    "uk_lidar": "United Kingdom terrain data © Environment Agency copyright and/or "
    "database right 2015. All rights reserved.",
    "eudem": "Europe terrain data produced using Copernicus data and information funded "
    "by the European Union - EU-DEM layers.",
    "srtm": "SRTM data courtesy of the U.S. Geological Survey.",
    "gmted": "GMTED2010 data courtesy of the U.S. Geological Survey.",
    "etopo1": "Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric Administration.",
}
LICENCE = {
    "uk_lidar": "data.gov.uk LIDAR Composite Digital Terrain Model, Open Government "
    "Licence v3 (http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)",
}
TILE = 256


def decode_terrarium(rgb: np.ndarray) -> np.ndarray:
    """Terrarium RGB (uint8, [..., 3]) -> float32 metres."""
    rgb = rgb.astype(np.float64)
    return (rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768).astype(np.float32)


def mercator_px(lon, lat, z):
    """Global Web Mercator pixel coordinates (pixel edges at integers) at zoom z."""
    n = TILE * 2**z
    lat = np.radians(lat)
    px = (np.asarray(lon) + 180.0) / 360.0 * n
    py = (1.0 - np.log(np.tan(lat) + 1.0 / np.cos(lat)) / math.pi) / 2.0 * n
    return px, py


def tile_range(enu: Enu, half: float, z: int):
    """Inclusive tile x/y ranges covering the square ENU domain of half-size ``half``."""
    lon0, lat0, lon1, lat1 = enu.inverse_bbox(half)
    px0, py1 = mercator_px(lon0, lat0, z)
    px1, py0 = mercator_px(lon1, lat1, z)
    return (
        range(int(px0 // TILE), int(px1 // TILE) + 1),
        range(int(py0 // TILE), int(py1 // TILE) + 1),
    )


def grid_axis(half: float, dx: float) -> np.ndarray:
    n = round(2 * half / dx) + 1
    return -half + dx * np.arange(n)


def resample(mosaic: np.ndarray, tx0: int, ty0: int, enu: Enu, xs, ys, z: int) -> np.ndarray:
    """Bilinear samples of a tile mosaic (top-left tile tx0, ty0) at ENU grid points.

    Returns [len(ys), len(xs)] with row j at ys[j] (south to north).
    """
    xx, yy = np.meshgrid(xs, ys)
    lon = enu.lon0 + xx / enu.kx
    lat = enu.lat0 + yy / enu.ky
    px, py = mercator_px(lon, lat, z)
    # Pixel centres sit at half-integers.
    fx = px - tx0 * TILE - 0.5
    fy = py - ty0 * TILE - 0.5
    h, w = mosaic.shape
    i0 = np.clip(np.floor(fx).astype(int), 0, w - 2)
    j0 = np.clip(np.floor(fy).astype(int), 0, h - 2)
    u = np.clip(fx - i0, 0, 1)
    v = np.clip(fy - j0, 0, 1)
    m = mosaic.astype(np.float64)
    out = (
        m[j0, i0] * (1 - u) * (1 - v)
        + m[j0, i0 + 1] * u * (1 - v)
        + m[j0 + 1, i0] * (1 - u) * v
        + m[j0 + 1, i0 + 1] * u * v
    )
    return out.astype(np.float32)


def fetch_tile(url: str, path: Path, retries=4):
    """Download a tile (if not cached); return (bytes, imagery sources or None)."""
    meta = path.with_suffix(".json")
    if path.exists() and meta.exists():
        return path.read_bytes(), json.loads(meta.read_text())
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as res:
                data = res.read()
                info = {
                    "url": url,
                    "retrieved": datetime.now(UTC).isoformat(timespec="seconds"),
                    "last_modified": res.headers.get("Last-Modified"),
                    "etag": (res.headers.get("ETag") or "").strip('"'),
                    "imagery_sources": [
                        s.strip()
                        for s in (res.headers.get("x-amz-meta-x-imagery-sources") or "").split(",")
                        if s.strip()
                    ],
                }
            break
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    meta.write_text(json.dumps(info, indent=1) + "\n")
    return data, info


def build_dem(config: dict, cache: Path, out: Path, zoom=15, half=4100.0, dx=5.0):
    from PIL import Image

    origin = config["origin"]
    enu = Enu(origin["longitude"], origin["latitude"])
    xr, yr = tile_range(enu, half + 2 * dx, zoom)
    mosaic = np.zeros((len(yr) * TILE, len(xr) * TILE), np.float32)
    tiles, sources = [], set()
    for b, ty in enumerate(yr):
        for a, tx in enumerate(xr):
            url = TILE_URL.format(z=zoom, x=tx, y=ty)
            data, info = fetch_tile(url, cache / str(zoom) / str(tx) / f"{ty}.png")
            rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
            mosaic[b * TILE : (b + 1) * TILE, a * TILE : (a + 1) * TILE] = decode_terrarium(rgb)
            tiles.append(
                {
                    "z": zoom,
                    "x": tx,
                    "y": ty,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "retrieved": info["retrieved"],
                    "last_modified": info.get("last_modified"),
                    "imagery_sources": info.get("imagery_sources", []),
                }
            )
            sources.update(s.split("/")[0] for s in info.get("imagery_sources", []))
    xs = grid_axis(half, dx)
    dem = resample(mosaic, xr[0], yr[0], enu, xs, xs, zoom)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "dem.npy", dem)
    res_m = 2 * math.pi * 6378137 * math.cos(math.radians(origin["latitude"])) / (TILE * 2**zoom)
    index = {
        "schema": "scene-dem-v1",
        "scene_id": config["scene_id"],
        "file": "dem.npy",
        "dtype": "<f4",
        "shape": list(dem.shape),
        "layout": "row j = y0 + j*dx (south to north), column i = x0 + i*dx (west to east)",
        "x0": float(xs[0]),
        "y0": float(xs[0]),
        "dx": dx,
        "units": "m",
        "projection": {
            "frame": "ENU",
            "method": "equirectangular tangent plane (fetch_overture.Enu): "
            "x = (lon - lon0) * R * cos(lat0) * pi/180, y = (lat - lat0) * R * pi/180, "
            "R = 6378137 m",
            "origin": origin,
        },
        "vertical_datum": "Heights as delivered by Terrarium tiles (metres, no datum "
        "conversion documented by Tilezen). The UK source is the Environment Agency "
        "LIDAR Composite DTM, published in metres above Ordnance Datum Newlyn (ODN).",
        "surface": "bare-earth DTM (source: uk_lidar LIDAR-DTM-2M composite)",
        "resampling": "bilinear in Web Mercator pixel space at the ENU grid nodes",
        "source": {
            "name": "AWS Terrain Tiles (Tilezen Joerd) terrarium",
            "url_template": TILE_URL,
            "documentation": DOCS,
            "zoom": zoom,
            "nominal_pixel_m": round(res_m, 2),
            "imagery_sources": sorted(sources),
            "license": ATTRIBUTION_DOC,
            "attribution": [ATTRIBUTION[s] for s in sorted(sources) if s in ATTRIBUTION],
            "licences": {s: LICENCE[s] for s in sorted(sources) if s in LICENCE},
            "tiles": tiles,
        },
        "sha256": hashlib.sha256((out / "dem.npy").read_bytes()).hexdigest(),
        "stats": {
            "min": round(float(dem.min()), 2),
            "max": round(float(dem.max()), 2),
            "mean": round(float(dem.mean()), 2),
        },
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return dem, index


def load_dem(index_path: Path):
    """(dem float32 [ny, nx], index dict) from a DEM index.json."""
    index = json.loads(index_path.read_text())
    dem = np.load(index_path.parent / index["file"])
    if list(dem.shape) != index["shape"]:
        raise ValueError(f"{index_path}: shape {dem.shape} != {index['shape']}")
    return dem, index


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("config", type=Path)
    p.add_argument("cache", type=Path, help="tile cache directory (cache/<scene>/terrain)")
    p.add_argument("out", type=Path, help="DEM directory (project/<scene>/input/terrain)")
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    t = config.get("terrain", {})
    dem, index = build_dem(
        config,
        args.cache,
        args.out,
        zoom=t.get("zoom", 15),
        half=t.get("half_m", config["domain_m"] / 2 + 100),
        dx=t.get("dem_m", 5.0),
    )
    print(
        f"dem {dem.shape} dx={index['dx']} m, {len(index['source']['tiles'])} tiles "
        f"z{index['source']['zoom']}, sources={index['source']['imagery_sources']} "
        f"range {index['stats']['min']}..{index['stats']['max']} m -> {args.out}"
    )


if __name__ == "__main__":
    main()
