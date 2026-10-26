// The Grosvenor Hotel (now The Clermont, Victoria), Buckingham Palace Road (James Thomas
// Knowles, exhibited 1860, opened 1862). Italianate hotel of yellow brick and Bath stone
// with a rusticated ground floor, portrait roundels in the first-floor window spandrels,
// rising to ~150 ft under one of London's first French pavilion roofs.
export default {
  id: 'grosvenor_hotel_victoria',
  name: 'Grosvenor Hotel, Victoria',
  claims: ['f4f2322d-a29e-4725-bba0-980f41a9a318'],
  references: [
    {
      title: 'The Clermont, Victoria - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Clermont,_Victoria',
      used_for:
        'J. T. Knowles, RA 1860, opened 1862; listing: one of the first French pavilion roofs in London; yellow brick and Bath stone, rusticated ground floor',
    },
    {
      title: '1862 - The Grosvenor Hotel, London - Archiseek',
      url: 'https://www.archiseek.com/grosvenor-hotel-pimlico-london/',
      used_for: 'Italianate, eight storeys to 150 ft with a French Renaissance roof',
    },
    {
      title: 'Grosvenor Hotel heads - London Remembers',
      url: 'https://www.londonremembers.com/sites/2869',
      used_for:
        'portrait busts/roundels in the first-floor window spandrels of the Buckingham Palace Road front',
    },
  ],
  notes:
    'Overture h 15.5 m replaced: cornice 26 m over ground + six storeys, mansard with two dormer tiers to ' +
    '~34 m, end and centre pavilion roofs to ~42 m with cresting (towards the quoted 150 ft). Bay rhythm, ' +
    'pavilion widths, roundel count and the porch are approximations from the descriptions.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // ---- local helpers (modules have no imports) -----------------------------------
    const ccw = (r) => {
      const o = r.slice();
      if (kit.ringArea(o) < 0) o.reverse();
      return o;
    };
    const edges = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          a,
          b,
          k,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
          mx: (a[0] + b[0]) / 2,
          my: (a[1] + b[1]) / 2,
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box on edge e from s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
      const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, p[0], p[1], z0, Math.abs(s1 - s0), Math.abs(d1 - d0), z1 - z0, e.ang, c);
    };
    const prism = (m, ring, z0, z1, top = m) => {
      kit.walls(batch, m, [[ring]], z0, z1);
      if (top) kit.cap(batch, top, [[ring]], z1);
    };
    const wins = (e, s0, s1, z, o) => kit.windowRow(batch, at(e, s0), at(e, s1), z, o);
    const cyl = (m, x, y, z0, r0, r1, h, seg = 12) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) => {
      const g = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
      g.dispose();
    };
    // Rectangle ring (CCW) centred at (cx, cy), long axis at angle ang.
    const rect = (cx, cy, ang, L, W) => {
      const c = Math.cos(ang),
        s = Math.sin(ang);
      return [
        [-L / 2, -W / 2],
        [L / 2, -W / 2],
        [L / 2, W / 2],
        [-L / 2, W / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    // Triangular gable (pediment) standing on edge e between s0..s1, base z, rise, from d0..d1.
    const gable = (m, e, s0, s1, z, rise, d0 = 0, d1 = 0.4) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, 0);
      sh.lineTo(s1, 0);
      sh.lineTo((s0 + s1) / 2, rise);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d1 - d0, bevelEnabled: false });
      // shape x along edge, y up, extrude z outward -> map to world
      const m4 = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m4.setPosition(e.a[0] + e.nx * d0, e.a[1] + e.ny * d0, z);
      batch.addGeometry(m, g, m4);
      g.dispose();
    };
    // Facing test: cosine between an edge's outward normal and a direction (dx, dy).
    const facing = (e, dx, dy) => (e.nx * dx + e.ny * dy) / (Math.hypot(dx, dy) || 1);
    // Sloped band (mansard / hipped roof) from ring at z0 to the ring inset by `inset` at z1.
    // Returns the inner ring; capped with topMat unless topMat is null.
    const mansard = (m, ring, z0, inset, z1, topMat = m) => {
      const inner = kit.offsetRing(ring, -inset);
      for (let k = 0; k < ring.length; k++) {
        const j = (k + 1) % ring.length;
        const a = ring[k],
          b = ring[j],
          c = inner[j],
          d = inner[k];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [d[0], d[1], z1],
          [0, 0],
          [l / 3, 0],
          [l / 3, 1],
          [0, 1],
        );
      }
      if (topMat) kit.cap(batch, topMat, [[inner]], z1);
      return inner;
    };
    // Rows of windows on edge e at each sill height in zs.
    const rows = (e, s0, s1, zs, o) => {
      for (const z of zs)
        kit.windowRow(batch, at(e, s0), at(e, s1), z, typeof o === 'function' ? o(z) : o);
    };
    // ---------------------------------------------------------------------------------
    const brick = kit.mat('#c6ad7b', { roughness: 0.9 });
    const bath = kit.mat('#d8c69c', { roughness: 0.8 });
    const slate = kit.mat('#4e555c', { roughness: 0.72 });
    const lead = kit.mat('lead');
    const iron = kit.mat('#25282a', { roughness: 0.5, metalness: 0.5 });
    const glass = kit.mat('#2b3741', { roughness: 0.15, metalness: 0.35 });
    const frame = kit.mat('#f1efe8');
    const ring = ccw(buildings[0].polys[0][0]);
    const G = 5.2,
      ST = 3.45,
      NU = 6,
      CORN = G + NU * ST; // 25.9
    kit.walls(batch, bath, [[ring]], 0, G);
    kit.walls(batch, brick, [[ring]], G, CORN);
    for (let z = 0.6; z < G - 0.5; z += 0.6)
      kit.cornice(batch, bath, ring, z, { height: 0.48, projection: 0.06 });
    kit.cornice(batch, bath, ring, G - 0.45, { height: 0.55, projection: 0.35 });
    kit.cornice(batch, bath, ring, G + ST - 0.2, { height: 0.3, projection: 0.12 });
    kit.cornice(batch, bath, ring, CORN - 0.9, { height: 1.0, projection: 0.8, steps: 3 });
    kit.walls(batch, bath, [[ring]], CORN, CORN + 0.8);
    mansard(slate, kit.offsetRing(ring, -0.5), CORN + 0.5, 1.6, CORN + 7.4, lead);
    const E = edges(ring);
    const main = E.filter((e) => e.len > 15);
    const front = main.reduce((p, q) => (q.len > p.len ? q : p)); // Buckingham Palace Road front
    for (const e of E) {
      if (e.len < 8) continue;
      const nb = Math.round(e.len / 3.4);
      const o = { count: nb, margin: 0.8, frame, sill: bath, glass, bars: 1 };
      wins(e, 0, e.len, 0.9, { ...o, width: 1.6, height: 3.1, head: 'arch', frame: bath });
      wins(e, 0, e.len, G + 0.5, {
        ...o,
        width: 1.4,
        height: 2.6,
        head: 'arch',
        surround: 0.16,
        surroundMat: bath,
      });
      for (let f = 1; f < NU; f++)
        wins(e, 0, e.len, G + f * ST + 0.55, {
          ...o,
          width: 1.3,
          height: f < 3 ? 2.3 : 2.0,
          head: f === 1 ? 'pediment' : 'lintel',
          surround: 0.12,
          surroundMat: bath,
        });
      // quoins at the edge ends
      for (const s of [0.6, e.len - 0.6])
        for (let z = G; z < CORN - 1; z += 1.0)
          ebox(
            bath,
            e,
            s - (z % 2 < 1 ? 0.6 : 0.4),
            s + (z % 2 < 1 ? 0.6 : 0.4),
            0,
            0.1,
            z,
            z + 0.5,
          );
      // first-floor balconies on the long fronts
      if (e.len > 30) ebox(iron, e, 1, e.len - 1, 0.6, 0.66, G + 0.3, G + 1.2);
      if (e.len > 30) ebox(bath, e, 1, e.len - 1, 0, 0.7, G + 0.15, G + 0.3);
      // dormers: two tiers in the mansard
      for (const [z, inset, k0] of [
        [CORN + 0.9, 0.6, 0],
        [CORN + 4.3, 1.3, 0.5],
      ]) {
        for (let k = 0; k < nb; k++) {
          if (k0 && k % 2) continue;
          const s = 0.8 + ((e.len - 1.6) * (k + 0.5)) / nb;
          ebox(slate, e, s - 0.75, s + 0.75, -inset - 0.9, -inset, z, z + 2.0);
          wins(e, s - 0.75, s + 0.75, z + 0.25, {
            count: 1,
            margin: 0.2,
            width: 0.9,
            height: 1.4,
            head: 'arch',
            frame,
            sill: bath,
            glass,
            bars: 0,
            depth: 0.06,
          });
        }
      }
    }
    // portrait roundels in the first-floor spandrels of the main front
    {
      const e = front,
        nb = Math.round(e.len / 3.4);
      const disc = new THREE.CylinderGeometry(0.42, 0.42, 0.14, 12);
      for (let k = 0; k < nb - 1; k++) {
        const s = 0.8 + ((e.len - 1.6) * (k + 1)) / nb;
        const p = at(e, s, 0.07);
        const m = new THREE.Matrix4().makeRotationZ(e.ang);
        m.setPosition(p[0], p[1], G + 2.55);
        batch.addGeometry(bath, disc, m);
      }
      disc.dispose();
      // entrance porch with paired columns
      const sm = e.len / 2;
      ebox(bath, e, sm - 4, sm + 4, 0, 4.0, 4.3, 5.0);
      for (const s of [sm - 3.5, sm - 2.9, sm + 2.9, sm + 3.5]) {
        const p = at(e, s, 3.6);
        cyl(bath, p[0], p[1], 0, 0.28, 0.25, 4.3, 10);
      }
      ebox(glass, e, sm - 1.6, sm + 1.6, 0, 0.12, 0.1, 3.6);
    }
    // French pavilion roofs: both ends and the centre of the main front
    {
      const e = front;
      for (const s of [6.5, e.len / 2, e.len - 6.5]) {
        const c = at(e, s, -7);
        const pw = s === e.len / 2 ? 14 : 12;
        const pr = rect(c[0], c[1], e.ang, pw, 14);
        kit.walls(batch, brick, [[pr]], CORN, CORN + 2.2);
        kit.cornice(batch, bath, pr, CORN + 1.6, { height: 0.6, projection: 0.4 });
        // convex (bell-cast) roof: two mansard stages then a flat cresting deck
        const r1 = mansard(slate, pr, CORN + 2.2, 0.9, CORN + 8.5, null);
        const r2 = mansard(slate, r1, CORN + 8.5, 2.2, CORN + 14.0, lead);
        for (const pe of edges(r2)) {
          ebox(iron, pe, 0, pe.len, -0.05, 0.05, CORN + 14.0, CORN + 15.2);
          for (let q = 0; q <= pe.len; q += 0.7)
            ebox(iron, pe, q - 0.04, q + 0.04, -0.05, 0.05, CORN + 14.0, CORN + 15.6);
        }
        for (const pe of edges(pr))
          wins(pe, 0, pe.len, CORN + 3.4, {
            count: 2,
            margin: 2.4,
            width: 1.1,
            height: 2.0,
            head: 'arch',
            frame,
            sill: bath,
            glass,
            bars: 0,
            depth: 0.9,
          });
        // chimney stacks either side
        for (const sx of [-pw / 2 - 1.5, pw / 2 + 1.5]) {
          const q = at(e, s + sx, -8);
          kit.box(batch, brick, q[0], q[1], CORN + 7, 1.6, 3.2, 4.2, e.ang);
        }
      }
    }
    g.add(batch.toGroup('grosvenor_hotel_victoria'));
    return g;
  },
};
