"""compare_top -- pixel-aligned satellite-vs-render top comparison for the city block
(verification figure), and the bbox-cropped satellite tile the tree detector
reads (`fetch_bbox_satellite`, cached as block_sat_bbox.png).

The milestone figure compared a hand-grabbed satellite screenshot with a perspective
top render: different extent, different centre, different projection -- the layouts
never lined up visually. This does it properly:

  left  : Google Static Maps satellite, fetched around the bbox centre and CROPPED
          to the exact OSM bbox with Web-Mercator pixel math
  right : orthographic straight-down render of the live Blender scene, camera framed
          to the SAME bbox in local metres (north = +y = up)

Usage (Blender scene already assembled via city_generate --assemble-only):
  python -m img2city.city.compare_top --out data/city_sk
"""
from __future__ import annotations
import argparse
import json
import math
import os

from PIL import Image

from img2city.building.generate import _send
from img2city.imagery.maps_fetch import STATICMAP, _get, _key

ZOOM, SCALE, SIZE = 17, 2, 640          # 1280 px, ~0.37 m/px at London latitude


def merc_px(lat, lng, zoom, scale):
    """Web-Mercator world pixel coords at (zoom, scale)."""
    n = 256 * (2 ** zoom) * scale
    x = (lng + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def fetch_bbox_satellite(bbox, out_png):
    """Static-map satellite cropped exactly to bbox (s, w, n, e)."""
    s, w, n, e = bbox
    clat, clng = (s + n) / 2, (w + e) / 2
    _get(STATICMAP, {"center": f"{clat},{clng}", "zoom": ZOOM, "scale": SCALE,
                     "size": f"{SIZE}x{SIZE}", "maptype": "satellite", "key": _key()},
         out_png)
    img = Image.open(out_png)
    cx, cy = merc_px(clat, clng, ZOOM, SCALE)
    x0, y0 = merc_px(n, w, ZOOM, SCALE)          # top-left = (north, west)
    x1, y1 = merc_px(s, e, ZOOM, SCALE)
    half = SIZE * SCALE / 2
    box = (round(x0 - cx + half), round(y0 - cy + half),
           round(x1 - cx + half), round(y1 - cy + half))
    if min(box) < 0 or max(box) > SIZE * SCALE:
        raise SystemExit(f"bbox exceeds the fetched tile ({box}); lower ZOOM")
    img.crop(box).save(out_png)
    return out_png


# camera framed to the bbox in scene coordinates: orthographic, straight down,
# default rotation (0,0,0) already looks along -z with +y (north) up
ORTHO_TOP = r'''
import bpy
cam = bpy.data.objects.new("BBoxTop", bpy.data.cameras.new("BBoxTop"))
bpy.context.scene.collection.objects.link(cam)
cam.data.type = 'ORTHO'
cam.data.ortho_scale = %f
cam.location = (%f, %f, 400)
cam.data.clip_end = 1000
bpy.context.scene.camera = cam
sc = bpy.context.scene
try: sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine = 'BLENDER_EEVEE'
# generate.RENDER_OUT hard-codes 900x900 -- render with our own tail so the
# resolution keeps the bbox aspect (ortho_scale maps to the LARGER dimension)
sc.render.resolution_x = %d
sc.render.resolution_y = %d
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
'''


def render_bbox_top(anchor, out_png, res_x, res_y):
    s, w, n, e = anchor["bbox"]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    x0, x1 = (w - anchor["lon0"]) * kx, (e - anchor["lon0"]) * kx
    y0, y1 = (s - anchor["lat0"]) * 110540.0, (n - anchor["lat0"]) * 110540.0
    ext_x, ext_y = x1 - x0, y1 - y0
    # AUTO sensor fit applies ortho_scale to the larger render dimension
    ortho = ext_y if res_y >= res_x else ext_x
    code = ORTHO_TOP % (ortho, (x0 + x1) / 2, (y0 + y1) / 2,
                        res_x, res_y, os.path.abspath(out_png))
    _res, err = _send(code, timeout=600)
    if err:
        raise SystemExit(f"render failed: {err}\n(is the assembled scene still open "
                         "in Blender? re-run city_generate --assemble-only first)")
    return out_png


def compose(sat_png, render_png, out_png, overlay_png, gap=12):
    """satellite | render | 50%-blend overlay (the overlay is the alignment proof)."""
    a = Image.open(sat_png).convert("RGB")
    b = Image.open(render_png).convert("RGB").resize(a.size, Image.LANCZOS)
    ov = Image.blend(a, b, 0.5)
    ov.save(overlay_png)
    canvas = Image.new("RGB", (a.width * 3 + gap * 2, a.height), (255, 255, 255))
    for i, img in enumerate((a, b, ov)):
        canvas.paste(img, (i * (a.width + gap), 0))
    canvas.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser(description="Aligned satellite-vs-render top figure")
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    anchor = json.load(open(os.path.join(out, "buildings.json")))["anchor"]

    sat = fetch_bbox_satellite(anchor["bbox"], os.path.join(out, "block_sat_bbox.png"))
    sw, sh = Image.open(sat).size
    print(f"[sat] cropped to bbox: {sw}x{sh} px")
    ren = render_bbox_top(anchor, os.path.join(out, "block_render_bbox.png"), sw, sh)
    fig = compose(sat, ren,
                  os.path.join(out, "compare_block_sat_vs_agent_aligned.png"),
                  os.path.join(out, "overlay_sat_render.png"))
    print(f"[done] {fig}")


if __name__ == "__main__":
    main()
