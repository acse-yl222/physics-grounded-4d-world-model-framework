"""img2city/building/facade_colors.py -- photo-sampled PART COLOURS per building (the editable
appearance route, 2026-07-18 direction decision: appearance belongs on the
parametric parts as material values, not draped photo pixels; the projection-quad
branch in facade_project.py is retired from assembly and kept for comparison).

Per building the street photo is rectified onto the known facade plane (same
camera math as facade_project) and four colours are measured deterministically:

  wall    median of facade pixels outside the (dilated) detected window boxes,
          above the stucco band
  stucco  same, below the stucco band top (when the spec has stucco floors)
  frame   median over thin rings around the detected window boxes
  glaze   median inside the boxes (shrunk) -- the glazing tint

The colours are written to buildings/<id>/colors.json (linear RGB for Blender +
sRGB bytes for humans) and injected at assembly as desc["colors"] / the polygon
params' "colors" key; components.palette_alias turns them into shared per-colour
material variants, so every part remains a plain editable material. Buildings
with no usable photo (no facade facts) keep the default palette.

  python -m img2city.building.facade_colors --out data/city_sk            # all buildings, cached
  python -m img2city.building.facade_colors --out data/city_sk --force
  python -m img2city.building.facade_colors --out data/city_sk --eval     # untex vs colored, DreamSim
"""
from __future__ import annotations
import argparse
import json
import math
import os

import numpy as np
from PIL import Image

from img2city.building.facade_project import (KX, KY, _cam_basis, _front_masses, _poly_inside,
                            _rectify)

MIN_DIST = 4.0        # colours tolerate closer panos than projection did
MIN_PX = {"wall": 800, "stucco": 500, "frame": 300, "glaze": 300}


def _srgb_to_linear(c8):
    c = c8 / 255.0
    return float(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92)


def _to_linear(rgb8):
    return [round(_srgb_to_linear(v), 4) for v in rgb8]


def _median_rgb(arr, mask):
    n = int(mask.sum())
    if n == 0:
        return None, 0
    px = arr[mask]
    return [float(np.median(px[:, ch])) for ch in range(3)], n


def _boxes_to_facade(boxes, C, F, R, U, O, D, n_out, img_wh, length, height):
    """Photo-pixel boxes -> (u0,v0,u1,v1) rectangles on the facade plane."""
    n3 = np.array([n_out[0], n_out[1], 0.0])
    O3 = np.asarray(O, dtype=float)
    D3 = np.array([D[0], D[1], 0.0])
    f = img_wh[0] / 2.0
    rects = []
    for x0, y0, x1, y1 in boxes:
        us, vs = [], []
        for px_, py_ in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            d = (F + R * (px_ - img_wh[0] / 2.0) / f
                 + U * (img_wh[1] / 2.0 - py_) / f)
            den = d @ n3
            if abs(den) < 1e-6:
                break
            t = ((O3 - C) @ n3) / den
            if t <= 0:
                break
            P = C + t * d
            us.append(float((P - O3) @ D3))
            vs.append(float(P[2]))
        else:
            u0, u1 = min(us), max(us)
            v0, v1 = min(vs), max(vs)
            if (-2 < u0 and u1 < length + 2 and -1 < v0 and v1 < height + 2
                    and 0.25 <= u1 - u0 <= 4.5 and 0.35 <= v1 - v0 <= 5.0):
                rects.append((u0, v0, u1, v1))
    return rects


def _rect_mask(shape, rects, length, height, grow):
    """Boolean mask of the given facade rects grown by `grow` metres (row 0 =
    facade top, same layout as facade_project._rectify)."""
    h_px, w_px = shape
    m = np.zeros(shape, dtype=bool)
    for u0, v0, u1, v1 in rects:
        c0 = max(0, int((u0 - grow) / length * w_px))
        c1 = min(w_px, int(math.ceil((u1 + grow) / length * w_px)))
        r0 = max(0, int((height - (v1 + grow)) / height * h_px))
        r1 = min(h_px, int(math.ceil((height - (v0 - grow)) / height * h_px)))
        if c1 > c0 and r1 > r0:
            m[r0:r1, c0:c1] = True
    return m


