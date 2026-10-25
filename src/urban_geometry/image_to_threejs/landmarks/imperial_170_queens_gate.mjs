// 170 Queen's Gate (R. Norman Shaw, 1888-9), the Imperial College Rector's
// residence on the corner of Queen's Gate and Imperial College Road. Wren-revival
// red brick house with stone dressings: white small-paned sashes under gauged
// brick heads with aprons and louvred shutters, a hipped tiled roof to the eaves
// with a white modillion cornice, a central curved pedimented dormer with a
// Serlian window flanked by segmental-pedimented dormers, and tall brick stacks.
// ---- local helpers (self-contained; duplicated per module by design) ----
function ccw(ring) {
  let a = 0;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a >= 0 ? ring : ring.slice().reverse();
}
function ringEdges(ring) {
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
      tx: dx / len,
      ty: dy / len,
      nx: dy / len,
      ny: -dx / len,
      ang: Math.atan2(dy, dx),
    });
  }
  return out;
}
// One wall quad a->b (outward normal on the right of a->b) with kit.walls-style UVs.
function wallQuad(batch, m, a, b, z0, z1, { bay = 3.6, storey = 3.2, uvBase = 0, color } = {}) {
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const n = Math.round(len / bay);
  const u1 = n >= 1 ? n / 4 : 0.03;
  const v0 = (z0 - uvBase) / (2 * storey),
    v1 = (z1 - uvBase) / (2 * storey);
  batch.quad(
    m,
    [a[0], a[1], z0],
    [b[0], b[1], z0],
    [b[0], b[1], z1],
    [a[0], a[1], z1],
    [0, v0],
    [u1, v0],
    [u1, v1],
    [0, v1],
    color,
  );
}
// Walls of a ring where pick(edge) returns { m, bay, storey, uvBase } or null to skip.
function edgeWalls(batch, ring, z0, z1, pick) {
  for (const e of ringEdges(ring)) {
    const o = pick(e);
    if (o) wallQuad(batch, o.m, e.a, e.b, z0, z1, o);
  }
}
function prism(kit, batch, wallM, capM, ring, z0, z1, opt = {}) {
  kit.walls(batch, wallM, [[ring]], z0, z1, opt);
  if (capM) kit.cap(batch, capM, [[ring]], z1);
}
// Projecting horizontal band (string course / cornice) of height h at z, out metres proud.
function band(kit, batch, m, ring, z, h, out) {
  const r = kit.offsetRing(ring, out);
  kit.walls(batch, m, [[r]], z, z + h);
  kit.cap(batch, m, [[r]], z + h);
  if (out > 0.05) kit.cap(batch, m, [[r]], z, { down: true });
}
// Parapet wall of thickness t on the ring between z and z + h.
function parapet(kit, batch, m, ring, z, h, t = 0.3) {
  const inner = kit.offsetRing(ring, -t);
  kit.walls(batch, m, [[ring]], z, z + h);
  kit.walls(batch, m, [[inner.slice().reverse()]], z, z + h);
  kit.cap(batch, m, [[ring, inner.slice().reverse()]], z + h);
}
// Vertical fins along an edge: count from spacing, depth outwards, width along the edge.
function finsAlong(kit, batch, m, e, z0, z1, spacing, depth, width, { skipEnds = true } = {}) {
  const n = Math.max(1, Math.round(e.len / spacing));
  for (let i = skipEnds ? 1 : 0; i <= (skipEnds ? n - 1 : n); i++) {
    const t = (i / n) * e.len;
    const x = e.a[0] + e.tx * t + (e.nx * depth) / 2,
      y = e.a[1] + e.ty * t + (e.ny * depth) / 2;
    kit.box(batch, m, x, y, z0, width, depth, z1 - z0, e.ang);
  }
}
// Horizontal bar along an edge (sunshade, louvre, canopy).
function barAlong(kit, batch, m, e, z, h, depth, inset = 0) {
  const L = e.len - 2 * inset;
  if (L <= 0.1) return;
  const mid = e.len / 2;
  const x = e.a[0] + e.tx * mid + (e.nx * depth) / 2,
    y = e.a[1] + e.ty * mid + (e.ny * depth) / 2;
  kit.box(batch, m, x, y, z, L, depth, h, e.ang);
}
function pointOn(e, t, off = 0) {
  return [e.a[0] + e.tx * t + e.nx * off, e.a[1] + e.ty * t + e.ny * off];
}
// Canvas helpers.
function noiseFill(g, w, h, base, r, amt = 0.08, size = 3) {
  g.fillStyle = base;
  g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += size)
    for (let x = 0; x < w; x += size) {
      const k = (r() - 0.5) * amt;
      g.fillStyle = k > 0 ? `rgba(255,255,255,${k})` : `rgba(0,0,0,${-k})`;
      g.fillRect(x, y, size, size);
    }
}
function brickCourses(g, w, h, r, base, course = 3) {
  noiseFill(g, w, h, base, r, 0.12, 3);
  g.fillStyle = 'rgba(230,220,200,0.18)';
  for (let y = 0; y < h; y += course) g.fillRect(0, y, w, 1);
}
function glassPane(g, x, y, w, h, r, base = [46, 62, 74]) {
  const grd = g.createLinearGradient(x, y, x + w * 0.4, y + h);
  const k = 0.85 + r() * 0.3;
  grd.addColorStop(
    0,
    `rgb(${(base[0] * k * 1.5) | 0},${(base[1] * k * 1.45) | 0},${(base[2] * k * 1.4) | 0})`,
  );
  grd.addColorStop(1, `rgb(${(base[0] * k) | 0},${(base[1] * k) | 0},${(base[2] * k) | 0})`);
  g.fillStyle = grd;
  g.fillRect(x, y, w, h);
}
function sash(g, x, y, w, h, r, { frame = '#f2efe6', panesX = 3, panesY = 2, bar = 2 } = {}) {
  g.fillStyle = frame;
  g.fillRect(x - bar, y - bar, w + 2 * bar, h + 2 * bar);
  glassPane(g, x, y, w, h, r);
  g.fillStyle = frame;
  g.fillRect(x, y + h / 2 - bar / 2, w, bar * 1.2);
  for (let i = 1; i < panesX; i++) g.fillRect(x + (w * i) / panesX - 0.5, y, 1.2, h);
  for (let j = 1; j < panesY * 2; j++)
    if (j !== panesY) g.fillRect(x, y + (h * j) / (panesY * 2) - 0.5, w, 1.2);
}
// ---- end helpers ----

