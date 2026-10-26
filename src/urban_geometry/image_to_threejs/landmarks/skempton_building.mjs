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
    {
      title: 'Contact us - Civil and Environmental Engineering, Imperial College',
      url: 'https://www.imperial.ac.uk/engineering/departments/civil-engineering/about-us/contact/',
      used_for:
        'department housed in the Skempton Building on Imperial College Road (entrance side)',
    },
  ],
  notes:
    'Massing from the Overture footprint at 20 m (6 floors). Facade grid (slender precast mullions at 1.6 m over continuous slab bands, recessed dark ground storey on a column line), entrance canopy and signage, north-light rooflights and roof plant are reconstructed from the 1960s Norman & Dawbarn idiom; no photograph could be fetched.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const b = byId['c7e47974-cdef-43e7-b350-351d8ab671a1'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const conc = plainTile(kit, 'skempton:agg', '#cdc6b6', 0.52);
    const concB = plainTile(kit, 'skempton:band', '#d8d2c4', 0.53, { panels: 1 });
    const concDk = kit.mat('#8f8a80');
    const roofM = kit.roof('flat', 1);
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const frame = kit.mat('#5f6466', { roughness: 0.45, metalness: 0.4 });
    const Z1 = 4.2,
      FH = 3.16,
      NF = 5,
      TOP = Z1 + NF * FH; // 20.0
    const ground = painted(kit, 'skempton:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2f3a42');
      c.fillStyle = '#6e7377';
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 2, 0, 4, h);
      c.fillRect(0, h * 0.72, w, 4);
      c.fillStyle = '#5b5550';
      c.fillRect(0, h * 0.88, w, h * 0.12);
      c.fillStyle = 'rgba(255,240,210,0.3)';
      for (let i = 0; i < 4; i++) c.fillRect(16 + i * 64, h * 0.08, 30, 4);
      c.fillStyle = 'rgba(220,235,245,0.2)';
      c.fillRect(0, h * 0.72, w, h * 0.16);
    });
    const E = edges(ring);
    // Ground storey recessed behind the column line.
    const inner = kit.offsetRing(ring, -0.9);
    wallsM(batch, ground, [inner], 0, Z1, 4.8, Z1);
    kit.cap(batch, concDk, [[ring]], Z1, { down: true });
    kit.cap(batch, kit.mat('paving'), [[ring]], 0.03);
    fins(kit, batch, concDk, ring, 0, Z1, 6.4, 0.6, 0.6, { minLen: 6 });
    kit.cornice(batch, concB, ring, Z1 - 0.55, { height: 0.55, projection: 0.15 });
    // Upper storeys: precast grid of slender mullions between continuous slab bands.
    for (const e of E) {
      const L = local(kit, batch, e.a, e.b);
      bayFacade(L, {
        z0: Z1,
        floors: NF,
        fh: FH,
        bay: 1.6,
        pier: 0.24,
        spandrel: 0.95,
        head: 0.42,
        inset: 0.28,
        wall: conc,
        glass,
        frame,
        mullions: 0,
        transom: 0.7,
        sill: concDk,
        sillProj: 0.02,
      });
    }
    for (let k = 0; k < NF; k++)
      kit.cornice(batch, concB, ring, Z1 + k * FH - 0.04, { height: 0.42, projection: 0.22 });
    // Corner piers.
    for (const e of E)
      if (e.len > 5) {
        const L = local(kit, batch, e.a, e.b);
        L.box(conc, 0.3, 0.15, Z1, 0.6, 0.3, TOP - Z1);
      }
    // Roof: parapet and coping, handrail, north-light rooflights, plant, lift tower.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, conc, [ring], TOP, 0.9, 0.3);
    kit.cornice(batch, concB, ring, TOP + 0.9, { height: 0.12, projection: 0.06 });
    const north = E.find((e) => Math.abs(e.a[0] - 1737.3) < 0.5); // north face of the lab wing
    const F = frameOf(north.a, north.b); // u west, n north (outward)
    const glazing = kit.mat('#6d8796', { roughness: 0.2, metalness: 0.3 });
    for (let k = 0; k < 5; k++) {
      const u = 5 + k * 6.5;
      for (let j = 0; j < 2; j++) {
        const n0 = -6 - j * 10;
        const a = F.P(u, n0, TOP),
          b2 = F.P(u + 4.5, n0, TOP);
        const a2 = F.P(u, n0 - 3.5, TOP + 1.8),
          b3 = F.P(u + 4.5, n0 - 3.5, TOP + 1.8);
        batch.quad(glazing, a, b2, b3, a2, [0, 0], [1, 0], [1, 1], [0, 1]);
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
        // glazing bars on the north slope
        for (let m = 1; m < 5; m++) {
          const t = (m * 4.5) / 5;
          const p0 = F.P(u + t, n0 - 1.75, 0);
          const bar = new THREE.BoxGeometry(0.06, Math.hypot(3.5, 1.8), 0.06);
          const M = new THREE.Matrix4()
            .makeRotationZ(F.ang)
            .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(1.8, 3.5)));
          M.setPosition(p0[0], p0[1], TOP + 0.93);
          batch.addGeometry(frame, bar, M);
        }
        const [rx, ry] = F.P(u + 2.25, n0 - 3.5);
        kit.box(batch, kit.mat('lead'), rx, ry, TOP + 1.78, 4.7, 0.3, 0.1, F.ang);
      }
    }
    const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
    const rin = kit.offsetRing(ring, -1.0);
    for (let k = 0; k < rin.length; k++)
      railing(kit, batch, rail, rin[k], rin[(k + 1) % rin.length], TOP, {
        height: 1.1,
        spacing: 1.5,
        bar: 0.05,
      });
    const louvre = painted(kit, 'skempton:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#a7abab');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.4)';
        c.fillRect(0, y, w, 2);
      }
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(0, 0, 2, h);
    });
    roofClutter(kit, batch, louvre, ring, TOP, 0.37, 10, F.ang, 3);
    // Access walkway slabs, extract flues and a roof hatch.
    const walk = kit.mat('#bdb8ad');
    for (let u = 2; u < 34; u += 1.0) {
      const [x, y] = F.P(u, -28);
      kit.box(batch, walk, x, y, TOP, 0.9, 0.9, 0.06, F.ang);
    }
    const flue = new THREE.CylinderGeometry(0.22, 0.22, 2.4, 10).rotateX(Math.PI / 2);
    const cowl = new THREE.CylinderGeometry(0.4, 0.3, 0.3, 10).rotateX(Math.PI / 2);
    for (const [u, n] of [
      [3, -3.5],
      [3.8, -3.5],
      [38, -30],
      [38.8, -30],
      [24, -34],
    ]) {
      const [x, y] = F.P(u, n);
      batch.addGeometry(
        kit.mat('steel'),
        flue,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 1.2),
      );
      batch.addGeometry(
        kit.mat('steel'),
        cowl,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 2.5),
      );
    }
    flue.dispose();
    cowl.dispose();
    {
      const [x, y] = F.P(30, -24);
      kit.box(batch, kit.mat('#7d8285'), x, y, TOP, 1.2, 1.2, 0.5, F.ang);
    }
    const fan = new THREE.CylinderGeometry(0.6, 0.6, 0.3, 12).rotateX(Math.PI / 2);
    for (let k = 0; k < 4; k++) {
      const [x, y] = F.P(8 + k * 4, -32);
      kit.box(batch, kit.mat('#b9bdbe'), x, y, TOP, 2.8, 2.2, 1.4, F.ang);
      batch.addGeometry(
        kit.mat('#3b4044'),
        fan,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 1.55),
      );
    }
    fan.dispose();
    const west = E.find((e) => Math.abs(e.a[0] - 1667.7) < 0.5);
    const W = frameOf(west.a, west.b);
    const core = fixCCW(kit, rectRing(W, 12, 20, -9, -3));
    prism(kit, batch, conc, roofM, [core], TOP, TOP + 3.8);
    kit.cornice(batch, concB, core, TOP + 3.8, { height: 0.3, projection: 0.15 });
    {
      const [x, y] = W.P(16, -3.02);
      kit.box(batch, kit.mat('#4a4f52'), x, y, TOP, 1.0, 0.06, 2.1, W.ang);
    }
    // Entrance on Imperial College Road (south face): canopy, signage, steps.
    const south = E.find((e) => e.len > 70);
    const S = local(kit, batch, south.a, south.b);
    const uc = south.len * 0.55;
    S.box(kit.mat('#d9d6cf'), uc, 1.3, 3.5, 10, 3.6, 0.32);
    S.box(kit.mat('#3f4447'), uc, 3.08, 3.2, 10, 0.12, 0.3);
    for (const s of [-1, 1]) S.box(kit.mat('#3f4447'), uc + s * 4.7, 2.85, 0, 0.16, 0.16, 3.5);
    const sign = kit.paintedMaterial('skempton:sign', 1024, 96, (c, w, h) => {
      c.fillStyle = '#0f2f57';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#ffffff';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.font = 'bold 44px sans-serif';
      c.fillText('Skempton Building', w * 0.27, h / 2);
      c.font = '30px sans-serif';
      c.fillText('Civil and Environmental Engineering', w * 0.72, h / 2);
    });
    {
      const [x, y] = S.P(uc, 3.15);
      const sg = new THREE.PlaneGeometry(9, 0.9).rotateX(Math.PI / 2);
      batch.addGeometry(sign, sg, new THREE.Matrix4().makeRotationZ(S.ang).setPosition(x, y, 3.0));
    }
    steps(S, kit.mat('#c9c3b6'), uc, 0, 7, 2, 0.14, 0.4);
    // Doors in the recessed lobby.
    for (const d of [-1.6, 0, 1.6]) S.box(kit.mat('#2a3138'), uc + d, -0.86, 0, 1.4, 0.06, 2.6);
    g.add(batch.toGroup('skempton'));
    // Street furniture outside the entrance.
    g.add(
      ctx.placeAssets(
        'bicycle_stand',
        [0.2, 0.24, 0.28, 0.32].map((f) => [
          ...S.P(south.len * f, 2.2).slice(0, 2),
          S.ang + Math.PI / 2,
        ]),
      ),
    );
    g.add(
      ctx.placeAssets(
        'bollard',
        [-6, -4, 4, 6].map((d) => [...S.P(uc + d, 4.6).slice(0, 2), S.ang]),
      ),
    );
    return g;
  },
};