def _facade_frame(entry, m, pscene):
    """(O, D, n_out, length, height, stuc_top) of the facade to sample, or None.
    OBB mode works in building-local coords, polygon mode in scene coords --
    mirroring facade_project.project_building."""
    desc = entry["desc"]
    tr = desc.get("terrace") or {}
    if "poly" in entry:
        pts = entry["poly"]
        fl = int(entry.get("floors", 4)); fh = float(entry.get("floor_h", 3.2))
        best = None
        n = len(pts)
        for k in range(n):
            x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % n]
            el = math.hypot(x2 - x1, y2 - y1)
            if el < 5.0:
                continue
            ang = math.atan2(y2 - y1, x2 - x1)
            mx_, my_ = (x1 + x2) / 2, (y1 + y2) / 2
            nx, ny = -math.sin(ang), math.cos(ang)
            if _poly_inside(mx_ + nx, my_ + ny, pts):
                nx, ny = -nx, -ny
            perp = (pscene[0] - mx_) * nx + (pscene[1] - my_) * ny
            if perp < MIN_DIST:
                continue
            if best is None or el > best[0]:
                if (y2 - y1) * nx - (x2 - x1) * ny > 0:
                    O = np.array([x1, y1, 0.0]); D = ((x2 - x1) / el, (y2 - y1) / el)
                else:
                    O = np.array([x2, y2, 0.0]); D = ((x1 - x2) / el, (y1 - y2) / el)
                best = (el, O, D, (nx, ny))
        if best is None:
            return None
        el, O, D, n_out = best
        stuc = max(0, min(fl, int(tr.get("stucco_floors", 1))))
        return O, D, n_out, el, fl * fh, stuc * fh, False
    fronts = _front_masses(desc)
    # BACK-FACE fallback (08-11, "bring the colours out"): 15/78 CW panos stand BEHIND
    # the front mass (front_rotation picks the front from the pano used at SPEC
    # time; colours may use a different pano or a rot flip) -- the old guard
    # just gave up and the building kept the default palette. Measure whichever
    # face the camera actually sees.
    if fronts:
        q0 = max(fronts, key=lambda f: f["len"])
        if pscene[1] > q0["y_f"] - MIN_DIST:
            fronts = []                       # front invisible -> rebuild below
    if not fronts:
        # _front_masses serves the PROJECTION path, where skipping glass masses
        # is correct -- but an all-glass tower then has no measurable facade and
        # every Canary Wharf tower fell out of the colour pipeline. Same math,
        # glass masses included (colour only; the projection contract untouched).
        L = float(desc.get("footprint", [60, 36])[0])
        W = float(desc.get("footprint", [60, 36])[1])
        N = min(100, max(1, int(desc.get("floors", 6))))
        FH = float(desc.get("floor_h", 4.3))
        infos = []
        for mss in (desc.get("masses") or [{"x": [0, 1], "y": [0, 1], "floors": N}]):
            ax, bx = mss.get("x", [0, 1]); ay, by = mss.get("y", [0, 1])
            mn = min(100, max(1, int(mss.get("floors", N))))
            mcx = -L / 2 + (ax + bx) / 2 * L; mln = max(2.0, (bx - ax) * L)
            mcy = -W / 2 + (ay + by) / 2 * W; mwd = max(2.0, (by - ay) * W)
            infos.append({"y_f": mcy - mwd / 2, "y_b": mcy + mwd / 2,
                          "x0": mcx - mln / 2, "len": mln,
                          "h": mn * FH, "floors": mn, "fh": FH})
        front = min(q["y_f"] for q in infos)
        back = max(q["y_b"] for q in infos)
        if pscene[1] <= front - MIN_DIST:              # camera sees the front
            fronts = [q for q in infos if q["y_f"] <= front + 1.0]
        elif pscene[1] >= back + MIN_DIST:             # camera sees the BACK
            q = max((q for q in infos if q["y_b"] >= back - 1.0),
                    key=lambda f: f["len"])
            tr2 = desc.get("terrace") or {}
            stuc = max(0, min(q["floors"], int(tr2.get("stucco_floors", 1))))
            return (np.array([q["x0"] + q["len"], q["y_b"], 0.0]), (-1.0, 0.0),
                    (0.0, 1.0), q["len"], q["h"], stuc * q["fh"], True)
        else:
            return None                                # camera beside the mass
    q = max(fronts, key=lambda f: f["len"])
    stuc = max(0, min(q["floors"], int(tr.get("stucco_floors", 1))))
    return (np.array([q["x0"], q["y_f"], 0.0]), (1.0, 0.0), (0.0, -1.0),
            q["len"], q["h"], stuc * q["fh"], True)


