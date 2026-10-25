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
  ],
  notes:
    'Banding rhythm, window sizes and the balustrade are generic Webb/Edwardian classical detail, not traced from photographs. The whole Overture footprint (which may include later infill behind the street range) is modelled in the same idiom. Height 12.9 m from Overture.',
  build({ THREE, kit, buildings }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 4.4,
      storey = (H - 1.3 - gf) / 2;
    const b = new kit.MeshBatch();
    const stone = kit.mat('portland_stone'),
      roofM = kit.roof('flat', 2),
      lead = kit.mat('lead');
    const upper = kit.paintedMaterial('imperial_chemistry_rcs1:upper', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1806);
      brickCourses(c, w, h, r, '#a0523c', 3);
      // stone banding: a broad band every ~0.8 m
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
          c.fillRect(wx + ww / 2 - 6, wy - 12, 12, 12); // keystone
          c.fillRect(wx - 10, wy + wh + 3, ww + 20, 5); // sill
          sash(c, wx, wy, ww, wh, r, { panesX: 2, panesY: 2, bar: 2 });
        }
    });
    const groundM = kit.paintedMaterial('imperial_chemistry_rcs1:ground', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2806);
      noiseFill(c, w, h, '#d8d0bc', r, 0.06, 4);
      c.fillStyle = 'rgba(80,70,55,0.35)';
      for (let y = 0; y < h; y += 21) c.fillRect(0, y, w, 2); // rustication joints
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
    edgeWalls(b, ring, 0, gf, (e) => ({ m: groundM, bay: 4.2, storey: gf / 2 }));
    edgeWalls(b, ring, gf, H - 1.3, (e) => ({ m: upper, bay: 4.2, storey, uvBase: gf }));
    band(kit, b, stone, ring, gf - 0.25, 0.4, 0.15); // first-floor string course
    band(kit, b, stone, ring, 0, 0.6, 0.12); // plinth
    // Modillion cornice.
    band(kit, b, stone, ring, H - 1.6, 0.6, 0.55);
    for (const e of ringEdges(kit.offsetRing(ring, 0.3))) {
      const n = Math.floor(e.len / 0.9);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n));
        kit.box(b, stone, p[0], p[1], H - 1.85, 0.2, 0.5, 0.25, e.ang);
      }
    }
    // Balustraded parapet on the street (north-facing) edges, plain parapet elsewhere.
    for (const e of ringEdges(ring)) {
      if (e.ny > 0.7 && e.len > 8) {
        barAlong(kit, b, stone, e, H - 1.0, 0.18, 0.5, 0);
        barAlong(kit, b, stone, e, H - 0.18, 0.18, 0.5, 0);
        const n = Math.floor(e.len / 0.45);
        const post = new THREE.CylinderGeometry(0.1, 0.15, 0.64, 6).rotateX(Math.PI / 2);
        for (let i = 0; i < n; i++) {
          const p = pointOn(e, (i + 0.5) * (e.len / n), 0.25);
          b.addGeometry(stone, post, new THREE.Matrix4().makeTranslation(p[0], p[1], H - 0.5));
        }
        post.dispose();
        for (let t = 0; t <= e.len; t += e.len / Math.max(1, Math.round(e.len / 5))) {
          const p = pointOn(e, Math.min(t, e.len), 0.25);
          kit.box(b, stone, p[0], p[1], H - 1.0, 0.6, 0.6, 1.1, e.ang);
        }
      } else wallQuad(b, stone, e.a, e.b, H - 1.0, H - 0.1);
    }
    kit.cap(b, roofM, [[ring]], H - 0.92);
    // Slate-and-lead roof lights over the former laboratories.
    const fr = kit.ringFrame(ring);
    const ex = kit.orientedExtent(ring, fr.angle);
    for (let i = 0; i < 3; i++) {
      const p = ex.at(
        ex.u0 + (ex.u1 - ex.u0) * (0.25 + i * 0.25),
        ex.v0 + (ex.v1 - ex.v0) * 0.55,
        0,
      );
      kit.box(b, lead, p[0], p[1], H - 1.0, 8, 4, 1.4, fr.angle);
      kit.box(b, kit.mat('glass'), p[0], p[1], H + 0.4, 7.4, 3.4, 0.5, fr.angle);
    }
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_chemistry_rcs1'));
    return g;
  },
};
