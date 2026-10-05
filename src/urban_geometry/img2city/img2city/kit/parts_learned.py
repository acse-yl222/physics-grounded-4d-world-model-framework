"""img2city/kit/parts_learned.py -- REGION-DIALECT parts authored by library_grow.
Additive only: concatenated after components.py, registered via
PARTS.update; gate 0 guarantees no name here shadows a core part.
"""


# ---- learned_from: london · cluster: trainshed · gates: smoke+regress+lift ----
import math


def _xs_mesh(name, verts, faces, matname):
    """non-box surface/solid from explicit geometry (the box() helper cannot taper)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(MAT[matname])
    return o


def _xs_beam(name, p0, p1, thick, matname):
    """square beam between two points that share the same x (rotates in the y-z plane)."""
    dy = p1[1] - p0[1]
    dz = p1[2] - p0[2]
    ln = max(0.06, math.hypot(dy, dz))
    c = [(p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, (p0[2] + p1[2]) * 0.5]
    o = box(name, c, [thick, ln, thick], matname)
    o.rotation_euler = (math.atan2(dz, dy), 0.0, 0.0)
    return o


def _xs_outline(length, width, tip_w, taper, nose, segs, sign, cx):
    """(x, half_width) samples: broad blunt end -> straight taper -> rounded prow tip.
    sign = +1 puts the tip at +x, -1 at -x."""
    L = max(2.0, float(length))
    hw = max(0.4, float(width) * 0.5)
    ht = min(max(0.2, float(tip_w) * 0.5), hw * 0.9)
    nz = max(0.3, min(float(nose), L * 0.45))
    tl = max(0.0, min(float(taper) * L, L - nz - 0.5))
    d = [(0.0, hw), (L - nz - tl, hw), (L - nz, ht)]
    n = max(2, int(segs))
    for k in range(1, n + 1):
        th = 0.5 * math.pi * k / n
        d.append((L - nz + nz * math.sin(th), max(0.10, ht * math.cos(th))))
    x0 = cx - sign * L * 0.5
    out = []
    for dd, h in d:
        x = x0 + sign * dd
        if out and abs(x - out[-1][0]) < 1e-4:
            continue
        out.append((x, h))
    return out


def _xs_hw_at(samples, x):
    ss = sorted(samples, key=lambda s: s[0])
    if x <= ss[0][0]:
        return ss[0][1]
    if x >= ss[-1][0]:
        return ss[-1][1]
    for k in range(len(ss) - 1):
        x0, h0 = ss[k]
        x1, h1 = ss[k + 1]
        if x0 <= x <= x1:
            t = 0.0 if (x1 - x0) < 1e-9 else (x - x0) / (x1 - x0)
            return h0 + (h1 - h0) * t
    return ss[-1][1]


def _xs_prism(name, loop, z0, z1, matname):
    m = len(loop)
    verts = [(x, y, z0) for (x, y) in loop] + [(x, y, z1) for (x, y) in loop]
    faces = [[k for k in range(m - 1, -1, -1)], [m + k for k in range(m)]]
    for k in range(m):
        k2 = (k + 1) % m
        faces.append([k, k2, m + k2, m + k])
    return _xs_mesh(name, verts, faces, matname)


def _xs_roof_band(name, samples, cy, eaves, ridge, f0, f1, side, matname):
    """strip of one roof plane between two slope fractions (0 = ridge, 1 = eave)."""
    verts = []
    faces = []
    for (x, h) in samples:
        for f in (f0, f1):
            verts.append((x, cy + side * h * f, ridge + (eaves - ridge) * f))
    for k in range(len(samples) - 1):
        a = 2 * k
        faces.append([a, a + 1, a + 3, a + 2])
    return _xs_mesh(name, verts, faces, matname)


def _xs_fascia(name, samples, cy, side, z_top, drop, matname):
    verts = []
    faces = []
    for (x, h) in samples:
        verts.append((x, cy + side * h, z_top))
        verts.append((x, cy + side * h, z_top - drop))
    for k in range(len(samples) - 1):
        a = 2 * k
        faces.append([a, a + 1, a + 3, a + 2])
    return _xs_mesh(name, verts, faces, matname)


def _xs_gable_roof(i, tag, samples, cy, eaves, ridge, glaze, glass_mat, roof_mat, bar_mat, bars):
    """two sloping planes meeting on ONE long central ridge; the upper `glaze` fraction
    of each slope is translucent, the rest opaque. White bars make the glass read."""
    out = []
    g = min(0.98, max(0.0, float(glaze)))
    for side, sn in ((1.0, "P"), (-1.0, "M")):
        if g > 0.02:
            out.append(_xs_roof_band("%sGlass%d_%s" % (tag, i, sn), samples, cy, eaves, ridge, 0.0, g, side, glass_mat))
        if g < 0.98:
            out.append(_xs_roof_band("%sSlate%d_%s" % (tag, i, sn), samples, cy, eaves, ridge, g, 1.0, side, roof_mat))
    xs = sorted([s[0] for s in samples])
    out.append(box("%sRidge%d" % (tag, i), [(xs[0] + xs[-1]) * 0.5, cy, ridge + 0.10],
                   [xs[-1] - xs[0], 0.34, 0.30], bar_mat))
    nb = max(0, int(bars))
    for k in range(nb):
        x = xs[0] + (xs[-1] - xs[0]) * (k + 0.5) / nb
        h = _xs_hw_at(samples, x)
        for side, sn in ((1.0, "P"), (-1.0, "M")):
            out.append(_xs_beam("%sBar%d_%02d%s" % (tag, i, k, sn), [x, cy, ridge + 0.07],
                                [x, cy + side * h, eaves + 0.07], 0.11, bar_mat))
    return out


def _xs_truss(i, tag, k, x, cy, hw, eaves, ridge, thick, matname, struts, curved, rib_segs, rib_curve):
    """one transverse bay frame: tie beam + either straight lattice rafters (posts and
    diagonals) or curved ribs with hangers up to the roof plane."""
    out = [box("%sTie%d_%02d" % (tag, i, k), [x, cy, eaves], [thick, 2.0 * hw, thick * 0.7], matname)]
    ns = max(2, int(rib_segs))
    nst = max(1, int(struts))
    for side, sn in ((1.0, "P"), (-1.0, "M")):
        if curved:
            pts = []
            for j in range(ns + 1):
                t = float(j) / ns
                pts.append([x, cy + side * hw * (1.0 - t), eaves + (ridge - eaves) * (t ** rib_curve)])
            for j in range(ns):
                out.append(_xs_beam("%sRib%d_%02d%s%d" % (tag, i, k, sn, j), pts[j], pts[j + 1], thick, matname))
            for j in range(1, ns):
                t = float(j) / ns
                zp = eaves + (ridge - eaves) * t
                out.append(_xs_beam("%sHang%d_%02d%s%d" % (tag, i, k, sn, j), pts[j],
                                    [pts[j][0], pts[j][1], zp], thick * 0.5, matname))
        else:
            out.append(_xs_beam("%sRaft%d_%02d%s" % (tag, i, k, sn), [x, cy, ridge],
                                [x, cy + side * hw, eaves], thick, matname))
            for j in range(1, nst):
                f = float(j) / nst
                y = cy + side * hw * f
                z = ridge + (eaves - ridge) * f
                out.append(_xs_beam("%sPost%d_%02d%s%d" % (tag, i, k, sn, j), [x, y, eaves], [x, y, z], thick * 0.55, matname))
                y2 = cy + side * hw * min(1.0, f + 1.0 / nst)
                out.append(_xs_beam("%sDiag%d_%02d%s%d" % (tag, i, k, sn, j), [x, y2, eaves], [x, y, z], thick * 0.45, matname))
    return out


def _xs_column(i, tag, k, j, x, y, h, r, matname, cap_mat):
    """ornate cast-iron column: shaft cylinder, splayed base, capital, two brackets."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=h, location=(x, y, h * 0.5))
    o = bpy.context.active_object
    o.name = "%sCol%d_%02d_%d" % (tag, i, k, j)
    o.data.materials.append(MAT[matname])
    out = [o]
    out.append(box("%sColBase%d_%02d_%d" % (tag, i, k, j), [x, y, 0.22], [r * 3.0, r * 3.0, 0.44], matname))
    out.append(box("%sColCap%d_%02d_%d" % (tag, i, k, j), [x, y, h - 0.20], [r * 3.2, r * 3.2, 0.40], cap_mat))
    for side, sn in ((1.0, "P"), (-1.0, "M")):
        out.append(_xs_beam("%sColBr%d_%02d_%d%s" % (tag, i, k, j, sn), [x, y + side * r, h - 0.95],
                            [x, y + side * r * 3.4, h - 0.10], 0.16, cap_mat))
    return out


def prow_shed(p, i):
    """Flatiron trainshed mass: the plan runs from a BROAD BLUNT end to a narrow
    ROUNDED PROW (the wedge that follows a road junction), the walls are brick, and a
    single long central ridge carries a pitched roof whose upper `glaze` fraction is
    translucent, sat on exposed lattice trusses in regular bays. Use with
    {"_set": {"masses": []}} -- this part IS the mass, not an addition to a box."""
    L = float(p.get("length", 40.0))
    W = float(p.get("width", 20.0))
    at = p.get("at", [0.0, 0.0])
    cx = float(at[0])
    cy = float(at[1])
    eaves = float(p.get("wall_height", 4.0))
    ridge = float(p.get("ridge_height", eaves + 2.4))
    sign = -1.0 if str(p.get("prow", "+x")).lower().startswith("-") else 1.0
    samples = _xs_outline(L, W, float(p.get("tip_width", max(1.5, W * 0.12))),
                          float(p.get("taper", 0.45)), float(p.get("nose", 3.0)),
                          int(p.get("nose_segs", 6)), sign, cx)
    wall_mat = str(p.get("wall_material", "brick"))
    out = []
    loop = [(x, cy + h) for (x, h) in samples] + [(x, cy - h) for (x, h) in reversed(samples)]
    out.append(_xs_prism("XSProw%d" % i, loop, 0.0, eaves, wall_mat))
    bd = float(p.get("band", 0.5))
    if bd > 0.02:
        lp2 = [(x, cy + h + 0.16) for (x, h) in samples] + [(x, cy - h - 0.16) for (x, h) in reversed(samples)]
        out.append(_xs_prism("XSProwBand%d" % i, lp2, eaves - bd, eaves, str(p.get("band_material", "stone"))))
    xb, hb = samples[0]
    out.append(_xs_mesh("XSProwGable%d" % i, [(xb, cy - hb, eaves), (xb, cy + hb, eaves), (xb, cy, ridge)],
                        [[0, 1, 2]], wall_mat))
    xt, ht = samples[-1]
    out.append(_xs_mesh("XSProwGableT%d" % i, [(xt, cy - ht, eaves), (xt, cy + ht, eaves), (xt, cy, ridge)],
                        [[0, 1, 2]], wall_mat))
    out += _xs_gable_roof(i, "XSProw", samples, cy, eaves, ridge, float(p.get("glaze", 0.70)),
                          str(p.get("glass_material", "vault_glass")), str(p.get("roof_material", "slate")),
                          str(p.get("bar_material", "white")), int(p.get("glazing_bars", 14)))
    bays = max(0, int(p.get("bays", 8)))
    fmat = str(p.get("frame_material", "iron"))
    fth = float(p.get("frame_thickness", 0.22))
    xs0 = min(s[0] for s in samples)
    xs1 = max(s[0] for s in samples)
    for k in range(bays):
        x = xs0 + (xs1 - xs0) * (k + 0.5) / bays
        h = _xs_hw_at(samples, x)
        out += _xs_truss(i, "XSProw", k, x, cy, h, eaves, ridge, fth, fmat,
                         int(p.get("struts", 3)), bool(p.get("curved_ribs", False)),
                         int(p.get("rib_segs", 5)), float(p.get("rib_curve", 1.6)))
    return out


def platform_canopy(p, i):
    """Open platform trainshed: rows of ornate cast-iron columns carrying curved rib
    trusses under a pitched glazed canopy whose plan narrows to a wedge tip at one end.
    Builds NO walls and nothing above the ridge, so the result reads as a single low
    open story. Use with {"_set": {"masses": [], "floors": 1}}."""
    L = float(p.get("length", 40.0))
    W = float(p.get("width", 18.0))
    at = p.get("at", [0.0, 0.0])
    cx = float(at[0])
    cy = float(at[1])
    eaves = float(p.get("eaves_height", 4.2))
    ridge = float(p.get("ridge_height", eaves + 2.0))
    sign = -1.0 if str(p.get("tip", "+x")).lower().startswith("-") else 1.0
    samples = _xs_outline(L, W, float(p.get("tip_width", max(1.5, W * 0.16))),
                          float(p.get("taper", 0.40)), float(p.get("nose", 3.0)),
                          int(p.get("nose_segs", 6)), sign, cx)
    col_mat = str(p.get("column_material", "iron"))
    frame_mat = str(p.get("frame_material", col_mat))
    out = []
    out += _xs_gable_roof(i, "XSCan", samples, cy, eaves, ridge, float(p.get("glaze", 0.80)),
                          str(p.get("glass_material", "vault_glass")), str(p.get("roof_material", "slate_dark")),
                          str(p.get("bar_material", "white")), int(p.get("glazing_bars", 12)))
    fas = float(p.get("fascia", 0.45))
    if fas > 0.02:
        for side, sn in ((1.0, "P"), (-1.0, "M")):
            out.append(_xs_fascia("XSCanFascia%d_%s" % (i, sn), samples, cy, side, eaves + 0.05, fas, frame_mat))
    bays = max(1, int(p.get("bays", 8)))
    fth = float(p.get("frame_thickness", 0.20))
    fr = p.get("column_fracs", [-0.55, 0.55])
    cr = float(p.get("column_radius", 0.26))
    ch = float(p.get("column_height", eaves))
    cap_mat = str(p.get("capital_material", frame_mat))
    xs0 = min(s[0] for s in samples)
    xs1 = max(s[0] for s in samples)
    for k in range(bays):
        x = xs0 + (xs1 - xs0) * (k + 0.5) / bays
        h = _xs_hw_at(samples, x)
        out += _xs_truss(i, "XSCan", k, x, cy, h, eaves, ridge, fth, frame_mat,
                         int(p.get("struts", 3)), bool(p.get("curved_ribs", True)),
                         int(p.get("rib_segs", 6)), float(p.get("rib_curve", 1.6)))
        for j, f in enumerate(fr):
            out += _xs_column(i, "XSCan", k, j, x, cy + float(f) * h, ch, cr, col_mat, cap_mat)
    return out