def _roof_colour(m, anchor, bdir):
    """Median roof colour over the footprint in the building's OWN satellite
    crop (Static Maps: centred on the building, zoom 19, scale 2 -> web-mercator
    metres/px known). Deterministic; the aerial's dominant surface is the ROOF,
    and the kit default is near-white regardless of what the satellite shows."""
    sat_p = os.path.join(bdir, "satellite.png")
    if not os.path.exists(sat_p):
        return None
    img = np.asarray(Image.open(sat_p).convert("RGB"), dtype=float)
    Hpx, Wpx = img.shape[:2]
    lat = m["center_latlng"][0]
    mpp = 156543.03392 * math.cos(math.radians(lat)) / (2 ** 19) / 2  # scale=2
    kx = KX * math.cos(math.radians(anchor["lat0"]))
    ccx = (m["center_latlng"][1] - anchor["lon0"]) * kx
    ccy = (m["center_latlng"][0] - anchor["lat0"]) * KY
    pts = [((q[0] - ccx) / mpp + Wpx / 2, Hpx / 2 - (q[1] - ccy) / mpp)
           for q in m["pts"]]
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    vals = []
    for py in range(max(0, int(min(ys))), min(Hpx, int(max(ys)) + 1), 2):
        for px in range(max(0, int(min(xs))), min(Wpx, int(max(xs)) + 1), 2):
            ins = False
            n = len(pts)
            for k in range(n):
                x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % n]
                if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                    ins = not ins
            if ins:
                vals.append(img[py, px])
    if len(vals) < 150:
        return None
    med = np.median(np.array(vals), axis=0)
    lin = [round(min(0.85, _srgb_to_linear(float(v)) * 1.15), 4) for v in med]
    return lin


def colors_building(entry, m, anchor, bdir, force=False):
    """-> colours dict (also cached in colors.json) or None."""
    cpath = os.path.join(bdir, "colors.json")
    if os.path.exists(cpath) and not force:
        c = json.load(open(cpath))
        return c if c else None
    from img2city.city.generate import ref_photo
    photo_p = ref_photo(bdir)             # cleaned reference when gate-accepted
    pano_p = os.path.join(bdir, "pano.json")
    ff_p = os.path.join(bdir, "facade_facts.json")
    result = None
    if all(os.path.exists(p) for p in (photo_p, pano_p, ff_p)):
        facts = json.load(open(ff_p)) or {}
        if not facts.get("_win_boxes"):
            # curtain-wall path (08-10): OWLv2 -- tuned for punched sash windows
            # -- detects NOTHING on a glass grid (Citi's facts are null), so the
            # box gate starved every tower of colour. A glass facade needs no
            # boxes: the whole skin IS the glazing; measure the facade median.
            glass = False
            try:
                _sp = json.load(open(os.path.join(bdir, "spec.json")))
                _ms = _sp.get("masses") or [{}]
                _bg = max(_ms, key=lambda mm: (mm.get("x", [0, 1])[1] - mm.get("x", [0, 1])[0])
                          * (mm.get("y", [0, 1])[1] - mm.get("y", [0, 1])[0]))
                glass = (_bg.get("facade") or _sp.get("facade")) == "glass"
            except Exception:
                pass
            # boxless fallback for EVERY facade (08-10 round 2): 42/78 CW
            # masonry buildings had zero OWLv2 boxes too. With no boxes the
            # wall median simply includes the windows -- the median is robust
            # while wall pixels dominate, and a measured-if-imperfect wall beats
            # the default palette. frame/glaze stay box-gated (they NEED rings).
            facts = {"_win_boxes": []}
            if not glass:
                facts["_boxless_masonry"] = True
        if facts is not None:
            result = _measure(entry, m, anchor, bdir, facts,
                              Image.open(photo_p).convert("RGB"),
                              json.load(open(pano_p)))
    # roof tone from the building's own satellite crop -- independent of the
    # street-photo path, so a tower whose pano failed still gets its roof right
    rc = _roof_colour(m, anchor, bdir)
    if rc:
        result = result or {}
        result["roof"] = rc
    with open(cpath, "w") as f:
        json.dump(result or {}, f, indent=1)
    return result


