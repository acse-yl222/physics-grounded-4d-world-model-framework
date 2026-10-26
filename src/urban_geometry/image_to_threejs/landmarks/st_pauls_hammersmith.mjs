// St Paul's Church, Queen Caroline Street, Hammersmith (J. P. Seddon and H. R. Gough,
// 1882-91, Grade II*). Large Gothic town church beside the Hammersmith Flyover: coursed pink
// rubblestone with ashlar dressings, aisled nave under a steep slate roof with a lancet
// clerestory, big traceried east and west windows and a four-stage pinnacled tower at the
// north-east.
export default {
  id: 'st_pauls_hammersmith',
  name: "St Paul's Church, Hammersmith",
  claims: ['bfa7663c-a6b1-4bba-91df-8e48bc2643e8'],
  references: [
    {
      title: 'Church of St Paul, Hammersmith - British Listed Buildings (1079802)',
      url: 'https://britishlistedbuildings.co.uk/101079802-church-of-st-paul-hammersmith-hammersmith-broadway-ward',
      used_for:
        'Seddon and Gough, coursed pink rubblestone with ashlar dressings, 4-stage pinnacled tower at north east, Grade II*',
    },
    {
      title: 'St Paul Hammersmith - Church of England heritage record',
      url: 'https://heritage.churchofengland.org/buildings/7738',
      used_for: 'ring of eight bells (belfry in the tower)',
    },
    {
      title: "St Paul's Churchyard and St Paul's Green - London Gardens Trust",
      url: 'https://londongardenstrust.org/conservation/inventory/site-record?ID=HAF055',
      used_for: 'setting in the churchyard / green beside the flyover',
    },
  ],
  notes:
    'Tower height (~38 m to the pinnacles), nave eaves (12 m) and ridge (21 m), the aisle/nave widths, buttress ' +
    'spacing, window counts and tracery, and the treatment of the lower western block (modelled as a gabled ' +
    'narthex/baptistery) are estimates; the footprint h=16.9 m is used only as a guide. Tracery is simplified to ' +
    'mullioned lancets under pointed heads.',
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
    const ang = Math.atan2(-1676.4 + 1677.6, -1697.0 + 1750.0); // nave axis (east along the south wall)
    const O = kit.orientedExtent(ring, ang);
    const P = (u, v) => {
      const p = O.at(u, v, 0);
      return [p[0], p[1]];
    };
    const rect = (u0, v0, u1, v1) => [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)];
    const uE = O.u1,
      uW = O.u1 - 53.3; // main body
    const v0 = O.v0,
      v1 = O.v1,
      vm = (v0 + v1) / 2;
    const rub = kit.mat('#b38878', { roughness: 0.95 });
    const ash = kit.mat('#d8cdb3', { roughness: 0.85 });
    const slate = kit.mat('slate');
    const glass = kit.mat('#4a5560', { roughness: 0.2, metalness: 0.2 });
    const lead = kit.mat('lead');

    const AE = 6.8, // aisle eaves
      CL0 = 9.6, // clerestory base
      NE = 13.0, // nave eaves
      NR = 21.5; // nave ridge
    const NW = 11.0; // nave width
    const nv0 = vm - NW / 2,
      nv1 = vm + NW / 2;
    // aisles (outer walls) and lean-to roofs
    const aisles = rect(uW, v0, uE - 9, v1);
    kit.walls(B, rub, [[aisles]], 0, AE, { bay: 1e6 });
    kit.cornice(B, ash, aisles, 0, { height: 0.6, projection: 0.15 });
    kit.cornice(B, ash, aisles, AE - 0.3, { height: 0.3, projection: 0.2 });
    for (const [a, b, c, d] of [
      [P(uW, v0), P(uE - 9, v0), P(uE - 9, nv0), P(uW, nv0)],
      [P(uE - 9, v1), P(uW, v1), P(uW, nv1), P(uE - 9, nv1)],
    ])
      B.add(
        slate,
        [
          [...a, AE],
          [...b, AE],
          [...c, CL0],
          [...d, CL0],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    // nave clerestory + roof, chancel continuing east at full width of the nave
    const nave = rect(uW, nv0, uE, nv1);
    kit.walls(B, rub, [[nave]], CL0 - 0.2, NE, { bay: 1e6 });
    kit.cornice(B, ash, nave, NE - 0.3, { height: 0.3, projection: 0.2 });
    kit.pitchedRoof(B, slate, rub, nave, ang, NE, NR - NE, 'gabled', { overhang: 0.3 });
    // chancel side walls below the clerestory where the aisles stop
    const chancel = rect(uE - 9, nv0, uE, nv1);
    kit.walls(B, rub, [[chancel]], 0, CL0, { bay: 1e6 });
    // buttresses and aisle lancets (pairs per bay)
    const E0 = edgesOf(aisles);
    const bayW = 4.9;
    for (const e of [E0[0], E0[2]]) {
      const n = Math.round(e.len / bayW);
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        ebox(ash, e, s - 0.45, s + 0.45, 0, 0.9, 0, AE - 1.2);
        ebox(ash, e, s - 0.4, s + 0.4, 0, 0.5, AE - 1.2, AE - 0.3);
      }
      for (let k = 0; k < n; k++) {
        const s = ((k + 0.5) * e.len) / n;
        kit.windowRow(B, at(e, s - 1.5), at(e, s + 1.5), 1.6, {
          width: 0.8,
          height: 3.4,
          count: 2,
          margin: 0.3,
          glass,
          frame: ash,
          sill: ash,
          head: 'arch',
          bars: 1,
          depth: 0.2,
        });
      }
    }
    // clerestory lancets in threes
    const EN = edgesOf(nave);
    for (const e of [EN[0], EN[2]]) {
      const n = Math.round(e.len / bayW);
      for (let k = 0; k < n; k++) {
        const s = ((k + 0.5) * e.len) / n;
        kit.windowRow(B, at(e, s - 1.8), at(e, s + 1.8), CL0 + 0.6, {
          width: 0.6,
          height: 1.8,
          count: 3,
          margin: 0.4,
          glass,
          frame: ash,
          sill: ash,
          head: 'arch',
          bars: 0,
          depth: 0.15,
        });
      }
    }
    // great east window and west window (tall pointed, mullioned)
    for (const e of [EN[1], EN[3]]) {
      const m = e.len / 2;
      kit.windowRow(B, at(e, m - 3.4), at(e, m + 3.4), 3.0, {
        width: 1.1,
        height: 7.5,
        count: 4,
        margin: 0.4,
        glass,
        frame: ash,
        sill: ash,
        head: 'arch',
        bars: 2,
        depth: 0.25,
      });
      // enclosing pointed arch hood (approximated by a stone ring of boxes)
      for (let t = 0; t <= 12; t++) {
        const th = Math.PI * (t / 12);
        const s = m - Math.cos(th) * 3.6,
          z = 10.5 + Math.sin(th) * 3.4;
        ebox(ash, e, s - 0.35, s + 0.35, 0, 0.3, z - 0.25, z + 0.25);
      }
      ebox(glass, e, m - 2.6, m + 2.6, 0.02, 0.06, 10.5, 12.8);
      // angle buttresses at the gable corners
      ebox(ash, e, -0.9, 0.3, -0.2, 1.2, 0, NE + 1);
      ebox(ash, e, e.len - 0.3, e.len + 0.9, -0.2, 1.2, 0, NE + 1);
    }
    // ---- western narthex / baptistery block (lower, gabled) ------------------------------
    {
      const wb = rect(O.u0, v0 + 1.0, uW, v1 - 4.5);
      kit.walls(B, rub, [[wb]], 0, 7.5, { bay: 1e6 });
      kit.cornice(B, ash, wb, 0, { height: 0.6, projection: 0.15 });
      kit.pitchedRoof(B, slate, rub, wb, ang + Math.PI / 2, 7.5, 5.5, 'gabled', { overhang: 0.3 });
      const ew = edgesOf(wb);
      const w = ew[3]; // west wall
      const m = w.len / 2;
      kit.windowRow(B, at(w, 0), at(w, w.len), 2.4, {
        width: 0.9,
        height: 3.0,
        count: 3,
        margin: 3,
        glass,
        frame: ash,
        sill: ash,
        head: 'arch',
        bars: 1,
        depth: 0.2,
      });
      for (const e of [ew[0], ew[2]]) {
        kit.windowRow(B, e.a, e.b, 2.6, {
          width: 0.8,
          height: 2.6,
          count: 3,
          margin: 2.5,
          glass,
          frame: ash,
          sill: ash,
          head: 'arch',
          bars: 1,
          depth: 0.2,
        });
        // gable west doorway
      }
      ebox(kit.mat('#4a3426'), w, m - 1.2, m + 1.2, 0, 0.12, 0, 2.6);
      ebox(ash, w, m - 1.6, m + 1.6, 0, 0.35, 2.6, 3.0);
    }
    // ---- north-east tower: four stages, belfry, parapet and pinnacles ---------------------
    {
      const T = 8.2;
      const tu0 = uE - 9 - T + 0.4,
        tv1 = v1;
      const tr = rect(tu0, tv1 - T, tu0 + T, tv1);
      const st = [0, 9.5, 17.0, 23.5, 31.0];
      for (let i = 0; i < 4; i++) {
        const r = kit.offsetRing(tr, -0.25 * i);
        kit.walls(B, rub, [[r]], st[i], st[i + 1], { bay: 1e6 });
        kit.cornice(B, ash, r, st[i + 1] - 0.35, { height: 0.35, projection: 0.25 });
      }
      const top = kit.offsetRing(tr, -0.75);
      kit.cap(B, lead, [[top]], st[4]);
      parapet(ash, top, st[4], 1.3, 0.35);
      // angle buttresses with set-offs
      for (const e of edgesOf(tr)) {
        for (const s of [0.6, e.len - 0.6]) {
          ebox(ash, e, s - 0.6, s + 0.6, 0, 1.1, 0, 9.5);
          ebox(ash, e, s - 0.5, s + 0.5, -0.1, 0.7, 9.5, 23.5);
        }
        // stage windows: lancet at stage 2, paired louvred belfry openings at stage 4
        kit.windowRow(B, e.a, e.b, 11.5, {
          width: 0.7,
          height: 3.2,
          count: 1,
          margin: 2,
          glass,
          frame: ash,
          sill: ash,
          head: 'arch',
          bars: 0,
          depth: 0.2,
        });
        kit.windowRow(B, at(e, 0.75), at(e, e.len - 0.75), 24.6, {
          width: 1.0,
          height: 4.6,
          count: 2,
          margin: 1.3,
          glass: kit.mat('#3a3633'),
          frame: ash,
          sill: ash,
          head: 'arch',
          bars: 4,
          depth: 0.25,
        });
        // clock face on the third stage
        const c = at(e, e.len / 2, 0.12);
        const cg = new THREE.CylinderGeometry(1.1, 1.1, 0.1, 20);
        B.addGeometry(
          kit.mat('#e8e2cf'),
          cg,
          new THREE.Matrix4().makeRotationZ(e.ang).setPosition(c[0], c[1], 20.2),
        );
        cg.dispose();
      }
      // pinnacles at the four corners and mid-parapet
      for (const p of top) {
        cyl(ash, p[0], p[1], st[4], 0.45, 0.45, 2.4, 8);
        cyl(ash, p[0], p[1], st[4] + 2.4, 0.5, 0.02, 3.8, 8);
      }
      const ctr = kit.ringFrame(tr);
      cyl(ash, ctr.cx, ctr.cy, st[4], 0.1, 0.05, 4.5, 6); // flagpole
    }
    g.add(B.toGroup('st_pauls_hammersmith'));
    return g;
  },
};
