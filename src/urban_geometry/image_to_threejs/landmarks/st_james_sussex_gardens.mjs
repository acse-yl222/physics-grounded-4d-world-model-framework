// Church of St James, Sussex Gardens, Paddington (Grade II*). The 1841-43 church by
// Goldicutt and Gutch was rebuilt and turned round by G. E. Street in 1881-82: the old
// east end became the west, and the 1843 tower and recessed spire were kept at the new
// (liturgical) east end facing Sussex Gardens. Decorated Gothic, yellow brick with stone
// dressings, aisled nave with clerestory under a steep slate roof.
export default {
  id: 'st_james_sussex_gardens',
  name: 'St James, Sussex Gardens',
  claims: ['a8641f56-b859-41ed-b264-2aa7b8da99fe'],
  references: [
    {
      title: 'Church of St James, Hyde Park Ward - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101237437-church-of-st-james-hyde-park-ward',
      used_for:
        '1881 by G.E. Street retaining 1841-43 work by Goldicutt and Gutch; Decorated style; yellow brick, knapped flint; two-stage east tower with recessed spire; aisled nave',
    },
    {
      title: 'St James Paddington - Church of England Church Heritage Record',
      url: 'https://heritage.churchofengland.org/buildings/7600',
      used_for:
        'Street turned the church round, building over the old church and keeping the 1843 tower, spire, porches and crypt',
    },
    {
      title: 'Sussex Gardens Open Space - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record?ID=WST120',
      used_for: 'remodelling date 1882 and setting on Sussex Gardens',
    },
    {
      title: 'St James Paddington - Geograph',
      url: 'https://www.geograph.org.uk/photo/3918033',
      used_for: 'completion c. 1884',
    },
  ],
  notes:
    'Spire height is not given by the sources found; the tip is modelled at ~52 m (tower 25 m + spire). Tower placed at the north-east (Sussex Gardens) end of the footprint; nave/aisle widths, clerestory and window tracery are simplified (pointed lights with a single transom).',
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
    const ring = ringOf('a8641f56-b859-41ed-b264-2aa7b8da99fe');
    const brick = kit.mat('#c3ab78', { roughness: 0.92 });
    const stone = kit.mat('#d9cfb4', { roughness: 0.85 });
    const slate = kit.mat('slate');
    const glassW = kit.mat('#2e3a40', { roughness: 0.3, metalness: 0.2 });
    const louvre = kit.mat('#37332e', { roughness: 0.9 });
    const ang = Math.atan2(760.7 - 733.7, 1668.6 - 1637.4); // long axis, SW -> NE
    const c = Math.cos(ang),
      s = Math.sin(ang);
    const L = (u, v) => [1660.25 + u * c - v * s, 737.96 + u * s + v * c];
    const local = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
    // footprint extent along the axis: u in [-21, 21], v in [-11.5, 11.5]
    const AISLE = 8.0,
      NAVE = 15.5,
      RIDGE = 23.5,
      NV = 5.2;

    // aisles (outer walls on the footprint) with lean-to roofs
    const aisleRing = local(-19.5, 13.5, -11.2, 11.2);
    prism(brick, aisleRing, 0, AISLE, null);
    kit.cornice(B, stone, aisleRing, 0, { height: 0.8, projection: 0.2 });
    kit.cornice(B, stone, aisleRing, AISLE - 0.4, { height: 0.4, projection: 0.25 });
    for (const sgn of [-1, 1]) {
      const a0 = L(-19.5, sgn * 11.4),
        a1 = L(13.5, sgn * 11.4),
        b0 = L(-19.5, sgn * NV),
        b1 = L(13.5, sgn * NV);
      const q = sgn > 0 ? [a1, a0, b0, b1] : [a0, a1, b1, b0];
      B.add(
        slate,
        [
          [q[0][0], q[0][1], AISLE],
          [q[1][0], q[1][1], AISLE],
          [q[2][0], q[2][1], 11.2],
          [q[3][0], q[3][1], 11.2],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    // aisle windows: pointed two-light windows between buttresses
    const AE = edgesOf(aisleRing);
    for (const e of [AE[0], AE[2]]) {
      kit.windowRow(B, e.a, e.b, 2.0, {
        bay: 4.1,
        width: 1.9,
        height: 3.6,
        head: 'arch',
        glass: glassW,
        frame: stone,
        sill: stone,
        bars: 1,
        depth: 0.2,
        margin: 1.5,
      });
      const n = Math.round(e.len / 4.1);
      for (let i = 0; i <= n; i++) {
        const t = 1.5 + ((e.len - 3) * i) / n - 2.05 * 0;
        ebox(brick, e, t - 0.35, t + 0.35, 0, 0.8, 0, AISLE - 1.2);
        ebox(stone, e, t - 0.4, t + 0.4, 0, 0.9, AISLE - 1.3, AISLE - 1.05);
      }
    }
    // nave walls, clerestory and steep gabled slate roof
    const nave = local(-19.5, 13.5, -NV, NV);
    prism(brick, nave, AISLE, NAVE, null);
    kit.pitchedRoof(B, slate, brick, nave, ang, NAVE, RIDGE - NAVE, 'gabled', { overhang: 0.4 });
    kit.cornice(B, stone, nave, NAVE - 0.35, { height: 0.35, projection: 0.2 });
    const NE = edgesOf(nave);
    for (const e of [NE[0], NE[2]])
      kit.windowRow(B, e.a, e.b, 11.6, {
        bay: 4.1,
        width: 1.3,
        height: 2.6,
        head: 'arch',
        glass: glassW,
        frame: stone,
        bars: 0,
        margin: 1.5,
      });
    // great west window (SW gable) and gable cross
    {
      const e = NE[3];
      kit.windowRow(B, e.a, e.b, 4.0, {
        count: 1,
        width: 5.2,
        height: 10.0,
        head: 'arch',
        glass: glassW,
        frame: stone,
        bars: 3,
        depth: 0.3,
        margin: 2,
      });
      const m = at(e, e.len / 2, 0.2);
      kit.box(B, stone, m[0], m[1], RIDGE - 0.2, 0.25, 0.25, 2.0, ang);
      kit.box(B, stone, m[0], m[1], RIDGE + 1.0, 1.2, 0.25, 0.25, ang + Math.PI / 2);
      // west porch
      prism(brick, local(-21, -19.5, -2.6, 2.6), 0, 4.6, null);
      kit.pitchedRoof(
        B,
        slate,
        brick,
        local(-21, -19.5, -2.6, 2.6),
        ang + Math.PI / 2,
        4.6,
        2.6,
        'gabled',
        { overhang: 0.2 },
      );
    }
    // chancel link to the tower
    prism(brick, local(13.5, 15.5, -NV, NV), 0, NAVE, null);
    kit.pitchedRoof(
      B,
      slate,
      brick,
      local(13.5, 15.5, -NV, NV),
      ang,
      NAVE,
      RIDGE - NAVE - 1,
      'gabled',
      { overhang: 0.2 },
    );

    // --- 1843 tower and recessed spire at the Sussex Gardens end ----------------------
    const TS = 7.2,
      TT = 25;
    const tc = L(17.8, 0);
    const tower = rect(tc[0], tc[1], TS, TS, ang);
    prism(brick, tower, 0, TT, stone);
    for (const z of [0, 9.5, 17])
      kit.cornice(B, stone, tower, z, { height: z ? 0.45 : 0.9, projection: 0.2 });
    kit.cornice(B, stone, tower, TT - 0.6, { height: 0.6, projection: 0.35, steps: 2 });
    const TE = edgesOf(tower);
    for (const e of TE) {
      for (const [s0, s1] of [
        [-0.1, 0.9],
        [e.len - 0.9, e.len + 0.1],
      ]) {
        ebox(brick, e, s0, s1, 0, 1.1, 0, 10);
        ebox(brick, e, s0 + 0.1, s1 - 0.1, 0, 0.6, 10, 18);
      }
      kit.windowRow(B, e.a, e.b, 18.2, {
        count: 2,
        width: 1.0,
        height: 4.2,
        head: 'arch',
        glass: louvre,
        frame: stone,
        bars: 2,
        margin: 1.4,
      });
      kit.windowRow(B, e.a, e.b, 11.2, {
        count: 1,
        width: 1.0,
        height: 3.0,
        head: 'arch',
        glass: glassW,
        frame: stone,
        bars: 0,
        margin: 2,
      });
    }
    // east door under the tower, facing Sussex Gardens
    kit.windowRow(B, TE[1].a, TE[1].b, 0.2, {
      count: 1,
      width: 2.0,
      height: 3.2,
      head: 'arch',
      glass: louvre,
      frame: stone,
      bars: 0,
      depth: 0.35,
      margin: 2,
    });
    // parapet and corner pinnacles
    for (const e of TE) {
      ebox(stone, e, 0, e.len, -0.1, 0.3, TT, TT + 1.1);
      for (let k = 1; k < 6; k++)
        ebox(stone, e, (k * e.len) / 6 - 0.4, (k * e.len) / 6 + 0.4, -0.1, 0.3, TT + 1.1, TT + 1.5);
    }
    for (const [x, y] of tower) {
      kit.box(B, stone, x, y, TT - 0.5, 0.9, 0.9, 3.0, ang);
      cyl(stone, x, y, TT + 2.5, TT + 5.0, 0.5, 0.02, 4, ang + Math.PI / 4);
    }
    const TIP = 52,
      R0 = 2.8;
    cyl(stone, tc[0], tc[1], TT, TT + 1.0, R0 + 0.15, R0, 8, ang + Math.PI / 8);
    cyl(stone, tc[0], tc[1], TT + 1.0, TIP, R0, 0.1, 8, ang + Math.PI / 8);
    const rAt = (z) => R0 + ((0.1 - R0) * (z - TT - 1)) / (TIP - TT - 1);
    for (const [z, w, h] of [
      [TT + 2, 1.0, 2.0],
      [37, 0.6, 1.2],
    ])
      for (let q = 0; q < 4; q++) {
        const a = ang + (q * Math.PI) / 2;
        const r = rAt(z + h / 2) + 0.05;
        const x = tc[0] + Math.cos(a) * r,
          y = tc[1] + Math.sin(a) * r;
        kit.box(B, stone, x, y, z, w, 0.5, h, a + Math.PI / 2);
        kit.box(
          B,
          louvre,
          x + Math.cos(a) * 0.26,
          y + Math.sin(a) * 0.26,
          z + 0.15,
          w * 0.55,
          0.02,
          h * 0.7,
          a + Math.PI / 2,
        );
        cyl(stone, x, y, z + h, z + h + w * 0.7, w * 0.55, 0.02, 4, a + Math.PI / 4);
      }
    cyl(kit.mat('bronze'), tc[0], tc[1], TIP - 0.2, TIP + 0.5, 0.15, 0.1, 6);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 0.5, 0.1, 0.1, 1.4, ang);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 1.3, 0.7, 0.1, 0.1, ang + Math.PI / 2);
    return B.toGroup('st_james_sussex_gardens');
  },
};
