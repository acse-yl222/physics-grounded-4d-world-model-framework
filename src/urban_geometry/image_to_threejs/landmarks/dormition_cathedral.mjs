// Russian Orthodox Cathedral of the Dormition and All Saints, Ennismore Gardens,
// Knightsbridge (former Anglican church of All Saints). Italian Romanesque church by Lewis
// Vulliamy, 1848-9, in brick; restored and extended 1887-97 by C. Harrison Townsend, who
// gave it a stone west front closely copied from San Zeno, Verona (sgraffito by Heywood
// Sumner on the tympanum, 1896-1903); a tall Italianate campanile (c.1860-71) rises on
// the south side to the right of the facade. Grade II*; Russian Orthodox since 1956.
export default {
  id: 'dormition_cathedral',
  name: 'Cathedral of the Dormition and All Saints',
  claims: ['6d46082c-9441-4f42-b99e-1dd229ed5b87'],
  references: [
    {
      title: 'Dormition Cathedral, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Dormition_Cathedral,_London',
      used_for:
        'west facade a close copy of San Zeno, Verona; campanile; Russian Orthodox since 1956',
    },
    {
      title: 'Russian Orthodox Church of the Assumption and All Saints - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101066842-russian-orthodox-patriarchial-church-of-the-assumption-of-all-saints-knightsbridge-and-belgravia-ward',
      used_for:
        'Grade II*; 1848-9 L Vulliamy, additions 1887-97 by Townsend; brick with stone west facade; Italian Romanesque; campanile to the south-west; rose window',
    },
    {
      title: 'All Saints, Ennismore Gardens - victorianweb.org',
      url: 'https://victorianweb.org/victorian/art/architecture/townsend/9.html',
      used_for:
        "campanile to Vulliamy's design c.1860; Heywood Sumner sgraffito and glass 1896-1903",
    },
    {
      title: 'Assumption and All Saints, Ennismore Gardens - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2013/02/03/assumption-and-all-saints-ennismore-gardens-russian-orthodox-cathedral/',
      used_for: 'tower added c.1870',
    },
    {
      title: 'Two similar churches, one in Kensington and the other in Wiltshire - Adam Yamey',
      url: 'https://adam-yamey-writes.com/tag/sourozh/',
      used_for: 'tall bell tower stands to the right of the facade seen from the street',
    },
  ],
  notes:
    'Basilican section (aisles 7.5 m, clerestory 13.5 m, nave ridge 18 m) and campanile height (34 m) are ' +
    'estimates; no dimensions were found. The campanile is placed on the south projection of the footprint about ' +
    '16 m east of the west front; brick colour, window counts and the south and east additions are assumptions. ' +
    'The San Zeno front is abstracted to pilaster strips, raking corbel arcades, a wheel window, a gabled porch ' +
    'on two columns and a painted sgraffito tympanum. An Orthodox cross is added on the west gable.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    if (!byId['6d46082c-9441-4f42-b99e-1dd229ed5b87']) return g;
    // local frame: origin at the north-west corner, u east along the nave, v north
    const ang = (9.0 * Math.PI) / 180;
    g.position.set(2153.6, -644.1, 0);
    g.rotation.z = ang;
    const brick = kit.mat('#9c5a43', { roughness: 0.9 });
    const stone = kit.mat('#ddd0b4', { roughness: 0.85 });
    const slate = kit.mat('#5b6066', { roughness: 0.8 });
    const glass = kit.mat('#3a3a48', { roughness: 0.2, metalness: 0.3 });
    const gold = kit.mat('gold');
    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ]; // CCW for u0<u1, v0<v1
    const L = 44.6,
      VN = -5.0,
      VS = -14.0,
      VA = -19.0,
      ZA = 7.5,
      ZC = 13.5,
      ZR = 18.0;
    // aisles
    for (const [a, b2] of [
      [VN, 0],
      [VA, VS],
    ]) {
      const r = R(0.6, a, L, b2);
      T.prism(brick, r, 0, ZA);
      kit.cornice(batch, stone, r, ZA - 0.4, { height: 0.4, projection: 0.2 });
    }
    // lean-to aisle roofs
    const lean = (v0, v1) => {
      const z0 = ZA,
        z1 = ZA + 2.4;
      batch.add(
        slate,
        [
          [0.6, v0, z0],
          [L, v0, z0],
          [L, v1, z1],
          [0.6, v1, z1],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        v0 > v1 ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3],
      );
    };
    lean(0.3, VN);
    lean(VA - 0.3, VS);
    // nave clerestory and roof
    const nave = R(0.6, VS, L, VN);
    kit.walls(batch, brick, [[nave]], ZA, ZC);
    kit.cornice(batch, stone, nave, ZC - 0.4, { height: 0.4, projection: 0.25 });
    T.gableRoof(slate, brick, T.edges(nave)[0], 0, L - 0.6, 0, -(VN - VS), ZC, ZR - ZC, 0.3);
    // windows: round-arched aisle and clerestory windows (north and south)
    for (const [a, b2, z, h, bay] of [
      [[L, 0], [0.6, 0], 2.6, 3.4, 4.4],
      [[0.6, VA], [L, VA], 2.6, 3.4, 4.4],
      [[L, VN], [0.6, VN], ZA + 2.6, 2.2, 4.4],
      [[0.6, VS], [L, VS], ZA + 2.6, 2.2, 4.4],
    ])
      kit.windowRow(batch, a, b2, z, {
        width: 1.2,
        height: h,
        bay,
        margin: 2.0,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 1,
      });
    // corbel table under the eaves
    for (const v of [0, VA])
      for (let u = 1.2; u < L; u += 0.9)
        kit.box(batch, stone, u, v + (v === 0 ? 0.12 : -0.12), ZA - 0.9, 0.18, 0.24, 0.5);
    // east end: chancel gable window
    kit.windowRow(batch, [L, VS + 1], [L, VN - 1], 7.5, {
      width: 2.6,
      height: 5.0,
      count: 1,
      glass,
      frame: stone,
      sill: stone,
      head: 'arch',
      bars: 2,
    });
    // south additions
    T.prism(brick, R(0.6, -21.0, 15.5, VA), 0, 6.0);
    T.prism(brick, R(22.0, -27.6, 27.0, VA), 0, 7.0);
    T.prism(brick, R(36.0, -27.4, L, VA), 0, 6.5);
    T.gableRoof(
      slate,
      brick,
      T.edges(R(36.0, -27.4, L, VA))[0],
      0,
      L - 36.0,
      0,
      -(VA + 27.4),
      6.5,
      2.6,
    );
    kit.cap(batch, kit.mat('#7f7f7b'), [[R(0.6, -21.0, 15.5, VA)]], 6.05);
    // --- campanile -------------------------------------------------------------------
    {
      const u0 = 15.5,
        v0 = -27.6,
        w = 6.5,
        H = 30.0;
      const tr = R(u0, v0, u0 + w, v0 + w);
      T.prism(brick, tr, 0, H);
      // corner pilaster strips and string courses
      for (const [u, v] of tr) kit.box(batch, brick, u, v, 0, 0.8, 0.8, H);
      for (const z of [7, 13, 19, 24])
        kit.cornice(batch, stone, tr, z, { height: 0.3, projection: 0.35 });
      // small slit windows on the shaft
      const TE = T.edges(tr);
      for (const e of TE)
        for (const z of [9, 15])
          T.win(e, 0, e.len, z, {
            width: 0.5,
            height: 1.8,
            count: 1,
            glass,
            frame: stone,
            sill: stone,
            head: 'arch',
            bars: 0,
          });
      // belfry: triple arcade each face
      for (const e of TE) {
        for (let k = 0; k < 3; k++) {
          const s = 1.0 + k * 1.75 + 0.6;
          T.ebox(kit.mat('#1e2024'), e, s - 0.55, s + 0.55, -0.02, 0.02, 24.5, 28.2);
          T.cyl(stone, ...T.at(e, s - 0.85, 0.12), 24.5, 3.0, 0.12, 0.12, 8);
        }
        for (let u = 0.4; u < e.len; u += 0.55)
          T.ebox(stone, e, u - 0.1, u + 0.1, 0, 0.25, H - 1.2, H - 0.8);
      }
      kit.cornice(batch, stone, tr, H - 0.6, { height: 0.6, projection: 0.45, steps: 2 });
      // low pyramidal roof and cross
      const c = [u0 + w / 2, v0 + w / 2];
      const pyr = new THREE.ConeGeometry(w * 0.78, 4.0, 4)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI / 4);
      batch.addGeometry(kit.mat('#9a6a4f'), pyr, T.M(c[0], c[1], H + 2.0));
      pyr.dispose();
      T.cyl(gold, c[0], c[1], H + 4.0, 2.4, 0.06, 0.06, 6);
      kit.box(batch, gold, c[0], c[1], H + 5.6, 0.1, 1.1, 0.1);
      kit.box(batch, gold, c[0], c[1], H + 5.0, 0.1, 0.7, 0.08, 0.35);
    }
    // --- San Zeno west front in stone -----------------------------------------------------
    {
      const u = 0.0,
        d = 0.6; // front slab from u=0 to u=0.6
      // central nave gable and aisle fronts
      kit.box(batch, stone, u + d / 2, (VN + VS) / 2, 0, d, VN - VS + 0.6, ZC + 0.2);
      const gtri = (v0, v1, z0, z1) => {
        const vm = (v0 + v1) / 2;
        T.tri(stone, [u, v0, z0], [u, v1, z0], [u, vm, z1]);
        T.tri(stone, [u + d, v1, z0], [u + d, v0, z0], [u + d, vm, z1]);
        batch.add(
          stone,
          [
            [u, v1, z0],
            [u + d, v1, z0],
            [u + d, vm, z1],
            [u, vm, z1],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 2, 1, 0, 3, 2],
        );
        batch.add(
          stone,
          [
            [u, v0, z0],
            [u + d, v0, z0],
            [u + d, vm, z1],
            [u, vm, z1],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      };
      gtri(VS - 0.3, VN + 0.3, ZC + 0.2, ZR + 0.6);
      for (const [a, b2] of [
        [VN, 0.3],
        [VA - 0.3, VS],
      ])
        kit.box(batch, stone, u + d / 2, (a + b2) / 2, 0, d, Math.abs(b2 - a), ZA + 0.6);
      // half-gable lean-to fronts over the aisles
      T.tri(stone, [u, 0.3, ZA + 0.6], [u, VN, ZA + 0.6], [u, VN, ZA + 3.0]);
      T.tri(stone, [u, VS, ZA + 0.6], [u, VA - 0.3, ZA + 0.6], [u, VS, ZA + 3.0]);
      // pilaster strips (lesenes)
      for (const v of [0.1, VN, (VN + VS) / 2 - 2.3, (VN + VS) / 2 + 2.3, VS, VA - 0.1])
        kit.box(batch, stone, u - 0.15, v, 0, 0.3, 0.6, v === VN || v === VS ? ZC + 0.2 : ZA + 0.6);
      // raking corbel arcades under the central gable
      for (let i = 0; i <= 12; i++) {
        const t = i / 12;
        const v = VS + (VN - VS) * t;
        const z = ZC + 0.2 + (ZR + 0.6 - ZC - 0.2) * (1 - Math.abs(2 * t - 1)) - 0.5;
        kit.box(batch, stone, u - 0.12, v, z - 0.4, 0.24, 0.22, 0.4);
      }
      // horizontal arcaded gallery band and wheel window
      for (let v = VS + 0.6; v < VN - 0.4; v += 0.8)
        T.cyl(stone, u - 0.2, v, ZA + 0.4, 1.4, 0.08, 0.08, 6);
      kit.box(batch, stone, u - 0.2, (VN + VS) / 2, ZA + 1.8, 0.4, VN - VS, 0.25);
      const wv = (VN + VS) / 2,
        wz = ZA + 4.2;
      const wheel = new THREE.TorusGeometry(2.0, 0.22, 6, 24).rotateY(Math.PI / 2);
      batch.addGeometry(stone, wheel, T.M(u - 0.15, wv, wz));
      wheel.dispose();
      const disc = new THREE.CylinderGeometry(1.9, 1.9, 0.05, 24).rotateZ(Math.PI / 2);
      batch.addGeometry(glass, disc, T.M(u - 0.05, wv, wz));
      disc.dispose();
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 8;
        kit.box(batch, stone, u - 0.15, wv, wz - 0.06, 0.12, 3.8, 0.12, 0);
        const sp = new THREE.BoxGeometry(0.12, 3.8, 0.12).rotateX(a);
        batch.addGeometry(stone, sp, T.M(u - 0.15, wv, wz));
        sp.dispose();
      }
      // aisle-front round windows
      for (const v of [VN / 2, (VS + VA) / 2])
        kit.windowRow(batch, [u, v + 0.8], [u, v - 0.8], 3.0, {
          width: 1.1,
          height: 2.6,
          count: 1,
          glass,
          frame: stone,
          sill: stone,
          head: 'arch',
        });
      // porch (prothyrum): two columns, round arch, small gable, painted sgraffito tympanum
      const pw = 4.0,
        pd = 2.6,
        pz = 5.2;
      for (const s of [-1, 1]) {
        T.cyl(stone, u - pd + 0.3, wv + (s * pw) / 2, 0.6, pz - 0.6, 0.22, 0.2, 10);
        kit.box(batch, kit.mat('#b9a98a'), u - pd + 0.3, wv + (s * pw) / 2, 0, 0.9, 0.7, 0.6); // lion plinths
      }
      kit.box(batch, stone, u - pd / 2, wv, pz, pd, pw + 0.8, 0.5);
      const pg = new THREE.CylinderGeometry(1.0, 1.0, pd, 3, 1).rotateZ(Math.PI / 2);
      pg.scale(1, (pw + 0.8) / 1.73, 1.0);
      batch.addGeometry(
        slate,
        pg,
        new THREE.Matrix4()
          .makeTranslation(u - pd / 2, wv, pz + 1.0)
          .multiply(new THREE.Matrix4().makeRotationX(Math.PI)),
      );
      pg.dispose();
      const sg = kit.paintedMaterial('dormition:sgraffito', 256, 128, (c, w, h) => {
        c.fillStyle = '#c8b48a';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#7a3b2a';
        c.beginPath();
        c.arc(w / 2, h, h * 0.95, Math.PI, 0);
        c.fill();
        c.fillStyle = '#e8dcc0';
        for (let i = 0; i < 7; i++) {
          const x = w * (0.2 + i * 0.1);
          c.beginPath();
          c.arc(x, h * 0.55, 6, 0, Math.PI * 2);
          c.fill();
          c.fillRect(x - 5, h * 0.6, 10, 30);
        }
        c.fillStyle = '#d4a944';
        c.beginPath();
        c.arc(w / 2, h * 0.3, 12, 0, Math.PI * 2);
        c.fill();
      });
      batch.quad(
        sg,
        [u - 0.02, wv + 1.8, 3.4],
        [u - 0.02, wv - 1.8, 3.4],
        [u - 0.02, wv - 1.8, 5.1],
        [u - 0.02, wv + 1.8, 5.1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      kit.box(batch, kit.mat('#3b2a1f'), u - 0.05, wv, 0, 0.1, 2.2, 3.4); // bronze doors
      for (let i = 0; i < 3; i++)
        kit.box(
          batch,
          stone,
          u - 1.0 - i * 0.4,
          wv,
          0,
          0.4 + i * 0.0,
          6.0 - i * 0.6,
          0.18 * (3 - i),
        );
      // Orthodox cross on the west gable
      T.cyl(gold, u + 0.3, wv, ZR + 0.6, 2.0, 0.05, 0.05, 6);
      kit.box(batch, gold, u + 0.3, wv, ZR + 1.9, 0.1, 1.0, 0.1);
      kit.box(batch, gold, u + 0.3, wv, ZR + 2.35, 0.1, 0.6, 0.08);
      kit.box(batch, gold, u + 0.3, wv, ZR + 1.15, 0.08, 0.7, 0.08, 0);
    }
    g.add(batch.toGroup('dormition_cathedral'));
    return g;
  },
};

// ---- local geometry helpers (modules have no imports) -------------------------------
function tools(THREE, kit, batch) {
  const ccw = (r) => {
    r = r.slice();
    if (kit.ringArea(r) < 0) r.reverse();
    return r;
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
      };
    });
  // point along edge e at distance s, offset d outward
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  // box aligned with edge e: s0..s1 along, d0..d1 outward, z0..z1
  const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
    const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(
      batch,
      m,
      p[0],
      p[1],
      z0,
      Math.max(0.01, s1 - s0),
      Math.max(0.01, d1 - d0),
      Math.max(0.01, z1 - z0),
      e.ang,
      c,
    );
  };
  const prism = (m, ring, z0, z1, opts) => {
    kit.walls(batch, m, [[ring]], z0, z1, opts);
    kit.cap(batch, m, [[ring]], z1);
  };
  const M = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
  const cyl = (m, x, y, z0, h, r0, r1 = r0, seg = 12) => {
    const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z0 + h / 2));
    g.dispose();
  };
  const lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(Math.max(0.001, r), h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z));
    g.dispose();
  };
  // windows on the sub-span s0..s1 of edge e
  const win = (e, s0, s1, z, opts) => kit.windowRow(batch, at(e, s0), at(e, s1), z, opts);
  const quad = (m, p, q, z0, z1, c) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      c,
    );
  const tri = (m, p, q, r, c) =>
    batch.add(
      m,
      [p, q, r],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
      c,
    );
  // sloped band from ring at z0 to the ring inset by d at z1 (mansards, hips); returns inner ring
  const slope = (m, ring, z0, d, z1, capTop = true) => {
    const inn = kit.offsetRing(ring, -d);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inn[(k + 1) % ring.length],
        e = inn[k];
      batch.add(
        m,
        [
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [e[0], e[1], z1],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    if (capTop) kit.cap(batch, m, [[inn]], z1);
    return inn;
  };
  // pitched gable roof over an edge-aligned rectangle: along e from s0..s1, depth d0..d1 (outward
  // negative = inward), ridge parallel to e. Gable triangles in wall material.
  const gableRoof = (roofM, wallM, e, s0, s1, d0, d1, z, rise, ov = 0.3) => {
    const dm = (d0 + d1) / 2;
    const P = (s, d, zz) => {
      const p = at(e, s, d);
      return [p[0], p[1], zz];
    };
    const A = P(s0 - ov, d0 - ov * Math.sign(d1 - d0), z),
      B = P(s1 + ov, d0 - ov * Math.sign(d1 - d0), z);
    const C = P(s1 + ov, dm, z + rise),
      D = P(s0 - ov, dm, z + rise);
    const A2 = P(s0 - ov, d1 + ov * Math.sign(d1 - d0), z),
      B2 = P(s1 + ov, d1 + ov * Math.sign(d1 - d0), z);
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    // undersides so the roof reads from below/behind
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    for (const s of [s0, s1]) {
      const p = P(s, d0, z),
        q = P(s, d1, z),
        r = P(s, dm, z + rise);
      tri(wallM, p, q, r);
      tri(wallM, q, p, r);
    }
  };
  const hasRoad = (e) => e; // placeholder for symmetry
  return { ccw, edges, at, ebox, prism, cyl, lathe, win, quad, tri, slope, gableRoof, M, hasRoad };
}

// Stucco terrace house fronts (Kensington type): rusticated raised ground floor,
// porches, first-floor balcony, moulded window surrounds, cornice, attic, mansard.
function stuccoTerrace(T, kit, batch, ring, o) {
  const { edges, at, ebox, win, cyl, slope } = T;
  const wall = o.wall ?? kit.mat('#ece6da');
  const back = o.back ?? kit.mat('#c9b48e');
  const trim = o.trim ?? kit.mat('#f6f2ea');
  const roofM = o.roofM ?? kit.mat('slate');
  const glass = o.glass ?? kit.mat('#2c3640', { roughness: 0.2, metalness: 0.3 });
  const frame = o.frame ?? kit.mat('#f4f4f0');
  const black = kit.mat('#1d1f22', { roughness: 0.5, metalness: 0.4 });
  const Z = o.levels; // floor lines e.g. [0, 1.2, 5.2, 9.4, 12.8, 15.9] ; last = main cornice
  const top = Z[Z.length - 1];
  const fronts = new Set(o.fronts);
  const E = edges(ring);
  // body
  for (const e of E) {
    const m = fronts.has(e.k) || (o.stuccoAll ?? false) ? wall : back;
    T.quad(m, e.a, e.b, 0, top);
  }
  // basement area / plinth band
  kit.cornice(batch, trim, ring, 0, { height: Z[1], projection: 0.08 });
  // string courses
  for (let i = 2; i < Z.length - 1; i++)
    kit.cornice(batch, trim, ring, Z[i] - 0.2, { height: 0.22, projection: 0.1 });
  // main cornice + blocking course
  kit.cornice(batch, trim, ring, top - 0.55, { height: 0.55, projection: 0.45, steps: 2 });
  kit.walls(batch, wall, [[ring]], top, top + 0.9);
  const pin = kit.offsetRing(ring, -0.3);
  kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + 0.9);
  kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + 0.9);
  // roof
  const zr = top + 0.6;
  let roofTop = zr;
  if (o.mansard !== false) {
    const mh = o.mansardH ?? 3.0;
    const inn = slope(roofM, pin, zr, mh * 0.35, zr + mh, false);
    const inn2 = kit.offsetRing(inn, -0.3);
    kit.cap(batch, kit.mat('lead'), [[inn]], zr + mh);
    roofTop = zr + mh;
    // dormers on fronts
    for (const e of E) {
      if (!fronts.has(e.k) || e.len < 4) continue;
      const n = Math.max(1, Math.round((e.len - 2) / (o.bay ?? 2.6)));
      for (let i = 0; i < n; i++) {
        const s = 1 + ((e.len - 2) * (i + 0.5)) / n;
        ebox(roofM, e, s - 0.75, s + 0.75, -1.6, -0.55, zr, zr + 2.2);
        ebox(trim, e, s - 0.8, s + 0.8, -1.6, -0.5, zr + 2.2, zr + 2.35);
        ebox(glass, e, s - 0.45, s + 0.45, -0.58, -0.5, zr + 0.4, zr + 1.9);
      }
    }
  } else {
    kit.cap(batch, kit.mat('#8a8a86'), [[pin]], zr);
  }
  // chimney stacks along party walls (short edges perpendicular to the front) or spaced
  let chim = o.chimneys ?? [];
  if (o.autoChimneys)
    for (const e of E)
      if (!fronts.has(e.k) && e.len > 6) {
        const p = at(e, e.len / 2, -0.7);
        chim = chim.concat([[p[0], p[1], e.ang + Math.PI / 2]]);
      }
  if (chim.length) {
    const pot = kit.mat('#b0603e');
    for (const [x, y, ang] of chim) {
      kit.box(batch, back, x, y, roofTop - 1, 0.7, 2.4, 2.4, ang);
      kit.box(batch, trim, x, y, roofTop + 1.4, 0.85, 2.6, 0.2, ang);
      for (let k = -1; k <= 1; k++)
        cyl(
          pot,
          x - Math.sin(ang) * k * 0.7,
          y + Math.cos(ang) * k * 0.7,
          roofTop + 1.6,
          0.6,
          0.14,
          0.11,
          6,
        );
    }
  }
  // fenestration
  const bay = o.bay ?? 2.6;
  for (const e of E) {
    if (e.len < 1.6) continue;
    const front = fronts.has(e.k);
    for (let s = 1; s < Z.length - 1; s++) {
      const h = Z[s + 1] - Z[s];
      const first = s === 2;
      const opts = front
        ? {
            width: 1.15,
            height: Math.min(h - 1.0, first ? 2.9 : 2.3),
            bay,
            margin: 0.7,
            glass,
            frame,
            sill: trim,
            surround: 0.16,
            surroundMat: trim,
            head: first ? 'pediment' : s === 1 ? 'lintel' : 'lintel',
            bars: 1,
          }
        : {
            width: 1.0,
            height: Math.min(h - 1.0, 2.0),
            bay: bay + 0.6,
            margin: 0.8,
            glass,
            frame,
            sill: trim,
            head: 'none',
            bars: 1,
          };
      if (!front && o.plainBack === 'blank') continue;
      win(e, 0, e.len, Z[s] + (first ? 0.25 : 0.7), opts);
    }
    if (!front) continue;
    // rusticated ground floor: horizontal grooves
    for (let z = Z[1] + 0.5; z < Z[2] - 0.3; z += 0.5)
      ebox(trim, e, 0, e.len, 0, 0.06, z, z + 0.08);
    // first-floor balcony with balustrade
    if (o.balcony !== false) {
      ebox(trim, e, 0.2, e.len - 0.2, 0, 0.9, Z[2] - 0.22, Z[2]);
      kit.balustrade(batch, trim, [at(e, 0.3, 0.8), at(e, e.len - 0.3, 0.8)], Z[2], {
        height: 0.95,
        spacing: 0.32,
      });
    }
    // area railings at pavement edge
    if (o.railings !== false) {
      for (let s = 0.2; s < e.len; s += 0.25)
        ebox(black, e, s - 0.015, s + 0.015, 2.4, 2.43, 0, 1.1);
      ebox(black, e, 0, e.len, 2.38, 2.45, 1.05, 1.1);
    }
  }
  // porches
  for (const [k, s] of o.porches ?? []) {
    const e = E[k];
    const w = 2.4,
      z0 = Z[1],
      zc = Z[2] - 0.3;
    for (const ds of [-w / 2, w / 2]) cyl(trim, ...at(e, s + ds, 1.9), z0, zc - z0, 0.22, 0.2, 10);
    for (const ds of [-w / 2, w / 2]) ebox(trim, e, s + ds - 0.2, s + ds + 0.2, 0, 0.4, z0, zc);
    ebox(trim, e, s - w / 2 - 0.35, s + w / 2 + 0.35, 0, 2.3, zc, Z[2] - 0.22);
    // steps up from pavement across the area
    for (let i = 0; i < 5; i++)
      ebox(trim, e, s - 0.9, s + 0.9, 1.6 + i * 0.3, 2.5 + 0.3 * i, 0, z0 - i * (z0 / 5));
    ebox(kit.mat('#1f2a30'), e, s - 0.6, s + 0.6, 0, 0.05, z0, zc - 0.5);
  }
  return { top, roofTop };
}

