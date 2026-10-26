// Royal College of Music, Prince Consort Road (Sir Arthur Blomfield, 1890-94), with the
// Amaryllis Fleming Concert Hall behind (Sidney Smith, 1899-1901) and the later
// Britten Theatre block. Symmetrical twelve-bay red brick front with buff stone
// banding and dressings, a steep slate roof with dormers, end towers capped by
// pyramidal roofs with corner tourelles, and a projecting two-bay centre with a stone
// gable holding a clock flanked by finials over a central arched entrance.
export default {
  id: 'royal_college_of_music',
  name: 'Royal College of Music',
  claims: [
    '9e685150-c49b-4687-89d0-5391bdc51b65', // Blomfield building (front range)
    'd8830a31-a66e-49d9-8059-c1ee4c3aef03', // Amaryllis Fleming Concert Hall
    '8a4fa60d-dd46-4859-9c06-770968c77ed3', // Britten Theatre block (west of the courtyard)
  ],
  references: [
    {
      title: 'Royal College of Music - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101265501-royal-college-of-music-knightsbridge-and-belgravia-ward',
      used_for:
        'twelve-bay symmetrical front, red brick with stone banding, steep slate roof, end towers with pyramidal tops and tourelles, centre gable with clock, concert hall 1899-1901 by Sidney Smith',
    },
    {
      title: 'Royal College of Music - victorianweb.org',
      url: 'https://victorianweb.org/art/architecture/blomfield/2.html',
      used_for: 'Blomfield design opposite the Royal Albert Hall',
    },
    {
      title: 'Royal College of Music, London - penang-traveltips',
      url: 'https://www.penang-traveltips.com/europe/uk/england/london/royal-college-of-music.htm',
      used_for: 'Flemish Mannerist style, red brick dressed with buff stone',
    },
    {
      title: 'Royal College of Music dramatic new - Planet Hugill',
      url: 'https://www.planethugill.com/2015/04/royal-college-of-music-dramatic-new.html',
      used_for: 'Britten Theatre lies west of the courtyard behind the front range',
    },
  ],
  notes:
    'Eaves raised to ~17 m with a ~6 m slate roof; towers to ~25 m walls plus pyramidal caps (~33 m) proportioned from the ' +
    'listing description, not measured. The 8a4fa60d footprint is assumed to be the Britten Theatre block (modelled as a plain ' +
    'brick volume). The north (Prince Consort Road) elevations have 3D stone-dressed windows, string courses, quoins, a ' +
    'columned entrance portal with steps, name band and area railings; side and rear elevations keep a painted 4-bay tile. ' +
    'Chimney positions, dormer count and tourelle details are approximations; the clock gable is simplified.',
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const BRICK = '#9c4a36',
      STONE = '#d8c49a';
    const stone = kit.mat(STONE),
      slate = kit.roof('slate', 1),
      lead = kit.mat('#5f676c', { roughness: 0.5, metalness: 0.3 }),
      brick = kit.mat(BRICK);

    // Facade tile: 4 bays (3.6 m) x full eaves height H (17 m), drawn bottom-up.
    const H = 17;
    const facadeMat = (key, hgt, opts = {}) =>
      kit.paintedMaterial(`royal_college_of_music:${key}`, 512, 512, (c, w, h) => {
        const P = h / hgt,
          Y = (m) => h - m * P,
          bw = w / 4;
        c.fillStyle = BRICK;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(0,0,0,0.06)';
        for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
        const band = (z0, z1, col = STONE) => {
          c.fillStyle = col;
          c.fillRect(0, Y(z1), w, (z1 - z0) * P);
        };
        // Ground storey banded in stone and brick.
        for (let z = 0.4; z < 4.4; z += 0.6) band(z, z + 0.3);
        band(0, 0.6, '#b7a27c');
        const win = (x, z0, z1, ww, arch) => {
          c.fillStyle = STONE;
          c.fillRect(x - ww / 2 - 4, Y(z1) - 4, ww + 8, (z1 - z0) * P + 8);
          c.fillStyle = '#28303a';
          c.fillRect(x - ww / 2, Y(z1), ww, (z1 - z0) * P);
          if (arch) {
            c.fillStyle = STONE;
            c.beginPath();
            c.arc(x, Y(z1), ww / 2 + 4, Math.PI, 0);
            c.fill();
            c.fillStyle = '#28303a';
            c.beginPath();
            c.arc(x, Y(z1), ww / 2, Math.PI, 0);
            c.fill();
          }
          // stone mullion and transom
          c.fillStyle = STONE;
          c.fillRect(x - 2, Y(z1), 4, (z1 - z0) * P);
          c.fillRect(x - ww / 2, Y(z0 + (z1 - z0) * 0.62), ww, 4);
        };
        for (let b = 0; b < 4 && opts.windows !== false; b++) {
          const x = bw * (b + 0.5);
          if (opts.ground !== false) win(x, 1.0, 3.6, 46, true);
          win(x, 5.4, 8.4, 52, false);
          win(x, 9.6, 12.2, 52, false);
          win(x, 13.4, 15.4, 46, false);
          // pilaster strips between bays
          c.fillStyle = 'rgba(60,20,10,0.25)';
          c.fillRect(b * bw, Y(16), 6, 11.6 * P);
        }
        band(4.6, 5.0);
        band(8.9, 9.2);
        band(12.7, 13.0);
        band(16.0, 17.0);
        if (hgt > 17 && opts.windows !== false)
          for (let b = 0; b < 4; b++) win(bw * (b + 0.5), 18, 22, 40, true);
      });
    const front = facadeMat('front', H);
    const plain = facadeMat('plain', H, { windows: false });
    const plainTower = facadeMat('plainTower', 26, { windows: false });
    const glass = kit.mat('#26303a', { roughness: 0.15, metalness: 0.3 }),
      white = kit.mat('#ece8de'),
      timber = kit.mat('#4a3022', { roughness: 0.7 }),
      ironMat = kit.mat('#1d2022', { roughness: 0.5, metalness: 0.4 });
    // ---- Lean framed windows (local x along the wall a -> b, y up, z outward; outward
    // normal on the right of a -> b), cached per spec: glass, moulded surround, mullion
    // and transom, sill, keystone or pediment.
    const winKit = (() => {
      const cache = new Map();
      const outline = (w, h, head, grow) => {
        const s = new THREE.Shape();
        const x0 = -w / 2 - grow,
          x1 = w / 2 + grow;
        s.moveTo(x0, -grow);
        s.lineTo(x1, -grow);
        if (head === 'arch') {
          s.lineTo(x1, h);
          s.absarc(0, h, w / 2 + grow, 0, Math.PI, false);
        } else {
          s.lineTo(x1, h + grow);
          s.lineTo(x0, h + grow);
        }
        s.lineTo(x0, -grow);
        return s;
      };
      const parts = (spec) => {
        const key = JSON.stringify(spec, (k, v) => (v && v.isMaterial ? v.uuid : v));
        if (cache.has(key)) return cache.get(key);
        const {
          w,
          h,
          head = 'flat',
          bars = 1,
          f = 0.18,
          glass,
          sur,
          bar,
          sill: sillMat,
          depth = 0.13,
        } = spec;
        const out = [];
        const gs = new THREE.ShapeGeometry(outline(w, h, head, 0), 5);
        gs.translate(0, 0, 0.02);
        out.push([gs, glass]);
        if (f > 0) {
          const ring = outline(w, h, head, f);
          ring.holes.push(new THREE.Path(outline(w, h, head, 0).getPoints(5).reverse()));
          out.push([
            new THREE.ExtrudeGeometry(ring, { depth, bevelEnabled: false, curveSegments: 5 }),
            sur,
          ]);
        }
        const top = head === 'arch' ? h + w / 2 : h;
        if (bars) {
          const nv = bars === 2 ? 2 : 1;
          for (let i = 1; i <= nv; i++) {
            const vb = new THREE.BoxGeometry(0.07, top, 0.07);
            vb.translate(-w / 2 + (w * i) / (nv + 1), top / 2, 0.06);
            out.push([vb, bar]);
          }
          const hb = new THREE.BoxGeometry(w, 0.07, 0.07);
          hb.translate(0, head === 'arch' ? h : h * 0.66, 0.06);
          out.push([hb, bar]);
        }
        const sl = new THREE.BoxGeometry(w + 2 * f + 0.2, 0.14, 0.26);
        sl.translate(0, -f - 0.07, 0.13);
        out.push([sl, sillMat ?? sur]);
        if (head === 'arch') {
          const ks = new THREE.BoxGeometry(Math.max(0.22, w * 0.18), f + 0.12, 0.2);
          ks.translate(0, top + f / 2, 0.1);
          out.push([ks, sur]);
        } else if (head === 'pediment' || head === 'lintel') {
          const hw = w / 2 + f + 0.15;
          const lt = new THREE.BoxGeometry(2 * hw, 0.16, 0.24);
          lt.translate(0, h + f + 0.08, 0.12);
          out.push([lt, sur]);
          if (head === 'pediment') {
            const t = new THREE.Shape();
            t.moveTo(-hw, 0);
            t.lineTo(hw, 0);
            t.lineTo(0, hw * 0.42);
            t.closePath();
            const pg = new THREE.ExtrudeGeometry(t, { depth: 0.22, bevelEnabled: false });
            pg.translate(0, h + f + 0.16, 0);
            out.push([pg, sur]);
          }
        }
        cache.set(key, out);
        return out;
      };
      const edge = (a, b) => {
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        const ux = (b[0] - a[0]) / L,
          uy = (b[1] - a[1]) / L;
        return { a, b, L, ux, uy, nx: uy, ny: -ux, ang: Math.atan2(uy, ux) };
      };
      const place = (e, geo, m, lx, z, out = 0) => {
        const mm = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(e.ux, e.uy, 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(e.nx, e.ny, 0),
        );
        mm.setPosition(e.a[0] + e.ux * lx + e.nx * out, e.a[1] + e.uy * lx + e.ny * out, z);
        batch.addGeometry(m, geo, mm);
      };
      const row = (a, b, z, n, margin, spec) => {
        const e = edge(a, b);
        const usable = e.L - 2 * margin;
        const xs = [];
        for (let k = 0; k < n; k++) {
          const lx = margin + (usable * (k + 0.5)) / n;
          for (const [geo, m] of parts(spec)) place(e, geo, m, lx, z);
          xs.push(lx);
        }
        return xs;
      };
      // Projecting band (string course) along an edge.
      const band = (a, b, z, h, proj, m) => {
        const e = edge(a, b);
        kit.box(
          batch,
          m,
          (a[0] + b[0]) / 2 + (e.nx * proj) / 2,
          (a[1] + b[1]) / 2 + (e.ny * proj) / 2,
          z,
          e.L + proj,
          proj,
          h,
          e.ang,
        );
      };
      return { parts, edge, place, row, band };
    })();
    const latheB = (mat, prof, o) => {
      const m = kit.lathe(mat, prof, o);
      m.updateMatrix();
      batch.addGeometry(mat, m.geometry, m.matrix);
      m.geometry.dispose();
    };
    const wallQuad = (mat, a, b, z0, z1, storey) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const n = Math.round(len / 3.6);
      const u1 = n >= 1 ? n / 4 : 0.03;
      batch.quad(
        mat,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, z0 / (2 * storey)],
        [u1, z0 / (2 * storey)],
        [u1, z1 / (2 * storey)],
        [0, z1 / (2 * storey)],
      );
    };

    // ---- Front range.
    const main = byId['9e685150-c49b-4687-89d0-5391bdc51b65'];
    let fr = null;
    if (main) {
      const ring = ccw(main.polys[0][0]);
      fr = kit.ringFrame(ring);
      let ang = fr.angle;
      if (Math.cos(ang) < 0) ang += Math.PI;
      const e = kit.orientedExtent(ring, ang);
      const north = [];
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const ed = winKit.edge(a, b);
        const isFront = ed.nx * -Math.sin(ang) + ed.ny * Math.cos(ang) > 0.6;
        wallQuad(isFront ? plain : front, a, b, 0, H, H / 2);
        if (isFront) north.push(ed);
      }
      const win3 = (a, b, n, margin, centre) => {
        if (!centre)
          winKit.row(a, b, 1.0, n, margin, {
            w: 1.5,
            h: 1.9,
            head: 'arch',
            glass,
            sur: stone,
            bar: white,
            f: 0.2,
          });
        winKit.row(a, b, 5.4, n, margin, {
          w: 1.75,
          h: 3.0,
          head: 'lintel',
          glass,
          sur: stone,
          bar: stone,
          f: 0.16,
        });
        winKit.row(a, b, 9.6, n, margin, {
          w: 1.75,
          h: 2.6,
          head: 'lintel',
          glass,
          sur: stone,
          bar: stone,
          f: 0.16,
        });
        winKit.row(a, b, 13.4, n, margin, {
          w: 1.6,
          h: 2.0,
          head: 'flat',
          glass,
          sur: stone,
          bar: stone,
          f: 0.14,
        });
      };
      for (const ed of north) {
        // string courses and quoins
        for (const [z, h, pr] of [
          [0, 0.6, 0.12],
          [4.6, 0.4, 0.14],
          [8.9, 0.3, 0.1],
          [12.7, 0.3, 0.1],
        ])
          winKit.band(ed.a, ed.b, z, h, pr, stone);
        for (const p of [ed.a, ed.b])
          for (let z = 0.6; z < H - 1; z += 1.2)
            kit.box(
              batch,
              stone,
              p[0] + ed.nx * 0.05,
              p[1] + ed.ny * 0.05,
              z,
              0.7,
              0.12,
              0.6,
              ed.ang,
            );
        if (ed.L < 3) continue;
        const n = Math.max(1, Math.round((ed.L - 1.2) / 3.6));
        const mu =
          ((ed.a[0] + ed.b[0]) / 2) * Math.cos(ang) + ((ed.a[1] + ed.b[1]) / 2) * Math.sin(ang);
        const centre = Math.abs(mu - (e.u0 + e.u1) / 2) < 6.5;
        win3(ed.a, ed.b, n, 0.6, centre);
      }
      kit.cap(batch, kit.mat('#5d6268'), [[ring]], H);
      // projecting stone cornice
      const ro = kit.offsetRing(ring, 0.35);
      kit.walls(batch, stone, [[ro]], H - 0.6, H);
      kit.cap(batch, stone, [[ro, ring.slice().reverse()]], H);
      const L = e.u1 - e.u0;
      const tw = Math.min(11.5, L * 0.18); // tower width along the front
      const at = (u, v, z) => e.at(u, v, z);
      const rect = (ua, ub, va, vb) =>
        [at(ua, va, 0), at(ub, va, 0), at(ub, vb, 0), at(ua, vb, 0)].map((p) => [p[0], p[1]]);
      // Steep slate roof over the range between the towers, with dormers.
      const ru0 = e.u0 + tw,
        ru1 = e.u1 - tw;
      kit.pitchedRoof(
        batch,
        slate,
        brick,
        rect(ru0, ru1, e.v0 + 0.5, e.v1 - 0.6),
        ang,
        H,
        6.2,
        'hipped',
        { overhang: 0.3 },
      );
      // Dormers on the front (north, +v) slope: stone cheeks, framed window, slate gable.
      const nd = 8;
      for (let k = 0; k < nd; k++) {
        const u = ru0 + 3 + ((ru1 - ru0 - 6) * (k + 0.5)) / nd;
        const p = at(u, e.v1 - 2.0, 0);
        kit.box(batch, stone, p[0], p[1], H, 2.0, 2.2, 2.4, ang);
        winKit.row(at(u + 1.0, e.v1 - 0.9, 0), at(u - 1.0, e.v1 - 0.9, 0), H + 0.45, 1, 0.4, {
          w: 1.0,
          h: 1.4,
          head: 'flat',
          glass,
          sur: white,
          bar: white,
          f: 0.08,
        });
        kit.pitchedRoof(
          batch,
          slate,
          stone,
          rectAround(p, 2.0, 2.2),
          ang + Math.PI / 2,
          H + 2.4,
          1.0,
          'gabled',
          {
            overhang: 0.1,
          },
        );
        const f = at(u, e.v1 - 0.95, 0);
        kit.box(batch, stone, f[0], f[1], H + 3.4, 0.25, 0.25, 0.7, ang);
      }
      function rectAround(p, w, d) {
        const c = Math.cos(ang),
          s = Math.sin(ang);
        return [
          [-w / 2, -d / 2],
          [w / 2, -d / 2],
          [w / 2, d / 2],
          [-w / 2, d / 2],
        ].map(([x, y]) => [p[0] + x * c - y * s, p[1] + x * s + y * c]);
      }
      // Tall brick chimney stacks on the back slope with stone caps and pots.
      const pot = new THREE.CylinderGeometry(0.18, 0.22, 0.8, 8).rotateX(Math.PI / 2);
      for (const t of [0.12, 0.38, 0.62, 0.88]) {
        const p = at(ru0 + (ru1 - ru0) * t, e.v0 + 4.5, 0);
        kit.box(batch, brick, p[0], p[1], H + 2, 2.2, 0.9, 5.6, ang);
        kit.box(batch, stone, p[0], p[1], H + 5.6, 2.45, 1.15, 0.3, ang);
        kit.box(batch, stone, p[0], p[1], H + 7.6, 2.45, 1.15, 0.3, ang);
        for (const d of [-0.8, 0, 0.8]) {
          const q = at(ru0 + (ru1 - ru0) * t + d * 0.8, e.v0 + 4.5, 0);
          batch.addGeometry(
            kit.mat('#9a5a3e'),
            pot,
            new THREE.Matrix4().makeTranslation(q[0], q[1], H + 8.3),
          );
        }
      }
      pot.dispose();
      // End towers: walls rising to 26 m with arched windows, pyramidal slate caps, tourelles.
      for (const [ua, ub] of [
        [e.u0, e.u0 + tw],
        [e.u1 - tw, e.u1],
      ]) {
        const tr = rect(ua, ub, e.v0 + 1.0, e.v1);
        const tH = 26;
        const tro8 = kit.offsetRing(tr, 0.08);
        kit.walls(batch, plainTower, [[tro8]], H - 0.6, tH, { bay: tw / 2 + 0.01, storey: tH / 2 });
        for (let k = 0; k < 4; k++) {
          const a = tro8[k],
            b = tro8[(k + 1) % 4];
          winKit.row(a, b, 18.2, 2, 1.6, {
            w: 1.5,
            h: 2.4,
            head: 'arch',
            glass,
            sur: stone,
            bar: white,
            f: 0.2,
          });
          winKit.row(a, b, 22.4, 3, 1.4, {
            w: 0.8,
            h: 1.1,
            head: 'flat',
            glass,
            sur: stone,
            bar: stone,
            f: 0.12,
          });
          winKit.band(a, b, 21.6, 0.35, 0.12, stone);
        }
        kit.cornice(batch, stone, tro8, tH - 0.9, { height: 0.9, projection: 0.45, steps: 3 });
        kit.cap(batch, stone, [[kit.offsetRing(tr, 0.53)]], tH);
        kit.pitchedRoof(batch, slate, brick, tr, ang, tH, 9.5, 'pyramidal', { overhang: 0 });
        const tc = at((ua + ub) / 2, (e.v0 + 1 + e.v1) / 2, 0);
        latheB(
          lead,
          [
            [0.001, 0],
            [0.4, 0],
            [0.18, 0.5],
            [0.3, 0.9],
            [0.06, 1.3],
            [0.04, 3.4],
            [0.001, 3.5],
          ],
          {
            x: tc[0],
            y: tc[1],
            z: tH + 9.1,
            segments: 10,
          },
        );
        // gabled lucarne on each face of the pyramid
        for (const [u, v, rot] of [
          [(ua + ub) / 2, e.v1 - 1.2, 0],
          [(ua + ub) / 2, e.v0 + 2.2, Math.PI],
        ]) {
          const p = at(u, v, 0);
          kit.box(batch, stone, p[0], p[1], tH, 1.8, 1.2, 2.2, ang);
          kit.pitchedRoof(
            batch,
            slate,
            stone,
            rectAround(p, 1.8, 1.2),
            ang + Math.PI / 2,
            tH + 2.2,
            0.9,
            'gabled',
            { overhang: 0.08 },
          );
          const q = at(u, v + (rot ? -0.62 : 0.62), 0);
          kit.box(batch, glass, q[0], q[1], tH + 0.4, 0.9, 0.05, 1.3, ang);
        }
        for (const [u, v] of [
          [ua, e.v0 + 1.0],
          [ub, e.v0 + 1.0],
          [ua, e.v1],
          [ub, e.v1],
        ]) {
          const p = at(u, v, 0);
          latheB(
            brick,
            [
              [0.85, 0],
              [0.9, 0.3],
              [0.9, 5.5],
            ],
            { x: p[0], y: p[1], z: tH - 3, segments: 12 },
          );
          latheB(
            stone,
            [
              [0.9, 0],
              [1.05, 0.15],
              [1.05, 0.55],
              [0.9, 0.7],
            ],
            { x: p[0], y: p[1], z: tH + 2.4, segments: 12 },
          );
          latheB(
            slate,
            [
              [1.05, 0],
              [0.7, 1.4],
              [0.25, 3.0],
              [0.001, 3.8],
            ],
            { x: p[0], y: p[1], z: tH + 3.1, segments: 12 },
          );
          latheB(
            lead,
            [
              [0.06, 0],
              [0.03, 1.2],
              [0.001, 1.25],
            ],
            { x: p[0], y: p[1], z: tH + 6.85, segments: 6 },
          );
          // corbel ring under the tourelle
          latheB(
            stone,
            [
              [0.001, 0],
              [0.3, 0],
              [0.9, 0.9],
            ],
            { x: p[0], y: p[1], z: tH - 3.9, segments: 12 },
          );
        }
      }
      // Projecting centre with stone Flemish gable, clock and finials; arched entrance.
      const um = (e.u0 + e.u1) / 2;
      const uOf = (p) => p[0] * Math.cos(ang) + p[1] * Math.sin(ang);
      const cEdges = north.filter(
        (ed) =>
          ed.L > 3 && Math.abs(uOf([(ed.a[0] + ed.b[0]) / 2, (ed.a[1] + ed.b[1]) / 2]) - um) < 6.5,
      );
      const cf = cEdges.length
        ? winKit.edge(cEdges[0].a, cEdges[cEdges.length - 1].b)
        : winKit.edge(at(um + 5, e.v1, 0), at(um - 5, e.v1, 0));
      const cm = [(cf.a[0] + cf.b[0]) / 2, (cf.a[1] + cf.b[1]) / 2];
      const th = cf.ang + Math.PI; // along the front towards the east
      const cp = (d, out) => [cm[0] - cf.ux * d + cf.nx * out, cm[1] - cf.uy * d + cf.ny * out];
      const cw = Math.min(10.5, cf.L);
      const gz0 = H,
        gz1 = H + 7.5;
      const shape = new THREE.Shape();
      shape.moveTo(-cw / 2, 0);
      shape.lineTo(cw / 2, 0);
      shape.lineTo(cw / 2, 1.2);
      shape.quadraticCurveTo(cw / 2 - 0.3, 3.2, cw / 2 - 1.6, 3.6);
      shape.lineTo(cw / 2 - 1.6, 5.2);
      shape.quadraticCurveTo(1.6, 6.2, 0, gz1 - gz0);
      shape.quadraticCurveTo(-1.6, 6.2, -cw / 2 + 1.6, 5.2);
      shape.lineTo(-cw / 2 + 1.6, 3.6);
      shape.quadraticCurveTo(-cw / 2 + 0.3, 3.2, -cw / 2, 1.2);
      shape.lineTo(-cw / 2, 0);
      const gab = new THREE.ExtrudeGeometry(shape, {
        depth: 1.2,
        bevelEnabled: false,
        curveSegments: 6,
      });
      gab.rotateX(Math.PI / 2);
      gab.rotateZ(th);
      const gp = cp(0, 0.3);
      gab.translate(gp[0], gp[1], gz0);
      batch.addGeometry(stone, gab, null);
      // gable windows: pair under the clock, small oculus above
      winKit.row(cp(cw / 2 - 1.8, 0.31), cp(-cw / 2 + 1.8, 0.31), H + 0.5, 2, 0.6, {
        w: 1.1,
        h: 1.6,
        head: 'arch',
        glass,
        sur: kit.mat('#c9b48a'),
        bar: white,
        f: 0.15,
      });
      const clock = kit.paintedMaterial('royal_college_of_music:clock2', 128, 128, (c, w, h) => {
        c.fillStyle = STONE;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d6b04c';
        c.beginPath();
        c.arc(w / 2, h / 2, 60, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = '#1c2a3a';
        c.beginPath();
        c.arc(w / 2, h / 2, 54, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = '#e8d9a8';
        for (let k = 0; k < 12; k++) {
          const t = (k / 12) * Math.PI * 2;
          c.fillRect(w / 2 + Math.cos(t) * 44 - 3, h / 2 + Math.sin(t) * 44 - 3, 6, 6);
        }
        c.strokeStyle = '#d6b04c';
        c.lineWidth = 5;
        c.beginPath();
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2, 22);
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2 + 28, h / 2 + 12);
        c.stroke();
      });
      const ccp = cp(0, 0.36);
      const cg = new THREE.Mesh(new THREE.CircleGeometry(1.0, 24), clock);
      cg.rotation.set(-Math.PI / 2, 0, 0);
      const holder = new THREE.Group();
      holder.add(cg);
      holder.position.set(ccp[0], ccp[1], gz0 + 3.9);
      holder.rotation.z = th;
      g.add(holder);
      for (const sgn of [-1, 1]) {
        const p = cp(sgn * (cw / 2 - 0.3), -0.3);
        latheB(
          stone,
          [
            [0.001, 0],
            [0.45, 0],
            [0.45, 0.5],
            [0.3, 0.7],
            [0.32, 1.2],
            [0.12, 2.4],
            [0.001, 2.6],
          ],
          {
            x: p[0],
            y: p[1],
            z: gz0 + 1.2,
            segments: 8,
          },
        );
        const q = cp(sgn * (cw / 2 - 1.6), -0.3);
        latheB(
          stone,
          [
            [0.001, 0],
            [0.3, 0],
            [0.3, 0.4],
            [0.1, 1.6],
            [0.001, 1.7],
          ],
          {
            x: q[0],
            y: q[1],
            z: gz0 + 5.2,
            segments: 8,
          },
        );
      }
      const apex = cp(0, -0.3);
      latheB(
        stone,
        [
          [0.001, 0],
          [0.35, 0],
          [0.35, 0.4],
          [0.18, 0.5],
          [0.25, 0.9],
          [0.05, 2.0],
          [0.001, 2.05],
        ],
        {
          x: apex[0],
          y: apex[1],
          z: gz1 - 0.1,
          segments: 8,
        },
      );
      // Gable roof behind the centre gable.
      kit.pitchedRoof(
        batch,
        slate,
        brick,
        rect(um - cw / 2 + 0.5, um + cw / 2 - 0.5, e.v1 - 8, e.v1 - 0.2),
        ang + Math.PI / 2,
        H,
        6.4,
        'gabled',
        { overhang: 0 },
      );
      // Entrance: stone portal with columns, timber doors under arched fanlights, steps.
      const portal = [cp(2.9, 0.02), cp(-2.9, 0.02)];
      const pe = winKit.edge(portal[0], portal[1]);
      kit.box(
        batch,
        stone,
        (portal[0][0] + portal[1][0]) / 2 + pe.nx * 0.3,
        (portal[0][1] + portal[1][1]) / 2 + pe.ny * 0.3,
        0,
        6.4,
        0.6,
        4.6,
        pe.ang,
      );
      winKit.row(cp(2.9, 0.62), cp(-2.9, 0.62), 0.45, 1, 1.6, {
        w: 2.3,
        h: 2.5,
        head: 'arch',
        glass: timber,
        sur: kit.mat('#c9b48a'),
        bar: kit.mat('#2a1c14'),
        f: 0.35,
      });
      winKit.row(cp(-1.6, 0.02), cp(-3.2, 0.02), 0.45, 1, 0.1, {
        w: 1.2,
        h: 2.0,
        head: 'arch',
        glass: timber,
        sur: stone,
        bar: kit.mat('#2a1c14'),
        f: 0.2,
      });
      winKit.row(cp(3.2, 0.02), cp(1.6, 0.02), 0.45, 1, 0.1, {
        w: 1.2,
        h: 2.0,
        head: 'arch',
        glass: timber,
        sur: stone,
        bar: kit.mat('#2a1c14'),
        f: 0.2,
      });
      kit.colonnade(
        batch,
        kit.mat('#a7978a', { roughness: 0.35 }),
        cp(1.75, 1.15),
        cp(-1.75, 1.15),
        0.45,
        3.9,
        { count: 2, radius: 0.22, capital: 'corinthian', segments: 10 },
      );
      const ent = cp(0, 0.95);
      kit.box(batch, stone, ent[0], ent[1], 4.35, 4.4, 0.9, 0.5, pe.ang);
      // name band over the entrance
      const sign = kit.paintedMaterial('royal_college_of_music:sign', 512, 48, (c, w, h) => {
        c.fillStyle = STONE;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#5a3a26';
        c.font = 'bold 30px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('ROYAL COLLEGE OF MUSIC', w / 2, h / 2 + 2);
      });
      {
        const p0 = cp(2.6, 0.63),
          p1 = cp(-2.6, 0.63);
        batch.quad(
          sign,
          [p0[0], p0[1], 4.85],
          [p1[0], p1[1], 4.85],
          [p1[0], p1[1], 5.45],
          [p0[0], p0[1], 5.45],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      for (let k = 0; k < 3; k++) {
        const p = cp(0, 1.7 + (2 - k) * 0.35);
        kit.box(
          batch,
          kit.mat('#b9b0a2'),
          p[0],
          p[1],
          k * 0.15,
          5.6 + (2 - k) * 0.6,
          0.35 + (2 - k) * 0.0,
          0.15,
          pe.ang,
        );
      }
      // Area railings along the front (black iron with finials) and lamps by the door.
      for (const ed of north) {
        if (ed.L < 3) continue;
        const off = 1.4,
          a = [ed.a[0] + ed.nx * off, ed.a[1] + ed.ny * off],
          b = [ed.b[0] + ed.nx * off, ed.b[1] + ed.ny * off];
        const uC = uOf([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
        if (Math.abs(uC - um) < 4) continue;
        kit.box(
          batch,
          ironMat,
          (a[0] + b[0]) / 2,
          (a[1] + b[1]) / 2,
          1.0,
          ed.L,
          0.05,
          0.06,
          ed.ang,
        );
        kit.box(
          batch,
          ironMat,
          (a[0] + b[0]) / 2,
          (a[1] + b[1]) / 2,
          0.15,
          ed.L,
          0.05,
          0.06,
          ed.ang,
        );
        const n = Math.floor(ed.L / 0.16);
        for (let i = 0; i < n; i++) {
          const t = (i + 0.5) / n;
          kit.box(
            batch,
            ironMat,
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            0,
            0.025,
            0.025,
            1.15,
            ed.ang,
          );
        }
      }
      const lampAt = [cp(3.6, 1.6), cp(-3.6, 1.6)].map((p) => [p[0], p[1], cf.ang + Math.PI]);
      if (placeAssets) g.add(placeAssets('street_lamp', lampAt));
    }

    // ---- Amaryllis Fleming Concert Hall: brick hall with tall arched windows, slate roof.
    const hall = byId['d8830a31-a66e-49d9-8059-c1ee4c3aef03'];
    if (hall) {
      const ring = ccw(hall.polys[0][0]);
      const hf = kit.ringFrame(ring);
      const hH = 13.6;
      const hallMat = kit.paintedMaterial('royal_college_of_music:hall', 512, 256, (c, w, h) => {
        const P = h / hH,
          Y = (m) => h - m * P;
        c.fillStyle = BRICK;
        c.fillRect(0, 0, w, h);
        c.fillStyle = STONE;
        c.fillRect(0, Y(1), w, P);
        c.fillRect(0, Y(13.6), w, 0.8 * P);
        for (let b = 0; b < 4; b++) {
          const x = (w / 4) * (b + 0.5);
          c.fillStyle = STONE;
          c.fillRect(x - 26, Y(11), 52, 8 * P);
          c.beginPath();
          c.arc(x, Y(11), 26, Math.PI, 0);
          c.fill();
          c.fillStyle = '#2a323c';
          c.fillRect(x - 20, Y(10.8), 40, 7.6 * P);
          c.beginPath();
          c.arc(x, Y(10.8), 20, Math.PI, 0);
          c.fill();
        }
      });
      kit.walls(batch, hallMat, [[ring]], 0, hH, { bay: 4.0, storey: hH / 2 });
      kit.pitchedRoof(batch, slate, brick, ring, hf.angle, hH, 5.0, 'gabled', { overhang: 0.2 });
      // roof lantern / ventilator along the ridge
      const p = [hf.cx, hf.cy];
      kit.box(batch, lead, p[0], p[1], hH + 4.6, hf.length * 0.5, 1.6, 1.0, hf.angle);
    }

    // ---- Britten Theatre block: plain brick fly-tower volume.
    const bt = byId['8a4fa60d-dd46-4859-9c06-770968c77ed3'];
    if (bt) {
      const ring = ccw(bt.polys[0][0]);
      kit.walls(batch, kit.facade('red_brick', 2), [[ring]], 0, bt.h ?? 16.5, {
        bay: 3.6,
        storey: 3.4,
      });
      kit.cap(batch, kit.mat('#6a6c6e'), [[ring]], bt.h ?? 16.5);
    }
    g.add(batch.toGroup('royal_college_of_music'));
    return g;
  },
};
