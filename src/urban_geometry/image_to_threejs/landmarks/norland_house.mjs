// Norland House, Edward Woods Estate, Shepherd's Bush (Hammersmith & Fulham council, late 1960s).
// One of the estate's three 24-storey residential towers (Norland, Poynter and Stebbing
// Houses): a twin-slab plan with recessed slots between the halves, refurbished c.2011-13
// (ECD Architects) with rendered external insulation and Rockpanel board cladding replacing
// the original brick finish, and four lightweight steel-framed penthouse flats added at roof
// level clad in wood-finish Rockpanel; further insulation and recladding works followed in 2022.
export default {
  id: 'norland_house',
  name: 'Norland House',
  claims: ['e082a5e9-2c2b-4173-a81f-f6a7792f4764'],
  references: [
    {
      title: 'Edward Woods Estate - London Gardens Trust inventory',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record/?ID=HAF012',
      used_for: 'estate layout and towers',
    },
    {
      title:
        'Rockwool helps the Edward Woods Estate achieve a low carbon future - Construction Index',
      url: 'https://www.theconstructionindex.co.uk/news/view/rockwool-helps-the-edward-woods-estate-achieve-a-low-carbon-future',
      used_for: 'refurbishment replacing the brick finish with rendered external insulation',
    },
    {
      title: 'ROCKPANEL breathes fresh life into a landmark project - Specification Online',
      url: 'https://mail.specificationonline.co.uk/articles/2016-03-22/rockpanel-breathes-fresh-life-into-a-landmark-project',
      used_for: 'Rockpanel cladding combined with Rockwool insulation',
    },
    {
      title: 'Edward Woods - ECD Architects',
      url: 'https://ecda.co.uk/?p=1149',
      used_for:
        'four penthouse flats on each tower roof, steel frames faced in wood-finish Rockpanel',
    },
    {
      title: 'Norland House - Buildington',
      url: 'https://www.buildington.co.uk/buildings/8288/england/london-w11/queensdale-crescent/norland-house',
      used_for:
        '24 storeys; ECD refurbishment 2013; 2022 removal of south-elevation solar panels and recladding',
    },
    {
      title: 'Appendix 1 - List of 6 storeys blocks - LBHF',
      url: 'https://democracy.lbhf.gov.uk/documents/s96936/Appendix 1 - List of 6 storeys blocks 051017.pdf',
      used_for: '24-storey blocks with 23 residential floors',
    },
  ],
  notes:
    'Height from 24 storeys (3.4 m ground + 22 x 2.75 m + 3.0 m penthouse level, ~67 m) instead of Overture h. ' +
    'Cladding colours (off-white render, grey bands, timber-tone penthouses), the window module, balcony ' +
    'positions and the lift-motor room are estimates; rooftop wind turbines and the former south-facade solar ' +
    'panels are omitted as their current state is unclear.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    // ---- local helpers (edge frames, boxes along edges, prisms, glazing) ----
    const B = new kit.MeshBatch();
    const ccw = (r) => {
      r = r.slice();
      if (kit.ringArea(r) < 0) r.reverse();
      return r;
    };
    const edgesOf = (r) =>
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
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box along edge e: s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, col) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(
        B,
        m,
        c[0],
        c[1],
        z0,
        Math.max(0.01, s1 - s0),
        Math.max(0.01, d1 - d0),
        z1 - z0,
        e.ang,
        col,
      );
    };
    const quad = (m, p, q, z0, z1, d = 0) =>
      B.quad(
        m,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    const prism = (wall, roof, ring, z0, z1, o = {}) => {
      kit.walls(B, wall, [[ring]], z0, z1, o);
      if (roof) kit.cap(B, roof, [[ring]], z1);
    };
    const parapet = (m, ring, z, h = 0.9, t = 0.3) => {
      const inn = kit.offsetRing(ring, -t).reverse();
      kit.walls(B, m, [[ring]], z, z + h, { bay: 1e6 });
      kit.walls(B, m, [[inn]], z, z + h, { bay: 1e6 });
      kit.cap(B, m, [[ring, inn]], z + h);
    };
    // Lofted band between two rings with equal vertex counts (sloped walls / roofs).
    const loft = (m, r0, z0, r1, z1) => {
      for (let k = 0; k < r0.length; k++) {
        const j = (k + 1) % r0.length;
        B.add(
          m,
          [
            [r0[k][0], r0[k][1], z0],
            [r0[j][0], r0[j][1], z0],
            [r1[j][0], r1[j][1], z1],
            [r1[k][0], r1[k][1], z1],
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
    };
    // Windows on every edge longer than minLen, storey by storey.
    const winRows = (ring, z0, n, st, opts, minLen = 4, filter) => {
      for (let s = 0; s < n; s++)
        for (const e of edgesOf(ring)) {
          if (e.len < minLen || (filter && !filter(e, s))) continue;
          kit.windowRow(B, e.a, e.b, z0 + s * st, typeof opts === 'function' ? opts(s, e) : opts);
        }
    };
    // Continuous glazing band with mullions on every edge of a ring.
    const ribbon = (ring, z0, z1, glass, mull, pitch = 1.5, minLen = 0.5, filter) => {
      for (const e of edgesOf(ring)) {
        if (e.len < minLen || (filter && !filter(e))) continue;
        quad(glass, e.a, e.b, z0, z1);
        const n = Math.max(1, Math.round(e.len / pitch));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(mull, e, Math.max(0, s - 0.05), Math.min(e.len, s + 0.05), 0, 0.12, z0, z1);
        }
      }
    };
    const frameAt = (f, u, v) => [
      f.cx + Math.cos(f.angle) * u - Math.sin(f.angle) * v,
      f.cy + Math.sin(f.angle) * u + Math.cos(f.angle) * v,
    ];
    const signMat = (key, text, bg, fg, font = 'bold 40px sans-serif', w = 512, h = 64) =>
      kit.paintedMaterial(
        key,
        w,
        h,
        (c, W, H) => {
          c.fillStyle = bg;
          c.fillRect(0, 0, W, H);
          c.fillStyle = fg;
          c.font = font;
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(text, W / 2, H / 2 + 2);
        },
        { roughness: 0.6 },
      );
    const cyl = (m, x, y, z0, r0, r1, h, seg = 16) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      B.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    // Rooftop plant boxes scattered within a ring's oriented frame.
    const plantBoxes = (ring, z, rnd, n, m, spread = 0.55) => {
      const f = kit.ringFrame(ring);
      for (let i = 0; i < n; i++) {
        const p = frameAt(f, (rnd() - 0.5) * f.length * spread, (rnd() - 0.5) * f.width * spread);
        kit.box(B, m, p[0], p[1], z, 2 + rnd() * 3, 1.5 + rnd() * 2, 1.2 + rnd() * 1.5, f.angle);
      }
    };
    // ---- end helpers ----
    const ring = ccw(buildings[0].polys[0][0]);
    const render = kit.mat('#e6e3dc', { roughness: 0.8 });
    const band = kit.mat('#8f969a', { roughness: 0.7 });
    const glass = kit.mat('#42535e', { roughness: 0.12, metalness: 0.3 });
    const frame = kit.mat('#f2f2f0', { roughness: 0.5 });
    const timberClad = kit.mat('#9b7451', { roughness: 0.75 });
    const roofM = kit.mat('#7d7f80');
    const rail = kit.mat('#b9c3c7', { roughness: 0.15, metalness: 0.3 });
    const brick = kit.mat('#7c5a4a');
    const G = 3.4,
      ST = 2.75,
      N = 22;
    const H = G + N * ST;
    // ground floor: entrance lobby glazing behind a brick plinth
    ribbon(kit.offsetRing(ring, -0.4), 0, G - 0.4, glass, kit.mat('#3a3a3a'), 2.0);
    kit.walls(B, brick, [[ring]], G - 0.4, G, { bay: 1e6 });
    kit.cap(B, brick, [[ring]], G - 0.4, { down: true });
    for (const e of edgesOf(ring)) {
      if (e.len < 4) continue;
      const n = Math.max(1, Math.round(e.len / 5));
      for (let k = 0; k <= n; k++) {
        const s = 0.3 + ((e.len - 0.6) * k) / n;
        ebox(brick, e, s - 0.3, s + 0.3, -0.4, 0, 0, G - 0.4);
      }
    }
    // residential floors: render spandrel + strip of windows with render piers
    const E = edgesOf(ring);
    for (let s = 0; s < N; s++) {
      const z = G + s * ST;
      kit.walls(B, s % 2 ? render : render, [[ring]], z, z + 0.95, { bay: 1e6 });
      const rg = kit.offsetRing(ring, -0.12);
      for (const e of edgesOf(rg)) {
        if (e.len < 0.3) continue;
        quad(glass, e.a, e.b, z + 0.95, z + ST - 0.3);
      }
      kit.walls(B, render, [[ring]], z + ST - 0.3, z + ST, { bay: 1e6 });
      if (s % 4 === 3) kit.cornice(B, band, ring, z + ST - 0.3, { height: 0.3, projection: 0.08 });
    }
    // vertical piers / window mullions over the full height
    for (const e of E) {
      if (e.len < 1.5) continue;
      const n = Math.max(1, Math.round(e.len / 2.4));
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        const w = k === 0 || k === n ? 0.35 : 0.22;
        ebox(
          k % 3 === 0 ? band : render,
          e,
          Math.max(0, s - w),
          Math.min(e.len, s + w),
          -0.05,
          0.12,
          G,
          H,
        );
      }
    }
    // balconies: glazed-balustrade balconies on the long east and west faces every storey
    for (const e of E) {
      if (e.len < 20) continue;
      for (let s = 1; s < N; s++) {
        const z = G + s * ST;
        for (const c of [e.len * 0.3, e.len * 0.7]) {
          ebox(render, e, c - 1.7, c + 1.7, 0.12, 1.3, z - 0.15, z);
          ebox(rail, e, c - 1.7, c + 1.7, 1.25, 1.3, z, z + 1.0);
        }
      }
    }
    kit.cap(B, roofM, [[ring]], H);
    parapet(band, ring, H, 0.9, 0.25);
    // penthouse level: set-back timber-clad flats with glazing and a lift-motor room
    {
      const p = kit.offsetRing(ring, -1.4);
      const f = kit.ringFrame(ring);
      const pr = [
        frameAt(f, -f.length / 2 + 1.6, -f.width / 2 + 1.6),
        frameAt(f, f.length / 2 - 1.6, -f.width / 2 + 1.6),
        frameAt(f, f.length / 2 - 1.6, f.width / 2 - 1.6),
        frameAt(f, -f.length / 2 + 1.6, f.width / 2 - 1.6),
      ];
      void p;
      const ph = ccw(pr);
      kit.walls(B, timberClad, [[ph]], H, H + 3.0, { bay: 1e6 });
      for (const e of edgesOf(ph)) {
        const n = Math.max(1, Math.floor(e.len / 3.2));
        for (let k = 0; k < n; k++) {
          const c = ((k + 0.5) * e.len) / n;
          if (k % 2 === 0) ebox(glass, e, c - 1.1, c + 1.1, 0, 0.05, H + 0.2, H + 2.6);
        }
        // vertical timber battens
        for (let s = 0.2; s < e.len; s += 0.6)
          ebox(timberClad, e, s - 0.04, s + 0.04, 0.02, 0.1, H, H + 3.0);
      }
      kit.cap(B, roofM, [[ph]], H + 3.0);
      kit.cornice(B, band, ph, H + 3.0, { height: 0.25, projection: 0.3 });
      const c = frameAt(f, 0, 0);
      kit.box(B, band, c[0], c[1], H + 3.0, 6, 4, 2.6, f.angle);
    }
    g.add(B.toGroup('norland_house'));
    return g;
  },
};
