"""img2city/library/grow.py -- the PROPOSE step of region-driven library growth.

library/learn.py mines what a region demanded that the kit could not express;
this module hands one such demand cluster to an agent and lets it AUTHOR the
missing part -- then makes the part earn its place through three gates. The
recipe is ShapeLib's propose->implement->validate staged workflow (related_work
§R, arXiv 2502.08884) with two changes: design intent is the MINED demands, not
hand-written text, and validation includes a property ShapeLib never checks --
that every existing region still renders byte-identically.

The contract the agent writes under:
  * SIBLING parts only -- gate 0 statically rejects any top-level name that
    already exists in components.py (concatenation order would let a duplicate
    def silently SHADOW the core part);
  * parts are plain (p, i) -> [objects] functions using box()/MAT, registered
    via a PARTS_LEARNED dict; specs reach them through the additive
    `extra_parts` key, which no existing spec carries.

The three gates:
  1. smoke    -- the part builds standalone in Blender without error;
  2. regress  -- full city_sk reassembly, render_regress fingerprint CLEAN
                 (no existing object may change by a vertex);
  3. lift     -- paired A/B on the demanding buildings: the SAME spec with and
                 without the new part, rendered from the SAME refine cameras
                 (spec_render_ctx), scored against the CACHED checklist with the
                 same judge and k. The checklist was derived from the photos
                 before the part existed, so the proposer cannot game the test.

Dry run (station cluster -- known ground truth, STATION_BUILD was hand-built
07-27 for exactly these demands):

  python -m img2city.library.grow --out data/city_sk --cluster trainshed \
      --ids 101322157 101322161 --region london
"""
from __future__ import annotations
import argparse
import ast
import json
import os
import re
import subprocess

from img2city import config, kit
from img2city.agent import llm


def _stage(module, *args):
    """Keep learning gates on the same Python environment as the agent."""
    return subprocess.run(config.module_cmd(module, *args),
                          cwd=config.PROJECT_ROOT,
                          env=config.subprocess_env(), check=True)

SYSTEM = (
    "You are extending a small parametric BUILDING-PART library used inside "
    "Blender. You write clean, deterministic bpy code in exactly the house style "
    "you are shown, and you answer with one fenced Python block and nothing else."
)

PROMPT = """The parametric building kit below could not express features that a
judge repeatedly demanded on real buildings (checks the refined models still
FAIL). Your job: author the MISSING PART(S) so those demands become expressible.

## The unmet demands (verbatim failed checks, by building)

{demands}

## The buildings

{buildings}

Reference photos are attached in that order (street photo per building, then a
satellite crop of the first). The renders that failed these checks were built
from each building's JSON spec on its OSM footprint rectangle.

## House style -- the part contract

A part is a function `def my_part(p, i):` that reads its typed parameters from
dict `p`, builds objects with the helpers below, and returns a LIST of the
objects it created. `i` is the building index used in object names (every name
must embed it, e.g. "XSshed%d_3" % i).

Coordinates are BUILDING-LOCAL: the building is centred on the origin,
+z is up, ground at z=0, metres. Use each building's spatial brief to identify
the photographed face; it need not be -y. The host mass spans
x in [-L/2, L/2], y in [-W/2, W/2].

Helpers in scope (do NOT redefine them):
  box(name, [cx,cy,cz], [sx,sy,sz], matname) -> object   axis-aligned box
  obj.rotation_euler = (rx, ry, rz)                       to rotate a box
  MAT[matname] / _mn(name)                                material lookup
  bpy.data.meshes.new / from_pydata                       for non-box geometry
Available material names: {mats}

Two existing parts, verbatim, as style exemplars:

```python
{exemplars}
```

## What you must return -- ONE fenced python block, nothing else

Everything in code (never JSON -- string escaping killed two runs):

```python
def my_part(p, i):
    ...

PARTS_LEARNED = {{"my_part": my_part}}

SCHEMA_LINE = 'my_part: {{...params...}}  one-line doc for the spec schema'
SMOKE = [{{"type": "my_part", "at": [0, 0], ...example params...}}]
PER_BUILDING = {{"<osmid>": [{{"type": "my_part", ...params tuned to THAT building...}}]}}
NOTES = "one paragraph: what the parts are and the parameter choices"
```

Rules:
- AT MOST TWO part functions, the whole block UNDER 140 lines. One cluster is
  ONE feature family -- do not bundle other features you noticed in the photos;
  they get their own clusters later. An over-scoped reply gets truncated and
  fails whole.
- NEW top-level names only; never redefine an existing helper or part.
- Deterministic: no random, no Date; every dimension from p with a default.
- Keep each part parametric and general (this is a LIBRARY part for a REGION,
  not scenery for one building): lengths/widths/heights/counts/materials all
  come from p. Ranges must make sense at 5-100 m scale.
- The demanding buildings' specs already model their solid masses; your parts
  ADD what is missing (they render on top of the existing spec via
  "extra_parts"). If a demand implies the mass itself is wrong (e.g. "open
  shed, not a solid box"), your part may build the open structure and the
  per_building entry may set the spec key "masses" to [] via the special entry
  {{"_set": {{"masses": [], "floors": 1}}}} as the FIRST list element.
- per_building params must come from the photos + the OSM dims given above.
"""


