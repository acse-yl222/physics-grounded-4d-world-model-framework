"""img2city/building/courtyard_agent.py -- recover courtyards OSM does not model, from the
satellite tile (08-17: "we already call all these Google APIs -- when
OSM is missing information, look there").

Two-tier courtyard sourcing:
  tier 1  OSM multipolygon inner rings (deterministic; city_pilot.fetch_osm
          keeps them as meta["holes"] since 08-17)
  tier 2  THIS module: for big buildings (>= --min-area m2) with NO tier-1
          holes, the agent reads the building's own satellite.png and returns
          courtyard rectangles in OBB fractions; they are converted to scene
          polygons and written into buildings.json meta["holes"] with
          src="satellite_agent" provenance (same pattern as every other
          agent-read value). The Natural History Museum is the type case: a
          solid `way` in OSM, two big internal courtyards on the tile.

The assembly's polygon builder boolean-cuts meta["holes"] regardless of tier.

  python -m img2city.building.courtyard_agent --out data/city_sk2            # all eligible
  python -m img2city.building.courtyard_agent --out data/city_sk2 --ids 24436446
"""
from __future__ import annotations

from img2city import config
from img2city.agent import llm
import argparse
import json
import math
import os
import re

SYSTEM = ("You are reading ONE building's satellite image to map its internal "
          "courtyards (open-air voids fully enclosed by the building). "
          "Reply with JSON only.")

ASK = """The satellite image is centred on one building: {name} (footprint about
{L:.0f} m x {W:.0f} m, outlined by its roof). Identify its INTERNAL COURTYARDS:
open-air voids fully surrounded by the building's own roof. Ignore streets,
front plazas, lightwells under 6 m, and gaps between this and OTHER buildings.

Reply JSON only:
{{"courtyards": [{{"cx": 0.0-1.0, "cy": 0.0-1.0, "w": 0.0-1.0, "h": 0.0-1.0}}],
  "confidence": 0.0-1.0, "note": "<one line>"}}

cx,cy = courtyard centre as fractions of the footprint's oriented bounding box
(0,0 = one corner, 1,1 = the opposite); w,h = courtyard size as fractions of
the box edges. Empty list if the roof is solid."""


def read_courtyards(m, bdir, model):
    sat = os.path.join(bdir, "satellite.png")
    if not os.path.exists(sat):
        return None
    L, W = m["obb"][2], m["obb"][3]
    txt, _u, _c = llm.vision_call(
        SYSTEM, ASK.format(name=m.get("name") or "unnamed", L=L, W=W),
        [sat], model=model)
    mm = re.search(r"\{.*\}", txt, re.S)
    if not mm:
        return None
    try:
        rec = json.loads(mm.group(0), strict=False)
    except json.JSONDecodeError:
        return None
    cx0, cy0, _L, _W, ang = m["obb"]
    ca, sa = math.cos(ang), math.sin(ang)
    holes = []
    for c in rec.get("courtyards") or []:
        try:
            fx, fy = float(c["cx"]) - 0.5, float(c["cy"]) - 0.5
            hw, hh = float(c["w"]) * _L / 2, float(c["h"]) * _W / 2
        except (KeyError, TypeError, ValueError):
            continue
        if hw < 3.0 or hh < 3.0:                     # <6 m voids: not courtyards
            continue
        # shrink a touch so the cut never nicks the outer wall
        hw, hh = min(hw, _L * 0.42), min(hh, _W * 0.42)
        ox, oy = fx * _L, fy * _W
        ring = []
        for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            x, y = ox + dx, oy + dy
            ring.append([round(cx0 + x * ca - y * sa, 2),
                         round(cy0 + x * sa + y * ca, 2)])
        holes.append(ring)
    return {"holes": holes, "confidence": rec.get("confidence"),
            "note": str(rec.get("note") or "")[:120]}


ASK_MASS = """The satellite image is centred on one building: {name} (footprint
about {L:.0f} m x {W:.0f} m). Divide its roof into up to 8 rectangular ZONES of
visibly DISTINCT height or form -- towers, main halls/naves, low wings,
entrance pavilions. Do not invent zones on a uniform roof.

Reply JSON only:
{{"zones": [{{"cx": 0.0-1.0, "cy": 0.0-1.0, "w": 0.0-1.0, "h": 0.0-1.0,
   "kind": "tower|hall|wing|pavilion|other"}}],
  "confidence": 0.0-1.0, "note": "<one line>"}}

cx,cy/w,h are fractions of the footprint's oriented bounding box. Only zones
INSIDE this building's own roof."""


def _zone_rings(m, zones):
    """OBB-fraction rectangles -> scene-coordinate rings, centre-inside-poly
    filtered (the OBB corners of a big museum lie in its gardens)."""
    from img2city.scene.assets import _point_in_poly
    cx0, cy0, L, W, ang = m["obb"]
    ca, sa = math.cos(ang), math.sin(ang)
    rings = []
    for z in zones or []:
        try:
            fx, fy = float(z["cx"]) - 0.5, float(z["cy"]) - 0.5
            hw, hh = float(z["w"]) * L / 2, float(z["h"]) * W / 2
        except (KeyError, TypeError, ValueError):
            continue
        if hw < 2.0 or hh < 2.0:
            continue
        ox, oy = fx * L, fy * W
        ccx, ccy = cx0 + ox * ca - oy * sa, cy0 + ox * sa + oy * ca
        if not _point_in_poly(ccx, ccy, [tuple(q) for q in m["pts"]]):
            continue
        ring = []
        for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            x, y = ox + dx, oy + dy
            ring.append([round(cx0 + x * ca - y * sa, 2),
                         round(cy0 + x * sa + y * ca, 2)])
        rings.append({"pts": ring, "kind": str(z.get("kind") or "other")[:12]})
    return rings