def arch_arcade(p, i):
    """A run of masonry wall pierced by a row of ROUND-ARCHED openings (an arcade),
    with voussoir rings, plinth and cornice. The arch heads are cut by stepping the
    soffit of narrow wall slats, so no boolean is needed. axis 'x' or 'y'."""
    at = p.get("at", [0.0, 0.0])
    cx = float(at[0])
    cy = float(at[1])
    Lw = float(p.get("length", 24.0))
    H = float(p.get("height", 6.0))
    t = float(p.get("thickness", 0.7))
    n = max(1, int(p.get("count", 5)))
    pw = float(p.get("pier", 1.2))
    spring = float(p.get("springing", H * 0.45))
    wall_mat = str(p.get("material", "brick"))
    arch_mat = str(p.get("arch_material", "stone"))
    horiz = not str(p.get("axis", "x")).lower().startswith("y")
    span = max(0.6, (Lw - (n + 1) * pw) / n)
    r = min(span * 0.5, max(0.4, H - spring - 0.35))
    ns = max(4, int(p.get("arch_segs", 12)))
    nv = max(5, int(p.get("ring_segs", 11)))
    rt = float(p.get("ring", 0.30))
    u0 = -Lw * 0.5
    out = []
    for k in range(n + 1):
        u = u0 + pw * 0.5 + k * (pw + span)
        c = [cx + u, cy, H * 0.5] if horiz else [cx, cy + u, H * 0.5]
        s = [pw, t, H] if horiz else [t, pw, H]
        out.append(box("XSArcPier%d_%02d" % (i, k), c, s, wall_mat))
    for k in range(n):
        uc = u0 + pw + span * 0.5 + k * (pw + span)
        for j in range(ns):
            du = -span * 0.5 + span * (j + 0.5) / ns
            zs = spring + (math.sqrt(max(0.0, r * r - du * du)) if abs(du) < r else 0.0)
            hg = max(0.06, H - zs)
            c = [cx + uc + du, cy, zs + hg * 0.5] if horiz else [cx, cy + uc + du, zs + hg * 0.5]
            s = [span / ns + 0.02, t, hg] if horiz else [t, span / ns + 0.02, hg]
            out.append(box("XSArcSpan%d_%02d_%02d" % (i, k, j), c, s, wall_mat))
        seg = 1.15 * math.pi * r / nv
        for j in range(nv):
            th = math.pi * (j + 0.5) / nv
            u = uc - r * math.cos(th)
            z = spring + r * math.sin(th)
            if horiz:
                o = box("XSArcVous%d_%02d_%02d" % (i, k, j), [cx + u, cy, z], [seg, t * 1.06, rt], arch_mat)
                o.rotation_euler = (0.0, th - math.pi * 0.5, 0.0)
            else:
                o = box("XSArcVous%d_%02d_%02d" % (i, k, j), [cx, cy + u, z], [t * 1.06, seg, rt], arch_mat)
                o.rotation_euler = (math.pi * 0.5 - th, 0.0, 0.0)
            out.append(o)
    pl = float(p.get("plinth", 0.5))
    if pl > 0.02:
        c = [cx, cy, pl * 0.5]
        s = [Lw, t * 1.25, pl] if horiz else [t * 1.25, Lw, pl]
        out.append(box("XSArcPlinth%d" % i, c, s, str(p.get("plinth_material", "stone"))))
    cw = float(p.get("cornice", 0.45))
    if cw > 0.02:
        c = [cx, cy, H - cw * 0.5]
        s = [Lw, t * 1.30, cw] if horiz else [t * 1.30, Lw, cw]
        out.append(box("XSArcCorn%d" % i, c, s, str(p.get("cornice_material", "stone"))))
    bk = float(p.get("backing", 1.0))
    if abs(bk) > 0.01:
        off = t * 0.55 + 0.06
        c = [cx, cy + bk * off, H * 0.5] if horiz else [cx + bk * off, cy, H * 0.5]
        s = [Lw, 0.10, H] if horiz else [0.10, Lw, H]
        out.append(box("XSArcBack%d" % i, c, s, str(p.get("backing_material", "interior"))))
    return out


PARTS_LEARNED = {"prow_shed": prow_shed, "platform_canopy": platform_canopy, "arch_arcade": arch_arcade}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: roundcorner · gates: smoke+regress+lift ----
def _rr_plan(L, W, radii, seg=8):
    """Rounded-rectangle plan: CCW (x,y) points for an L x W rectangle centred on the
    origin whose four corners are filleted by radii [SW, SE, NE, NW] (-y is the street
    front). Returns (points, owner) where owner[k] is the corner index that generated
    the point, or -1 for a sharp corner -- used to tag which side faces are curved."""
    hx, hy = L / 2.0, W / 2.0
    rmax = min(hx, hy)
    rs = [max(0.0, min(float(r), rmax)) for r in radii]
    cor = [(-hx, -hy, 180.0), (hx, -hy, 270.0), (hx, hy, 0.0), (-hx, hy, 90.0)]
    sx = [-1.0, 1.0, 1.0, -1.0]
    sy = [-1.0, -1.0, 1.0, 1.0]
    pts, owner = [], []
    for c in range(4):
        r = rs[c]
        px, py, a0 = cor[c]
        if r <= 1e-6:
            pts.append((px, py))
            owner.append(-1)
            continue
        ax, ay = px - sx[c] * r, py - sy[c] * r
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / float(seg))
            pts.append((ax + r * math.cos(a), ay + r * math.sin(a)))
            owner.append(c)
    return pts, owner


def _rr_shell(name, pts, z0, z1, mat, mat2=None, owner=None, cap_top=False, cap_bottom=False):
    """Extrude a closed plan polygon between z0 and z1. If mat2 is given, faces whose
    plan edge lies on a corner arc get material slot 1 (curved glass drum ends)."""
    n = len(pts)
    verts = [(x, y, z0) for (x, y) in pts] + [(x, y, z1) for (x, y) in pts]
    faces, curved = [], []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((k, k2, n + k2, n + k))
        curved.append(owner is not None and owner[k] >= 0 and owner[k] == owner[k2])
    if cap_top:
        faces.append(tuple(range(n, 2 * n)))
        curved.append(False)
    if cap_bottom:
        faces.append(tuple(range(n - 1, -1, -1)))
        curved.append(False)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(MAT[mat])
    if mat2 is not None:
        o.data.materials.append(MAT[mat2])
        for k, poly in enumerate(me.polygons):
            if k < len(curved) and curved[k]:
                poly.material_index = 1
    return o


def rounded_block(p, i):
    """Extruded rounded-rectangle MASS: a block whose corners are filleted by a per-corner
    radius, so a footprint can have one bowed corner, one semicircular short end (radius =
    W/2 on both corners of that end), or four strongly rounded corners. Optional extras that
    must follow the curve: horizontal glazing bands repeated once per floor, a light parapet
    band round the whole roof edge, and a different material on the arc faces only
    (curve_material="glass" -> curved full-height glass drum end)."""
    L, W = [float(v) for v in p.get("size", [30.0, 20.0])]
    H = float(p.get("height", 10.0))
    z0 = float(p.get("base", 0.0))
    at = p.get("at", [0.0, 0.0])
    ox, oy = float(at[0]), float(at[1])
    rr = p.get("radii", p.get("radius", 0.0))
    radii = [float(v) for v in rr] if isinstance(rr, (list, tuple)) else [float(rr)] * 4
    seg = max(2, int(p.get("seg", 8)))
    mat = p.get("material", "stone")
    cmat = p.get("curve_material", None)

    pts, owner = _rr_plan(L, W, radii, seg)
    pts = [(x + ox, y + oy) for (x, y) in pts]
    out = [_rr_shell("RBlock%d" % i, pts, z0, z0 + H, mat, cmat, owner, True, True)]

    nb = int(p.get("band_count", 0))
    if nb > 0:
        bh = float(p.get("band_h", 2.0))
        pit = float(p.get("band_pitch", 3.6))
        bz = float(p.get("band_z0", 1.0))
        bo = float(p.get("band_out", 0.12))
        bpts, _bo = _rr_plan(L + 2 * bo, W + 2 * bo, [r + bo for r in radii], seg)
        bpts = [(x + ox, y + oy) for (x, y) in bpts]
        for k in range(nb):
            za = z0 + bz + pit * k
            out.append(_rr_shell("RBand%d_%02d" % (i, k), bpts, za, za + bh,
                                 p.get("band_material", "glass")))

    ph = float(p.get("parapet_h", 0.0))
    if ph > 0.0:
        po = float(p.get("parapet_out", 0.3))
        pd = float(p.get("parapet_drop", 0.4))
        ppts, _po = _rr_plan(L + 2 * po, W + 2 * po, [r + po for r in radii], seg)
        ppts = [(x + ox, y + oy) for (x, y) in ppts]
        out.append(_rr_shell("RParapet%d" % i, ppts, z0 + H - pd, z0 + H + ph,
                             p.get("parapet_material", "white"), None, None, True, False))
    return out


def roof_deck(p, i):
    """Flat paved / vegetated roof terrace patch sitting on an existing roof slab: a thin
    plate of any material (brick = terracotta paving, plant = green roof) with an optional
    low kerb upstand round it, and optional rounded corners so it can sit against a bowed
    corner."""
    at = p.get("at", [0.0, 0.0, 10.0])
    cx, cy, z = float(at[0]), float(at[1]), float(at[2])
    sx, sy = [float(v) for v in p.get("size", [20.0, 15.0])]
    t = float(p.get("thickness", 0.3))
    rr = p.get("radii", p.get("radius", 0.0))
    radii = [float(v) for v in rr] if isinstance(rr, (list, tuple)) else [float(rr)] * 4
    seg = max(2, int(p.get("seg", 8)))
    pts, _ow = _rr_plan(sx, sy, radii, seg)
    pts = [(x + cx, y + cy) for (x, y) in pts]
    out = [_rr_shell("Deck%d" % i, pts, z, z + t, p.get("material", "brick"),
                     None, None, True, True)]
    kh = float(p.get("kerb_h", 0.0))
    if kh > 0.0:
        ko = float(p.get("kerb_out", 0.25))
        kpts, _k = _rr_plan(sx + 2 * ko, sy + 2 * ko, [r + ko for r in radii], seg)
        kpts = [(x + cx, y + cy) for (x, y) in kpts]
        out.append(_rr_shell("DeckKerb%d" % i, kpts, z, z + t + kh,
                             p.get("kerb_material", "stone"), None, None, True, False))
    return out


def roof_light_well(p, i):
    """Rectangular courtyard light-well cut down into a roof slab: a recessed floor at
    depth, four reveal walls at the rim so the opening reads as a hole, and an optional
    cover -- cover="glass" adds a pale glazed skylight of rectangular panes with a bar
    grid, cover="none" leaves it open (floor_material="plant" for a planted courtyard)."""
    at = p.get("at", [0.0, 0.0, 10.0])
    cx, cy, z = float(at[0]), float(at[1]), float(at[2])
    sx, sy = [float(v) for v in p.get("size", [16.0, 10.0])]
    d = float(p.get("depth", 5.0))
    t = float(p.get("wall_t", 0.5))
    wmat = p.get("wall_material", "stone")
    out = [box("WellFloor%d" % i, [cx, cy, z - d], [sx, sy, 0.4],
               p.get("floor_material", "slab"))]
    out.append(box("WellWN%d" % i, [cx, cy + (sy - t) / 2.0, z - d / 2.0], [sx, t, d], wmat))
    out.append(box("WellWS%d" % i, [cx, cy - (sy - t) / 2.0, z - d / 2.0], [sx, t, d], wmat))
    out.append(box("WellWE%d" % i, [cx + (sx - t) / 2.0, cy, z - d / 2.0], [t, sy - 2 * t, d], wmat))
    out.append(box("WellWW%d" % i, [cx - (sx - t) / 2.0, cy, z - d / 2.0], [t, sy - 2 * t, d], wmat))
    cover = str(p.get("cover", "none")).lower()
    if cover != "none":
        ch = float(p.get("cover_h", 0.6))
        iw, il = sx - 2 * t, sy - 2 * t
        out.append(box("WellGlass%d" % i, [cx, cy, z + ch], [iw, il, 0.12],
                       p.get("cover_material", "vault_glass")))
        bars = p.get("bars", [6, 2])
        nx, ny = max(1, int(bars[0])), max(1, int(bars[1]))
        bw = float(p.get("bar_w", 0.22))
        bh = float(p.get("bar_h", 0.3))
        bmat = p.get("bar_material", "white")
        for k in range(nx + 1):
            x = cx + (-0.5 + k / float(nx)) * iw
            out.append(box("WellBarX%d_%02d" % (i, k), [x, cy, z + ch + bh / 2.0],
                           [bw, il, bh], bmat))
        for k in range(ny + 1):
            y = cy + (-0.5 + k / float(ny)) * il
            out.append(box("WellBarY%d_%02d" % (i, k), [cx, y, z + ch + bh / 2.0],
                           [iw, bw, bh], bmat))
    return out


def rooflight_band(p, i):
    """Raised glazed / ribbed rooflight: a flat glass panel on low kerbs with evenly
    spaced ribs across it, optionally repeated `count` times at `pitch` to make long
    continuous glazed bands along a roof edge. cross_ribs>0 turns it into a gridded,
    latticed panel (rib_material="iron" for the grey lattice sort)."""
    at = p.get("at", [0.0, 0.0, 10.0])
    cx, cy, z = float(at[0]), float(at[1]), float(at[2])
    Lb, Wb = [float(v) for v in p.get("size", [20.0, 6.0])]
    axis = str(p.get("axis", "X")).upper()
    cnt = max(1, int(p.get("count", 1)))
    pitch = float(p.get("pitch", Wb * 1.6))
    kh = float(p.get("kerb_h", 0.4))
    kw = float(p.get("kerb_w", 0.35))
    ribs = max(1, int(p.get("ribs", 8)))
    cross = max(0, int(p.get("cross_ribs", 0)))
    rw = float(p.get("rib_w", 0.22))
    rh = float(p.get("rib_h", 0.28))
    gmat = p.get("material", "vault_glass")
    rmat = p.get("rib_material", "white")
    kmat = p.get("kerb_material", "stone")
    out = []
    for b in range(cnt):
        off = (b - (cnt - 1) / 2.0) * pitch

        def C(u, v, zz, _o=off):
            return [cx + u, cy + _o + v, zz] if axis == "X" else [cx + _o + v, cy + u, zz]

        def S(a_len, a_wid, hh):
            return [a_len, a_wid, hh] if axis == "X" else [a_wid, a_len, hh]

        out.append(box("RLGlass%d_%d" % (i, b), C(0.0, 0.0, z + kh + 0.06),
                       S(Lb, Wb, 0.12), gmat))
        out.append(box("RLKerbA%d_%d" % (i, b), C(0.0, (Wb + kw) / 2.0, z + kh / 2.0),
                       S(Lb + 2 * kw, kw, kh), kmat))
        out.append(box("RLKerbB%d_%d" % (i, b), C(0.0, -(Wb + kw) / 2.0, z + kh / 2.0),
                       S(Lb + 2 * kw, kw, kh), kmat))
        for k in range(ribs + 1):
            u = (-0.5 + k / float(ribs)) * Lb
            out.append(box("RLRib%d_%d_%02d" % (i, b, k), C(u, 0.0, z + kh + rh / 2.0),
                           S(rw, Wb, rh), rmat))
        if cross > 0:
            for k in range(cross + 1):
                v = (-0.5 + k / float(cross)) * Wb
                out.append(box("RLX%d_%d_%02d" % (i, b, k), C(0.0, v, z + kh + rh / 2.0),
                               S(Lb, rw, rh), rmat))
    return out


def roof_setbacks(p, i):
    """Stepped setback terraces on a flat roof: a perimeter parapet upstand at `base`
    plus `levels` concentric slabs, each inset by `inset` and raised by `rise`, so the
    roof steps DOWN toward the perimeter and the central block is the highest part.
    Corner radii keep the steps following a rounded footprint."""
    at = p.get("at", [0.0, 0.0])
    cx, cy = float(at[0]), float(at[1])
    L, W = [float(v) for v in p.get("size", [40.0, 30.0])]
    base = float(p.get("base", 10.0))
    levels = max(1, int(p.get("levels", 2)))
    inset = float(p.get("inset", 5.0))
    rise = float(p.get("rise", 1.0))
    mat = p.get("material", "stone")
    rr = p.get("radii", p.get("radius", 0.0))
    radii = [float(v) for v in rr] if isinstance(rr, (list, tuple)) else [float(rr)] * 4
    seg = max(2, int(p.get("seg", 8)))
    out = []
    ph = float(p.get("parapet_h", 0.0))
    if ph > 0.0:
        po = float(p.get("parapet_out", 0.25))
        ppts, _o = _rr_plan(L + 2 * po, W + 2 * po, [r + po for r in radii], seg)
        ppts = [(x + cx, y + cy) for (x, y) in ppts]
        out.append(_rr_shell("SetPara%d" % i, ppts, base - 0.35, base + ph,
                             p.get("parapet_material", "white"), None, None, True, False))
    for k in range(1, levels + 1):
        lw = max(2.0, L - 2.0 * inset * k)
        ww = max(2.0, W - 2.0 * inset * k)
        rk = [max(0.0, r - inset * k) for r in radii]
        pts, _o = _rr_plan(lw, ww, rk, seg)
        pts = [(x + cx, y + cy) for (x, y) in pts]
        out.append(_rr_shell("SetStep%d_%02d" % (i, k), pts, base - 0.3, base + rise * k,
                             mat, None, None, True, True))
    return out


def roof_drum(p, i):
    """Circular drum/disc structure on a roof (a white rooftop rotunda) with optional
    small rectangular skylight/vent panels sitting on its top face."""
    at = p.get("at", [0.0, 0.0, 10.0])
    cx, cy, z = float(at[0]), float(at[1]), float(at[2])
    r = float(p.get("radius", 8.0))
    h = float(p.get("height", 2.0))
    segs = max(8, int(p.get("segs", 32)))
    bpy.ops.mesh.primitive_cylinder_add(vertices=segs, radius=r, depth=h,
                                        location=(cx, cy, z + h / 2.0))
    o = bpy.context.active_object
    o.name = "Drum%d" % i
    o.data.materials.append(MAT[p.get("material", "white")])
    out = [o]
    npan = max(0, int(p.get("panels", 0)))
    if npan > 0:
        px, py, pz = [float(v) for v in p.get("panel_size", [4.0, 2.5, 0.8])]
        gap = float(p.get("panel_gap", 3.0))
        pmat = p.get("panel_material", "glass")
        axis = str(p.get("panel_axis", "X")).upper()
        for k in range(npan):
            d = (k - (npan - 1) / 2.0) * (px + gap if axis == "X" else py + gap)
            c = [cx + d, cy, z + h + pz / 2.0] if axis == "X" else [cx, cy + d, z + h + pz / 2.0]
            out.append(box("DrumPanel%d_%02d" % (i, k), c, [px, py, pz], pmat))
    return out