def _exemplars():
    src = open(kit.COMPONENTS_PY).read()
    out = []
    for name in ("barrel_vault", "dome"):
        m = re.search(r"^def %s\(p, i\):.*?(?=^def |\Z)" % name, src, re.S | re.M)
        out.append(m.group(0).rstrip())
    return "\n\n".join(out), src


def _top_names(tree):
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def gate0_static(part_source, comp_src):
    """Sibling rule, machine-enforced: parse, and reject any top-level name that
    components.py already defines (a later def would shadow the core part when
    the sources are concatenated). Returns (learned_names, errors)."""
    errs = []
    try:
        tree = ast.parse(part_source)
    except SyntaxError as e:
        return set(), ["syntax error: %s" % e]
    mine = _top_names(tree)
    core = _top_names(ast.parse(comp_src))
    clash = (mine - {"PARTS_LEARNED"}) & core
    if clash:
        errs.append("redefines core names: %s" % sorted(clash))
    if "PARTS_LEARNED" not in mine:
        errs.append("must end with PARTS_LEARNED = {name: fn}")
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr in ("random", "now"):
            errs.append("non-deterministic call: .%s" % n.attr)
    return mine - {"PARTS_LEARNED"}, errs


def write_learned(part_source, region, cluster, out_dir):
    path = str(kit.PARTS_LEARNED_PY)
    header = ""
    if not os.path.exists(path):
        header = (
            '"""parts_learned.py -- REGION-DIALECT parts authored by library_grow.\n'
            "Additive only: concatenated after components.py, registered via\n"
            "PARTS.update; gate 0 guarantees no name here shadows a core part.\n"
            '"""\n')
    stamp = ("\n\n# ---- learned_from: %s · cluster: %s · gates: "
             "smoke+regress+lift ----\n" % (region, cluster))
    # re-running a cluster REPLACES its section (idempotent), never duplicates it
    body = open(path).read() if os.path.exists(path) else header
    mark = "· cluster: %s ·" % cluster
    if mark in body:
        i = body.index("\n\n# ---- learned_from:", max(0, body.index(mark) - 200))
        j = body.find("\n\n# ---- learned_from:", i + 10)
        body = body[:i] + (body[j:] if j != -1 else "")
    body += (stamp + part_source.rstrip() +
             "\n\nBUILDERS.update(PARTS_LEARNED)\n")
    with open(path, "w") as f:
        f.write(body)
    return path