// Segment of a circle (chord w, rise) as a slab of depth d (centred on y), base at z=0.
function segmentSlab(THREE, w, rise, d) {
  const R = ((w * w) / 4 + rise * rise) / (2 * rise);
  const sh = new THREE.Shape();
  sh.moveTo(-w / 2, 0);
  sh.lineTo(w / 2, 0);
  const a0 = Math.atan2(R - rise, w / 2);
  sh.absarc(0, rise - R, R, a0, Math.PI - a0, false);
  const geo = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 12 });
  geo.rotateX(Math.PI / 2); // shape y -> z, extrusion +z -> -y
  geo.translate(0, d / 2, 0);
  return geo;
}

export default {
  id: 'imperial_170_queens_gate',
  name: "170 Queen's Gate (Rector's Residence)",
  claims: ['28351f56-86f4-4152-99fe-01ac157d7cca'],
  references: [
    {
      title: "170 Queen's Gate - British Listed Buildings (Historic England 1227415)",
      url: 'https://britishlistedbuildings.co.uk/101227415-170-queens-gate-sw7-knightsbridge-and-belgravia-ward',
      used_for:
        'Grade II*, Shaw 1888, red brick Wren revival, gauged brick heads and aprons, small-pane sashes, louvred shutters, hipped tiled roof to eaves, central curved pedimented dormer with Serlian motif, segmental pediments, tall stacks',
    },
    {
      title: "170 Queen's Gate - Imperial College history",
      url: 'https://imperial.ac.uk/about/history/170-queens-gate',
      used_for: "red brick with stone dressings, completed 1889, Rector's lodging",
    },
    {
      title: "Plate 104: No. 170 Queen's Gate - Survey of London vol 38",
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-104',
      used_for: 'date 1888-9, main front to Imperial College Road',
    },
  ],
  notes:
    'Eaves raised to 11.1 m (three tall storeys over a low plinth) with a 5 m hipped roof; the Overture height 10.4 m is inferred from floors. Bay count (7 x 4), door position and dormer sizes are proportioned from the listing text, not measured.',
  build({ THREE, kit, buildings }) {
    const ring = ccw(buildings[0].polys[0][0]);
    // Main front: the long edge whose outward normal points most to the south.
    const es = ringEdges(ring);
    const front = es.filter((e) => e.len > 15).sort((p, q) => p.ny - q.ny)[0];
    const ang = front.ang;
    const ex = kit.orientedExtent(ring, ang);
    const { u0, u1, v0, v1 } = ex;
    const L = u1 - u0,
      D = v1 - v0,
      um = (u0 + u1) / 2,
      vm = (v0 + v1) / 2;
    const g = new THREE.Group();
    g.rotation.z = ang; // local (u, v) -> world
    const b = new kit.MeshBatch();
    const brick = kit.mat('#9a4a36'),
      stone = kit.mat('portland_stone'),
      white = kit.mat('white'),
      roofM = kit.roof('clay', 2),
      dark = kit.mat('dark_glass'),
      stackM = kit.mat('#8a4433');
    const storey = 3.4,
      base = 0.9,
      eave = base + 3 * storey,
      rise = 5.0;
    const bay = L / 7;
    const facadeM = kit.paintedMaterial('imperial_170qg:bay', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1702);
      brickCourses(c, w, h, r, '#9a4a36', 3);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const x = i * cw,
            y = j * ch;
          const ww = cw * 0.36,
            wh = ch * 0.6,
            wx = x + (cw - ww) / 2,
            wy = y + ch * 0.2;
          // Gauged rubbed-brick head and apron in brighter brick.
          c.fillStyle = '#c0644a';
          c.fillRect(wx - 6, wy - 12, ww + 12, 11);
          c.fillRect(wx - 3, wy + wh + 3, ww + 6, ch * 0.12);
          c.fillStyle = 'rgba(0,0,0,0.25)';
          for (let k = 0; k < 8; k++) c.fillRect(wx - 6 + ((ww + 12) * k) / 8, wy - 12, 1, 11);
          // Louvred shutters.
          c.fillStyle = '#3d4a3f';
          c.fillRect(wx - ww * 0.42 - 3, wy, ww * 0.38, wh);
          c.fillRect(wx + ww + 5, wy, ww * 0.38, wh);
          c.fillStyle = 'rgba(255,255,255,0.12)';
          for (let k = wy; k < wy + wh; k += 3) {
            c.fillRect(wx - ww * 0.42 - 3, k, ww * 0.38, 1);
            c.fillRect(wx + ww + 5, k, ww * 0.38, 1);
          }
          sash(c, wx, wy, ww, wh, r, { panesX: 3, panesY: 3, bar: 2.5 });
        }
    });
    // Plinth (stone), brick walls with painted sashes.
    const rect = [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    kit.walls(b, stone, [[rect]], 0, base);
    for (const e of ringEdges(rect))
      wallQuad(b, facadeM, e.a, e.b, base, eave, {
        bay: e.len > 20 ? bay : D / 4,
        storey,
        uvBase: base,
      });
    // String courses and quoins in stone.
    band(kit, b, stone, rect, base + storey - 0.1, 0.22, 0.08);
    band(kit, b, stone, rect, base - 0.12, 0.18, 0.1);
    for (const [cu, cv] of rect)
      for (let z = base, k = 0; z < eave - 0.3; z += 0.6, k++) {
        const w1 = k % 2 ? 0.9 : 0.55;
        kit.box(b, stone, cu, cv, z, w1, w1, 0.58);
      }
    // White modillion eaves cornice.
    band(kit, b, white, rect, eave - 0.35, 0.55, 0.5);
    for (const e of ringEdges(kit.offsetRing(rect, 0.3))) {
      const n = Math.round(e.len / 0.7);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n));
        kit.box(b, white, p[0], p[1], eave - 0.6, 0.18, 0.5, 0.25, e.ang);
      }
    }
    // Hipped tiled roof.
    const roofRing = kit.offsetRing(rect, 0.15);
    kit.pitchedRoof(b, roofM, brick, roofRing, 0, eave + 0.2, rise, 'hipped', { overhang: 0.3 });
    const half = D / 2 + 0.45;
    const slopeZ = (d) => eave + 0.2 + (rise * d) / half; // d: inwards from the eave line
    // Dormers on the front and back slopes.
    const dormer = (u, w, h, face, kind) => {
      const d = 1.4;
      const vFace = face < 0 ? v0 + d : v1 - d;
      const zb = slopeZ(d + 0.45) - 0.2;
      const depth = 2.4;
      const vc = vFace - (face * depth) / 2;
      kit.box(b, white, u, vc, zb, w, depth, h);
      // cheeks in tile colour
      kit.box(b, roofM, u - w / 2 - 0.05, vc - face * 0.1, zb, 0.12, depth, h);
      kit.box(b, roofM, u + w / 2 + 0.05, vc - face * 0.1, zb, 0.12, depth, h);
      // windows (Serlian = central arched light with side lights)
      const vf = vFace + face * 0.04;
      if (kind === 'serlian') {
        const ch = h - 1.5;
        kit.box(b, dark, u, vf, zb + 0.35, w * 0.3, 0.05, ch);
        kit.box(b, dark, u - w * 0.32, vf, zb + 0.35, w * 0.17, 0.05, ch * 0.75);
        kit.box(b, dark, u + w * 0.32, vf, zb + 0.35, w * 0.17, 0.05, ch * 0.75);
        const arch = segmentSlab(THREE, w * 0.3, w * 0.15, 0.05);
        b.addGeometry(
          dark,
          arch,
          new THREE.Matrix4().makeTranslation(u, vf + 0.025, zb + 0.35 + ch),
        );
        arch.dispose();
      } else kit.box(b, dark, u, vf, zb + 0.35, w * 0.6, 0.05, h - 0.8);
      // lead roof behind and a curved (segmental) pediment over the front
      kit.box(b, kit.mat('lead'), u, vc, zb + h, w + 0.2, depth, 0.15);
      const ped = segmentSlab(THREE, w + 0.5, Math.min(1.1, w * 0.28), 0.5);
      b.addGeometry(
        white,
        ped,
        new THREE.Matrix4().makeTranslation(u, vFace - face * 0.15, zb + h - 0.05),
      );
      ped.dispose();
    };
    dormer(um, 4.6, 3.3, -1, 'serlian');
    dormer(u0 + bay * 1.5, 2.0, 2.3, -1, 'seg');
    dormer(u1 - bay * 1.5, 2.0, 2.3, -1, 'seg');
    dormer(um, 2.0, 2.3, 1, 'seg');
    // Tall brick stacks with stone caps rising well above the ridge.
    const ridgeZ = eave + 0.2 + rise;
    const stack = (u, v, w, d) => {
      kit.box(b, stackM, u, v, eave, w, d, ridgeZ + 3.2 - eave);
      kit.box(b, stone, u, v, ridgeZ + 3.2, w + 0.3, d + 0.3, 0.35);
      for (let i = 0; i < 3; i++) {
        const p = new THREE.CylinderGeometry(0.15, 0.18, 0.7, 6).rotateX(Math.PI / 2);
        b.addGeometry(
          kit.mat('terracotta'),
          p,
          new THREE.Matrix4().makeTranslation(u - w / 3 + (i * w) / 3, v, ridgeZ + 3.9),
        );
        p.dispose();
      }
    };
    stack(u0 + D / 2 - 0.2, vm, 2.6, 1.3);
    stack(u1 - D / 2 + 0.2, vm, 2.6, 1.3);
    stack(u0 + 0.9, vm + 3.2, 1.2, 2.4);
    stack(u1 - 0.9, vm - 3.2, 1.2, 2.4);
    // Stone doorcase with segmental hood at the centre of the front, and area railing.
    kit.box(b, stone, um, v0 - 0.25, 0, 2.8, 0.5, 3.9);
    kit.box(b, kit.mat('#2d3530'), um, v0 - 0.52, base, 1.4, 0.06, 2.6);
    kit.box(b, stone, um, v0 - 0.9, 3.8, 3.4, 1.4, 0.3);
    kit.box(b, stone, um, v0 - 1.0, 0, 2.6, 1.6, base - 0.1);
    for (let u = u0 - 0.5; u <= u1 + 0.5; u += 0.25)
      if (Math.abs(u - um) > 1.4) kit.box(b, kit.mat('black'), u, v0 - 1.8, 0, 0.04, 0.04, 1.1);
    kit.box(b, kit.mat('black'), um - L / 4 - 0.4, v0 - 1.8, 1.05, L / 2 - 2, 0.06, 0.06);
    kit.box(b, kit.mat('black'), um + L / 4 + 0.4, v0 - 1.8, 1.05, L / 2 - 2, 0.06, 0.06);
    g.add(b.toGroup('imperial_170_queens_gate'));
    return g;
  },
};