def roof_box_cluster(p, i):
    """Deterministic grid of small boxy rooftop units: rows x cols of plant boxes /
    louvre-vent boxes with a fixed gap. rows=1 gives the row of vent boxes that sits
    just inside a parapet; 2x3 gives a cluster of mechanical plant at one end of a roof.
    h_alt scales every other box so the cluster
    does not read as one slab."""
    at = p.get("at", [0.0, 0.0, 10.0])
    cx, cy, z = float(at[0]), float(at[1]), float(at[2])
    rows = max(1, int(p.get("rows", 2)))
    cols = max(1, int(p.get("cols", 3)))
    sx, sy, sz = [float(v) for v in p.get("size", [5.0, 4.0, 2.5])]
    gap = p.get("gap", [2.5, 2.5])
    gx, gy = float(gap[0]), float(gap[1])
    mat = p.get("material", "slab")
    h_alt = float(p.get("h_alt", 1.0))
    out = []
    for r in range(rows):
        for c in range(cols):
            x = cx + (c - (cols - 1) / 2.0) * (sx + gx)
            y = cy + (r - (rows - 1) / 2.0) * (sy + gy)
            h = sz * (h_alt if (r + c) % 2 else 1.0)
            out.append(box("PlantBox%d_%d_%d" % (i, r, c), [x, y, z + h / 2.0],
                           [sx, sy, h], mat))
    return out


PARTS_LEARNED = {
    "rounded_block": rounded_block,
    "roof_deck": roof_deck,
    "roof_light_well": roof_light_well,
    "rooflight_band": rooflight_band,
    "roof_setbacks": roof_setbacks,
    "roof_drum": roof_drum,
    "roof_box_cluster": roof_box_cluster,
}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: pyramid · gates: smoke+regress+lift ----
def piered_shaft(p, i):
    """Dark tower shaft clad in densely spaced FULL-HEIGHT vertical piers/mullions.
    A slightly inset dark core box (the recessed glazing/spandrel plane) plus one
    unbroken pier per bay on all four faces, so the vertical rhythm reads top to
    bottom with no horizontal banding. Optional wider corner piers."""
    at = p.get("at", [0.0, 0.0])
    sz = p.get("size", [40.0, 40.0])
    L = float(sz[0])
    W = float(sz[1])
    z0 = float(p.get("base", 0.0))
    H = float(p.get("height", 80.0))
    rec = float(p.get("recess", 0.35))
    pw = float(p.get("pier_w", 0.5))
    pd = float(p.get("pier_d", 0.45))
    sp = max(0.4, float(p.get("pier_spacing", 1.6)))
    cw = float(p.get("corner_w", 0.0))
    core_mat = str(p.get("material", "slate_dark"))
    pier_mat = str(p.get("pier_material", "slate_dark"))
    cx = float(at[0])
    cy = float(at[1])
    zc = z0 + H / 2.0
    out = [box("Shaft%d" % i, [cx, cy, zc], [L - 2.0 * rec, W - 2.0 * rec, H], core_mat)]
    # wider corner piers (the shaft's outer quoins)
    if cw > 0.0:
        k = 0
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                out.append(box("ShaftCorner%d_%d" % (i, k),
                               [cx + sx * (L / 2.0 - cw / 2.0), cy + sy * (W / 2.0 - cw / 2.0), zc],
                               [cw, cw, H], pier_mat))
                k += 1
    endw = cw if cw > 0.0 else pw
    # piers on the -y / +y faces, marching along x
    ax = L / 2.0 - endw / 2.0
    nx = max(2, int(round((2.0 * ax) / sp)) + 1)
    for k in range(nx):
        if cw > 0.0 and (k == 0 or k == nx - 1):
            continue
        x = -ax + (2.0 * ax) * k / float(nx - 1)
        for sy in (-1.0, 1.0):
            out.append(box("ShaftPierX%d_%03d%s" % (i, k, "n" if sy < 0 else "p"),
                           [cx + x, cy + sy * (W / 2.0 - pd / 2.0), zc],
                           [pw, pd, H], pier_mat))
    # piers on the -x / +x faces, marching along y
    ay = W / 2.0 - endw / 2.0
    ny = max(2, int(round((2.0 * ay) / sp)) + 1)
    for k in range(ny):
        if cw > 0.0 and (k == 0 or k == ny - 1):
            continue
        y = -ay + (2.0 * ay) * k / float(ny - 1)
        for sx in (-1.0, 1.0):
            out.append(box("ShaftPierY%d_%03d%s" % (i, k, "n" if sx < 0 else "p"),
                           [cx + sx * (L / 2.0 - pd / 2.0), cy + y, zc],
                           [pd, pw, H], pier_mat))
    return out


def crown_band(p, i):
    """Pale horizontal crown band capping a shaft, with an optional projecting cornice
    lip on top. Solid by default; open=1 builds it as a four-sided ring instead."""
    at = p.get("at", [0.0, 0.0])
    sz = p.get("size", [40.0, 40.0])
    L = float(sz[0])
    W = float(sz[1])
    z0 = float(p.get("base", 0.0))
    h = float(p.get("height", 4.0))
    o = float(p.get("out", 0.4))
    t = float(p.get("thick", 1.2))
    mat = str(p.get("material", "white"))
    ch = float(p.get("cornice_h", 0.0))
    co = float(p.get("cornice_out", o + 0.6))
    cmat = str(p.get("cornice_material", mat))
    cx = float(at[0])
    cy = float(at[1])
    zc = z0 + h / 2.0
    bl = L + 2.0 * o
    bw = W + 2.0 * o
    out = []
    if int(p.get("open", 0)):
        for sy in (-1.0, 1.0):
            out.append(box("Crown%d_y%s" % (i, "n" if sy < 0 else "p"),
                           [cx, cy + sy * (bw / 2.0 - t / 2.0), zc], [bl, t, h], mat))
        for sx in (-1.0, 1.0):
            out.append(box("Crown%d_x%s" % (i, "n" if sx < 0 else "p"),
                           [cx + sx * (bl / 2.0 - t / 2.0), cy, zc], [t, bw - 2.0 * t, h], mat))
    else:
        out.append(box("Crown%d" % i, [cx, cy, zc], [bl, bw, h], mat))
    if ch > 0.0:
        out.append(box("CrownCornice%d" % i, [cx, cy, z0 + h + ch / 2.0],
                       [L + 2.0 * co, W + 2.0 * co, ch], cmat))
    return out


def hipped_roof(p, i):
    """Shallow four-sided hipped/pyramidal roof standing on a flat perimeter roof deck
    with a parapet band. ridge=0 gives a true pyramid with a single central apex;
    ridge>0 gives a hipped roof with a ridge of that length along `axis`. Four raised
    hip beams run corner-to-apex so the X reads clearly in plan, and `rungs` adds
    horizontal purlin rings up the slopes (the ribbed roof lattice of the photos)."""
    at = p.get("at", [0.0, 0.0])
    sz = p.get("size", [40.0, 40.0])
    L = float(sz[0])
    W = float(sz[1])
    z0 = float(p.get("base", 0.0))
    dh = float(p.get("deck_h", 0.4))
    m = float(p.get("margin", 3.0))
    rise = float(p.get("rise", 6.0))
    ridge = max(0.0, float(p.get("ridge", 0.0)))
    axis = str(p.get("axis", "X")).upper()
    ph = float(p.get("parapet_h", 1.2))
    pt = float(p.get("parapet_t", 0.5))
    rw = float(p.get("ridge_w", 0.5))
    rup = float(p.get("ridge_up", 0.12))
    rungs = int(p.get("rungs", 0))
    mat = str(p.get("material", "slate"))
    rmat = str(p.get("ridge_material", "white"))
    dmat = str(p.get("deck_material", "stone"))
    pmat = str(p.get("parapet_material", dmat))
    cx = float(at[0])
    cy = float(at[1])
    out = []
    # flat perimeter deck + parapet band around the building edge
    if dh > 0.0:
        out.append(box("RoofDeck%d" % i, [cx, cy, z0 + dh / 2.0], [L, W, dh], dmat))
    zp = z0 + dh
    if ph > 0.0:
        for sy in (-1.0, 1.0):
            out.append(box("RoofParapet%d_y%s" % (i, "n" if sy < 0 else "p"),
                           [cx, cy + sy * (W / 2.0 - pt / 2.0), zp + ph / 2.0], [L, pt, ph], pmat))
        for sx in (-1.0, 1.0):
            out.append(box("RoofParapet%d_x%s" % (i, "n" if sx < 0 else "p"),
                           [cx + sx * (L / 2.0 - pt / 2.0), cy, zp + ph / 2.0],
                           [pt, W - 2.0 * pt, ph], pmat))
    # pyramid / hip body, inset from the edge by the deck margin
    bx = max(0.5, L / 2.0 - m)
    by = max(0.5, W / 2.0 - m)
    tx = (ridge / 2.0) if axis == "X" else 0.0
    ty = (ridge / 2.0) if axis == "Y" else 0.0
    tx = min(tx, bx * 0.9)
    ty = min(ty, by * 0.9)
    b = [(-bx, -by), (bx, -by), (bx, by), (-bx, by)]
    verts = [(cx + q[0], cy + q[1], zp) for q in b]
    if ridge <= 0.0:
        verts.append((cx, cy, zp + rise))
        faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
        tops = [(0.0, 0.0), (0.0, 0.0)]
    elif axis == "X":
        tops = [(-tx, 0.0), (tx, 0.0)]
        verts.append((cx - tx, cy, zp + rise))
        verts.append((cx + tx, cy, zp + rise))
        faces = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    else:
        tops = [(0.0, -ty), (0.0, ty)]
        verts.append((cx, cy - ty, zp + rise))
        verts.append((cx, cy + ty, zp + rise))
        faces = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5)]
    me = bpy.data.meshes.new("HipRoof%dMesh" % i)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new("HipRoof%d" % i, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(MAT[mat])
    out.append(ob)
    # four diagonal hip beams: corner -> nearest apex, forming the X in plan
    for k in range(4):
        x0 = cx + b[k][0]
        y0 = cy + b[k][1]
        ap = tops[0] if k in (0, 3) else tops[1]
        if ridge <= 0.0:
            ap = (0.0, 0.0)
        x1 = cx + ap[0]
        y1 = cy + ap[1]
        dx = x1 - x0
        dy = y1 - y0
        run = math.sqrt(dx * dx + dy * dy)
        ln = math.sqrt(run * run + rise * rise)
        if ln < 1e-4:
            continue
        pitch = math.atan2(rise, run) if run > 1e-6 else math.pi / 2.0
        yaw = math.atan2(dy, dx)
        bm = box("HipRidge%d_%d" % (i, k),
                 [(x0 + x1) / 2.0, (y0 + y1) / 2.0, zp + rise / 2.0 + rup],
                 [ln, rw, rw], rmat)
        bm.rotation_euler = (0.0, -pitch, yaw)
        out.append(bm)
    # horizontal purlin rings up the slopes
    for k in range(rungs):
        t = (k + 1.0) / (rungs + 1.0)
        hx = bx + t * (tx - bx)
        hy = by + t * (ty - by)
        z = zp + t * rise + rup * 0.5
        if hx < 0.3 or hy < 0.3:
            continue
        out.append(box("RoofRung%d_%02dn" % (i, k), [cx, cy - hy, z], [2.0 * hx, rw * 0.5, rw * 0.5], rmat))
        out.append(box("RoofRung%d_%02dp" % (i, k), [cx, cy + hy, z], [2.0 * hx, rw * 0.5, rw * 0.5], rmat))
        out.append(box("RoofRung%d_%02dw" % (i, k), [cx - hx, cy, z], [rw * 0.5, 2.0 * hy, rw * 0.5], rmat))
        out.append(box("RoofRung%d_%02de" % (i, k), [cx + hx, cy, z], [rw * 0.5, 2.0 * hy, rw * 0.5], rmat))
    return out


PARTS_LEARNED = {"piered_shaft": piered_shaft, "crown_band": crown_band, "hipped_roof": hipped_roof}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: parapetring · gates: smoke+regress+lift ----
def roof_parapet(p, i):
    """Continuous parapet band ringing a flat roof deck. Follows a rectangle that may have
    chamfered (angled) corners, so the roof outline can read as an irregular polygon. With
    louvres>0 the band is built as horizontal slats (louvred/slatted screen); a thin cap rail
    is always added on top so the roofline reads as one unbroken horizontal line."""
    ax, ay = [float(v) for v in p.get("at", [0.0, 0.0])]
    L, W = [float(v) for v in p.get("size", [20.0, 20.0])]
    z = float(p.get("z", 10.0)); h = float(p.get("h", 1.2)); t = float(p.get("t", 0.5))
    mat = p.get("material", "white"); slats = int(p.get("louvres", 0))
    ch = float(p.get("chamfer", 0.0)); corners = p.get("corners", ["x-y-"])
    hx, hy = L / 2.0, W / 2.0
    base = [(-hx, -hy, "x-y-"), (hx, -hy, "x+y-"), (hx, hy, "x+y+"), (-hx, hy, "x-y+")]
    pts = []
    for k, (px, py, key) in enumerate(base):
        c = min(ch, 0.45 * min(L, W)) if (ch > 0.0 and key in corners) else 0.0
        if c <= 0.0:
            pts.append((px, py)); continue
        sx = 1.0 if px > 0 else -1.0; sy = 1.0 if py > 0 else -1.0
        a = (px, py - sy * c); b = (px - sx * c, py)
        pts += [a, b] if k % 2 == 0 else [b, a]
    out = []; n = len(pts)
    for e in range(n):
        x0, y0 = pts[e]; x1, y1 = pts[(e + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy)
        if d < 0.05:
            continue
        cx, cy = ax + (x0 + x1) / 2.0, ay + (y0 + y1) / 2.0
        rz = math.atan2(dy, dx)
        bars = []
        if slats > 0:
            bh = h / (2.0 * slats - 1.0) if slats > 1 else h
            for s in range(slats):
                bars.append((z + 2.0 * s * bh + bh / 2.0, bh, t))
        else:
            bars.append((z + h / 2.0, h, t))
        bars.append((z + h + 0.09, 0.18, t * 1.35))
        for s, (bz, bh2, bt) in enumerate(bars):
            o = box("Parapet%d_%02d_%d" % (i, e, s), [cx, cy, bz], [d + t, bt, bh2], mat)
            o.rotation_euler = (0.0, 0.0, rz)
            out.append(o)
    return out


def roof_deck(p, i):
    """One rectangular field laid on a flat roof deck. kind: 'green' (vegetated sedum patch),
    'skylight' (glazed rooflight on a light upstand, subdivided into a grid of panes) or
    'void' (courtyard / lightwell: dark recessed deck framed by a light coping ring)."""
    ax, ay = [float(v) for v in p.get("at", [0.0, 0.0])]
    Lx, Ly = [float(v) for v in p.get("size", [10.0, 10.0])]
    z = float(p.get("z", 10.0)); kind = str(p.get("kind", "green")).lower()
    out = []

    def ring(w):
        return [(ax, ay - Ly / 2.0 - w / 2.0, Lx + 2 * w, w), (ax, ay + Ly / 2.0 + w / 2.0, Lx + 2 * w, w),
                (ax - Lx / 2.0 - w / 2.0, ay, w, Ly), (ax + Lx / 2.0 + w / 2.0, ay, w, Ly)]

    if kind == "green":
        kerb = float(p.get("kerb", 0.4))
        out.append(box("RoofGreen%d_%d" % (i, int(abs(ax) + abs(ay))), [ax, ay, z + 0.15],
                       [Lx, Ly, 0.30], p.get("material", "plant")))
        for e, (cx, cy, sx, sy) in enumerate(ring(kerb)):
            out.append(box("GreenKerb%d_%d_%d" % (i, int(abs(ax) + abs(ay)), e), [cx, cy, z + 0.13],
                           [sx, sy, 0.26], p.get("kerb_material", "white")))
    elif kind == "skylight":
        nx, ny = [int(v) for v in p.get("grid", [4, 4])]
        bw = float(p.get("bar", 0.35)); up = float(p.get("rise", 0.55))
        tag = int(abs(ax) + abs(ay))
        for e, (cx, cy, sx, sy) in enumerate(ring(0.5)):
            out.append(box("SkyUpstand%d_%d_%d" % (i, tag, e), [cx, cy, z + up / 2.0],
                           [sx, sy, up], p.get("kerb_material", "white")))
        out.append(box("Skylight%d_%d" % (i, tag), [ax, ay, z + up + 0.12], [Lx, Ly, 0.24],
                       p.get("material", "glass")))
        for gx in range(nx + 1):
            out.append(box("SkyBarX%d_%d_%02d" % (i, tag, gx),
                           [ax - Lx / 2.0 + Lx * gx / float(nx), ay, z + up + 0.26],
                           [bw, Ly, 0.22], p.get("bar_material", "white")))
        for gy in range(ny + 1):
            out.append(box("SkyBarY%d_%d_%02d" % (i, tag, gy),
                           [ax, ay - Ly / 2.0 + Ly * gy / float(ny), z + up + 0.26],
                           [Lx, bw, 0.22], p.get("bar_material", "white")))
    else:
        cop = float(p.get("coping", 1.0)); cw = float(p.get("coping_w", 0.55))
        tag = int(abs(ax) + abs(ay))
        out.append(box("RoofVoid%d_%d" % (i, tag), [ax, ay, z + 0.05], [Lx, Ly, 0.22],
                       p.get("material", "interior")))
        for e, (cx, cy, sx, sy) in enumerate(ring(cw)):
            out.append(box("VoidCope%d_%d_%d" % (i, tag, e), [cx, cy, z + cop / 2.0],
                           [sx, sy, cop], p.get("coping_material", "white")))
    return out


PARTS_LEARNED = {"roof_parapet": roof_parapet, "roof_deck": roof_deck}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: pilotis · gates: smoke+regress+lift ----
def undercroft(p, i):
    """Open colonnaded ground storey / covered passage: a flat soffit slab carried on a
    regular row (or two rows) of free-standing piers, with optional deep downstand beams
    running ACROSS the passage and a blank stone fascia band above the soffit edge. Gives
    the cantilever/overhang read: the columns sit inboard of the soffit edge, so the mass
    above visibly oversails the passage. at = plan centre of the passage."""
    at = p.get("at", [0.0, 0.0])
    L = float(p.get("length", 40.0))
    D = float(p.get("depth", 8.0))
    h = float(p.get("height", 6.0))
    st = float(p.get("soffit_t", 0.8))
    ax = str(p.get("axis", "X")).upper()
    smat = p.get("soffit_material", "base")
    cmat = p.get("col_material", "stone")

    def pos(u, v, z):
        return [at[0] + u, at[1] + v, z] if ax == "X" else [at[0] + v, at[1] + u, z]

    def siz(a, b, c):
        return [a, b, c] if ax == "X" else [b, a, c]

    out = [box("UcSoffit%d" % i, pos(0.0, 0.0, h + st * 0.5), siz(L, D, st), smat)]
    nb = int(p.get("beams", 0))
    bd = float(p.get("beam_d", 1.0))
    bw = float(p.get("beam_w", 0.8))
    for k in range(nb):
        u = -L * 0.5 + L * (k + 0.5) / nb
        out.append(box("UcBeam%d_%02d" % (i, k), pos(u, 0.0, h - bd * 0.5),
                       siz(bw, D, bd), smat))
    n = max(int(p.get("count", 8)), 1)
    cw = float(p.get("col_w", 1.2))
    cd = float(p.get("col_d", cw))
    ins = float(p.get("inset", 0.8))
    rows = int(p.get("rows", 1))
    vs = [float(p.get("row_v", 0.0))] if rows < 2 else [-(D * 0.5 - ins), D * 0.5 - ins]
    rnd = str(p.get("col_shape", "square")).lower() == "round"
    for r, v in enumerate(vs):
        for k in range(n):
            u = -L * 0.5 + L * (k + 0.5) / n
            c = pos(u, v, h * 0.5)
            if rnd:
                bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=cw * 0.5,
                                                    depth=h, location=tuple(c))
                o = bpy.context.active_object
                o.name = "UcCol%d_%d%02d" % (i, r, k)
                o.data.materials.append(MAT[cmat])
                out.append(o)
            else:
                out.append(box("UcCol%d_%d%02d" % (i, r, k), c, siz(cw, cd, h), cmat))
    fh = float(p.get("fascia_h", 0.0))
    if fh > 0.0:
        ft = float(p.get("fascia_t", 0.5))
        fm = p.get("fascia_material", "stone")
        sides = [-1.0, 1.0] if bool(p.get("fascia_both", False)) else [float(p.get("fascia_side", -1.0))]
        for s in sides:
            out.append(box("UcFascia%d_%d" % (i, int(s) + 1),
                           pos(0.0, s * (D * 0.5 - ft * 0.5), h + st + fh * 0.5),
                           siz(L, ft, fh), fm))
    return out


def plaza_apron(p, i):
    """Open paved plaza deck fronting a colonnaded base: a thin raised paving slab with an
    optional flight of low steps stepping down on its outer edge. at = plan centre."""
    at = p.get("at", [0.0, 0.0])
    L = float(p.get("length", 40.0))
    D = float(p.get("depth", 12.0))
    lev = float(p.get("level", 0.3))
    ax = str(p.get("axis", "X")).upper()
    mat = p.get("material", "slab")
    nst = int(p.get("steps", 0))
    tr = float(p.get("tread", 0.5))
    side = float(p.get("side", -1.0))

    def pos(u, v, z):
        return [at[0] + u, at[1] + v, z] if ax == "X" else [at[0] + v, at[1] + u, z]

    def siz(a, b, c):
        return [a, b, c] if ax == "X" else [b, a, c]

    out = [box("Plaza%d" % i, pos(0.0, 0.0, lev * 0.5), siz(L, D, lev), mat)]
    for k in range(nst):
        z = lev * (k + 1) / float(nst + 1)
        v = side * (D * 0.5 + tr * (nst - k) - tr * 0.5)
        out.append(box("PlazaStep%d_%02d" % (i, k), pos(0.0, v, z * 0.5),
                       siz(L, tr, z), mat))
    return out


PARTS_LEARNED = {"undercroft": undercroft, "plaza_apron": plaza_apron}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: spandrel · gates: smoke+regress+lift ----
def ribbon_curtain_shell(p, i):
    """Curtain-wall ENVELOPE: tinted glass faces on all four sides plus ONE continuous
    horizontal spandrel band per floor that wraps uninterrupted around every face and
    around the rounded corners, with an optional pale crown band at the very top.
    corner_r > 0 turns the four vertical corners into quarter-round glass, so the
    ribbons curve round the corner with no vertical crease."""
    at = p.get("at", [0.0, 0.0])
    L = float(p["size"][0]); W = float(p["size"][1])
    cx = float(at[0]); cy = float(at[1]); z0 = float(p.get("base_z", 0.0))
    n = max(1, int(p.get("floors", 20))); fh = float(p.get("floor_h", 3.6))
    r = min(max(0.0, float(p.get("corner_r", 0.0))), 0.45 * min(L, W))
    t = float(p.get("depth", 0.5)); bh = float(p.get("band_h", 0.9))
    pr = float(p.get("proud", 0.18))
    gm = p.get("glass", "glass_green"); bm = p.get("band", "slab")
    ch = float(p.get("crown_h", 0.0)); cm = p.get("crown", "white")
    H = n * fh
    fl = max(L - 2.0 * r, 0.6); fw = max(W - 2.0 * r, 0.6)
    out = []

    def rim(z, h, extra, mat, tag):
        out.append(box("%s%d_yn" % (tag, i), [cx, cy - W / 2.0 + t / 2.0, z], [fl, t + extra, h], mat))
        out.append(box("%s%d_yp" % (tag, i), [cx, cy + W / 2.0 - t / 2.0, z], [fl, t + extra, h], mat))
        out.append(box("%s%d_xn" % (tag, i), [cx - L / 2.0 + t / 2.0, cy, z], [t + extra, fw, h], mat))
        out.append(box("%s%d_xp" % (tag, i), [cx + L / 2.0 - t / 2.0, cy, z], [t + extra, fw, h], mat))

    def posts(z, h, rad, mat, tag):
        if r < 0.05:
            return
        for sx in (-1, 1):
            for sy in (-1, 1):
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=20, radius=rad, depth=h,
                    location=(cx + sx * (L / 2.0 - r), cy + sy * (W / 2.0 - r), z))
                o = bpy.context.active_object
                o.name = "%s%d_%d%d" % (tag, i, sx > 0, sy > 0)
                o.data.materials.append(MAT[mat])
                out.append(o)

    rim(z0 + H / 2.0, H, 0.0, gm, "RCglass")          # the glazed shaft
    posts(z0 + H / 2.0, H, r, gm, "RCglassC")          # rounded glazed corners
    top = z0 + H - ch
    for k in range(n + 1):                             # one ribbon band per floor line
        zb = z0 + k * fh
        if zb > top - 0.3 or zb > z0 + H:
            continue
        rim(zb, bh, 2.0 * pr, bm, "RCband%02d" % k)
        posts(zb, bh, r + pr, bm, "RCbandC%02d" % k)
    if ch > 0.01:                                      # pale crown band at the very top
        rim(top + ch / 2.0, ch, 2.0 * pr + 0.08, cm, "RCcrown")
        posts(top + ch / 2.0, ch, r + pr + 0.04, cm, "RCcrownC")
    return out


