"""typology.py -- per-building TYPOLOGY CARD selection (§S, built 08-11).

The dialect key moved from geography to typology: a style is learned once and
reused wherever that typology appears; geography is only where it was learned.
This module answers "which dialect(s) does THIS building get?" -- zero-shot,
from the building's own photo + hard signals, against the card deck
(typology_cards.json: name + discriminative cues; cards with empty `tags` are
seeded classes whose dialect fills in when a region demands it).

Selection is a cheap cached vision call (haiku-class): the VLM's pretrained
prior over world architecture IS the world coverage we do not build ourselves
(ISPRS 2024 zero-shot building-age; SciReports 2026 facade materials). "none
fits" is a legal answer and is the DISCOVERY signal -- such buildings run on
core, and when a cluster of them shares unmet demands, the grow loop authors a
new dialect + card.

Misclassification cost is bounded by design: cards only add schema OPTIONS; the
photo drives the spec agent's choices and the judge punishes mismatches (the
flat schema exposed every SK terrace to tower vocabulary for a month with zero
style bleed).

  python -m img2city.building.typology --out data/city_cw               # classify every building
  python -m img2city.building.typology --out data/city_cw --ids 5986754
"""
from __future__ import annotations

from img2city import config
from img2city.agent import llm
import argparse
import concurrent.futures as cf
import json
import os
import re
import threading

_LOCK = threading.Lock()
CARDS_PATH = os.environ.get('IMG2CITY_TYPOLOGY_CARDS', os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "typology_cards.json"))

SYSTEM = (
    "You are an architectural surveyor classifying ONE building into a small "
    "deck of typology cards from its photo and facts. You answer with JSON only."
)

ASK = """Classify this building.

Facts: {facts}

The card deck (name: discriminative cues):
{deck}

Reply with JSON only:
{{"cards": ["<best card>", "<optional second card>"],
  "confidence": 0.0-1.0,
  "none_fits": false,
  "note": "<one line why>"}}

Rules:
- Pick 1 card, 2 only for genuine hybrids (e.g. church with an office wing).
- If no card matches what you SEE, set "none_fits": true and "cards": [] --
  that is a useful answer, not a failure.
- Judge from the photo first; the facts break ties.
"""


def load_cards():
    return json.load(open(CARDS_PATH))


def _facts(m):
    """The hard-signal line of the ASK. A web upload carries no survey (no OSM
    footprint/height/type) -- say so instead of inventing numbers that would
    bias the read; the photo is then the only evidence, which is the case the
    deck was designed for (judge from the photo first)."""
    if m.get("height") is None:
        return ("none -- a single uploaded photo, no footprint, height or "
                "OSM type; judge from the photo alone.")
    return (f"{m.get('name') or 'unnamed'}; height {m['height']:.0f} m; "
            f"footprint ~{m['area_m2']:.0f} m2; OSM type {m.get('btype')}; "
            f"resolved function {m.get('func') or 'none'}.")


def card_tags(card_names):
    """Schema tags for a set of chosen cards (seed cards may map to none yet)."""
    by = {c["name"]: c for c in load_cards()}
    tags = set()
    for n in card_names or []:
        tags |= set(by.get(n, {}).get("tags") or [])
    return tags


def pick(m, bdir, model=config.VISION_MODEL, force=False):
    """-> {"cards": [...], "confidence", "none_fits", "src"} cached in
    bdir/typology.json. Falls back to {} (core-only) when there is no usable
    photo -- classification without evidence would be a guess."""
    tp = os.path.join(bdir, "typology.json")
    if os.path.exists(tp) and not force:
        return json.load(open(tp))
    from img2city.city.generate import ref_photo
    from img2city.imagery.rescue_imagery import unusable_image
    photo = ref_photo(bdir)
    result = {"cards": [], "confidence": 0.0, "none_fits": False,
              "src": "no_photo"}
    if os.path.exists(photo) and not unusable_image(photo):
        deck = "\n".join(f"- {c['name']}: {c['cues']}" for c in load_cards())
        txt, _u, _c = llm.vision_call(
            SYSTEM, ASK.format(facts=_facts(m), deck=deck),
            [photo], model=model)
        mm = re.search(r"\{.*\}", txt, re.S)
        if mm:
            try:
                rec = json.loads(mm.group(0), strict=False)
                known = {c["name"] for c in load_cards()}
                result = {"cards": [c for c in (rec.get("cards") or [])
                                    if c in known][:2],
                          "confidence": float(rec.get("confidence") or 0.0),
                          "none_fits": bool(rec.get("none_fits")),
                          "note": str(rec.get("note") or "")[:120],
                          "src": "photo_agent"}
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    with _LOCK:
        json.dump(result, open(tp, "w"), indent=1)
    return result


def building_tags(out, m, bdir):
    """The schema tags THIS building's spec/refine calls should use: its cached
    card pick when present, else the area's legacy region default."""
    tp = os.path.join(bdir, "typology.json")
    from img2city.building.generate import area_region, REGION_TAGS
    fallback = REGION_TAGS.get(area_region(out), {area_region(out)})
    if os.path.exists(tp):
        rec = json.load(open(tp))
        if rec.get("cards"):
            tags = card_tags(rec["cards"])
            # SEED-card pick (a card with no dialect yet): keep the pick as the
            # DISCOVERY signal, but the building keeps its area dialect until
            # that card grows parts -- otherwise 115/252 SK buildings that read
            # as shophouse/haussmann lookalikes would silently lose the terrace
            # vocabulary they demonstrably need (deck calibration finding, 08-11)
            return tags if tags else fallback
        if rec.get("none_fits"):
            return set()                      # explicit no-match: core-only
    return fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--model", default=config.VISION_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas = [m for m in d["buildings"]
             if not a.ids or m["id"] in set(a.ids)]
    done = {"n": 0}
    import collections
    tally = collections.Counter()

    def one(m):
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if not os.path.isdir(bdir):
            return
        rec = pick(m, bdir, a.model, a.force)
        with _LOCK:
            done["n"] += 1
            key = ",".join(rec.get("cards") or []) or \
                ("none_fits" if rec.get("none_fits") else rec.get("src", "?"))
            tally[key] += 1
            if done["n"] % 20 == 0:
                print(f"[typology] {done['n']}/{len(metas)}")

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, metas))
    print(f"[typology] {done['n']} classified:")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
