// Blackett Laboratory (Department of Physics), Imperial College South Kensington.
// Completed 1961 on the corner of Prince Consort Road and Queen's Gate; steel-
// framed, planned under P. M. S. Blackett (Head of Physics from 1953), with the
// staff common room on level 8. Modelled as a T-shaped six-storey block: a
// pale stone-faced grid frame with recessed windows over a dark glazed ground
// floor, a set-back top storey (common room level) and rooftop plant.

// ---- self-contained helpers (no imports; kit/THREE passed in) ----
function edges(ring) {
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
      ux: dx / len,
      uy: dy / len,
      nx: dy / len,
      ny: -dx / len,
      ang: Math.atan2(dy, dx),
    });
  }
  return out;
}
// Wall quads with UVs in tiles of tw metres (integer tiles per edge) x th metres from zb.
function wallSeg(batch, mat, a, b, z0, z1, tw, th, zb = 0, u0 = 0) {
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const n = Math.max(1, Math.round(len / tw));
  const v0 = (z0 - zb) / th,
    v1 = (z1 - zb) / th;
  batch.quad(
    mat,
    [a[0], a[1], z0],
    [b[0], b[1], z0],
    [b[0], b[1], z1],
    [a[0], a[1], z1],
    [u0, v0],
    [u0 + n, v0],
    [u0 + n, v1],
    [u0, v1],
  );
}
function wallsM(batch, mat, rings, z0, z1, tw, th, zb = 0, skip = null) {
  rings.forEach((ring, ri) => {
    for (const e of edges(ring)) {
      if (skip && skip(e, ri)) continue;
      wallSeg(batch, mat, e.a, e.b, z0, z1, tw, th, zb);
    }
  });
}
// Closed prism (walls, top, optional bottom) of a polygon [outer, ...holes].
function prism(
  kit,
  batch,
  wallMat,
  topMat,
  poly,
  z0,
  z1,
  { tw = 3, th = 3, zb = 0, bottom = false } = {},
) {
  wallsM(batch, wallMat, poly, z0, z1, tw, th, zb);
  if (topMat) kit.cap(batch, topMat, [poly], z1);
  if (bottom) kit.cap(batch, topMat || wallMat, [poly], z0, { down: true });
}
// Parapet band of thickness t on every ring of a polygon.
function parapet(kit, batch, mat, poly, z, h, t = 0.3) {
  poly.forEach((ring, ri) => {
    const inner = kit.offsetRing(ring, -t);
    wallsM(batch, mat, [ring], z, z + h, 3, 3);
    wallsM(batch, mat, [inner.slice().reverse()], z, z + h, 3, 3);
    const band = ri === 0 ? [ring, inner.slice().reverse()] : [inner.slice().reverse(), ring];
    kit.cap(batch, mat, [band], z + h);
  });
}
// Projecting horizontal band (string course / slab edge) around the outer ring.
function hband(kit, batch, mat, ring, z, h, out) {
  const r = kit.offsetRing(ring, out);
  wallsM(batch, mat, [r], z, z + h, 3, 3);
  kit.cap(batch, mat, [[r]], z + h);
  kit.cap(batch, mat, [[r]], z, { down: true });
}
// Vertical fins / pilasters along edges.
function fins(
  kit,
  batch,
  mat,
  ring,
  z0,
  z1,
  spacing,
  depth,
  width,
  { minLen = 4, skip = null, inset = 0 } = {},
) {
  for (const e of edges(ring)) {
    if (e.len < minLen || (skip && skip(e))) continue;
    const n = Math.max(1, Math.round(e.len / spacing));
    for (let i = inset; i <= n - inset; i++) {
      const t = (i * e.len) / n;
      const x = e.a[0] + e.ux * t + (e.nx * depth) / 2,
        y = e.a[1] + e.uy * t + (e.ny * depth) / 2;
      kit.box(batch, mat, x, y, z0, width, depth, z1 - z0, e.ang);
    }
  }
}
// Local facade frame along edge a->b: P(u, n, z) with u along the edge, n outward.
function frameOf(a, b) {
  const dx = b[0] - a[0],
    dy = b[1] - a[1],
    len = Math.hypot(dx, dy);
  const ux = dx / len,
    uy = dy / len,
    nx = uy,
    ny = -ux;
  return {
    len,
    ang: Math.atan2(dy, dx),
    P: (u, n, z = 0) => [a[0] + ux * u + nx * n, a[1] + uy * u + ny * n, z],
  };
}
function rectRing(F, u0, u1, n0, n1) {
  // CCW in scene coordinates (u along edge, n outward = right of edge)
  return [F.P(u0, n1), F.P(u1, n1), F.P(u1, n0), F.P(u0, n0)].map((p) => [p[0], p[1]]);
}
function fixCCW(kit, ring) {
  return kit.ringArea(ring) < 0 ? ring.slice().reverse() : ring;
}
function painted(kit, key, w, h, draw, params = {}) {
  return kit.paintedMaterial(key, w, h, draw, { roughness: 0.82, ...params });
}
// Canvas painting helpers: z measured upward in tile fractions.
function fillTile(g, w, h, col) {
  g.fillStyle = col;
  g.fillRect(0, 0, w, h);
}
function grain(g, w, h, seed, kit, amt = 0.06, col = '0,0,0') {
  const r = kit.rng(seed);
  for (let i = 0; i < (w * h) / 60; i++) {
    g.fillStyle = `rgba(${col},${(r() * amt).toFixed(3)})`;
    g.fillRect(r() * w, r() * h, 1 + r() * 3, 1 + r() * 2);
  }
}
function win(g, x, y0f, wpx, y1f, h, glass, frame, panes = 1, mull = 2) {
  // y0f/y1f: bottom/top as fraction of tile height (0 = bottom)
  const top = h * (1 - y1f),
    hh = h * (y1f - y0f);
  g.fillStyle = glass;
  g.fillRect(x, top, wpx, hh);
  if (frame) {
    g.fillStyle = frame;
    for (let i = 0; i <= panes; i++) g.fillRect(x + (i * (wpx - mull)) / panes, top, mull, hh);
    g.fillRect(x, top, wpx, mull);
    g.fillRect(x, top + hh - mull, wpx, mull);
  }
  // sky reflection gradient
  const gr = g.createLinearGradient(0, top, 0, top + hh);
  gr.addColorStop(0, 'rgba(255,255,255,0.18)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(x, top, wpx, hh * 0.6);
}
function inRing(ring, x, y) {
  let ins = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i],
      [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
// Rooftop plant boxes scattered inside a ring (deterministic), kept `margin` from edges.
function roofClutter(kit, batch, mat, ring, z, seed, count, ang = 0, margin = 2.5) {
  const r = kit.rng(seed);
  const inner = kit.offsetRing(ring, -margin);
  let xs = ring.map((p) => p[0]),
    ys = ring.map((p) => p[1]);
  const x0 = Math.min(...xs),
    x1 = Math.max(...xs),
    y0 = Math.min(...ys),
    y1 = Math.max(...ys);
  let placed = 0;
  for (let t = 0; t < count * 20 && placed < count; t++) {
    const x = x0 + r() * (x1 - x0),
      y = y0 + r() * (y1 - y0);
    const w = 1.5 + r() * 3,
      d = 1.5 + r() * 2.5,
      h = 0.8 + r() * 1.6;
    if (!inRing(inner, x, y) || !inRing(inner, x + w / 2, y) || !inRing(inner, x - w / 2, y))
      continue;
    kit.box(batch, mat, x, y, z, w, d, h, ang);
    placed++;
  }
}
// ---- end helpers ----

export default {
  id: 'blackett_laboratory',
  name: 'Blackett Laboratory (Imperial College Physics)',
  claims: ['fc97c25d-2316-42d9-8db4-9cd9ad109b99'],
  references: [
    {
      title: 'Blackett Laboratory - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Blackett_Laboratory',
      used_for: "corner of Prince Consort Road and Queen's Gate; Physics since completion in 1961",
    },
    {
      title: 'The story of physics at South Kensington - Imperial College',
      url: 'https://www.imperial.ac.uk/natural-sciences/departments/physics/about-us/department-history/the-story-of-physics-at-south-kensington/',
      used_for: 'planned as a first-class steel frame building from the early 1950s',
    },
    {
      title: 'From the Royal College of Science to the Blackett Laboratory - Imperial College',
      url: 'https://www.imperial.ac.uk/physics/about-us/department-history/a-history-of-the-imperial-physics-department/',
      used_for: "Blackett's role in the design; common room on level 8",
    },
  ],
  notes:
    'Main block kept at the footprint height (20 m, 6 floors) plus a set-back top storey for the level-8 common room (~23.6 m). Cladding material and grid rhythm are not confirmed by the sources found (no photos fetched).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const ring = byId['fc97c25d-2316-42d9-8db4-9cd9ad109b99'].polys[0][0];
    const batch = new kit.MeshBatch();
    const stone = kit.mat('#d8d1bf');
    const Z1 = 4.5,
      FH = 3.1,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const grid = painted(kit, 'blackett:grid', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#d9d2c0');
      grain(c, w, h, 0.91, kit, 0.06);
      for (let i = 0; i < 4; i++) {
        const x = (i * w) / 4;
        c.fillStyle = '#b9b2a2';
        c.fillRect(x + 8, h * 0.22, w / 4 - 16, h * 0.66);
        win(c, x + 12, 0.25, w / 4 - 24, 0.85, h, '#2b3640', '#e4e0d6', 2, 3);
        c.fillStyle = '#5d5a55';
        c.fillRect(x + 12, h * (1 - 0.36), w / 4 - 24, 3);
      }
    });
    const base = painted(kit, 'blackett:base', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2a353d');
      c.fillStyle = '#c9c2b1';
      c.fillRect(0, 0, w, h * 0.16);
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 6, 0, 12, h);
      c.fillStyle = 'rgba(220,235,245,0.2)';
      c.fillRect(0, h * 0.16, w, h * 0.22);
      c.fillStyle = '#6b6f70';
      c.fillRect(0, h * 0.5, w, 3);
    });
    const top = painted(kit, 'blackett:top', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#26313a');
      c.fillStyle = '#c7c9c6';
      c.fillRect(0, 0, w, h * 0.14);
      c.fillRect(0, h * 0.9, w, h * 0.1);
      for (let i = 0; i <= 6; i++) c.fillRect((i * w) / 6 - 2, 0, 4, h);
      c.fillStyle = 'rgba(210,230,245,0.25)';
      c.fillRect(0, h * 0.14, w, h * 0.3);
    });
    wallsM(batch, base, [ring], 0, Z1, 7.2, Z1);
    wallsM(batch, grid, [ring], Z1, TOP, 7.2, (FH * 2) / 2, Z1);
    // Projecting frame: floor bands and piers every 3.6 m.
    for (let k = 0; k < NF; k++) hband(kit, batch, stone, ring, Z1 + k * FH - 0.3, 0.3, 0.3);
    fins(kit, batch, stone, ring, Z1 - 0.3, TOP, 3.6, 0.32, 0.4, { minLen: 6 });
    kit.cap(batch, kit.roof('flat', 0), [[ring]], TOP);
    parapet(kit, batch, stone, [ring], TOP, 1.0, 0.35);
    // Set-back top storey (common room) over the Prince Consort Road range.
    const front = edges(ring).find((e) => Math.abs(e.a[0] - 1505.5) < 0.5);
    const F = frameOf(front.a, front.b); // u west along Prince Consort Road, n north
    const cr = fixCCW(kit, rectRing(F, 4, front.len - 4, -15, -2.5));
    wallsM(batch, top, [cr], TOP, TOP + 3.6, 3.6, 3.6, TOP);
    kit.cap(batch, kit.roof('flat', 1), [[cr]], TOP + 3.6);
    hband(kit, batch, kit.mat('#c7c9c6'), cr, TOP + 3.6, 0.45, 0.6);
    roofClutter(kit, batch, kit.mat('aluminium'), ring, TOP, 0.93, 6, F.ang, 3);
    // Entrance canopy on Prince Consort Road.
    const can = fixCCW(kit, rectRing(F, front.len * 0.35, front.len * 0.55, 0, 2.6));
    prism(kit, batch, stone, stone, [can], 3.6, 4.1, { bottom: true });
    g.add(batch.toGroup('blackett'));
    return g;
  },
};
