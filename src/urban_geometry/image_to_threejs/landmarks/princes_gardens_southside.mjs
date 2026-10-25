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
        'limestone / brick / stucco palette, front elevation echoing terrace fenestration, stepped rear bays',
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
  ],
  notes:
    'Window grid, glazed joints and attic treatment are inferred from the KPF description, not traced from photos. Front halls 20 m from Overture; Keogh (rear range) kept at its Overture 7.2 m with a set-back upper storey, which may understate it.',
  build({ THREE, kit, byId }) {
    const b = new kit.MeshBatch();
    const stone = kit.mat('#e2dccb'),
      zinc = kit.mat('#5c6266', { roughness: 0.55 }),
      roofM = kit.roof('flat', 0),
      glass = kit.mat('dark_glass'),
      brickM = kit.mat('#b9a27c');
    const storey = 3.1,
      gf = 3.6;
    const frontM = kit.paintedMaterial('princes_gardens_southside:front', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2007);
      noiseFill(c, w, h, '#e2dccb', r, 0.05, 4);
      c.fillStyle = 'rgba(120,110,90,0.18)';
      for (let y = 0; y < h; y += 21) c.fillRect(0, y, w, 1);
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 1, h);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.44,
            wh = ch * 0.72,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.12;
          c.fillStyle = '#c9c2b0';
          c.fillRect(wx - 4, wy - 4, ww + 8, wh + 8);
          glassPane(c, wx, wy, ww, wh, r, [44, 58, 68]);
          c.fillStyle = '#8f969a';
          c.fillRect(wx + ww * 0.62, wy, 3, wh);
          c.fillRect(wx, wy + wh * 0.78, ww, 3);
        }
    });
    const rearM = kit.paintedMaterial('princes_gardens_southside:rear', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3007);
      brickCourses(c, w, h, r, '#b9a27c', 3);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.5,
            wh = ch * 0.64,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.16;
          c.fillStyle = '#eeeae0';
          c.fillRect(wx - 3, wy - 3, ww + 6, wh + 6);
          glassPane(c, wx, wy, ww, wh, r, [44, 58, 68]);
          c.fillStyle = '#eeeae0';
          c.fillRect(wx + ww / 2 - 1, wy, 2, wh);
        }
    });
    const baseM = kit.paintedMaterial('princes_gardens_southside:base', 512, 256, (c, w, h) => {
      const r = kit.rng(0.4007);
      noiseFill(c, w, h, '#d6cfbd', r, 0.05, 4);
      for (let i = 0; i < 4; i++) {
        const x = i * (w / 4) + 10;
        glassPane(c, x, h * 0.12, w / 4 - 20, h * 0.8, r, [52, 70, 82]);
        c.fillStyle = '#7d8487';
        c.fillRect(x + (w / 4 - 20) / 2 - 1, h * 0.12, 3, h * 0.8);
      }
    });
    const atticM = kit.paintedMaterial('princes_gardens_southside:attic', 512, 256, (c, w, h) => {
      const r = kit.rng(0.5007);
      noiseFill(c, w, h, '#5c6266', r, 0.05, 4);
      c.fillStyle = 'rgba(255,255,255,0.08)';
      for (let x = 0; x < w; x += 16) c.fillRect(x, 0, 2, h); // standing seams
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++)
          glassPane(c, i * (w / 4) + 14, j * (h / 2) + 18, w / 4 - 28, h / 2 - 40, r, [60, 78, 90]);
    });
    const front = (e) => e.ny > 0.8 && e.len > 10;
    for (const key of ['falmouth', 'tizard', 'selkirk']) {
      const bld = byId[IDS[key]];
      if (!bld) continue;
      const ring = ccw(bld.polys[0][0]);
      const H = bld.h,
        attic = H - storey;
      edgeWalls(b, ring, 0, gf, (e) =>
        front(e) ? { m: baseM, bay: 3.4, storey: gf / 2 } : { m: rearM, bay: 3.4, storey },
      );
      edgeWalls(b, ring, gf, attic, (e) =>
        front(e)
          ? { m: frontM, bay: 3.4, storey, uvBase: gf }
          : { m: rearM, bay: 3.4, storey, uvBase: gf },
      );
      edgeWalls(b, ring, attic, H, () => ({ m: atticM, bay: 3.4, storey: storey }));
      band(kit, b, stone, ring, attic - 0.3, 0.35, 0.35);
      band(kit, b, stone, ring, gf - 0.2, 0.25, 0.15);
      kit.cap(b, roofM, [[ring]], H);
      parapet(kit, b, zinc, ring, H, 0.5, 0.15);
      // Recessed full-height glazed joint at the west end of each hall's front.
      for (const e of ringEdges(ring)) {
        if (!front(e)) continue;
        const p = pointOn(e, 1.0, 0.02);
        kit.box(b, glass, p[0], p[1], gf, 2.0, 0.08, attic - gf, e.ang);
        // entrance canopy at the centre of each front
        const q = pointOn(e, e.len / 2, 1.0);
        kit.box(b, zinc, q[0], q[1], gf - 0.6, 5, 2.0, 0.3, e.ang);
        // roof plant / stair overrun
        const s = pointOn(e, e.len * 0.7, -7);
        kit.box(b, zinc, s[0], s[1], H, 6, 4, 2.6, e.ang);
      }
    }
    // Keogh: lower rear range stepping down to the mews.
    const kb = byId[IDS.keogh];
    if (kb) {
      const ring = ccw(kb.polys[0][0]);
      const H = kb.h;
      edgeWalls(b, ring, 0, H, () => ({ m: rearM, bay: 3.4, storey: H / 2 }));
      kit.cap(b, roofM, [[ring]], H);
      parapet(kit, b, stone, ring, H, 0.6, 0.2);
      const inner = kit.offsetRing(ring, -1.2);
      edgeWalls(b, inner, H, H + 3.0, () => ({ m: atticM, bay: 3.4, storey: 3.0 }));
      kit.cap(b, roofM, [[inner]], H + 3.0);
    }
    const g = new THREE.Group();
    g.add(b.toGroup('princes_gardens_southside'));
    return g;
  },
};
