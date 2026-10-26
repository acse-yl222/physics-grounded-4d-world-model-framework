// Shepherd's Bush Market, on the east side of the Hammersmith & City line viaduct between
// Uxbridge Road and Goldhawk Road (street market since 1914). Long narrow lane lined with single-storey
// lock-up stall units under corrugated roofs, colourful awnings and fascia boards: one row
// in front of the railway arches on the west side, another along the east side, and stall
// blocks towards Goldhawk Road, entered under a market sign from Uxbridge Road.
export default {
  id: 'shepherds_bush_market',
  name: "Shepherd's Bush Market",
  claims: [
    'b6430ab8-320a-4daf-91f4-36de9cec67c8',
    '3cc2605a-adf3-4a29-901a-d1f6181ea523',
    '0049adb7-fb31-4406-bf56-8e3711dc9bb4',
    'c72113f7-240a-4454-982d-a27f54503d49',
    'f093d704-dc30-48e5-8796-156f779e9841',
    '9ff781d7-4bad-4d2d-8cb3-6189dbf104fd',
  ],
  references: [
    {
      title: "Shepherd's Bush Market - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_Market',
      used_for: 'market history (1914 opening, 1918 reopening), Yoo Capital ownership',
    },
    {
      title: 'Shepherds Bush Market through the ages - LBHF',
      url: 'https://www.lbhf.gov.uk/news/2016/12/shepherds-bush-market-through-ages',
      used_for:
        'east side of the railway viaduct between Goldhawk Road and Uxbridge Road; 90+ traders',
    },
    {
      title: "About - Shepherd's Bush Market",
      url: 'https://shepherdsbushmarket.org/about/',
      used_for: 'stalls on Railway Approach from 30 June 1914',
    },
    {
      title: 'Shepherds Bush Market London - Foresyte',
      url: 'https://foresyteapp.com/shepherds-bush-market-london/',
      used_for: 'railway arches used as shops since the 1863 viaduct',
    },
  ],
  notes:
    'The six narrow 4 m "retail" footprints along the market lane are interpreted as the stall rows (west row in ' +
    'front of the railway arches, east row, and blocks near Goldhawk Road). Unit width (3 m), awning colours, ' +
    'fascia boards, roof form and the entrance sign are generic market stall features, not surveyed; the ' +
    'viaduct itself is not in the scene data and is not modelled. Recent redevelopment proposals are ignored.',
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
    const rec = (p) => ccw(buildings.find((b) => b.id.startsWith(p)).polys[0][0]);
    const rnd = kit.rng(0.2417);
    const roofM = kit.mat('#9aa0a3', { roughness: 0.5, metalness: 0.5 });
    const wall = kit.mat('#d9d4c8', { roughness: 0.85 });
    const shutter = kit.mat('#7f8a90', { roughness: 0.5, metalness: 0.5 });
    const dark = kit.mat('#2c2f31', { roughness: 0.8 });
    const steel = kit.mat('dark_steel');
    const awnCols = [
      '#c8102e',
      '#1d5fa8',
      '#2e8b57',
      '#f2a900',
      '#7b2d8b',
      '#e05a1b',
      '#16a2a6',
      '#b3202f',
    ];
    const awn = awnCols.map((c) => kit.mat(c, { roughness: 0.7 }));
    const fasciaCols = ['#ffffff', '#f6e7b4', '#ffd400', '#e5e5e5', '#d8ecff'];
    const fascia = fasciaCols.map((c) => kit.mat(c, { roughness: 0.6 }));
    const goods = ['#c43c3c', '#e9c46a', '#2a9d8f', '#f4a261', '#6d597a', '#ffffff', '#264653'].map(
      (c) => kit.mat(c, { roughness: 0.8 }),
    );

    // A stall row: rear wall/roof over the footprint, open fronts on the edges facing `side`.
    const row = (r, isFront) => {
      kit.walls(B, wall, [[r]], 0, 3.2, { bay: 1e6 });
      // mono-pitch corrugated roof: cap slightly raised, with a fascia
      kit.cap(B, roofM, [[r]], 3.6);
      kit.walls(B, roofM, [[r]], 3.2, 3.6, { bay: 1e6 });
      for (const e of edgesOf(r)) {
        if (e.len < 2.5 || !isFront(e)) continue;
        const n = Math.max(1, Math.round(e.len / 3.0));
        for (let k = 0; k < n; k++) {
          const s0 = (k * e.len) / n,
            s1 = ((k + 1) * e.len) / n;
          const open = rnd() < 0.75;
          if (open) {
            ebox(dark, e, s0 + 0.1, s1 - 0.1, -0.05, 0.02, 0, 2.6); // open stall interior
            // goods on display tables / racks
            ebox(
              goods[Math.floor(rnd() * goods.length)],
              e,
              s0 + 0.3,
              s1 - 0.3,
              0.05,
              0.85,
              0,
              0.9,
            );
            if (rnd() < 0.5)
              ebox(
                goods[Math.floor(rnd() * goods.length)],
                e,
                s0 + 0.4,
                s1 - 0.4,
                0.05,
                0.25,
                1.2,
                2.3,
              );
          } else ebox(shutter, e, s0 + 0.1, s1 - 0.1, 0.02, 0.06, 0, 2.6);
          ebox(steel, e, s0 - 0.06, s0 + 0.06, 0, 0.12, 0, 3.2); // divider post
          // fascia board and sloping awning
          ebox(
            fascia[Math.floor(rnd() * fascia.length)],
            e,
            s0 + 0.05,
            s1 - 0.05,
            0.02,
            0.12,
            2.7,
            3.2,
          );
          const a = awn[Math.floor(rnd() * awn.length)];
          const c = at(e, (s0 + s1) / 2, 0.85);
          const geo = new THREE.BoxGeometry(s1 - s0 - 0.1, 1.7, 0.05);
          const m = new THREE.Matrix4()
            .makeRotationZ(e.ang)
            .multiply(new THREE.Matrix4().makeRotationX(-0.35))
            .setPosition(c[0], c[1], 2.55);
          B.addGeometry(a, geo, m);
          geo.dispose();
        }
      }
    };
    const west = rec('b6430ab8'),
      west2 = rec('c72113f7'),
      east = rec('3cc2605a'),
      blk = rec('0049adb7'),
      north = rec('f093d704'),
      small = rec('9ff781d7');
    row(west, (e) => e.nx > 0.5);
    row(west2, (e) => e.nx > 0.5);
    row(east, (e) => e.nx < -0.5);
    row(north, (e) => e.nx < -0.5);
    row(blk, (e) => e.len > 5);
    row(small, (e) => e.len > 5);
    // lane surface: market stall pitches are left to the ground layer.
    // Uxbridge Road entrance sign spanning the lane at its north end
    {
      const a = west[0],
        b = north[north.length - 2] || north[0];
      const e = edgesOf([a, b])[0];
      cyl(steel, a[0], a[1], 0, 0.12, 0.12, 5.6, 8);
      cyl(steel, b[0], b[1], 0, 0.12, 0.12, 5.6, 8);
      ebox(
        signMat('sbm:sign', "SHEPHERD'S BUSH MARKET", '#c8102e', '#ffffff', 'bold 30px sans-serif'),
        e,
        0,
        e.len,
        -0.08,
        0.08,
        4.4,
        5.4,
      );
    }
    g.add(B.toGroup('shepherds_bush_market'));
    return g;
  },
};
