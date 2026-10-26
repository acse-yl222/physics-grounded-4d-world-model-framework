"""Fill a georeferenced GLB scene's empty surroundings with OSM building footprints.

Footprints are mapped into the model frame with a georef_roads.py report, extruded
to tagged or estimated heights (LOD1, flat roofs) and written as a separate,
classified GLB. A flat ground extension covers the rest of the area. The context is
kept inside the area whose SCALED grid plan equals the base scene's, so merging it
does not enlarge the simulation domain.

Dropped: buildings already in the detailed model (``<prefix><osm id>`` nodes), inside
the detailed zone, overlapping detailed buildings or modelled roads, or crossing the
context extent. Every kept building records its OSM id and height source.
"""

import argparse
import hashlib
import json
import math
import re
import struct
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

if __name__ == "__main__" and not __package__:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from urban_geometry.voxelization.georef_roads import (
    enu_basis,
    latlon_to_local,
    read_positions,
    to_latlon,
)
from urban_geometry.voxelization.glb_plan import PAD_M, local_bounds, plan_grid, read_glb_header

OVERPASS = "https://overpass-api.de/api/interpreter"
LEVEL_M = 3.2
MIN_HEIGHT_M = 3.0
BUILDING_MATERIAL = "context building; OSM footprint, estimated height"
GROUND_MATERIAL = "context ground; assumed flat"
ROAD = re.compile(r"^(Road|PaveL|PaveR)_")


# ---------------------------------------------------------------- base scene


def read_indices(doc, f, base, index):
    acc = doc["accessors"][index]
    dtype = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}[acc["componentType"]]
    bv = doc["bufferViews"][acc["bufferView"]]
    f.seek(base + bv.get("byteOffset", 0) + acc.get("byteOffset", 0))
    return np.frombuffer(f.read(np.dtype(dtype).itemsize * acc["count"]), dtype).astype(np.int64)


def base_scene(path, model_prefix):
    """Detailed OSM ids, road triangles (local xy) and ground boxes (local) of a baked GLB."""
    doc, base = read_glb_header(path)
    ids, roads, ground = set(), [], []
    pattern = re.compile(rf"^{re.escape(model_prefix)}(\d+)")
    with Path(path).open("rb") as f:
        for node in doc["nodes"]:
            name = node.get("name", "")
            if m := pattern.match(name):
                ids.add(int(m.group(1)))
            if "mesh" not in node:
                continue
            is_ground = node.get("extras", {}).get("physics_class") == "ground" or name == "Ground"
            if not (ROAD.match(name) or is_ground):
                continue
            if any(k in node for k in ("matrix", "translation", "rotation", "scale", "children")):
                raise ValueError(f"{name}: base scene must have baked transforms")
            for prim in doc["meshes"][node["mesh"]]["primitives"]:
                v = read_positions(doc, f, base, prim["attributes"]["POSITION"])
                local = np.stack([v[:, 0], -v[:, 2], v[:, 1]], 1)
                if is_ground:
                    ground.append([local.min(0), local.max(0)])
                elif "indices" in prim:
                    tri = read_indices(doc, f, base, prim["indices"]).reshape(-1, 3)
                    roads.append(local[tri][:, :, :2])
    return doc, ids, (np.concatenate(roads) if roads else np.zeros((0, 3, 2))), ground


def context_extent(doc, cell):
    """Largest box whose grid plan equals the base scene's plan (PAD_M/2 inside each edge)."""
    plan = plan_grid(local_bounds(doc), cell)
    lo = plan["origin_xy"] + PAD_M / 2
    return plan, np.array([lo, lo + plan["size_xy_m"] - PAD_M])


# ---------------------------------------------------------------- OSM footprints


