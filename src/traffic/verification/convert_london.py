from pathlib import Path
from common.layout import scene_input
from common.runtime import trial_root

"""
Convert the GeoJSON of the real London map to the road network format for the simulator

Notes:
Some frameworks and code were implemented with the assistance of AI. 
Clear instructions and objectives were provided to ensure all code modified by AI aligns with my intentions.
"""
import json
import sys
import os
from collections import defaultdict, Counter
import numpy as np

CELL_SIZE = 3.0
M_PER_DEG_LAT = 111320.0

MAIN_HIGHWAYS = {
    "primary",
    "secondary",
    "trunk",
    "tertiary",
    "trunk_link",
    "primary_link",
    "secondary_link",
}


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _backwards(dir_chain, s):
    if dir_chain is None or len(s) < 2:
        return False
    dir_s = (s[1][0] - s[0][0], s[1][1] - s[0][1])
    return dir_chain[0] * dir_s[0] + dir_chain[1] * dir_s[1] < 0


def _seg_length_m(seg, m_per_deg_lon):
    total = 0.0
    for a, b in zip(seg, seg[1:]):
        dlon = (b[0] - a[0]) * m_per_deg_lon
        dlat = (b[1] - a[1]) * M_PER_DEG_LAT
        total += (dlon**2 + dlat**2) ** 0.5
    return total


def _try_extend(anchor, dir_away, s, threshold_deg):
    """
    Determine whether splicing is possible
    """
    if _dist(anchor, s[0]) <= threshold_deg and len(s) >= 2:
        dir_s = (s[1][0] - s[0][0], s[1][1] - s[0][1])
        if dir_away is None or dir_away[0] * dir_s[0] + dir_away[1] * dir_s[1] >= 0:
            return True, False
    if _dist(anchor, s[-1]) <= threshold_deg and len(s) >= 2:
        dir_s = (s[-2][0] - s[-1][0], s[-2][1] - s[-1][1])
        if dir_away is None or dir_away[0] * dir_s[0] + dir_away[1] * dir_s[1] >= 0:
            return True, True
    return None


def merge_segments(segments, threshold_deg=0.0002):
    """
    Splice together fragments of the same road
    """
    segs = [list(s) for s in segments]
    used = [False] * len(segs)
    chains = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        chain = segs[i]
        while True:
            extended = False
            # Extend backward first (append to the tail), then extend forward (prepend to the head)
            for side in ("tail", "head"):
                if len(chain) < 2:
                    anchor = chain[0]
                    dir_away = None
                elif side == "tail":
                    anchor = chain[-1]
                    dir_away = (
                        chain[-1][0] - chain[-2][0],
                        chain[-1][1] - chain[-2][1],
                    )  # Continue moving away from the end of the chain
                else:
                    anchor = chain[0]
                    dir_away = (
                        chain[0][0] - chain[1][0],
                        chain[0][1] - chain[1][1],
                    )  # Continue moving away from the chain head
                best_j, best_d, best_rev = None, float("inf"), False
                for j in range(len(segs)):
                    if used[j]:
                        continue
                    s = segs[j]
                    r = _try_extend(anchor, dir_away, s, threshold_deg)
                    if r is None:
                        continue
                    ok, rev = r
                    d = _dist(anchor, s[-1] if rev else s[0])
                    if d < best_d:
                        best_j, best_d, best_rev = j, d, rev
                if best_j is not None:
                    s = segs[best_j]
                    if side == "tail":
                        ss = s[::-1] if best_rev else s
                        chain = chain + ss[1:]
                    else:
                        chain = s + chain[1:]
                    used[best_j] = True
                    extended = True
                    break
            if not extended:
                break
        chains.append(chain)
    return chains


def mid_line(c1, c2):
    if _dist(c1[0], c2[-1]) < _dist(c1[0], c2[0]):
        c2 = c2[::-1]
    n = min(len(c1), len(c2))
    return [((c1[i][0] + c2[i][0]) / 2, (c1[i][1] + c2[i][1]) / 2) for i in range(n)]


def is_parallel(c1, c2):
    d_ss = _dist(c1[0], c2[0]) + _dist(c1[-1], c2[-1])
    d_st = _dist(c1[0], c2[-1]) + _dist(c1[-1], c2[0])
    return min(d_ss, d_st) < 0.0005


