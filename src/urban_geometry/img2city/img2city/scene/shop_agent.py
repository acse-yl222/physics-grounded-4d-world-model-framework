"""img2city/scene/shop_agent.py -- the STREET-VIEW pass over the shop layer.

scene/shops.py gives every unit a typed parameter vector, but the appearance
half of it (fascia colour, awning, glazing proportion) is a CATEGORY DEFAULT at
confidence 0.30 -- a plausible London palette, not this shop. This module goes
and looks: one Street View frame aimed straight at each frontage, an agent reads
the shopfronts it can see, and the values it reports are written back with
`src: "streetview"` and confidence 0.80, the prior kept alongside.

This is plan item 10 ("street view as a second identity signal") applied to the
ground floor, and it obeys the refine rule the building loop already follows:
observed values overwrite guesses, never the other way round. `sign_text` stays
on Places -- the agent tunes appearance, it does not rename businesses (a
misread fascia would invent a shop).

One photo per UNIT, not per frontage: a South Kensington street is narrow, so a
camera 13 m out with a 70 deg field of view frames a SINGLE shopfront -- the
first cut asked about a whole eleven-unit parade against a photo showing one
shop, and the agent rightly answered "not visible" to all of it. Aimed at one
unit, the target shop sits in the middle of the frame and the ordering question
disappears.

The agent also reports whether the fascia lettering MATCHES the business we
expect there. That is an independent check on the deterministic POI-to-wall
assignment -- a mismatch is recorded (`name_check`), never acted on by renaming,
because the photo is a 2024 snapshot and tenants change.

  python -m img2city.scene.shop_agent --out data/city_sk                 # all named frontages
  python -m img2city.scene.shop_agent --out data/city_sk --limit 5       # try a few first
  python -m img2city.scene.shop_agent --out data/city_sk --workers 6
"""
from __future__ import annotations

from img2city import config
import argparse
import concurrent.futures as cf
import json
import math
import os
import re
import threading

from img2city.imagery import maps_fetch
from img2city.agent import llm

STANDOFF = 13.0          # m out from the frontage the virtual camera stands
PANO_RADIUS = 30         # m; MUST be an int -- the Street View metadata
                         # endpoint 400s on "radius=30.0"
FOV = 70.0

SYSTEM = (
    "You are reading a Google Street View photograph of a London shop parade to "
    "recover the APPEARANCE PARAMETERS of each shopfront. You report only what is "
    "visible in the photograph. You never invent a shop that is not there and you "
    "never rename one. Reply with JSON only."
)

ASK = """This photo looks at one shopfront on a London street.

The model expects this unit here:
  name:     {name}
  type:     {cat}
  frontage: about {w:.1f} m wide

Read the shopfront in the MIDDLE of the frame and reply with this JSON and
nothing else:

{{"visible": true,
  "name_on_fascia": "AMATHUS",   // the lettering you can actually read, or null
  "name_matches": true,          // does it plausibly match the expected name?
  "fascia_hex": "#2b2f31",       // signboard / frontage paint, sRGB hex
  "sign_hex": "#e8e2d4",         // the lettering colour
  "awning": false,               // is a projecting awning or canopy out?
  "awning_hex": null,            // its colour if there is one
  "stall_h": 0.35,               // solid plinth under the glass, metres (0 if glass meets the pavement)
  "glaz_frac": 0.72,             // fraction of the ground-storey height that is clear glazing
  "note": "charcoal painted timber shopfront, white lettering"
}}

Rules:
- If the middle of the frame is not a shopfront, or it is hidden behind a tree,
  van or scaffold, set "visible": false and leave the rest null. That is a normal
  answer, not a failure.
- Sample colours from the SHOPFRONT ITSELF, never the brickwork above or the
  pavement. Give the paint as it reads; prefer a deep desaturated value.
- Report "name_matches": false if the fascia clearly reads as a different
  business. Still fill in the colours -- a changed tenant is still this unit.
- stall_h between 0 and 1.1; glaz_frac between 0.35 and 0.85.
"""

_LOCK = threading.Lock()


def _hex_to_lin(h):
    """sRGB hex -> linear RGB, the space every material value in this pipeline
    uses (facade_colors.py convention)."""
    if not isinstance(h, str):
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", h.strip())
    if not m:
        return None
    v = m.group(1)
    out = []
    for k in range(3):
        c = int(v[2 * k:2 * k + 2], 16) / 255.0
        out.append(round(c ** 2.2, 4))
    return out


