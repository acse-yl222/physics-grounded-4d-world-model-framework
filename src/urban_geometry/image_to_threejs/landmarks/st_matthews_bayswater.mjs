// St Matthew's, St Petersburgh Place, Bayswater (John Johnson, designed 1880, built
// 1881-82; Grade II*). Victorian Gothic in Bargate ragstone with Box-ground and Bath-stone
// dressings, with an unusually wide (50 ft) nave and a 240 ft (73 m) spire - one of the
// tallest in West London, visible for miles around.
export default {
  id: 'st_matthews_bayswater',
  name: "St Matthew's, Bayswater",
  claims: ['61fea737-6706-455c-af47-c3a76f0d6a69'],
  references: [
    {
      title: "St Matthew's, Bayswater - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Matthew%27s,_Bayswater',
      used_for:
        'John Johnson, 1880-82, Victorian Gothic revival, Grade II*, replacing the Bayswater Chapel of 1818',
    },
    {
      title: "St Matthew's Bayswater - Victorian Web",
      url: 'https://victorianweb.org/art/architecture/johnsonj/5.html',
      used_for:
        'Bargate rag-stone with Box-ground and Bath-stone dressings; spire 240 ft (73 m); nave 50 ft wide',
    },
    {
      title: 'Church of St Matthew, Lancaster Gate Ward - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101236098-church-of-st-matthew-lancaster-gate-ward/maps',
      used_for: 'listing and location on St Petersburgh Place',
    },
    {
      title: 'St Matthew, Bayswater (Exterior) - Ship of Fools',
      url: 'https://steam2.shipoffools.com/?p=1845',
      used_for: 'soaring spire dominating the narrow road',
    },
  ],
  notes:
    'Spire height 73 m from the Victorian Web figure. The tower is placed on the square projection at the north-east corner of the footprint (St Petersburgh Place side); nave/transept roof heights and the window tracery are estimated. Footprint is nearly square, so a cruciform roof (wide nave, transepts) over aisled walls is assumed.',
  build(ctx) {
    // ---- local helpers (no imports: kept inline) ---------------------------------
    const { THREE, kit } = ctx;
    const B = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r.slice());
    const ringOf = (id) => ccw(ctx.byId[id].polys[0][0]);
    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1e-9;
        return {
          a,
          b,
          k,
          len,
          ux: dx / len,
          uy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.ux * s + e.nx * d, e.a[1] + e.uy * s + e.ny * d];
    // Box on edge e: along-edge span s0..s1, outward offset d0..d1, height z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(B, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const prism = (m, ring, z0, z1, topM = m) => {
      kit.walls(B, m, [[ring]], z0, z1, { bay: 1e6 });
      if (topM) kit.cap(B, topM, [[ring]], z1);
    };
    // Local rectangle (centre cx, cy, size w x d, rotated a) as a CCW ring.
    const rect = (cx, cy, w, d, a = 0) => {
      const c = Math.cos(a),
        s = Math.sin(a);
      return [
        [-w / 2, -d / 2],
        [w / 2, -d / 2],
        [w / 2, d / 2],
        [-w / 2, d / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    const geo = (m, g, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    // Upright cylinder / cone / pyramid (axis +z) from z0 to z1.
    const cyl = (m, x, y, z0, z1, r0, r1 = r0, seg = 12, rz = 0) =>
      geo(
        m,
        new THREE.CylinderGeometry(r1, r0, z1 - z0, seg).rotateX(Math.PI / 2),
        x,
        y,
        (z0 + z1) / 2,
        rz,
      );
    // Curtain wall on every edge of ring: glass, vertical mullions and storey bands.
    const curtain = (ring, z0, z1, o = {}) => {
      const {
        glass = kit.mat('glass'),
        frame = kit.mat('aluminium'),
        mull = 1.5,
        storey = 3.6,
        fin = 0.12,
        band = 0.25,
        bandMat = frame,
        minLen = 0.3,
        finMat = frame,
        edgeFilter = () => true,
      } = o;
      for (const e of edgesOf(ring)) {
        if (e.len < minLen || !edgeFilter(e)) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        if (mull > 0) {
          const n = Math.max(1, Math.round(e.len / mull));
          for (let i = 0; i < n; i++) {
            const s = (i * e.len) / n;
            ebox(finMat, e, s - 0.04, s + 0.04, 0, fin, z0, z1);
          }
        }
        if (band > 0)
          for (let z = z0 + storey; z < z1 - 0.3; z += storey)
            ebox(bandMat, e, 0, e.len, 0, fin * 0.8, z - band / 2, z + band / 2);
      }
    };
    // Punched windows storey by storey on edges passing filter.
    const punched = (ring, z0, storeys, storey, opts, filter = (e) => e.len > 2.5) => {
      for (const e of edgesOf(ring)) {
        if (!filter(e)) continue;
        for (let s = 0; s < storeys; s++) {
          const o = typeof opts === 'function' ? opts(s, e) : opts;
          if (o) kit.windowRow(B, e.a, e.b, z0 + s * storey, o);
        }
      }
    };
    // Distance from point to the nearest named road centreline (scene roads).
    const roadSegs = (names) => {
      const out = [];
      for (const r of ctx.scene.roads || []) {
        if (r.cls === 'footway' || (names && !names.includes(r.name))) continue;
        for (let i = 1; i < r.line.length; i++) out.push([r.line[i - 1], r.line[i]]);
      }
      return out;
    };
    // Nearest point on the road centrelines: [distance, x, y].
    const segNearest = (p, segs) => {
      let best = [Infinity, 0, 0];
      for (const [a, b] of segs) {
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          l = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l));
        const x = a[0] + t * dx,
          y = a[1] + t * dy,
          d = Math.hypot(p[0] - x, p[1] - y);
        if (d < best[0]) best = [d, x, y];
      }
      return best;
    };
    // Does edge e face a road: the nearest road point lies within maxD and in front of the
    // edge (within ~50 degrees of its outward normal)?
    const facesRoad = (e, segs, maxD = 22, cosMin = 0.64) => {
      const m = at(e, e.len / 2, 0);
      const [d, x, y] = segNearest(m, segs);
      if (!(d < maxD) || d < 1e-6) return false;
      return ((x - m[0]) * e.nx + (y - m[1]) * e.ny) / d > cosMin;
    };
    // ------------------------------------------------------------------------------
    const rag = kit.mat('#a8936b', { roughness: 0.95 }); // Bargate stone, warm brown-yellow
    const dress = kit.mat('#d8ccae', { roughness: 0.85 });
    const slate = kit.mat('slate');
    const glassW = kit.mat('#2e3a40', { roughness: 0.3, metalness: 0.2 });
    const louvre = kit.mat('#37332e', { roughness: 0.9 });
    const ring = ringOf('61fea737-6706-455c-af47-c3a76f0d6a69');
    const ang = Math.atan2(596.0 - 592.5, 641.3 - 623.7); // nave axis (W -> E)
    const c = Math.cos(ang),
      s = Math.sin(ang);
    const O = [645.66, 579.91];
    const L = (u, v) => [O[0] + u * c - v * s, O[1] + u * s + v * c];
    const local = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
    const AW = 11; // aisle wall height
    // outer (aisle) walls on the footprint
    prism(rag, ring, 0, AW, kit.mat('#7b7f83'));
    kit.cornice(B, dress, ring, 0, { height: 0.9, projection: 0.2 });
    kit.cornice(B, dress, ring, AW - 0.4, { height: 0.4, projection: 0.25 });
    punched(
      ring,
      2.2,
      1,
      0,
      {
        bay: 4.2,
        width: 1.8,
        height: 5.2,
        head: 'arch',
        glass: glassW,
        frame: dress,
        sill: dress,
        bars: 1,
        depth: 0.25,
        margin: 1.4,
      },
      (e) => e.len > 6,
    );
    // nave: 50 ft (15.2 m) wide, clerestoried, steep slate roof
    const NV = 7.8,
      NAVE = 19,
      RIDGE = 29;
    const nave = local(-18.6, 18.6, -NV, NV);
    prism(rag, nave, AW, NAVE, null);
    kit.pitchedRoof(B, slate, rag, nave, ang, NAVE, RIDGE - NAVE, 'gabled', { overhang: 0.4 });
    kit.cornice(B, dress, nave, NAVE - 0.4, { height: 0.4, projection: 0.2 });
    const NE = edgesOf(nave);
    for (const e of [NE[0], NE[2]])
      kit.windowRow(B, e.a, e.b, AW + 1.8, {
        bay: 4.6,
        width: 1.6,
        height: 3.6,
        head: 'arch',
        glass: glassW,
        frame: dress,
        bars: 1,
        margin: 2,
      });
    kit.windowRow(B, NE[1].a, NE[1].b, 5, {
      count: 1,
      width: 6.5,
      height: 11.5,
      head: 'arch',
      glass: glassW,
      frame: dress,
      bars: 3,
      depth: 0.3,
      margin: 2,
    });
    kit.windowRow(B, NE[3].a, NE[3].b, 6, {
      count: 1,
      width: 5.5,
      height: 9.5,
      head: 'arch',
      glass: glassW,
      frame: dress,
      bars: 3,
      depth: 0.3,
      margin: 2,
    });
    // transepts
    const tr = local(-5.5, 5.5, -16.5, 15.8);
    prism(rag, tr, AW, NAVE - 1.5, null);
    kit.pitchedRoof(B, slate, rag, tr, ang + Math.PI / 2, NAVE - 1.5, 8.5, 'gabled', {
      overhang: 0.4,
    });
    const TE = edgesOf(tr);
    for (const e of [TE[1], TE[3]])
      kit.windowRow(B, e.a, e.b, AW + 0.5, {
        count: 1,
        width: 4.5,
        height: 6.5,
        head: 'arch',
        glass: glassW,
        frame: dress,
        bars: 2,
        depth: 0.3,
        margin: 2,
      });
    // gable crosses
    for (const [u, v] of [
      [18.6, 0],
      [-18.6, 0],
    ]) {
      const p = L(u, v);
      kit.box(B, dress, p[0], p[1], RIDGE - 0.2, 0.3, 0.3, 2.2, ang);
      kit.box(B, dress, p[0], p[1], RIDGE + 1.1, 0.3, 1.3, 0.3, ang);
    }

    // --- tower and 73 m spire at the north-east corner ----------------------------
    const tc = [656.7, 599.6];
    const TS = 8.4,
      TT = 30,
      TIP = 73;
    const tower = rect(tc[0], tc[1], TS, TS, ang);
    prism(rag, tower, 0, TT, dress);
    for (const z of [0, 11, 19.5])
      kit.cornice(B, dress, tower, z, { height: z ? 0.45 : 1.0, projection: 0.22 });
    kit.cornice(B, dress, tower, TT - 0.7, { height: 0.7, projection: 0.4, steps: 2 });
    const TW = edgesOf(tower);
    for (const e of TW) {
      for (const [s0, s1] of [
        [-0.1, 1.0],
        [e.len - 1.0, e.len + 0.1],
      ]) {
        ebox(rag, e, s0, s1, 0, 1.3, 0, 12);
        ebox(rag, e, s0 + 0.1, s1 - 0.1, 0, 0.8, 12, 21);
        ebox(rag, e, s0 + 0.2, s1 - 0.2, 0, 0.4, 21, TT - 1);
        ebox(dress, e, s0, s1, 0, 1.4, 11.8, 12.2);
      }
      kit.windowRow(B, e.a, e.b, 21.5, {
        count: 2,
        width: 1.2,
        height: 5.6,
        head: 'arch',
        glass: louvre,
        frame: dress,
        bars: 2,
        depth: 0.3,
        margin: 1.7,
      });
      kit.windowRow(B, e.a, e.b, 13.5, {
        count: 1,
        width: 1.0,
        height: 3.4,
        head: 'arch',
        glass: glassW,
        frame: dress,
        bars: 0,
        margin: 2,
      });
    }
    kit.windowRow(B, TW[0].a, TW[0].b, 0.3, {
      count: 1,
      width: 2.3,
      height: 3.6,
      head: 'arch',
      glass: louvre,
      frame: dress,
      bars: 0,
      depth: 0.4,
      margin: 2,
    });
    // corner pinnacles and the octagonal spire with lucarnes and bands
    for (const [x, y] of tower) {
      const d = Math.hypot(x - tc[0], y - tc[1]);
      const px = tc[0] + ((x - tc[0]) * (d - 0.4)) / d,
        py = tc[1] + ((y - tc[1]) * (d - 0.4)) / d;
      kit.box(B, dress, px, py, TT - 0.6, 1.1, 1.1, 3.4, ang);
      cyl(dress, px, py, TT + 2.8, TT + 7.0, 0.62, 0.03, 4, ang + Math.PI / 4);
    }
    const R0 = 3.6;
    cyl(rag, tc[0], tc[1], TT, TT + 1.0, R0 + 0.2, R0, 8, ang + Math.PI / 8);
    cyl(rag, tc[0], tc[1], TT + 1.0, TIP, R0, 0.12, 8, ang + Math.PI / 8);
    const rAt = (z) => R0 + ((0.12 - R0) * (z - TT - 1)) / (TIP - TT - 1);
    for (const z of [44, 56])
      cyl(dress, tc[0], tc[1], z, z + 0.4, rAt(z) + 0.1, rAt(z + 0.4) + 0.1, 8, ang + Math.PI / 8);
    for (const [z, w, h] of [
      [TT + 1.5, 1.5, 3.0],
      [45.5, 0.9, 2.0],
      [57, 0.6, 1.3],
    ])
      for (let q = 0; q < 4; q++) {
        const a = ang + (q * Math.PI) / 2;
        const r = rAt(z + h / 2) + 0.1;
        const x = tc[0] + Math.cos(a) * r,
          y = tc[1] + Math.sin(a) * r;
        kit.box(B, dress, x, y, z, w, 0.6, h, a + Math.PI / 2);
        kit.box(
          B,
          louvre,
          x + Math.cos(a) * 0.31,
          y + Math.sin(a) * 0.31,
          z + 0.2,
          w * 0.55,
          0.02,
          h * 0.7,
          a + Math.PI / 2,
        );
        cyl(dress, x, y, z + h, z + h + w * 0.8, w * 0.6, 0.02, 4, a + Math.PI / 4);
      }
    cyl(kit.mat('bronze'), tc[0], tc[1], TIP - 0.2, TIP + 0.6, 0.18, 0.12, 6);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 0.6, 0.12, 0.12, 1.8, ang);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 1.6, 0.9, 0.12, 0.12, ang + Math.PI / 2);
    return B.toGroup('st_matthews_bayswater');
  },
};
