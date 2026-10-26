// 170 Queen's Gate (R. Norman Shaw, 1888-9), the Imperial College Rector's
// residence on the corner of Queen's Gate and Imperial College Road. Wren-revival
// red brick house with stone dressings: white small-paned sashes under gauged
// brick heads with aprons and louvred shutters, a hipped tiled roof to the eaves
// with a white modillion cornice, a central curved pedimented dormer with a
// Serlian window flanked by segmental-pedimented dormers, and tall brick stacks.
// ---- local helpers (self-contained; duplicated per module by design) ----
function ccw(ring) {
  let a = 0;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a >= 0 ? ring : ring.slice().reverse();
}
function ringEdges(ring) {
  const out = [];
  for (let k = 0; k < ring.length; k++) {
    const a = ring[k],
      b = ring[(k + 1) % ring.length];
    const dx = b[0] - a[0],
      dy = b[1] - a[1],
      len = Math.hypot(dx, dy);
    if (len < 0.05) continue;
    out.push({
      k,
      a,
      b,
      len,
      tx: dx / len,
      ty: dy / len,
      nx: dy / len,
      ny: -dx / len,
      ang: Math.atan2(dy, dx),
    });
  }
  return out;
}
// One wall quad a->b (outward normal on the right of a->b) with kit.walls-style UVs.
function wallQuad(batch, m, a, b, z0, z1, { bay = 3.6, storey = 3.2, uvBase = 0, color } = {}) {
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const n = Math.round(len / bay);
  const u1 = n >= 1 ? n / 4 : 0.03;
  const v0 = (z0 - uvBase) / (2 * storey),
    v1 = (z1 - uvBase) / (2 * storey);
  batch.quad(
    m,
    [a[0], a[1], z0],
    [b[0], b[1], z0],
    [b[0], b[1], z1],
    [a[0], a[1], z1],
    [0, v0],
    [u1, v0],
    [u1, v1],
    [0, v1],
    color,
  );
}
// Walls of a ring where pick(edge) returns { m, bay, storey, uvBase } or null to skip.
function edgeWalls(batch, ring, z0, z1, pick) {
  for (const e of ringEdges(ring)) {
    const o = pick(e);
    if (o) wallQuad(batch, o.m, e.a, e.b, z0, z1, o);
  }
}
function prism(kit, batch, wallM, capM, ring, z0, z1, opt = {}) {
  kit.walls(batch, wallM, [[ring]], z0, z1, opt);
  if (capM) kit.cap(batch, capM, [[ring]], z1);
}
// Projecting horizontal band (string course / cornice) of height h at z, out metres proud.
function band(kit, batch, m, ring, z, h, out) {
  const r = kit.offsetRing(ring, out);
  kit.walls(batch, m, [[r]], z, z + h);
  kit.cap(batch, m, [[r]], z + h);
  if (out > 0.05) kit.cap(batch, m, [[r]], z, { down: true });
}
// Parapet wall of thickness t on the ring between z and z + h.
function parapet(kit, batch, m, ring, z, h, t = 0.3) {
  const inner = kit.offsetRing(ring, -t);
  kit.walls(batch, m, [[ring]], z, z + h);
  kit.walls(batch, m, [[inner.slice().reverse()]], z, z + h);
  kit.cap(batch, m, [[ring, inner.slice().reverse()]], z + h);
}
// Vertical fins along an edge: count from spacing, depth outwards, width along the edge.
function finsAlong(kit, batch, m, e, z0, z1, spacing, depth, width, { skipEnds = true } = {}) {
  const n = Math.max(1, Math.round(e.len / spacing));
  for (let i = skipEnds ? 1 : 0; i <= (skipEnds ? n - 1 : n); i++) {
    const t = (i / n) * e.len;
    const x = e.a[0] + e.tx * t + (e.nx * depth) / 2,
      y = e.a[1] + e.ty * t + (e.ny * depth) / 2;
    kit.box(batch, m, x, y, z0, width, depth, z1 - z0, e.ang);
  }
}
// Horizontal bar along an edge (sunshade, louvre, canopy).
function barAlong(kit, batch, m, e, z, h, depth, inset = 0) {
  const L = e.len - 2 * inset;
  if (L <= 0.1) return;
  const mid = e.len / 2;
  const x = e.a[0] + e.tx * mid + (e.nx * depth) / 2,
    y = e.a[1] + e.ty * mid + (e.ny * depth) / 2;
  kit.box(batch, m, x, y, z, L, depth, h, e.ang);
}
function pointOn(e, t, off = 0) {
  return [e.a[0] + e.tx * t + e.nx * off, e.a[1] + e.ty * t + e.ny * off];
}
// Canvas helpers.
function noiseFill(g, w, h, base, r, amt = 0.08, size = 3) {
  g.fillStyle = base;
  g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += size)
    for (let x = 0; x < w; x += size) {
      const k = (r() - 0.5) * amt;
      g.fillStyle = k > 0 ? `rgba(255,255,255,${k})` : `rgba(0,0,0,${-k})`;
      g.fillRect(x, y, size, size);
    }
}
function brickCourses(g, w, h, r, base, course = 3) {
  noiseFill(g, w, h, base, r, 0.12, 3);
  g.fillStyle = 'rgba(230,220,200,0.18)';
  for (let y = 0; y < h; y += course) g.fillRect(0, y, w, 1);
}
function glassPane(g, x, y, w, h, r, base = [46, 62, 74]) {
  const grd = g.createLinearGradient(x, y, x + w * 0.4, y + h);
  const k = 0.85 + r() * 0.3;
  grd.addColorStop(
    0,
    `rgb(${(base[0] * k * 1.5) | 0},${(base[1] * k * 1.45) | 0},${(base[2] * k * 1.4) | 0})`,
  );
  grd.addColorStop(1, `rgb(${(base[0] * k) | 0},${(base[1] * k) | 0},${(base[2] * k) | 0})`);
  g.fillStyle = grd;
  g.fillRect(x, y, w, h);
}
function sash(g, x, y, w, h, r, { frame = '#f2efe6', panesX = 3, panesY = 2, bar = 2 } = {}) {
  g.fillStyle = frame;
  g.fillRect(x - bar, y - bar, w + 2 * bar, h + 2 * bar);
  glassPane(g, x, y, w, h, r);
  g.fillStyle = frame;
  g.fillRect(x, y + h / 2 - bar / 2, w, bar * 1.2);
  for (let i = 1; i < panesX; i++) g.fillRect(x + (w * i) / panesX - 0.5, y, 1.2, h);
  for (let j = 1; j < panesY * 2; j++)
    if (j !== panesY) g.fillRect(x, y + (h * j) / (panesY * 2) - 0.5, w, 1.2);
}
// ---- end helpers ----
// ---- detail helpers (refinement pass; self-contained) ----
// Quad whose winding is chosen so that its face normal agrees with n.
function quadN(batch, m, p, uv, n, color) {
  const ux = p[1][0] - p[0][0],
    uy = p[1][1] - p[0][1],
    uz = p[1][2] - p[0][2];
  const vx = p[2][0] - p[0][0],
    vy = p[2][1] - p[0][1],
    vz = p[2][2] - p[0][2];
  const cx = uy * vz - uz * vy,
    cy = uz * vx - ux * vz,
    cz = ux * vy - uy * vx;
  if (cx * n[0] + cy * n[1] + cz * n[2] < 0) {
    p = [p[0], p[3], p[2], p[1]];
    uv = [uv[0], uv[3], uv[2], uv[1]];
  }
  batch.quad(m, p[0], p[1], p[2], p[3], uv[0], uv[1], uv[2], uv[3], color);
}
// Wall along edge e (z0..z1) pierced by openings [{t0, t1, zb, zt}] (t along the edge),
// with real reveals of depth d and an optional dark back panel inside each opening.
// UVs: one texture tile = tile[0] x tile[1] metres measured from (a, uvBase).
function punchedWall(batch, wallM, revealM, e, z0, z1, holes, opt = {}) {
  const { d = 0.22, tile = [14.4, 6.4], uvBase = 0, color, back } = opt;
  const P = (t, z, o = 0) => [e.a[0] + e.tx * t + e.nx * o, e.a[1] + e.ty * t + e.ny * o, z];
  const UV = (t, z) => [t / tile[0], (z - uvBase) / tile[1]];
  const n = [e.nx, e.ny, 0];
  const zs = new Set([z0, z1]);
  for (const h of holes) {
    if (h.zb > z0 && h.zb < z1) zs.add(h.zb);
    if (h.zt > z0 && h.zt < z1) zs.add(h.zt);
  }
  const Z = [...zs].sort((p, q) => p - q);
  for (let i = 0; i < Z.length - 1; i++) {
    const za = Z[i],
      zb = Z[i + 1],
      zm = (za + zb) / 2;
    const cut = holes.filter((h) => h.zb < zm && h.zt > zm).sort((p, q) => p.t0 - q.t0);
    const seg = (ta, tb) => {
      if (tb - ta > 1e-3)
        quadN(
          batch,
          wallM,
          [P(ta, za), P(tb, za), P(tb, zb), P(ta, zb)],
          [UV(ta, za), UV(tb, za), UV(tb, zb), UV(ta, zb)],
          n,
          color,
        );
    };
    let t = 0;
    for (const h of cut) {
      seg(t, h.t0);
      t = Math.max(t, h.t1);
    }
    seg(t, e.len);
  }
  const rv = revealM ?? wallM;
  for (const h of holes) {
    const dd = h.d ?? d;
    const sq = [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ];
    quadN(
      batch,
      rv,
      [P(h.t0, h.zb), P(h.t0, h.zb, -dd), P(h.t0, h.zt, -dd), P(h.t0, h.zt)],
      sq,
      [e.tx, e.ty, 0],
      color,
    );
    quadN(
      batch,
      rv,
      [P(h.t1, h.zb), P(h.t1, h.zb, -dd), P(h.t1, h.zt, -dd), P(h.t1, h.zt)],
      sq,
      [-e.tx, -e.ty, 0],
      color,
    );
    quadN(
      batch,
      rv,
      [P(h.t0, h.zt), P(h.t1, h.zt), P(h.t1, h.zt, -dd), P(h.t0, h.zt, -dd)],
      sq,
      [0, 0, -1],
      color,
    );
    quadN(
      batch,
      rv,
      [P(h.t0, h.zb), P(h.t1, h.zb), P(h.t1, h.zb, -dd), P(h.t0, h.zb, -dd)],
      sq,
      [0, 0, 1],
      color,
    );
    if (h.back ?? back)
      quadN(
        batch,
        h.back ?? back,
        [P(h.t0, h.zb, -dd), P(h.t1, h.zb, -dd), P(h.t1, h.zt, -dd), P(h.t0, h.zt, -dd)],
        sq,
        n,
      );
  }
}
// Evenly spaced openings along an edge: n bays, opening width w, from zb to zt.
function bayHoles(e, n, w, zb, zt, { margin = 0, skip = () => false, d } = {}) {
  const out = [];
  const usable = e.len - 2 * margin;
  for (let k = 0; k < n; k++) {
    if (skip(k)) continue;
    const t = margin + (usable * (k + 0.5)) / n;
    out.push({ t0: t - w / 2, t1: t + w / 2, zb, zt, k, t, d });
  }
  return out;
}
// A framed window (kit.windowRow) set into an opening at the back of its reveal.
function fitWindow(kit, batch, e, h, opts = {}) {
  const dd = (h.d ?? opts.d ?? 0.22) - 0.02;
  const A = [e.a[0] + e.tx * h.t0 - e.nx * dd, e.a[1] + e.ty * h.t0 - e.ny * dd];
  const B = [e.a[0] + e.tx * h.t1 - e.nx * dd, e.a[1] + e.ty * h.t1 - e.ny * dd];
  const { arch = 0, ...rest } = opts;
  kit.windowRow(batch, A, B, h.zb, {
    count: 1,
    margin: 0,
    width: h.t1 - h.t0 - 0.06,
    height: h.zt - h.zb - arch,
    head: arch ? 'arch' : 'none',
    depth: 0.1,
    ...rest,
  });
}
// Box placed by edge coordinates (t along the edge, o outwards from the wall plane).
function boxOn(kit, batch, m, e, t, o, z0, w, d, h, color) {
  kit.box(
    batch,
    m,
    e.a[0] + e.tx * t + e.nx * o,
    e.a[1] + e.ty * t + e.ny * o,
    z0,
    w,
    d,
    h,
    e.ang,
    color,
  );
}
// Flight of n steps rising towards the wall at edge position t (w wide).
function stepsOn(kit, batch, m, e, t, w, n, { rise = 0.16, tread = 0.32, z0 = 0 } = {}) {
  for (let i = 0; i < n; i++) {
    const depth = tread * (n - i);
    boxOn(kit, batch, m, e, t, depth / 2, z0 + i * rise, w, depth, rise);
  }
}
// Railing between points p and q (scene / local plane) with bars, rails and finials.
function railing(kit, batch, m, p, q, z, { h = 1.1, spacing = 0.13, finial = true } = {}) {
  const dx = q[0] - p[0],
    dy = q[1] - p[1],
    len = Math.hypot(dx, dy);
  if (len < 0.2) return;
  const ang = Math.atan2(dy, dx);
  const mx = (p[0] + q[0]) / 2,
    my = (p[1] + q[1]) / 2;
  kit.box(batch, m, mx, my, z + h - 0.06, len, 0.05, 0.05, ang);
  kit.box(batch, m, mx, my, z + 0.12, len, 0.04, 0.04, ang);
  const n = Math.max(1, Math.floor(len / spacing));
  for (let i = 0; i <= n; i++) {
    const x = p[0] + (dx * i) / n,
      y = p[1] + (dy * i) / n;
    kit.box(batch, m, x, y, z, 0.022, 0.022, h + (finial ? 0.08 : 0), ang);
    if (finial && i % 2 === 0) kit.box(batch, m, x, y, z + h + 0.04, 0.05, 0.05, 0.07, ang + 0.785);
  }
}
// Thin paved slab over a ring (forecourt, area, terrace).
function paved(kit, batch, m, ring, z = 0.04) {
  kit.walls(batch, m, [[ring]], 0, z, { bay: 1e6 });
  kit.cap(batch, m, [[ring]], z, { scale: 4 });
}
// Rectangle ring from an edge: from t0..t1 along e, o0..o1 outwards.
function edgeRect(e, t0, t1, o0, o1) {
  const P = (t, o) => [e.a[0] + e.tx * t + e.nx * o, e.a[1] + e.ty * t + e.ny * o];
  const r = [P(t0, o0), P(t1, o0), P(t1, o1), P(t0, o1)];
  let a = 0;
  for (let k = 0; k < 4; k++) a += r[k][0] * r[(k + 1) % 4][1] - r[(k + 1) % 4][0] * r[k][1];
  return a >= 0 ? r : r.reverse();
}
// Louvred enclosure: frame box plus horizontal slats on each side.
function louvreBox(kit, batch, frameM, slatM, x, y, z0, w, d, h, ang, pitch = 0.25) {
  kit.box(batch, frameM, x, y, z0, w - 0.3, d - 0.3, h, ang);
  kit.box(batch, frameM, x, y, z0 + h, w + 0.1, d + 0.1, 0.18, ang);
  const c = Math.cos(ang),
    s = Math.sin(ang);
  for (let z = z0 + 0.2; z < z0 + h - 0.1; z += pitch) {
    for (const sg of [-1, 1]) {
      kit.box(
        batch,
        slatM,
        x - s * sg * (d / 2 - 0.08),
        y + c * sg * (d / 2 - 0.08),
        z,
        w,
        0.05,
        0.12,
        ang,
      );
      kit.box(
        batch,
        slatM,
        x + c * sg * (w / 2 - 0.08),
        y + s * sg * (w / 2 - 0.08),
        z,
        0.05,
        d,
        0.12,
        ang,
      );
    }
  }
  for (const [su, sv] of [
    [-1, -1],
    [1, -1],
    [1, 1],
    [-1, 1],
  ])
    kit.box(
      batch,
      frameM,
      x + c * su * (w / 2 - 0.05) - s * sv * (d / 2 - 0.05),
      y + s * su * (w / 2 - 0.05) + c * sv * (d / 2 - 0.05),
      z0,
      0.14,
      0.14,
      h,
      ang,
    );
}
// Roof edge guard rail inset from a ring.
function roofRail(kit, batch, m, ring, z, inset = 0.6, h = 1.1) {
  const r = kit.offsetRing(ring, -inset);
  for (let k = 0; k < r.length; k++) {
    const p = r[k],
      q = r[(k + 1) % r.length];
    const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
    if (len < 0.5) continue;
    const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
    kit.box(batch, m, (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, z + h - 0.05, len, 0.05, 0.05, ang);
    kit.box(batch, m, (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, z + h / 2, len, 0.04, 0.04, ang);
    const n = Math.max(1, Math.round(len / 1.6));
    for (let i = 0; i <= n; i++)
      kit.box(
        batch,
        m,
        p[0] + ((q[0] - p[0]) * i) / n,
        p[1] + ((q[1] - p[1]) * i) / n,
        z,
        0.05,
        0.05,
        h,
        ang,
      );
  }
}
// Extract flue with a conical rain cap (lathe) at (x, y) from z0 to z0 + h.
function flue(THREE, batch, m, x, y, z0, h, r = 0.35) {
  const g = new THREE.LatheGeometry(
    [
      [0.001, 0],
      [r, 0],
      [r, h],
      [r * 1.25, h + 0.05],
      [r * 1.25, h + 0.12],
      [r * 1.7, h + 0.35],
      [r * 1.7, h + 0.4],
      [0.001, h + 0.7],
    ].map(([a, b]) => new THREE.Vector2(a, b)),
    10,
  ).rotateX(Math.PI / 2);
  batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0));
  g.dispose();
}
// Sign panel material with text.
function signMaterial(
  kit,
  key,
  text,
  { bg = '#1e2a36', fg = '#f4f1ea', w = 512, h = 64, font = 'bold 34px sans-serif' } = {},
) {
  return kit.paintedMaterial(key, w, h, (c, W, H) => {
    c.fillStyle = bg;
    c.fillRect(0, 0, W, H);
    c.fillStyle = fg;
    c.font = font;
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.fillText(text, W / 2, H / 2 + 2);
  });
}
// ---- end detail helpers ----

