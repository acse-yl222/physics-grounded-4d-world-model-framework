"""img2city/imagery/acquire_view.py -- autonomously fetch a facade image of a building and let the
agent (Claude vision) pick the best one. ("Auto-fetch, then let the agent judge.")

Pipeline:
  1. geocode the building.
  2. sample Street View panoramas on a ring around it (metadata API).
  3. for each distinct pano, aim the camera at the building (+ pitch up) and fetch a shot.
  4. ask Claude (vision) to score each shot for "clearly shows <building>",
     pick the best, save it as streetview.png, and write candidates_report.json.
  If no candidate shows the building, it says so (fall back to your own photo).

Needs:
  GOOGLE_MAPS_API_KEY                         (fetching)
  a Claude backend for judging:
    --backend sdk   Claude Agent SDK / Max subscription (default; `claude login`, unset ANTHROPIC_API_KEY)
    --backend api   ANTHROPIC_API_KEY (pay-as-you-go)

Run:
  python -m img2city.imagery.acquire_view --query "Queen's Tower, Imperial College London" --out data/queens_tower
"""
from __future__ import annotations

from img2city import config
from img2city.agent import llm
import argparse
import json
import math
import os
import re
import shutil

from img2city.imagery.maps_fetch import geocode, sv_metadata, _bearing, _get, _key, STREETVIEW, STATICMAP


def ring_panos(lat, lng, radius_m, n, key):
    """Distinct Street View panos found on a ring of n points at radius_m around (lat,lng)."""
    found = {}
    for i in range(n):
        ang = 2 * math.pi * i / n
        dlat = (radius_m * math.cos(ang)) / 111320.0
        dlng = (radius_m * math.sin(ang)) / (111320.0 * math.cos(math.radians(lat)))
        meta = sv_metadata(lat + dlat, lng + dlng, radius_m, key)
        if meta.get("status") == "OK" and meta.get("pano_id"):
            loc = meta["location"]
            found.setdefault(meta["pano_id"], (loc["lat"], loc["lng"]))
    return list(found.values())


def fetch_candidate(plat, plng, blat, blng, out_path, pitch, fov, key):
    hd = _bearing(plat, plng, blat, blng)               # aim the camera at the building
    _get(STREETVIEW, {"location": f"{plat},{plng}", "size": "640x640",
                      "heading": round(hd, 1), "pitch": pitch, "fov": fov,
                      "source": "outdoor", "key": key}, out_path)
    return hd


def _parse_judge(text):
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            return bool(j.get("visible")), float(j.get("score", 0.0)), str(j.get("note", ""))
        except Exception:
            pass
    return False, 0.0, text[:60]


def judge(img_path, building, backend, model):
    system = ("You verify whether a target building is clearly visible in a "
              "street-level photo. Reply ONLY with JSON.")
    user = (f'Target building: "{building}". Does this image clearly show THAT building '
            "(not just nearby or other buildings)? Reply ONLY: "
            '{"visible": true|false, "score": 0..1, "note": "<short>"}')
    text, _, _ = llm.vision_call(system, user, [img_path], model, backend=backend,
                                 max_tokens=150)
    return _parse_judge(text)


def main():
    ap = argparse.ArgumentParser(description="Auto-fetch street views and let the agent pick the best")
    ap.add_argument("--query", help="building name / address")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--model", default=config.VISION_MODEL)
    ap.add_argument("--radius", type=int, default=55, help="ring radius (m) to look for panos")
    ap.add_argument("--n", type=int, default=8, help="ring sample points")
    ap.add_argument("--pitch", type=float, default=22.0)
    ap.add_argument("--fov", type=float, default=95.0)
    ap.add_argument("--out", required=True, help="building directory (data/<building>)")
    a = ap.parse_args()

    key = _key()
    if a.lat is not None and a.lng is not None:
        blat, blng, building = a.lat, a.lng, (a.query or f"{a.lat},{a.lng}")
    elif a.query:
        blat, blng = geocode(a.query)
        building = a.query
        print(f"geocoded '{building}' -> {blat},{blng}")
    else:
        raise SystemExit("Give --query or both --lat and --lng")

    os.makedirs(a.out, exist_ok=True)
    _get(STATICMAP, {"center": f"{blat},{blng}", "zoom": 19, "size": "640x640",
                     "scale": 2, "maptype": "satellite", "key": key},
         os.path.join(a.out, "satellite.png"))

    panos = ring_panos(blat, blng, a.radius, a.n, key)
    if not panos:
        raise SystemExit(f"No Street View panos within {a.radius} m -- raise --radius.")
    print(f"found {len(panos)} distinct panos; fetching + judging ({a.backend})...")

    cand_dir = os.path.join(a.out, "candidates")
    os.makedirs(cand_dir, exist_ok=True)
    results = []
    for i, (plat, plng) in enumerate(panos):
        p = os.path.join(cand_dir, f"cand_{i:02d}.png")
        hd = fetch_candidate(plat, plng, blat, blng, p, a.pitch, a.fov, key)
        visible, score, note = judge(p, building, a.backend, a.model)
        results.append({"file": p, "pano": [plat, plng], "heading": round(hd, 1),
                        "visible": visible, "score": score, "note": note})
        print(f"  cand_{i:02d}  heading {hd:5.0f}  visible={visible}  score={score:.2f}  {note}")

    results.sort(key=lambda r: (r["visible"], r["score"]), reverse=True)
    best = results[0]
    with open(os.path.join(a.out, "candidates_report.json"), "w") as f:
        json.dump(results, f, indent=2)
    if best["visible"] and best["score"] > 0:
        shutil.copy(best["file"], os.path.join(a.out, "streetview.png"))
        print(f"\nbest -> {best['file']} (score {best['score']:.2f}) saved as streetview.png")
    else:
        print("\nNo candidate clearly shows the building. Raise --radius/--n, or use your "
              "own photo (e.g. reference.png) for this one.")


if __name__ == "__main__":
    main()
