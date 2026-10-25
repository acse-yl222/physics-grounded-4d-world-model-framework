// Brompton Oratory (Church of the Immaculate Heart of Mary), Brompton Road.
// Italian Baroque church by Herbert Gribble (body 1880-84), Portland stone facade by
// George Sherrin (1892-95) and the lead-covered dome over the crossing with E. A.
// Rickards' lantern (1895-96). Nave of three main bays with side chapels, transepts
// and an apsed chancel; symmetrical facade of five bays below and three above with a
// pediment and recessed porch, partly rusticated with applied pilasters and blind
// niches; dome on a windowed drum with cupola and ball finial (about 61 m / 200 ft).
export default {
  id: 'brompton_oratory',
  name: 'Brompton Oratory',
  claims: ['19eb774d-4dec-4c9a-967f-38c229614635'],
  references: [
    {
      title: 'Brompton Oratory - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Brompton_Oratory',
      used_for:
        'Herbert Gribble design, Italian/Roman Baroque, Portland stone exterior, concrete vaults and dome',
    },
    {
      title: 'The Oratory, Brompton - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101358123-the-oratory-brompton-hans-town-ward',
      used_for:
        'listing: 5 bays below / 3 above, pediment, recessed porch, rusticated with pilasters and blind niches; nave of 3 bays, transepts, apsed chancel; lead dome over crossing with cupola and ball finial',
    },
    {
      title: 'Survey of London vol. 41 - British History Online',
      url: 'https://archive.british-history.ac.uk/node/41981',
      used_for: 'dates: body 1880-4, facade 1892-5, dome 1895-6, Rickards designer of the lantern',
    },
    {
      title: 'George Campbell Sherrin - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/George_Campbell_Sherrin',
      used_for: 'Sherrin dome design built 1895-96',
    },
    {
      title: 'Brompton Oratory - temples.org',
      url: 'https://temples.org/temples/united-kingdom/brompton-oratory-london',
      used_for: 'dome height about 200 ft, copper/lead exterior',
    },
  ],
  notes:
    'Facade faces Brompton Road (SSE). Internal layout (nave/chapels/transepts/crossing) placed within the ' +
    'Overture outline by proportion; nave eaves 24 m and dome cross at ~60 m are estimates. No western towers are ' +
    'modelled: the listing and Survey of London describe only the facade and dome. Facade sculpture reduced ' +
    'to niches and finials.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const ring = buildings[0].polys[0][0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // Local frame: origin at the facade centre, x along the facade, y along the axis (north-north-west).
    const OX = 2153.1,
      OY = -1070.55;
    const A = (24.8 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const L = (x, y) => [OX + x * ca - y * sa, OY + x * sa + y * ca];
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const lbox = (m, x, y, z0, w, d, h, rz = 0) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A + rz);
    };
    const lgeo = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      batch.addGeometry(
        m,
        geo,
        new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], z),
      );
      geo.dispose();
    };
    const stoneC = '#ddd5c2';
    const stone = kit.mat(stoneC, { roughness: 0.8 });
    const stoneD = kit.mat('#cbc2ad', { roughness: 0.85 });
    const leadM = kit.mat('#7c858a', { roughness: 0.55, metalness: 0.25 });
    const leadRoof = kit.roof('lead', 0);
    const dark = kit.mat('#2a3038');
    const gold = kit.mat('gold');

    // Side elevation: rusticated base, pilasters, blind niches, high arched windows.
    const sideMat = kit.paintedMaterial('brompton_oratory:side', 512, 512, (c, w, h) => {
      const r = kit.rng(0.808);
      c.fillStyle = stoneC;
      c.fillRect(0, 0, w, h);
      for (let i = 0; i < 500; i++) {
        c.fillStyle = `rgba(120,110,90,${0.04 + r() * 0.05})`;
        c.fillRect(r() * w, r() * h, 4 + r() * 14, 2 + r() * 4);
      }
      // rustication on lower 35 %
      c.fillStyle = 'rgba(110,100,85,0.45)';
      for (let y = h * 0.65; y < h; y += 14) c.fillRect(0, y, w, 2);
      const bw = w / 4;
      for (let k = 0; k < 4; k++) {
        const x = k * bw;
        // pilaster
        c.fillStyle = '#e8e1cf';
        c.fillRect(x - 8, h * 0.08, 16, h * 0.57);
        c.fillStyle = 'rgba(100,90,75,0.35)';
        c.fillRect(x + 8, h * 0.08, 3, h * 0.57);
        // blind niche (lower) and arched window (upper)
        const nx = x + bw / 2;
        c.fillStyle = '#c4baa3';
        c.beginPath();
        c.moveTo(nx - 14, h * 0.92);
        c.lineTo(nx - 14, h * 0.74);
        c.arc(nx, h * 0.74, 14, Math.PI, 0);
        c.lineTo(nx + 14, h * 0.92);
        c.fill();
        c.fillStyle = '#3a4048';
        c.beginPath();
        c.moveTo(nx - 22, h * 0.52);
        c.lineTo(nx - 22, h * 0.28);
        c.arc(nx, h * 0.28, 22, Math.PI, 0);
        c.lineTo(nx + 22, h * 0.52);
        c.fill();
        c.fillStyle = '#e8e1cf';
        c.fillRect(nx - 26, h * 0.52, 52, 6);
        c.fillRect(nx - 1.5, h * 0.2, 3, h * 0.32);
      }
      // entablature
      c.fillStyle = '#e8e1cf';
      c.fillRect(0, 0, w, h * 0.08);
      c.fillStyle = 'rgba(100,90,75,0.4)';
      c.fillRect(0, h * 0.08, w, 3);
    });

    // ---- side chapels / outer walls on the footprint ---------------------------------
    const HC = 13.5;
    kit.walls(batch, sideMat, [[ring]], 0, HC, { bay: 5.5, storey: HC / 2 });
    {
      const o = kit.offsetRing(ring, 0.5);
      kit.walls(batch, stone, [[o]], HC, HC + 0.7);
      kit.cap(batch, stone, [[o, ring.slice().reverse()]], HC + 0.7);
      kit.cap(batch, stone, [[o, ring.slice().reverse()]], HC, { down: true });
      const inner = kit.offsetRing(ring, -0.4);
      kit.walls(batch, stoneD, [[ring]], HC + 0.7, HC + 1.6);
      kit.walls(batch, stoneD, [[inner.slice().reverse()]], HC, HC + 1.6);
      kit.cap(batch, stone, [[ring, inner.slice().reverse()]], HC + 1.6);
      kit.cap(batch, leadM, [[inner]], HC + 0.3);
    }

    // ---- nave, transepts, chancel, apse -----------------------------------------------
    const HN = 24;
    const clerestory = kit.paintedMaterial('brompton_oratory:clerestory', 512, 256, (c, w, h) => {
      c.fillStyle = stoneC;
      c.fillRect(0, 0, w, h);
      const bw = w / 4;
      for (let k = 0; k < 4; k++) {
        const x = k * bw + bw / 2;
        // thermal (Diocletian) window
        c.fillStyle = '#e8e1cf';
        c.beginPath();
        c.arc(x, h * 0.62, bw * 0.4, Math.PI, 0);
        c.fill();
        c.fillStyle = '#353b44';
        c.beginPath();
        c.arc(x, h * 0.62, bw * 0.34, Math.PI, 0);
        c.fill();
        c.fillStyle = '#e8e1cf';
        c.fillRect(x - bw * 0.13, h * 0.62 - bw * 0.34, 4, bw * 0.34);
        c.fillRect(x + bw * 0.13 - 4, h * 0.62 - bw * 0.34, 4, bw * 0.34);
        c.fillStyle = '#e8e1cf';
        c.fillRect(k * bw - 6, 0, 12, h);
      }
      c.fillStyle = '#e8e1cf';
      c.fillRect(0, 0, w, h * 0.12);
      c.fillRect(0, h * 0.62, w, 5);
    });
    const vol = (x0, y0, x1, y1, z1, alongY, rise, uvBay) => {
      const r4 = rect(x0, y0, x1, y1);
      kit.walls(batch, clerestory, [[r4]], HC, z1, {
        bay: uvBay,
        storey: (z1 - HC) / 2,
        uvBase: HC,
      });
      kit.walls(batch, stone, [[kit.offsetRing(r4, 0.45)]], z1 - 0.8, z1);
      kit.cap(batch, stone, [[kit.offsetRing(r4, 0.45), r4.slice().reverse()]], z1);
      kit.pitchedRoof(
        batch,
        leadRoof,
        stone,
        r4,
        alongY ? A + Math.PI / 2 : A,
        z1,
        rise,
        'gabled',
        { overhang: 0.3 },
      );
    };
    vol(-8.5, 5, 8.5, 52, HN, true, 5.5, 47 / 12); // nave: 3 main bays
    vol(-21.5, 52.5, 19.5, 71.5, HN, false, 5.5, 4.8); // transepts
    vol(-8.5, 71.5, 8.5, 84, HN - 1, true, 5.0, 4.5); // chancel
    // apse: half-cylinder with half-cone roof
    {
      const R = 8.5;
      const apse = new THREE.CylinderGeometry(
        R,
        R,
        HN - 1 - HC,
        16,
        1,
        true,
        -Math.PI / 2,
        Math.PI,
      ).rotateX(Math.PI / 2);
      lgeo(apse, stone, 0, 84, HC + (HN - 1 - HC) / 2);
      const cone = new THREE.ConeGeometry(
        R + 0.4,
        5.0,
        16,
        1,
        false,
        -Math.PI / 2,
        Math.PI,
      ).rotateX(Math.PI / 2);
      lgeo(cone, leadM, 0, 84, HN - 1 + 2.5);
      for (let k = 0; k < 3; k++) {
        const a = Math.PI / 4 + (k * Math.PI) / 4;
        lbox(
          dark,
          Math.cos(a) * (R + 0.02),
          84 + Math.sin(a) * (R + 0.02),
          HC + 2.5,
          2.2,
          0.1,
          4.5,
          a - Math.PI / 2,
        );
      }
    }

    // ---- crossing: square base, drum, dome, lantern ------------------------------------
    {
      const cy = 62,
        cx = -1;
      lbox(stone, cx, cy, HN, 20, 19, 3.5);
      lbox(stoneD, cx, cy, HN + 3.5, 20.6, 19.6, 0.6);
      const R = 8.6;
      const zDrum = HN + 4.1;
      const drum = new THREE.CylinderGeometry(R, R, 8.5, 32).rotateX(Math.PI / 2);
      lgeo(drum, stone, cx, cy, zDrum + 4.25);
      // paired pilasters and arched windows around the drum
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        const wx = cx + Math.cos(a) * (R + 0.05),
          wy = cy + Math.sin(a) * (R + 0.05);
        lbox(dark, wx, wy, zDrum + 1.5, 2.4, 0.12, 5.0, a + Math.PI / 2);
        const arch = new THREE.CircleGeometry(1.2, 10, 0, Math.PI).rotateX(Math.PI / 2);
        lgeo(
          arch,
          dark,
          cx + Math.cos(a) * (R + 0.08),
          cy + Math.sin(a) * (R + 0.08),
          zDrum + 6.5,
          a + Math.PI / 2,
        );
        const pa = a + Math.PI / 8;
        for (const d of [-0.55, 0.55]) {
          const px = cx + Math.cos(pa) * (R + 0.35) - Math.sin(pa) * d,
            py = cy + Math.sin(pa) * (R + 0.35) + Math.cos(pa) * d;
          lbox(stone, px, py, zDrum, 0.6, 0.6, 8.5, pa);
        }
      }
      lgeo(
        new THREE.CylinderGeometry(R + 0.9, R + 0.9, 0.9, 32).rotateX(Math.PI / 2),
        stoneD,
        cx,
        cy,
        zDrum + 8.95,
      );
      lgeo(
        new THREE.CylinderGeometry(R + 0.3, R + 0.3, 1.4, 32).rotateX(Math.PI / 2),
        stone,
        cx,
        cy,
        zDrum + 10.1,
      );
      // lead-covered dome with ribs, slightly raised profile
      const zDome = zDrum + 10.8;
      const prof = [];
      for (let i = 0; i <= 14; i++) {
        const t = (i / 14) * (Math.PI / 2);
        prof.push(new THREE.Vector2(Math.cos(t) * (R + 0.1), Math.sin(t) * (R + 0.1) * 1.32));
      }
      prof.push(new THREE.Vector2(0, (R + 0.1) * 1.32));
      lgeo(new THREE.LatheGeometry(prof, 32).rotateX(Math.PI / 2), leadM, cx, cy, zDome);
      for (let k = 0; k < 16; k++) {
        const a = (k * Math.PI) / 8;
        for (let i = 0; i < 10; i++) {
          const t0 = (i / 10) * (Math.PI / 2) * 0.9,
            t1 = ((i + 1) / 10) * (Math.PI / 2) * 0.9;
          const p0 = [Math.cos(t0) * (R + 0.2), Math.sin(t0) * (R + 0.2) * 1.32],
            p1 = [Math.cos(t1) * (R + 0.2), Math.sin(t1) * (R + 0.2) * 1.32];
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const rib = new THREE.BoxGeometry(len, 0.3, 0.22);
          const p = L(cx, cy);
          const m = new THREE.Matrix4()
            .makeTranslation(p[0], p[1], zDome)
            .multiply(new THREE.Matrix4().makeRotationZ(A + a))
            .multiply(
              new THREE.Matrix4().makeTranslation((p0[0] + p1[0]) / 2, 0, (p0[1] + p1[1]) / 2),
            )
            .multiply(new THREE.Matrix4().makeRotationY(-Math.atan2(p1[1] - p0[1], p1[0] - p0[0])));
          batch.addGeometry(stoneD, rib, m);
          rib.dispose();
        }
      }
      // lantern (Rickards): columned drum, small dome, ball and cross
      const zL = zDome + (R + 0.1) * 1.32 - 0.6;
      lgeo(
        new THREE.CylinderGeometry(2.6, 2.8, 5.2, 16).rotateX(Math.PI / 2),
        stone,
        cx,
        cy,
        zL + 2.6,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        lbox(
          dark,
          cx + Math.cos(a) * 2.62,
          cy + Math.sin(a) * 2.62,
          zL + 1.0,
          0.9,
          0.08,
          2.8,
          a + Math.PI / 2,
        );
        lgeo(
          new THREE.CylinderGeometry(0.22, 0.22, 4.4, 6).rotateX(Math.PI / 2),
          stone,
          cx + Math.cos(a + Math.PI / 8) * 3.1,
          cy + Math.sin(a + Math.PI / 8) * 3.1,
          zL + 2.4,
        );
      }
      lgeo(
        new THREE.CylinderGeometry(3.4, 3.4, 0.5, 16).rotateX(Math.PI / 2),
        stoneD,
        cx,
        cy,
        zL + 5.0,
      );
      const cap = new THREE.SphereGeometry(2.7, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2)
        .rotateX(Math.PI / 2)
        .scale(1, 1, 1.4);
      lgeo(cap, leadM, cx, cy, zL + 5.25);
      lgeo(
        new THREE.CylinderGeometry(0.5, 0.7, 1.4, 8).rotateX(Math.PI / 2),
        stone,
        cx,
        cy,
        zL + 9.2,
      );
      lgeo(new THREE.SphereGeometry(0.75, 12, 8).rotateX(Math.PI / 2), gold, cx, cy, zL + 10.5);
      lbox(gold, cx, cy, zL + 11.1, 0.18, 0.18, 2.4);
      lbox(gold, cx, cy, zL + 12.4, 1.2, 0.18, 0.18);
    }

    // ---- facade on Brompton Road ----------------------------------------------------------
    {
      const rus = kit.paintedMaterial('brompton_oratory:rustic', 256, 256, (c, w, h) => {
        c.fillStyle = stoneC;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(110,100,85,0.5)';
        for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 3);
        for (let y = 0, k = 0; y < h; y += 32, k++)
          for (let x = k % 2 ? 32 : 0; x < w; x += 64) c.fillRect(x, y, 3, 32);
      });
      const F0 = -0.6; // facade plane (slightly proud of the footprint edge)
      const W1 = 40,
        H1 = 15.5,
        W2 = 23,
        H2 = 12;
      // lower storey: rusticated wall
      const lower = rect(-W1 / 2, F0, W1 / 2, F0 + 3);
      kit.walls(batch, rus, [[lower]], 0, H1, { bay: 4, storey: 4 });
      kit.cap(batch, stone, [[lower]], H1);
      // recessed porch (centre bay) with dark opening
      lbox(dark, 0, F0 - 0.01, 0.6, 7.0, 0.1, 9.0);
      const porchArch = new THREE.CircleGeometry(3.5, 16, 0, Math.PI).rotateX(Math.PI / 2);
      lgeo(porchArch, dark, 0, F0 - 0.02, 9.6);
      // paired columns / pilasters: 5 bays below
      const bay1 = W1 / 5;
      for (let k = 0; k <= 5; k++) {
        const x = -W1 / 2 + k * bay1;
        for (const d of [-0.8, 0.8]) {
          const xx = x + (k === 0 ? 0.9 : k === 5 ? -0.9 : d);
          lgeo(
            new THREE.CylinderGeometry(0.55, 0.62, H1 - 3.2, 14).rotateX(Math.PI / 2),
            stone,
            xx,
            F0 - 0.9,
            1.4 + (H1 - 3.2) / 2,
          );
          lbox(stoneD, xx, F0 - 0.9, 0, 1.5, 1.5, 1.4);
          lbox(stone, xx, F0 - 0.9, H1 - 1.8, 1.5, 1.5, 0.6);
          if (k === 0 || k === 5) break;
        }
      }
      // blind niches in the outer bays
      for (const x of [
        -W1 / 2 + bay1 * 0.5,
        -W1 / 2 + bay1 * 1.5,
        W1 / 2 - bay1 * 1.5,
        W1 / 2 - bay1 * 0.5,
      ]) {
        lbox(stoneD, x, F0 - 0.02, 3.5, 2.0, 0.1, 5.0);
        lgeo(
          new THREE.CircleGeometry(1.0, 10, 0, Math.PI).rotateX(Math.PI / 2),
          stoneD,
          x,
          F0 - 0.03,
          8.5,
        );
        lbox(stone, x, F0 - 0.3, 3.0, 2.6, 0.6, 0.4);
        lgeo(
          new THREE.CylinderGeometry(0.35, 0.45, 2.2, 8).rotateX(Math.PI / 2),
          stone,
          x,
          F0 - 0.25,
          4.6,
        );
        lgeo(new THREE.SphereGeometry(0.35, 8, 6), stone, x, F0 - 0.25, 6.0);
      }
      // entablature of the lower order
      lbox(stone, 0, F0 - 0.6, H1 - 1.2, W1 + 1.4, 2.6, 1.2);
      lbox(stoneD, 0, F0 - 0.6, H1, W1 + 2, 3.0, 0.5);
      // upper storey: 3 bays, paired pilasters, central window, pediment
      const upper = rect(-W2 / 2, F0 + 0.5, W2 / 2, F0 + 3);
      kit.walls(batch, stone, [[upper]], H1 + 0.5, H1 + 0.5 + H2);
      const bay2 = W2 / 3;
      for (let k = 0; k <= 3; k++) {
        const x = -W2 / 2 + k * bay2;
        for (const d of k === 0 ? [0.5] : k === 3 ? [-0.5] : [-0.6, 0.6]) {
          lgeo(
            new THREE.CylinderGeometry(0.45, 0.5, H2 - 1.5, 12).rotateX(Math.PI / 2),
            stone,
            x + d,
            F0 + 0.0,
            H1 + 0.5 + (H2 - 1.5) / 2,
          );
        }
      }
      lbox(dark, 0, F0 + 0.45, H1 + 2.5, 3.6, 0.1, 5.5);
      lgeo(
        new THREE.CircleGeometry(1.8, 12, 0, Math.PI).rotateX(Math.PI / 2),
        dark,
        0,
        F0 + 0.44,
        H1 + 8.0,
      );
      for (const x of [-bay2, bay2]) {
        lbox(stoneD, x, F0 + 0.45, H1 + 3.0, 2.0, 0.1, 4.5);
        lgeo(
          new THREE.CircleGeometry(1.0, 10, 0, Math.PI).rotateX(Math.PI / 2),
          stoneD,
          x,
          F0 + 0.44,
          H1 + 7.5,
        );
      }
      // scroll buttresses linking the storeys
      for (const s of [-1, 1]) {
        const scroll = new THREE.CylinderGeometry(2.6, 2.6, 1.2, 12, 1, false, 0, Math.PI / 2)
          .rotateX(Math.PI / 2)
          .rotateY(Math.PI / 2);
        lgeo(scroll, stone, s * (W2 / 2 + 0.0), F0 + 1.6, H1 + 0.5, s > 0 ? 0 : Math.PI);
        lgeo(new THREE.SphereGeometry(0.6, 8, 6), stone, s * (W1 / 2 - 1.2), F0 - 0.6, H1 + 1.1);
        lgeo(
          new THREE.CylinderGeometry(0.3, 0.5, 1.6, 8).rotateX(Math.PI / 2),
          stone,
          s * (W1 / 2 - 1.2),
          F0 - 0.6,
          H1 + 2.2,
        );
      }
      const zE = H1 + 0.5 + H2 - 1.5;
      lbox(stone, 0, F0 + 0.3, zE, W2 + 1.2, 2.2, 1.5);
      // pediment
      const pedH = 4.2;
      const zp = zE + 1.5;
      const P = (x, z, d) => {
        const q = L(x, F0 + d);
        return [q[0], q[1], z];
      };
      const hw = W2 / 2 + 0.6;
      for (const [d0, d1] of [[-0.8, 2.6]]) {
        batch.add(
          stone,
          [P(-hw, zp, d0), P(hw, zp, d0), P(0, zp + pedH, d0)],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 1, 2],
        );
        batch.add(
          stone,
          [P(-hw, zp, d1), P(hw, zp, d1), P(0, zp + pedH, d1)],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 2, 1],
        );
        batch.quad(
          leadM,
          P(-hw, zp, d0),
          P(0, zp + pedH, d0),
          P(0, zp + pedH, d1),
          P(-hw, zp, d1),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          leadM,
          P(hw, zp, d1),
          P(0, zp + pedH, d1),
          P(0, zp + pedH, d0),
          P(hw, zp, d0),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      // acroteria / finials on the pediment
      for (const [x, z] of [
        [0, zp + pedH],
        [-hw + 0.3, zp],
        [hw - 0.3, zp],
      ]) {
        lbox(stone, x, F0 + 0.8, z, 0.9, 0.9, 1.0);
        lgeo(new THREE.SphereGeometry(0.4, 8, 6), stone, x, F0 + 0.8, z + 1.4);
      }
      // gable wall behind the upper storey up to the nave roof
      lbox(stone, 0, F0 + 4.5, H1, 17, 3, zE + 1.5 - H1);
      // steps
      lbox(stoneD, 0, F0 - 3.0, 0, W1 * 0.6, 3.0, 0.4);
      lbox(stoneD, 0, F0 - 2.2, 0.4, W1 * 0.55, 1.5, 0.35);
    }
    g.add(batch.toGroup('brompton_oratory'));
    return g;
  },
};