def unit_photo(out, anchor, u, force=False):
    """One Street View frame aimed at THIS unit: the camera stands STANDOFF metres
    out along the frontage normal and looks back at the unit centre, so the shop
    fills the frame. The per-building streetview.png cached by the generation step
    frames the WHOLE building and renders its ground floor at a few dozen pixels."""
    d = os.path.join(out, "shop_views")
    os.makedirs(d, exist_ok=True)
    png = os.path.join(d, "%s.png" % u["id"])
    if os.path.exists(png) and not force:
        return png
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0

    def to_ll(x, y):
        return anchor["lat0"] + y / ky, anchor["lon0"] + x / kx

    tgt = to_ll(u["x"], u["y"])
    key = maps_fetch._key()
    # at a wide junction the point 13 m out lands in the carriageway and the
    # nearest panorama is the one ACROSS the road -- the shop then sits 40 m away
    # behind a bus and the agent (rightly) reports it cannot see it. Step in and
    # retry before giving up.
    pano = None
    for so, rad in ((STANDOFF, PANO_RADIUS), (7.0, 14), (4.0, 10)):
        cam = to_ll(u["x"] + u["nx"] * so, u["y"] + u["ny"] * so)
        meta = maps_fetch.sv_metadata(cam[0], cam[1], rad, key)
        if meta.get("status") != "OK":
            continue
        loc = meta["location"]
        dx = (loc["lng"] - tgt[1]) * kx
        dy = (loc["lat"] - tgt[0]) * ky
        pano = loc
        if math.hypot(dx, dy) <= 22.0:
            break
    if pano is None:
        return None
    hd = maps_fetch._bearing(pano["lat"], pano["lng"], tgt[0], tgt[1])
    maps_fetch._get(maps_fetch.STREETVIEW,
                    {"location": f"{pano['lat']},{pano['lng']}", "size": "640x640",
                     "heading": round(hd, 1), "pitch": 2.0, "fov": FOV,
                     "source": "outdoor", "key": key}, png)
    return png


def read_unit(out, anchor, u, model, force=False):
    """Ask the agent to read one shopfront. Returns (updated?, tokens)."""
    png = unit_photo(out, anchor, u, force)
    if not png or not os.path.exists(png):
        return False, 0
    txt, usage, _cost = llm.vision_call(
        SYSTEM, ASK.format(name=u["name"] or "an unnamed retail unit",
                           cat=u["category"], w=u["params"]["width"]),
        [png], model=model)
    tok = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return False, tok
    try:
        rec = json.loads(m.group(0))
    except json.JSONDecodeError:
        return False, tok
    if not rec.get("visible"):
        u["obs"] = "not visible"
        return False, tok

    p, src, conf = u["params"], u["src"], u["conf"]
    moved = False

    def _set(k, v, lo=None, hi=None):
        nonlocal moved
        if v is None:
            return
        if lo is not None:
            try:
                v = max(lo, min(hi, float(v)))
            except (TypeError, ValueError):
                return
        u.setdefault("prior", {}).setdefault(k, p[k])
        p[k] = v
        src[k] = "streetview"
        conf[k] = 0.80
        moved = True

    _set("fascia_rgb", _hex_to_lin(rec.get("fascia_hex")))
    _set("sign_rgb", _hex_to_lin(rec.get("sign_hex")))
    if isinstance(rec.get("awning"), bool):
        _set("awning", rec["awning"])
        if rec["awning"]:
            _set("awning_rgb", _hex_to_lin(rec.get("awning_hex")))
    _set("stall_h", rec.get("stall_h"), 0.0, 1.1)
    gf = rec.get("glaz_frac")
    if gf is not None:
        try:
            gf = max(0.35, min(0.85, float(gf)))
            fh = (p["stall_h"] + p["glaz_h"] + p["fascia_h"]) / 0.92
            _set("glaz_h", round(fh * gf, 2))
        except (TypeError, ValueError):
            pass
    # independent check on the deterministic POI-to-wall assignment. Recorded,
    # never acted on: the imagery is a 2024 snapshot and tenants change, so a
    # mismatch is evidence to review, not licence to rename the unit.
    if rec.get("name_on_fascia"):
        u["fascia_read"] = str(rec["name_on_fascia"])[:60]
    if u["name"] and rec.get("name_on_fascia"):
        u["name_check"] = ("match" if rec.get("name_matches")
                           else "mismatch: fascia reads %r"
                           % str(rec["name_on_fascia"])[:40])
    if rec.get("note"):
        u["note"] = str(rec["note"])[:160]
    return moved, tok