def glazed_podium_wing(p, i):
    """Low glazed podium / annex attached along ONE side of the host mass and projecting
    beyond its footprint: banded glass box, a few storeys, pale parapet cap."""
    L = float(p["size"][0]); W = float(p["size"][1])
    side = str(p.get("side", "-x")).lower()
    a0, a1 = [float(v) for v in p.get("along", [0.15, 0.8])]
    proj = float(p.get("project", 10.0)); grip = float(p.get("grip", 1.5))
    n = max(1, int(p.get("floors", 2))); fh = float(p.get("floor_h", 4.2))
    z0 = float(p.get("base_z", 0.0)); bh = float(p.get("band_h", 0.7))
    gm = p.get("glass", "glass_green"); bm = p.get("band", "slab"); cm = p.get("cap", "white")
    H = n * fh
    if side in ("-x", "+x"):
        s = -1.0 if side == "-x" else 1.0
        dy = max(2.0, (a1 - a0) * W); ay = -W / 2.0 + (a0 + a1) * 0.5 * W
        dx = proj + grip; ax = s * (L / 2.0 + proj * 0.5 - grip * 0.5)
    else:
        s = -1.0 if side == "-y" else 1.0
        dx = max(2.0, (a1 - a0) * L); ax = -L / 2.0 + (a0 + a1) * 0.5 * L
        dy = proj + grip; ay = s * (W / 2.0 + proj * 0.5 - grip * 0.5)
    out = [box("Podium%d" % i, [ax, ay, z0 + H / 2.0], [dx, dy, H], gm)]
    for k in range(n + 1):
        z = z0 + k * fh
        if z > z0 + H - 0.4:
            continue
        out.append(box("PodBand%d_%02d" % (i, k), [ax, ay, z + bh / 2.0],
                       [dx + 0.30, dy + 0.30, bh], bm))
    out.append(box("PodCap%d" % i, [ax, ay, z0 + H + 0.25], [dx + 0.5, dy + 0.5, 0.5], cm))
    return out


PARTS_LEARNED = {"ribbon_curtain_shell": ribbon_curtain_shell,
                 "glazed_podium_wing": glazed_podium_wing}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canary_wharf · cluster: plantbanks · gates: smoke+regress+lift ----
def roof_patch(p, i):
    """Flat rectangular patch laid on a roof deck: a glazed rooflight/atrium panel
    (glass in an upstand kerb, crossed by white glazing bars so it reads as glazing,
    not a dark hole), a planted green/sedum area, or a plain deck strip of a
    contrasting material. at=[cx,cy] is the plan centre, z the deck level; length
    runs along X unless axis='Y', and rot turns the patch for diagonal blocks."""
    at = p.get("at", [0.0, 0.0]); cx, cy = float(at[0]), float(at[1])
    z = float(p.get("z", 20.0))
    L = float(p.get("length", 20.0)); W = float(p.get("width", 8.0))
    if str(p.get("axis", "X")).upper() == "Y":
        L, W = W, L
    kind = str(p.get("kind", "glazed")).lower()
    a = math.radians(float(p.get("rot", 0.0))); ca, sa = math.cos(a), math.sin(a)
    kerb = float(p.get("kerb", 0.45 if kind == "glazed" else 0.30))
    mat = str(p.get("material", {"glazed": "vault_glass", "green": "plant"}.get(kind, "roof")))
    trim = str(p.get("trim", "white" if kind == "glazed" else "slab"))
    tag = str(p.get("tag", "%d_%d" % (int(round(cx)), int(round(cy)))))
    def P(dx, dy):
        return [cx + dx * ca - dy * sa, cy + dx * sa + dy * ca]
    out = []
    for k, (dx, dy, sx, sy) in enumerate([(0.0, W / 2.0, L + 0.6, 0.3),
                                          (0.0, -W / 2.0, L + 0.6, 0.3),
                                          (L / 2.0, 0.0, 0.3, W + 0.6),
                                          (-L / 2.0, 0.0, 0.3, W + 0.6)]):
        c = P(dx, dy)
        o = box("XRPKerb%d_%s_%d" % (i, tag, k), [c[0], c[1], z + kerb / 2.0], [sx, sy, kerb], trim)
        o.rotation_euler = (0, 0, a); out.append(o)
    fz = z + (kerb * 0.85 if kind == "glazed" else 0.14)
    c = P(0.0, 0.0)
    f = box("XRPFill%d_%s" % (i, tag), [c[0], c[1], fz], [L, W, 0.22], mat)
    f.rotation_euler = (0, 0, a); out.append(f)
    if kind == "glazed":
        n = int(p.get("bars", max(3, int(L / 3.0))))
        for k in range(n):
            c = P(-L / 2.0 + L * (k + 0.5) / n, 0.0)
            o = box("XRPBar%d_%s_%02d" % (i, tag, k), [c[0], c[1], fz + 0.17], [0.22, W, 0.24], trim)
            o.rotation_euler = (0, 0, a); out.append(o)
        c = P(0.0, 0.0)
        o = box("XRPRidge%d_%s" % (i, tag), [c[0], c[1], fz + 0.26], [L, 0.32, 0.32], trim)
        o.rotation_euler = (0, 0, a); out.append(o)
    return out

def louvre_screen(p, i):
    """A run of tilted louvre slats between two end posts under a top rail. Serves as
    a rooftop plant/mechanical screen, a perimeter parapet screen, or -- small, with
    back=True -- a vent grille set flush into a facade. at=[cx,cy,cz] is the centre of
    the screen face; the run goes along X unless axis='Y', rot turns it in plan."""
    at = p.get("at", [0.0, 0.0, 0.0])
    cx, cy, cz = float(at[0]), float(at[1]), float(at[2])
    L = float(p.get("length", 20.0)); H = float(p.get("height", 2.4))
    d = float(p.get("depth", 0.5)); ax = str(p.get("axis", "X")).upper()
    n = int(p.get("count", max(3, int(H / 0.38))))
    t = float(p.get("slat", 0.14))
    tilt = math.radians(float(p.get("tilt", 25.0)))
    a = math.radians(float(p.get("rot", 0.0))); ca, sa = math.cos(a), math.sin(a)
    mat = str(p.get("material", "white")); back = bool(p.get("back", False))
    off = float(p.get("face", -1.0)) * d * 0.5 if back else 0.0
    tag = str(p.get("tag", "%d_%d_%d" % (int(round(cx)), int(round(cy)), int(round(cz)))))
    def P(dx, dy):
        return [cx + dx * ca - dy * sa, cy + dx * sa + dy * ca]
    def put(nm, dx, dy, zz, sx, sy, sz, m, rx=0.0, ry=0.0):
        c = P(dx, dy)
        o = box(nm, [c[0], c[1], zz], [sx, sy, sz], m)
        o.rotation_euler = (rx, ry, a)
        return o
    out = []
    if back:
        bm = str(p.get("back_material", "slate_dark"))
        if ax == "X":
            out.append(put("XLvBack%d_%s" % (i, tag), 0.0, 0.0, cz, L, 0.18, H, bm))
        else:
            out.append(put("XLvBack%d_%s" % (i, tag), 0.0, 0.0, cz, 0.18, L, H, bm))
    for k in range(n):
        zz = cz - H / 2.0 + H * (k + 0.5) / n
        if ax == "X":
            out.append(put("XLvSlat%d_%s_%02d" % (i, tag, k), 0.0, off, zz, L, d, t, mat, rx=tilt))
        else:
            out.append(put("XLvSlat%d_%s_%02d" % (i, tag, k), off, 0.0, zz, d, L, t, mat, ry=-tilt))
    if bool(p.get("posts", True)):
        pw = float(p.get("post", 0.28))
        for s in (-1.0, 1.0):
            if ax == "X":
                out.append(put("XLvPost%d_%s_%d" % (i, tag, int(s)), s * L / 2.0, off, cz,
                               pw, d + 0.16, H, mat))
            else:
                out.append(put("XLvPost%d_%s_%d" % (i, tag, int(s)), off, s * L / 2.0, cz,
                               d + 0.16, pw, H, mat))
        if ax == "X":
            out.append(put("XLvRail%d_%s" % (i, tag), 0.0, off, cz + H / 2.0 + 0.1,
                           L + 0.4, d + 0.16, 0.2, mat))
        else:
            out.append(put("XLvRail%d_%s" % (i, tag), off, 0.0, cz + H / 2.0 + 0.1,
                           d + 0.16, L + 0.4, 0.2, mat))
    return out

