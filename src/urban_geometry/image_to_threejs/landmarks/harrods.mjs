// Harrods, Brompton Road, Knightsbridge (C. W. Stephens, 1901-05; Basil Street
// elevation rebuilt by Louis D. Blanc 1929-30). Island block faced in pinky-buff
// (salmon) Doulton terracotta: two lower storeys of large display windows under
// Harrods-green awnings, four storeys of pilastered bays above, a heavy cornice and
// balustrade, copper mansard attics with dormers at the corners and the four-bay
// pavilions, octagonal cupolas on the corners and the octagonal terracotta-ribbed
// dome with dormers/lunettes and a cupola over the centre of the Brompton Road front
// (bay rhythm 2:4:3:3:3:4:2).
export default {
  id: 'harrods',
  name: 'Harrods',
  claims: ['1206a894-cc7b-4c26-9f6d-5c7ab5ed6e58'],
  references: [
    {
      title: 'Harrods - Wrenn Report (Historic England listing text)',
      url: 'https://www.thewrennreport.co.uk/building/E60000194-22da2404-ff8f-451a-bb6d-4f11f5b72f61/harrods',
      used_for:
        'pinky-buff Doulton terracotta, two lower storeys of display windows plus four storeys, octagonal dome with terracotta ribs, dormers, lunettes and cupola; corner cupolas; copper mansard attics; 2:4:3:3:3:4:2 bays',
    },
    {
      title: 'Harrods - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=1294346',
      used_for: 'C. W. Stephens 1901-05; Basil Street elevation by Louis D. Blanc 1929-30',
    },
    {
      title: 'Architectural sculpture - Victorian Web',
      url: 'https://victorianweb.org/sculpture/architectural/6.html',
      used_for: 'salmon-pink Doulton block terracotta Brompton Road facade',
    },
    {
      title: 'Harrods awnings - Make Architects',
      url: 'https://makearchitects.com/?p=12748',
      used_for: 'straight traditional awnings in Harrods green with gold lettering',
    },
  ],
  notes:
    'Overture height (9.9 m) is far too low; cornice set at 24 m, balustrade 26-27 m, mansards to ~30 m, corner ' +
    'cupolas ~38 m and dome lantern ~46 m, proportioned from the storey count in the listing. Dome placed on the ' +
    'Overture round building part. Pavilion/mansard positions follow the 2:4:3:3:3:4:2 rhythm on Brompton Road; ' +
    'on Hans Road only the corner and one central attic are modelled. Facade is a painted generic Stephens bay.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const b = buildings[0];
    const ring = b.polys[0][0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();

    const TC = '#d49b78';
    const terracotta = kit.mat(TC, { roughness: 0.7 });
    const terracottaLight = kit.mat('#d7a483', { roughness: 0.7 });
    const copperG = kit.mat('copper_green');
    const leadM = kit.mat('lead');
    const gold = kit.mat('gold');
    const awningM = kit.mat('#1f4a35', { roughness: 0.8, side: THREE.DoubleSide });
    const dark = kit.mat('dark_glass');

    // Facade: one tile = 4 bays x full 24 m height (v = z / 24).
    const facade = kit.paintedMaterial('harrods:elevation', 512, 1024, (c, w, h) => {
      const r = kit.rng(0.3141);
      const Y = (z) => h - (z / 24) * h; // z metres -> canvas y
      c.fillStyle = TC;
      c.fillRect(0, 0, w, h);
      // block joints
      c.fillStyle = 'rgba(120,70,50,0.18)';
      for (let z = 0; z < 24; z += 0.6) c.fillRect(0, Y(z), w, 1);
      for (let i = 0; i < 400; i++) {
        c.fillStyle = `rgba(255,230,210,${0.05 + r() * 0.06})`;
        c.fillRect(r() * w, r() * h, 6 + r() * 10, 3);
      }
      const bw = w / 4;
      const win = (
        x0,
        z0,
        z1,
        ww,
        { arch = false, frame = '#5a4434', glass = '#46586a', bars = 1 } = {},
      ) => {
        const y0 = Y(z1),
          y1 = Y(z0);
        c.fillStyle = '#e2b796';
        c.fillRect(x0 - 5, y0 - 5, ww + 10, y1 - y0 + 8);
        c.fillStyle = frame;
        c.fillRect(x0, y0, ww, y1 - y0);
        c.fillStyle = glass;
        c.fillRect(x0 + 3, y0 + 3, ww - 6, y1 - y0 - 6);
        c.fillStyle = frame;
        for (let k = 1; k <= bars; k++)
          c.fillRect(x0 + (ww * k) / (bars + 1) - 1.5, y0, 3, y1 - y0);
        c.fillRect(x0, y0 + (y1 - y0) * 0.3, ww, 3);
        if (arch) {
          c.fillStyle = '#e2b796';
          c.beginPath();
          c.arc(x0 + ww / 2, y0, ww / 2 + 5, Math.PI, 0);
          c.fill();
          c.fillStyle = frame;
          c.beginPath();
          c.arc(x0 + ww / 2, y0, ww / 2, Math.PI, 0);
          c.fill();
          c.fillStyle = glass;
          c.beginPath();
          c.arc(x0 + ww / 2, y0, ww / 2 - 3, Math.PI, 0);
          c.fill();
        }
      };
      for (let k = 0; k < 4; k++) {
        const x = k * bw;
        // ground floor: display window with bronze frame (awning is modelled in 3D)
        win(x + bw * 0.08, 0.6, 4.6, bw * 0.84, { frame: '#4a3a26', glass: '#4a5560', bars: 2 });
        c.fillStyle = '#e8d6b0';
        c.fillRect(x + bw * 0.08, Y(4.6) - 3, bw * 0.84, 3);
        // first floor: wide windows
        win(x + bw * 0.12, 5.8, 9.4, bw * 0.76, { bars: 2 });
        // four upper storeys: pairs of windows, arched on the top storey
        for (const [z0, z1, arch] of [
          [10.6, 12.9, false],
          [14.0, 16.3, false],
          [17.4, 19.7, false],
          [20.6, 22.6, true],
        ]) {
          win(x + bw * 0.16, z0, z1 - (arch ? 0.7 : 0), bw * 0.3, { arch });
          win(x + bw * 0.54, z0, z1 - (arch ? 0.7 : 0), bw * 0.3, { arch });
        }
        // pilasters between bays (upper storeys)
        c.fillStyle = '#d9a27f';
        c.fillRect(x - 5, Y(23.4), 10, Y(10.0) - Y(23.4));
        c.fillStyle = 'rgba(90,50,35,0.25)';
        c.fillRect(x + 5, Y(23.4), 2, Y(10.0) - Y(23.4));
      }
      // string courses
      c.fillStyle = '#dcae8c';
      for (const z of [5.0, 9.9, 13.5, 16.9, 20.2]) c.fillRect(0, Y(z + 0.35), w, (0.35 / 24) * h);
      c.fillStyle = '#b97b59';
      c.fillRect(0, Y(10.0), w, 3);
      c.fillRect(0, Y(24), w, (0.6 / 24) * h);
    });

    // ---- main block -----------------------------------------------------------
    const H = 24;
    kit.walls(batch, facade, [[ring]], 0, H, { bay: 6.2, storey: H / 2 });
    const off = (d) => kit.offsetRing(ring, d);
    const band = (z0, z1, d, m) => {
      const o = off(d);
      kit.walls(batch, m, [[o]], z0, z1);
      kit.cap(batch, m, [[o, ring.slice().reverse()]], z1);
      kit.cap(batch, m, [[o, ring.slice().reverse()]], z0, { down: true });
    };
    // frieze, cornice and balustrade
    kit.walls(batch, terracotta, [[ring]], H, H + 1.6);
    band(H + 1.6, H + 2.1, 0.9, terracottaLight);
    band(H - 0.2, H + 0.25, 0.3, terracottaLight);
    const inner = off(-0.5);
    const BAL0 = H + 2.1,
      BAL1 = H + 3.1;
    kit.walls(batch, terracotta, [[ring]], BAL0, BAL0 + 0.25);
    kit.walls(batch, terracotta, [[ring]], BAL1 - 0.2, BAL1);
    kit.cap(batch, terracottaLight, [[ring, inner.slice().reverse()]], BAL1);
    kit.walls(batch, terracotta, [[inner.slice().reverse()]], BAL0, BAL1);
    kit.cap(batch, leadM, [[ring]], H + 2.1);
    // balusters along the perimeter
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const n = Math.floor(len / 0.7);
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      for (let i = 1; i < n; i++) {
        const t = i / n;
        kit.box(
          batch,
          terracotta,
          p[0] + (q[0] - p[0]) * t,
          p[1] + (q[1] - p[1]) * t,
          BAL0 + 0.25,
          0.22,
          0.22,
          0.55,
          ang,
        );
      }
    }
    // ground-floor awnings (Harrods green), one per bay
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 4) continue;
      const ux = (q[0] - p[0]) / len,
        uy = (q[1] - p[1]) / len;
      const nx = uy,
        ny = -ux; // outward normal of a CCW ring
      const nb = Math.max(1, Math.round(len / 6.2));
      const bwid = len / nb;
      for (let i = 0; i < nb; i++) {
        const s0 = i * bwid + bwid * 0.09,
          s1 = (i + 1) * bwid - bwid * 0.09;
        const A0 = [p[0] + ux * s0, p[1] + uy * s0],
          A1 = [p[0] + ux * s1, p[1] + uy * s1];
        const z0 = 4.75,
          z1 = 3.75,
          out = 1.5;
        batch.quad(
          awningM,
          [A0[0], A0[1], z0],
          [A0[0] + nx * out, A0[1] + ny * out, z1],
          [A1[0] + nx * out, A1[1] + ny * out, z1],
          [A1[0], A1[1], z0],
          [0, 0],
          [0, 1],
          [1, 1],
          [1, 0],
        );
        // valance
        batch.quad(
          awningM,
          [A0[0] + nx * out, A0[1] + ny * out, z1],
          [A0[0] + nx * out, A0[1] + ny * out, z1 - 0.35],
          [A1[0] + nx * out, A1[1] + ny * out, z1 - 0.35],
          [A1[0] + nx * out, A1[1] + ny * out, z1],
          [0, 0],
          [0, 1],
          [1, 1],
          [1, 0],
        );
      }
    }

    // ---- frontage frames ------------------------------------------------------------
    // Brompton Road: W corner -> N corner; Hans Road: N corner -> E corner.
    const near = (x, y) =>
      ring.reduce((best, p) =>
        Math.hypot(p[0] - x, p[1] - y) < Math.hypot(best[0] - x, best[1] - y) ? p : best,
      );
    const W = near(2506, -809),
      Nn = near(2603, -720),
      E = near(2685, -798);
    const frameOf = (a, c) => {
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
      const ux = (c[0] - a[0]) / len,
        uy = (c[1] - a[1]) / len;
      return { a, len, ux, uy, ix: uy, iy: -ux, ang: Math.atan2(uy, ux) }; // i = inward normal (frontages run against the CCW ring)
    };
    const BR = frameOf(W, Nn),
      HR = frameOf(Nn, E);
    const at = (F, s, d) => [F.a[0] + F.ux * s + F.ix * d, F.a[1] + F.uy * s + F.iy * d];

    // Mansard attic block: rectangle along a frontage, sloped copper sides with dormers.
    const mansard = (F, s0, s1, depth, z0, z1, inset, dormers) => {
      const w = s1 - s0;
      const P = (s, d, z) => {
        const q = at(F, s, d);
        return [q[0], q[1], z];
      };
      const b0 = [P(s0, 0.6, z0), P(s1, 0.6, z0), P(s1, depth, z0), P(s0, depth, z0)];
      const t0 = [
        P(s0 + inset, 0.6 + inset, z1),
        P(s1 - inset, 0.6 + inset, z1),
        P(s1 - inset, depth - inset, z1),
        P(s0 + inset, depth - inset, z1),
      ];
      // order: front (d small) faces outward (toward -d)
      const face = (a, bb, cc, dd) =>
        batch.quad(copperG, a, bb, cc, dd, [0, 0], [1, 0], [1, 1], [0, 1]);
      face(b0[1], b0[0], t0[0], t0[1]); // front
      face(b0[2], b0[1], t0[1], t0[2]);
      face(b0[3], b0[2], t0[2], t0[3]);
      face(b0[0], b0[3], t0[3], t0[0]);
      batch.quad(leadM, t0[0], t0[3], t0[2], t0[1], [0, 0], [0, 1], [1, 1], [1, 0]);
      // dormers on the front slope
      for (let k = 0; k < dormers; k++) {
        const s = s0 + ((k + 0.5) * w) / dormers;
        const q = at(F, s, 0.6 + inset * 0.45);
        kit.box(batch, terracottaLight, q[0], q[1], z0 + 0.3, 1.8, 1.0, 2.3, F.ang);
        const q2 = at(F, s, 0.6 + inset * 0.45 - 0.52);
        kit.box(batch, dark, q2[0], q2[1], z0 + 0.6, 1.1, 0.06, 1.5, F.ang);
        // pediment
        const ped = new THREE.CylinderGeometry(1.25, 1.25, 1.1, 3, 1)
          .rotateX(Math.PI / 2)
          .rotateY(Math.PI / 2);
        const m = new THREE.Matrix4().makeRotationZ(F.ang).setPosition(q[0], q[1], z0 + 2.75);
        batch.addGeometry(terracotta, new THREE.BufferGeometry().copy(ped).scale(1, 1, 0.45), m);
        ped.dispose();
      }
    };
    // Octagonal cupola (corner turret) on a square attic base.
    const cupola = (x, y, z0, r, ang) => {
      const add = (geo, m, z) => {
        batch.addGeometry(
          m,
          geo,
          new THREE.Matrix4().makeRotationZ(ang + Math.PI / 8).setPosition(x, y, z),
        );
        geo.dispose();
      };
      add(
        new THREE.CylinderGeometry(r, r * 1.05, 4.2, 8).rotateX(Math.PI / 2),
        terracotta,
        z0 + 2.1,
      );
      for (let k = 0; k < 8; k++) {
        const a = ang + Math.PI / 8 + (k * Math.PI) / 4 + Math.PI / 8;
        const wx = x + Math.cos(a) * r * 0.93,
          wy = y + Math.sin(a) * r * 0.93;
        kit.box(batch, dark, wx, wy, z0 + 1.0, r * 0.5, 0.1, 2.4, a + Math.PI / 2);
      }
      add(
        new THREE.CylinderGeometry(r * 1.15, r * 1.15, 0.5, 8).rotateX(Math.PI / 2),
        terracottaLight,
        z0 + 4.45,
      );
      const dome = new THREE.SphereGeometry(r * 1.02, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2)
        .rotateX(Math.PI / 2)
        .scale(1, 1, 1.25);
      add(dome, copperG, z0 + 4.7);
      add(
        new THREE.CylinderGeometry(0.45, 0.55, 1.6, 8).rotateX(Math.PI / 2),
        terracottaLight,
        z0 + 4.7 + r * 1.25 + 0.6,
      );
      add(
        new THREE.SphereGeometry(0.5, 8, 5).rotateX(Math.PI / 2),
        copperG,
        z0 + 4.7 + r * 1.25 + 1.6,
      );
      add(
        new THREE.CylinderGeometry(0.05, 0.05, 1.6, 4).rotateX(Math.PI / 2),
        gold,
        z0 + 4.7 + r * 1.25 + 2.6,
      );
    };

    const bay = BR.len / 21;
    const Z0 = BAL0; // attics start behind the balustrade
    // Brompton Road pavilions: 2:4:3:3:3:4:2
    mansard(BR, 0, 2 * bay, 13, Z0, Z0 + 4.2, 1.6, 2);
    mansard(BR, 2 * bay, 6 * bay, 10, Z0, Z0 + 3.6, 1.6, 4);
    mansard(BR, 15 * bay, 19 * bay, 10, Z0, Z0 + 3.6, 1.6, 4);
    mansard(BR, 19 * bay, 21 * bay, 13, Z0, Z0 + 4.2, 1.6, 2);
    // Hans Road: corner pavilion at the east end and a central attic
    mansard(HR, HR.len - 12.5, HR.len, 13, Z0, Z0 + 4.2, 1.6, 2);
    mansard(HR, HR.len * 0.38, HR.len * 0.62, 10, Z0, Z0 + 3.6, 1.6, 4);
    // corner cupolas
    for (const [F, s] of [
      [BR, bay],
      [BR, 20 * bay],
      [HR, HR.len - 6.2],
    ]) {
      const q = at(F, s, 6.4);
      cupola(q[0], q[1], Z0 + 4.2, 3.2, F.ang);
    }

    // ---- central dome (on the Overture round part) ------------------------------------
    {
      const part = b.parts?.[0]?.polys?.[0]?.[0];
      let cx, cy, r;
      if (part) {
        cx = part.reduce((s, p) => s + p[0], 0) / part.length;
        cy = part.reduce((s, p) => s + p[1], 0) / part.length;
        r = part.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / part.length;
      } else {
        [cx, cy] = at(BR, 10.5 * bay, 7);
        r = 6.3;
      }
      const ang = BR.ang + Math.PI / 8;
      const add = (geo, m, z) => {
        batch.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(ang).setPosition(cx, cy, z));
        geo.dispose();
      };
      // square terracotta base with pedimented centre gable on the front
      const base = at(BR, 10.5 * bay, 7.0);
      kit.box(batch, terracotta, base[0], base[1], Z0, 3 * bay, 12.5, 4.2, BR.ang);
      kit.box(batch, terracottaLight, base[0], base[1], Z0 + 4.2, 3 * bay + 0.6, 13.1, 0.5, BR.ang);
      const pedPos = at(BR, 10.5 * bay, 1.2);
      const ped = new THREE.CylinderGeometry(4.6, 4.6, 1.2, 3, 1)
        .rotateX(Math.PI / 2)
        .rotateY(Math.PI / 2)
        .scale(1, 1, 0.42);
      batch.addGeometry(
        terracottaLight,
        ped,
        new THREE.Matrix4().makeRotationZ(BR.ang).setPosition(pedPos[0], pedPos[1], Z0 + 4.7 + 0.1),
      );
      ped.dispose();
      // octagonal drum with lunettes
      const zd = Z0 + 4.7;
      add(
        new THREE.CylinderGeometry(r * 0.92, r * 0.95, 5.0, 8).rotateX(Math.PI / 2),
        terracotta,
        zd + 2.5,
      );
      for (let k = 0; k < 8; k++) {
        const a = ang + Math.PI / 8 + (k * Math.PI) / 4;
        const ax = cx + Math.cos(a) * r * 0.87,
          ay = cy + Math.sin(a) * r * 0.87;
        kit.box(batch, dark, ax, ay, zd + 1.0, r * 0.45, 0.12, 2.6, a + Math.PI / 2);
        const lun = new THREE.CircleGeometry(r * 0.22, 10, 0, Math.PI).rotateX(Math.PI / 2);
        batch.addGeometry(
          dark,
          lun,
          new THREE.Matrix4()
            .makeRotationZ(a + Math.PI / 2 + Math.PI)
            .setPosition(cx + Math.cos(a) * r * 0.94, cy + Math.sin(a) * r * 0.94, zd + 3.6),
        );
        lun.dispose();
      }
      add(
        new THREE.CylinderGeometry(r * 1.02, r * 1.02, 0.6, 8).rotateX(Math.PI / 2),
        terracottaLight,
        zd + 5.3,
      );
      // octagonal dome: copper panels with terracotta ribs
      const zb = zd + 5.6;
      const prof = [];
      for (let i = 0; i <= 8; i++) {
        const t = (i / 8) * (Math.PI / 2);
        prof.push(new THREE.Vector2(Math.cos(t) * r * 0.95, Math.sin(t) * r * 1.15));
      }
      add(new THREE.LatheGeometry(prof, 8).rotateX(Math.PI / 2), copperG, zb);
      for (let k = 0; k < 8; k++) {
        const a = ang + (k * Math.PI) / 4 + Math.PI / 8 - Math.PI / 8;
        for (let i = 0; i < 8; i++) {
          const t0 = (i / 8) * (Math.PI / 2),
            t1 = ((i + 1) / 8) * (Math.PI / 2);
          const p0 = [Math.cos(t0) * r * 0.97, Math.sin(t0) * r * 1.17],
            p1 = [Math.cos(t1) * r * 0.97, Math.sin(t1) * r * 1.17];
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const rib = new THREE.BoxGeometry(len, 0.45, 0.35);
          const m = new THREE.Matrix4()
            .makeRotationZ(a)
            .multiply(
              new THREE.Matrix4().makeTranslation((p0[0] + p1[0]) / 2, 0, (p0[1] + p1[1]) / 2),
            )
            .multiply(new THREE.Matrix4().makeRotationY(-Math.atan2(p1[1] - p0[1], p1[0] - p0[0])));
          m.premultiply(new THREE.Matrix4().makeTranslation(cx, cy, zb));
          batch.addGeometry(terracottaLight, rib, m);
          rib.dispose();
        }
      }
      // pedimented dormers around the dome base
      for (let k = 0; k < 4; k++) {
        const a = ang + Math.PI / 8 + (k * Math.PI) / 2 + BR.ang * 0;
        const dx = cx + Math.cos(a) * r * 0.78,
          dy = cy + Math.sin(a) * r * 0.78;
        kit.box(batch, terracottaLight, dx, dy, zb, 1.8, 1.4, 2.0, a + Math.PI / 2);
        kit.box(
          batch,
          dark,
          dx + Math.cos(a) * 0.72,
          dy + Math.sin(a) * 0.72,
          zb + 0.3,
          1.0,
          0.06,
          1.3,
          a + Math.PI / 2,
        );
      }
      // cupola (lantern) with ball and finial
      const zt = zb + r * 1.15;
      add(
        new THREE.CylinderGeometry(1.5, 1.6, 3.2, 8).rotateX(Math.PI / 2),
        terracottaLight,
        zt + 1.4,
      );
      for (let k = 0; k < 8; k++) {
        const a = ang + Math.PI / 8 + (k * Math.PI) / 4;
        kit.box(
          batch,
          dark,
          cx + Math.cos(a) * 1.45,
          cy + Math.sin(a) * 1.45,
          zt + 0.4,
          0.6,
          0.06,
          1.8,
          a + Math.PI / 2,
        );
      }
      add(
        new THREE.SphereGeometry(1.75, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2)
          .rotateX(Math.PI / 2)
          .scale(1, 1, 1.3),
        copperG,
        zt + 3.0,
      );
      add(new THREE.SphereGeometry(0.45, 8, 6).rotateX(Math.PI / 2), gold, zt + 5.7);
      add(new THREE.CylinderGeometry(0.06, 0.06, 1.6, 4).rotateX(Math.PI / 2), gold, zt + 6.7);
    }

    // ---- gold "HARRODS" lettering on the frieze over the central bays ----------------------
    {
      const sign = kit.paintedMaterial(
        'harrods:sign',
        1024,
        64,
        (c, w, h) => {
          c.fillStyle = TC;
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#e0b84e';
          c.font = 'bold 50px serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('H A R R O D S', w / 2, h / 2 + 2);
        },
        { roughness: 0.5 },
      );
      for (const [F, s, wid] of [
        [BR, 10.5 * bay, 3 * bay],
        [HR, HR.len / 2, HR.len * 0.24],
      ]) {
        const p = at(F, s, -0.06);
        const geo = new THREE.PlaneGeometry(wid, 1.3).rotateX(-Math.PI / 2);
        // plane normal after rotateX(-90) is +y, i.e. outward once rotated to the frontage
        batch.addGeometry(
          sign,
          geo,
          new THREE.Matrix4().makeRotationZ(F.ang).setPosition(p[0], p[1], H + 0.85),
        );
        geo.dispose();
      }
    }

    // ---- rooftop: plant rooms and glazed lantern lights over the internal halls ----------
    {
      const inside = (x, y) => {
        let c = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [xi, yi] = ring[i],
            [xj, yj] = ring[j];
          if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
        }
        return c;
      };
      const rr = kit.rng(0.6021);
      const plant = kit.mat('#9a9a96');
      const glazing = kit.mat('glass');
      const [mx, my] = at(BR, BR.len / 2, 55);
      let placed = 0;
      for (let tries = 0; tries < 80 && placed < 9; tries++) {
        const x = mx + (rr() - 0.5) * 110,
          y = my + (rr() - 0.5) * 110;
        const w = 6 + rr() * 10,
          d = 4 + rr() * 6;
        const ok = [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ].every(([sx, sy]) => {
          const px =
              x + sx * (w / 2 + 14) * Math.cos(BR.ang) - sy * (d / 2 + 14) * Math.sin(BR.ang),
            py = y + sx * (w / 2 + 14) * Math.sin(BR.ang) + sy * (d / 2 + 14) * Math.cos(BR.ang);
          return inside(px, py);
        });
        if (!ok) continue;
        kit.box(batch, plant, x, y, H + 2.1, w, d, 2.5 + rr() * 2, BR.ang);
        placed++;
      }
      // two long glazed ridge lights
      for (const d of [36, 62]) {
        const [x, y] = at(BR, BR.len / 2, d);
        if (!inside(x, y)) continue;
        const prism = new THREE.CylinderGeometry(2.6, 2.6, 34, 3, 1)
          .rotateZ(Math.PI / 2)
          .scale(1, 1, 0.6);
        batch.addGeometry(
          glazing,
          prism,
          new THREE.Matrix4().makeRotationZ(BR.ang).setPosition(x, y, H + 2.1 + 0.8),
        );
        prism.dispose();
      }
    }

    g.add(batch.toGroup('harrods'));
    return g;
  },
};
