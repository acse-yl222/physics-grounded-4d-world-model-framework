// Sir Ernst Chain Building - Wolfson Laboratories, Imperial College (built 1962-5 by
// Architects' Co-Partnership as the Biochemistry range; renamed 2012 after the
// Nobel laureate who founded the department). Seven-storey laboratory block on
// Imperial College Road: a rhythm of projecting precast concrete mullions framing
// tall dark-glazed bays with dark spandrel panels, brick end walls, a set-back
// glazed entrance floor and rooftop plant / extract stacks.
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
  id: 'imperial_sir_ernst_chain',
  name: 'Sir Ernst Chain Building - Wolfson Laboratories',
  claims: ['e7b8d92c-ea3c-4dac-aabb-b548d6b05f07'],
  references: [
    {
      title: 'Sir Ernst Chain is honoured in building naming ceremony - Imperial News',
      url: 'https://www.imperial.ac.uk/news/115787/sir-ernst-chain-honoured-building-naming/',
      used_for: 'building identity, 2012 renaming of the biochemistry building',
    },
    {
      title: 'plate 76 - Survey of London vol 38 (Imperial College in 1973)',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for: 'Biochemistry range 1962-5 by Architects Co-Partnership',
    },
    {
      title: 'Royal College of Science - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_College_of_Science',
      used_for:
        'the western wing of the Webb building was demolished in 1961 for the new biochemistry building on this site',
    },
  ],
  notes:
    'No facade description found; elevation (concrete mullion fins, dark spandrels, brick ends) is a reconstruction in the 1960s ACP idiom, not traced from photos. Height 23.2 m from Overture (7 floors). Refinement: each 1.6 m bay is a real recessed opening with an aluminium-framed window (centre mullion, transom, opening light) over a recessed dark spandrel panel, between full-height projecting precast fins and floor-edge beams; plain brick returns; the set-back ground floor has a mullioned glazed screen behind columns under the fins, an entrance canopy with a name sign (wording from the 2012 naming, placement assumed) and steps; the roof has a brick plant room with louvre bands, lift motor room, capped extract flues on a frame and guard rails.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 3.8,
      storey = (H - 1.0 - gf) / 6;
    const b = new kit.MeshBatch();
    const conc = kit.mat('#d3cec3'),
      conc2 = kit.mat('#c6c0b3'),
      brick = kit.mat('#8d6450'),
      roofM = kit.roof('flat', 2),
      flueM = kit.mat('#aab0b4', { roughness: 0.5, metalness: 0.4 }),
      glass = kit.mat('#2a3740', { roughness: 0.1, metalness: 0.3 }),
      spandrel = kit.mat('#454b4f', { roughness: 0.6 }),
      alu = kit.mat('#9ea5a9', { roughness: 0.45, metalness: 0.4 }),
      darkAlu = kit.mat('#3f4549', { roughness: 0.45, metalness: 0.4 }),
      paving = kit.mat('#b8b1a3');
    const brickM = kit.paintedMaterial('imperial_sir_ernst_chain:brick', 256, 256, (c, w, h) => {
      const r = kit.rng(0.5524);
      brickCourses(c, w, h, r, '#8d6450', 3);
    });
    const concM = kit.paintedMaterial('imperial_sir_ernst_chain:conc', 256, 256, (c, w, h) => {
      const r = kit.rng(0.5525);
      noiseFill(c, w, h, '#d3cec3', r, 0.08, 3);
    });
    const es = ringEdges(ring);
    const north = es.filter((e) => e.len > 20).sort((p, q) => q.ny - p.ny)[0];
    // Ground floor set back 1 m: mullioned glazed screen.
    const inner = kit.offsetRing(ring, -1.0);
    for (const e of ringEdges(inner)) {
      boxOn(kit, b, glass, e, e.len / 2, -0.02, 0, e.len, 0.04, gf);
      const n = Math.max(1, Math.round(e.len / 1.6));
      for (let i = 0; i <= n; i++)
        boxOn(kit, b, darkAlu, e, (i * e.len) / n, 0.04, 0, 0.07, 0.12, gf);
      boxOn(kit, b, darkAlu, e, e.len / 2, 0.04, 2.5, e.len, 0.1, 0.08);
      boxOn(kit, b, spandrel, e, e.len / 2, 0.03, 2.6, e.len, 0.05, gf - 2.6);
    }
    kit.cap(b, conc, [[ring]], gf, { down: true });
    paved(kit, b, paving, ring, 0.03);
    const top = H - 1.0;
    for (const e of es) {
      if (e.len <= 8) {
        wallQuad(b, brickM, e.a, e.b, gf, top, { bay: 3.6, storey: 3.6 });
        continue;
      }
      // Bays of 1.6 m between fins; each storey one recessed opening per bay.
      const nb = Math.max(2, Math.round(e.len / 1.6));
      const bw = e.len / nb;
      const holes = [];
      for (let k = 0; k < 6; k++)
        for (let i = 0; i < nb; i++)
          holes.push({
            t0: i * bw + 0.16,
            t1: (i + 1) * bw - 0.16,
            zb: gf + k * storey + 0.25,
            zt: gf + (k + 1) * storey - 0.1,
            k: i,
          });
      punchedWall(b, concM, conc2, e, gf, top, holes, {
        d: 0.3,
        tile: [7.2, 7.2],
        uvBase: gf,
        back: glass,
      });
      for (const h of holes) {
        const w = h.t1 - h.t0,
          tm = (h.t0 + h.t1) / 2,
          hh = h.zt - h.zb;
        // dark spandrel panel in the lower third, window above
        boxOn(kit, b, spandrel, e, tm, -0.26, h.zb, w, 0.06, hh * 0.3);
        boxOn(kit, b, alu, e, tm, -0.24, h.zb + hh * 0.3, w, 0.1, 0.07);
        boxOn(kit, b, alu, e, tm, -0.24, h.zb + hh * 0.3, 0.06, 0.1, hh * 0.7);
        boxOn(kit, b, alu, e, tm, -0.24, h.zb + hh * 0.78, w, 0.08, 0.05);
        for (const s of [-1, 1])
          boxOn(
            kit,
            b,
            alu,
            e,
            tm + s * (w / 2 - 0.03),
            -0.24,
            h.zb + hh * 0.3,
            0.06,
            0.1,
            hh * 0.7,
          );
        boxOn(kit, b, alu, e, tm, -0.24, h.zt - 0.06, w, 0.1, 0.06);
      }
      // Projecting precast mullion fins every two bays, full height of the upper floors.
      for (let i = 0; i <= nb; i += 2) {
        const p = pointOn(e, Math.min(e.len, i * bw), 0.22);
        kit.box(b, conc, p[0], p[1], 0, 0.32, 0.45, top + 0.2, e.ang);
      }
      // floor-edge beams
      for (let k = 0; k <= 6; k++) barAlong(kit, b, conc, e, gf + k * storey - 0.12, 0.22, 0.25);
      barAlong(kit, b, conc, e, gf - 0.5, 0.5, 0.5);
    }
    parapet(kit, b, conc, ring, top, 1.0, 0.3);
    kit.cornice(b, conc2, ring, H - 0.05, { height: 0.08, projection: 0.06 });
    kit.cap(b, roofM, [[ring]], top + 0.01);
    // Entrance canopy and name sign on Imperial College Road.
    {
      const e = north;
      const t = e.len * 0.5;
      boxOn(kit, b, conc, e, t, 1.2, 3.1, 7.2, 3.4, 0.3);
      boxOn(kit, b, darkAlu, e, t, 2.9, 3.05, 7.3, 0.08, 0.4);
      const sign = signMaterial(kit, 'imperial_sir_ernst_chain:sign', 'SIR ERNST CHAIN BUILDING', {
        bg: '#14324f',
        font: 'bold 30px sans-serif',
      });
      boxOn(kit, b, sign, e, t, 2.95, 3.1, 6.2, 0.03, 0.28);
      boxOn(kit, b, kit.mat('#1a2228'), e, t, -0.95, 0, 3.4, 0.05, 2.5);
      for (const s of [-1, 0, 1])
        boxOn(kit, b, darkAlu, e, t + s * 0.85, -0.92, 0, 0.06, 0.08, 2.5);
      stepsOn(kit, b, conc2, e, t, 7.0, 1, { rise: 0.12, tread: 2.6 });
    }
    // Rooftop plant room, lift motor room and extract stacks.
    const ex = kit.orientedExtent(ring, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const pr = at((ex.u0 + ex.u1) / 2 - 3, (ex.v0 + ex.v1) / 2);
    kit.box(b, brick, pr[0], pr[1], H - 1, 18, 7, 4.2, frame.angle);
    kit.box(b, conc, pr[0], pr[1], H + 3.2, 18.4, 7.4, 0.3, frame.angle);
    louvreBox(kit, b, darkAlu, alu, pr[0], pr[1], H - 0.2, 18.2, 7.2, 1.6, frame.angle, 0.2);
    const lm = at(ex.u1 - 6, (ex.v0 + ex.v1) / 2 + 2);
    kit.box(b, brick, lm[0], lm[1], H - 1, 4.5, 5, 5.5, frame.angle);
    kit.box(b, conc, lm[0], lm[1], H + 4.5, 4.8, 5.3, 0.25, frame.angle);
    for (let i = 0; i < 8; i++) {
      const p = at(ex.u0 + 6 + i * 3, ex.v1 - 2.5);
      flue(THREE, b, flueM, p[0], p[1], H - 1, 6.2, 0.3);
    }
    for (const dv of [-0.7, 0.7]) {
      const p = at(ex.u0 + 16.5, ex.v1 - 2.5 + dv);
      kit.box(b, darkAlu, p[0], p[1], H + 2.4, 23, 0.1, 0.1, frame.angle);
    }
    roofRail(kit, b, alu, ring, top, 0.8, 1.1);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_sir_ernst_chain'));
    if (placeAssets) {
      const pl = [];
      for (let i = 0; i < 4; i++) {
        const p = pointOn(north, north.len * 0.72 + i * 1.2, 2.0);
        pl.push([p[0], p[1], north.ang + Math.PI / 2]);
      }
      g.add(placeAssets('bicycle_stand', pl));
    }
    return g;
  },
};
