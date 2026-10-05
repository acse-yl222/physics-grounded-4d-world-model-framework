"""img2city/building/facade_project.py -- deterministic street-photo -> facade projection textures
(productionised from the 2026-07-18 pilot; the "why Google 3D looks real" lesson:
drape the photo itself over the geometry, but keep OUR editable kit underneath).

We know the pano camera's exact position (pano.json), its aim (maps_fetch auto-aims
at the building centre), its fov (90 deg / 640 px -> f = 320 px) and the facade
plane (OBB front face / polygon street edges), so the street photo can be rectified
onto the facade by exact perspective back-projection -- no learning, no LLM.

Per building (cached in buildings/<id>/textures/):
  facade_proj_<k>.png   rectified + mirror-tiled facade strip per projected quad
  facade_proj.json      quad frames (building-local for OBB, scene coords for
                        polygon mode) + vertical-alignment offset + coverage

Open issues from the pilot, addressed here:
  1. double-exposed windows: the projection is carried by a thin QUAD floating
     QOFF=0.29 m outside the wall face -- in front of the kit's glazing (0.25) and
     sash bars (0.285) so those can never double-expose, behind the jamb rings
     (0.30+), sills, cornices and porticos so the 3-D relief still reads. The kit
     additionally suppresses front-face glazing under a "photo_proj" flag
     (components.py) so nothing pokes through even at glancing angles.
  2. single-photo coverage: the well-covered column strip is detected and
     MIRROR-TILED across the full facade length (legitimate for repetitive
     terraces); polygon buildings are handled PER EDGE (only edges that face the
     pano and land in the photo frustum get a quad).
  3. ~0.5 m vertical misalignment (assumed 2.5 m eye height): the OWLv2 window
     rows (facade_facts.json "_rows_px") are back-projected onto the facade plane
     and the median offset to the kit's window-row heights is applied (clamped).
  4. occluders (railings, cars) stay baked in -- accepted at this LoD.
  5. projection stays OUT of the judge loop: assembly + appearance eval only
     (research SS-P: colored renders hide geometry defects from VLM judges).

Caveats: photos fetched by city_pilot --imagery (the 6 largest buildings) used
pitch=20 rather than ensure_imagery's 18 -- a ~2 deg vertical error the facts-row
alignment largely absorbs. Glass-facade masses are never projected.

  python -m img2city.building.facade_project --out data/city_sk              # all buildings, cached
  python -m img2city.building.facade_project --out data/city_sk --force
  python -m img2city.building.facade_project --out data/city_sk --eval       # subset DreamSim eval
"""
from __future__ import annotations
import argparse
import glob
import json
import math
import os

import numpy as np
from PIL import Image

QOFF = 0.29          # quad offset outside the wall face (see docstring, issue 1)
EYE_H = 2.5          # Street View camera height assumed by the whole pipeline
PITCH = math.radians(18.0)   # ensure_imagery fetches with pitch=18
RES = 24             # texels per metre of facade
MAX_W = 4096         # texture width cap
KX = 111320.0        # metres per degree lon at equator (times cos(lat0))
KY = 110540.0        # metres per degree lat


# ---------------------------------------------------------------- camera model

def _cam_basis(pano_xy, aim_xy):
    """Orthonormal basis of the street-view photo camera: forward (aimed at the
    building centre, pitched up 18 deg), right, up. All in the same 2-D frame the
    inputs are given in (scene or building-local), z = height."""
    dx, dy = aim_xy[0] - pano_xy[0], aim_xy[1] - pano_xy[1]
    n = math.hypot(dx, dy) or 1.0
    fx, fy = dx / n, dy / n
    F = np.array([fx * math.cos(PITCH), fy * math.cos(PITCH), math.sin(PITCH)])
    R = np.array([fy, -fx, 0.0])                     # F x world-up, horizontal
    U = np.cross(R, F)
    C = np.array([pano_xy[0], pano_xy[1], EYE_H])
    return C, F, R, U