def gate1_smoke(smoke_entries, tag):
    """Each new part must build + render standalone without a Blender error."""
    from img2city.city.generate import _send, CLEAR
    from img2city.building.generate import load_components_src
    comp = load_components_src()
    build = "import json as _gj\n" + "\n".join(
        "assemble(_gj.loads(%r))" % json.dumps({"parts": [e]})
        for e in smoke_entries)
    code = (CLEAR + "\n" + comp + "\nensure_materials()\n" + build +
            "\nprint('SMOKE_OK', len([o for o in bpy.data.objects if o.type==\"MESH\"]))")
    res, err = _send(code, timeout=900)
    if err:
        raise RuntimeError("smoke build errored: %s" % err[:300])
    txt = (res or {}).get("result", "")
    if "SMOKE_OK" not in txt:
        raise RuntimeError("smoke build produced no objects: %s" % txt[-200:])
    if not re.search(r'SMOKE_OK\s+[1-9][0-9]*', txt):
        raise RuntimeError('smoke build produced zero meshes')
    print(f"[grow {tag}] gate 1 smoke: {txt.strip().splitlines()[-1]}")


ELEV_CAM = """
import bpy, math
_ec = bpy.data.objects.get('GrowCam') or bpy.data.objects.new('GrowCam', bpy.data.cameras.new('GrowCam'))
if _ec.name not in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.link(_ec)
_ec.location = (%f, %f, %f)
_ec.rotation_euler = (math.radians(%f), 0, math.radians(%f))
_ec.data.lens = 32.0; _ec.data.clip_end = 10000
bpy.context.scene.camera = _ec
sc = bpy.context.scene
"""


def _elev_render(ctx, sp, png):
    """An ELEVATED 3/4 render of the spec (origin-centred OBB path): the pano
    camera stands in the street, so roof translucency / trusses-under-canopy /
    open-side checks are physically unanswerable from it -- the trainshed dry
    run scored 0.250 -> 0.250 while the glazed roof only showed as a sliver.
    Both A and B are rendered through this same camera, so the pairing stays
    fair; poly-mode buildings keep the street-only protocol for now."""
    from img2city.city.generate import _send, CLEAR, LIGHT_STREET, RENDER_OUT
    from img2city.building.generate import spec_to_code
    import math as _m
    L, W = ctx["L"], ctx["W"]
    H = max(int(mm.get("floors", sp.get("floors", 2))) for mm in
            (sp.get("masses") or [{}])) * float(sp.get("floor_h", 3.2))
    D = 1.15 * max(L, W) + 2.0 * H
    px, py, pz = 0.30 * L, -D * 0.80, 0.62 * D
    tz = H * 0.35
    nn = _m.hypot(px, py)
    yaw = _m.degrees(_m.atan2(px / nn, -py / nn))
    pitch = 90.0 - _m.degrees(_m.atan2(pz - tz, nn))
    code = (CLEAR + "\n" + spec_to_code(json.dumps(sp), ctx["comp"])
            + ELEV_CAM % (px, py, pz, pitch, yaw)
            + LIGHT_STREET + (RENDER_OUT % png))
    from img2city.city.generate import _BLENDER_LOCK
    with _BLENDER_LOCK:
        res, err = _send(code, timeout=600)
    if err:
        raise RuntimeError("elevated render failed: %s" % err[:150])


