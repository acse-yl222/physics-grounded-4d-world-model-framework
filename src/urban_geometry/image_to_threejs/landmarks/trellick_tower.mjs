// Trellick Tower, Golborne Road / Cheltenham Estate, North Kensington
// (Erno Goldfinger, 1968-72). 31-storey bush-hammered concrete slab with a
// separate slender lift/service tower at its north-west end, joined to the
// slab's access corridors by enclosed bridges at every third storey and
// crowned by the cantilevered boiler house. Deep recessed balconies lined with
// cedar boarding give the long elevations their chequered depth.
export default {
  id: 'trellick_tower',
  name: 'Trellick Tower',
  claims: ['e4024000-21e9-4920-ac2d-767c6cb60fdd', 'a0522042-7936-4c38-8523-883efe042e67'],
  references: [
    {
      title: 'Trellick Tower - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Trellick_Tower',
      used_for: '31 storeys, 98 m roof height, separate service tower, Goldfinger 1972',
    },
    {
      title: 'Trellick Tower - Designing Buildings',
      url: 'https://www.designingbuildings.co.uk/wiki/Trellick_Tower',
      used_for: 'bridge-like walkways every third floor linking slab and service tower',
    },
    {
      title: 'Trellick and Edenham listed status (RBKC)',
      url: 'https://www.rbkc.gov.uk/pdf/Trellick%20and%20Edenham%20listed%20status.pdf',
      used_for: 'bush-hammered in-situ concrete, pebble-finished panels, timber-clad balconies',
    },
    {
      title: 'The future passed: Trellick Tower at 50 - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/blog/the-future-passed-the-trellick-tower-at-50',
      used_for: 'deep recessed cedar-lined balconies; boiler house projecting like a ship bridge',
    },
  ],
  notes:
    'Slab and service tower from the Overture footprints; slab roof 92 m, boiler house top 98 m (reference ' +
    'roof height). Facade rhythm (two flat storeys + corridor storey per 3-storey group) is schematic; ' +
    'balcony pattern and window counts are approximate, colours from textual descriptions only.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const O = [-343, 1914],
      A = (-23 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const ext = (ring) => {
      const p = ring.map(toL);
      return {
        u0: Math.min(...p.map((q) => q[0])),
        u1: Math.max(...p.map((q) => q[0])),
        v0: Math.min(...p.map((q) => q[1])),
        v1: Math.max(...p.map((q) => q[1])),
      };
    };
    const slabB = byId['e4024000-21e9-4920-ac2d-767c6cb60fdd'];
    const svcB = byId['a0522042-7936-4c38-8523-883efe042e67'];
    const S = ext(slabB.polys[0][0]);
    const T = ext(svcB.polys[0][0]);
    // Main slab sits on the north-east part of the footprint; the low podium on the south-west.
    const slab = { u0: S.u0 + 0.5, u1: S.u1 - 0.3, v0: -1.4, v1: S.v1 - 0.2 };
    const pod = { u0: S.u0 + 4, u1: S.u1 - 0.3, v0: S.v0 + 0.3, v1: -1.4 };
    const svc = { u0: T.u0 + 0.6, u1: T.u1 - 0.3, v0: T.v0 + 0.3, v1: T.v1 - 0.6 };
    const TOP = 92,
      BASE = 6,
      GROUP = (TOP - 2 - BASE) / 9; // 9 groups of 3 storeys

    const b = new kit.MeshBatch();
    const conc = kit.mat('#9d978c', { roughness: 0.95 });
    const concDark = kit.mat('#77736c', { roughness: 0.95 });
    const glassM = kit.mat('dark_glass');
    const cedar = kit.mat('#8a5a3a', { roughness: 0.9 });
    const roofM = kit.mat('#6f6c67');

    const concBg = (g2, w, h, seed) => {
      const r = kit.rng(seed);
      g2.fillStyle = '#a09a8f';
      g2.fillRect(0, 0, w, h);
      for (let k = 0; k < 2500; k++) {
        g2.fillStyle = `rgba(${60 + r() * 60},${55 + r() * 60},${50 + r() * 50},${0.08 + r() * 0.1})`;
        g2.fillRect(r() * w, r() * h, 1 + r() * 2, 1 + r() * 2);
      }
    };
    const win = (g2, x, y, w, h) => {
      g2.fillStyle = '#26323b';
      g2.fillRect(x, y, w, h);
      g2.fillStyle = 'rgba(160,190,205,0.25)';
      g2.fillRect(x, y, w, h * 0.35);
      g2.fillStyle = '#c9c6bd';
      for (let k = 1; k < 3; k++) g2.fillRect(x + (k * w) / 3 - 1, y, 2, h);
      g2.fillRect(x, y + h * 0.62, w, 2);
    };
    // Long elevation (one tile = 4 bays x one 3-storey group): two flat storeys with
    // cedar-lined recessed balconies alternating with glazing, then the narrow
    // corridor storey with its strip of small windows.
    const longFace = kit.paintedMaterial('trellick_tower:long', 512, 384, (g2, w, h) => {
      concBg(g2, w, h, 0.31);
      const fh = h / 3;
      for (let bay = 0; bay < 4; bay++) {
        const x = (bay * w) / 4;
        // two flat storeys (rows 2 and 1 from top in canvas = lower storeys)
        for (let s = 0; s < 2; s++) {
          const y = h - (s + 1) * fh;
          const balcony = (bay + s) % 2 === 0;
          if (balcony) {
            g2.fillStyle = '#5d3b26';
            g2.fillRect(x + 8, y + 10, w / 4 - 16, fh - 16);
            g2.fillStyle = '#8b5b3b';
            g2.fillRect(x + 8, y + 10, w / 4 - 16, 12);
            win(g2, x + 22, y + 26, w / 4 - 44, fh - 40);
            g2.fillStyle = '#b5afa4';
            g2.fillRect(x + 8, y + fh - 26, w / 4 - 16, 10); // balcony parapet
          } else {
            win(g2, x + 10, y + 18, w / 4 - 20, fh - 34);
          }
        }
        // corridor storey: small square windows
        for (let k = 0; k < 3; k++) win(g2, x + 14 + k * 38, 30, 22, fh - 62);
      }
      g2.fillStyle = 'rgba(70,66,60,0.6)';
      for (let s = 0; s <= 3; s++) g2.fillRect(0, s * fh - 2, w, 4);
    });
    const endFace = kit.paintedMaterial('trellick_tower:end', 256, 384, (g2, w, h) => {
      concBg(g2, w, h, 0.47);
      g2.fillStyle = 'rgba(70,66,60,0.45)';
      for (let s = 0; s <= 3; s++) g2.fillRect(0, (s * h) / 3 - 2, w, 3);
      win(g2, w / 2 - 10, h / 3 + 20, 20, h / 3 - 40);
    });
    // Service tower: blank concrete with staggered narrow staircase slots.
    const svcFace = kit.paintedMaterial('trellick_tower:svc', 128, 384, (g2, w, h) => {
      concBg(g2, w, h, 0.73);
      for (let s = 0; s < 3; s++) {
        g2.fillStyle = '#2a333a';
        g2.fillRect(w * 0.42, s * (h / 3) + 30 + (s % 2) * 30, 18, h / 3 - 90);
      }
    });
    const quad = (m, p, q, z0, z1, ur, vr, v0 = 0) =>
      b.quad(
        m,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [0, v0],
        [ur, v0],
        [ur, v0 + vr],
        [0, v0 + vr],
      );
    // Box in local coordinates with per-face materials and UV repeats.
    const lbox = (r, z0, z1, mats, rep, capM) => {
      const c = [W(r.u0, r.v0), W(r.u1, r.v0), W(r.u1, r.v1), W(r.u0, r.v1)];
      const lu = r.u1 - r.u0,
        lv = r.v1 - r.v0;
      for (let k = 0; k < 4; k++) {
        const len = k % 2 === 0 ? lu : lv;
        quad(
          mats[k],
          c[k],
          c[(k + 1) % 4],
          z0,
          z1,
          rep ? rep(k, len)[0] : len / 4,
          rep ? rep(k, len)[1] : (z1 - z0) / 4,
          rep ? (rep(k, len)[2] ?? 0) : 0,
        );
      }
      if (capM) {
        b.add(
          capM,
          [
            [...c[0], z1],
            [...c[1], z1],
            [...c[2], z1],
            [...c[3], z1],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
        b.add(
          capM,
          [
            [...c[0], z0],
            [...c[1], z0],
            [...c[2], z0],
            [...c[3], z0],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 2, 1, 0, 3, 2],
        );
      }
    };
    const box = (u, v, z0, du, dv, h, m) => {
      const [x, y] = W(u, v);
      kit.box(b, m, x, y, z0, du, dv, h, A);
    };

    // --- Main slab -------------------------------------------------------------
    const bays = (len, bw) => Math.max(1, Math.round(len / bw)) / 4;
    lbox(slab, BASE, BASE + 9 * GROUP, [longFace, endFace, longFace, endFace], (k, len) =>
      k % 2 === 0 ? [bays(len, 5.4), 9, 0] : [1, 9, 0],
    );
    // top storey / parapet band and roof
    lbox(
      { u0: slab.u0 - 0.2, u1: slab.u1 + 0.2, v0: slab.v0 - 0.2, v1: slab.v1 + 0.2 },
      BASE + 9 * GROUP,
      TOP,
      [conc, conc, conc, conc],
      null,
      roofM,
    );
    // recessed glazed ground floor under the slab with pilotis
    lbox({ u0: slab.u0 + 1.2, u1: slab.u1 - 1.2, v0: slab.v0 + 1.2, v1: slab.v1 - 1.2 }, 0, BASE, [
      glassM,
      glassM,
      glassM,
      glassM,
    ]);
    for (let u = slab.u0 + 0.6; u <= slab.u1 - 0.5; u += (slab.u1 - slab.u0 - 1.2) / 6)
      for (const v of [slab.v0 + 0.6, slab.v1 - 0.6]) box(u, v, 0, 1.0, 1.0, BASE, concDark);
    // horizontal floor-slab lips every group, vertical cross-wall fins
    for (let k = 0; k <= 9; k++) {
      const z = BASE + k * GROUP - 0.25;
      for (const v of [slab.v0 - 0.25, slab.v1 + 0.25])
        box((slab.u0 + slab.u1) / 2, v, z, slab.u1 - slab.u0 + 0.5, 0.5, 0.5, conc);
    }
    const nf = 8;
    for (let k = 0; k <= nf; k++) {
      const u = slab.u0 + ((slab.u1 - slab.u0) * k) / nf;
      for (const v of [slab.v0 - 0.3, slab.v1 + 0.3]) box(u, v, BASE, 0.45, 0.6, 9 * GROUP, conc);
    }
    // roof plant / lift motor rooms
    box(slab.u0 + 8, (slab.v0 + slab.v1) / 2, TOP, 6, 6, 2.5, concDark);
    box(slab.u1 - 8, (slab.v0 + slab.v1) / 2, TOP, 5, 5, 2, concDark);

    // --- Podium on the south-west side ------------------------------------------
    lbox(pod, 0, 7.2, [glassM, conc, conc, conc], (k, len) => [len / 4, 7.2 / 4], roofM);
    box((pod.u0 + pod.u1) / 2, pod.v0 - 0.2, 5.6, pod.u1 - pod.u0, 0.5, 1.6, conc);

    // --- Service tower -----------------------------------------------------------
    lbox(svc, 0, TOP, [svcFace, svcFace, conc, svcFace], (k, len) => [1, 9, 0], roofM);
    for (let k = 0; k <= 9; k++)
      box(
        (svc.u0 + svc.u1) / 2,
        (svc.v0 + svc.v1) / 2,
        BASE + k * GROUP - 0.15,
        svc.u1 - svc.u0 + 0.3,
        svc.v1 - svc.v0 + 0.3,
        0.3,
        concDark,
      );
    // Boiler house: cantilevered plant room with ribbed walls and a jutting nose.
    const bh = { u0: svc.u0 - 3.2, u1: svc.u1 + 0.4, v0: svc.v0 - 1.5, v1: svc.v1 + 1.5 };
    lbox(bh, TOP - 1, TOP + 5.5, [conc, conc, conc, conc], null, roofM);
    for (let k = 0; k <= 10; k++) {
      const v = bh.v0 + ((bh.v1 - bh.v0) * k) / 10;
      box(bh.u0 - 0.25, v, TOP - 1, 0.5, 0.35, 6.5, concDark);
    }
    for (const v of [bh.v0 + 2, bh.v1 - 2]) box(bh.u0 - 1.2, v, TOP + 0.5, 2.4, 1.2, 4, conc);
    box((bh.u0 + bh.u1) / 2, (bh.v0 + bh.v1) / 2, TOP + 5.5, 4, 3, 1.5, concDark); // flue head
    // tapering brackets under the boiler house overhang
    for (const v of [bh.v0 + 1, bh.v1 - 1]) {
      const geo = new THREE.BufferGeometry();
      const p0 = W(svc.u0, v),
        p1 = W(bh.u0, v);
      const verts = [
        [p0[0], p0[1], TOP - 7],
        [p1[0], p1[1], TOP - 1],
        [p0[0], p0[1], TOP - 1],
      ];
      b.add(
        conc,
        verts,
        [
          [0, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2],
      );
      b.add(
        conc,
        verts,
        [
          [0, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 2, 1],
      );
      geo.dispose();
    }

    // --- Bridges every third storey (corridor level of each group) ---------------
    const bv0 = Math.max(svc.v0, slab.v0) + 1.5,
      bv1 = bv0 + 2.6;
    for (let k = 0; k < 9; k++) {
      const z = BASE + k * GROUP + GROUP * (2 / 3);
      const br = { u0: svc.u1 - 0.1, u1: slab.u0 + 0.1, v0: bv0, v1: bv1 };
      lbox(br, z - 0.4, z + GROUP / 3, [conc, conc, conc, conc], null, conc);
      // slot window along the bridge
      for (const v of [bv0 - 0.06, bv1 + 0.06])
        box((br.u0 + br.u1) / 2, v, z + 0.7, br.u1 - br.u0 - 1, 0.1, 1.0, glassM);
    }
    g.add(b.toGroup('trellick_tower'));
    return g;
  },
};
