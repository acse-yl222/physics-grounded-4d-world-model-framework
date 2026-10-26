// Royal School of Mines (Sir Aston Webb, 1909-13, Grade II) and the Bessemer
// Building behind it, Imperial College South Kensington.
// RSM: long symmetrical Classical front to Prince Consort Road in Portland stone,
// three storeys over a rusticated ground floor, with a seven-bay centrepiece set
// forward and articulated by Roman Ionic pilasters; the wider central bay holds a
// three-storey semi-domed entrance niche (arched windows in its upper storey),
// above it a blind attic with sculptured groups; the entrance is flanked by the
// high pedestals and busts of the Wernher and Beit memorials (P. R. Montford,
// 1910). Balustraded parapet and hipped green slate roofs.
// Bessemer: 1960s laboratory block behind (Dalby Court side), refurbished by
// Sheppard Robson (2006) with a renewed facade and pink-glass entrance feature;
// plus the low glazed link structure at its west end.

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
  id: 'royal_school_of_mines',
  name: 'Royal School of Mines and Bessemer Building',
  claims: [
    '84298f4f-be03-46fc-af9c-bffe24858013', // Royal School of Mines
    'f3f6f1cb-79b1-45a7-b6dc-a7b702afc3c6', // Bessemer Building
    'eea65bdd-c0b4-443b-8cbe-5e17319dc64f', // Link Structure (west end of Bessemer)
  ],
  references: [
    {
      title: 'Royal School of Mines (Imperial College) - listed building (gohistoric)',
      url: 'https://gohistoric.com/places/528970-royal-school-mines-imperial-college-science-technology-london/listed',
      used_for:
        'Historic England list entry 1227162: Aston Webb 1909-13, Portland stone, 3 storeys + attic, centre 7 bays forward with Roman Ionic pilasters, semidomed niche, blind attic with sculptured groups, hipped green slate roof, Wernher and Beit busts on high pedestals',
    },
    {
      title: 'Royal School of Mines - Manchester History (listing text)',
      url: 'https://manchesterhistory.net/architecture/1920/minesschool.html',
      used_for: 'Portland stone cladding, memorial sculptures either side of the grand entrance',
    },
    {
      title: 'Wernher and Beit memorials - Victorian Web',
      url: 'https://victorianweb.org/victorian/sculpture/montford/7.html',
      used_for:
        'P. R. Montford 1910 memorials: busts plus four allegorical figures (a digging figure for mining and a woman for prosperity on the Wernher side; an armoured figure with a curved sword and one in animal skins on the Beit side); foundation stone on the Wernher plinth',
    },
    {
      title: 'London Remembers - RSM name panels',
      url: 'https://londonremembers.com/memorials/unwin-at-ic',
      used_for:
        'Beit bust right of the entrance, Wernher left; west wing named after Aston Webb, east after the Goldsmiths',
    },
    {
      title: 'Imperial College Bessemer Building (MIT DOME, Sheppard Robson)',
      url: 'https://dome.mit.edu/handle/1721.3/92658',
      used_for: '1960s building, 2006 entrance matched to renewed Bessemer facade with pink glass',
    },
    {
      title: 'Explore the new RSM and Bessemer - Imperial College',
      url: 'https://www.imperial.ac.uk/news/31814/explore-rsm-bessemer/',
      used_for: 'joint RSM/Bessemer refurbishment programme',
    },
  ],
  notes:
    'RSM storey heights raised above the footprint record (12.9 m) to Edwardian proportions (cornice 14.2 m, ridge ~19.5 m) per the listing (3 storeys + attic). The Prince Consort Road front, centre block and Exhibition Road return have real windows (rusticated ground floor with keystoned openings, architraved first-floor sashes with console hoods, plain second-floor architraves), plinth, string courses, modillion cornice and a balustrade with dies; courtyard elevations keep the painted bay tile. Bay count (30), niche size, the frieze lettering, the area railings and the attic sculpture groups are proportioned/abstracted, not surveyed. The Bessemer elevation pattern (pale spandrel bands, aluminium ribbon glazing) and pink-glass entrance zone are approximate (no photos available).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const rsm = byId['84298f4f-be03-46fc-af9c-bffe24858013'].polys[0][0];
    const bes = byId['f3f6f1cb-79b1-45a7-b6dc-a7b702afc3c6'].polys[0][0];
    const link = byId['eea65bdd-c0b4-443b-8cbe-5e17319dc64f'].polys[0][0];
    const stone = kit.mat('portland_stone');
    const stone2 = kit.mat('portland_stone', { side: THREE.DoubleSide });
    const bronze = kit.mat('bronze');
    const slate = kit.mat('#66756b', { roughness: 0.75 });
    const ZC = 14.2,
      ZP = 15.0;
    // ---------- RSM elevation tile: one bay, ground to frieze ----------
    const bay = painted(kit, 'rsm:bay', 128, 392, (c, w, h) => {
      const Y = (z) => h - (z / ZC) * h;
      fillTile(c, w, h, '#ded6c3');
      grain(c, w, h, 0.81, kit, 0.05);
      c.fillStyle = '#c9c0ab';
      c.fillRect(0, Y(0.6), w, Y(0) - Y(0.6));
      c.fillStyle = 'rgba(90,80,60,0.35)';
      for (let z = 0.6; z < 5.2; z += 0.55) c.fillRect(0, Y(z), w, 1.5); // rustication
      c.fillStyle = '#cfc6b1';
      c.fillRect(0, Y(5.6), w, Y(5.2) - Y(5.6)); // string course
      c.fillRect(0, Y(12.9), w, 2);
      const sash = (x0, z0, ww, z1, frame = true) => {
        const x = (x0 / 4.65) * w,
          wp = (ww / 4.65) * w;
        if (frame) {
          c.fillStyle = '#e8e2d2';
          c.fillRect(x - 4, Y(z1) - 4, wp + 8, Y(z0) - Y(z1) + 8);
        }
        c.fillStyle = '#2a3036';
        c.fillRect(x, Y(z1), wp, Y(z0) - Y(z1));
        c.fillStyle = '#efece4';
        c.fillRect(x + wp / 2 - 1, Y(z1), 2, Y(z0) - Y(z1));
        for (let k = 1; k < 4; k++) c.fillRect(x, Y(z0 + ((z1 - z0) * k) / 4), wp, 1.5);
      };
      sash(1.4, 1.6, 1.85, 4.2, false);
      c.fillStyle = '#e8e2d2';
      c.fillRect((2.1 / 4.65) * w, Y(4.6), (0.45 / 4.65) * w, Y(4.2) - Y(4.6)); // keystone
      sash(1.45, 6.2, 1.75, 9.2);
      c.fillStyle = '#d9d1bd';
      c.fillRect((1.2 / 4.65) * w, Y(9.75), (2.25 / 4.65) * w, Y(9.35) - Y(9.75)); // hood
      sash(1.5, 10.4, 1.65, 12.4);
    });
    const balus = painted(kit, 'rsm:balustrade', 128, 64, (c, w, h) => {
      fillTile(c, w, h, '#ddd5c2');
      c.fillStyle = 'rgba(70,65,55,0.55)';
      for (let i = 0; i < 6; i++) c.fillRect(8 + i * 20, h * 0.25, 10, h * 0.55);
      c.fillStyle = '#e6dfcd';
      c.fillRect(0, 0, w, h * 0.22);
    });
    const attic = painted(kit, 'rsm:attic', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#dcd4c1');
      grain(c, w, h, 0.83, kit, 0.05);
      c.strokeStyle = 'rgba(80,72,58,0.45)';
      c.lineWidth = 3;
      c.strokeRect(w * 0.1, h * 0.25, w * 0.8, h * 0.5);
      c.fillStyle = 'rgba(80,72,58,0.3)';
      c.fillRect(0, h * 0.12, w, 3);
      c.fillRect(0, h * 0.86, w, 3);
    });
    // ---------- RSM walls ----------
    const north = edges(rsm).find((e) => e.len > 120); // Prince Consort Road front
    const F = frameOf(north.a, north.b); // u: east -> west, n: north (outward)
    const L = F.len,
      C = L / 2,
      HW = 16.3,
      PR = 1.4,
      NB = 4; // centre block half-width, projection
    const seg = (m, u0, n0, u1, n1, z0, z1, tw, th, zb = 0) =>
      wallSeg(batch, m, F.P(u0, n0), F.P(u1, n1), z0, z1, tw, th, zb);
    // Main elevations (Prince Consort Road front, centre block, Exhibition Road
    // return) get real windows in plain rusticated / ashlar stone; the courtyard
    // elevations keep the painted bay tile.
    const rust = plainTile(kit, 'rsm:rust', '#d4ccb8', 0.86, { joints: 5 });
    const ashlar = plainTile(kit, 'rsm:ashlar', '#ded6c3', 0.87, { joints: 10 });
    const revealM = plainTile(kit, 'rsm:reveal', '#cfc7b3', 0.88);
    const dress = kit.mat('#e6dfcd');
    const sashGlass = kit.mat('#46596a', { roughness: 0.18, metalness: 0.15 });
    const sash = kit.mat('#efece4', { roughness: 0.5 });
    const eastE0 = edges(rsm).find((e) => Math.abs(e.a[0] - 1793.5) < 0.5);
    const classical = (a, b, u0, u1, bayW) => {
      const FL = local(kit, batch, a, b);
      const o = {
        u0,
        u1,
        bay: bayW,
        inset: 0.32,
        reveal: revealM,
        glass: sashGlass,
        frame: sash,
        mullions: 1,
        sill: dress,
        sillProj: 0.14,
      };
      // rusticated ground storey: segment-headed openings with keystones
      bayFacade(FL, {
        ...o,
        z0: 0,
        floors: 1,
        fh: 5.2,
        pier: bayW - 1.85,
        spandrel: 1.6,
        head: 1.0,
        wall: rust,
        transom: 0.62,
        surround: 0.02,
        surroundMat: dress,
        keystone: true,
      });
      FL.fN(dress, u0, u1, 5.2, 5.6, 0); // string course face (projecting band added below)
      // first floor (piano nobile): tall sashes with architraves and cornice hoods
      bayFacade(FL, {
        ...o,
        z0: 5.6,
        floors: 1,
        fh: 4.3,
        pier: bayW - 1.75,
        spandrel: 0.6,
        head: 0.7,
        wall: ashlar,
        transom: 0.55,
        surround: 0.18,
        surroundMat: dress,
      });
      // second floor: shorter sashes with plain architraves
      bayFacade(FL, {
        ...o,
        z0: 9.9,
        floors: 1,
        fh: 2.9,
        pier: bayW - 1.65,
        spandrel: 0.5,
        head: 0.4,
        wall: ashlar,
        transom: 0.5,
        surround: 0.15,
        surroundMat: dress,
      });
      FL.fN(ashlar, u0, u1, 12.8, ZC, 0); // frieze
      const span = u1 - u0,
        nb = Math.max(1, Math.round(span / bayW)),
        bw = span / nb;
      for (let i = 0; i < nb; i++) {
        const uc = u0 + (i + 0.5) * bw;
        // hood mould on consoles over the first-floor windows
        FL.box(dress, uc, 0.2, 9.38, 2.7, 0.4, 0.18);
        FL.box(dress, uc, 0.14, 9.2, 2.45, 0.28, 0.18);
        for (const s of [-1, 1]) FL.box(dress, uc + s * 1.25, 0.12, 8.75, 0.2, 0.24, 0.45);
        // apron panel under the first-floor sill
        FL.box(dress, uc, 0.03, 5.75, 1.6, 0.06, 0.35);
      }
      return FL;
    };
    for (const e of edges(rsm)) {
      if (e.k === north.k) continue;
      if (e.k === eastE0.k) {
        classical(e.a, e.b, 0, e.len, 4.65);
        continue;
      }
      wallSeg(batch, bay, e.a, e.b, 0, ZC, 4.65, ZC);
    }
    classical(north.a, north.b, 0, C - HW, 4.65);
    classical(north.a, north.b, C + HW, L, 4.65);
    // Centre block: side faces, front bays either side of the central bay.
    seg(rust, C - HW, 0, C - HW, PR, 0, 5.2, 1.4, 3);
    seg(rust, C + HW, PR, C + HW, 0, 0, 5.2, 1.4, 3);
    seg(ashlar, C - HW, 0, C - HW, PR, 5.2, ZC, 1.4, 3);
    seg(ashlar, C + HW, PR, C + HW, 0, 5.2, ZC, 1.4, 3);
    classical(F.P(C - HW, PR), F.P(C + HW, PR), 0, HW - NB, 4.1);
    classical(F.P(C - HW, PR), F.P(C + HW, PR), HW + NB, 2 * HW, 4.1);
    // Central bay with the arched mouth of the niche.
    const R = 3.4,
      ZS = ZC - R - 0.6; // springing of the semidome
    {
      const pts = [
        [-NB, 0],
        [-R, 0],
        [-R, ZS],
      ];
      for (let i = 1; i < 16; i++) {
        const a = Math.PI - (i * Math.PI) / 16;
        pts.push([R * Math.cos(a), ZS + R * Math.sin(a)]);
      }
      pts.push([R, ZS], [R, 0], [NB, 0], [NB, ZC], [-NB, ZC]);
      const tris = THREE.ShapeUtils.triangulateShape(
        pts.map(([x, y]) => new THREE.Vector2(x, y)),
        [],
      );
      const verts = pts.map(([s, z]) => F.P(C + s, PR, z));
      batch.add(
        stone2,
        verts,
        pts.map(([s, z]) => [s / 4, z / 4]),
        tris.flat(),
      );
    }
    // Niche: half cylinder with doors / square windows / arched upper windows, and semidome.
    const nicheM = painted(
      kit,
      'rsm:niche',
      512,
      512,
      (c, w, h) => {
        const Y = (z) => h - (z / ZS) * h;
        fillTile(c, w, h, '#d4ccb8');
        grain(c, w, h, 0.85, kit, 0.05);
        c.fillStyle = 'rgba(90,80,60,0.3)';
        for (let z = 0.6; z < 4.6; z += 0.55) c.fillRect(0, Y(z), w, 2);
        for (const f of [0.22, 0.5, 0.78]) {
          const x = f * w;
          c.fillStyle = '#e6dfcd';
          c.fillRect(x - 46, Y(4.4), 92, Y(0) - Y(4.4));
          c.fillStyle = '#3a2c22';
          c.fillRect(x - 38, Y(3.9), 76, Y(0) - Y(3.9)); // doors
          c.fillStyle = '#2a3036';
          c.fillRect(x - 26, Y(7.0), 52, Y(5.3) - Y(7.0)); // square windows
          c.beginPath(); // arched upper windows
          c.moveTo(x - 26, Y(7.9));
          c.lineTo(x - 26, Y(9.2));
          c.arc(x, Y(9.2), 26, Math.PI, 0);
          c.lineTo(x + 26, Y(7.9));
          c.closePath();
          c.fill();
          c.fillStyle = '#efece4';
          c.fillRect(x - 1, Y(9.9), 2, Y(7.9) - Y(9.9));
          c.fillRect(x - 26, Y(8.8), 52, 2);
        }
        c.fillStyle = '#e3dccb';
        c.fillRect(0, Y(4.9), w, 6);
        c.fillRect(0, Y(7.6), w, 5);
      },
      { side: THREE.DoubleSide },
    );
    {
      const N = 16,
        verts = [],
        uvs = [],
        idx = [];
      for (let i = 0; i <= N; i++) {
        const a = (i * Math.PI) / N;
        const u = C - R * Math.cos(a),
          n = PR - R * Math.sin(a);
        verts.push(F.P(u, n, 0), F.P(u, n, ZS));
        uvs.push([i / N, 0], [i / N, 1]);
        if (i < N) idx.push(2 * i, 2 * i + 2, 2 * i + 1, 2 * i + 1, 2 * i + 2, 2 * i + 3);
      }
      batch.add(nicheM, verts, uvs, idx);
      const dv = [],
        du = [],
        di = [],
        M = 8;
      for (let j = 0; j <= M; j++)
        for (let i = 0; i <= N; i++) {
          const a = (i * Math.PI) / N,
            e = (j * Math.PI) / 2 / M;
          dv.push(
            F.P(
              C - R * Math.cos(e) * Math.cos(a),
              PR - R * Math.cos(e) * Math.sin(a),
              ZS + R * Math.sin(e),
            ),
          );
          du.push([i / N, j / M]);
        }
      for (let j = 0; j < M; j++)
        for (let i = 0; i < N; i++) {
          const p = j * (N + 1) + i;
          di.push(p, p + 1, p + N + 1, p + 1, p + N + 2, p + N + 1);
        }
      batch.add(stone2, dv, du, di);
      // floor of the niche
      const fl = [F.P(C, PR, 0.05)];
      for (let i = 0; i <= N; i++) {
        const a = (i * Math.PI) / N;
        fl.push(F.P(C - R * Math.cos(a), PR - R * Math.sin(a), 0.05));
      }
      batch.add(
        stone2,
        fl,
        fl.map(() => [0, 0]),
        Array.from({ length: N }, (_, i) => [0, i + 1, i + 2]).flat(),
      );
    }
    // Plinth, string courses and architrave as bands on the main elevations only
    // (they must not cross the mouth of the niche).
    const bandRuns = [
      [north.a, north.b, 0, C - HW],
      [north.a, north.b, C + HW, L],
      [eastE0.a, eastE0.b, 0, eastE0.len],
      [F.P(C - HW, PR), F.P(C + HW, PR), 0, HW - R - 0.45],
      [F.P(C - HW, PR), F.P(C + HW, PR), HW + R + 0.45, 2 * HW],
      [F.P(C - HW, 0), F.P(C - HW, PR), 0, PR],
      [F.P(C + HW, PR), F.P(C + HW, 0), 0, PR],
    ];
    const bands = (z, h, proj, m) => {
      for (const [p0, p1, u0, u1] of bandRuns) {
        const BL = local(kit, batch, p0, p1);
        BL.box(m, (u0 + u1) / 2, proj / 2, z, u1 - u0 + proj * 2, proj, h);
      }
    };
    bands(0, 0.6, 0.12, kit.mat('#cfc6b1'));
    bands(5.2, 0.2, 0.1, dress);
    bands(5.4, 0.2, 0.2, dress);
    bands(9.82, 0.12, 0.06, dress);
    bands(12.8, 0.2, 0.08, dress);
    bands(13.0, 0.15, 0.13, dress);
    // Roman Ionic pilasters with bases, volute capitals and entablature breaks.
    const pil = [-HW + 0.6, -12.2, -8.1, -NB, NB, 8.1, 12.2, HW - 0.6];
    const volute = new THREE.CylinderGeometry(0.17, 0.17, 0.5, 10);
    for (const s of pil) {
      const PL = local(kit, batch, F.P(C + s - 1, PR), F.P(C + s + 1, PR));
      PL.box(stone, 1, 0.2, 5.6, 0.9, 0.4, 6.9);
      PL.box(kit.mat('#cfc6b1'), 1, 0.27, 5.6, 1.2, 0.54, 0.3);
      PL.box(dress, 1, 0.25, 5.9, 1.05, 0.5, 0.14);
      for (const k of [-0.27, 0, 0.27])
        PL.box(kit.mat('#cbc3ae'), 1 + k, 0.405, 6.2, 0.08, 0.02, 6.1); // fluting
      PL.box(dress, 1, 0.25, 12.35, 1.0, 0.5, 0.18);
      PL.box(dress, 1, 0.3, 12.53, 1.25, 0.6, 0.14);
      for (const d of [-0.52, 0.52]) {
        const [x, y] = PL.P(1 + d, 0.32);
        batch.addGeometry(
          dress,
          volute,
          new THREE.Matrix4().makeRotationZ(PL.ang).setPosition(x, y, 12.4),
        );
      }
      PL.box(dress, 1, 0.35, 12.67, 1.35, 0.7, 0.12); // abacus
    }
    volute.dispose();
    // Main cornice: architrave, frieze, modillions and a three-step projecting cornice.
    const cb = fixCCW(kit, rectRing(F, C - HW - 0.5, C + HW + 0.5, -0.5, PR + 0.65));
    const cbFace = fixCCW(kit, rectRing(F, C - HW, C + HW, -0.5, PR));
    for (const r of [rsm, cbFace])
      kit.cornice(batch, dress, r, ZC + 0.3, { height: ZP - ZC - 0.3, projection: 0.65, steps: 3 });
    kit.cornice(batch, dress, rsm, ZC, { height: 0.3, projection: 0.2 });
    kit.cap(batch, dress, [[cb]], ZP);
    {
      // modillions under the cornice on the front, the centre block and the east return
      const runs = [
        [north.a, north.b, 0, C - HW],
        [north.a, north.b, C + HW, L],
        [F.P(C - HW, PR), F.P(C + HW, PR), 0, 2 * HW],
        [eastE0.a, eastE0.b, 0, eastE0.len],
      ];
      for (const [p0, p1, u0, u1] of runs) {
        const ML = local(kit, batch, p0, p1);
        const n = Math.floor((u1 - u0) / 0.75);
        for (let i = 0; i < n; i++)
          ML.box(dress, u0 + ((i + 0.5) * (u1 - u0)) / n, 0.22, ZC + 0.08, 0.16, 0.42, 0.22);
      }
    }
    {
      // Balustraded parapet: real balusters with dies on the main elevations,
      // the painted balustrade on the courtyard sides.
      const r2 = kit.offsetRing(rsm, 0.2);
      const inner = kit.offsetRing(rsm, -0.15);
      const nE = r2.length;
      const isMain = (k) => k === north.k || k === eastE0.k;
      for (let k = 0; k < nE; k++) {
        const k1 = (k + 1) % nE;
        if (isMain(k)) continue;
        wallSeg(batch, balus, r2[k], r2[k1], ZP, ZP + 1.1, 2.4, 1.1, ZP);
        wallSeg(batch, stone, inner[k1], inner[k], ZP, ZP + 1.1, 3, 3);
        kit.cap(batch, dress, [[[r2[k], r2[k1], inner[k1], inner[k]]]], ZP + 1.1);
      }
      const bal = (p0, p1) => {
        const BL = local(kit, batch, p0, p1);
        kit.balustrade(batch, stone, [BL.P(0, -0.05), BL.P(BL.len, -0.05)], ZP, {
          height: 1.1,
          spacing: 0.3,
        });
        const n = Math.max(1, Math.round(BL.len / 4.65));
        for (let i = 0; i <= n; i++) {
          BL.box(stone, (i * BL.len) / n, -0.05, ZP, 0.55, 0.45, 1.15);
          BL.box(dress, (i * BL.len) / n, -0.05, ZP + 1.15, 0.65, 0.55, 0.08);
        }
      };
      const fr = local(kit, batch, r2[north.k], r2[(north.k + 1) % nE]);
      bal(fr.P(0, 0), fr.P(C - HW - 0.6, 0));
      bal(fr.P(C + HW + 0.6, 0), fr.P(fr.len, 0));
      bal(r2[eastE0.k], r2[(eastE0.k + 1) % nE]);
      // short balustrade returns at the ends of the centre-block cornice
      for (const [u0, u1] of [
        [C - HW - 0.5, C - HW + 0.4],
        [C + HW - 0.4, C + HW + 0.5],
      ])
        bal(F.P(u0, PR + 0.4), F.P(u1, PR + 0.4));
    }
    kit.cap(batch, kit.mat('lead'), [[kit.offsetRing(rsm, -0.1)]], ZP + 0.06);
    // Blind attic over the centrepiece with sculptured groups.
    const at = fixCCW(kit, rectRing(F, C - HW + 0.4, C + HW - 0.4, -6, PR - 0.1));
    wallsM(batch, attic, [at], ZP, ZP + 4.0, 8, 4.0, ZP);
    kit.cap(batch, stone, [[at]], ZP + 4.0);
    kit.cornice(batch, dress, at, ZP + 3.55, { height: 0.45, projection: 0.35, steps: 2 });
    kit.cornice(batch, kit.mat('#cfc6b1'), at, ZP, { height: 0.4, projection: 0.1 });
    {
      // pilaster strips on the attic over the order below, and a lettered panel
      for (const s of pil) {
        const [x, y] = F.P(C + s, PR + 0.05);
        kit.box(batch, dress, x, y, ZP + 0.4, 1.0, 0.3, 3.15, F.ang);
      }
      const name = kit.paintedMaterial('rsm:name', 1024, 96, (c, w, h) => {
        c.fillStyle = '#ddd5c2';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#4a4436';
        c.font = 'bold 60px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('ROYAL SCHOOL OF MINES', w / 2, h / 2 + 2);
      });
      // lettering in the frieze over the niche
      const [x, y] = F.P(C, PR + 0.02);
      const pg = new THREE.PlaneGeometry(2 * NB - 1.4, 0.6).rotateX(Math.PI / 2);
      batch.addGeometry(
        name,
        pg,
        new THREE.Matrix4().makeRotationZ(F.ang).setPosition(x, y, 13.65),
      );
    }
    const figure = (u, n, z, s) => {
      const [x, y] = F.P(u, n);
      kit.box(batch, stone, x, y, z, 2.4 * s, 1.4 * s, 0.6 * s, F.ang);
      const body = new THREE.CylinderGeometry(0.42 * s, 0.6 * s, 1.9 * s, 7).rotateX(Math.PI / 2);
      batch.addGeometry(
        stone,
        body,
        new THREE.Matrix4().makeTranslation(x, y, z + 0.6 * s + 0.95 * s),
      );
      const head = new THREE.SphereGeometry(0.3 * s, 7, 5);
      batch.addGeometry(
        stone,
        head,
        new THREE.Matrix4().makeTranslation(x, y, z + 0.6 * s + 2.15 * s),
      );
    };
    for (const s of [-1, 1]) {
      figure(C + s * 6.5, PR - 0.8, ZP + 4.0, 1.0);
      figure(C + s * 8.3, PR - 1.2, ZP + 4.0, 0.85);
      figure(C + s * 4.9, PR - 1.2, ZP + 4.0, 0.85);
    }
    // Hipped green slate roofs: front range and east (Goldsmiths') wing.
    kit.pitchedRoof(
      batch,
      slate,
      stone,
      fixCCW(kit, rectRing(F, 0.4, L - 0.4, -10.3, -0.4)),
      F.ang,
      ZP,
      4.4,
      'hipped',
      { overhang: 0 },
    );
    const eastE = edges(rsm).find((e) => Math.abs(e.a[0] - 1793.5) < 0.5);
    const EF = frameOf(eastE.a, eastE.b); // u north along Exhibition Road side, n east
    kit.pitchedRoof(
      batch,
      slate,
      stone,
      fixCCW(kit, rectRing(EF, 0.4, eastE.len - 0.4, -26.5, -0.4)),
      EF.ang,
      ZP,
      4.8,
      'hipped',
      { overhang: 0 },
    );
    // Chimney stacks along the ridge with cornice caps and pots; lead ridge rolls.
    const pot = new THREE.CylinderGeometry(0.15, 0.19, 0.6, 8).rotateX(Math.PI / 2);
    for (const u of [12, 40, L - 40, L - 12]) {
      const CL = local(kit, batch, F.P(u - 1, -5.3), F.P(u + 1, -5.3));
      CL.box(stone, 1, 0, ZP + 2.5, 1.0, 2.6, 3.4);
      CL.box(dress, 1, 0, ZP + 5.5, 1.25, 2.85, 0.25);
      CL.box(dress, 1, 0, ZP + 5.0, 1.1, 2.7, 0.12);
      for (const d of [-0.8, 0, 0.8]) {
        const [x, y] = CL.P(1, d);
        batch.addGeometry(
          kit.mat('#a0553a'),
          pot,
          new THREE.Matrix4().makeTranslation(x, y, ZP + 6.05),
        );
      }
    }
    pot.dispose();
    {
      const RL = local(kit, batch, F.P(10.3, -5.35), F.P(L - 10.3, -5.35));
      RL.box(kit.mat('lead'), RL.len / 2, 0, ZP + 4.35, RL.len, 0.22, 0.12);
      // cast-iron roof vents and a few rooflights on the slopes
      for (const f of [0.18, 0.33, 0.67, 0.82]) {
        RL.box(kit.mat('#3d4347'), RL.len * f, -1.8, ZP + 3.4, 0.5, 0.5, 0.9);
        const [x, y] = F.P(10.3 + RL.len * f + 4, -7.6);
        const tilt = Math.atan2(4.4, 4.95);
        const zr = ZP + 4.4 * (1 - 2.25 / 4.95) + 0.08;
        const M = new THREE.Matrix4()
          .makeRotationZ(F.ang)
          .multiply(new THREE.Matrix4().makeRotationX(-tilt));
        M.setPosition(x, y, zr);
        batch.addGeometry(
          kit.mat('#5d7484', { roughness: 0.2, metalness: 0.3 }),
          new THREE.BoxGeometry(1.4, 1.8, 0.12),
          M,
        );
      }
    }
    // Wernher (left) and Beit (right) memorials (P. R. Montford, 1910): busts on
    // high moulded pedestals, with four carved allegorical figures (mining and
    // prosperity; an armoured figure with a curved sword and one in skins).
    const carved = kit.mat('#d9d1bd');
    const person = (u, n, z, sc, facing, pose) => {
      const [x, y] = F.P(u, n);
      const M = (dx, dy, dz) =>
        new THREE.Matrix4()
          .makeRotationZ(F.ang + facing)
          .setPosition(x, y, z)
          .multiply(new THREE.Matrix4().makeTranslation(dx * sc, dy * sc, dz * sc));
      const cyl = (r0, r1, h) =>
        new THREE.CylinderGeometry(r0 * sc, r1 * sc, h * sc, 8).rotateX(Math.PI / 2);
      for (const lx of [-0.12, 0.12])
        batch.addGeometry(carved, cyl(0.09, 0.11, 0.85), M(lx, 0, 0.43));
      batch.addGeometry(
        carved,
        cyl(pose === 'robe' ? 0.32 : 0.2, pose === 'robe' ? 0.38 : 0.22, 0.85),
        M(0, 0, pose === 'robe' ? 0.43 : 0.92),
      );
      batch.addGeometry(carved, cyl(0.24, 0.2, 0.62), M(0, 0, 1.25));
      batch.addGeometry(carved, new THREE.SphereGeometry(0.13 * sc, 8, 6), M(0, 0, 1.7));
      const arm = (side, lift) => {
        const g2 = cyl(0.06, 0.07, 0.6);
        const R2 = new THREE.Matrix4().makeRotationY(side * lift);
        batch.addGeometry(carved, g2.applyMatrix4(R2), M(side * 0.3, 0, 1.28));
      };
      arm(-1, 0.25);
      arm(1, pose === 'pick' || pose === 'sword' ? 1.1 : 0.25);
      if (pose === 'pick')
        batch.addGeometry(
          kit.mat('#9a948a'),
          new THREE.BoxGeometry(0.05 * sc, 0.05 * sc, 1.1 * sc),
          M(0.62, 0, 1.55),
        );
      if (pose === 'sword')
        batch.addGeometry(
          kit.mat('#9a948a'),
          new THREE.BoxGeometry(0.04 * sc, 0.08 * sc, 0.9 * sc),
          M(0.62, 0, 1.75),
        );
    };
    for (const s of [-1, 1]) {
      const PL = local(kit, batch, F.P(C + s * 6.6 - 1, PR + 2.6), F.P(C + s * 6.6 + 1, PR + 2.6));
      // stepped base, die with panels, cornice cap
      PL.box(stone, 1, 0, 0, 3.4, 3.4, 0.35);
      PL.box(stone, 1, 0, 0.35, 3.0, 3.0, 0.45);
      PL.box(dress, 1, 0, 0.8, 2.25, 2.25, 0.3);
      PL.box(stone, 1, 0, 1.1, 1.9, 1.9, 3.7);
      for (const d of [-1, 1]) PL.box(kit.mat('#cfc6b1'), 1, d * 0.96, 1.6, 1.3, 0.04, 2.6); // sunk panels
      PL.box(dress, 1, 0, 4.8, 2.15, 2.15, 0.2);
      PL.box(dress, 1, 0, 5.0, 2.4, 2.4, 0.22);
      PL.box(kit.mat('#e9e3d4'), 1, 0, 5.22, 1.6, 1.6, 0.3);
      const [x, y] = PL.P(1, 0);
      // bronze bust: socle, shoulders and head
      batch.addGeometry(
        bronze,
        new THREE.CylinderGeometry(0.28, 0.4, 0.35, 10).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(x, y, 5.7),
      );
      batch.addGeometry(
        bronze,
        new THREE.SphereGeometry(0.62, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2)
          .rotateX(Math.PI / 2)
          .scale(1.2, 0.7, 0.9),
        new THREE.Matrix4().makeRotationZ(F.ang).setPosition(x, y, 5.86),
      );
      batch.addGeometry(
        bronze,
        new THREE.CylinderGeometry(0.16, 0.19, 0.25, 8).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(x, y, 6.5),
      );
      batch.addGeometry(
        bronze,
        new THREE.SphereGeometry(0.3, 12, 9).scale(0.85, 0.95, 1.12),
        new THREE.Matrix4().makeTranslation(x, y, 6.9),
      );
      // inscription panel
      const insc = kit.paintedMaterial(`rsm:insc${s}`, 256, 128, (c, w, h) => {
        c.fillStyle = '#d4ccb8';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#5a5244';
        c.font = 'bold 34px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(s < 0 ? 'WERNHER' : 'BEIT', w / 2, h * 0.45);
      });
      const [ix, iy] = PL.P(1, 0.97);
      batch.addGeometry(
        insc,
        new THREE.PlaneGeometry(1.4, 0.7).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeRotationZ(PL.ang).setPosition(ix, iy, 3.9),
      );
      // forward plinth with the two allegorical figures
      PL.box(stone, 1, 1.4, 0, 2.8, 1.2, 0.8);
      PL.box(dress, 1, 1.4, 0.8, 2.9, 1.3, 0.1);
      const poses = s < 0 ? ['pick', 'robe'] : ['sword', 'skins'];
      person(C + s * 6.6 - 0.65, PR + 4.0, 0.9, 1.0, 0, poses[0]);
      person(C + s * 6.6 + 0.65, PR + 4.0, 0.9, 0.95, 0, poses[1]);
    }
    // Entrance steps and a paved forecourt between the memorials.
    for (let k = 0; k < 3; k++) {
      const [x, y] = F.P(C, PR + 0.4 + 0.4 * (2 - k));
      kit.box(batch, stone, x, y, 0, 7.6 - k * 0.4, 0.8 + 0.8 * k, 0.16 * (k + 1), F.ang);
    }
    kit.cap(
      batch,
      kit.mat('#c9c2b3'),
      [[fixCCW(kit, rectRing(F, C - 10, C + 10, PR, PR + 6.5))]],
      0.03,
    );
    // Basement-area railings along the front (cast iron, finials), broken at the centre.
    const iron = kit.mat('#1f2224', { roughness: 0.5, metalness: 0.4 });
    for (const [u0, u1] of [
      [1, C - HW - 0.5],
      [C + HW + 0.5, L - 1],
    ])
      railing(kit, batch, iron, F.P(u0, 1.6), F.P(u1, 1.6), 0, {
        height: 1.15,
        spacing: 0.14,
        finials: true,
      });
    for (const u of [C - HW - 0.5, C + HW + 0.5])
      railing(kit, batch, iron, F.P(u, 1.6), F.P(u, 0.05), 0, {
        height: 1.15,
        spacing: 0.14,
        finials: true,
      });
    {
      const EL = local(kit, batch, eastE0.a, eastE0.b);
      railing(kit, batch, iron, EL.P(1, 1.6), EL.P(EL.len - 1, 1.6), 0, {
        height: 1.15,
        spacing: 0.14,
        finials: true,
      });
    }
    // ---------- Bessemer Building ----------
    const BT = 23.2,
      B1 = 4.6,
      BFH = (BT - B1) / 6;
    // Renewed facade: pale spandrel bands and dark ribbon glazing with aluminium
    // mullions; the north walls are against the RSM below its roof (~15 m).
    const besSp = plainTile(kit, 'bessemer:spandrel', '#d7d8d4', 0.29, { panels: 2 });
    const besR = kit.mat('#bfc1be');
    const besGl = kit.mat('#3c4c57', { roughness: 0.15, metalness: 0.25 });
    const besFr = kit.mat('#8e969b', { roughness: 0.4, metalness: 0.5 });
    for (const e of edges(bes)) {
      const BL = local(kit, batch, e.a, e.b);
      const againstRSM = e.a[1] > -760 && e.b[1] > -760 && Math.abs(Math.sin(e.ang)) < 0.5;
      const z0 = againstRSM ? 15.4 : B1;
      if (againstRSM) BL.fN(besSp, 0, e.len, 0, 15.4);
      else
        bayFacade(BL, {
          z0: 0,
          floors: 1,
          fh: B1,
          bay: 6,
          pier: 0.4,
          spandrel: 0.3,
          head: 0.65,
          inset: 0.3,
          wall: besSp,
          reveal: besR,
          glass: besGl,
          frame: besFr,
          mullions: 2,
          transom: 0.8,
        });
      const fl = Math.max(1, Math.round((BT - z0) / BFH));
      bayFacade(BL, {
        z0,
        floors: fl,
        fh: (BT - z0) / fl,
        bay: 1.5,
        ribbon: true,
        endPier: 0.4,
        spandrel: 0.95,
        head: 0.3,
        inset: 0.25,
        wall: besSp,
        reveal: besR,
        glass: besGl,
        frame: besFr,
        mullions: 1,
        transom: 0.75,
      });
    }
    for (let k = 1; k < 6; k++)
      kit.cornice(batch, kit.mat('#e4e5e1'), bes, B1 + k * BFH - 0.12, {
        height: 0.12,
        projection: 0.12,
      });
    kit.cap(batch, kit.roof('flat', 1), [[bes]], BT);
    parapet(kit, batch, kit.mat('#c8c9c4'), [bes], BT, 0.9, 0.3);
    const louvre = painted(kit, 'bessemer:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#b3b6b4');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.4)';
        c.fillRect(0, y, w, 2);
      }
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(0, 0, 2, h);
    });
    roofClutter(kit, batch, louvre, bes, BT, 0.29, 12, F.ang, 3);
    {
      const rail = kit.mat('#a3a9ad', { metalness: 0.5, roughness: 0.4 });
      const rin = kit.offsetRing(bes, -1.2);
      for (let k = 0; k < rin.length; k++) {
        const p0 = rin[k],
          p1 = rin[(k + 1) % rin.length];
        if (Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 3)
          railing(kit, batch, rail, p0, p1, BT, { height: 1.1, spacing: 1.5, bar: 0.05 });
      }
    }
    const fanG = new THREE.CylinderGeometry(0.55, 0.55, 0.25, 12).rotateX(Math.PI / 2);
    {
      const sb = edges(bes).find((e) => e.len > 90);
      const SB = frameOf(sb.a, sb.b);
      for (const [u0, u1, n0, n1, h] of [
        [8, 30, -30, -12, 3.6],
        [52, 70, -26, -10, 4.2],
        [80, 92, -22, -8, 3.0],
      ]) {
        const pr = fixCCW(kit, rectRing(SB, u0, u1, n0, n1));
        prism(kit, batch, louvre, kit.roof('flat', 0), [pr], BT, BT + h, {
          tw: 3,
          th: 3,
        });
        hband(kit, batch, kit.mat('#8d9093'), pr, BT + h, 0.35, 0.2);
        for (let k = 0; k < 3; k++) {
          const [x, y] = SB.P(u0 + 2.5 + k * 3.2, (n0 + n1) / 2);
          kit.box(batch, kit.mat('#c4c8c9'), x, y, BT + h + 0.35, 1.8, 1.8, 0.9, SB.ang);
          batch.addGeometry(
            kit.mat('#3b4044'),
            fanG,
            new THREE.Matrix4().makeTranslation(x, y, BT + h + 1.35),
          );
        }
        const [dx, dy] = SB.P(u0 - 0.5, (n0 + n1) / 2);
        kit.box(batch, kit.mat('#9ea3a4'), dx, dy, BT + 0.2, 1.0, 1.2, h - 0.8, SB.ang); // riser duct
      }
    }
    // Pink-glass entrance feature on the Dalby Court (south) face.
    const south = edges(bes).find((e) => e.len > 90);
    const S = frameOf(south.a, south.b); // u east, n south (outward)
    const pink = kit.mat('#d9a3b8', {
      roughness: 0.15,
      metalness: 0.2,
      transparent: true,
      opacity: 0.7,
    });
    const pinkDk = painted(
      kit,
      'bessemer:pinkentrance',
      256,
      128,
      (c, w, h) => {
        fillTile(c, w, h, '#8a5a6e');
        const gr = c.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, 'rgba(240,190,210,0.6)');
        gr.addColorStop(1, 'rgba(120,60,90,0.2)');
        c.fillStyle = gr;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d9d6d4';
        for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 3, 0, 6, h);
        c.fillRect(0, h * 0.3, w, 4);
      },
      { roughness: 0.2, metalness: 0.2 },
    );
    const eu0 = S.len * 0.42,
      eu1 = S.len * 0.6;
    for (let u = eu0; u <= eu1; u += 1.2) {
      const [x, y] = S.P(u, 0.45);
      kit.box(batch, pink, x, y, 0, 0.55, 0.9, B1 + 2 * BFH, S.ang + 0.5);
    }
    const ent = fixCCW(kit, rectRing(S, eu0 + 3, eu1 - 3, 0, 3.2));
    wallsM(batch, pinkDk, [ent], 0, 3.8, 3, 3.8);
    kit.cap(batch, kit.mat('#e4e5e1'), [[ent]], 3.8);
    hband(
      kit,
      batch,
      kit.mat('#e4e5e1'),
      fixCCW(kit, rectRing(S, eu0, eu1, 0, 1.2)),
      B1 + 2 * BFH,
      0.5,
      0,
    );
    // Link structure (glazed, single storey).
    for (const e of edges(link)) {
      const LL = local(kit, batch, e.a, e.b);
      bayFacade(LL, {
        z0: 0,
        floors: 1,
        fh: 4.0,
        bay: 1.5,
        ribbon: true,
        endPier: 0.15,
        spandrel: 0.1,
        head: 0.35,
        inset: 0.08,
        wall: besFr,
        glass: kit.mat('#6d8796', { roughness: 0.15, metalness: 0.3 }),
        frame: besFr,
        mullions: 1,
        transom: 0.7,
      });
    }
    kit.cap(batch, kit.mat('#9aa1a6'), [[link]], 4.0);
    g.add(batch.toGroup('rsm_bessemer'));
    return g;
  },
};
