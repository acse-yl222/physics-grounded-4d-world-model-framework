// Roderic Hill Building and ACE Extension, Imperial College South Kensington
// (Aeronautics and Chemical Engineering). Roderic Hill was opened on 28 May 1957
// by Queen Elizabeth the Queen Mother on the former Queen's lawn behind Prince
// Consort Road, a steel-framed six-storey block housing aeronautics and its
// aerostructures laboratory; the later ACE (Aeronautics & Chemical Engineering)
// Extension runs behind it towards the Sherfield Building. Modelled: Roderic
// Hill as a 1950s Portland-stone-dressed brick block with a stone-framed
// entrance bay to Prince Consort Road and a copper-roofed top-floor plant
// penthouse; ACE Extension as a five-storey grey metal-clad block with ribbon
// glazing, blue-grey spandrels and a glazed stair tower.

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
  id: 'roderic_hill_ace',
  name: 'Roderic Hill Building and ACE Extension (Imperial College)',
  claims: [
    '344bf538-7f01-4ffe-a7b6-91e36dc0fee1', // Roderic Hill Building
    'd13c2f28-2406-4392-abff-fb031588b15e', // ACE Extension
  ],
  references: [
    {
      title: 'Aeronautics department history - Imperial College',
      url: 'https://www.imperial.ac.uk/engineering/departments/aeronautics/about/history/',
      used_for:
        'Roderic Hill Building opened 28 May 1957 by the Queen Mother; aerostructures laboratory',
    },
    {
      title: 'Centenary memories (Oakley) - Imperial College',
      url: 'https://www.imperial.ac.uk/centenary/memories/oakley.shtml',
      used_for:
        "steel girders on the former Queen's lawn; Bone Building beside it with a courtyard behind",
    },
    {
      title: 'South Kensington campus map (Imperial College)',
      url: 'https://www.sbg.bio.ic.ac.uk/files/SouthKensingtonCampus.pdf',
      used_for: 'occupants of Roderic Hill, Bone and ACE Extension',
    },
    {
      title: "Roderic Maxwell Hill - Grace's Guide",
      url: 'https://www.gracesguide.co.uk/Roderic_Maxwell_Hill',
      used_for: 'namesake (Rector)',
    },
  ],
  notes:
    'Heights from the footprint records (Roderic Hill 20 m / 6 floors, ACE Extension 16.8 m / 5 floors). Facade materials and patterns are plausible reconstructions for their periods; no photographs were available.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const rh = byId['344bf538-7f01-4ffe-a7b6-91e36dc0fee1'];
    const ace = byId['d13c2f28-2406-4392-abff-fb031588b15e'];
    const rr = rh.polys[0][0],
      ar = ace.polys[0][0];
    const stone = kit.mat('portland_stone');
    // ---- Roderic Hill ----
    const RZ1 = 4.4,
      RFH = (rh.h - RZ1) / 5,
      RT = rh.h;
    const brick = painted(kit, 'rh:brick', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#8f5a44');
      const r = kit.rng(0.17);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          c.fillStyle = `rgba(${120 + r() * 40},${70 + r() * 25},${50 + r() * 20},0.9)`;
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      for (let i = 0; i < 3; i++) {
        const x = 12 + i * 82;
        c.fillStyle = '#ddd6c4';
        c.fillRect(x - 5, h * 0.18, 68, h * 0.72);
        win(c, x, 0.24, 58, 0.86, h, '#2a333a', '#e8e4da', 3, 3);
      }
    });
    const rhGround = painted(kit, 'rh:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#d6cfbd');
      grain(c, w, h, 0.18, kit, 0.06);
      c.fillStyle = 'rgba(90,80,60,0.3)';
      for (let y = 0; y < h; y += 16) c.fillRect(0, y, w, 1.5);
      for (let i = 0; i < 3; i++) win(c, 14 + i * 82, 0.15, 56, 0.8, h, '#2a333a', '#e8e4da', 3, 3);
    });
    wallsM(batch, rhGround, [rr], 0, RZ1, 7.5, RZ1);
    wallsM(batch, brick, [rr], RZ1, RT, 7.5, RFH, RZ1);
    hband(kit, batch, stone, rr, RZ1 - 0.35, 0.45, 0.2);
    hband(kit, batch, stone, rr, RT - 0.6, 0.6, 0.35);
    kit.cap(batch, kit.roof('flat', 0), [[rr]], RT + 0.05);
    parapet(kit, batch, stone, [rr], RT, 0.8, 0.3);
    // Stone entrance bay on Prince Consort Road.
    const front = edges(rr).find((e) => Math.abs(e.a[0] - 1574.2) < 0.5);
    const F = frameOf(front.a, front.b); // u west along the road, n north
    const bayR = fixCCW(kit, rectRing(F, front.len / 2 - 5, front.len / 2 + 5, -0.2, 0.9));
    const entr = painted(kit, 'rh:entrance', 256, 512, (c, w, h) => {
      fillTile(c, w, h, '#e0d9c7');
      grain(c, w, h, 0.19, kit, 0.05);
      c.fillStyle = '#2a333a';
      c.fillRect(w * 0.2, h * 0.08, w * 0.6, h * 0.8);
      c.fillStyle = '#e8e4da';
      for (let i = 1; i < 4; i++) c.fillRect(w * 0.2 + (i * w * 0.6) / 4 - 2, h * 0.08, 4, h * 0.8);
      for (let k = 1; k < 6; k++) c.fillRect(w * 0.2, h * 0.08 + (k * h * 0.8) / 6, w * 0.6, 5);
      c.fillStyle = '#3a2c22';
      c.fillRect(w * 0.3, h * 0.9, w * 0.4, h * 0.1);
    });
    wallsM(batch, entr, [bayR], 0, RT + 0.8, 10, RT + 0.8);
    kit.cap(batch, stone, [[bayR]], RT + 0.8);
    // Copper-roofed plant penthouse.
    const ph = fixCCW(kit, rectRing(F, 8, front.len - 10, -12, -3));
    prism(kit, batch, kit.mat('#cfc8b6'), null, [ph], RT, RT + 3.0);
    kit.pitchedRoof(batch, kit.mat('copper_green'), stone, ph, F.ang, RT + 3.0, 1.4, 'hipped', {
      overhang: 0.3,
    });
    // ---- ACE Extension ----
    const AZ1 = 4.0,
      AT = ace.h,
      AFH = (AT - AZ1) / 4;
    const clad = painted(kit, 'ace:clad', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#9ea4a8');
      c.fillStyle = 'rgba(0,0,0,0.15)';
      for (let i = 0; i < 8; i++) c.fillRect((i * w) / 8, 0, 1.5, h);
      c.fillStyle = '#5c6f7e';
      c.fillRect(0, h * 0.08, w, h * 0.2);
      c.fillStyle = '#23313b';
      c.fillRect(0, h * 0.36, w, h * 0.52);
      c.fillStyle = '#c2c7ca';
      for (let i = 0; i < 4; i++) c.fillRect((i * w) / 4, h * 0.36, 5, h * 0.52);
      c.fillStyle = 'rgba(190,210,225,0.22)';
      c.fillRect(0, h * 0.36, w, h * 0.2);
    });
    const aceGround = painted(kit, 'ace:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2a363f');
      c.fillStyle = '#9ea4a8';
      c.fillRect(0, 0, w, h * 0.15);
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 3, 0, 6, h);
      c.fillStyle = 'rgba(200,220,235,0.2)';
      c.fillRect(0, h * 0.15, w, h * 0.3);
    });
    wallsM(batch, aceGround, [ar], 0, AZ1, 6, AZ1);
    wallsM(batch, clad, [ar], AZ1, AT, 6, AFH, AZ1);
    hband(kit, batch, kit.mat('#c2c7ca'), ar, AT - 0.5, 0.5, 0.3);
    kit.cap(batch, kit.roof('flat', 2), [[ar]], AT + 0.05);
    parapet(kit, batch, kit.mat('#b4babd'), [ar], AT, 0.9, 0.25);
    roofClutter(kit, batch, kit.mat('aluminium'), ar, AT, 0.21, 12, F.ang, 2.5);
    // Glazed stair tower on the long south face.
    const se = edges(ar)
      .filter((e) => e.len > 25)
      .sort((a, b) => a.a[1] - b.a[1])[0];
    const S = frameOf(se.a, se.b);
    const st = fixCCW(kit, rectRing(S, se.len / 2 - 3, se.len / 2 + 3, -1, 2.5));
    wallsM(batch, kit.mat('green_glass'), [st], 0, AT + 2.6, 3, 3);
    kit.cap(batch, kit.mat('#b4babd'), [[st]], AT + 2.6);
    fins(kit, batch, kit.mat('#c2c7ca'), st, 0, AT + 2.6, 2, 0.15, 0.15, { minLen: 1 });
    g.add(batch.toGroup('roderic_hill_ace'));
    return g;
  },
};
