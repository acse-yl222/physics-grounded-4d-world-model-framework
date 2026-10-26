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
    'on Hans Road only the corner and one central attic are modelled. Brompton Road and Hans Road elevations have ' +
    'real window frames, sills, arch heads, pilasters, string courses, modillions and a turned balustrade with ' +
    'entrance bays at a regular interval (positions estimated); Basil Street / Hans Crescent keep a painted ' +
    'Stephens bay. Rooftop plant and rooflights are generic, not surveyed.',
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

    // Round-arched window row: kit.windowRow for the rectangular part, plus the arch
    // frame ring and a half-disc of glass in the wall plane for the head.
    const archRow = (a, b, z, o) => {
      kit.windowRow(batch, a, b, z, { ...o, head: 'none' });
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy),
        ux = dx / len,
        uy = dy / len,
        ang = Math.atan2(dy, dx);
      const margin = o.margin ?? 0.6,
        bay = o.bay ?? 3.6,
        depth = o.depth ?? 0.12;
      const usable = len - 2 * margin;
      const n = o.count ?? Math.max(0, Math.floor(usable / bay + 0.35));
      const r = o.width / 2;
      const rot = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      for (let k = 0; k < n; k++) {
        const t = margin + (usable * (k + 0.5)) / n;
        const cx = a[0] + ux * t,
          cy = a[1] + uy * t;
        const disc = new THREE.CircleGeometry(r, 12, 0, Math.PI).rotateX(Math.PI / 2);
        batch.addGeometry(
          o.glass,
          disc,
          new THREE.Matrix4()
            .makeRotationZ(ang)
            .setPosition(cx + uy * 0.03, cy - ux * 0.03, z + o.height),
        );
        disc.dispose();
        const ringG = new THREE.TorusGeometry(r + 0.04, 0.07, 4, 12, Math.PI);
        const m = rot
          .clone()
          .setPosition(cx + uy * depth * 0.9, cy - ux * depth * 0.9, z + o.height);
        batch.addGeometry(o.sill ?? o.frame, ringG, m);
        ringG.dispose();
        if (o.bars) {
          kit.box(
            batch,
            o.frame,
            cx + uy * depth * 0.5,
            cy - ux * depth * 0.5,
            z + o.height,
            0.05,
            depth * 0.6,
            r,
            ang,
          );
        }
        if (o.surround) {
          const sr = new THREE.TorusGeometry(
            r + o.surround * 0.6,
            o.surround * 0.5,
            3,
            12,
            Math.PI,
          );
          batch.addGeometry(
            o.surroundMat,
            sr,
            rot.clone().setPosition(cx + uy * depth * 0.5, cy - ux * depth * 0.5, z + o.height),
          );
          sr.dispose();
        }
      }
    };
    // ---- main block -----------------------------------------------------------
    const H = 24;
    // Principal elevations (Brompton Road W -> N corner, Hans Road N -> E corner) get
    // real windows; Basil Street / Hans Crescent keep the painted bay.
    const nearPt = (x, y) =>
      ring.reduce((best, p) =>
        Math.hypot(p[0] - x, p[1] - y) < Math.hypot(best[0] - x, best[1] - y) ? p : best,
      );
    const cW = nearPt(2506, -809),
      cN = nearPt(2603, -720),
      cE = nearPt(2685, -798);
    const segDist = (p, a, b) => {
      const vx = b[0] - a[0],
        vy = b[1] - a[1];
      const t = Math.max(
        0,
        Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / (vx * vx + vy * vy)),
      );
      return Math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy);
    };
    const isFront = (a, b) => {
      const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      return segDist(m, cW, cN) < 4 || segDist(m, cN, cE) < 4;
    };
    const plain = kit.paintedMaterial('harrods:plain', 512, 1024, (c, w, h) => {
      const r = kit.rng(0.2718);
      const Y = (z) => h - (z / 24) * h;
      c.fillStyle = TC;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(120,70,50,0.2)';
      for (let z = 0; z < 24; z += 0.6) c.fillRect(0, Y(z), w, 1);
      for (let z = 0, k = 0; z < 24; z += 0.6, k++)
        for (let x = k % 2 ? 0 : 32; x < w; x += 64) c.fillRect(x, Y(z + 0.6), 1, (0.6 / 24) * h);
      for (let i = 0; i < 500; i++) {
        c.fillStyle = `rgba(${r() < 0.5 ? '255,230,210' : '150,90,60'},${0.04 + r() * 0.05})`;
        c.fillRect(r() * w, r() * h, 6 + r() * 14, 3 + r() * 3);
      }
      // window reveals (dark recess behind the 3D frames) so the openings read deep
      const bw = w / 4;
      const hole = (x0, z0, z1, ww, arch) => {
        c.fillStyle = '#3b3029';
        c.fillRect(x0, Y(z1), ww, Y(z0) - Y(z1));
        if (arch) {
          c.beginPath();
          c.arc(x0 + ww / 2, Y(z1), ww / 2, Math.PI, 0);
          c.fill();
        }
      };
      for (let k = 0; k < 4; k++) {
        const x = k * bw;
        hole(x + bw * 0.08, 0.5, 4.7, bw * 0.84);
        hole(x + bw * 0.12, 5.75, 9.45, bw * 0.76);
        for (const [z0, z1, arch] of [
          [10.55, 12.95],
          [13.95, 16.35],
          [17.35, 19.75],
          [20.55, 21.95, true],
        ]) {
          hole(x + bw * 0.16 - 1, z0, z1, bw * 0.3 + 2, arch);
          hole(x + bw * 0.54 - 1, z0, z1, bw * 0.3 + 2, arch);
        }
      }
    });
    const BAY = 6.2;
    const frontEdges = [];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const front = isFront(a, b);
      const n = Math.round(len / BAY);
      const u1 = n >= 1 ? n / 4 : 0.03;
      const shade = 0.96 + ((k * 0.37) % 1) * 0.06;
      batch.quad(
        front ? plain : facade,
        [a[0], a[1], 0],
        [b[0], b[1], 0],
        [b[0], b[1], H],
        [a[0], a[1], H],
        [0, 0],
        [u1, 0],
        [u1, 1],
        [0, 1],
        [shade, shade, shade],
      );
      if (front && n >= 1) frontEdges.push({ a, b, len, n });
    }

    // Real windows, pilasters and entrances on the principal elevations.
    const bronzeF = kit.mat('#4a3a26', { roughness: 0.45, metalness: 0.6 });
    const sashF = kit.mat('#5a4434', { roughness: 0.6 });
    const glassM = kit.mat('#46586a', { roughness: 0.15, metalness: 0.3 });
    const shopGlass = kit.mat('#55626b', { roughness: 0.1, metalness: 0.35 });
    const tcDress = kit.mat('#e2b796', { roughness: 0.7 });
    let bayIndex = 0;
    for (const { a, b, len, n } of frontEdges) {
      const bw = len / n;
      const ux = (b[0] - a[0]) / len,
        uy = (b[1] - a[1]) / len;
      const ang = Math.atan2(uy, ux);
      const nx = uy,
        ny = -ux;
      const at = (s, d = 0) => [a[0] + ux * s + nx * d, a[1] + uy * s + ny * d];
      for (let i = 0; i < n; i++) {
        const s0 = i * bw,
          s1 = (i + 1) * bw;
        const A0 = at(s0),
          A1 = at(s1);
        const entrance = bayIndex % 5 === 2;
        bayIndex++;
        if (entrance) {
          // bronze entrance doors with a fanlight under the awning
          const c = at((s0 + s1) / 2, 0.02);
          kit.box(batch, shopGlass, c[0], c[1], 0, bw * 0.6, 0.06, 4.3, ang);
          const cf = at((s0 + s1) / 2, 0.1);
          for (const du of [-0.3, -0.1, 0.1, 0.3]) {
            const q = at((s0 + s1) / 2 + du * bw, 0.1);
            kit.box(batch, bronzeF, q[0], q[1], 0, 0.14, 0.16, 4.3, ang);
          }
          kit.box(batch, bronzeF, cf[0], cf[1], 3.0, bw * 0.62, 0.18, 0.14, ang);
          kit.box(batch, bronzeF, cf[0], cf[1], 4.3, bw * 0.66, 0.2, 0.2, ang);
          const st = at((s0 + s1) / 2, 0.6);
          kit.box(batch, kit.mat('#9c948a'), st[0], st[1], 0, bw * 0.7, 1.2, 0.12, ang);
        } else
          kit.windowRow(batch, A0, A1, 0.6, {
            width: bw * 0.84,
            height: 4.0,
            count: 1,
            margin: 0,
            depth: 0.16,
            glass: shopGlass,
            frame: bronzeF,
            sill: tcDress,
            head: 'none',
            bars: 2,
          });
        kit.windowRow(batch, A0, A1, 5.8, {
          width: bw * 0.76,
          height: 3.6,
          count: 1,
          margin: 0,
          depth: 0.14,
          glass: glassM,
          frame: sashF,
          sill: tcDress,
          head: 'lintel',
          bars: 2,
        });
        for (const [z0, z1, arch] of [
          [10.6, 12.9, false],
          [14.0, 16.3, false],
          [17.4, 19.7, false],
          [20.6, 21.9, true],
        ])
          (arch ? archRow : (aa, bb, zz, oo) => kit.windowRow(batch, aa, bb, zz, oo))(A0, A1, z0, {
            width: bw * 0.3,
            height: z1 - z0,
            count: 2,
            margin: bw * 0.12,
            depth: 0.12,
            glass: glassM,
            frame: sashF,
            sill: tcDress,
            head: 'lintel',
            bars: 1,
            surround: 0.14,
            surroundMat: tcDress,
          });
        // terracotta pilaster with capital between the paired windows' bays (upper storeys)
        const p = at(s0, 0.14);
        kit.box(batch, terracottaLight, p[0], p[1], 10.0, 0.75, 0.28, 13.4, ang);
        kit.box(batch, terracottaLight, p[0], p[1], 23.0, 1.0, 0.45, 0.45, ang);
        kit.box(batch, terracottaLight, p[0], p[1], 9.9, 0.95, 0.4, 0.3, ang);
        // ground-floor pier
        const gp = at(s0, 0.1);
        kit.box(batch, terracotta, gp[0], gp[1], 0, bw * 0.16, 0.2, 5.0, ang);
      }
      const p = at(len, 0.14);
      kit.box(batch, terracottaLight, p[0], p[1], 10.0, 0.75, 0.28, 13.4, ang);
    }
    const off = (d) => kit.offsetRing(ring, d);
    const band = (z0, z1, d, m) => {
      const o = off(d);
      kit.walls(batch, m, [[o]], z0, z1, { bay: 1e6 });
      kit.cap(batch, m, [[o, ring.slice().reverse()]], z1);
      kit.cap(batch, m, [[o, ring.slice().reverse()]], z0, { down: true });
    };
    // string courses, frieze, cornice and balustrade
    band(4.95, 5.35, 0.22, terracottaLight);
    band(9.7, 10.1, 0.35, terracottaLight);
    for (const z of [13.5, 16.9, 20.2]) band(z, z + 0.25, 0.12, terracottaLight);
    kit.walls(batch, terracotta, [[ring]], H, H + 1.6, { bay: 1e6 });
    band(H + 1.2, H + 1.6, 0.5, terracottaLight);
    band(H + 1.6, H + 2.1, 0.9, terracottaLight);
    band(H - 0.2, H + 0.25, 0.3, terracottaLight);
    const inner = off(-0.5);
    const BAL0 = H + 2.1,
      BAL1 = H + 3.1;
    // modillion brackets under the cornice on the principal elevations
    for (const { a, b, len } of frontEdges) {
      const ux = (b[0] - a[0]) / len,
        uy = (b[1] - a[1]) / len;
      const nm = Math.floor(len / 1.2);
      for (let i = 0; i < nm; i++) {
        const s = (i + 0.5) * (len / nm);
        kit.box(
          batch,
          terracottaLight,
          a[0] + ux * s + uy * 0.5,
          a[1] + uy * s - ux * 0.5,
          H + 1.35,
          0.25,
          0.75,
          0.3,
          Math.atan2(uy, ux),
        );
      }
    }
    kit.walls(batch, terracotta, [[ring]], BAL0, BAL0 + 0.25, { bay: 1e6 });
    kit.walls(batch, terracotta, [[ring]], BAL1 - 0.2, BAL1, { bay: 1e6 });
    kit.cap(batch, terracottaLight, [[ring, inner.slice().reverse()]], BAL1);
    kit.walls(batch, terracotta, [[inner.slice().reverse()]], BAL0, BAL1, { bay: 1e6 });
    kit.cap(batch, kit.roof('flat', 1), [[ring]], H + 2.1, { scale: 12 });
    // balusters: turned on the principal elevations, simple blocks elsewhere
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      if (isFront(p, q)) {
        kit.balustrade(batch, terracottaLight, [p, q], BAL0, { height: 1.0, spacing: 0.42 });
        const np = Math.floor(len / 6.2);
        for (let i = 0; i <= np; i++) {
          const t = np ? i / np : 0;
          kit.box(
            batch,
            terracotta,
            p[0] + (q[0] - p[0]) * t,
            p[1] + (q[1] - p[1]) * t,
            BAL0,
            0.6,
            0.6,
            1.15,
            ang,
          );
        }
        continue;
      }
      const n = Math.floor(len / 0.7);
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
    // ground-floor awnings (Harrods green with gold lettering on the valance)
    const valance = kit.paintedMaterial(
      'harrods:valance',
      512,
      64,
      (c, w, h) => {
        c.fillStyle = '#1f4a35';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d9b45a';
        c.fillRect(0, 4, w, 2);
        c.fillRect(0, h - 6, w, 2);
        c.font = 'bold 34px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('Harrods', w / 2, h / 2 + 1);
      },
      { roughness: 0.8, side: THREE.DoubleSide },
    );
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
          valance,
          [A0[0] + nx * out, A0[1] + ny * out, z1 - 0.35],
          [A1[0] + nx * out, A1[1] + ny * out, z1 - 0.35],
          [A1[0] + nx * out, A1[1] + ny * out, z1],
          [A0[0] + nx * out, A0[1] + ny * out, z1],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        // side cheeks and support arms
        for (const [P0, sgn] of [
          [A0, 1],
          [A1, -1],
        ]) {
          batch.add(
            awningM,
            [
              [P0[0], P0[1], z0],
              [P0[0] + nx * out, P0[1] + ny * out, z1],
              [P0[0] + nx * out, P0[1] + ny * out, z1 - 0.35],
            ],
            [
              [0, 0],
              [1, 0],
              [1, 1],
            ],
            sgn > 0 ? [0, 2, 1] : [0, 1, 2],
          );
        }
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

    // arched windows on the front of the dome's square base and the attic mansards' fronts
    archRow(at(BR, 12 * bay - 0.5, 0.72), at(BR, 9 * bay + 0.5, 0.72), Z0 + 0.5, {
      width: 1.4,
      height: 2.2,
      count: 3,
      margin: 0.8,
      depth: 0.14,
      glass: glassM,
      frame: sashF,
      sill: tcDress,
      bars: 1,
      surround: 0.14,
      surroundMat: tcDress,
    });
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
      const plant = kit.paintedMaterial(
        'harrods:plant',
        128,
        128,
        (c, w, h) => {
          c.fillStyle = '#9d9d98';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#7f807c';
          for (let y = 6; y < h; y += 6) c.fillRect(0, y, w, 2);
          c.fillStyle = '#6b6c69';
          for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 2, h);
        },
        { vertexColors: true },
      );
      const plantTop = kit.mat('#8d8d89');
      const glazing = kit.mat('#7d98a8', { roughness: 0.1, metalness: 0.3 });
      const ribM = kit.mat('#e2e4e2', { roughness: 0.5, metalness: 0.3 });
      const [mx, my] = at(BR, BR.len / 2, 55);
      const fits = (x, y, w, d, m) =>
        [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ].every(([sx, sy]) => {
          const px = x + sx * (w / 2 + m) * Math.cos(BR.ang) - sy * (d / 2 + m) * Math.sin(BR.ang),
            py = y + sx * (w / 2 + m) * Math.sin(BR.ang) + sy * (d / 2 + m) * Math.cos(BR.ang);
          return inside(px, py);
        });
      // glazed pitched rooflights over the internal halls, on low upstands, with ribs
      const lights = [];
      for (const [s, d, len] of [
        [0.5, 30, 34],
        [0.5, 50, 40],
        [0.3, 72, 26],
        [0.7, 72, 26],
        [0.5, 94, 30],
      ]) {
        const [x, y] = at(BR, BR.len * s, d);
        if (!fits(x, y, len, 7, 4)) continue;
        lights.push([x, y, len]);
        const r4 = [-1, 1, 1, -1].map((sx, k) => {
          const sy = k < 2 ? -1 : 1;
          return [
            x + sx * (len / 2) * Math.cos(BR.ang) - sy * 3.5 * Math.sin(BR.ang),
            y + sx * (len / 2) * Math.sin(BR.ang) + sy * 3.5 * Math.cos(BR.ang),
          ];
        });
        kit.walls(batch, plantTop, [[r4]], H + 2.1, H + 2.8, { bay: 1e6 });
        kit.pitchedRoof(batch, glazing, plantTop, r4, BR.ang, H + 2.8, 2.2, 'gabled', {
          overhang: 0,
        });
        for (let k = 0; k <= Math.round(len / 2); k++) {
          const t = -len / 2 + (k * len) / Math.round(len / 2);
          for (const sy of [-1, 1]) {
            const b0 = [
              x + t * Math.cos(BR.ang) - sy * 3.5 * Math.sin(BR.ang),
              y + t * Math.sin(BR.ang) + sy * 3.5 * Math.cos(BR.ang),
            ];
            const b1 = [x + t * Math.cos(BR.ang), y + t * Math.sin(BR.ang)];
            const geo = new THREE.BoxGeometry(0.1, 0.1, Math.hypot(3.5, 2.2));
            const dir = new THREE.Vector3(b1[0] - b0[0], b1[1] - b0[1], 2.2).normalize();
            const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
            batch.addGeometry(
              ribM,
              geo,
              new THREE.Matrix4().compose(
                new THREE.Vector3((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2, H + 2.8 + 1.1 + 0.04),
                q,
                new THREE.Vector3(1, 1, 1),
              ),
            );
            geo.dispose();
          }
        }
      }
      // plant rooms, lift motor rooms and tanks spread over the rest of the roof
      let placed = 0;
      for (let tries = 0; tries < 220 && placed < 18; tries++) {
        const x = mx + (rr() - 0.5) * 120,
          y = my + (rr() - 0.5) * 120;
        const w = 4 + rr() * 10,
          d = 3 + rr() * 6;
        if (!fits(x, y, w, d, 12)) continue;
        if (
          lights.some(
            ([lx, ly, ll]) => Math.hypot(lx - x, ly - y) < ll / 2 + Math.max(w, d) / 2 + 2,
          )
        )
          continue;
        const hh = 2.2 + rr() * 2.4;
        kit.box(batch, plant, x, y, H + 2.1, w, d, hh, BR.ang, [1, 1, 1]);
        kit.box(batch, plantTop, x, y, H + 2.1 + hh, w + 0.2, d + 0.2, 0.15, BR.ang);
        if (rr() < 0.4) {
          const fan = new THREE.CylinderGeometry(0.8, 0.8, 0.6, 12).rotateX(Math.PI / 2);
          batch.addGeometry(
            plantTop,
            fan,
            new THREE.Matrix4().makeTranslation(x, y, H + 2.1 + hh + 0.45),
          );
          fan.dispose();
        }
        placed++;
      }
    }

    g.add(batch.toGroup('harrods'));
    return g;
  },
};
