"""photo.py -- photo-upload flow: image -> typology card -> spec agent -> parametric building.

The uploaded photo takes the SAME path a city building takes (09-07): a cheap
haiku card pick against typology_cards.json decides which dialect the spec
agent sees, then ONE spec call (generate.gen_spec, core schema + that card's
dialect lines) writes the editable description from the photo alone; a headless
rebuild_bpy.py --desc turns it into a glb.  Optional agent refine runs the full
generate.py loop (live Blender + the configured model) seeded from that spec, under the same
tags.

Until 09-07 this page ran learn/predict.py (ResNet18 image->params).  That net
is a single-archetype regressor -- its 17 outputs are all dimensions of the
business-school glass block -- so every upload came back as a variant of that
one building (user report on a Queen's Tower photo).  The prior stays available
on the CLI (learn/README.md); the web path no longer uses it.
"""
import json
import subprocess
import tempfile
import time
import uuid
from io import BytesIO
from pathlib import Path

from img2city import config
from img2city.webapp import areas, jobs
from img2city.webapp import rebuild as rebuild_mod

UPLOADS = areas.DATA / "web_uploads"
CARD_MODEL = config.PHOTO_CARD_MODEL
SPEC_MODEL = config.PHOTO_SPEC_MODEL

PHOTO_BRIEF = {
    "source": "ONE uploaded photograph; no survey footprint, height or OSM type",
    "note": ("Estimate footprint [L, W] in metres, floor count and floor_h from the "
             "photo's proportions (typical storey ~3.0-3.5 m for masonry, ~3.6-4.3 m "
             "for glass offices; a slender tower is a small footprint with many "
             "floors). Read facade type, materials, roof form and every distinctive "
             "feature from what you actually see; do not add features the photo does "
             "not show. GATE: if the image does not show a building clearly enough to "
             "read its structure (unrelated enclosed interior, blurred, not a building), output ONLY the "
             'JSON {"unusable": "<short reason>"} and nothing else.'),
}


def classify(pdir):
    """Card pick for the upload, cached in pdir/typology.json (photo-only facts)."""
    from img2city.building import typology
    return typology.pick({"name": None}, str(pdir), model=CARD_MODEL)


def spec_from_photo(img, card):
    """The project agent writes the spec from the photo under the card's dialect
    (one generation + one self-repair, as city_generate.agent_spec does)."""
    from img2city.building import typology
    from img2city.building.generate import gen_spec, validate_desc
    tags = typology.card_tags(card.get("cards")) if card.get("cards") else set()
    brief = dict(PHOTO_BRIEF)
    if card.get("cards"):
        brief["typology_card"] = ", ".join(card["cards"])
        if card.get("note"):
            brief["typology_note"] = card["note"]
    brief_txt = json.dumps(brief)
    code, usage = gen_spec([str(img)], None, None, None, "sdk", SPEC_MODEL,
                           brief=brief_txt, tags=tags)
    tok = usage["prompt_tokens"] + usage["completion_tokens"]
    if '"unusable"' in (code or ""):
        reason = "imagery unusable"
        try:
            reason = json.loads(code[code.index("{"):code.rindex("}") + 1]).get("unusable", reason)
        except Exception:
            pass
        raise RuntimeError(f"photo unusable: {reason}")
    desc, errs = validate_desc(code)
    if errs:
        code, usage = gen_spec([str(img)], code, None, "; ".join(errs[:6]), "sdk",
                               SPEC_MODEL, brief=brief_txt, tags=tags)
        tok += usage["prompt_tokens"] + usage["completion_tokens"]
        desc, errs = validate_desc(code)
    if errs or desc is None:
        raise RuntimeError("invalid spec after repair: " + "; ".join(errs[:4]))
    return desc, {"tokens": tok, "spec_model": SPEC_MODEL, "card_model": CARD_MODEL,
                  "tags": sorted(tags)}