PARTS_LEARNED = {"roof_patch": roof_patch, "louvre_screen": louvre_screen}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: canal_house · cluster: gables · gates: smoke+regress+lift ----
def pitched_roof(p, i):
    """Pitched roof prism over a rectangular plan: plain gable (hip=0), hipped roof
    (0<hip<1) or a pyramidal lantern/hub (hip=1). Ridge runs along `axis`; `rot`
    turns the whole roof about z (diagonal long axes). Optional front-slope dormers
    and one chimney stack."""
    at = p.get("at", [0.0, 0.0])
    L = float(p.get("length", 20.0)); W = float(p.get("width", 10.0))
    ez = float(p.get("eaves_z", 9.0)); ov = float(p.get("overhang", 0.35))
    hip = max(0.0, min(1.0, float(p.get("hip", 0.0))))
    rise = float(p["rise"]) if "rise" in p else math.tan(math.radians(float(p.get("pitch", 45.0)))) * 0.5 * W
    rot = math.radians(float(p.get("rot", 0.0))); ax = str(p.get("axis", "X")).upper()
    A = 0.5 * L + ov; B = 0.5 * W + ov; R = A * (1.0 - hip)
    if R < 0.05:
        vs = [(-A, -B, 0), (A, -B, 0), (A, B, 0), (-A, B, 0), (0, 0, rise)]
        fs = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)]
    else:
        vs = [(-A, -B, 0), (A, -B, 0), (A, B, 0), (-A, B, 0), (-R, 0, rise), (R, 0, rise)]
        fs = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (3, 2, 1, 0)]
    if ax == "Y":
        vs = [(-v[1], v[0], v[2]) for v in vs]
    me = bpy.data.meshes.new("PRoofMesh%d" % i)
    me.from_pydata(vs, [], fs); me.update()
    o = bpy.data.objects.new("PitchRoof%d_%s" % (i, ax), me)
    bpy.context.scene.collection.objects.link(o)
    o.location = (at[0], at[1], ez); o.rotation_euler = (0, 0, rot)
    o.data.materials.append(MAT[p.get("material", "slate_dark")])
    out = [o]
    def place(dx, dy):
        return [at[0] + dx * math.cos(rot) - dy * math.sin(rot),
                at[1] + dx * math.sin(rot) + dy * math.cos(rot)]
    nd = int(p.get("dormers", 0))
    dw = float(p.get("dormer_w", 1.7)); dh = float(p.get("dormer_h", 1.8))
    for k in range(nd):
        a1 = ((k + 0.5) / nd - 0.5) * L * 0.84; off = -0.30 * W
        zc = ez + rise * 0.38
        dx, dy = (a1, off) if ax == "X" else (off, a1)
        b = box("Dormer%d_%d" % (i, k), place(dx, dy) + [zc],
                [dw, 1.9, dh] if ax == "X" else [1.9, dw, dh], p.get("dormer_material", "stone"))
        b.rotation_euler = (0, 0, rot); out.append(b)
        dx2, dy2 = (a1, off - 1.0) if ax == "X" else (off - 1.0, a1)
        g = box("DormerGl%d_%d" % (i, k), place(dx2, dy2) + [zc],
                [dw * 0.66, 0.14, dh * 0.66] if ax == "X" else [0.14, dw * 0.66, dh * 0.66], "glass")
        g.rotation_euler = (0, 0, rot); out.append(g)
    ch = p.get("chimney")
    if ch:
        a1 = float(ch[0]) * L * 0.45; hh = float(ch[1]); cw = float(ch[2])
        dx, dy = (a1, 0.0) if ax == "X" else (0.0, a1)
        Hc = rise + hh
        b = box("Chimney%d" % i, place(dx, dy) + [ez + 0.5 * Hc], [cw, cw * 0.75, Hc],
                p.get("chimney_material", "brick"))
        b.rotation_euler = (0, 0, rot); out.append(b)
    return out


def stepped_gable(p, i):
    """Ornamental Dutch stepped/tapering gable wall (default) or a plain triangular
    gable face (shape='tri', lattice-barred), standing on top of a facade. `at` is
    the centre of the wall plane; axis='Y' -> wall faces the street. Optional finial."""
    at = p.get("at", [0.0, 0.0])
    w = float(p.get("width", 9.0)); bz = float(p.get("base_z", 12.0))
    tz = float(p.get("top_z", 19.0)); th = float(p.get("thickness", 0.6))
    n = max(1, int(p.get("steps", 5))); neck = float(p.get("neck", 0.16))
    mat = p.get("material", "brick"); cop = p.get("coping", "stone")
    ax = str(p.get("axis", "Y")).upper(); H = max(0.6, tz - bz); out = []
    def blk(nm, cz, bw, bh, t2, m):
        c = [at[0], at[1], cz]
        s = [bw, t2, bh] if ax == "Y" else [t2, bw, bh]
        return box(nm, c, s, m)
    if str(p.get("shape", "stepped")) == "tri":
        hw, ht = 0.5 * w, 0.5 * th
        vs = [(-hw, -ht, 0), (hw, -ht, 0), (0, -ht, H), (-hw, ht, 0), (hw, ht, 0), (0, ht, H)]
        if ax == "X":
            vs = [(-v[1], v[0], v[2]) for v in vs]
        me = bpy.data.meshes.new("TriGabMesh%d" % i)
        me.from_pydata(vs, [], [(0, 1, 2), (5, 4, 3), (0, 2, 5, 3), (1, 4, 5, 2), (0, 3, 4, 1)])
        me.update()
        o = bpy.data.objects.new("TriGable%d" % i, me)
        bpy.context.scene.collection.objects.link(o)
        o.location = (at[0], at[1], bz)
        o.data.materials.append(MAT[mat]); out.append(o)
        nb = int(p.get("bars", 3))
        for k in range(nb):
            f = (k + 1.0) / (nb + 1.0)
            out.append(blk("GabBar%d_%d" % (i, k), bz + H * f, w * (1.0 - f) + 0.25, 0.22,
                           th + 0.16, p.get("bar_material", "mullion")))
    else:
        for k in range(n):
            f = k / float(max(1, n - 1))
            bw = w * (1.0 - (1.0 - neck) * f); z0 = bz + H * k / n
            out.append(blk("Gable%d_%d" % (i, k), z0 + 0.5 * H / n, bw, H / n, th, mat))
            out.append(blk("GabCop%d_%d" % (i, k), z0 + H / n, bw + 0.45, 0.26, th + 0.18, cop))
    fh = float(p.get("finial", 0.0))
    if fh > 0.01:
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=float(p.get("finial_r", 0.22)),
                                        radius2=0.0, depth=fh,
                                        location=(at[0], at[1], tz + 0.5 * fh))
        o2 = bpy.context.active_object; o2.name = "Finial%d" % i
        o2.data.materials.append(MAT[p.get("finial_material", "iron")]); out.append(o2)
    return out


PARTS_LEARNED = {"pitched_roof": pitched_roof, "stepped_gable": stepped_gable}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: paris · cluster: balconyrail · gates: smoke+regress+lift ----
def balcony_band(p, i):
    """Continuous Haussmann balcony: thin stone slab on consoles carrying a dark
    wrought-iron railing (bottom rail, ornamental cast mid band, top rail, balusters)
    running the FULL width of one facade at one or more storeys. 'face' is the signed
    coordinate of the wall plane, 'side' which facade, 'levels' the floor heights."""
    side = str(p.get("side", "-y")).lower()
    L = float(p.get("length", 20.0))
    face = float(p.get("face", -10.0))
    along = float(p.get("along", 0.0))
    dep = float(p.get("depth", 0.85))
    rh = float(p.get("rail_h", 1.0))
    st = float(p.get("slab_t", 0.18))
    sp = max(float(p.get("spacing", 0.30)), 0.12)
    mat = str(p.get("material", "iron"))
    smat = str(p.get("slab_material", "stone"))
    levels = [float(z) for z in p.get("levels", [p.get("z", 6.0)])]
    s = 1.0 if side in ("+y", "+x") else -1.0
    ax = 0 if side in ("-y", "+y") else 1          # 0: band runs along x, 1: along y
    n = min(max(4, int(L / sp)), int(p.get("max_posts", 180)))
    nc = min(max(2, int(L / max(float(p.get("console_step", 2.4)), 0.8))), 48)
    out = []
    for m, z in enumerate(levels):
        def put(tag, u, v, w, su, sv, sw, mm):
            c = [u, v, w] if ax == 0 else [v, u, w]
            sz = [su, sv, sw] if ax == 0 else [sv, su, sw]
            return box("BalBand%d_%d_%s" % (i, m, tag), c, sz, mm)
        ve = face + s * (dep - 0.09)
        out.append(put("slab", along, face + s * (dep * 0.5 - 0.06), z + st * 0.5,
                       L, dep, st, smat))
        out.append(put("bot", along, ve, z + st + 0.07, L, 0.07, 0.07, mat))
        out.append(put("top", along, ve, z + st + rh, L, 0.10, 0.10, mat))
        out.append(put("orn", along, ve, z + st + rh * 0.55, L, 0.06, 0.30, mat))
        for k in range(n):
            u = along - L * 0.5 + L * (k + 0.5) / n
            out.append(put("p%03d" % k, u, ve, z + st + rh * 0.5, 0.05, 0.05, rh, mat))
        for k in range(nc):
            u = along - L * 0.5 + L * (k + 0.5) / nc
            out.append(put("c%02d" % k, u, face + s * (dep * 0.4), z - 0.19,
                           0.26, dep * 0.8, 0.38, smat))
    return out


def window_guards(p, i):
    """Juliet balustrades / window guards: a row of short dark iron railings on stone
    sills, one per window bay, repeated over the storeys listed in 'levels'. Gives the
    vertical bay rhythm of a Paris facade without projecting a full balcony."""
    side = str(p.get("side", "-y")).lower()
    face = float(p.get("face", -10.0))
    span = float(p.get("span", 20.0))
    along = float(p.get("along", 0.0))
    nb = max(1, min(int(p.get("bays", 6)), 40))
    w = float(p.get("width", 1.4))
    rh = float(p.get("rail_h", 0.95))
    pr = float(p.get("proj", 0.18))
    npst = max(2, min(int(p.get("posts", 4)), 12))
    mat = str(p.get("material", "iron"))
    smat = str(p.get("sill_material", "stone"))
    sill = bool(p.get("sill", True))
    levels = [float(z) for z in p.get("levels", [p.get("z", 6.0)])]
    s = 1.0 if side in ("+y", "+x") else -1.0
    ax = 0 if side in ("-y", "+y") else 1
    out = []
    for m, z in enumerate(levels):
        for k in range(nb):
            u0 = along - span * 0.5 + span * (k + 0.5) / nb
            def put(tag, u, v, ww, su, sv, sw, mm):
                c = [u, v, ww] if ax == 0 else [v, u, ww]
                sz = [su, sv, sw] if ax == 0 else [sv, su, sw]
                return box("WGuard%d_%d_%02d_%s" % (i, m, k, tag), c, sz, mm)
            ve = face + s * pr
            if sill:
                out.append(put("sill", u0, face + s * (pr * 0.5), z + 0.03,
                               w + 0.34, pr, 0.07, smat))
            out.append(put("bot", u0, ve, z + 0.12, w, 0.06, 0.06, mat))
            out.append(put("top", u0, ve, z + rh, w, 0.08, 0.08, mat))
            out.append(put("orn", u0, ve, z + rh * 0.55, w, 0.05, 0.22, mat))
            for q in range(npst):
                u = u0 - w * 0.5 + w * (q + 0.5) / npst
                out.append(put("p%d" % q, u, ve, z + rh * 0.5, 0.045, 0.045, rh, mat))
            out.append(put("e0", u0 - w * 0.5, ve, z + rh * 0.5, 0.06, 0.06, rh, mat))
            out.append(put("e1", u0 + w * 0.5, ve, z + rh * 0.5, 0.06, 0.06, rh, mat))
    return out


PARTS_LEARNED = {"balcony_band": balcony_band, "window_guards": window_guards}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: paris · cluster: courtyard · gates: smoke+regress+lift ----
def mansard_cap(p, i):
    """Steep dark mansard cap: an eaves cornice, a four-sided sloped band (outer eaves
    loop rising inward to a smaller top loop), a flatter top deck that can be a ring
    around a courtyard hole, plus dormers set into the slope and chimney stacks."""
    L = float(p.get("length", 20.0)); W = float(p.get("width", 12.0))
    z0 = float(p.get("base_z", 15.0)); h = float(p.get("height", 3.5))
    inset = float(p.get("inset", 1.8)); over = float(p.get("overhang", 0.35))
    mat = p.get("material", "slate_dark"); tmat = p.get("top_material", "slate")
    out = []; zc = z0
    if p.get("cornice", True):
        out.append(box("ManCorn%d" % i, [0, 0, z0 + 0.19],
                       [L + 2 * over + 0.4, W + 2 * over + 0.4, 0.38],
                       p.get("cornice_material", "stone")))
        zc = z0 + 0.38
    ox, oy = L / 2.0 + over, W / 2.0 + over
    ix, iy = max(ox - inset, 1.0), max(oy - inset, 1.0)
    zt = zc + h
    def mk(name, vs, fs, m):
        me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.update()
        o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
        o.data.materials.append(MAT[m]); return o
    lo = [(-ox, -oy), (ox, -oy), (ox, oy), (-ox, oy)]
    li = [(-ix, -iy), (ix, -iy), (ix, iy), (-ix, iy)]
    ring = [(k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k) for k in range(4)]
    out.append(mk("Mansard%d" % i, [(x, y, zc) for x, y in lo] + [(x, y, zt) for x, y in li], ring, mat))
    cy = p.get("courtyard")
    if cy:
        hx, hy, hl, hw = float(cy[0]), float(cy[1]), float(cy[2]) / 2.0, float(cy[3]) / 2.0
        lh = [(hx - hl, hy - hw), (hx + hl, hy - hw), (hx + hl, hy + hw), (hx - hl, hy + hw)]
        out.append(mk("MansardDeck%d" % i, [(x, y, zt) for x, y in li] + [(x, y, zt) for x, y in lh], ring, tmat))
    else:
        out.append(box("MansardDeck%d" % i, [0, 0, zt + 0.06], [2 * ix, 2 * iy, 0.12], tmat))
    nd = int(p.get("dormers", 0))
    dw = float(p.get("dormer_width", 1.1)); dh = float(p.get("dormer_height", 1.3))
    frac = float(p.get("dormer_frac", 0.45)); dmat = p.get("dormer_material", "stone")
    for s in (p.get("dormer_sides", ["front"]) if nd > 0 else []):
        s = str(s).lower(); horiz = s in ("front", "back")
        sgn = -1.0 if s in ("front", "left") else 1.0
        edge = (oy - inset * frac) if horiz else (ox - inset * frac)
        zz = zc + h * frac + dh / 2.0
        span_len = (2 * ix) if horiz else (2 * iy)
        for k in range(nd):
            u = -span_len / 2.0 + span_len * (k + 0.5) / nd
            c = [u, sgn * edge, zz] if horiz else [sgn * edge, u, zz]
            out.append(box("Dorm%d_%s%02d" % (i, s, k), c,
                           [dw, 0.9, dh] if horiz else [0.9, dw, dh], dmat))
            gc = list(c); gc[1 if horiz else 0] += sgn * 0.48
            out.append(box("DormGl%d_%s%02d" % (i, s, k), gc,
                           [dw * 0.66, 0.10, dh * 0.66] if horiz else [0.10, dw * 0.66, dh * 0.66], "glass"))
    for k, ch in enumerate(p.get("chimneys", []) or []):
        chh = float(ch[2]) if len(ch) > 2 else 1.8
        sx = float(ch[3]) if len(ch) > 3 else 1.0
        sy = float(ch[4]) if len(ch) > 4 else 0.8
        out.append(box("Chim%d_%02d" % (i, k), [float(ch[0]), float(ch[1]), zt + chh / 2.0],
                       [sx, sy, chh], p.get("chimney_material", "stone")))
    return out


