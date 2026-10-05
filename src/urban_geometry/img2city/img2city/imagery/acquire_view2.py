"""img2city/imagery/acquire_view2.py -- a SECOND validated street view per building, into the
refine loop's existing view2/ convention (so both one-shot spec calls and the
refine loop pick it up with zero further wiring).

Vantage rule: sample panos on a ring around the centroid, keep the usable shot
whose bearing is FURTHEST from the primary pano's (a second view is worth its
cost only if it shows a different facade). Content-validated (no sorry tiles).

  python -m img2city.imagery.acquire_view2 --out data/city_ams --min-area 150
"""
from __future__ import annotations
import argparse
import json
import math
import os

from img2city.imagery import maps_fetch
from img2city.imagery.rescue_imagery import unusable_image


def acquire(m, bdir, key):
    lat, lng = m["center_latlng"]
    h = max(6.0, m["height"])
    kx = 111320.0 * math.cos(math.radians(lat))
    p1 = json.load(open(os.path.join(bdir, "pano.json")))
    b1 = maps_fetch._bearing(lat, lng, p1[0], p1[1])   # centroid -> primary pano
    want = max(30.0, min(120.0, h * 0.8))
    best = None
    for k in range(12):
        a = k * math.pi / 6
        qlat = lat + want * math.cos(a) / 110540.0
        qlng = lng + want * math.sin(a) / kx
        meta = maps_fetch.sv_metadata(qlat, qlng, 45, key)
        if meta.get("status") != "OK":
            continue
        p = meta["location"]
        dist = math.hypot((p["lng"] - lng) * kx, (p["lat"] - lat) * 110540.0)
        if dist < 10:
            continue
        b2 = maps_fetch._bearing(lat, lng, p["lat"], p["lng"])
        sep = abs((b2 - b1 + 180) % 360 - 180)         # angular separation
        if best is None or sep > best[0]:
            best = (sep, p, dist)
    if best is None or best[0] < 55:                   # same side: not worth it
        return None
    sep, p, dist = best
    v2 = os.path.join(bdir, "view2")
    os.makedirs(v2, exist_ok=True)
    hd = maps_fetch._bearing(p["lat"], p["lng"], lat, lng)
    pitch = min(40.0, math.degrees(math.atan2(h * 0.45, dist)))
    png = os.path.join(v2, "streetview.png")
    maps_fetch._get(maps_fetch.STREETVIEW,
                    {"location": f"{p['lat']},{p['lng']}", "size": "640x640",
                     "heading": round(hd, 1), "pitch": round(pitch, 1),
                     "fov": 90, "source": "outdoor", "key": key}, png)
    if unusable_image(png):
        os.remove(png)
        return None
    json.dump([p["lat"], p["lng"]], open(os.path.join(v2, "pano.json"), "w"))
    return sep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-area", type=float, default=0.0)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    d = json.load(open(os.path.join(out, "buildings.json")))
    key = maps_fetch._key()
    got = skip = none = 0
    for m in d["buildings"]:
        if a.ids and str(m["id"]) not in set(a.ids):
            continue
        if m["area_m2"] < a.min_area:
            continue
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if not os.path.exists(os.path.join(bdir, "pano.json")):
            continue
        if os.path.exists(os.path.join(bdir, "view2", "streetview.png")) \
                and not a.force:
            skip += 1
            continue
        sep = acquire(m, bdir, key)
        if sep is None:
            none += 1
        else:
            got += 1
    print(f"[view2] {got} acquired, {skip} already had one, "
          f"{none} no independent vantage")


if __name__ == "__main__":
    main()