def convert(geojson_path):
    with open(geojson_path) as f:
        data = json.load(f)

    feats = [f for f in data["features"] if f["properties"].get("highway") in MAIN_HIGHWAYS]

    byname = defaultdict(list)
    for f in feats:
        byname[f["properties"].get("name", "unnamed")].append(f)

    allpts = [p for f in feats for p in f["geometry"]["coordinates"]]
    min_lon = min(p[0] for p in allpts)
    max_lon = max(p[0] for p in allpts)
    min_lat = min(p[1] for p in allpts)
    max_lat = max(p[1] for p in allpts)

    # Meters-per-degree derived from this map's own centre latitude (generic,
    # not a hard-coded London latitude), so any real map works.
    lat_center = (min_lat + max_lat) / 2.0
    m_per_deg_lon = 111320.0 * np.cos(np.radians(lat_center))

    span_c = (max_lon - min_lon) * m_per_deg_lon / CELL_SIZE
    span_r = (max_lat - min_lat) * M_PER_DEG_LAT / CELL_SIZE
    PAD = 2.0
    grid_size = int(np.ceil(max(span_c, span_r)) + 2 * PAD)

    roads = []
    for name, fs in sorted(byname.items()):
        oneway = Counter(f["properties"].get("oneway", "no") for f in fs).most_common(1)[0][0]
        lanes = int(Counter(f["properties"].get("lanes", "1") for f in fs).most_common(1)[0][0])
        highway = Counter(f["properties"].get("highway") for f in fs).most_common(1)[0][0]

        segs = [f["geometry"]["coordinates"] for f in fs]
        segs = [s for s in segs if _seg_length_m(s, m_per_deg_lon) >= 15]  # filter
        chains = merge_segments(segs)
        chains = [c for c in chains if len(c) >= 3]
        if not chains:
            continue

        if len(chains) == 2 and is_parallel(chains[0], chains[1]):
            # Two-way arterial road
            pieces = [(mid_line(chains[0], chains[1]), True, max(1, lanes // 2), name)]
        elif len(chains) == 1:
            two_way = oneway != "yes"
            pieces = [(chains[0], two_way, max(1, lanes // 2) if two_way else lanes, name)]
        else:
            pieces = [(c, False, lanes, f"{name}#{k}") for k, c in enumerate(chains)]

        for chain, two_way, lanes_per_dir, rname in pieces:
            centerline = []
            for lon, lat in chain:
                col = (lon - min_lon) * m_per_deg_lon / CELL_SIZE + PAD
                row = (max_lat - lat) * M_PER_DEG_LAT / CELL_SIZE + PAD
                centerline.append((round(row, 2), round(col, 2)))
            roads.append(
                {
                    "centerline": centerline,
                    "lanes_per_dir": lanes_per_dir,
                    "two_way": two_way,
                    "name": rname,
                    "highway": highway,
                }
            )

    # Coordinate transform: grid (row,col) <-> WGS84 (lon,lat); read by export_prediction.py.
    transform = {
        "cell_size_m": CELL_SIZE,
        "pad": PAD,
        "m_per_deg_lat": M_PER_DEG_LAT,
        "m_per_deg_lon": m_per_deg_lon,
        "origin_lon": min_lon,
        "origin_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "min_lat": min_lat,
        "max_lat": max_lat,
        "note": "grid(row,col)->lonlat: lon=origin_lon+(col-pad)*cell_size_m/m_per_deg_lon; lat=origin_lat-(row-pad)*cell_size_m/m_per_deg_lat",
    }

    return roads, grid_size, transform


if __name__ == "__main__":
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(scene_input("south_ken", "traffic", "roads.geojson"))
    )
    roads, grid_size, transform = convert(path)
    print(f"Total {len(roads)} main roads:\n")
    for r in roads:
        rows = [p[0] for p in r["centerline"]]
        cols = [p[1] for p in r["centerline"]]
        print(
            f"  {r['name']}: hw={r['highway']}, lanes_per_dir={r['lanes_per_dir']}, "
            f"two_way={r['two_way']}, point={len(r['centerline'])}, "
            f"row[{min(rows):.0f},{max(rows):.0f}], col[{min(cols):.0f},{max(cols):.0f}]"
        )

    out = (
        sys.argv[2]
        if len(sys.argv) > 2
        else str(trial_root("south_ken", "traffic_map") / "london_roads.json")
    )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({"grid_size": grid_size, "roads": roads, "transform": transform}, f, indent=2)
    print(f"\nGRID_SIZE={grid_size}, saved: {out}")
