"""img2city/library/learn.py -- grow the part library FROM THE REGION'S OWN FAILURES.

The parts library was never designed up front. Three times now it has grown the
same way, by hand: take the checklist questions the refined models still FAIL,
count what they keep asking for, and implement the top of that list.

  07-14 round 1  dormers 13/34, mansard 10/34, pediment 7/34, shopfront 6/34
  07-19 round 3  podium / fins / colonnade / balustrade / arched heads (campus)
  07-20 round 4  ribbon facade, giant order (post-war slab, grand stone front)
  07-26 schema   the 5/10 plateau WAS the finding -- the judge's complaints named
                 GN_Terrace v0.2's missing inputs; adding them moved 5 -> 6 and
                 DreamSim 0.499 -> 0.448

This module makes that loop repeatable and region-driven, which is what a new
area needs: a London terrace kit turned loose on a brutalist estate or a canal
belt will fail, and the useful output is not "it failed" but a RANKED LIST OF
MISSING VOCABULARY, measured the same way in both places.

Two commands:

  --backfill   the evidence is thrown away today: refine writes how MANY checks
               failed, never which. `city_generate` now persists `unmet`, but the
               224 finished city_sk buildings predate that. checklist.json and
               best.png are both still on disk, so re-scoring the best render
               against its own checklist recovers the whole baseline corpus.
               (k=1: this feeds a frequency count, not an accept/reject gate.)

  --mine       rank the surviving demands across one or more areas. Deterministic
               keyword statistics, zero LLM -- the same counting done by hand in
               round 1, so the numbers are comparable with the ones in the
               logbook. Terms the kit can already express are marked, because
               those are refinement failures, not vocabulary gaps.

  python -m img2city.library.learn --backfill --out data/city_sk --workers 8
  python -m img2city.library.learn --mine --out data/city_sk
  python -m img2city.library.learn --mine --out data/city_sk data/city_barbican   # transfer
"""
from __future__ import annotations

from img2city import config
from img2city.agent import llm
import argparse
import collections
import concurrent.futures as cf
import json
import os
import re
import threading

from img2city import kit

# Words that carry no architectural signal. Deliberately NOT a stopword list off
# the shelf: "roof"/"window"/"wall" are kept, because "is the roof ..." questions
# are exactly what we are counting.
STOP = set("""a an the is are was were be been being do does did of to in on at by
for with from as it its this that these those there here and or but not no any
some each every all both either neither than then so such only just also very
more most much many few less least same other another which who whom whose what
when where why how if while during above below over under again further once
you your model render image photo building buildings candidate shown show shows
visible appear appears look looks seen see does have has had between about
approximately roughly least same
one two three single double large small big little long short tall low high wide
narrow upper lower main other end ends side sides front back top bottom middle
centre center portion part parts area areas section rather mostly entirely
whole full half least most across along around whether least
level taller wider shorter higher deeper clearly noticeably roughly visibly
extreme close crop cropped read reads seen per contain contains containing
times they them their set into standing free separate individual typical
overall massing rectangle rectangular elongated shape shaped form formed
row rows pairs pair each""".split())

def _kit_vocabulary():
    """DERIVE the kit's vocabulary from the code instead of trusting a hand list:
    BUILDERS keys + learned PARTS_LEARNED names, every p.get("...") parameter
    name in components.py + parts_learned.py, and every field word in the spec
    schema (core + all dialect lines). The hand list drifted the moment the
    library grew ("stepped setback" was ranked MISSING while masses expressed it
    -- an EXPRESSIBLE gap, 08-10); a derived set grows with the kit by
    construction."""
    import re as _re
    words = set()
    src = ""
    for fp in kit.kit_sources():
        src += open(fp).read() + "\n"
    # part registry keys + learned registrations
    for m in _re.finditer(r'"([a-z_0-9]+)":\s*[a-z_0-9]+,?\s*(?:#.*)?$', src, _re.M):
        words.update(m.group(1).split("_"))
    # typed parameter names the parts read
    for m in _re.finditer(r'p\.get\(\s*"([a-z_0-9]+)"', src):
        words.update(m.group(1).split("_"))
    # schema field words, core + every dialect line (learned lines included)
    try:
        from img2city.building import generate
        lines = [l for _t, l in generate.SPEC_LINES]
        dj = kit.SPEC_DIALECT_JSON
        if os.path.exists(dj):
            lines += [e["line"] for e in json.load(open(dj))]
        for ln in lines:
            head = ln.split(":")[0]
            words.update(head.split("_"))
            for m in _re.finditer(r'"([a-z_]+)"', ln.split("  ")[0]):
                words.update(m.group(1).split("_"))
    except Exception:
        pass
    return {w for w in words if len(w) > 2}


