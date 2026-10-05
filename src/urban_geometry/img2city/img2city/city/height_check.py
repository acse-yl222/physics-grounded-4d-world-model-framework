"""img2city/city/height_check.py -- verify the scene's building heights against Environment
Agency LiDAR (supervisor ask, 2026-07-14 meeting: "check the accuracy of the
generated building heights against a reference").

Reference: EA LiDAR Composite 1 m DSM (last return) minus 1 m DTM = measured
building height above local ground, fetched once for the block bbox from the
DEFRA WCS (open data):
  .../lidar-composite-digital-surface-model-last-return-dsm-1m/wcs
  .../lidar-composite-digital-terrain-model-dtm-1m/wcs
Both tiles are cached in data/<out>/lidar/{dsm,dtm}.tif (EPSG:27700, 1 m).

Per building: footprint (scene metres) -> WGS84 via the equirect anchor -> BNG
via pyproj; median of (DSM - DTM) over interior pixels = LiDAR height (median is
robust to pitched roofs and edge mixing; p90 is also reported as a ridge proxy).
Compared against the scene height (OSM building:levels x 3.2 for 195/229
buildings; 34 defaults -- no building here carries a surveyed height tag).

  python -m img2city.city.height_check --out data/city_sk
"""
from __future__ import annotations
import argparse
import json
import math
import os

import numpy as np
from PIL import Image

from img2city.scene.assets import _point_in_poly


def load_grid(path):
    a = np.asarray(Image.open(path), dtype=float)
    a[a < -100] = np.nan                     # nodata
    return a


def _bng_window(anchor):
    """The BNG pixel window the WCS fetch uses: bbox corners -> EPSG:27700,
    floor/ceil with a 30 m pad. emin/nmax derive from the SAME formula, so any
    area works without hand-passing tile origins (they were hard-coded to the
    city_sk tile until the Canary Wharf bootstrap hit NaNs)."""
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    s_, w_, n_, e_ = anchor["bbox"]
    x0, y0 = tr.transform(w_, s_)
    x1, y1 = tr.transform(e_, n_)
    return (math.floor(x0) - 30, math.floor(y0) - 30,
            math.ceil(x1) + 30, math.ceil(y1) + 30)


WCS = {"dsm": ("lidar-composite-digital-surface-model-last-return-dsm-1m",
               "9ba4d5ac-d596-445a-9056-dae3ddec0178__"
               "Lidar_Composite_Elevation_LZ_DSM_1m"),
       "dtm": ("lidar-composite-digital-terrain-model-dtm-1m",
               "Lidar_Composite_Elevation_DTM_1m")}


def fetch_tiles(out, anchor):
    """DEFRA WCS GetCoverage for the area bbox, cached. England-only data --
    outside EA coverage the request fails and heights stay on OSM tags."""
    import urllib.request
    x0, y0, x1, y1 = _bng_window(anchor)
    os.makedirs(os.path.join(out, "lidar"), exist_ok=True)
    for tag, (slug, cov) in WCS.items():
        p = os.path.join(out, "lidar", tag + ".tif")
        if os.path.exists(p):
            continue
        url = ("https://environment.data.gov.uk/spatialdata/%s/wcs"
               "?service=WCS&version=2.0.1&request=GetCoverage&coverageid=%s"
               "&format=image/tiff&subset=E(%d,%d)&subset=N(%d,%d)"
               % (slug, cov, x0, x1, y0, y1))
        with urllib.request.urlopen(url, timeout=180) as r:
            open(p, "wb").write(r.read())
        print(f"[heights] fetched {tag}.tif")


PITCHED = {"valley", "gable", "pitched_roof", "hipped_roof", "ridges", "sawtooth",
           "stepped_gable"}
CURVED = {"dome", "vault"}


