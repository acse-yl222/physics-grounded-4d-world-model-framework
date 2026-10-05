"""img2city/building/generate.py -- the AGENT generates a Blender model of a building from its images.

The core "image -> editable 3D" loop, run autonomously by the agent:
  1. Claude (vision) looks at data/<b>/satellite.png (footprint) + streetview.png
     (facade) and WRITES bpy code that builds a clean, parametric, editable model.
  2. The code runs in live Blender (BlenderMCP socket); the harness auto-frames a
     camera and renders.
  3. Claude (vision) compares the render to the real photo -> score + one critique.
  4. Claude revises its bpy from the critique (and self-repairs any Blender error).
  5. loop until the score passes a threshold or max-iters; the best version is saved
     as best.py / best.png.

Run on your Mac (Blender open + BlenderMCP server on :9876; provider + model from .env):
  python -m img2city.building.generate --data data/queens_tower --max-iters 6
  python -m img2city.building.generate --data data/modern1 --model claude-api:claude-sonnet-5
  # match a specific reference image (e.g. an aerial model render):
  python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial
  # assemble from the parts library (reliable; agent emits a JSON spec, not raw bpy):
  python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial --mode assemble

The agent writes ONLY geometry (objects + materials); the harness adds camera /
lights / render. LLM-written bpy is imperfect -- the error-repair + critique loop
is what makes it converge, so expect a few rough early iterations.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import socket
import time

from img2city.judge.perceptual import dreamsim_dist
from img2city import config
from img2city.agent import llm
from img2city.kit import load_kit_src, SPEC_DIALECT_JSON

HOST, PORT = config.MCP_HOST, config.MCP_PORT

# One batch removal instead of one remap pass per ID, then purge the orphan
# meshes / cameras / lights every render leaves behind: removing IDs one by
# one is O(total data-blocks) each, so after a day of live renders a single
# CLEAR took minutes at 100% CPU (08-23 diagnosis by stack sample).
CLEAR = ("import bpy\n"
         "bpy.data.batch_remove(list(bpy.data.objects) + list(bpy.data.materials))\n"
         "bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)\n")

# Wraps the agent's geometry: auto-frame a camera on the built model + render.
# Two viewpoints: 'street' (frontal worm's-eye, default) and 'aerial' (high 3/4,
# to match an aerial / model reference like modelpic).
RENDER_HEAD = r'''
import bpy, math, mathutils
objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not objs:
    raise RuntimeError("agent code created no mesh objects")
mn = [1e18]*3; mx = [-1e18]*3
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
cx, cy, cz = [(mn[i]+mx[i])/2 for i in range(3)]
size = max(mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2], 1.0)
tgt = bpy.data.objects.new("Tgt", None); bpy.context.scene.collection.objects.link(tgt)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); bpy.context.scene.collection.objects.link(cam)
'''

# frontal, slightly-low, looking-up view of the -Y facade (street-view-like)
CAM_STREET = r'''
tgt.location = (cx, cy, cz*0.62)
cam.location = (cx, cy - max(size*1.35, 12.0), cz*0.28); cam.data.lens = 40
'''

# 3/4 aerial matching the modelpic composition: elevated view from beyond the +x short
# end, front (-y) facade on the left, long axis receding. The DISTANCE is auto-fitted to
# the whole bounding box -- the previous fixed-offset camera produced close-up crops
# that hid built features (the checklist then failed "no vault visible" on models that
# HAD the vault, and IoU rewarded the crop for filling the frame like the reference).
CAM_AERIAL = r'''
ex = mx[0]-mn[0]; ey = mx[1]-mn[1]; ez = mx[2]-mn[2]
tgt.location = (cx, cy, cz*0.85)
_dir = mathutils.Vector((0.72, -0.55, 0.60)); _dir.normalize()
_rad = 0.5*math.sqrt(ex*ex + ey*ey + ez*ez)
cam.data.lens = 42
_hfov = 2*math.atan(18.0/cam.data.lens)
_dist = _rad / math.tan(_hfov/2) * 1.04
cam.location = (cx + _dir.x*_dist, cy + _dir.y*_dist, cz*0.85 + _dir.z*_dist)
'''

RENDER_CAM = r'''
con = cam.constraints.new('TRACK_TO'); con.target = tgt
con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
bpy.context.scene.camera = cam
sc = bpy.context.scene
'''

# street: sky + single sun (matches a real street photo). Tamed exposure, same
# values as city_pilot.CITY_RENDER: the old sun 3.5 + full-strength sky blew out
# the white stucco band (the judge kept scoring "can't count storeys" on washed-out
# renders, not on wrong geometry). AgX + negative exposure roll the highlights
# back -- and MUST be set explicitly here: view_settings persist across the live
# Blender session, so without this the street render inherits whatever the last
# run set (e.g. LIGHT_STUDIO's 'Standard' +0.2).
LIGHT_STREET = r'''
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); bpy.context.scene.collection.objects.link(sun)
sun.data.energy = 2.2; sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(40))
w = bpy.context.scene.world or bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg: bg.inputs[0].default_value = (0.75, 0.82, 0.90, 1); bg.inputs[1].default_value = 0.7
_vs = bpy.context.scene.view_settings
try: _vs.view_transform = 'AgX'
except Exception: pass
try: _vs.exposure = -0.7
except Exception: pass
'''

# aerial: black background + soft studio lights + punchy transform (matches a
# model-style reference like modelpic, so a white model doesn't wash out).
LIGHT_STUDIO = r'''
try:
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.2
except Exception: pass
def _AL(n, loc, e, s, rot=(0, 0, 0)):
    l = bpy.data.lights.new(n, 'AREA'); l.size = s; l.energy = e
    o = bpy.data.objects.new(n, l); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
_d = max(size, 12.0)
_AL("Key",   (cx, cy - _d*1.1, cz + _d*2.4), _d*_d*3.0, _d*2.4)
_AL("Top",   (cx, cy + _d*0.6, cz + _d*3.0), _d*_d*2.2, _d*3.2)
_AL("Fill",  (cx, cy - _d*1.6, cz + _d*1.4), _d*_d*1.7, _d*1.8, (math.radians(60), 0, 0))
_AL("FFill", (cx, cy - _d*1.5, cz*0.4 + 2.0), _d*_d*1.2, _d*1.5, (math.radians(80), 0, 0))
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); bpy.context.scene.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(15))
w = bpy.context.scene.world or bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg: bg.inputs[0].default_value = (0, 0, 0, 1); bg.inputs[1].default_value = 0.0
'''

# straight-down roof view (auto-fit): roof features (plant, ridges, vault extent) are
# a few pixels in the aerial 3/4 view and the inspector kept mis-judging them; a
# second local render is free and gives the checklist direct evidence.
CAM_TOP = r'''
_radT = 0.5*math.sqrt((mx[0]-mn[0])**2 + (mx[1]-mn[1])**2 + (mx[2]-mn[2])**2)
cam.data.lens = 42
_hfovT = 2*math.atan(18.0/cam.data.lens)
tgt.location = (cx, cy, cz)
cam.location = (cx, cy + 0.001, cz + _radT / math.tan(_hfovT/2) * 1.02)
'''

RENDER_OUT = r'''
try: sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine = 'BLENDER_EEVEE'
try: sc.eevee.use_raytracing = True
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = 900, 900
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
'''

# geometry-only channel for the dual-channel judge (research pass §P): Workbench
# matcap render from the SAME camera -- shape defects the beauty render hides are
# unmistakable here. Restores EEVEE afterwards so later renders are unaffected.
NORMAL_OUT = r'''
sc.render.engine = 'BLENDER_WORKBENCH'
_sh = sc.display.shading
_sh.light = 'MATCAP'
try: _sh.studio_light = 'check_normal+y.exr'
except Exception: pass
_sh.color_type = 'SINGLE'
_sh.show_cavity = True
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
try: sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine = 'BLENDER_EEVEE'
'''


def _send(code, timeout=180):
    """Run bpy code in Blender via the BlenderMCP socket. Returns (result, error)."""
    payload = json.dumps({"type": "execute_code", "params": {"code": code}}).encode("utf-8")
    buf, resp = b"", None
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(payload)
            while True:
                ch = s.recv(8192)
                if not ch:
                    break
                buf += ch
                try:
                    resp = json.loads(buf.decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
    except OSError as e:
        return None, f"socket error: {e} (is Blender + the BlenderMCP server running on :{PORT}?)"
    if resp is None:
        return None, "no reply from Blender"
    if resp.get("status") != "success":
        return None, str(resp.get("message"))[:800]
    error = component_errors(resp.get("result", {}))
    if error:
        return None, error
    return resp.get("result", {}), None


def component_errors(result):
    """Caught part failures must not masquerade as a complete agent model."""
    output = result.get("result", "") if isinstance(result, dict) else str(result)
    failed = [line for line in output.splitlines()
              if "[components]" in line and
              ("failed:" in line or "skip unknown part:" in line)]
    return "\n".join(failed)[:2500] or None


def build_and_render(geometry_code, out_png, view="street", top_png=None):
    cam = CAM_AERIAL if view == "aerial" else CAM_STREET
    light = LIGHT_STUDIO if view == "aerial" else LIGHT_STREET
    wrap = RENDER_HEAD + cam + RENDER_CAM + light + (RENDER_OUT % out_png)
    if top_png:
        wrap += CAM_TOP + (RENDER_OUT % top_png)
    return _send(CLEAR + "\n" + geometry_code + "\n" + wrap)


_SMALL_CACHE = {}


def _shrink(path, max_px=640):
    """Cache a <=max_px copy of an image for VLM calls. Full-res 900 px renders +
    reference photos dominated the old token bill (~85k/iteration); the geometry
    judgements the loop needs survive 640 px fine, at a fraction of the tokens."""
    try:
        from PIL import Image
    except Exception:
        return path
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return path
    hit = _SMALL_CACHE.get(key)
    if hit and os.path.exists(hit):
        return hit
    im = Image.open(path)
    if max(im.size) <= max_px:
        _SMALL_CACHE[key] = path
        return path
    im.thumbnail((max_px, max_px))
    import hashlib
    import tempfile
    h = hashlib.md5((path + str(key[1])).encode()).hexdigest()[:10]
    out = os.path.join(tempfile.gettempdir(), "gen_small_%s.jpg" % h)
    im.convert("RGB").save(out, quality=85)
    _SMALL_CACHE[key] = out
    return out


def _vision(system, user, image_paths, backend, model, max_tokens=2500):
    """One model call for this stage: (text, usage).  ``backend`` is an
    optional provider override (None = .env); the Claude transports get the
    640 px copies (their vision budget), other providers see the originals."""
    provider, model = llm.resolve(model, backend, default_model=config.SPEC_MODEL)
    if llm.is_claude(provider):
        image_paths = [_shrink(p) for p in image_paths if p]
    text, usage, _cost = llm.vision_call(system, user, image_paths, f"{provider}:{model}",
                                         max_tokens=max_tokens, max_turns=10)
    return text, usage


def _extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


GEN_SYS = ("You are an expert Blender (bpy) modeller building clean, PARAMETRIC, "
           "editable building models in real-world metres. FIRST briefly analyse the "
           "building shown -- overall massing, number of floors / approx height, "
           "footprint shape, and its 2-3 most DISTINCTIVE features -- THEN output ONE "
           "```python code block that creates mesh objects + materials reproducing it, "
           "with correct PROPORTIONS and SCALE and those distinctive features (e.g. "
           "exposed structural frames, atria, louvred or curtain-wall facades), not a "
           "plain box. Do NOT add camera, lights, world, or render calls -- the harness "
           "does that. Write robust code (keep all parentheses/brackets balanced). "
           "Place the building centred near the origin with its MAIN FRONT FACADE "
           "facing -Y (the harness photographs it from the front along -Y).")


def gen_step(images, prev_code, critique, error, backend, model,
             brief=None, history=None, phase="full", n_aux=0):
    ctx = _context_blocks(brief, history)
    if prev_code is None:
        user = ("Image 1 = top-down satellite (footprint / plan). Image 2 = a reference "
                "view of the target building (height / floors / style / distinctive "
                "features). Write bpy that builds a parametric model matching it: "
                "massing, floors, windows, roof, and material colours appropriate to "
                "its type. Output ONLY the ```python block."
                + (AUX_NOTE.format(n=n_aux) if n_aux else "") + ctx)
    elif error:
        user = ("Your previous bpy raised this Blender error:\n" + error +
                "\n\nFix it and output ONLY the corrected full ```python block." + ctx +
                "\n\nPrevious code:\n```python\n" + prev_code + "\n```")
    else:
        user = ("Image 1 = the target reference image, image 2 = your current render, "
                "image 3 = satellite. Most important fix: " + (critique or "") + ctx +
                "\n\nRevise your bpy to match the target better (proportions, "
                "floors, roof, openings). Output ONLY the corrected full ```python "
                "block.\n\nPrevious code:\n```python\n" + prev_code + "\n```")
    text, usage = _vision(GEN_SYS, user, images, backend, model)
    return _extract_code(text), usage


def _critique_once(render, photo, backend, model, fields):
    # Rubric judging: per-criterion scores are more stable + informative than a single
    # number (LLM-as-judge best practice), and averaging them cuts variance. The "fix"
    # is the informative feedback the refine step needs (Self-Refine: feedback quality
    # is the bottleneck).
    system = ("You are a strict architectural model critic comparing a 3D render to a "
              "reference image. Judge criterion-by-criterion, then reply ONLY with JSON.")
    desc = {"massing": '"massing" (overall shape + footprint)',
            "proportions": '"proportions" (height vs length/width)',
            "features": '"features" (are the reference\'s DISTINCTIVE elements present and correct: '
                        'structural frames, vault / roof shapes, entrance volumes, etc.)',
            "roof": '"roof"', "facade": '"facade"'}
    user = ('Image 1 = target reference, image 2 = current 3D render. Score each field 0..1: '
            + ", ".join(desc[f] for f in fields) +
            '. Then "fix" = the single most important thing to add or change next. '
            'Reply ONLY: {' + ",".join('"%s":0..1' % f for f in fields) + ',"fix":"..."}')
    txt, usage = _vision(system, user, [photo, render], backend, model, max_tokens=400)
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            vals = [float(j[k]) for k in fields if k in j]
            score = round(sum(vals) / len(vals), 3) if vals else 0.0
            return score, str(j.get("fix", "")), usage
        except Exception:
            pass
    return 0.0, txt[:160], usage


_IOU_CACHE = {}


def iou_anchor(render, photo):
    """Deterministic silhouette-IoU blended into the score. The VLM rubric swings
    ~±0.1 on IDENTICAL geometry -- larger than a real iteration's improvement -- so on
    its own the accept/reject decision was mostly noise. IoU is coarse but exactly
    repeatable and anchors the combined score. Both modelpic-style references and the
    studio renders sit on black, so bg='black' masks work for both."""
    try:
        from img2city.judge.evaluator import SilhouetteEvaluator
        ev = _IOU_CACHE.get(photo)
        if ev is None:
            ev = SilhouetteEvaluator(photo, bg="black")
            _IOU_CACHE[photo] = ev
        return ev.score(render, bg="black")["iou"]
    except Exception:
        return None


def critique_step(render, photo, backend, model, k=2, fields=None):
    """Stabilised critic: k rubric calls -> median (k>=3) / mean (k=2), blended with the
    deterministic IoU anchor. Returns (combined, rubric, iou, fix, usage)."""
    fields = fields or ["massing", "proportions", "features", "roof", "facade"]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    scores, fixes = [], []
    for _ in range(max(1, int(k))):
        s, f, u = _critique_once(render, photo, backend, model, fields)
        scores.append(s)
        fixes.append(f)
        usage["prompt_tokens"] += u["prompt_tokens"]
        usage["completion_tokens"] += u["completion_tokens"]
    srt = sorted(scores)
    rubric = srt[len(srt) // 2] if len(srt) % 2 else round(sum(srt[len(srt) // 2 - 1:len(srt) // 2 + 1]) / 2, 3)
    fix = fixes[min(range(len(scores)), key=lambda i: abs(scores[i] - rubric))]
    iou = iou_anchor(render, photo)
    combined = round(0.7 * rubric + 0.3 * iou, 3) if iou is not None else rubric
    return combined, rubric, iou, fix, usage


def _ab_once(photo, a_png, b_png, backend, model):
    system = "You compare two 3D renders (A, B) against a reference photo. Reply ONLY with JSON."
    user = ('Image 1 = reference. Image 2 = render A. Image 3 = render B. Which render '
            'matches the reference building more closely overall (massing, roof features, '
            'facade, distinctive elements)? Reply ONLY: {"winner":"A"|"B","why":"<short>"}')
    txt, usage = _vision(system, user, [photo, a_png, b_png], backend, model, max_tokens=150)
    m = re.search(r'"winner"\s*:\s*"([AB])"', txt)
    w = re.search(r'"why"\s*:\s*"([^"]*)"', txt)
    return (m.group(1) if m else "A"), (w.group(1) if w else ""), usage


def ab_judge(photo, a_png, b_png, backend, model):
    """(--judge rubric path) single-call near-tie gate; kept for comparison runs."""
    winner, _, usage = _ab_once(photo, a_png, b_png, backend, model)
    return winner, usage


def ab_vote(photo, a_png, b_png, backend, model, votes=2):
    """Swap-CONSISTENT pairwise vote -- the PRIMARY accept signal in checklist mode.
    `votes` = total judge calls, spent as votes//2 order-swapped PAIRS: each pair asks
    the same comparison in both presentation orders and its verdict counts ONLY if it
    survives the swap. ~26% of raw pairwise VLM verdicts flip with presentation order
    (position bias, arXiv 2606.18451/2606.20364); the old majority-over-alternating-
    orders let a position-biased split read as a legitimate 1-1 tie, whereas
    discarding order-inconsistent verdicts both de-biases the signal and makes an
    all-flips outcome an honest 'no real difference'. Majority over the consistent
    pairs; zero consistent pairs or a split -> 'tie'. Pairwise selection is far more
    stable than the absolute 0..1 scores it replaces (BlenderAlchemy / GPTEval3D),
    and BlenderGym shows compute on verification beats compute on more generation."""
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    wins = {"A": 0, "B": 0}
    whys = []
    for _ in range(max(1, int(votes) // 2)):
        w1, why1, u1 = _ab_once(photo, a_png, b_png, backend, model)
        w2, why2, u2 = _ab_once(photo, b_png, a_png, backend, model)
        w2 = "A" if w2 == "B" else "B"          # map back to the true labels
        for u in (u1, u2):
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["completion_tokens"] += u["completion_tokens"]
        if w1 != w2:
            continue                            # order-dependent verdict -- discard
        wins[w1] += 1
        why = why1 or why2
        if why:
            whys.append(("[candidate] " if w1 == "B" else "[prev-best] ") + why)
    winner = "B" if wins["B"] > wins["A"] else ("A" if wins["A"] > wins["B"] else "tie")
    return winner, "; ".join(whys)[:220], usage


CHECKLIST_SYS = ("You are an architectural inspector writing a verification checklist "
                 "for a 3D model of a building. Reply ONLY with JSON.")


def checklist_step(images, brief, backend, model, n=12, views=None):
    """One-time: derive binary YES/NO checks from the reference (CADCodeVerify / TIFA
    style question-based verification). Each check is answerable from a render of the
    candidate model ALONE and phrased so YES = matches the reference. Scoring by
    pass-fraction is far more stable than a holistic 0..1 VLM score, and every failed
    check is a concrete, targeted fix for the refine step -- so the same call that
    scores also produces the feedback.
    `views`: optional [(key, description), ...] of the renders the candidate will be
    judged in; each check must then name the ONE view that answers it, so the
    inspector later sees exactly one image per question (a reference + multi-image
    panel pushed a VLM judge into answering purely by position, arXiv 2606.20364;
    it also fixes checks that were unanswerable from the view they were asked in)."""
    vtxt, vfield = "", ""
    if views:
        vtxt = ("\nThe candidate model will be rendered in these views: " +
                "; ".join('"%s" = %s' % (k, d) for k, d in views) +
                '. Give EVERY check a "view" field naming the ONE view it can be '
                'answered from (e.g. roof/plan checks from a top view, facade '
                'checks from a street view).')
        vfield = ',"view":"%s"' % ('"|"'.join(k for k, _ in views))
    user = ("The image is the REFERENCE for a target building." +
            (("\nMeasured brief of the reference:\n" + brief) if brief else "") +
            ("\nWrite %d binary checks that a CORRECT 3D model of this building must "
             "pass. Each check must be answerable by looking at a render of the "
             "candidate model ALONE (no reference beside it), concrete and independently "
             "verifiable, and phrased so YES = matches the reference (e.g. 'Does the "
             "tallest block sit at the far end?', 'Does the tall block have 7 floors?'). "
             "Cover massing, proportions, roof, facade, and EACH distinctive feature."
             + vtxt + " Reply ONLY:\n"
             '{"checks":[{"q":"...","cat":"massing"|"proportions"|"roof"|"facade"|"feature"'
             + vfield + '},...]}')
            % n)
    txt, usage = _vision(CHECKLIST_SYS, user, images, backend, model, max_tokens=1400)
    m = re.search(r"\{.*\}", txt, re.S)
    checks = [c for c in json.loads(m.group(0)).get("checks", [])
              if isinstance(c, dict) and c.get("q")]
    if not checks:
        raise ValueError("checklist came back empty")
    if views:
        keys = [k for k, _ in views]
        for c in checks:
            if c.get("view") not in keys:
                c["view"] = keys[0]
    return checks, usage


def _checklist_once(img, intro, sel, backend, model):
    """One inspector sample over one view: {check_index_in_sel: answer_dict}."""
    qs = "\n".join("%d. %s" % (i + 1, c["q"]) for i, c in enumerate(sel))
    system = ("You are a strict inspector of 3D building renders. Judge each check ONLY "
              "from what is clearly visible in the render. Reply ONLY with JSON.")
    user = (intro + " Answer every check strictly "
            "(pass=true only if clearly true in the render):\n" + qs +
            '\nReply ONLY: {"answers":[{"i":1,"pass":true,"note":""},...]} -- one entry '
            'per check, "note" = short reason when pass=false.')
    txt, usage = _vision(system, user, [img], backend, model, max_tokens=1400)
    m = re.search(r"\{.*\}", txt, re.S)
    amap = {}
    if m:
        try:
            for x in json.loads(m.group(0)).get("answers", []):
                if isinstance(x, dict):
                    amap[int(x.get("i", 0)) - 1] = x
        except Exception:
            pass
    return amap, usage


def checklist_score(render, checks, backend, model, cats=None, top=None, k=1,
                    normal=None, street2=None):
    """Answer the reference-derived checks against the render ALONE (the questions
    already encode the reference facts, so the inspector never scores holistically).
    Returns (pass_rate, failed_checks, usage).

    Judge-v2 upgrades (2026-07-11 research pass, related_work_methods.md §J):
      * one view per question -- checks tagged "view":"top" (or untagged roof
        checks) are asked against the top render ALONE, the rest against the main
        render ALONE, instead of one call carrying every image (multi-image panels
        push VLM judges into position answering, arXiv 2606.20364);
      * k>1 samples the inspector k times and each check passes by MAJORITY --
        single-sample binary answers flip 1-2 checks on IDENTICAL geometry (the
        documented stochastic inconsistency of absolute VLM judging), and per-check
        majority voting is the checklist-shaped version of 'mean of k samplings'."""
    use = [c for c in checks if not cats or c.get("cat") in cats] or checks
    intro_main = "The image is a render of a candidate 3D model."
    intro_top = ("The image is a straight-down top view render of a candidate 3D "
                 "model (roof and plan only).")
    # dual-channel judging (2026-07-15 research pass, §P): colored renders HIDE
    # geometry defects from VLM judges (arXiv 2606.20364: ~50/50 on obvious
    # defects; Gen3DEval scores geometry on appearance-stripped renders). Shape
    # questions (massing/proportions) are therefore asked against the untextured
    # matcap render; facade/feature questions stay on the beauty render.
    intro_norm = ("The image is an UNTEXTURED matcap render of a candidate 3D "
                  "model showing pure geometry -- judge SHAPE only and ignore "
                  "that there are no colors or materials.")
    intro_s2 = ("The image is a render of a candidate 3D model from a SECOND "
                "street viewpoint showing a different side of the building.")
    s2sel = [c for c in use if c.get("view") == "street2"] if street2 else []
    rest = [c for c in use if c not in s2sel]
    if top:
        topsel = [c for c in rest
                  if c.get("view") == "top" or (not c.get("view") and c.get("cat") == "roof")]
        mainsel = [c for c in rest if c not in topsel]
    else:
        topsel, mainsel = [], list(rest)
    geosel = []
    if normal:
        geosel = [c for c in mainsel if c.get("cat") in ("massing", "proportions")]
        mainsel = [c for c in mainsel if c not in geosel]
    groups = ([(render, intro_main, mainsel)] if mainsel else []) \
        + ([(street2, intro_s2, s2sel)] if s2sel else []) \
        + ([(top, intro_top, topsel)] if topsel else []) \
        + ([(normal, intro_norm, geosel)] if geosel else [])
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    votes = {}                                   # id(check) -> pass count
    notes = {}
    k = max(1, int(k))
    for _ in range(k):
        for img, intro, sel in groups:
            amap, u = _checklist_once(img, intro, sel, backend, model)
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["completion_tokens"] += u["completion_tokens"]
            for i, c in enumerate(sel):
                x = amap.get(i)
                if x and x.get("pass"):
                    votes[id(c)] = votes.get(id(c), 0) + 1
                elif x and x.get("note"):
                    notes[id(c)] = str(x["note"])[:120]
    passed, failed = 0, []
    for c in use:
        if votes.get(id(c), 0) * 2 > k:          # strict majority of the k samples
            passed += 1
        else:
            failed.append({"q": c["q"], "cat": c.get("cat", ""),
                           "note": notes.get(id(c), "")})
    return round(passed / len(use), 3), failed, usage


# Synthetic aux views are WEAK references: they may hallucinate, so they inform the
# brief + the first generation but never the checklist or scoring (which stay on the
# real photo), and the prompt tells the model where its trust must lie.
AUX_NOTE = ("\nThe FIRST image is the authoritative REAL reference. The LAST {n} "
            "image(s) are SYNTHESIZED auxiliary views of the same building from other "
            "angles -- use them for the sides hidden in the real reference (back "
            "facade, far end), but wherever they conflict with the real reference, "
            "TRUST THE REAL REFERENCE.")

ANALYZE_SYS = ("You are an architectural analyst decomposing ONE reference image of a "
               "building (a physical model photo or a real photo). Reply ONLY with JSON.")


def analyze_step(images, backend, model, n_aux=0):
    """One-time structured decomposition of the reference -> a compact BRIEF injected
    into every later generation prompt. Grounding all iterations in the same measured
    breakdown stops the spec drifting (previously every refine re-eyeballed the photo
    from scratch and 'discovered' a different building each time)."""
    user = ((AUX_NOTE.format(n=n_aux) + "\n") if n_aux else "") + (
        'Use this coordinate convention: the short end NEAREST the camera = "+x"; the far end = "-x"; '
        'the long facade visible on the LEFT = "-y" (the front). Analyse the building and reply ONLY with JSON:\n'
        '{"footprint_ratio": <long/short, number>, "est_length_m": <number>,\n'
        ' "height_to_length": <tallest point height / footprint length, as VISIBLE in the image, number>,\n'
        ' "storey_zones": [{"x":[a,b],"floors":N}, ...]  (2-4 zones as fractions 0..1 from -x far to +x near, '
        'with the floor count VISIBLE in each zone -- count the floor lines),\n'
        ' "features": [{"name":"vault|ridged white roof|green louvred volume|masonry entrance tower|open '
        'colonnade/plaza cage|rooftop plant|other", "where":"which end/side + along-fractions", "size_hint":"..."}],\n'
        ' "materials": "<one line>", "nearest_to_camera": "<one line: what sits at the +x end>"}')
    txt, usage = _vision(ANALYZE_SYS, user, images, backend, model, max_tokens=700)
    m = re.search(r"\{.*\}", txt, re.S)
    return (m.group(0) if m else txt).strip(), usage


# --------------------------------------------------------------------------
# ASSEMBLE MODE: the agent emits a JSON parts-spec built via components.py,
# instead of writing raw bpy. Far more reliable + captures distinctive parts.
# The schema the spec agent sees, assembled per REGION: a shared core plus
# the region's own dialect lines. Flat growth was the contamination path --
# every new region's vocabulary would land in front of every other region's
# agent (a Kensington terrace could grow a canal-house stepped gable). Tags
# are PROVISIONAL until two-region mining data exists (library/learn.py);
# the criterion then is: demanded in both regions -> core, one -> dialect.
SPEC_LINES = [
    ('core',
     'footprint: [L, W]   (L = long axis, W = depth, metres)'),
    ('core',
     'colors: {wall:[r,g,b],frame:[r,g,b],glaze:[r,g,b],roof:[r,g,b]} optional LINEAR RGB 0..1; use observed material colours, including distinctive red glazed masonry. Only use visible evidence; do not tint the whole building from foliage or vehicles.'),
    ('core',
     'floors: integer   (overall default, used if a mass omits its own)'),
    ('core',
     'masses: list of 0-4 volumes (empty ONLY when extra_parts builds an open structure) -- COMPOSE the building from these instead of one box:'),
    ('core',
     '   {"x":[a,b], "y":[c,d], "floors":N, "facade":"glass"|"masonry"}  (x,y are FRACTIONS 0..1 of the footprint; e.g. a TALL block at one end + a LOWER wing with fewer floors; 3 masses with decreasing floors = stepped roof TERRACES)'),
    ('core',
     'facade: "glass" | "masonry"   (used only when you give NO masses; most modern campus buildings are "glass")'),
    ('core',
     'frame: {"x":[a,b], "y":[c,d], "over":m, "height":m, "bays":N, "plaza":{"end":"-x"|"+x","depth":m}}  OR null  -- white exoskeleton cage hugging the facades; "plaza" continues the cage past that end over OPEN ground (freestanding colonnade)'),
    ('core',
     'roof: list of any of:'),
    ('core',
     '   {"type":"vault","end":"-x"|"+x"|"-y"|"+y","span_frac":0..1,"radius":m}   ribbed glass barrel at that end of the roof; its RIDGE RUNS ALONG the building axis and its arch face closes that end'),
    ('core',
     '   {"type":"ridges","frac":[a,b],"count":N}   solid WHITE ridged/fabric roof between fractions a..b of the length (large bright roof areas)'),
    ('core',
     '   {"type":"sawtooth","frac":[a,b],"count":N}   thin slanted rooflight slats (small skylight strips)'),
    ('core',
     '   {"type":"plant","boxes":[[px,py,height,sx,sy],...]}   mechanical boxes (px,py relative to centre; snapped onto the roof of the mass under their centroid). Use 3-6 boxes: real roofs have a DENSE plant terrace, not one lone unit'),
    ('core',
     '   {"type":"dome","at":[px,py],"radius":m,"material":"copper"|"stone"|"white"}   rounded dome snapped onto the roof of the mass under it (set when the photo shows a dome/rotunda)'),
    ('core',
     'volumes: list of {"type":"green_glass","side":"-y"|"+y"|"-x"|"+x","along":[a,b],"height_frac":0..1,"depth":m}   a louvred green-glass mass flush to that facade spanning fractions a..b'),
    ('core',
     'entrance: {"side":"-y"|"+y"|"-x"|"+x","along":[a,b],"height_frac":0..1}   masonry entrance TOWER (windows + sign) + steps; height_frac ~0.6 reads as a real tower, not a porch'),
    ('core',
     'typology: "terrace" | "institutional"   READ OFF THE IMAGERY + building type. "terrace" = London housing row (auto: chimney valley roof, balconies, porticos, railings, stucco band). "institutional" = college/museum/office block: NONE of the housing parts, flat parapet roof default, no stucco band -- use this for every campus/civic building or it will wrongly render as housing'),
    ('terrace_victorian',
     'colonnade: {"faces":["-y"],"z0":m,"z1":m,"spacing_m":6} OR null   giant-order engaged stone columns (shaft+capital+base+entablature) over a base course -- grand institutional stone fronts (set z0..z1 to the columned storeys)'),
    ('terrace_victorian',
     'balustrade: true|false   balustraded stone parapet (posts + rail) along every roofline -- Edwardian/classical stone blocks'),
    ('core',
     'arch_windows: true|false  (+ optional "arch_row": storey index)   round-arched window heads with a glazed lunette on that storey (default the main floor) -- set when the photo shows arched windows'),
    ('core',
     'podium: {"floors": 1|2} OR null   ground floor(s) become a FULL-HEIGHT GLASS CURTAIN WALL with dark mullions + a dark fascia band above (institutional/campus buildings: set it when the street view shows continuous glazing at street level under a solid upper facade)'),
    ('core',
     'fins: {"faces":["-y","+y"],"spacing":0.9,"depth":0.45,"mat":"white"|"stone"|"sign"} OR true OR null   brise-soleil screen: closely-spaced VERTICAL FINS over the upper facade (set when the photo shows a finned/louvred concrete or metal facade -- e.g. 1960s campus slabs)'),
    ('core',
     'ribbon: {"glaze_frac":0.52,"mullion_m":1.3,"spandrel":"white"|"sign"|"stone"} OR null   RIBBON facade: every storey is a CONTINUOUS HORIZONTAL glazing strip (glaze_frac = how much of the storey height is glass) alternating with a solid SPANDREL band, plus a regular vertical MULLION rhythm (mullion_m = mullion spacing). Set this for post-war MODERNIST SLABS whose facade reads as horizontal bands of window running the full length -- NOT individual punched windows. (Mutually exclusive with punched windows; the whole street facade becomes bands.)'),
    ('terrace_victorian',
     'terrace: {"bay_m": m, "stucco_floors": 0|1|2, "balcony": true, "railings": true, "roof_form": "valley"|"gable"|"flat"|"mansard", "roof_tone": "dark"|"mid"|"light", "dormers": true|false, "pediment": true|false, "shopfront": true|false, "bay_windows": true|false} OR null -- articulation of masonry TERRACE ROWS (joined houses): bay_m = house unit width (party-wall pilasters + one door portico per bay; read it off the photo), stucco_floors = how many lowest storeys are white stucco (rest = brick), balcony = continuous first-floor cast-iron balcony, railings = street-edge iron railings. roof_form/roof_tone: READ OFF THE SATELLITE VIEW -- "valley" = the London M-roof (a terrace row shows TWO parallel dark pitched strips from the air), "gable" = one ridge, "flat" = flat deck, "mansard" = steep truncated slope ring with a flat cap (grand Victorian blocks); tone = how dark the roof reads from above (London slate is usually "dark"). dormers = a row of small roofed windows ON the street-facing roof slope (set when the photo shows attic windows in the roof). pediment = central triangular pediment above the front cornice. shopfront = ground floor is RETAIL (continuous glazing + dark fascia) instead of stucco-band windows -- set it when the street view shows shops/pub/cafe at street level. bay_windows = canted projecting window bay beside each door portico (the classic London terrace bay -- set it when the photo shows ground-floor windows stepping OUT from the facade)'),
    ('core',
     'extra_parts: [{"type":"<learned part name>", ...typed params...}] OR null -- instances of LEARNED library parts. Only the part names documented in the schema lines above (if any) are valid; coordinates are building-local like every part. Use them for the distinctive one-off features of LANDMARK buildings (a pyramid crown, a stepped gable, a glazed shed) that the standard knobs cannot express.'),
    ('core',
     'ORIENTATION (critical): -y = FRONT long facade, +y = back, -x/+x = the two short ends. The render camera is an aerial 3/4 view standing NEAREST THE +x END, front facade on the left, long axis receding away. Put whatever appears NEAREST the camera in the reference at +x, and the far-end features at -x. Building centred on origin; z=0..H.'),
]


# LEGACY region names -> typology-card tags (the dialect key moved from
# geography to TYPOLOGY, 08-11 §S: a style is learned once and reused wherever
# that typology appears; geography is just where you happened to learn it)
REGION_TAGS = {"london": {"terrace_victorian", "rail_terminus"},
               "canary_wharf": {"cbd_tower"}}


def spec_schema(region="london"):
    """Backward-compatible entry: an area REGION resolves to its typology tags.
    Per-building card selection calls spec_schema_tags directly."""
    return spec_schema_tags(REGION_TAGS.get(region, {region}))


def spec_schema_tags(tags):
    """Core lines + the dialect lines of the given TYPOLOGY tags, in authoring
    order. Learned lines live in spec_dialect.json (data, not source)."""
    tags = set(tags) | {"core"}
    lines = [l for t, l in SPEC_LINES if t in tags]
    dj = str(SPEC_DIALECT_JSON)
    if os.path.exists(dj):
        for e in json.load(open(dj)):
            if e.get("region") in tags:
                lines.append(e["line"])
    return "".join(l + "\n" for l in lines)


# city_sk default -- byte-identical to the old flat SPEC_SCHEMA constant
SPEC_SCHEMA = spec_schema('london')


# A worked example (a DIFFERENT building) so the agent learns the spec format +
# coordinate convention without copying the target -- few-shot in-context learning.
EXAMPLE_SPEC = (
    '{"footprint":[70,30],\n'
    ' "masses":[{"x":[0,0.4],"y":[0,1],"floors":8,"facade":"glass"},\n'
    '           {"x":[0.4,0.75],"y":[0,1],"floors":5,"facade":"glass"},\n'
    '           {"x":[0.75,1],"y":[0,1],"floors":4,"facade":"glass"}],\n'
    ' "frame":{"x":[0,1],"y":[0,1],"over":2,"height":33.6,"bays":9,"plaza":{"end":"+x","depth":9}},\n'
    ' "roof":[{"type":"vault","end":"-x","span_frac":0.3,"radius":8},\n'
    '         {"type":"ridges","frac":[0.4,0.7],"count":7},\n'
    '         {"type":"plant","boxes":[[-20,3,2.5,9,7]]}],\n'
    ' "volumes":[{"type":"green_glass","side":"+x","along":[0.2,0.8],"height_frac":0.55,"depth":5}],\n'
    ' "entrance":{"side":"-y","along":[0.85,0.97],"height_frac":0.6}}'
)

# ---- Library-learning TEMPLATES (SceneCraft-style): the agent starts from the closest
# generic archetype and ADAPTS its numbers, instead of writing a building from scratch.
TEMPLATES = {
    "modern_block": {"footprint": [50, 28], "floors": 7, "facade": "glass",
                     "frame": {"over": 4, "bays": 6},
                     "roof": [{"type": "plant", "boxes": [[0, 0, 3, 12, 8]]}],
                     "entrance": {"side": "-y", "along": [0.4, 0.6]}},
    # long glazed slab, terraced toward the camera (+x), tall block + ribbed vault at
    # the far -x end, white ridged roof mid, cage + plaza colonnade -- the hand-tuned
    # Business School composition (components.BS_DESC3), generalised as a template.
    "terraced_long_glass": {"footprint": [95, 40], "floor_h": 4.2,
        "masses": [{"x": [0.0, 0.45], "y": [0, 1], "floors": 7, "facade": "glass"},
                   {"x": [0.45, 0.78], "y": [0, 1], "floors": 5, "facade": "glass"},
                   {"x": [0.78, 1.0], "y": [0, 1], "floors": 4, "facade": "glass"}],
        "frame": {"x": [0, 1], "y": [0, 1], "over": 2, "height": 29.4, "bays": 12,
                  "plaza": {"end": "+x", "depth": 12}},
        "roof": [{"type": "vault", "end": "-x", "span_frac": 0.28, "radius": 11},
                 {"type": "ridges", "frac": [0.45, 0.75], "count": 8},
                 {"type": "plant", "boxes": [[-30, 5, 2.5, 10, 7], [-24, -5, 2.8, 8, 6],
                                             [-36, -3, 2.3, 6, 5]]},
                 {"type": "plant", "boxes": [[15, 4, 2.2, 8, 6], [10, -4, 2.5, 7, 5]]}],
        "volumes": [{"type": "green_glass", "side": "+x", "along": [0.15, 0.85], "height_frac": 0.55, "depth": 6}],
        "entrance": {"side": "-y", "along": [0.85, 0.98], "height_frac": 0.6}},
    "tall_block_plus_wing": {"footprint": [92, 34],
        "masses": [{"x": [0, 0.35], "y": [0, 1], "floors": 6, "facade": "glass"},
                   {"x": [0.35, 1], "y": [0, 1], "floors": 4, "facade": "glass"}],
        "frame": {"x": [0.33, 1], "y": [0, 1], "over": 2.5, "height": 26, "bays": 9},
        "roof": [{"type": "vault", "end": "-x", "span_frac": 0.3, "radius": 7},
                 {"type": "ridges", "frac": [0.4, 0.9], "count": 10},
                 {"type": "plant", "boxes": [[8, 0, 3, 12, 8]]}],
        "volumes": [{"type": "green_glass", "side": "-y", "along": [0.55, 0.78], "height_frac": 0.7, "depth": 5}],
        "entrance": {"side": "-y", "along": [0.42, 0.58]}},
    "masonry_tower": {"footprint": [24, 24], "floors": 9, "facade": "masonry",
                      "masses": [{"x": [0, 1], "y": [0, 1], "floors": 9,
                                  "facade": "masonry", "wall": "stone"}],
                      "roof": [{"type": "plant", "boxes": [[0, 0, 2, 8, 8]]}]},
}
TEMPLATES_TEXT = "\n".join("[%s] %s" % (k, json.dumps(v)) for k, v in TEMPLATES.items())

# Two-step (analyse -> assemble), à la 3D-GPT / SceneCraft blueprint: plan the building
# before emitting parts, and require one part per listed feature.
SPEC_SYS_HEAD = ("You design a building by emitting a compact JSON DESCRIPTION; the system computes "
            "ALL coordinates so the result is architecturally coherent (the frame wraps the block, "
            "roof features sit on the roof, volumes are flush to the named facade, the entrance is "
            "at ground level). You do NOT place parts by coordinate. Metres; -y is the FRONT facade. "
            "Work in TWO steps. STEP 1 -- analyse the target in 2-3 lines (footprint L x W, floors / "
            "height, distinctive features, and any PARTS OF DIFFERENT HEIGHTS) and PICK the closest "
            "TEMPLATE below. STEP 2 -- COPY that template and ADAPT its numbers (footprint, floors, "
            "mass splits, and each feature's position / size / end) to match the reference -- do NOT "
            "write from scratch, and keep every feature the target actually has. Output ONE ```json "
            "block following this schema:\n")


def build_spec_sys(region="london"):
    """The spec-writing system prompt for a REGION: shared core schema + that
    region's dialect lines (learned ones included via spec_dialect.json). Built
    per call, not at import -- the flat import-time constant meant a Canary
    Wharf building could never see the vocabulary its own region had learned."""
    return ("You design a building by emitting a compact JSON DESCRIPTION; the system computes "
            "ALL coordinates so the result is architecturally coherent (the frame wraps the block, "
            "roof features sit on the roof, volumes are flush to the named facade, the entrance is "
            "at ground level). You do NOT place parts by coordinate. Metres; -y is the FRONT facade. "
            "Work in TWO steps. STEP 1 -- analyse the target in 2-3 lines (footprint L x W, floors / "
            "height, distinctive features, and any PARTS OF DIFFERENT HEIGHTS) and PICK the closest "
            "TEMPLATE below. STEP 2 -- COPY that template and ADAPT its numbers (footprint, floors, "
            "mass splits, and each feature's position / size / end) to match the reference -- do NOT "
            "write from scratch, and keep every feature the target actually has. Output ONE ```json "
            "block following this schema:\n" + spec_schema(region) +
            "\nTEMPLATES -- start from the closest, then adapt every number to the reference:\n"
            + TEMPLATES_TEXT)


SPEC_SYS_TAIL = ("\nTEMPLATES -- start from the closest, then adapt every number to the reference:\n"
                 + TEMPLATES_TEXT)


def typology_exemplar(bdir):
    """The verified same-typology worked example for this building's card pick,
    or None. Registry: typology_exemplars.json (best refined spec per card)."""
    try:
        cards = json.load(open(os.path.join(bdir, "typology.json"))).get("cards")
        reg = json.load(open(EXEMPLARS_PATH))
        for c in cards or []:
            if c in reg:
                return reg[c]["spec"]
    except Exception:
        pass
    return None


def area_region(out):
    """The area's region tag: data/<area>/region.json {"region": ...}, default
    london (city_sk predates regions). Written by city_pilot on bootstrap or by
    hand; the typology-card upgrade will replace this with per-building picks."""
    try:
        return json.load(open(os.path.join(out, "region.json")))["region"]
    except Exception:
        return "london"


def build_spec_sys_tags(tags, exemplar=None):
    """Spec system prompt from an explicit TYPOLOGY-TAG set (per-building card
    selection); build_spec_sys(region) remains the area-default path. `exemplar`
    is a VERIFIED same-typology reconstruction (self-distillation, 08-12: the
    refine loop's best outputs become the one-shot few-shot) appended after the
    templates so the agent anchors on a proven spec of the same building type."""
    ex = ""
    if exemplar:
        ex = ("\n\nWORKED EXAMPLE -- a VERIFIED reconstruction of a building of "
              "this same type (adapt its structure and level of detail; never "
              "copy its dimensions):\n" + json.dumps(exemplar))
    return (SPEC_SYS_HEAD + spec_schema_tags(tags) + SPEC_SYS_TAIL + ex)


SPEC_SYS = build_spec_sys("london")     # legacy single-building path


def hidden_brief_step(images, backend, model):
    """Max-subscription alternative to synth_views.py (no image-generation key needed):
    Claude looks at the real reference and INFERS what the hidden sides most plausibly
    look like -- as text, not pixels -- with explicit confidence per item. Injected
    beside the BRIEF into every generation prompt; the real reference wins on conflict."""
    system = ("You are an architectural analyst inferring the UNSEEN sides of a building "
              "from one photo. Be explicit about uncertainty. Reply ONLY with JSON.")
    user = ('The image shows ONE view of a building (a physical model photo). Infer what '
            'the HIDDEN sides most plausibly look like, using visible evidence (symmetry, '
            'floor bands continuing around corners, roof elements crossing the roofline) '
            'and typical architectural logic. Reply ONLY with JSON:\n'
            '{"back_facade": "<likely appearance of the hidden long facade>",\n'
            ' "far_end": "<likely appearance of the far short end>",\n'
            ' "hidden_roof": "<likely content of roof areas not visible>",\n'
            ' "confidence": {"back_facade":"high|med|low","far_end":"...","hidden_roof":"..."},\n'
            ' "assumptions": ["<each assumption made>", ...]}')
    txt, usage = _vision(system, user, images, backend, model, max_tokens=700)
    m = re.search(r"\{.*\}", txt, re.S)
    return (m.group(0) if m else txt).strip(), usage


def _context_blocks(brief, history):
    """Shared prompt context: the one-time reference brief + what was already tried.
    The history block is what breaks the old 'add the barrel vault' x7 loop -- without
    it the agent had amnesia and re-applied the same failed fix every iteration."""
    ctx = ""
    if brief:
        ctx += ("\n\nBUILDING BRIEF (one-time analysis of the reference; trust it for "
                "layout and floor counts):\n" + brief)
    if history:
        lines = "\n".join("  iter %s: tried %r -> score %.3f (%s)" %
                          (h["iter"], h["fix"][:80], h["score"],
                           "accepted" if h["accepted"] else "rejected") for h in history[-4:])
        ctx += ("\n\nRECENT ATTEMPTS (fix tried -> resulting score):\n" + lines +
                "\nDo NOT repeat a fix that already failed. If a feature exists but reads "
                "wrong, ADJUST its parameters (position / size / end / span) instead of "
                "adding it again.")
    return ctx


PHASE_RULES = {
    # teach-step-by-step (supervisor feedback): get the MASSING right first, freeze it,
    # then place features -- instead of regenerating the whole building every iteration.
    "massing": ("\n\nPHASE 1 -- MASSING ONLY: output a spec containing ONLY the keys "
                "footprint, floor_h, masses (and optionally frame). NO roof / volumes / "
                "entrance yet. Get the footprint ratio, mass split and floor counts right."),
    "features": ("\n\nPHASE 2 -- FEATURES: footprint, floor_h and masses are LOCKED (the "
                 "system overwrites any change you make to them). Keep them verbatim and "
                 "only add/adjust frame, roof, volumes and entrance."),
    "full": "",
}


def gen_spec(images, prev_spec, critique, error, backend, model,
             brief=None, history=None, phase="full", n_aux=0, region="london",
             tags=None, exemplar=None):
    ctx = _context_blocks(brief, history) + PHASE_RULES.get(phase, "")
    if prev_spec is None:
        user = ("Image 1 is the TARGET building -- your reference. PICK the closest "
                "template (in the system prompt) and ADAPT it to match THIS building's "
                "PROPORTIONS (long:short footprint ratio, height) and features. Output ONLY "
                "the ```json building description."
                + (AUX_NOTE.format(n=n_aux) if n_aux else "") + ctx)
    elif error:
        user = ("Your previous JSON spec failed with:\n" + error +
                "\n\nFix it and output ONLY the corrected full ```json spec." + ctx +
                "\n\nPrevious spec:\n" + prev_spec)
    else:
        ref = ("Image 1 = the target reference, image 2 = your current render."
               if len(images) <= 2 else
               "The first %d images are the TARGET reference views (street-level "
               "photo first, then a satellite/top view); the LAST image is your "
               "current render." % (len(images) - 1))
        user = (ref + " Most "
                "important fix: " + (critique or "") + ctx + "\n\nAdjust the JSON description "
                "(proportions and/or parts) to match the target better. Output ONLY the "
                "corrected full ```json description.\n\nPrevious:\n" + prev_spec)
    sys_prompt = (build_spec_sys_tags(tags, exemplar) if tags is not None
                  else build_spec_sys(region))
    from img2city.kit import material_names
    sys_prompt += ("\nActual kit material names (use these exact keys for material "
                   "parameters; do not invent names): " + ", ".join(material_names()))
    text, usage = _vision(sys_prompt, user, images, backend, model)
    m = re.search(r"\{.*\}", text, re.S)
    return (m.group(0) if m else text).strip(), usage


def brief_consistency(desc, brief):
    """Deterministic massing check against the measured BRIEF. Root cause of the
    'chunky' look across every run: the brief measures the footprint ratio / length /
    floor counts correctly, but the agent's spec kept shrinking them (60-68 m specs
    vs ~95 m reality) and nothing pushed back. Violations are fed back exactly like
    schema errors, BEFORE Blender -- generous tolerances, and only while the massing
    is still editable."""
    try:
        b = json.loads(re.search(r"\{.*\}", brief, re.S).group(0))
    except Exception:
        return []
    v = []
    fp = desc.get("footprint") or []
    if len(fp) == 2 and all(isinstance(x, (int, float)) and x > 0 for x in fp):
        L, W = float(fp[0]), float(fp[1])
        r = b.get("footprint_ratio")
        if isinstance(r, (int, float)) and r > 0 and abs(L / W - r) / r > 0.25:
            v.append("footprint ratio L/W=%.2f but the brief measured %.2f" % (L / W, r))
        el = b.get("est_length_m")
        if isinstance(el, (int, float)) and el > 0 and abs(L - el) / el > 0.30:
            v.append("length L=%.0f m but the brief estimated %.0f m" % (L, el))
    try:
        bmax = max(int(z["floors"]) for z in (b.get("storey_zones") or []))
    except Exception:
        bmax = None
    try:
        smax = max(int(m.get("floors", 1)) for m in (desc.get("masses") or []))
    except Exception:
        smax = None
    if bmax and smax and abs(smax - bmax) > 1:
        v.append("tallest mass has %d floors but the brief counted %d" % (smax, bmax))
    # the anti-chunkiness constraint: with an auto-fit camera only PROPORTIONS are
    # visible, and height/length is the one the agent kept getting wrong (0.49 specs
    # vs ~0.35 reality read as a stubby block). Scale-free, unlike est_length_m,
    # which the brief itself underestimates.
    ht = b.get("height_to_length")
    if (isinstance(ht, (int, float)) and ht > 0 and smax
            and len(fp) == 2 and isinstance(fp[0], (int, float)) and fp[0] > 0):
        Hs = smax * float(desc.get("floor_h", 4.3))
        if abs(Hs / float(fp[0]) - ht) / ht > 0.30:
            v.append("tallest-height/length = %.2f but the brief measured %.2f -- "
                     "adjust footprint length or floor_h" % (Hs / float(fp[0]), ht))
    return v


EXEMPLARS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "typology_exemplars.json")


def load_components_src():
    """components.py + parts_learned.py as one Blender-executable source blob
    (see img2city.kit.load_kit_src -- kept here because every stage imports it
    from generate)."""
    return load_kit_src()


def spec_to_code(spec_text, components_src):
    """Embed components.py + a validated JSON building DESCRIPTION, built in Blender."""
    safe = json.dumps(json.loads(spec_text))   # canonical; raises if not valid JSON
    return (components_src + "\nimport json as _json\n_desc = _json.loads(%r)\n"
            "build_building(_desc)\n" % safe)


def validate_desc(spec_text):
    """Validated-output check (CAD-Coder style): parse + schema/range-check the building
    description; return (desc, errors). Non-empty errors are fed back to the agent to
    self-repair BEFORE anything reaches Blender, so invalid specs never hit the renderer."""
    m = re.search(r"\{.*\}", spec_text, re.S)
    if not m:
        return None, ["output is not a JSON object"]
    try:
        d = json.loads(m.group(0))
    except Exception as e:
        return None, ["not valid JSON: %s" % (str(e)[:120])]
    errs = []
    from img2city.kit import material_names
    palette = set(material_names())
    from img2city import kit as _kit
    from img2city.library.audit import registry_names
    known_parts = registry_names(str(_kit.COMPONENTS_PY), "BUILDERS") | registry_names(str(_kit.PARTS_LEARNED_PY), "PARTS_LEARNED")
    for part in d.get("extra_parts") or []:
        if not isinstance(part, dict):
            errs.append("each extra_parts entry must be an object")
            continue
        if part.get("type") not in known_parts:
            errs.append("unknown extra part " + str(part.get("type")) + "; use a registered kit part")
        for key, value in part.items():
            if key == "material" or key.endswith("_material") or key.endswith("_mat"):
                if isinstance(value, str) and value not in palette:
                    errs.append(f"unknown kit material {value!r} in {key}; choose from " +
                                ", ".join(sorted(palette)))
    for channel, rgb in (d.get("colors") or {}).items():
        if channel in {"wall", "frame", "glaze", "roof", "stucco", "glass"} and not (
                isinstance(rgb, list) and len(rgb) == 3 and all(
                    isinstance(v, (int, float)) and 0 <= v <= 1 for v in rgb)):
            errs.append("colors." + channel + " must be three linear RGB values in 0..1")
    fp = d.get("footprint")
    if not (isinstance(fp, list) and len(fp) == 2 and all(isinstance(v, (int, float)) and v > 0 for v in fp)):
        errs.append('"footprint" must be [L,W] of positive numbers')
    ms = d.get("masses")
    if ms is not None:
        if not isinstance(ms, list):
            errs.append('"masses" must be a list')
        elif not ms and not d.get("extra_parts"):
            errs.append('empty "masses" requires structural extra_parts')
        else:
            for k, mm in enumerate(ms):
                for ax in ("x", "y"):
                    r = mm.get(ax)
                    if not (isinstance(r, list) and len(r) == 2 and 0 <= r[0] < r[1] <= 1):
                        errs.append('mass %d "%s" must be [a,b] with 0<=a<b<=1' % (k, ax))
                fl = mm.get("floors", 1)
                if not (isinstance(fl, int) and fl >= 1):
                    errs.append('mass %d "floors" must be a positive integer' % k)
    if d.get("frame") is not None and not isinstance(d.get("frame"), dict):
        errs.append('"frame" must be an object or null')
    for v in (d.get("volumes") or []):
        if v.get("side") not in ("-y", "+y", "-x", "+x"):
            errs.append('a volume "side" must be -y/+y/-x/+x')
    en = d.get("entrance")
    if en is not None and en.get("side") not in ("-y", "+y", "-x", "+x"):
        errs.append('entrance "side" must be -y/+y/-x/+x')
    for rf in (d.get("roof") or []):
        if rf.get("type") not in ("vault", "sawtooth", "ridges", "plant", "dome"):
            errs.append('a roof item "type" must be vault/sawtooth/ridges/plant/dome')
    tr = d.get("terrace")
    if tr is not None:
        if not isinstance(tr, dict):
            errs.append('"terrace" must be an object or null')
        else:
            if tr.get("roof_form") is not None and tr["roof_form"] not in ("valley", "gable", "flat", "mansard"):
                errs.append('terrace "roof_form" must be valley/gable/flat/mansard')
            if tr.get("roof_tone") is not None and tr["roof_tone"] not in ("dark", "mid", "light"):
                errs.append('terrace "roof_tone" must be dark/mid/light')
    if en is not None and "height_frac" in en:
        try:
            if not (0.1 <= float(en["height_frac"]) <= 1.0):
                errs.append('entrance "height_frac" must be in [0.1, 1]')
        except Exception:
            errs.append('entrance "height_frac" must be a number')
    fr = d.get("frame")
    if isinstance(fr, dict) and fr.get("plaza") is not None:
        if not (isinstance(fr["plaza"], dict) and fr["plaza"].get("end") in ("-x", "+x")):
            errs.append('frame "plaza" must be {"end":"-x"|"+x","depth":m}')
    return d, errs


def main():
    ap = argparse.ArgumentParser(description="Agent generates a Blender model of a building from its images")
    ap.add_argument("--data", required=True, help="folder containing satellite.png and/or streetview.png")
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--model", default=config.SPEC_MODEL,
                    help="spec model; '<provider>:<model>' pins the provider")
    ap.add_argument("--max-iters", type=int, default=6)
    ap.add_argument("--stop-score", type=float, default=0.85)
    ap.add_argument("--ref", default=None,
                    help="target reference image to MATCH (path, or filename inside --data); "
                         "overrides streetview as the critic target, e.g. modelpic.jpeg")
    ap.add_argument("--view", choices=["street", "aerial"], default="street",
                    help="render viewpoint to match the reference: 'street'=frontal worm's-eye, "
                         "'aerial'=high 3/4 (use with an aerial/model reference like modelpic)")
    ap.add_argument("--mode", choices=["code", "assemble"], default="code",
                    help="'code'=agent writes raw bpy (baseline); 'assemble'=agent emits a JSON "
                         "parts spec built via components.py (reliable, captures distinctive parts)")
    ap.add_argument("--hidden-brief", action="store_true",
                    help="one-time Claude INFERENCE of the unseen sides (text, not "
                         "pixels) injected beside the brief -- the Max-subscription "
                         "alternative to --aux-refs synthetic images (Claude cannot "
                         "generate images, but it can reason about hidden geometry)")
    ap.add_argument("--aux-refs", default=None,
                    help="comma-separated SYNTHETIC auxiliary views (e.g. from "
                         "synth_views.py; paths relative to --data). Weak references: "
                         "they inform the BRIEF and the FIRST generation only -- the "
                         "checklist and all scoring stay on the real --ref photo")
    ap.add_argument("--tags", default=None,
                    help="comma-separated typology tags for assemble-mode schema; "
                         "omit for the regional default, '' for core vocabulary only")
    ap.add_argument("--init-desc", default=None,
                    help="path to a JSON building description (e.g. from img2city.prior.predict's "
                         "image->params model) to SEED iteration 0 instead of the LLM's first guess")
    ap.add_argument("--judge", choices=["checklist", "rubric"], default="checklist",
                    help="'checklist'=binary question checklist + order-swapped pairwise "
                         "vote + IoU veto (default); 'rubric'=old absolute rubric scoring")
    ap.add_argument("--ab-votes", type=int, default=2,
                    help="total pairwise judge calls per accept decision in checklist "
                         "mode, spent as votes//2 order-swapped pairs; only "
                         "swap-consistent verdicts count (position-bias filter)")
    ap.add_argument("--iou-guard", type=float, default=0.05,
                    help="veto a pairwise win if silhouette IoU regresses by more than this")
    ap.add_argument("--inspector-k", type=int, default=3,
                    help="checklist inspector samples per iteration; each check passes "
                         "by majority vote (1 = old single-sample behaviour, which "
                         "flips 1-2 checks on identical geometry)")
    ap.add_argument("--ds-guard", type=float, default=0.06,
                    help="veto a pairwise win if the DreamSim perceptual distance to "
                         "the reference regresses by more than this (0 = disable; "
                         "ignored when dreamsim is not installed)")
    ap.add_argument("--judge-model", default=config.JUDGE_MODEL,
                    help="cheaper model for the PAIRWISE VOTE calls only, e.g. "
                         "an explicit Claude model; default = IMG2CITY_JUDGE_MODEL. The "
                         "checklist INSPECTOR stays on the strong model: measured on run "
                         "20260704-213717, Haiku passed 12/12 checks on a render where "
                         "the strong model passed 4/12 -- a lenient inspector inflates "
                         "scores, stops the run early and starves the agent of real fixes")
    ap.add_argument("--unlock-after", type=int, default=2,
                    help="unlock the phase-A massing lock after this many consecutive "
                         "scored iterations with a failing massing/proportions check "
                         "(checklist mode; 0 = never unlock)")
    ap.add_argument("--critic-k", type=int, default=2,
                    help="rubric-critic samples per iteration (median/mean); 1 = old noisy behaviour")
    ap.add_argument("--phase-a-iters", type=int, default=2,
                    help="iterations spent on MASSING ONLY before features (assemble mode); 0 = off")
    ap.add_argument("--no-ab", action="store_true", help="disable the pairwise A/B accept gate")
    ap.add_argument("--no-brief", action="store_true", help="skip the one-time reference analysis")
    a = ap.parse_args()

    # absolute paths: Blender runs in its OWN (read-only) working dir, so the render
    # filepath must be absolute; the Read-tool also resolves images more reliably.
    sat = os.path.abspath(os.path.join(a.data, "satellite.png"))
    sv = os.path.abspath(os.path.join(a.data, "streetview.png"))
    ref = None
    if a.ref:
        ref = a.ref if os.path.isabs(a.ref) else os.path.abspath(os.path.join(a.data, a.ref))
        if not os.path.exists(ref):
            raise SystemExit(f"--ref not found: {ref}")
    if ref:
        # ONLY the reference image (modelpic). Rule: do NOT use the satellite or
        # street-view images at all -- the agent sees and is scored against modelpic alone.
        base_imgs = [ref]
        photo = ref
    else:
        base_imgs = [p for p in (sat, sv) if os.path.exists(p)]
        photo = sv if os.path.exists(sv) else sat
    if not base_imgs:
        raise SystemExit(f"need satellite.png/streetview.png (or --ref) in {a.data}")

    aux = []
    if a.aux_refs:
        for p in (s.strip() for s in a.aux_refs.split(",")):
            if not p:
                continue
            q = p if os.path.isabs(p) else os.path.abspath(os.path.join(a.data, p))
            if os.path.exists(q):
                aux.append(q)
            else:
                print(f"  [aux] not found, skipping: {p}")
    if aux:
        print(f"  [aux] {len(aux)} synthetic view(s) -> brief + first generation only")

    genfn = gen_spec if a.mode == "assemble" else gen_step
    if a.mode == "assemble" and a.tags is not None:
        import functools
        genfn = functools.partial(
            gen_spec, tags={t.strip() for t in a.tags.split(",") if t.strip()})
    components_src = load_components_src() if a.mode == "assemble" else None
    init_desc_text = (open(a.init_desc).read() if (a.init_desc and a.mode == "assemble") else None)
    init_used = False

    run = os.path.abspath(os.path.join(a.data, "gen", time.strftime("%Y%m%d-%H%M%S")))
    os.makedirs(run, exist_ok=True)
    print(f"[generate] {a.data} (backend={a.backend}, mode={a.mode}) -> {run}\n")

    total_tokens = 0

    # One-time structured decomposition of the reference (the BRIEF): measured layout +
    # floor counts + feature list that every later prompt is grounded in.
    brief = None
    if not a.no_brief:
        try:
            brief, busage = analyze_step(base_imgs + aux, a.backend, a.model,
                                         n_aux=len(aux))
            total_tokens += busage["prompt_tokens"] + busage["completion_tokens"]
            with open(os.path.join(run, "brief.json"), "w") as f:
                f.write(brief)
            print("  [brief] reference decomposed -> brief.json")
        except Exception as e:
            print(f"  [brief] analysis failed ({str(e)[:80]}) -- continuing without it")

    # the checklist must derive from OBSERVED evidence only -- snapshot the brief
    # before any hidden-sides inference is appended (weak-reference discipline: an
    # inferred back-facade feature must never become a required check)
    checklist_brief = brief

    # One-time hidden-sides inference (text): appended to the brief so every later
    # prompt carries it; marked as inference so the real reference wins on conflict.
    if a.hidden_brief:
        try:
            hb, husage = hidden_brief_step(base_imgs, a.backend, a.model)
            total_tokens += husage["prompt_tokens"] + husage["completion_tokens"]
            with open(os.path.join(run, "hidden_brief.json"), "w") as f:
                f.write(hb)
            note = ("\n\nHIDDEN-SIDES INFERENCE (reasoned from the visible view, NOT "
                    "observed -- where it conflicts with the real reference, the "
                    "reference wins):\n" + hb)
            brief = (brief + note) if brief else note.strip()
            print("  [hidden] unseen-sides inference -> hidden_brief.json")
        except Exception as e:
            print(f"  [hidden] inference failed ({str(e)[:80]}) -- continuing without it")

    # One-time reference-derived binary checklist (question-based verification). If it
    # can't be built, fall back to the old rubric judge for this run.
    checklist = None
    if a.judge == "checklist":
        try:
            checklist, clusage = checklist_step(base_imgs, checklist_brief, a.backend, a.model)
            total_tokens += clusage["prompt_tokens"] + clusage["completion_tokens"]
            with open(os.path.join(run, "checklist.json"), "w") as f:
                json.dump(checklist, f, indent=1)
            print(f"  [checklist] {len(checklist)} checks derived -> checklist.json")
        except Exception as e:
            a.judge = "rubric"
            print(f"  [checklist] failed ({str(e)[:80]}) -- falling back to --judge rubric")

    # Always refine from the BEST version so far (not the last) -- otherwise one bad
    # iteration drags the rest down. Errored code is fed back from `last_code` to fix.
    jmodel = a.judge_model or a.model   # judge calls may run on a cheaper model
    best = -1.0; best_code = None; best_render = None; best_crit = None; best_iou = None
    best_ds = None
    best_pass = 0.0; massing_streak = 0; brief_vetoes = 0
    last_code = None; error = None; log = []; history = []
    prev_scored_phase = None  # last phase that actually produced a scored render
    frozen = None            # massing keys locked after phase A (assemble mode)
    phase_a = a.phase_a_iters if a.mode == "assemble" else 0
    for it in range(a.max_iters + 1):
        phase = "massing" if (phase_a and it < phase_a) else ("features" if phase_a else "full")
        if phase_a and it == phase_a and best_code is not None and frozen is None:
            try:
                bd = json.loads(best_code)
                frozen = {k: bd[k] for k in ("footprint", "floor_h", "masses") if k in bd}
                print(f"  [phase] massing locked after iter {it - 1}: "
                      f"{json.dumps(frozen)[:100]}")
            except Exception:
                frozen = None
        print(f"  iter {it:02d} [{phase}]: agent writing spec/bpy (~1-2 min)...", flush=True)
        try:
            if error:
                code, gusage = genfn(base_imgs, last_code, None, error, a.backend, a.model,
                                     brief=brief, history=history, phase=phase)
            elif best_code is None and init_desc_text and not init_used:
                # seed iter 0 from the learned image->params model (no LLM call)
                code, gusage = init_desc_text, {"prompt_tokens": 0, "completion_tokens": 0}
                init_used = True
                print("  iter %02d: seeding from learned image->params model (--init-desc)" % it)
            elif best_code is None:
                code, gusage = genfn(base_imgs + aux, None, None, None, a.backend, a.model,
                                     brief=brief, history=history, phase=phase,
                                     n_aux=len(aux))
            else:
                refine = [photo, best_render]   # reference + current render only (no satellite)
                code, gusage = genfn(refine, best_code, best_crit, None, a.backend, a.model,
                                     brief=brief, history=history, phase=phase)
        except Exception as e:
            msg = str(e)[:140]
            print(f"  iter {it:02d}: AGENT/SDK ERROR -> skipping this iter: {msg}")
            log.append({"iter": it, "agent_error": msg})
            time.sleep(3)
            continue
        it_tokens = gusage["prompt_tokens"] + gusage["completion_tokens"]

        # enforce the phase-B massing lock: the agent may echo the massing, but the
        # frozen values always win (prompt-only "do not change X" is not reliable)
        if frozen and a.mode == "assemble":
            try:
                d = json.loads(re.search(r"\{.*\}", code, re.S).group(0))
                d.update(frozen)
                code = json.dumps(d, indent=1)
            except Exception:
                pass

        ext = "json" if a.mode == "assemble" else "py"
        with open(os.path.join(run, f"r{it:02d}.{ext}"), "w") as f:
            f.write(code)
        out = os.path.join(run, f"r{it:02d}.png")
        print("           building + rendering in Blender...", flush=True)
        if a.mode == "assemble":
            _desc, verrs = validate_desc(code)   # validated output: check BEFORE Blender
            # deterministic massing-vs-BRIEF guard (only while massing is editable,
            # max 2 vetoes/run so a bad brief estimate can't eat the whole budget)
            if (not verrs and _desc and checklist_brief and frozen is None
                    and brief_vetoes < 2):
                bv = brief_consistency(_desc, checklist_brief)
                if bv:
                    brief_vetoes += 1
                    verrs = ["massing disagrees with the measured BRIEF (trust the "
                             "brief): " + "; ".join(bv[:3])]
            if verrs:
                runnable, err = None, "INVALID spec, fix these: " + "; ".join(verrs[:6])
            else:
                runnable, err = spec_to_code(code, components_src), None
        else:
            runnable, err = code, None
        out_top = None
        if not err:
            if a.judge == "checklist" and a.view == "aerial":
                out_top = os.path.join(run, f"r{it:02d}_top.png")
            _res, err = build_and_render(runnable, out, a.view, top_png=out_top)
        last_code = code

        if err:
            total_tokens += it_tokens
            print(f"  iter {it:02d}: BLENDER ERROR  tokens={it_tokens}  -> feeding back: {err[:70]}")
            log.append({"iter": it, "error": err[:120], "tokens": it_tokens})
            error = err
            continue
        error = None

        print("           scoring render vs photo...", flush=True)
        # phase A judges massing/proportions only -- features are not built yet, so
        # scoring them would just punish the phase for following its instructions
        fields = ["massing", "proportions"] if phase == "massing" else None
        try:
            if a.judge == "checklist":
                cats = ("massing", "proportions") if phase == "massing" else None
                # inspector stays on the STRONG model -- see --judge-model help
                passed, failed, cusage = checklist_score(
                    out, checklist, a.backend, a.model, cats=cats,
                    top=(out_top if out_top and os.path.exists(out_top) else None),
                    k=a.inspector_k)
                # the silhouette evaluator assumes a black modelpic-style backdrop; on
                # a real street photo (sky background) its mask is garbage, so the
                # anchor only applies to aerial/model references
                iou = iou_anchor(out, photo) if a.view == "aerial" else None
                # combined score is for LOGGING + the stop criterion + tie-breaks only;
                # acceptance is decided by the pairwise vote below, not this number
                score = round(0.5 * passed + 0.5 * iou, 3) if iou is not None else passed
                rubric = passed
                crit = ("; ".join((f["note"] or f["q"]) for f in failed[:3])
                        or "all checks pass -- refine proportions/details")
            else:
                score, rubric, iou, crit, cusage = critique_step(
                    out, photo, a.backend, a.model, k=a.critic_k, fields=fields)
            # DreamSim perceptual anchor (deterministic, LLM-free): the anchor that
            # still works on street photos, where the sky background breaks the
            # silhouette IoU. Moderate signal (Spearman -0.33 on our 53-building
            # validation), so it guards and tie-breaks -- never the primary score.
            ds = dreamsim_dist(out, photo) if a.ds_guard > 0 else None
        except Exception as e:
            msg = str(e)[:140]
            total_tokens += it_tokens
            print(f"  iter {it:02d}: CRITIC/SDK ERROR -> keeping render, skipping score: {msg}")
            log.append({"iter": it, "critic_error": msg, "render": out, "tokens": it_tokens})
            time.sleep(3)
            continue
        it_tokens += cusage["prompt_tokens"] + cusage["completion_tokens"]

        # accept/reject. checklist mode: the order-swapped pairwise vote is the PRIMARY
        # signal (absolute scores only break ties), with a deterministic IoU veto so a
        # persuasive-but-wrong render can't displace a geometrically better one. rubric
        # mode keeps the old behaviour: score threshold + single A/B near-tie gate.
        # Phase boundaries reset the comparison (a features render always replaces a
        # massing-only best).
        phase_changed = prev_scored_phase is not None and prev_scored_phase != phase
        prev_scored_phase = phase
        judge_why = ""
        if best_render is None or phase_changed:
            accepted = True
        elif a.judge == "checklist":
            # verifier cascade (cost control): when the checklist pass-rate and the
            # deterministic anchors agree on a direction, decide without spending vote
            # calls; the pairwise vote is reserved for MIXED signals. pass-rate is
            # quantised (1/len(checks)), so a strict >/< is a real change.
            iou_ok = iou is None or best_iou is None or iou >= best_iou - a.iou_guard
            iou_worse = iou is not None and best_iou is not None and iou < best_iou
            ds_ok = ds is None or best_ds is None or ds <= best_ds + a.ds_guard
            if rubric > best_pass and iou_ok and ds_ok:
                accepted = True
                judge_why = "auto-accept: more checks pass, anchors within guard"
            elif rubric < best_pass and iou_worse:
                accepted = False
                judge_why = "auto-reject: fewer checks pass and IoU regressed"
            elif a.no_ab:
                accepted = score > best
            else:
                try:
                    winner, judge_why, aus = ab_vote(photo, best_render, out, a.backend,
                                                     jmodel, votes=a.ab_votes)
                    it_tokens += aus["prompt_tokens"] + aus["completion_tokens"]
                except Exception:
                    winner = "tie"
                if winner == "B":
                    accepted = iou_ok and ds_ok
                    if not iou_ok:
                        judge_why += (" [VETO: silhouette IoU regressed %.3f -> %.3f]"
                                      % (best_iou, iou))
                    elif not ds_ok:
                        judge_why += (" [VETO: DreamSim regressed %.3f -> %.3f]"
                                      % (best_ds, ds))
                elif winner == "tie":
                    # swap-consistent vote found no real difference: fall back to the
                    # combined score, then to the deterministic perceptual anchor
                    accepted = score > best or (
                        abs(score - best) < 1e-9 and ds is not None
                        and best_ds is not None and ds < best_ds - 0.01)
                else:
                    accepted = False
        elif score > best + 0.03:
            accepted = True
        elif score > best - 0.03 and not a.no_ab:
            try:
                winner, aus = ab_judge(photo, best_render, out, a.backend, jmodel)
                it_tokens += aus["prompt_tokens"] + aus["completion_tokens"]
                accepted = (winner == "B")
            except Exception:
                accepted = False
        else:
            accepted = False
        total_tokens += it_tokens

        flag = ""
        if accepted:
            best, best_code, best_render, best_crit = score, code, out, crit
            best_iou = iou
            best_ds = ds
            best_pass = rubric
            shutil.copy(out, os.path.join(run, "best.png"))
            with open(os.path.join(run, "best." + ext), "w") as f:
                f.write(code)
            flag = "  <- best"
        hist_fix = crit if accepted or not judge_why else (crit + " | judge: " + judge_why)
        history.append({"iter": it, "fix": hist_fix, "score": score, "accepted": accepted})
        log.append({"iter": it, "phase": phase, "score": score, "rubric": rubric, "iou": iou,
                    "ds": ds, "accepted": accepted, "critique": crit, "judge_why": judge_why,
                    "render": out, "tokens": it_tokens})
        print(f"  iter {it:02d}: score={score:.3f} (rubric={rubric:.3f} iou={iou if iou is None else round(iou, 3)}"
              f" ds={ds})  tokens={it_tokens}  {crit[:45]}{flag}")

        # massing-lock escape hatch: the phase-A lock can freeze a defect (e.g. a
        # missing roofline step-down) that the checklist then flags forever, because
        # the keys that control it are no longer editable. If a massing/proportions
        # check fails --unlock-after scored iterations in a row while the lock is
        # active, unlock and tell the agent massing is editable again.
        if a.judge == "checklist" and phase == "features" and frozen is not None:
            m_fail = any(f.get("cat") in ("massing", "proportions") for f in failed)
            massing_streak = massing_streak + 1 if m_fail else 0
            if a.unlock_after and massing_streak >= a.unlock_after:
                frozen = None
                phase_a = 0                  # subsequent iterations run phase='full'
                prev_scored_phase = "full"   # features->full is NOT a comparison reset
                best_crit = ((best_crit or "") + " NOTE: footprint/floor_h/masses are "
                             "UNLOCKED again -- change them to fix the failing "
                             "massing/proportions checks.")
                print(f"  [phase] massing UNLOCKED (massing checks failed "
                      f"{massing_streak} scored iters in a row)")

        if phase != "massing" and score >= a.stop_score:
            print("  -> reached target score")
            break

    with open(os.path.join(run, "log.json"), "w") as f:
        json.dump({"best_score": best, "total_tokens": total_tokens, "iterations": log}, f, indent=2)
    print(f"\nbest score = {best:.2f}  |  total tokens = {total_tokens}")
    print(f"outputs in {run} (best.png / best.py / log.json)")


if __name__ == "__main__":
    main()
