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
  ],
  notes:
    'No facade description found; elevation (concrete mullion fins, dark spandrels, brick ends) is a reconstruction in the 1960s ACP idiom, not traced from photos. Height 23.2 m from Overture (7 floors).',
  build({ THREE, kit, buildings, frame }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 3.8,
      storey = (H - 1.0 - gf) / 6;
    const b = new kit.MeshBatch();
    const conc = kit.mat('#d3cec3'),
      brick = kit.mat('#8d6450'),
      roofM = kit.roof('flat', 2),
      flueM = kit.mat('#aab0b4', { roughness: 0.5 });
    const bays = kit.paintedMaterial('imperial_sir_ernst_chain:bays', 512, 256, (c, w, h) => {
      const r = kit.rng(0.5523);
      noiseFill(c, w, h, '#d3cec3', r, 0.06, 4);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const x = i * cw + cw * 0.08,
            y = j * ch + 3,
            ww = cw * 0.84,
            hh = ch * 0.68;
          glassPane(c, x, y, ww, hh, r, [36, 46, 54]);
          c.fillStyle = '#c4c0b6';
          c.fillRect(x + ww / 2 - 1.5, y, 3, hh);
          c.fillRect(x, y + hh * 0.72, ww, 2);
          c.fillStyle = '#4a4f52'; // dark spandrel panel
          c.fillRect(x, y + hh + 3, ww, ch - hh - 9);
        }
    });
    const groundM = kit.paintedMaterial('imperial_sir_ernst_chain:ground', 512, 256, (c, w, h) => {
      const r = kit.rng(0.12);
      glassPane(c, 0, 0, w, h, r, [55, 70, 80]);
      c.fillStyle = '#d3cec3';
      for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 3, 0, 6, h);
      c.fillRect(0, 0, w, 8);
    });
    // Ground floor set back 1 m.
    const inner = kit.offsetRing(ring, -1.0);
    edgeWalls(b, inner, 0, gf, () => ({ m: groundM, bay: 3.6, storey: gf / 2 }));
    kit.cap(b, conc, [[ring]], gf, { down: true });
    const top = H - 1.0;
    edgeWalls(b, ring, gf, top, (e) =>
      e.len > 8 ? { m: bays, bay: 1.6, storey, uvBase: gf } : { m: brick },
    );
    // Projecting precast mullion fins on the long elevations, full height of the upper floors.
    for (const e of ringEdges(ring)) {
      if (e.len < 8) continue;
      finsAlong(kit, b, conc, e, gf - 0.3, top + 0.2, 1.6 * 2, 0.45, 0.3);
      barAlong(kit, b, conc, e, gf - 0.5, 0.5, 0.5);
    }
    parapet(kit, b, conc, ring, top, 1.0, 0.3);
    kit.cap(b, roofM, [[ring]], top + 0.01);
    // Rooftop plant room, lift motor room and extract stacks.
    const ex = kit.orientedExtent(ring, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const pr = at((ex.u0 + ex.u1) / 2 - 3, (ex.v0 + ex.v1) / 2);
    kit.box(b, brick, pr[0], pr[1], H - 1, 18, 7, 4.2, frame.angle);
    kit.box(b, conc, pr[0], pr[1], H + 3.2, 18.4, 7.4, 0.3, frame.angle);
    const lm = at(ex.u1 - 6, (ex.v0 + ex.v1) / 2 + 2);
    kit.box(b, brick, lm[0], lm[1], H - 1, 4.5, 5, 5.5, frame.angle);
    const flue = new THREE.CylinderGeometry(0.3, 0.3, 1, 10).rotateX(Math.PI / 2);
    for (let i = 0; i < 8; i++) {
      const p = at(ex.u0 + 6 + i * 3, ex.v1 - 2.5);
      b.addGeometry(
        flueM,
        flue,
        new THREE.Matrix4()
          .makeScale(1, 1, 4.5)
          .premultiply(new THREE.Matrix4().makeTranslation(p[0], p[1], H + 1.2)),
      );
    }
    flue.dispose();
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_sir_ernst_chain'));
    return g;
  },
};
