// Hammersmith Town Hall, King Street / Great West Road (E. Berry Webber, 1938-39, Grade II).
// Neo-Georgian "Swedish Georgian" civic block: three storeys and attic around an inner
// courtyard; Portland stone ground floor with channelled rustication and a moulded plinth;
// red-purple brick upper floors in monk bond, slightly set back; steel Crittall windows; a
// roll-moulded banded brick parapet; a symmetrical nine-bay south elevation with a taller
// projecting centrepiece; yellow stock brick to the courtyard. The 1970s northern
// extension (excluded from the listing) has been demolished for the new civic campus.
export default {
  id: 'hammersmith_town_hall',
  name: 'Hammersmith Town Hall',
  claims: ['6d7515fa-b778-4ba2-8c90-8f7fbccba05f', '69b78d4e-efc5-45fb-a957-9cdb9971f0e0'],
  references: [
    {
      title: 'Hammersmith Town Hall - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_Town_Hall',
      used_for:
        'architect E. Berry Webber, 1938-39, Grade II, Swedish Georgian style, later extension',
    },
    {
      title: 'Hammersmith Town Hall - British Listed Buildings (1079785)',
      url: 'https://britishlistedbuildings.co.uk/101079785',
      used_for:
        'red-purple brick in monk bond, Portland stone ground floor with rustication and plinth, three storeys and attic, set-back upper floors, Crittall windows, banded brick parapet, nine-bay south elevation with projecting centrepiece, yellow stock courtyard',
    },
    {
      title: 'Hammersmith Town Hall, London - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1930/hammersmithtownhall.html',
      used_for: 'red brick with Portland stone dressings, Neo-Georgian',
    },
    {
      title: 'Hammersmith Town Hall - LBHF',
      url: 'https://lbhf.gov.uk/councillors-and-democracy/about-hammersmith-fulham-council/hammersmith-town-hall',
      used_for: 'history: north steps lost to the 1971-75 extension',
    },
  ],
  notes:
    'Two Overture footprints (h=7 m and 8 m, too low) are combined into one oriented courtyard block. Storey ' +
    'heights (5.0 m stone ground floor, 4.6 m and 4.2 m upper floors, 3.2 m attic), the 14 m range depth, the ' +
    'width and height of the south centrepiece, window sizes and the entrance doorcase are estimates; the ' +
    'attic is modelled as a set-back storey behind the parapet. Murals, flagpole and the courtyard fittings ' +
    'are not modelled; the new civic-campus buildings to the north are not part of this model.',
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
    const rings = buildings.map((b) => ccw(b.polys[0][0]));
    // Orientation of the long south edge of the main footprint.
    const main = rings[0];
    const se =
      edgesOf(main)
        .sort((a, b) => b.len - a.len)
        .find((e) => Math.abs(e.dx) > 0.7) || edgesOf(main).find((e) => Math.abs(e.dx) > 0.7);
    let ang = Math.atan2(se.dy, se.dx);
    if (Math.cos(ang) < 0) ang += Math.PI;
    const ex = { u0: Infinity, u1: -Infinity, v0: Infinity, v1: -Infinity };
    for (const r of rings) {
      const o = kit.orientedExtent(r, ang);
      ex.u0 = Math.min(ex.u0, o.u0);
      ex.u1 = Math.max(ex.u1, o.u1);
      ex.v0 = Math.min(ex.v0, o.v0);
      ex.v1 = Math.max(ex.v1, o.v1);
    }
    const O = kit.orientedExtent(rings[0], ang);
    const P = (u, v) => {
      const p = O.at(u, v, 0);
      return [p[0], p[1]];
    };
    const rect = (u0, v0, u1, v1) => [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)];

    const stone = kit.mat('portland_stone');
    const brick = kit.mat('#6c3836', { roughness: 0.92 });
    const stock = kit.mat('london_stock');
    const roofM = kit.mat('#6f6d69');
    const glass = kit.mat('#3c4d58', { roughness: 0.15, metalness: 0.3 });
    const frame = kit.mat('#ece9df');
    const bronze = kit.mat('bronze');

    const D = 14; // range depth
    const Z1 = 5.0,
      Z2 = 9.6,
      Z3 = 13.8,
      ZA = 17.0;
    const outer = rect(ex.u0, ex.v0, ex.u1, ex.v1);
    const court = rect(ex.u0 + D, ex.v0 + D, ex.u1 - D, ex.v1 - D).reverse();
    const upper = kit.offsetRing(outer, -0.35);
    const courtU = kit.offsetRing(rect(ex.u0 + D, ex.v0 + D, ex.u1 - D, ex.v1 - D), 0.35).reverse();

    // ground floor: Portland stone with channelled rustication and moulded plinth
    kit.walls(B, stone, [[outer]], 0, Z1, { bay: 1e6 });
    kit.walls(B, stock, [[court]], 0, Z3, { bay: 1e6 });
    for (let z = 0.9; z < Z1 - 0.3; z += 0.6)
      for (const e of edgesOf(outer)) ebox(stone, e, 0, e.len, 0, 0.06, z, z + 0.48);
    kit.cornice(B, stone, outer, 0, { height: 0.9, projection: 0.18 });
    kit.cornice(B, stone, outer, Z1 - 0.35, { height: 0.35, projection: 0.25 });
    // brick upper floors set back
    kit.walls(B, brick, [[upper]], Z1, Z3, { bay: 1e6 });
    kit.cap(B, roofM, [[upper, courtU]], Z3 + 0.01);
    kit.cap(B, stone, [[outer, upper.slice().reverse()]], Z1);
    // banded brick parapet with stone coping
    parapet(brick, upper, Z3, 1.1, 0.35);
    kit.cornice(B, stone, upper, Z3 + 1.0, { height: 0.15, projection: 0.08 });
    kit.cornice(B, brick, upper, Z3 + 0.35, { height: 0.12, projection: 0.06 });
    // attic: set-back storey on the ranges
    const atticO = kit.offsetRing(outer, -3.2);
    const atticI = kit.offsetRing(rect(ex.u0 + D, ex.v0 + D, ex.u1 - D, ex.v1 - D), 2.5).reverse();
    kit.walls(B, brick, [[atticO]], Z3, ZA, { bay: 1e6 });
    kit.walls(B, brick, [[atticI]], Z3, ZA, { bay: 1e6 });
    kit.cap(B, roofM, [[atticO, atticI]], ZA);
    parapet(stone, atticO, ZA, 0.5, 0.25);

    // windows: tall stone-ground-floor windows, upper storeys in brick, attic small
    const win = (z, w, h, bay, bars, head = 'lintel', fr = frame) => ({
      width: w,
      height: h,
      bay,
      margin: 2.0,
      glass,
      frame: fr,
      sill: stone,
      head,
      bars,
    });
    winRows(outer, 1.3, 1, 0, win(1.3, 1.6, 2.8, 4.4, 2, 'segment'), 6);
    winRows(upper, Z1 + 0.8, 1, 0, win(0, 1.5, 3.0, 4.4, 2), 6);
    winRows(upper, Z2 + 0.7, 1, 0, win(0, 1.4, 2.5, 4.4, 2), 6);
    winRows(atticO, Z3 + 1.2, 1, 0, win(0, 1.2, 1.4, 4.4, 1, 'none'), 6);
    winRows(court, 1.2, 3, 4.2, win(0, 1.3, 2.3, 4.0, 1, 'none'), 6);

    // south centrepiece: nine bays, projecting and one storey taller
    {
      const cu = (ex.u0 + ex.u1) / 2,
        W = 34,
        pr = 2.2;
      const cp = rect(cu - W / 2, ex.v0 - pr, cu + W / 2, ex.v0 + D - 2);
      const ZC = ZA + 3.4;
      kit.walls(B, stone, [[cp]], 0, Z1, { bay: 1e6 });
      const cpu = kit.offsetRing(cp, -0.3);
      kit.walls(B, brick, [[cpu]], Z1, ZC, { bay: 1e6 });
      kit.cap(B, roofM, [[cpu]], ZC);
      parapet(brick, cpu, ZC, 1.1, 0.35);
      kit.cornice(B, stone, cpu, ZC + 1.0, { height: 0.18, projection: 0.1 });
      kit.cornice(B, stone, cp, Z1 - 0.35, { height: 0.35, projection: 0.25 });
      kit.cornice(B, stone, cp, 0, { height: 0.9, projection: 0.18 });
      const fe = edgesOf(cpu)[0]; // south edge (rect order: u0v0 -> u1v0)
      // nine tall first-floor windows (piano nobile) with balconettes, smaller above
      kit.windowRow(B, fe.a, fe.b, Z1 + 0.6, {
        width: 1.8,
        height: 4.0,
        count: 9,
        margin: 1.5,
        glass,
        frame,
        sill: stone,
        bars: 3,
        head: 'segment',
      });
      kit.windowRow(B, fe.a, fe.b, Z1 + 5.6, {
        width: 1.6,
        height: 2.6,
        count: 9,
        margin: 1.5,
        glass,
        frame,
        sill: stone,
        bars: 2,
      });
      kit.windowRow(B, fe.a, fe.b, ZA + 0.3, {
        width: 1.3,
        height: 1.6,
        count: 9,
        margin: 1.5,
        glass,
        frame,
        sill: stone,
        bars: 1,
        head: 'none',
      });
      for (let k = 0; k < 9; k++) {
        const s = 1.5 + ((fe.len - 3) * (k + 0.5)) / 9;
        ebox(bronze, fe, s - 1.1, s + 1.1, 0.05, 0.55, Z1 + 0.5, Z1 + 0.6);
        ebox(bronze, fe, s - 1.1, s + 1.1, 0.5, 0.55, Z1 + 0.6, Z1 + 1.5);
      }
      // ground floor: three arched entrance openings under a stone balcony
      const ge = edgesOf(cp)[0];
      kit.windowRow(B, ge.a, ge.b, 0.6, {
        width: 2.6,
        height: 3.2,
        count: 3,
        margin: 9,
        glass: kit.mat('#2a2622'),
        frame: bronze,
        sill: stone,
        bars: 1,
        head: 'arch',
      });
      ebox(stone, ge, 7, ge.len - 7, 0, 1.4, Z1 - 0.4, Z1 + 0.1);
      kit.balustrade(B, stone, [at(ge, 7, 1.25), at(ge, ge.len - 7, 1.25)], Z1 + 0.1, {
        height: 1.0,
        spacing: 0.35,
      });
      // steps
      for (let k = 0; k < 4; k++)
        ebox(stone, ge, 8, ge.len - 8, 0, 4.2 - k * 0.8, k * 0.15, (k + 1) * 0.15);
      // name band
      ebox(
        signMat('htownhall:name', 'HAMMERSMITH TOWN HALL', '#d8d1bf', '#3c3833', 'bold 34px serif'),
        ge,
        9,
        ge.len - 9,
        0.02,
        0.04,
        Z1 - 0.32,
        Z1 - 0.02,
      );
    }
    g.add(B.toGroup('hammersmith_town_hall'));
    return g;
  },
};
