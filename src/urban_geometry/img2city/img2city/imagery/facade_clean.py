"""img2city/imagery/facade_clean.py -- clean building references: pick the best street view, then
strip the environment (trees, cars, street furniture) from the photo so the
judge/BRIEF/colours see the BUILDING, not its occluders.

Why (2026-07-19 direction decision): single-building fidelity is capped by input
imagery -- RSM's photo is a tree + lamp post + car with the stone front barely
visible; the whole judge loop optimises against pixels that are not building.
The Queen's Tower / Business School results were good precisely because their
references were hand-picked clean shots. This module automates that.

Three stages per building (each cached, each skippable):

1. VIEW SELECT (`--select`): ring of Street View panos scaled to the footprint
   (reuses acquire_view.ring_panos + Claude vision judging); the best-scoring
   candidate that actually shows the building replaces streetview.png (original
   archived as streetview_orig.png, pano.json updated so the pano-matched
   camera stays honest).
2. CLEAN (`--clean`): Gemini image edit removes vegetation/vehicles/furniture
   and completes occluded facade, writing streetview_clean.png. NEVER
   overwrites the real photo. Requires GEMINI_API_KEY with credits.
3. HALLUCINATION GATE (built into --clean): the cleaned image is only ACCEPTED
   (clean_meta.json {"accepted": true}) if (a) OWLv2 facade facts on the
   cleaned photo agree with the original where the original was readable
   (row count within 1, typical windows per row within 2), and (b) the
   vegetation+vehicle pixel fraction actually dropped. An edit that invents
   storeys or windows fails (a); an edit that did nothing fails (b).

Downstream: city_generate.ref_photo(bdir) returns streetview_clean.png only
when accepted, so refine/BRIEF/colours all inherit the clean reference.

  python -m img2city.imagery.facade_clean --out data/city_icl --select --ids 110085215
  python -m img2city.imagery.facade_clean --out data/city_icl --clean  --ids 110085215
"""
from __future__ import annotations

from img2city import config
from img2city.agent import llm
import argparse
import json
import math
import os
import shutil

CLEAN_PROMPT = (
    "Edit this street-level photo. REMOVE every tree, bush, car, van, bus, "
    "bicycle, person, lamp post, sign post, wire and street furniture that "
    "stands in front of the building, and plausibly complete the parts of the "
    "facade they covered. KEEP the building itself EXACTLY as photographed: "
    "same number of storeys, same windows in the same positions, same "
    "materials, same EXACT facade colours, same perspective and framing. "
    "Reproduce any signage or lettering on the building LETTER FOR LETTER "
    "where legible; where letters are hidden behind an occluder, keep them "
    "plausible and consistent with the visible ones. Do not add any feature "
    "that is not visible in the photo. Keep the sky and road simple and "
    "neutral. Output the edited photo only.")


def _edit_openai_image(photo, outp, model, prompt=None, ref=None, quality="medium"):
    """OpenAI image-edit endpoint (gpt-image-2 was the 2026-07 leaderboard #1
    for image editing; the Gemini free tier has zero image-model quota). `ref`:
    optional second input image -- an already-cleaned view of the SAME building
    from another angle, passed as material/colour evidence (dense occlusion
    leaves the model free to invent a facade; a clean sibling view pins it).
    quality=medium by default: ~half the cost of high (~$0.10 vs $0.20/image)
    and the medium tier tops the LMArena editing board in its own right."""
    import base64
    import requests
    files = [("image[]", (os.path.basename(photo), open(photo, "rb"), "image/png"))]
    if ref:
        files.append(("image[]", (os.path.basename(ref), open(ref, "rb"), "image/png")))
    try:
        r = requests.post(
            config.OPENAI_BASE_URL + "/images/edits",
            headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
            files=files,
            data={"model": model, "prompt": prompt or CLEAN_PROMPT,
                  "quality": quality, "size": "1024x1024"},
            timeout=300)
    finally:
        for _, (_, fh, _) in files:
            fh.close()
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"].get("message", "?")[:150])
    with open(outp, "wb") as f:
        f.write(base64.b64decode(j["data"][0]["b64_json"]))