def fetch_buildings(bbox, url):
    s, w, n, e = bbox
    q = (
        f"[out:json][timeout:120];(way[building]({s},{w},{n},{e});"
        f"relation[building]({s},{w},{n},{e}););out tags geom;"
    )
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={
            "User-Agent": "physics-grounded-4d-world-model/1.0 (context buildings)",
            "Accept": "application/json",
        },
    )
    doc = json.loads(urllib.request.urlopen(req, timeout=180).read())
    doc["query"] = q
    doc["endpoint"] = url
    doc["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return doc


def join_rings(segments):
    """Join open member ways into closed rings; returns rings as lists of (lat, lon)."""
    rings, open_ = [], [list(s) for s in segments if len(s) > 1]
    while open_:
        ring = open_.pop()
        while ring[0] != ring[-1]:
            for i, seg in enumerate(open_):
                if seg[0] == ring[-1]:
                    ring += seg[1:]
                elif seg[-1] == ring[-1]:
                    ring += seg[::-1][1:]
                else:
                    continue
                open_.pop(i)
                break
            else:
                break
        if ring[0] == ring[-1] and len(ring) >= 4:
            rings.append(ring)
    return rings


def footprints(raw):
    """(osm key, tags, outer ring [(lat, lon)], had_holes) for each building element."""
    for e in raw["elements"]:
        tags = e.get("tags", {})
        if e["type"] == "way" and e.get("geometry"):
            ring = [(g["lat"], g["lon"]) for g in e["geometry"]]
            if ring[0] == ring[-1] and len(ring) >= 4:
                yield f"way/{e['id']}", e["id"], tags, ring, False
        elif e["type"] == "relation":
            members = e.get("members", [])
            outer = [
                [(g["lat"], g["lon"]) for g in m["geometry"]]
                for m in members
                if m.get("role") == "outer" and m.get("geometry")
            ]
            holes = any(m.get("role") == "inner" for m in members)
            for k, ring in enumerate(join_rings(outer)):
                yield f"relation/{e['id']}#{k}", None, tags, ring, holes


def height(tags, default):
    if h := re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*m?\s*$", tags.get("height", "")):
        return max(float(h.group(1)), MIN_HEIGHT_M), "osm height"
    if lv := re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*$", tags.get("building:levels", "")):
        return max(float(lv.group(1)) * LEVEL_M, MIN_HEIGHT_M), f"osm levels x {LEVEL_M} m"
    return default, "estimated: median of the detailed model's buildings"


# ---------------------------------------------------------------- geometry


def clean_ring(xy):
    """Open, counter-clockwise ring without repeated or collinear points; None if degenerate.

    Accepts open or closed input; closing duplicates of the first point are removed.
    """
    pts = []
    for p in np.asarray(xy, float):
        if not pts or np.hypot(*(p - pts[-1])) > 0.05:
            pts.append(p)
    while len(pts) > 1 and np.hypot(*(pts[-1] - pts[0])) <= 0.05:
        pts.pop()
    keep = []
    for i, p in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % len(pts)]
        if abs((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) > 1e-6:
            keep.append(p)
    if len(keep) < 3:
        return None
    ring = np.array(keep)
    area = 0.5 * np.sum(ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1])
    if abs(area) < 1.0:
        return None
    return ring if area > 0 else ring[::-1]


def ear_clip(ring):
    """Triangulate a simple CCW polygon; raises ValueError for self-intersecting rings."""
    idx = list(range(len(ring)))
    tris = []
    guard = 0
    while len(idx) > 3:
        guard += 1
        if guard > 10 * len(ring) ** 2:
            raise ValueError("ear clipping did not converge")
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = ring[i0], ring[i1], ring[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            others = ring[[j for j in idx if j not in (i0, i1, i2)]]
            if len(others) and inside_triangle(others, a, b, c).any():
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            raise ValueError("no ear found (self-intersecting footprint)")
    tris.append(tuple(idx))
    return np.array(tris)


def side(p, u, v):
    """Signed area of (u, v, p); positive when p is left of u -> v. Broadcasts over rows."""
    return (v[..., 0] - u[..., 0]) * (p[..., 1] - u[..., 1]) - (v[..., 1] - u[..., 1]) * (
        p[..., 0] - u[..., 0]
    )


def inside_triangle(p, a, b, c):
    return (side(p, a, b) >= 0) & (side(p, b, c) >= 0) & (side(p, c, a) >= 0)


def extrude(ring, z0, z1):
    """Flat-shaded prism: (positions, normals, indices) in glTF axes (x, z, -y)."""
    n = len(ring)
    roof = np.c_[ring, np.full(n, z1)]
    pos, nor, ind = [roof], [np.tile([0.0, 0.0, 1.0], (n, 1))], [ear_clip(ring)]
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        d = b - a
        out = np.array([d[1], -d[0], 0.0]) / np.hypot(*d)
        base = sum(len(p) for p in pos)
        pos.append(np.array([[*a, z0], [*b, z0], [*b, z1], [*a, z1]]))
        nor.append(np.tile(out, (4, 1)))
        ind.append(base + np.array([[0, 1, 2], [0, 2, 3]]))
    p, q = np.concatenate(pos), np.concatenate(nor)
    to_gltf = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float).T
    return p @ to_gltf, q @ to_gltf, np.concatenate(ind)