def _measure(entry, m, anchor, bdir, facts, photo, pano):
    kx = KX * math.cos(math.radians(anchor["lat0"]))
    pscene = ((pano[1] - anchor["lon0"]) * kx, (pano[0] - anchor["lat0"]) * KY)
    c_ll = m["center_latlng"]
    aimscene = ((c_ll[1] - anchor["lon0"]) * kx, (c_ll[0] - anchor["lat0"]) * KY)
    if "poly" in entry:
        plocal, alocal = pscene, aimscene
    else:
        cx, cy, rot = entry["cx"], entry["cy"], entry["rot"]
        cr, sr = math.cos(-rot), math.sin(-rot)

        def to_local(sx, sy):
            dx0, dy0 = sx - cx, sy - cy
            return (cr * dx0 - sr * dy0, sr * dx0 + cr * dy0)
        plocal, alocal = to_local(*pscene), to_local(*aimscene)
    frame = _facade_frame(entry, m, plocal)
    if frame is None:
        return None
    O, D, n_out, length, height, stuc_top, obb_mode = frame
    if obb_mode:
        # distance measured along the face's own OUTWARD normal -- the old
        # front-only form (O_y - pano_y) is negative for the back face and
        # silently killed every back-face measurement
        if ((plocal[0] - O[0]) * n_out[0]
                + (plocal[1] - O[1]) * n_out[1]) < MIN_DIST:
            return None
    C, F, R, U = _cam_basis(plocal, alocal)
    out, valid = _rectify(photo, C, F, R, U, O, D, length, height, 0.0)
    r_, g_, b_ = out[..., 0], out[..., 1], out[..., 2]
    sky = (b_ > r_ + 25) & (b_ > 140)
    # street trees in front of the facade painted several walls leaf-green
    # (112145361 measured (87,103,63)) -- exclude vegetation-coloured pixels
    veg = (g_ > r_ + 12) & (g_ > b_ + 12)
    sky = sky | veg
    rects = _boxes_to_facade(facts["_win_boxes"], C, F, R, U, O, D, n_out,
                             photo.size, length, height)
    vgrid = height - (np.arange(out.shape[0]) + 0.5) * (height / out.shape[0])
    vv = vgrid[:, None] * np.ones((1, out.shape[1]))
    dil = _rect_mask(out.shape[:2], rects, length, height, 0.35)
    usable = valid & ~sky
    colors, counts = {}, {}
    cw, n = _median_rgb(out, usable & ~dil & (vv > stuc_top + 0.3)
                        & (vv < height * 0.96))
    if n >= MIN_PX["wall"]:
        colors["wall"], counts["wall"] = cw, n
    if stuc_top > 0:
        cs, n = _median_rgb(out, usable & ~dil & (vv > 0.3) & (vv < stuc_top - 0.2))
        if n >= MIN_PX["stucco"]:
            colors["stucco"], counts["stucco"] = cs, n
    if rects:
        ring = _rect_mask(out.shape[:2], rects, length, height, 0.18) \
            & ~_rect_mask(out.shape[:2], rects, length, height, -0.10)
        cf, n = _median_rgb(out, usable & ring)
        if n >= MIN_PX["frame"]:
            colors["frame"], counts["frame"] = cf, n
        inner = _rect_mask(out.shape[:2], rects, length, height, -0.18)
        cg, n = _median_rgb(out, valid & inner)
        if n >= MIN_PX["glaze"]:
            colors["glaze"], counts["glaze"] = cg, n
    if "wall" not in colors:
        return None
    # frame/glaze rings land on brick when the detector boxes are loose -- a
    # trim colour that is not clearly distinct from the wall is contamination;
    # drop it and keep the default white trim (London trim is white far more
    # often than it is brick-coloured)
    for k in ("frame", "glaze"):
        if k in colors and sum(abs(a - b) for a, b in
                               zip(colors[k], colors["wall"])) < 60:
            del colors[k]
            counts.pop(k, None)
    lin = {k: [_srgb_to_linear(v) for v in colors[k]] for k in colors}
    # illumination correction: the median bakes the photo's shade into the
    # colour, and the render then shades it AGAIN (868975264's white terrace
    # measured olive-grey). If the trim is plausibly white (neutral + bright),
    # use it as the illumination reference and divide it out per channel;
    # otherwise brighten-only normalise on the 85th-percentile luminance.
    fr = colors.get("frame")
    if fr and max(fr) - min(fr) < 25 and sum(fr) / 3 > 90:
        fac = [min(3.0, max(0.4, 0.72 / max(0.02, c))) for c in lin["frame"]]
    else:
        lum = out[usable].mean(axis=-1) if usable.any() else np.array([180.0])
        p85 = _srgb_to_linear(float(np.percentile(lum, 85)))
        k85 = min(2.4, max(1.0, 0.55 / max(0.03, p85)))
        fac = [k85, k85, k85]
    # wall cap (2026-07-26): full illumination recovery is right for white trim
    # and stucco, but on DARK masonry it inflates the albedo -- photo-dark
    # London stock measured mid-grey and rendered near-white under sun+AgX
    # (the "why is the block white" question). Cap the WALL's recovery so dark
    # brick stays dark; trim/stucco/glaze keep the full correction.
    wfac = [min(f, 1.35) for f in fac]
    lin = {k: [round(min(0.92, c * ((wfac if k == "wall" else fac)[i])), 4)
               for i, c in enumerate(v)]
           for k, v in lin.items()}
    # stucco samples the ground floor, where shade/railings/planting darken the
    # median most (868975264's white terrace measured khaki) -- a stucco that is
    # near-neutral and reasonably bright is painted white stucco; snap it up
    st = lin.get("stucco")
    if st and max(st) - min(st) < 0.09 and sum(st) / 3 > 0.28:
        lin["stucco"] = [round(max(c, 0.75) , 4) for c in st]
    # stone brighten (2026-07-20, RSM): a NEUTRAL wall (Portland/limestone, low
    # saturation) measured under overcast + rendered under AgX -0.7EV reads
    # olive-dark; scale a near-neutral dark wall up to a cream target.
    # GATED BY WALL CLASS (2026-07-26): saturation alone cannot tell Portland
    # stone from LONDON STOCK BRICK -- both measure near-neutral -- and the
    # ungated brighten bleached dark terrace brick to cream (the "why is the
    # whole block white" question). Brighten only when the SPEC says the
    # building is stone.
    wl = lin.get("wall")
    wall_class = "brick"
    try:
        _sp = json.load(open(os.path.join(bdir, "spec.json")))
        _ms = _sp.get("masses") or [{}]
        _big = max(_ms, key=lambda mm: (mm.get("x", [0, 1])[1] - mm.get("x", [0, 1])[0])
                   * (mm.get("y", [0, 1])[1] - mm.get("y", [0, 1])[0]))
        wall_class = str(_big.get("wall") or _sp.get("wall") or "brick")
    except Exception:
        pass
    if (wl and wall_class == "stone"
            and max(wl) - min(wl) < 0.12 and sum(wl) / 3 < 0.5):
        s = 0.62 / max(0.05, max(wl))
        lin["wall"] = [round(min(0.92, c * s), 4) for c in wl]
    # CURTAIN-WALL tint (Canary Wharf, 08-10): a glass-facade building's whole
    # skin is the "glass" material, which is tuned bright for the black-bg judge
    # renders and reads WHITE in a city scene. Emit an explicit "glass" colour --
    # the measured glazing tint, wall sample as fallback -- ONLY for buildings
    # whose dominant mass is glass; palette_alias maps it opt-in, so every
    # existing colors.json (no "glass" key) renders byte-identically.
    try:
        _fac = str(_big.get("facade") or _sp.get("facade") or "")
    except Exception:
        _fac = ""
    if _fac == "glass":
        src = lin.get("glaze") or lin.get("wall")
        if src:
            lin["glass"] = [round(min(0.55, c), 4) for c in src]
    lin["_srgb"] = {k: [int(v) for v in colors[k]] for k in colors}
    lin["_px"] = counts
    lin["_boxes_used"] = len(rects)
    return lin


