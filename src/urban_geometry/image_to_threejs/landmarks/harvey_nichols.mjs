// Harvey Nichols, 109-125 Knightsbridge (C. W. Stephens, built in stages 1889-94; later
// inter-war alterations). Department store on the corner of Knightsbridge and Sloane
// Street: tall plate-glass shop windows under the store's black canopies, upper storeys of
// red brick with stone dressings, a canted corner, and a slate mansard with dormers.
export default {
  id: 'harvey_nichols',
  name: 'Harvey Nichols',
  claims: ['d3129735-42d1-4095-9457-2e0d520a1a38'],
  references: [
    {
      title: 'Harvey Nichols - the history',
      url: 'https://www.harveynichols.com/info/help/about/the-history/',
      used_for: 'old premises demolished 1889, present building built in stages 1889-94',
    },
    {
      title: 'Harvey Nichols - Buildington',
      url: 'https://www.buildington.co.uk/buildings/904/england/london-sw1x/109-125-knightsbridge/harvey-nichols',
      used_for: 'architect Charles William Stephens (Claridges, Park Lane Hotel)',
    },
    {
      title: 'Knightsbridge South Side - Survey of London vol. 45 (British History Online)',
      url: 'https://prod.british-history.ac.uk/node/38510',
      used_for:
        'mixture of late Victorian and inter-war exterior; growth shop by shop; Knightsbridge and Sloane Street fronts',
    },
  ],
  notes:
    'Facade materials (red brick with stone dressings above, stone ground and first floors), storey split ' +
    '(6 m shop storey, three 3.7 m upper storeys, mansard), the canted corner with its lead cupola, and the ' +
    'pilaster rhythm are reconstructed from general knowledge of the building; the searched sources do not ' +
    'describe materials. Overture height 14.9 m is raised to ~23 m to the mansard top.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // ---- local helpers (modules have no imports) -----------------------------------
    const ccw = (r) => {
      const o = r.slice();
      if (kit.ringArea(o) < 0) o.reverse();
      return o;
    };
    const edges = (r) =>
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
          mx: (a[0] + b[0]) / 2,
          my: (a[1] + b[1]) / 2,
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box on edge e from s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
      const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, p[0], p[1], z0, Math.abs(s1 - s0), Math.abs(d1 - d0), z1 - z0, e.ang, c);
    };
    const prism = (m, ring, z0, z1, top = m) => {
      kit.walls(batch, m, [[ring]], z0, z1);
      if (top) kit.cap(batch, top, [[ring]], z1);
    };
    const wins = (e, s0, s1, z, o) => kit.windowRow(batch, at(e, s0), at(e, s1), z, o);
    const cyl = (m, x, y, z0, r0, r1, h, seg = 12) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) => {
      const g = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
      g.dispose();
    };
    // Rectangle ring (CCW) centred at (cx, cy), long axis at angle ang.
    const rect = (cx, cy, ang, L, W) => {
      const c = Math.cos(ang),
        s = Math.sin(ang);
      return [
        [-L / 2, -W / 2],
        [L / 2, -W / 2],
        [L / 2, W / 2],
        [-L / 2, W / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    // Triangular gable (pediment) standing on edge e between s0..s1, base z, rise, from d0..d1.
    const gable = (m, e, s0, s1, z, rise, d0 = 0, d1 = 0.4) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, 0);
      sh.lineTo(s1, 0);
      sh.lineTo((s0 + s1) / 2, rise);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d1 - d0, bevelEnabled: false });
      // shape x along edge, y up, extrude z outward -> map to world
      const m4 = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m4.setPosition(e.a[0] + e.nx * d0, e.a[1] + e.ny * d0, z);
      batch.addGeometry(m, g, m4);
      g.dispose();
    };
    // Facing test: cosine between an edge's outward normal and a direction (dx, dy).
    const facing = (e, dx, dy) => (e.nx * dx + e.ny * dy) / (Math.hypot(dx, dy) || 1);
    // Drop near-duplicate and nearly collinear vertices (makes offsets well behaved).
    const clean = (r, tol = 0.8) => {
      let o = r.filter((p, k) => {
        const q = r[(k + 1) % r.length];
        return Math.hypot(q[0] - p[0], q[1] - p[1]) > tol;
      });
      for (let pass = 0; pass < 3; pass++)
        o = o.filter((p, k) => {
          const a = o[(k - 1 + o.length) % o.length],
            b = o[(k + 1) % o.length];
          const cr = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]);
          const l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
          return Math.abs(cr) / l > 0.25;
        });
      return o;
    };
    // Sloped band (mansard / hipped roof) from ring at z0 to the ring inset by `inset` at z1.
    // Returns the inner ring; capped with topMat unless topMat is null.
    const mansard = (m, ring, z0, inset, z1, topMat = m) => {
      const inner = kit.offsetRing(ring, -inset);
      for (let k = 0; k < ring.length; k++) {
        const j = (k + 1) % ring.length;
        const a = ring[k],
          b = ring[j],
          c = inner[j],
          d = inner[k];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [d[0], d[1], z1],
          [0, 0],
          [l / 3, 0],
          [l / 3, 1],
          [0, 1],
        );
      }
      if (topMat) kit.cap(batch, topMat, [[inner]], z1);
      return inner;
    };
    // Rows of windows on edge e at each sill height in zs.
    const rows = (e, s0, s1, zs, o) => {
      for (const z of zs)
        kit.windowRow(batch, at(e, s0), at(e, s1), z, typeof o === 'function' ? o(z) : o);
    };
    // ---------------------------------------------------------------------------------
    const brick = kit.mat('#9a4f3b', { roughness: 0.88 });
    const stone = kit.mat('#ded6c3', { roughness: 0.8 });
    const slate = kit.mat('#4f565d', { roughness: 0.75 });
    const lead = kit.mat('#7d878b', { roughness: 0.55, metalness: 0.3 });
    const glass = kit.mat('#26333b', { roughness: 0.1, metalness: 0.4 });
    const shopGlass = kit.mat('#3d4c55', { roughness: 0.08, metalness: 0.4 });
    const frame = kit.mat('#f1f0ea');
    const black = kit.mat('#16181a', { roughness: 0.5 });
    const roofM = kit.mat('#8c8b86');

    let ring = ccw(buildings[0].polys[0][0]);
    // canted corner at the Knightsbridge / Sloane Street corner (north-east vertex)
    const ci = ring.reduce((bi, p, i) => (p[0] + p[1] > ring[bi][0] + ring[bi][1] ? i : bi), 0);
    const CP = ring[ci].slice();
    {
      const n = ring.length,
        p = ring[ci],
        a = ring[(ci - 1 + n) % n],
        b = ring[(ci + 1) % n];
      const cut = 4.5;
      const u = (q) => {
        const l = Math.hypot(q[0] - p[0], q[1] - p[1]);
        return [p[0] + ((q[0] - p[0]) / l) * cut, p[1] + ((q[1] - p[1]) / l) * cut];
      };
      ring = [...ring.slice(0, ci), u(a), u(b), ...ring.slice(ci + 1)];
    }
    const G = 6.0,
      ST = 3.7,
      NU = 3,
      CORN = G + NU * ST; // 17.1
    kit.walls(batch, stone, [[ring]], 0, G + ST);
    kit.walls(batch, brick, [[ring]], G + ST, CORN);
    kit.cornice(batch, stone, ring, G - 0.5, { height: 0.7, projection: 0.3 });
    kit.cornice(batch, stone, ring, G + ST - 0.25, { height: 0.4, projection: 0.15 });
    kit.cornice(batch, stone, ring, CORN - 0.5, { height: 0.9, projection: 0.55, steps: 2 });
    // parapet + mansard
    kit.walls(batch, stone, [[ring]], CORN, CORN + 0.9);
    mansard(slate, kit.offsetRing(ring, -0.6), CORN + 0.4, 2.2, CORN + 4.6, roofM);

    for (const e of edges(ring)) {
      if (e.len < 3) continue;
      const corner = e.len < 7 && Math.hypot(e.mx - CP[0], e.my - CP[1]) < 5;
      const front = facing(e, -0.37, 0.93) > 0.8 || facing(e, 0.97, -0.24) > 0.8 || corner;
      // ground floor: plate-glass display windows between stone piers + black canopies
      const nb = Math.max(1, Math.round(e.len / 4.6));
      for (let k = 0; k < nb; k++) {
        const s0 = (k * e.len) / nb,
          s1 = ((k + 1) * e.len) / nb;
        ebox(stone, e, s0, s0 + 0.7, 0, 0.35, 0, G);
        ebox(shopGlass, e, s0 + 0.7, s1, -0.15, -0.05, 0.5, G - 1.1);
        ebox(black, e, s0 + 0.7, s1, -0.1, 0.05, 0, 0.5);
        if (front) ebox(black, e, s0 + 0.7, s1, 0, 1.6, G - 1.5, G - 1.2);
      }
      // stone pilasters through the upper storeys
      const np = Math.max(1, Math.round(e.len / 4.6));
      for (let k = 0; k <= np; k++) {
        const s = (k * e.len) / np;
        ebox(stone, e, Math.max(0, s - 0.45), Math.min(e.len, s + 0.45), 0, 0.25, G, CORN - 0.5);
      }
      // windows: tall first-floor (stone) windows with arched heads, brick storeys above
      rows(e, 0, e.len, [G + 0.6], {
        width: 2.6,
        height: 2.5,
        count: np,
        margin: 0.4,
        head: 'segment',
        frame,
        sill: stone,
        glass,
        bars: 1,
      });
      rows(e, 0, e.len, [G + ST + 0.7, G + 2 * ST + 0.7], {
        width: 1.5,
        height: 2.2,
        count: np * 2,
        margin: 0.4,
        head: 'lintel',
        frame,
        sill: stone,
        glass,
        bars: 1,
        surround: 0.14,
        surroundMat: stone,
      });
      // dormers
      const nd = Math.max(1, Math.floor(e.len / 4.6));
      if (!corner)
        for (let k = 0; k < nd; k++) {
          const s = ((k + 0.5) * e.len) / nd;
          ebox(slate, e, s - 0.9, s + 0.9, -1.8, -0.9, CORN + 0.4, CORN + 3.0);
          wins(e, s - 0.9, s + 0.9, CORN + 1.0, {
            width: 1.0,
            height: 1.6,
            count: 1,
            margin: 0.4,
            head: 'none',
            frame,
            sill: stone,
            glass,
            bars: 1,
            depth: 0.1,
          });
          ebox(lead, e, s - 1.0, s + 1.0, -1.9, -0.75, CORN + 3.0, CORN + 3.25);
        }
      if (corner) {
        // corner cupola on a drum
        const p = at(e, e.len / 2, -2.2);
        cyl(stone, p[0], p[1], CORN, 2.4, 2.4, 3.4, 12);
        cyl(stone, p[0], p[1], CORN + 3.4, 2.6, 2.6, 0.4, 12);
        lathe(
          lead,
          [
            [0.01, 0],
            [2.5, 0],
            [2.3, 1.2],
            [1.6, 2.4],
            [0.5, 3.1],
            [0.3, 3.4],
            [0.35, 3.9],
            [0.01, 4.1],
          ],
          p[0],
          p[1],
          CORN + 3.8,
          16,
        );
        // shop name sign on the corner
        const sign = kit.paintedMaterial('harvey_nichols:sign', 512, 64, (c, w, h) => {
          c.fillStyle = '#16181a';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#f4f2ec';
          c.font = 'bold 34px serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('HARVEY NICHOLS', w / 2, h / 2 + 2);
        });
        const a = at(e, 0, 1.65),
          b = at(e, e.len, 1.65);
        batch.quad(
          sign,
          [a[0], a[1], G - 1.5],
          [b[0], b[1], G - 1.5],
          [b[0], b[1], G - 0.9],
          [a[0], a[1], G - 0.9],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    // chimneys / roof plant
    const fr = kit.ringFrame(ring);
    kit.box(batch, roofM, fr.cx, fr.cy, CORN + 4.6, 14, 8, 2.4, fr.angle);
    g.add(batch.toGroup('harvey_nichols'));
    return g;
  },
};
