"""img2city/building/glass_agent.py -- the AGENT decides curtain-wall appearance from the photo.

The pixel path cannot measure a curtain wall: the facade median is the sky it
reflects (identical near-white triplets on every tower, 08-10), and the gloss
values were briefly hand-picked by the orchestrator -- which violates the
project rule that outputs are the agent's (08-11: appearance decisions
belong to the agent, not to whoever runs the pipeline). This pass closes both:
per glass-facade building the agent looks at the street photo and reports WHAT
THE MATERIAL IS -- tint hue and a named reflectivity class -- which is exactly
the judgement a VLM can make through reflections where pixel statistics cannot.

Values land in colors.json (`glass` linear RGB + `glass_look` class, source
"streetview", conf 0.8, prior kept) and components.palette_alias maps the class
to metallic/roughness via GLASS_LOOK. Buildings the agent cannot see keep the
pixel-path fallback; nothing is hand-set.

  python -m img2city.building.glass_agent --out data/city_cw
  python -m img2city.building.glass_agent --out data/city_cw --limit 3     # try a few first
"""
from __future__ import annotations

from img2city import config
import argparse
import concurrent.futures as cf
import json
import os
import re
import threading

from img2city.agent import llm

SYSTEM = (
    "You are a facade materials surveyor. You look at one street photograph of "
    "a curtain-wall / glazed building and report the GLASS SKIN's appearance -- "
    "its tint and how reflective it is -- reading through reflections the way a "
    "surveyor would. Reply with a single JSON object and nothing else."
)

ASK = """The photo shows this building (it may be partly occluded or reflect sky):
  name: {name}
  about {h:.0f} m tall, footprint {L:.0f} x {W:.0f} m

Report the curtain-wall glass skin:

{{"visible": true,
  "glass_hex": "#1f3442",   // the glass TINT as sRGB hex -- the colour the glazing
                            // itself contributes, not the sky it mirrors; typical
                            // real values are deep blue/green/grey/bronze
  "look": "glossy",         // one of: "mirror" (sharp sky/building reflections),
                            // "glossy" (clear reflections, softened), "satin"
                            // (dull sheen, diffuse reflections), "matte"
  "spandrel_hex": null,     // colour of solid spandrel/mullion bands if clearly
                            // present, else null
  "note": "<one line: what the skin is, e.g. 'blue-green reflective glass with dark mullions'>"
}}

Rules:
- If the building is not visible or not glazed, set "visible": false, rest null.
- glass_hex is the DARK base tint you would paint the glass; never white/sky.
- Pick the look from the reflections you can actually see in the photo.
"""

LOOKS = {"mirror", "glossy", "satin", "matte"}
_LOCK = threading.Lock()


def _unusable(photo_p):
    """Delegates to rescue_imagery.unusable_image -- the original std<8 test
    PASSED the sorry tile (its text/logo push std to ~15), and a night rerun of
    the OCS rescue trusted a fresh placeholder over the real photo because of
    exactly that. One detector, one place."""
    from img2city.imagery.rescue_imagery import unusable_image
    return unusable_image(photo_p)


def tower_view(t, anchor, force=False):
    """A shot that actually CONTAINS the tower: street panos sit metres from the
    podium, so a 150 m shaft exits the frame (or the tile is the sorry
    placeholder). Stand back along whatever pano the metadata offers at growing
    radii and pitch up at the shaft. Cached as glass_view.png."""
    import math
    from img2city.imagery import maps_fetch
    out_p = os.path.join(t["bdir"], "glass_view.png")
    if os.path.exists(out_p) and not force:
        return out_p
    lat, lng = t["lat"], t["lng"]
    key = maps_fetch._key()
    kx = 111320.0 * math.cos(math.radians(lat))
    # sv_metadata(center, r) returns the NEAREST pano however big r is -- to
    # stand back you must QUERY FROM out there: sample points on a ring at
    # ~0.8H in 8 compass directions and keep the pano closest to that distance
    want = max(50.0, t["h"] * 0.8)
    best = None
    for k in range(8):
        a = k * math.pi / 4
        qlat = lat + want * math.cos(a) / 110540.0
        qlng = lng + want * math.sin(a) / kx
        meta = maps_fetch.sv_metadata(qlat, qlng, 60, key)
        if meta.get("status") != "OK":
            continue
        p = meta["location"]
        dist = max(10.0, math.hypot((p["lng"] - lng) * kx,
                                    (p["lat"] - lat) * 110540.0))
        score = abs(dist - want)
        if best is None or score < best[2]:
            best = (p, dist, score)
    if best is None:
        return None
    best = (best[0], best[1])
    p, dist = best
    hd = maps_fetch._bearing(p["lat"], p["lng"], lat, lng)
    pitch = min(55.0, math.degrees(math.atan2(t["h"] * 0.55, dist)))
    maps_fetch._get(maps_fetch.STREETVIEW,
                    {"location": f"{p['lat']},{p['lng']}", "size": "640x640",
                     "heading": round(hd, 1), "pitch": round(pitch, 1),
                     "fov": 100, "source": "outdoor", "key": key}, out_p)
    if _unusable(out_p):
        os.remove(out_p)
        return None
    return out_p


