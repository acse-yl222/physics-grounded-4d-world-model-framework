// Skempton Building (Civil & Environmental Engineering), Imperial College.
// Opened 1963 as the Civil Engineering Building (Norman & Dawbarn, ~110,000 sq ft),
// renamed after Sir Alec Skempton in 2004. Six-storey concrete-framed L block
// facing Imperial College Road: precast grid of slender vertical mullions over
// continuous slab bands, a dark recessed ground storey, flat roof with plant and
// north-light rooflights over the heavy structures/hydraulics laboratory wing.

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
  id: 'skempton_building',
  name: 'Skempton Building (Imperial College Civil Engineering)',
  claims: ['c7e47974-cdef-43e7-b350-351d8ab671a1'],
  references: [
    {
      title: 'History of the department - Civil Engineering, Imperial College',
      url: 'https://imperial.ac.uk/civil-engineering/about-us/history-of-the-department',
      used_for:
        'building opened 1963 as the Civil Engineering Building, renamed Skempton Building in 2004',
    },
    {
      title: 'New Civil Engineering Building at Imperial College (Emerald)',
      url: 'https://www.emerald.com/insight/content/doi/10.1108/eb015445/full/html',
      used_for: '1964 notice: Norman & Dawbarn architects, over 110,000 sq ft',
    },
    {
      title: 'Survey of London vol. 38, plate 76',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for: "1960-9 Norman and Dawbarn buildings around the Queen's Tower",
    },
  ],
  notes:
    'Massing from the Overture footprint at 20 m (6 floors). Facade grid, rooflights and plinth treatment are reconstructed from the 1960s Norman & Dawbarn idiom; no photograph could be fetched.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const b = byId['c7e47974-cdef-43e7-b350-351d8ab671a1'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const conc = kit.mat('#cfc8b8', { roughness: 0.9 });
    const concDk = kit.mat('#8f8a80');
    const roofM = kit.roof('flat', 1);
    const glass = kit.mat('glass');
    const Z1 = 4.2,
      FH = 3.16,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const upper = painted(kit, 'skempton:upper', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#cbc4b4');
      grain(c, w, h, 0.52, kit, 0.07);
      for (let i = 0; i < 2; i++)
        win(c, i * (w / 2) + 6, 0.3, w / 2 - 12, 0.9, h, '#33414b', '#6a6d6c', 2, 3);
      c.fillStyle = 'rgba(0,0,0,0.18)';
      c.fillRect(0, h * 0.27, w, 3);
    });
    const ground = painted(kit, 'skempton:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2f3a42');
      c.fillStyle = '#6e7377';
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 2, 0, 4, h);
      c.fillRect(0, h * 0.72, w, 4);
      c.fillStyle = '#5b5550';
      c.fillRect(0, h * 0.88, w, h * 0.12);
      c.fillStyle = 'rgba(220,235,245,0.2)';
      c.fillRect(0, h * 0.72, w, h * 0.16);
    });
    // Ground storey slightly recessed behind the column line.
    const inner = kit.offsetRing(ring, -0.9);
    wallsM(batch, ground, [inner], 0, Z1, 4.8, Z1);
    kit.cap(batch, concDk, [[ring]], Z1, { down: true });
    fins(kit, batch, concDk, ring, 0, Z1, 6.4, 0.6, 0.6, { minLen: 6 });
    // Upper storeys.
    wallsM(batch, upper, [ring], Z1, TOP, 3.2, FH, Z1);
    for (let k = 0; k < NF; k++) hband(kit, batch, conc, ring, Z1 + k * FH - 0.45, 0.45, 0.28);
    // Slender precast mullions on the long faces.
    fins(kit, batch, conc, ring, Z1, TOP - 0.45, 1.6, 0.3, 0.22, { minLen: 20 });
    // Roof: parapet, plant, north-light rooflights over the laboratory wing.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, conc, [ring], TOP, 0.9, 0.3);
    const E = edges(ring);
    const north = E.find((e) => Math.abs(e.a[0] - 1737.3) < 0.5); // north face of the lab wing
    const F = frameOf(north.a, north.b); // u west, n north (outward)
    for (let k = 0; k < 5; k++) {
      const u = 5 + k * 6.5;
      for (let j = 0; j < 2; j++) {
        const n0 = -6 - j * 10;
        const a = F.P(u, n0, TOP),
          b2 = F.P(u + 4.5, n0, TOP);
        const a2 = F.P(u, n0 - 3.5, TOP + 1.8),
          b3 = F.P(u + 4.5, n0 - 3.5, TOP + 1.8);
        // glazed north-facing slope + solid back slope
        batch.quad(glass, a, b2, b3, a2, [0, 0], [1, 0], [1, 1], [0, 1]);
        const a4 = F.P(u, n0 - 7, TOP),
          b4 = F.P(u + 4.5, n0 - 7, TOP);
        batch.quad(concDk, a2, b3, b4, a4, [0, 0], [1, 0], [1, 1], [0, 1]);
        batch.add(
          concDk,
          [a, a2, a4],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 1, 2],
        );
        batch.add(
          concDk,
          [b2, b4, b3],
          [
            [0, 0],
            [0.5, 1],
            [1, 0],
          ],
          [0, 1, 2],
        );
      }
    }
    roofClutter(kit, batch, kit.mat('aluminium'), ring, TOP, 0.37, 10, F.ang, 3);
    // Stair/lift tower at the west wing.
    const west = E.find((e) => Math.abs(e.a[0] - 1667.7) < 0.5);
    const W = frameOf(west.a, west.b);
    const core = fixCCW(kit, rectRing(W, 12, 20, -9, -3));
    prism(kit, batch, conc, roofM, [core], TOP, TOP + 3.8);
    g.add(batch.toGroup('skempton'));
    return g;
  },
};
