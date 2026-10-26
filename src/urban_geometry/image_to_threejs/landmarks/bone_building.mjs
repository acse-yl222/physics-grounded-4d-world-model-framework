// Bone Building, Imperial College South Kensington (Chemical Engineering and
// Aeronautics), named after William A. Bone, professor of chemical technology.
// Stands beside the 1957 Roderic Hill Building with a courtyard behind it.
// Modelled as a four-storey red-brick laboratory block with Portland stone
// plinth, string courses, window surrounds and cornice, a parapet, chimney/flue
// stacks and roof-light hoods over the former laboratory floor.

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
  id: 'bone_building',
  name: 'Bone Building (Imperial College)',
  claims: ['83b620cc-5e12-4222-a5ea-fceb42477b2a'],
  references: [
    {
      title: 'Centenary memories (Oakley) - Imperial College',
      url: 'https://www.imperial.ac.uk/centenary/memories/oakley.shtml',
      used_for: 'Bone Building beside the new Roderic Hill Building, courtyard behind',
    },
    {
      title: 'South Kensington campus map (Imperial College)',
      url: 'https://www.sbg.bio.ic.ac.uk/files/SouthKensingtonCampus.pdf',
      used_for: 'Bone Building houses Aeronautics and Chemical Engineering',
    },
    {
      title: 'History - Department of Chemical Engineering, Imperial College',
      url: 'https://imperial.ac.uk/chemical-engineering/about/history',
      used_for:
        'department opened 1912 under Professor William Bone; new building in Prince Consort Road completed 1914',
    },
    {
      title: 'ACEX & Bone - BMJ Architects',
      url: 'https://www.bmjarchitects.co.uk/projects/acex-%26-bone',
      used_for: 'later phased refurbishment of the ACEX and Bone buildings (not modelled)',
    },
  ],
  notes:
    "Imperial gives 1914 for the completion of the department's new building in Prince Consort Road, taken here as the Bone Building; its elevation is not documented in the sources found. Red brick with Portland stone plinth, string course, window surrounds, modillion cornice and a stone doorcase is an assumption matched to the pre-war Imperial laboratory buildings; the later BMJ refurbishment (overcladding/render) is not represented. Height from the footprint record (13.6 m, 4 floors).",
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const b = byId['83b620cc-5e12-4222-a5ea-fceb42477b2a'];
    const ring = b.polys[0][0];
    const batch = new kit.MeshBatch();
    const stone = kit.mat('portland_stone');
    const stone2 = kit.mat('#e3dccb');
    const stoneT = plainTile(kit, 'bone:stone', '#d6cebb', 0.34, { joints: 10 });
    const stoneP = plainTile(kit, 'bone:stoneplain', '#d2cab7', 0.35);
    const brick = plainTile(kit, 'bone:brick', '#c27458', 0.33, { brick: true });
    const glass = kit.mat('#4a5f6d', { roughness: 0.2, metalness: 0.15 });
    const white = kit.mat('#ece8de', { roughness: 0.5 });
    const Z1 = 3.8,
      FH = (b.h - Z1) / 3,
      TOP = b.h;
    const E = edges(ring);
    const north = E.find((e) => Math.abs(e.a[0] - 1585.1) < 0.5); // exposed north face
    const ND = local(kit, batch, north.a, north.b);
    const doorU = 4.6; // doorway on the part of the north face clear of Roderic Hill
    for (const e of E) {
      const L = local(kit, batch, e.a, e.b);
      const segs =
        e.k === north.k
          ? [
              [0, doorU - 1.6],
              [doorU + 1.6, e.len],
            ]
          : [[0, e.len]];
      if (e.k === north.k) L.fN(stoneT, doorU - 1.6, doorU + 1.6, 0, Z1);
      if (e.k === north.k) L.fN(brick, doorU - 1.6, doorU + 1.6, Z1, TOP);
      for (const [u0, u1] of segs) {
        bayFacade(L, {
          u0,
          u1,
          z0: 0,
          floors: 1,
          fh: Z1,
          bay: 3.2,
          pier: 1.5,
          spandrel: 0.9,
          head: 0.7,
          inset: 0.2,
          wall: stoneT,
          reveal: stoneP,
          glass,
          frame: white,
          mullions: 1,
          transom: 0.5,
          sill: stone,
          sillProj: 0.1,
          keystone: true,
          surround: 0.01,
          surroundMat: stone,
        });
        bayFacade(L, {
          u0,
          u1,
          z0: Z1,
          floors: 3,
          fh: FH,
          bay: 3.2,
          pier: 1.65,
          spandrel: 0.75,
          head: 0.5,
          inset: 0.18,
          wall: brick,
          reveal: stoneP,
          glass,
          frame: white,
          mullions: 1,
          transom: 0.5,
          sill: stone,
          sillProj: 0.1,
          surround: 0.16,
          surroundMat: stone,
          keystone: true,
        });
      }
    }
    // Plinth, first-floor string course, sill band, modillion cornice.
    kit.cornice(batch, stone, ring, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(batch, stone, ring, Z1 - 0.3, { height: 0.4, projection: 0.15, steps: 2 });
    kit.cornice(batch, stone2, ring, Z1 + 2 * FH - 0.2, { height: 0.22, projection: 0.08 });
    kit.cornice(batch, stone2, ring, TOP - 0.55, { height: 0.55, projection: 0.45, steps: 3 });
    for (const e of E) {
      if (e.len < 3) continue;
      const L = local(kit, batch, e.a, e.b);
      const n = Math.floor(e.len / 0.6);
      for (let i = 0; i < n; i++)
        L.box(stone, ((i + 0.5) * e.len) / n, 0.18, TOP - 0.75, 0.14, 0.36, 0.2);
    }
    kit.cap(batch, kit.roof('flat', 1), [[ring]], TOP + 0.08);
    parapet(kit, batch, brick, [ring], TOP + 0.05, 1.0, 0.3);
    kit.cap(
      batch,
      stone,
      [[kit.offsetRing(ring, 0.05), kit.offsetRing(ring, -0.35).reverse()]],
      TOP + 1.07,
    );
    // Stone doorcase with pediment, steps and name panel on the north face.
    {
      const L = ND;
      L.box(stone, doorU - 1.25, 0.2, 0, 0.6, 0.4, 3.4);
      L.box(stone, doorU + 1.25, 0.2, 0, 0.6, 0.4, 3.4);
      L.box(stone, doorU, 0.25, 3.4, 3.4, 0.5, 0.35);
      const st2 = kit.mat('portland_stone', { side: THREE.DoubleSide });
      const z0 = 3.75,
        pu0 = doorU - 1.85,
        pu1 = doorU + 1.85;
      const tri = (n) => [L.P(pu0, n, z0), L.P(pu1, n, z0), L.P(doorU, n, z0 + 0.65)];
      const f = tri(0.5),
        bk = tri(0);
      batch.add(
        st2,
        f,
        [
          [0, 0],
          [1, 0],
          [0.5, 0.3],
        ],
        [0, 1, 2],
      );
      batch.quad(st2, f[0], f[2], bk[2], bk[0], [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.quad(st2, f[2], f[1], bk[1], bk[2], [0, 0], [1, 0], [1, 1], [0, 1]);
      L.fN(kit.mat('#3a2c22'), doorU - 0.85, doorU + 0.85, 0.45, 2.9, 0.02);
      L.fN(glass, doorU - 0.85, doorU + 0.85, 2.95, 3.35, 0.02);
      L.box(kit.mat('#2a2a2a'), doorU, 0.05, 1.5, 0.05, 0.08, 0.3);
      steps(L, stone, doorU, 0, 3.0, 3, 0.15, 0.32);
    }
    // Chimney / fume-flue stacks with pots and lab roof-light hoods.
    const long = E.slice().sort((a, b) => b.len - a.len)[0];
    const F = frameOf(long.a, long.b);
    const brickM = brick;
    const pot = new THREE.CylinderGeometry(0.16, 0.2, 0.7, 8).rotateX(Math.PI / 2);
    for (const u of [5, 15, 25, 34]) {
      if (u > long.len - 2) continue;
      const [x, y] = F.P(u, -2.2);
      kit.box(batch, brickM, x, y, TOP, 1.4, 2.2, 3.6, F.ang);
      kit.box(batch, stone, x, y, TOP + 3.6, 1.6, 2.4, 0.3, F.ang);
      kit.box(batch, stone, x, y, TOP + 2.8, 1.5, 2.3, 0.12, F.ang);
      for (const d of [-0.6, 0, 0.6]) {
        const [px, py] = F.P(u, -2.2 + d);
        batch.addGeometry(
          kit.mat('#a0553a'),
          pot,
          new THREE.Matrix4().makeTranslation(px, py, TOP + 4.25),
        );
      }
    }
    pot.dispose();
    for (const u of [9, 20]) {
      const [x, y] = F.P(u, -10);
      kit.box(batch, kit.mat('lead'), x, y, TOP, 6, 4, 1.2, F.ang);
      // pitched glazed lantern on the hood
      const L = local(kit, batch, F.P(u - 2.7, -8.3), F.P(u + 2.7, -8.3));
      const gl = kit.mat('#7d95a2', { roughness: 0.2, metalness: 0.3 });
      const a0 = L.P(0, 0, TOP + 1.2),
        a1 = L.P(L.len, 0, TOP + 1.2);
      const r0 = L.P(0, -1.7, TOP + 2.1),
        r1 = L.P(L.len, -1.7, TOP + 2.1);
      const b0 = L.P(0, -3.4, TOP + 1.2),
        b1 = L.P(L.len, -3.4, TOP + 1.2);
      batch.quad(gl, a0, a1, r1, r0, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.quad(gl, b1, b0, r0, r1, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.add(
        kit.mat('lead'),
        [a0, r0, b0],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        kit.mat('lead'),
        [a1, b1, r1],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      for (let k = 0; k <= 6; k++) {
        const uu = (k * L.len) / 6;
        const p = L.P(uu, -1.7);
        batch.addGeometry(
          kit.mat('dark_steel'),
          new THREE.BoxGeometry(0.06, 0.06, 0.95),
          new THREE.Matrix4().makeTranslation(p[0], p[1], TOP + 1.65),
        );
      }
      L.box(kit.mat('lead'), L.len / 2, -1.7, TOP + 2.08, L.len + 0.1, 0.18, 0.1);
    }
    g.add(batch.toGroup('bone'));
    return g;
  },
};
