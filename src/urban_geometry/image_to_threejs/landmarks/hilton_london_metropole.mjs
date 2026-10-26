// Hilton London Metropole, 225 Edgware Road (Richard Seifert, opened 1972). A 24-storey,
// 91 m tower with east and west wings on a conference podium between the Marylebone
// Flyover and Paddington Basin; an 11-storey second wing was added in 1989 and a
// conference extension (HOK) in 2000.
export default {
  id: 'hilton_london_metropole',
  name: 'Hilton London Metropole',
  claims: ['fe3d16e8-a1d7-44e0-b109-7c8dc624e729'],
  references: [
    {
      title: 'Hilton London Metropole - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hilton_London_Metropole',
      used_for:
        'Richard Seifert; 24-storey 91 m tower opened 1972; 11-storey second wing 1989; bounded by the Marylebone Flyover and Paddington Basin',
    },
    {
      title: 'Hilton London Metropole - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1970/hiltonmetropole.html',
      used_for: 'main tower with east and west wings',
    },
    {
      title: 'The First Metropole Hotel Extension - locallocalhistory',
      url: 'https://www.locallocalhistory.co.uk/mp/p200/page223.htm',
      used_for: 'bedrooms up to the 25th floor with a plant room above',
    },
    {
      title: 'Hilton London Metropole - Buildington',
      url: 'https://www.buildington.co.uk/buildings/1881/england/london-w2/225-edgware-road/hilton-london-metropole',
      used_for: 'HOK conference extension completed 2000',
    },
  ],
  notes:
    'The whole site is a single Overture footprint; the split into podium (10 m), 11-storey west wing along the flyover, 7-storey east wing and the 91 m tower slab parallel to Edgware Road is reconstructed from the descriptions (positions approximate). Facade treatments are generic Seifert precast mullions / 1980s ribbon glazing.',
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
    const conc = kit.mat('#dcd8ce', { roughness: 0.82 });
    const spand = kit.mat('#c2beb4', { roughness: 0.85 });
    const glass = kit.mat('#34444f', { roughness: 0.12, metalness: 0.35 });
    const blueGlass = kit.mat('#4f6676', { roughness: 0.1, metalness: 0.45 });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8a8984');
    const site = ringOf('fe3d16e8-a1d7-44e0-b109-7c8dc624e729');

    // --- podium ---------------------------------------------------------------------
    const PH = 10;
    for (const e of edgesOf(site)) {
      if (e.len < 0.3) continue;
      B.quad(
        conc,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], PH],
        [e.a[0], e.a[1], PH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      if (e.len < 5) continue;
      ebox(glass, e, 0.6, e.len - 0.6, 0.02, 0.05, 0.4, 4.2);
      const n = Math.round(e.len / 3);
      for (let i = 0; i <= n; i++)
        ebox(conc, e, (i * e.len) / n - 0.3, (i * e.len) / n + 0.3, 0, 0.3, 0, 4.4);
      ebox(blueGlass, e, 0.6, e.len - 0.6, 0.02, 0.05, 5.4, 8.8);
      ebox(spand, e, 0, e.len, 0, 0.25, 4.4, 5.2);
    }
    kit.cornice(B, conc, site, PH - 0.6, { height: 0.6, projection: 0.3 });
    kit.cap(B, roofM, [[site]], PH);

    // --- 1989 west wing: 11 storeys of ribbon glazing along the flyover --------------
    const west = [
      [1981, 1456],
      [2080, 1456],
      [2080, 1477.6],
      [2044.9, 1483.0],
      [1981, 1483.2],
    ];
    const WH = 37;
    const WST = (WH - PH - 1) / 9;
    for (const e of edgesOf(west)) {
      B.quad(
        blueGlass,
        [e.a[0], e.a[1], PH],
        [e.b[0], e.b[1], PH],
        [e.b[0], e.b[1], WH],
        [e.a[0], e.a[1], WH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      for (let k = 0; k <= 9; k++)
        ebox(conc, e, 0, e.len, 0, 0.3, PH + k * WST, PH + k * WST + 1.0);
      const n = Math.round(e.len / 1.8);
      for (let i = 1; i < n; i++)
        ebox(dark, e, (i * e.len) / n - 0.04, (i * e.len) / n + 0.04, 0, 0.1, PH, WH);
    }
    kit.cornice(B, conc, west, WH - 0.2, { height: 1.0, projection: 0.3 });
    kit.cap(B, roofM, [[west]], WH + 0.8);
    kit.box(B, roofM, 2030, 1468, WH + 0.8, 18, 9, 3, 0);

    // --- east wing (7 storeys) ----------------------------------------------------
    const east = [
      [2080, 1445],
      [2081.9, 1445],
      [2099.7, 1427],
      [2127.8, 1395.4],
      [2151.2, 1416.8],
      [2154.8, 1416.4],
      [2157.8, 1419.5],
      [2158.2, 1423.4],
      [2155.5, 1427.3],
      [2151, 1427.5],
      [2149.3, 1428.7],
      [2151.2, 1430.6],
      [2132.4, 1451.5],
      [2130, 1450.9],
      [2127, 1453],
      [2108.4, 1473.2],
      [2080, 1477.6],
    ];
    const EH = 23.7;
    prism(conc, east, PH, EH, roofM);
    punched(
      east,
      PH + 0.9,
      4,
      3.25,
      {
        bay: 2.1,
        width: 1.5,
        height: 1.8,
        glass,
        frame: dark,
        sill: spand,
        head: 'none',
        bars: 0,
        depth: 0.15,
      },
      (e) => e.len > 4,
    );
    for (let k = 0; k < 4; k++)
      kit.cornice(B, spand, east, PH + 0.4 + k * 3.25, { height: 0.3, projection: 0.12 });
    kit.cornice(B, conc, east, EH - 0.7, { height: 0.7, projection: 0.3 });

    // --- 1972 tower: 24 storeys, 91 m, slab parallel to Edgware Road -------------
    const ang = Math.atan2(1395.4 - 1427, 2127.8 - 2099.7);
    const tower = rect(2117.5, 1434.0, 44, 17, ang);
    const TT = 87.0,
      H = 91;
    const TST = (TT - EH) / 20;
    for (const e of edgesOf(tower)) {
      B.quad(
        glass,
        [e.a[0], e.a[1], EH],
        [e.b[0], e.b[1], EH],
        [e.b[0], e.b[1], TT],
        [e.a[0], e.a[1], TT],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const n = Math.round(e.len / 1.25);
      for (let i = 0; i <= n; i++) {
        const corner = i === 0 || i === n;
        const s = (i * e.len) / n;
        ebox(
          conc,
          e,
          s - (corner ? 0.6 : 0.16),
          s + (corner ? 0.6 : 0.16),
          0,
          corner ? 0.6 : 0.42,
          EH,
          TT,
        );
      }
      for (let k = 0; k <= 20; k++)
        ebox(spand, e, 0, e.len, 0.02, 0.3, EH + k * TST - 0.5, EH + k * TST + 0.35);
    }
    kit.cornice(B, conc, tower, TT, { height: 1.2, projection: 0.4 });
    kit.cap(B, roofM, [[tower]], TT + 1.2);
    const crown = rect(2117.5, 1434.0, 32, 12, ang);
    prism(conc, crown, TT + 1.2, H, roofM);
    for (const e of edgesOf(crown)) ebox(dark, e, 1, e.len - 1, 0, 0.06, TT + 1.8, H - 0.8);
    return B.toGroup('hilton_london_metropole');
  },
};