def gate3_lift(out, osmid, extra, model, k, gdir):
    """Paired A/B: same spec with and without the new part, same cameras, same
    cached checklist, same judge. STREET-tagged checks in cats roof/feature are
    judged against an ELEVATED 3/4 render (identical protocol on both sides) --
    the street camera cannot see a roof plane or the structure under a canopy.
    Returns {tag: (pass_rate, dreamsim)}."""
    from img2city.city.generate import spec_render_ctx
    from img2city.building.generate import checklist_score
    from img2city.judge.perceptual import dreamsim_dist
    ctx = spec_render_ctx(out, osmid)          # AFTER parts_learned.py exists
    checks = json.load(open(os.path.join(out, "buildings", str(osmid),
                                         "refine", "checklist.json")))
    elev_checks = [c for c in checks
                   if not ctx["poly_mode"] and c.get("view") == "street"
                   and c.get("cat") in ("roof", "feature")]
    main_checks = [c for c in checks if c not in elev_checks]
    spec_a = dict(ctx["spec"]); spec_a["plinth"] = False
    spec_b = json.loads(json.dumps(spec_a))
    extension_frame = None
    if ctx['poly_mode']:
        from img2city.city.generate import front_rotation
        extension_frame = {'cx':ctx['m']['obb'][0], 'cy':ctx['m']['obb'][1],
            'rotation_rad':front_rotation(ctx['m'],ctx['pano'],ctx['anchor'])}
        spec_b['extra_parts_frame'] = extension_frame
    for e in extra:
        if "_set" in e:
            spec_b.update(e["_set"])
        else:
            # some specs carry "extra_parts": null (agent-emitted); setdefault
            # would hand back the None (08-13 balconyrail gate-3 crash)
            if spec_b.get("extra_parts") is None:
                spec_b["extra_parts"] = []
            spec_b["extra_parts"].append(e)
    rates = {}
    for tag, sp in (("A", spec_a), ("B", spec_b)):
        png = os.path.join(gdir, f"{osmid}_{tag}.png")
        top = os.path.join(gdir, f"{osmid}_{tag}_top.png")
        _res, err = ctx["render"](sp, png, top)
        if err:
            raise RuntimeError(f"{tag} render failed: {err[:150]}")
        r_main, _f, _u = checklist_score(png, main_checks, "sdk", model,
                                         top=top, k=k)
        n_e, r_elev = len(elev_checks), 0.0
        if elev_checks:
            elev = os.path.join(gdir, f"{osmid}_{tag}_elev.png")
            _elev_render(ctx, sp, elev)
            r_elev, _f2, _u2 = checklist_score(elev, elev_checks, "sdk", model,
                                               k=k)
        n_m = len(main_checks)
        rate = (r_main * n_m + r_elev * n_e) / max(1, n_m + n_e)
        from img2city.imagery.reference_audit import context
        audit = context(ctx['bdir']) or {}
        ds = dreamsim_dist(png, ctx["photo"]) if audit.get('camera_verified') else None
        rates[tag] = (round(rate, 3), ds)
        print(f"[grow] {osmid} {tag}: pass {rate:.3f} "
              f"(street {r_main:.2f} x{n_m}, elev {r_elev:.2f} x{n_e}) ds {ds}")
    if extension_frame is not None:
        # Persist the exact frame tested by the renderer for later adoption.
        extra.append({'_set':{'extra_parts_frame':extension_frame}})
    return rates


