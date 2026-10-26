// One Hyde Park, 100 Knightsbridge (Rogers Stirk Harbour + Partners, 2007-11). Four
// linked residential pavilions, elongated hexagons in plan (wider in the middle, tapering
// to the park and Knightsbridge ends), rising in two-storey steps from 10 storeys at the
// west to 14 at the peak and 12 at the east. Transparent circulation cores (glazed lifts
// and stairs) link the pavilions; white concrete frame, glass and copper - the side
// elevations carry hand-finished copper privacy fins. Retail podium on Knightsbridge.
export default {
  id: 'one_hyde_park',
  name: 'One Hyde Park',
  claims: ['487b2885-f959-4021-baa2-9e6c14686a3f'],
  references: [
    {
      title: 'One Hyde Park by Rogers Stirk Harbour + Partners - Dezeen',
      url: 'https://www.dezeen.com/2011/02/10/one-hyde-park-by-rogers-stirk-harbour-partners/amp/',
      used_for:
        'four linked towers of differing heights, plans wider in the middle tapering to the ends, duplex penthouses',
    },
    {
      title: 'One Hyde Park - World Construction Network',
      url: 'https://www.worldconstructionnetwork.com:443/projects/one-hyde-park',
      used_for:
        'two-storey steps: 10 storeys west, 14 at the peak, 12 east; glazed circulation cores; view corridor',
    },
    {
      title: 'One Hyde Park - Permasteelisa Group',
      url: 'https://www.permasteelisagroup.com/historic-project/one-hyde-park/',
      used_for: 'unitised cladding, hand-painted solid copper privacy fins on the side elevations',
    },
    {
      title: 'First impressions: Rogers One Hyde Park - Building',
      url: 'https://building.co.uk/careers/first-impressions-rogers-one-hyde-park/5016080.article',
      used_for: 'white concrete frame, glass and copper palette',
    },
  ],
  notes:
    'Pavilion outlines are cut from the single Overture footprint (four hexagons plus link cores). Storeys ' +
    'per pavilion (west to east 10, 12, 14, 12 + ground) follow the WCN description; the assignment of the ' +
    'peak to the third pavilion, the 3.5 m storey, the fin pitch and the external white column/bracing ' +
    'pattern are approximations. Ground-floor retail on the Knightsbridge end is generic.',
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
    const white = kit.mat('#e9e7e1', { roughness: 0.7 });
    const copper = kit.mat('#a5683f', { roughness: 0.55, metalness: 0.55 });
    const glass = kit.mat('#4a5d68', { roughness: 0.1, metalness: 0.45 });
    const cgl = kit.mat('#9db3bc', { roughness: 0.08, metalness: 0.3 });
    const steel = kit.mat('#d5d8da', { roughness: 0.4, metalness: 0.6 });
    const roofM = kit.mat('#8f908c');
    const shop = kit.mat('#2a3138', { roughness: 0.2, metalness: 0.3 });

    // Pavilion hexagons, west to east (from the Overture outline).
    const pav = [
      [
        [2664, -515],
        [2674, -515],
        [2680, -493],
        [2680, -481],
        [2671, -460],
        [2661, -461],
        [2655, -481],
        [2655, -494],
      ],
      [
        [2697, -513],
        [2706, -512],
        [2711, -490],
        [2710, -478],
        [2700, -457],
        [2690, -458],
        [2685, -480],
        [2687, -493],
      ],
      [
        [2728, -508],
        [2738, -507],
        [2741, -486],
        [2739, -473],
        [2729, -455],
        [2719, -456],
        [2716, -477],
        [2718, -489],
      ],
      [
        [2759, -501],
        [2768, -499],
        [2770, -479],
        [2768, -466],
        [2756, -449],
        [2747, -451],
        [2745, -472],
        [2748, -484],
      ],
    ].map(ccw);
    const storeys = [10, 12, 14, 12];
    const G = 5.0,
      ST = 3.5;
    pav.forEach((ring, i) => {
      const n = storeys[i];
      const top = G + n * ST;
      const inner = kit.offsetRing(ring, -0.5);
      // glazed volume set back behind the slab edges
      kit.walls(batch, glass, [[inner]], 0, top);
      kit.cap(batch, roofM, [[ring]], top + 0.6);
      kit.walls(batch, white, [[ring]], top, top + 0.6);
      for (const e of edges(ring)) {
        if (e.len < 1) continue;
        const side = Math.abs(e.dx) < 0.55; // long, nearly north-south side faces
        const end = !side;
        // slab edges
        for (let f = 0; f <= n; f++) {
          const z = G + f * ST;
          ebox(white, e, 0, e.len, -0.5, end ? 1.4 : 0.1, z - 0.35, z);
        }
        // ground floor: retail glazing on the Knightsbridge (south) end, lobby elsewhere
        ebox(e.ny < 0 && end ? shop : glass, e, 0.3, e.len - 0.3, -0.6, -0.5, 0, G - 0.4);
        // white columns at the corners
        ebox(white, e, 0, 0.7, -0.5, 0.25, 0, top);
        if (side) {
          // copper privacy fins on the side elevations
          const nf = Math.floor(e.len / 0.9);
          for (let k = 1; k < nf; k++) {
            const s = (k * e.len) / nf;
            ebox(copper, e, s - 0.06, s + 0.06, -0.45, 0.5, G, top);
          }
        } else {
          // end elevations: balcony balustrades of glass with steel rails, vertical mullions
          for (let f = 1; f <= n; f++) {
            const z = G + f * ST;
            ebox(cgl, e, 0.4, e.len - 0.4, 1.3, 1.36, z, z + 1.1);
            ebox(steel, e, 0.4, e.len - 0.4, 1.28, 1.4, z + 1.1, z + 1.16);
          }
          const nm = Math.max(2, Math.round(e.len / 1.6));
          for (let k = 1; k < nm; k++) {
            const s = (k * e.len) / nm;
            ebox(steel, e, s - 0.04, s + 0.04, -0.5, -0.38, G, top);
          }
          // external cross-bracing on the ends (steel rods)
          for (let f = 0; f < n; f += 2) {
            const z0 = G + f * ST,
              z1 = z0 + 2 * ST;
            const p = at(e, 0.4, 0.9),
              q = at(e, e.len - 0.4, 0.9);
            for (const [a, b] of [
              [
                [p[0], p[1], z0],
                [q[0], q[1], z1],
              ],
              [
                [q[0], q[1], z0],
                [p[0], p[1], z1],
              ],
            ]) {
              const dx = b[0] - a[0],
                dy = b[1] - a[1],
                dz = b[2] - a[2];
              const L = Math.hypot(dx, dy, dz);
              const rod = new THREE.CylinderGeometry(0.06, 0.06, L, 5);
              const m = new THREE.Matrix4().makeRotationFromQuaternion(
                new THREE.Quaternion().setFromUnitVectors(
                  new THREE.Vector3(0, 1, 0),
                  new THREE.Vector3(dx / L, dy / L, dz / L),
                ),
              );
              m.setPosition((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
              batch.addGeometry(steel, rod, m);
              rod.dispose();
            }
          }
        }
      }
      // rooftop plant enclosure (penthouse level set back)
      const pr = kit.offsetRing(ring, -3);
      if (kit.ringArea(pr) > 20) prism(steel, pr, top + 0.6, top + 2.8, roofM);
    });

    // Link cores between the pavilions (glazed lift and stair towers).
    const links = [
      [2650, 2655, -495, -481, 10],
      [2680, 2685, -494, -481, 10],
      [2711, 2716, -490, -476, 12],
      [2741, 2745, -487, -474, 12],
      [2770, 2775, -479, -464, 12],
    ];
    for (const [x0, x1, y0, y1, n] of links) {
      const ring = [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
      ];
      const top = G + (n + 1) * ST;
      prism(cgl, ring, 0, top, roofM);
      for (const e of edges(ring)) {
        ebox(white, e, 0, 0.3, -0.3, 0, 0, top);
        for (let f = 0; f <= n + 1; f++)
          ebox(white, e, 0, e.len, -0.3, 0.05, G + f * ST - 0.25, G + f * ST);
      }
      // lift car in the glazed shaft
      kit.box(batch, steel, (x0 + x1) / 2, (y0 + y1) / 2, G + 3 * ST, 1.6, 1.6, 2.4);
    }
    g.add(batch.toGroup('one_hyde_park'));
    return g;
  },
};
