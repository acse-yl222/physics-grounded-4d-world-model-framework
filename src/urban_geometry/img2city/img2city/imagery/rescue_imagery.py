"""img2city/imagery/rescue_imagery.py -- replace PLACEHOLDER reference photos with real ones.

The imagery fetch never validated static-image CONTENT, and Google returns a
"Sorry, we have no imagery here" tile as a 200 OK -- 48/78 Canary Wharf
references were that grey card (the estate interior has no public panos at the
building centroids), so half the area's specs and checklists were derived from
satellite alone while a placeholder posed as the street photo.

Per building with an unusable reference: sample panos on RINGS around the
centroid (metadata queried FROM the ring points -- sv_metadata always returns
the nearest pano to the query point, however large the radius), fetch a
pitched-up shot sized to the building, validate content, and only on success
replace streetview.png + pano.json (originals kept as .pre_rescue) and clear
the derived files (gate/spec/facts/colors -> .pre_rescue) so the agent re-runs
from real imagery. Buildings with no reachable pano keep their state and are
listed -- honest satellite-only coverage, not silent garbage.

  python -m img2city.imagery.rescue_imagery --out data/city_cw            # report + rescue
  python -m img2city.imagery.rescue_imagery --out data/city_cw --dry-run
"""
from __future__ import annotations
import argparse
import json
import math
import os
import shutil

import numpy as np
from PIL import Image

from img2city.imagery import maps_fetch


def unusable_image(p):
    """Google's sorry tile and any near-blank frame: near-uniform BACKGROUND
    with only a sliver of ink (plain std misses the tile -- its text/logo push
    std past a threshold)."""
    try:
        a = np.asarray(Image.open(p).convert("L"), dtype=float)
    except Exception:
        return True
    med = np.median(a)
    return float(np.mean(np.abs(a - med) < 6)) > 0.93


def rescue_building(m, bdir, key, dry=False):
    lat, lng = m["center_latlng"]
    h = max(6.0, m["height"])
    # a giant-FOOTPRINT building needs a stand-off scaled to its plan size,
    # not its height: the Science Museum (h~20 m but 140 m wide) was
    # "rescued" from 18 m — a doorway close-up read as an interior (08-17)
    if m.get("obb"):
        h = max(h, 0.55 * max(m["obb"][2], m["obb"][3]))
    else:
        h = max(h, 0.55 * (m.get("area_m2") or 0.0) ** 0.5)
    kx = 111320.0 * math.cos(math.radians(lat))
    best = None
    for want in (max(35.0, h * 0.7), max(60.0, h * 1.0), 130.0):
        for k in range(12):
            a = k * math.pi / 6
            qlat = lat + want * math.cos(a) / 110540.0
            qlng = lng + want * math.sin(a) / kx
            meta = maps_fetch.sv_metadata(qlat, qlng, 50, key)
            if meta.get("status") != "OK":
                continue
            p = meta["location"]
            # INDOOR-PANO FILTER (08-17): museums are full of interior Street
            # View, and a pano whose position lies INSIDE the building's own
            # footprint is an interior by construction — the Science Museum's
            # "rescued" views were exhibition halls. Geometric test, no tags.
            if m.get("pts"):
                px = (p["lng"] - lng) * kx
                py = (p["lat"] - lat) * 110540.0
                cxl = sum(q[0] for q in m["pts"]) / len(m["pts"])
                cyl = sum(q[1] for q in m["pts"]) / len(m["pts"])
                pxs, pys = cxl + px, cyl + py
                inside = False
                pts_ = m["pts"]
                for a_, b_ in zip(pts_, pts_[1:] + pts_[:1]):
                    if (a_[1] > pys) != (b_[1] > pys):
                        t_ = (pys - a_[1]) / (b_[1] - a_[1])
                        if pxs < a_[0] + t_ * (b_[0] - a_[0]):
                            inside = not inside
                if inside:
                    continue
            dist = math.hypot((p["lng"] - lng) * kx, (p["lat"] - lat) * 110540.0)
            if dist < 12:
                continue
            score = abs(dist - h * 0.8)
            if best is None or score < best[0]:
                best = (score, p, dist)
        if best:
            break
    if best is None:
        return None
    _s, p, dist = best
    if dry:
        return dist
    hd = maps_fetch._bearing(p["lat"], p["lng"], lat, lng)
    pitch = min(45.0, math.degrees(math.atan2(h * 0.5, dist)))
    tmp = os.path.join(bdir, "_rescue.png")
    maps_fetch._get(maps_fetch.STREETVIEW,
                    {"location": f"{p['lat']},{p['lng']}", "size": "640x640",
                     "heading": round(hd, 1), "pitch": round(pitch, 1),
                     "fov": 90, "source": "outdoor", "key": key}, tmp)
    if unusable_image(tmp):
        os.remove(tmp)
        return None
    sv = os.path.join(bdir, "streetview.png")
    for f in (sv, os.path.join(bdir, "pano.json")):
        if os.path.exists(f) and not os.path.exists(f + ".pre_rescue"):
            shutil.copy(f, f + ".pre_rescue")
    shutil.move(tmp, sv)
    json.dump([p["lat"], p["lng"]], open(os.path.join(bdir, "pano.json"), "w"))
    # stale derived state -> .pre_rescue, so the agent re-runs from the photo
    for stale in ("gate.json", "spec.json", "facade_facts.json", "colors.json",
                  "streetview_clean.png", "glass_view.png"):
        sp = os.path.join(bdir, stale)
        if os.path.exists(sp):
            bak = sp + ".pre_rescue"
            if os.path.exists(bak):
                os.remove(sp)
            else:
                shutil.move(sp, bak)
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    d = json.load(open(os.path.join(out, "buildings.json")))
    key = maps_fetch._key()
    rescued, hopeless, fine = [], [], 0
    for m in d["buildings"]:
        bdir = os.path.join(out, "buildings", str(m["id"]))
        sv = os.path.join(bdir, "streetview.png")
        clean = os.path.join(bdir, "streetview_clean.png")
        ref = clean if os.path.exists(clean) else sv
        if not os.path.exists(sv):
            continue
        if not unusable_image(ref):
            fine += 1
            continue
        got = rescue_building(m, bdir, key, a.dry_run)
        if got is None:
            hopeless.append(m["id"])
        else:
            rescued.append(m["id"])
            print(f"[rescue] {m['id']} ({(m.get('name') or m['btype'])[:24]}): "
                  f"pano {got:.0f} m out")
    print(f"[rescue] {fine} already fine, {len(rescued)} rescued, "
          f"{len(hopeless)} no public pano (satellite-only): {hopeless}")
    if rescued and not a.dry_run:
        with open(os.path.join(out, "rescued_ids.json"), "w") as f:
            json.dump(rescued, f)
        print(f"[rescue] re-spec next: python -m img2city.city.generate --out {a.out} "
              f"--min-area 999999 --extra-ids " + " ".join(map(str, rescued)))


if __name__ == "__main__":
    main()
