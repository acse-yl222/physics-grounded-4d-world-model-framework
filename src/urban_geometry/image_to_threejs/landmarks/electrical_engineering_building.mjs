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
      title: 'Imperial College of Science, Technology and Medicine - AIM25 identity statement',
      url: 'https://aim25.com/cats/3/1082.htm',
      used_for:
        'South Kensington site largely rebuilt 1950s-mid 1970s under the 1957 Jubilee Expansion Scheme',
    },
    {
      title: 'Survey of London vol. 38, plate 76',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-76',
      used_for: "1960-9 Imperial College buildings by Norman and Dawbarn behind the Queen's Tower",
    },
  ],
  notes:
    'No photographs could be downloaded; elevation rhythm (ribbon windows between precast spandrel bands, blank ends with a stair-window strip) is reconstructed from the 1960s Imperial idiom. Height from the footprint record (45.6 m, 14 floors). The north end abuts the Bessemer Building up to its 23 m roof, so that end is blind below it. Ground-floor reception, signage, roof plant, masts and handrails are approximate.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const b = byId['031912fe-8683-49ce-8793-860351f0b479'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const conc = plainTile(kit, 'eee:conc', '#c4bdb1', 0.41, { panels: 2 });
    const concPlain = plainTile(kit, 'eee:concplain', '#bab3a7', 0.42);
    const concDark = kit.mat('#8d877e');
    const nose = kit.mat('#d3cdc2');
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const frame = kit.mat('#55595c', { roughness: 0.4, metalness: 0.5 });
    const roofM = kit.roof('flat', 1);
    const FH = 3.15,
      Z1 = 4.5,
      NF = 13,
      TOP = Z1 + NF * FH; // 45.45 m
    const BES = 23.2; // Bessemer roof against the north end
    const E = edges(ring);
    const isLong = (e) => e.len > 40;
    const lobby = painted(kit, 'eee:lobby', 512, 128, (c, w, h) => {
      fillTile(c, w, h, '#2b3a44');
      c.fillStyle = '#c9d3d8';
      c.fillRect(0, h * 0.84, w, h * 0.16);
      c.fillStyle = 'rgba(255,240,210,0.35)';
      for (let i = 0; i < 6; i++) c.fillRect(20 + i * 84, h * 0.06, 40, 6);
      c.fillStyle = '#7c8a92';
      for (let i = 0; i <= 8; i++) c.fillRect((i * w) / 8 - 3, 0, 6, h);
      c.fillRect(0, h * 0.22, w, 4);
      c.fillStyle = 'rgba(220,235,245,0.25)';
      c.fillRect(0, 0, w, h * 0.22);
    });
    // ---- Ground floor: recessed glazed reception behind a line of pilotis.
    const inner = kit.offsetRing(ring, -1.4);
    for (const e of edges(inner)) wallSeg(batch, lobby, e.a, e.b, 0, Z1, 6, Z1);
    kit.cap(batch, concDark, [[ring]], Z1, { down: true });
    kit.cap(batch, kit.mat('paving'), [[ring]], 0.03);
    const pil = new THREE.CylinderGeometry(0.38, 0.38, Z1, 12).rotateX(Math.PI / 2);
    for (const e of E) {
      const n = Math.max(1, Math.round(e.len / 6.5));
      for (let i = 0; i < n; i++) {
        const t = ((i + 0.5) * e.len) / n;
        const x = e.a[0] + e.ux * t - e.nx * 0.55,
          y = e.a[1] + e.uy * t - e.ny * 0.55;
        batch.addGeometry(concDark, pil, new THREE.Matrix4().makeTranslation(x, y, Z1 / 2));
      }
    }
    pil.dispose();
    // Fascia at first-floor level.
    kit.cornice(batch, nose, ring, Z1 - 0.6, { height: 0.6, projection: 0.12 });
    // ---- Tower faces.
    for (const e of E) {
      const L = local(kit, batch, e.a, e.b);
      if (isLong(e)) {
        bayFacade(L, {
          z0: Z1,
          floors: NF,
          fh: FH,
          bay: 3.75,
          ribbon: true,
          endPier: 0.9,
          spandrel: 1.05,
          head: 0.3,
          inset: 0.3,
          wall: conc,
          reveal: concPlain,
          glass,
          frame,
          mullions: 2,
          transom: 0.62,
        });
        // Corner piers.
        for (const u of [0.45, e.len - 0.45]) L.box(conc, u, 0.12, Z1, 0.9, 0.24, TOP - Z1);
      } else {
        const north = e.a[1] > -805;
        const z0 = north ? BES : Z1;
        if (north) L.fN(concPlain, 0, e.len, Z1, BES);
        const nf = Math.round((TOP - z0) / FH);
        // Blank end wall with a central stair-window strip.
        bayFacade(L, {
          z0,
          floors: nf,
          fh: (TOP - z0) / nf,
          bay: e.len,
          pier: e.len - 1.8,
          spandrel: 0.5,
          head: 0.35,
          inset: 0.25,
          wall: concPlain,
          glass,
          frame,
          mullions: 0,
          transom: 0.5,
        });
        L.box(conc, e.len / 2 - 1.35, 0.15, z0, 0.5, 0.3, TOP - z0);
        L.box(conc, e.len / 2 + 1.35, 0.15, z0, 0.5, 0.3, TOP - z0);
      }
    }
    // Slab-edge noses at every floor on the long faces.
    for (let k = 1; k < NF; k++) {
      const z = Z1 + k * FH - 0.14;
      for (const e of E.filter(isLong)) {
        const L = local(kit, batch, e.a, e.b);
        L.box(nose, e.len / 2, 0.09, z, e.len - 1.8, 0.18, 0.14);
      }
    }
    // ---- Roof: parapet and coping, handrail, set-back plant storey, lift rooms, masts.
    kit.cap(batch, roofM, [[ring]], TOP);
    parapet(kit, batch, concPlain, [ring], TOP, 1.1, 0.3);
    kit.cornice(batch, nose, ring, TOP + 1.1, { height: 0.12, projection: 0.08 });
    const rail = kit.mat('#9aa1a6', { metalness: 0.5, roughness: 0.4 });
    const rin = kit.offsetRing(ring, -1.2);
    for (let k = 0; k < rin.length; k++)
      railing(kit, batch, rail, rin[k], rin[(k + 1) % rin.length], TOP, {
        height: 1.1,
        spacing: 1.6,
        bar: 0.05,
      });
    const F = frameOf(E[0].a, E[0].b); // south edge, u east, n south
    const Lw = E[1].len;
    const louvre = painted(kit, 'eee:louvre', 128, 128, (c, w, h) => {
      fillTile(c, w, h, '#9fa3a3');
      for (let y = 0; y < h; y += 6) {
        c.fillStyle = 'rgba(40,45,50,0.45)';
        c.fillRect(0, y, w, 2);
      }
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(0, 0, 2, h);
    });
    const plant = fixCCW(kit, rectRing(F, 3, E[0].len - 3, -Lw + 12, -14));
    prism(kit, batch, louvre, roofM, [plant], TOP, TOP + 3.6, { tw: 3, th: 3.6 });
    kit.cornice(batch, concDark, plant, TOP + 3.6, { height: 0.4, projection: 0.3 });
    const lift = fixCCW(kit, rectRing(F, 6, 13, -12, -6));
    prism(kit, batch, concPlain, roofM, [lift], TOP, TOP + 5.5, { tw: 4, th: 6.3 });
    kit.cornice(batch, nose, lift, TOP + 5.5, { height: 0.25, projection: 0.15 });
    {
      const L = local(kit, batch, F.P(6, -6), F.P(13, -6));
      L.box(kit.mat('#4a4f52'), 3.5, 0.03, TOP + 0.05, 1.0, 0.08, 2.1); // door
      L.box(louvre, 1.2, 0.03, TOP + 3, 1.2, 0.08, 1.2);
    }
    const steel = kit.mat('dark_steel');
    const masts = [F.P(4, -5, 0), F.P(E[0].len - 4, -Lw + 6, 0), F.P(E[0].len / 2, -Lw / 2, 0)];
    masts.forEach(([x, y], i) => {
      const h = i === 2 ? 12 : 8;
      const z0 = i === 2 ? TOP + 3.6 : TOP;
      const geo = new THREE.CylinderGeometry(0.1, 0.16, h, 8).rotateX(Math.PI / 2);
      batch.addGeometry(steel, geo, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      kit.box(batch, steel, x, y, z0, 0.8, 0.8, 0.3, F.ang);
      for (let k = 1; k <= 3; k++) {
        const d = new THREE.BoxGeometry(1.6, 0.06, 0.06);
        batch.addGeometry(
          steel,
          d,
          new THREE.Matrix4()
            .makeRotationZ(F.ang + k)
            .setPosition(x, y, z0 + h * (0.45 + k * 0.15)),
        );
        // panel antennas
        const pa = new THREE.BoxGeometry(0.3, 0.12, 1.2);
        batch.addGeometry(
          kit.mat('#e6e7e3'),
          pa,
          new THREE.Matrix4()
            .makeRotationZ(F.ang + k * 2.1)
            .setPosition(
              x + Math.cos(F.ang + k * 2.1) * 0.35,
              y + Math.sin(F.ang + k * 2.1) * 0.35,
              z0 + h * 0.6,
            ),
        );
      }
      const dish = new THREE.SphereGeometry(0.5, 10, 4, 0, Math.PI * 2, 0, Math.PI / 3);
      batch.addGeometry(
        kit.mat('#e6e7e3'),
        dish,
        new THREE.Matrix4()
          .makeRotationZ(F.ang)
          .multiply(new THREE.Matrix4().makeRotationY(Math.PI / 2))
          .setPosition(x, y, z0 + h * 0.8),
      );
    });
    // Cooling units with fan housings on the plant roof.
    const fan = new THREE.CylinderGeometry(0.7, 0.7, 0.35, 14).rotateX(Math.PI / 2);
    for (let k = 0; k < 4; k++) {
      const [x, y] = F.P(4.5 + k * 3.2, -Lw / 2 + 4, 0);
      kit.box(batch, kit.mat('aluminium'), x, y, TOP + 3.6, 2.6, 2.6, 1.3, F.ang);
      batch.addGeometry(
        kit.mat('#3b4044'),
        fan,
        new THREE.Matrix4().makeTranslation(x, y, TOP + 3.6 + 1.4),
      );
    }
    fan.dispose();
    // Duct runs across the main roof.
    for (const nn of [-9, -Lw + 9]) {
      const L = local(kit, batch, F.P(2.5, nn), F.P(E[0].len - 2.5, nn));
      L.box(kit.mat('#b0b4b4'), L.len / 2, 0, TOP + 0.3, L.len, 0.9, 0.7);
      for (let u = 1; u < L.len; u += 3) L.box(kit.mat('#6b6f70'), u, 0, TOP, 0.2, 1.0, 0.3);
    }
    // ---- Entrance on the east (Dalby Court) face: canopy, signage, steps.
    const east = E.find(isLong);
    {
      const L = local(kit, batch, east.a, east.b);
      const uc = east.len * 0.45;
      L.box(kit.mat('#d8dadb'), uc, 1.2, 3.6, 9, 3.8, 0.3);
      L.box(kit.mat('#4b5154'), uc, 3.0, 3.25, 9, 0.12, 0.35);
      for (const s of [-1, 1]) L.box(kit.mat('#4b5154'), uc + s * 4.2, 2.8, 0, 0.15, 0.15, 3.6);
      const sign = kit.paintedMaterial('eee:sign', 512, 64, (c, w, h) => {
        c.fillStyle = '#0f2f57';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#ffffff';
        c.font = 'bold 30px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('Electrical and Electronic Engineering', w / 2, h / 2);
      });
      const [x, y] = L.P(uc, 3.07);
      const sg = new THREE.PlaneGeometry(8, 1).rotateX(Math.PI / 2);
      batch.addGeometry(sign, sg, new THREE.Matrix4().makeRotationZ(L.ang).setPosition(x, y, 3.42));
      L.box(kit.mat('#e1ddd3'), uc, 1.6, 0, 9.6, 3.2, 0.12);
    }
    g.add(batch.toGroup('eee'));
    // Bicycle stands and bollards outside the entrance.
    {
      const L = local(kit, batch, east.a, east.b);
      const ang = L.ang;
      const pts = [0.25, 0.32, 0.38].map((f) => [...L.P(east.len * f, 3.5).slice(0, 2), ang]);
      g.add(ctx.placeAssets('bicycle_stand', pts));
      const bl = [0.6, 0.65, 0.7].map((f) => [...L.P(east.len * f, 3.2).slice(0, 2), ang]);
      g.add(ctx.placeAssets('bollard', bl));
    }
    return g;
  },
};