def roof_class(spec):
    """Collapse a spec's roof vocabulary into one class for LiDAR validation:
    flat / flat_plant (flat with plant boxes) / pitched / mansard / curved /
    unknown (no spec). Pitched covers every ridged form (valley, gable, hipped,
    sawtooth, ridges); mansard is kept apart because its relief is a steep
    lower slope plus a flat deck, neither flat nor a ridge."""
    if not spec:
        return "unknown"
    forms = set()
    t = spec.get("terrace") or {}
    if t.get("roof_form"):
        forms.add(t["roof_form"])
    if spec.get("roof_form"):
        forms.add(spec["roof_form"])
    for k in ("pitched_roof", "hipped_roof", "mansard_cap", "stepped_gable"):
        if spec.get(k):
            forms.add(k)
    feats = set()
    for r in spec.get("roof") or []:
        if isinstance(r, dict) and r.get("type"):
            feats.add(r["type"])
    for e in spec.get("extra_parts") or []:
        if isinstance(e, dict) and e.get("type"):
            forms.add(e["type"])
    forms |= feats
    if forms & {"mansard", "mansard_cap"}:
        return "mansard"
    if forms & CURVED:
        return "curved"
    if forms & PITCHED:
        return "pitched"
    return "flat_plant" if "plant" in feats else "flat"


