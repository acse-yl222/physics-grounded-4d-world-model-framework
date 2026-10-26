// Dyson Building, 25 Exhibition Road: home since 2018 of Imperial College's Dyson
// School of Design Engineering. Edwardian Baroque former Royal Mail sorting office
// (and Met Office London HQ 1910-19, later a Science Museum annexe) on the corner of
// Exhibition Road and Imperial College Road, refurbished by Pascall+Watson with
// its exterior retained. Four storeys: rusticated stone ground floor with large
// sweeping curved-headed windows, red brick upper floors with tall box sashes in
// stone surrounds, stone quoins, a main cornice under an attic storey, and a
// balustraded parapet; a low glazed link joins the RCS1 range to the west.
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
// Segmental pediment / arch slab of chord w and rise, depth d.
function segment(THREE, batch, m, x, y, z, w, rise, d, ang) {
  const R = ((w * w) / 4 + rise * rise) / (2 * rise);
  const sh = new THREE.Shape();
  sh.moveTo(-w / 2, 0);
  sh.lineTo(w / 2, 0);
  const a0 = Math.atan2(R - rise, w / 2);
  sh.absarc(0, rise - R, R, a0, Math.PI - a0, false);
  const g = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 10 });
  g.translate(0, 0, -d / 2);
  g.rotateX(Math.PI / 2);
  batch.addGeometry(m, g, new THREE.Matrix4().makeRotationZ(ang).setPosition(x, y, z));
  g.dispose();
}

