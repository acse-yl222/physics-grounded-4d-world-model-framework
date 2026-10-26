// Bush Theatre, 7 Uxbridge Road, Shepherd's Bush - the former Passmore Edwards Free Library
// (Maurice Bingham Adams, 1895-96), converted for the theatre by Haworth Tompkins (2011,
// extended 2017). English Renaissance front of red brick with Portland stone cornices and
// mullions, a front gable carrying the life-size "Shepherd in the Bush" sculpture, the
// donor's name carved over the pedimented entrance porch; reading-room hall behind (now
// the auditorium) under a pitched roof.
export default {
  id: 'bush_theatre',
  name: 'Bush Theatre (former Passmore Edwards Library)',
  claims: ['cb1e6542-851e-4f7b-b406-5cf5b254c859'],
  references: [
    {
      title: "Passmore Edwards Public Library, Shepherd's Bush - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Passmore_Edwards_Public_Library,_Shepherd%27s_Bush',
      used_for: '1895-96, Maurice Bingham Adams, brick structure with timber frame',
    },
    {
      title: "Shepherd's Bush (Uxbridge Rd) Library 1896 - The Passmore Edwards Legacy",
      url: 'https://thepassmoreedwardslegacy.org.uk/hammersmith-uxbridge-rd-library-1896',
      used_for:
        "English Renaissance style, red brick with Portland stone cornices and mullions, gable sculpture 'Shepherd in the Bush', name carved over the entrance",
    },
    {
      title: 'The Bush Theatre - Heritage of London Trust',
      url: 'https://www.heritageoflondon.org/projects/the-bush-theatre',
      used_for: 'entrance porch with pediment mouldings and lettering, entrance steps',
    },
    {
      title: 'Bush Theatre - Haworth Tompkins',
      url: 'https://www.haworthtompkins.com/work/bush-theatre',
      used_for: 'conversion of the former library into auditorium, foyer and back of house',
    },
  ],
  notes:
    'Front range depth (13 m), eaves (10.5 m) and gable apex (17 m) heights, window counts, the bay rhythm and ' +
    'the shaped (Dutch-type) gable outline are estimates; the sculpture is a simple figure on a plinth in a ' +
    'niche. The rear hall/auditorium roof form and rooflights and the 2017 rear extension are simplified.',
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
    const ang = Math.atan2(-130.8 + 124.7, -1754.0 + 1778.4);
    const O = kit.orientedExtent(ring, ang);
    const P = (u, v) => {
      const p = O.at(u, v, 0);
      return [p[0], p[1]];
    };
    const rect = (u0, v0, u1, v1) => [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)];
    const brick = kit.mat('#9a4535', { roughness: 0.9 });
    const stone = kit.mat('portland_stone');
    const slate = kit.mat('slate');
    const glass = kit.mat('#39434b', { roughness: 0.2, metalness: 0.2 });
    const frame = kit.mat('#efece4');
    const door = kit.mat('#3b2a20');
    // front range across the full width at the north (v1) end
    const u0 = O.u0 + 0.3,
      u1 = O.u1 - 0.3,
      v1 = O.v1 - 0.2;
    const D = 13;
    const front = rect(u0 + 1.5, v1 - D, u1 - 0.5, v1);
    const EAV = 10.5,
      APEX = 17;
    kit.walls(B, brick, [[front]], 0, EAV, { bay: 1e6 });
    kit.cornice(B, stone, front, 0, { height: 0.7, projection: 0.12 });
    kit.cornice(B, stone, front, 4.6, { height: 0.3, projection: 0.12 }); // first-floor band
    kit.cornice(B, stone, front, EAV - 0.5, { height: 0.5, projection: 0.4, steps: 2 });
    kit.pitchedRoof(B, slate, brick, front, ang, EAV, 5.0, 'hipped', { overhang: 0.2 });
    const fe = edgesOf(front)[2]; // north face (u1,v1) -> (u0,v1)
    const W = fe.len;
    // stone-mullioned windows: two storeys of three-light windows either side of the centre
    for (const [s0, s1] of [
      [1.0, W / 2 - 4.2],
      [W / 2 + 4.2, W - 1.0],
    ]) {
      kit.windowRow(B, at(fe, s0), at(fe, s1), 1.4, {
        width: 0.75,
        height: 2.6,
        count: 3,
        margin: 0.4,
        glass,
        frame: stone,
        sill: stone,
        bars: 1,
        surround: 0.18,
        depth: 0.2,
      });
      kit.windowRow(B, at(fe, s0), at(fe, s1), 5.6, {
        width: 0.75,
        height: 2.9,
        count: 3,
        margin: 0.4,
        glass,
        frame: stone,
        sill: stone,
        bars: 1,
        surround: 0.18,
        depth: 0.2,
        head: 'pediment',
      });
    }
    // central shaped gable rising above the roof, with a sculpture niche and stone copings
    {
      const gw = 8.4;
      const m = W / 2;
      const steps = [
        [gw / 2, EAV],
        [gw / 2, EAV + 2.0],
        [gw / 2 - 1.2, EAV + 2.6],
        [gw / 2 - 1.2, EAV + 4.2],
        [gw / 2 - 2.6, EAV + 5.2],
        [0.9, APEX - 0.4],
        [0, APEX],
      ];
      const sh = new THREE.Shape();
      sh.moveTo(-gw / 2, EAV);
      for (const [x, z] of steps.slice().reverse()) sh.lineTo(-x, z);
      for (const [x, z] of steps) sh.lineTo(x, z);
      sh.lineTo(-gw / 2, EAV);
      const geo = new THREE.ExtrudeGeometry(sh, { depth: 0.9, bevelEnabled: false });
      // shape x -> along the face, shape y -> z (up), extrude -> into the building
      const c = at(fe, m, -0.65);
      const mtx = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(fe.dx, fe.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(fe.nx, fe.ny, 0),
      );
      mtx.setPosition(c[0], c[1], 0);
      B.addGeometry(brick, geo, mtx);
      geo.dispose();
      // copings along the gable steps
      for (const sgn of [-1, 1])
        for (let k = 0; k < steps.length - 1; k++) {
          const [xa, za] = steps[k],
            [xb, zb] = steps[k + 1];
          if (Math.abs(zb - za) < 0.01) continue;
          const s = m + (sgn * (xa + xb)) / 2;
          ebox(
            stone,
            fe,
            s - Math.max(0.25, Math.abs(xb - xa) / 2 + 0.15),
            s + Math.max(0.25, Math.abs(xb - xa) / 2 + 0.15),
            0.1,
            0.4,
            Math.max(za, zb) - 0.2,
            Math.max(za, zb) + 0.05,
          );
        }
      // gable window + niche with the Shepherd figure
      kit.windowRow(B, at(fe, m - 2), at(fe, m + 2), EAV + 0.6, {
        width: 1.0,
        height: 1.8,
        count: 2,
        margin: 0.5,
        glass,
        frame: stone,
        sill: stone,
        bars: 1,
        depth: 0.2,
      });
      ebox(kit.mat('#3c3530'), fe, m - 0.7, m + 0.7, 0.2, 0.3, EAV + 3.2, EAV + 5.2);
      ebox(stone, fe, m - 0.9, m + 0.9, 0.2, 0.6, EAV + 3.0, EAV + 3.2);
      const fig = at(fe, m, 0.45);
      cyl(stone, fig[0], fig[1], EAV + 3.2, 0.28, 0.2, 1.4, 8);
      const head = new THREE.SphereGeometry(0.17, 8, 6);
      B.addGeometry(stone, head, new THREE.Matrix4().makeTranslation(fig[0], fig[1], EAV + 4.75));
      head.dispose();
      // projecting central bay below the gable
      ebox(brick, fe, m - gw / 2, m + gw / 2, 0, 0.25, 0, EAV);
      kit.windowRow(B, at(fe, m - gw / 2, 0.25), at(fe, m + gw / 2, 0.25), 5.6, {
        width: 1.1,
        height: 3.0,
        count: 3,
        margin: 0.6,
        glass,
        frame: stone,
        sill: stone,
        bars: 2,
        surround: 0.2,
        depth: 0.2,
        head: 'arch',
      });
      // entrance porch: stone pediment over a round-arched doorway, steps
      ebox(stone, fe, m - 2.4, m + 2.4, 0.25, 1.6, 0, 0.45);
      ebox(stone, fe, m - 2.2, m - 1.6, 0.25, 1.3, 0.45, 4.0);
      ebox(stone, fe, m + 1.6, m + 2.2, 0.25, 1.3, 0.45, 4.0);
      ebox(stone, fe, m - 2.4, m + 2.4, 0.25, 1.45, 4.0, 4.5);
      ebox(door, fe, m - 1.1, m + 1.1, 0.25, 0.3, 0.45, 3.3);
      const pg = new THREE.CylinderGeometry(2.6, 2.6, 1.2, 3, 1).rotateX(Math.PI / 2);
      pg.scale(1, 0.32, 1);
      const pc = at(fe, m, 0.85);
      const pm = new THREE.Matrix4()
        .makeRotationZ(fe.ang)
        .multiply(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
      pm.setPosition(pc[0], pc[1], 4.5 + 0.45);
      B.addGeometry(stone, pg, pm);
      pg.dispose();
      ebox(
        signMat('bush:name', 'PASSMORE EDWARDS', '#d9d2c0', '#5a5246', 'bold 38px serif'),
        fe,
        m - 2.2,
        m + 2.2,
        1.46,
        1.5,
        4.02,
        4.45,
      );
      ebox(
        signMat('bush:theatre', 'BUSH THEATRE', '#1b1b1b', '#ffffff', 'bold 44px sans-serif'),
        fe,
        1.2,
        W / 2 - 4.6,
        0.25,
        0.3,
        4.1,
        4.9,
      );
    }
    // chimney stacks at the hip ends
    for (const s of [2.5, W - 2.5]) {
      const c = at(fe, s, -D / 2);
      kit.box(B, brick, c[0], c[1], EAV + 1, 1.2, 2.2, 6.6, ang);
      kit.box(B, stone, c[0], c[1], EAV + 7.6, 1.5, 2.5, 0.35, ang);
    }
    // rear hall (auditorium) and back-of-house wing over the remaining footprint
    {
      const rear = rect(u0 + 1.5, O.v0 + 0.5, u1 - 2.5, v1 - D);
      kit.walls(B, brick, [[rear]], 0, 8.0, { bay: 1e6 });
      kit.pitchedRoof(B, slate, brick, rear, ang + Math.PI / 2, 8.0, 4.0, 'gabled', {
        overhang: 0.25,
      });
      const f = kit.ringFrame(rear);
      for (const v of [-1, 1]) {
        const p = frameAt(f, 0, v * f.width * 0.22);
        kit.box(
          B,
          kit.mat('#9fb4bd', { roughness: 0.1 }),
          p[0],
          p[1],
          9.6,
          f.length * 0.5,
          1.6,
          0.25,
          f.angle,
        );
      }
      const re = edgesOf(rear);
      for (const e of [re[1], re[3]])
        kit.windowRow(B, e.a, e.b, 3.0, {
          width: 1.2,
          height: 3.4,
          bay: 4.2,
          margin: 1.5,
          glass,
          frame: stone,
          sill: stone,
          bars: 1,
          head: 'arch',
          depth: 0.18,
        });
    }
    g.add(B.toGroup('bush_theatre'));
    return g;
  },
};
