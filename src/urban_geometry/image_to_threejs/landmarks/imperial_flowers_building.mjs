// Flowers Building, Imperial College (Foster and Partners, opened December 2000),
// the life-sciences research building behind the Sir Ernst Chain Building, named
// after former Rector Lord Flowers. Nine-storey high-tech laboratory block:
// alternating bands of silver aluminium panels and full-width glazing shaded by
// projecting horizontal aluminium louvre blades, solid-clad ends with glazed
// stair slots, a louvred rooftop plant enclosure with a row of stainless steel
// extract flues, and a low glazed west wing.
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

export default {
  id: 'imperial_flowers_building',
  name: 'Flowers Building, Imperial College',
  claims: ['3298ff75-3b67-4db6-b8a7-e6558bd5b0ea'],
  references: [
    {
      title: 'Celebrating 25 Years of the Flowers Building - Imperial News',
      url: 'https://www.imperial.ac.uk/news/articles/natural-sciences/life-sciences/2026/celebrating-25-years-of-the-flowers-building/',
      used_for: 'designed by Norman Foster & Partners, life sciences research building',
    },
    {
      title: 'Completed Campus Renewal Projects - Imperial College Centenary',
      url: 'https://imperial.ac.uk/Centenary/completed_campus_projects.shtml',
      used_for: 'opened December 2000, named after Lord Flowers',
    },
  ],
  notes:
    'No facade description was returned by searches (a search for terracotta louvres found none on this building); the aluminium-band / louvre elevation and rooftop flues follow Foster lab buildings of that period and are approximate. Main block 29.6 m (9 floors) and west wing 7.2 m from the Overture outline and part. Refinement: long elevations are built storey by storey - projecting aluminium spandrel panels with joints, recessed full-width glazing with mullions every 1.5 m and transoms - carrying external louvre blades (three slats each) on outrigger brackets; the ends are solid panel-clad with a recessed glazed stair slot; recessed glazed ground floor behind round columns with an entrance canopy; roof has a slatted plant enclosure, capped stainless flues on a gantry, cable trays, a lift overrun and guard rails; the west wing has mullioned glazing, an aluminium fascia and roof lights.',
  build({ THREE, kit, buildings, frame }) {
    const bld = buildings[0];
    const H = bld.h;
    const wing = ccw(
      bld.parts?.[0]?.polys?.[0]?.[0] ?? [
        [1547.2, -984.1],
        [1529.0, -986.4],
        [1529.6, -991.0],
        [1527.8, -991.2],
        [1529.8, -1006.5],
        [1549.5, -1004.0],
      ],
    );
    const main = ccw([
      [1549.5, -1004.0],
      [1590.4, -998.9],
      [1588.9, -987.4],
      [1585.2, -987.9],
      [1584.6, -983.6],
      [1547.7, -988.3],
      [1547.2, -984.1],
    ]);
    const wingH = bld.parts?.[0]?.h ?? 7.2;
    const b = new kit.MeshBatch();
    const alu = kit.mat('#c9ced1', { roughness: 0.4, metalness: 0.45 }),
      alu2 = kit.mat('#aeb5b9', { roughness: 0.45, metalness: 0.45 }),
      aluDark = kit.mat('#7d868b', { roughness: 0.45, metalness: 0.4 }),
      glass = kit.mat('#3e5462', { roughness: 0.08, metalness: 0.35 }),
      roofM = kit.roof('flat', 0),
      flueM = kit.mat('#c4c9cc', { roughness: 0.3, metalness: 0.6 });
    const storey = (H - 2.0) / 9;
    const panelM = kit.paintedMaterial('imperial_flowers_building:panel', 256, 128, (c, w, h) => {
      const r = kit.rng(0.3299);
      noiseFill(c, w, h, '#c9ced1', r, 0.03, 4);
      c.fillStyle = 'rgba(0,0,0,0.22)';
      for (let x = 0; x <= w; x += 64) c.fillRect(x, 0, 1.5, h); // panel joints every 1.5 m (tile 6 m)
      c.fillRect(0, h / 2, w, 1);
    });
    const endM = kit.paintedMaterial('imperial_flowers_building:endpanel', 256, 256, (c, w, h) => {
      const r = kit.rng(0.77);
      noiseFill(c, w, h, '#c3c8cb', r, 0.04, 4);
      c.fillStyle = 'rgba(0,0,0,0.14)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 1);
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 1, h);
    });
    const top = H - 2.0;
    const es = ringEdges(main);
    // Glazed, recessed ground floor behind round columns.
    const gIn = kit.offsetRing(main, -0.8);
    kit.walls(b, glass, [[gIn]], 0, storey);
    for (const e of ringEdges(gIn)) {
      const n = Math.max(1, Math.round(e.len / 1.5));
      for (let i = 0; i <= n; i++)
        boxOn(kit, b, aluDark, e, (i * e.len) / n, 0.04, 0, 0.07, 0.1, storey);
      boxOn(kit, b, aluDark, e, e.len / 2, 0.04, 2.7, e.len, 0.1, 0.08);
    }
    kit.cap(b, alu, [[main]], storey, { down: true });
    const col = new THREE.CylinderGeometry(0.25, 0.25, storey, 14).rotateX(Math.PI / 2);
    for (const e of es) {
      if (e.len < 10) continue;
      const n = Math.round(e.len / 7.2);
      for (let i = 0; i <= n; i++) {
        const p = pointOn(e, (i / n) * e.len, -0.4);
        b.addGeometry(alu2, col, new THREE.Matrix4().makeTranslation(p[0], p[1], storey / 2));
      }
    }
    col.dispose();
    // Upper floors.
    for (const e of es) {
      if (e.len > 14) {
        const holes = [];
        for (let k = 1; k < 9; k++)
          holes.push({
            t0: 0.3,
            t1: e.len - 0.3,
            zb: k * storey + storey * 0.36,
            zt: (k + 1) * storey - 0.05,
          });
        punchedWall(b, panelM, aluDark, e, storey, top, holes, {
          d: 0.35,
          tile: [6.0, storey * 2],
          uvBase: storey,
          back: glass,
        });
        const m = Math.max(1, Math.round((e.len - 0.6) / 1.5));
        for (const h of holes) {
          for (let i = 0; i <= m; i++)
            boxOn(
              kit,
              b,
              aluDark,
              e,
              h.t0 + (i * (h.t1 - h.t0)) / m,
              -0.3,
              h.zb,
              0.06,
              0.1,
              h.zt - h.zb,
            );
          boxOn(
            kit,
            b,
            aluDark,
            e,
            e.len / 2,
            -0.3,
            h.zb + (h.zt - h.zb) * 0.62,
            h.t1 - h.t0,
            0.1,
            0.06,
          );
          // spandrel panel cover strip
          boxOn(kit, b, alu, e, e.len / 2, 0.03, h.zb - 0.12, e.len, 0.06, 0.12);
        }
        // External horizontal louvre blades (three slats) on outrigger brackets, per floor.
        for (let k = 1; k < 9; k++) {
          const z = storey * (k + 0.97);
          for (let s = 0; s < 3; s++) {
            const o = 0.25 + s * 0.32;
            const L = e.len - 1.2;
            const mid = pointOn(e, e.len / 2, o + 0.13);
            kit.box(b, alu2, mid[0], mid[1], z + s * 0.03, L, 0.26, 0.04, e.ang);
          }
        }
        const nb = Math.round(e.len / 3.6);
        for (let i = 1; i < nb; i++)
          for (let k = 1; k < 9; k++) {
            const p = pointOn(e, (i * e.len) / nb, 0.6);
            kit.box(b, aluDark, p[0], p[1], storey * (k + 0.97) - 0.1, 0.08, 1.2, 0.18, e.ang);
          }
        finsAlong(kit, b, alu2, e, storey, top, 7.2, 1.25, 0.1);
      } else {
        // Solid clad ends with a recessed glazed stair slot.
        const holes =
          e.len > 6
            ? [{ t0: e.len * 0.42, t1: e.len * 0.58, zb: storey + 0.3, zt: top - 0.3 }]
            : [];
        punchedWall(b, endM, aluDark, e, storey, top, holes, {
          d: 0.4,
          tile: [Math.max(4, e.len), Math.max(4, e.len)],
          uvBase: storey,
          back: glass,
        });
        for (const h of holes)
          for (let k = 1; k < 9; k++)
            boxOn(
              kit,
              b,
              aluDark,
              e,
              (h.t0 + h.t1) / 2,
              -0.35,
              k * storey + 0.3,
              h.t1 - h.t0,
              0.1,
              0.08,
            );
      }
    }
    for (let k = 1; k <= 9; k++)
      kit.cornice(b, alu, main, k * storey - 0.08, { height: 0.08, projection: 0.06 });
    // Roof: plant enclosure clad in louvres, flues on a gantry, cable trays and rails.
    kit.cap(b, roofM, [[main]], top);
    parapet(kit, b, alu, main, top, 0.9, 0.25);
    const ex = kit.orientedExtent(main, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const um = (ex.u0 + ex.u1) / 2,
      vm = (ex.v0 + ex.v1) / 2;
    const pc = at(um + 1, vm);
    louvreBox(
      kit,
      b,
      aluDark,
      alu2,
      pc[0],
      pc[1],
      top,
      ex.u1 - ex.u0 - 10,
      7.5,
      4.0,
      frame.angle,
      0.22,
    );
    const n = 10;
    for (let i = 0; i < n; i++) {
      const p = at(ex.u0 + 6 + (i * (ex.u1 - ex.u0 - 12)) / (n - 1), vm);
      flue(THREE, b, flueM, p[0], p[1], top + 4.18, 4.0, 0.4);
    }
    for (const dv of [-0.9, 0.9]) {
      const p = at(um, vm + dv);
      kit.box(b, aluDark, p[0], p[1], top + 5.2, ex.u1 - ex.u0 - 11, 0.12, 0.12, frame.angle);
    }
    for (const dv of [-3.2, 3.2]) {
      const p = at(um, vm + dv);
      kit.box(b, aluDark, p[0], p[1], top + 0.3, ex.u1 - ex.u0 - 12, 0.6, 0.12, frame.angle);
    }
    const lm = at(ex.u1 - 3.5, vm + 1.5);
    kit.box(b, alu, lm[0], lm[1], top, 3.5, 4.0, 5.2, frame.angle);
    roofRail(kit, b, alu2, main, top, 0.7, 1.1);
    // West wing: mullioned glazed pavilion with an aluminium fascia and roof lights.
    const wr = ringEdges(wing);
    kit.walls(b, glass, [[kit.offsetRing(wing, -0.02)]], 0, wingH - 0.8);
    for (const e of wr) {
      const m = Math.max(1, Math.round(e.len / 1.8));
      for (let i = 0; i <= m; i++)
        boxOn(kit, b, aluDark, e, (i * e.len) / m, 0.03, 0, 0.08, 0.12, wingH - 0.8);
      boxOn(kit, b, aluDark, e, e.len / 2, 0.03, (wingH - 0.8) / 2, e.len, 0.1, 0.1);
      boxOn(kit, b, aluDark, e, e.len / 2, 0.03, 0, e.len, 0.12, 0.12);
    }
    kit.walls(b, alu, [[kit.offsetRing(wing, 0.15)]], wingH - 0.8, wingH);
    kit.cap(b, roofM, [[kit.offsetRing(wing, 0.15)]], wingH);
    const wf = kit.ringFrame(wing);
    for (let i = -1; i <= 1; i++) {
      const p = [wf.cx + i * 5 * Math.cos(wf.angle), wf.cy + i * 5 * Math.sin(wf.angle)];
      kit.box(b, aluDark, p[0], p[1], wingH, 2.4, 6, 0.4, wf.angle);
      kit.box(b, glass, p[0], p[1], wingH + 0.4, 2.2, 5.8, 0.25, wf.angle);
    }
    // Entrance canopy on the south side (Frankland Road) of the main block.
    const south = es.slice().sort((p, q) => p.ny - q.ny)[0];
    boxOn(kit, b, alu, south, south.len * 0.35, 1.6, storey - 0.4, 6, 3.2, 0.25);
    boxOn(kit, b, kit.mat('#1d262c'), south, south.len * 0.35, -0.75, 0, 3.2, 0.06, 2.6);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_flowers_building'));
    return g;
  },
};