// Generic masonry block: walls, storey windows on every edge long enough, string
// courses, cornice, parapet and a flat or slated (mansard / hipped) roof.
function masonryBlock(T, kit, batch, ring, o) {
  const wall = o.wall,
    trim = o.trim ?? wall;
  const Z = o.levels;
  const top = Z[Z.length - 1];
  const E = T.edges(ring);
  for (const e of E) T.quad(o.wallFor ? o.wallFor(e) : wall, e.a, e.b, 0, top);
  if (o.plinth) kit.cornice(batch, trim, ring, 0, { height: o.plinth, projection: 0.08 });
  for (const z of o.bands ?? [])
    kit.cornice(batch, trim, ring, z, { height: 0.25, projection: 0.1 });
  kit.cornice(batch, trim, ring, top - (o.corniceH ?? 0.45), {
    height: o.corniceH ?? 0.45,
    projection: o.corniceP ?? 0.35,
    steps: 2,
  });
  const par = o.parapet ?? 0.8;
  const pin = kit.offsetRing(ring, -0.3);
  if (par > 0) {
    kit.walls(batch, wall, [[ring]], top, top + par);
    kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + par);
    kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + par);
  }
  let roofTop = top;
  if (o.roof === 'slope') {
    const inn = T.slope(
      o.roofM ?? kit.mat('slate'),
      pin,
      top + 0.2,
      o.roofInset ?? 2.5,
      top + (o.roofRise ?? 3.5),
      false,
    );
    kit.cap(batch, kit.mat('lead'), [[inn]], top + (o.roofRise ?? 3.5));
    roofTop = top + (o.roofRise ?? 3.5);
  } else kit.cap(batch, o.roofM ?? kit.mat('#8b8b87'), [[pin]], top + 0.15);
  for (const e of E) {
    if (e.len < (o.minEdge ?? 2.5)) continue;
    for (let s = 0; s < Z.length - 1; s++) {
      const w = typeof o.win === 'function' ? o.win(s, e, Z[s + 1] - Z[s]) : o.win;
      if (!w) continue;
      T.win(e, 0, e.len, Z[s] + (w.sillOff ?? 0.9), w);
    }
  }
  return { top, roofTop, E };
}

