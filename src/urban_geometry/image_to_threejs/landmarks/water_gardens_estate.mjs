// The Water Gardens, Burwood Place / Edgware Road (Trehearne, Norman, Preston & Partners
// for the Church Commissioners, 1961-66; landscape by Philip Hicks). Three 17-storey
// towers, a lower block and a terrace around a garden suspended on a raised podium deck
// over basement garaging - split levels, strong horizontals, rocks, willows and falling
// water - with a parade of shops along Edgware Road. The landscape is Grade II registered.
export default {
  id: 'water_gardens_estate',
  name: 'The Water Gardens',
  claims: [
    '14ee681a-edad-431a-93e4-ba234d230274',
    'caddc3d5-7d8c-487d-a8ee-4bf966a5d05a',
    '92691686-02ca-4bfb-a61a-5ba5608586a8',
    'bbad4679-1234-44cf-a9ac-01bc6344ae22',
    '45486ea2-b6e9-43dd-b2e2-20eec9b6c5e2',
    'cfc2d9a3-630b-4ef4-b9fd-b55a080b473d',
    '29ec0926-9253-4b4c-96e9-aff1a5979383',
    '3ac28727-1fe8-4623-ac16-1663c535a646',
    '717c0cfd-c9cd-4752-a150-1ec4eeeca562',
    'b3c1b47d-59e3-415c-8458-be35fce2c51d',
    '21781a84-81d5-4629-842f-a2b3a258fb8d',
  ],
  references: [
    {
      title: 'The Water Gardens, Burwood Place - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Water_Gardens,_Burwood_Place',
      used_for:
        'architects Trehearne and Norman, Preston and Partners; landscape by Philip Hicks; registered 2020',
    },
    {
      title: 'The Water Gardens (Westminster) - London Gardens Trust',
      url: 'https://www.londongardenstrust.org/inventory/site-record/?ID=WST136',
      used_for:
        '1961-66; three 17-storey towers, smaller blocks and a terrace of houses around communal gardens on a raised podium deck over basement garaging; rocks, willows and falling water; split levels and strong horizontals',
    },
    {
      title: 'The Water Gardens - New London Architecture',
      url: 'https://nla.london/projects/the-water-gardens',
      used_for: '5,000 sqm podium deck, two-thirds covered by water; 2018 refurbishment',
    },
    {
      title: 'The Water Gardens W2 - National Garden Scheme',
      url: 'https://ngs.org.uk/gardens/the-water-gardens-w2',
      used_for: 'Grade II listed gardens and ponds',
    },
  ],
  notes:
    'Tower facades (brown brick piers with continuous white balcony slabs on the long faces) and the 5-storey block treatment are approximate. The water-garden deck outline is reconstructed west of the towers (no footprint) with deck level ~2.4 m; pool shapes, stepping stones and the willows (silver birch asset as stand-in) are schematic. The Heron and Norfolk Crescent are not part of this module.',
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
    const brick = kit.mat('#7d5a45', { roughness: 0.92 });
    const conc = kit.mat('#e4e0d6', { roughness: 0.8 });
    const glass = kit.mat('#34454f', { roughness: 0.12, metalness: 0.35 });
    const dark = kit.mat('dark_steel');
    const water = kit.mat('#46707f', { roughness: 0.08, metalness: 0.2 });
    const paving = kit.mat('#c9c3b5', { roughness: 0.9 });
    const rock = kit.mat('#8f887c', { roughness: 1 });
    const roofM = kit.mat('#8a8984');
    const shop = kit.mat('#2f3940', { roughness: 0.15, metalness: 0.3, emissive: '#1a160c' });
    const fascia = kit.mat('#3b3f44', { roughness: 0.6 });
    const R = kit.rng(4711);
    const base = ctx.byId['14ee681a-edad-431a-93e4-ba234d230274'];
    const parts = base.parts.map((p) => ({ ring: ccw(p.polys[0][0]), h: p.h }));

    // --- towers -------------------------------------------------------------------
    const DECK = 4.0,
      ST = 3.05,
      N = 17,
      TOPW = DECK + N * ST;
    for (const id of [
      '92691686-02ca-4bfb-a61a-5ba5608586a8',
      'bbad4679-1234-44cf-a9ac-01bc6344ae22',
      '45486ea2-b6e9-43dd-b2e2-20eec9b6c5e2',
    ]) {
      const ring = ringOf(id);
      const E = edgesOf(ring);
      // entrance level (glazed lobby under the first floor)
      for (const e of E) {
        B.quad(
          dark,
          [e.a[0], e.a[1], 0],
          [e.b[0], e.b[1], 0],
          [e.b[0], e.b[1], DECK],
          [e.a[0], e.a[1], DECK],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        ebox(glass, e, 1, e.len - 1, 0.01, 0.05, 0.2, DECK - 0.4);
      }
      for (const e of E) {
        const long = e.len > 18;
        B.quad(
          long ? glass : brick,
          [e.a[0], e.a[1], DECK],
          [e.b[0], e.b[1], DECK],
          [e.b[0], e.b[1], TOPW],
          [e.a[0], e.a[1], TOPW],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        if (long) {
          // brick piers between window bays, white balcony slabs with railings
          const n = Math.round(e.len / 3.4);
          for (let i = 0; i <= n; i++)
            ebox(
              brick,
              e,
              (i * e.len) / n - (i % n ? 0.3 : 1.2),
              (i * e.len) / n + (i % n ? 0.3 : 1.2),
              0,
              0.3,
              DECK,
              TOPW,
            );
          for (let k = 1; k <= N; k++) {
            const z = DECK + k * ST;
            ebox(conc, e, 1.2, e.len - 1.2, 0, 1.5, z - 0.22, z);
            if (k < N) ebox(dark, e, 1.2, e.len - 1.2, 1.42, 1.5, z, z + 1.0);
          }
          for (let k = 0; k < N; k++)
            ebox(conc, e, 1.2, e.len - 1.2, 0.02, 0.12, DECK + k * ST + 0.95, DECK + k * ST + 1.05);
        } else {
          for (let k = 0; k < N; k++)
            kit.windowRow(B, e.a, e.b, DECK + k * ST + 0.9, {
              count: 2,
              width: 0.8,
              height: 1.5,
              glass,
              frame: conc,
              sill: conc,
              head: 'none',
              bars: 0,
              margin: 3,
            });
        }
      }
      kit.cornice(B, conc, ring, TOPW, { height: 0.8, projection: 0.3 });
      kit.cap(B, roofM, [[ring]], TOPW + 0.8);
      const f = kit.ringFrame(ring);
      prism(brick, rect(f.cx, f.cy, 9, 6, f.angle), TOPW + 0.8, 58.4, roofM);
    }

    // --- shop parade along Edgware Road and the podium deck --------------------------
    const roads = roadSegs(['Edgware Road']);
    for (const p of parts) {
      if (p.h > 50) continue; // tower volumes handled above
      const H = p.h > 8 ? 10.4 : DECK;
      prism(H > 8 ? conc : paving, p.ring, 0, H, roofM);
      for (const e of edgesOf(p.ring)) {
        if (e.len < 3) continue;
        const front = facesRoad(e, roads, 30);
        if (front || H > 8) {
          ebox(shop, e, 0.3, e.len - 0.3, 0.01, 0.05, 0.2, 3.4);
          ebox(fascia, e, 0, e.len, 0, 0.25, 3.4, 4.1);
          const n = Math.max(1, Math.round(e.len / 5.5));
          for (let i = 0; i <= n; i++)
            ebox(conc, e, (i * e.len) / n - 0.25, (i * e.len) / n + 0.25, 0, 0.3, 0, 3.4);
        }
        if (H > 8)
          kit.windowRow(B, e.a, e.b, 5.2, {
            bay: 2.4,
            width: 1.6,
            height: 1.5,
            glass,
            frame: dark,
            sill: conc,
            head: 'none',
            bars: 0,
          });
        if (H > 8)
          kit.windowRow(B, e.a, e.b, 7.9, {
            bay: 2.4,
            width: 1.6,
            height: 1.5,
            glass,
            frame: dark,
            sill: conc,
            head: 'none',
            bars: 0,
          });
      }
      if (H > 8) kit.cornice(B, conc, p.ring, H - 0.5, { height: 0.5, projection: 0.25 });
      else kit.cornice(B, conc, p.ring, DECK, { height: 1.0, projection: 0.15 });
    }
    // individual shop units mapped separately on Edgware Road: same parade treatment
    for (const id of [
      'cfc2d9a3-630b-4ef4-b9fd-b55a080b473d',
      '29ec0926-9253-4b4c-96e9-aff1a5979383',
      '3ac28727-1fe8-4623-ac16-1663c535a646',
      '717c0cfd-c9cd-4752-a150-1ec4eeeca562',
      'b3c1b47d-59e3-415c-8458-be35fce2c51d',
      '21781a84-81d5-4629-842f-a2b3a258fb8d',
    ]) {
      const ring = ringOf(id);
      prism(conc, ring, 0, 10.3, roofM);
      for (const e of edgesOf(ring)) {
        if (e.len < 3 || !facesRoad(e, roads, 30)) continue;
        ebox(shop, e, 0.3, e.len - 0.3, 0.01, 0.05, 0.2, 3.4);
        ebox(fascia, e, 0, e.len, 0, 0.25, 3.4, 4.1);
        kit.windowRow(B, e.a, e.b, 5.2, {
          bay: 2.4,
          width: 1.6,
          height: 1.5,
          glass,
          frame: dark,
          sill: conc,
          head: 'none',
          bars: 0,
        });
        kit.windowRow(B, e.a, e.b, 7.9, {
          bay: 2.4,
          width: 1.6,
          height: 1.5,
          glass,
          frame: dark,
          sill: conc,
          head: 'none',
          bars: 0,
        });
      }
    }

    // --- 5-storey block (flats 301-396) -------------------------------------------
    {
      const ring = ringOf('caddc3d5-7d8c-487d-a8ee-4bf966a5d05a');
      const H = 16.9;
      prism(brick, ring, 0, H, roofM);
      for (const e of edgesOf(ring)) {
        if (e.len < 6) continue;
        for (let k = 1; k <= 5; k++)
          ebox(conc, e, 0.5, e.len - 0.5, 0, k < 5 ? 1.2 : 0.3, k * 3.2 - 0.2, k * 3.2);
        for (let k = 1; k < 5; k++)
          ebox(dark, e, 0.5, e.len - 0.5, 1.12, 1.2, k * 3.2, k * 3.2 + 1.0);
      }
      punched(
        ring,
        0.9,
        5,
        3.2,
        {
          bay: 3.0,
          width: 2.0,
          height: 1.8,
          glass,
          frame: conc,
          sill: conc,
          head: 'none',
          bars: 1,
        },
        (e) => e.len > 5,
      );
      kit.cornice(B, conc, ring, H - 0.6, { height: 0.6, projection: 0.3 });
    }

    // --- the water garden on its podium deck ----------------------------------------
    {
      const DZ = 2.4;
      const deck = ccw([
        [2264, 1227],
        [2246, 1207],
        [2268, 1181],
        [2300, 1168],
        [2336, 1161],
        [2346, 1160],
        [2306, 1196],
        [2276, 1228],
      ]);
      kit.walls(B, paving, [[deck]], 0, DZ, { bay: 1e6 });
      kit.cornice(B, conc, deck, DZ, { height: 0.9, projection: 0.15 });
      // pools covering about two thirds of the deck, at split levels with cascades
      const pools = [
        [
          [2258, 1210],
          [2270, 1196],
          [2286, 1204],
          [2276, 1218],
        ],
        [
          [2275, 1192],
          [2298, 1180],
          [2306, 1190],
          [2290, 1203],
        ],
        [
          [2302, 1176],
          [2332, 1166],
          [2338, 1168],
          [2312, 1188],
        ],
      ].map(ccw);
      kit.cap(B, paving, [[deck, ...pools.map((p) => kit.offsetRing(p, 0.35).reverse())]], DZ);
      pools.forEach((p, i) => {
        const z = DZ - 0.25 - i * 0.35;
        kit.cap(B, water, [[p]], z);
        kit.walls(B, conc, [[kit.offsetRing(p, 0.35).reverse()]], z - 0.1, DZ, { bay: 1e6 });
        kit.cap(B, conc, [[kit.offsetRing(p, 0.35), p.slice().reverse()]], z - 0.02);
        // cascade lip to the next pool
        const e = edgesOf(p)[1];
        ebox(conc, e, e.len * 0.35, e.len * 0.65, -0.1, 0.4, z, z + 0.3);
        ebox(
          kit.mat('#bcd6de', { roughness: 0.1 }),
          e,
          e.len * 0.37,
          e.len * 0.63,
          0.4,
          0.5,
          z - 0.35,
          z + 0.3,
        );
        // stepping stones and rocks
        for (let k = 0; k < 6; k++) {
          const t = (k + 0.5) / 6;
          const c = [p[0][0] + (p[2][0] - p[0][0]) * t, p[0][1] + (p[2][1] - p[0][1]) * t];
          kit.box(B, paving, c[0], c[1], z, 1.4, 1.4, 0.35, 0.6);
          if (R() < 0.5)
            kit.box(
              B,
              rock,
              c[0] + 2.5 * (R() - 0.5),
              c[1] + 2.5 * (R() - 0.5),
              z,
              1.2 + R(),
              0.9 + R(),
              0.6 + R() * 0.8,
              R() * 3,
            );
        }
      });
      const g = B.toGroup('water_gardens_estate');
      if (ctx.placeAssets) {
        const trees = [
          [2262, 1220],
          [2281, 1188],
          [2289, 1216],
          [2318, 1176],
          [2340, 1163],
          [2252, 1205],
        ].map(([x, y]) => [x, y, R() * 6]);
        g.add(ctx.placeAssets('silver_birch', trees, { z: DZ, scaleOf: () => 10 + R() * 3 }));
      }
      return g;
    }
  },
};