# the vocabulary the kit HAS: hand-curated ARCHITECTURAL SYNONYMS only (a check
# says "sash window", the kit key says WinH) -- the mechanical part of the set
# (registry keys, p.get parameters, schema fields) is DERIVED by
# _kit_vocabulary() and unioned in below.
EXPRESSIBLE = {
    "plinth", "block", "curtain", "wall", "facade", "grid", "exoskeleton",
    "barrel", "vault", "sawtooth", "ridge", "roof", "rooftop", "plant", "stone",
    "glass", "steps", "punched", "window", "windows", "podium", "glazing", "fin",
    "fins", "colonnade", "balustrade", "terrace", "balcony", "portico",
    "porticos", "bay", "bays", "polygon", "railing", "railings", "shaft", "dome",
    "spire", "mansard", "dormer", "dormers", "pediment", "shopfront", "ribbon",
    "giant", "arch", "arched", "cornice", "stucco", "brick", "slate", "chimney",
    "chimneys", "storey", "storeys", "floor", "floors", "sash", "sashes",
    "parapet", "valley", "gable", "flat", "pitched", "sill", "sills", "jamb",
    "mullion", "mullions", "awning", "fascia", "stallriser", "pier", "piers",
    # COLOUR is not a vocabulary gap: facade_colors.py measures it off the photo
    # and palette_alias binds it to the parts (the 07-19 appearance decision). A
    # check failing on "red/brown brick" is an appearance miss, not a missing part.
    "white", "black", "grey", "gray", "red", "brown", "buff", "cream", "green",
    "blue", "yellow", "dark", "light", "pale", "colour", "color", "painted",
    "rendered", "render",
    # spec keys / existing scene layers: demands phrased around these are tuning
    # (footprint comes from OSM; doors/steps/fences/railings are existing parts)
    "footprint", "door", "doors", "entrance", "entrances", "steps", "fence",
    "fences", "grid", "grids", "pane", "panes",
    # setback/terracing IS expressible: masses with decreasing floors (the
    # schema says so explicitly) -- the 08-10 misclassification
    "setback", "setbacks", "stepped",
}
EXPRESSIBLE |= _kit_vocabulary()

# demands that CANNOT be judged from a single-building render at all -- the
# question needs the neighbours/street context the crop never shows ("is it
# attached to the terrace?", "does a taller block rise behind it?"). These are a
# JUDGE-FRAMING gap, not a vocabulary gap; counted separately so they neither
# pollute the part ranking nor get silently dropped.
CONTEXT = {"cannot", "judged", "confirmed", "confirm", "attached", "adjacent",
           "neighbour", "neighbours", "neighbouring", "neighboring", "alone",
           "behind", "next", "surrounding", "context"}

_LOCK = threading.Lock()


# --------------------------------------------------------------- backfill
def _one(out, bid, backend, model, k):
    from img2city.building.generate import checklist_score
    rdir = os.path.join(out, "buildings", bid, "refine")
    res_p = os.path.join(rdir, "result.json")
    chk_p = os.path.join(rdir, "checklist.json")
    best = os.path.join(rdir, "best.png")
    try:
        res = json.load(open(res_p))
    except Exception:
        return None
    if res.get("unmet") is not None:
        return "skip"
    if not (os.path.exists(chk_p) and os.path.exists(best)):
        return None
    checks = json.load(open(chk_p))
    top = os.path.join(rdir, "t00.png")
    _rate, failed, usage = checklist_score(
        best, checks, backend, model, top=top if os.path.exists(top) else None, k=k)
    res["unmet"] = [{"q": f.get("q"), "cat": f.get("cat"), "view": f.get("view"),
                     "note": (f.get("note") or "")[:200]} for f in failed]
    res["unmet_src"] = "backfill"
    with _LOCK:
        json.dump(res, open(res_p, "w"), indent=1)
    return usage


def backfill(out, backend, model, workers, limit, min_area=0.0):
    bdir = os.path.join(out, "buildings")
    # area-ordered, largest first: the big buildings carry the richest checklists
    # (a sub-200 m2 house gets 6-8 checks, RSM gets 20+), so a capped run should
    # spend its budget on the strongest vocabulary signal, not the first N ids
    area = {}
    try:
        for m in json.load(open(os.path.join(out, "buildings.json")))["buildings"]:
            area[str(m["id"])] = m.get("area_m2", 0.0)
    except Exception:
        pass
    ids = sorted((d for d in os.listdir(bdir)
                  if os.path.exists(os.path.join(bdir, d, "refine", "result.json"))
                  and area.get(d, 0.0) >= min_area),
                 key=lambda d: -area.get(d, 0.0))
    if limit:
        ids = ids[:limit]
    print(f"[lib] backfilling `unmet` for {len(ids)} refined buildings "
          f"(>= {min_area:.0f} m2, {model}, k=1, {workers} workers)")
    done = {"n": 0, "ok": 0, "skip": 0, "tok": 0}

    def run(bid):
        try:
            r = _one(out, bid, backend, model, 1)
        except Exception as e:
            r = None
            print(f"[lib] {bid}: {type(e).__name__} {str(e)[:70]}")
        with _LOCK:
            done["n"] += 1
            if r == "skip":
                done["skip"] += 1
            elif r is not None:
                done["ok"] += 1
                done["tok"] += (r.get("prompt_tokens", 0)
                                + r.get("completion_tokens", 0)) if isinstance(r, dict) else 0
            if done["n"] % 20 == 0:
                print(f"[lib] {done['n']}/{len(ids)} "
                      f"({done['ok']} scored, {done['skip']} already had it, "
                      f"~{done['tok']/1000:.0f}k tok)")

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(run, ids))
    print(f"[lib] backfill done: {done['ok']} scored, {done['skip']} skipped, "
          f"~{done['tok']/1000:.0f}k tokens")


