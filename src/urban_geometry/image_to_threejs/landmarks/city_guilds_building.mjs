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
    'Footprint overlaps the Business School (a07c23b2); the overlapping north-east part is cut out of this model so the Business School landmark/generic can occupy it. Height 20 m from the footprint record. 1960s elevations (ribbon windows between concrete spandrel bands over a glazed ground storey between concrete piers) and the 2017 Exhibition Road front (double-height display glazing with the flight simulator, aluminium-finned curtain wall above) are reconstructed from descriptions only; signage text and roof plant are approximate.',
  build(ctx) {
    const { THREE, kit } = ctx;
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
    const concT = plainTile(kit, 'cg:conc', '#cdc6b6', 0.61, { panels: 2 });
    const concP = plainTile(kit, 'cg:concplain', '#bdb6a6', 0.62);
    const concDk = kit.mat('#8c877d');
    const alu = kit.mat('#b9bec2', { roughness: 0.35, metalness: 0.6 });
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const frame = kit.mat('#d8d2c6', { roughness: 0.5 });
    const roofM = kit.roof('flat', 2);
    const Z1 = 4.4,
      FH = 3.12,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const curtain = painted(kit, 'cg:curtain', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2a3a45');
      const gr = c.createLinearGradient(0, 0, w, h);
      gr.addColorStop(0, 'rgba(170,200,220,0.4)');
      gr.addColorStop(1, 'rgba(160,190,210,0.08)');
      c.fillStyle = gr;
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#9aa1a6';
      c.fillRect(0, h * 0.9, w, h * 0.1);
      for (let i = 0; i < 4; i++) c.fillRect((i * w) / 4, 0, 3, h);
    });
    const display = painted(kit, 'cg:display', 1024, 256, (c, w, h) => {
      fillTile(c, w, h, '#33434e');
      // lit interior with the flight simulator capsule and a wing section on show
      c.fillStyle = 'rgba(255,245,220,0.35)';
      for (let i = 0; i < 12; i++) c.fillRect(30 + i * 84, h * 0.04, 46, 5);
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
      c.fillStyle = 'rgba(255,255,255,0.18)';
      c.fillRect(0, 0, w, h * 0.12);
    });
    const E = edges(ring);
    const isExh = (e) => Math.abs(e.a[0] - 1811.1) < 0.5; // Exhibition Road face
    const exh = E.find(isExh);
    // 1960s elevations: glazed ground storey between piers, ribbon windows above.
    for (const e of E) {
      if (isExh(e)) continue;
      const L = local(kit, batch, e.a, e.b);
      bayFacade(L, {
        z0: 0,
        floors: 1,
        fh: Z1,
        bay: 3.6,
        pier: 0.6,
        spandrel: 0.35,
        head: 0.75,
        inset: 0.4,
        wall: concP,
        glass,
        frame: kit.mat('#55595c', { metalness: 0.4, roughness: 0.4 }),
        mullions: 1,
        transom: 0.75,
      });
      bayFacade(L, {
        z0: Z1,
        floors: NF,
        fh: FH,
        bay: 1.2,
        ribbon: true,
        endPier: 0.5,
        spandrel: 1.0,
        head: 0.35,
        inset: 0.28,
        wall: concT,
        reveal: concP,
        glass,
        frame,
        mullions: 0,
        transom: 0.7,
      });
    }
    // Slab-edge bands with a dark shadow line beneath.
    for (let k = 0; k < NF; k++) {
      const z = Z1 + k * FH - 0.4;
      for (const e of E) {
        if (isExh(e) || e.len < 1) continue;
        const L = local(kit, batch, e.a, e.b);
        L.box(conc, e.len / 2, 0.14, z, e.len + 0.25, 0.28, 0.4);
        L.box(concDk, e.len / 2, 0.06, z - 0.06, e.len, 0.12, 0.06);
      }
    }
    // Exhibition Road: double-height display glazing, finned curtain wall, frame.
    const X = local(kit, batch, exh.a, exh.b);
    X.fN(display, 0.8, X.len - 0.8, 0, 7.6, -0.3);
    for (let u = 0.8; u <= X.len - 0.79; u += (X.len - 1.6) / 18)
      X.box(alu, u, -0.22, 0, 0.12, 0.16, 7.6);
    X.box(alu, X.len / 2, -0.22, 3.9, X.len - 1.6, 0.16, 0.12);
    X.fZ(alu, 0.8, X.len - 0.8, -0.3, 0, 7.6, false);
    X.fN(curtain, 0, X.len, 7.6, TOP, 0);
    for (let k = 0; k < 4; k++)
      X.box(alu, X.len / 2, 0.08, 7.6 + k * FH + FH - 0.15, X.len, 0.16, 0.15);
    for (let u = 1.5; u < X.len - 1; u += 1.5) X.box(alu, u, 0.3, 7.6, 0.12, 0.6, TOP - 7.6);
    for (const u of [0.4, X.len - 0.4]) X.box(alu, u, 0.5, 0, 0.8, 1.0, TOP + 0.9);
    X.box(alu, X.len / 2, 0.5, TOP, X.len, 1.0, 0.9);
    X.box(alu, X.len / 2, 0.4, 7.2, X.len, 0.8, 0.4);
    // Entrance canopy, doors, signage and steps.
    const cu0 = X.len * 0.45,
      cu1 = X.len * 0.75;
    X.box(alu, (cu0 + cu1) / 2, 1.6, 4.6, cu1 - cu0, 3.2, 0.4);
    for (const s of [-1, 1])
      X.box(
        kit.mat('#4b5154'),
        (cu0 + cu1) / 2 + s * ((cu1 - cu0) / 2 - 0.4),
        2.9,
        0,
        0.16,
        0.16,
        4.6,
      );
    for (const d of [-1.5, 0, 1.5])
      X.fN(
        kit.mat('#2a3138'),
        (cu0 + cu1) / 2 + d - 0.65,
        (cu0 + cu1) / 2 + d + 0.65,
        0,
        2.6,
        -0.28,
      );
    const sign = kit.paintedMaterial('cg:sign', 1024, 96, (c, w, h) => {
      c.fillStyle = '#0f2f57';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#ffffff';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.font = 'bold 48px sans-serif';
      c.fillText('City and Guilds Building', w / 2, h / 2);
    });
    {
      const [x, y] = X.P((cu0 + cu1) / 2, 3.22);
      const sg = new THREE.PlaneGeometry(cu1 - cu0 - 1, 0.7).rotateX(Math.PI / 2);
      batch.addGeometry(sign, sg, new THREE.Matrix4().makeRotationZ(X.ang).setPosition(x, y, 4.8));
    }
    steps(X, kit.mat('#c9c3b6'), (cu0 + cu1) / 2, 0, cu1 - cu0 - 1, 2, 0.13, 0.4);
    // Roof: membrane, parapet with coping, handrail, plant and wind-tunnel housings.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, concP, [ring], TOP, 0.9, 0.3);
    kit.cornice(batch, conc, ring, TOP + 0.9, { height: 0.12, projection: 0.06 });
    const louvre = painted(kit, 'cg:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#a9a8a2');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.4)';
        c.fillRect(0, y, w, 2);
      }
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(0, 0, 2, h);
    });
    roofClutter(kit, batch, louvre, ring, TOP, 0.71, 14, E[0].ang, 3);
    const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
    const rin = kit.offsetRing(ring, -1.1);
    for (let k = 0; k < rin.length; k++) {
      const p0 = rin[k],
        p1 = rin[(k + 1) % rin.length];
      if (Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 3)
        railing(kit, batch, rail, p0, p1, TOP, { height: 1.1, spacing: 1.5, bar: 0.05 });
    }
    const S = frameOf(E[0].a, E[0].b);
    const plant = fixCCW(kit, rectRing(S, 12, 40, -26, -8));
    prism(kit, batch, louvre, roofM, [plant], TOP, TOP + 4.2, { tw: 3, th: 4.2 });
    hband(kit, batch, concDk, plant, TOP + 4.2, 0.4, 0.25);
    const fan = new THREE.CylinderGeometry(0.7, 0.7, 0.35, 14).rotateX(Math.PI / 2);
    for (let k = 0; k < 4; k++) {
      const [x, y] = S.P(15 + k * 6.5, -17);
      kit.box(batch, kit.mat('#c4c8c9'), x, y, TOP + 4.6, 2.4, 2.4, 0.9, S.ang);
      batch.addGeometry(
        kit.mat('#3b4044'),
        fan,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 5.6),
      );
    }
    fan.dispose();
    // Wind-tunnel exhaust stack beside the plant room.
    {
      const [x, y] = S.P(44, -16);
      batch.addGeometry(
        kit.mat('steel'),
        new THREE.CylinderGeometry(0.9, 0.9, 6, 16).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(x, y, TOP + 3),
      );
      batch.addGeometry(
        kit.mat('dark_steel'),
        new THREE.CylinderGeometry(1.0, 1.0, 0.3, 16).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(x, y, TOP + 6),
      );
    }
    g.add(batch.toGroup('city_guilds'));
    g.add(
      ctx.placeAssets(
        'bollard',
        [-0.1, 0.0, 0.1].flatMap((f) => [[...X.P(cu0 - 2 + f * 10, 4).slice(0, 2), X.ang]]),
      ),
    );
    return g;
  },
};