// Segment of a circle (chord w, rise) as a slab of depth d (centred on y), base at z=0.
function segmentSlab(THREE, w, rise, d) {
  const R = ((w * w) / 4 + rise * rise) / (2 * rise);
  const sh = new THREE.Shape();
  sh.moveTo(-w / 2, 0);
  sh.lineTo(w / 2, 0);
  const a0 = Math.atan2(R - rise, w / 2);
  sh.absarc(0, rise - R, R, a0, Math.PI - a0, false);
  const geo = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 12 });
  geo.rotateX(Math.PI / 2); // shape y -> z, extrusion +z -> -y
  geo.translate(0, d / 2, 0);
  return geo;
}

export default {
  id: 'imperial_170_queens_gate',
  name: "170 Queen's Gate (Rector's Residence)",
  claims: ['28351f56-86f4-4152-99fe-01ac157d7cca'],
  references: [
    {
      title: "170 Queen's Gate - British Listed Buildings (Historic England 1227415)",
      url: 'https://britishlistedbuildings.co.uk/101227415-170-queens-gate-sw7-knightsbridge-and-belgravia-ward',
      used_for:
        'Grade II*, Shaw 1888, red brick Wren revival, gauged brick heads and aprons, small-pane sashes, louvred shutters, hipped tiled roof to eaves, central curved pedimented dormer with Serlian motif, segmental pediments, tall stacks',
    },
    {
      title: "170 Queen's Gate - Imperial College history",
      url: 'https://imperial.ac.uk/about/history/170-queens-gate',
      used_for: "red brick with stone dressings, completed 1889, Rector's lodging",
    },
    {
      title: "Plate 104: No. 170 Queen's Gate - Survey of London vol 38",
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-104',
      used_for: 'date 1888-9, main front to Imperial College Road',
    },
  ],
  notes:
    'Eaves raised to 11.1 m (three tall storeys over a low plinth) with a 5 m hipped roof; the Overture height 10.4 m is inferred from floors. Bay count (7 x 4), door position and dormer sizes are proportioned from the listing text, not measured. Refinement: real recessed sash windows (glazing bars, meeting rails, stone sills, gauged brick flat arches with keystones, rubbed-brick aprons, 3D louvred shutters), stone doorcase with pilasters and segmental hood over steps, stone quoins, modillion eaves cornice with bed mould, dormers with framed casements, corbelled stacks with pots, dwarf wall and railings with a gate; the rear and end windows repeat the front pattern without shutters (assumption).',
  build({ THREE, kit, buildings, placeAssets }) {
    const ring = ccw(buildings[0].polys[0][0]);
    // Main front: the long edge whose outward normal points most to the south.
    const es = ringEdges(ring);
    const front = es.filter((e) => e.len > 15).sort((p, q) => p.ny - q.ny)[0];
    const ang = front.ang;
    const ex = kit.orientedExtent(ring, ang);
    const { u0, u1, v0, v1 } = ex;
    const L = u1 - u0,
      D = v1 - v0,
      um = (u0 + u1) / 2,
      vm = (v0 + v1) / 2;
    const outer = new THREE.Group();
    const g = new THREE.Group();
    g.rotation.z = ang; // local (u, v) -> world
    outer.add(g);
    const b = new kit.MeshBatch();
    const stone = kit.mat('#d9d0bb'),
      stone2 = kit.mat('#cfc5ad'),
      white = kit.mat('#f3f0e8'),
      roofM = kit.roof('clay', 2),
      dark = kit.mat('dark_glass'),
      stackM = kit.mat('#8a4433'),
      rubbed = kit.mat('#b65d44'),
      brickPlain = kit.mat('#93483a'),
      lead = kit.mat('lead'),
      doorM = kit.mat('#263229'),
      iron = kit.mat('#1d2022', { roughness: 0.5 }),
      potM = kit.mat('#b6693f');
    const storey = 3.4,
      base = 0.9,
      eave = base + 3 * storey,
      rise = 5.0;
    const brickM = kit.paintedMaterial('imperial_170qg:brick', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1702);
      brickCourses(c, w, h, r, '#9a4a36', 3);
      // Flemish bond headers slightly darker
      c.fillStyle = 'rgba(40,10,5,0.12)';
      for (let y = 0; y < h; y += 3)
        for (let x = (y / 3) % 2 ? 0 : 4; x < w; x += 8) c.fillRect(x, y, 3, 2);
    });
    const shutterM = kit.paintedMaterial('imperial_170qg:shutter', 64, 128, (c, w, h) => {
      c.fillStyle = '#3a4a3c';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.16)';
      for (let y = 4; y < h - 4; y += 4) c.fillRect(4, y, w - 8, 1.5);
      c.fillStyle = 'rgba(0,0,0,0.35)';
      c.fillRect(0, 0, 4, h);
      c.fillRect(w - 4, 0, 4, h);
      c.fillRect(0, h / 2 - 2, w, 4);
    });
    const rect = [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    const edges = ringEdges(rect);
    const fe = edges[0]; // front (normal -v)
    // Plinth (stone) and string course over it.
    kit.walls(b, stone2, [[kit.offsetRing(rect, 0.06)]], 0, base);
    kit.cornice(b, stone, rect, base - 0.12, { height: 0.18, projection: 0.12 });
    // Brick walls punched with recessed sash windows.
    const doorT = L / 2;
    const win = [
      { zb: base + 0.75, h: 2.35 },
      { zb: base + storey + 0.65, h: 2.5 },
      { zb: base + 2 * storey + 0.6, h: 1.95 },
    ];
    for (const e of edges) {
      const nb = e.len > 20 ? 7 : 4;
      const holes = [];
      win.forEach((w, s) => {
        for (const h of bayHoles(e, nb, 1.28, w.zb, w.zb + w.h, {
          margin: 0.9,
          skip: (k) => e === fe && s === 0 && k === 3,
        }))
          holes.push({ ...h, s });
      });
      if (e === fe)
        holes.push({
          t0: doorT - 0.8,
          t1: doorT + 0.8,
          zb: base,
          zt: base + 2.85,
          door: true,
          d: 0.35,
        });
      punchedWall(b, brickM, brickPlain, e, base, eave, holes, {
        d: 0.24,
        tile: [e.len > 20 ? L : D, 2 * storey],
        uvBase: base,
        back: dark,
      });
      for (const h of holes) {
        const w = h.t1 - h.t0,
          tm = (h.t0 + h.t1) / 2;
        if (h.door) {
          // Panelled door with a radial fanlight under a stone doorcase.
          boxOn(kit, b, doorM, e, tm, -0.33, h.zb, w - 0.1, 0.06, 2.3);
          for (const s of [-1, 1])
            for (const z of [0.25, 1.25])
              boxOn(
                kit,
                b,
                kit.mat('#2f3d33'),
                e,
                tm + s * 0.36,
                -0.29,
                h.zb + z,
                0.55,
                0.03,
                0.85,
              );
          boxOn(kit, b, white, e, tm, -0.3, h.zb + 2.3, w - 0.1, 0.1, 0.1);
          boxOn(kit, b, dark, e, tm, -0.33, h.zb + 2.4, w - 0.1, 0.04, 0.45);
          for (let i = -2; i <= 2; i++)
            boxOn(kit, b, white, e, tm + i * 0.28, -0.31, h.zb + 2.4, 0.04, 0.04, 0.45);
          // pilasters, entablature and segmental hood
          for (const s of [-1, 1]) {
            boxOn(kit, b, stone, e, tm + s * 1.15, 0.12, base, 0.42, 0.24, 2.85);
            boxOn(kit, b, stone, e, tm + s * 1.15, 0.14, base + 2.8, 0.55, 0.3, 0.2);
            boxOn(kit, b, stone, e, tm + s * 1.15, 0.14, base, 0.55, 0.3, 0.25);
          }
          boxOn(kit, b, stone, e, tm, 0.16, base + 3.0, 3.0, 0.34, 0.3);
          const ped = segmentSlab(THREE, 3.2, 0.5, 0.42);
          const p = [e.a[0] + e.tx * tm + e.nx * 0.2, e.a[1] + e.ty * tm + e.ny * 0.2];
          b.addGeometry(stone, ped, new THREE.Matrix4().makeTranslation(p[0], p[1], base + 3.3));
          ped.dispose();
          stepsOn(kit, b, stone2, e, tm, 2.6, 5, { rise: base / 5, tread: 0.34 });
          continue;
        }
        fitWindow(kit, b, e, h, { d: 0.24, glass: dark, frame: white, sill: white, bars: 2 });
        // meeting rail of the sash
        const dd = 0.2;
        boxOn(kit, b, white, e, tm, -dd + 0.06, h.zb + (h.zt - h.zb) * 0.52, w - 0.08, 0.08, 0.07);
        // stone sill, gauged brick flat arch with keystone, rubbed-brick apron
        boxOn(kit, b, stone, e, tm, 0.06, h.zb - 0.12, w + 0.3, 0.2, 0.12);
        boxOn(kit, b, rubbed, e, tm, 0.025, h.zt, w + 0.32, 0.05, 0.4);
        boxOn(kit, b, stone, e, tm, 0.04, h.zt - 0.02, 0.26, 0.08, 0.46);
        if (h.s < 2) boxOn(kit, b, rubbed, e, tm, 0.02, h.zb - 0.62, w - 0.1, 0.04, 0.5);
        // louvred shutters folded back beside the front and Queen's Gate windows
        if (e === fe || e === edges[3])
          for (const s of [-1, 1])
            boxOn(
              kit,
              b,
              shutterM,
              e,
              tm + s * (w / 2 + 0.33),
              0.04,
              h.zb,
              0.58,
              0.05,
              h.zt - h.zb,
            );
      }
    }
    // String course at first floor and stone quoins.
    kit.cornice(b, stone, rect, base + storey - 0.1, { height: 0.22, projection: 0.08 });
    for (const [cu, cv] of rect)
      for (let z = base, k = 0; z < eave - 0.6; z += 0.6, k++) {
        const w1 = k % 2 ? 0.95 : 0.6;
        kit.box(b, k % 3 ? stone : stone2, cu, cv, z + 0.01, w1, w1, 0.56);
      }
    // White modillion eaves cornice with bed mould and fascia.
    kit.cornice(b, white, rect, eave - 0.75, { height: 0.25, projection: 0.12 });
    kit.cornice(b, white, rect, eave - 0.35, { height: 0.55, projection: 0.55, steps: 3 });
    for (const e of ringEdges(kit.offsetRing(rect, 0.28))) {
      const n = Math.round(e.len / 0.55);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n));
        kit.box(b, white, p[0], p[1], eave - 0.6, 0.16, 0.48, 0.25, e.ang);
      }
    }
    // Hipped tiled roof with lead hips and ridge.
    const roofRing = kit.offsetRing(rect, 0.15);
    const pr = kit.pitchedRoof(b, roofM, brickPlain, roofRing, 0, eave + 0.2, rise, 'hipped', {
      overhang: 0.3,
    });
    const ridgeZ = eave + 0.2 + rise;
    const ridgeM = kit.mat('#7a3a2a');
    {
      const [r0, r1] = pr.ridge;
      kit.box(
        b,
        ridgeM,
        (r0[0] + r1[0]) / 2,
        (r0[1] + r1[1]) / 2,
        ridgeZ - 0.08,
        Math.hypot(r1[0] - r0[0], r1[1] - r0[1]) + 0.2,
        0.3,
        0.22,
        0,
      );
      // hip rolls
      const ee = pr.e;
      const corners = [
        [ee.u0 - 0.3, ee.v0 - 0.3, r0],
        [ee.u1 + 0.3, ee.v0 - 0.3, r1],
        [ee.u1 + 0.3, ee.v1 + 0.3, r1],
        [ee.u0 - 0.3, ee.v1 + 0.3, r0],
      ];
      for (const [cu, cv, r] of corners) {
        const p = [cu, cv, eave + 0.2];
        const dx = r[0] - p[0],
          dy = r[1] - p[1],
          dz = r[2] - p[2];
        const len = Math.hypot(dx, dy, dz);
        const geo = new THREE.CylinderGeometry(0.11, 0.11, len, 6);
        const q = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          new THREE.Vector3(dx / len, dy / len, dz / len),
        );
        const m = new THREE.Matrix4().compose(
          new THREE.Vector3(p[0] + dx / 2, p[1] + dy / 2, p[2] + dz / 2),
          q,
          new THREE.Vector3(1, 1, 1),
        );
        b.addGeometry(ridgeM, geo, m);
        geo.dispose();
      }
    }
    const half = D / 2 + 0.45;
    const slopeZ = (d) => eave + 0.2 + (rise * d) / half; // d: inwards from the eave line
    // Dormers on the front and back slopes.
    const dormer = (u, w, h, face, kind) => {
      const d = 1.4;
      const vFace = face < 0 ? v0 + d : v1 - d;
      const zb = slopeZ(d + 0.45) - 0.2;
      const depth = 2.4;
      const vc = vFace - (face * depth) / 2;
      kit.box(b, white, u, vc, zb, w, depth, h);
      kit.box(b, lead, u - w / 2 - 0.05, vc - face * 0.1, zb, 0.12, depth, h);
      kit.box(b, lead, u + w / 2 + 0.05, vc - face * 0.1, zb, 0.12, depth, h);
      // pilaster strips and an apron in white joinery
      for (const s of [-1, 1])
        kit.box(b, white, u + s * (w / 2 - 0.12), vFace + face * 0.06, zb, 0.24, 0.12, h);
      const fa = (x0, x1) => [
        [x0, vFace + face * 0.02],
        [x1, vFace + face * 0.02],
      ];
      const win = (x0, x1, z, hh, head) => {
        const [A, B] = face < 0 ? fa(x0, x1) : fa(x1, x0);
        kit.windowRow(b, A, B, z, {
          count: 1,
          margin: 0,
          width: Math.abs(x1 - x0),
          height: hh,
          head,
          glass: dark,
          frame: white,
          sill: white,
          bars: 1,
          depth: 0.1,
        });
      };
      if (kind === 'serlian') {
        const ch = h - 1.6;
        win(u - w * 0.14, u + w * 0.14, zb + 0.45, ch - w * 0.14, 'arch');
        win(u - w * 0.4, u - w * 0.22, zb + 0.45, ch * 0.72, 'lintel');
        win(u + w * 0.22, u + w * 0.4, zb + 0.45, ch * 0.72, 'lintel');
        for (const s of [-1, 1])
          kit.box(
            b,
            white,
            u + s * w * 0.18,
            vFace + face * 0.1,
            zb + 0.45,
            0.14,
            0.14,
            ch * 0.72 + 0.1,
          );
      } else win(u - w * 0.3, u + w * 0.3, zb + 0.4, h - 1.0, 'none');
      // lead roof behind and a curved (segmental) pediment over the front
      kit.box(b, lead, u, vc, zb + h, w + 0.2, depth, 0.15);
      const ped = segmentSlab(THREE, w + 0.5, Math.min(1.1, w * 0.28), 0.5);
      b.addGeometry(
        white,
        ped,
        new THREE.Matrix4().makeTranslation(u, vFace - face * 0.15, zb + h - 0.05),
      );
      ped.dispose();
      kit.box(b, white, u, vFace - face * 0.1, zb + h - 0.2, w + 0.5, 0.6, 0.2);
    };
    const bay = (L - 1.8) / 7;
    dormer(um, 4.6, 3.3, -1, 'serlian');
    dormer(u0 + 0.9 + bay * 1.5, 2.0, 2.3, -1, 'seg');
    dormer(u1 - 0.9 - bay * 1.5, 2.0, 2.3, -1, 'seg');
    dormer(um, 2.0, 2.3, 1, 'seg');
    dormer(u0 + 0.9 + bay * 1.5, 2.0, 2.3, 1, 'seg');
    dormer(u1 - 0.9 - bay * 1.5, 2.0, 2.3, 1, 'seg');
    // Tall brick stacks with corbelled caps and clay pots rising well above the ridge.
    const pot = new THREE.LatheGeometry(
      [
        [0.001, 0],
        [0.2, 0],
        [0.17, 0.08],
        [0.15, 0.55],
        [0.19, 0.62],
        [0.19, 0.7],
        [0.14, 0.72],
        [0.001, 0.72],
      ].map(([r, z]) => new THREE.Vector2(r, z)),
      8,
    ).rotateX(Math.PI / 2);
    const stack = (u, v, w, d, np) => {
      kit.box(b, stackM, u, v, eave, w, d, ridgeZ + 3.0 - eave);
      // recessed panels on the faces
      kit.box(b, kit.mat('#7c3c2e'), u, v, ridgeZ - 0.5, w + 0.04, d - 0.5, 2.6);
      kit.box(b, kit.mat('#7c3c2e'), u, v, ridgeZ - 0.5, w - 0.5, d + 0.04, 2.6);
      kit.box(b, stackM, u, v, ridgeZ + 2.75, w + 0.2, d + 0.2, 0.15);
      kit.box(b, stone, u, v, ridgeZ + 2.9, w + 0.36, d + 0.36, 0.22);
      kit.box(b, stackM, u, v, ridgeZ + 3.12, w + 0.1, d + 0.1, 0.25);
      for (let i = 0; i < np; i++) {
        const t = np === 1 ? 0 : -0.5 + i / (np - 1);
        const long = w >= d;
        b.addGeometry(
          potM,
          pot,
          new THREE.Matrix4().makeTranslation(
            u + (long ? t * (w - 0.5) : 0),
            v + (long ? 0 : t * (d - 0.5)),
            ridgeZ + 3.37,
          ),
        );
      }
    };
    stack(u0 + D / 2 - 0.2, vm, 2.6, 1.3, 4);
    stack(u1 - D / 2 + 0.2, vm, 2.6, 1.3, 4);
    stack(u0 + 0.9, vm + 3.2, 1.2, 2.4, 2);
    stack(u1 - 0.9, vm - 3.2, 1.2, 2.4, 2);
    pot.dispose();
    // Rainwater downpipes with hoppers at the corners of the front and back.
    for (const [cu, cv, sv] of [
      [u0 + 1.2, v0, -1],
      [u1 - 1.2, v0, -1],
      [u0 + 1.2, v1, 1],
      [u1 - 1.2, v1, 1],
    ]) {
      kit.box(b, iron, cu, cv + sv * 0.08, 0, 0.1, 0.1, eave - 0.6);
      kit.box(b, iron, cu, cv + sv * 0.12, eave - 1.0, 0.32, 0.22, 0.35);
    }
    // Dwarf wall with stone coping and railings along the front; gate on the door axis.
    const rv = v0 - 2.4;
    for (const [a0, a1] of [
      [u0 - 0.6, um - 1.3],
      [um + 1.3, u1 + 0.6],
    ]) {
      kit.box(b, brickPlain, (a0 + a1) / 2, rv, 0, a1 - a0, 0.34, 0.5);
      kit.box(b, stone, (a0 + a1) / 2, rv, 0.5, a1 - a0 + 0.04, 0.42, 0.1);
      railing(kit, b, iron, [a0, rv], [a1, rv], 0.6, { h: 1.0, spacing: 0.14 });
    }
    for (const s of [-1, 1]) {
      kit.box(b, stone2, um + s * 1.45, rv, 0, 0.5, 0.5, 1.6);
      kit.box(b, stone, um + s * 1.45, rv, 1.6, 0.62, 0.62, 0.14);
      const ball = new THREE.SphereGeometry(0.2, 10, 6);
      b.addGeometry(stone, ball, new THREE.Matrix4().makeTranslation(um + s * 1.45, rv, 1.94));
      ball.dispose();
    }
    railing(kit, b, iron, [um - 1.15, rv], [um + 1.15, rv], 0, { h: 1.5, spacing: 0.12 });
    // York stone path from gate to steps, gravel strips either side.
    kit.box(
      b,
      kit.mat('#bdb4a0'),
      um,
      (rv + v0 - 1.7) / 2,
      0,
      2.2,
      Math.abs(rv - (v0 - 1.7)),
      0.05,
    );
    kit.box(
      b,
      kit.mat('#a9a08a'),
      (u0 - 0.6 + um - 1.2) / 2,
      (rv + v0) / 2,
      0,
      um - 1.2 - u0 + 0.6,
      Math.abs(rv - v0) - 0.3,
      0.035,
    );
    kit.box(
      b,
      kit.mat('#a9a08a'),
      (um + 1.2 + u1 + 0.6) / 2,
      (rv + v0) / 2,
      0,
      u1 + 0.6 - um - 1.2,
      Math.abs(rv - v0) - 0.3,
      0.035,
    );
    g.add(b.toGroup('imperial_170_queens_gate'));
    // Two lamp standards flanking the gate (scene coordinates).
    const W = (u, v) => ex.at(u, v, 0);
    const pl = [W(um - 2.2, rv - 0.6), W(um + 2.2, rv - 0.6)].map((p) => [
      p[0],
      p[1],
      ang + Math.PI,
    ]);
    if (placeAssets) outer.add(placeAssets('street_lamp', pl));
    return outer;
  },
};
