"""img2city/prior/gen_dataset.py -- render a synthetic (image, parameters) dataset for the image->params
model. Runs on the Mac with Blender + the BlenderMCP server open (it reuses the harness
socket + render wrap). Lighting / camera / exposure are randomised so the trained net
transfers from these synthetic renders to a real model photo like modelpic.

  python -m img2city.prior.gen_dataset --n 3000 --out data/prior/dataset

Output: data/prior/dataset/img00000.png ... + labels.csv (image path + raw parameter vector).
"""
import os
import csv
import json
import glob
import random
import argparse
from img2city import config
from img2city.building import generate as G
from img2city.prior import params as P


def render_code(desc, out_png, rng):
    """CLEAR + build the building + a domain-randomised low-res studio render."""
    src = G.load_components_src()
    geo = src + "\nimport json as _json\nbuild_building(_json.loads(%r))\n" % json.dumps(desc)
    head = G.RENDER_HEAD + G.CAM_AERIAL + G.RENDER_CAM + G.LIGHT_STUDIO
    # randomise camera jitter, exposure, background brightness -> robustness / sim-to-real
    rj = ("\ntry: sc.render.engine='BLENDER_EEVEE_NEXT'\nexcept Exception: sc.render.engine='BLENDER_EEVEE'\n"
          "cam.location.x += %f\ncam.location.y += %f\ncam.location.z += %f\n"
          "sc.view_settings.exposure = %f\n"
          "_b = sc.world.node_tree.nodes.get('Background')\n"
          "if _b: _b.inputs[0].default_value=(%f,%f,%f,1); _b.inputs[1].default_value=%f\n"
          "try: sc.eevee.taa_render_samples = 16\nexcept Exception: pass\n"
          "sc.render.resolution_x = 288\nsc.render.resolution_y = 260\n"
          "sc.render.image_settings.file_format='PNG'\n"
          "sc.render.filepath = r'%s'\nbpy.ops.render.render(write_still=True)\n") % (
              rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-2, 3),
              rng.uniform(-0.1, 0.5),
              round(rng.uniform(0, 0.06), 3), round(rng.uniform(0, 0.06), 3), round(rng.uniform(0, 0.06), 3),
              round(rng.uniform(0.0, 0.5), 2),
              out_png)
    return G.CLEAR + "\n" + geo + "\n" + head + rj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--out", default=str(config.PRIOR_DIR / "dataset"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    # start clean: drop leftover images from any previous run (labels.csv is truncated below)
    old = glob.glob(os.path.join(out, "img*.png"))
    for _o in old:
        os.remove(_o)
    if old:
        print("cleared %d leftover image(s) from %s" % (len(old), out))
    rng = random.Random(a.seed)

    lp = os.path.join(out, "labels.csv")
    f = open(lp, "w", newline="")
    w = csv.writer(f); w.writerow(["image"] + P.NAMES); f.flush()
    ok = 0
    try:
        for i in range(a.n):
            vec = P.sample_vec(rng)
            desc = P.vec_to_desc(vec)
            png = os.path.join(out, "img%05d.png" % i)
            _res, err = G._send(render_code(desc, png, rng))
            if err:
                print("  [%d] render error, skip: %s" % (i, str(err)[:80]))
                continue
            w.writerow([png] + [round(v, 4) for v in vec]); f.flush()   # save as we go: safe to Ctrl-C
            ok += 1
            print("  rendered %d / %d" % (ok, a.n), flush=True)         # print every sample so it never looks frozen
    finally:
        f.close()
    print("done: %d samples -> %s" % (ok, lp))


if __name__ == "__main__":
    main()
