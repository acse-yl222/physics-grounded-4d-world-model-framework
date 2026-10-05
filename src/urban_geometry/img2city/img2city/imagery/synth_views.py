"""img2city/imagery/synth_views.py -- synthesize auxiliary views of the reference building with an
image-editing model (Gemini "Nano Banana"), to use as WEAK references.

Why: with a single reference photo (modelpic) the sides the camera cannot see are
unconstrained -- the agent just guesses the back facade and the far end. An
image-editing model can extrapolate the same building from other viewpoints (the
06-09 demo showed this works well on partial building images). The synthetic views
are treated as WEAK references only: they inform the BRIEF and the FIRST generation,
but scoring / the checklist stay on the real photo, so hallucinated details can
never become required features.

Setup (one-time):
  1. Get a key at https://aistudio.google.com/apikey (free tier is enough)
  2. Put it in .env:  GEMINI_API_KEY=...   (models: IMG2CITY_IMAGE_EDIT_MODELS)
  3. pip install -e ".[gemini]"

Usage:
  python -m img2city.imagery.synth_views --ref data/business_school/modelpic.jpeg \
                         --out data/business_school/synth
  # then:
  python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial \
      --mode assemble --backend sdk \
      --aux-refs synth/farend_aerial.png,synth/back_aerial.png,synth/front_elevation.png
"""
from __future__ import annotations
import argparse
import os

from img2city import config

PROMPT_TMPL = (
    "This is a photo of a physical architectural scale model of a building on a black "
    "studio background. Generate an image of the SAME model -- identical geometry, "
    "materials, colours and lighting -- photographed from a different viewpoint: "
    "{view}. Do NOT invent, add or remove any building elements; every feature must "
    "stay consistent with the original photo. Keep the black studio background and "
    "the same architectural-model photography style."
)

# viewpoints chosen to cover what modelpic hides: the far end, the back facade, and
# a flat elevation for floor counts / facade banding
VIEWS = {
    "farend_aerial": ("an elevated three-quarter view from beyond the OPPOSITE short "
                      "end of the building, so the end with the curved glass vault is "
                      "nearest the camera"),
    "back_aerial": ("an elevated three-quarter view showing the BACK long facade -- "
                    "the side hidden in the original photo"),
    "front_elevation": ("a straight-on frontal elevation of the long front facade, "
                        "camera at mid-building height, the full length of the "
                        "building visible and horizontal in frame"),
}

def gemini_models():
    """The Gemini entries of ``config.IMAGE_EDIT_MODELS``, in configured order."""
    return [m.partition(":")[2] for m in config.IMAGE_EDIT_MODELS if m.startswith("gemini:")]


def main():
    ap = argparse.ArgumentParser(description="Synthesize auxiliary views of a reference building")
    ap.add_argument("--ref", required=True, help="the real reference photo (e.g. modelpic.jpeg)")
    ap.add_argument("--out", required=True, help="output folder for the synthetic views")
    ap.add_argument("--views", default=",".join(VIEWS),
                    help="comma-separated subset of: " + ", ".join(VIEWS))
    a = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in .env first (https://aistudio.google.com/apikey)")
    try:
        from google import genai
    except ImportError:
        raise SystemExit("pip install google-genai pillow")
    from PIL import Image

    models = gemini_models()
    if not models:
        raise SystemExit("no gemini:* entry in IMG2CITY_IMAGE_EDIT_MODELS")
    client = genai.Client()
    ref = Image.open(a.ref)
    os.makedirs(a.out, exist_ok=True)

    for name in [v.strip() for v in a.views.split(",") if v.strip()]:
        if name not in VIEWS:
            print(f"[skip] unknown view {name!r}")
            continue
        prompt = PROMPT_TMPL.format(view=VIEWS[name])
        out_path = os.path.join(a.out, f"{name}.png")
        last_err = None
        for model in models:
            try:
                r = client.models.generate_content(model=model, contents=[prompt, ref])
                img_bytes = None
                for part in r.candidates[0].content.parts:
                    data = getattr(getattr(part, "inline_data", None), "data", None)
                    if data:
                        img_bytes = data
                        break
                if not img_bytes:
                    raise RuntimeError("response contained no image part")
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"[ok] {name}: {out_path}  (model={model})")
                last_err = None
                break
            except Exception as e:
                last_err = e
                continue
        if last_err is not None:
            print(f"[FAIL] {name}: {str(last_err)[:200]}")


if __name__ == "__main__":
    main()
