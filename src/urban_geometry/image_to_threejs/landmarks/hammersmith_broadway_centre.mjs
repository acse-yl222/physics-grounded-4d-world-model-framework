// Hammersmith Broadway: the Broadway Centre (EPR Architects, opened 1994) - offices over the
// Broadway Shopping Centre wrapped around the two-level Hammersmith bus station, integrated
// with the Hammersmith (District and Piccadilly lines) station whose buildings were
// rebuilt into the complex (Minale Tattersfield reusing the Harry W. Ford tiling in the
// north ticket hall), and the open-air platform canopies running south-east.
export default {
  id: 'hammersmith_broadway_centre',
  name: 'Hammersmith Broadway Centre, Bus Station and Station',
  claims: [
    'fe5d7822-92c4-4482-b088-5877cb34f1f8',
    'd1c84a0d-3c20-41c7-91e0-449b73b3cab9',
    'f1dab892-5d7b-4035-89c1-13c70762d749',
    '21ddae09-7834-4733-9b4c-00febd8d9aea',
    '868ea82d-0343-4f07-8331-4de0df16981a',
  ],
  references: [
    {
      title: 'Hammersmith Broadway - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_Broadway',
      used_for:
        'shopping centre opened 1994 by EPR Architects; offices, retail and transport complex',
    },
    {
      title: 'Hammersmith bus station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_bus_station',
      used_for:
        'two-level bus station: upper station above the shopping centre, lower at ground level',
    },
    {
      title: 'Hammersmith tube station (District and Piccadilly lines) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_tube_station_(District_and_Piccadilly_lines)',
      used_for:
        'station buildings incorporated into the shopping centre and interchange in the early 1990s; reused Ford tiling',
    },
    {
      title: 'EPR Architects - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/EPR_Architects',
      used_for: 'architect practice',
    },
  ],
  notes:
    'The upper bus deck is set at 13 m to match the level-2 access ramps in the road layer; the shopping-centre ' +
    'volume under it, the office storey heights (5 m retail + 5 x 3.8 m), the cladding colours (grey stone piers, ' +
    'blue-green ribbon glazing), the bus-shelter canopies, the station frontage glazing and roundels and the ' +
    'platform-canopy column spacing are assumptions; no detailed facade description was found.',
  build({ THREE, kit, buildings, placeAssets }) {
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
    const rec = (id) => buildings.find((b) => b.id === id);
    const centre = ccw(rec('fe5d7822-92c4-4482-b088-5877cb34f1f8').polys[0][0]);
    const bus = ccw(rec('d1c84a0d-3c20-41c7-91e0-449b73b3cab9').polys[0][0]);
    const stn = ccw(rec('f1dab892-5d7b-4035-89c1-13c70762d749').polys[0][0]);
    const can1 = ccw(rec('21ddae09-7834-4733-9b4c-00febd8d9aea').polys[0][0]);
    const can2 = ccw(rec('868ea82d-0343-4f07-8331-4de0df16981a').polys[0][0]);

    const clad = kit.mat('#c9c6bd', { roughness: 0.75 });
    const cladDark = kit.mat('#8d8b86', { roughness: 0.7 });
    const glass = kit.mat('#4f7a82', { roughness: 0.1, metalness: 0.35 });
    const shop = kit.mat('#32424a', { roughness: 0.1, metalness: 0.3 });
    const frame = kit.mat('#5b6064', { roughness: 0.4, metalness: 0.5 });
    const roofM = kit.mat('#8a8a86');
    const deck = kit.mat('#5a5c5f', { roughness: 0.95 });
    const canopy = kit.mat('#e3e5e6', { roughness: 0.4, metalness: 0.4 });
    const luRed = kit.mat('#dc241f', { roughness: 0.5 });
    const luBlue = kit.mat('#0019a8', { roughness: 0.5 });
    const white = kit.mat('white');
    const steel = kit.mat('steel');
    const rnd = kit.rng(0.5521);

    // ---- Broadway Centre offices ---------------------------------------------------------
    const G = 5.0,
      ST = 3.8,
      N = 5,
      H = G + N * ST;
    {
      const r = centre;
      ribbon(kit.offsetRing(r, -0.5), 0, G - 0.6, shop, frame, 3.0);
      kit.walls(B, cladDark, [[r]], G - 0.6, G, { bay: 1e6 });
      kit.cap(B, cladDark, [[r]], G - 0.6, { down: true });
      for (let s = 0; s < N; s++) {
        const z = G + s * ST;
        kit.walls(B, clad, [[r]], z, z + 1.1, { bay: 1e6 });
        ribbon(kit.offsetRing(r, -0.2), z + 1.1, z + ST, glass, frame, 1.5);
      }
      // stone-clad piers every ~7.5 m on the long faces
      for (const e of edgesOf(r)) {
        if (e.len < 8) continue;
        const n = Math.round(e.len / 7.5);
        for (let k = 0; k <= n; k++) {
          const s = 0.35 + ((e.len - 0.7) * k) / n;
          ebox(clad, e, s - 0.4, s + 0.4, -0.5, 0.25, 0, H);
        }
      }
      kit.cap(B, roofM, [[r]], H);
      parapet(clad, r, H, 1.0, 0.3);
      kit.cornice(B, cladDark, r, H + 0.7, { height: 0.3, projection: 0.35 });
      plantBoxes(r, H, rnd, 5, kit.mat('#a0a29f'), 0.3);
      // "BROADWAY" lettering over the main entrance on the longest west-facing edge
      const ent = edgesOf(r)
        .filter((e) => e.len > 20)
        .sort((a, b) => b.len - a.len)[0];
      ebox(
        signMat('hbc:sign', 'BROADWAY', '#7f1d2d', '#ffffff', 'bold 46px sans-serif'),
        ent,
        ent.len / 2 - 6,
        ent.len / 2 + 6,
        0.3,
        0.4,
        G - 0.6,
        G + 0.6,
      );
    }
    // ---- shopping centre under the upper bus deck --------------------------------------
    const ZD = 13.0;
    {
      const r = bus;
      ribbon(kit.offsetRing(r, -0.4), 0, G - 0.6, shop, frame, 3.0);
      kit.walls(B, cladDark, [[r]], G - 0.6, ZD, { bay: 1e6 });
      kit.cap(B, deck, [[r]], ZD);
      parapet(clad, r, ZD, 1.1, 0.3);
      // bus stands: island canopies along the deck on slim columns
      const f = kit.ringFrame(r);
      for (const v of [-f.width * 0.18, f.width * 0.18]) {
        const a = frameAt(f, -f.length * 0.42, v),
          b = frameAt(f, f.length * 0.42, v);
        const e = edgesOf([a, b])[0];
        ebox(canopy, e, 0, e.len, -2.2, 2.2, ZD + 4.8, ZD + 5.1);
        ebox(
          kit.mat('#b9c7cc', { roughness: 0.1 }),
          e,
          0.5,
          e.len - 0.5,
          -0.05,
          0.05,
          ZD,
          ZD + 2.4,
        );
        for (let s = 1; s < e.len; s += 6)
          ebox(steel, e, s - 0.1, s + 0.1, -0.1, 0.1, ZD, ZD + 4.8);
        ebox(kit.mat('#dcdad2'), e, 0, e.len, -1.2, 1.2, ZD, ZD + 0.18); // kerbed island
      }
      // buses waiting at the upper-deck stands
      const buses = [];
      for (const [u, v] of [
        [-f.length * 0.22, -f.width * 0.18 - 4.3],
        [f.length * 0.18, -f.width * 0.18 - 4.3],
        [-f.length * 0.05, f.width * 0.18 + 4.3],
      ])
        buses.push([...frameAt(f, u, v), f.angle - Math.PI / 2]);
      const bg = placeAssets('double_decker_bus', buses);
      bg.position.z = ZD;
      g.add(bg);
    }
    // ---- District/Piccadilly station frontage ----------------------------------------------
    {
      const r = stn;
      const HS = 10.7;
      ribbon(
        kit.offsetRing(r, -0.3),
        0,
        6.0,
        kit.mat('#3c4d58', { roughness: 0.1, metalness: 0.3 }),
        frame,
        1.8,
      );
      kit.walls(B, kit.mat('#a8442f', { roughness: 0.6 }), [[r]], 6.0, HS, { bay: 1e6 }); // terracotta-red band
      kit.cap(B, roofM, [[r]], HS);
      parapet(kit.mat('#a8442f'), r, HS, 0.6, 0.25);
      // canopy and roundels over the entrance on its longest edge
      const e = edgesOf(r).sort((a, b) => b.len - a.len)[0];
      ebox(canopy, e, 1, e.len - 1, -0.3, 2.5, 4.3, 4.6);
      for (const s of [3, e.len - 3]) {
        const c = at(e, s, 0.4);
        const ringG = new THREE.TorusGeometry(1.0, 0.25, 6, 24).rotateX(Math.PI / 2);
        B.addGeometry(
          luRed,
          ringG,
          new THREE.Matrix4().makeRotationZ(e.ang).setPosition(c[0], c[1], 7.8),
        );
        ringG.dispose();
        kit.box(B, luBlue, c[0], c[1], 7.6, 2.6, 0.12, 0.45, e.ang);
      }
      ebox(
        signMat('hbc:stn', 'HAMMERSMITH STATION', '#0019a8', '#ffffff', 'bold 36px sans-serif'),
        e,
        e.len / 2 - 6,
        e.len / 2 + 6,
        0.27,
        0.33,
        6.3,
        7.3,
      );
    }
    // ---- platform canopies on columns -------------------------------------------------------
    for (const [r, z] of [
      [can1, 3.4],
      [can2, 2.9],
    ]) {
      const f = kit.ringFrame(r);
      kit.cap(B, canopy, [[r]], z);
      kit.cap(B, canopy, [[r]], z - 0.05, { down: true });
      kit.walls(B, kit.mat('#1f6e43'), [[r]], z - 0.35, z, { bay: 1e6 }); // valance
      for (let u = -f.length / 2 + 3; u <= f.length / 2 - 3; u += 7.5) {
        const p = frameAt(f, u, 0);
        cyl(kit.mat('#1f6e43'), p[0], p[1], 0, 0.14, 0.14, z - 0.05, 8);
      }
      // platform slab
      kit.cap(B, kit.mat('#bcb7ad'), [[kit.offsetRing(r, 0.5)]], 0.9);
      kit.walls(B, kit.mat('#bcb7ad'), [[kit.offsetRing(r, 0.5)]], 0, 0.9, { bay: 1e6 });
      // yellow line along the platform edges
      for (const e of edgesOf(kit.offsetRing(r, 0.35)).filter((e) => e.len > 50))
        ebox(kit.mat('#e8c547'), e, 0, e.len, -0.1, 0.1, 0.9, 0.92);
    }
    void white;
    g.add(B.toGroup('hammersmith_broadway_centre'));
    return g;
  },
};
