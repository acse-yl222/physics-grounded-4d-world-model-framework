// Porchester Hall and the Porchester Centre (Porchester Spa), Queensway / Porchester Road
// (Grade II*). Paddington borough architect Herbert Shepherd built the baths, pools and
// laundry along Queensway in 1923-25; with H. A. Thomerson he extended it in 1927-29 with
// the Turkish baths (Porchester Spa), a public library and the assembly rooms of
// Porchester Hall fronting Porchester Road. Steel frame faced in Portland stone and red,
// purple and stock brick.
export default {
  id: 'porchester_hall',
  name: 'Porchester Hall and Porchester Centre',
  claims: ['af877570-0c6e-4d31-a260-6089f7a6e397', 'fdb74a09-944b-498f-91a1-ab0b195d2a9b'],
  references: [
    {
      title: 'Porchester Hall - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Porchester_Hall',
      used_for:
        '1923-25 by Herbert Shepherd; 1927-29 extension with Thomerson adding Turkish baths, library and assembly rooms',
    },
    {
      title: 'Porchester Centre listing - British Listed Buildings 1262987',
      url: 'https://britishlistedbuildings.co.uk/101262987',
      used_for:
        'steel frame with Portland stone and red, purple and stock brick; earliest part along Queensway, 1927-29 part fronting Porchester Road; wedge-shaped plot',
    },
    {
      title: 'The Porchester Spa - Time Out',
      url: 'https://www.timeout.com/london/health-and-beauty/the-porchester-spa',
      used_for: 'spa opened 1929',
    },
    {
      title: 'Porchester baths interior - Historic England DP052718',
      url: 'https://historicengland.org.uk/images-books/photos/item/DP052718',
      used_for: 'top-lit pool hall (roof lantern over the baths)',
    },
  ],
  notes:
    'Facade composition (stone ground storey and giant pilasters on the Porchester Road front, brick upper storeys with stone bands, arched ground-floor windows on Queensway) is a simplified reconstruction; the pool-hall roof lanterns are schematic. Heights from Overture (12.7 m) plus parapets.',
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
    const stone = kit.mat('#e0d8c6', { roughness: 0.8 });
    const red = kit.mat('#8e4a3a', { roughness: 0.92 });
    const purple = kit.mat('#6e4a4d', { roughness: 0.92 });
    const glass = kit.mat('#2f3d45', { roughness: 0.2, metalness: 0.3 });
    const lantern = kit.mat('#8aa0aa', { roughness: 0.1, metalness: 0.3 });
    const roofM = kit.mat('#86837d');
    const slate = kit.mat('slate');
    const roads = roadSegs([
      'Porchester Road',
      'Queensway',
      'Bishops Bridge Road',
      "Bishop's Bridge Road",
    ]);

    // --- baths, laundry and library (Porchester Centre) ---------------------------
    const centre = ringOf('fdb74a09-944b-498f-91a1-ab0b195d2a9b');
    const H1 = 12.7;
    prism(red, centre, 0, H1, roofM);
    kit.cornice(B, stone, centre, 0, { height: 1.0, projection: 0.15 });
    kit.cornice(B, stone, centre, 4.6, { height: 0.4, projection: 0.15 });
    kit.cornice(B, stone, centre, H1 - 1.2, { height: 0.6, projection: 0.4, steps: 2 });
    for (const e of edgesOf(centre)) {
      if (e.len < 6) continue;
      const front = facesRoad(e, roads, 30);
      if (front) {
        ebox(stone, e, 0, e.len, 0, 0.12, 0, 4.6);
        kit.windowRow(B, e.a, e.b, 1.3, {
          bay: 4.4,
          width: 2.0,
          height: 2.4,
          head: 'arch',
          glass,
          frame: stone,
          sill: stone,
          bars: 1,
          depth: 0.2,
        });
        kit.windowRow(B, e.a, e.b, 6.0, {
          bay: 4.4,
          width: 1.6,
          height: 3.4,
          head: 'lintel',
          glass,
          frame: kit.mat('white'),
          sill: stone,
          bars: 2,
          surround: 0.25,
          surroundMat: stone,
        });
        // brick piers in purple brick between bays
        const n = Math.round(e.len / 4.4);
        for (let i = 0; i <= n; i++)
          ebox(
            purple,
            e,
            0.6 + ((e.len - 1.2) * i) / n - 0.35,
            0.6 + ((e.len - 1.2) * i) / n + 0.35,
            0,
            0.15,
            5.0,
            H1 - 1.2,
          );
      } else {
        kit.windowRow(B, e.a, e.b, 6.0, {
          bay: 5.5,
          width: 1.4,
          height: 2.6,
          head: 'segment',
          glass,
          frame: kit.mat('white'),
          sill: stone,
          bars: 1,
        });
      }
    }
    // stone parapet with a coping
    kit.walls(B, stone, [[centre]], H1, H1 + 1.0, { bay: 1e6 });
    kit.cornice(B, stone, centre, H1 + 1.0, { height: 0.2, projection: 0.1 });
    // top-lit pool halls: two pitched glazed lanterns over the baths
    for (const [cx, cy] of [
      [775, 1188],
      [791, 1203],
    ]) {
      const r = rect(cx, cy, 30, 9, 0.39);
      kit.pitchedRoof(B, slate, red, r, 0.39, H1, 3.2, 'gabled', { overhang: 0.2 });
      const lr = rect(cx, cy, 24, 2.6, 0.39);
      prism(lantern, lr, H1 + 2.4, H1 + 4.1, slate);
      const LE = edgesOf(lr);
      for (const e of [LE[0], LE[2]]) {
        const n = Math.round(e.len / 1.2);
        for (let i = 0; i <= n; i++)
          ebox(
            kit.mat('dark_steel'),
            e,
            (i * e.len) / n - 0.04,
            (i * e.len) / n + 0.04,
            0,
            0.06,
            H1 + 2.4,
            H1 + 4.1,
          );
      }
    }

    // --- Porchester Hall (assembly rooms), stone front to Porchester Road ------------
    const hall = ringOf('af877570-0c6e-4d31-a260-6089f7a6e397');
    const H2 = 12.7;
    prism(red, hall, 0, H2, roofM);
    kit.cornice(B, stone, hall, 0, { height: 1.0, projection: 0.15 });
    const mainFront = edgesOf(hall)
      .filter((e) => facesRoad(e, roads, 30))
      .sort((p, q) => q.len - p.len)[0];
    for (const e of edgesOf(hall)) {
      if (e.len < 8) continue;
      if (!facesRoad(e, roads, 30)) {
        kit.windowRow(B, e.a, e.b, 5.5, {
          bay: 4.5,
          width: 1.5,
          height: 3.0,
          head: 'arch',
          glass,
          frame: kit.mat('white'),
          sill: stone,
          bars: 1,
        });
        continue;
      }
      // Portland stone face: rusticated ground storey, giant pilasters, tall windows
      ebox(stone, e, -0.2, e.len + 0.2, 0, 0.35, 0, H2 + 1.2);
      for (let z = 0.9; z < 4.6; z += 0.6) ebox(stone, e, 0, e.len, 0.35, 0.42, z, z + 0.08);
      const n = Math.max(3, Math.round(e.len / 4.0));
      for (let i = 0; i <= n; i++) {
        const s = 0.8 + ((e.len - 1.6) * i) / n;
        ebox(stone, e, s - 0.4, s + 0.4, 0.35, 0.75, 4.6, H2 - 1.6);
        ebox(stone, e, s - 0.55, s + 0.55, 0.35, 0.85, H2 - 1.9, H2 - 1.5);
      }
      kit.windowRow(B, e.a, e.b, 1.5, {
        count: n,
        width: 1.6,
        height: 2.2,
        head: 'segment',
        glass,
        frame: stone,
        sill: stone,
        bars: 1,
        depth: 0.5,
        margin: 0.8,
      });
      kit.windowRow(B, e.a, e.b, 5.6, {
        count: n,
        width: 1.7,
        height: 4.0,
        head: 'arch',
        glass,
        frame: kit.mat('white'),
        sill: stone,
        bars: 2,
        depth: 0.5,
        margin: 0.8,
      });
      // central entrance with steps and a canopy
      const m = e.len / 2;
      if (mainFront && e.k === mainFront.k)
        ebox(kit.mat('#3a2f27'), e, m - 1.6, m + 1.6, 0.4, 0.5, 0.4, 3.6);
      if (mainFront && e.k === mainFront.k) {
        ebox(stone, e, m - 2.6, m + 2.6, 0.35, 2.2, 0, 0.35);
        ebox(stone, e, m - 2.2, m + 2.2, 0.35, 1.6, 3.9, 4.3);
      }
      ebox(stone, e, 0, e.len, 0.35, 1.0, H2 - 1.5, H2 - 0.8);
      ebox(stone, e, 0, e.len, 0.35, 0.6, H2 - 0.8, H2 + 1.2);
    }
    kit.cornice(B, stone, hall, H2 - 1.2, { height: 0.6, projection: 0.4, steps: 2 });
    kit.walls(B, stone, [[hall]], H2, H2 + 1.0, { bay: 1e6 });
    // assembly hall roof: shallow hipped slate roof over the main hall
    const f = kit.ringFrame(hall);
    kit.pitchedRoof(
      B,
      slate,
      red,
      rect(f.cx, f.cy, f.length * 0.65, f.width * 0.6, f.angle),
      f.angle,
      H2,
      3.0,
      'hipped',
      { overhang: 0.2 },
    );
    return B.toGroup('porchester_hall');
  },
};
