// Former Walham Green / Fulham Broadway Underground station, Fulham Road (Grade II).
// Trainshed of 1880 with a pitched glazed roof on wrought-iron trusses; the street
// entrance building (ticket hall, shopping arcade and offices) rebuilt in 1910 to the
// design of Harry W. Ford, architect to the District Railway: steel frame clad in brick
// with a brown faience facade. Superseded in 2003 by the entrance inside the Fulham
// Broadway shopping centre built alongside.
export default {
  id: 'fulham_broadway_station',
  name: 'Fulham Broadway station (former entrance and trainshed)',
  claims: ['7413b081-93d5-4773-bbd7-ae4449801f4c'],
  references: [
    {
      title:
        'Fulham Broadway Underground Station, former entrance building and trainshed - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101358569-fulham-broadway-underground-station-former-entrance-building-and-trainshed-fulham-broadway-ward',
      used_for:
        'trainshed 1880 with pitched glazed roof on wrought-iron trusses; entrance building rebuilt 1910 by Harry W Ford; steel frame clad in brick, brown faience facade; ticket hall, arcade, offices',
    },
    {
      title: 'Fulham Broadway tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Fulham_Broadway_tube_station',
      used_for:
        'renaming from Walham Green; 2003 relocation of the entrance into the shopping centre',
    },
    {
      title: 'The street entrance to Walham Green Underground Station - Historic England',
      url: 'https://historicengland.org.uk/images-books/photos/item/BL21141',
      used_for: 'street entrance (caption)',
    },
  ],
  notes:
    'Entrance block taken as the southern 8 m of the footprint facing Fulham Road (two storeys + parapet, ' +
    '11.8 m) and the trainshed as the rest; the cutting is not modelled (tracks/platform level at ground). ' +
    'Faience bay design, lettering, truss pitch and roof glazing ratio are estimates.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const a0 = (-90.29 * Math.PI) / 180,
      CX = 360.02,
      CY = -2906.73;
    const ca = Math.cos(a0),
      sa = Math.sin(a0);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca]; // u: south, v: east
    const rect = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
    const faience = kit.mat('#8a5a3c', { roughness: 0.45 });
    const faienceL = kit.mat('#a87a55', { roughness: 0.45 });
    const brick = kit.mat('#7d4d3a', { roughness: 0.9 });
    const glass = kit.mat('#2a343c', { roughness: 0.3, metalness: 0.2 });
    const glassR = kit.mat('#a9bfc8', {
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.7,
    });
    const iron = kit.mat('#4e5a5e', { roughness: 0.5, metalness: 0.5 });
    const roofM = kit.mat('#7b7f80');
    const cream = kit.mat('#efe4c6', { roughness: 0.5 });

    // ---- entrance building ------------------------------------------------------------
    const U0 = 15.2,
      U1 = 23.0,
      V0 = -11.8,
      V1 = 4.0,
      H = 11.8;
    const eb = rect(U0, U1, V0, V1);
    kit.walls(batch, brick, [[eb]], 0, H - 0.2, { bay: 1e6 });
    kit.cap(batch, roofM, [[eb]], H - 0.2);
    // faience front (u = U1, facing Fulham Road): edge from v1 to v0 has outward normal +u
    const fa = L(U1 + 0.4, V0),
      fb = L(U1 + 0.4, V1);
    const fr = rect(U1, U1 + 0.4, V0, V1);
    kit.walls(batch, faience, [[fr]], 0, H, { bay: 1e6 });
    kit.cap(batch, faience, [[fr]], H);
    kit.cornice(batch, faienceL, fr, 4.6, { height: 0.35, projection: 0.15 });
    kit.cornice(batch, faienceL, fr, H - 1.6, { height: 0.5, projection: 0.35 });
    // ground floor: wide central arch to the ticket hall flanked by shop openings
    {
      const m = L(U1 + 0.42, (V0 + V1) / 2);
      kit.box(batch, kit.mat('#1d2226'), m[0], m[1], 0, 0.06, 4.6, 3.8, a0);
      const arch = new THREE.CylinderGeometry(2.3, 2.3, 0.06, 16, 1, false, -Math.PI / 2, Math.PI);
      batch.addGeometry(
        glass,
        arch,
        new THREE.Matrix4().makeRotationZ(a0 - Math.PI / 2).setPosition(m[0], m[1], 3.8),
      );
      arch.dispose();
      const ring = new THREE.TorusGeometry(2.45, 0.18, 4, 14, Math.PI);
      batch.addGeometry(
        faienceL,
        ring,
        new THREE.Matrix4()
          .makeRotationZ(a0 + Math.PI / 2)
          .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
          .setPosition(m[0], m[1], 3.8),
      );
      ring.dispose();
      for (const v of [V0 + 2.2, V1 - 2.2]) {
        const p = L(U1 + 0.42, v);
        kit.box(batch, glass, p[0], p[1], 0.5, 0.06, 2.8, 3.2, a0);
      }
    }
    // London Underground roundels either side of the entrance arch
    for (const v of [V0 + 4.4, V1 - 4.4]) {
      const p = L(U1 + 0.75, v);
      const disc = new THREE.CylinderGeometry(0.55, 0.55, 0.06, 24);
      batch.addGeometry(
        kit.mat('#c8102e'),
        disc,
        new THREE.Matrix4().makeRotationZ(a0 + Math.PI / 2).setPosition(p[0], p[1], 4.0),
      );
      disc.dispose();
      const bar = L(U1 + 0.8, v);
      kit.box(batch, kit.mat('#10239e'), bar[0], bar[1], 3.88, 0.05, 1.4, 0.24, a0);
    }
    // first floor: arched windows in faience surrounds
    kit.windowRow(batch, fa, fb, 6.0, {
      glass,
      frame: cream,
      sill: faienceL,
      head: 'arch',
      count: 5,
      width: 1.6,
      height: 2.3,
      margin: 0.6,
      bars: 2,
      surround: 0.2,
      surroundMat: faienceL,
    });
    // pilasters
    for (let k = 0; k <= 5; k++) {
      const p = L(U1 + 0.55, V0 + 0.3 + (k * (V1 - V0 - 0.6)) / 5);
      kit.box(batch, faienceL, p[0], p[1], 0, 0.35, 0.55, H - 1.6, a0);
    }
    // lettered fascia
    const sign = kit.paintedMaterial(
      'fulham_broadway_station:fascia',
      1024,
      96,
      (c, w, h) => {
        c.fillStyle = '#6e4229';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#f1e7c9';
        c.font = 'bold 52px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('FULHAM BROADWAY STATION', w / 2, h / 2 + 3);
      },
      { roughness: 0.5 },
    );
    {
      const a = L(U1 + 0.62, V0 + 0.6),
        b = L(U1 + 0.62, V1 - 0.6);
      batch.quad(
        sign,
        [a[0], a[1], H - 1.5],
        [b[0], b[1], H - 1.5],
        [b[0], b[1], H - 0.3],
        [a[0], a[1], H - 0.3],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // parapet with a raised centre
    {
      const c = L(U1 + 0.2, (V0 + V1) / 2);
      kit.box(batch, faience, c[0], c[1], H, 0.6, 6, 1.4, a0);
      kit.box(batch, faienceL, c[0], c[1], H + 1.4, 0.8, 6.4, 0.25, a0);
    }

    // ---- trainshed ----------------------------------------------------------------------
    {
      const S0 = -23,
        S1 = U0,
        W0 = -11.8,
        W1 = 4.0,
        WH = 5.2,
        RIDGE = 10.4;
      const vm = (W0 + W1) / 2,
        half = (W1 - W0) / 2;
      for (const v of [W0, W1]) {
        const r = rect(S0, S1, v === W0 ? W0 : W1 - 0.6, v === W0 ? W0 + 0.6 : W1);
        kit.walls(batch, brick, [[r]], 0, WH, { bay: 1e6 });
        kit.cap(batch, brick, [[r]], WH);
      }
      const end = rect(S0, S0 + 0.6, W0, W1);
      kit.walls(batch, brick, [[end]], 0, WH, { bay: 1e6 });
      const zOf = (v) => WH + (RIDGE - WH) * (1 - Math.abs(v - vm) / half);
      const slope = (v0, v1, mat) => {
        const p0 = L(S0, v0),
          p1 = L(S1, v0),
          p2 = L(S1, v1),
          p3 = L(S0, v1);
        const verts = [
          [...p0, zOf(v0)],
          [...p1, zOf(v0)],
          [...p2, zOf(v1)],
          [...p3, zOf(v1)],
        ];
        const nz = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]);
        batch.add(
          mat,
          verts,
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          nz > 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2],
        );
      };
      slope(W0, W0 + 2.2, roofM);
      slope(W0 + 2.2, vm, glassR);
      slope(W1, W1 - 2.2, roofM);
      slope(W1 - 2.2, vm, glassR);
      // gable end screens
      for (const u of [S0]) {
        const a = L(u, W0),
          b = L(u, W1),
          c = L(u, vm);
        batch.add(
          brick,
          [
            [...a, WH],
            [...b, WH],
            [...c, RIDGE],
          ],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 2, 1],
        );
      }
      const rg = L((S0 + S1) / 2, vm);
      kit.box(batch, roofM, rg[0], rg[1], RIDGE - 0.1, S1 - S0, 0.8, 0.35, a0);
      // glazing bars on the roof lights and brick piers along the side walls
      for (let u = S0 + 1; u < S1; u += 1.2)
        for (const [va, vb2] of [
          [W0 + 2.2, vm],
          [W1 - 2.2, vm],
        ]) {
          const p0 = L(u, va),
            p1 = L(u, vb2);
          const z0 = zOf(va) + 0.04,
            z1 = zOf(vb2) + 0.04;
          const m = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2];
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const gb = new THREE.BoxGeometry(0.05, Math.hypot(len, z1 - z0), 0.06);
          const mt = new THREE.Matrix4()
            .makeRotationZ(a0)
            .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(z1 - z0, vb2 > va ? len : -len)))
            .setPosition(m[0], m[1], (z0 + z1) / 2);
          batch.addGeometry(iron, gb, mt);
          gb.dispose();
        }
      for (let u = S0 + 0.5; u < S1; u += 4.5)
        for (const v of [W0 - 0.15, W1 + 0.15]) {
          const p = L(u, v);
          kit.box(batch, brick, p[0], p[1], 0, 0.6, 0.3, WH + 0.2, a0);
        }
      for (const v of [W0 - 0.02, W1 + 0.02]) {
        const e0 = v < 0 ? L(S1, v) : L(S0, v),
          e1 = v < 0 ? L(S0, v) : L(S1, v);
        kit.windowRow(batch, e0, e1, 1.6, {
          glass,
          frame: cream,
          head: 'arch',
          width: 1.2,
          height: 2.0,
          bay: 4.5,
          margin: 2.0,
          bars: 1,
        });
      }
      // wrought-iron trusses
      for (let u = S0 + 3; u < S1; u += 4.5) {
        const p = L(u, vm);
        kit.box(batch, iron, p[0], p[1], WH - 0.4, 0.15, W1 - W0 - 1.2, 0.25, a0);
        for (const s of [-1, 1]) {
          const q = L(u, vm + (s * half) / 2);
          const len = Math.hypot(half, RIDGE - WH);
          const geo = new THREE.BoxGeometry(0.15, len, 0.22);
          const m = new THREE.Matrix4()
            .makeRotationZ(a0)
            .multiply(new THREE.Matrix4().makeRotationX(-s * Math.atan2(RIDGE - WH, half)))
            .setPosition(q[0], q[1], (WH + RIDGE) / 2 - 0.3);
          batch.addGeometry(iron, geo, m);
          geo.dispose();
        }
        kit.box(batch, iron, p[0], p[1], WH - 0.15, 0.12, 0.12, RIDGE - WH - 0.2, a0);
      }
      // platforms
      for (const v of [W0 + 2.0, W1 - 2.0]) {
        const p = L((S0 + S1) / 2, v);
        kit.box(batch, kit.mat('#bdb6a8'), p[0], p[1], 0, S1 - S0 - 1, 3.2, 0.9, a0);
      }
    }
    g.add(batch.toGroup('fulham_broadway_station'));
    return g;
  },
};