// Frame facade: brick piers proud of the wall, concrete floor bands, metal windows between.
function pierFrame(T, kit, batch, e, z0, z1, storey, o) {
  const n = Math.max(1, Math.round(e.len / (o.bay ?? 3.2)));
  for (let k = 0; k <= n; k++) {
    const s = (k * e.len) / n;
    T.ebox(
      o.pier,
      e,
      Math.max(0, s - (o.pierW ?? 0.3)),
      Math.min(e.len, s + (o.pierW ?? 0.3)),
      -0.05,
      o.pierD ?? 0.3,
      z0,
      z1,
    );
  }
  for (let z = z0; z < z1 - 0.5; z += storey) {
    T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z, z + (o.bandH ?? 0.4));
    for (let k = 0; k < n; k++) {
      const s0 = (k * e.len) / n + (o.pierW ?? 0.3),
        s1 = ((k + 1) * e.len) / n - (o.pierW ?? 0.3);
      if (s1 - s0 < 0.4) continue;
      const zt = Math.min(z1, z + storey);
      if (o.spandrel)
        T.ebox(
          o.spandrel,
          e,
          s0,
          s1,
          0.0,
          0.07,
          z + (o.bandH ?? 0.4),
          z + (o.bandH ?? 0.4) + o.spandrelH,
        );
      const g0 = z + (o.bandH ?? 0.4) + (o.spandrel ? o.spandrelH : 0);
      T.ebox(o.glass, e, s0, s1, 0.01, 0.05, g0, zt);
      const m = Math.max(1, Math.round((s1 - s0) / (o.mullion ?? 1.1)));
      for (let j = 1; j < m; j++) {
        const s = s0 + ((s1 - s0) * j) / m;
        T.ebox(o.frame, e, s - 0.035, s + 0.035, 0.03, 0.1, g0, zt);
      }
      T.ebox(o.frame, e, s0, s1, 0.03, 0.1, g0 + (zt - g0) * 0.62, g0 + (zt - g0) * 0.62 + 0.06);
    }
  }
  T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z1 - 0.1, z1 + 0.3);
}

// Clip a ring to the half-plane n . p >= c (Sutherland-Hodgman).
function clipHalf(ring, n, c) {
  const out = [];
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    const fp = n[0] * p[0] + n[1] * p[1] - c,
      fq = n[0] * q[0] + n[1] * q[1] - c;
    if (fp >= 0) out.push(p);
    if (fp * fq < 0) {
      const t = fp / (fp - fq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
}
