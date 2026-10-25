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
  ],
  notes:
    'No facade description was found; the ribbon-window / concrete-spandrel elevation, brick cores and rooftop extract stacks are a generic reconstruction of a 1960s ACP lab block, not traced from photos. Height 26.4 m from Overture (8 floors).',
  build({ THREE, kit, buildings, frame }) {
    const bld = buildings[0];
    const ring = ccw(bld.polys[0][0]);
    const H = bld.h,
      gf = 4.2,
      storey = (H - 1.2 - gf) / 7;
    const b = new kit.MeshBatch();
    const conc = kit.mat('#c9c4b8'),
      dconc = kit.mat('dark_concrete'),
      brick = kit.mat('#6e4a3a'),
      steel = kit.mat('#aab0b4', { roughness: 0.5 }),
      roofM = kit.roof('flat', 1);
    const ribbon = kit.paintedMaterial(
      'imperial_chemistry_building:ribbon',
      512,
      256,
      (c, w, h) => {
        const r = kit.rng(0.6868);
        noiseFill(c, w, h, '#c9c4b8', r, 0.07, 4);
        for (let j = 0; j < 2; j++) {
          const y = j * (h / 2);
          // window strip occupies the upper 58% of each storey
          const wy = y + 4,
            wh = (h / 2) * 0.56;
          glassPane(c, 0, wy, w, wh, r, [40, 52, 60]);
          c.fillStyle = '#d8d4ca';
          for (let i = 0; i <= 16; i++) c.fillRect((i * w) / 16 - 1.5, wy, 3, wh);
          c.fillStyle = 'rgba(255,255,255,0.10)';
          for (let i = 0; i < 16; i++)
            if (r() < 0.35) c.fillRect((i * w) / 16 + 2, wy + 2, w / 16 - 4, wh * 0.35);
          // spandrel panel joints
          c.fillStyle = 'rgba(0,0,0,0.18)';
          for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 0.5, wy + wh, 1, h / 2 - wh - 4);
          c.fillRect(0, wy + wh + 1, w, 2);
        }
      },
    );
    const ground = kit.paintedMaterial(
      'imperial_chemistry_building:ground',
      512,
      256,
      (c, w, h) => {
        const r = kit.rng(0.11);
        noiseFill(c, w, h, '#3a4248', r, 0.05, 4);
        glassPane(c, 0, h * 0.08, w, h * 0.84, r, [52, 68, 78]);
        c.fillStyle = '#9aa1a6';
        for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 2, 0, 4, h);
        c.fillRect(0, h * 0.5 - 2, w, 4);
      },
    );
    // Recessed glazed ground floor behind a line of columns.
    const inner = kit.offsetRing(ring, -1.2);
    edgeWalls(b, inner, 0, gf, () => ({ m: ground, bay: 3.6, storey: gf / 2 }));
    kit.cap(b, conc, [[ring]], gf, { down: true });
    for (const e of ringEdges(ring)) {
      if (e.len < 6) continue;
      const n = Math.round(e.len / 7.2);
      for (let i = 0; i <= n; i++) {
        const p = pointOn(e, (i / n) * e.len, -0.45);
        kit.box(b, conc, p[0], p[1], 0, 0.6, 0.6, gf, e.ang);
      }
    }
    // Upper floors: ribbon windows; short returns in brown brick (stair cores).
    const top = H - 1.2;
    edgeWalls(b, ring, gf, top, (e) =>
      e.len > 9 ? { m: ribbon, bay: 1.8 * 2, storey, uvBase: gf } : { m: brick },
    );
    // Projecting floor-edge bands.
    for (let k = 0; k <= 7; k++) band(kit, b, conc, ring, gf + k * storey - 0.15, 0.3, 0.12);
    parapet(kit, b, conc, ring, top, 1.2, 0.35);
    kit.cap(b, roofM, [[ring]], top + 0.01);
    // Brick stair / service towers rising above the roof at the ends of the slab.
    const ex = kit.orientedExtent(ring, frame.angle);
    const at = (u, v) => ex.at(u, v, 0);
    const tower = (u, v, w, d, h) => {
      const p = at(u, v);
      kit.box(b, brick, p[0], p[1], 0.01, w, d, h, frame.angle);
      kit.box(b, conc, p[0], p[1], h, w + 0.3, d + 0.3, 0.3, frame.angle);
    };
    tower(ex.u0 + 4.5, ex.v1 - 4, 6, 6, H + 3.4);
    tower(ex.u1 - 4.5, ex.v1 - 3, 6, 5, H + 3.4);
    // Plant room with louvres.
    const louvre = kit.paintedMaterial(
      'imperial_chemistry_building:louvre',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#8f969a';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#5d6366';
        for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 3);
      },
    );
    const pc = at((ex.u0 + ex.u1) / 2, (ex.v0 + ex.v1) / 2 + 1);
    kit.box(b, louvre, pc[0], pc[1], H, 30, 8, 3.2, frame.angle);
    kit.box(b, dconc, pc[0], pc[1], H + 3.2, 30.6, 8.6, 0.3, frame.angle);
    // Fume-cupboard extract stacks: rows of steel flues along the south side.
    const flue = new THREE.CylinderGeometry(0.35, 0.35, 1, 10).rotateX(Math.PI / 2);
    const rr = kit.rng(0.886);
    for (let i = 0; i < 14; i++)
      for (const v of [ex.v0 + 3.2, ex.v0 + 5]) {
        const u = ex.u0 + 10 + i * ((ex.u1 - ex.u0 - 20) / 13);
        const p = at(u, v);
        const hh = 3 + rr() * 2.5;
        const m = new THREE.Matrix4()
          .makeScale(1, 1, hh)
          .premultiply(new THREE.Matrix4().makeTranslation(p[0], p[1], H + hh / 2 - 1.2));
        b.addGeometry(steel, flue, m);
      }
    flue.dispose();
    // Ducts linking flues to the plant room.
    const d0 = at((ex.u0 + ex.u1) / 2, ex.v0 + 4.1);
    kit.box(b, steel, d0[0], d0[1], H - 0.6, ex.u1 - ex.u0 - 18, 1.0, 1.0, frame.angle);
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_chemistry_building'));
    return g;
  },
};
