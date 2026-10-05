"""img2city/prior/headless_gen.py -- generate the synthetic (image, parameters) dataset in a HEADLESS
Blender process. No interactive Blender, no BlenderMCP, no socket -- so it can't hang or
slow down like the socket approach. This is the reliable way to render thousands of samples.

Run (adjust the Blender path if needed):

  cd <repo>
  $IMG2CITY_BLENDER --background \
      --python img2city/prior/headless_gen.py -- --n 1500 --out data/prior/dataset

It builds each random building with the parts library and renders the same studio / aerial
view the agent uses, with light/exposure/background randomised. Saves images + labels.csv
incrementally (safe to Ctrl-C). No add-on or MCP server required.
"""
import bpy
import sys
import os
import csv
import glob
import random
import ast
import runpy
from pathlib import Path
from types import SimpleNamespace

# args after the "--" separator
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def _arg(flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = Path(HERE).parent
PROJECT_ROOT = PACKAGE.parent
# Blender has its own Python: load only the self-contained kit and parameter
# definitions. Importing building.generate also imports host PIL/ML modules.
kit_dir = PACKAGE / "kit"
kit_ns = {"_VENDOR_DIR": str(kit_dir / "vendor")}
exec(compile((kit_dir / "components.py").read_text(), "components.py", "exec"), kit_ns)
components = SimpleNamespace(**kit_ns)
params = SimpleNamespace(**runpy.run_path(str(Path(HERE) / "params.py")))
# Reuse the canonical render strings without importing their host module.
render_names = {"RENDER_HEAD", "CAM_AERIAL", "RENDER_CAM", "LIGHT_STUDIO"}
render_tree = ast.parse((PACKAGE / "building" / "generate.py").read_text())
render_values = {target.id: ast.literal_eval(node.value)
                 for node in render_tree.body if isinstance(node, ast.Assign)
                 for target in node.targets
                 if isinstance(target, ast.Name) and target.id in render_names}
if render_values.keys() != render_names:
    raise RuntimeError("missing canonical render strings")
generate = SimpleNamespace(**render_values)
data_dir = Path(os.environ.get("IMG2CITY_DATA_DIR", PROJECT_ROOT / "data")).expanduser()
prior_dir = Path(os.environ.get("IMG2CITY_PRIOR_DIR", data_dir / "prior")).expanduser()

N = int(_arg("--n", "1500"))
OUT = os.path.abspath(_arg("--out", str(prior_dir / "dataset")))
SEED = int(_arg("--seed", "0"))

os.makedirs(OUT, exist_ok=True)
for _old in glob.glob(os.path.join(OUT, "img*.png")):   # start clean
    os.remove(_old)
rng = random.Random(SEED)

# domain-randomised, low-res render tail (uses cam / sc defined by the render-wrap above)
RTAIL = ("\ntry: sc.render.engine='BLENDER_EEVEE_NEXT'\nexcept Exception: sc.render.engine='BLENDER_EEVEE'\n"
         "try: sc.eevee.taa_render_samples=16\nexcept Exception: pass\n"
         "cam.location.x += %f\ncam.location.z += %f\nsc.view_settings.exposure=%f\n"
         "_b=sc.world.node_tree.nodes.get('Background')\n"
         "if _b: _b.inputs[0].default_value=(%f,%f,%f,1)\n"
         "sc.render.resolution_x=288\nsc.render.resolution_y=260\n"
         "sc.render.image_settings.file_format='PNG'\n"
         "sc.render.filepath=r'%s'\nbpy.ops.render.render(write_still=True)\n")

f = open(os.path.join(OUT, "labels.csv"), "w", newline="")
w = csv.writer(f); w.writerow(["image"] + params.NAMES); f.flush()
ok = 0
for i in range(N):
    vec = params.sample_vec(rng)
    desc = params.vec_to_desc(vec)
    out_png = os.path.join(OUT, "img%05d.png" % i)
    try:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for m in list(bpy.data.materials):
            bpy.data.materials.remove(m)
        components.build_building(desc)
        bgv = round(rng.uniform(0.0, 0.06), 3)
        tail = RTAIL % (rng.uniform(-3, 3), rng.uniform(-2, 3), rng.uniform(0.0, 0.4),
                        bgv, bgv, bgv, out_png)
        wrap = generate.RENDER_HEAD + generate.CAM_AERIAL + generate.RENDER_CAM + generate.LIGHT_STUDIO + tail
        exec(wrap, {})
    except Exception as e:
        print("  [%d] skip: %s" % (i, str(e)[:90]), flush=True)
        continue
    w.writerow([out_png] + [round(v, 4) for v in vec]); f.flush()
    ok += 1
    print("rendered %d / %d" % (ok, N), flush=True)
f.close()
print("done: %d samples -> %s" % (ok, os.path.join(OUT, "labels.csv")))
