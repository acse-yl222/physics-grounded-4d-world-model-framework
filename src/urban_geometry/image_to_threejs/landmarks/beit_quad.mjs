// Beit Quadrangle: Imperial College Union and Beit Hall, Prince Consort Road (Sir Aston
// Webb; Union building 1910-11, east, west, north and south ranges of the quad added
// 1912-1931). Red brick Edwardian Tudor-style ranges with Portland stone dressings
// (mullioned windows, string courses, coped parapets) under steep slate roofs with
// dormers and chimney stacks, enclosing a courtyard entered through a stone archway
// on Prince Consort Road whose pediment carries the Imperial College coat of arms.
export default {
  id: 'beit_quad',
  name: 'Beit Quad (Imperial College Union and Beit Hall)',
  claims: [
    '0a73225b-2a74-4c94-a906-3845d038da31', // Imperial College Union (north range)
    '5a9ce829-61dc-447f-a41d-2307b207d1ff', // Beit Hall (east, south, west ranges)
  ],
  references: [
    {
      title: 'Beit Hall - Wikipedia',
      url: 'https://www.Wikipedia.com/wiki/Beit_Hall',
      used_for: 'Aston Webb design, built 1910; Union 1910-11, quad ranges 1912-1931',
    },
    {
      title: 'About: Beit Hall - DBpedia',
      url: 'https://dbpedia.org/page/Beit_Hall',
      used_for: 'history and capacity',
    },
    {
      title: 'A Quick Tour of the Union Bar - PocketSights',
      url: 'https://pocketsights.stqry.com/tour/53093/preview',
      used_for:
        'archway with the Imperial College coat of arms in the pediment above the entrance; Tudor style',
    },
    {
      title: "Design for Students' Union, Imperial College - RIBApix",
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/design-for-students-union-imperial-college-kensington-london-perspective-of-entrance-facade/posterid/RIBA35495.html',
      used_for: "Aston Webb's entrance facade design",
    },
  ],
  notes:
    'No listing text with materials was returned by search; the red brick with Portland stone dressings, ' +
    "slate roofs, dormers and chimneys follow the well-known appearance of the quad and Webb's Imperial work " +
    'and are approximate. Ranges are split into hipped-roof rectangles fitted to the footprints; eaves at ' +
    '~13.5 m (Union 14.5 m) so ridges match the footprint heights (16.8 / 17.8 m). Gateway proportions estimated.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const union = byId['0a73225b-2a74-4c94-a906-3845d038da31'];
    const beit = byId['5a9ce829-61dc-447f-a41d-2307b207d1ff'];

    // Red brick with stone-mullioned cross windows and string courses (4 bays x 2 storeys).
    const brick = kit.paintedMaterial('beit_quad:brick', 512, 512, (c, w, h) => {
      const r = kit.rng(1910);
      c.fillStyle = '#9a4f3a';
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 6)
        for (let x = (y / 6) % 2 ? -8 : 0; x < w; x += 16) {
          const k = 0.86 + r() * 0.22;
          c.fillStyle = `rgb(${Math.round(154 * k)},${Math.round(79 * k)},${Math.round(58 * k)})`;
          c.fillRect(x + 1, y + 1, 14, 4);
        }
      const sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        // stone string course at sill level
        c.fillStyle = '#dcd5c3';
        c.fillRect(0, y0 + sh - 22, w, 9);
        for (let b = 0; b < 4; b++) {
          const x0 = b * (w / 4) + 26,
            ww = w / 4 - 52;
          const wy = y0 + 34,
            wh = sh - 70;
          // stone surround
          c.fillStyle = '#dcd5c3';
          c.fillRect(x0 - 7, wy - 9, ww + 14, wh + 16);
          c.fillStyle = '#28323a';
          c.fillRect(x0, wy, ww, wh);
          c.fillStyle = 'rgba(160,175,185,0.35)';
          c.fillRect(x0, wy, ww, wh * 0.3);
          // mullion + transom (cross window) and leaded glazing bars
          c.fillStyle = '#dcd5c3';
          c.fillRect(x0 + ww / 2 - 4, wy, 8, wh);
          c.fillRect(x0, wy + wh * 0.32, ww, 7);
          c.fillStyle = 'rgba(220,214,200,0.45)';
          for (let q = 1; q < 4; q++) c.fillRect(x0, wy + (q * wh) / 4, ww, 1);
        }
      }
    });
    const stone = kit.mat('portland_stone');
    const slate = kit.mat('#4f565d', { roughness: 0.8 });
    const brickSolid = kit.mat('#93503b');
    const dark = kit.mat('#20272c');

    const unionRing = union.polys[0][0];
    const beitRing = beit.polys[0][0];
    const eaveB = 13.5,
      eaveU = 14.5;
    // Walls of the actual footprints.
    kit.walls(batch, brick, [[beitRing]], 0, eaveB, { bay: 3.6, storey: 3.375 });
    kit.walls(batch, brick, [[unionRing]], 0, eaveU, { bay: 3.6, storey: 3.625 });
    // Stone plinth and coped parapet band.
    kit.walls(batch, stone, [[kit.offsetRing(beitRing, 0.12)]], 0, 1.0);
    kit.walls(batch, stone, [[kit.offsetRing(unionRing, 0.12)]], 0, 1.0);
    kit.walls(batch, stone, [[kit.offsetRing(beitRing, 0.15)]], eaveB - 0.5, eaveB + 0.3);
    kit.walls(batch, stone, [[kit.offsetRing(unionRing, 0.15)]], eaveU - 0.5, eaveU + 0.3);
    kit.cap(batch, kit.mat('#7d7f80'), [[beitRing]], eaveB + 0.05);
    kit.cap(batch, kit.mat('#7d7f80'), [[unionRing]], eaveU + 0.05);

    // Hipped slate roofs on rectangles fitted to each range.
    const ranges = [
      {
        ring: [
          [1513, -731],
          [1589, -724],
          [1588, -714.5],
          [1512.5, -721],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // south
      {
        ring: [
          [1514.5, -721],
          [1531, -719.5],
          [1527.6, -684],
          [1512, -685],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // west
      {
        ring: [
          [1571.5, -716],
          [1588, -715],
          [1583.5, -678.5],
          [1569.5, -680],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // east
      {
        ring: [
          [1509.5, -691],
          [1517.5, -691],
          [1517, -676],
          [1509.5, -677],
        ],
        eave: eaveB,
        rise: 2.4,
      }, // north-west wing
      {
        ring: [
          [1510.5, -667],
          [1581, -659.5],
          [1582, -678.5],
          [1511, -676],
        ],
        eave: eaveU,
        rise: 3.25,
      }, // Union, north
    ];
    const dormerRoofs = [];
    for (const R of ranges) {
      const ring = kit.ringArea(R.ring) < 0 ? R.ring.slice().reverse() : R.ring;
      const fr = kit.ringFrame(ring);
      const res = kit.pitchedRoof(
        batch,
        slate,
        brickSolid,
        ring,
        fr.angle,
        R.eave + 0.3,
        R.rise,
        'hipped',
        { overhang: 0.2 },
      );
      dormerRoofs.push({ fr, R, res });
    }
    // Dormers along both slopes and chimney stacks on the ridges.
    for (const { fr, R } of dormerRoofs) {
      if (fr.length < 20) continue;
      const ca = Math.cos(fr.angle),
        sa = Math.sin(fr.angle);
      const at = (u, v) => [fr.cx + u * ca - v * sa, fr.cy + u * sa + v * ca];
      const n = Math.floor((fr.length - 8) / 5.4);
      for (let i = 0; i < n; i++) {
        const u = -((n - 1) * 5.4) / 2 + i * 5.4;
        for (const side of [-1, 1]) {
          const v = side * (fr.width / 2 - 1.6);
          const [x, y] = at(u, v);
          kit.box(batch, stone, x, y, R.eave + 0.3, 2.0, 1.4, 2.0, fr.angle);
          const [wx, wy] = at(u, v + side * 0.72);
          kit.box(batch, dark, wx, wy, R.eave + 0.6, 1.2, 0.05, 1.3, fr.angle);
          kit.box(batch, slate, x, y, R.eave + 2.3, 2.3, 1.7, 0.3, fr.angle);
        }
      }
      for (const u of [-fr.length / 2 + 7, 0, fr.length / 2 - 7]) {
        const [x, y] = at(u, 0);
        kit.box(batch, brickSolid, x, y, R.eave + R.rise - 0.5, 1.2, 3.2, 2.8, fr.angle);
        kit.box(batch, stone, x, y, R.eave + R.rise + 2.3, 1.4, 3.4, 0.3, fr.angle);
      }
    }

    // Stone gateway on Prince Consort Road: frontispiece with arched entrance, flanking
    // pilasters, a raised pediment carrying the coat of arms.
    const front = [
      [1510, -667],
      [1581, -659],
    ];
    const fx = front[1][0] - front[0][0],
      fy = front[1][1] - front[0][1];
    const fl = Math.hypot(fx, fy);
    const ex = fx / fl,
      ey = fy / fl,
      nx = -ey,
      ny = ex; // outward (north): left of the eastward front line
    const ang = Math.atan2(ey, ex);
    const mid = [(front[0][0] + front[1][0]) / 2, (front[0][1] + front[1][1]) / 2];
    const G = (s, t) => [mid[0] + ex * s + nx * t, mid[1] + ey * s + ny * t];
    const GW = 11,
      GH = eaveU + 3.2;
    {
      const [x, y] = G(0, 0.6);
      kit.box(batch, stone, x, y, 0, GW, 1.4, GH, ang);
      // pilasters / buttresses
      for (const s of [-GW / 2 - 0.4, GW / 2 + 0.4]) {
        const [px, py] = G(s, 0.8);
        kit.box(batch, stone, px, py, 0, 1.1, 1.8, GH + 1.6, ang);
        const [qx, qy] = G(s, 0.8);
        kit.box(batch, stone, qx, qy, GH + 1.6, 0.6, 0.6, 1.4, ang); // finials
      }
    }
    // Arched opening (dark) on the outer face.
    const archMat = dark;
    const AW = 4.6,
      AH = 6.2;
    {
      const [x, y] = G(0, 1.33);
      kit.box(batch, archMat, x, y, 0, AW, 0.06, AH - AW / 2, ang);
      const semi = new THREE.CircleGeometry(AW / 2, 16, 0, Math.PI);
      const m = new THREE.Matrix4()
        .makeRotationZ(ang + Math.PI)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      m.setPosition(x + nx * 0.04, y + ny * 0.04, AH - AW / 2);
      batch.addGeometry(archMat, semi, m);
    }
    // Pediment above the parapet: triangular stone gable with a coat-of-arms panel.
    {
      const s0 = -GW / 2,
        s1 = GW / 2,
        t0 = -0.1,
        t1 = 1.3;
      const z0 = GH,
        z1 = GH + 3.0;
      const A = (s, t, z) => {
        const [x, y] = G(s, t);
        return [x, y, z];
      };
      batch.add(
        stone,
        [A(s1, t1, z0), A(s0, t1, z0), A(0, t1, z1)],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        stone,
        [A(s0, t0, z0), A(s1, t0, z0), A(0, t0, z1)],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      batch.quad(
        stone,
        A(s0, t1, z0),
        A(s0, t0, z0),
        A(0, t0, z1),
        A(0, t1, z1),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        stone,
        A(s1, t0, z0),
        A(s1, t1, z0),
        A(0, t1, z1),
        A(0, t0, z1),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    const arms = kit.paintedMaterial('beit_quad:arms', 128, 128, (c, w, h) => {
      c.fillStyle = '#d9d1bd';
      c.fillRect(0, 0, w, h);
      // shield: blue field, gold chief with a lion, open book in base (simplified)
      c.fillStyle = '#2a4f86';
      c.beginPath();
      c.moveTo(24, 16);
      c.lineTo(104, 16);
      c.lineTo(104, 70);
      c.quadraticCurveTo(104, 108, 64, 120);
      c.quadraticCurveTo(24, 108, 24, 70);
      c.closePath();
      c.fill();
      c.fillStyle = '#c9a54a';
      c.fillRect(24, 16, 80, 26);
      c.fillStyle = '#f2efe6';
      c.fillRect(42, 66, 44, 22);
      c.fillStyle = '#9a3a2a';
      c.fillRect(60, 22, 10, 14);
    });
    {
      const [x, y] = G(0, 1.32);
      const z = GH - 3.6;
      const a = [x - ex * 1.4, y - ey * 1.4],
        b = [x + ex * 1.4, y + ey * 1.4];
      // faces outward (north): travel westward (b -> a) so the outward side is on the right
      batch.quad(
        arms,
        [b[0], b[1], z],
        [a[0], a[1], z],
        [a[0], a[1], z + 2.8],
        [b[0], b[1], z + 2.8],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // Upper windows on the frontispiece (stone-mullioned oriel band).
    {
      const [x, y] = G(0, 1.34);
      for (const z of [AH + 1.6, AH + 4.6]) kit.box(batch, archMat, x, y, z, 5.6, 0.05, 2.0, ang);
      for (const s of [-1.4, 0, 1.4]) {
        const [mx, my] = G(s, 1.36);
        kit.box(batch, stone, mx, my, AH + 1.6, 0.25, 0.08, 5.0, ang);
      }
    }
    // Paved courtyard and the passage through the north range.
    const quad = [
      [1532, -719],
      [1572, -715],
      [1569, -686],
      [1574, -685],
      [1573, -679],
      [1528, -683],
    ];
    kit.cap(
      batch,
      kit.mat('paving'),
      [[kit.ringArea(quad) < 0 ? quad.slice().reverse() : quad]],
      0.04,
    );

    g.add(batch.toGroup('beit_quad'));
    return g;
  },
};