def _auc(pos, neg):
    """Rank-based AUC: P(relief of a random non-flat > random flat); ties 0.5."""
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def roof_check(a, hgt, d, anchor, tr):
    """--roof: does the roof FORM the agent wrote into each spec agree with the
    LiDAR surface? Per building, relief = p90 - p10 of (DSM - DTM) over
    INTERIOR pixels (1 m eroded, so edge mixing with the street and neighbours
    drops out). A flat roof is a low-relief surface; ridged forms are not.
    Reported threshold-free (AUC of relief separating predicted non-flat from
    predicted flat), per-class relief medians, and agreement with the OSM
    roof:shape tag on the (small) tagged subset. The LoD1 baseline predicts
    "flat" for every building, so its AUC is 0.5 by construction."""
    H, W = hgt.shape
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    osm_shape = {}
    try:
        raw = json.load(open(os.path.join(a.out, "osm_raw.json")))
        els = raw.get("elements", raw) if isinstance(raw, dict) else raw
        for e in els:
            sh = (e.get("tags") or {}).get("roof:shape")
            if sh:
                osm_shape[e["id"]] = sh
    except Exception:
        pass
    OSM_FLAT = {"flat"}
    OSM_PITCHED = {"gabled", "hipped", "double_saltbox", "quadruple_saltbox",
                   "gambrel", "skillion", "pyramidal", "saltbox", "half-hipped"}
    rows = []
    for b in d["buildings"]:
        bdir = os.path.join(a.out, "buildings", str(b["id"]))
        sp_p = os.path.join(bdir, "spec.json")
        spec = json.load(open(sp_p)) if os.path.exists(sp_p) else None
        shell = os.path.exists(os.path.join(bdir, "gate.json"))
        bng = []
        for x, y in b["pts"]:
            e, n = tr.transform(anchor["lon0"] + x / kx, anchor["lat0"] + y / 110540.0)
            bng.append((e, n))
        es = [p[0] for p in bng]; ns = [p[1] for p in bng]
        vals, slopes = [], []
        for r in range(max(1, int(a.nmax - max(ns))), min(H - 1, int(a.nmax - min(ns)) + 1)):
            n = a.nmax - r - 0.5
            for c in range(max(1, int(min(es) - a.emin)), min(W - 1, int(max(es) - a.emin) + 1)):
                e = a.emin + c + 0.5
                if not _point_in_poly(e, n, bng):
                    continue
                # erosion by a.erode metres: the footprint ring within that
                # distance of the wall is dropped, so OSM-vs-LiDAR
                # misregistration and wall-edge gradients stay outside
                er = a.erode
                if not all(_point_in_poly(e + de, n + dn, bng)
                           for de, dn in ((er, 0), (-er, 0), (0, er), (0, -er),
                                          (er, er), (-er, er), (er, -er), (-er, -er))):
                    continue
                v = hgt[r, c]
                if not np.isfinite(v):
                    continue
                vals.append(v)
                # local slope (central differences on the 1 m DSM): a ridged
                # roof has a steady gradient, a flat roof ~0; robust to the
                # wing/courtyard STEPS that dominate p90-p10 on large plans
                gx = hgt[r, c + 1] - hgt[r, c - 1]
                gy = hgt[r + 1, c] - hgt[r - 1, c]
                if np.isfinite(gx) and np.isfinite(gy):
                    slopes.append(0.5 * math.hypot(gx, gy))
        if len(vals) < 12 or len(slopes) < 12:
            continue
        vals = np.array(vals)
        rows.append({"id": b["id"], "cls": roof_class(spec) if not shell else "shell",
                     "slope_med": round(float(np.median(slopes)), 3),
                     "relief": round(float(np.percentile(vals, 90)
                                           - np.percentile(vals, 10)), 2),
                     "iqr": round(float(np.percentile(vals, 75)
                                        - np.percentile(vals, 25)), 2),
                     "lidar_med": round(float(np.median(vals)), 1),
                     "n_px": int(len(vals)),
                     "osm_shape": osm_shape.get(b["id"])})
    print(f"[roof] {len(rows)} buildings with >=12 interior LiDAR px")
    res = {}
    for key, label in (("slope_med", "median local slope (m/m)"),
                       ("relief", "p90-p10 relief (m)")):
        by = {}
        for r in rows:
            by.setdefault(r["cls"], []).append(r[key])
        print(f"  -- {label} --")
        print("  class         n   median   [q25, q75]")
        for cls, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
            v = np.array(v)
            print(f"  {cls:12s} {len(v):4d}   {np.median(v):6.3f}   "
                  f"[{np.percentile(v, 25):.3f}, {np.percentile(v, 75):.3f}]")
        flat = [r[key] for r in rows if r["cls"] in ("flat", "flat_plant")]
        pitched = [r[key] for r in rows if r["cls"] == "pitched"]
        nonflat = [r[key] for r in rows if r["cls"] in ("pitched", "mansard", "curved")]
        res[key] = {"auc_pitched_vs_flat": _auc(pitched, flat),
                    "auc_nonflat_vs_flat": _auc(nonflat, flat),
                    "n_flat": len(flat), "n_pitched": len(pitched),
                    "n_nonflat": len(nonflat)}
        print(f"  AUC pitched vs flat = {res[key]['auc_pitched_vs_flat']:.3f}  "
              f"(n={len(pitched)} vs {len(flat)});  any non-flat vs flat = "
              f"{res[key]['auc_nonflat_vs_flat']:.3f} (n={len(nonflat)} vs {len(flat)})")
    print("  LoD1 baseline (all flat): AUC 0.5 by construction")
    # OSM roof:shape subset
    agree = tot = 0
    conf = {}
    for r in rows:
        sh = r["osm_shape"]
        if not sh or r["cls"] in ("shell", "unknown"):
            continue
        osm_c = "flat" if sh in OSM_FLAT else ("pitched" if sh in OSM_PITCHED
                                               else ("mansard" if sh == "mansard" else None))
        if osm_c is None:
            continue
        ours = "flat" if r["cls"] in ("flat", "flat_plant") else r["cls"]
        tot += 1
        agree += int(ours == osm_c)
        conf[(osm_c, ours)] = conf.get((osm_c, ours), 0) + 1
    print(f"  OSM roof:shape agreement: {agree}/{tot}" + (f" = {agree/tot:.2f}" if tot else ""))
    for (o, u), c in sorted(conf.items()):
        print(f"    osm={o:8s} ours={u:10s} {c}")
    from img2city.agent.tokens import provenance
    outp = os.path.join(a.out, "roof_check.json")
    json.dump({"rows": rows, "auc": res,
               "osm_agree": agree, "osm_total": tot,
               "provenance": provenance(metrics=["slope_med", "relief_p90_p10"])},
              open(outp, "w"), indent=1)
    print(f"  -> {outp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--erode", type=float, default=3.0,
                    help="--roof: metres of footprint edge to discard")
    ap.add_argument("--roof", action="store_true",
                    help="validate roof FORM (flat/pitched/mansard) against LiDAR relief")
    ap.add_argument("--emin", type=float, default=None,
                    help="override tile origin (default: derived from the bbox)")
    ap.add_argument("--nmax", type=float, default=None)
    ap.add_argument("--apply", action="store_true",
                    help="write trusted LiDAR heights back into buildings.json "
                         "(guards: >=30 px, lidar >= 2.5 m -- glass roofs read "
                         "as ~0 because the laser penetrates them -- and |err| > 2 m)")
    a = ap.parse_args()
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    d0 = json.load(open(os.path.join(a.out, "buildings.json")))
    if a.emin is None or a.nmax is None:
        x0, y0, x1, y1 = _bng_window(d0["anchor"])
        a.emin = float(x0) if a.emin is None else a.emin
        a.nmax = float(y1) if a.nmax is None else a.nmax
    fetch_tiles(a.out, d0["anchor"])
    dsm = load_grid(os.path.join(a.out, "lidar", "dsm.tif"))
    dtm = load_grid(os.path.join(a.out, "lidar", "dtm.tif"))
    hgt = dsm - dtm
    H, W = hgt.shape
    d = json.load(open(os.path.join(a.out, "buildings.json")))
    anchor = d["anchor"]
    if a.roof:
        return roof_check(a, hgt, d, anchor, tr)
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    rows = []
    for b in d["buildings"]:
        bng = []
        for x, y in b["pts"]:
            lon = anchor["lon0"] + x / kx
            lat = anchor["lat0"] + y / 110540.0
            e, n = tr.transform(lon, lat)
            bng.append((e, n))
        es = [p[0] for p in bng]; ns = [p[1] for p in bng]
        vals = []
        for r in range(max(0, int(a.nmax - max(ns))), min(H, int(a.nmax - min(ns)) + 1)):
            n = a.nmax - r - 0.5
            for c in range(max(0, int(min(es) - a.emin)), min(W, int(max(es) - a.emin) + 1)):
                e = a.emin + c + 0.5
                if _point_in_poly(e, n, bng):
                    v = hgt[r, c]
                    if np.isfinite(v):
                        vals.append(v)
        if len(vals) < 8:                    # too small / nodata -> skip
            continue
        vals = np.array(vals)
        rows.append({"id": b["id"], "ours": b["height"], "src": b["height_src"],
                     "lidar_med": round(float(np.median(vals)), 1),
                     "lidar_p90": round(float(np.percentile(vals, 90)), 1),
                     "n_px": len(vals)})
    ours = np.array([r["ours"] for r in rows])
    med = np.array([r["lidar_med"] for r in rows])
    err = ours - med
    print(f"[heights] {len(rows)} buildings vs EA LiDAR 1m DSM-DTM")
    print(f"  bias (ours - lidar median): {err.mean():+.1f} m,  MAE {np.abs(err).mean():.1f} m")
    print(f"  Pearson r: {np.corrcoef(ours, med)[0, 1]:.3f}")
    within = [(np.abs(err) <= t).mean() * 100 for t in (2, 3, 5)]
    print(f"  within 2/3/5 m: {within[0]:.0f}% / {within[1]:.0f}% / {within[2]:.0f}%")
    worst = sorted(rows, key=lambda r: -abs(r["ours"] - r["lidar_med"]))[:8]
    print("  worst offenders (ours vs lidar med / p90):")
    for r in worst:
        print(f"    {r['id']}: {r['ours']} vs {r['lidar_med']} / {r['lidar_p90']} "
              f"({r['src']}, {r['n_px']} px)")
    with open(os.path.join(a.out, "height_check.json"), "w") as f:
        json.dump(rows, f, indent=1)
    print(f"  -> {a.out}/height_check.json")
    if a.apply:
        by_id = {r["id"]: r for r in rows}
        fixed = 0
        for b in d["buildings"]:
            r = by_id.get(b["id"])
            if not r or r["n_px"] < 30 or r["lidar_med"] < 2.5:
                continue
            # TOWER-ON-PODIUM guard (Canary Wharf bootstrap): when the footprint
            # holds two roof levels, the median measures the PODIUM -- applying
            # it flattened JP Morgan 153 m -> 50.6 m while p90 (152.7) matched
            # the surveyed tag. Bimodal test: p90 >> median. Then a surveyed tag
            # that agrees with p90 is the TOWER height -- keep it; a default
            # height gets p90 (the tall mass dominates the skyline, and LoD1
            # carries one height per footprint).
            med, p90 = r["lidar_med"], r["lidar_p90"]
            tgt = med
            if p90 > 1.4 * med:
                if b["height_src"].startswith("tag") and p90 * 0.85 <= b["height"] <= p90 * 1.15:
                    continue                     # tag measures the tower: trust it
                tgt = p90
            if abs(b["height"] - tgt) > 2.0:
                b["height"] = tgt
                b["height_src"] = "lidar"
                fixed += 1
        with open(os.path.join(a.out, "buildings.json"), "w") as f:
            json.dump(d, f)
        print(f"  [apply] {fixed} heights corrected to LiDAR -> buildings.json")


if __name__ == "__main__":
    main()
