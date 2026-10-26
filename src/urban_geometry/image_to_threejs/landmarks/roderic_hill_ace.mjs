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
// Local facade frame on edge a -> b of an outer CCW ring: u along the edge, n outward,
// z up. fN/fZ/fU emit correctly wound quads facing +n, +-z and +-u.
function local(kit, batch, a, b) {
  const dx = b[0] - a[0],
    dy = b[1] - a[1],
    len = Math.hypot(dx, dy) || 1;
  const ux = dx / len,
    uy = dy / len,
    nx = uy,
    ny = -ux;
  const ang = Math.atan2(dy, dx);
  const P = (u, n, z = 0) => [a[0] + ux * u + nx * n, a[1] + uy * u + ny * n, z];
  const T = 3;
  const q = (m, p, t) => batch.quad(m, p[0], p[1], p[2], p[3], t[0], t[1], t[2], t[3]);
  return {
    len,
    ang,
    P,
    fN(m, u0, u1, z0, z1, n = 0) {
      if (u1 - u0 < 1e-3 || z1 - z0 < 1e-3) return;
      q(
        m,
        [P(u0, n, z0), P(u1, n, z0), P(u1, n, z1), P(u0, n, z1)],
        [
          [u0 / T, z0 / T],
          [u1 / T, z0 / T],
          [u1 / T, z1 / T],
          [u0 / T, z1 / T],
        ],
      );
    },
    fZ(m, u0, u1, n0, n1, z, up = true) {
      if (u1 - u0 < 1e-3 || n1 - n0 < 1e-3) return;
      const p = [P(u0, n0, z), P(u0, n1, z), P(u1, n1, z), P(u1, n0, z)];
      const t = [
        [u0 / T, n0 / T],
        [u0 / T, n1 / T],
        [u1 / T, n1 / T],
        [u1 / T, n0 / T],
      ];
      if (!up) {
        p.reverse();
        t.reverse();
      }
      q(m, p, t);
    },
    fU(m, u, n0, n1, z0, z1, s = 1) {
      if (n1 - n0 < 1e-3 || z1 - z0 < 1e-3) return;
      const p = [P(u, n0, z0), P(u, n0, z1), P(u, n1, z1), P(u, n1, z0)];
      const t = [
        [n0 / T, z0 / T],
        [n0 / T, z1 / T],
        [n1 / T, z1 / T],
        [n1 / T, z0 / T],
      ];
      if (s < 0) {
        p.reverse();
        t.reverse();
      }
      q(m, p, t);
    },
    box(m, u, n, z0, w, d, h) {
      const [x, y] = P(u, n);
      kit.box(batch, m, x, y, z0, w, d, h, ang);
    },
  };
}
// Storeys of recessed openings on one edge: solid spandrel / head bands and piers
// in `wall`, glass set back by `inset` with reveals, frames, mullions and sills.
// ribbon: one continuous opening per storey with mullions every `bay / (mullions+1)`.
function bayFacade(L, o) {
  const {
    u0 = 0,
    u1 = L.len,
    z0 = 0,
    floors = 1,
    fh = 3.2,
    bay = 3.6,
    pier = 0.6,
    spandrel = 0.9,
    head = 0.4,
    inset = 0.25,
    wall,
    glass,
    frame = null,
    reveal = wall,
    mullions = 1,
    mullW = 0.07,
    transom = 0,
    sill = null,
    sillProj = 0.12,
    ribbon = false,
    endPier = 0.6,
    skip = null,
    surround = 0,
    surroundMat = null,
    keystone = false,
  } = o;
  const span = u1 - u0;
  if (span < 0.3) return;
  const nb = Math.max(1, Math.round(span / bay)),
    bw = span / nb;
  for (let f = 0; f < floors; f++) {
    const zb = z0 + f * fh,
      za = zb + spandrel,
      zc = zb + fh - head;
    if (span < Math.max(pier + 0.6, 1.2) || (skip && skip(f))) {
      L.fN(wall, u0, u1, zb, zb + fh);
      continue;
    }
    L.fN(wall, u0, u1, zb, za);
    L.fN(wall, u0, u1, zc, zb + fh);
    const ops = [];
    if (ribbon) ops.push([u0 + endPier, u1 - endPier]);
    else
      for (let i = 0; i < nb; i++) ops.push([u0 + i * bw + pier / 2, u0 + (i + 1) * bw - pier / 2]);
    let prev = u0;
    for (const [a, b] of ops) {
      L.fN(wall, prev, a, za, zc);
      prev = b;
    }
    L.fN(wall, prev, u1, za, zc);
    for (const [a, b] of ops) {
      const w = b - a,
        hh = zc - za;
      L.fN(glass, a, b, za, zc, -inset);
      L.fZ(reveal, a, b, -inset, 0, za, true);
      L.fZ(reveal, a, b, -inset, 0, zc, false);
      L.fU(reveal, a, -inset, 0, za, zc, 1);
      L.fU(reveal, b, -inset, 0, za, zc, -1);
      if (frame) {
        const n = -inset + 0.05;
        const m = ribbon ? Math.max(0, Math.round(w / (bay / (mullions + 1))) - 1) : mullions;
        for (let k = 1; k <= m; k++) L.box(frame, a + (w * k) / (m + 1), n, za, mullW, 0.1, hh);
        L.box(frame, (a + b) / 2, n, za, w, 0.1, mullW);
        L.box(frame, (a + b) / 2, n, zc - mullW, w, 0.1, mullW);
        if (!ribbon) {
          L.box(frame, a + mullW / 2, n, za, mullW, 0.1, hh);
          L.box(frame, b - mullW / 2, n, za, mullW, 0.1, hh);
        }
        if (transom) L.box(frame, (a + b) / 2, n, za + hh * transom, w, 0.1, mullW);
      }
      if (sill)
        L.box(
          sill,
          (a + b) / 2,
          (sillProj - inset) / 2,
          za - 0.07,
          w + 0.12,
          sillProj + inset,
          0.08,
        );
      if (surround) {
        const sm = surroundMat || wall;
        L.box(sm, a - surround / 2, 0.03, za, surround, 0.06, hh + surround);
        L.box(sm, b + surround / 2, 0.03, za, surround, 0.06, hh + surround);
        L.box(sm, (a + b) / 2, 0.03, zc, w + 2 * surround, 0.06, surround);
        if (keystone) L.box(sm, (a + b) / 2, 0.05, zc - 0.05, 0.4, 0.1, surround + 0.15);
      }
    }
  }
}
// Simple railing a -> b (top and bottom rails, square bars).
function railing(
  kit,
  batch,
  mat,
  a,
  b,
  z,
  { height = 1.1, spacing = 0.16, bar = 0.025, finials = false } = {},
) {
  const dx = b[0] - a[0],
    dy = b[1] - a[1],
    len = Math.hypot(dx, dy);
  if (len < 0.2) return;
  const ang = Math.atan2(dy, dx);
  const mx = (a[0] + b[0]) / 2,
    my = (a[1] + b[1]) / 2;
  kit.box(batch, mat, mx, my, z + height - 0.05, len, 0.05, 0.05, ang);
  kit.box(batch, mat, mx, my, z + 0.12, len, 0.04, 0.04, ang);
  const n = Math.max(1, Math.round(len / spacing));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const x = a[0] + dx * t,
      y = a[1] + dy * t;
    kit.box(batch, mat, x, y, z, bar, bar, height + (finials ? 0.08 : 0), ang);
    if (finials && i % 2 === 0)
      kit.box(batch, mat, x, y, z + height + 0.04, 0.06, 0.06, 0.08, ang + Math.PI / 4);
  }
}
// Flight of steps on a local frame: centred at u, from n0 outward, w wide.
function steps(L, mat, u, n0, w, count, rise = 0.15, tread = 0.32, narrow = 0) {
  for (let k = 0; k < count; k++) {
    const d = tread * (count - k);
    L.box(mat, u, n0 + d / 2, k * rise, w - narrow * k * 2, d, rise);
  }
}
// Fine painted wall tile without windows (stone / concrete / brick), 3 m square.
function plainTile(kit, key, base, seed, { joints = 0, brick = false, panels = 0 } = {}) {
  return kit.paintedMaterial(
    key,
    256,
    256,
    (c, w, h) => {
      c.fillStyle = base;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(seed);
      if (brick) {
        // 3 m tile: 40 courses of 75 mm, 13 bricks of 225 mm.
        const ch = h / 40,
          bw = w / 13;
        for (let y = 0; y < 40; y++)
          for (let x = -(y % 2) * 0.5; x < 13; x++) {
            const v = r();
            c.fillStyle = `rgba(${(v * 40) | 0},${(v * 18) | 0},${(v * 10) | 0},${0.1 + v * 0.18})`;
            c.fillRect(x * bw + 1, y * ch + 1, bw - 2, ch - 1.5);
          }
        c.fillStyle = 'rgba(230,220,200,0.25)';
        for (let y = 0; y < 40; y++) c.fillRect(0, y * ch, w, 1);
        return;
      }
      for (let i = 0; i < (w * h) / 40; i++) {
        c.fillStyle = `rgba(0,0,0,${(r() * 0.06).toFixed(3)})`;
        c.fillRect(r() * w, r() * h, 1 + r() * 3, 1 + r() * 2);
      }
      for (let i = 0; i < (w * h) / 120; i++) {
        c.fillStyle = `rgba(255,255,255,${(r() * 0.06).toFixed(3)})`;
        c.fillRect(r() * w, r() * h, 1 + r() * 2, 1 + r() * 2);
      }
      if (joints) {
        c.fillStyle = 'rgba(60,55,45,0.28)';
        const rows = joints;
        for (let y = 0; y < rows; y++) {
          c.fillRect(0, (y * h) / rows, w, 1.5);
          const off = (y % 2) * 0.5;
          for (let x = 0; x < 3; x++)
            c.fillRect(((x + off) * w) / 3, (y * h) / rows, 1.5, h / rows);
        }
      }
      if (panels) {
        c.fillStyle = 'rgba(40,40,40,0.22)';
        for (let i = 0; i < panels; i++) {
          c.fillRect((i * w) / panels, 0, 2, h);
          c.fillRect(0, (i * h) / panels, w, 2);
        }
      }
    },
    { roughness: 0.88 },
  );
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
    {
      title: 'ACEX & Bone - BMJ Architects',
      url: 'https://www.bmjarchitects.co.uk/projects/acex-%26-bone',
      used_for:
        'phased refurbishment: overcladding of the existing buildings, new render and windows, new welcoming entrance, rooftop extension',
    },
    {
      title: 'd+b facades to refurbish ACE building, Imperial College London',
      url: 'https://www.dbfacades.com/db-facades-to-refurbish-ace-building-imperial-college-london/',
      used_for: 'ACE building aluminium overcladding and replacement windows (2012)',
    },
  ],
  notes:
    'Heights from the footprint records (Roderic Hill 20 m / 6 floors, ACE Extension 16.8 m / 5 floors). Roderic Hill is drawn as a 1950s brick block with a rusticated Portland stone ground storey, stone window surrounds and a full-height stone-framed glazed entrance bay to Prince Consort Road; ACE as its 2010s aluminium overcladding with replacement ribbon windows and a glazed stair tower/entrance. Window rhythm, colours and signage are plausible reconstructions; no photographs were available.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const rh = byId['344bf538-7f01-4ffe-a7b6-91e36dc0fee1'];
    const ace = byId['d13c2f28-2406-4392-abff-fb031588b15e'];
    const rr = rh.polys[0][0],
      ar = ace.polys[0][0];
    const stone = kit.mat('portland_stone');
    const stoneT = plainTile(kit, 'rh:stone', '#dcd5c3', 0.18, { joints: 8 });
    const stoneP = plainTile(kit, 'rh:stoneplain', '#d6cfbd', 0.19);
    const brick = plainTile(kit, 'rh:brick', '#8f5a44', 0.17, { brick: true });
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const white = kit.mat('#ece8de', { roughness: 0.5 });
    // ---- Roderic Hill ----
    const RZ1 = 4.4,
      RFH = (rh.h - RZ1) / 5,
      RT = rh.h;
    const front = edges(rr).find((e) => Math.abs(e.a[0] - 1574.2) < 0.5);
    const F = frameOf(front.a, front.b); // u west along the road, n north
    const bayU0 = front.len / 2 - 5,
      bayU1 = front.len / 2 + 5;
    for (const e of edges(rr)) {
      const L = local(kit, batch, e.a, e.b);
      const isFront = e.k === front.k;
      const segs = isFront
        ? [
            [0, bayU0 - 0.2],
            [bayU1 + 0.2, e.len],
          ]
        : [[0, e.len]];
      if (isFront) L.fN(stoneP, bayU0 - 0.2, bayU1 + 0.2, 0, RT);
      for (const [u0, u1] of segs) {
        bayFacade(L, {
          u0,
          u1,
          z0: 0,
          floors: 1,
          fh: RZ1,
          bay: 3.0,
          pier: 1.1,
          spandrel: 0.75,
          head: 0.85,
          inset: 0.22,
          wall: stoneT,
          reveal: stoneP,
          glass,
          frame: white,
          mullions: 2,
          transom: 0.72,
          sill: stone,
          sillProj: 0.08,
          keystone: true,
          surround: 0.01,
          surroundMat: stone,
        });
        bayFacade(L, {
          u0,
          u1,
          z0: RZ1,
          floors: 5,
          fh: RFH,
          bay: 3.0,
          pier: 1.25,
          spandrel: 0.85,
          head: 0.55,
          inset: 0.2,
          wall: brick,
          reveal: stoneP,
          glass,
          frame: white,
          mullions: 2,
          transom: 0.7,
          sill: stone,
          sillProj: 0.08,
          surround: 0.14,
          surroundMat: stone,
        });
      }
    }
    kit.cornice(batch, stone, rr, 0, { height: 0.5, projection: 0.1 });
    kit.cornice(batch, stone, rr, RZ1 - 0.35, { height: 0.45, projection: 0.2 });
    kit.cornice(batch, stone, rr, RT - 0.6, { height: 0.6, projection: 0.35, steps: 2 });
    kit.cap(batch, kit.roof('flat', 0), [[rr]], RT + 0.05);
    parapet(kit, batch, stone, [rr], RT, 0.8, 0.3);
    kit.cornice(batch, kit.mat('#e6e0d0'), rr, RT + 0.8, { height: 0.1, projection: 0.06 });
    // Stone-framed glazed entrance bay on Prince Consort Road.
    {
      const L = local(kit, batch, front.a, front.b);
      const bw = bayU1 - bayU0;
      // projecting frame
      L.box(stone, bayU0 + 0.45, 0.45, 0, 0.9, 0.9, RT + 0.8);
      L.box(stone, bayU1 - 0.45, 0.45, 0, 0.9, 0.9, RT + 0.8);
      L.box(stone, (bayU0 + bayU1) / 2, 0.45, RT - 0.6, bw, 0.9, 1.4);
      // full-height glazed screen with stone mullions and floor transoms
      const gu0 = bayU0 + 0.9,
        gu1 = bayU1 - 0.9;
      L.fN(glass, gu0, gu1, 3.2, RT - 0.6, 0.1);
      for (let k = 0; k <= 4; k++)
        L.box(stone, gu0 + ((gu1 - gu0) * k) / 4, 0.3, 3.2, 0.3, 0.4, RT - 3.8);
      for (let k = 0; k < 5; k++)
        L.box(stone, (gu0 + gu1) / 2, 0.3, RZ1 + k * RFH - 0.25, gu1 - gu0, 0.4, 0.25);
      for (let k = 0; k < 4; k++)
        for (let j = 0; j < 5; j++) {
          const uu = gu0 + ((gu1 - gu0) * (k + 0.5)) / 4;
          L.box(white, uu, 0.16, RZ1 + j * RFH + RFH * 0.45, (gu1 - gu0) / 4 - 0.3, 0.06, 0.06);
          L.box(white, uu, 0.16, RZ1 + j * RFH, 0.06, 0.06, RFH - 0.25);
        }
      // entrance doors, canopy, steps and name
      L.fN(kit.mat('#2a3138'), gu0, gu1, 0.45, 3.2, 0.1);
      for (let k = 1; k < 4; k++)
        L.box(kit.mat('#9aa1a6'), gu0 + ((gu1 - gu0) * k) / 4, 0.15, 0.45, 0.08, 0.08, 2.75);
      L.box(stone, (bayU0 + bayU1) / 2, 1.6, 3.2, bw + 0.6, 2.4, 0.35);
      steps(L, stone, (bayU0 + bayU1) / 2, 0.9, bw - 1.8, 3, 0.15, 0.35);
      const name = kit.paintedMaterial('rh:name', 512, 64, (c, w, h) => {
        c.fillStyle = '#dcd5c3';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#3a3a3a';
        c.font = 'bold 32px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('RODERIC HILL BUILDING', w / 2, h / 2);
      });
      const [x, y] = L.P((bayU0 + bayU1) / 2, 2.81);
      const pg = new THREE.PlaneGeometry(bw - 1, 0.32).rotateX(Math.PI / 2);
      batch.addGeometry(name, pg, new THREE.Matrix4().makeRotationZ(L.ang).setPosition(x, y, 3.38));
      kit.cap(batch, stone, [[fixCCW(kit, rectRing(F, bayU0, bayU1, 0, 0.9))]], RT + 0.8);
    }
    // Area railings along Prince Consort Road (both front edges), gap at the steps.
    const iron = kit.mat('#1f2224', { roughness: 0.5, metalness: 0.4 });
    for (const e of edges(rr).filter((x) => Math.abs(x.ang + 3.04) < 0.05)) {
      const L = local(kit, batch, e.a, e.b);
      const parts =
        e.k === front.k
          ? [
              [0.3, bayU0 - 0.8],
              [bayU1 + 0.8, e.len - 0.3],
            ]
          : [[0.3, e.len - 0.3]];
      for (const [u0, u1] of parts)
        railing(kit, batch, iron, L.P(u0, 1.4), L.P(u1, 1.4), 0, {
          height: 1.1,
          spacing: 0.13,
          finials: true,
        });
    }
    // Copper-roofed plant penthouse with louvres.
    const ph = fixCCW(kit, rectRing(F, 8, front.len - 10, -12, -3));
    const louvre = painted(kit, 'rh:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#cfc8b6');
      c.fillStyle = 'rgba(60,55,45,0.45)';
      for (let x = 10; x < w; x += 42) for (let y = 30; y < h - 10; y += 6) c.fillRect(x, y, 24, 2);
    });
    prism(kit, batch, louvre, null, [ph], RT, RT + 3.0, { tw: 3, th: 3 });
    kit.pitchedRoof(batch, kit.mat('copper_green'), stone, ph, F.ang, RT + 3.0, 1.4, 'hipped', {
      overhang: 0.3,
    });
    // ---- ACE Extension ----
    const AZ1 = 4.0,
      AT = ace.h,
      AFH = (AT - AZ1) / 4;
    const clad = plainTile(kit, 'ace:clad', '#a3a9ad', 0.21, { panels: 3 });
    const cladDk = kit.mat('#5c6f7e', { roughness: 0.5, metalness: 0.3 });
    const aframe = kit.mat('#c2c7ca', { roughness: 0.4, metalness: 0.5 });
    for (const e of edges(ar)) {
      const L = local(kit, batch, e.a, e.b);
      bayFacade(L, {
        z0: 0,
        floors: 1,
        fh: AZ1,
        bay: 3.0,
        pier: 0.3,
        spandrel: 0.3,
        head: 0.6,
        inset: 0.2,
        wall: clad,
        glass: kit.mat('#3e505c', { roughness: 0.18, metalness: 0.15 }),
        frame: aframe,
        mullions: 1,
        transom: 0.75,
      });
      bayFacade(L, {
        z0: AZ1,
        floors: 4,
        fh: AFH,
        bay: 1.5,
        ribbon: true,
        endPier: 0.4,
        spandrel: 1.0,
        head: 0.3,
        inset: 0.18,
        wall: clad,
        reveal: cladDk,
        glass,
        frame: aframe,
        mullions: 1,
        transom: 0.78,
      });
    }
    for (let k = 1; k < 4; k++)
      kit.cornice(batch, cladDk, ar, AZ1 + k * AFH - 0.12, { height: 0.12, projection: 0.08 });
    kit.cornice(batch, aframe, ar, AT - 0.5, { height: 0.5, projection: 0.3 });
    kit.cap(batch, kit.roof('flat', 2), [[ar]], AT + 0.05);
    parapet(kit, batch, kit.mat('#b4babd'), [ar], AT, 0.9, 0.25);
    const aceL = painted(kit, 'ace:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#a5a9a9');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.4)';
        c.fillRect(0, y, w, 2);
      }
    });
    roofClutter(kit, batch, aceL, ar, AT, 0.21, 14, F.ang, 2.5);
    {
      const fan = new THREE.CylinderGeometry(0.55, 0.55, 0.3, 12).rotateX(Math.PI / 2);
      const AF = frameOf([1604.4, -821.9], [1632.7, -818.0]);
      for (let k = 0; k < 5; k++) {
        const [x, y] = AF.P(4 + k * 4.5, -10);
        kit.box(batch, kit.mat('#c4c8c9'), x, y, AT, 2.4, 2.4, 1.3, AF.ang);
        batch.addGeometry(
          kit.mat('#3b4044'),
          fan,
          new THREE.Matrix4().makeTranslation(x, y, AT + 1.45),
        );
      }
      fan.dispose();
      const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
      const rin = kit.offsetRing(ar, -1.0);
      for (let k = 0; k < rin.length; k++)
        if (
          Math.hypot(
            rin[k][0] - rin[(k + 1) % rin.length][0],
            rin[k][1] - rin[(k + 1) % rin.length][1],
          ) > 3
        )
          railing(kit, batch, rail, rin[k], rin[(k + 1) % rin.length], AT, {
            height: 1.1,
            spacing: 1.5,
            bar: 0.05,
          });
    }
    // Glazed stair tower / entrance on the long south face.
    const se = edges(ar)
      .filter((e) => e.len > 25)
      .sort((a, b) => a.a[1] - b.a[1])[0];
    const S = frameOf(se.a, se.b);
    const st = fixCCW(kit, rectRing(S, se.len / 2 - 3, se.len / 2 + 3, -1, 2.5));
    wallsM(
      batch,
      kit.mat('#6f9592', { roughness: 0.15, metalness: 0.25 }),
      [st],
      0,
      AT + 2.6,
      3,
      3,
    );
    kit.cap(batch, kit.mat('#b4babd'), [[st]], AT + 2.6);
    fins(kit, batch, aframe, st, 0, AT + 2.6, 2, 0.15, 0.15, { minLen: 1 });
    for (let k = 1; k <= 5; k++)
      kit.cornice(batch, aframe, st, k * 3.3, { height: 0.12, projection: 0.12 });
    {
      const L = local(kit, batch, se.a, se.b);
      L.box(aframe, se.len / 2, 3.8, 3.4, 8, 2.8, 0.25);
      L.box(kit.mat('#2a3138'), se.len / 2, 2.52, 0, 2.4, 0.06, 2.6);
      const sign = kit.paintedMaterial('ace:sign', 1024, 96, (c, w, h) => {
        c.fillStyle = '#0f2f57';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#ffffff';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.font = 'bold 44px sans-serif';
        c.fillText('ACE Extension', w * 0.25, h / 2);
        c.font = '32px sans-serif';
        c.fillText('Aeronautics · Chemical Engineering', w * 0.7, h / 2);
      });
      const [x, y] = L.P(se.len / 2, 5.22);
      const pg = new THREE.PlaneGeometry(7.8, 0.6).rotateX(Math.PI / 2);
      batch.addGeometry(sign, pg, new THREE.Matrix4().makeRotationZ(L.ang).setPosition(x, y, 3.65));
    }
    g.add(batch.toGroup('roderic_hill_ace'));
    {
      const L = local(kit, batch, se.a, se.b);
      g.add(
        ctx.placeAssets(
          'bicycle_stand',
          [-9, -7.5, -6, 6, 7.5, 9].map((d) => [
            ...L.P(se.len / 2 + d, 3.5).slice(0, 2),
            L.ang + Math.PI / 2,
          ]),
        ),
      );
      g.add(ctx.placeAssets('bench', [[...L.P(se.len / 2 + 13, 3).slice(0, 2), L.ang + Math.PI]]));
    }
    return g;
  },
};