REGION_PALETTE_KEYS = ("wall", "stucco", "frame")
REGION_PALETTE_MIN_N = 12


def build_region_palette(out):
    """Derive the AREA's default palette from its own measured buildings: the
    per-channel median over every colors.json that carries that channel. No
    hand-picked values -- an area with too few measurements (< REGION_PALETTE_MIN_N)
    gets no palette file and keeps the kit defaults. Written to
    <out>/region_palette.json; colors_for() fills only a building's MISSING
    channels from it, so measured values always win."""
    import glob as _glob
    import statistics as _st
    vals = {k: [] for k in REGION_PALETTE_KEYS}
    for p in _glob.glob(os.path.join(out, "buildings", "*", "colors.json")):
        try:
            c = json.load(open(p))
        except Exception:
            continue
        for k in REGION_PALETTE_KEYS:
            v = c.get(k)
            if v and len(v) >= 3:
                vals[k].append(v[:3])
    pal = {k: [round(_st.median(v[i] for v in vs), 4) for i in range(3)]
           for k, vs in vals.items() if len(vs) >= REGION_PALETTE_MIN_N}
    pp = os.path.join(out, "region_palette.json")
    if not pal:
        if os.path.exists(pp):
            os.remove(pp)
        print("[colors] region palette: too few measured buildings, none written")
        return None
    pal["_n"] = {k: len(vs) for k, vs in vals.items() if len(vs) >= REGION_PALETTE_MIN_N}
    pal["_src"] = "median of this area's photo-measured buildings"
    with open(pp, "w") as f:
        json.dump(pal, f, indent=1)
    print(f"[colors] region palette -> {pp} " +
          " ".join(f"{k}(n={pal['_n'][k]})" for k in pal["_n"]))
    return pal