export default {
  id: 'imperial_dyson_building',
  name: 'Dyson School of Design Engineering (25 Exhibition Road)',
  claims: ['f84e24cc-0cba-4bcb-a8dc-9c39610db775', '22d8e5b3-c1a4-4dbb-841a-dfd4e76aec40'],
  references: [
    {
      title: 'Dyson School of Design Engineering - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Dyson_School_of_Design_Engineering',
      used_for:
        'Dyson Building at 25 Exhibition Road since 2018; former Met Office London HQ 1910-19 and Science Museum building; original interiors and signage kept inside the entrance from Exhibition Road',
    },
    {
      title: 'Dyson Building - Imperial College of London (Pascall+Watson)',
      url: 'https://www.pascalls.co.uk/projects/work/education/dyson-building',
      used_for: 'exterior retained, treated as if Grade II* listed; four-storey change of use',
    },
    {
      title: 'Dyson School of Design Engineering fitted with Selectaglaze windows - PBC Today',
      url: 'https://www.pbctoday.co.uk/news/planning-construction-news/dyson-school-design-engineering/66755/',
      used_for:
        'Edwardian baroque former sorting office on the corner of Exhibition Road and Imperial College Road; large sweeping curved-headed casements and tall box sash windows',
    },
    {
      title:
        'dyson school of design engineering link bridge receives planning approval - Pascall+Watson',
      url: 'https://www.pascalls.co.uk/news/article/dyson-school-of-design-engineering-link-bridge-receives-planning-approval/',
      used_for: 'minimalist glazed link structure',
    },
  ],
  notes:
    'Searches confirmed the Edwardian Baroque style and window types but not the facing materials; red brick with Portland stone dressings is assumed. Bay rhythm, corner treatment and attic are approximate. The 3.4 m strip footprint between RCS1 and the Dyson Building is modelled as a low glazed link. Height 13.6 m from Overture. Refinement: the two street fronts (Imperial College Road, Exhibition Road) have real recessed windows - segmental-headed multi-pane casements with keystones in a channelled stone ground floor, tall box sashes in stone architraves with alternating triangular and segmental pediments (first floor) and keyed heads (second floor), small attic lights - a columned Baroque doorcase with segmental pediment and steps in the middle of the Exhibition Road front (entrance per Wikipedia; exact bay assumed), stepped main cornice with modillions, kit balustrade with dies and urns, and a corner pavilion with oculi, a lathe-turned drum, lead dome, lantern and gilded finial. Rear/west faces keep painted elevations.',
  build({ THREE, kit, byId }) {
    const main = byId['f84e24cc-0cba-4bcb-a8dc-9c39610db775'];
    const link = byId['22d8e5b3-c1a4-4dbb-841a-dfd4e76aec40'];
    const ring = ccw(main.polys[0][0]);
    const H = main.h,
      gf = 4.6,
      cornice = H - 3.1,
      storey = (cornice - gf) / 2;
    const b = new kit.MeshBatch();
    const stone = kit.mat('#e0d9c7'),
      stone2 = kit.mat('#d4ccb8'),
      roofM = kit.roof('slate', 1),
      dark = kit.mat('dark_glass'),
      white = kit.mat('#f0ede6'),
      lead = kit.mat('#6f777b', { roughness: 0.55, metalness: 0.3 }),
      gold = kit.mat('gold'),
      doorM = kit.mat('#1f2b33'),
      brickPlain = kit.mat('#99493a'),
      iron = kit.mat('#1d2022', { roughness: 0.5 });
    const groundM = kit.paintedMaterial('imperial_dyson_building:ground', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2501);
      noiseFill(c, w, h, '#ddd5c2', r, 0.06, 4);
      c.fillStyle = 'rgba(90,80,60,0.35)';
      for (let y = 0; y < h; y += 18) c.fillRect(0, y, w, 2);
      const cw = w / 4;
      for (let i = 0; i < 4; i++) {
        const ww = cw * 0.66,
          x = i * cw + (cw - ww) / 2,
          y = h * 0.14,
          hh = h * 0.7;
        c.fillStyle = '#e9e3d4';
        c.fillRect(x - 6, y - 6, ww + 12, hh + 10);
        glassPane(c, x, y + 10, ww, hh - 10, r, [40, 54, 64]);
        c.beginPath();
        c.ellipse(x + ww / 2, y + 12, ww / 2, 14, 0, Math.PI, 0);
        c.fill();
        c.fillStyle = '#efece4';
        for (let k = 1; k < 4; k++) c.fillRect(x + (ww * k) / 4 - 1, y, 2, hh);
        c.fillRect(x, y + hh * 0.38, ww, 2);
        c.fillStyle = '#f0ebe0';
        c.fillRect(x + ww / 2 - 8, y - 8, 16, 18);
      }
    });
    const upperM = kit.paintedMaterial('imperial_dyson_building:upper', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3501);
      brickCourses(c, w, h, r, '#9c4c38', 3);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.4,
            wh = ch * 0.68,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.16;
          c.fillStyle = '#e2dbc9';
          c.fillRect(wx - 8, wy - 9, ww + 16, wh + 15);
          c.fillRect(wx - 11, wy - 14, ww + 22, 7);
          sash(c, wx, wy, ww, wh, r, { panesX: 2, panesY: 1, bar: 2 });
        }
    });
    const atticM = kit.paintedMaterial('imperial_dyson_building:attic', 512, 128, (c, w, h) => {
      const r = kit.rng(0.4501);
      brickCourses(c, w, h, r, '#9c4c38', 3);
      const cw = w / 4;
      for (let i = 0; i < 4; i++) {
        const ww = cw * 0.4,
          wx = i * cw + (cw - ww) / 2;
        c.fillStyle = '#e2dbc9';
        c.fillRect(wx - 6, h * 0.22 - 6, ww + 12, h * 0.55 + 10);
        sash(c, wx, h * 0.22, ww, h * 0.5, r, { panesX: 2, panesY: 1, bar: 2 });
      }
    });
    const brickM = kit.paintedMaterial('imperial_dyson_building:brick', 256, 256, (c, w, h) => {
      const r = kit.rng(0.3502);
      brickCourses(c, w, h, r, '#9c4c38', 3);
    });
    const rustic = kit.paintedMaterial('imperial_dyson_building:rustic', 256, 256, (c, w, h) => {
      const r = kit.rng(0.2502);
      noiseFill(c, w, h, '#ddd5c2', r, 0.06, 4);
      c.fillStyle = 'rgba(80,70,50,0.45)';
      for (let y = 0; y < h; y += 20) c.fillRect(0, y, w, 3);
    });
    const es = ringEdges(ring);
    const street = (e) => (e.ny > 0.7 || e.nx > 0.7) && e.len > 8;
    const detailed = (e) => e.nx > -0.7 && e.len > 6;
    const entranceEdge = es.filter((e) => e.nx > 0.7).sort((p, q) => q.len - p.len)[0];
    const atticZ0 = cornice + 0.6,
      atticZ1 = H - 0.9;
    for (const e of es) {
      if (!detailed(e)) {
        wallQuad(b, groundM, e.a, e.b, 0, gf, { bay: 4.4, storey: gf / 2 });
        wallQuad(b, upperM, e.a, e.b, gf, cornice, { bay: 4.4, storey, uvBase: gf });
        wallQuad(b, atticM, e.a, e.b, atticZ0, atticZ1, {
          bay: 4.4,
          storey: (atticZ1 - atticZ0) / 2,
          uvBase: atticZ0,
        });
        continue;
      }
      const n = Math.max(1, Math.round((e.len - 1.6) / 4.4));
      const doorK = e === entranceEdge ? Math.floor(n / 2) : -1;
      const opt = { margin: 0.8 };
      // Ground floor: big segmental-headed casements.
      const gh = bayHoles(e, n, 2.3, 0.9, gf - 0.5, { ...opt, skip: (k) => k === doorK });
      let doorT = -1;
      if (doorK >= 0) {
        doorT = 0.8 + ((e.len - 1.6) * (doorK + 0.5)) / n;
        gh.push({ t0: doorT - 1.1, t1: doorT + 1.1, zb: 0.6, zt: 3.9, door: true, d: 0.55 });
      }
      punchedWall(b, rustic, stone2, e, 0, gf, gh, { d: 0.4, tile: [7.2, 7.2], back: stone2 });
      for (const h of gh) {
        const tm = (h.t0 + h.t1) / 2,
          w = h.t1 - h.t0;
        if (h.door) {
          boxOn(kit, b, doorM, e, tm, -0.52, h.zb, w - 0.3, 0.06, 2.7);
          for (const s of [-1, 1])
            for (const z of [0.2, 1.4])
              boxOn(kit, b, kit.mat('#2a3842'), e, tm + s * 0.45, -0.48, h.zb + z, 0.7, 0.03, 1.0);
          boxOn(kit, b, dark, e, tm, -0.52, h.zb + 2.8, w - 0.3, 0.05, h.zt - h.zb - 2.85);
          for (let i = -2; i <= 2; i++)
            boxOn(
              kit,
              b,
              white,
              e,
              tm + i * 0.36,
              -0.49,
              h.zb + 2.8,
              0.05,
              0.05,
              h.zt - h.zb - 2.85,
            );
          boxOn(kit, b, white, e, tm, -0.49, h.zb + 2.7, w - 0.2, 0.1, 0.1);
          // paired Ionic-ish columns, broken entablature and segmental pediment
          for (const s of [-1, 1])
            for (const k of [0, 1]) {
              const p = pointOn(e, tm + s * (1.55 + k * 0.75), 0.5);
              const col = new THREE.CylinderGeometry(0.22, 0.26, 3.9, 14).rotateX(Math.PI / 2);
              b.addGeometry(
                stone,
                col,
                new THREE.Matrix4().makeTranslation(p[0], p[1], 0.6 + 1.95),
              );
              col.dispose();
              kit.box(b, stone, p[0], p[1], 0.3, 0.65, 0.65, 0.3, e.ang);
              kit.box(b, stone, p[0], p[1], 4.5, 0.7, 0.7, 0.18, e.ang);
            }
          boxOn(kit, b, stone, e, tm, 0.5, 4.68, 5.4, 1.0, 0.7);
          boxOn(kit, b, stone, e, tm, 0.55, 5.38, 5.8, 1.1, 0.15);
          const p = pointOn(e, tm, 0.5);
          segment(THREE, b, stone, p[0], p[1], 5.53, 5.8, 1.0, 1.0, e.ang);
          boxOn(kit, b, stone, e, tm, 0.1, 3.9, 0.55, 0.25, 0.75); // keystone
          stepsOn(kit, b, stone2, e, tm, 5.0, 4, { rise: 0.15, tread: 0.36 });
          // lamps on the doorcase piers
          for (const s of [-1, 1]) {
            const q = pointOn(e, tm + s * 2.8, 0.9);
            kit.box(b, iron, q[0], q[1], 0.6, 0.12, 0.12, 2.2, e.ang);
            kit.box(
              b,
              kit.mat('#fff1c8', { emissive: new THREE.Color('#ffe2a0'), emissiveIntensity: 0.4 }),
              q[0],
              q[1],
              2.8,
              0.35,
              0.35,
              0.55,
              e.ang,
            );
            kit.box(b, iron, q[0], q[1], 3.35, 0.45, 0.45, 0.08, e.ang);
          }
          continue;
        }
        fitWindow(kit, b, e, h, { d: 0.4, glass: dark, frame: white, sill: white, bars: 2 });
        boxOn(kit, b, stone, e, tm, 0.04, h.zt - 0.1, w + 0.7, 0.08, 0.35); // voussoir band
        boxOn(kit, b, stone, e, tm, 0.08, h.zt - 0.3, 0.45, 0.16, 0.7); // keystone
        boxOn(kit, b, stone, e, tm, 0.08, h.zb - 0.16, w + 0.4, 0.24, 0.16); // sill
      }
      // Upper floors: tall box sashes in stone architraves.
      const uh = [];
      for (let s = 0; s < 2; s++) {
        const zb = gf + s * storey + (s ? 0.55 : 0.8);
        for (const h of bayHoles(e, n, 1.35, zb, zb + (s ? 2.0 : 2.4), opt)) uh.push({ ...h, s });
      }
      punchedWall(b, brickM, stone, e, gf, cornice, uh, {
        d: 0.3,
        tile: [7.2, 7.2],
        uvBase: gf,
        back: dark,
      });
      for (const h of uh) {
        const tm = (h.t0 + h.t1) / 2,
          w = h.t1 - h.t0;
        fitWindow(kit, b, e, h, { d: 0.3, glass: dark, frame: white, sill: white, bars: 1 });
        boxOn(kit, b, white, e, tm, -0.22, h.zb + (h.zt - h.zb) * 0.5, w - 0.08, 0.08, 0.07);
        for (const s of [-1, 1])
          boxOn(
            kit,
            b,
            stone,
            e,
            tm + s * (w / 2 + 0.13),
            0.05,
            h.zb - 0.05,
            0.26,
            0.1,
            h.zt - h.zb + 0.1,
          );
        boxOn(kit, b, stone, e, tm, 0.05, h.zt + 0.05, w + 0.52, 0.1, 0.28);
        boxOn(kit, b, stone, e, tm, 0.1, h.zb - 0.18, w + 0.6, 0.22, 0.16);
        if (h.s === 0) {
          boxOn(kit, b, stone, e, tm, 0.15, h.zt + 0.33, w + 0.9, 0.34, 0.14);
          const p = pointOn(e, tm, 0.15);
          if (h.k % 2)
            segment(THREE, b, stone, p[0], p[1], h.zt + 0.47, w + 0.9, 0.38, 0.34, e.ang);
          else pediment(THREE, b, stone, p[0], p[1], h.zt + 0.47, w + 0.9, 0.48, 0.34, e.ang);
        } else boxOn(kit, b, stone, e, tm, 0.1, h.zt + 0.02, 0.36, 0.18, 0.5);
        // apron panel under the first-floor windows
        if (h.s === 0) boxOn(kit, b, stone, e, tm, 0.03, h.zb - 0.75, w, 0.06, 0.5);
      }
      // Attic storey: small square lights.
      const ah = bayHoles(e, n, 1.1, atticZ0 + 0.45, atticZ1 - 0.45, opt);
      punchedWall(b, brickM, stone, e, atticZ0, atticZ1, ah, {
        d: 0.22,
        tile: [7.2, 7.2],
        uvBase: atticZ0,
        back: dark,
      });
      for (const h of ah) {
        fitWindow(kit, b, e, h, { d: 0.22, glass: dark, frame: white, sill: white, bars: 1 });
        boxOn(
          kit,
          b,
          stone,
          e,
          (h.t0 + h.t1) / 2,
          0.05,
          h.zb - 0.12,
          h.t1 - h.t0 + 0.4,
          0.14,
          0.12,
        );
      }
      // brick pilaster strips with stone caps between the attic lights
      for (let k = 0; k <= n; k++) {
        const t = 0.8 + ((e.len - 1.6) * k) / n;
        boxOn(kit, b, brickPlain, e, t, 0.08, atticZ0, 0.7, 0.16, atticZ1 - atticZ0);
        boxOn(kit, b, stone, e, t, 0.1, atticZ1 - 0.3, 0.85, 0.22, 0.3);
      }
    }
    kit.cornice(b, stone, ring, gf - 0.3, { height: 0.45, projection: 0.2, steps: 2 });
    kit.cornice(b, stone, ring, cornice - 0.35, { height: 0.3, projection: 0.15 });
    kit.cornice(b, stone, ring, cornice, { height: 0.6, projection: 0.65, steps: 3 });
    for (const e of ringEdges(kit.offsetRing(ring, 0.35))) {
      const n = Math.floor(e.len / 0.75);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n));
        kit.box(b, stone, p[0], p[1], cornice - 0.25, 0.18, 0.55, 0.25, e.ang);
      }
    }
    kit.cornice(b, stone2, ring, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(b, stone, ring, atticZ1 - 0.1, { height: 0.25, projection: 0.25, steps: 2 });
    // Stone quoins at every corner of the upper floors.
    for (const e of es)
      for (let z = gf, k = 0; z < cornice - 0.2; z += 0.55, k++) {
        const w1 = k % 2 ? 1.0 : 0.6;
        kit.box(b, k % 3 ? stone : stone2, e.a[0], e.a[1], z, w1, w1, 0.53, e.ang);
      }
    // Balustraded parapet with dies; urns on the street-front dies.
    const urn = new THREE.LatheGeometry(
      [
        [0.001, 0],
        [0.22, 0],
        [0.22, 0.08],
        [0.1, 0.18],
        [0.12, 0.25],
        [0.26, 0.45],
        [0.24, 0.62],
        [0.14, 0.7],
        [0.18, 0.76],
        [0.06, 0.84],
        [0.08, 0.95],
        [0.001, 1.0],
      ].map(([r, z]) => new THREE.Vector2(r, z)),
      10,
    ).rotateX(Math.PI / 2);
    for (const e of es) {
      const a = pointOn(e, 0, 0.22),
        q = pointOn(e, e.len, 0.22);
      kit.balustrade(b, stone, [a, q], H - 0.9, { height: 0.9, spacing: 0.32 });
      const nd = Math.max(1, Math.round(e.len / 4.4));
      for (let i = 0; i <= nd; i++) {
        const p = pointOn(e, (i / nd) * e.len, 0.22);
        kit.box(b, stone, p[0], p[1], H - 0.9, 0.6, 0.6, 1.05, e.ang);
        kit.box(b, stone, p[0], p[1], H + 0.15, 0.7, 0.7, 0.1, e.ang);
        if (street(e) && i % 2 === 0)
          b.addGeometry(stone, urn, new THREE.Matrix4().makeTranslation(p[0], p[1], H + 0.25));
      }
    }
    urn.dispose();
    kit.cap(b, kit.roof('flat', 1), [[ring]], H - 0.9);
    // Corner pavilion at Exhibition Road / Imperial College Road (north-east corner).
    const ne = ring.reduce((q, p) => (p[0] + p[1] > q[0] + q[1] ? p : q), ring[0]);
    const north = es.slice().sort((p, q) => q.ny - p.ny)[0];
    const ang = north.ang;
    const sgn = Math.hypot(north.a[0] - ne[0], north.a[1] - ne[1]) < 0.5 ? 1 : -1;
    const pc = [
      ne[0] + sgn * north.tx * 3.6 - north.nx * 3.6,
      ne[1] + sgn * north.ty * 3.6 - north.ny * 3.6,
    ];
    const pz0 = cornice + 0.6,
      pz1 = H + 1.4;
    kit.box(b, stone, pc[0], pc[1], pz0, 7.6, 7.6, pz1 - pz0, ang);
    // rusticated pilasters at the pavilion corners
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    for (const [su, sv] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ]) {
      const x = pc[0] + ca * su * 3.6 - sa * sv * 3.6,
        y = pc[1] + sa * su * 3.6 + ca * sv * 3.6;
      for (let z = pz0, k = 0; z < pz1 - 0.3; z += 0.45, k++)
        kit.box(b, k % 2 ? stone : stone2, x, y, z, 1.0, 1.0, 0.4, ang);
    }
    kit.box(b, stone, pc[0], pc[1], pz1, 8.3, 8.3, 0.35, ang);
    kit.box(b, stone, pc[0], pc[1], pz1 + 0.35, 7.8, 7.8, 0.25, ang);
    for (const [nx, ny] of [
      [north.nx, north.ny],
      [north.ny, -north.nx],
      [-north.ny, north.nx],
    ]) {
      const ring2 = new THREE.TorusGeometry(0.9, 0.16, 6, 20);
      const disc = new THREE.CylinderGeometry(0.78, 0.78, 0.1, 20).rotateX(Math.PI / 2);
      const rot = new THREE.Matrix4()
        .makeRotationZ(Math.atan2(ny, nx) + Math.PI / 2)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      const zc = (pz0 + pz1) / 2;
      const t = new THREE.Matrix4().makeTranslation(pc[0] + nx * 3.85, pc[1] + ny * 3.85, zc);
      b.addGeometry(stone, ring2, t.clone().multiply(rot));
      b.addGeometry(
        dark,
        disc,
        new THREE.Matrix4().makeTranslation(pc[0] + nx * 3.81, pc[1] + ny * 3.81, zc).multiply(rot),
      );
      // cross glazing bars and four keystones
      kit.box(
        b,
        white,
        pc[0] + nx * 3.84,
        pc[1] + ny * 3.84,
        zc - 0.78,
        0.06,
        0.06,
        1.56,
        Math.atan2(ny, nx),
      );
      kit.box(
        b,
        white,
        pc[0] + nx * 3.84,
        pc[1] + ny * 3.84,
        zc - 0.03,
        0.06,
        1.56,
        0.06,
        Math.atan2(ny, nx),
      );
      kit.box(
        b,
        stone,
        pc[0] + nx * 3.9,
        pc[1] + ny * 3.9,
        zc + 0.75,
        0.35,
        0.3,
        0.45,
        Math.atan2(ny, nx),
      );
      ring2.dispose();
      disc.dispose();
    }
    // Drum, lead dome, lantern and gilded finial.
    const dz = pz1 + 0.6;
    b.addGeometry(
      stone,
      new THREE.CylinderGeometry(2.4, 2.5, 1.3, 24).rotateX(Math.PI / 2),
      new THREE.Matrix4().makeTranslation(pc[0], pc[1], dz + 0.65),
    );
    b.addGeometry(
      stone,
      new THREE.CylinderGeometry(2.65, 2.65, 0.2, 24).rotateX(Math.PI / 2),
      new THREE.Matrix4().makeTranslation(pc[0], pc[1], dz + 1.4),
    );
    const domeProfile = [];
    for (let i = 0; i <= 10; i++) {
      const a = (i / 10) * (Math.PI / 2);
      domeProfile.push([2.4 * Math.cos(a), 2.6 * Math.sin(a)]);
    }
    const dome = kit.lathe(lead, domeProfile, { x: pc[0], y: pc[1], z: dz + 1.5, segments: 24 });
    // ribs
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2;
      for (let i = 0; i < 6; i++) {
        const t0 = (i / 6) * (Math.PI / 2),
          t1 = ((i + 1) / 6) * (Math.PI / 2);
        const r0 = 2.42 * Math.cos(t0),
          r1 = 2.42 * Math.cos(t1);
        const z0 = 2.62 * Math.sin(t0),
          z1 = 2.62 * Math.sin(t1);
        const len = Math.hypot(r1 - r0, z1 - z0);
        const geo = new THREE.BoxGeometry(0.1, 0.1, len);
        const m = new THREE.Matrix4()
          .makeTranslation(
            pc[0] + (Math.cos(a) * (r0 + r1)) / 2,
            pc[1] + (Math.sin(a) * (r0 + r1)) / 2,
            dz + 1.5 + (z0 + z1) / 2,
          )
          .multiply(new THREE.Matrix4().makeRotationZ(a))
          .multiply(new THREE.Matrix4().makeRotationY(Math.atan2(r1 - r0, z1 - z0)));
        b.addGeometry(lead, geo, m);
        geo.dispose();
      }
    }
    const lz = dz + 1.5 + 2.5;
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2;
      kit.box(
        b,
        stone,
        pc[0] + Math.cos(a) * 0.55,
        pc[1] + Math.sin(a) * 0.55,
        lz,
        0.14,
        0.14,
        1.1,
        a,
      );
    }
    b.addGeometry(
      dark,
      new THREE.CylinderGeometry(0.48, 0.48, 1.1, 12).rotateX(Math.PI / 2),
      new THREE.Matrix4().makeTranslation(pc[0], pc[1], lz + 0.55),
    );
    const lantern = kit.lathe(
      lead,
      [
        [0.75, 0],
        [0.75, 0.12],
        [0.62, 0.15],
        [0.62, 0.25],
        [0.35, 0.6],
        [0.08, 0.95],
        [0.001, 1.0],
      ],
      { x: pc[0], y: pc[1], z: lz + 1.1, segments: 12 },
    );
    const finial = kit.lathe(
      gold,
      [
        [0.12, 0],
        [0.05, 0.3],
        [0.16, 0.42],
        [0.16, 0.55],
        [0.04, 0.68],
        [0.03, 1.3],
        [0.001, 1.35],
      ],
      { x: pc[0], y: pc[1], z: lz + 2.05, segments: 10 },
    );
    // Slate mansard behind the balustrade, flat lead crown, stacks and rooflights.
    {
      const r0 = kit.offsetRing(ring, -0.7),
        r1 = kit.offsetRing(ring, -3.2);
      const z0 = H - 0.9,
        z1 = H + 1.5;
      for (let k = 0; k < r0.length; k++) {
        const k2 = (k + 1) % r0.length;
        const A = [...r0[k], z0],
          B = [...r0[k2], z0],
          C = [...r1[k2], z1],
          D = [...r1[k], z1];
        const dx = B[0] - A[0],
          dy = B[1] - A[1],
          l = Math.hypot(dx, dy) || 1;
        quadN(
          b,
          roofM,
          [A, B, C, D],
          [
            [0, 0],
            [l / 3, 0],
            [l / 3, 1],
            [0, 1],
          ],
          [dy / l, -dx / l, 0.8],
        );
      }
      kit.cap(b, lead, [[r1]], z1);
      for (const e of es.filter((e) => e.len > 20)) {
        for (const t of [0.3, 0.7]) {
          const p = pointOn(e, e.len * t, -4.5);
          kit.box(b, brickPlain, p[0], p[1], z1, 0.9, 2.0, 1.8, e.ang);
          kit.box(b, stone, p[0], p[1], z1 + 1.8, 1.1, 2.2, 0.2, e.ang);
        }
        // dormers on the mansard slope over each bay
        const n = Math.max(1, Math.round((e.len - 1.6) / 4.4));
        for (let k = 0; k < n; k++) {
          const t = 0.8 + ((e.len - 1.6) * (k + 0.5)) / n;
          const p = pointOn(e, t, -1.9);
          kit.box(b, lead, p[0], p[1], z0 + 0.2, 1.2, 1.4, 1.5, e.ang);
          const q = pointOn(e, t, -1.18);
          kit.box(b, dark, q[0], q[1], z0 + 0.45, 0.8, 0.04, 0.95, e.ang);
          kit.box(b, white, q[0], q[1], z0 + 0.9, 0.8, 0.06, 0.05, e.ang);
        }
      }
    }
    // Low glazed link to the west with mullions.
    if (link) {
      const lr = ccw(link.polys[0][0]);
      const alu = kit.mat('aluminium');
      kit.walls(b, kit.mat('glass'), [[kit.offsetRing(lr, -0.05)]], 0, link.h - 0.4);
      kit.walls(b, alu, [[lr]], link.h - 0.4, link.h);
      kit.cap(b, alu, [[lr]], link.h);
      for (const e of ringEdges(lr)) {
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let i = 0; i <= n; i++)
          boxOn(kit, b, alu, e, (i * e.len) / n, 0.0, 0, 0.06, 0.12, link.h - 0.4);
      }
    }
    // Railings along the area of the Imperial College Road front.
    railing(kit, b, iron, pointOn(north, 0.5, 1.4), pointOn(north, north.len - 0.5, 1.4), 0, {
      h: 1.05,
    });
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_dyson_building'));
    g.add(dome, lantern, finial);
    return g;
  },
};
