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
    "Massing, light wells and the domed rooftop part (32-36 m) come from the footprint record; the dome is drawn as an observatory-style dome with a shutter slit on a ribbed drum. Facade rhythm (dark ribbon windows between heavy exposed-aggregate spandrels, close-set concrete fins on the Queen's Gate front, recessed ground storey on a column line), colours, entrance and roof plant are reconstructions without photographic confirmation. The north face against the Blackett Laboratory is blind below its 20 m roof.",
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const b = byId['5add8849-9cf4-47d8-8c51-468c40d01959'];
    const poly = b.polys[0];
    const ring = poly[0];
    const batch = new kit.MeshBatch();
    const conc = kit.mat('#a8a092', { roughness: 0.95 });
    const agg = plainTile(kit, 'huxley:agg', '#a69e90', 0.71, { panels: 2 });
    const aggPlain = plainTile(kit, 'huxley:aggplain', '#9e968a', 0.72);
    const concDk = kit.mat('#6f6a62');
    const glass = kit.mat('#435763', { roughness: 0.2, metalness: 0.15 });
    const frame = kit.mat('#4b4f50', { roughness: 0.45, metalness: 0.4 });
    const Z1 = 4.2,
      NF = 7,
      FH = (b.h - Z1) / NF,
      TOP = b.h;
    const ground = painted(kit, 'huxley:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#2b3339');
      c.fillStyle = '#857e72';
      c.fillRect(0, 0, w, h * 0.18);
      for (let i = 0; i <= 3; i++) c.fillRect((i * w) / 3 - 5, 0, 10, h);
      c.fillStyle = 'rgba(255,240,210,0.3)';
      for (let i = 0; i < 3; i++) c.fillRect(25 + i * 85, h * 0.22, 34, 4);
      c.fillStyle = 'rgba(210,225,235,0.18)';
      c.fillRect(0, h * 0.18, w, h * 0.25);
    });
    const E = edges(ring);
    const BL = 20.0; // Blackett roof against the north face
    const againstBlackett = (e) =>
      Math.abs(e.a[1] + 807.7) < 0.3 && Math.abs(e.a[0] - 1492.5) < 0.3;
    // Recessed ground storey with column line.
    const inner = kit.offsetRing(ring, -1.0);
    wallsM(batch, ground, [inner], 0, Z1, 7.5, Z1);
    kit.cap(batch, concDk, [[ring]], Z1, { down: true });
    kit.cap(batch, kit.mat('paving'), [[ring]], 0.03);
    const col = new THREE.BoxGeometry(0.7, 0.7, Z1);
    for (const e of E) {
      if (e.len < 8) continue;
      const n = Math.max(1, Math.round(e.len / 7.5));
      for (let i = 1; i < n; i++) {
        const t = (i * e.len) / n;
        batch.addGeometry(
          concDk,
          col,
          new THREE.Matrix4()
            .makeRotationZ(e.ang)
            .setPosition(e.a[0] + e.ux * t - e.nx * 0.35, e.a[1] + e.uy * t - e.ny * 0.35, Z1 / 2),
        );
      }
    }
    col.dispose();
    // Upper storeys: outer faces with ribbon windows between heavy spandrels.
    for (const e of E) {
      const L = local(kit, batch, e.a, e.b);
      const z0 = againstBlackett(e) ? BL : Z1;
      if (z0 > Z1) L.fN(aggPlain, 0, e.len, Z1, z0);
      const fl = Math.round((TOP - z0) / FH);
      bayFacade(L, {
        z0,
        floors: fl,
        fh: (TOP - z0) / fl,
        bay: 2.5,
        ribbon: true,
        endPier: 0.5,
        spandrel: 1.25,
        head: 0.35,
        inset: 0.35,
        wall: agg,
        reveal: aggPlain,
        glass,
        frame,
        mullions: 1,
        transom: 0.8,
      });
    }
    // Light wells: punched windows.
    for (const hole of poly.slice(1))
      for (const e of edges(hole)) {
        const L = local(kit, batch, e.a, e.b);
        L.fN(aggPlain, 0, e.len, 0, Z1);
        bayFacade(L, {
          z0: Z1,
          floors: NF,
          fh: FH,
          bay: 2.4,
          pier: 0.8,
          spandrel: 0.95,
          head: 0.45,
          inset: 0.2,
          wall: aggPlain,
          glass,
          frame,
          mullions: 0,
          transom: 0.7,
        });
      }
    for (let k = 0; k < NF; k++)
      kit.cornice(batch, conc, ring, Z1 + k * FH - 0.5, { height: 0.5, projection: 0.35 });
    // Queen's Gate front: close-set vertical concrete fins.
    const qg = E.find((e) => Math.abs(e.a[0] - 1448.2) < 0.5);
    fins(kit, batch, conc, ring, Z1 - 0.5, TOP, 2.5, 0.55, 0.3, {
      minLen: 50,
      skip: (e) => e.k !== qg.k,
    });
    // Roof: cap with holes, parapets with coping, plant, handrail.
    kit.cap(batch, kit.roof('flat', 2), [poly], TOP);
    parapet(kit, batch, conc, poly, TOP, 1.1, 0.35);
    kit.cornice(batch, kit.mat('#b8b1a4'), ring, TOP + 1.1, { height: 0.15, projection: 0.12 });
    const F = frameOf(qg.a, qg.b);
    const louvre = painted(kit, 'huxley:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#9c9f9e');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.4)';
        c.fillRect(0, y, w, 2);
      }
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(0, 0, 2, h);
    });
    roofClutter(kit, batch, louvre, ring, TOP, 0.75, 14, F.ang, 3, poly.slice(1));
    const plant = fixCCW(kit, rectRing(F, 16, 30, -50, -38));
    prism(kit, batch, louvre, kit.roof('flat', 1), [plant], TOP, TOP + 3.4, { tw: 3, th: 3.4 });
    kit.cornice(batch, concDk, plant, TOP + 3.4, { height: 0.35, projection: 0.2 });
    const fan = new THREE.CylinderGeometry(0.75, 0.75, 0.35, 14).rotateX(Math.PI / 2);
    for (let k = 0; k < 3; k++) {
      const [x, y] = F.P(18.5 + k * 4.5, -44);
      batch.addGeometry(
        kit.mat('#3b4044'),
        fan,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 3.6),
      );
    }
    fan.dispose();
    const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
    const rin = kit.offsetRing(ring, -1.2);
    for (let k = 0; k < rin.length; k++)
      railing(kit, batch, rail, rin[k], rin[(k + 1) % rin.length], TOP, {
        height: 1.1,
        spacing: 1.6,
        bar: 0.05,
      });
    // Domed rooftop structure (part 375b4f29: 32-36 m) on a ribbed drum.
    const part = b.parts?.[0];
    if (part) {
      const pr = part.polys[0][0];
      const cx = pr.reduce((s, p) => s + p[0], 0) / pr.length,
        cy = pr.reduce((s, p) => s + p[1], 0) / pr.length;
      const rad = Math.max(...pr.map((p) => Math.hypot(p[0] - cx, p[1] - cy))) * 0.95;
      const zD = part.minh ?? 32;
      const dh = part.h - zD;
      const drumM = plainTile(kit, 'huxley:drum', '#b9b3a6', 0.74, { panels: 1 });
      const drum = new THREE.CylinderGeometry(rad, rad, zD - TOP, 28, 1, true).rotateX(Math.PI / 2);
      batch.addGeometry(drumM, drum, new THREE.Matrix4().makeTranslation(cx, cy, (TOP + zD) / 2));
      const rib = new THREE.BoxGeometry(0.25, 0.3, zD - TOP);
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2;
        batch.addGeometry(
          conc,
          rib,
          new THREE.Matrix4()
            .makeRotationZ(a)
            .setPosition(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad, (TOP + zD) / 2),
        );
      }
      rib.dispose();
      // door in the drum
      kit.box(batch, kit.mat('#3a3f42'), cx + rad + 0.02, cy, TOP, 0.1, 1.0, 2.1, 0);
      const ringG = new THREE.CylinderGeometry(rad + 0.35, rad + 0.35, 0.4, 28).rotateX(
        Math.PI / 2,
      );
      batch.addGeometry(conc, ringG, new THREE.Matrix4().makeTranslation(cx, cy, zD - 0.2));
      const prof = [];
      for (let i = 0; i <= 10; i++) {
        const t = (i / 10) * (Math.PI / 2);
        prof.push([rad * Math.cos(t) + 0.001, dh * Math.sin(t)]);
      }
      const dome = kit.lathe(kit.mat('#e9ebea', { roughness: 0.4, metalness: 0.3 }), prof, {
        x: cx,
        y: cy,
        z: zD,
        segments: 32,
      });
      g.add(dome);
      // Shutter slit and its rails over the crown.
      for (let i = 0; i < 8; i++) {
        const t0 = (i / 8) * (Math.PI / 2) * 0.95;
        const t1 = ((i + 1) / 8) * (Math.PI / 2) * 0.95;
        const x0 = rad * Math.cos(t0),
          z0 = dh * Math.sin(t0);
        const x1 = rad * Math.cos(t1),
          z1 = dh * Math.sin(t1);
        const len = Math.hypot(x1 - x0, z1 - z0);
        const sl = new THREE.BoxGeometry(len, 0.9, 0.12);
        const M = new THREE.Matrix4()
          .makeTranslation(cx + ((x0 + x1) / 2) * 1.01, cy, zD + ((z0 + z1) / 2) * 1.01)
          .multiply(new THREE.Matrix4().makeRotationY(-Math.atan2(z1 - z0, x1 - x0)));
        batch.addGeometry(kit.mat('#30363a'), sl, M);
        sl.dispose();
      }
      // Handrail around the dome terrace.
      const dr = [];
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2;
        dr.push([cx + Math.cos(a) * (rad + 1.2), cy + Math.sin(a) * (rad + 1.2)]);
      }
      for (let k = 0; k < 16; k++)
        railing(kit, batch, rail, dr[k], dr[(k + 1) % 16], TOP, {
          height: 1.0,
          spacing: 0.6,
          bar: 0.03,
        });
    }
    // Entrance on Queen's Gate: canopy, name, steps, doors.
    const Q = local(kit, batch, qg.a, qg.b);
    const uc = qg.len * 0.5;
    Q.box(kit.mat('#bdb6a8'), uc, 1.4, 3.6, 8, 3.8, 0.35);
    for (const s of [-1, 1]) Q.box(concDk, uc + s * 3.7, 3.0, 0, 0.3, 0.3, 3.6);
    const sign = kit.paintedMaterial('huxley:sign', 1024, 96, (c, w, h) => {
      c.fillStyle = '#0f2f57';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#ffffff';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.font = 'bold 46px sans-serif';
      c.fillText('Huxley Building', w * 0.3, h / 2);
      c.font = '34px sans-serif';
      c.fillText("180 Queen's Gate", w * 0.75, h / 2);
    });
    {
      const [x, y] = Q.P(uc, 3.32);
      const sg = new THREE.PlaneGeometry(7.6, 0.6).rotateX(Math.PI / 2);
      batch.addGeometry(sign, sg, new THREE.Matrix4().makeRotationZ(Q.ang).setPosition(x, y, 3.65));
    }
    for (const d of [-1.5, 0, 1.5]) Q.box(kit.mat('#2a3138'), uc + d, -0.96, 0, 1.3, 0.06, 2.6);
    steps(Q, kit.mat('#b9b2a4'), uc, 0, 7, 2, 0.14, 0.4);
    g.add(batch.toGroup('huxley'));
    g.add(
      ctx.placeAssets(
        'bicycle_stand',
        [0.2, 0.23, 0.26, 0.29, 0.32].map((f) => [
          ...Q.P(qg.len * f, 2.0).slice(0, 2),
          Q.ang + Math.PI / 2,
        ]),
      ),
    );
    return g;
  },
};