def rasterise_polygon(ring, origin, cell, shape):
    """Boolean mask of cell centres inside a polygon (even-odd rule)."""
    lo = np.floor((ring.min(0) - origin) / cell).astype(int)
    hi = np.ceil((ring.max(0) - origin) / cell).astype(int)
    lo, hi = np.maximum(lo, 0), np.minimum(hi, [shape[1], shape[0]])
    if np.any(hi <= lo):
        return None, None
    xs = origin[0] + (np.arange(lo[0], hi[0]) + 0.5) * cell
    ys = origin[1] + (np.arange(lo[1], hi[1]) + 0.5) * cell
    gx, gy = np.meshgrid(xs, ys)
    inside = np.zeros(gx.shape, bool)
    a, b = ring, np.roll(ring, -1, 0)
    for (x0, y0), (x1, y1) in zip(a, b):
        cross = (y0 > gy) != (y1 > gy)
        xint = x0 + (gy - y0) * (x1 - x0) / np.where(y1 == y0, 1e-12, y1 - y0)
        inside ^= cross & (gx < xint)
    return (slice(lo[1], hi[1]), slice(lo[0], hi[0])), inside


def rasterise_triangles(tris, origin, cell, shape, chunk=20000):
    mask = np.zeros(shape, bool)
    for s in range(0, len(tris), chunk):
        t = tris[s : s + chunk]
        lo = np.clip(np.floor((t.min(1) - origin) / cell).astype(int), 0, [shape[1], shape[0]])
        hi = np.clip(np.ceil((t.max(1) - origin) / cell).astype(int), 0, [shape[1], shape[0]])
        w, h = hi[:, 0] - lo[:, 0], hi[:, 1] - lo[:, 1]
        n = np.maximum(w, 0) * np.maximum(h, 0)
        k = np.repeat(np.arange(len(t)), n)
        off = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
        ix = lo[k, 0] + off % np.maximum(w[k], 1)
        iy = lo[k, 1] + off // np.maximum(w[k], 1)
        p = origin + (np.stack([ix, iy], 1) + 0.5) * cell
        a, b, c = t[k, 0], t[k, 1], t[k, 2]
        s1, s2, s3 = side(p, a, b), side(p, b, c), side(p, c, a)
        hit = ((s1 >= 0) & (s2 >= 0) & (s3 >= 0)) | ((s1 <= 0) & (s2 <= 0) & (s3 <= 0))
        mask[iy[hit], ix[hit]] = True
    return mask


def convex_hull(points):
    pts = sorted(map(tuple, points))
    if len(pts) < 3:
        return np.array(pts)

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and (
                (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])
                <= 0
            ):
                out.pop()
            out.append(p)
        return out[:-1]

    return np.array(half(pts) + half(pts[::-1]))


