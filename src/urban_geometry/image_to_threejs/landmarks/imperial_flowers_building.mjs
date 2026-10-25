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
    'No facade description was returned by searches; the aluminium-band / louvre elevation and rooftop flues follow Foster lab buildings of that period and are approximate. Main block 29.6 m (9 floors) and west wing 7.2 m from the Overture outline and part.',
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
    // Main block = outline minus the west wing (shared edge 1547.2,-984.1 -> 1549.5,-1004.0).
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
    const alu = kit.mat('#c9ced1', { roughness: 0.45 }),
      alu2 = kit.mat('#aeb5b9', { roughness: 0.5 }),
      glass = kit.mat('glass'),
      roofM = kit.roof('flat', 0),
      flueM = kit.mat('#c4c9cc', { roughness: 0.35 });
    const storey = (H - 2.0) / 9;
    const bandM = kit.paintedMaterial('imperial_flowers_building:band', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3298);
      for (let j = 0; j < 2; j++) {
        const y = j * (h / 2);
        // aluminium spandrel panel (lower 35%), glazing above (65%)
        c.fillStyle = '#c9ced1';
        c.fillRect(0, y, w, h / 2);
        glassPane(c, 0, y + 2, w, (h / 2) * 0.62, r, [62, 84, 98]);
        c.fillStyle = '#e0e3e5';
        for (let i = 0; i <= 12; i++) c.fillRect((i * w) / 12 - 1, y + 2, 2, (h / 2) * 0.62);
        c.fillStyle = 'rgba(0,0,0,0.15)';
        for (let i = 0; i <= 6; i++)
          c.fillRect((i * w) / 6 - 0.5, y + (h / 2) * 0.64, 1, (h / 2) * 0.36);
        c.fillRect(0, y + (h / 2) * 0.82, w, 1);
      }
    });
    const endM = kit.paintedMaterial('imperial_flowers_building:end', 256, 256, (c, w, h) => {
      const r = kit.rng(0.77);
      noiseFill(c, w, h, '#c3c8cb', r, 0.04, 4);
      c.fillStyle = 'rgba(0,0,0,0.12)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 1);
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 1, h);
      glassPane(c, w * 0.42, 0, w * 0.16, h, r, [62, 84, 98]); // glazed stair slot
    });
    const top = H - 2.0;
    // Glazed, recessed ground floor.
    const gIn = kit.offsetRing(main, -0.8);
    kit.walls(b, glass, [[gIn]], 0, storey);
    kit.cap(b, alu, [[main]], storey, { down: true });
    edgeWalls(b, main, storey, top, (e) =>
      e.len > 14
        ? { m: bandM, bay: 3.6, storey, uvBase: storey }
        : { m: endM, bay: e.len, storey: e.len / 2 },
    );
    // External horizontal louvre blades on the long elevations, one per floor.
    for (const e of ringEdges(main)) {
      if (e.len < 14) continue;
      for (let k = 1; k < 9; k++) barAlong(kit, b, alu2, e, storey * (k + 0.95), 0.12, 1.1, 0.6);
      // slender vertical outriggers that carry the blades
      finsAlong(kit, b, alu2, e, storey, top, 7.2, 1.1, 0.12);
    }
    // Roof: plant enclosure clad in louvres, and a row of stainless steel flues.
    kit.cap(b, roofM, [[main]], top);
    parapet(kit, b, alu, main, top, 0.9, 0.25);
    const louvre = kit.paintedMaterial('imperial_flowers_building:louvre', 128, 128, (c, w, h) => {
      c.fillStyle = '#b8bec2';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#7f878b';
      for (let y = 0; y < h; y += 6) c.fillRect(0, y, w, 2);
    });
    const ex = kit.orientedExtent(main, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const um = (ex.u0 + ex.u1) / 2,
      vm = (ex.v0 + ex.v1) / 2;
    const pc = at(um + 1, vm);
    kit.box(b, louvre, pc[0], pc[1], top, ex.u1 - ex.u0 - 10, 7.5, 4.0, frame.angle);
    kit.box(b, alu, pc[0], pc[1], top + 4.0, ex.u1 - ex.u0 - 9.6, 7.9, 0.25, frame.angle);
    const flue = new THREE.CylinderGeometry(0.4, 0.4, 1, 12).rotateX(Math.PI / 2);
    const n = 10;
    for (let i = 0; i < n; i++) {
      const p = at(ex.u0 + 6 + (i * (ex.u1 - ex.u0 - 12)) / (n - 1), vm);
      b.addGeometry(
        flueM,
        flue,
        new THREE.Matrix4()
          .makeScale(1, 1, 4)
          .premultiply(new THREE.Matrix4().makeTranslation(p[0], p[1], top + 4.25 + 2)),
      );
    }
    flue.dispose();
    // West wing: glazed pavilion with an aluminium fascia.
    const glazed = kit.paintedMaterial('imperial_flowers_building:wing', 512, 256, (c, w, h) => {
      const r = kit.rng(0.41);
      glassPane(c, 0, 0, w, h, r, [70, 92, 104]);
      c.fillStyle = '#d7dbdd';
      for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 2, 0, 4, h);
      c.fillRect(0, h / 2 - 2, w, 4);
    });
    edgeWalls(b, wing, 0, wingH - 0.8, () => ({ m: glazed, bay: 1.8, storey: (wingH - 0.8) / 2 }));
    kit.walls(b, alu, [[wing]], wingH - 0.8, wingH);
    kit.cap(b, roofM, [[wing]], wingH);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_flowers_building'));
    return g;
  },
};
