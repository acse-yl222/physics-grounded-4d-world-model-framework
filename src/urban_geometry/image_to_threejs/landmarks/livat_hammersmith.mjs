// Livat Hammersmith (the former Kings Mall, opened 1979; rebuilt by Ingka Centres and
// reopened 2022 with IKEA, Primark and Sainsbury's) with the Ashcroft Square deck housing
// built over it, and the Lyric Hammersmith theatre at its eastern end on Lyric Square (the
// Matcham auditorium rebuilt inside the complex in 1979; new entrance and the Reuben
// Foundation wing by Rick Mather Architects, 2015, with David Batchelor's neon "19-20-21"
// on the facade facing Lyric Square).
export default {
  id: 'livat_hammersmith',
  name: 'Livat Hammersmith (Kings Mall), Ashcroft Square and Lyric Hammersmith',
  claims: ['dc98f78d-5ee6-421c-aee6-f4815625cc8f', '04e0c92a-8b67-470d-9b57-ebff244e9510'],
  references: [
    {
      title: 'Livat Hammersmith - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Livat_Hammersmith',
      used_for:
        'formerly Kings Mall, opened 1979, entrances off King Street, Ashcroft Square and Sovereign Court housing in the complex, Ingka purchase 2020, reopening 2022, anchors',
    },
    {
      title: 'Ingka Centres launches in London with world-first urban meeting place',
      url: 'https://www.ingkacentres.com/cs/newsroom/ingka-centres-launches-in-london-with-world-first-urban-meeting-place',
      used_for: 'Livat Hammersmith concept and opening',
    },
    {
      title: 'Lyric Theatre (Hammersmith) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Lyric_Theatre_(Hammersmith)',
      used_for: 'theatre on Lyric Square within the King Street complex',
    },
    {
      title: 'Rick Mather Architects refurbishes and expands Lyric Hammersmith - Dezeen',
      url: 'https://www.dezeen.com/2015/12/27/rick-mather-architects-refurbishment-expansion-lyric-hammersmith-theatre-london/',
      used_for: '2015 Reuben Foundation wing to the west, triple-height foyer',
    },
    {
      title: '19-20-21 (2015) - Contemporary Art Society',
      url: 'https://www.contemporaryartsociety.org/node/36190',
      used_for: "David Batchelor's neon piece on the facade facing Lyric Square",
    },
  ],
  notes:
    'The Lyric is the 16.5 m sub-part of the Livat footprint (a part cannot be claimed on its own, so it is modelled ' +
    'here). Mall podium height (10.5 m), the Ashcroft Square housing as six storeys of brown-brick deck-access ' +
    'blocks over the podium with access galleries on the courtyard side, the courtyard deck garden, the King ' +
    'Street entrance canopy and LIVAT lettering, the theatre fly tower height (22 m) and the neon colours are ' +
    'assumptions.',
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
    const liv = buildings.find((b) => b.id.startsWith('dc98f78d'));
    const ash = buildings.find((b) => b.id.startsWith('04e0c92a'));
    const ring = ccw(liv.polys[0][0]);
    const lyric = ccw(liv.parts[0].polys[0][0]);
    const ashO = ccw(ash.polys[0][0]);
    const ashH = ash.polys[0][1] ? ccw(ash.polys[0][1]) : null;
    const brownBrick = kit.mat('#7a5644', { roughness: 0.92 });
    const conc = kit.mat('#b9b4aa', { roughness: 0.9 });
    const clad = kit.mat('#d9d4c8', { roughness: 0.7 });
    const timber = kit.mat('#b98b5b', { roughness: 0.7 });
    const shop = kit.mat('#34454e', { roughness: 0.1, metalness: 0.3 });
    const glass = kit.mat('#3f5562', { roughness: 0.12, metalness: 0.3 });
    const frame = kit.mat('#3d4246', { roughness: 0.4, metalness: 0.5 });
    const roofM = kit.mat('#8a8a86');
    const green = kit.mat('grass');
    const white = kit.mat('white');
    const rnd = kit.rng(0.6617);
    const ZP = 10.5;

    // ---- mall podium ------------------------------------------------------------------------
    ribbon(kit.offsetRing(ring, -0.5), 0, 5.0, shop, frame, 3.4);
    kit.walls(B, clad, [[ring]], 5.0, ZP, { bay: 1e6 });
    kit.cap(B, clad, [[ring]], 5.0, { down: true });
    for (const e of edgesOf(ring)) {
      if (e.len < 8) continue;
      for (let z = 6.2; z < ZP - 0.6; z += 1.5)
        ebox(kit.mat('#c4bfb3'), e, 0.3, e.len - 0.3, 0, 0.06, z, z + 0.25);
    }
    kit.cap(B, roofM, [[ring]], ZP);
    parapet(clad, ring, ZP, 1.1, 0.3);
    // King Street entrance (south face): timber-slatted canopy, glazed double-height entrance, LIVAT letters
    {
      const fe = edgesOf(ring)
        .filter((e) => e.ny < -0.6)
        .sort((a, b) => b.len - a.len)[0];
      const m = fe.len / 2;
      ebox(glass, fe, m - 9, m + 9, 0, 0.6, 0, ZP - 0.4);
      for (let k = 0; k <= 9; k++)
        ebox(frame, fe, m - 9 + 2 * k - 0.06, m - 9 + 2 * k + 0.06, 0.6, 0.75, 0, ZP - 0.4);
      ebox(timber, fe, m - 12, m + 12, 0.6, 5.5, 4.6, 5.0);
      for (let s = m - 12; s <= m + 12; s += 0.5)
        ebox(timber, fe, s - 0.06, s + 0.06, 0.6, 5.5, 4.3, 4.6);
      ebox(
        signMat('livat:sign', 'LIVAT', '#ffffff', '#1e1e1e', 'bold 54px sans-serif', 256, 64),
        fe,
        m - 4,
        m + 4,
        0.76,
        0.82,
        ZP - 3.2,
        ZP - 0.8,
      );
      // IKEA / anchor signage further along the frontage
      ebox(
        signMat('livat:ikea', 'IKEA', '#0058a3', '#ffda1a', 'bold 54px sans-serif', 256, 64),
        fe,
        m + 14,
        m + 20,
        0.1,
        0.16,
        6.2,
        8.4,
      );
    }
    // ---- Ashcroft Square deck housing over the podium -------------------------------------
    {
      const D = 10; // block depth (fallback)
      const outer = kit.offsetRing(ashO, -0.8);
      const court = ashH || kit.offsetRing(ashO, -D);
      const innerB = court.slice().reverse(); // CW: faces into the courtyard
      const ZT = 29.6,
        ST = 3.1,
        N = 6;
      kit.walls(B, brownBrick, [[outer]], ZP, ZP + N * ST, { bay: 1e6 });
      kit.walls(B, brownBrick, [[innerB]], ZP, ZP + N * ST, { bay: 1e6 });
      kit.cap(B, roofM, [[outer, innerB]], ZP + N * ST);
      parapet(brownBrick, outer, ZP + N * ST, 0.9, 0.3);
      // outer windows
      winRows(
        outer,
        ZP + 0.9,
        N,
        ST,
        {
          width: 1.4,
          height: 1.6,
          bay: 3.4,
          margin: 1.0,
          glass,
          frame: white,
          sill: conc,
          head: 'none',
          bars: 1,
          depth: 0.1,
        },
        6,
      );
      // courtyard-side access galleries (concrete deck slabs + balustrade walls) and windows
      for (const e of edgesOf(innerB)) {
        if (e.len < 6) continue;
        for (let s = 0; s < N; s++) {
          const z = ZP + s * ST;
          ebox(conc, e, 0, e.len, 0, 1.6, z + ST - 0.2, z + ST);
          ebox(conc, e, 0, e.len, 1.45, 1.6, z + ST, z + ST + 1.0);
          kit.windowRow(B, e.a, e.b, z + 1.0, {
            width: 1.0,
            height: 1.3,
            bay: 3.4,
            margin: 1.0,
            glass,
            frame: white,
            sill: conc,
            head: 'none',
            bars: 0,
            depth: 0.08,
          });
        }
      }
      // courtyard podium deck garden at the podium roof
      kit.cap(B, green, [[court]], ZP + 0.03);
      const f = kit.ringFrame(court);
      for (let k = 0; k < 10; k++) {
        const p = frameAt(f, (rnd() - 0.5) * f.length * 0.6, (rnd() - 0.5) * f.width * 0.6);
        cyl(kit.mat('bark'), p[0], p[1], ZP, 0.12, 0.12, 2.2, 6);
        const t = new THREE.IcosahedronGeometry(1.5 + rnd(), 0);
        B.addGeometry(
          kit.mat('foliage'),
          t,
          new THREE.Matrix4().makeTranslation(p[0], p[1], ZP + 3.4),
        );
        t.dispose();
      }
      void ZT;
      // lift / stair towers at the corners of the housing ring
      for (const e of edgesOf(outer).filter((e) => e.len > 30)) {
        ebox(brownBrick, e, e.len / 2 - 2.5, e.len / 2 + 2.5, -5, 0.4, ZP, ZP + N * ST + 2.5);
      }
    }
    // ---- Lyric Hammersmith at the east end ---------------------------------------------------
    {
      const r = lyric;
      const HL = 16.5;
      const red = kit.mat('#8c3b2f', { roughness: 0.85 });
      kit.walls(B, red, [[r]], 0, HL, { bay: 1e6 });
      kit.cap(B, roofM, [[r]], HL);
      parapet(red, r, HL, 0.8, 0.3);
      // fly tower over the stage (western half of the part)
      const f = kit.ringFrame(r);
      const ft = [
        frameAt(f, -f.length * 0.35, -9),
        frameAt(f, -f.length * 0.02, -9),
        frameAt(f, -f.length * 0.02, 9),
        frameAt(f, -f.length * 0.35, 9),
      ];
      const ftr = ccw(ft);
      kit.walls(B, red, [[ftr]], HL, 22, { bay: 1e6 });
      kit.cap(B, roofM, [[ftr]], 22);
      // east entrance front onto Lyric Square: triple-height glazed foyer, canopy, sign, neon
      const fe = edgesOf(r)
        .filter((e) => e.nx > 0.6 && e.len > 8)
        .sort((a, b) => b.len - a.len)[0];
      if (fe) {
        ebox(glass, fe, 0.8, fe.len - 0.8, 0, 0.5, 0, 12);
        for (let s = 0.8; s <= fe.len - 0.8; s += 1.8)
          ebox(frame, fe, s - 0.06, s + 0.06, 0.5, 0.65, 0, 12);
        for (const z of [4.2, 8.2]) ebox(frame, fe, 0.8, fe.len - 0.8, 0.5, 0.65, z, z + 0.12);
        ebox(kit.mat('#1e1e1e'), fe, 0.5, fe.len - 0.5, 0, 2.5, 3.6, 3.9);
        ebox(
          signMat('lyric:sign', 'LYRIC', '#1e1e1e', '#ffffff', 'bold 54px sans-serif', 256, 64),
          fe,
          fe.len / 2 - 3,
          fe.len / 2 + 3,
          2.5,
          2.55,
          3.4,
          4.1,
        );
        // neon bands (19-20-21) on the upper facade
        const neon = ['#ff3b6b', '#ffd400', '#28c7fa', '#7cff5b', '#ff8a00', '#b46cff'];
        neon.forEach((c, k) => {
          const s = 1.5 + k * ((fe.len - 3) / neon.length);
          ebox(
            kit.mat(c, { emissive: c, emissiveIntensity: 0.6 }),
            fe,
            s,
            s + (fe.len - 3) / neon.length - 0.4,
            0.66,
            0.72,
            13.0,
            13.5,
          );
        });
      }
      // stalls/auditorium windows on the King Street side of the wing
      const se = edgesOf(r)
        .filter((e) => e.ny < -0.6)
        .sort((a, b) => b.len - a.len)[0];
      if (se)
        kit.windowRow(B, se.a, se.b, 5.5, {
          width: 2.0,
          height: 6.0,
          bay: 4.5,
          margin: 2,
          glass,
          frame,
          sill: frame,
          head: 'none',
          bars: 1,
        });
    }
    g.add(B.toGroup('livat_hammersmith'));
    return g;
  },
};
