// Huxley Building, 180 Queen's Gate, Imperial College South Kensington
// (Mathematics and Computing). Post-war concrete block on the east side of
// Queen's Gate, on the site of William Emerson's 178 Queen's Gate, linked to the
// Blackett Laboratory; widely disliked for its looks (2024 "Christopher Wren
// Demolition Award" finalist in Felix). Modelled as an eight-storey block with
// two light wells: dark ribbon windows between heavy exposed-aggregate concrete
// spandrels, close-set vertical concrete fins on the Queen's Gate front, a
// recessed ground floor, plant on the roof and the small domed rooftop structure
// recorded in the footprint data at its north edge.

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
  id: 'huxley_building',
  name: 'Huxley Building (Imperial College)',
  claims: ['5add8849-9cf4-47d8-8c51-468c40d01959'],
  references: [
    {
      title: "Queen's Gate - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Queen%27s_Gate',
      used_for: "Huxley Building on the east side of Queen's Gate",
    },
    {
      title: 'The exterior of 178 Queens Gate (Historic England)',
      url: 'https://historicengland.org.uk/images-books/photos/item/BL13479',
      used_for: "site formerly occupied by William Emerson's house",
    },
    {
      title: 'Huxley Building architecture competition finalist - Felix',
      url: 'https://felixonline.co.uk/articles/huxley-building-architecture-competition-finalist/',
      used_for: 'brutalist-era concrete building with a poor public image',
    },
    {
      title: 'South Kensington campus venues - Imperial College',
      url: 'https://imperial.ac.uk/events-and-hospitality/venues/south-kensington-campus-venues',
      used_for: 'building identity / use',
    },
  ],
  notes:
    'Massing, light wells and the domed rooftop part (32-36 m) come from the footprint record; facade rhythm, colours and the drum under the dome are reconstructions without photographic confirmation.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const b = byId['5add8849-9cf4-47d8-8c51-468c40d01959'];
    const poly = b.polys[0];
    const ring = poly[0];
    const batch = new kit.MeshBatch();
    const conc = kit.mat('#a8a092', { roughness: 0.95 });
    const concDk = kit.mat('#6f6a62');
    const Z1 = 4.2,
      NF = 7,
      FH = (b.h - Z1) / NF,
      TOP = b.h;
    const band = painted(kit, 'huxley:band', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#a69e90');
      grain(c, w, h, 0.71, kit, 0.12);
      grain(c, w, h, 0.72, kit, 0.08, '255,255,255');
      c.fillStyle = '#1f2a31';
      c.fillRect(0, h * 0.4, w, h * 0.46);
      c.fillStyle = '#4b4f50';
      for (let i = 0; i < 6; i++) c.fillRect((i * w) / 6, h * 0.4, 4, h * 0.46);
      c.fillStyle = 'rgba(190,210,225,0.18)';
      c.fillRect(0, h * 0.4, w, h * 0.15);
      c.fillStyle = 'rgba(0,0,0,0.25)';
      c.fillRect(0, h * 0.86, w, 4);
    });
    const ground = painted(kit, 'huxley:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2b3339');
      c.fillStyle = '#857e72';
      c.fillRect(0, 0, w, h * 0.18);
      for (let i = 0; i <= 3; i++) c.fillRect((i * w) / 3 - 5, 0, 10, h);
      c.fillStyle = 'rgba(210,225,235,0.18)';
      c.fillRect(0, h * 0.18, w, h * 0.25);
    });
    const court = painted(kit, 'huxley:court', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#b2ab9e');
      grain(c, w, h, 0.73, kit, 0.08);
      for (let i = 0; i < 2; i++) win(c, 8 + i * 64, 0.3, 48, 0.85, h, '#2c363e', '#55595b', 1, 3);
    });
    // Recessed ground storey with column line.
    const inner = kit.offsetRing(ring, -1.0);
    wallsM(batch, ground, [inner], 0, Z1, 7.5, Z1);
    kit.cap(batch, concDk, [[ring]], Z1, { down: true });
    fins(kit, batch, concDk, ring, 0, Z1, 7.5, 0.7, 0.7, { minLen: 8 });
    // Upper storeys: outer faces banded, light wells plainer.
    wallsM(batch, band, [ring], Z1, TOP, 7.5, FH, Z1);
    wallsM(batch, court, poly.slice(1), 0, TOP, 3.6, FH * 2, 0);
    for (let k = 0; k < NF; k++) hband(kit, batch, conc, ring, Z1 + k * FH - 0.5, 0.5, 0.35);
    // Queen's Gate front: close-set vertical concrete fins.
    const qg = edges(ring).find((e) => Math.abs(e.a[0] - 1448.2) < 0.5);
    fins(kit, batch, conc, ring, Z1 - 0.5, TOP, 2.5, 0.55, 0.3, {
      minLen: 50,
      skip: (e) => e.k !== qg.k,
    });
    // Roof: cap with holes, parapets, plant.
    kit.cap(batch, kit.roof('flat', 2), [poly], TOP);
    parapet(kit, batch, conc, poly, TOP, 1.1, 0.35);
    const F = frameOf(qg.a, qg.b);
    roofClutter(kit, batch, kit.mat('aluminium'), ring, TOP, 0.75, 14, F.ang, 3, poly.slice(1));
    const plant = fixCCW(kit, rectRing(F, 16, 30, -50, -38));
    prism(kit, batch, kit.mat('#9b968c'), kit.roof('flat', 1), [plant], TOP, TOP + 3.4);
    // Domed rooftop structure (part 375b4f29: 32-36 m) on a drum.
    const part = b.parts?.[0];
    if (part) {
      const pr = part.polys[0][0];
      const cx = pr.reduce((s, p) => s + p[0], 0) / pr.length,
        cy = pr.reduce((s, p) => s + p[1], 0) / pr.length;
      const rad = Math.max(...pr.map((p) => Math.hypot(p[0] - cx, p[1] - cy))) * 0.95;
      const zD = part.minh ?? 32;
      const drum = new THREE.CylinderGeometry(rad, rad, zD - TOP, 20, 1, true).rotateX(Math.PI / 2);
      batch.addGeometry(
        kit.mat('#b9b3a6'),
        drum,
        new THREE.Matrix4().makeTranslation(cx, cy, (TOP + zD) / 2),
      );
      const ring2 = new THREE.CylinderGeometry(rad + 0.35, rad + 0.35, 0.4, 20).rotateX(
        Math.PI / 2,
      );
      batch.addGeometry(conc, ring2, new THREE.Matrix4().makeTranslation(cx, cy, zD - 0.2));
      const dome = new THREE.SphereGeometry(rad, 20, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      batch.addGeometry(
        kit.mat('#e9ebea', { roughness: 0.4, metalness: 0.3 }),
        dome,
        new THREE.Matrix4()
          .makeTranslation(cx, cy, zD)
          .multiply(new THREE.Matrix4().makeScale(1, 1, (part.h - zD) / rad)),
      );
      kit.box(
        batch,
        kit.mat('dark_steel'),
        cx + rad * 0.35,
        cy,
        zD + 0.4,
        0.9,
        0.2,
        (part.h - zD) * 0.8,
        0,
      );
    }
    g.add(batch.toGroup('huxley'));
    return g;
  },
};
