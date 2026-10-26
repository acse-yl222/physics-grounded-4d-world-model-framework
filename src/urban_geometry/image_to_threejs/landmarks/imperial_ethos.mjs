// Ethos sports centre, Imperial College (Arup Associates, opened 2006) on the
// north side of Prince's Gardens: four storeys above a deck-level 25 m pool and
// sports hall. Modelled as a pale stone-clad volume whose front to the gardens is
// a full-height glazed curtain wall (gym and studio floors visible behind slim
// mullions and floor-edge bands) under a thin projecting roof canopy, with an
// entrance canopy, solid flank walls with vertical slot windows and rooftop plant.
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
  id: 'imperial_ethos',
  name: 'Ethos Sport Imperial',
  claims: ['5151acb6-c3ca-482d-87f5-ef659ace6ca7'],
  references: [
    {
      title: 'Visit the Ethos website - Imperial Sport (South Kensington facilities)',
      url: 'https://www.imperial.ac.uk/admin-services/sport/facilities/south-kensington/',
      used_for:
        "four-storey facility on the north side of Prince's Gardens with a 25 m deck-level pool",
    },
    {
      title: 'Imperial College starts work on sports centre - Leisure Opportunities',
      url: 'https://leisureopportunities.co.uk/news/Imperial-College-starts-work-on-sports-centre/8548',
      used_for:
        'designed by Arup Associates to blend with surrounding architecture; built on the 1960s underground sports centre; pool in the basement, sports hall, squash courts, gym; top two floors residential accommodation for visiting academics; artwork on the facade',
    },
    {
      title:
        'Boris Johnson opens restored London square after £160m investment by Imperial College London',
      url: 'https://www.imperial.ac.uk/news/80641/boris-johnson-opens-restored-london-square/',
      used_for: "sports centre as part of the Prince's Gardens redevelopment",
    },
  ],
  notes:
    'No facade description was found by search; the glazed south front, stone flanks and canopies are approximate. Height 17.2 m from Overture. Refinement: the south front is a real curtain wall over the two sports floors (mullions every 1.5 m, transoms, spandrel bands, gym interior painted behind the glass) set in a stone frame, while the top two (residential) floors - per the Leisure Opportunities brief - are stone-clad with recessed paired windows and aluminium frames; entrance canopy on slim columns with glazed doors and an ETHOS fascia sign, a coloured-glass artwork strip (the brief mentions facade artwork; its form is not known), slot windows in reveals on the flanks, louvred plant enclosure, roof rail, and a paved forecourt with cycle stands and bollards.',
  build({ THREE, kit, buildings, placeAssets }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      storey = (H - 1.0) / 4;
    const b = new kit.MeshBatch();
    const stone = kit.mat('#ddd5c1'),
      stone2 = kit.mat('#d2c9b3'),
      alu = kit.mat('#c8ccce', { roughness: 0.45, metalness: 0.4 }),
      darkAlu = kit.mat('#4b5257', { roughness: 0.45, metalness: 0.4 }),
      roofM = kit.roof('flat', 2),
      dark = kit.mat('#3a4247'),
      glass = kit.mat('#2f3e48', { roughness: 0.1, metalness: 0.3 }),
      paving = kit.mat('#bfb8aa'),
      slab = kit.mat('#a9a296');
    const interior = kit.paintedMaterial(
      'imperial_ethos:interior',
      512,
      256,
      (c, w, h) => {
        const r = kit.rng(0.2006);
        for (let j = 0; j < 2; j++) {
          const y = j * (h / 2);
          const grd = c.createLinearGradient(0, y, 0, y + h / 2);
          grd.addColorStop(0, '#6f8796');
          grd.addColorStop(0.7, '#4c6170');
          grd.addColorStop(1, '#3a4a55');
          c.fillStyle = grd;
          c.fillRect(0, y, w, h / 2);
          c.fillStyle = 'rgba(240,235,210,0.4)';
          for (let i = 0; i < 8; i++) c.fillRect(i * 64 + 12, y + 8, 40, 3);
          c.fillStyle = 'rgba(30,30,35,0.55)';
          for (let i = 0; i < 10; i++)
            if (r() < 0.6) c.fillRect(i * 51 + r() * 20, y + h / 2 - 34, 18 + r() * 14, 26);
        }
        c.fillStyle = 'rgba(255,255,255,0.1)';
        for (let i = 0; i < 8; i++) c.fillRect(i * 64 + 6, 0, 18, h);
      },
      { roughness: 0.2, metalness: 0.1 },
    );
    const flank = kit.paintedMaterial('imperial_ethos:stone', 256, 256, (c, w, h) => {
      const r = kit.rng(0.3006);
      noiseFill(c, w, h, '#ddd5c1', r, 0.05, 4);
      c.fillStyle = 'rgba(110,100,80,0.2)';
      for (let y = 0; y < h; y += 21) c.fillRect(0, y, w, 1); // 0.6 m courses on a 7.2 m tile
      for (let y = 0, k = 0; y < h; y += 21, k++)
        for (let x = k % 2 ? 0 : 21; x < w; x += 42) c.fillRect(x, y, 1, 21);
    });
    const art = kit.paintedMaterial('imperial_ethos:art', 512, 32, (c, w, h) => {
      const r = kit.rng(0.4006);
      const cols = ['#d0573a', '#e7a83a', '#3c8fb0', '#5ea65a', '#e8e0cf', '#21486b'];
      for (let x = 0; x < w;) {
        const ww = 6 + r() * 26;
        c.fillStyle = cols[Math.floor(r() * cols.length)];
        c.fillRect(x, 0, ww, h);
        x += ww;
      }
    });
    const es = ringEdges(ring);
    const isFront = (e) => e.ny < -0.8 && e.len > 20;
    const top = H - 1.0;
    const z2 = 2 * storey; // residential floors above
    for (const e of es) {
      if (isFront(e)) {
        // Sports floors: curtain wall set 0.4 m behind the stone frame.
        const hole = { t0: 1.2, t1: e.len - 1.2, zb: 0, zt: z2 - 0.6, d: 0.45, back: false };
        // Residential floors: paired windows.
        const n = Math.round((e.len - 2.4) / 3.0);
        const holes = [hole];
        for (let s = 0; s < 2; s++) {
          const zb = z2 + s * storey + 0.75;
          for (const h of bayHoles(e, n, 1.7, zb, zb + storey - 1.25, { margin: 1.2 }))
            holes.push({ ...h, s });
        }
        punchedWall(b, flank, stone2, e, 0, top, holes, { d: 0.3, tile: [7.2, 7.2], back: glass });
        // interior seen through the glass
        boxOn(kit, b, interior, e, e.len / 2, -0.46, 0, e.len - 2.4, 0.02, z2 - 0.6);
        const m = Math.round((e.len - 2.4) / 1.5);
        for (let i = 0; i <= m; i++)
          boxOn(
            kit,
            b,
            alu,
            e,
            1.2 + (i * (e.len - 2.4)) / m,
            -0.35,
            0,
            i % 4 ? 0.06 : 0.12,
            i % 4 ? 0.2 : 0.35,
            z2 - 0.6,
          );
        for (const z of [0, 2.8, storey, storey + 2.8, z2 - 0.75])
          boxOn(kit, b, alu, e, e.len / 2, -0.38, z, e.len - 2.4, 0.14, z === storey ? 0.5 : 0.08);
        // artwork strip at first-floor level
        boxOn(kit, b, art, e, e.len / 2, -0.41, storey + 0.5, e.len - 2.4, 0.02, 0.8);
        for (const h of holes.slice(1)) {
          fitWindow(kit, b, e, h, { d: 0.3, glass, frame: darkAlu, sill: alu, bars: 0 });
          boxOn(
            kit,
            b,
            darkAlu,
            e,
            (h.t0 + h.t1) / 2,
            -0.22,
            h.zb + (h.zt - h.zb) * 0.75,
            h.t1 - h.t0,
            0.06,
            0.05,
          );
          boxOn(kit, b, darkAlu, e, (h.t0 + h.t1) / 2, -0.22, h.zb, 0.1, 0.08, h.zt - h.zb); // pair mullion
          boxOn(
            kit,
            b,
            kit.mat('#566b77', { roughness: 0.1, metalness: 0.3 }),
            e,
            (h.t0 + h.t1) / 2,
            -0.08,
            h.zb + 0.02,
            h.t1 - h.t0 - 0.04,
            0.02,
            0.95,
          ); // glass Juliet balustrade
          boxOn(
            kit,
            b,
            alu,
            e,
            (h.t0 + h.t1) / 2,
            -0.08,
            h.zb + 0.97,
            h.t1 - h.t0 - 0.04,
            0.05,
            0.05,
          );
          boxOn(
            kit,
            b,
            alu,
            e,
            (h.t0 + h.t1) / 2,
            0.04,
            h.zb - 0.08,
            h.t1 - h.t0 + 0.12,
            0.12,
            0.08,
          );
        }
        // stone frame: projecting jambs, floor band and a thin projecting roof canopy
        for (const t of [0.6, e.len - 0.6]) boxOn(kit, b, stone, e, t, 0.2, 0, 1.2, 0.4, H);
        boxOn(kit, b, stone, e, e.len / 2, 0.15, z2 - 0.6, e.len, 0.3, 0.6);
        barAlong(kit, b, alu, e, H - 0.2, 0.25, 2.4, -0.6);
        // Entrance canopy and doors towards the west end.
        const t = e.len * 0.3;
        boxOn(kit, b, alu, e, t, 2.0, 3.6, 9, 4.0, 0.35);
        boxOn(kit, b, darkAlu, e, t, 3.98, 3.55, 9, 0.06, 0.45);
        for (const s of [-1, 1]) boxOn(kit, b, darkAlu, e, t + s * 4.2, 3.6, 0, 0.18, 0.18, 3.6);
        boxOn(kit, b, dark, e, t, -0.5, 0, 5, 0.05, 2.8);
        for (let i = -2; i <= 2; i++)
          boxOn(kit, b, darkAlu, e, t + i * 1.25, -0.47, 0, 0.08, 0.08, 2.8);
        const sign = signMaterial(kit, 'imperial_ethos:sign', 'ETHOS', {
          bg: '#0b3b66',
          font: 'bold 44px sans-serif',
          w: 256,
          h: 64,
        });
        boxOn(kit, b, sign, e, t, 4.03, 3.62, 2.6, 0.03, 0.4);
        paved(kit, b, paving, edgeRect(e, -1, e.len + 1, 0, 6.5), 0.05);
        for (let i = 0; i < 14; i++)
          boxOn(kit, b, slab, e, 2 + i * ((e.len - 4) / 13), 6.55, 0, 0.6, 0.6, 0.06);
        e.front = true;
        continue;
      }
      // Flanks / rear: stone with tall slot windows in deep reveals.
      if (e.len < 4) {
        wallQuad(b, flank, e.a, e.b, 0, top, { bay: 3.6, storey: 3.6 });
        continue;
      }
      const n = Math.max(1, Math.round(e.len / 4.0));
      const holes = [];
      for (let s = 0; s < 4; s++)
        for (const h of bayHoles(e, n, 0.7, s * storey + 0.9, (s + 1) * storey - 0.5, {
          margin: 1.0,
        }))
          holes.push(h);
      punchedWall(b, flank, stone2, e, 0, top, holes, { d: 0.35, tile: [7.2, 7.2], back: glass });
      for (const h of holes)
        fitWindow(kit, b, e, h, { d: 0.35, glass, frame: darkAlu, sill: alu, bars: 0 });
      for (let s = 1; s < 4; s++)
        boxOn(kit, b, stone, e, e.len / 2, 0.04, s * storey - 0.15, e.len, 0.08, 0.15);
    }
    parapet(kit, b, stone, ring, H - 1.0, 1.0, 0.4);
    kit.cornice(b, alu, ring, H - 0.06, { height: 0.06, projection: 0.05 });
    kit.cap(b, roofM, [[ring]], H - 0.99);
    // Rooftop plant enclosure (pool hall air handling) and roof rail.
    const fr = kit.ringFrame(ring);
    const ex = kit.orientedExtent(ring, fr.angle);
    const pc = ex.at((ex.u0 + ex.u1) / 2, (ex.v0 + ex.v1) / 2, 0);
    const louvre = kit.mat('#9da3a6', { roughness: 0.5, metalness: 0.3 });
    louvreBox(kit, b, darkAlu, louvre, pc[0], pc[1], H - 1.0, 18, 10, 3.0, fr.angle, 0.25);
    for (let i = 0; i < 4; i++) {
      const p = ex.at((ex.u0 + ex.u1) / 2 - 6 + i * 4, (ex.v0 + ex.v1) / 2, 0);
      flue(THREE, b, alu, p[0], p[1], H + 2.18, 1.4, 0.4);
    }
    const lp = ex.at(ex.u0 + 6, ex.v1 - 5, 0);
    kit.box(b, stone2, lp[0], lp[1], H - 1.0, 4, 5, 3.6, fr.angle);
    kit.box(b, stone, lp[0], lp[1], H + 2.6, 4.3, 5.3, 0.25, fr.angle);
    roofRail(kit, b, alu, ring, H - 1.0, 1.0, 1.1);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_ethos'));
    if (placeAssets) {
      const e = es.find((x) => x.front);
      if (e) {
        const st = [],
          bo = [];
        for (let i = 0; i < 6; i++) {
          const p = pointOn(e, e.len * 0.55 + i * 1.1, 4.5);
          st.push([p[0], p[1], e.ang + Math.PI / 2]);
        }
        for (let i = 0; i < 6; i++) {
          const p = pointOn(e, e.len * 0.3 - 5 + i * 2, 6.2);
          bo.push([p[0], p[1], e.ang]);
        }
        g.add(placeAssets('bicycle_stand', st));
        g.add(placeAssets('bollard', bo));
      }
    }
    return g;
  },
};
