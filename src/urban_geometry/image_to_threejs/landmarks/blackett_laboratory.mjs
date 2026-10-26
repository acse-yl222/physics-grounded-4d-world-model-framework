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
    {
      title: 'Historical facts and figures - Imperial College centenary',
      url: 'https://www.imperial.ac.uk/centenary/historical_facts_and_figures.shtml',
      used_for:
        'the Prince Consort Road fascia of the Blackett Laboratory shows the state of physics knowledge in the 1960s',
    },
  ],
  notes:
    'Main block kept at the footprint height (20 m, 6 floors) plus a set-back glazed top storey for the level-8 common room (~23.6 m). The stem south face abuts the Huxley Building and is left blind. Cladding material and grid rhythm (stone-faced frame, piers every 3.6 m, recessed two-light windows) are not confirmed by the sources found; the physics fascia over the Prince Consort Road entrance is recorded but its content is unknown, so it is drawn as a frieze of standard equations and diagrams.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const ring = byId['fc97c25d-2316-42d9-8db4-9cd9ad109b99'].polys[0][0];
    const batch = new kit.MeshBatch();
    const stone = kit.mat('#d8d1bf');
    const stoneT = plainTile(kit, 'blackett:stone', '#e2dac6', 0.91, { joints: 6 });
    const stoneR = plainTile(kit, 'blackett:reveal', '#cbc4b2', 0.92);
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const frame = kit.mat('#e4e0d6', { roughness: 0.5 });
    const dframe = kit.mat('#3d4347', { roughness: 0.45, metalness: 0.5 });
    const Z1 = 4.5,
      FH = 3.1,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const E = edges(ring);
    const blind = (e) => Math.abs(e.a[1] + 810.3) < 0.5; // stem end against Huxley
    for (const e of E) {
      const L = local(kit, batch, e.a, e.b);
      if (blind(e)) {
        L.fN(stoneT, 0, e.len, 0, TOP);
        continue;
      }
      // Dark glazed ground storey between stone piers.
      bayFacade(L, {
        z0: 0,
        floors: 1,
        fh: Z1,
        bay: 3.6,
        pier: 0.7,
        spandrel: 0.35,
        head: 0.7,
        inset: 0.35,
        wall: stoneT,
        reveal: stoneR,
        glass: kit.mat('#3e505c', { roughness: 0.18, metalness: 0.15 }),
        frame: dframe,
        mullions: 1,
        transom: 0.74,
      });
      // Upper floors: recessed two-light windows in the stone grid.
      bayFacade(L, {
        z0: Z1,
        floors: NF,
        fh: FH,
        bay: 3.6,
        pier: 0.55,
        spandrel: 0.85,
        head: 0.45,
        inset: 0.3,
        wall: stoneT,
        reveal: stoneR,
        glass,
        frame,
        mullions: 1,
        transom: 0.72,
        sill: stone,
        sillProj: 0.06,
      });
    }
    // Projecting frame: floor bands and piers every 3.6 m.
    for (let k = 0; k < NF; k++) hband(kit, batch, stone, ring, Z1 + k * FH - 0.3, 0.3, 0.3);
    fins(kit, batch, stone, ring, Z1 - 0.3, TOP, 3.6, 0.32, 0.4, { minLen: 6, skip: blind });
    kit.cornice(batch, stone, ring, 0, { height: 0.45, projection: 0.12 }); // plinth
    kit.cap(batch, kit.roof('flat', 0), [[ring]], TOP);
    parapet(kit, batch, stone, [ring], TOP, 1.0, 0.35);
    kit.cornice(batch, kit.mat('#e2dccd'), ring, TOP + 1.0, { height: 0.14, projection: 0.1 });
    // Set-back glazed top storey (common room) over the Prince Consort Road range.
    const front = E.find((e) => Math.abs(e.a[0] - 1505.5) < 0.5);
    const F = frameOf(front.a, front.b); // u west along Prince Consort Road, n north
    const cr = fixCCW(kit, rectRing(F, 4, front.len - 4, -15, -2.5));
    for (const e of edges(cr)) {
      const L = local(kit, batch, e.a, e.b);
      bayFacade(L, {
        z0: TOP,
        floors: 1,
        fh: 3.6,
        bay: 1.8,
        ribbon: true,
        endPier: 0.3,
        spandrel: 0.5,
        head: 0.45,
        inset: 0.15,
        wall: kit.mat('#c7c9c6'),
        glass: kit.mat('#4a6170', { roughness: 0.12, metalness: 0.3 }),
        frame: dframe,
        mullions: 1,
      });
    }
    kit.cap(batch, kit.roof('flat', 1), [[cr]], TOP + 4.0);
    kit.cornice(batch, kit.mat('#c7c9c6'), cr, TOP + 3.6, { height: 0.45, projection: 0.6 });
    parapet(kit, batch, kit.mat('#c7c9c6'), [kit.offsetRing(cr, 0.6)], TOP + 4.05, 0.35, 0.25);
    {
      // plant on the common-room roof: louvred units with fans, duct, flues
      const crL = local(kit, batch, F.P(4, -2.5), F.P(front.len - 4, -2.5));
      const fan = new THREE.CylinderGeometry(0.6, 0.6, 0.3, 12).rotateX(Math.PI / 2);
      for (let k = 0; k < 4; k++) {
        const u = 6 + k * ((crL.len - 12) / 3);
        crL.box(kit.mat('#b4b8b8'), u, -7, TOP + 4.05, 2.6, 2.4, 1.3);
        const [x, y] = crL.P(u, -7);
        batch.addGeometry(
          kit.mat('#3b4044'),
          fan,
          new THREE.Matrix4().makeTranslation(x, y, TOP + 5.5),
        );
      }
      fan.dispose();
      crL.box(kit.mat('#9ea3a4'), crL.len / 2, -10.5, TOP + 4.05, crL.len - 8, 0.8, 0.6);
    }
    // Roof terrace handrail around the common room.
    const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
    const tr = kit.offsetRing(cr, 1.2);
    for (let k = 0; k < tr.length; k++)
      railing(kit, batch, rail, tr[k], tr[(k + 1) % tr.length], TOP, {
        height: 1.05,
        spacing: 0.12,
        bar: 0.02,
      });
    roofClutter(kit, batch, kit.mat('aluminium'), ring, TOP, 0.93, 6, F.ang, 3);
    {
      // lift motor room and flue on the stem
      const stem = E.find((e) => Math.abs(e.a[0] - 1468.6) < 0.5);
      const SF = frameOf(stem.a, stem.b);
      const lm = fixCCW(kit, rectRing(SF, 8, 15, -10, -3));
      prism(kit, batch, stoneT, kit.roof('flat', 1), [lm], TOP, TOP + 3.2);
      kit.cornice(batch, stone, lm, TOP + 3.2, { height: 0.3, projection: 0.15 });
      const fl = new THREE.CylinderGeometry(0.3, 0.3, 4, 10).rotateX(Math.PI / 2);
      const [fx, fy] = SF.P(22, -8);
      batch.addGeometry(kit.mat('steel'), fl, new THREE.Matrix4().makeTranslation(fx, fy, TOP + 2));
    }
    // Entrance on Prince Consort Road: canopy, physics fascia, doors, steps, name.
    const PL = local(kit, batch, front.a, front.b);
    const u0 = front.len * 0.35,
      u1 = front.len * 0.55;
    const can = fixCCW(kit, rectRing(F, u0, u1, 0, 2.6));
    prism(kit, batch, stone, stone, [can], 3.6, 4.1, { bottom: true });
    const fascia = kit.paintedMaterial('blackett:fascia', 1024, 128, (c, w, h) => {
      c.fillStyle = '#1f2a33';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#e7e2d2';
      c.textBaseline = 'middle';
      c.font = 'italic 30px serif';
      const eq = [
        'E = mc²',
        '∇·E = ρ/ε₀',
        'F = q(E + v×B)',
        'λ = h/p',
        'ΔxΔp ≥ ħ/2',
        'S = k log W',
      ];
      eq.forEach((t, i) => c.fillText(t, 20 + i * 168, h * 0.32));
      c.strokeStyle = '#e7e2d2';
      c.lineWidth = 2;
      for (let i = 0; i < 6; i++) {
        const x = 70 + i * 168;
        c.beginPath();
        c.arc(x, h * 0.75, 16, 0, Math.PI * 2);
        c.stroke();
        c.beginPath();
        c.ellipse(x, h * 0.75, 30, 9, i * 0.6, 0, Math.PI * 2);
        c.stroke();
      }
      c.fillRect(0, 2, w, 2);
      c.fillRect(0, h - 4, w, 2);
    });
    {
      const [x, y] = PL.P((u0 + u1) / 2, 0.36);
      const pg = new THREE.PlaneGeometry(u1 - u0 + 4, 1.0).rotateX(Math.PI / 2);
      batch.addGeometry(
        fascia,
        pg,
        new THREE.Matrix4().makeRotationZ(PL.ang).setPosition(x, y, Z1 - 0.62),
      );
    }
    const name = kit.paintedMaterial('blackett:name', 512, 64, (c, w, h) => {
      c.fillStyle = '#d8d1bf';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#2c2c2c';
      c.font = 'bold 34px serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('BLACKETT LABORATORY', w / 2, h / 2);
    });
    {
      const [x, y] = PL.P((u0 + u1) / 2, 2.62);
      const pg = new THREE.PlaneGeometry(u1 - u0 - 0.6, 0.48).rotateX(Math.PI / 2);
      batch.addGeometry(
        name,
        pg,
        new THREE.Matrix4().makeRotationZ(PL.ang).setPosition(x, y, 3.85),
      );
    }
    for (const d of [-1.5, 0, 1.5])
      PL.box(kit.mat('#2a3138'), (u0 + u1) / 2 + d, 0.02, 0.45, 1.3, 0.08, 2.5);
    steps(PL, stone, (u0 + u1) / 2, 0, u1 - u0, 3, 0.15, 0.35);
    g.add(batch.toGroup('blackett'));
    g.add(
      ctx.placeAssets(
        'bollard',
        [-1, 1].map((s) => [
          ...PL.P((u0 + u1) / 2 + s * ((u1 - u0) / 2 + 1), 2.4).slice(0, 2),
          PL.ang,
        ]),
      ),
    );
    return g;
  },
};
