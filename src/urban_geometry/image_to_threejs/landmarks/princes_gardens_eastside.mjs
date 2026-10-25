// Eastside halls of residence, Prince's Gardens (Kohn Pedersen Fox, phase 2 of the
// Prince's Gardens masterplan, opened 2009): Wilkinson, Gabor and Linstead halls,
// 454 undergraduate rooms on the east side of the square. Eight storeys: a
// limestone-framed front to the gardens with paired windows in a regular terrace
// rhythm over a double-height glazed base (Kawneer unitised curtain walling),
// recessed glazed joints between the three halls, a dark metal attic, and rear
// elevations stepping back towards the mews in brick bays.
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
  wilkinson: 'c718310f-6644-4eb6-9774-9b1159d70ade',
  gabor: 'a44753fb-883d-4c1b-953e-7c36f58382fb',
  linstead: '17b6f6d3-5988-410a-9dad-fb3ce9c22694',
};

export default {
  id: 'princes_gardens_eastside',
  name: "Eastside Halls, Prince's Gardens (Imperial College)",
  claims: Object.values(IDS),
  references: [
    {
      title: 'princes gardens redevelopment - KPF',
      url: 'https://www.kpf.com/project/princes-gardens-redevelopment',
      used_for:
        'limestone / brick / stucco palette, rhythmic front fenestration, stepped rear bays',
    },
    {
      title: 'Kawneer restores a princely feel to a historic London Square - Specification Online',
      url: 'https://www.specificationonline.co.uk/articles/2016-03-22/kawneer-restores-a-princely-feel-to-a-historic-london-square',
      used_for: 'AA201 unitised curtain walling on phase 2 (Eastside) of the KPF masterplan',
    },
    {
      title: 'At a glance - Eastside (Imperial accommodation)',
      url: 'https://www.imperial.ac.uk/students/accommodation/prospective/ug/halls/eastside/',
      used_for: 'three adjoining halls, 454 rooms',
    },
    {
      title: 'Places: Eastside - Imperial video archive',
      url: 'https://blogs.imperial.ac.uk/videoarchive/places-eastside/',
      used_for: 'Gabor, Linstead and Wilkinson halls',
    },
  ],
  notes:
    'Facade proportions, the glazed base and the attic are inferred from the KPF/Kawneer descriptions rather than traced from photos. Height 26.4 m from Overture (8 floors).',
  build({ THREE, kit, byId }) {
    const b = new kit.MeshBatch();
    const stone = kit.mat('#e0d9c6'),
      zinc = kit.mat('#596064', { roughness: 0.55 }),
      roofM = kit.roof('flat', 1),
      glass = kit.mat('dark_glass');
    const storey = 3.0,
      base = 6.0;
    const frontM = kit.paintedMaterial('princes_gardens_eastside:front', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2009);
      noiseFill(c, w, h, '#e0d9c6', r, 0.05, 4);
      c.fillStyle = 'rgba(120,110,90,0.16)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 1);
      const cw = w / 2,
        ch = h / 2; // two bay pairs per tile (bay 3.4 m -> pair 6.8 m)
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 2; i++) {
          const wx = i * cw + cw * 0.12,
            ww = cw * 0.76,
            wy = j * ch + ch * 0.1,
            wh = ch * 0.74;
          c.fillStyle = '#7b8285';
          c.fillRect(wx - 3, wy - 3, ww + 6, wh + 6);
          glassPane(c, wx, wy, ww, wh, r, [46, 62, 72]);
          c.fillStyle = '#7b8285';
          for (let k = 1; k < 4; k++) c.fillRect(wx + (ww * k) / 4 - 1.5, wy, 3, wh);
          c.fillRect(wx, wy + wh * 0.8, ww, 3);
        }
    });
    const rearM = kit.paintedMaterial('princes_gardens_eastside:rear', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3009);
      brickCourses(c, w, h, r, '#9d5a45', 3);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.52,
            wh = ch * 0.64,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.16;
          c.fillStyle = '#d9d4c8';
          c.fillRect(wx - 3, wy - 3, ww + 6, wh + 6);
          glassPane(c, wx, wy, ww, wh, r, [44, 58, 68]);
        }
    });
    const baseM = kit.paintedMaterial('princes_gardens_eastside:base', 512, 256, (c, w, h) => {
      const r = kit.rng(0.4009);
      glassPane(c, 0, 0, w, h, r, [58, 76, 88]);
      c.fillStyle = '#c9cfd2';
      for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 2, 0, 4, h);
      c.fillRect(0, h / 2 - 2, w, 4);
    });
    const atticM = kit.paintedMaterial('princes_gardens_eastside:attic', 512, 256, (c, w, h) => {
      const r = kit.rng(0.5009);
      noiseFill(c, w, h, '#596064', r, 0.05, 4);
      c.fillStyle = 'rgba(255,255,255,0.08)';
      for (let x = 0; x < w; x += 16) c.fillRect(x, 0, 2, h);
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++)
          glassPane(c, i * (w / 4) + 12, j * (h / 2) + 16, w / 4 - 24, h / 2 - 34, r, [60, 78, 90]);
    });
    const front = (e) => e.nx < -0.8 && e.len > 10;
    for (const key of ['wilkinson', 'gabor', 'linstead']) {
      const bld = byId[IDS[key]];
      if (!bld) continue;
      const ring = ccw(bld.polys[0][0]);
      const H = bld.h,
        attic = H - storey;
      edgeWalls(b, ring, 0, base, (e) =>
        front(e) ? { m: baseM, bay: 3.4, storey: base / 2 } : { m: rearM, bay: 3.4, storey },
      );
      edgeWalls(b, ring, base, attic, (e) =>
        front(e)
          ? { m: frontM, bay: 3.4, storey, uvBase: base }
          : { m: rearM, bay: 3.4, storey, uvBase: base },
      );
      edgeWalls(b, ring, attic, H, () => ({ m: atticM, bay: 3.4, storey }));
      band(kit, b, stone, ring, attic - 0.35, 0.4, 0.4);
      band(kit, b, stone, ring, base - 0.3, 0.35, 0.25);
      kit.cap(b, roofM, [[ring]], H);
      parapet(kit, b, zinc, ring, H, 0.5, 0.15);
      for (const e of ringEdges(ring)) {
        if (!front(e)) continue;
        // projecting stone frame piers every two bays on the front
        finsAlong(kit, b, stone, e, base, attic, 6.8, 0.35, 0.5, { skipEnds: false });
        // glazed joint at the north end of each hall
        const p = pointOn(e, 1.1, 0.4);
        kit.box(b, glass, p[0], p[1], base, 2.2, 0.08, attic - base, e.ang);
        const q = pointOn(e, e.len / 2, 1.2);
        kit.box(b, zinc, q[0], q[1], 3.4, 6, 2.4, 0.3, e.ang);
        const s = pointOn(e, e.len * 0.5, -9);
        kit.box(b, zinc, s[0], s[1], H, 5, 4, 2.6, e.ang);
      }
    }
    const g = new THREE.Group();
    g.add(b.toGroup('princes_gardens_eastside'));
    return g;
  },
};