def in_convex(p, hull):
    a, b = hull, np.roll(hull, -1, 0)
    return bool(
        np.all((b[:, 0] - a[:, 0]) * (p[1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (p[0] - a[:, 0]) >= 0)
    )


# ---------------------------------------------------------------- glTF output


class GlbWriter:
    def __init__(self):
        self.doc = {
            "asset": {"version": "2.0", "generator": "p4d OSM context buildings"},
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "materials": [],
            "accessors": [],
            "bufferViews": [],
            "buffers": [],
        }
        self.bin = bytearray()
        self.materials = {}

    def material(self, name, rgb):
        if name not in self.materials:
            self.materials[name] = len(self.doc["materials"])
            self.doc["materials"].append(
                {
                    "name": name,
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [*rgb, 1.0],
                        "metallicFactor": 0.0,
                        "roughnessFactor": 0.9,
                    },
                }
            )
        return self.materials[name]

    def accessor(self, array, component, kind, target, bounds=False):
        data = np.ascontiguousarray(array).tobytes()
        self.bin += b"\0" * (-len(self.bin) % 4)
        self.doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data), "target": target}
        )
        self.bin += data
        acc = {
            "bufferView": len(self.doc["bufferViews"]) - 1,
            "componentType": component,
            "count": len(array),
            "type": kind,
        }
        if bounds:
            acc["min"], acc["max"] = array.min(0).tolist(), array.max(0).tolist()
        self.doc["accessors"].append(acc)
        return len(self.doc["accessors"]) - 1

    def add(self, name, positions, normals, indices, material, extras):
        prim = {
            "attributes": {
                "POSITION": self.accessor(positions.astype(np.float32), 5126, "VEC3", 34962, True),
                "NORMAL": self.accessor(normals.astype(np.float32), 5126, "VEC3", 34962),
            },
            "indices": self.accessor(indices.astype(np.uint32).reshape(-1), 5125, "SCALAR", 34963),
            "material": material,
        }
        self.doc["meshes"].append({"name": name, "primitives": [prim]})
        self.doc["nodes"].append(
            {"name": name, "mesh": len(self.doc["meshes"]) - 1, "extras": extras}
        )
        self.doc["scenes"][0]["nodes"].append(len(self.doc["nodes"]) - 1)

    def write(self, path):
        self.doc["buffers"] = [{"byteLength": len(self.bin)}]
        write_glb(path, self.doc, bytes(self.bin))


