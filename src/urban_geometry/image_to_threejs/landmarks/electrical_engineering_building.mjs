// Electrical & Electronic Engineering Building, Imperial College South Kensington.
// 1960s slab tower (part of the Jubilee expansion; Norman & Dawbarn era) rising
// ~14 storeys over Dalby Court. Modelled as a reinforced-concrete slab with
// continuous ribbon windows and slab-edge bands on the long east/west faces,
// blank end walls with a stair-window strip, a recessed glazed ground floor on
// pilotis (re-fronted reception, 2002), and a set-back rooftop plant storey with
// antenna masts.

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
  id: 'electrical_engineering_building',
  name: 'Electrical & Electronic Engineering Building (Imperial College)',
  claims: ['031912fe-8683-49ce-8793-860351f0b479'],
  references: [
    {
      title: 'EEE at a glance - Imperial College London',
      url: 'https://www.imperial.ac.uk/electrical-engineering/about/at-a-glance/',
      used_for: 'dedicated department building at the heart of the South Kensington campus',
    },
    {
      title: "Kontor's £1.1 million Imperial fitout - Skanska",
      url: 'https://skanska.co.uk/about-skanska/news-and-events/press-releases/48178/Kontors-1.1-million-Imperial-fitout',
      used_for: 'lower-level facade stripped and re-formed as a glazed reception (2002)',
    },
    {
      title: 'Survey of London vol. 38, plate 76',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for: "1960-9 Imperial College buildings by Norman and Dawbarn behind the Queen's Tower",
    },
  ],
  notes:
    'No photographs could be downloaded; elevation rhythm (ribbon windows, slab bands, blank ends) is reconstructed from memory of the tower and the generic 1960s Imperial idiom. Height from the footprint record (45.6 m, 14 floors); plant storey and masts are approximate.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const b = byId['031912fe-8683-49ce-8793-860351f0b479'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const conc = kit.mat('#bdb6aa', { roughness: 0.9 });
    const concDark = kit.mat('#8d877e');
    const glass = kit.mat('dark_glass');
    const roofM = kit.mat('#9a968f');
    const FH = 3.15,
      Z1 = 4.5,
      NF = 13,
      TOP = Z1 + NF * FH; // 45.45 m
    const ribbon = painted(kit, 'eee:ribbon', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#c3bcb0');
      grain(c, w, h, 0.41, kit, 0.07);
      c.fillStyle = '#26323b';
      c.fillRect(0, h * 0.1, w, h * 0.56);
      const gr = c.createLinearGradient(0, h * 0.1, 0, h * 0.66);
      gr.addColorStop(0, 'rgba(170,195,215,0.35)');
      gr.addColorStop(1, 'rgba(170,195,215,0.02)');
      c.fillStyle = gr;
      c.fillRect(0, h * 0.1, w, h * 0.56);
      c.fillStyle = '#5a5f62';
      for (let i = 0; i < 4; i++) c.fillRect((i * w) / 4, h * 0.1, 5, h * 0.56);
      c.fillRect(0, h * 0.42, w, 2);
      c.fillStyle = 'rgba(0,0,0,0.25)';
      c.fillRect(0, h * 0.66, w, 3);
    });
    const endwall = painted(kit, 'eee:end', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#b8b1a5');
      grain(c, w, h, 0.43, kit, 0.08);
      c.fillStyle = 'rgba(0,0,0,0.12)';
      for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 1, h);
      c.fillRect(0, h * 0.5, w, 1);
    });
    const lobby = painted(kit, 'eee:lobby', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2b3a44');
      c.fillStyle = '#7c8a92';
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 3, 0, 6, h);
      c.fillRect(0, h * 0.25, w, 4);
      c.fillStyle = 'rgba(220,235,245,0.25)';
      c.fillRect(0, 0, w, h * 0.25);
    });
    const E = edges(ring);
    const isLong = (e) => e.len > 40;
    // Ground floor: recessed glazed lobby and perimeter pilotis.
    const inner = kit.offsetRing(ring, -1.4);
    wallsM(batch, lobby, [inner], 0, Z1, 5, Z1);
    fins(kit, batch, concDark, ring, 0, Z1, 6.5, 0.7, 0.7, { minLen: 3 });
    // Tower faces.
    for (const e of E) {
      const m = isLong(e) ? ribbon : endwall;
      wallSeg(batch, m, e.a, e.b, Z1, TOP, isLong(e) ? 5 : 4, FH * (isLong(e) ? 1 : 2), Z1);
    }
    kit.cap(batch, concDark, [[ring]], Z1, { down: true });
    // Stair window strip on the end walls.
    for (const e of E.filter((x) => !isLong(x))) {
      const mx = (e.a[0] + e.b[0]) / 2 + e.nx * 0.08,
        my = (e.a[1] + e.b[1]) / 2 + e.ny * 0.08;
      kit.box(batch, glass, mx, my, Z1 + 1, 1.6, 0.16, TOP - Z1 - 2, e.ang);
      kit.box(batch, conc, mx + e.nx * 0.2, my + e.ny * 0.2, Z1, 0.5, 0.4, TOP - Z1, e.ang);
    }
    // Slab-edge bands at every floor and corner piers.
    for (let k = 0; k < NF; k++) hband(kit, batch, conc, ring, Z1 + k * FH - 0.35, 0.35, 0.22);
    fins(kit, batch, conc, ring, Z1, TOP, 200, 0.45, 0.9, { minLen: 3 });
    // Roof: parapet, set-back plant storey, lift motor rooms, masts.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, conc, [ring], TOP, 1.1, 0.3);
    const F = frameOf(E[0].a, E[0].b); // south edge, u east, n south
    const L = E[1].len;
    const plant = fixCCW(kit, rectRing(F, 3, E[0].len - 3, -L + 12, -14));
    prism(kit, batch, endwall, roofM, [plant], TOP, TOP + 3.6, { tw: 4, th: 6.3 });
    hband(kit, batch, concDark, plant, TOP + 3.6, 0.4, 0.3);
    const lift = fixCCW(kit, rectRing(F, 6, 13, -12, -6));
    prism(kit, batch, endwall, roofM, [lift], TOP, TOP + 5.5, { tw: 4, th: 6.3 });
    const steel = kit.mat('dark_steel');
    const masts = [F.P(4, -5, 0), F.P(E[0].len - 4, -L + 6, 0), F.P(E[0].len / 2, -L / 2, 0)];
    masts.forEach(([x, y], i) => {
      const h = i === 2 ? 12 : 8;
      const z0 = i === 2 ? TOP + 4 : TOP;
      const m = new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2);
      const geo = new THREE.CylinderGeometry(0.12, 0.18, h, 6).rotateX(Math.PI / 2);
      batch.addGeometry(steel, geo, m);
      for (let k = 1; k <= 2; k++) {
        const d = new THREE.BoxGeometry(1.6, 0.08, 0.08);
        batch.addGeometry(
          steel,
          d,
          new THREE.Matrix4().makeTranslation(x, y, z0 + h * (0.5 + k * 0.2)),
        );
      }
    });
    // Cooling units on the plant roof.
    for (let k = 0; k < 3; k++) {
      const [x, y] = F.P(6 + k * 3.5, -L / 2 + 4, 0);
      kit.box(batch, kit.mat('aluminium'), x, y, TOP + 4, 2.4, 2.4, 1.4, F.ang);
    }
    g.add(batch.toGroup('eee'));
    return g;
  },
};
