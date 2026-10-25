// Bone Building, Imperial College South Kensington (Chemical Engineering and
// Aeronautics), named after William A. Bone, professor of chemical technology.
// Stands beside the 1957 Roderic Hill Building with a courtyard behind it.
// Modelled as a four-storey red-brick laboratory block with Portland stone
// plinth, string courses, window surrounds and cornice, a parapet, chimney/flue
// stacks and roof-light hoods over the former laboratory floor.

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
function roofClutter(kit, batch, mat, ring, z, seed, count, ang = 0, margin = 2.5, holes = []) {
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
    if (holes.some((hr) => inRing(kit.offsetRing(hr, -margin - 2), x, y))) continue;
    kit.box(batch, mat, x, y, z, w, d, h, ang);
    placed++;
  }
}
// ---- end helpers ----

export default {
  id: 'bone_building',
  name: 'Bone Building (Imperial College)',
  claims: ['83b620cc-5e12-4222-a5ea-fceb42477b2a'],
  references: [
    {
      title: 'Centenary memories (Oakley) - Imperial College',
      url: 'https://www.imperial.ac.uk/centenary/memories/oakley.shtml',
      used_for: 'Bone Building beside the new Roderic Hill Building, courtyard behind',
    },
    {
      title: 'South Kensington campus map (Imperial College)',
      url: 'https://www.sbg.bio.ic.ac.uk/files/SouthKensingtonCampus.pdf',
      used_for: 'Bone Building houses Aeronautics and Chemical Engineering',
    },
  ],
  notes:
    'Construction date and elevation are not documented in the sources found; red brick with stone dressings is an assumption matched to the pre-war Imperial laboratory buildings. Height from the footprint record (13.6 m, 4 floors).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const b = byId['83b620cc-5e12-4222-a5ea-fceb42477b2a'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const stone = kit.mat('portland_stone');
    const Z1 = 3.8,
      FH = (b.h - Z1) / 3,
      TOP = b.h;
    const wall = painted(kit, 'bone:wall', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#9a5440');
      const r = kit.rng(0.33);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          c.fillStyle = `rgba(${130 + r() * 40},${66 + r() * 22},${48 + r() * 18},0.95)`;
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      for (let i = 0; i < 2; i++) {
        const x = 14 + i * 64;
        c.fillStyle = '#ddd6c4';
        c.fillRect(x - 4, h * 0.2, 44, h * 0.7);
        win(c, x, 0.24, 36, 0.86, h, '#283037', '#ece8de', 2, 2);
        c.fillStyle = '#ddd6c4';
        c.fillRect(x - 6, h * 0.12, 48, 6);
      }
    });
    const base = painted(kit, 'bone:base', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#d6cebb');
      grain(c, w, h, 0.34, kit, 0.06);
      c.fillStyle = 'rgba(90,80,60,0.3)';
      for (let y = 0; y < h; y += 14) c.fillRect(0, y, w, 1.5);
      for (let i = 0; i < 2; i++) win(c, 14 + i * 64, 0.2, 36, 0.8, h, '#283037', '#ece8de', 2, 2);
    });
    wallsM(batch, base, [ring], 0, Z1, 4, Z1);
    wallsM(batch, wall, [ring], Z1, TOP, 4, FH, Z1);
    hband(kit, batch, stone, ring, Z1 - 0.3, 0.4, 0.15);
    hband(kit, batch, stone, ring, Z1 + 2 * FH - 0.2, 0.25, 0.1);
    hband(kit, batch, kit.mat('#e3dccb'), ring, TOP - 0.5, 0.55, 0.45);
    kit.cap(batch, kit.roof('flat', 1), [[ring]], TOP + 0.08);
    parapet(kit, batch, kit.mat('#9a5440'), [ring], TOP + 0.05, 1.0, 0.3);
    kit.cap(
      batch,
      stone,
      [[kit.offsetRing(ring, 0.05), kit.offsetRing(ring, -0.35).reverse()]],
      TOP + 1.07,
    );
    // Chimney / fume-flue stacks and lab roof-light hoods.
    const E = edges(ring);
    const long = E.slice().sort((a, b) => b.len - a.len)[0];
    const F = frameOf(long.a, long.b);
    const brickM = kit.mat('#8e4d3a');
    for (const u of [5, 15, 25, 34]) {
      if (u > long.len - 2) continue;
      const [x, y] = F.P(u, -2.2);
      kit.box(batch, brickM, x, y, TOP, 1.4, 2.2, 3.6, F.ang);
      kit.box(batch, stone, x, y, TOP + 3.6, 1.6, 2.4, 0.3, F.ang);
      for (const d of [-0.5, 0.5]) {
        const [px, py] = F.P(u, -2.2 + d);
        kit.box(batch, kit.mat('#7a5a48'), px, py, TOP + 3.9, 0.35, 0.35, 0.6, F.ang);
      }
    }
    for (const u of [9, 20]) {
      const [x, y] = F.P(u, -10);
      kit.box(batch, kit.mat('lead'), x, y, TOP, 6, 4, 1.2, F.ang);
      kit.box(batch, kit.mat('glass'), x, y, TOP + 1.2, 5.4, 3.4, 0.5, F.ang);
    }
    g.add(batch.toGroup('bone'));
    return g;
  },
};