def adopt(out, prop, report, region, cluster, defer_assembly=False):
    """Adoption is a SEPARATE decision from acceptance: write the winning
    extra_parts into the demanding buildings' spec.json (prior kept as
    .pre_<cluster>) and land the schema line as a region-dialect entry in
    spec_dialect.json, so the region's future spec agents can ask for the part
    themselves. Only buildings whose paired B beat A are adopted."""
    adopted = []
    for bid, r in report["buildings"].items():
        if r["pass_b"] <= r["pass_a"]:
            continue
        sp_path = os.path.join(out, "buildings", bid, "spec.json")
        spec = json.load(open(sp_path))
        bak = sp_path + ".pre_" + cluster
        if not os.path.exists(bak):
            json.dump(spec, open(bak, "w"), indent=1)
        for e in r["extra_parts"]:
            if "_set" in e:
                spec.update(e["_set"])
            else:
                if spec.get("extra_parts") is None:   # agent-emitted null
                    spec["extra_parts"] = []
                spec["extra_parts"].append(e)
        json.dump(spec, open(sp_path, "w"), indent=1)
        adopted.append(bid)
    # CARD GRADUATION (08-15 decision: "dialect must follow the TYPOLOGY"): the
    # dialect key is the majority typology card among the WINNERS -- the same
    # convention rail_terminus/cbd_tower/canal_house already use -- so the
    # vocabulary travels to any future area where that typology appears,
    # instead of being locked to the region it was learned in. The card itself
    # graduates (tags filled, learned_from stamped); region stays the fallback
    # key only when the winners have no card consensus.
    key = region
    votes = {}
    for bid in adopted:
        tp = os.path.join(out, "buildings", bid, "typology.json")
        try:
            for c in (json.load(open(tp)).get("cards") or [])[:1]:
                votes[c] = votes.get(c, 0) + 1
        except Exception:
            continue
    if votes:
        card_name = max(votes, key=votes.get)
        if votes[card_name] * 2 > len(adopted):        # strict majority
            from img2city.building.typology import CARDS_PATH
            cards = json.load(open(CARDS_PATH))
            for c in cards:
                if c["name"] == card_name:
                    if not c.get("tags"):
                        c["tags"] = [card_name]
                        c["learned_from"] = os.path.basename(out)
                        json.dump(cards, open(CARDS_PATH, "w"), indent=1)
                        print(f"[grow {cluster}] card GRADUATED: {card_name} "
                              f"(learned_from {os.path.basename(out)})")
                    key = card_name
                    break
    dj = str(kit.SPEC_DIALECT_JSON)
    entries = json.load(open(dj)) if os.path.exists(dj) else []
    entries = [e for e in entries if e.get("cluster") != cluster]
    entries.append({"region": key, "cluster": cluster,
                    "line": prop["schema_line"]})
    json.dump(entries, open(dj, "w"), indent=1)
    print(f"[grow {cluster}] adopted by {adopted}; dialect key '{key}' -> {dj}")
    if adopted and not defer_assembly:
        # adoption IS deliberate drift: refresh the area's regress baseline or
        # every SUBSEQUENT cluster's gate 2 fails on the adopted delta (tonight's
        # pilotis/parapetring reruns were killed by the pyramid adoption)
        print(f"[grow {cluster}] re-baselining {os.path.basename(out)} after adoption...")
        _stage("city.generate", "--out", out, "--assemble-only", "--min-area", "0")
        _stage("city.render_regress", "--snapshot", "--out", out)
    return adopted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--cluster", required=True, help="short tag, e.g. trainshed")
    ap.add_argument("--ids", type=int, nargs="+", required=True)
    ap.add_argument("--region", default="london")
    ap.add_argument("--model", default=config.LEARNING_MODEL,
                    help="component authoring model (IMG2CITY_LEARNING_MODEL)")
    ap.add_argument("--judge-model", default=config.JUDGE_MODEL,
                    help="independent visual evaluation model (IMG2CITY_JUDGE_MODEL)")
    ap.add_argument("--k", type=int, default=3, help="judge samples per check")
    ap.add_argument("--skip-propose", action="store_true",
                    help="reuse the saved proposal (iterate on gates only)")
    ap.add_argument("--skip-build", action="store_true",
                    help="parts already written + regress-checked: gate 3 only")
    ap.add_argument("--adopt", action="store_true",
                    help="after ACCEPT: write extra_parts into the winners' "
                         "spec.json + land the dialect schema line")
    ap.add_argument('--regress-out', action='append', help='Explicit isolated regression area; repeat for several areas')
    ap.add_argument('--defer-assembly', action='store_true', help='Caller assembles after adoption; no immediate baseline refresh')
    ap.add_argument('--feedback-file', help='Previous failed proposal and validation errors for agent repair')
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    gdir = os.path.join(out, "library_grow", a.cluster)
    os.makedirs(gdir, exist_ok=True)

    # ---- gather the cluster evidence
    demands, buildings, images = [], [], []
    metas = {m["id"]: m for m in
             json.load(open(os.path.join(out, "buildings.json")))["buildings"]}
    from img2city.city.generate import obb, ref_photo, spatial_brief
    from img2city.imagery.reference_audit import context
    for bid in a.ids:
        bdir = os.path.join(out, "buildings", str(bid))
        res = json.load(open(os.path.join(bdir, "refine", "result.json")))
        spec = json.load(open(os.path.join(bdir, "spec.json")))
        m = metas[bid]
        o = obb(m["pts"])
        demands.append("building %s:\n%s" % (bid, "\n".join(
            "  - [%s] %s" % (u["cat"], u["q"]) for u in res.get("unmet") or [])))
        buildings.append(
            "building %s: OSM %s, %.0f x %.0f m footprint, height %.1f m, "
            "current spec: %s" % (bid, m.get("btype"), o[2], o[3], m["height"],
                                  json.dumps(spec))
            + '\nSpatial evidence: ' + json.dumps(spatial_brief(dict(m, obb=o), bdir))
            + '\nReference audit: ' + json.dumps(context(bdir)))
        images.append(ref_photo(bdir))
    sat = os.path.join(out, "buildings", str(a.ids[0]), "satellite.png")
    if os.path.exists(sat):
        images.append(sat)

    exemplars, comp_src = _exemplars()
    # components.py imports bpy at module level (it runs inside Blender), so the
    # material names are read off the SOURCE, not the module
    mm_ = re.search(r"MAT_SPEC = \{(.*?)\n\}", comp_src, re.S)
    mats = sorted(set(re.findall(r'^\s*"([a-z_0-9]+)":', mm_.group(1), re.M)))
    prompt = PROMPT.format(demands="\n\n".join(demands),
                           buildings="\n".join(buildings),
                           mats=", ".join(mats),
                           exemplars=exemplars)
    if a.feedback_file:
        prompt += '\nPrevious attempt to repair:\n' + open(a.feedback_file).read()

    prop_path = os.path.join(gdir, "proposal.json")
    if a.skip_propose and os.path.exists(prop_path):
        prop = json.load(open(prop_path))
        print(f"[grow {a.cluster}] reusing saved proposal")
    else:
        txt = None
        for attempt in range(2):
            note = ("" if attempt == 0 else
                    "\n\nYOUR PREVIOUS REPLY FAILED TO PARSE (truncated or "
                    "malformed python). Reply again, SHORTER: at most two part "
                    "functions, under 120 lines, one fenced block.")
            print(f"[grow {a.cluster}] proposing ({a.model}, {len(images)} images"
                  f"{', retry' if attempt else ''})...")
            txt, usage, _c = llm.vision_call(SYSTEM, prompt + note, images,
                                             model=a.model, timeout_s=600.0)
            try:
                mprobe = re.search(r"```python\n(.*?)```", txt, re.S)
                ast.parse(mprobe.group(1))
                break
            except Exception as e:
                print(f"[grow {a.cluster}] parse failed: {str(e)[:80]}")
                if attempt:
                    raise
        # EVERYTHING arrives as code in one fenced block (JSON metadata failed
        # twice more on string escaping -- schema_line itself contains quotes).
        # The metadata lives in four literal assignments, pulled off the AST.
        open(os.path.join(gdir, "raw.txt"), "w").write(txt)
        mcode = re.search(r"```python\n(.*?)```", txt, re.S)
        if not mcode:
            raise SystemExit(f"[grow {a.cluster}] no fenced python block in reply")
        src = mcode.group(1)
        tree = ast.parse(src)
        meta_names = {"SCHEMA_LINE", "SMOKE", "PER_BUILDING", "NOTES"}
        prop, drop = {}, []
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in meta_names:
                prop[node.targets[0].id.lower()] = ast.literal_eval(node.value)
                drop.append((node.lineno, node.end_lineno))
        lines = src.splitlines()
        keep = [ln for k, ln in enumerate(lines, 1)
                if not any(a_ <= k <= b_ for a_, b_ in drop)]
        prop["part_source"] = "\n".join(keep).strip() + "\n"
        prop.setdefault("schema_line", "")
        prop.setdefault("smoke", [])
        prop.setdefault("per_building", {})
        prop["per_building"] = {str(k): v for k, v
                                in prop["per_building"].items()}
        json.dump(prop, open(prop_path, "w"), indent=1)
        print(f"[grow {a.cluster}] proposal saved "
              f"(~{(usage.get('prompt_tokens',0)+usage.get('completion_tokens',0))/1000:.0f}k tok)")

    # ---- gate 0: static sibling rule
    names, errs = gate0_static(prop["part_source"], comp_src)
    if errs:
        raise SystemExit(f"[grow {a.cluster}] gate 0 FAILED: {errs}")
    print(f"[grow {a.cluster}] gate 0 static: new parts {sorted(names)}")

    if not a.skip_build:
        lp = write_learned(prop["part_source"], a.region, a.cluster, out)
        print(f"[grow {a.cluster}] appended to {lp}")

        # ---- gate 1: smoke
        gate1_smoke(prop["smoke"], a.cluster)

        # ---- gate 2: regress. The isolation property protects EVERY region
        # that already has a baseline, not just the one being grown -- iterate
        # them all (the CW dry run only checked its own area; city_sk had to be
        # verified by hand afterwards).
        import glob as _glob
        areas = a.regress_out or sorted(os.path.dirname(f) for f in
                       _glob.glob(os.path.join(os.path.dirname(out),
                                               "*", "regress_baseline.json")))
        if out not in areas:
            areas.append(out)
        for ar in areas:
            print(f"[grow {a.cluster}] gate 2 regress: {os.path.basename(ar)}...")
            try:
                _stage("city.generate", "--out", ar, "--assemble-only", "--min-area", "0")
                _stage("city.render_regress", "--check", "--out", ar)
            except subprocess.CalledProcessError as exc:
                raise SystemExit(f"[grow {a.cluster}] gate 2 FAILED: "
                                 f"assembly or regression check failed in {os.path.basename(ar)}") from exc

    # ---- gate 3: paired lift on the demanding buildings
    report = {"cluster": a.cluster, "region": a.region, "parts": sorted(names),
              "schema_line": prop.get("schema_line"), "buildings": {}}
    for bid in a.ids:
        extra = prop["per_building"].get(str(bid))
        if not extra:
            print(f"[grow] {bid}: no per_building entry, skipped")
            continue
        rates = gate3_lift(out, bid, extra, a.judge_model, a.k, gdir)
        report["buildings"][str(bid)] = {
            "pass_a": rates["A"][0], "pass_b": rates["B"][0],
            "ds_a": rates["A"][1], "ds_b": rates["B"][1],
            "extra_parts": extra}
    ok = [b for b in report["buildings"].values() if b["pass_b"] > b["pass_a"]]
    bad = [b for b in report["buildings"].values() if b["pass_b"] < b["pass_a"]]
    # verdict rule v2 (08-12): adoption is PER-BUILDING (only winners adopt), so
    # a global any-regression veto double-gated the decision -- the ams gables
    # cluster (2 strong lifts incl. 0.33->0.75, one -0.08) was vetoed by a
    # single noisy pair while its regressed building would never have adopted
    # anyway. ACCEPT = at least one building genuinely improves; a cluster that
    # helps nobody (parapetring: 0 up, 2 down) is still rejected.
    report['models'] = {'learning': a.model, 'judge': a.judge_model}
    report["verdict"] = ("ACCEPT" if ok else
                         "REJECT" if bad else "NO-CHANGE")
    json.dump(report, open(os.path.join(gdir, "report.json"), "w"), indent=1)
    print(f"[grow {a.cluster}] verdict: {report['verdict']} "
          f"({len(ok)} improved, {len(bad)} regressed) -> {gdir}/report.json")
    if report["verdict"] != "ACCEPT":
        print(f"[grow {a.cluster}] NOTE: parts stay in parts_learned.py for "
              f"iteration; revert the file section to withdraw them")
    elif a.adopt:
        adopt(out, prop, report, a.region, a.cluster, defer_assembly=a.defer_assembly)


if __name__ == "__main__":
    main()