def colors_for(out, osmid):
    """Cached colours for one building (assembly-time lookup, no compute).
    Channels the building's own measurement lacks fall back to the area's
    region_palette.json (itself the median of the area's measured buildings);
    an area without that file behaves exactly as before."""
    p = os.path.join(out, "buildings", str(osmid), "colors.json")
    c = json.load(open(p)) if os.path.exists(p) else {}
    pp = os.path.join(out, "region_palette.json")
    if os.path.exists(pp):
        try:
            pal = json.load(open(pp))
            filled = [k for k in REGION_PALETTE_KEYS
                      if not c.get(k) and pal.get(k)]
            for k in filled:
                c[k] = pal[k]
            if filled:
                c["_region_default"] = filled
        except Exception:
            pass
    # roof/glass are self-sufficient channels (satellite roof tone lands even
    # when the street-photo path failed) -- any measured key is worth injecting
    return c if c and (c.get("wall") or c.get("roof") or c.get("glass")) else None


def run_all(out, force=False, ids=None):
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas = {mm["id"]: mm for mm in d["buildings"]}
    anchor = d["anchor"]
    placements = json.load(open(os.path.join(out, "agent_placements.json")))
    done = skipped = 0
    for entry in placements:
        if ids and str(entry["id"]) not in ids:
            continue
        m = metas.get(entry["id"])
        if m is None:
            continue
        bdir = os.path.join(out, "buildings", str(entry["id"]))
        c = colors_building(entry, m, anchor, bdir, force)
        if c:
            done += 1
            print(f"[{entry['id']}] " + "  ".join(
                f"{k}:{tuple(c['_srgb'][k])}" for k in ("wall", "stucco", "frame",
                                                        "glaze") if k in c))
        else:
            skipped += 1
    print(f"[colors] {done} buildings coloured, {skipped} on the default palette")


