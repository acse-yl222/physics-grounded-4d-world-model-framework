// City & Guilds Building (formerly Mechanical Engineering), Imperial College.
// Early-1960s concrete-framed block on Exhibition Road, built on the site of the
// 1885 City & Guilds College; renamed 2017 when its Exhibition Road facade was
// modernised as a glazed shop window onto the department (flight simulator on
// show). Modelled: 1960s banded concrete elevations with ribbon windows, a new
// aluminium-finned curtain wall and double-height display glazing to Exhibition
// Road, flat roof with plant. The part of the footprint occupied by the
// Business School (Foster, 2004) is left to that building.

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
  id: 'city_guilds_building',
  name: 'City & Guilds Building (Imperial College)',
  claims: ['4d70a509-252b-4948-b15c-eecc72fdba04'],
  references: [
    {
      title: 'City & Guilds legacy celebrated as building is renamed - Imperial College',
      url: 'https://www.imperial.ac.uk/news/129966/city-guilds-legacy-celebrated-building-renamed/',
      used_for:
        'early 1960s building overlooking Exhibition Road, formerly Mechanical Engineering; facade modernised with a flight simulator on show (2017)',
    },
    {
      title: 'History of Imperial College London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/History_of_Imperial_College_London',
      used_for: 'site of the 1885 City and Guilds College, demolished 1962',
    },
    {
      title: 'Survey of London vol. 38, plate 76',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for: "1960-9 Norman and Dawbarn buildings around the Queen's Tower",
    },
  ],
  notes:
    'Footprint overlaps the Business School (a07c23b2); the overlapping north-east part is cut out of this model so the Business School landmark/generic can occupy it. Height 20 m from the footprint record. 1960s elevations and the 2017 curtain-wall pattern are reconstructed from descriptions only.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    // Claimed outline minus the Business School footprint (a07c23b2).
    const ring = [
      [1757.0, -911.3],
      [1811.1, -904.7],
      [1804.6, -850.0],
      [1779.5, -852.8],
      [1777.1, -830.4],
      [1775.0, -812.3],
      [1770.0, -775.2],
      [1755.2, -777.3],
      [1759.3, -812.1],
      [1759.6, -816.7],
      [1745.5, -818.4],
      [1755.2, -899.0],
      [1749.7, -899.8],
      [1747.2, -900.4],
      [1748.4, -910.8],
      [1756.8, -909.6],
    ];
    const batch = new kit.MeshBatch();
    const conc = kit.mat('#cdc6b6', { roughness: 0.9 });
    const concDk = kit.mat('#8c877d');
    const alu = kit.mat('#b9bec2', { roughness: 0.35, metalness: 0.6 });
    const roofM = kit.roof('flat', 2);
    const Z1 = 4.4,
      FH = 3.12,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const old = painted(kit, 'cg:old', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#c9c1b0');
      grain(c, w, h, 0.61, kit, 0.07);
      c.fillStyle = '#9a8c78';
      c.fillRect(0, h * 0.02, w, h * 0.26);
      c.fillStyle = '#2c3942';
      c.fillRect(0, h * 0.34, w, h * 0.52);
      c.fillStyle = '#d8d2c6';
      for (let i = 0; i < 6; i++) c.fillRect((i * w) / 6, h * 0.34, 5, h * 0.52);
      c.fillRect(0, h * 0.62, w, 3);
      c.fillStyle = 'rgba(200,220,235,0.18)';
      c.fillRect(0, h * 0.34, w, h * 0.2);
    });
    const oldGround = painted(kit, 'cg:oldground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#b3ab9b');
      grain(c, w, h, 0.62, kit, 0.08);
      for (let i = 0; i < 3; i++) win(c, 10 + i * 82, 0.0, 60, 0.75, h, '#2d3a43', '#55595c', 2, 3);
    });
    const curtain = painted(kit, 'cg:curtain', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#1f2c35');
      const gr = c.createLinearGradient(0, 0, w, h);
      gr.addColorStop(0, 'rgba(160,190,210,0.35)');
      gr.addColorStop(1, 'rgba(160,190,210,0.05)');
      c.fillStyle = gr;
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#9aa1a6';
      c.fillRect(0, h * 0.9, w, h * 0.1);
      for (let i = 0; i < 4; i++) c.fillRect((i * w) / 4, 0, 3, h);
    });
    const display = painted(kit, 'cg:display', 1024, 256, (c, w, h) => {
      fillTile(c, w, h, '#2a3842');
      // lit interior with the flight simulator capsule and a wing section on show
      c.fillStyle = '#c9d2d6';
      c.fillRect(0, h * 0.82, w, h * 0.18);
      c.fillStyle = '#f1f1ee';
      c.beginPath();
      c.ellipse(w * 0.3, h * 0.48, w * 0.05, h * 0.2, 0, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = '#26303a';
      c.fillRect(w * 0.27, h * 0.4, w * 0.06, h * 0.07);
      c.strokeStyle = '#6c7378';
      c.lineWidth = 6;
      for (const dx of [-0.035, 0, 0.035]) {
        c.beginPath();
        c.moveTo(w * (0.3 + dx), h * 0.66);
        c.lineTo(w * (0.3 + dx * 1.5), h * 0.82);
        c.stroke();
      }
      c.fillStyle = '#1d5fa8';
      c.beginPath();
      c.moveTo(w * 0.55, h * 0.55);
      c.lineTo(w * 0.75, h * 0.5);
      c.lineTo(w * 0.75, h * 0.56);
      c.lineTo(w * 0.55, h * 0.6);
      c.fill();
      c.fillStyle = 'rgba(255,255,255,0.22)';
      c.fillRect(0, 0, w, h * 0.12);
      c.fillStyle = '#8f979c';
      for (let i = 0; i <= 18; i++) c.fillRect((i * w) / 18 - 3, 0, 6, h);
      c.fillRect(0, h * 0.12, w, 4);
    });
    const E = edges(ring);
    const isExh = (e) => Math.abs(e.a[0] - 1811.1) < 0.5; // Exhibition Road face
    for (const e of E) {
      if (isExh(e)) {
        wallSeg(batch, display, e.a, e.b, 0, 7.6, e.len, 7.6);
        wallSeg(batch, curtain, e.a, e.b, 7.6, TOP, 6, FH * 1.0, 7.6);
      } else {
        wallSeg(batch, oldGround, e.a, e.b, 0, Z1, 7.2, Z1);
        wallSeg(batch, old, e.a, e.b, Z1, TOP, 7.2, FH, Z1);
      }
    }
    // 1960s slab bands (not on the new curtain wall).
    const exh = E.find(isExh);
    for (let k = 0; k < NF; k++) {
      const z = Z1 + k * FH - 0.4;
      for (const e of E) {
        if (isExh(e)) continue;
        const o = 0.25;
        const a = [e.a[0] + e.nx * o, e.a[1] + e.ny * o],
          b = [e.b[0] + e.nx * o, e.b[1] + e.ny * o];
        wallSeg(batch, conc, a, b, z, z + 0.4, 3, 3);
        batch.quad(
          conc,
          [e.a[0], e.a[1], z + 0.4],
          [e.b[0], e.b[1], z + 0.4],
          [b[0], b[1], z + 0.4],
          [a[0], a[1], z + 0.4],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    // Exhibition Road: aluminium fins, deep frame and entrance canopy.
    const X = frameOf(exh.a, exh.b);
    for (let u = 1.5; u < X.len - 1; u += 1.5) {
      const [x, y] = X.P(u, 0.3);
      kit.box(batch, alu, x, y, 7.6, 0.12, 0.6, TOP - 7.6, X.ang);
    }
    for (const u of [0.4, X.len - 0.4]) {
      const [x, y] = X.P(u, 0.5);
      kit.box(batch, alu, x, y, 0, 0.8, 1.0, TOP + 0.9, X.ang);
    }
    const f0 = X.P(0, 1),
      f1 = X.P(X.len, 1);
    hband(
      kit,
      batch,
      alu,
      [X.P(0, 0), X.P(X.len, 0), X.P(X.len, 1.0), X.P(0, 1.0)].map((p) => [p[0], p[1]]).reverse(),
      TOP,
      0.9,
      0,
    );
    const can = fixCCW(kit, rectRing(X, X.len * 0.45, X.len * 0.75, 0, 3.2));
    prism(kit, batch, alu, alu, [can], 4.6, 5.0, { bottom: true });
    // Roof.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, conc, [ring], TOP, 0.9, 0.3);
    roofClutter(kit, batch, kit.mat('aluminium'), ring, TOP, 0.71, 14, E[0].ang, 3);
    // Plant room / wind-tunnel housings on the south block.
    const S = frameOf(E[0].a, E[0].b);
    const plant = fixCCW(kit, rectRing(S, 12, 40, -26, -8));
    prism(kit, batch, kit.mat('#a9a8a2'), roofM, [plant], TOP, TOP + 4.2);
    hband(kit, batch, concDk, plant, TOP + 4.2, 0.4, 0.25);
    g.add(batch.toGroup('city_guilds'));
    return g;
  },
};