# ------------------------------------------------------------------- mine
def _terms(text):
    """Salient words + adjacent pairs. Pairs matter: 'exposed concrete' and
    'concrete frame' are different demands, and round 1's hand count effectively
    read pairs too ('bay window', 'mansard roof')."""
    ws = [w for w in re.split(r"[^a-zA-Z]+", (text or "").lower())
          if len(w) > 2 and w not in STOP]
    return set(ws) | {f"{a} {b}" for a, b in zip(ws, ws[1:])}


def mine(outs, top_n, min_buildings):
    areas = {}
    for out in outs:
        name = os.path.basename(out.rstrip("/"))
        bdir = os.path.join(out, "buildings")
        per_term_b = collections.Counter()     # term -> buildings demanding it
        per_term_c = collections.Counter()     # term -> failed checks mentioning it
        examples, n_b, n_unmet, no_data = {}, 0, 0, 0
        for bid in sorted(os.listdir(bdir)):
            f = os.path.join(bdir, bid, "refine", "result.json")
            if not os.path.exists(f):
                continue
            try:
                res = json.load(open(f))
            except Exception:
                continue
            unmet = res.get("unmet")
            if unmet is None:
                no_data += 1
                continue
            n_b += 1
            n_unmet += len(unmet)
            seen = set()
            for u in unmet:
                t = _terms((u.get("q") or "") + " " + (u.get("note") or ""))
                for term in t:
                    per_term_c[term] += 1
                    examples.setdefault(term, (u.get("q") or "")[:150])
                seen |= t
            for term in seen:
                per_term_b[term] += 1
        areas[name] = {"b": per_term_b, "c": per_term_c, "ex": examples,
                       "n_b": n_b, "n_unmet": n_unmet, "no_data": no_data}
        print(f"[lib] {name}: {n_b} buildings with unmet data "
              f"({n_unmet} surviving demands), {no_data} without "
              f"-- run --backfill on those")

    # rank on the FIRST area, report the others alongside (the transfer column)
    base = areas[list(areas)[0]]
    if not base["n_b"]:
        print("[lib] nothing to mine yet: no result.json carries `unmet`. "
              "Run --backfill first, or refine a building with the current code.")
        return areas
    rows = []
    for term, nb in base["b"].most_common():
        if nb < min_buildings:
            continue
        def _expr(w):
            return w in EXPRESSIBLE or (w.endswith("s") and w[:-1] in EXPRESSIBLE)
        ws = term.split()
        if any(w in CONTEXT for w in ws):
            kind = "context"         # unjudgeable from a lone-building render
        elif all(_expr(w) for w in ws):
            kind = "tuning"          # the kit has this; it was applied badly
        elif any(_expr(w) for w in ws):
            kind = "partial"         # adjacent to something we have
        else:
            kind = "MISSING"
        rows.append((term, nb, base["c"][term], kind, base["ex"].get(term, "")))
    # rank MISSING first, then PHRASES over bare words (a two-word demand like
    # "glazed roof" or "exposed steel" names a part; "structure" on its own is a
    # fragment of one), then by how many buildings asked
    rows.sort(key=lambda r: (r[3] != "MISSING", " " not in r[0], -r[1]))

    print(f"\n{'term':<28}{'bldgs':>6}{'checks':>7}  kind      example demand")
    print("-" * 110)
    for term, nb, nc, kind, ex in rows[:top_n]:
        extra = ""
        for nm, a in list(areas.items())[1:]:
            extra += f" | {nm}:{a['b'][term]}"
        print(f"{term:<28}{nb:>6}{nc:>7}  {kind:<9} {ex[:52]}{extra}")
    print("\nMISSING = no part or knob in the kit names this; those are the "
          "candidates for a new part.\ntuning = the kit can express it and the "
          "refine loop simply did not get there.")
    return areas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", nargs="+", required=True,
                    help="one or more area dirs; the first is ranked, the rest "
                         "are shown as comparison columns")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--mine", action="store_true")
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--model", default=config.JUDGE_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-area", type=float, default=0.0,
                    help="backfill only buildings at least this large (m2)")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--min-buildings", type=int, default=3)
    a = ap.parse_args()
    outs = [os.path.abspath(o) for o in a.out]
    if a.backfill:
        backfill(outs[0], a.backend, a.model, a.workers, a.limit, a.min_area)
    if a.mine or not a.backfill:
        mine(outs, a.top, a.min_buildings)


if __name__ == "__main__":
    main()
