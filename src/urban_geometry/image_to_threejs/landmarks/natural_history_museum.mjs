// Natural History Museum, South Kensington (Alfred Waterhouse, 1873-1881) with the
// Darwin Centre (C.F. Moller, 2009) and the Earth Galleries / Red Zone (former
// Geological Museum, Allison & Markham, 1935).
//
// Waterhouse building: symmetrical Romanesque front of buff and blue-grey banded
// terracotta on Cromwell Road, ~207 m long; a three-bay centrepiece set forward with
// the great round-arched entrance between two spired towers (~58 m); wings of
// round-headed windows (coupled lights on ground and first floors) ending in
// pavilions with steep pavilion roofs; pitched slate roofs; behind the front the
// cathedral-like Hintze Hall with its long glazed roof and top-lit gallery wings.
// Darwin Centre: an eight-storey white "cocoon" inside a glass box. Earth Galleries:
// stripped-classical Portland stone block on Exhibition Road with a glazed atrium,
// linked north to the Science Museum by a bridge over an arched gateway.
//
// Everything is built in a local frame aligned with the Cromwell Road front
// (u east along the front, v north), origin at the centre of the main entrance.
const O = [1668, -1167],
  ANG = 0.1247;

export default {
  id: 'natural_history_museum',
  name: 'Natural History Museum',
  claims: [
    '879ff4e2-4778-4c8b-8535-f252df2bc0b1', // Natural History Museum (Waterhouse + Earth Galleries)
    'f26c3834-e72f-4603-8dd1-28315210b0db', // Darwin Centre
    '9e33528c-5619-48da-85c7-6fd332e30473', // Lodge (Queen's Gate side)
    '5f2a364a-3a51-4fd6-b40a-799f15fbff37', // bridge over the gateway to the Science Museum
  ],
  references: [
    {
      title: 'Natural History Museum, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Natural_History_Museum,_London',
      used_for:
        'Waterhouse, Romanesque terracotta building, buff and blue-grey terracotta, Gibbs and Canning tiles',
    },
    {
      title: 'Listed Buildings Search (RBKC) - Natural History Museum',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=203737',
      used_for:
        'listing: buff and grey terracotta, pitched slated roof, three-bay centrepiece with two spired towers, end bays with steep pavilion roofs, square-headed ground and round-headed first floor windows with coupled lights',
    },
    {
      title: 'Natural History Museum - Gardenvisit (London and its environs, 1927)',
      url: 'https://www.gardenvisit.com/book/london_and_its_environs_1927/41_the_natural_history_museum/natural_history_museum',
      used_for: 'central block with two towers 192 ft high, wings ending in pavilions',
    },
    {
      title: 'Natural History Museum (Bluffton University architecture notes)',
      url: 'https://homepages.bluffton.edu/~sullivanm/england/london/scimuseum/waterhouse.html',
      used_for: 'terracotta in yellowish brown with bands of bluish grey',
    },
    {
      title: 'Alfred Waterhouse: museum building, cathedral to nature (NHM)',
      url: 'https://www.nhm.ac.uk/discover/alfred-waterhouse-museum-building-cathedral-to-nature.html',
      used_for: 'terracotta over iron and steel frame, cathedral-like Hintze Hall',
    },
    {
      title: 'Darwin Centre - architravel',
      url: 'https://architravel.com/project/darwin-centre',
      used_for: 'eight-storey concrete cocoon inside a glass atrium (C.F. Moller)',
    },
    {
      title: "Danish cocoon completed for London's insects - C.F. Moller",
      url: 'https://www.cfmoller.com/g/Danish-cocoon-completed-for-Londons-insects-i12627.html',
      used_for: 'cocoon form, completion 2008/2009',
    },
    {
      title: 'Geological Museum - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Geological_Museum',
      used_for:
        'Allison and Markham building on Exhibition Road (1935), now the Red Zone / Earth Galleries',
    },
    {
      title: 'Nature (1935) on the new Geological Museum',
      url: 'https://www.nature.com/articles/1351060a0',
      used_for: 'linked to the Science Museum by corridors over an arched gateway',
    },
  ],
  notes:
    'Footprint from Overture (front measured 207 m). Heights are estimates from descriptions: towers 58 m (192 ft), ' +
    'front eaves 19 m, pavilions 24 m + steep roofs, Hintze Hall ridge 34 m; the Overture h (13.7 m) is inferred and ' +
    'ignored. Plan behind the front (gallery wings, light courts, north range) is schematic. Darwin Centre height (28 m) ' +
    'assumed from its eight storeys; Earth Galleries height (22 m + attic) estimated. Lodge modelled as a small ' +
    'terracotta lodge. Facade ornament is painted onto canvas textures.',

  build({ THREE, kit }) {
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    const B = new kit.MeshBatch();

    // ---------- palette ----------
    const BUFF = '#d6c096',
      BUFF_D = '#c4ab80',
      BLUE = '#838f9b',
      BLUE_D = '#5f6b75',
      WIN = '#2a3036',
      WIN_L = '#46505a';
    const buff = kit.mat(BUFF, { roughness: 0.8 }),
      blue = kit.mat(BLUE, { roughness: 0.8 }),
      slateMat = kit.roof('slate', 1),
      slate = kit.mat('#4e555d', { roughness: 0.75 }),
      glass = kit.mat('glass'),
      darkGlass = kit.mat('dark_glass'),
      iron = kit.mat('dark_steel'),
      lead = kit.mat('lead'),
      stone = kit.mat('portland_stone'),
      paving = kit.mat('paving'),
      white = kit.mat('#efebe2', { roughness: 0.7 }),
      clearGlass = kit.mat('#9fb8c4', {
        roughness: 0.1,
        metalness: 0.2,
        transparent: true,
        opacity: 0.38,
      });

    // ---------- canvas helpers ----------
    const archPath = (g, x, yTop, w, yBot) => {
      g.beginPath();
      g.moveTo(x, yBot);
      g.lineTo(x, yTop + w / 2);
      g.arc(x + w / 2, yTop + w / 2, w / 2, Math.PI, 0);
      g.lineTo(x + w, yBot);
      g.closePath();
    };
    const fillArch = (g, x, yTop, w, yBot, col) => {
      archPath(g, x, yTop, w, yBot);
      g.fillStyle = col;
      g.fill();
    };
    // Arch with banded voussoir ring (alternate buff and blue).
    const bandedArch = (g, x, yTop, w, yBot, ring, col = WIN) => {
      const cx = x + w / 2,
        cy = yTop + w / 2;
      const n = 11;
      for (let k = 0; k < n; k++) {
        g.beginPath();
        g.arc(cx, cy, w / 2 + ring, Math.PI + (k * Math.PI) / n, Math.PI + ((k + 1) * Math.PI) / n);
        g.arc(cx, cy, w / 2, Math.PI + ((k + 1) * Math.PI) / n, Math.PI + (k * Math.PI) / n, true);
        g.closePath();
        g.fillStyle = k % 2 ? BLUE : BUFF_D;
        g.fill();
      }
      fillArch(g, x, yTop, w, yBot, col);
    };
    const stripes = (g, w, y0, y1, step, thick) => {
      g.fillStyle = BLUE;
      for (let y = y1; y > y0; y -= step) g.fillRect(0, y - thick, w, thick);
    };

    // One facade bay (7 m wide) of the Cromwell Road front, `Hm` metres high.
    // Storeys: basement (square-headed), ground (coupled lights), first (round-headed
    // with coupled lights), attic; pavilions get one extra storey.
    const bayMat = (key, Hm, tall) =>
      kit.paintedMaterial(`nhm:${key}`, 256, Math.round(Hm * 37), (g, W, Hp) => {
        const s = Hp / Hm,
          Y = (z) => Hp - z * s,
          X = (m) => m * (W / 7);
        g.fillStyle = BUFF;
        g.fillRect(0, 0, W, Hp);
        // banding: dense blue-grey courses on the lower storeys, sparser above
        stripes(g, W, Y(7.5), Y(0), 0.62 * s, 0.22 * s);
        stripes(g, W, Y(Hm), Y(7.5), 1.25 * s, 0.18 * s);
        // plinth
        g.fillStyle = BLUE_D;
        g.fillRect(0, Y(1.0), W, 1.0 * s);
        // piers between bays
        g.fillStyle = BUFF_D;
        g.fillRect(0, 0, X(0.7), Hp);
        g.fillRect(W - X(0.7), 0, X(0.7), Hp);
        g.fillStyle = BLUE;
        for (let z = 0.4; z < Hm; z += 0.9) {
          g.fillRect(0, Y(z + 0.3), X(0.7), 0.3 * s);
          g.fillRect(W - X(0.7), Y(z + 0.3), X(0.7), 0.3 * s);
        }
        // basement windows (square headed)
        g.fillStyle = WIN;
        g.fillRect(X(2.1), Y(1.9), X(1.1), 0.8 * s);
        g.fillRect(X(3.8), Y(1.9), X(1.1), 0.8 * s);
        // ground floor: coupled round-headed lights under a relieving arch
        bandedArch(g, X(1.6), Y(6.4), X(3.8), Y(2.4), X(0.35), BUFF_D);
        fillArch(g, X(1.95), Y(5.9), X(1.4), Y(2.5), WIN);
        fillArch(g, X(3.65), Y(5.9), X(1.4), Y(2.5), WIN);
        // string course
        g.fillStyle = BLUE_D;
        g.fillRect(0, Y(7.2), W, 0.35 * s);
        g.fillStyle = BUFF_D;
        g.fillRect(0, Y(7.6), W, 0.3 * s);
        // first floor: tall round-headed window with coupled lights and a roundel
        const f0 = 8.2,
          f1 = tall ? 13.6 : 13.2;
        bandedArch(g, X(1.4), Y(f1), X(4.2), Y(f0), X(0.4), BUFF_D);
        fillArch(g, X(1.8), Y(f1 - 2.0), X(1.5), Y(f0 + 0.1), WIN);
        fillArch(g, X(3.7), Y(f1 - 2.0), X(1.5), Y(f0 + 0.1), WIN);
        g.beginPath();
        g.arc(X(3.5), Y(f1 - 0.95), X(0.55), 0, Math.PI * 2);
        g.fillStyle = WIN_L;
        g.fill();
        g.fillStyle = BLUE_D;
        g.fillRect(0, Y(14.2), W, 0.35 * s);
        let top = 14.6;
        if (tall) {
          // extra pavilion storey
          bandedArch(g, X(1.9), Y(19.3), X(3.2), Y(15.2), X(0.3), BUFF_D);
          fillArch(g, X(2.2), Y(18.8), X(1.1), Y(15.3), WIN);
          fillArch(g, X(3.7), Y(18.8), X(1.1), Y(15.3), WIN);
          g.fillStyle = BLUE_D;
          g.fillRect(0, Y(19.9), W, 0.35 * s);
          top = 20.3;
        }
        // attic: arcade of small coupled windows
        for (let k = 0; k < 3; k++)
          fillArch(g, X(1.3 + k * 1.6), Y(top + 2.4), X(1.0), Y(top + 0.4), WIN);
        // corbel table and cornice
        g.fillStyle = BUFF_D;
        g.fillRect(0, Y(Hm - 0.3), W, 0.3 * s);
        g.fillStyle = BLUE;
        for (let k = 0; k < 10; k++) {
          g.beginPath();
          g.arc(X(0.35 + k * 0.7), Y(Hm - 0.75), X(0.25), Math.PI, 0);
          g.fill();
        }
        g.fillStyle = BLUE_D;
        g.fillRect(0, Y(Hm - 0.75), W, 0.12 * s);
      });
    const wingMat = bayMat('wing', 19, false);
    const pavMat = bayMat('pavilion', 24, true);

    // Plain banded terracotta for blind gallery walls, courts and backs.
    const bandMat = kit.paintedMaterial('nhm:bands', 128, 256, (g, W, Hp) => {
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      g.fillStyle = BLUE;
      for (let y = 0; y < Hp; y += 32) g.fillRect(0, y, W, 9);
      g.fillStyle = WIN;
      // a few small round-headed windows (back elevations)
      fillArch(g, 48, 40, 32, 110, WIN);
    });
    // Back elevation: banded with windows in two rows.
    const backMat = kit.paintedMaterial('nhm:back', 128, 256, (g, W, Hp) => {
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      g.fillStyle = BLUE;
      for (let y = 0; y < Hp; y += 22) g.fillRect(0, y, W, 6);
      fillArch(g, 40, 30, 48, 100, WIN);
      fillArch(g, 40, 140, 48, 220, WIN);
    });

    // Pier cladding: buff with blue-grey courses.
    const pierMat = kit.paintedMaterial('nhm:pier', 32, 256, (g, W, Hp) => {
      g.fillStyle = BUFF_D;
      g.fillRect(0, 0, W, Hp);
      g.fillStyle = BLUE;
      for (let y = 0; y < Hp; y += 12) g.fillRect(0, y, W, 4);
    });
    // Tower shaft face (8.5 m wide, 36 m high).
    const towerMat = kit.paintedMaterial('nhm:tower', 256, 1024, (g, W, Hp) => {
      const Hm = 36,
        s = Hp / Hm,
        Y = (z) => Hp - z * s,
        X = (m) => m * (W / 8.5);
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      stripes(g, W, 0, Hp, 0.75 * s, 0.25 * s);
      g.fillStyle = BUFF_D;
      g.fillRect(0, 0, X(1.0), Hp);
      g.fillRect(W - X(1.0), 0, X(1.0), Hp);
      // windows stacked up the shaft
      fillArch(g, X(3.2), Y(6.2), X(2.1), Y(2.0), WIN);
      bandedArch(g, X(2.6), Y(13.5), X(3.3), Y(8.5), X(0.35), WIN);
      bandedArch(g, X(2.9), Y(20.0), X(2.7), Y(15.5), X(0.3), WIN);
      for (const z of [23, 28]) {
        fillArch(g, X(2.4), Y(z + 3.2), X(1.4), Y(z), WIN);
        fillArch(g, X(4.7), Y(z + 3.2), X(1.4), Y(z), WIN);
      }
      g.fillStyle = BLUE_D;
      for (const z of [7.2, 14.5, 21.3, 32.6]) g.fillRect(0, Y(z), W, 0.4 * s);
      // arcaded corbel table at the top
      g.fillStyle = BLUE;
      for (let k = 0; k < 12; k++) {
        g.beginPath();
        g.arc(X(0.35 + k * 0.72), Y(34.6), X(0.28), Math.PI, 0);
        g.fill();
      }
    });
    // Centrepiece between the towers: great round-arched portal and gable.
    const CW = 15.4,
      CH = 31;
    const centreMat = kit.paintedMaterial('nhm:centre', 512, 1024, (g, W, Hp) => {
      const s = Hp / CH,
        Y = (z) => Hp - z * s,
        X = (m) => m * (W / CW);
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      stripes(g, W, Y(CH), Y(0), 0.7 * s, 0.24 * s);
      g.fillStyle = BLUE_D;
      g.fillRect(0, Y(1.2), W, 1.2 * s);
      // receding orders of the portal
      const orders = [
        [9.6, BLUE],
        [8.8, BUFF_D],
        [8.0, BLUE],
        [7.2, BUFF],
        [6.4, BLUE_D],
      ];
      const cx = CW / 2,
        spring = 7.8;
      for (const [w, col] of orders)
        fillArch(g, X(cx - w / 2), Y(spring + w / 2), X(w), Y(0.4), col);
      fillArch(g, X(cx - 2.9), Y(spring + 2.9), X(5.8), Y(0.4), '#3a3328');
      // doors and tympanum glazing
      g.fillStyle = '#5a4630';
      g.fillRect(X(cx - 2.4), Y(5.2), X(4.8), 4.8 * s);
      g.fillStyle = WIN_L;
      g.fillRect(X(cx - 2.4), Y(spring + 2.4), X(4.8), (spring + 2.4 - 5.6) * s);
      // gallery of statues/arches over the portal
      g.fillStyle = BLUE_D;
      g.fillRect(0, Y(14.6), W, 0.4 * s);
      for (let k = 0; k < 7; k++) {
        fillArch(g, X(1.2 + k * 1.95), Y(18.6), X(1.25), Y(15.2), WIN);
        g.fillStyle = BLUE;
        g.fillRect(X(1.0 + k * 1.95), Y(15.2), X(1.65), 0.25 * s);
      }
      g.fillStyle = BLUE_D;
      g.fillRect(0, Y(19.4), W, 0.4 * s);
      // rose / round window in the gable
      g.beginPath();
      g.arc(X(cx), Y(23.6), X(2.4), 0, Math.PI * 2);
      g.fillStyle = BLUE;
      g.fill();
      g.beginPath();
      g.arc(X(cx), Y(23.6), X(1.9), 0, Math.PI * 2);
      g.fillStyle = WIN;
      g.fill();
      g.strokeStyle = BUFF_D;
      g.lineWidth = X(0.18);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        g.beginPath();
        g.moveTo(X(cx), Y(23.6));
        g.lineTo(X(cx + Math.cos(a) * 1.9), Y(23.6 + Math.sin(a) * 1.9));
        g.stroke();
      }
      // coping of the gable
      g.strokeStyle = BLUE_D;
      g.lineWidth = X(0.5);
      g.beginPath();
      g.moveTo(0, Y(22.3));
      g.lineTo(X(cx), Y(CH - 0.3));
      g.lineTo(W, Y(22.3));
      g.stroke();
    });

    // ---------- geometry helpers ----------
    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    /** Walls of a CCW ring with one texture tile per `bayW` metres and v 0..1 over z0..z1. */
    const texWalls = (m, ring, z0, z1, bayW, vr = [0, 1], color) => {
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 0.05) continue;
        const n = Math.max(1, Math.round(len / bayW));
        B.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [0, vr[0]],
          [n, vr[0]],
          [n, vr[1]],
          [0, vr[1]],
          color,
        );
      }
    };
    const flat = (m, ring, z, down = false) => kit.cap(B, m, [[ring]], z, { down });
    const box = (m, u, v, z0, w, d, h, a = 0) => kit.box(B, m, u, v, z0, w, d, h, a);
    const geo = (m, g, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, rz)),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    // Square pyramid (spire / pavilion roof) with apex at z0 + h.
    const pyramid = (m, u, v, z0, w, d, h) => {
      const g = new THREE.ConeGeometry(Math.SQRT1_2, 1, 4, 1, true)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI / 4);
      geo(m, g, u, v, z0 + h / 2, 0, w, d, h);
    };
    const octagon = (m, u, v, z0, r, h, rTop = r, open = false) => {
      const g = new THREE.CylinderGeometry(rTop, r, h, 8, 1, open).rotateX(Math.PI / 2);
      geo(m, g, u, v, z0 + h / 2, Math.PI / 8);
    };
    const roof = (
      ring,
      angle,
      eave,
      rise,
      kind = 'gabled',
      m = slateMat,
      wall = bandMat,
      overhang = 0.4,
    ) => kit.pitchedRoof(B, m, wall, ring, angle, eave, rise, kind, { overhang });
    // Strip along a roof slope (glazing): slope from eave line to ridge, fractions f0..f1.
    const slopeStrip = (m, u0, u1, vEave, vRidge, zE, zR, f0, f1, lift = 0.06) => {
      const P = (u, f) => [u, vEave + (vRidge - vEave) * f, zE + (zR - zE) * f + lift];
      const pts = [P(u0, f0), P(u1, f0), P(u1, f1), P(u0, f1)];
      // keep CCW seen from above/outside
      if (vRidge < vEave) pts.reverse();
      B.add(
        m,
        pts,
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    };
    // Same along a slope running in u (ridge parallel to v).
    const slopeStripU = (m, v0, v1, uEave, uRidge, zE, zR, f0, f1, lift = 0.06) => {
      const P = (v, f) => [uEave + (uRidge - uEave) * f, v, zE + (zR - zE) * f + lift];
      const pts = [P(v0, f0), P(v1, f0), P(v1, f1), P(v0, f1)];
      if (uRidge > uEave) pts.reverse();
      B.add(
        m,
        pts,
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    };
    const cresting = (u0, v0, u1, v1, z) => {
      const len = Math.hypot(u1 - u0, v1 - v0),
        a = Math.atan2(v1 - v0, u1 - u0);
      box(iron, (u0 + u1) / 2, (v0 + v1) / 2, z, len, 0.12, 0.9, a);
      for (let t = 0; t <= len; t += 1.6)
        box(iron, u0 + ((u1 - u0) * t) / len, v0 + ((v1 - v0) * t) / len, z, 0.12, 0.12, 1.4, a);
    };

    // ---------- base infill (single-storey galleries filling the light courts) ----------
    const FOOT = [
      [-103.2, 2.7],
      [-86.4, 2.3],
      [-86.1, 5.0],
      [-15.5, 5.0],
      [-15.3, -2.8],
      [16.2, -2.6],
      [16.3, 5.3],
      [87.2, 4.9],
      [87.5, 2.3],
      [104.3, 2.5],
      [104.9, 24.6],
      [104.9, 91.8],
      [102.4, 91.8],
      [102.5, 93.2],
      [78.0, 93.0],
      [78.0, 87.1],
      [53.5, 87.8],
      [53.3, 118.3],
      [-27.3, 118.4],
      [-31.5, 118.6],
      [-31.6, 124.2],
      [-40.4, 124.2],
      [-40.5, 118.2],
      [-79.4, 118.6],
      [-79.6, 121.4],
      [-101.0, 121.2],
      [-101.2, 93.8],
      [-102.6, 35.4],
    ];
    const inner = kit.offsetRing(FOOT, -0.6);
    texWalls(bandMat, inner, 0, 6.5, 4);
    flat(lead, inner, 6.5);

    // ---------- front range wings ----------
    const EAVE = 19;
    for (const [u0, u1] of [
      [-86.1, -15.5],
      [16.3, 87.2],
    ]) {
      const r = R(u0, 5.0, u1, 27);
      texWalls(wingMat, r, 0, EAVE, 7.05);
      box(blue, (u0 + u1) / 2, 4.85, EAVE - 0.1, u1 - u0, 0.6, 0.5);
      roof(r, 0, EAVE, 6.5, 'gabled');
      cresting(u0, 16, u1, 16, EAVE + 6.5);
      // projecting banded piers between the bays of the front elevation
      const nb = Math.max(1, Math.round((u1 - u0) / 7.05));
      for (let k = 0; k <= nb; k++) {
        const u = u0 + ((u1 - u0) * k) / nb;
        const pr = R(u - 0.6, 4.45, u + 0.6, 5.0);
        texWalls(pierMat, pr, 0, EAVE + 0.4, 1.2);
        box(blue, u, 4.7, EAVE + 0.4, 1.4, 0.8, 0.3);
      }
      box(buff, (u0 + u1) / 2, 4.8, 7.0, u1 - u0, 0.5, 0.4);
      box(buff, (u0 + u1) / 2, 4.8, 14.0, u1 - u0, 0.5, 0.4);
      // dormers with small gables along the front slope
      for (let u = u0 + 5; u < u1 - 4; u += 14.1) {
        const d = R(u - 1.4, 5.6, u + 1.4, 9);
        texWalls(bandMat, d, EAVE, EAVE + 2.6, 3);
        roof(d, Math.PI / 2, EAVE + 2.6, 1.6, 'gabled', slateMat, buff, 0.2);
      }
      // chimney / ventilation stacks on the ridge
      for (let u = u0 + 10; u < u1 - 5; u += 21) box(buff, u, 16, EAVE + 4, 1.6, 1.6, 4.5);
    }

    // ---------- end pavilions with steep pavilion roofs ----------
    for (const [u0, u1] of [
      [-103.2, -86.1],
      [87.2, 104.6],
    ]) {
      const r = R(u0, 2.4, u1, 20.5);
      texWalls(pavMat, r, 0, 24, 5.8);
      box(blue, (u0 + u1) / 2, 11.45, 23.6, u1 - u0 + 0.8, 18.9, 0.6);
      const cu = (u0 + u1) / 2;
      // truncated steep pavilion roof with iron cresting, small lantern
      const g = new THREE.CylinderGeometry(Math.SQRT1_2 * 0.38, Math.SQRT1_2, 1, 4, 1, false)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI / 4);
      geo(slate, g, cu, 11.45, 24.6 + 6.5, 0, u1 - u0 + 0.6, 18.7, 13);
      cresting(cu - 3.1, 11.45 - 3.4, cu + 3.1, 11.45 - 3.4, 37.6);
      cresting(cu - 3.1, 11.45 + 3.4, cu + 3.1, 11.45 + 3.4, 37.6);
      octagon(buff, cu, 11.45, 37.6, 1.5, 2.4);
      pyramid(slate, cu, 11.45, 40, 3.2, 3.2, 3.4);
      // octagonal corner turrets at the front corners
      for (const uc of [u0 + 1.2, u1 - 1.2]) {
        octagon(buff, uc, 3.4, 0, 1.35, 26.5);
        for (let z = 2; z < 26; z += 1.6) octagon(blue, uc, 3.4, z, 1.42, 0.35);
        octagon(slate, uc, 3.4, 26.5, 1.5, 4.2, 0.05, true);
      }
      // gabled dormer on the pavilion roof front
      const d = R(cu - 2.2, 2.6, cu + 2.2, 6);
      texWalls(bandMat, d, 24, 28, 3);
      roof(d, Math.PI / 2, 28, 2.4, 'gabled', slateMat, buff, 0.2);
    }

    // ---------- side ranges and north range ----------
    const ranges = [
      [R(-102.6, 20.5, -88.5, 121.0), Math.PI / 2],
      [R(89.5, 20.5, 104.6, 91.6), Math.PI / 2],
      [R(-88.5, 98, 53.2, 118.2), 0],
    ];
    for (const [r, a] of ranges) {
      texWalls(backMat, r, 0, 17, 4.2);
      roof(r, a, 17, 5, 'gabled');
    }

    // ---------- Hintze Hall: central hall with long glazed roof ----------
    {
      const r = R(-14.5, 20, 14.5, 98);
      texWalls(backMat, r, 0, 22, 4.2);
      // clerestory buttresses
      for (let v = 30; v < 96; v += 6.5)
        for (const u of [-14.9, 14.9]) box(buff, u, v, 0, 0.9, 1.2, 22.5);
      roof(r, Math.PI / 2, 22, 12, 'gabled');
      for (const [ue, ur] of [
        [-14.9, 0],
        [14.9, 0],
      ])
        slopeStripU(glass, 24, 95, ue, ur, 22, 34, 0.22, 0.86);
      cresting(0, 24, 0, 95, 34);
      // roof ribs over the glazing
      for (let v = 24; v <= 95; v += 3.55)
        for (const ue of [-14.9, 14.9]) {
          const len = Math.hypot(14.9 * 0.64, 12 * 0.64),
            sg = Math.sign(ue);
          const um = ue * (1 - 0.54),
            zm = 22 + 12 * 0.54;
          const m = new THREE.Matrix4().compose(
            new THREE.Vector3(um, v, zm + 0.1),
            new THREE.Quaternion().setFromEuler(new THREE.Euler(0, sg * Math.atan2(12, 14.9), 0)),
            new THREE.Vector3(1, 1, 1),
          );
          const g = new THREE.BoxGeometry(len, 0.18, 0.18);
          B.addGeometry(iron, g, m);
          g.dispose();
        }
    }

    // ---------- centrepiece: portal block and twin spired towers ----------
    {
      const r = R(-7.4, -2.7, 8.0, 21);
      // side and back walls
      texWalls(bandMat, r, 0, 22.3, 4);
      // painted front face including the gable (pentagon), slightly proud of the walls
      const vF = -2.75,
        u0 = -7.7,
        u1 = 7.7,
        zG = 22.3;
      const pts = [
        [u0, vF, 0],
        [u1, vF, 0],
        [u1, vF, zG],
        [0, vF, CH],
        [u0, vF, zG],
      ];
      const uv = pts.map(([u, , z]) => [(u - u0) / (u1 - u0), z / CH]);
      B.add(centreMat, pts, uv, [0, 1, 2, 0, 2, 4, 2, 3, 4]);
      roof(R(-7.4, -2.7, 8.0, 21), Math.PI / 2, zG, CH - zG, 'gabled', slateMat, buff, 0.3);
      // statue at the apex and finials
      octagon(buff, 0.3, -2.4, CH - 0.4, 0.6, 1.0);
      geo(
        stone,
        new THREE.CylinderGeometry(0.35, 0.45, 2.4, 8).rotateX(Math.PI / 2),
        0.3,
        -2.4,
        CH + 1.8,
      );
      // receding orders of the great portal in relief
      for (const [ro, ri, d, m] of [
        [4.85, 4.05, 1.1, blue],
        [4.05, 3.35, 0.75, buff],
        [3.35, 2.95, 0.4, blue],
      ]) {
        const sp = 7.8;
        const sh = new THREE.Shape();
        sh.moveTo(-ro, 0);
        sh.lineTo(-ro, sp);
        sh.absarc(0, sp, ro, Math.PI, 0, true);
        sh.lineTo(ro, 0);
        sh.lineTo(ri, 0);
        sh.lineTo(ri, sp);
        sh.absarc(0, sp, ri, 0, Math.PI, false);
        sh.lineTo(-ri, 0);
        sh.closePath();
        const eg = new THREE.ExtrudeGeometry(sh, {
          depth: d,
          bevelEnabled: false,
          curveSegments: 16,
        });
        const mm = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, -1, vF, 0, 1, 0, 0, 0, 0, 0, 1);
        B.addGeometry(m, eg, mm);
        eg.dispose();
      }
      // colonnettes flanking the portal
      for (const u of [-5.4, 5.4]) {
        geo(
          blue,
          new THREE.CylinderGeometry(0.32, 0.32, 7.6, 10).rotateX(Math.PI / 2),
          u,
          vF - 0.6,
          4.0,
        );
        box(buff, u, vF - 0.6, 7.6, 0.9, 0.9, 0.5);
      }
      // steps up to the entrance
      for (let k = 0; k < 5; k++)
        box(stone, 0.3, -3.6 - k * 0.7, 0, 13 - k * 0.2, 0.7, 1.2 - k * 0.24);
      // ramps / forecourt paving
      box(paving, 0.3, -12, 0, 26, 14, 0.12);

      for (const tu of [-11.6, 12.3]) {
        const tw = 8.4,
          tv = 1.5;
        const tr = R(tu - tw / 2, tv - tw / 2, tu + tw / 2, tv + tw / 2);
        texWalls(towerMat, tr, 0, 36, tw);
        // corner buttresses with blue bands
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ]) {
          box(buff, tu + du * (tw / 2), tv + dv * (tw / 2), 0, 1.3, 1.3, 36.5);
          for (let z = 3; z < 36; z += 3)
            box(blue, tu + du * (tw / 2), tv + dv * (tw / 2), z, 1.38, 1.38, 0.35);
        }
        box(blue, tu, tv, 35.8, tw + 1.4, tw + 1.4, 0.7);
        // belfry stage: pairs of tall round-arched openings on each face
        texWalls(bandMat, kit.offsetRing(tr, -0.4), 36.5, 44.5, 3);
        for (let k = 0; k < 4; k++) {
          const a = (k * Math.PI) / 2,
            nx = Math.sin(a),
            ny = -Math.cos(a);
          for (const off of [-1.8, 1.8]) {
            const cu = tu + nx * (tw / 2 - 0.3) + Math.cos(a) * off,
              cv = tv + ny * (tw / 2 - 0.3) + Math.sin(a) * off;
            box(darkGlass, cu, cv, 37.6, 1.7, 0.3, 4.6, a);
            // half-disc arch head (axis along the face normal)
            const m = new THREE.Matrix4().compose(
              new THREE.Vector3(cu, cv, 42.2),
              new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, a)),
              new THREE.Vector3(1, 1, 1),
            );
            const hd = new THREE.CylinderGeometry(
              0.85,
              0.85,
              0.3,
              10,
              1,
              false,
              -Math.PI / 2,
              Math.PI,
            );
            B.addGeometry(darkGlass, hd, m);
            hd.dispose();
          }
        }
        box(blue, tu, tv, 44.4, tw + 0.6, tw + 0.6, 0.8);
        // corner pinnacles at the base of the spire
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ]) {
          octagon(buff, tu + du * (tw / 2 - 0.2), tv + dv * (tw / 2 - 0.2), 44.5, 0.55, 3.2);
          octagon(
            slate,
            tu + du * (tw / 2 - 0.2),
            tv + dv * (tw / 2 - 0.2),
            47.7,
            0.62,
            2.6,
            0.02,
            true,
          );
        }
        // tall slate spire with gabled lucarnes and iron finial
        pyramid(slate, tu, tv, 45.2, tw - 0.4, tw - 0.4, 12.6);
        for (let k = 0; k < 4; k++) {
          const a = (k * Math.PI) / 2;
          const cu = tu + Math.sin(a) * 2.3,
            cv = tv - Math.cos(a) * 2.3;
          const lr = R(cu - 0.6, cv - 0.6, cu + 0.6, cv + 0.6);
          texWalls(bandMat, lr, 46.8, 48.6, 3);
          roof(lr, a + Math.PI / 2, 48.6, 1.1, 'gabled', slateMat, buff, 0.1);
        }
        geo(iron, new THREE.CylinderGeometry(0.06, 0.1, 2.4, 6).rotateX(Math.PI / 2), tu, tv, 59);
        geo(kit.mat('gold'), new THREE.SphereGeometry(0.22, 8, 6), tu, tv, 58.2);
      }
    }

    // ---------- top-lit gallery wings in the courts ----------
    const wingsW = [
      [-80, -69],
      [-59, -48],
      [-38, -27],
    ];
    const wingsE = [
      [27, 38],
      [48, 59],
      [69, 80],
    ];
    for (const [u0, u1] of wingsW) {
      const r = R(u0, 27, u1, 98);
      texWalls(bandMat, r, 6.5, 13, 4, [0.2, 1]);
      roof(r, Math.PI / 2, 13, 3.5, 'gabled');
      for (const ue of [u0 - 0.3, u1 + 0.3])
        slopeStripU(glass, 28, 97, ue, (u0 + u1) / 2, 13, 16.5, 0.5, 0.95);
    }
    for (const [u0, u1] of wingsE) {
      const r = R(u0, 27, u1, 87.5);
      texWalls(bandMat, r, 6.5, 13, 4, [0.2, 1]);
      roof(r, Math.PI / 2, 13, 3.5, 'gabled');
      for (const ue of [u0 - 0.3, u1 + 0.3])
        slopeStripU(glass, 28, 86.5, ue, (u0 + u1) / 2, 13, 16.5, 0.5, 0.95);
    }
    // small round "lantern" turrets at Hintze Hall north end
    for (const u of [-16, 16]) {
      octagon(buff, u, 98, 0, 2.2, 27);
      for (let z = 2; z < 27; z += 1.8) octagon(blue, u, 98, z, 2.28, 0.35);
      octagon(slate, u, 98, 27, 2.4, 6, 0.05, true);
    }

    // ---------- Earth Galleries / Red Zone (former Geological Museum) ----------
    {
      const r = [
        [104.9, 24.6],
        [171.9, 24.6],
        [172.2, 74.5],
        [172.9, 91.6],
        [104.9, 91.8],
      ];
      const stoneF = kit.facade('portland_stone', 1);
      kit.walls(B, stoneF, [[r]], 0, 22, { bay: 3.8, storey: 4.3 });
      texWalls(stone, r, 0, 1.6, 4);
      // cornice and attic
      const c = kit.offsetRing(r, 0.6);
      kit.walls(B, stone, [[c]], 21.2, 22.2);
      flat(stone, c, 22.2);
      flat(stone, c, 21.2, true);
      const at = kit.offsetRing(r, -2.5);
      kit.walls(B, kit.facade('portland_stone', 2), [[at]], 22.2, 26, { bay: 3.8, storey: 3.8 });
      // atrium (Earth Hall) with glazed roof
      const ar = R(122, 38, 156, 80);
      flat(lead, at, 26);
      texWalls(stone, ar, 26, 27.4, 4);
      roof(ar, Math.PI / 2, 27.4, 2.5, 'gabled', glass, stone, 0.2);
      for (let v = 39; v < 80; v += 3) box(iron, 139, v, 27.4, 34, 0.15, 0.3);
      // Exhibition Road entrance: tall recessed portal with flanking piers
      const eu = 172.3;
      box(darkGlass, eu + 0.1, 52, 0, 0.4, 9, 10.5);
      for (let z = 0.6; z < 10.5; z += 2.2) box(stone, eu + 0.2, 52, z, 0.3, 9, 0.2);
      for (const v of [46.5, 57.5]) box(stone, eu + 0.5, v, 0, 1.4, 2.0, 12.5);
      box(stone, eu + 0.5, 52, 10.5, 1.0, 13, 2.0);
      box(kit.mat('red'), eu + 1.05, 52, 11, 0.1, 7, 1.0);
      box(stone, eu + 2.5, 52, 0, 4, 16, 0.4);
      // south entrance pavilion (rounded) towards the east garden
      geo(stone, new THREE.CylinderGeometry(6.2, 6.2, 7, 28).rotateX(Math.PI / 2), 160, 18.6, 3.5);
      geo(
        darkGlass,
        new THREE.CylinderGeometry(
          6.25,
          6.25,
          4.4,
          28,
          1,
          true,
          Math.PI * 0.15,
          Math.PI * 0.7,
        ).rotateX(Math.PI / 2),
        160,
        18.6,
        3.2,
      );
      flat(lead, kit.offsetRing(R(154, 12.4, 166, 24.6), -0.2), 7.05);
    }

    // ---------- bridge over the arched gateway to the Science Museum ----------
    {
      const v0 = 91.8,
        v1 = 123.3,
        L = v1 - v0,
        H = 18,
        span = 11;
      const sh = new THREE.Shape();
      sh.moveTo(0, 0);
      sh.lineTo(L / 2 - span / 2, 0);
      sh.lineTo(L / 2 - span / 2, 6);
      sh.absarc(L / 2, 6, span / 2, Math.PI, 0, true);
      sh.lineTo(L / 2 + span / 2, 0);
      sh.lineTo(L, 0);
      sh.lineTo(L, H);
      sh.lineTo(0, H);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: 8, bevelEnabled: false, curveSegments: 12 });
      // shape x -> v, shape y -> z, extrude z -> u
      const m = new THREE.Matrix4().set(0, 0, 1, 137.4, 1, 0, 0, v0, 0, 1, 0, 0, 0, 0, 0, 1);
      B.addGeometry(stone, g, m);
      g.dispose();
      for (const v of [v0 + 6, v1 - 6]) box(darkGlass, 145.45, v, 9, 0.1, 3.5, 6);
      box(stone, 141.4, (v0 + v1) / 2, H, 8.6, L, 0.6);
    }

    // ---------- Darwin Centre: white cocoon in a glass box ----------
    {
      const r = R(-154.2, 94.0, -101.1, 121.8);
      const H = 28;
      texWalls(clearGlass, r, 0, H, 4);
      const ru = -127.6,
        rv = 107.9;
      // structure: mullions and floor transoms on the glass skin
      for (let u = -154.2; u <= -101; u += 4.42) {
        box(white, u, 94.0, 0, 0.16, 0.3, H);
        box(white, u, 121.8, 0, 0.16, 0.3, H);
      }
      for (let v = 94; v <= 122; v += 4.63) {
        box(white, -154.2, v, 0, 0.3, 0.16, H);
        box(white, -101.1, v, 0, 0.3, 0.16, H);
      }
      for (let z = 7; z < H; z += 7) {
        texWalls(white, kit.offsetRing(r, 0.15), z, z + 0.18, 30);
      }
      // glazed roof with white beams
      flat(clearGlass, r, H);
      for (let u = -152; u < -101; u += 4) box(white, u, rv, H, 0.4, 27.8, 0.6);
      kit.walls(B, white, [[kit.offsetRing(r, 0.3)]], H, H + 1.2);
      // the cocoon: elongated egg of white sprayed concrete
      const cg = new THREE.SphereGeometry(1, 40, 22);
      geo(white, cg, ru, rv - 0.5, 13.8, 0.02, 24.5, 10.5, 13.6);
      // ground floor lobby and dark base
      box(darkGlass, ru, rv, 0, 50, 25, 0.3);
      // link to the Waterhouse building
      box(clearGlass, -100.9, 108, 0, 1.2, 10, 18);
    }

    // ---------- lodge on the Queen's Gate side ----------
    {
      const r = R(-165.9, 69.7, -157.7, 84.6);
      texWalls(backMat, r, 0, 6.5, 3.2);
      roof(r, Math.PI / 2, 6.5, 4.5, 'hipped', slateMat, buff, 0.4);
      box(buff, -161.8, 77, 9.5, 1.0, 1.0, 3.5);
    }

    root.add(B.toGroup('natural_history_museum'));
    return root;
  },
};
