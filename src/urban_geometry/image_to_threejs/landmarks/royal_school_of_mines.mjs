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
      used_for: 'P. R. Montford 1910 memorials with allegorical figures',
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
    'RSM storey heights raised above the footprint record (12.9 m) to Edwardian proportions (cornice 14.2 m, ridge ~19.5 m) per the listing (3 storeys + attic). Bay count (30) and niche size are proportioned, not surveyed; sculptured groups are abstracted. The Bessemer elevation pattern and pink-glass entrance zone are approximate (no photos available).',
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
    for (const e of edges(rsm)) {
      if (e === north || e.k === north.k) continue;
      wallSeg(batch, bay, e.a, e.b, 0, ZC, 4.65, ZC);
    }
    seg(bay, 0, 0, C - HW, 0, 0, ZC, 4.65, ZC);
    seg(bay, C + HW, 0, L, 0, 0, ZC, 4.65, ZC);
    // Centre block: side faces, front bays either side of the central bay.
    seg(bay, C - HW, 0, C - HW, PR, 0, ZC, 1.4, ZC);
    seg(bay, C + HW, PR, C + HW, 0, 0, ZC, 1.4, ZC);
    seg(bay, C - HW, PR, C - NB, PR, 0, ZC, 4.1, ZC);
    seg(bay, C + NB, PR, C + HW, PR, 0, ZC, 4.1, ZC);
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
    // Roman Ionic pilasters with capitals on the centrepiece.
    const pil = [-HW + 0.6, -12.2, -8.1, -NB, NB, 8.1, 12.2, HW - 0.6];
    for (const s of pil) {
      const [x, y] = F.P(C + s, PR + 0.2);
      kit.box(batch, stone, x, y, 5.6, 0.95, 0.4, 7.0, F.ang);
      kit.box(batch, kit.mat('#e9e3d4'), x, y, 12.6, 1.25, 0.6, 0.55, F.ang);
      kit.box(batch, kit.mat('#cfc6b1'), x, y, 5.2, 1.15, 0.55, 0.45, F.ang);
    }
    // Cornice + balustrade around the whole RSM, forward over the centre block.
    hband(kit, batch, kit.mat('#e6dfcd'), rsm, ZC, ZP - ZC, 0.6);
    const cb = fixCCW(kit, rectRing(F, C - HW - 0.5, C + HW + 0.5, -0.5, PR + 0.65));
    hband(kit, batch, kit.mat('#e6dfcd'), cb, ZC, ZP - ZC, 0);
    {
      const r2 = kit.offsetRing(rsm, 0.2);
      wallsM(batch, balus, [r2], ZP, ZP + 1.1, 2.4, 1.1, ZP);
      const inner = kit.offsetRing(rsm, -0.15);
      wallsM(batch, stone, [inner.slice().reverse()], ZP, ZP + 1.1, 3, 3);
      kit.cap(batch, kit.mat('#e6dfcd'), [[r2, inner.slice().reverse()]], ZP + 1.1);
    }
    kit.cap(batch, kit.mat('lead'), [[kit.offsetRing(rsm, -0.1)]], ZP + 0.06);
    // Blind attic over the centrepiece with sculptured groups.
    const at = fixCCW(kit, rectRing(F, C - HW + 0.4, C + HW - 0.4, -6, PR - 0.1));
    wallsM(batch, attic, [at], ZP, ZP + 4.0, 8, 4.0, ZP);
    kit.cap(batch, stone, [[at]], ZP + 4.0);
    hband(kit, batch, kit.mat('#e6dfcd'), at, ZP + 3.6, 0.45, 0.35);
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
    // Chimney stacks along the ridge.
    for (const u of [12, 40, L - 40, L - 12]) {
      const [x, y] = F.P(u, -5.3);
      kit.box(batch, stone, x, y, ZP + 2.5, 1.0, 2.6, 3.4, F.ang);
    }
    // Wernher (left) and Beit (right) memorials: high pedestals with busts and figures.
    for (const s of [-1, 1]) {
      const [x, y] = F.P(C + s * 6.6, PR + 2.6);
      kit.box(batch, stone, x, y, 0, 3.0, 3.0, 0.8, F.ang);
      kit.box(batch, stone, x, y, 0.8, 1.9, 1.9, 4.4, F.ang);
      kit.box(batch, kit.mat('#e9e3d4'), x, y, 5.2, 2.3, 2.3, 0.4, F.ang);
      const sh = new THREE.BoxGeometry(1.5, 0.8, 0.9);
      batch.addGeometry(
        bronze,
        sh,
        new THREE.Matrix4().makeRotationZ(F.ang).setPosition(x, y, 6.05),
      );
      batch.addGeometry(
        bronze,
        new THREE.SphereGeometry(0.48, 10, 8),
        new THREE.Matrix4().makeTranslation(x, y, 6.95),
      );
      for (const t of [-0.7, 0.7]) {
        const [fx, fy] = F.P(C + s * 6.6 + t, PR + 4.0);
        batch.addGeometry(
          bronze,
          new THREE.CylinderGeometry(0.32, 0.45, 1.5, 7).rotateX(Math.PI / 2),
          new THREE.Matrix4().makeTranslation(fx, fy, 1.55),
        );
        batch.addGeometry(
          bronze,
          new THREE.SphereGeometry(0.24, 7, 5),
          new THREE.Matrix4().makeTranslation(fx, fy, 2.5),
        );
      }
      const [px, py] = F.P(C + s * 6.6, PR + 4.0);
      kit.box(batch, stone, px, py, 0, 2.4, 1.0, 0.8, F.ang);
    }
    // Entrance steps.
    for (let k = 0; k < 3; k++) {
      const [x, y] = F.P(C, PR + 0.4 + 0.4 * (2 - k));
      kit.box(batch, stone, x, y, 0, 7.6 - k * 0.4, 0.8 + 0.8 * k, 0.16 * (k + 1), F.ang);
    }
    // ---------- Bessemer Building ----------
    const BT = 23.2,
      B1 = 4.6,
      BFH = (BT - B1) / 6;
    const besWall = painted(kit, 'bessemer:wall', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#d7d8d4');
      c.fillStyle = 'rgba(0,0,0,0.12)';
      for (let i = 0; i < 4; i++) c.fillRect((i * w) / 4, 0, 2, h);
      c.fillStyle = '#2d3b46';
      c.fillRect(0, h * 0.3, w, h * 0.5);
      c.fillStyle = '#8e969b';
      for (let i = 0; i < 8; i++) c.fillRect((i * w) / 8, h * 0.3, 3, h * 0.5);
      c.fillStyle = 'rgba(190,210,225,0.22)';
      c.fillRect(0, h * 0.3, w, h * 0.18);
    });
    const besGround = painted(kit, 'bessemer:ground', 256, 128, (c, w, h) => {
      fillTile(c, w, h, '#26323a');
      c.fillStyle = '#c9cac6';
      c.fillRect(0, 0, w, h * 0.14);
      c.fillStyle = '#7d868b';
      for (let i = 0; i <= 4; i++) c.fillRect((i * w) / 4 - 2, 0, 4, h);
      c.fillStyle = 'rgba(200,220,235,0.18)';
      c.fillRect(0, h * 0.14, w, h * 0.25);
    });
    wallsM(batch, besGround, [bes], 0, B1, 6, B1);
    wallsM(batch, besWall, [bes], B1, BT, 6, BFH, B1);
    for (let k = 1; k < 6; k++)
      hband(kit, batch, kit.mat('#e4e5e1'), bes, B1 + k * BFH - 0.3, 0.3, 0.15);
    kit.cap(batch, kit.roof('flat', 1), [[bes]], BT);
    parapet(kit, batch, kit.mat('#c8c9c4'), [bes], BT, 0.9, 0.3);
    roofClutter(kit, batch, kit.mat('aluminium'), bes, BT, 0.29, 12, F.ang, 3);
    {
      const sb = edges(bes).find((e) => e.len > 90);
      const SB = frameOf(sb.a, sb.b);
      for (const [u0, u1, n0, n1, h] of [
        [8, 30, -30, -12, 3.6],
        [52, 70, -26, -10, 4.2],
        [80, 92, -22, -8, 3.0],
      ]) {
        const pr = fixCCW(kit, rectRing(SB, u0, u1, n0, n1));
        prism(kit, batch, kit.mat('#b7b9b6'), kit.roof('flat', 0), [pr], BT, BT + h, {
          tw: 3,
          th: 3,
        });
        hband(kit, batch, kit.mat('#8d9093'), pr, BT + h, 0.35, 0.2);
        for (let k = 0; k < 3; k++) {
          const [x, y] = SB.P(u0 + 2.5 + k * 3.2, (n0 + n1) / 2);
          kit.box(batch, kit.mat('dark_steel'), x, y, BT + h + 0.35, 1.6, 1.6, 0.9, SB.ang);
        }
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
    wallsM(batch, kit.mat('glass'), [link], 0, 4.0, 3, 4);
    kit.cap(batch, kit.mat('#9aa1a6'), [[link]], 4.0);
    g.add(batch.toGroup('rsm_bessemer'));
    return g;
  },
};