def facade_band(p, i):
    """Continuous horizontal band across one or more facades: a projecting stone ledge
    (cornice / string course / balcony floor) with an optional dark iron railing of
    top+bottom rails and evenly spaced balusters running the full span."""
    L = float(p.get("length", 20.0)); W = float(p.get("width", 12.0))
    z = float(p.get("z", 6.0)); d = float(p.get("depth", 0.45))
    t = float(p.get("thickness", 0.28)); raw_span = p.get("span", 1.0)
    span = (float(raw_span[1]) - float(raw_span[0])
            if isinstance(raw_span, (list, tuple)) and len(raw_span) == 2
            else float(raw_span))
    rail = bool(p.get("railing", True)); rh = float(p.get("rail_height", 0.95))
    rmat = p.get("rail_material", "iron"); lmat = p.get("material", "stone")
    step = float(p.get("post_spacing", 1.1))
    # tolerate the two conventions the agents actually wrote (09-08 audit of
    # every spec on disk): `span` as a [a, b] fraction range or as METRES
    # (= the facade length), and `sides` as -y/+y/-x/+x. A metres span was
    # being multiplied by the facade length -- a 25.6 m band became a 650 m
    # railing running across the whole street (Goethe Institute, city_rah).
    _AXIS = {"-y": "front", "+y": "back", "-x": "left", "+x": "right"}
    out = []
    for s in p.get("sides", ["front"]):
        s = _AXIS.get(str(s).lower(), str(s).lower()); horiz = s in ("front", "back")
        sgn = -1.0 if s in ("front", "left") else 1.0
        side_len = L if horiz else W
        frac = span / side_len if span > 1.5 else span      # metres -> fraction
        frac = max(0.05, min(1.0, frac))
        span_len = side_len * frac + 2 * d
        off = (W / 2.0 if horiz else L / 2.0) + d / 2.0
        c = [0.0, sgn * off, z + t / 2.0] if horiz else [sgn * off, 0.0, z + t / 2.0]
        out.append(box("Band%d_%s%d" % (i, s, int(z * 10)), c,
                       [span_len, d, t] if horiz else [d, span_len, t], lmat))
        if not rail:
            continue
        for k, fz in ((0, 0.07), (1, rh - 0.06)):
            rc = [c[0], c[1], z + t + fz]
            out.append(box("BandRail%d_%s%d_%d" % (i, s, int(z * 10), k), rc,
                           [span_len, 0.10, 0.11] if horiz else [0.10, span_len, 0.11], rmat))
        n = max(3, int(span_len / max(step, 0.4)))
        for k in range(n):
            u = -span_len / 2.0 + span_len * (k + 0.5) / n
            pc = [u, sgn * off, z + t + rh / 2.0] if horiz else [sgn * off, u, z + t + rh / 2.0]
            out.append(box("BandPost%d_%s%d_%02d" % (i, s, int(z * 10), k), pc,
                           [0.08, 0.08, rh], rmat))
    return out


PARTS_LEARNED = {"mansard_cap": mansard_cap, "facade_band": facade_band}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: london · cluster: rotunda · gates: smoke+regress+lift ----
def oval_drum(p, i):
    """Closed elliptical BRICK DRUM built from `segments` tangential wall panels, so the
    wall visibly curves (convex) instead of reading as a flat plane. Each panel carries the
    full storey stack: pale stone base with rectangular doorways and a projecting horizontal
    canopy over them, `tiers` of tall arched (round-topped) windows on the brick, then a
    contrasting decorative frieze band and a cornice lip just under the roof line."""
    rx = float(p.get("rx", 20.0)); ry = float(p.get("ry", rx))
    n = max(12, int(p.get("segments", 40)))
    z0 = float(p.get("z0", 0.0))
    bh = float(p.get("base_h", 5.0))
    tiers = max(1, int(p.get("tiers", 2))); th = float(p.get("tier_h", 7.0))
    fh = float(p.get("frieze_h", 2.5)); t = float(p.get("wall_t", 1.2))
    ww = float(p.get("window_w", 3.0)); wr = float(p.get("window_ratio", 2.0))
    wev = max(1, int(p.get("window_every", 2))); dev = max(1, int(p.get("door_every", 5)))
    cd = float(p.get("canopy_depth", 3.0))
    mb = p.get("base_material", "stone"); mw = p.get("wall_material", "brick")
    mf = p.get("frieze_material", "stucco"); mg = p.get("glass_material", "glass")
    mc = p.get("canopy_material", "slate_dark")
    out = []
    for k in range(n):
        a1 = 2 * math.pi * k / n; a2 = 2 * math.pi * (k + 1) / n
        x1, y1 = rx * math.cos(a1), ry * math.sin(a1)
        x2, y2 = rx * math.cos(a2), ry * math.sin(a2)
        cx, cy = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
        seg = math.hypot(x2 - x1, y2 - y1) * 1.08
        rz = math.atan2(y2 - y1, x2 - x1)
        ox, oy = math.cos(rz - math.pi / 2), math.sin(rz - math.pi / 2)   # outward normal

        def panel(nm, z, h, mat, d=0.0, sx=None, sy=None):
            o = box("%s%d_%02d" % (nm, i, k), [cx + ox * d, cy + oy * d, z0 + z + h / 2],
                    [sx or seg, sy or t, h], mat)
            o.rotation_euler = (0, 0, rz); out.append(o); return o

        panel("DrumBase", 0.0, bh, mb, 0.25, sy=t * 1.4)
        for q in range(tiers):
            panel("DrumWall", bh + q * th, th, mw)
        panel("DrumFrieze", bh + tiers * th, fh, mf, 0.20)
        panel("DrumCornice", bh + tiers * th + fh, 0.9, mb, 0.55, sy=t + 1.1)
        panel("DrumCanopy", bh - 0.45, 0.28, mc, cd * 0.5 + 0.25, sy=cd)
        if k % dev == 0:
            panel("DrumDoor", 0.15, bh * 0.62, "interior", 0.62, sx=seg * 0.45, sy=t * 0.5)
        if k % wev == 0:
            wh = ww * wr; rh = wh - ww * 0.5
            for q in range(tiers):
                zb = z0 + bh + q * th + (th - wh) * 0.5
                g = box("DrumWin%d_%02d_%d" % (i, k, q),
                        [cx + ox * 0.15, cy + oy * 0.15, zb + rh / 2], [ww, t * 0.6, rh], mg)
                g.rotation_euler = (0, 0, rz); out.append(g)
                bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=ww * 0.5, depth=t * 0.6,
                    location=(cx + ox * 0.15, cy + oy * 0.15, zb + rh))
                c = bpy.context.active_object
                c.rotation_euler = (0, math.pi / 2, rz - math.pi / 2)
                c.name = "DrumWinArch%d_%02d_%d" % (i, k, q)
                c.data.materials.append(MAT[mg]); out.append(c)
    return out


def radial_glazed_dome(p, i):
    """Shallow GLAZED DOME on an oval plan, subdivided into narrow radial wedge panels by
    `ribs` glazing bars that follow the dome profile and converge on a small circular
    hub/lantern (oculus) at the exact centre."""
    at = p.get("at", [0, 0]); z = float(p.get("z", 10.0))
    rx = float(p.get("rx", 15.0)); ry = float(p.get("ry", rx))
    rise = float(p.get("rise", 5.0))
    nb = max(8, int(p.get("ribs", 32))); steps = max(2, int(p.get("rib_steps", 4)))
    hr = float(p.get("hub_r", 2.0)); hh = float(p.get("hub_h", 1.6))
    mg = p.get("material", "vault_glass"); mr = p.get("rib_material", "white")
    mh = p.get("hub_material", "copper")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=nb, ring_count=max(6, steps * 3),
                                         radius=1.0, location=(at[0], at[1], z))
    d = bpy.context.active_object
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=(at[0], at[1], z), plane_no=(0, 0, 1), clear_inner=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    d.scale = (rx, ry, rise)
    bpy.ops.object.transform_apply(scale=True)
    d.name = "GDome%d" % i
    d.data.materials.append(MAT[mg])
    out = [d]
    for k in range(nb):                     # radial glazing bars over the glass
        a = 2 * math.pi * k / nb
        R = math.hypot(rx * math.cos(a), ry * math.sin(a))
        for s in range(steps):
            u1, u2 = float(s) / steps, float(s + 1) / steps
            r1, r2 = R * u1, R * u2
            z1 = rise * math.sqrt(max(0.0, 1 - u1 * u1))
            z2 = rise * math.sqrt(max(0.0, 1 - u2 * u2))
            dr, dz = r2 - r1, z2 - z1
            rm, zm = 0.5 * (r1 + r2), 0.5 * (z1 + z2)
            o = box("GDomeRib%d_%02d_%d" % (i, k, s),
                    [at[0] + rm * math.cos(a), at[1] + rm * math.sin(a), z + zm + 0.12],
                    [math.hypot(dr, dz) * 1.06, 0.30, 0.26], mr)
            o.rotation_euler = (0, -math.atan2(dz, dr), a)
            out.append(o)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=hr, depth=hh,
                                        location=(at[0], at[1], z + rise + hh * 0.2))
    h = bpy.context.active_object
    h.name = "GDomeHub%d" % i
    h.data.materials.append(MAT[mh])
    out.append(h)
    return out


PARTS_LEARNED = {"oval_drum": oval_drum, "radial_glazed_dome": radial_glazed_dome}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: amsterdam · cluster: arch_entrance · gates: smoke+regress+lift ----
def stoop(p, i):
    """Raised Amsterdam entrance: stone landing + external flight of steps down to the
    pavement, thin iron handrails on both cheeks, and an optional sunken souterrain
    door with small windows beside it. `at` is the point on the facade plane; `facing`
    is the outward normal of that facade."""
    ax, ay = float(p["at"][0]), float(p["at"][1])
    n = {"-y": (0.0, -1.0), "+y": (0.0, 1.0), "-x": (-1.0, 0.0), "+x": (1.0, 0.0)}[str(p.get("facing", "-y"))]
    t = (1.0, 0.0) if abs(n[0]) < 0.5 else (0.0, 1.0)
    rise = float(p.get("rise", 1.2)); ns = max(1, int(p.get("steps", 4)))
    w = float(p.get("width", 1.8)); tr = float(p.get("tread", 0.32))
    land = float(p.get("landing", 0.75)); mat = p.get("material", "stone")
    rh = float(p.get("rail_h", 0.95)); rmat = p.get("rail_material", "iron")
    def P(d, s, z): return [ax + n[0] * d + t[0] * s, ay + n[1] * d + t[1] * s, z]
    def S(dd, ss, hh): return [abs(n[0]) * dd + abs(t[0]) * ss, abs(n[1]) * dd + abs(t[1]) * ss, hh]
    out = [box("Stoop%d_land" % i, P(land * 0.5, 0.0, rise * 0.5), S(land, w, rise), mat)]
    for k in range(ns):                                   # outermost tread is the lowest
        h = rise * (ns - k) / (ns + 1.0)
        out.append(box("Stoop%d_st%d" % (i, k), P(land + (k + 0.5) * tr, 0.0, h * 0.5), S(tr, w, h), mat))
    if bool(p.get("rail", True)):
        d0, z0 = land + ns * tr - 0.12, rise / (ns + 1.0) + rh * 0.8
        d1, z1 = land * 0.3, rise + rh
        Lr = math.hypot(d1 - d0, z1 - z0)
        for sg in (-1.0, 1.0):
            s = sg * (w * 0.5 - 0.06)
            r = box("Stoop%d_rail%d" % (i, int(sg)), P((d0 + d1) * 0.5, s, (z0 + z1) * 0.5),
                    ([0.06, Lr, 0.06] if abs(n[0]) < 0.5 else [Lr, 0.06, 0.06]), rmat)
            if abs(n[0]) < 0.5:
                r.rotation_euler = (math.atan2(z1 - z0, n[1] * (d1 - d0)), 0, 0)
            else:
                r.rotation_euler = (0, math.atan2(-(z1 - z0), n[0] * (d1 - d0)), 0)
            out.append(r)
            out.append(box("Stoop%d_nwT%d" % (i, int(sg)), P(d1, s, rise + rh * 0.5), S(0.08, 0.08, rh), rmat))
            out.append(box("Stoop%d_nwB%d" % (i, int(sg)), P(d0, s, z0 * 0.5), S(0.08, 0.08, z0), rmat))
    if bool(p.get("basement", False)):                    # souterrain, sunk below pavement
        bo = float(p.get("basement_at", -(w * 0.5 + 0.95)))
        bw = float(p.get("basement_w", 1.0)); bz = float(p.get("basement_drop", 0.45))
        sd = -1.0 if bo < 0 else 1.0
        out.append(box("Stoop%d_bdoor" % i, P(0.07, bo, 1.0 - bz), S(0.14, bw, 2.0),
                       p.get("basement_material", "slate_dark")))
        for k, g in enumerate((0.5, 1.3)):
            out.append(box("Stoop%d_bwin%d" % (i, k), P(0.05, bo + sd * (bw * 0.5 + g), 0.78 - bz),
                           S(0.10, 0.62, 0.75), p.get("basement_glass", "glass")))
    return out


def door_surround(p, i):
    """Door leaf set in a contrasting stone surround: jambs plus either a flat lintel or a
    semicircular arched head of voussoirs over a glazed fanlight. `double` adds the centre
    mullion of a double / warehouse door. Sits proud of the facade plane at `at`."""
    ax, ay = float(p["at"][0]), float(p["at"][1])
    n = {"-y": (0.0, -1.0), "+y": (0.0, 1.0), "-x": (-1.0, 0.0), "+x": (1.0, 0.0)}[str(p.get("facing", "-y"))]
    t = (1.0, 0.0) if abs(n[0]) < 0.5 else (0.0, 1.0)
    dw = float(p.get("width", 1.2)); dh = float(p.get("height", 2.4))
    z0 = float(p.get("sill", 0.0)); sw = float(p.get("jamb", 0.28)); pr = float(p.get("proj", 0.15))
    smat = p.get("surround", "white"); dmat = p.get("door", "slate_dark")
    arch = bool(p.get("arch", False)); R = dw * 0.5; Rm = R + sw * 0.5
    def P(d, s, z): return [ax + n[0] * d + t[0] * s, ay + n[1] * d + t[1] * s, z]
    def S(dd, ss, hh): return [abs(n[0]) * dd + abs(t[0]) * ss, abs(n[1]) * dd + abs(t[1]) * ss, hh]
    out = [box("Door%d_leaf" % i, P(0.06, 0.0, z0 + dh * 0.5), S(0.12, dw, dh), dmat)]
    jh = dh + (0.0 if arch else sw)
    for sg in (-1.0, 1.0):
        out.append(box("Door%d_jamb%d" % (i, int(sg)), P(pr * 0.5, sg * (dw + sw) * 0.5, z0 + jh * 0.5),
                       S(pr, sw, jh), smat))
    if bool(p.get("double", False)):
        out.append(box("Door%d_mull" % i, P(0.10, 0.0, z0 + dh * 0.5), S(0.10, 0.09, dh), smat))
    if not arch:
        out.append(box("Door%d_lint" % i, P(pr * 0.5, 0.0, z0 + dh + sw * 0.5), S(pr, dw + 2 * sw, sw), smat))
    else:
        nv = int(p.get("voussoirs", 11))
        seg = math.pi * Rm / nv * 1.18
        for k in range(nv):
            th = math.pi * (k + 0.5) / nv
            c = P(pr * 0.5, Rm * math.cos(th), z0 + dh + Rm * math.sin(th))
            sz = [seg, pr, sw] if abs(n[0]) < 0.5 else [pr, seg, sw]
            v = box("Door%d_vs%02d" % (i, k), c, sz, smat)
            if abs(n[0]) < 0.5:
                v.rotation_euler = (0, -(th + math.pi * 0.5), 0)
            else:
                v.rotation_euler = (th + math.pi * 0.5, 0, 0)
            out.append(v)
        me = bpy.data.meshes.new("Fanlight%d_m" % i)          # semicircular fanlight glass
        vs = [P(0.05, 0.0, z0 + dh)]
        nf = 14
        for k in range(nf + 1):
            th = math.pi * k / nf
            vs.append(P(0.05, R * math.cos(th), z0 + dh + R * math.sin(th)))
        me.from_pydata(vs, [], [(0, k, k + 1) for k in range(1, nf + 1)])
        me.update()
        o = bpy.data.objects.new("Fanlight%d" % i, me)
        bpy.context.collection.objects.link(o)
        o.data.materials.append(MAT[p.get("fanlight", "glass")])
        out.append(o)
    return out


