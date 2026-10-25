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
      used_for: 'designed by Arup Associates to blend with surrounding architecture',
    },
    {
      title:
        'Boris Johnson opens restored London square after £160m investment by Imperial College London',
      url: 'https://www.imperial.ac.uk/news/80641/boris-johnson-opens-restored-london-square/',
      used_for: "sports centre as part of the Prince's Gardens redevelopment",
    },
  ],
  notes:
    'No facade description was found by search; the glazed south front (per the brief), stone flanks and canopies are approximate. Height 17.2 m from Overture.',
  build({ THREE, kit, buildings }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      storey = (H - 1.0) / 4;
    const b = new kit.MeshBatch();
    const stone = kit.mat('#ddd5c1'),
      alu = kit.mat('#c8ccce', { roughness: 0.45 }),
      roofM = kit.roof('flat', 2),
      dark = kit.mat('#3a4247');
    const glazing = kit.paintedMaterial('imperial_ethos:glazing', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2006);
      // interior: lit gym / studio floors seen through the glass
      for (let j = 0; j < 2; j++) {
        const y = j * (h / 2);
        const grd = c.createLinearGradient(0, y, 0, y + h / 2);
        grd.addColorStop(0, '#6f8796');
        grd.addColorStop(0.7, '#4c6170');
        grd.addColorStop(1, '#3a4a55');
        c.fillStyle = grd;
        c.fillRect(0, y, w, h / 2);
        c.fillStyle = 'rgba(240,235,210,0.35)'; // ceiling lights
        for (let i = 0; i < 8; i++) c.fillRect(i * 64 + 12, y + 8, 40, 3);
        c.fillStyle = 'rgba(30,30,35,0.55)'; // equipment silhouettes
        for (let i = 0; i < 10; i++)
          if (r() < 0.6) c.fillRect(i * 51 + r() * 20, y + h / 2 - 34, 18 + r() * 14, 26);
        c.fillStyle = '#d0d4d6';
        c.fillRect(0, y + h / 2 - 7, w, 7); // floor edge
      }
      c.fillStyle = '#b9bfc2';
      for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 2, 0, 4, h);
      c.fillStyle = 'rgba(255,255,255,0.10)';
      for (let i = 0; i < 8; i++) c.fillRect(i * 64 + 6, 0, 18, h);
    });
    const flank = kit.paintedMaterial('imperial_ethos:flank', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3006);
      noiseFill(c, w, h, '#ddd5c1', r, 0.05, 4);
      c.fillStyle = 'rgba(110,100,80,0.18)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 1);
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 1, h);
      for (let i = 0; i < 4; i++) glassPane(c, i * 128 + 54, 16, 20, h - 32, r, [44, 58, 68]);
    });
    const front = (e) => e.ny < -0.8 && e.len > 20;
    edgeWalls(b, ring, 0, H - 1.0, (e) =>
      front(e) ? { m: glazing, bay: 3.0, storey, uvBase: 0 } : { m: flank, bay: 3.6, storey: 3.2 },
    );
    parapet(kit, b, stone, ring, H - 1.0, 1.0, 0.4);
    kit.cap(b, roofM, [[ring]], H - 0.99);
    for (const e of ringEdges(ring)) {
      if (!front(e)) continue;
      // stone frame around the glazed front and a thin roof canopy
      finsAlong(kit, b, stone, e, 0, H, e.len, 0.8, 1.2, { skipEnds: false });
      barAlong(kit, b, alu, e, H - 0.2, 0.25, 2.4, -0.6);
      // slender external mullions every 3 m
      finsAlong(kit, b, alu, e, 0.3, H - 1.2, 3.0, 0.35, 0.12);
      // entrance canopy and doors towards the west end
      const p = pointOn(e, e.len * 0.3, 2.0);
      kit.box(b, alu, p[0], p[1], 3.6, 9, 4.0, 0.35, e.ang);
      const d = pointOn(e, e.len * 0.3, 0.06);
      kit.box(b, dark, d[0], d[1], 0, 5, 0.1, 2.8, e.ang);
    }
    // Rooftop plant enclosure (pool hall air handling).
    const fr = kit.ringFrame(ring);
    const ex = kit.orientedExtent(ring, fr.angle);
    const pc = ex.at((ex.u0 + ex.u1) / 2, (ex.v0 + ex.v1) / 2, 0);
    const louvre = kit.paintedMaterial('imperial_ethos:louvre', 128, 128, (c, w, h) => {
      c.fillStyle = '#9da3a6';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#6c7376';
      for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 3);
    });
    kit.box(b, louvre, pc[0], pc[1], H - 1.0, 18, 10, 3.0, fr.angle);
    kit.box(b, alu, pc[0], pc[1], H + 2.0, 18.4, 10.4, 0.25, fr.angle);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_ethos'));
    return g;
  },
};