def _veg_vehicle_frac(path):
    """Vegetation-hue + saturated-vehicle-colour pixel fraction (coarse,
    deterministic -- used only as a 'did the edit remove anything' signal)."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    veg = (g > r + 12) & (g > b + 12)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    vivid = (mx - mn > 90) & ~veg          # saturated paint (cars, awnings)
    return float((veg | vivid).mean())


# ------------------------------------------------------------------ stage 1

def _blocked_frac(pxy, tgt_pts, others):
    """Fraction of the target footprint's corners whose sightline from the pano
    is blocked by ANOTHER building's footprint (deterministic neighbour-building
    gate, 2026-07-20: a vision judge shown a grand facade and told the target's
    name scored 0.92 on a photo of the two buildings IN FRONT of the target).
    A crossing only counts as a blocker before 90% of the way to the corner, so
    an attached neighbour sharing the target's own wall does not false-flag."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    def hit_t(p1, p2, a, b):
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (b[0] - a[0], b[1] - a[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:
            return None
        t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
        u = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
        return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None

    # only judge corners the pano could actually SEE: a corner self-occluded by
    # the target's OWN mass (a back corner behind the building) is invisible
    # regardless of neighbours, so counting it as "blocked" wrongly rejects a
    # perfectly good face-on FRONT pano just because the building's back corners
    # sit near other campus buildings (2026-07-20: this bug hid RSM's real
    # entrance front for a whole session -- the fix this pass was built for).
    nt = len(tgt_pts)

    def _self_occluded(q, qi):
        for k in range(nt):
            a, b = tgt_pts[k], tgt_pts[(k + 1) % nt]
            if k == qi or (k + 1) % nt == qi:      # edges touching this corner
                continue
            tt = hit_t(pxy, q, a, b)
            if tt is not None and tt < 0.98:
                return True
        return False

    visible, blocked = 0, 0
    for qi, q in enumerate(tgt_pts):
        if _self_occluded(q, qi):
            continue
        visible += 1
        for pts in others:
            n = len(pts)
            if any((t := hit_t(pxy, q, pts[k], pts[(k + 1) % n])) is not None
                   and t < 0.9 for k in range(n)):
                blocked += 1
                break
    return blocked / max(1, visible)


def _framing(m, anchor_ll, plat, plng):
    """Deterministic framing for one pano: aim heading at the building's angular
    CENTROID (all footprint corners, not the centre point), fov sized to fit the
    whole building, plus how many facades are visible (corner 3/4 views see 2).
    Returns (heading, fov, spread_deg, n_faces)."""
    lat0, lng0 = anchor_ll
    kx = 111320.0 * math.cos(math.radians(lat0))
    px = (plng - lng0) * kx
    py = (plat - lat0) * 110540.0
    brs = []
    for qx, qy in m["pts"]:
        brs.append(math.degrees(math.atan2(qx - px, qy - py)) % 360)
    # circular span: rotate so the gap is behind the camera
    brs.sort()
    gaps = [(brs[(k + 1) % len(brs)] - brs[k]) % 360 for k in range(len(brs))]
    kmax = max(range(len(gaps)), key=lambda k: gaps[k])
    lo = brs[(kmax + 1) % len(brs)]
    spread = (360 - gaps[kmax]) % 360
    heading = (lo + spread / 2) % 360
    fov = min(120.0, max(65.0, spread * 1.15 + 8))
    # visible facades: outward-normal test per long edge
    n_faces = 0
    pts = m["pts"]
    for k in range(len(pts)):
        x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % len(pts)]
        if math.hypot(x2 - x1, y2 - y1) < 8.0:
            continue
        ang = math.atan2(y2 - y1, x2 - x1)
        nx, ny = -math.sin(ang), math.cos(ang)
        mx_, my_ = (x1 + x2) / 2, (y1 + y2) / 2
        # outward = away from footprint interior
        cx_ = sum(q[0] for q in pts) / len(pts)
        cy_ = sum(q[1] for q in pts) / len(pts)
        if (mx_ - cx_) * nx + (my_ - cy_) * ny < 0:
            nx, ny = -nx, -ny
        if (px - mx_) * nx + (py - my_) * ny > 3.0:
            n_faces += 1
    return heading, fov, spread, n_faces


def select_view(out, osmid, backend=None, model=config.VISION_MODEL, n=10,
                sub="", min_sep=0.0):
    """Ring candidates scaled to the footprint; framing computed per pano (aim +
    fov fitted to the WHOLE footprint, corner views preferred); Claude picks the
    best shot that actually shows the building. Returns (changed, best_score).

    sub/min_sep (multi-view, 2026-07-20): with sub="view2" the selected view is
    written to <bdir>/view2/ (same file names, so gate_clean/ref_photo work on
    that directory unchanged) and candidates whose bearing from the building
    centre lies within min_sep degrees of the PRIMARY pano's bearing are skipped
    -- the second view must actually see a different side of the building."""
    from img2city.imagery.acquire_view import ring_panos, judge
    from img2city.imagery.maps_fetch import _key, _get, STREETVIEW
    d = json.load(open(os.path.join(out, "buildings.json")))
    anchor = d["anchor"]
    m = next(mm for mm in d["buildings"] if mm["id"] == osmid)
    bdir = os.path.join(out, "buildings", str(osmid))
    primary = bdir
    if sub:
        bdir = os.path.join(bdir, sub)
    os.makedirs(bdir, exist_ok=True)
    lat, lng = m["center_latlng"]
    b0 = None
    if min_sep:
        pp = os.path.join(primary, "pano.json")
        if os.path.exists(pp):
            p0 = json.load(open(pp))
            b0 = math.degrees(math.atan2(
                (p0[1] - lng) * math.cos(math.radians(lat)), p0[0] - lat)) % 360
    xs = [q[0] for q in m["pts"]]; ys = [q[1] for q in m["pts"]]
    # int: the Street View metadata API 400s on a float radius
    radius = int(max(45.0, max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 25))
    name = m.get("name") or f"the building at {lat:.5f},{lng:.5f}"
    key = _key()
    panos = ring_panos(lat, lng, radius, n, key)
    if not panos:
        print(f"[{osmid}] no panos on ring r={radius:.0f}")
        return False, 0.0
    cdir = os.path.join(bdir, "view_candidates")
    os.makedirs(cdir, exist_ok=True)
    others = [mm["pts"] for mm in d["buildings"]
              if mm["id"] != osmid and mm["area_m2"] >= 300]
    kx0 = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    best = None
    for j, (plat, plng) in enumerate(panos[:n]):
        if b0 is not None:
            b = math.degrees(math.atan2(
                (plng - lng) * math.cos(math.radians(lat)), plat - lat)) % 360
            if abs((b - b0 + 180) % 360 - 180) < min_sep:
                continue
        pxy = ((plng - anchor["lon0"]) * kx0, (plat - anchor["lat0"]) * 110540.0)
        bf = _blocked_frac(pxy, m["pts"], others)
        if bf > 0.6:
            print(f"[{osmid}] cand {j}: skipped -- {bf:.0%} of sightlines "
                  "blocked by other buildings")
            continue
        heading, fov, spread, n_faces = _framing(
            m, (anchor["lat0"], anchor["lon0"]), plat, plng)
        p = os.path.join(cdir, f"cand_{j:02d}.png")
        _get(STREETVIEW, {"location": f"{plat},{plng}", "size": "640x640",
                          "heading": round(heading, 1), "pitch": 16,
                          "fov": round(fov), "source": "outdoor", "key": key}, p)
        vis, score, note = judge(p, name, backend, model)
        dist = math.hypot((plat - lat) * 110540.0,
                          (plng - lng) * 111320.0 * math.cos(math.radians(lat)))
        # prefer: visible, corner views (2+ faces), whole building fits
        # (spread within the fov cap), not worm's-eye close
        eff = score * (0.6 if dist < 18 else 1.0) \
            * (1.15 if n_faces >= 2 else 1.0) \
            * (0.75 if spread * 1.15 + 8 > 120 else 1.0)
        print(f"[{osmid}] cand {j}: visible={vis} score={score:.2f} "
              f"faces={n_faces} spread={spread:.0f} fov={fov:.0f} "
              f"dist={dist:.0f}m  {note[:40]}")
        if vis and (best is None or eff > best[0]):
            best = (eff, p, (plat, plng), (heading, fov))
    if best is None:
        print(f"[{osmid}] no candidate shows the building -- keeping current view")
        return False, 0.0
    _, bp, pano, hf = best
    cur = os.path.join(bdir, "streetview.png")
    if os.path.exists(cur) and not os.path.exists(os.path.join(bdir, "streetview_orig.png")):
        shutil.copy(cur, os.path.join(bdir, "streetview_orig.png"))
    shutil.copy(bp, cur)
    # extended pano record: [lat, lng, heading, fov, pitch] -- the render camera
    # must reproduce the photo's OWN fov/pitch or the comparison punishes
    # framing, not the model (fov-90 render vs fov-120 photo shrank the
    # building to a horizontal strip). 2-element consumers keep working.
    with open(os.path.join(bdir, "pano.json"), "w") as f:
        json.dump(list(pano) + [round(hf[0], 1), round(hf[1]), 16], f)
    # stale derived data must not survive a reference change
    for stale in ("facade_facts.json", "colors.json", "streetview_clean.png",
                  "clean_meta.json"):
        sp = os.path.join(bdir, stale)
        if os.path.exists(sp):
            os.remove(sp)
    print(f"[{osmid}] view replaced (score {best[0]:.2f}); facts/colors caches cleared")
    return True, best[0]


# ------------------------------------------------------------------ stage 2+3

def _building_name(bdir):
    """Best-effort building name from the area's buildings.json (bdir is
    <out>/buildings/<id>[/view2])."""
    try:
        d = os.path.abspath(bdir)
        while d and os.path.basename(os.path.dirname(d)) != "buildings":
            nd = os.path.dirname(d)
            if nd == d:
                return None
            d = nd
        osmid = int(os.path.basename(d))
        out = os.path.dirname(os.path.dirname(d))
        meta = json.load(open(os.path.join(out, "buildings.json")))
        m = next(mm for mm in meta["buildings"] if mm["id"] == osmid)
        return m.get("name")
    except Exception:
        return None


def _vlm_consistency(photo, outp, backend=None, model=config.VISION_MODEL,
                     name=None):
    """Claude-vision structural consistency check, used when OWLv2 cannot read
    the facade (e.g. modernist ribbon glazing has no discrete 'windows' to
    detect). Compares the BUILDING in original vs edit: storeys, fenestration
    rhythm, materials, roofline, signage text. Returns (ok, note)."""
    system = ("You verify an AI-edited photo against its original. "
              "Reply ONLY with JSON.")
    known = (f' The building is known to be named "{name}" -- flag signage '
             "text that contradicts that name." if name else "")
    user = ("Image 1 is the ORIGINAL street photo (building partly occluded by "
            "trees/vehicles/furniture). Image 2 is an AI edit that should ONLY "
            "remove the occluders and plausibly complete the hidden facade. "
            "Compare THE BUILDING between the images: storey count, window "
            "pattern and rhythm, materials and colours, roofline, and any "
            "signage text legible in the original (letter for letter)." + known +
            " Ignore sky, road, people and framing differences. Reply ONLY: "
            '{"consistent": true|false, "discrepancies": ["<short>", ...]}')
    txt, _, _ = llm.vision_call(system, user, [photo, outp], model, backend=backend)
    import re
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return False, "vlm reply unparseable"
    try:
        j = json.loads(m.group(0))
    except Exception:
        return False, "vlm reply unparseable"
    disc = "; ".join(str(x) for x in j.get("discrepancies", []))[:200]
    return bool(j.get("consistent")), disc or "consistent"


def gate_clean(bdir, meta=None, backend=None, model=config.VISION_MODEL):
    """Hallucination gate on an EXISTING streetview_clean.png. Deterministic
    where possible: occluder fraction must drop (only judged when the original
    HAS measurable occluder pixels -- bare winter trees are invisible to the
    vegetation-hue detector), and the OWLv2 window grid must agree with the
    original where BOTH photos are readable. When OWLv2 is blind on either
    side (modernist ribbon glazing has no discrete windows), falls back to a
    Claude-vision structural consistency check. Writes clean_meta.json."""
    meta_p = os.path.join(bdir, "clean_meta.json")
    photo = os.path.join(bdir, "streetview.png")
    outp = os.path.join(bdir, "streetview_clean.png")
    meta = dict(meta or {})
    meta["accepted"] = False
    if not os.path.exists(photo) or not os.path.exists(outp):
        meta["why"] = "missing streetview.png or streetview_clean.png"
    else:
        f0, f1 = _veg_vehicle_frac(photo), _veg_vehicle_frac(outp)
        meta["occluder_frac"] = [round(f0, 3), round(f1, 3)]
        from img2city.imagery.facade_facts import facts
        fo, fc = facts(photo), facts(outp)
        meta["facts_orig"] = bool(fo)
        meta["facts_clean"] = bool(fc)
        why = None
        if f0 >= 0.03 and f1 > f0 - 0.01:
            why = f"occluders not reduced ({f0:.2f}->{f1:.2f})"
        elif fo is not None and fc is not None:
            if (abs(fo["visible_window_rows"] - fc["visible_window_rows"]) > 1
                    or abs(fo["typical_windows_per_row"]
                           - fc["typical_windows_per_row"]) > 2):
                # OWLv2 window counts are unstable on ORNATE facades (RSM's
                # entrance front: 12 vs 6-7 per row on a faithful edit) -- don't
                # hard-reject on the count alone; let the VLM adjudicate structure.
                ok, note = _vlm_consistency(photo, outp, backend, model,
                                            name=_building_name(bdir))
                meta["vlm_check"] = note
                if not ok:
                    why = ("window grid changed: rows "
                           f"{fo['visible_window_rows']}->{fc['visible_window_rows']}, "
                           f"typical {fo['typical_windows_per_row']}->"
                           f"{fc['typical_windows_per_row']}; vlm: " + note)
            else:
                meta["rows"] = [fo["visible_window_rows"],
                                fc["visible_window_rows"]]
        else:
            ok, note = _vlm_consistency(photo, outp, backend, model,
                                        name=_building_name(bdir))
            meta["vlm_check"] = note
            if not ok:
                why = "vlm: " + note
        if why:
            meta["why"] = why
        else:
            meta["accepted"] = True
    with open(meta_p, "w") as f:
        json.dump(meta, f, indent=1)
    tag = "ACCEPTED" if meta["accepted"] else f"rejected ({meta.get('why', '?')[:60]})"
    print(f"[{os.path.basename(bdir)}] gate {tag}")
    return meta


REF_NOTE = ("\nThe SECOND input image shows the SAME building photographed from "
            "a different angle with occluders already removed -- use it ONLY as "
            "evidence of the building's true materials, colours, storey count "
            "and window pattern. The output must keep the FIRST image's "
            "viewpoint and framing.")


def _edit_gemini_image(photo, outp, model, prompt):
    """Gemini image-to-image edit via google-genai (reads GEMINI_API_KEY)."""
    from google import genai
    from PIL import Image
    client = genai.Client()
    with Image.open(photo) as img:
        r = client.models.generate_content(model=model, contents=[prompt, img])
    blob = None
    for part in r.candidates[0].content.parts:
        data = getattr(getattr(part, "inline_data", None), "data", None)
        if data:
            blob = data
            break
    if not blob:
        raise RuntimeError("no image in response")
    with open(outp, "wb") as f:
        f.write(blob)


def _edit_once(photo, outp, prompt, ref=None):
    """One edit attempt over ``config.IMAGE_EDIT_MODELS`` (``<provider>:<model>``
    entries, tried in order; entries whose key is missing are skipped).
    Returns the model name that produced the edit; raises on total failure."""
    last = None
    if ref:
        prompt = prompt + REF_NOTE
    for entry in config.IMAGE_EDIT_MODELS:
        provider, _, model = entry.partition(":")
        if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            try:
                _edit_openai_image(photo, outp, model, prompt=prompt, ref=ref)
                return model
            except Exception as e:                 # noqa: BLE001 -- next model
                last = e
        elif provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
            try:
                _edit_gemini_image(photo, outp, model, prompt)
                return model
            except Exception as e:                 # noqa: BLE001 -- next model
                last = e
        elif provider not in ("openai", "gemini"):
            raise ValueError(f"IMG2CITY_IMAGE_EDIT_MODELS entry {entry!r}: provider must be openai or gemini")
    raise last or RuntimeError("no usable image-edit model: set OPENAI_API_KEY and/or "
                               "GEMINI_API_KEY (see IMG2CITY_IMAGE_EDIT_MODELS)")


def clean_photo(bdir, force=False, retries=2):
    """Occluder-removal edit + hallucination gate, with gate-feedback retries:
    a rejected edit is re-attempted with the gate's discrepancy list appended
    to the prompt (same philosophy as the refine loop -- the check that fails
    becomes the fix instruction). When cleaning a secondary view (view2/), an
    ACCEPTED clean of the primary view is passed as a reference image so dense
    occlusion cannot make the model invent a different facade. Returns
    clean_meta dict."""
    meta_p = os.path.join(bdir, "clean_meta.json")
    if os.path.exists(meta_p) and not force:
        return json.load(open(meta_p))
    photo = os.path.join(bdir, "streetview.png")
    outp = os.path.join(bdir, "streetview_clean.png")
    ref = None
    parent = os.path.dirname(os.path.abspath(bdir))
    # a secondary view lives INSIDE a building dir (…/buildings/<id>/view2);
    # for a primary view the parent is the …/buildings container itself
    if os.path.basename(parent) != "buildings":
        pmeta = os.path.join(parent, "clean_meta.json")
        pclean = os.path.join(parent, "streetview_clean.png")
        try:
            if os.path.exists(pclean) and json.load(open(pmeta)).get("accepted"):
                ref = pclean
        except Exception:
            pass
    meta = {"accepted": False}
    if not os.path.exists(photo):
        meta["why"] = "no photo"
    else:
        prompt = CLEAN_PROMPT
        for attempt in range(retries + 1):
            try:
                mdl = _edit_once(photo, outp, prompt, ref=ref)
            except Exception as e:
                meta["why"] = str(e)[:160]
                break
            meta = gate_clean(bdir, {"model": mdl, "attempt": attempt,
                                     "ref_view": bool(ref)})
            if meta["accepted"]:
                return meta
            prompt = (CLEAN_PROMPT +
                      "\nIMPORTANT -- a previous edit of this photo was rejected "
                      "for deviating from the original in these ways: " +
                      meta.get("why", "?") +
                      ". Avoid exactly those deviations this time.")
    with open(meta_p, "w") as f:
        json.dump(meta, f, indent=1)
    tag = "ACCEPTED" if meta["accepted"] else f"rejected ({meta.get('why', '?')[:60]})"
    print(f"[{os.path.basename(bdir)}] clean {tag}")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--ids", nargs="*", help="osmids (default: none -- be explicit)")
    ap.add_argument("--select", action="store_true", help="stage 1: pick best view")
    ap.add_argument("--clean", action="store_true", help="stage 2+3: Gemini clean + gate")
    ap.add_argument("--gate-only", action="store_true",
                    help="run the hallucination gate on an existing "
                         "streetview_clean.png (manual/AI-Studio route, no API)")
    ap.add_argument("--second", action="store_true",
                    help="operate on the SECOND viewpoint (<bdir>/view2/): "
                         "--select picks a view >=70 deg from the primary pano")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retries", type=int, default=1,
                    help="gate-feedback re-edits per view (each retry is a "
                         "paid image call; 1 keeps a failed view at 2 images)")
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--model", default=config.VISION_MODEL)
    a = ap.parse_args()
    if not a.ids:
        raise SystemExit("pass --ids explicitly (view selection costs vision calls)")
    sub = "view2" if a.second else ""
    for sid in a.ids:
        bdir = os.path.join(os.path.abspath(a.out), "buildings", sid, sub)
        if a.select:
            select_view(os.path.abspath(a.out), int(sid), a.backend, a.model,
                        sub=sub, min_sep=70.0 if a.second else 0.0)
        if a.clean:
            clean_photo(bdir, force=a.force, retries=a.retries)
        if a.gate_only:
            gate_clean(bdir)


if __name__ == "__main__":
    main()