PARTS_LEARNED = {"stoop": stoop, "door_surround": door_surround}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: amsterdam · cluster: arch_rows · gates: smoke+regress+lift ----
def arched_opening_grid(p, i):
    """Grid of recessed facade openings with round/segmental ARCHED heads: white reveal
    frame, glazed (or dark door) leaf, stone sill, brick voussoir band and a glazed
    tympanum/fanlight. rise=0 gives a flat-topped opening; tall h + dark glass_material
    gives warehouse / carriage doors. Openings run along the chosen face."""
    face = str(p.get("face", "-y"))
    sgn = -1.0 if face[0] == "-" else 1.0
    hz = face[-1].lower()                       # '-y' face -> openings run along x
    fa = float(p.get("face_at", -6.0))
    u0, u1 = [float(v) for v in p.get("span", [-6.0, 6.0])]
    cols, rows = max(1, int(p.get("cols", 3))), max(1, int(p.get("rows", 1)))
    w, h = float(p.get("width", 1.3)), float(p.get("height", 1.9))
    z0, dz = float(p.get("z0", 4.0)), float(p.get("dz", 3.2))
    rise = float(p.get("rise", 0.0))            # arch height above the springing line
    d = float(p.get("depth", 0.14))
    fw = float(p.get("frame", 0.11))
    tb = float(p.get("arch_band", 0.26))
    ns = max(2, int(p.get("arch_steps", 5)))
    gm = str(p.get("glass_material", "glass"))
    am = str(p.get("arch_material", "brick"))
    fm = str(p.get("frame_material", "white"))
    sm = str(p.get("sill_material", "stone"))
    tm = str(p.get("arch_fill_material", gm))
    out = []

    def pos(u, z, o):
        return [u, fa + sgn * o, z] if hz == "y" else [fa + sgn * o, u, z]

    def siz(a, t, c):
        return [a, t, c] if hz == "y" else [t, a, c]

    for c in range(cols):
        u = u0 + (u1 - u0) * (c + 0.5) / cols
        for r in range(rows):
            zs = z0 + dz * r                     # sill
            zc = zs + h                          # springing line
            n = "%02d%02d" % (c, r)
            out.append(box("XSarcFrm%d_%s" % (i, n), pos(u, zs + h * 0.5, d * 0.35),
                           siz(w + 2 * fw, d, h + 2 * fw), fm))
            out.append(box("XSarcGls%d_%s" % (i, n), pos(u, zs + h * 0.5, d * 0.85),
                           siz(w, d * 0.5, h), gm))
            out.append(box("XSarcSil%d_%s" % (i, n), pos(u, zs - 0.07, d + 0.14),
                           siz(w + 0.46, 0.32, 0.13), sm))
            if rise <= 0.02:
                continue
            a = w * 0.5
            for k in range(ns):                  # elliptical head, course by course
                f = (k + 0.5) / ns
                hc = a * math.sqrt(max(0.0, 1.0 - f * f))
                zk, hk = zc + rise * f, rise / ns * 1.06
                out.append(box("XSarcTym%d_%s_%d" % (i, n, k), pos(u, zk, d * 0.85),
                               siz(2.0 * hc, d * 0.5, hk), tm))
                for s in (-1, 1):
                    out.append(box("XSarcVou%d_%s_%d%s" % (i, n, k, "L" if s < 0 else "R"),
                                   pos(u + s * (hc + tb * 0.5), zk, d * 0.3),
                                   siz(tb, d, hk), am))
            out.append(box("XSarcCrn%d_%s" % (i, n), pos(u, zc + rise + tb * 0.45, d * 0.3),
                           siz(a * 0.8 + tb, d, tb * 0.95), am))
    return out


def hinged_shutters(p, i):
    """Pairs of large hinged shutter leaves flanking each opening of a grid (same
    span/cols/rows/z0/dz convention as arched_opening_grid). angle=0 lays the leaves
    flat on the wall, 10-20 deg swings them open as in the pakhuis photos."""
    face = str(p.get("face", "-y"))
    sgn = -1.0 if face[0] == "-" else 1.0
    hz = face[-1].lower()
    fa = float(p.get("face_at", -6.0))
    u0, u1 = [float(v) for v in p.get("span", [-6.0, 6.0])]
    cols, rows = max(1, int(p.get("cols", 3))), max(1, int(p.get("rows", 1)))
    gap = float(p.get("gap", 0.95))              # opening centre -> hinge line
    lw, lh = float(p.get("leaf_w", 0.9)), float(p.get("leaf_h", 2.4))
    t = float(p.get("thick", 0.09))
    z0, dz = float(p.get("z0", 4.0)), float(p.get("dz", 3.2))
    zoff = float(p.get("z_off", 0.0))
    ang = math.radians(float(p.get("angle", 12.0)))
    mat = str(p.get("material", "white"))
    out = []
    for c in range(cols):
        u = u0 + (u1 - u0) * (c + 0.5) / cols
        for r in range(rows):
            zk = z0 + dz * r + zoff + lh * 0.5
            for s in (-1, 1):
                cu = u + s * (gap + lw * 0.5 * math.cos(ang))
                od = 0.07 + lw * 0.5 * math.sin(ang)
                ctr = [cu, fa + sgn * od, zk] if hz == "y" else [fa + sgn * od, cu, zk]
                o = box("XSshut%d_%02d%02d%s" % (i, c, r, "L" if s < 0 else "R"), ctr,
                        [lw, t, lh] if hz == "y" else [t, lw, lh], mat)
                o.rotation_euler = (0, 0, (s if hz == "y" else -s) * sgn * ang)
                out.append(o)
                out.append(box("XSshutH%d_%02d%02d%s" % (i, c, r, "L" if s < 0 else "R"),
                               [u + s * (gap - 0.05), fa + sgn * 0.05, zk] if hz == "y"
                               else [fa + sgn * 0.05, u + s * (gap - 0.05), zk],
                               siz_ := ([0.14, 0.12, lh * 0.96] if hz == "y" else [0.12, 0.14, lh * 0.96]),
                               str(p.get("hinge_material", "iron"))))
    return out


PARTS_LEARNED = {"arched_opening_grid": arched_opening_grid, "hinged_shutters": hinged_shutters}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: london · cluster: terminus_roofscape · gates: smoke+regress+lift ----
def viaduct_deck(p, i):
    """Elevated rail/station deck: a slab carried on regularly spaced columns with an
    open undercroft, a heavy fascia beam band running the full length just under the
    platform, an edge balustrade, and rail tracks running through both short ends."""
    at = p.get("at", [0, 0]); cx, cy = float(at[0]), float(at[1])
    L = float(p.get("length", 60.0)); W = float(p.get("width", 12.0))
    z = float(p.get("deck_z", 7.0)); st = float(p.get("slab_t", 0.9))
    bh = float(p.get("beam_h", 1.2)); bt = float(p.get("beam_t", 0.7))
    smat = p.get("material", "slab"); out = []
    out.append(box("VdSlab%d" % i, [cx, cy, z - st / 2.0], [L, W, st], smat))
    for s in (-1, 1):                                   # heavy continuous deck/beam band
        out.append(box("VdBeam%d_%d" % (i, s > 0), [cx, cy + s * (W / 2.0 - bt / 2.0),
                   z - st - bh / 2.0], [L, bt, bh], p.get("beam_material", smat)))
    n = max(int(p.get("columns", 9)), 2); cs = float(p.get("col_size", 1.1))
    ch = max(z - st - bh, 0.5); ins = float(p.get("col_inset", 1.6))
    for k in range(n):
        X = cx + L * (-0.47 + 0.94 * k / (n - 1.0))
        for r, s in enumerate((-1, 1)):
            out.append(box("VdCol%d_%02d_%d" % (i, k, r), [X, cy + s * (W / 2.0 - ins),
                       ch / 2.0], [cs, cs, ch], p.get("col_material", "base")))
    rh = float(p.get("rail_h", 1.1))
    if rh > 0:
        rm = p.get("rail_material", "iron"); npo = max(int(p.get("rail_posts", 24)), 2)
        for s in (-1, 1):
            ry = cy + s * (W / 2.0 - 0.15)
            out.append(box("VdRail%d_%d" % (i, s > 0), [cx, ry, z + rh], [L, 0.12, 0.12], rm))
            out.append(box("VdRailM%d_%d" % (i, s > 0), [cx, ry, z + rh * 0.55], [L, 0.10, 0.10], rm))
            for k in range(npo):
                out.append(box("VdRailP%d_%d_%02d" % (i, s > 0, k),
                           [cx - L / 2.0 + L * (k + 0.5) / npo, ry, z + rh / 2.0], [0.10, 0.10, rh], rm))
    nt = int(p.get("tracks", 2)); off = float(p.get("track_offset", W * 0.26))
    ov = float(p.get("track_overrun", 10.0)); g = float(p.get("gauge", 1.44))
    for t in range(max(nt, 0)):
        ty = cy + (off * (2.0 * t / (nt - 1.0) - 1.0) if nt > 1 else 0.0)
        out.append(box("VdBed%d_%d" % (i, t), [cx, ty, z + 0.13], [L + 2 * ov, g + 1.2, 0.26],
                   p.get("bed_material", "slate_dark")))
        for s in (-1, 1):
            out.append(box("VdTrk%d_%d_%d" % (i, t, s > 0), [cx, ty + s * g / 2.0, z + 0.36],
                       [L + 2 * ov, 0.12, 0.20], p.get("track_material", "iron")))
    return out


def twin_canopy(p, i):
    """N (default 2) parallel GLAZED ridged canopies running lengthwise, separated by a
    continuous open slot down the middle. Each slopes from a centre ridge down to both
    long eaves and is divided into regular transverse rib bays (ribbed striped glazing)."""
    at = p.get("at", [0, 0]); cx, cy = float(at[0]), float(at[1])
    L = float(p.get("length", 60.0)); cw = float(p.get("canopy_width", 4.6))
    gap = float(p.get("gap", 1.8)); z0 = float(p.get("eave_z", 9.0))
    rise = float(p.get("rise", 1.4)); bays = max(int(p.get("bays", 16)), 1)
    n = max(int(p.get("count", 2)), 1); rt = float(p.get("rib_t", 0.22))
    gm = p.get("material", "vault_glass"); rm = p.get("rib_material", "white")
    ang = math.atan2(rise, cw / 2.0); slen = math.hypot(cw / 2.0, rise); out = []
    for c in range(n):
        oy = cy + (gap + cw) * (c - (n - 1) / 2.0)
        verts = []
        for X in (cx - L / 2.0, cx + L / 2.0):
            verts += [(X, oy - cw / 2.0, z0), (X, oy, z0 + rise), (X, oy + cw / 2.0, z0)]
        me = bpy.data.meshes.new("CanopyM%d_%d" % (i, c))
        me.from_pydata(verts, [], [(0, 1, 4, 3), (1, 2, 5, 4)]); me.update()
        o = bpy.data.objects.new("Canopy%d_%d" % (i, c), me)
        bpy.context.collection.objects.link(o)
        o.data.materials.append(MAT[gm]); out.append(o)
        out.append(box("CanRidge%d_%d" % (i, c), [cx, oy, z0 + rise + 0.10], [L, 0.26, 0.26], rm))
        for s in (-1, 1):
            out.append(box("CanEave%d_%d_%d" % (i, c, s > 0), [cx, oy + s * cw / 2.0, z0 - 0.06],
                       [L, 0.22, 0.22], rm))
            out.append(box("CanMull%d_%d_%d" % (i, c, s > 0), [cx, oy + s * cw / 4.0,
                       z0 + rise / 2.0 + 0.06], [L, 0.10, 0.10], rm))
        for k in range(bays + 1):
            X = cx - L / 2.0 + L * k / float(bays)
            for s in (-1, 1):
                b = box("CanRib%d_%d_%02d_%d" % (i, c, k, s > 0), [X, oy + s * cw / 4.0,
                        z0 + rise / 2.0 + 0.06], [rt, slen, rt], rm)
                b.rotation_euler = (-s * ang, 0, 0); out.append(b)
        ph = float(p.get("post_h", 0.0))
        if ph > 0:
            npst = max(int(p.get("posts", 9)), 2); pm = p.get("post_material", "iron")
            for k in range(npst):
                X = cx + L * (-0.47 + 0.94 * k / (npst - 1.0))
                for s in (-1, 1):
                    out.append(box("CanPost%d_%d_%02d_%d" % (i, c, k, s > 0),
                               [X, oy + s * cw / 2.0, z0 - ph / 2.0], [0.24, 0.24, ph], pm))
    return out


PARTS_LEARNED = {"viaduct_deck": viaduct_deck, "twin_canopy": twin_canopy}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: delhi · cluster: shutterfront · gates: smoke+regress+lift ----
def shop_shutter_row(p, i):
    """Ground-floor bazaar shopfront band on one facade: darker plinth/skirting,
    N roller-shutter bays (ribbed slats) split by narrow piers, and a continuous
    horizontal signage fascia running the whole run above the shutters."""
    side = str(p.get("side", "-y")).lower()
    face = float(p["face"])                      # signed coord of the wall plane
    L = float(p["length"])
    off = float(p.get("offset", 0.0))            # centre of the run along the facade
    n = -1.0 if side.startswith("-") else 1.0
    ax = 0 if side.endswith("x") else 1          # 1 = wall normal is Y
    bays = max(1, int(p.get("bays", 3)))
    hsh = float(p.get("shutter_h", 3.0))
    plh = float(p.get("plinth_h", 0.30))
    fah = float(p.get("fascia_h", 0.80))
    d = float(p.get("depth", 0.14))
    pier = float(p.get("pier", 0.35))
    m_sh = p.get("shutter", "iron")
    m_fa = p.get("fascia", "sign")
    m_pl = p.get("plinth", "slate_dark")
    m_pi = p.get("pier_mat", "stucco")

    def put(nm, cu, lu, cz, hz, dd, mat):
        c = [0.0, 0.0, cz]
        s = [0.0, 0.0, hz]
        if ax == 1:
            c[0], c[1] = cu, face + n * dd * 0.5
            s[0], s[1] = lu, dd
        else:
            c[1], c[0] = cu, face + n * dd * 0.5
            s[1], s[0] = lu, dd
        return box(nm, c, s, mat)

    out = [put("XSplinth%d" % i, off, L, plh * 0.5, plh, d + 0.06, m_pl)]
    pitch = L / bays
    op = max(0.6, pitch - pier)
    hop = max(0.4, hsh - plh)
    nslat = max(2, min(8, int(hop / 0.45)))
    for k in range(bays):
        cu = off - L * 0.5 + (k + 0.5) * pitch
        out.append(put("XSshut%d_%d" % (i, k), cu, op, plh + hop * 0.5, hop, d, m_sh))
        for j in range(nslat):
            zc = plh + hop * (j + 0.5) / nslat
            out.append(put("XSslat%d_%d_%d" % (i, k, j), cu, op - 0.06, zc, 0.07,
                           d + 0.05, m_sh))
    for k in range(bays + 1):
        cu = off - L * 0.5 + k * pitch
        out.append(put("XSpier%d_%d" % (i, k), cu, pier, hsh * 0.5, hsh, d + 0.02, m_pi))
    out.append(put("XSfascia%d" % i, off, L, hsh + fah * 0.5, fah, d + 0.10, m_fa))
    out.append(put("XSfasctrim%d" % i, off, L + 0.06, hsh + fah - 0.05, 0.10,
                   d + 0.16, p.get("trim", "white")))
    return out


