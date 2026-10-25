// Dyson Building, 25 Exhibition Road: home since 2018 of Imperial College's Dyson
// School of Design Engineering. Edwardian Baroque former Royal Mail sorting office
// (and Met Office London HQ 1910-19, later a Science Museum annexe) on the corner of
// Exhibition Road and Imperial College Road, refurbished by Pascall+Watson with
// its exterior retained. Four storeys: rusticated stone ground floor with large
// sweeping curved-headed windows, red brick upper floors with tall box sashes in
// stone surrounds, stone quoins, a main cornice under an attic storey, and a
// balustraded parapet; a low glazed link joins the RCS1 range to the west.
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

export default {
  id: 'imperial_dyson_building',
  name: 'Dyson School of Design Engineering (25 Exhibition Road)',
  claims: ['f84e24cc-0cba-4bcb-a8dc-9c39610db775', '22d8e5b3-c1a4-4dbb-841a-dfd4e76aec40'],
  references: [
    {
      title: 'Dyson School of Design Engineering - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Dyson_School_of_Design_Engineering',
      used_for:
        'Dyson Building at 25 Exhibition Road since 2018; former Met Office London HQ 1910-19 and Science Museum building',
    },
    {
      title: 'Dyson Building - Imperial College of London (Pascall+Watson)',
      url: 'https://www.pascalls.co.uk/projects/work/education/dyson-building',
      used_for: 'exterior retained, treated as if Grade II* listed; four-storey change of use',
    },
    {
      title: 'Dyson School of Design Engineering fitted with Selectaglaze windows - PBC Today',
      url: 'https://www.pbctoday.co.uk/news/planning-construction-news/dyson-school-design-engineering/66755/',
      used_for:
        'Edwardian baroque former sorting office on the corner of Exhibition Road and Imperial College Road; large sweeping curved-headed casements and tall box sash windows',
    },
    {
      title:
        'dyson school of design engineering link bridge receives planning approval - Pascall+Watson',
      url: 'https://www.pascalls.co.uk/news/article/dyson-school-of-design-engineering-link-bridge-receives-planning-approval/',
      used_for: 'minimalist glazed link structure',
    },
  ],
  notes:
    'Searches confirmed the Edwardian Baroque style and window types but not the facing materials; red brick with Portland stone dressings is assumed. Bay rhythm, corner treatment and attic are approximate. The 3.4 m strip footprint between RCS1 and the Dyson Building is modelled as a low glazed link. Height 13.6 m from Overture.',
  build({ THREE, kit, byId }) {
    const main = byId['f84e24cc-0cba-4bcb-a8dc-9c39610db775'];
    const link = byId['22d8e5b3-c1a4-4dbb-841a-dfd4e76aec40'];
    const ring = ccw(main.polys[0][0]);
    const H = main.h,
      gf = 4.6,
      cornice = H - 3.1,
      storey = (cornice - gf) / 2;
    const b = new kit.MeshBatch();
    const stone = kit.mat('portland_stone'),
      roofM = kit.roof('slate', 1),
      dark = kit.mat('dark_glass');
    const groundM = kit.paintedMaterial('imperial_dyson_building:ground', 512, 256, (c, w, h) => {
      const r = kit.rng(0.2501);
      noiseFill(c, w, h, '#ddd5c2', r, 0.06, 4);
      c.fillStyle = 'rgba(90,80,60,0.35)';
      for (let y = 0; y < h; y += 18) c.fillRect(0, y, w, 2);
      const cw = w / 4;
      for (let i = 0; i < 4; i++) {
        // large curved-headed (segmental) window
        const ww = cw * 0.66,
          x = i * cw + (cw - ww) / 2,
          y = h * 0.14,
          hh = h * 0.7;
        c.fillStyle = '#e9e3d4';
        c.fillRect(x - 6, y - 6, ww + 12, hh + 10);
        glassPane(c, x, y + 10, ww, hh - 10, r, [40, 54, 64]);
        c.beginPath();
        c.ellipse(x + ww / 2, y + 12, ww / 2, 14, 0, Math.PI, 0);
        c.fill();
        c.fillStyle = '#efece4';
        for (let k = 1; k < 4; k++) c.fillRect(x + (ww * k) / 4 - 1, y, 2, hh);
        c.fillRect(x, y + hh * 0.38, ww, 2);
        c.fillStyle = '#f0ebe0';
        c.fillRect(x + ww / 2 - 8, y - 8, 16, 18); // keystone
      }
    });
    const upperM = kit.paintedMaterial('imperial_dyson_building:upper', 512, 256, (c, w, h) => {
      const r = kit.rng(0.3501);
      brickCourses(c, w, h, r, '#9c4c38', 3);
      const cw = w / 4,
        ch = h / 2;
      for (let j = 0; j < 2; j++)
        for (let i = 0; i < 4; i++) {
          const ww = cw * 0.4,
            wh = ch * 0.68,
            wx = i * cw + (cw - ww) / 2,
            wy = j * ch + ch * 0.16;
          c.fillStyle = '#e2dbc9';
          c.fillRect(wx - 8, wy - 9, ww + 16, wh + 15);
          c.fillRect(wx - 11, wy - 14, ww + 22, 7); // cornice hood
          sash(c, wx, wy, ww, wh, r, { panesX: 2, panesY: 1, bar: 2 });
        }
    });
    const atticM = kit.paintedMaterial('imperial_dyson_building:attic', 512, 128, (c, w, h) => {
      const r = kit.rng(0.4501);
      brickCourses(c, w, h, r, '#9c4c38', 3);
      const cw = w / 4;
      for (let i = 0; i < 4; i++) {
        const ww = cw * 0.4,
          wx = i * cw + (cw - ww) / 2;
        c.fillStyle = '#e2dbc9';
        c.fillRect(wx - 6, h * 0.22 - 6, ww + 12, h * 0.55 + 10);
        sash(c, wx, h * 0.22, ww, h * 0.5, r, { panesX: 2, panesY: 1, bar: 2 });
      }
    });
    edgeWalls(b, ring, 0, gf, () => ({ m: groundM, bay: 4.4, storey: gf / 2 }));
    edgeWalls(b, ring, gf, cornice, () => ({ m: upperM, bay: 4.4, storey, uvBase: gf }));
    // Attic storey above the main cornice (one storey, texture tile = one row of 128 px).
    edgeWalls(b, ring, cornice + 0.6, H - 0.9, () => ({
      m: atticM,
      bay: 4.4,
      storey: (H - 0.9 - cornice - 0.6) / 2,
      uvBase: cornice + 0.6,
    }));
    band(kit, b, stone, ring, gf - 0.3, 0.45, 0.18);
    band(kit, b, stone, ring, cornice, 0.6, 0.6);
    band(kit, b, stone, ring, 0, 0.5, 0.1);
    // Stone quoins at every convex corner of the upper floors.
    for (const e of ringEdges(ring)) {
      for (let z = gf, k = 0; z < cornice - 0.2; z += 0.55, k++) {
        const w1 = k % 2 ? 1.0 : 0.6;
        kit.box(b, stone, e.a[0], e.a[1], z, w1, w1, 0.53, e.ang);
      }
    }
    // Balustraded parapet and a slate roof behind it.
    const post = new THREE.CylinderGeometry(0.09, 0.14, 0.55, 6).rotateX(Math.PI / 2);
    for (const e of ringEdges(ring)) {
      barAlong(kit, b, stone, e, H - 0.9, 0.15, 0.45);
      barAlong(kit, b, stone, e, H - 0.15, 0.15, 0.45);
      const n = Math.floor(e.len / 0.42);
      for (let i = 0; i < n; i++) {
        const p = pointOn(e, (i + 0.5) * (e.len / n), 0.22);
        b.addGeometry(stone, post, new THREE.Matrix4().makeTranslation(p[0], p[1], H - 0.47));
      }
      const p = pointOn(e, 0, 0.22);
      kit.box(b, stone, p[0], p[1], H - 0.9, 0.7, 0.7, 1.15, e.ang);
    }
    post.dispose();
    kit.cap(b, kit.roof('flat', 1), [[ring]], H - 0.9);
    // Corner feature at Exhibition Road / Imperial College Road (north-east corner):
    // stone-faced pavilion with a segmental pediment and a small cupola.
    const ne = ring.reduce((q, p) => (p[0] + p[1] > q[0] + q[1] ? p : q), ring[0]);
    const north = ringEdges(ring).sort((p, q) => q.ny - p.ny)[0];
    const ang = north.ang;
    // the north edge runs westwards from the corner; step along it and inwards
    const sgn = Math.hypot(north.a[0] - ne[0], north.a[1] - ne[1]) < 0.5 ? 1 : -1;
    const pc = [
      ne[0] + sgn * north.tx * 3.6 - north.nx * 3.6,
      ne[1] + sgn * north.ty * 3.6 - north.ny * 3.6,
    ];
    kit.box(b, stone, pc[0], pc[1], cornice + 0.6, 7.6, 7.6, H - cornice + 0.8, ang);
    // oculus windows in stone surrounds on the two street faces of the pavilion
    for (const [nx, ny] of [
      [north.nx, north.ny],
      [north.ny, -north.nx],
    ]) {
      const ring2 = new THREE.CylinderGeometry(1.0, 1.0, 0.2, 16);
      const disc = new THREE.CylinderGeometry(0.75, 0.75, 0.24, 16);
      const rot = new THREE.Matrix4().makeRotationZ(Math.atan2(ny, nx) - Math.PI / 2);
      const t = new THREE.Matrix4().makeTranslation(
        pc[0] + nx * 3.85,
        pc[1] + ny * 3.85,
        (cornice + H) / 2 + 0.6,
      );
      b.addGeometry(stone, ring2, t.clone().multiply(rot));
      b.addGeometry(dark, disc, t.clone().multiply(rot));
      ring2.dispose();
      disc.dispose();
    }
    kit.box(b, roofM, pc[0], pc[1], H + 1.4, 6.0, 6.0, 0.8, ang);
    const dome = new THREE.SphereGeometry(1.6, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
      Math.PI / 2,
    );
    b.addGeometry(
      kit.mat('lead'),
      dome,
      new THREE.Matrix4().makeTranslation(pc[0], pc[1], H + 2.2),
    );
    dome.dispose();
    const fin = new THREE.CylinderGeometry(0.06, 0.1, 1.4, 6).rotateX(Math.PI / 2);
    b.addGeometry(kit.mat('gold'), fin, new THREE.Matrix4().makeTranslation(pc[0], pc[1], H + 4.4));
    fin.dispose();
    // Low glazed link to the west.
    if (link) {
      const lr = ccw(link.polys[0][0]);
      kit.walls(b, kit.mat('glass'), [[kit.offsetRing(lr, -0.05)]], 0, link.h - 0.4);
      kit.walls(b, kit.mat('aluminium'), [[lr]], link.h - 0.4, link.h);
      kit.cap(b, kit.mat('aluminium'), [[lr]], link.h);
    }
    const g = new THREE.Group();
    g.add(b.toGroup('imperial_dyson_building'));
    return g;
  },
};
