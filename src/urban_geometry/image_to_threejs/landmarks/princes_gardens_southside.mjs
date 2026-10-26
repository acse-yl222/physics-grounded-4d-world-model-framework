// Southside halls of residence, Prince's Gardens (Kohn Pedersen Fox, opened 2007):
// Falmouth, Tizard, Selkirk and Keogh halls, 413 beds, replacing the 1963 Sheppard
// Robson concrete halls. A material palette of limestone, brick and stucco
// references the 19th-century terraces: the six-storey limestone front to the
// gardens repeats the terraces' regular vertical window rhythm over a glazed base,
// with recessed glazed joints between the halls and a dark metal attic; the rear
// elevations to the mews step back in bays of buff brick.
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

const IDS = {
  falmouth: 'a4244b77-ceb5-4377-a646-a94e5cdb2714',
  tizard: 'bfe3f43c-485d-44aa-a567-466a40f90f7f',
  selkirk: 'deec4af8-7758-4763-9054-71f24a5cb25d',
  keogh: '2b426de4-4776-4699-a31a-fb99683996d8',
};

export default {
  id: 'princes_gardens_southside',
  name: "Southside Halls, Prince's Gardens (Imperial College)",
  claims: Object.values(IDS),
  references: [
    {
      title: 'princes gardens redevelopment - KPF',
      url: 'https://www.kpf.com/project/princes-gardens-redevelopment',
      used_for:
        'limestone / brick / stucco palette, front elevation echoing terrace fenestration, stepped rear bays, two storeys lower than the 1960s blocks',
    },
    {
      title: 'Imperial College Halls of Residence - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Imperial_College_Halls_of_Residence',
      used_for:
        'Southside = four halls (Falmouth, Keogh, Selkirk, Tizard), 413 beds, opened October 2007; 1963 Sheppard Robson predecessor',
    },
    {
      title: 'Eastside Update - Imperial News',
      url: 'https://www.imperial.ac.uk/news/29454/eastside-update/',
      used_for: 'Southside and Eastside both designed by Kohn Pedersen Fox',
    },
    {
      title:
        'Boris Johnson opens restored London square after £160m investment by Imperial College London',
      url: 'https://imperial.ac.uk/news/80641/boris-johnson-opens-restored-london-square',
      used_for: 'new blocks sit lower than their predecessors, in line with the adjacent terraces',
    },
    {
      title: 'Southside Halls, Imperial College - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101250855-southside-halls-imperial-college-knightsbridge-and-belgravia-ward',
      used_for: 'the listed 1960-63 board-marked concrete predecessor (not modelled; context only)',
    },
  ],
  notes:
    'Window grid, glazed joints and attic treatment are inferred from the KPF description, not traced from photos. Front halls 20 m from Overture; Keogh (rear range) kept at its Overture 7.2 m with a set-back upper storey, which may understate it. Refinement: limestone garden fronts with real recessed vertical windows (aluminium frames, transom, glass Juliet balustrades, stone sills) in the terrace rhythm, projecting stone piers, string course over a glazed base of recessed shopfront-like windows and an entrance with canopy and steps per hall, recessed full-height glazed joints with mullions, zinc attic with standing seams and punched windows, stone cornice; the stepped buff-brick rear bays and Keogh have punched windows; roof overruns, plant louvres and guard rails; paved strip with benches along the gardens.',
  build({ THREE, kit, byId, placeAssets }) {
    const b = new kit.MeshBatch();
    const stone = kit.mat('#e2dccb'),
      stone2 = kit.mat('#d7d0bd'),
      zinc = kit.mat('#5c6266', { roughness: 0.55, metalness: 0.3 }),
      roofM = kit.roof('flat', 0),
      glass = kit.mat('#2e3d48', { roughness: 0.1, metalness: 0.3 }),
      frameM = kit.mat('#6d7478', { roughness: 0.45, metalness: 0.4 }),
      juliet = kit.mat('#5d727e', { roughness: 0.1, metalness: 0.3 }),
      white = kit.mat('#ece9e1'),
      paving = kit.mat('#c2bbad'),
      doorM = kit.mat('#1b2328');
    const gf = 3.6;
    const stoneM = kit.paintedMaterial('princes_gardens_southside:stone', 256, 256, (c, w, h) => {
      const r = kit.rng(0.2008);
      noiseFill(c, w, h, '#e2dccb', r, 0.05, 4);
      c.fillStyle = 'rgba(120,110,90,0.18)';
      for (let y = 0; y < h; y += 21) c.fillRect(0, y, w, 1);
      for (let y = 0, k = 0; y < h; y += 21, k++)
        for (let x = k % 2 ? 0 : 32; x < w; x += 64) c.fillRect(x, y, 1, 21);
    });
    const brickM = kit.paintedMaterial('princes_gardens_southside:brick', 256, 256, (c, w, h) => {
      const r = kit.rng(0.3008);
      brickCourses(c, w, h, r, '#b9a27c', 3);
    });
    const zincM = kit.paintedMaterial('princes_gardens_southside:zinc', 128, 128, (c, w, h) => {
      const r = kit.rng(0.5008);
      noiseFill(c, w, h, '#5c6266', r, 0.05, 4);
      c.fillStyle = 'rgba(255,255,255,0.12)';
      for (let x = 0; x < w; x += 11) c.fillRect(x, 0, 1.5, h);
    });
    const front = (e) => e.ny > 0.8 && e.len > 10;
    const fronts = [];
    const brickBays = (e, z0, z1, storeys) => {
      const n = Math.max(1, Math.round(e.len / 3.4));
      const holes = [];
      const sh = (z1 - z0) / storeys;
      for (let s = 0; s < storeys; s++)
        for (const h of bayHoles(
          e,
          n,
          Math.min(1.2, e.len - 0.9),
          z0 + s * sh + 0.8,
          z0 + (s + 1) * sh - 0.4,
        ))
          holes.push(h);
      punchedWall(b, brickM, stone2, e, z0, z1, holes, {
        d: 0.22,
        tile: [7.2, 7.2],
        uvBase: z0,
        back: glass,
      });
      for (const h of holes) {
        fitWindow(kit, b, e, h, { d: 0.22, glass, frame: white, sill: white, bars: 0 });
        boxOn(kit, b, white, e, (h.t0 + h.t1) / 2, -0.15, h.zb, 0.06, 0.06, h.zt - h.zb);
        boxOn(kit, b, stone, e, (h.t0 + h.t1) / 2, 0.04, h.zb - 0.1, h.t1 - h.t0 + 0.2, 0.12, 0.1);
      }
    };
    const atticBays = (ring, z0, z1) => {
      for (const e of ringEdges(ring)) {
        if (e.len < 2.2) {
          wallQuad(b, zincM, e.a, e.b, z0, z1, { bay: 1.5, storey: 1.5 });
          continue;
        }
        const n = Math.max(1, Math.round(e.len / 3.4));
        const holes = bayHoles(e, n, Math.min(1.4, e.len - 0.9), z0 + 0.8, z1 - 0.6);
        punchedWall(b, zincM, zinc, e, z0, z1, holes, {
          d: 0.2,
          tile: [3, 3],
          uvBase: z0,
          back: glass,
        });
        for (const h of holes)
          fitWindow(kit, b, e, h, { d: 0.2, glass, frame: frameM, sill: frameM, bars: 0 });
      }
    };
    for (const key of ['falmouth', 'tizard', 'selkirk']) {
      const bld = byId[IDS[key]];
      if (!bld) continue;
      const ring = ccw(bld.polys[0][0]);
      const H = bld.h,
        attic = H - 3.1,
        storey = (attic - gf) / 4;
      for (const e of ringEdges(ring)) {
        if (!front(e)) {
          if (e.len < 2.2) wallQuad(b, brickM, e.a, e.b, 0, attic, { bay: 3.6, storey: 3.6 });
          else {
            brickBays(e, 0, gf, 1);
            brickBays(e, gf, attic, 4);
          }
          continue;
        }
        fronts.push(e);
        // Glazed joint at the west end of each hall's front.
        const joint = 2.0;
        const L = e.len - joint;
        const n = Math.max(2, Math.round(L / 3.4));
        const bw = L / n;
        const te = joint + Math.floor(n / 2) * bw + bw / 2;
        const gh = [
          { t0: 0.15, t1: joint - 0.15, zb: 0, zt: attic - 0.2, d: 0.8, back: false, joint: true },
        ];
        for (let i = 0; i < n; i++) {
          const t = joint + (i + 0.5) * bw;
          if (Math.abs(t - te) < 0.1)
            gh.push({ t0: t - 1.2, t1: t + 1.2, zb: 0.15, zt: gf - 0.5, d: 0.45, door: true });
          else gh.push({ t0: t - 1.15, t1: t + 1.15, zb: 0.5, zt: gf - 0.5, d: 0.35 });
        }
        punchedWall(
          b,
          stoneM,
          stone2,
          e,
          0,
          gf,
          gh.map((h) => (h.joint ? { ...h, zt: gf } : h)),
          { d: 0.35, tile: [7.2, 7.2], back: glass },
        );
        const holes = [{ ...gh[0], zb: gf }];
        for (let s = 0; s < 4; s++)
          for (let i = 0; i < n; i++) {
            const t = joint + (i + 0.5) * bw;
            holes.push({
              t0: t - 0.62,
              t1: t + 0.62,
              zb: gf + s * storey + 0.5,
              zt: gf + (s + 1) * storey - 0.35,
            });
          }
        punchedWall(b, stoneM, stone2, e, gf, attic, holes, {
          d: 0.3,
          tile: [7.2, 7.2],
          uvBase: gf,
          back: glass,
        });
        // joint glazing with mullions and floor transoms
        {
          const h = gh[0];
          const tm = (h.t0 + h.t1) / 2;
          boxOn(kit, b, glass, e, tm, -0.78, 0, h.t1 - h.t0, 0.04, attic - 0.2);
          boxOn(kit, b, frameM, e, tm, -0.72, 0, 0.08, 0.1, attic - 0.2);
          for (let z = gf; z < attic - 0.3; z += storey)
            boxOn(kit, b, frameM, e, tm, -0.72, z, h.t1 - h.t0, 0.1, 0.12);
        }
        for (const h of gh.slice(1)) {
          const tm = (h.t0 + h.t1) / 2,
            w = h.t1 - h.t0;
          if (h.door) {
            boxOn(kit, b, doorM, e, tm, -0.42, h.zb, w - 0.1, 0.05, 2.5);
            for (const s of [-1, 0, 1])
              boxOn(
                kit,
                b,
                frameM,
                e,
                tm + s * (w / 2 - 0.05),
                -0.4,
                h.zb,
                0.07,
                0.08,
                h.zt - h.zb,
              );
            boxOn(kit, b, frameM, e, tm, -0.4, h.zb + 2.5, w, 0.08, 0.08);
            boxOn(kit, b, zinc, e, tm, 1.0, gf - 0.6, 5, 2.0, 0.3);
            boxOn(kit, b, frameM, e, tm, 1.98, gf - 0.65, 5, 0.06, 0.4);
            stepsOn(kit, b, stone2, e, tm, 3.6, 1, { rise: 0.15, tread: 0.6 });
            continue;
          }
          fitWindow(kit, b, e, h, { d: 0.35, glass, frame: frameM, sill: frameM, bars: 0 });
          for (const s of [-1, 0, 1])
            boxOn(kit, b, frameM, e, tm + (s * w) / 3, -0.27, h.zb, 0.07, 0.08, h.zt - h.zb);
          boxOn(kit, b, frameM, e, tm, -0.27, h.zt - 0.5, w, 0.08, 0.06);
        }
        for (const h of holes.slice(1)) {
          const tm = (h.t0 + h.t1) / 2,
            w = h.t1 - h.t0;
          fitWindow(kit, b, e, h, { d: 0.3, glass, frame: frameM, sill: frameM, bars: 0 });
          boxOn(kit, b, frameM, e, tm, -0.22, h.zt - 0.5, w, 0.08, 0.06);
          boxOn(kit, b, juliet, e, tm, -0.05, h.zb + 0.05, w - 0.06, 0.02, 0.9);
          boxOn(kit, b, frameM, e, tm, -0.05, h.zb + 0.95, w - 0.06, 0.04, 0.04);
          boxOn(kit, b, stone, e, tm, 0.06, h.zb - 0.1, w + 0.25, 0.16, 0.1);
        }
        // projecting stone piers every two bays
        for (let i = 0; i <= n; i += 2)
          boxOn(kit, b, stone, e, joint + i * bw, 0.16, 0, 0.6, 0.32, attic);
      }
      atticBays(ring, attic, H);
      kit.cornice(b, stone, ring, attic - 0.3, { height: 0.35, projection: 0.38, steps: 2 });
      kit.cornice(b, stone, ring, gf - 0.2, { height: 0.25, projection: 0.18 });
      kit.cornice(b, stone2, ring, 0, { height: 0.4, projection: 0.06 });
      kit.cap(b, roofM, [[ring]], H);
      parapet(kit, b, zinc, ring, H, 0.5, 0.15);
      kit.cornice(b, frameM, ring, H + 0.45, { height: 0.06, projection: 0.04 });
      for (const e of ringEdges(ring)) {
        if (!front(e)) continue;
        const s = pointOn(e, e.len * 0.7, -7);
        kit.box(b, zinc, s[0], s[1], H, 6, 4, 2.6, e.ang);
        kit.box(b, frameM, s[0], s[1], H + 2.6, 6.3, 4.3, 0.15, e.ang);
        const p2 = pointOn(e, e.len * 0.3, -9);
        louvreBox(kit, b, frameM, zinc, p2[0], p2[1], H, 5, 3, 1.6, e.ang, 0.22);
      }
      roofRail(kit, b, frameM, ring, H, 1.2, 1.1);
    }
    // Keogh: lower rear range stepping down to the mews.
    const kb = byId[IDS.keogh];
    if (kb) {
      const ring = ccw(kb.polys[0][0]);
      const H = kb.h;
      for (const e of ringEdges(ring)) {
        if (e.len < 2.2) wallQuad(b, brickM, e.a, e.b, 0, H, { bay: 3.6, storey: 3.6 });
        else brickBays(e, 0, H, 2);
      }
      kit.cornice(b, stone, ring, H - 0.2, { height: 0.2, projection: 0.15 });
      kit.cap(b, roofM, [[ring]], H);
      parapet(kit, b, stone, ring, H, 0.6, 0.2);
      const inner = kit.offsetRing(ring, -1.2);
      atticBays(inner, H, H + 3.0);
      kit.cap(b, roofM, [[inner]], H + 3.0);
      kit.cornice(b, frameM, inner, H + 2.95, { height: 0.08, projection: 0.06 });
    }
    for (const e of fronts) paved(kit, b, paving, edgeRect(e, 0, e.len, 0, 3.0), 0.05);
    const g = new THREE.Group();
    g.add(b.toGroup('princes_gardens_southside'));
    if (placeAssets && fronts.length) {
      const pl = [];
      for (const e of fronts)
        for (const f of [0.25, 0.85]) {
          const p = pointOn(e, e.len * f, 2.5);
          pl.push([p[0], p[1], e.ang + Math.PI]);
        }
      g.add(placeAssets('bench', pl));
    }
    return g;
  },
};
