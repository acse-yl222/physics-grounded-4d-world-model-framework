// Chemistry RCS1, Imperial College: the surviving section of Sir Aston Webb's
// Royal College of Science building (1906) on Imperial College Road, now used by
// the Department of Chemistry. Classical three-storey red brick range with
// distinctive Portland stone banding, a rusticated stone ground floor, tall
// stone-framed windows with keystones, a heavy modillion cornice and balustraded
// parapet to the street front; the rear courtyard wings are plainer.
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
// Triangular pediment (width w, rise) as a prism of depth d centred on (x, y) at z, along ang.
function pediment(THREE, batch, m, x, y, z, w, rise, d, ang) {
  const sh = new THREE.Shape();
  sh.moveTo(-w / 2, 0);
  sh.lineTo(w / 2, 0);
  sh.lineTo(0, rise);
  sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false });
  g.translate(0, 0, -d / 2);
  g.rotateX(Math.PI / 2);
  batch.addGeometry(m, g, new THREE.Matrix4().makeRotationZ(ang).setPosition(x, y, z));
  g.dispose();
}

export default {
  id: 'imperial_chemistry_rcs1',
  name: 'Chemistry RCS1 (Royal College of Science, Aston Webb)',
  claims: ['18b99e43-c816-4a20-9a58-6525438d1280'],
  references: [
    {
      title: 'Royal College of Science - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_College_of_Science',
      used_for:
        'Aston Webb building in a Classical style with distinctive brick courses, mostly demolished',
    },
    {
      title: 'chemistry at imperial (history)',
      url: 'https://www.imperial.ac.uk/chemistry/about/our-history/chemistry-at-imperial/',
      used_for:
        '1906 Aston Webb building on Imperial College Road; part survives as RCS-1, cleaned and refurbished with Wolfson Foundation help',
    },
    {
      title: 'Take a closer look - Imperial College London',
      url: 'https://www.imperial.ac.uk/stories/take-a-closer-look',
      used_for:
        'Webb design completed 1906, symmetrical with the chemistry wing towards Exhibition Road; only the eastern wing survives; facade resembles his V&A front on Cromwell Road',
    },
  ],
  notes:
    'Banding rhythm, window sizes and the balustrade are generic Webb/Edwardian classical detail, not traced from photographs. The whole Overture footprint (which may include later infill behind the street range) is modelled in the same idiom. Height 12.9 m from Overture. Refinement: the north (street) faces have real recessed windows - round-headed sashes with keystones in a rusticated Portland stone ground floor, tall sashes in stone architraves with keystones and cornice hoods (first floor) and plain architraves (second floor) in red brick with stone bands - plus a stone doorcase with columns, pediment and steps on the longest street face (position assumed), stepped cornice with modillions, kit balustrade with dies, quoins, glazed ridge lanterns over the former laboratories, ventilation stacks and area railings. Courtyard and rear faces keep the painted elevation.',
  build({ THREE, kit, buildings }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 4.4,
      storey = (H - 1.3 - gf) / 2;
    const b = new kit.MeshBatch();
    const stone = kit.mat('#ddd6c4'),
      stone2 = kit.mat('#d2cab5'),
      roofM = kit.roof('flat', 2),
      lead = kit.mat('lead'),
      white = kit.mat('#efece4'),
      dark = kit.mat('dark_glass'),
      brickPlain = kit.mat('#9b4f3a'),
      iron = kit.mat('#1d2022', { roughness: 0.5 }),
      glassRoof = kit.mat('#7d95a3', { roughness: 0.15, metalness: 0.3 }),
      doorM = kit.mat('#3b2a1e');
    const upper = kit.paintedMaterial('imperial_chemistry_rcs1:upper', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1806);
      brickCourses(c, w, h, r, '#a0523c', 3);
      c.fillStyle = '#ddd6c4';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 9);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.42,
            wh = ch * 0.66,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.18;
          c.fillStyle = '#e3dccb';
          c.fillRect(wx - 7, wy - 7, ww + 14, wh + 12);
          c.fillRect(wx + ww / 2 - 6, wy - 12, 12, 12);
          c.fillRect(wx - 10, wy + wh + 3, ww + 20, 5);
          sash(c, wx, wy, ww, wh, r, { panesX: 2, panesY: 2, bar: 2 });
        }
    });
    const groundM = kit.paintedMaterial('imperial_chemistry_rcs1:ground', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2806);
      noiseFill(c, w, h, '#d8d0bc', r, 0.06, 4);
      c.fillStyle = 'rgba(80,70,55,0.35)';
      for (let y = 0; y < h; y += 21) c.fillRect(0, y, w, 2);
      const cw = w / 4;
      for (let i = 0; i < 4; i++) {
        const ww = cw * 0.46,
          x = i * cw + (cw - ww) / 2,
          y = h * 0.2,
          hh = h * 0.62;
        c.fillStyle = '#2f3b45';
        c.beginPath();
        c.moveTo(x, y + hh);
        c.lineTo(x, y + ww / 2);
        c.arc(x + ww / 2, y + ww / 2, ww / 2, Math.PI, 0);
        c.lineTo(x + ww, y + hh);
        c.fill();
        sash(c, x + 3, y + ww / 2, ww - 6, hh - ww / 2 - 3, r, { panesX: 2, panesY: 2, bar: 1.5 });
        c.fillStyle = '#e8e2d2';
        c.fillRect(x + ww / 2 - 7, y - 4, 14, 14);
      }
    });
    // Plain textures for the walls that get real windows.
    const brickBand = kit.paintedMaterial(
      'imperial_chemistry_rcs1:brickband',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.1807);
        brickCourses(c, w, h, r, '#a0523c', 3);
        // broad Portland stone bands every ~0.9 m (tile = 7.2 m high)
        for (let y = 0; y < h; y += 32) {
          c.fillStyle = '#dcd4c1';
          c.fillRect(0, y, w, 9);
          c.fillStyle = 'rgba(0,0,0,0.12)';
          c.fillRect(0, y + 9, w, 1);
          for (let x = 0; x < w; x += 22) c.fillRect(x, y, 1, 9);
        }
      },
    );
    const rustic = kit.paintedMaterial('imperial_chemistry_rcs1:rustic', 256, 256, (c, w, h) => {
      const r = kit.rng(0.2807);
      noiseFill(c, w, h, '#d8d0bc', r, 0.06, 4);
      c.fillStyle = 'rgba(70,60,45,0.45)';
      for (let y = 0; y < h; y += 24) c.fillRect(0, y, w, 3); // channelled rustication
      c.fillStyle = 'rgba(70,60,45,0.25)';
      for (let y = 0, k = 0; y < h; y += 24, k++)
        for (let x = k % 2 ? 0 : 30; x < w; x += 60) c.fillRect(x, y, 1.5, 24);
    });
    const isFront = (e) => e.ny > 0.7 && e.len > 8;
    const fronts = [];
    for (const e of ringEdges(ring)) {
      if (!isFront(e)) {
        wallQuad(b, groundM, e.a, e.b, 0, gf, { bay: 4.2, storey: gf / 2 });
        wallQuad(b, upper, e.a, e.b, gf, H - 1.3, { bay: 4.2, storey, uvBase: gf });
        continue;
      }
      fronts.push(e);
      const n = Math.max(1, Math.round(e.len / 4.2));
      const doorK = e.len > 25 ? Math.floor(n / 2) : -1;
      e.doorK = doorK;
      e.n = n;
      // Ground floor: round-headed windows.
      const gh = bayHoles(e, n, 1.7, 0.9, gf - 0.55, { skip: (k) => k === doorK });
      if (doorK >= 0) {
        const t = (e.len * (doorK + 0.5)) / n;
        gh.push({ t0: t - 1.0, t1: t + 1.0, zb: 0.6, zt: 3.6, door: true, d: 0.5 });
      }
      punchedWall(b, rustic, stone2, e, 0, gf, gh, { d: 0.35, tile: [7.2, 7.2], back: stone2 });
      for (const h of gh) {
        const tm = (h.t0 + h.t1) / 2,
          w = h.t1 - h.t0;
        if (h.door) {
          boxOn(kit, b, doorM, e, tm, -0.46, h.zb, w - 0.2, 0.06, 2.6);
          for (const s2 of [-1, 1])
            for (const z of [0.2, 1.35])
              boxOn(
                kit,
                b,
                kit.mat('#4a3626'),
                e,
                tm + s2 * 0.42,
                -0.42,
                h.zb + z,
                0.62,
                0.03,
                1.0,
              );
          boxOn(kit, b, dark, e, tm, -0.46, h.zb + 2.65, w - 0.2, 0.05, h.zt - h.zb - 2.7);
          boxOn(kit, b, white, e, tm, -0.43, h.zb + 2.6, w - 0.1, 0.08, 0.08);
          // Doric columns, entablature and triangular pediment
          for (const s of [-1, 1]) {
            const p = pointOn(e, tm + s * 1.55, 0.45);
            b.addGeometry(
              stone,
              new THREE.CylinderGeometry(0.24, 0.28, 3.4, 14).rotateX(Math.PI / 2),
              new THREE.Matrix4().makeTranslation(p[0], p[1], 0.6 + 1.7),
            );
            kit.box(b, stone, p[0], p[1], 0.3, 0.75, 0.75, 0.3, e.ang);
            kit.box(b, stone, p[0], p[1], 4.0, 0.7, 0.7, 0.2, e.ang);
          }
          boxOn(kit, b, stone, e, tm, 0.45, 4.2, 4.2, 0.9, 0.55);
          const p = pointOn(e, tm, 0.45);
          pediment(THREE, b, stone, p[0], p[1], 4.75, 4.6, 1.1, 0.8, e.ang);
          const pr = pointOn(e, tm, 0.35);
          kit.box(b, stone2, pr[0], pr[1], 4.75, 0.5, 0.2, 0.5, e.ang); // tympanum cartouche
          stepsOn(kit, b, stone2, e, tm, 4.0, 4, { rise: 0.15, tread: 0.35 });
          continue;
        }
        fitWindow(kit, b, e, h, {
          d: 0.35,
          glass: dark,
          frame: white,
          sill: white,
          bars: 1,
          arch: (w - 0.06) / 2,
        });
        boxOn(kit, b, stone, e, tm, 0.05, h.zt - 0.35, 0.42, 0.12, 0.55); // keystone
        boxOn(kit, b, stone, e, tm, 0.06, h.zb - 0.14, w + 0.4, 0.22, 0.14); // sill
      }
      // Upper floors: tall sashes in stone architraves.
      const uh = [];
      for (let s = 0; s < 2; s++) {
        const zb = gf + s * storey + (s ? 0.55 : 0.75);
        for (const h of bayHoles(e, n, 1.3, zb, zb + (s ? 2.2 : 2.55), {
          skip: (k) => s === 0 && k === doorK,
        }))
          uh.push({ ...h, s });
      }
      punchedWall(b, brickBand, stone, e, gf, H - 1.3, uh, {
        d: 0.28,
        tile: [7.2, 7.2],
        uvBase: gf,
        back: dark,
      });
      for (const h of uh) {
        const tm = (h.t0 + h.t1) / 2,
          w = h.t1 - h.t0;
        fitWindow(kit, b, e, h, { d: 0.28, glass: dark, frame: white, sill: white, bars: 1 });
        boxOn(kit, b, white, e, tm, -0.2, h.zb + (h.zt - h.zb) * 0.5, w - 0.08, 0.08, 0.07);
        for (const s of [-1, 1])
          boxOn(
            kit,
            b,
            stone,
            e,
            tm + s * (w / 2 + 0.11),
            0.04,
            h.zb - 0.05,
            0.22,
            0.08,
            h.zt - h.zb + 0.15,
          );
        boxOn(kit, b, stone, e, tm, 0.04, h.zt, w + 0.44, 0.08, 0.2);
        boxOn(kit, b, stone, e, tm, 0.07, h.zt + 0.04, 0.32, 0.14, 0.42); // keystone
        boxOn(kit, b, stone, e, tm, 0.08, h.zb - 0.15, w + 0.55, 0.2, 0.15); // sill
        if (h.s === 0) {
          boxOn(kit, b, stone, e, tm, 0.12, h.zt + 0.25, w + 0.9, 0.3, 0.16); // cornice hood
          for (const s of [-1, 1])
            boxOn(kit, b, stone, e, tm + s * (w / 2 + 0.3), 0.1, h.zt - 0.2, 0.16, 0.22, 0.45); // consoles
        }
      }
      if (doorK >= 0) {
        // carved stone panel above the entrance pediment
        const t = (e.len * (doorK + 0.5)) / n;
        boxOn(kit, b, stone, e, t, 0.05, gf + 1.7, 2.2, 0.1, 1.5);
        boxOn(kit, b, stone2, e, t, 0.1, gf + 1.9, 1.8, 0.06, 1.1);
      }
      // Quoins at the ends of each street face.
      for (const t of [0.3, e.len - 0.3])
        for (let z = gf, k = 0; z < H - 1.9; z += 0.6, k++)
          boxOn(
            kit,
            b,
            stone,
            e,
            t + (t < 1 ? 1 : -1) * (k % 2 ? 0.2 : 0),
            0.04,
            z + 0.02,
            k % 2 ? 1.0 : 0.6,
            0.1,
            0.56,
          );
    }
    kit.cornice(b, stone, ring, gf - 0.3, { height: 0.45, projection: 0.18, steps: 2 }); // first-floor string course
    kit.cornice(b, stone2, ring, 0, { height: 0.7, projection: 0.12 }); // plinth
    kit.cornice(b, stone, ring, gf + storey - 0.05, { height: 0.18, projection: 0.08 }); // sill band
    // Stepped modillion cornice.
    kit.cornice(b, stone, ring, H - 1.95, { height: 0.25, projection: 0.15 });
    kit.cornice(b, stone, ring, H - 1.6, { height: 0.6, projection: 0.6, steps: 3 });
    for (const e of ringEdges(kit.offsetRing(ring, 0.3))) {
      const n = Math.floor(e.len / 0.7);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n));
        kit.box(b, stone, p[0], p[1], H - 1.85, 0.18, 0.5, 0.25, e.ang);
      }
    }
    // Balustraded parapet on the street faces with dies, plain parapet elsewhere.
    for (const e of ringEdges(ring)) {
      if (isFront(e)) {
        const a = pointOn(e, 0, 0.25),
          q = pointOn(e, e.len, 0.25);
        kit.balustrade(b, stone, [a, q], H - 1.0, { height: 1.0, spacing: 0.32 });
        const nd = Math.max(1, Math.round(e.len / 4.2));
        for (let i = 0; i <= nd; i++) {
          const p = pointOn(e, (i / nd) * e.len, 0.25);
          kit.box(b, stone, p[0], p[1], H - 1.0, 0.6, 0.6, 1.1, e.ang);
          kit.box(b, stone, p[0], p[1], H + 0.1, 0.7, 0.7, 0.1, e.ang);
        }
        if (e.doorK >= 0) {
          // raised attic panel over the entrance bay
          const t = (e.len * (e.doorK + 0.5)) / e.n;
          boxOn(kit, b, stone, e, t, 0.25, H - 1.0, 5.0, 0.6, 1.7);
          boxOn(kit, b, stone, e, t, 0.3, H + 0.7, 5.3, 0.7, 0.2);
        }
      } else wallQuad(b, stone, e.a, e.b, H - 1.0, H - 0.1);
    }
    kit.cap(b, roofM, [[ring]], H - 0.92);
    // Glazed ridge lanterns over the former laboratories.
    const fr = kit.ringFrame(ring);
    const ex = kit.orientedExtent(ring, fr.angle);
    for (let i = 0; i < 3; i++) {
      const c = ex.at(
        ex.u0 + (ex.u1 - ex.u0) * (0.25 + i * 0.25),
        ex.v0 + (ex.v1 - ex.v0) * 0.55,
        0,
      );
      kit.box(b, lead, c[0], c[1], H - 1.0, 8, 4, 1.0, fr.angle);
      const lr = [
        [-3.8, -1.8],
        [3.8, -1.8],
        [3.8, 1.8],
        [-3.8, 1.8],
      ].map(([u, v]) => [
        c[0] + u * Math.cos(fr.angle) - v * Math.sin(fr.angle),
        c[1] + u * Math.sin(fr.angle) + v * Math.cos(fr.angle),
      ]);
      kit.pitchedRoof(b, glassRoof, lead, lr, fr.angle, H, 1.2, 'hipped', { overhang: 0.05 });
      for (let k = -3; k <= 3; k++) {
        const p = [c[0] + k * 1.1 * Math.cos(fr.angle), c[1] + k * 1.1 * Math.sin(fr.angle)];
        kit.box(b, lead, p[0], p[1], H, 0.06, 3.7, 0.7, fr.angle);
      }
    }
    // Brick ventilation stacks with stone caps along the spine of the street range.
    for (const e of fronts)
      if (e.len > 15)
        for (const t of [0.25, 0.75]) {
          const p = pointOn(e, e.len * t, -5);
          kit.box(b, brickPlain, p[0], p[1], H - 1.0, 1.2, 2.2, 3.0, e.ang);
          kit.box(b, stone, p[0], p[1], H + 2.0, 1.45, 2.45, 0.25, e.ang);
        }
    // Area railings along the street faces.
    for (const e of fronts) {
      const segs =
        e.doorK >= 0
          ? [
              [0, (e.len * (e.doorK + 0.5)) / e.n - 2.4],
              [(e.len * (e.doorK + 0.5)) / e.n + 2.4, e.len],
            ]
          : [[0, e.len]];
      for (const [t0, t1] of segs)
        railing(kit, b, iron, pointOn(e, t0, 1.6), pointOn(e, t1, 1.6), 0, { h: 1.05 });
    }
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_chemistry_rcs1'));
    return g;
  },
};