def shop_awning(p, i):
    """Thin corrugated canopy/eave projecting from one facade: tilted ribbed slab
    on small brackets. Serves as a shopfront awning or an overhanging roof eave."""
    side = str(p.get("side", "-y")).lower()
    face = float(p["face"])
    L = float(p["length"])
    off = float(p.get("offset", 0.0))
    z = float(p["z"])
    proj = float(p.get("proj", 1.0))
    th = float(p.get("thick", 0.10))
    tilt = math.radians(float(p.get("tilt", 8.0)))
    mat = p.get("material", "iron")
    ribs = max(0, int(p.get("ribs", 10)))
    brk = max(0, int(p.get("brackets", 6)))
    n = -1.0 if side.startswith("-") else 1.0
    ax = 0 if side.endswith("x") else 1
    cn = face + n * proj * 0.5                   # centre on the normal axis

    def slab(nm, cu, lu, cz, hz, ln, lp, mat2):
        c = [0.0, 0.0, cz]
        s = [0.0, 0.0, hz]
        if ax == 1:
            c[0], c[1] = cu, ln
            s[0], s[1] = lu, lp
        else:
            c[1], c[0] = cu, ln
            s[1], s[0] = lu, lp
        o = box(nm, c, s, mat2)
        if ax == 1:
            o.rotation_euler = (-n * tilt, 0.0, 0.0)
        else:
            o.rotation_euler = (0.0, n * tilt, 0.0)
        return o

    out = [slab("XSawn%d" % i, off, L, z, th, cn, proj, mat)]
    for k in range(ribs):
        cu = off - L * 0.5 + L * (k + 0.5) / ribs
        out.append(slab("XSawnrib%d_%d" % (i, k), cu, min(0.12, L / (2.0 * ribs)),
                        z + th * 0.5 + 0.035, 0.07, cn, proj, mat))
    for k in range(brk):
        cu = off - L * 0.5 + L * (k + 0.5) / brk
        c = [0.0, 0.0, z - 0.30]
        s = [0.0, 0.0, 0.60]
        if ax == 1:
            c[0], c[1] = cu, face + n * proj * 0.30
            s[0], s[1] = 0.09, 0.09
        else:
            c[1], c[0] = cu, face + n * proj * 0.30
            s[1], s[0] = 0.09, 0.09
        out.append(box("XSawnbrk%d_%d" % (i, k), c, s, p.get("bracket_mat", "iron")))
    return out


PARTS_LEARNED = {"shop_shutter_row": shop_shutter_row, "shop_awning": shop_awning}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: delhi · cluster: chhajja · gates: smoke+regress+lift ----
def facade_bands(p, i):
    """Horizontal trim family for flat-roofed street blocks: projecting string-course
    bands at chosen floor lines, a flat parapet ring on the roof deck (straight top
    edge, no eaves) and flat projecting window hoods/sunshades in the band colour."""
    L, W = [float(v) for v in p.get("size", [10.0, 10.0])]
    fl = max(1, int(p.get("floors", 3)))
    fh = float(p.get("floor_h", 3.0))
    z0 = float(p.get("base_z", 0.0))
    bh = float(p.get("band_h", 0.32))
    q = float(p.get("proj", 0.12))
    mat = p.get("material", "brick")
    sides = list(p.get("sides", ["-y"]))
    out = []

    def strip(tag, z, h, d):
        for s in sides:
            g = -1.0 if s[0] == "-" else 1.0
            if s.endswith("y"):
                c, sz = [0.0, g * (W / 2.0 + d / 2.0 - 0.04), z], [L, d, h]
            else:
                c, sz = [g * (L / 2.0 + d / 2.0 - 0.04), 0.0, z], [d, W, h]
            out.append(box("XSbnd%d_%s%s" % (i, tag, s[0] + s[1]), c, sz, mat))

    for k in p.get("levels", list(range(1, fl + 1))):
        strip("L%d" % int(k), z0 + float(k) * fh - bh / 2.0, bh, q)
    ztop = z0 + fl * fh
    ph = float(p.get("parapet_h", 0.8))
    pt = float(p.get("parapet_t", 0.24))
    if p.get("parapet", True):
        pm = p.get("parapet_material", "stone")
        zc = ztop + ph / 2.0
        for nm, c, sz in (("f", [0.0, -W / 2.0 + pt / 2.0, zc], [L, pt, ph]),
                          ("b", [0.0, W / 2.0 - pt / 2.0, zc], [L, pt, ph]),
                          ("l", [-L / 2.0 + pt / 2.0, 0.0, zc], [pt, W - 2.0 * pt, ph]),
                          ("r", [L / 2.0 - pt / 2.0, 0.0, zc], [pt, W - 2.0 * pt, ph])):
            out.append(box("XSpar%d_%s" % (i, nm), c, sz, pm))
        strip("cap", ztop + ph - bh / 2.0, bh, q + 0.06)
    n = int(p.get("hood_count", 0))
    if n > 0:
        hw = float(p.get("hood_w", 1.5))
        ht = float(p.get("hood_t", 0.14))
        hp = float(p.get("hood_proj", 0.38))
        hz = float(p.get("hood_z", fh * 0.76))
        g = -1.0 if str(p.get("hood_side", "-y"))[0] == "-" else 1.0
        for k in p.get("hood_levels", list(range(1, fl))):
            for j in range(n):
                x = -L / 2.0 + L * (j + 0.5) / n
                out.append(box("XShood%d_%d_%d" % (i, int(k), j),
                               [x, g * (W / 2.0 + hp / 2.0 - 0.05), z0 + float(k) * fh + hz],
                               [hw, hp, ht], mat))
    return out


def shopfront_band(p, i):
    """Ground-floor commercial band: wide dark recessed shop openings/shutters split by
    slim piers (each bay reads as a doorway), under a continuous signboard lintel that
    runs the full frontage -- the ground floor stops looking like punched windows."""
    L, W = [float(v) for v in p.get("size", [10.0, 10.0])]
    side = str(p.get("side", "-y"))
    n = max(1, int(p.get("bays", 3)))
    z0 = float(p.get("base_z", 0.0))
    h = float(p.get("height", 2.6))
    pw = float(p.get("pier_w", 0.26))
    pd = float(p.get("pier_proj", 0.30))
    sh = float(p.get("sign_h", 0.45))
    om = p.get("opening_material", "slate_dark")
    pm = p.get("pier_material", "stucco")
    sm = p.get("sign_material", "sign")
    g = -1.0 if side[0] == "-" else 1.0
    ay = side.endswith("y")
    span = L if ay else W
    off = (W if ay else L) / 2.0
    out = []

    def put(nm, u, d, su, sd, sz, cz, m):
        c = [u, g * (off + d), cz] if ay else [g * (off + d), u, cz]
        s = [su, sd, sz] if ay else [sd, su, sz]
        out.append(box(nm, c, s, m))

    bw = max(0.4, (span - (n + 1) * pw) / n)
    for j in range(n):
        put("XSshop%d_%d" % (i, j), -span / 2.0 + pw * (j + 1) + bw * (j + 0.5),
            0.04, bw, 0.10, h, z0 + h / 2.0, om)
    for j in range(n + 1):
        put("XSpier%d_%d" % (i, j), -span / 2.0 + pw / 2.0 + j * (pw + bw),
            pd / 2.0 - 0.02, pw, pd, h, z0 + h / 2.0, pm)
    put("XSsign%d" % i, 0.0, pd / 2.0 - 0.02, span, pd, sh, z0 + h + sh / 2.0, sm)
    return out


PARTS_LEARNED = {"facade_bands": facade_bands, "shopfront_band": shopfront_band}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: delhi · cluster: balconygrille · gates: smoke+regress+lift ----
def shopfront_row(p, i):
    """Ground-floor street frontage: a row of bays (roller shutters / doors / glazing)
    separated by masonry piers, each opening recessed behind the pier face, with a flat
    signboard band above (full-width band, or one board per bay). Set bays=[] and
    height=0 to emit only the signage band at any z0 (upper-facade lettering strip)."""
    at = p.get("at", [0.0, 0.0])
    cx0 = float(at[0]); yf = float(at[1]); zc = float(p.get("z0", 0.0))
    h = float(p.get("height", 2.8)); d = float(p.get("depth", 0.30))
    pier = float(p.get("pier", 0.32)); rec = float(p.get("recess", 0.18))
    bays = list(p.get("bays", []))
    sign_h = float(p.get("sign_h", 0.7))
    pmat = p.get("pier_material", "stucco"); smat = p.get("sign_material", "sign")
    if bays:
        total = sum(float(b.get("w", 2.0)) for b in bays) + pier * (len(bays) + 1)
    else:
        total = float(p.get("width", 6.0))
    out = []
    x = cx0 - total * 0.5
    for k, b in enumerate(bays):
        bw = float(b.get("w", 2.0)); kind = str(b.get("kind", "shutter"))
        out.append(box("XSpier%d_%02d" % (i, k), [x + pier * 0.5, yf + d * 0.5, zc + h * 0.5],
                       [pier, d, h], pmat))
        x += pier
        cx = x + bw * 0.5
        oh = max(0.6, h - float(b.get("head", 0.16)))
        out.append(box("XSdark%d_%02d" % (i, k), [cx, yf + rec + 0.34, zc + oh * 0.5],
                       [bw - 0.06, 0.08, oh], "interior"))
        lm = p.get("shutter_material", "iron") if kind == "shutter" else p.get("door_material", "base")
        lw = bw - 0.10
        if kind != "open":
            out.append(box("XSleaf%d_%02d" % (i, k), [cx, yf + rec + 0.06, zc + oh * 0.5],
                           [lw, 0.10, oh], "glass" if kind == "glass" else lm))
        if kind == "shutter":
            nr = max(2, int(oh / 0.40))
            for r in range(nr):
                out.append(box("XSrib%d_%02d_%02d" % (i, k, r),
                               [cx, yf + rec + 0.005, zc + oh * (r + 0.5) / nr],
                               [lw, 0.05, 0.06], lm))
        out.append(box("XShead%d_%02d" % (i, k), [cx, yf + d * 0.45, zc + oh + (h - oh) * 0.5],
                       [bw, d * 0.9, h - oh], pmat))
        x += bw
    if bays:
        out.append(box("XSpier%d_%02d" % (i, len(bays)), [x + pier * 0.5, yf + d * 0.5, zc + h * 0.5],
                       [pier, d, h], pmat))
    if p.get("sign", True) and sign_h > 0.0:
        sz = zc + h + sign_h * 0.5
        if str(p.get("sign_mode", "band")) == "bay" and bays:
            x = cx0 - total * 0.5 + pier
            for k, b in enumerate(bays):
                bw = float(b.get("w", 2.0))
                out.append(box("XSsign%d_%02d" % (i, k), [x + bw * 0.5, yf - 0.05, sz],
                               [bw - 0.15, 0.14, sign_h], smat))
                x += bw + pier
        else:
            out.append(box("XSsign%d" % i, [cx0, yf - 0.05, sz], [total, 0.14, sign_h], smat))
    return out


def street_grille(p, i):
    """Open metal railing / grille screen standing on the pavement in front of the
    frontage: bottom-mid-top rails, close-pitched vertical bars, stouter posts, and
    optional gate leaves (framed panels) at given offsets."""
    at = p.get("at", [0.0, 0.0])
    cx = float(at[0]); yf = float(at[1]); zc = float(p.get("z0", 0.0))
    w = float(p.get("width", 6.0)); h = float(p.get("height", 2.4))
    t = float(p.get("thickness", 0.07)); pitch = float(p.get("bar_pitch", 0.18))
    bw = float(p.get("bar_w", 0.05)); mat = p.get("material", "iron")
    out = []
    for nm, z, th in (("lo", zc + 0.08, 0.14), ("mid", zc + h * 0.55, 0.10), ("hi", zc + h - 0.07, 0.14)):
        out.append(box("XGrail%d_%s" % (i, nm), [cx, yf, z], [w, t, th], mat))
    n = max(2, int(w / max(0.06, pitch)))
    for k in range(n):
        out.append(box("XGbar%d_%03d" % (i, k), [cx - w * 0.5 + w * (k + 0.5) / n, yf, zc + h * 0.5],
                       [bw, t * 0.8, h], mat))
    npo = max(2, int(p.get("posts", int(w / 2.0) + 1)))
    for k in range(npo):
        out.append(box("XGpost%d_%02d" % (i, k), [cx - w * 0.5 + w * k / (npo - 1), yf, zc + (h + 0.12) * 0.5],
                       [float(p.get("post_w", 0.14)), t * 1.6, h + 0.12], mat))
    for k, g in enumerate(p.get("gates", [])):
        gx = cx + float(g.get("x", 0.0)); gw = float(g.get("w", 2.4)); gh = float(g.get("h", h))
        for s in (-1, 1):
            out.append(box("XGstile%d_%02d_%d" % (i, k, (s + 1) // 2),
                           [gx + s * gw * 0.5, yf - 0.03, zc + gh * 0.5], [0.10, t, gh], mat))
        out.append(box("XGhead%d_%02d" % (i, k), [gx, yf - 0.03, zc + gh - 0.06], [gw, t, 0.12], mat))
    return out


PARTS_LEARNED = {"shopfront_row": shopfront_row, "street_grille": street_grille}

BUILDERS.update(PARTS_LEARNED)


# ---- learned_from: delhi · cluster: roofclutter · gates: smoke+regress+lift ----
def shop_recess(p, i):
    """Ground-floor shopfront: a row of recessed shutter/gate bays set behind
    projecting bulkhead piers and a full-width canopy slab, so the shop level reads
    dark and open under a shaded overhang instead of as solid punched wall.
    y_wall = the host mass facade plane (-W/2 for a street-facing front)."""
    L = float(p.get("width", 18.0))
    H = float(p.get("height", 3.4))
    d = float(p.get("depth", 0.6))
    yw = float(p.get("y_wall", -6.0))
    cx = float(p.get("at", [0.0, 0.0])[0])
    n = max(1, int(p.get("bays", 4)))
    pw = float(p.get("pier_w", 0.4))
    yf = yw - d                                  # forward face of piers / canopy
    out = []
    out.append(box("ShopVoid%d" % i, [cx, yw - 0.04, H * 0.5],
                   [L, 0.16, H], p.get("void_mat", "interior")))
    bw = max(0.4, (L - pw * (n + 1)) / n)
    sh = H * float(p.get("shutter_frac", 0.92))
    for k in range(n):
        bx = cx - L * 0.5 + pw * (k + 1) + bw * (k + 0.5)
        out.append(box("ShopBay%d_%02d" % (i, k), [bx, yw - 0.17, sh * 0.5],
                       [bw, 0.14, sh], p.get("shutter", "iron")))
    for k in range(n + 1):
        px = cx - L * 0.5 + pw * 0.5 + k * (bw + pw)
        out.append(box("ShopPier%d_%02d" % (i, k), [px, yw - d * 0.5, H * 0.5],
                       [pw, d, H], p.get("pier_mat", "stucco")))
    if p.get("canopy", True):
        oh = float(p.get("overhang", 0.4))
        t = float(p.get("canopy_t", 0.28))
        out.append(box("ShopCanopy%d" % i, [cx, (yf - oh + yw) * 0.5, H + t * 0.5],
                       [L + 0.12, d + oh, t], p.get("canopy_mat", "slab")))
    return out


def signage_band(p, i):
    """Horizontal shop-signage / lettering band spanning the facade width: a fascia
    backing plate plus rows x panels of proud sign boards. z = bottom of the band."""
    L = float(p.get("width", 18.0))
    h = float(p.get("height", 1.1))
    z = float(p.get("z", 3.4))
    yw = float(p.get("y_wall", -6.0))
    cx = float(p.get("at", [0.0, 0.0])[0])
    pr = float(p.get("proud", 0.16))
    n = max(1, int(p.get("panels", 3)))
    rows = max(1, int(p.get("rows", 1)))
    g = float(p.get("gap", 0.12))
    mats = list(p.get("materials", ["sign", "white"]))
    out = [box("SignFascia%d" % i, [cx, yw - pr * 0.5, z + h * 0.5],
               [L, pr, h], p.get("back_mat", "base"))]
    pwid = max(0.3, (L - g * (n + 1)) / n)
    rh = max(0.2, (h - g * (rows + 1)) / rows)
    for r in range(rows):
        for k in range(n):
            bx = cx - L * 0.5 + g * (k + 1) + pwid * (k + 0.5)
            bz = z + g * (r + 1) + rh * (r + 0.5)
            out.append(box("SignPanel%d_%02d_%02d" % (i, r, k),
                           [bx, yw - pr - 0.05, bz], [pwid, 0.10, rh],
                           mats[(k + r) % len(mats)]))
    return out


PARTS_LEARNED = {"shop_recess": shop_recess, "signage_band": signage_band}

BUILDERS.update(PARTS_LEARNED)