def _hex_to_lin(h):
    if not isinstance(h, str):
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", h.strip())
    if not m:
        return None
    v = m.group(1)
    return [round((int(v[2 * k:2 * k + 2], 16) / 255.0) ** 2.2, 4)
            for k in range(3)]


def glass_targets(out):
    """Glass-facade buildings (dominant mass) with a street photo."""
    d = json.load(open(os.path.join(out, "buildings.json")))
    targets = []
    for m in d["buildings"]:
        bdir = os.path.join(out, "buildings", str(m["id"]))
        sp_p = os.path.join(bdir, "spec.json")
        if not os.path.exists(sp_p):
            continue
        sp = json.load(open(sp_p))
        ms = sp.get("masses") or [{}]
        big = max(ms, key=lambda mm: (mm.get("x", [0, 1])[1] - mm.get("x", [0, 1])[0])
                  * (mm.get("y", [0, 1])[1] - mm.get("y", [0, 1])[0]))
        if (big.get("facade") or sp.get("facade")) != "glass":
            continue
        from img2city.city.generate import ref_photo, obb
        photo = ref_photo(bdir)
        if not os.path.exists(photo):
            continue
        o = obb(m["pts"])
        targets.append({"id": m["id"], "bdir": bdir, "photo": photo,
                        "name": m.get("name") or m.get("btype") or "office",
                        "h": m["height"], "L": o[2], "W": o[3],
                        "lat": m["center_latlng"][0], "lng": m["center_latlng"][1]})
    return targets


def read_one(t, model, anchor=None):
    photo = t["photo"]
    gv = os.path.join(t["bdir"], "glass_view.png")
    if os.path.exists(gv):
        photo = gv                        # dedicated tower shot from a prior pass
    elif _unusable(photo) or t["h"] > 45:
        # sorry-tile reference, or a shaft no street-level frame can hold --
        # acquire a stood-back pitched-up view before asking the agent
        got = tower_view(t, anchor)
        if got:
            photo = got
        elif _unusable(t["photo"]):
            return "no usable imagery", 0
    txt, usage, _c = llm.vision_call(
        SYSTEM, ASK.format(name=t["name"], h=t["h"], L=t["L"], W=t["W"]),
        [photo], model=model)
    tok = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None, tok
    try:
        rec = json.loads(m.group(0), strict=False)
    except json.JSONDecodeError:
        return None, tok
    if not rec.get("visible"):
        return "not visible", tok
    lin = _hex_to_lin(rec.get("glass_hex"))
    look = rec.get("look")
    if lin is None or look not in LOOKS:
        return None, tok
    cpath = os.path.join(t["bdir"], "colors.json")
    with _LOCK:
        c = json.load(open(cpath)) if os.path.exists(cpath) else {}
        if c.get("glass"):
            c.setdefault("_prior", {})["glass"] = c["glass"]
        c["glass"] = lin
        c["glass_look"] = look
        c["_glass_src"] = {"src": "streetview_agent", "conf": 0.8,
                           "note": str(rec.get("note") or "")[:120]}
        if rec.get("spandrel_hex"):
            sl = _hex_to_lin(rec["spandrel_hex"])
            if sl:
                c["_spandrel"] = sl
        json.dump(c, open(cpath, "w"), indent=1)
    return look, tok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--model", default=config.VISION_MODEL)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    targets = glass_targets(out)
    # only buildings the agent has not read yet -- reruns fill gaps, never respend
    def _has_look(t):
        cp = os.path.join(t["bdir"], "colors.json")
        return os.path.exists(cp) and bool(json.load(open(cp)).get("glass_look"))
    targets = [t for t in targets if not _has_look(t)]
    if a.limit:
        targets = targets[:a.limit]
    print(f"[glass-agent] {len(targets)} glass-facade buildings, {a.model}")
    done = {"n": 0, "ok": 0, "tok": 0}

    def run(t):
        try:
            res, tok = read_one(t, a.model)
        except Exception as e:
            res, tok = f"{type(e).__name__}", 0
        with _LOCK:
            done["n"] += 1
            done["ok"] += res in LOOKS
            done["tok"] += tok
            print(f"[glass-agent] {done['n']}/{len(targets)} {t['id']} "
                  f"{str(t['name'])[:24]!r}: {res} ({done['tok']/1000:.0f}k tok)")

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(run, targets))
    print(f"[glass-agent] {done['ok']}/{len(targets)} read "
          f"(~{done['tok']/1000:.0f}k tokens)")


if __name__ == "__main__":
    main()