def _eval(out, ids=None):
    """Untextured default palette vs photo-coloured parts, DreamSim vs the
    street photo, from the same pano camera. Zero-LLM. Writes colors_eval.json."""
    from img2city.building.generate import (_send, RENDER_OUT, RENDER_CAM, CLEAR, LIGHT_STREET,
                          spec_to_code)
    from img2city.city.generate import (PANO_RENDER, CAM_GATE, POLY_BUILD, poly_params,
                               load_components_src, obb)
    from img2city.judge.perceptual import dreamsim_dist
    out = os.path.abspath(out)
    d = json.load(open(os.path.join(out, "buildings.json")))
    bmetas, anchor = d["buildings"], d["anchor"]
    placements = {e["id"]: e for e in
                  json.load(open(os.path.join(out, "agent_placements.json")))}
    if ids is None:
        ids = json.load(open(os.path.join(out, "eval_subset.json")))
    comp = load_components_src()
    kx = KX * math.cos(math.radians(anchor["lat0"]))
    rows = []
    for sid in ids:
        osmid = int(sid)
        m = next((mm for mm in bmetas if mm["id"] == osmid), None)
        entry = placements.get(osmid)
        bdir = os.path.join(out, "buildings", str(osmid))
        from img2city.city.generate import ref_photo
        photo = ref_photo(bdir)           # cleaned reference when gate-accepted
        pano_p = os.path.join(bdir, "pano.json")
        if not (m and entry and os.path.exists(photo) and os.path.exists(pano_p)):
            continue
        m["obb"] = obb(m["pts"])
        spec = json.load(open(os.path.join(bdir, "spec.json")))
        colors = colors_building(entry, m, anchor, bdir)
        pano = tuple(json.load(open(pano_p)))
        rot = entry["rot"]
        cx, cy = m["obb"][0], m["obb"][1]
        dx = (pano[1] - anchor["lon0"]) * kx - cx
        dy = (pano[0] - anchor["lat0"]) * KY - cy
        lx = math.cos(-rot) * dx - math.sin(-rot) * dy
        ly = math.sin(-rot) * dx + math.cos(-rot) * dy
        dist = math.hypot(lx, ly)
        L, W = m["obb"][2], m["obb"][3]
        poly_mode = "poly" in entry
        _hs = max(int(mm.get("floors", spec.get("floors", 4))) for mm in
                  (spec.get("masses") or [{}])) * float(spec.get("floor_h", 3.2))
        stand = max(12.0, 1.1 * _hs)
        if not poly_mode and (ly > -(W / 2 + 4.0) or dist < 8.0):
            lx = max(-L / 2, min(L / 2, lx))
            ly = -(W / 2 + stand)
        zt = min(_hs * 0.55, 2.5 + 0.32 * dist)
        if poly_mode:
            xs = [q2[0] for q2 in m["pts"]]; ys = [q2[1] for q2 in m["pts"]]
            scale = 1.25 * max(max(xs) - min(xs), max(ys) - min(ys))
            cam = (PANO_RENDER % (cx, cy, zt, cx + dx, cy + dy)) + RENDER_CAM \
                + (CAM_GATE % min(20.0, scale / 5.0)) + LIGHT_STREET
        else:
            cam = (PANO_RENDER % (0, 0, zt, lx, ly)) + RENDER_CAM \
                + (CAM_GATE % (L / 4.0)) + LIGHT_STREET
        row = {"id": osmid, "has_colors": bool(colors)}
        for name, cset in (("untex", None), ("colored", colors)):
            if name == "colored" and not cset:
                row[name] = None       # default palette -> identical to untex
                continue
            png = os.path.join(bdir, "textures", f"ceval_{name}.png")
            if poly_mode:
                pparams = poly_params(spec, pts=m["pts"])
                if cset:
                    pparams["colors"] = cset
                head = CLEAR + "\n" + comp + "\n" + (POLY_BUILD % json.dumps(pparams))
            else:
                sp = {**spec, "colors": cset} if cset else spec
                head = CLEAR + "\n" + spec_to_code(json.dumps(sp), comp)
            _res, err = _send(head + "\n" + cam + (RENDER_OUT % png), timeout=600)
            if err:
                print(f"[{osmid}] {name} render failed: {err[:80]}")
                row[name] = None
                continue
            row[name] = dreamsim_dist(png, photo)
        rows.append(row)
        print(f"[{osmid}] ds untex {row.get('untex')} colored {row.get('colored')} "
              f"({'photo palette' if colors else 'default'})")
    have = [r for r in rows
            if r.get("untex") is not None and r.get("colored") is not None]
    if have:
        mu = sum(r["untex"] for r in have) / len(have)
        mc = sum(r["colored"] for r in have) / len(have)
        closer = sum(1 for r in have if r["colored"] < r["untex"])
        print(f"\n[colors-eval] {len(have)} buildings: DreamSim untex {mu:.4f} | "
              f"photo-coloured {mc:.4f} ({closer}/{len(have)} closer)")
    with open(os.path.join(out, "colors_eval.json"), "w") as f:
        json.dump(rows, f, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--eval", action="store_true")
    a = ap.parse_args()
    if a.eval:
        _eval(a.out, a.ids)
    else:
        run_all(a.out, a.force, set(a.ids) if a.ids else None)
        build_region_palette(a.out)


if __name__ == "__main__":
    main()
