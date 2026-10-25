// Shepherd's Bush Empire (O2 Shepherd's Bush Empire), Shepherd's Bush Green.
// Frank Matcham, 1903, for Oswald Stoll; BBC Television Theatre 1953-1991. Grade II.
// Unusually for Matcham an Arts and Crafts composition in terracotta, brick and
// roughcast, asymmetrical: a round corner tower (brick base, roughcast shaft,
// octagonal terracotta top stage with lantern and cupola), roughcast main
// stage with terracotta-framed windows, entrance canopy facing the Green.
export default {
  id: 'shepherds_bush_empire',
  name: "Shepherd's Bush Empire",
  claims: ['c48cc70b-bab2-4fe0-806b-238192436bd1'],
  references: [
    {
      title: 'BBC Television Theatre - British Listed Buildings (Historic England listing)',
      url: 'https://www.britishlistedbuildings.co.uk/101358593-bbc-television-theatre-shepherds-bush-green-ward',
      used_for:
        'Matcham 1903, terracotta/brick/roughcast, asymmetrical, round tower with octagonal terracotta top stage, lantern and cupola',
    },
    {
      title: "Shepherd's Bush Empire - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_Empire',
      used_for: 'history (Stoll, BBC Television Theatre), Grade II status',
    },
    {
      title: "About Us | O2 Shepherd's Bush Empire",
      url: 'https://academymusicgroup.com/o2shepherdsbushempire/about-us',
      used_for: 'tower as a skyline landmark, current O2 branding',
    },
    {
      title: 'Shepherds Bush Empire - Theatres Trust database',
      url: 'https://database.theatrestrust.org.uk/resources/theatres/show/2026',
      used_for: 'theatre type / auditorium behind the front range',
    },
  ],
  notes:
    'OSM height (8.4 m) replaced by estimates: front range 15 m, auditorium roof 19 m, fly tower 23 m, tower ~29 m to the finial. Window rhythm, gables and canopy lettering are drawn from general descriptions, not measured photos.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const b = buildings[0];
    const ring = b.polys[0][0];
    // Front (north) edge facing the Green.
    const A = [-1652.8, -310.1],
      B = [-1679.5, -319.5];
    const ang = Math.atan2(B[1] - A[1], B[0] - A[0]) + Math.PI; // east-going along the front
    const c = Math.cos(ang),
      s = Math.sin(ang);
    const nx = -s,
      ny = c; // outward normal (to the north)
    const brick = kit.mat('#8a4a37', DS),
      rough = kit.mat('#e8e0cf', DS),
      terra = kit.mat('#b9714c', DS),
      slate = kit.mat('slate', DS),
      lead = kit.mat('lead', DS),
      dark = kit.mat('dark_glass', DS),
      gold = kit.mat('gold', DS),
      blueSign = kit.mat('#1450a0', DS);

    const lower = kit.paintedMaterial(
      'sbe:lower',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#8a4a37';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,240,220,0.13)';
        for (let r = 0; r < h; r += 6) x.fillRect(0, r, w, 1);
        for (let k = 0; k < 4; k++) {
          const x0 = k * 128 + 30;
          // Terracotta-framed openings, round heads on the ground floor.
          x.fillStyle = '#c27b55';
          x.fillRect(x0 - 6, 150, 80, 106);
          x.fillStyle = '#25303a';
          x.fillRect(x0, 160, 68, 96);
          x.fillStyle = '#c27b55';
          x.fillRect(x0 - 6, 22, 80, 86);
          x.fillStyle = '#2e3d48';
          x.fillRect(x0, 30, 68, 72);
          x.fillStyle = '#d9cfbd';
          x.fillRect(x0 + 32, 30, 4, 72);
          x.fillRect(x0, 64, 68, 4);
        }
        x.fillStyle = '#c27b55';
        x.fillRect(0, 124, w, 10);
      },
      DS,
    );
    const upper = kit.paintedMaterial(
      'sbe:upper',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#e8e0cf';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.33);
        for (let k = 0; k < 900; k++) {
          x.fillStyle = `rgba(120,100,80,${0.05 + r() * 0.06})`;
          x.fillRect(r() * w, r() * h, 2, 2);
        }
        for (let k = 0; k < 4; k++) {
          const x0 = k * 128 + 24;
          x.fillStyle = '#b9714c';
          x.fillRect(x0 - 8, 140, 96, 96);
          x.fillRect(x0 - 8, 14, 96, 96);
          x.fillStyle = '#2e3d48';
          x.fillRect(x0, 148, 80, 80);
          x.fillRect(x0, 22, 80, 80);
          x.fillStyle = '#e6dccb';
          for (const m of [26, 53]) {
            x.fillRect(x0 + m, 148, 4, 80);
            x.fillRect(x0 + m, 22, 4, 80);
          }
        }
      },
      DS,
    );

    // Main range: brick ground/first floor, roughcast above, cornice.
    kit.walls(batch, lower, b.polys, 0, 7.2, { bay: 4.2, storey: 3.6 });
    kit.walls(batch, upper, b.polys, 7.2, 15, { bay: 4.2, storey: 3.9, uvBase: 7.2 });
    kit.walls(batch, terra, [[kit.offsetRing(ring, 0.25)]], 15, 15.8);
    kit.cap(batch, lead, [[kit.offsetRing(ring, 0.25)]], 15.8);
    kit.walls(batch, terra, [[kit.offsetRing(ring, 0.15)]], 7.0, 7.4);

    // Auditorium roof: hipped slate roof over the body behind the front range.
    const at = (u, v) => [A[0] + u * c + v * nx, A[1] + u * s + v * ny]; // u along front (east), v outward
    const audRing = [at(-24, -12), at(-1, -12), at(-1, -33), at(-24, -33)];
    kit.walls(batch, rough, [[audRing]], 15.8, 18.5);
    kit.pitchedRoof(batch, slate, rough, audRing, ang, 18.5, 4.5, 'hipped');
    // Fly tower at the back (south-west).
    const fly = [at(-27, -28), at(-10, -28), at(-10, -40), at(-27, -40)];
    kit.walls(batch, kit.facade('london_stock', 1), [[fly]], 15.8, 23, { bay: 6, storey: 3.6 });
    kit.pitchedRoof(batch, slate, brick, fly, ang, 23, 2.2, 'gabled');

    // Two Arts and Crafts gables on the front.
    for (const [u0, u1] of [
      [-21, -13],
      [-9.5, -3],
    ]) {
      const p0 = at(u0, 0.15),
        p1 = at(u1, 0.15),
        pm = at((u0 + u1) / 2, 0.15);
      batch.add(
        rough,
        [
          [p0[0], p0[1], 15.8],
          [p1[0], p1[1], 15.8],
          [pm[0], pm[1], 20],
        ],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      const q0 = at(u0 - 0.4, 0.4),
        q1 = at(u1 + 0.4, 0.4),
        qm = at((u0 + u1) / 2, 0.4);
      // Terracotta coping on the gable verges.
      for (const [P0, P1] of [
        [q0, qm],
        [qm, q1],
      ]) {
        const z0 = P0 === qm ? 20.3 : 15.8,
          z1 = P1 === qm ? 20.3 : 15.8;
        batch.add(
          terra,
          [
            [P0[0], P0[1], z0],
            [P1[0], P1[1], z1],
            [P1[0], P1[1], z1 + 0.5],
            [P0[0], P0[1], z0 + 0.5],
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
      // Gable window.
      const wc = at((u0 + u1) / 2, 0.25);
      kit.box(batch, dark, wc[0], wc[1], 16.3, 2.2, 0.2, 2.2, ang);
      // Pitched roof behind the gable, running back into the main roof.
      const gr = [at(u0, 0.1), at(u1, 0.1), at(u1, -10), at(u0, -10)];
      kit.pitchedRoof(batch, slate, rough, gr, ang + Math.PI / 2, 15.8, 3.6, 'gabled', {
        overhang: 0.2,
      });
    }

    // Entrance canopy with the venue name.
    const sign = kit.paintedMaterial(
      'sbe:sign',
      1024,
      64,
      (x, w, h) => {
        x.fillStyle = '#10213f';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#ffffff';
        x.font = 'bold 40px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText("O2  SHEPHERD'S BUSH EMPIRE", w / 2, h / 2 + 2);
        x.fillStyle = '#2f7fd8';
        x.beginPath();
        x.arc(70, h / 2, 22, 0, Math.PI * 2);
        x.fill();
      },
      DS,
    );
    {
      const u0 = -22,
        u1 = -2,
        dep = 3.2,
        z = 4.2;
      const p = [at(u0, 0), at(u1, 0), at(u1, dep), at(u0, dep)];
      kit.cap(batch, kit.mat('dark_steel', DS), [[p]], z + 0.9);
      kit.cap(
        batch,
        kit.mat('#f3e9c6', { emissive: '#4a3d20', side: THREE.DoubleSide }),
        [[p]],
        z,
        { down: true },
      );
      batch.quad(
        sign,
        [p[3][0], p[3][1], z],
        [p[2][0], p[2][1], z],
        [p[2][0], p[2][1], z + 0.9],
        [p[3][0], p[3][1], z + 0.9],
        [1, 0],
        [0, 0],
        [0, 1],
        [1, 1],
      );
      for (const k of [0, 1]) {
        const pp = p[k],
          qq = p[3 - k];
        batch.quad(
          sign,
          [pp[0], pp[1], z],
          [qq[0], qq[1], z],
          [qq[0], qq[1], z + 0.9],
          [pp[0], pp[1], z + 0.9],
          [0, 0],
          [0.1, 0],
          [0.1, 1],
          [0, 1],
        );
      }
      // Vertical blade sign at the west end of the front.
      const bs = at(-23.2, 1.2);
      kit.box(batch, blueSign, bs[0], bs[1], 6, 0.3, 1.6, 8, ang + Math.PI / 2);
    }

    // Round corner tower (east end).
    const tc = [-1637.3, -331.0];
    const R = 3.3;
    const add = (geo, m, z) => {
      geo.rotateX(Math.PI / 2);
      batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(tc[0], tc[1], z));
      geo.dispose();
    };
    add(new THREE.CylinderGeometry(R, R + 0.2, 8, 24, 1, true), brick, 4);
    add(new THREE.CylinderGeometry(R + 0.35, R + 0.35, 0.6, 24), terra, 8.2);
    add(new THREE.CylinderGeometry(R, R, 10, 24, 1, true), rough, 13.5);
    add(new THREE.CylinderGeometry(R + 0.4, R + 0.4, 0.7, 24), terra, 18.7);
    // Octagonal terracotta top stage with arched openings.
    add(new THREE.CylinderGeometry(R * 0.95, R * 0.95, 4.2, 8, 1, true), terra, 21.2);
    for (let k = 0; k < 8; k++) {
      const a = (k + 0.5) * (Math.PI / 4);
      const px = tc[0] + Math.cos(a) * R * 0.92,
        py = tc[1] + Math.sin(a) * R * 0.92;
      kit.box(batch, dark, px, py, 19.9, 0.25, 1.1, 2.6, a);
    }
    add(new THREE.CylinderGeometry(R + 0.2, R + 0.2, 0.5, 8), terra, 23.55);
    // Ogee cupola, lantern and finial (lead with a gilded finial).
    add(new THREE.CylinderGeometry(R * 0.35, R * 0.95, 2.4, 8), lead, 25);
    add(new THREE.CylinderGeometry(0.75, 0.75, 1.6, 8, 1, true), terra, 27);
    add(new THREE.ConeGeometry(1.05, 1.6, 8), lead, 28.6);
    add(new THREE.SphereGeometry(0.28, 8, 6), gold, 29.6);
    add(new THREE.CylinderGeometry(0.06, 0.06, 1.2, 4), gold, 30.2);
    // Windows on the tower shaft.
    for (const z of [10.5, 14.5]) {
      for (const a of [0.2, 1.2, -0.8]) {
        const px = tc[0] + Math.cos(a) * (R + 0.05),
          py = tc[1] + Math.sin(a) * (R + 0.05);
        kit.box(batch, dark, px, py, z, 0.2, 1.1, 2.2, a);
      }
    }
    g.add(batch.toGroup('shepherds_bush_empire'));
    return g;
  },
};