def _toks(s):
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower())
            if len(w) > 2 and w not in ("the", "and", "london", "south",
                                        "kensington", "ltd", "shop", "cafe")}


def reconcile(units):
    """Correct the ORDER of units within one frontage from what the photos read.

    The deterministic layout puts each shop at its POI's projected position, and
    Google's pins are only accurate to a few metres, so neighbours on the same
    parade can swap places (the check caught 'Stickland Pharmacy' standing where
    the fascia reads BROTHER MARCUS). When two units on the same frontage each
    read as the other's business, exchanging their slots is a correction the
    photographs support -- so it is applied, and marked as such. A one-sided or
    ambiguous mismatch is left alone.

    Only the position moves; nothing is renamed."""
    by_edge = {}
    for u in units:
        by_edge.setdefault((u["host"], u["edge"]), []).append(u)
    swapped = 0
    for group in by_edge.values():
        for a in group:
            ra = _toks(a.get("fascia_read"))
            if not ra or not a.get("name"):
                continue
            for b in group:
                if b is a or not b.get("name"):
                    continue
                rb = _toks(b.get("fascia_read"))
                if not rb:
                    continue
                # a stands where b's business is, and b where a's is
                if not (ra & _toks(b["name"]) and rb & _toks(a["name"])):
                    continue
                for k in ("t0", "t1", "x", "y"):
                    a[k], b[k] = b[k], a[k]
                a["params"]["width"], b["params"]["width"] = (
                    b["params"]["width"], a["params"]["width"])
                a["name_check"] = b["name_check"] = "swapped to match the fascias"
                a["fascia_read"] = b["fascia_read"] = None
                swapped += 1
                break
    if swapped:
        print(f"[shop-agent] {swapped} pairs swapped into the positions their "
              f"fascias show")
    return swapped


def run(out, model, workers, limit, force):
    shops = json.load(open(os.path.join(out, "shops.json")))
    anchor = json.load(open(os.path.join(out, "buildings.json")))["anchor"]
    # only units Places named: an anonymous parade-fill unit has no identity to
    # confirm in the photo, and reading a colour off "whichever shop is here"
    # would be a guess dressed up as an observation
    todo = [u for u in shops["units"] if u["name"]]
    if limit:
        todo = todo[:limit]
    print(f"[shop-agent] {len(todo)} named units, model {model}, "
          f"{workers} workers")

    done = {"n": 0, "u": 0, "tok": 0}

    def one(u):
        try:
            moved, tok = read_unit(out, anchor, u, model, force)
        except Exception as e:
            print(f"[shop-agent] {u['id']}: {type(e).__name__} {e}")
            return
        with _LOCK:
            done["n"] += 1
            done["u"] += int(bool(moved))
            done["tok"] += tok
            print(f"[shop-agent] {done['n']}/{len(todo)} {u['id']} "
                  f"{maps_fetch.latin_only(u['name'])!r}: "
                  f"{'read' if moved else u.get('obs', 'no data')}"
                  f" ({done['tok']/1000:.0f}k tok)")
            json.dump(shops, open(os.path.join(out, "shops.json"), "w"), indent=1)

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, todo))

    reconcile(shops["units"])
    json.dump(shops, open(os.path.join(out, "shops.json"), "w"), indent=1)
    obs = sum(1 for u in shops["units"] if u["src"]["fascia_rgb"] == "streetview")
    bad = [u["id"] for u in shops["units"]
           if str(u.get("name_check", "")).startswith("mismatch")]
    print(f"[shop-agent] {done['u']}/{len(todo)} units read; {obs}/"
          f"{len(shops['units'])} units now carry a street-view colour "
          f"(~{done['tok']/1000:.0f}k tokens)")
    if bad:
        print(f"[shop-agent] {len(bad)} fascias did not match the expected "
              f"business (recorded as name_check, nothing renamed): {bad[:8]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--model", default=config.VISION_MODEL)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="re-fetch the photos")
    a = ap.parse_args()
    run(os.path.abspath(a.out), a.model, a.workers, a.limit, a.force)


if __name__ == "__main__":
    main()
