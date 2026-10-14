"""Estimate a GLB scene's georeference from road meshes named after OSM ways.

Road meshes named ``Road_<osm way id>`` are triangle strips of left/right vertex
pairs; pair midpoints give the modelled centreline. Each centreline point is matched
to the closest point on the same OSM way and a similarity transform (scale, rotation,
translation) from local metres to a WGS84 tangent plane is fitted by trimmed ICP.

Read-only: writes nothing unless --out or --osm-cache is given. The result is a
candidate origin and north, not a surveyed georeference.
"""

import argparse
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

if __name__ == "__main__" and not __package__:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from urban_geometry.voxelization.glb_plan import read_glb_header

OVERPASS = "https://overpass-api.de/api/interpreter"
ROAD = re.compile(r"^Road_(\d+)$")
A, F = 6378137.0, 1 / 298.257223563  # WGS84
E2 = F * (2 - F)


def read_positions(doc, f, base, index):
    acc = doc["accessors"][index]
    if acc["componentType"] != 5126 or acc["type"] != "VEC3" or "sparse" in acc:
        raise ValueError("Road POSITION accessors must be dense float32 VEC3")
    bv = doc["bufferViews"][acc["bufferView"]]
    if bv.get("byteStride", 12) != 12:
        raise ValueError("Interleaved road vertex buffers are not supported")
    f.seek(base + bv.get("byteOffset", 0) + acc.get("byteOffset", 0))
    return np.frombuffer(f.read(12 * acc["count"]), np.float32).reshape(-1, 3).astype(np.float64)


def model_centrelines(path):
    """{way id: (N,2) local xy centreline} using the voxeliser's gltf (x,-z) convention."""
    doc, base = read_glb_header(path)
    out = {}
    with Path(path).open("rb") as f:
        for node in doc["nodes"]:
            m = ROAD.match(node.get("name", ""))
            if not m or "mesh" not in node:
                continue
            if any(k in node for k in ("matrix", "translation", "rotation", "scale", "children")):
                raise ValueError(f"{node['name']}: road nodes must have baked transforms")
            pts = []
            for prim in doc["meshes"][node["mesh"]]["primitives"]:
                if "KHR_draco_mesh_compression" in prim.get("extensions", {}):
                    raise ValueError(f"{node['name']}: Draco road meshes are not supported")
                v = read_positions(doc, f, base, prim["attributes"]["POSITION"])
                if len(v) % 2:
                    raise ValueError(f"{node['name']}: odd vertex count; not a left/right strip")
                pts.append((v[0::2] + v[1::2]) / 2)
            c = np.concatenate(pts)
            out[int(m.group(1))] = np.stack([c[:, 0], -c[:, 2]], axis=1)
    return out


