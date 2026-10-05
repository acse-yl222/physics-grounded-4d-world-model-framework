"""img2city/building/texture_assets.py -- photo-derived tileable textures for every agent building
(the block-scale version of the 07-13 single-building pilot; related_work_methods.md
N / §O item 5, PUT-adjacent: texture from the building's OWN imagery).

Why not Paint3D / UrbanWorld: both require NVIDIA kaolin (CUDA-only wheels) --
blocked on this machine. This route is zero-API, deterministic, and keeps the
editability story intact: geometry is untouched and each texture is just an image
on a material node, swappable per building.

Per building (cached in buildings/<id>/textures/):
  brick.png    dark-uniform patch from streetview.png  (skipped for glass facades)
  stucco.png   bright-uniform patch from the lower half of streetview.png,
               rotated 90 deg (BOX projection renders the tile rotated on facades --
               validated in the pilot)
  slate.png    patch from the CENTRE region of satellite.png (the fetch centres the
               building, so the centre is the roof, not the street -- the pilot's
               first crop landed on parked cars), luminance window set by the
               spec's roof_tone, strong feature suppression (chimney shadows)

A channel with no acceptable patch falls back to the block default set (the
validated 869772993 textures) so every masonry building improves, none regress.

  python -m img2city.building.texture_assets --out data/city_sk            # all buildings, cached
  python -m img2city.building.texture_assets --out data/city_sk --force
"""
from __future__ import annotations
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image

DEFAULT_ID = "869772993"        # pilot building; its textures seed the fallback set


def find_patch(arr, size, sd_max, lum_lo, lum_hi, y_min=0.0, y_max=1.0,
               x_min=0.0, x_max=1.0, step=14):
    """Lowest-variance size*size patch inside the luminance window and region."""
    H, W = arr.shape[:2]
    best = None
    for y in range(int(H * y_min), min(H - size, int(H * y_max)), step):
        for x in range(int(W * x_min), min(W - size, int(W * x_max)), step):
            t = arr[y:y + size, x:x + size]
            lum = t.mean()
            if not (lum_lo < lum < lum_hi):
                continue
            sd = t.std(axis=(0, 1)).mean()
            if sd < sd_max and (best is None or sd < best[0]):
                best = (sd, x, y)
    return best


def tileable(img, out, size=256, feature_suppress=0.0):
    """Offset-by-half + cross-blend hides the wrap seam; feature_suppress pulls
    pixels toward the mean first (kills chimney shadows / large gradients)."""
    im = img.resize((size, size), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    m = a.mean(axis=(0, 1), keepdims=True)
    a = a * (1 - feature_suppress) + m * feature_suppress
    b = np.roll(np.roll(a, size // 2, 0), size // 2, 1)
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.minimum(np.abs(xx - size // 2), np.abs(yy - size // 2)) / (size // 2)
    w = np.clip(d * 3.0, 0, 1)[..., None]
    Image.fromarray((b * w + a * (1 - w)).astype(np.uint8)).save(out)


def extract_building(bdir, spec, force=False):
    """-> {"brick": bool, "stucco": bool, "slate": bool} (True = own texture written).
    Missing channels are NOT written here -- the caller decides on fallback."""
    tdir = os.path.join(bdir, "textures")
    meta_p = os.path.join(tdir, "meta.json")
    if os.path.exists(meta_p) and not force:
        return json.load(open(meta_p))
    os.makedirs(tdir, exist_ok=True)
    got = {"brick": False, "stucco": False, "slate": False}
    masses = spec.get("masses") or [{}]
    glass = (spec.get("facade") == "glass"
             or any(mm.get("facade") == "glass" for mm in masses))
    sv_p = os.path.join(bdir, "streetview.png")
    if os.path.exists(sv_p) and not glass:
        sv = Image.open(sv_p).convert("RGB")
        a = np.asarray(sv).astype(float)
        hit = find_patch(a, 56, 34, 25, 95, y_max=0.8)
        if hit:
            _, x, y = hit
            tileable(sv.crop((x, y, x + 56, y + 56)),
                     os.path.join(tdir, "brick.png"))
            got["brick"] = True
        hit = find_patch(a, 64, 14, 165, 245, y_min=0.45)
        if hit:
            _, x, y = hit
            tileable(sv.crop((x, y, x + 64, y + 64)),
                     os.path.join(tdir, "stucco.png"))
            Image.open(os.path.join(tdir, "stucco.png")).rotate(90).save(
                os.path.join(tdir, "stucco.png"))
            got["stucco"] = True
    sat_p = os.path.join(bdir, "satellite.png")
    if os.path.exists(sat_p):
        tone = (spec.get("terrace") or {}).get("roof_tone", "dark")
        lo, hi = (20, 95) if tone == "dark" else (60, 160)
        sat = Image.open(sat_p).convert("RGB")
        a = np.asarray(sat).astype(float)
        hit = find_patch(a, 48, 20, lo, hi,        # centre region = the roof itself
                         y_min=0.3, y_max=0.7, x_min=0.3, x_max=0.7, step=12)
        if hit:
            _, x, y = hit
            tileable(sat.crop((x, y, x + 48, y + 48)),
                     os.path.join(tdir, "slate.png"), feature_suppress=0.45)
            got["slate"] = True
    with open(meta_p, "w") as f:
        json.dump(got, f)
    return got


def run_all(out, force=False):
    """Extract every building; fill missing channels from the fallback set.
    -> entries list for the Blender texture chunk."""
    import shutil
    fb_bdir = os.path.join(out, "buildings", DEFAULT_ID)
    if os.path.exists(os.path.join(fb_bdir, "spec.json")):
        extract_building(fb_bdir, json.load(open(os.path.join(fb_bdir, "spec.json"))),
                         force)                    # fallback set must exist first
    fb_dir = os.path.join(fb_bdir, "textures")
    entries, own, fell = [], 0, 0
    for bdir in sorted(glob.glob(os.path.join(out, "buildings", "*"))):
        spec_p = os.path.join(bdir, "spec.json")
        if not os.path.exists(spec_p):
            continue
        spec = json.load(open(spec_p))
        got = extract_building(bdir, spec, force)
        tdir = os.path.join(bdir, "textures")
        for ch in ("brick", "stucco", "slate"):
            p = os.path.join(tdir, f"{ch}.png")
            if not got.get(ch) and not os.path.exists(p) \
                    and os.path.basename(bdir) != DEFAULT_ID:
                fb = os.path.join(fb_dir, f"{ch}.png")
                if os.path.exists(fb):
                    shutil.copy(fb, p)
                    fell += 1
        own += sum(got.values())
        entries.append({"id": int(os.path.basename(bdir)), "dir": tdir})
    print(f"[textures] {len(entries)} buildings, {own} own patches, "
          f"{fell} fallback channels")
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    run_all(a.out, a.force)


if __name__ == "__main__":
    main()
