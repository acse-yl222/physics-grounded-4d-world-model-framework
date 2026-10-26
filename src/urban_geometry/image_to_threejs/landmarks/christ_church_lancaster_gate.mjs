// Tower and spire of Christ Church, Lancaster Gate (F. & H. Francis, 1855; Grade II).
// The church was demolished in 1977-78; only the tower and needle spire survive, wrapped
// on the north by Spire House, a 1983 block of flats (Covell Matthews Partnership) that
// fills the rest of the island site in the middle of Lancaster Gate.
export default {
  id: 'christ_church_lancaster_gate',
  name: 'Christ Church Lancaster Gate (tower and spire) and Spire House',
  claims: ['7f973bcd-f35a-44ce-b996-eb3092a2993f'],
  references: [
    {
      title: 'Tower and Spire of Christ Church, Lancaster Gate - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101275008-tower-and-spire-of-christ-church-lancaster-gate-ward',
      used_for:
        '1855 by F and H Francis; rubblestone with ashlar dressings; Geometrical/Decorated Gothic; recessed spire behind an openwork parapet linked to corner pinnacles by openwork flying buttresses',
    },
    {
      title: 'Tower and Spire of Christ Church - Historic England list entry 1275008',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1275008',
      used_for: 'listing of the surviving tower and spire',
    },
    {
      title: 'Lancaster Gate - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Lancaster_Gate',
      used_for:
        'asymmetrical gothic church with needle spire; demolition 1977; Spire House housing scheme 1983 on the rest of the site',
    },
    {
      title: 'Barrie House, Lancaster Gate, with Christ Church - RIBApix',
      url: 'https://www.architecture.com/image-library/RIBApix/licensed-image/poster/barrie-house-lancaster-gate-bayswater-london-seen-from-the-southeast-with-christ-church-lancaster-ga/posterid/RIBA64479.html',
      used_for: 'Spire House credited to Covell Matthews Partnership',
    },
  ],
  notes:
    'Spire height is not given by the sources found; the tip is modelled at ~62 m (tower 31 m + recessed octagonal spire), judged from its prominence over the 6-storey terraces. Spire House is modelled as a 5-storey buff-brick block with stone bands and a flat roof (materials and window pattern approximate). Tower placed on the Overture part polygon at the south end of the site.',
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
    const rag = kit.mat('#a39a86', { roughness: 0.95 }); // Kentish rag rubblestone
    const ash = kit.mat('#d6ccb2', { roughness: 0.85 }); // Bath-stone ashlar dressings
    const spireM = kit.mat('#b3a98f', { roughness: 0.9 });
    const louvre = kit.mat('#3a3631', { roughness: 0.9 });
    const brick = kit.mat('#b8a07a', { roughness: 0.92 });
    const roofM = kit.mat('#7e7c78');
    const winGlass = kit.mat('dark_glass');

    // --- tower -----------------------------------------------------------------
    const ang = Math.atan2(616.91 - 613.17, 1397.78 - 1384.71); // tower west->east face
    const tc = [1389.28, 621.86];
    const S = 9.4; // tower shaft side
    const TOP = 31; // parapet base
    const tring = rect(tc[0], tc[1], S, S, ang);
    prism(rag, tring, 0, TOP, ash);
    for (const z of [0, 7.5, 16.5, 23])
      kit.cornice(B, ash, tring, z, { height: z ? 0.45 : 0.9, projection: z ? 0.18 : 0.3 });
    kit.cornice(B, ash, tring, TOP - 0.6, { height: 0.6, projection: 0.35, steps: 2 });
    const tE = edgesOf(tring);
    // Angle buttresses (two per corner, set back in three stages).
    for (const e of tE) {
      for (const [s0, s1] of [
        [-0.05, 1.15],
        [e.len - 1.15, e.len + 0.05],
      ]) {
        ebox(rag, e, s0, s1, 0, 1.5, 0, 9);
        ebox(rag, e, s0 + 0.1, s1 - 0.1, 0, 1.0, 9, 18);
        ebox(rag, e, s0 + 0.2, s1 - 0.2, 0, 0.55, 18, 27);
        ebox(ash, e, s0, s1, 0, 1.6, 8.8, 9.2);
        ebox(ash, e, s0 + 0.1, s1 - 0.1, 0, 1.1, 17.8, 18.2);
      }
    }
    // Openings: west/south door, middle-stage lancets, paired belfry lancets.
    tE.forEach((e, i) => {
      if (i === 0) {
        // south (entrance) face: deep pointed doorway with a gabled hood
        kit.windowRow(B, e.a, e.b, 0.3, {
          count: 1,
          width: 2.4,
          height: 3.4,
          head: 'arch',
          glass: louvre,
          frame: ash,
          bars: 0,
          depth: 0.35,
          margin: 2,
        });
        ebox(ash, e, e.len / 2 - 2.1, e.len / 2 + 2.1, 0, 0.6, 0, 0.5);
        kit.windowRow(B, e.a, e.b, 9.6, {
          count: 1,
          width: 2.2,
          height: 4.6,
          head: 'arch',
          glass: winGlass,
          frame: ash,
          bars: 1,
          depth: 0.2,
          margin: 2,
        });
      } else {
        kit.windowRow(B, e.a, e.b, 10.5, {
          count: 1,
          width: 1.2,
          height: 3.6,
          head: 'arch',
          glass: winGlass,
          frame: ash,
          bars: 0,
          depth: 0.18,
          margin: 2,
        });
      }
      kit.windowRow(B, e.a, e.b, 18.2, {
        count: 1,
        width: 0.8,
        height: 1.6,
        head: 'arch',
        glass: louvre,
        frame: ash,
        bars: 0,
        margin: 2,
      });
      kit.windowRow(B, e.a, e.b, 23.8, {
        count: 2,
        width: 1.25,
        height: 4.8,
        head: 'arch',
        glass: louvre,
        frame: ash,
        bars: 2,
        depth: 0.25,
        margin: 2.4,
      });
      // clock-stage blind arcading band
      for (let k = 0; k < 7; k++) {
        const s = 1.6 + k * ((e.len - 3.2) / 6);
        ebox(ash, e, s - 0.08, s + 0.08, 0, 0.12, 21.2, 22.8);
      }
    });
    // Openwork parapet with quatrefoil-ish piercings (posts) and corner pinnacles.
    for (const e of tE) {
      ebox(ash, e, 0, e.len, -0.1, 0.3, TOP, TOP + 0.25);
      ebox(ash, e, 0, e.len, -0.1, 0.3, TOP + 1.35, TOP + 1.6);
      for (let k = 1; k < 12; k++)
        ebox(
          ash,
          e,
          (k * e.len) / 12 - 0.07,
          (k * e.len) / 12 + 0.07,
          -0.05,
          0.25,
          TOP + 0.25,
          TOP + 1.35,
        );
    }
    const corners = tring;
    const PIN = 8.0;
    for (const [x, y] of corners) {
      const d = Math.hypot(x - tc[0], y - tc[1]);
      const px = tc[0] + ((x - tc[0]) * (d - 0.2)) / d,
        py = tc[1] + ((y - tc[1]) * (d - 0.2)) / d;
      kit.box(B, ash, px, py, TOP - 1, 1.3, 1.3, 5.2, ang);
      for (const [dx, dy] of [
        [0.55, 0.55],
        [-0.55, 0.55],
        [0.55, -0.55],
        [-0.55, -0.55],
      ]) {
        const c = Math.cos(ang),
          s = Math.sin(ang);
        cyl(
          ash,
          px + dx * c - dy * s,
          py + dx * s + dy * c,
          TOP + 4.2,
          TOP + 5.6,
          0.18,
          0.02,
          4,
          ang + Math.PI / 4,
        );
      }
      cyl(ash, px, py, TOP + 4.2, TOP + PIN, 0.75, 0.03, 4, ang + Math.PI / 4);
      // openwork flying buttress from the pinnacle to the spire base
      const sx = tc[0] + (px - tc[0]) * 0.42,
        sy = tc[1] + (py - tc[1]) * 0.42;
      const L = Math.hypot(px - sx, py - sy);
      const h0 = TOP + 2.6,
        h1 = TOP + 5.2;
      const slope = Math.atan2(h1 - h0, L);
      const g = new THREE.BoxGeometry(Math.hypot(L, h1 - h0), 0.28, 0.35);
      const M = new THREE.Matrix4()
        .makeRotationZ(Math.atan2(sy - py, sx - px))
        .multiply(new THREE.Matrix4().makeRotationY(-slope));
      M.setPosition((px + sx) / 2, (py + sy) / 2, (h0 + h1) / 2);
      B.addGeometry(ash, g, M);
      g.dispose();
    }
    // Recessed octagonal needle spire with three tiers of lucarnes and bands.
    const SB = TOP + 0.3,
      TIP = 62;
    const R0 = 3.6;
    cyl(rag, tc[0], tc[1], TOP, SB + 1.2, R0 + 0.15, R0, 8, ang + Math.PI / 8);
    cyl(spireM, tc[0], tc[1], SB + 1.2, TIP, R0, 0.12, 8, ang + Math.PI / 8);
    const rAt = (z) => R0 + ((0.12 - R0) * (z - SB - 1.2)) / (TIP - SB - 1.2);
    for (const z of [42, 50.5])
      cyl(
        ash,
        tc[0],
        tc[1],
        z,
        z + 0.35,
        rAt(z) + 0.12,
        rAt(z + 0.35) + 0.12,
        8,
        ang + Math.PI / 8,
      );
    for (const [z, w, h] of [
      [SB + 2, 1.5, 2.6],
      [40, 1.0, 1.8],
      [48.5, 0.7, 1.3],
    ]) {
      for (let q = 0; q < 4; q++) {
        const a = ang + (q * Math.PI) / 2 - Math.PI / 2;
        const r = rAt(z + h / 2) + 0.1;
        const x = tc[0] + Math.cos(a) * r,
          y = tc[1] + Math.sin(a) * r;
        kit.box(B, ash, x, y, z, w, 0.6, h, a + Math.PI / 2);
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
        // little gable over each lucarne
        const g = new THREE.CylinderGeometry(w * 0.62, w * 0.62, 0.6, 3, 1).rotateX(Math.PI / 2);
        g.scale(1, 0.55, 1);
        const M = new THREE.Matrix4()
          .makeRotationZ(a + Math.PI / 2)
          .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
        M.setPosition(x, y, z + h + w * 0.16);
        B.addGeometry(ash, g, M);
        g.dispose();
      }
    }
    // finial and cross
    cyl(kit.mat('bronze'), tc[0], tc[1], TIP - 0.2, TIP + 0.6, 0.18, 0.12, 6);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 0.6, 0.12, 0.12, 1.6, ang);
    kit.box(B, kit.mat('bronze'), tc[0], tc[1], TIP + 1.5, 0.9, 0.12, 0.12, ang);

    // --- Spire House (1983 flats) ---------------------------------------------------
    const flats = [
      [1372.2, 655.5],
      [1380.7, 626.8],
      [1393.9, 630.6],
      [1397.8, 616.9],
      [1408.1, 619.9],
      [1403.6, 635.0],
      [1397.9, 633.3],
      [1396.6, 637.7],
      [1406.9, 640.7],
      [1399.0, 667.3],
      [1388.5, 664.2],
      [1389.6, 660.7],
    ];
    const ST = 3.0,
      NS = 5,
      H = NS * ST + 0.6;
    prism(brick, flats, 0, H, roofM);
    kit.cornice(B, ash, flats, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(B, ash, flats, ST - 0.2, { height: 0.3, projection: 0.1 });
    kit.cornice(B, ash, flats, H - 0.5, { height: 0.5, projection: 0.2 });
    punched(
      flats,
      0.9,
      NS,
      ST,
      (s) => ({
        width: s === 0 ? 1.6 : 1.3,
        height: s === 0 ? 1.8 : 1.6,
        bay: 3.2,
        head: 'segment',
        frame: kit.mat('white'),
        sill: ash,
        bars: 1,
      }),
      (e) => e.len > 3.5,
    );
    // roof plant and lift overrun
    kit.box(B, roofM, 1398, 652, H, 6, 4, 2.2, ang);
    kit.box(B, roofM, 1392, 640, H, 3, 3, 1.5, ang);

    const g = B.toGroup('christ_church_lancaster_gate');
    return g;
  },
};
