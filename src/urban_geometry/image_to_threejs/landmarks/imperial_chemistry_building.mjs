// Imperial College Chemistry Building (Architects' Co-Partnership, 1968-70) on the
// south side of Imperial College Road. Eight-storey late-modernist laboratory slab:
// continuous ribbon windows between pale precast concrete spandrel bands, a
// recessed glazed ground floor, brick-clad stair/service cores, and a roof crowded
// with plant rooms and the steel fume-cupboard extract stacks of a chemistry lab.
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
  id: 'imperial_chemistry_building',
  name: 'Chemistry Building, Imperial College',
  claims: ['886385e0-8db0-49d2-b55b-98043ea1c3fd'],
  references: [
    {
      title: 'plate 76 - Survey of London vol 38 (Imperial College in 1973)',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for:
        'Chemistry block 1968-70 and Biochemistry range 1962-5 by Architects Co-Partnership',
    },
    {
      title: 'Department of Chemistry, Imperial College London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Department_of_Chemistry,_Imperial_College_London',
      used_for: 'building identity / use',
    },
    {
      title: 'chemistry at imperial (history)',
      url: 'https://www.imperial.ac.uk/chemistry/about/our-history/chemistry-at-imperial/',
      used_for: 'relationship with the surviving Aston Webb RCS-1 building',
    },
    {
      title: 'Royal College of Science - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_College_of_Science',
      used_for:
        'site history: the central Webb range was demolished in the 1970s for the new Chemistry building',
    },
  ],
  notes:
    'No facade description was found; the ribbon-window / concrete-spandrel elevation, brick cores and rooftop extract stacks are a generic reconstruction of a 1960s ACP lab block, not traced from photos. Height 26.4 m from Overture (8 floors). Refinement: ribbon windows are real recessed strips (aluminium mullions every 1.8 m, transoms, opening lights) between projecting exposed-aggregate spandrel bands; the colonnaded ground floor has a mullioned glazed screen, an entrance with canopy and fascia sign to Imperial College Road (wording assumed), and the roof carries a louvred plant room, capped extract flues on steel frames, ducts, lift overruns and guard rails. Short returns and the rear courtyard face keep a painted ribbon texture.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 4.2,
      storey = (H - 1.2 - gf) / 7;
    const b = new kit.MeshBatch();
    const conc = kit.mat('#c9c4b8'),
      conc2 = kit.mat('#bdb7aa'),
      dconc = kit.mat('dark_concrete'),
      brick = kit.mat('#6e4a3a'),
      steel = kit.mat('#aab0b4', { roughness: 0.5 }),
      galv = kit.mat('#9ea4a6', { roughness: 0.55, metalness: 0.4 }),
      roofM = kit.roof('flat', 1),
      glass = kit.mat('#34444f', { roughness: 0.12, metalness: 0.3 }),
      alu = kit.mat('#b9bdbf', { roughness: 0.45, metalness: 0.4 }),
      darkAlu = kit.mat('#4a5054', { roughness: 0.5, metalness: 0.3 }),
      paving = kit.mat('#b6afa2');
    const aggregate = kit.paintedMaterial(
      'imperial_chemistry_building:aggregate',
      256,
      128,
      (c, w, h) => {
        const r = kit.rng(0.6869);
        noiseFill(c, w, h, '#c9c4b8', r, 0.14, 2);
        c.fillStyle = 'rgba(0,0,0,0.2)';
        for (let x = 0; x <= w; x += 64) c.fillRect(x, 0, 1.5, h); // panel joints every 3.6 m
      },
    );
    const ribbon = kit.paintedMaterial(
      'imperial_chemistry_building:ribbon',
      512,
      256,
      (c, w, h) => {
        const r = kit.rng(0.6868);
        noiseFill(c, w, h, '#c9c4b8', r, 0.07, 4);
        for (let j = 0; j < 2; j++) {
          const y = j * (h / 2);
          const wy = y + 4,
            wh = (h / 2) * 0.56;
          glassPane(c, 0, wy, w, wh, r, [40, 52, 60]);
          c.fillStyle = '#d8d4ca';
          for (let i = 0; i <= 16; i++) c.fillRect((i * w) / 16 - 1.5, wy, 3, wh);
          c.fillStyle = 'rgba(0,0,0,0.18)';
          for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 0.5, wy + wh, 1, h / 2 - wh - 4);
          c.fillRect(0, wy + wh + 1, w, 2);
        }
      },
    );
    const louvre = kit.mat('#8f969a', { roughness: 0.5, metalness: 0.3 });
    const es = ringEdges(ring);
    const north = es.filter((e) => e.len > 20).sort((p, q) => q.ny - p.ny)[0];
    const top = H - 1.2;
    // Ground floor: glazed screen set back behind a line of square columns.
    const inner = kit.offsetRing(ring, -1.2);
    for (const e of ringEdges(inner)) {
      boxOn(kit, b, glass, e, e.len / 2, -0.02, 0, e.len, 0.04, gf);
      const n = Math.max(1, Math.round(e.len / 1.8));
      for (let i = 0; i <= n; i++)
        boxOn(kit, b, darkAlu, e, (i * e.len) / n, 0.04, 0, 0.08, 0.12, gf);
      boxOn(kit, b, darkAlu, e, e.len / 2, 0.04, 2.6, e.len, 0.1, 0.1);
      boxOn(kit, b, darkAlu, e, e.len / 2, 0.04, 0, e.len, 0.12, 0.15);
    }
    kit.cap(b, conc, [[ring]], gf, { down: true });
    for (const e of es) {
      if (e.len < 6) continue;
      const n = Math.round(e.len / 7.2);
      for (let i = 0; i <= n; i++) {
        const p = pointOn(e, (i / n) * e.len, -0.45);
        kit.box(b, conc2, p[0], p[1], 0, 0.6, 0.6, gf, e.ang);
        kit.box(b, conc, p[0], p[1], gf - 0.4, 0.8, 0.8, 0.4, e.ang);
      }
    }
    // Paving under the colonnade and a forecourt strip to the road.
    paved(kit, b, paving, ring, 0.03);
    // Upper floors.
    for (const e of es) {
      if (e.len <= 9) {
        wallQuad(b, brick, e.a, e.b, gf, top);
        continue;
      }
      if (e.ny < -0.6 && e !== north && e.len < 30) {
        // courtyard / rear returns: painted ribbons
        wallQuad(b, ribbon, e.a, e.b, gf, top, { bay: 3.6, storey, uvBase: gf });
        continue;
      }
      const holes = [];
      for (let k = 0; k < 7; k++) {
        const z = gf + k * storey;
        holes.push({ t0: 0.5, t1: e.len - 0.5, zb: z + 1.05, zt: z + storey - 0.25 });
      }
      punchedWall(b, aggregate, conc, e, gf, top, holes, {
        d: 0.3,
        tile: [14.4, 7.2],
        back: glass,
      });
      const n = Math.max(1, Math.round((e.len - 1) / 1.8));
      for (const h of holes) {
        const step = (h.t1 - h.t0) / n;
        for (let i = 0; i <= n; i++)
          boxOn(
            kit,
            b,
            alu,
            e,
            h.t0 + i * step,
            -0.24,
            h.zb,
            i % 2 ? 0.06 : 0.1,
            0.12,
            h.zt - h.zb,
          );
        // transom and sill / head members
        boxOn(kit, b, alu, e, e.len / 2, -0.24, h.zb + (h.zt - h.zb) * 0.7, h.t1 - h.t0, 0.1, 0.06);
        boxOn(kit, b, alu, e, e.len / 2, -0.24, h.zb, h.t1 - h.t0, 0.14, 0.08);
        // a few opening lights (top-hung vents) ajar
        const rr = kit.rng(h.zb * 7.1 + e.k);
        for (let i = 0; i < n; i++)
          if (rr() < 0.12)
            boxOn(
              kit,
              b,
              glass,
              e,
              h.t0 + (i + 0.5) * step,
              -0.14,
              h.zb + (h.zt - h.zb) * 0.72,
              step - 0.1,
              0.05,
              (h.zt - h.zb) * 0.27,
            );
      }
    }
    // Projecting floor-edge bands (drip moulds) at each spandrel head.
    for (let k = 0; k <= 7; k++)
      kit.cornice(b, conc, ring, gf + k * storey - 0.15, { height: 0.3, projection: 0.14 });
    parapet(kit, b, conc, ring, top, 1.2, 0.35);
    kit.cornice(b, dconc, ring, H - 0.05, { height: 0.08, projection: 0.06 });
    kit.cap(b, roofM, [[ring]], top + 0.01);
    // Entrance on Imperial College Road: canopy, doors, sign.
    {
      const e = north;
      const t = e.len * 0.42;
      boxOn(kit, b, darkAlu, e, t, 1.0, 3.3, 8.4, 3.6, 0.35);
      boxOn(kit, b, alu, e, t, 2.75, 3.25, 8.6, 0.12, 0.45);
      for (const s of [-1, 1]) boxOn(kit, b, darkAlu, e, t + s * 4.0, 2.6, 0, 0.15, 0.15, 3.3);
      boxOn(kit, b, kit.mat('#1c2329'), e, t, -1.16, 0, 3.6, 0.06, 2.5);
      for (const s of [-1, 0, 1]) boxOn(kit, b, alu, e, t + s * 0.9, -1.12, 0, 0.06, 0.08, 2.5);
      const sign = signMaterial(kit, 'imperial_chemistry_building:sign', 'CHEMISTRY BUILDING', {
        bg: '#0f2a4a',
      });
      boxOn(kit, b, sign, e, t, 2.84, 3.32, 7.2, 0.03, 0.3);
      stepsOn(kit, b, conc2, e, t, 7.5, 1, { rise: 0.12, tread: 2.2 });
    }
    // Brick stair / service towers rising above the roof at the ends of the slab.
    const ex = kit.orientedExtent(ring, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const tower = (u, v, w, d, h) => {
      const p = at(u, v);
      kit.box(b, brick, p[0], p[1], 0.01, w, d, h, frame.angle);
      kit.box(b, conc, p[0], p[1], h, w + 0.3, d + 0.3, 0.3, frame.angle);
      // vertical glazed slot up the tower faces
      kit.box(b, glass, p[0], p[1], gf, 0.9, d + 0.04, h - gf - 1.0, frame.angle);
      kit.box(b, glass, p[0], p[1], gf, w + 0.04, 0.9, h - gf - 1.0, frame.angle);
      louvreBox(kit, b, darkAlu, louvre, p[0], p[1], h + 0.3, w - 2, d - 2, 1.4, frame.angle, 0.22);
    };
    tower(ex.u0 + 4.5, ex.v1 - 4, 6, 6, H + 3.4);
    tower(ex.u1 - 4.5, ex.v1 - 3, 6, 5, H + 3.4);
    // Plant room with louvres.
    const um = (ex.u0 + ex.u1) / 2;
    const pc = at(um, (ex.v0 + ex.v1) / 2 + 1);
    louvreBox(kit, b, dconc, louvre, pc[0], pc[1], top, 30, 8, H - top + 3.2, frame.angle, 0.28);
    kit.box(b, galv, pc[0], pc[1], H + 3.4, 26, 6, 0.6, frame.angle);
    // Fume-cupboard extract stacks: two rows of capped steel flues on a frame.
    const rr = kit.rng(0.886);
    for (let i = 0; i < 14; i++)
      for (const v of [ex.v0 + 3.2, ex.v0 + 5]) {
        const u = ex.u0 + 10 + i * ((ex.u1 - ex.u0 - 20) / 13);
        const p = at(u, v);
        flue(THREE, b, steel, p[0], p[1], top, H - top + 2.5 + rr() * 2.5, 0.33);
      }
    // Support frame and ducts linking the flues to the plant room.
    for (const v of [ex.v0 + 2.6, ex.v0 + 5.6]) {
      const d0 = at(um, v);
      kit.box(b, galv, d0[0], d0[1], H + 0.6, ex.u1 - ex.u0 - 18, 0.15, 0.15, frame.angle);
    }
    for (let i = 0; i <= 7; i++) {
      const u = ex.u0 + 9 + i * ((ex.u1 - ex.u0 - 18) / 7);
      for (const v of [ex.v0 + 2.6, ex.v0 + 5.6]) {
        const p = at(u, v);
        kit.box(b, galv, p[0], p[1], top, 0.15, 0.15, H - top + 0.75, frame.angle);
      }
    }
    const d0 = at(um, ex.v0 + 4.1);
    kit.box(b, steel, d0[0], d0[1], top, ex.u1 - ex.u0 - 18, 1.0, 1.0, frame.angle);
    for (let i = 0; i < 4; i++) {
      const p = at(um - 9 + i * 6, ex.v0 + 6.5);
      kit.box(b, steel, p[0], p[1], top, 0.9, 3.2, 0.9, frame.angle);
    }
    roofRail(kit, b, galv, ring, top, 0.8, 1.1);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_chemistry_building'));
    // Cycle stands beside the entrance (scene coordinates).
    if (placeAssets) {
      const e = north;
      const pl = [];
      for (let i = 0; i < 5; i++) {
        const p = pointOn(e, e.len * 0.62 + i * 1.2, 2.2);
        pl.push([p[0], p[1], e.ang + Math.PI / 2]);
      }
      g.add(placeAssets('bicycle_stand', pl));
    }
    return g;
  },
};