def _build_glb(desc, glb_out):
    src_p = areas.CACHE / "_components_src.py"
    src_p.write_text(rebuild_mod.components_src())
    job = {"desc": desc, "components_src": str(src_p), "glb_out": str(glb_out)}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     dir=areas.CACHE) as f:
        json.dump(job, f)
        jp = f.name
    try:
        r = subprocess.run(
            [areas.BLENDER, "-b", "--python",
             str(Path(__file__).parent / "rebuild_bpy.py"), "--", "--desc", jp],
            capture_output=True, text=True, timeout=300)
    finally:
        Path(jp).unlink(missing_ok=True)
    from img2city.building.generate import component_errors
    if r.returncode or "BUILD_OK" not in r.stdout or component_errors(r.stdout):
        raise RuntimeError("build failed:\n" + r.stdout[-1200:] + r.stderr[-400:])


def create(image_bytes, suffix=".png"):
    """Save upload (PNG, the harness's streetview.png convention), pick the
    typology card, have the spec agent write the description, build the glb."""
    from PIL import Image
    pid = time.strftime("%m%d%H%M%S") + uuid.uuid4().hex[:4]
    pdir = UPLOADS / pid
    pdir.mkdir(parents=True, exist_ok=True)
    img = pdir / "streetview.png"
    Image.open(BytesIO(image_bytes)).convert("RGB").save(img)
    card = classify(pdir)
    desc, meta = spec_from_photo(img, card)
    (pdir / "desc.json").write_text(json.dumps(desc, indent=1))
    (pdir / "spec_meta.json").write_text(json.dumps(meta, indent=1))
    glb = pdir / "model.glb"
    _build_glb(desc, glb)
    return pid


def info(pid):
    pdir = UPLOADS / pid
    if not pdir.is_dir():
        raise KeyError(pid)
    desc = json.loads((pdir / "desc.json").read_text())
    card, meta = {}, {}
    if (pdir / "typology.json").exists():
        card = json.loads((pdir / "typology.json").read_text())
    if (pdir / "spec_meta.json").exists():
        meta = json.loads((pdir / "spec_meta.json").read_text())
    named = {}
    if (pdir / "pred_params.json").exists():
        named = json.loads((pdir / "pred_params.json").read_text())
    img = next((p for p in pdir.glob("streetview.*")), None)
    glbs = sorted(pdir.glob("model*.glb"), key=lambda p: p.stat().st_mtime)
    return {"id": pid, "desc": desc, "typology": card, "spec_meta": meta, "pred_params": named,
            "image": img.name if img else None,
            "glb": glbs[-1].name if glbs else None,
            "refined": (pdir / "refined.flag").exists()}


def dir_of(pid):
    pdir = UPLOADS / pid
    if not pdir.is_dir() or "/" in pid:
        raise KeyError(pid)
    return pdir


def rebuild(pid, desc):
    pdir = dir_of(pid)
    glb = pdir / f"model_{int(time.time())}.glb"
    _build_glb(desc, glb)
    (pdir / "desc.json").write_text(json.dumps(desc, indent=1))
    return glb


def start_refine(pid, iters=4):
    """Agent-refine job: full generate.py loop on the uploaded photo."""
    pdir = dir_of(pid)
    if not jobs.launch_blender():
        raise RuntimeError("could not start Blender+BlenderMCP on :9876")
    img = next((p for p in pdir.glob("streetview.*")), None)
    j = jobs.create("refine_photo", f"upload_{pid}", meta={"pid": pid})
    j.status = "running"

    def done(rc):
        if j.status == "cancelled":
            return
        runs = sorted((pdir / "gen").glob("*/best.json")) if (pdir / "gen").exists() else []
        if runs:
            best = json.loads(runs[-1].read_text())
            try:
                glb = rebuild(pid, best)
                (pdir / "refined.flag").write_text("1")
                j.meta["glb"] = glb.name
                j.status = "done"
            except Exception as e:
                j.status = "failed"
                j.error = str(e)
        else:
            j.status = "failed"
            j.error = f"generate.py produced no best.json (exit {rc}); see log"
    # the refine loop sees the same schema the spec was written under: core +
    # the upload's card dialect ('' = core only when no card fits)
    tags = []
    if (pdir / "typology.json").exists():
        from img2city.building import typology
        tags = sorted(typology.card_tags(
            json.loads((pdir / "typology.json").read_text()).get("cards")))
    j._run(config.module_cmd("building.generate", "--data", str(pdir),
            "--ref", img.name, "--view", "street", "--mode", "assemble",
            "--init-desc", str(pdir / "desc.json"), "--tags", ",".join(tags),
            "--max-iters", str(iters)), done, caffeinate=True)
    return j
