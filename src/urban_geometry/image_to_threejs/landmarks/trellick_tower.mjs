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
    {
      title: 'Trellick Tower - RBKC listed buildings search',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=471992',
      used_for:
        'balconies forming a pattern across the main facades, interrupted at the maisonette floor; corridors on the north face marked by pre-cast panels',
    },
    {
      title: 'Trellick Tower - Open House Festival',
      url: 'https://programme.openhouse.org.uk/listings/2203',
      used_for:
        'on the main south elevation every flat sits behind a balcony; access galleries and north facade with concrete infill panels',
    },
  ],
  notes:
    'Slab and service tower from the Overture footprints; slab roof 92 m, boiler house top 98 m (reference ' +
    'roof height). Facades are built in 3D bay by bay (11 bays x 27 storeys in 9 three-storey groups): on the ' +
    'south elevation every flat sits behind a deep cedar-lined recessed balcony (concrete upstand, rail, cedar ' +
    'soffit) chequered with framed bedroom windows, with a changed rhythm on the maisonette floors; the north ' +
    'elevation has pebble-finished precast panels with small windows along each access-corridor storey and ' +
    'occasional kitchen balconies. Floor-slab lips, cross-wall fins, pilotis, staggered stair slots on the ' +
    'service tower, enclosed bridges with glazed slots and joints, and a two-level ribbed, louvred boiler house ' +
    'cantilevered on raked brackets with flue stacks are modelled. Bay count, balcony pattern, window sizes and ' +
    'boiler house profile are interpretations of the textual sources (no photographs); lamps/benches/bollards ' +
    'are generic resources assets at assumed positions',
  build({ THREE, kit, byId, placeAssets }) {
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
    const glassM = kit.mat('#34434d', { roughness: 0.12, metalness: 0.3 });
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
    const add = (geo, m, u, v, z) => {
      const [x, y] = W(u, v);
      b.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(A).setPosition(x, y, z));
      geo.dispose();
    };

    // --- 3D facade kit ----------------------------------------------------------
    const cedarDark = kit.mat('#6e4329', { roughness: 0.9 });
    const frameM = kit.mat('#4b4f50', { roughness: 0.5, metalness: 0.4 });
    const railM = kit.mat('#3a3d3f', { roughness: 0.5, metalness: 0.5 });
    const pebble = kit.paintedMaterial('trellick_tower:pebble', 128, 128, (g2, w, h) => {
      const r = kit.rng(0.29);
      g2.fillStyle = '#b2aa9b';
      g2.fillRect(0, 0, w, h);
      for (let k = 0; k < 1400; k++) {
        const t = 110 + r() * 70;
        g2.fillStyle = `rgba(${t + 8},${t + 2},${t - 10},0.45)`;
        g2.beginPath();
        g2.arc(r() * w, r() * h, 0.8 + r() * 1.6, 0, 7);
        g2.fill();
      }
      g2.fillStyle = 'rgba(70,66,60,0.6)';
      g2.fillRect(0, 0, w, 2);
      g2.fillRect(0, 0, 2, h);
    });
    const bushConc = kit.paintedMaterial('trellick_tower:bush', 256, 256, (g2, w, h) =>
      concBg(g2, w, h, 0.61),
    );
    // wall quad on a slab face at outward offset d (F.s = outward sign along v)
    const faceAt = (F, ua, ub, d) => {
      const v = F.v + F.s * d;
      return F.s < 0 ? [W(ua, v), W(ub, v)] : [W(ub, v), W(ua, v)];
    };
    const panel = (F, ua, ub, z0, z1, d, m) => {
      const [p, q] = faceAt(F, ua, ub, d);
      quad(m, p, q, z0, z1, (ub - ua) / 4, (z1 - z0) / 4, z0 / 4);
    };
    const vAt = (F, d) => F.v + F.s * d;
    const win3 = (F, ua, ub, z, d, opts) => {
      const [p, q] = faceAt(F, ua, ub, d);
      kit.windowRow(b, p, q, z, {
        glass: glassM,
        frame: frameM,
        sill: conc,
        head: 'none',
        depth: 0.1,
        margin: 0,
        ...opts,
      });
    };
    const windowCell = (F, ua, ub, z0, z1) => {
      panel(F, ua, ub, z0, z1, 0, bushConc);
      win3(F, ua, ub, z0 + 0.85, 0, {
        count: 1,
        width: ub - ua - 1.3,
        height: z1 - z0 - 1.35,
        bars: 1,
      });
    };
    const balconyCell = (F, ua, ub, z0, z1, D = 1.8) => {
      const vm = vAt(F, -D / 2),
        um = (ua + ub) / 2,
        hh = z1 - z0;
      panel(F, ua, ub, z0, z1, -D, cedar);
      win3(F, ua + 0.2, ub - 0.2, z0 + 0.25, -D, {
        count: 2,
        width: (ub - ua - 0.9) / 2,
        height: hh - 0.75,
        bars: 1,
        sill: frameM,
      });
      for (const u of [ua + 0.12, ub - 0.12]) box(u, vm, z0, 0.24, D, hh, cedar);
      box(um, vm, z1 - 0.22, ub - ua, D, 0.22, cedarDark); // cedar-boarded soffit
      box(um, vm, z0, ub - ua, D, 0.18, concDark); // balcony floor
      box(um, vAt(F, -0.12), z0, ub - ua - 0.1, 0.24, 1.05, conc); // concrete upstand
      box(um, vAt(F, -0.12), z0 + 1.05, ub - ua - 0.1, 0.12, 0.06, railM);
    };
    const corridorCell = (F, ua, ub, z0, z1) => {
      panel(F, ua, ub, z0, z1, 0, pebble);
      win3(F, ua, ub, z0 + 1.2, 0.0, { count: 2, width: 0.7, height: 1.0, bars: 0, margin: 0.6 });
    };

    // --- Main slab -------------------------------------------------------------
    const NB = 11,
      bw = (slab.u1 - slab.u0) / NB;
    const FS = { v: slab.v0, s: -1 },
      Nf = { v: slab.v1, s: 1 };
    const ST = GROUP / 3;
    for (let k = 0; k < 9; k++) {
      for (let s = 0; s < 3; s++) {
        const z0 = BASE + k * GROUP + s * ST,
          z1 = z0 + ST;
        const corridor = s === 2;
        const maisonette = k === 7; // floors 23-24: changed balcony rhythm
        for (let j = 0; j < NB; j++) {
          const ua = slab.u0 + j * bw,
            ub = ua + bw;
          // south elevation: every flat behind a balcony, chequered with bedroom windows
          const balS = maisonette ? j % 3 !== 2 : corridor ? j % 2 === 1 : (j + s) % 2 === 0;
          (balS ? balconyCell : windowCell)(FS, ua, ub, z0, z1);
          // north elevation: precast panels along the access corridors, kitchen balconies
          if (corridor) corridorCell(Nf, ua, ub, z0, z1);
          else if (j % 4 === 1 && s === 0) balconyCell(Nf, ua, ub, z0, z1, 1.1);
          else windowCell(Nf, ua, ub, z0, z1);
        }
      }
    }
    // slab ends: blank bush-hammered concrete with the narrow window slot per group
    for (const [p, q] of [
      [W(slab.u0, slab.v1), W(slab.u0, slab.v0)],
      [W(slab.u1, slab.v0), W(slab.u1, slab.v1)],
    ])
      quad(endFace, p, q, BASE, BASE + 9 * GROUP, 1, 9, 0);
    // top storey / parapet band and roof
    lbox(
      { u0: slab.u0 - 0.2, u1: slab.u1 + 0.2, v0: slab.v0 - 0.2, v1: slab.v1 + 0.2 },
      BASE + 9 * GROUP,
      TOP,
      [bushConc, bushConc, bushConc, bushConc],
      null,
      roofM,
    );
    box(
      (slab.u0 + slab.u1) / 2,
      (slab.v0 + slab.v1) / 2,
      TOP,
      slab.u1 - slab.u0 + 0.4,
      slab.v1 - slab.v0 + 0.4,
      0.35,
      conc,
    );
    // recessed glazed ground floor under the slab with pilotis
    lbox({ u0: slab.u0 + 1.2, u1: slab.u1 - 1.2, v0: slab.v0 + 1.2, v1: slab.v1 - 1.2 }, 0, BASE, [
      glassM,
      glassM,
      glassM,
      glassM,
    ]);
    box(
      (slab.u0 + slab.u1) / 2,
      (slab.v0 + slab.v1) / 2,
      BASE - 0.6,
      slab.u1 - slab.u0,
      slab.v1 - slab.v0,
      0.6,
      conc,
    );
    for (let j = 0; j <= NB; j += 2)
      for (const v of [slab.v0 + 0.6, slab.v1 - 0.6])
        box(slab.u0 + j * bw, v, 0, 0.9, 1.1, BASE - 0.6, concDark);
    // floor-slab lips at each storey, deeper at the corridor levels; cross-wall fins
    for (let k = 0; k <= 27; k++) {
      const z = BASE + k * ST - 0.15;
      const deep = k % 3 === 0;
      for (const v of [slab.v0 - 0.15, slab.v1 + 0.15])
        box(
          (slab.u0 + slab.u1) / 2,
          v,
          z,
          slab.u1 - slab.u0 + 0.6,
          deep ? 0.55 : 0.3,
          deep ? 0.4 : 0.25,
          conc,
        );
    }
    for (let j = 0; j <= NB; j++) {
      const u = slab.u0 + j * bw;
      for (const v of [slab.v0 - 0.2, slab.v1 + 0.2]) box(u, v, BASE, 0.35, 0.5, 9 * GROUP, conc);
    }
    // roof plant / lift motor rooms
    box(slab.u0 + 8, (slab.v0 + slab.v1) / 2, TOP + 0.35, 6, 6, 2.5, concDark);
    box(slab.u1 - 8, (slab.v0 + slab.v1) / 2, TOP + 0.35, 5, 5, 2, concDark);

    // --- Podium on the south-west side ------------------------------------------
    lbox(pod, 0, 7.2, [glassM, conc, conc, conc], (k, len) => [len / 4, 7.2 / 4], roofM);
    box((pod.u0 + pod.u1) / 2, pod.v0 - 0.2, 5.6, pod.u1 - pod.u0, 0.5, 1.6, conc);
    {
      const F = { v: pod.v0, s: -1 };
      for (let u = pod.u0 + 0.5; u < pod.u1 - 0.5; u += 4.2) {
        box(u, pod.v0 - 0.15, 0, 0.35, 0.35, 5.6, concDark);
        win3(F, u + 0.25, Math.min(u + 4.0, pod.u1 - 0.4), 0.4, 0.06, {
          count: 1,
          width: 3.3,
          height: 4.0,
          bars: 1,
        });
      }
      box((pod.u0 + pod.u1) / 2, pod.v0 - 1.4, 4.4, pod.u1 - pod.u0, 2.6, 0.25, conc); // canopy
    }

    // --- Service tower -----------------------------------------------------------
    lbox(svc, 0, TOP, [svcFace, svcFace, bushConc, svcFace], (k, len) => [1, 9, 0], roofM);
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
    // staggered narrow stair and lift-lobby slot windows on the three free faces
    for (let st = 1; st < 30; st++) {
      const z = BASE + st * ST + 0.6;
      const off = st % 2 ? 0.25 : -0.25;
      const vm = (svc.v0 + svc.v1) / 2,
        um = (svc.u0 + svc.u1) / 2;
      box(svc.u0 - 0.05, vm + off * 4, z, 0.12, 0.55, 1.9, glassM);
      box(svc.u0 - 0.12, vm + off * 4, z - 0.12, 0.25, 0.9, 0.12, conc);
      for (const v of [svc.v0 - 0.05, svc.v1 + 0.05]) {
        box(um + off * 6, v, z, 0.55, 0.12, 1.9, glassM);
        box(um + off * 6, v, z - 0.12, 0.9, 0.25, 0.12, conc);
      }
    }
    // Boiler house: two-storey plant room cantilevered beyond the service tower like a
    // ship's bridge, ribbed walls, louvre bands, raked brackets and flue head.
    const bh = { u0: svc.u0 - 3.2, u1: svc.u1 + 0.4, v0: svc.v0 - 1.5, v1: svc.v1 + 1.5 };
    lbox(bh, TOP - 1, TOP + 2.8, [bushConc, bushConc, bushConc, bushConc], null, roofM);
    const bh2 = { u0: bh.u0 + 0.8, u1: bh.u1 - 0.4, v0: bh.v0 + 0.6, v1: bh.v1 - 0.6 };
    lbox(bh2, TOP + 2.8, TOP + 6.2, [bushConc, bushConc, bushConc, bushConc], null, roofM);
    box(
      (bh.u0 + bh.u1) / 2,
      (bh.v0 + bh.v1) / 2,
      TOP - 1.4,
      bh.u1 - bh.u0 + 0.4,
      bh.v1 - bh.v0 + 0.4,
      0.4,
      conc,
    );
    box(
      (bh.u0 + bh.u1) / 2,
      (bh.v0 + bh.v1) / 2,
      TOP + 2.6,
      bh.u1 - bh.u0 + 0.5,
      bh.v1 - bh.v0 + 0.5,
      0.35,
      conc,
    );
    box(
      (bh2.u0 + bh2.u1) / 2,
      (bh2.v0 + bh2.v1) / 2,
      TOP + 6.2,
      bh2.u1 - bh2.u0 + 0.4,
      bh2.v1 - bh2.v0 + 0.4,
      0.35,
      conc,
    );
    // vertical ribs on the cantilevered nose and sides
    for (let k = 0; k <= 10; k++) {
      const v = bh.v0 + ((bh.v1 - bh.v0) * k) / 10;
      box(bh.u0 - 0.25, v, TOP - 1, 0.5, 0.35, 3.6, concDark);
      box(
        bh2.u0 - 0.2,
        v * 0.92 + ((bh.v0 + bh.v1) / 2) * 0.08,
        TOP + 2.95,
        0.4,
        0.3,
        3.2,
        concDark,
      );
    }
    for (let k = 0; k <= 8; k++) {
      const u = bh.u0 + ((bh.u1 - bh.u0) * k) / 8;
      for (const v of [bh.v0 - 0.2, bh.v1 + 0.2]) box(u, v, TOP - 1, 0.35, 0.4, 3.6, concDark);
    }
    // louvre bands (horizontal slats) on the upper plant level
    for (let z = TOP + 3.4; z < TOP + 5.8; z += 0.4) {
      box(bh2.u0 - 0.1, (bh2.v0 + bh2.v1) / 2, z, 0.2, bh2.v1 - bh2.v0 - 1.2, 0.12, railM);
      for (const v of [bh2.v0 - 0.08, bh2.v1 + 0.08])
        box((bh2.u0 + bh2.u1) / 2, v, z, bh2.u1 - bh2.u0 - 1.2, 0.16, 0.12, railM);
    }
    // the "bridge" windows looking out from the cantilevered nose
    box(bh.u0 - 0.06, (bh.v0 + bh.v1) / 2, TOP + 0.6, 0.1, bh.v1 - bh.v0 - 2, 1.0, glassM);
    // flue head and stacks
    box((bh2.u0 + bh2.u1) / 2, (bh2.v0 + bh2.v1) / 2, TOP + 6.55, 4, 3, 1.6, concDark);
    for (const dv of [-0.8, 0.8])
      add(
        new THREE.CylinderGeometry(0.35, 0.35, 2.2, 10).rotateX(Math.PI / 2),
        railM,
        (bh2.u0 + bh2.u1) / 2 + 0.6,
        (bh2.v0 + bh2.v1) / 2 + dv,
        TOP + 8.6,
      );
    // tapering brackets under the boiler house overhang
    for (const v of [bh.v0 + 1, (bh.v0 + bh.v1) / 2, bh.v1 - 1]) {
      const p0 = W(svc.u0, v),
        p1 = W(bh.u0, v);
      const verts = [
        [p0[0], p0[1], TOP - 8],
        [p1[0], p1[1], TOP - 1.4],
        [p0[0], p0[1], TOP - 1.4],
      ];
      const off = [Math.sin(A) * 0.25, -Math.cos(A) * 0.25];
      for (const sg of [-1, 1]) {
        const vv = verts.map(([x, y, z]) => [x + off[0] * sg, y + off[1] * sg, z]);
        b.add(
          conc,
          vv,
          [
            [0, 0],
            [1, 1],
            [0, 1],
          ],
          sg > 0 ? [0, 1, 2] : [0, 2, 1],
        );
      }
      const P0 = [verts[0], verts[1]].map(([x, y, z]) => [x, y, z]);
      b.add(
        concDark,
        [
          [P0[0][0] - off[0], P0[0][1] - off[1], P0[0][2]],
          [P0[0][0] + off[0], P0[0][1] + off[1], P0[0][2]],
          [P0[1][0] + off[0], P0[1][1] + off[1], P0[1][2]],
          [P0[1][0] - off[0], P0[1][1] - off[1], P0[1][2]],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2],
      );
    }

    // --- Bridges every third storey (corridor level of each group) ---------------
    const bv0 = Math.max(svc.v0, slab.v0) + 1.5,
      bv1 = bv0 + 2.6;
    for (let k = 0; k < 9; k++) {
      const z = BASE + k * GROUP + GROUP * (2 / 3);
      const br = { u0: svc.u1 - 0.1, u1: slab.u0 + 0.1, v0: bv0, v1: bv1 };
      lbox(br, z - 0.4, z + GROUP / 3 - 0.3, [bushConc, bushConc, bushConc, bushConc], null, conc);
      // glazed slot along the bridge with mullions, neoprene joint bands at each end
      for (const v of [bv0 - 0.06, bv1 + 0.06]) {
        box((br.u0 + br.u1) / 2, v, z + 0.8, br.u1 - br.u0 - 1, 0.1, 1.0, glassM);
        for (let u = br.u0 + 0.5; u <= br.u1 - 0.4; u += 1.1)
          box(u, v + (v < bv0 ? -0.03 : 0.03), z + 0.8, 0.08, 0.1, 1.0, frameM);
        box(
          (br.u0 + br.u1) / 2,
          v + (v < bv0 ? -0.05 : 0.05),
          z + 0.7,
          br.u1 - br.u0 - 0.8,
          0.14,
          0.12,
          conc,
        );
      }
      for (const u of [br.u0 + 0.15, br.u1 - 0.15])
        box(u, (bv0 + bv1) / 2, z - 0.4, 0.3, bv1 - bv0 + 0.1, GROUP / 3 - 0.1, railM);
    }

    // --- Entrance surroundings ------------------------------------------------------
    if (placeAssets) {
      const head = (du, dv) => Math.atan2(-(du * ca - dv * sa), du * sa + dv * ca);
      const lamps = [],
        bollards = [],
        benches = [];
      for (let u = slab.u0 + 2; u < slab.u1; u += 11)
        lamps.push([...W(u, slab.v1 + 6), head(0, 1)]);
      for (let u = svc.u0; u < svc.u1 + 1; u += 1.6)
        bollards.push([...W(u, svc.v1 + 4), head(0, 1)]);
      for (const u of [slab.u0 + 6, slab.u0 + 16, slab.u0 + 26])
        benches.push([...W(u, slab.v1 + 4), head(0, -1)]);
      g.add(placeAssets('street_lamp', lamps, { name: 'trellick_tower:lamps' }));
      g.add(placeAssets('bollard', bollards, { name: 'trellick_tower:bollards' }));
      g.add(placeAssets('bench', benches, { name: 'trellick_tower:benches' }));
    }
    g.add(b.toGroup('trellick_tower'));
    return g;
  },
};
