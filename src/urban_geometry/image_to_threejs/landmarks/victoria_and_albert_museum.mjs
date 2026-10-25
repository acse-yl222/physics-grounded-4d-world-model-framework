// Victoria and Albert Museum, Cromwell Road / Exhibition Road, South Kensington.
// Aston Webb's Cromwell Road front (1899-1909): a ~219 m range of red brick with
// Portland stone dressings and bands, first-floor windows separated by niches of
// statues, a stone frontispiece with the grand arched entrance and, above it, the
// central tower: stone octagonal stages with columns carrying an open lantern in the
// outline of an imperial crown, topped by a figure of Fame. Exhibition Road side:
// the Aston Webb Screen opened up with entrances (AL_A, 2017) onto the porcelain-
// tiled Sackler Courtyard with its tile-roofed cafe pavilion. Behind: the
// 1860s brick and terracotta ranges around the John Madejski Garden (elliptical
// pool) and the top-lit Cast Courts.
// Local frame: u along Cromwell Road (east-north-east), v towards the north-north-west,
// origin at the main entrance.
const O = [1967, -1142],
  ANG = 0.2884;

export default {
  id: 'victoria_and_albert_museum',
  name: 'Victoria and Albert Museum',
  claims: [
    '9e8e12eb-0a6c-473a-9dbb-95da1d662ab7', // Victoria and Albert Museum
    '15e1d65d-685b-4897-83bb-92870507b04a', // V&A Patisserie (Sackler Courtyard cafe pavilion)
    '35d8865e-446a-4ec3-89b0-d6a1ba5ce494', // Aston Webb Screen on Exhibition Road
    '3ebbb048-b039-47cd-8cae-0ba1defa99bc', // infill in the north courtyard notch
  ],
  references: [
    {
      title:
        'Out of the shadows: the facade and decorative sculpture of the V&A, part 1 (V&A Online Journal)',
      url: 'https://www.vam.ac.uk/content/journals/research-journal/issue-no.-7-autumn-2015/out-of-the-shadows-the-faade-and-decorative-sculpture-of-the-victoria-and-albert-museum,-part-1',
      used_for:
        '219 m red brick and Portland stone front; open lantern in the outline of an imperial crown; 32 statues in niches between first-floor windows',
    },
    {
      title: 'A grand entrance on Cromwell Road (V&A)',
      url: 'https://www.vam.ac.uk/articles/a-grand-entrance-on-cromwell-road',
      used_for:
        'tower replanned as a three-storey octagonal structure; building brought forward onto Cromwell Road',
    },
    {
      title: 'Victoria and Albert Museum - MIT Dome',
      url: 'https://dome.mit.edu/handle/1721.3/136858',
      used_for: 'column-tiered tower supporting an open crown',
    },
    {
      title: 'Entrance, V&A Museum, London (Getty Images caption)',
      url: 'https://www.gettyimages.com.au/detail/photo/entrance-v-a-museum-london-england-royalty-free-image/2195561429',
      used_for:
        'Portland stone entrance facade; statues of Victoria, Albert, and Fame on the pinnacle of the tower crown',
    },
    {
      title: 'AL_A completes tile-covered entrance and subterranean gallery for V&A (Dezeen)',
      url: 'https://www.dezeen.com/2017/06/28/ala-amanda-levete-v-a-victoria-albert-museum-exhibition-road-quarter-courtyard-gallery-london/',
      used_for:
        'Exhibition Road Quarter: porcelain-tiled Sackler Courtyard, cafe with tiled roof, refurbished Aston Webb Screen',
    },
    {
      title: 'Treasures of London - The Aston Webb Screen (Exploring London)',
      url: 'https://exploring-london.com/tag/sir-aston-webb/',
      used_for: 'screen built to hide boilers, opened up with entrances into the courtyard',
    },
    {
      title: 'Victoria and Albert Museum - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101190187-victoria-and-albert-museum-brompton-hans-town-ward',
      used_for: 'quadrangle facades (Fowke, Sykes terracotta) at the heart of the museum',
    },
  ],
  notes:
    'Footprint from Overture (courtyard garden kept as a hole). Overture h (13.6 m) is inferred; heights are estimates: ' +
    'Cromwell Road range 22 m to the balustrade, frontispiece 25 m, tower crown with Fame at ~55 m (no published height ' +
    'found). Rear ranges, Cast Courts glazed roofs and the Henry Cole Wing block are schematic. Statue niches and stone ' +
    'banding are painted; the tower is simplified to octagonal stages, a column ring and eight crown ribs.',

  build({ THREE, kit }) {
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    const B = new kit.MeshBatch();

    const BRICK = '#9b4b37',
      BRICK_D = '#83402f',
      STONE = '#e0d9c7',
      STONE_D = '#c8bfa9',
      WIN = '#29313a';
    const stone = kit.mat('portland_stone'),
      stoneD = kit.mat(STONE_D),
      brick = kit.mat(BRICK, { roughness: 0.9 }),
      slateMat = kit.roof('slate', 2),
      lead = kit.mat('lead'),
      glass = kit.mat('glass'),
      darkGlass = kit.mat('dark_glass'),
      bronze = kit.mat('bronze'),
      gold = kit.mat('gold'),
      copper = kit.mat('copper_green'),
      water = kit.mat('water'),
      paving = kit.mat('paving'),
      grass = kit.mat('grass'),
      brickF = kit.facade('red_brick', 1);

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
    // Statue in a niche (pale silhouette on a shadowed niche).
    const niche = (g, cx, yTop, w, yBot) => {
      fillArch(g, cx - w / 2, yTop, w, yBot, '#8f877a');
      g.fillStyle = STONE;
      const h = yBot - yTop;
      g.fillRect(cx - w * 0.18, yTop + h * 0.32, w * 0.36, h * 0.62);
      g.beginPath();
      g.arc(cx, yTop + h * 0.24, w * 0.16, 0, Math.PI * 2);
      g.fill();
      g.fillRect(cx - w * 0.45, yBot - h * 0.06, w * 0.9, h * 0.06);
    };

    // ---------- painted elevations ----------
    // Cromwell Road range bay: 6.6 m wide, 22 m high.
    const RH = 22,
      BAY = 6.6;
    const rangeMat = kit.paintedMaterial('va:range', 256, 852, (g, W, H) => {
      const s = H / RH,
        Y = (z) => H - z * s,
        X = (m) => m * (W / BAY);
      g.fillStyle = BRICK;
      g.fillRect(0, 0, W, H);
      // brick texture hint
      g.fillStyle = BRICK_D;
      for (let z = 0; z < RH; z += 0.3) g.fillRect(0, Y(z), W, 1);
      // Portland stone base storey with rustication
      g.fillStyle = STONE;
      g.fillRect(0, Y(6.2), W, 6.2 * s);
      g.fillStyle = STONE_D;
      for (let z = 0.6; z < 6.2; z += 0.6) g.fillRect(0, Y(z), W, 2);
      // ground floor window
      fillArch(g, X(2.0), Y(5.3), X(2.6), Y(1.2), WIN);
      // stone bands across the brick (piers)
      g.fillStyle = STONE;
      for (let z = 7.2; z < 19; z += 1.35) g.fillRect(0, Y(z), W, 0.42 * s);
      g.fillRect(0, Y(6.9), W, 0.7 * s);
      // first floor: tall window with stone surround and pediment
      g.fillStyle = STONE;
      g.fillRect(X(1.7), Y(14.6), X(3.2), 7.2 * s);
      g.fillStyle = WIN;
      g.fillRect(X(2.1), Y(13.8), X(2.4), 6.2 * s);
      g.fillStyle = '#4a545e';
      g.fillRect(X(3.25), Y(13.8), X(0.1), 6.2 * s);
      g.fillRect(X(2.1), Y(11.6), X(2.4), 0.12 * s);
      g.fillStyle = STONE_D;
      g.beginPath();
      g.moveTo(X(1.5), Y(14.6));
      g.lineTo(X(3.3), Y(15.8));
      g.lineTo(X(5.1), Y(14.6));
      g.closePath();
      g.fill();
      // statue niches at the bay edges (between first-floor windows)
      niche(g, X(0), Y(14.0), X(1.1), Y(8.4));
      niche(g, X(BAY), Y(14.0), X(1.1), Y(8.4));
      // second floor windows
      g.fillStyle = STONE;
      g.fillRect(X(2.0), Y(19.0), X(2.6), 3.0 * s);
      g.fillStyle = WIN;
      g.fillRect(X(2.3), Y(18.7), X(2.0), 2.5 * s);
      // cornice and balustrade
      g.fillStyle = STONE;
      g.fillRect(0, Y(20.4), W, 1.0 * s);
      g.fillStyle = STONE_D;
      g.fillRect(0, Y(19.5), W, 0.25 * s);
      g.fillStyle = STONE;
      g.fillRect(0, Y(RH), W, 0.3 * s);
      g.fillRect(0, Y(20.6), W, 0.2 * s);
      g.fillStyle = '#b9b09a';
      for (let k = 0; k < 14; k++) g.fillRect(X(0.25 + k * 0.46), Y(21.7), X(0.18), 1.0 * s);
    });
    // Entrance frontispiece (22 m wide, 25 m high).
    const FW = 22,
      FH = 25;
    const frontMat = kit.paintedMaterial('va:frontispiece', 512, 580, (g, W, H) => {
      const s = H / FH,
        Y = (z) => H - z * s,
        X = (m) => m * (W / FW);
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      g.fillStyle = STONE_D;
      for (let z = 0.7; z < 7; z += 0.7) g.fillRect(0, Y(z), W, 1.5);
      // great entrance arch with recessed orders
      const cx = FW / 2;
      fillArch(g, X(cx - 4.6), Y(14.4), X(9.2), Y(0), STONE_D);
      fillArch(g, X(cx - 3.9), Y(13.6), X(7.8), Y(0), '#b3aa94');
      fillArch(g, X(cx - 3.2), Y(12.9), X(6.4), Y(0), '#3b3630');
      g.fillStyle = '#5c4a38';
      g.fillRect(X(cx - 2.4), Y(5.2), X(4.8), 5.2 * s);
      g.fillStyle = '#4a5560';
      g.fillRect(X(cx - 2.4), Y(9.4), X(4.8), 3.6 * s);
      // paired columns flanking the arch
      g.fillStyle = '#d2c9b4';
      for (const x of [cx - 6.6, cx - 5.4, cx + 4.6, cx + 5.8])
        g.fillRect(X(x), Y(13), X(0.8), 12 * s);
      g.fillStyle = STONE_D;
      g.fillRect(X(cx - 7.2), Y(13.8), X(14.4), 0.8 * s);
      // sculpture niches on the outer bays
      for (const x of [2.3, FW - 2.3]) {
        niche(g, X(x), Y(11.5), X(1.8), Y(5.5));
        g.fillStyle = WIN;
        g.fillRect(X(x - 1.0), Y(19.5), X(2.0), 4 * s);
      }
      // statue group over the arch (Prince Albert) and inscription band
      niche(g, X(cx), Y(21.5), X(2.4), Y(15.2));
      g.fillStyle = STONE_D;
      g.fillRect(0, Y(22.6), W, 0.5 * s);
      g.fillStyle = '#8c8372';
      g.font = `bold ${Math.round(0.75 * s)}px serif`;
      g.textAlign = 'center';
      g.fillText('VICTORIA AND ALBERT MUSEUM', X(cx), Y(23.3));
      g.fillStyle = STONE_D;
      g.fillRect(0, Y(FH), W, 0.6 * s);
    });
    // Garden-court ranges: red brick with terracotta (buff) bands and arched windows.
    const courtMat = kit.paintedMaterial('va:court', 128, 256, (g, W, H) => {
      g.fillStyle = BRICK;
      g.fillRect(0, 0, W, H);
      g.fillStyle = '#cdb38a';
      for (let y = 20; y < H; y += 64) g.fillRect(0, y, W, 7);
      fillArch(g, 36, 40, 56, 116, WIN);
      fillArch(g, 36, 168, 56, 244, WIN);
    });
    // Porcelain tiles (Sackler Courtyard paving and cafe roof).
    const tileMat = kit.paintedMaterial(
      'va:tiles',
      256,
      256,
      (g, W, H) => {
        g.fillStyle = '#eef0ea';
        g.fillRect(0, 0, W, H);
        const r = kit.rng(0.417);
        const n = 16,
          c = W / n;
        for (let i = 0; i < n; i++)
          for (let j = 0; j < n; j++) {
            const k = r();
            g.fillStyle = k < 0.33 ? '#e3e8e3' : k < 0.66 ? '#d6dfdd' : '#f6f6f2';
            g.fillRect(i * c + 0.5, j * c + 0.5, c - 1, c - 1);
            if (k > 0.85) {
              g.strokeStyle = '#a9bfbf';
              g.beginPath();
              g.moveTo(i * c + 2, j * c + 2);
              g.lineTo(i * c + c - 2, j * c + c - 2);
              g.stroke();
            }
          }
      },
      { roughness: 0.3 },
    );

    // ---------- helpers ----------
    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    const texWalls = (m, ring, z0, z1, bayW, vr = [0, 1], closed = true) => {
      const n0 = closed ? ring.length : ring.length - 1;
      for (let k = 0; k < n0; k++) {
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
        );
      }
    };
    const flat = (m, polys, z, down = false) => kit.cap(B, m, polys, z, { down, scale: 4 });
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
    const octagon = (m, u, v, z0, r, h, rTop = r, open = false) =>
      geo(
        m,
        new THREE.CylinderGeometry(rTop, r, h, 8, 1, open).rotateX(Math.PI / 2),
        u,
        v,
        z0 + h / 2,
        Math.PI / 8,
      );
    const cyl = (m, u, v, z0, r, h, seg = 10, rTop = r) =>
      geo(m, new THREE.CylinderGeometry(rTop, r, h, seg).rotateX(Math.PI / 2), u, v, z0 + h / 2);
    const roof = (
      ring,
      angle,
      eave,
      rise,
      kind = 'gabled',
      m = slateMat,
      wall = brick,
      overhang = 0.3,
    ) => kit.pitchedRoof(B, m, wall, ring, angle, eave, rise, kind, { overhang });

    // ---------- footprint base (all ranges up to 15 m, garden kept open) ----------
    const OUTER = [
      [-70.9, 174.8],
      [-72.4, 165.7],
      [-71.5, 165.6],
      [-76.4, 134.5],
      [-77.8, 134.7],
      [-79.1, 125.9],
      [-78.5, 125.8],
      [-78.6, 124.5],
      [-49.5, 119.6],
      [-50.2, 112.8],
      [-38.7, 115.6],
      [-41.5, 86.1],
      [-83.5, 87.7],
      [-84.5, 87.9],
      [-86.9, 73.4],
      [-99.7, 3.2],
      [-86.6, 1.0],
      [-86.4, 1.9],
      [-54.7, -2.1],
      [-54.6, -2.8],
      [-40.5, -3.4],
      [-40.2, 0.4],
      [-38.3, 1.2],
      [-38.3, 2.5],
      [-11.2, 1.2],
      [-11.2, 0.0],
      [11.3, -0.4],
      [30.9, -1.0],
      [59.6, -0.1],
      [60.0, -3.5],
      [74.1, -2.0],
      [74.1, -0.8],
      [119.2, 3.4],
      [118.3, 15.8],
      [116.5, 17.3],
      [112.6, 16.9],
      [111.5, 24.1],
      [122.9, 25.5],
      [126.1, 26.1],
      [124.9, 35.2],
      [117.1, 34.5],
      [98.6, 165.2],
      [94.5, 164.7],
      [94.0, 171.0],
      [84.2, 169.6],
      [83.9, 172.9],
      [77.2, 171.9],
      [76.6, 176.1],
      [50.0, 179.7],
      [33.2, 178.7],
      [23.1, 178.5],
      [-32.9, 178.1],
      [-35.5, 153.4],
      [-47.4, 155.1],
      [-43.9, 177.3],
      [-67.7, 181.0],
      [-68.7, 174.5],
    ].reverse(); // listed clockwise in the source -> make CCW
    const GARDEN = [
      [4.6, 86.2],
      [-25.2, 86.1],
      [-21.8, 129.5],
      [-7.7, 129.2],
      [-7.1, 127.3],
      [9.2, 126.0],
      [27.2, 126.0],
      [27.2, 129.4],
      [39.9, 129.9],
      [44.9, 86.3],
      [15.5, 86.0],
      [15.5, 87.7],
      [10.3, 87.6],
      [4.6, 87.7],
    ];
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const outer = ccw(OUTER),
      hole = ccw(GARDEN).slice().reverse(); // holes clockwise
    const baseIn = kit.offsetRing(outer, -0.5);
    texWalls(courtMat, baseIn, 0, 15, 4.5);
    texWalls(courtMat, hole, 0, 15, 4.5);
    flat(lead, [[baseIn, hole]], 15);

    // ---------- Cromwell Road range ----------
    {
      // front line from the Exhibition Road corner to the east end (from the footprint)
      const front = [
        [-99.7, 3.2],
        [-86.6, 1.0],
        [-54.7, -2.1],
        [-40.5, -3.4],
        [-38.3, 1.2],
        [-11.2, 1.2],
      ];
      const frontE = [
        [11.3, -0.4],
        [30.9, -1.0],
        [59.6, -0.1],
        [60.0, -3.5],
        [74.1, -2.0],
        [119.2, 3.4],
      ];
      const D = 19;
      const westRing = [...front, [-11.2, D], [-96.6, D]];
      const eastRing = [...frontE, [118.0, D], [11.3, D]];
      for (const ring of [westRing, eastRing]) {
        texWalls(rangeMat, ring, 0, RH, BAY);
        flat(lead, [[ring]], RH - 0.6);
      }
      // projecting cornice and first-floor string course along the front line
      for (const line of [front, frontE])
        for (let k = 0; k + 1 < line.length; k++) {
          const [a0, a1] = [line[k], line[k + 1]];
          const len = Math.hypot(a1[0] - a0[0], a1[1] - a0[1]);
          if (len < 1) continue;
          const an = Math.atan2(a1[1] - a0[1], a1[0] - a0[0]);
          const nu = Math.sin(an) * 0.35,
            nv = -Math.cos(an) * 0.35;
          const mu = (a0[0] + a1[0]) / 2 + nu,
            mv = (a0[1] + a1[1]) / 2 + nv;
          box(stone, mu, mv, 20.4, len + 0.7, 0.9, 1.0, an);
          box(stone, mu, mv, 6.6, len + 0.4, 0.6, 0.6, an);
          box(stoneD, mu, mv, 0, len + 0.4, 0.7, 1.2, an);
        }
      // slate roofs behind the balustrade
      roof(R(-96, 2.5, -12, D - 1), 0, RH - 0.6, 4.5);
      roof(R(12, 1.5, 117, D - 1), 0, RH - 0.6, 4.5);
      // end and intermediate pavilions raised above the balustrade
      for (const [u, v] of [
        [-93.5, 7],
        [110.5, 9],
        [-46.5, 4],
        [67, 3],
      ]) {
        const r = R(u - 6.5, v - 6, u + 6.5, v + 6);
        texWalls(stone, kit.offsetRing(r, -0.2), RH, RH + 3.2, 4);
        box(stoneD, u, v, RH + 3.2, 13.6, 12.6, 0.5);
        roof(
          R(u - 6.3, v - 5.8, u + 6.3, v + 5.8),
          0,
          RH + 3.7,
          3.2,
          'hipped',
          slateMat,
          stone,
          0.1,
        );
      }
      // stone quoins at the Exhibition Road corner
      for (let z = 0.8; z < RH; z += 1.6) box(stone, -99.6, 3.1, z, 1.6, 1.6, 0.8, 0.0);
      // dormers on the roof slopes
      for (const [u0, u1] of [
        [-90, -16],
        [17, 112],
      ])
        for (let u = u0 + 3; u < u1; u += 6.6) {
          const d = R(u - 0.9, 4.5, u + 0.9, 7.5);
          texWalls(stone, d, RH - 0.6, RH + 1.4, 3);
          roof(d, Math.PI / 2, RH + 1.4, 1, 'gabled', slateMat, stone, 0.1);
        }
    }

    // ---------- Exhibition Road range (north of the corner) ----------
    {
      const r2 = [
        [-96.6, 19],
        [-81.6, 19],
        [-72, 87.3],
        [-84.5, 87.9],
        [-86.9, 73.4],
      ];
      texWalls(rangeMat, r2, 0, RH, BAY);
      flat(lead, [[r2]], RH - 0.6);
    }

    // ---------- entrance frontispiece and central tower ----------
    {
      const v0 = -1.6;
      // painted front face
      B.quad(
        frontMat,
        [-11, v0, 0],
        [11, v0, 0],
        [11, v0, FH],
        [-11, v0, FH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      texWalls(
        stone,
        [
          [11, v0],
          [11, 16],
          [-11, 16],
          [-11, v0],
        ],
        0,
        FH,
        4,
        [0, 1],
        false,
      );
      flat(lead, [[R(-11, v0, 11, 16)]], FH);
      box(stoneD, 0, (v0 + 16) / 2, FH - 0.2, 22.8, 18.6, 0.6);
      // balustrade and urns
      for (const u of [-10.5, -3.5, 3.5, 10.5]) {
        box(stone, u, v0 + 0.4, FH + 0.4, 1, 1, 1.4);
        cyl(stone, u, v0 + 0.4, FH + 1.8, 0.35, 1.2, 8, 0.2);
      }
      box(stone, 0, v0 + 0.4, FH + 0.4, 22, 0.4, 1.0);
      // steps
      for (let k = 0; k < 3; k++) box(stone, 0, v0 - 0.6 - k * 0.6, 0, 14 - k, 0.6, 0.6 - k * 0.18);

      const tc = [0, 8];
      // stage 1: square stone base with corner buttresses, above the frontispiece
      box(stone, tc[0], tc[1], FH, 13, 13, 9);
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [-1, 1],
        [1, 1],
      ])
        box(stoneD, tc[0] + du * 6.3, tc[1] + dv * 6.3, FH, 1.6, 1.6, 9.7);
      for (let k = 0; k < 4; k++) {
        const a = (k * Math.PI) / 2;
        box(
          darkGlass,
          tc[0] + Math.sin(a) * 6.52,
          tc[1] - Math.cos(a) * 6.52,
          FH + 1.5,
          3.0,
          0.1,
          6.0,
          a,
        );
      }
      box(stoneD, tc[0], tc[1], FH + 9, 14, 14, 0.8);
      // stage 2: octagonal drum ringed by columns (column-tiered tower)
      const z2 = FH + 9.8;
      octagon(stone, tc[0], tc[1], z2, 4.6, 8.2);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        box(
          darkGlass,
          tc[0] + Math.cos(a) * 4.3,
          tc[1] + Math.sin(a) * 4.3,
          z2 + 1.5,
          1.2,
          0.1,
          4.8,
          a + Math.PI / 2,
        );
      }
      for (let k = 0; k < 16; k++) {
        const a = (k * Math.PI) / 8;
        cyl(stone, tc[0] + Math.cos(a) * 5.6, tc[1] + Math.sin(a) * 5.6, z2, 0.32, 7.4, 8, 0.28);
      }
      octagon(stoneD, tc[0], tc[1], z2 + 7.4, 6.2, 0.9);
      // balustrade ring
      octagon(stone, tc[0], tc[1], z2 + 8.3, 6.0, 0.9, 6.0, true);
      // stage 3: smaller octagon with statues at the angles
      const z3 = z2 + 8.3;
      octagon(stone, tc[0], tc[1], z3, 3.4, 4.6);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        cyl(stone, tc[0] + Math.cos(a) * 3.9, tc[1] + Math.sin(a) * 3.9, z3, 0.28, 1.8, 6, 0.2);
      }
      octagon(stoneD, tc[0], tc[1], z3 + 4.6, 3.9, 0.6);
      // stage 4: the open imperial crown — eight curved ribs on a ring, orb and Fame
      const z4 = z3 + 5.2,
        cr = 3.4,
        ch = 6.0;
      geo(stone, new THREE.TorusGeometry(cr, 0.32, 6, 24), tc[0], tc[1], z4 + 0.3);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        const pts = [];
        for (let t = 0; t <= 1.0001; t += 0.125) {
          const r =
            cr * (1 + 0.28 * Math.sin(Math.PI * t * 0.9)) * Math.cos((t * Math.PI) / 2) ** 0.8;
          pts.push(
            new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, ch * Math.sin((t * Math.PI) / 2)),
          );
        }
        const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 10, 0.26, 5, false);
        geo(stone, tube, tc[0], tc[1], z4 + 0.3);
        // small crocket finials on the ring
        cyl(
          stone,
          tc[0] + Math.cos(a + Math.PI / 8) * cr,
          tc[1] + Math.sin(a + Math.PI / 8) * cr,
          z4 + 0.4,
          0.18,
          0.9,
          6,
          0.05,
        );
      }
      // orb, plinth and the figure of Fame
      geo(stone, new THREE.SphereGeometry(0.75, 12, 8), tc[0], tc[1], z4 + ch + 0.5);
      cyl(bronze, tc[0], tc[1], z4 + ch + 1.1, 0.35, 2.2, 8, 0.22);
      geo(bronze, new THREE.SphereGeometry(0.24, 8, 6), tc[0], tc[1], z4 + ch + 3.5);
      // wings and raised trumpet of Fame
      box(bronze, tc[0], tc[1] + 0.2, z4 + ch + 2.4, 0.9, 0.1, 1.1);
      const tr = new THREE.CylinderGeometry(0.05, 0.12, 1.3, 6).rotateX(Math.PI / 2).rotateY(0.7);
      geo(gold, tr, tc[0] + 0.45, tc[1] - 0.1, z4 + ch + 3.5);
    }

    // ---------- Aston Webb Screen and Sackler Courtyard (Exhibition Road Quarter) ----------
    {
      const a0 = [-84.0, 87.8],
        a1 = [-78.1, 124.4];
      const len = Math.hypot(a1[0] - a0[0], a1[1] - a0[1]),
        ang = Math.atan2(a1[1] - a0[1], a1[0] - a0[0]);
      const at = (t, off = 0) => [
        a0[0] + ((a1[0] - a0[0]) * t) / len - Math.sin(ang) * -off,
        a0[1] + ((a1[1] - a0[1]) * t) / len + Math.cos(ang) * -off,
      ];
      const H = 12.7;
      // piers between open bays, entablature, attic with balustrade
      const nb = 11;
      for (let k = 0; k <= nb; k++) {
        const [u, v] = at((k * len) / nb);
        box(stone, u, v, 0, 0.9, 1.4, 9.2, ang + Math.PI / 2);
        cyl(stone, ...at((k * len) / nb, -1.0), 0, 0.4, 8.8, 10, 0.36);
        box(stone, ...at((k * len) / nb, -1.0), 8.8, 1.0, 1.0, 0.4, ang);
      }
      const [mu, mv] = at(len / 2);
      box(stone, mu, mv, 9.2, 2.2, len + 1.4, 1.6, ang - Math.PI / 2);
      box(stoneD, mu, mv, 10.8, 2.5, len + 1.8, 0.5, ang - Math.PI / 2);
      box(stone, mu, mv, 11.3, 1.2, len + 1.0, H - 11.3, ang - Math.PI / 2);
      // perforated aluminium gates in some openings
      const gate = kit.mat('#a9adb0', {
        metalness: 0.6,
        roughness: 0.4,
        transparent: true,
        opacity: 0.55,
      });
      for (const k of [1, 3, 7, 9]) {
        const [u, v] = at(((k + 0.5) * len) / nb);
        box(gate, u, v, 0, 0.08, len / nb - 1.4, 4.2, ang - Math.PI / 2);
      }
      // porcelain-tiled courtyard paving
      const court = ccw([
        [-83.5, 87.7],
        [-41.5, 86.1],
        [-38.7, 115.6],
        [-50.2, 112.8],
        [-49.5, 119.6],
        [-78.6, 124.5],
      ]);
      flat(tileMat, [[court]], 0.15);
      // glazed oculus / lantern lighting the gallery below
      const ov = [-56, 96];
      cyl(glass, ov[0], ov[1], 0.15, 3.2, 0.7, 20);
      // cafe pavilion: glazed walls under a faceted tiled roof
      const cafe = ccw([
        [-63.6, 111.2],
        [-50.2, 112.8],
        [-49.5, 119.6],
        [-77.6, 124.3],
      ]);
      texWalls(darkGlass, cafe, 0, 4.2, 3);
      const c = cafe.reduce(
        (s, p) => [s[0] + p[0] / cafe.length, s[1] + p[1] / cafe.length],
        [0, 0],
      );
      const top = [c[0] - 2, c[1] + 1.5, 7.2];
      for (let k = 0; k < cafe.length; k++) {
        const a = cafe[k],
          b = cafe[(k + 1) % cafe.length];
        B.add(
          tileMat,
          [[a[0], a[1], 4.2], [b[0], b[1], 4.2], top],
          [
            [0, 0],
            [2, 0],
            [1, 1],
          ],
          [0, 1, 2],
        );
      }
      // the main museum wall facing the courtyard: new entrance glazing
      box(darkGlass, -40.2, 100, 0, 0.3, 12, 4.5, Math.atan2(29.5, 2.8) - Math.PI / 2);
    }

    // ---------- higher ranges and top-lit halls behind ----------
    // Cast Courts: two great top-lit halls in the south-east of the site.
    for (const [u0, v0, u1, v1] of [
      [62, 24, 108, 52],
      [62, 55, 104, 84],
    ]) {
      const r = R(u0, v0, u1, v1);
      texWalls(courtMat, r, 15, 24, 4.5, [0.4, 1]);
      roof(r, 0, 24, 6, 'hipped', slateMat, brick);
      const mid = (v0 + v1) / 2;
      // glazed ridge lantern
      const g = R(u0 + 6, mid - 3.5, u1 - 6, mid + 3.5);
      texWalls(glass, g, 28.3, 30.4, 3);
      roof(g, 0, 30.4, 1.6, 'gabled', glass, glass, 0.2);
    }
    // western galleries behind the Cromwell Road range
    for (const [u0, v0, u1, v1] of [
      [-82, 22, -50, 58],
      [-46, 22, -28, 60],
      [-80, 62, -46, 84],
      [-6, 66, 50, 82],
    ]) {
      const r = R(u0, v0, u1, v1);
      texWalls(courtMat, r, 15, 18, 4.5, [0.6, 1]);
      const along = u1 - u0 > v1 - v0 ? 0 : Math.PI / 2;
      roof(r, along, 18, 4, 'hipped', slateMat, brick);
      const g =
        along === 0
          ? R(u0 + 4, (v0 + v1) / 2 - 2, u1 - 4, (v0 + v1) / 2 + 2)
          : R((u0 + u1) / 2 - 2, v0 + 4, (u0 + u1) / 2 + 2, v1 - 4);
      roof(g, along, 20.6, 1.4, 'gabled', glass, glass, 0.1);
    }
    // ranges around the garden (Fowke / Sykes): pitched roofs with roof lights
    for (const [r, a] of [
      [R(-30, 132, 45, 150), 0],
      [R(-40, 84, -26, 132), Math.PI / 2],
      [R(46, 84, 60, 132), Math.PI / 2],
    ]) {
      texWalls(courtMat, r, 15, 19, 4.5, [0.5, 1]);
      roof(r, a, 19, 4.2, 'gabled', slateMat, courtMat);
    }
    for (let u = -22; u < 40; u += 12) {
      const r = R(u, 28, u + 8, 62);
      texWalls(courtMat, r, 15, 17, 4, [0.7, 1]);
      roof(r, Math.PI / 2, 17, 2.4, 'gabled', glass, brick, 0.2);
    }
    // north ranges and the Henry Cole Wing block on Exhibition Road
    {
      const hc = ccw([
        [-79.1, 125.9],
        [-50, 121],
        [-46, 154.9],
        [-43.9, 177.3],
        [-67.7, 181.0],
        [-72.4, 165.7],
        [-76.4, 134.5],
      ]);
      const hcIn = kit.offsetRing(hc, -0.3);
      texWalls(kit.facade('red_brick', 3), hcIn, 15, 24, 4.5);
      flat(lead, [[hcIn]], 24);
      roof(R(-71, 130, -51, 176), Math.PI / 2, 24, 4, 'hipped', slateMat, brick);
      const nr = R(-32, 152, 92, 172);
      texWalls(courtMat, nr, 15, 20, 4.5, [0.5, 1]);
      roof(nr, 0, 20, 4.5, 'gabled', slateMat, courtMat);
      for (let u = -25; u < 90; u += 14) box(glass, u, 162, 24.3, 8, 3, 0.3);
    }
    // notch infill (claimed small footprint)
    {
      const r = ccw([
        [-33.9, 169.2],
        [-33.4, 174.0],
        [-44.1, 175.8],
        [-44.9, 171.0],
      ]);
      texWalls(brickF, r, 0, 13, 4);
      flat(lead, [[r]], 13);
    }

    // ---------- John Madejski Garden: lawn, paving and elliptical pool ----------
    {
      const g = ccw(GARDEN);
      flat(paving, [[g]], 0.08);
      flat(grass, [[kit.offsetRing(g, -6)]], 0.14);
      const pool = new THREE.CircleGeometry(1, 40);
      geo(water, pool, 9.5, 108, 0.2, 0, 14, 9, 1);
      geo(stone, new THREE.TorusGeometry(1, 0.03, 4, 40), 9.5, 108, 0.2, 0, 14, 9, 8);
    }

    root.add(B.toGroup('victoria_and_albert_museum'));
    return root;
  },
};