def fetch_ways(ids):
    q = f"[out:json][timeout:90];way(id:{','.join(map(str, sorted(ids)))});out tags geom;"
    req = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={
            "User-Agent": "physics-grounded-4d-world-model/1.0 (georeference check)",
            "Accept": "application/json",
        },
    )
    doc = json.loads(urllib.request.urlopen(req, timeout=120).read())
    doc["query"] = q
    doc["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return doc


def ecef(lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    n = A / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    return np.stack(
        [n * np.cos(lat) * np.cos(lon), n * np.cos(lat) * np.sin(lon), n * (1 - E2) * np.sin(lat)],
        -1,
    )


def enu_basis(lat0, lon0):
    la, lo = math.radians(lat0), math.radians(lon0)
    east = np.array([-math.sin(lo), math.cos(lo), 0.0])
    north = np.array([-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)])
    return ecef(lat0, lon0), east, north


def to_enu(lat, lon, frame):
    o, e, n = frame
    d = ecef(np.asarray(lat), np.asarray(lon)) - o
    return np.stack([d @ e, d @ n], -1)


def to_latlon(xy, frame):
    """Inverse of to_enu for points on the tangent plane, projected back to the ellipsoid."""
    o, e, n = frame
    p = o + xy[:, :1] * e + xy[:, 1:] * n
    lon = np.arctan2(p[:, 1], p[:, 0])
    r = np.hypot(p[:, 0], p[:, 1])
    lat = np.arctan2(p[:, 2], r * (1 - E2))
    for _ in range(5):
        nn = A / np.sqrt(1 - E2 * np.sin(lat) ** 2)
        h = r / np.cos(lat) - nn
        lat = np.arctan2(p[:, 2], r * (1 - E2 * nn / (nn + h)))
    return np.degrees(lat), np.degrees(lon)


def closest_on_polyline(p, line):
    """Closest points on polyline (M,2) for points p (N,2)."""
    a, b = line[:-1], line[1:]
    ab = b - a
    t = np.einsum("nmk,mk->nm", p[:, None] - a[None], ab) / np.maximum((ab**2).sum(1), 1e-12)
    q = a[None] + np.clip(t, 0, 1)[..., None] * ab[None]
    d = ((q - p[:, None]) ** 2).sum(-1)
    return q[np.arange(len(p)), d.argmin(1)]


def umeyama(src, dst, with_scale=True):
    ms, md = src.mean(0), dst.mean(0)
    s, d = src - ms, dst - md
    u, sig, vt = np.linalg.svd(d.T @ s / len(src))
    sign = np.diag([1.0, np.sign(np.linalg.det(u @ vt))])
    r = u @ sign @ vt
    c = (sig * np.diag(sign)).sum() / (s**2).sum(1).mean() if with_scale else 1.0
    return c, r, md - c * r @ ms


def match(params, model, osm):
    c, r, t = params
    src, dst = [], []
    for wid, pts in model.items():
        p = pts @ (c * r).T + t
        src.append(pts)
        dst.append(closest_on_polyline(p, osm[wid]))
    return np.concatenate(src), np.concatenate(dst)


def icp(model, osm, init, iters=40, keep=0.9, with_scale=True):
    params = init
    for _ in range(iters):
        src, dst = match(params, model, osm)
        c, r, t = params
        res = np.linalg.norm(src @ (c * r).T + t - dst, axis=1)
        inl = res <= np.quantile(res, keep)
        new = umeyama(src[inl], dst[inl], with_scale)
        done = abs(new[0] - c) < 1e-7 and np.abs(new[2] - t).max() < 1e-4
        params = new
        if done:
            break
    src, dst = match(params, model, osm)
    c, r, t = params
    return params, np.linalg.norm(src @ (c * r).T + t - dst, axis=1)


def rot(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def stats(res):
    return {
        "points": len(res),
        "rms_m": float(np.sqrt((res**2).mean())),
        "median_m": float(np.median(res)),
        "p95_m": float(np.quantile(res, 0.95)),
        "max_m": float(res.max()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("glb", type=Path)
    ap.add_argument(
        "--osm-json", type=Path, help="reuse a saved Overpass response instead of fetching"
    )
    ap.add_argument("--osm-cache", type=Path, help="save the fetched Overpass response here")
    ap.add_argument("--out", type=Path, help="write the JSON report here")
    args = ap.parse_args()

    model = model_centrelines(args.glb)
    if not model:
        raise SystemExit("no Road_<osm way id> meshes found")
    raw = json.loads(args.osm_json.read_text()) if args.osm_json else fetch_ways(model)
    if args.osm_cache:
        args.osm_cache.write_text(json.dumps(raw))
    ways = {e["id"]: e for e in raw["elements"] if e.get("type") == "way" and e.get("geometry")}
    missing = sorted(set(model) - set(ways))
    model = {k: v for k, v in model.items() if k in ways}

    lat = np.concatenate([[g["lat"] for g in ways[k]["geometry"]] for k in model])
    lon = np.concatenate([[g["lon"] for g in ways[k]["geometry"]] for k in model])
    frame = enu_basis(float(lat.mean()), float(lon.mean()))
    osm = {
        k: to_enu(
            [g["lat"] for g in ways[k]["geometry"]], [g["lon"] for g in ways[k]["geometry"]], frame
        )
        for k in model
    }

    # Coarse rotation sweep from a centroid-aligned start; the same-way constraint makes this unambiguous.
    allm = np.concatenate(list(model.values()))
    allo = np.concatenate(list(osm.values()))
    best = None
    for deg in range(0, 360, 5):
        r = rot(deg)
        init = (1.0, r, allo.mean(0) - r @ allm.mean(0))
        params, res = icp(model, osm, init, iters=8, with_scale=False)
        if best is None or np.median(res) < best[2]:
            best = (deg, params, float(np.median(res)))
    rigid, rigid_res = icp(model, osm, best[1], with_scale=False)
    sim, sim_res = icp(model, osm, rigid)

    # Split-half check: fit on alternate ways, measure on the ways left out.
    ids = sorted(model)
    halves = [{k: model[k] for k in ids[i::2]} for i in (0, 1)]
    cross = []
    for fit, held in (halves, halves[::-1]):
        params, _ = icp(fit, osm, sim)
        src, dst = match(params, held, osm)
        hc, hr, ht = params
        cross.append(stats(np.linalg.norm(src @ (hc * hr).T + ht - dst, axis=1)))

    c, r, t = sim
    heading = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    corners = np.array(
        [
            [0, 0],
            *[
                [x, y]
                for x in (allm[:, 0].min(), allm[:, 0].max())
                for y in (allm[:, 1].min(), allm[:, 1].max())
            ],
        ]
    )
    clat, clon = to_latlon(corners @ (c * r).T + t, frame)
    per_way = []
    for wid, pts in model.items():
        src, dst = match(sim, {wid: pts}, osm)
        res = np.linalg.norm(src @ (c * r).T + t - dst, axis=1)
        per_way.append(
            {
                "way": wid,
                "name": ways[wid].get("tags", {}).get("name"),
                "points": len(res),
                "median_m": float(np.median(res)),
                "max_m": float(res.max()),
            }
        )
    per_way.sort(key=lambda w: -w["median_m"])

    report = {
        "source": str(args.glb),
        "method": "Road_<way> strip midpoints -> closest point on same OSM way; trimmed (90%) similarity ICP on a WGS84 tangent plane",
        "model_axes": "local x = gltf x, local y = -gltf z (voxeliser convention)",
        "osm": {
            "timestamp_osm_base": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "fetched_at": raw.get("fetched_at"),
            "ways_used": len(model),
            "ways_missing": missing,
        },
        "rigid": {"residual": stats(rigid_res)},
        "similarity": {
            "scale": float(c),
            "rotation_deg_ccw_local_to_enu": heading,
            "local_y_bearing_deg": (-heading) % 360,
            "translation_enu_m": t.tolist(),
            "residual": stats(sim_res),
            "held_out_half_residual": cross,
        },
        "tangent_plane_origin_latlon": [float(lat.mean()), float(lon.mean())],
        "local_origin_latlon": [float(clat[0]), float(clon[0])],
        "road_extent_corners_latlon": [[float(a), float(b)] for a, b in zip(clat[1:], clon[1:])],
        "worst_ways": per_way[:10],
    }
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
