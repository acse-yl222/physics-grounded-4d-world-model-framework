// Latymer Upper School, 237 King Street, Hammersmith. The Upper School buildings between
// King Street and the river opened in January 1895 (foundation stone 1893); the main block
// was extended southward in 1930. Long red-brick main range running south from King Street;
// beside it the Performing Arts Centre (van Heyningen and Haward, 2008) in brick chosen to
// suit the older buildings.
export default {
  id: 'latymer_upper_school',
  name: 'Latymer Upper School',
  claims: ['40ed4c8f-bb18-470a-8185-4c46c6a21f37', '0502295e-f2bd-491a-91b0-648437baab4f'],
  references: [
    {
      title: 'Latymer Upper School - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Latymer_Upper_School',
      used_for: 'King Street site since 1895',
    },
    {
      title: 'History - Latymer Foundation',
      url: 'https://latymerfoundation.org/the-foundation/history',
      used_for: 'foundation stone 1893, opening 9 January 1895',
    },
    {
      title: 'Schools: Latymer and Godolphin Schools - British History Online',
      url: 'https://prod.british-history.ac.uk/node/15284',
      used_for:
        'buildings between King Street and the river, opened 1895; main block extended southward 1930',
    },
    {
      title: 'Latymer Upper School Performing Arts Centre - e-architect',
      url: 'https://www.e-architect.com/london/latymer-upper-school-building',
      used_for:
        'van Heyningen and Haward Performing Arts Centre, brick envelope in keeping with the school',
    },
  ],
  notes:
    'No description of the 1895 elevations was found; the main range is modelled as a three-storey red-brick ' +
    'Victorian school (4.2 m storeys) under a slate roof, with a gabled King Street front, stone-dressed ' +
    'mullioned windows, a central entrance and a small bell lantern - all assumptions, as are the identification ' +
    'of the long unnamed footprint as the 1895/1930 main block and the PAC’s glazed foyer and fly tower.',
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
    const main = ccw(buildings.find((b) => b.id.startsWith('40ed4c8f')).polys[0][0]);
    const pac = ccw(buildings.find((b) => b.id.startsWith('0502295e')).polys[0][0]);
    const brick = kit.mat('#93493a', { roughness: 0.9 });
    const stone = kit.mat('bath_stone');
    const slate = kit.mat('slate');
    const glass = kit.mat('#3a4650', { roughness: 0.2, metalness: 0.2 });
    const frame = kit.mat('#f1efe8');
    const door = kit.mat('#2f3b4a');
    const ST = 4.2,
      N = 3,
      EAV = ST * N + 0.6;
    // ---- main range: decompose the long N-S footprint into rectangles along its axis -----
    const ang = Math.PI / 2; // long axis north-south
    const O = kit.orientedExtent(main, ang);
    const P = (u, v) => {
      const p = O.at(u, v, 0);
      return [p[0], p[1]];
    };
    const rect = (u0, v0, u1, v1) => ccw([P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)]);
    // u runs north (+y); v runs west (-x)
    kit.walls(B, brick, [[main]], 0, EAV, { bay: 1e6 });
    kit.cornice(B, stone, main, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(B, stone, main, ST + 0.3, { height: 0.25, projection: 0.1 });
    kit.cornice(B, stone, main, EAV - 0.4, { height: 0.4, projection: 0.3 });
    kit.cap(B, kit.mat('#6f6d69'), [[main]], EAV);
    // pitched roof along the range (oriented rectangle of its central spine)
    const wid = O.v1 - O.v0;
    // main 20 m wide spine (v = -x): x -2550.6 .. -2530.4 from the south wing to King Street
    const spine = rect(O.u0 + 12.5, 2530.6, O.u1 - 4.4, 2550.4);
    kit.pitchedRoof(B, slate, brick, spine, ang, EAV, 6.0, 'hipped', { overhang: 0.3 });
    const south = rect(O.u0 + 0.2, 2525.6, O.u0 + 12.0, 2552.2);
    kit.pitchedRoof(B, slate, brick, south, 0, EAV, 5.0, 'hipped', { overhang: 0.3 });
    winRows(
      main,
      1.3,
      N,
      ST,
      (s) => ({
        width: 1.3,
        height: s === 0 ? 2.4 : 2.6,
        bay: 3.6,
        margin: 1.2,
        glass,
        frame: stone,
        sill: stone,
        head: s === 2 ? 'segment' : 'lintel',
        bars: 2,
        surround: 0.15,
        surroundMat: stone,
        depth: 0.18,
      }),
      8,
    );
    // King Street (north) front: projecting central gable with entrance and bell lantern
    {
      const fe = edgesOf(main)
        .filter((e) => e.ny > 0.7)
        .sort((a, b) => b.len - a.len)[0];
      const m = fe.len / 2;
      ebox(brick, fe, m - 5, m + 5, 0, 1.2, 0, EAV);
      // gable
      const sh = new THREE.Shape();
      sh.moveTo(-5, EAV);
      sh.lineTo(5, EAV);
      sh.lineTo(0, EAV + 6.5);
      sh.lineTo(-5, EAV);
      const geo = new THREE.ExtrudeGeometry(sh, { depth: 1.2, bevelEnabled: false });
      const c = at(fe, m, 0);
      const mt = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(fe.dx, fe.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(fe.nx, fe.ny, 0),
      );
      mt.setPosition(c[0], c[1], 0);
      B.addGeometry(brick, geo, mt);
      geo.dispose();
      ebox(stone, fe, m - 5.2, m + 5.2, 0, 1.45, EAV - 0.4, EAV);
      kit.windowRow(B, at(fe, m - 4, 1.2), at(fe, m + 4, 1.2), ST + 1.0, {
        width: 1.0,
        height: 3.6,
        count: 3,
        margin: 0.8,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 2,
        surround: 0.15,
        surroundMat: stone,
      });
      kit.windowRow(B, at(fe, m - 2, 1.2), at(fe, m + 2, 1.2), EAV + 1.0, {
        width: 1.4,
        height: 2.2,
        count: 1,
        margin: 0.5,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 2,
      });
      ebox(stone, fe, m - 2.0, m + 2.0, 1.2, 1.7, 0, 3.6);
      ebox(door, fe, m - 1.1, m + 1.1, 1.7, 1.75, 0, 3.0);
      ebox(stone, fe, m - 2.4, m + 2.4, 1.2, 1.9, 3.6, 4.0);
      ebox(
        signMat('latymer:name', 'LATYMER UPPER SCHOOL', '#d9c79e', '#4a3b2a', 'bold 30px serif'),
        fe,
        m - 2.3,
        m + 2.3,
        1.91,
        1.95,
        3.62,
        3.98,
      );
      // bell lantern on the ridge behind the gable
      const lc = at(fe, m, -7);
      kit.box(B, kit.mat('#ecebe6'), lc[0], lc[1], EAV + 6.0, 2.0, 2.0, 2.4, fe.ang);
      cyl(kit.mat('lead'), lc[0], lc[1], EAV + 8.4, 1.5, 0.05, 2.6, 8);
    }
    // chimneys along the ridge
    for (let k = 1; k <= 4; k++) {
      const p = P(O.u0 + ((O.u1 - O.u0) * k) / 5, (O.v0 + O.v1) / 2 + wid * 0.2);
      kit.box(B, brick, p[0], p[1], EAV + 3, 1.0, 2.0, 5.0, ang);
    }
    // ---- Performing Arts Centre ---------------------------------------------------------
    {
      const r = pac;
      const H = 11.5;
      const pb = kit.mat('#7d4a3a', { roughness: 0.9 });
      kit.walls(B, pb, [[r]], 0, H, { bay: 1e6 });
      kit.cap(B, kit.mat('#7f8183'), [[r]], H);
      parapet(kit.mat('#5d6266'), r, H, 0.5, 0.25);
      const f = kit.ringFrame(r);
      const ft = ccw([
        frameAt(f, -f.length * 0.1, -f.width / 2 + 0.5),
        frameAt(f, f.length * 0.25, -f.width / 2 + 0.5),
        frameAt(f, f.length * 0.25, f.width / 2 - 0.5),
        frameAt(f, -f.length * 0.1, f.width / 2 - 0.5),
      ]);
      kit.walls(B, pb, [[ft]], H, H + 4.5, { bay: 1e6 });
      kit.cap(B, kit.mat('#7f8183'), [[ft]], H + 4.5);
      // glazed foyer at the north end and tall slot windows
      const n = edgesOf(r).filter((e) => e.ny > 0.7)[0];
      if (n)
        ebox(
          kit.mat('#4a6470', { roughness: 0.1, metalness: 0.3 }),
          n,
          0.5,
          n.len - 0.5,
          0,
          0.1,
          0,
          7.5,
        );
      for (const e of edgesOf(r).filter((e) => e.len > 30))
        kit.windowRow(B, e.a, e.b, 1.0, {
          width: 0.6,
          height: 8.5,
          bay: 4.5,
          margin: 2.0,
          glass,
          frame: kit.mat('#5d6266'),
          sill: kit.mat('#5d6266'),
          head: 'none',
          bars: 0,
        });
    }
    g.add(B.toGroup('latymer_upper_school'));
    return g;
  },
};