def _lidar_sampler(out, anchor):
    """-> f(scene_ring) = p90 LiDAR height inside the ring, or None. England
    only (EA 1m DSM-DTM, tiles already cached by height_check)."""
    import numpy as np
    from img2city.city.height_check import load_grid, _bng_window
    from img2city.scene.assets import _point_in_poly
    from pyproj import Transformer
    dsm_p = os.path.join(out, "lidar", "dsm.tif")
    if not os.path.exists(dsm_p):
        return None
    hgt = load_grid(dsm_p) - load_grid(os.path.join(out, "lidar", "dtm.tif"))
    H, W = hgt.shape
    x0, y0, x1, y1 = _bng_window(anchor)
    emin, nmax = float(x0), float(y1)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))

    def sample(ring):
        bng = []
        for x, y in ring:
            lon = anchor["lon0"] + x / kx
            lat = anchor["lat0"] + y / 110540.0
            e, n = tr.transform(lon, lat)
            bng.append((e, n))
        es = [p[0] for p in bng]
        ns = [p[1] for p in bng]
        vals = []
        for r in range(max(0, int(nmax - max(ns))),
                       min(H, int(nmax - min(ns)) + 1)):
            n = nmax - r - 0.5
            for c in range(max(0, int(min(es) - emin)),
                           min(W, int(max(es) - emin) + 1)):
                e = emin + c + 0.5
                if _point_in_poly(e, n, bng):
                    v = hgt[r, c]
                    if np.isfinite(v):
                        vals.append(v)
        if len(vals) < 4:
            return None
        return round(float(np.percentile(np.array(vals), 90)), 1)
    return sample


def read_massing(m, bdir, model, sample):
    """Agent draws the zones (geometry from the satellite tile); LiDAR
    measures each zone's height (numbers are never guessed). Zones within
    ±15% of each other collapse to the base prism."""
    sat = os.path.join(bdir, "satellite.png")
    if not os.path.exists(sat):
        return None
    L, W = m["obb"][2], m["obb"][3]
    txt, _u, _c = llm.vision_call(
        SYSTEM, ASK_MASS.format(name=m.get("name") or "unnamed", L=L, W=W),
        [sat], model=model)
    mm = re.search(r"\{.*\}", txt, re.S)
    if not mm:
        return None
    try:
        rec = json.loads(mm.group(0), strict=False)
    except json.JSONDecodeError:
        return None
    rings = _zone_rings(m, rec.get("zones"))
    parts = []
    for r in rings:
        h = sample(r["pts"]) if sample else None
        if h and h >= 4.0:
            parts.append({**r, "h": h})
    if len(parts) < 2:
        return None
    hs = sorted(p["h"] for p in parts)
    if hs[-1] < 1.25 * hs[0]:                # uniform roof: keep the prism
        return None
    return {"parts": parts, "note": str(rec.get("note") or "")[:120]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--min-area", type=float, default=3000.0)
    ap.add_argument("--model", default=config.VISION_MODEL)
    ap.add_argument("--massing", action="store_true",
                    help="also read distinct-height roof zones (satellite "
                         "geometry + LiDAR-measured heights) -> sat_parts")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    from img2city.city.generate import obb
    bj = os.path.join(out, "buildings.json")
    d = json.load(open(bj))
    sample = _lidar_sampler(out, d["anchor"]) if a.massing else None
    if a.massing and sample is None:
        print("[courtyard] no LiDAR tiles -- massing heights unavailable, "
              "skipping massing")
    changed = 0
    for m in d["buildings"]:
        if a.ids and m["id"] not in set(a.ids):
            continue
        if not a.ids and m["area_m2"] < a.min_area:
            continue
        m["obb"] = obb(m["pts"])
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if not m.get("holes"):                # tier-1 OSM holes win
            rec = read_courtyards(m, bdir, a.model)
            if rec:
                print(f"[courtyard] {m['id']} '{m.get('name') or ''}': "
                      f"{len(rec['holes'])} courtyard(s), conf "
                      f"{rec['confidence']} -- {rec['note']}")
                if rec["holes"]:
                    m["holes"] = rec["holes"]
                    m["holes_src"] = "satellite_agent"
                    changed += 1
        if a.massing and sample:
            mrec = read_massing(m, bdir, a.model, sample)
            if mrec:
                m["sat_parts"] = mrec["parts"]
                m["sat_parts_src"] = "satellite_agent+ea_lidar"
                changed += 1
                print(f"[massing] {m['id']} '{m.get('name') or ''}': "
                      f"{len(mrec['parts'])} zones, heights "
                      f"{sorted(round(p['h']) for p in mrec['parts'])}"
                      f" -- {mrec['note']}")
            else:
                print(f"[massing] {m['id']} '{m.get('name') or ''}': "
                      "uniform roof / no differentiated zones")
        m.pop("obb", None)
    if changed:
        json.dump(d, open(bj, "w"), indent=1)
        print(f"[courtyard] {changed} building records updated -> {bj}")


if __name__ == "__main__":
    main()