def _project_px(P, C, F, R, U, img_wh):
    """World points (N,3) -> photo pixel coords + depth. f = img_w/2 (90 deg fov)."""
    q = P - C
    z = q @ F
    f = img_wh[0] / 2.0
    px = img_wh[0] / 2.0 + f * (q @ R) / np.where(z == 0, 1e-9, z)
    py = img_wh[1] / 2.0 - f * (q @ U) / np.where(z == 0, 1e-9, z)
    return px, py, z


def _sample_bilinear(arr, px, py):
    """Bilinear sample of an (H,W,3) float array at fractional pixel coords."""
    H, W = arr.shape[:2]
    x0 = np.clip(np.floor(px).astype(int), 0, W - 2)
    y0 = np.clip(np.floor(py).astype(int), 0, H - 2)
    fx = np.clip(px - x0, 0, 1)[..., None]
    fy = np.clip(py - y0, 0, 1)[..., None]
    a = arr[y0, x0]; b = arr[y0, x0 + 1]; c = arr[y0 + 1, x0]; d = arr[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# ------------------------------------------------------------- rectify + tile

def _rectify(photo, C, F, R, U, O, D, length, height, dz):
    """Inverse-warp the photo onto the facade rectangle (origin O at the wall
    face's bottom corner, unit direction D along the facade, z up). dz shifts the
    sampled height (vertical-alignment fix). Returns (float array row0=top, valid)."""
    w_px = min(MAX_W, max(8, int(length * RES)))
    h_px = min(1024, max(8, int(height * RES)))
    j, i = np.meshgrid(np.arange(w_px), np.arange(h_px))
    u = (j + 0.5) * (length / w_px)
    v = height - (i + 0.5) * (height / h_px)         # row 0 = facade top
    P = (O[None, None, :]
         + u[..., None] * np.array([D[0], D[1], 0.0])[None, None, :]
         + (v - dz)[..., None] * np.array([0.0, 0.0, 1.0])[None, None, :])
    arr = np.asarray(photo, dtype=float)
    px, py, z = _project_px(P.reshape(-1, 3), C, F, R, U, photo.size)
    px, py, z = (a.reshape(h_px, w_px) for a in (px, py, z))
    valid = ((z > 1.0) & (px >= 0) & (px <= photo.size[0] - 1)
             & (py >= 0) & (py <= photo.size[1] - 1))
    out = _sample_bilinear(arr, px, py)
    return out, valid


def _strip_and_tile(out, valid):
    """Find the best-covered contiguous column strip, fill its vertical gaps by
    clamp-extension, then mirror-tile it across the full width. Returns
    (uint8 image or None, coverage fraction, strip width in columns)."""
    h_px, w_px = valid.shape
    cov = valid[: int(h_px * 0.92)].mean(axis=0)     # ignore the topmost sliver
    # 0.65 (was 0.5): columns needing more than ~a third of their height
    # clamp-filled render as the vertical streak bands the 07-18 review flagged
    good = cov >= 0.65
    if not good.any():
        return None, float(cov.mean()), 0
    # longest contiguous run of well-covered columns
    runs, start = [], None
    for k, g in enumerate(list(good) + [False]):
        if g and start is None:
            start = k
        elif not g and start is not None:
            runs.append((k - start, start, k))
            start = None
    ln, s0, s1 = max(runs)
    # trim the strip edges: the outermost columns are photo-border pixels smeared
    # by clamping and show as vertical streak bands at every mirror seam
    trim = min(max(2, int(0.03 * (s1 - s0))), (s1 - s0 - 8) // 2 if s1 - s0 > 16 else 0)
    s0, s1 = s0 + trim, s1 - trim
    strip = out[:, s0:s1].copy()
    sv = valid[:, s0:s1]
    # vertical clamp-fill per column (photo top rarely covers the parapet line)
    idx = np.where(sv, np.arange(h_px)[:, None], h_px)
    first = idx.min(axis=0)                          # topmost valid row per column
    first = np.minimum(first, h_px - 1)
    rows = np.maximum(np.arange(h_px)[:, None], first[None, :])
    # below-bottom gaps: clamp upward as well
    idxb = np.where(sv, np.arange(h_px)[:, None], -1)
    last = np.maximum(idxb.max(axis=0), 0)
    rows = np.minimum(rows, last[None, :])
    strip = strip[rows, np.arange(s1 - s0)[None, :]]
    # baked-sky suppression: when the modelled facade top rises above the
    # photo's roofline, the top rows are sky -- per column, clamp-fill the
    # contiguous top sky run from the first non-sky pixel below it
    r_, b_ = strip[..., 0], strip[..., 2]
    sky = (b_ > r_ + 25) & (b_ > 140)
    h_s = strip.shape[0]
    first_ns = np.where((~sky).any(axis=0), np.argmax(~sky, axis=0), 0)
    # horizontally-smoothed fill colour (single-pixel clamping leaves streaks;
    # a smooth band reads as the parapet)
    fillc = strip[first_ns, np.arange(s1 - s0)]
    kk = np.ones(31) / 31.0
    fillc = np.stack([np.convolve(np.pad(fillc[:, c], 15, mode="edge"), kk,
                                  mode="valid") for c in range(3)], axis=-1)
    in_sky_run = np.arange(h_s)[:, None] < first_ns[None, :]
    strip = np.where(in_sky_run[..., None], fillc[None, :, :], strip)
    # mirror-tile across the full facade width
    sw = s1 - s0
    jj = np.arange(w_px) - s0
    k = np.mod(jj, 2 * sw)
    src = np.where(k < sw, k, 2 * sw - 1 - k)
    full = strip[:, src]
    return full.astype(np.uint8), float(cov[s0:s1].mean()), sw


def _align_dz(facts, C, F, R, U, O, n_out, img_wh, z_rows, height):
    """Back-project each detected window row (centre column of the photo) onto the
    facade plane; median offset to the nearest kit window-row height, clamped.
    Positive dz means the photo rows sit LOWER than the kit rows by dz."""
    if not facts or not facts.get("_rows_px") or not z_rows:
        return 0.0, 0
    n3 = np.array([n_out[0], n_out[1], 0.0])
    O3 = np.asarray(O, dtype=float)
    f = img_wh[0] / 2.0
    deltas = []
    for row in facts["_rows_px"]:
        d = (F + R * 0.0 + U * (img_wh[1] / 2.0 - row["y"]) / f)
        denom = d @ n3
        if abs(denom) < 1e-6:
            continue
        t = ((O3 - C) @ n3) / denom
        if t <= 0:
            continue
        v = (C + t * d)[2]
        if not (0.3 <= v <= height + 0.6):            # basement / dormer rows out
            continue
        z_near = min(z_rows, key=lambda z: abs(z - v))
        if abs(z_near - v) < 2.0:
            deltas.append(z_near - v)
    if len(deltas) < 2:
        return 0.0, len(deltas)
    dz = float(np.clip(np.median(deltas), -1.5, 1.5))
    return dz, len(deltas)


def _sky_frac(img):
    """Fraction of clearly-blue-sky pixels in a projection strip. A facade
    rectified from a correctly-modelled plane contains (almost) no sky; a high
    fraction means the plane extends into sky in the photo -- wrong aim, the
    building set back, or a junction shot (867484734: 0.83 on a strip that was
    mostly sky; the subset's genuine winners measure 0.0-0.34)."""
    a = img.astype(int)
    r, b = a[..., 0], a[..., 2]
    return float(((b > r + 25) & (b > 140)).mean())


SKY_MAX = 0.45
# quality gate 3: minimum perpendicular pano-to-facade distance. Closer than
# ~7 m the rectification stretches the upper storeys into smears (850052662's
# 3 m worm's-eye photo produced funhouse brick that matched nothing)
MIN_DIST = 7.0


# ------------------------------------------------- building geometry contracts

def _front_masses(desc):
    """Frontmost masonry masses of an OBB building -- the same formulas and the
    same 1.0 m alignment window as components.build_building/punched_windows (the
    two MUST agree or the kit suppresses glazing on faces that got no quad)."""
    L, W = float(desc.get("footprint", [60, 36])[0]), float(desc.get("footprint", [60, 36])[1])
    N = min(100, max(1, int(desc.get("floors", 6))))
    FH = float(desc.get("floor_h", 4.3))
    masses = desc.get("masses") or [{"x": [0, 1], "y": [0, 1], "floors": N,
                                     "facade": desc.get("facade", "glass")}]
    infos = []
    for mss in masses:
        if mss.get("facade", "glass") == "glass":
            continue
        ax, bx = mss.get("x", [0, 1]); ay, by = mss.get("y", [0, 1])
        mn = min(100, max(1, int(mss.get("floors", N))))
        mcx = -L / 2 + (ax + bx) / 2 * L; mln = max(2.0, (bx - ax) * L)
        mcy = -W / 2 + (ay + by) / 2 * W; mwd = max(2.0, (by - ay) * W)
        infos.append({"y_f": mcy - mwd / 2, "x0": mcx - mln / 2, "len": mln,
                      "h": mn * FH, "floors": mn, "fh": FH})
    if not infos:
        return []
    front = min(q["y_f"] for q in infos)
    return [q for q in infos if q["y_f"] <= front + 1.0]


def _poly_inside(x, y, pts):
    ins = False
    n = len(pts)
    for k in range(n):
        x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            ins = not ins
    return ins


# ------------------------------------------------------------------ per building

def project_building(entry, m, anchor, bdir, force=False):
    """-> meta dict (also written to textures/facade_proj.json) or None."""
    tdir = os.path.join(bdir, "textures")
    meta_p = os.path.join(tdir, "facade_proj.json")
    if os.path.exists(meta_p) and not force:
        return json.load(open(meta_p))
    photo_p = os.path.join(bdir, "streetview.png")
    pano_p = os.path.join(bdir, "pano.json")
    if not (os.path.exists(photo_p) and os.path.exists(pano_p)):
        return None
    desc = entry["desc"]
    masses = desc.get("masses") or [{}]
    if (desc.get("facade") == "glass"
            and all(mm.get("facade", "glass") == "glass" for mm in masses)):
        return None
    photo = Image.open(photo_p).convert("RGB")
    pano = json.load(open(pano_p))
    kx = KX * math.cos(math.radians(anchor["lat0"]))
    pscene = ((pano[1] - anchor["lon0"]) * kx, (pano[0] - anchor["lat0"]) * KY)
    c_ll = m["center_latlng"]
    aimscene = ((c_ll[1] - anchor["lon0"]) * kx, (c_ll[0] - anchor["lat0"]) * KY)
    facts = None
    ff_p = os.path.join(bdir, "facade_facts.json")
    if os.path.exists(ff_p):
        facts = json.load(open(ff_p))
    os.makedirs(tdir, exist_ok=True)
    # quality gate 1: no facade facts = the detector found no readable window
    # grid in the photo (junction shots, buses/scaffolding in front, building
    # far away) -- exactly the photos that projected garbage (723363790's red
    # bus, 846844923's smeared junction). No facts, no projection.
    if not facts:
        meta = {"mode": "poly" if "poly" in entry else "obb", "pose": None,
                "quads": [], "why": "no-facts"}
        with open(meta_p, "w") as f:
            json.dump(meta, f, indent=1)
        return meta
    quads = []
    if "poly" in entry:
        pts = entry["poly"]
        fl = int(entry.get("floors", 4)); fh = float(entry.get("floor_h", 3.2))
        H = fl * fh
        z_rows = [r * fh + fh * 0.52 for r in range(fl)]
        C, F, R, U = _cam_basis(pscene, aimscene)
        n = len(pts)
        for k in range(n):
            x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % n]
            el = math.hypot(x2 - x1, y2 - y1)
            if el < 5.0:
                continue
            ang = math.atan2(y2 - y1, x2 - x1)
            mx_, my_ = (x1 + x2) / 2, (y1 + y2) / 2
            nx, ny = -math.sin(ang), math.cos(ang)
            if _poly_inside(mx_ + nx, my_ + ny, pts):
                nx, ny = -nx, -ny
            # edge must face the pano, from at least MIN_DIST away
            perp = (pscene[0] - mx_) * nx + (pscene[1] - my_) * ny
            if perp <= 0:
                continue
            if perp < MIN_DIST:               # quality gate 3: worm's-eye smear
                continue
            # orient D so the quad's face normal (D x z-up) points outward
            if (y2 - y1) * nx - (x2 - x1) * ny > 0:
                O = np.array([x1, y1, 0.0]); D = ((x2 - x1) / el, (y2 - y1) / el)
            else:
                O = np.array([x2, y2, 0.0]); D = ((x1 - x2) / el, (y1 - y2) / el)
            dz, nrows = _align_dz(facts, C, F, R, U, O, (nx, ny),
                                  photo.size, z_rows, H)
            out, valid = _rectify(photo, C, F, R, U, O, D, el, H, dz)
            img, cov, sw = _strip_and_tile(out, valid)
            if img is None or sw / RES < max(3.0, 0.10 * el):
                continue
            if _sky_frac(img) > SKY_MAX:      # quality gate 2: plane hits sky
                continue
            img_p = os.path.join(tdir, f"facade_proj_{k}.png")
            Image.fromarray(img).save(img_p)
            quads.append({"k": k, "img": img_p, "o": [float(O[0]), float(O[1])],
                          "d": [float(D[0]), float(D[1])], "n": [nx, ny],
                          "len": el, "h": H, "off": QOFF, "dz": dz,
                          "cov": round(cov, 3), "strip_m": round(sw / RES, 1),
                          "align_rows": nrows})
        meta = {"mode": "poly", "pose": None, "quads": quads,
                "edges": [q["k"] for q in quads]}
    else:
        cx, cy, rot = entry["cx"], entry["cy"], entry["rot"]
        # pano and aim into building-local coords (same math as refine_building)
        cr, sr = math.cos(-rot), math.sin(-rot)

        def to_local(sx, sy):
            dx0, dy0 = sx - cx, sy - cy
            return (cr * dx0 - sr * dy0, sr * dx0 + cr * dy0)
        plocal = to_local(*pscene)
        alocal = to_local(*aimscene)
        C, F, R, U = _cam_basis(plocal, alocal)
        for k, q in enumerate(_front_masses(desc)):
            if q["y_f"] - plocal[1] < MIN_DIST:   # quality gate 3: worm's-eye smear
                continue
            z_rows = [r * q["fh"] + q["fh"] * 0.52 for r in range(q["floors"])]
            O = np.array([q["x0"], q["y_f"], 0.0])
            D = (1.0, 0.0)
            dz, nrows = _align_dz(facts, C, F, R, U, O, (0.0, -1.0),
                                  photo.size, z_rows, q["h"])
            out, valid = _rectify(photo, C, F, R, U, O, D, q["len"], q["h"], dz)
            img, cov, sw = _strip_and_tile(out, valid)
            if img is None or sw / RES < max(3.0, 0.10 * q["len"]):
                continue
            if _sky_frac(img) > SKY_MAX:      # quality gate 2: plane hits sky
                continue
            img_p = os.path.join(tdir, f"facade_proj_{k}.png")
            Image.fromarray(img).save(img_p)
            quads.append({"k": k, "img": img_p, "o": [q["x0"], q["y_f"]],
                          "d": [1.0, 0.0], "n": [0.0, -1.0],
                          "len": q["len"], "h": q["h"], "off": QOFF, "dz": dz,
                          "cov": round(cov, 3), "strip_m": round(sw / RES, 1),
                          "align_rows": nrows})
        meta = {"mode": "obb", "pose": [cx, cy, rot], "quads": quads}
    if not quads:
        meta["quads"] = []
    with open(meta_p, "w") as f:
        json.dump(meta, f, indent=1)
    return meta


# ------------------------------------------------------------- Blender chunk

PROJ_QUADS = r'''
import bpy, json as _pj, mathutils as _pmu
for _q in _pj.loads(%r):
    _mname = "facadeproj_%%d_%%d" %% (_q["id"], _q["k"])
    _mt = bpy.data.materials.get(_mname)
    if not _mt:
        _mt = bpy.data.materials.new(_mname); _mt.use_nodes = True
        _nt = _mt.node_tree
        for _n in list(_nt.nodes): _nt.nodes.remove(_n)
        _out = _nt.nodes.new("ShaderNodeOutputMaterial")
        _bs = _nt.nodes.new("ShaderNodeBsdfPrincipled")
        _bs.inputs["Roughness"].default_value = 0.85
        _tx = _nt.nodes.new("ShaderNodeTexImage")
        # the live session caches image datablocks across CLEAR (which removes
        # only objects/materials) -- a re-projected texture at the same path
        # would silently render with the OLD pixels (and pack_all would keep
        # them); drop any stale datablock for this path before loading
        for _im in [i for i in bpy.data.images if i.filepath == _q["img"]]:
            bpy.data.images.remove(_im)
        _tx.image = bpy.data.images.load(_q["img"], check_existing=False)
        _nt.links.new(_tx.outputs["Color"], _bs.inputs["Base Color"])
        _nt.links.new(_bs.outputs["BSDF"], _out.inputs["Surface"])
    _o = _q["o"]; _d = _q["d"]; _n2 = _q["n"]
    _ox, _oy = _o[0] + _n2[0] * _q["off"], _o[1] + _n2[1] * _q["off"]
    _L, _H = _q["len"], _q["h"]
    _vs = [(_ox, _oy, 0.05), (_ox + _d[0] * _L, _oy + _d[1] * _L, 0.05),
           (_ox + _d[0] * _L, _oy + _d[1] * _L, _H), (_ox, _oy, _H)]
    _me = bpy.data.meshes.new("ProjQ_%%d_%%d" %% (_q["id"], _q["k"]))
    _me.from_pydata(_vs, [], [(0, 1, 2, 3)])
    _uv = _me.uv_layers.new(name="UVMap")
    for _li, _uvco in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        _uv.data[_li].uv = _uvco
    _me.materials.append(_mt)
    _ob = bpy.data.objects.new("Proj_%%d_%%d" %% (_q["id"], _q["k"]), _me)
    bpy.context.scene.collection.objects.link(_ob)
    if _q.get("pose"):
        _p = _q["pose"]
        _ob.matrix_world = (_pmu.Matrix.Translation((_p[0], _p[1], 0))
                            @ _pmu.Matrix.Rotation(_p[2], 4, 'Z')) @ _ob.matrix_world
'''


def scene_chunk(out):
    """Blender code for every cached projection quad in the scene (used by
    city_generate.assemble). Returns (code, ids_with_quads: {id: meta})."""
    entries, metas = [], {}
    for meta_p in sorted(glob.glob(os.path.join(os.path.abspath(out), "buildings",
                                                "*", "textures", "facade_proj.json"))):
        bid = int(meta_p.split(os.sep)[-3])
        meta = json.load(open(meta_p))
        if not meta.get("quads"):
            continue
        metas[bid] = meta
        for q in meta["quads"]:
            # Blender runs with its own CWD: rebuild the image path absolute
            # from the meta file's location, whatever was stored
            img = os.path.join(os.path.dirname(meta_p), os.path.basename(q["img"]))
            entries.append({**q, "img": img, "id": bid, "pose": meta.get("pose")})
    if not entries:
        return "", {}
    return PROJ_QUADS % json.dumps(entries), metas


# -------------------------------------------------------------------- run-all

def run_all(out, force=False, ids=None):
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas, anchor = {m["id"]: m for m in d["buildings"]}, d["anchor"]
    placements = json.load(open(os.path.join(out, "agent_placements.json")))
    done = skipped = 0
    for entry in placements:
        if ids and str(entry["id"]) not in ids:
            continue
        bdir = os.path.join(out, "buildings", str(entry["id"]))
        m = metas.get(entry["id"])
        if m is None:
            continue
        meta = project_building(entry, m, anchor, bdir, force)
        if meta and meta.get("quads"):
            done += 1
            qs = meta["quads"]
            print(f"[{entry['id']}] {meta['mode']}: {len(qs)} quad(s), "
                  f"cov {qs[0]['cov']:.2f}, strip {qs[0]['strip_m']}m, "
                  f"dz {qs[0]['dz']:+.2f} ({qs[0]['align_rows']} rows)")
        else:
            skipped += 1
    print(f"[facade-proj] {done} buildings projected, {skipped} skipped "
          "(glass / no pano / low coverage)")


# ------------------------------------------------------------------- eval mode

def _eval(out, ids=None):
    """Three-way appearance eval on the subset, all from the SAME pano camera:
    untextured vs tiled-patch textures vs tiles + photo projection, DreamSim
    against the street photo. Zero-LLM. Writes proj_eval.json."""
    from img2city.building.generate import _send, RENDER_OUT, RENDER_CAM, CLEAR, LIGHT_STREET, spec_to_code
    from img2city.city.generate import (PANO_RENDER, CAM_GATE, POLY_BUILD, TEX_OVERRIDE,
                               poly_params, load_components_src, obb)
    from img2city.judge.perceptual import dreamsim_dist
    out = os.path.abspath(out)                 # Blender saves renders from its own CWD
    d = json.load(open(os.path.join(out, "buildings.json")))
    bmetas, anchor = d["buildings"], d["anchor"]
    placements = {e["id"]: e for e in json.load(open(os.path.join(out, "agent_placements.json")))}
    if ids is None:
        ids = json.load(open(os.path.join(out, "eval_subset.json")))
    comp = load_components_src()
    kx = KX * math.cos(math.radians(anchor["lat0"]))
    rows = []
    for sid in ids:
        osmid = int(sid)
        m = next((mm for mm in bmetas if mm["id"] == osmid), None)
        entry = placements.get(osmid)
        bdir = os.path.join(out, "buildings", str(osmid))
        photo = os.path.join(bdir, "streetview.png")
        pano_p = os.path.join(bdir, "pano.json")
        if not (m and entry and os.path.exists(photo) and os.path.exists(pano_p)):
            print(f"[{osmid}] missing inputs -- skipped")
            continue
        m["obb"] = obb(m["pts"])
        spec = json.load(open(os.path.join(bdir, "spec.json")))
        meta = project_building(entry, m, anchor, bdir)
        pano = tuple(json.load(open(pano_p)))
        rot = entry["rot"]
        cx, cy = m["obb"][0], m["obb"][1]
        dx = (pano[1] - anchor["lon0"]) * kx - cx
        dy = (pano[0] - anchor["lat0"]) * KY - cy
        lx = math.cos(-rot) * dx - math.sin(-rot) * dy
        ly = math.sin(-rot) * dx + math.cos(-rot) * dy
        dist = math.hypot(lx, ly)
        L, W = m["obb"][2], m["obb"][3]
        poly_mode = "poly" in entry
        # minimum-standoff guard, duplicated from city_generate.refine_building --
        # all three variants render from the SAME camera so the comparison is fair
        _hs = max(int(mm.get("floors", spec.get("floors", 4))) for mm in
                  (spec.get("masses") or [{}])) * float(spec.get("floor_h", 3.2))
        stand = max(12.0, 1.1 * _hs)
        if not poly_mode and (ly > -(W / 2 + 4.0) or dist < 8.0):
            lx = max(-L / 2, min(L / 2, lx))
            ly = -(W / 2 + stand)
        H = _hs
        zt = min(H * 0.55, 2.5 + 0.32 * dist)
        tex = TEX_OVERRIDE % os.path.join(bdir, "textures")
        proj_code = ""
        if meta and meta.get("quads"):
            qs = [{**q, "id": osmid,
                   "img": os.path.join(bdir, "textures", os.path.basename(q["img"])),
                   "pose": None if poly_mode else [0.0, 0.0, 0.0]}
                  for q in meta["quads"]]
            proj_code = PROJ_QUADS % json.dumps(qs)
        # the kit must know a quad is coming, exactly as at assembly: without the
        # photo_proj flag the OLD stucco band (offset 0.32 > QOFF) renders IN
        # FRONT of the quad and can hide it entirely (found on 723363790, whose
        # full-height band made the proj render pixel-identical to tex). Only the
        # "proj" variant gets the flag -- untex/tex must keep their own glazing.
        has_quads = bool(meta and meta.get("quads"))

        def _build(flagged):
            if poly_mode:
                pparams = poly_params(spec, pts=m["pts"])
                if flagged:
                    pparams["photo_proj_edges"] = meta.get("edges", [])
                return POLY_BUILD % json.dumps(pparams)
            sp = {**spec, "photo_proj": True} if flagged else spec
            return spec_to_code(json.dumps(sp), comp)
        if poly_mode:
            xs = [q2[0] for q2 in m["pts"]]; ys = [q2[1] for q2 in m["pts"]]
            scale = 1.25 * max(max(xs) - min(xs), max(ys) - min(ys))
            cam = (PANO_RENDER % (cx, cy, zt, cx + dx, cy + dy)) + RENDER_CAM \
                + (CAM_GATE % min(20.0, scale / 5.0)) + LIGHT_STREET
        else:
            cam = (PANO_RENDER % (0, 0, zt, lx, ly)) + RENDER_CAM \
                + (CAM_GATE % (L / 4.0)) + LIGHT_STREET
        row = {"id": osmid, "mode": "poly" if poly_mode else "obb",
               "quads": len(meta["quads"]) if meta else 0}
        for name, extra in (("untex", ""), ("tex", tex), ("proj", tex + proj_code)):
            png = os.path.join(bdir, "textures", f"eval_{name}.png")
            build = _build(name == "proj" and has_quads)
            head = (CLEAR + "\n" + comp + "\n" + build) if poly_mode \
                else (CLEAR + "\n" + build)
            _res, err = _send(head + "\n" + cam + extra + (RENDER_OUT % png),
                              timeout=600)
            if err:
                print(f"[{osmid}] {name} render failed: {err[:80]}")
                row[name] = None
                continue
            row[name] = dreamsim_dist(png, photo)
        rows.append(row)
        print(f"[{osmid}] ds untex {row.get('untex')} tex {row.get('tex')} "
              f"proj {row.get('proj')} ({row['quads']} quads)")
    ok = [r for r in rows if r.get("untex") is not None and r.get("proj") is not None]
    withq = [r for r in ok if r["quads"]]
    if withq:
        mu = sum(r["untex"] for r in withq) / len(withq)
        mp = sum(r["proj"] for r in withq) / len(withq)
        mt = sum(r["tex"] for r in withq if r["tex"] is not None) / max(1, len(
            [r for r in withq if r["tex"] is not None]))
        closer = sum(1 for r in withq if r["proj"] < r["untex"])
        print(f"\n[proj-eval] {len(withq)} buildings with quads: DreamSim "
              f"untex {mu:.4f} | tiled {mt:.4f} | proj {mp:.4f} "
              f"({closer}/{len(withq)} proj closer than untex)")
    with open(os.path.join(out, "proj_eval.json"), "w") as f:
        json.dump(rows, f, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ids", nargs="*", help="only these osmids")
    ap.add_argument("--eval", action="store_true",
                    help="three-way DreamSim eval on the eval subset (or --ids)")
    a = ap.parse_args()
    if a.eval:
        _eval(a.out, a.ids)
    else:
        run_all(a.out, a.force, set(a.ids) if a.ids else None)


if __name__ == "__main__":
    main()