def write_glb(path, doc, blob):
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    blob += b"\0" * (-len(blob) % 4)
    with Path(path).open("wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 28 + len(js) + len(blob)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + blob)


def merge(base_path, context_path, out_path):
    """Append the context GLB's nodes, meshes and materials to a single-buffer base GLB."""
    base, b0 = read_glb_header(base_path)
    ctx, c0 = read_glb_header(context_path)
    if len(base.get("buffers", [])) != 1 or "uri" in base["buffers"][0]:
        raise ValueError("merge needs a base GLB with one embedded buffer")
    blob = bytearray(Path(base_path).read_bytes()[b0 : b0 + base["buffers"][0]["byteLength"]])
    blob += b"\0" * (-len(blob) % 4)
    shift = len(blob)
    blob += Path(context_path).read_bytes()[c0 : c0 + ctx["buffers"][0]["byteLength"]]
    off = {
        k: len(base.setdefault(k, []))
        for k in ("bufferViews", "accessors", "materials", "meshes", "nodes")
    }
    for bv in ctx["bufferViews"]:
        base["bufferViews"].append({**bv, "byteOffset": bv.get("byteOffset", 0) + shift})
    for acc in ctx["accessors"]:
        base["accessors"].append({**acc, "bufferView": acc["bufferView"] + off["bufferViews"]})
    base["materials"] += ctx["materials"]
    for mesh in ctx["meshes"]:
        prims = []
        for p in mesh["primitives"]:
            attrs = {k: v + off["accessors"] for k, v in p["attributes"].items()}
            prims.append(
                {
                    **p,
                    "attributes": attrs,
                    "indices": p["indices"] + off["accessors"],
                    "material": p["material"] + off["materials"],
                }
            )
        base["meshes"].append({**mesh, "primitives": prims})
    for node in ctx["nodes"]:
        base["nodes"].append({**node, "mesh": node["mesh"] + off["meshes"]})
    roots = base["scenes"][base.get("scene", 0)]["nodes"]
    roots += [i + off["nodes"] for i in ctx["scenes"][0]["nodes"]]
    base["buffers"][0]["byteLength"] = len(blob)
    write_glb(out_path, base, bytes(blob))


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=Path, required=True, help="baked solver GLB of the scene")
    ap.add_argument("--georef", type=Path, required=True, help="georef_roads.py report")
    ap.add_argument("--out", type=Path, required=True, help="new output directory")
    ap.add_argument("--cell", type=int, default=2, help="grid cell the plan must preserve")
    ap.add_argument("--model-prefix", default="Agent_", help="detailed building node prefix")
    ap.add_argument("--osm-json", type=Path, help="reuse a saved Overpass response")
    ap.add_argument("--overpass", default=OVERPASS)
    ap.add_argument(
        "--merge-into",
        type=Path,
        action="append",
        default=[],
        help="also write <out>/<name> = this GLB + context (repeatable)",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)

    georef = json.loads(args.georef.read_text())
    doc, model_ids, road_tris, ground = base_scene(args.base, args.model_prefix)
    plan, extent = context_extent(doc, args.cell)

    sim = georef["similarity"]
    frame = enu_basis(*georef["tangent_plane_origin_latlon"])
    a = math.radians(sim["rotation_deg_ccw_local_to_enu"])
    r = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    corners = np.array([[x, y] for x in extent[:, 0] for y in extent[:, 1]])
    lat, lon = to_latlon(corners @ (sim["scale"] * r).T + sim["translation_enu_m"], frame)
    bbox = (lat.min() - 2e-4, lon.min() - 2e-4, lat.max() + 2e-4, lon.max() + 2e-4)

    raw = (
        json.loads(args.osm_json.read_text())
        if args.osm_json
        else fetch_buildings([round(v, 6) for v in bbox], args.overpass)
    )
    (args.out / "osm-buildings.json").write_text(json.dumps(raw))

    # 1 m occupancy of detailed buildings and modelled roads in the context extent.
    cell = 1.0
    shape = tuple(np.ceil((extent[1] - extent[0])[::-1] / cell).astype(int))
    roads = rasterise_triangles(road_tris, extent[0], cell, shape)
    detailed = np.zeros(shape, bool)
    items, detailed_pts = [], []
    for key, wid, tags, ring, holes in footprints(raw):
        xy = latlon_to_local([p[0] for p in ring], [p[1] for p in ring], georef)
        if wid in model_ids:
            detailed_pts.append(xy)
            sl, m = rasterise_polygon(xy, extent[0], cell, shape)
            if sl:
                detailed[sl] |= m
            continue
        items.append((key, tags, xy, holes))
    if not detailed_pts:
        raise SystemExit(f"no OSM building matches a {args.model_prefix}<id> node")
    hull = convex_hull(np.concatenate(detailed_pts))
    heights = []
    for n in doc["nodes"]:
        if (m := re.match(rf"^{re.escape(args.model_prefix)}(\d+)", n.get("name", ""))) and n.get(
            "extras", {}
        ).get("physics_class", "building") == "building":
            top = max(
                doc["accessors"][p["attributes"]["POSITION"]]["max"][1]
                for p in doc["meshes"][n["mesh"]]["primitives"]
            )
            heights.append((m.group(1), top))
    per_building = {}
    for k, top in heights:
        per_building[k] = max(per_building.get(k, 0.0), top)
    default_h = float(np.median(list(per_building.values())))

    glb = GlbWriter()
    mat = glb.material(BUILDING_MATERIAL, (0.78, 0.74, 0.68))
    reasons, sources, kept = Counter(), Counter(), []
    occupancy = np.zeros(shape, bool)
    for key, tags, xy, holes in items:
        ring = clean_ring(xy)
        if ring is None:
            reasons["degenerate footprint"] += 1
            continue
        if np.any(ring < extent[0]) or np.any(ring > extent[1]):
            reasons["crosses context extent"] += 1
            continue
        if in_convex(ring.mean(0), hull):
            reasons["inside detailed zone"] += 1
            continue
        sl, m = rasterise_polygon(ring, extent[0], cell, shape)
        area = max(int(m.sum()), 1) if sl else 1
        if sl and (detailed[sl] & m).sum() > 0.05 * area:
            reasons["overlaps detailed building"] += 1
            continue
        if sl and (roads[sl] & m).sum() > 0.2 * area:
            reasons["overlaps modelled road"] += 1
            continue
        h, src = height(tags, default_h)
        try:
            pos, nor, ind = extrude(ring, 0.0, h)
        except ValueError:
            reasons["self-intersecting footprint"] += 1
            continue
        name = "Context_" + key.replace("/", "_").replace("#", "_")
        extras = {"physics_class": "building", "osm": key, "height_m": h, "height_source": src}
        if holes:
            extras["note"] = "inner courtyards not modelled"
        glb.add(name, pos, nor, ind, mat, extras)
        if sl:
            occupancy[sl] |= m
        sources[src] += 1
        kept.append(
            {"osm": key, "height_m": h, "height_source": src, "ring": ring.round(2).tolist()}
        )

    # Flat ground ring: context extent minus the supplied ground's bounding box.
    gmat = glb.material(GROUND_MATERIAL, (0.55, 0.53, 0.5))
    if ground:
        g0 = np.min([g[0] for g in ground], 0)
        g1 = np.max([g[1] for g in ground], 0)
        z = float(g1[2])
        (x0, y0), (x1, y1) = extent
        boxes = [
            (x0, y0, x1, g0[1]),
            (x0, g1[1], x1, y1),
            (x0, g0[1], g0[0], g1[1]),
            (g1[0], g0[1], x1, g1[1]),
        ]
        for i, (ax, ay, bx, by) in enumerate(boxes):
            if bx - ax < 0.01 or by - ay < 0.01:
                continue
            quad = np.array([[ax, z, -ay], [bx, z, -ay], [bx, z, -by], [ax, z, -by]])
            glb.add(
                f"Ground: context extension {i}",
                quad,
                np.tile([0.0, 1.0, 0.0], (4, 1)),
                np.array([[0, 1, 2], [0, 2, 3]]),
                gmat,
                {"physics_class": "ground", "source": "assumed flat at supplied ground level"},
            )
    glb.write(args.out / "context.glb")

    merged_plan = plan_grid(
        np.vstack(
            [
                np.minimum(local_bounds(doc)[0], [*extent[0], 0]),
                np.maximum(local_bounds(doc)[1], [*extent[1], 0]),
            ]
        ),
        args.cell,
    )
    assert np.array_equal(merged_plan["origin_xy"], plan["origin_xy"])
    assert np.array_equal(merged_plan["size_xy_m"], plan["size_xy_m"])
    for target in args.merge_into:
        merge(target, args.out / "context.glb", args.out / target.name)

    def sha(p):
        return hashlib.file_digest(Path(p).open("rb"), "sha256").hexdigest()

    domain = plan["size_xy_m"].prod()
    report = {
        "base": {"file": args.base.name, "sha256": sha(args.base)},
        "georef": {"file": args.georef.name, "sha256": sha(args.georef)},
        "osm": {
            "endpoint": raw.get("endpoint"),
            "timestamp_osm_base": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "fetched_at": raw.get("fetched_at"),
            "bbox_swne": [float(v) for v in bbox],
            "license": "ODbL; © OpenStreetMap contributors",
            "elements": len(raw["elements"]),
        },
        "grid_plan": {
            "cell_m": args.cell,
            "origin_xy_m": plan["origin_xy"].tolist(),
            "size_xy_m": plan["size_xy_m"].tolist(),
            "unchanged_after_merge": True,
        },
        "context_extent_m": extent.tolist(),
        "detailed_model": {
            "prefix": args.model_prefix,
            "osm_ids_matched": len(model_ids & {e.get("id") for e in raw["elements"]}),
            "median_height_m": default_h,
        },
        "kept": len(kept),
        "dropped": dict(reasons),
        "height_sources": dict(sources),
        "level_height_m": LEVEL_M,
        "footprint_fraction_of_domain": {
            "detailed_osm_footprints": float(detailed.sum() * cell**2 / domain),
            "context_buildings": float(occupancy.sum() * cell**2 / domain),
        },
        "limits": [
            "LOD1 extrusions with flat roofs; facades, roofs and heights are not surveyed.",
            "Untagged heights use the detailed model's median building height.",
            "Inner courtyards of multipolygon buildings are filled.",
            "Ground extension is flat at the supplied ground level, not terrain.",
        ],
    }
    (args.out / "context-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "context-footprints.json").write_text(json.dumps(kept))
    print(json.dumps({k: report[k] for k in ("kept", "dropped", "height_sources")}, indent=2))
    print(json.dumps(report["footprint_fraction_of_domain"], indent=2))


if __name__ == "__main__":
    main()
