// Cadogan Hall, 5 Sloane Terrace (Robert Fellowes Chisholm, 1904-07, built as First Church
// of Christ, Scientist; concert hall since 2004). Grade II. Byzantine Revival: Portland
// stone ashlar street front over a granite arcade, seven coupled windows across the
// facade, a domed campanile, brown London stock brick to the parts away from the street
// and a polygonal sheet-metal roof behind a pierced stone parapet.
export default {
  id: 'cadogan_hall',
  name: 'Cadogan Hall',
  claims: ['d2338931-badb-4f02-9d03-b55d9c9e0249'],
  references: [
    {
      title: 'Cadogan Hall - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Cadogan_Hall',
      used_for:
        'former Church of Christ, Scientist, completed 1907, Byzantine Revival, R. F. Chisholm, Grade II, 953 seats',
    },
    {
      title: 'Cadogan Hall - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=424005',
      used_for:
        '1904-9, Dove Brothers; Portland stone ashlar, granite ground-floor arcade, London stock brick behind, polygonal sheet metal roof behind pierced stone parapet',
    },
    {
      title: 'The Christian Science church in Chelsea - Patrick Comerford',
      url: 'https://www.patrickcomerford.com/2022/10/the-christian-science-church-in-chelsea.html',
      used_for: 'domed campanile; seven coupled windows across the facade',
    },
  ],
  notes:
    'Street front taken as the north edge (Sloane Terrace). Front height 15 m, auditorium walls 17 m with a ' +
    'low octagonal metal roof to ~22 m, and the campanile (5.5 m square, ~31 m to the finial) at the east ' +
    'end of the front are estimates; arcade bay count and parapet piercing are simplified.',
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
    const portland = kit.mat('#e2dccb', { roughness: 0.8 });
    const granite = kit.mat('#9c8f89', { roughness: 0.6 });
    const stock = kit.mat('#8f7457', { roughness: 0.9 });
    const metal = kit.mat('#7d8a8c', { roughness: 0.5, metalness: 0.45 });
    const glass = kit.mat('#2f3b45', { roughness: 0.2, metalness: 0.3 });
    const frame = kit.mat('#ece9e0');
    const copper = kit.mat('copper_green');
    const ring = ccw(buildings[0].polys[0][0]);
    const E = edges(ring);
    const front = E.reduce((p, q) => (q.len * q.ny > p.len * p.ny ? q : p));
    const H = 17;
    kit.walls(batch, stock, [[ring]], 0, H);
    kit.cap(batch, kit.mat('#86847f'), [[ring]], H - 0.2);
    kit.cornice(batch, portland, ring, H - 0.6, { height: 0.6, projection: 0.25 });
    // stock-brick side windows (round-headed)
    for (const e of E) {
      if (e === front || e.len < 8) continue;
      wins(e, 0, e.len, 6.5, {
        bay: 4.2,
        margin: 2,
        width: 1.6,
        height: 4.2,
        head: 'arch',
        frame: portland,
        sill: portland,
        glass,
        bars: 1,
      });
    }
    // Portland stone street front block (5 m deep) with granite arcade
    const L = front.len,
      FH = 15;
    const fb = ccw([at(front, 0), at(front, L), at(front, L, -5), at(front, 0, -5)]);
    kit.walls(batch, portland, [[fb]], 4.6, FH);
    kit.walls(batch, granite, [[fb]], 0, 4.6);
    kit.cap(batch, kit.mat('#86847f'), [[fb]], FH);
    ebox(portland, front, 0, L, 0, 0.45, 4.4, 4.9);
    ebox(portland, front, -0.2, L + 0.2, 0, 0.6, FH - 0.7, FH);
    // ground-floor arcade: round arches on granite piers
    const na = 7;
    const t0 = front.dx < 0; // tower (east end) at s = 0
    const A0 = t0 ? 7 : 0,
      A1 = t0 ? L : L - 7;
    wins(front, A0, A1, 0.4, {
      count: na,
      margin: 1.0,
      width: 2.6,
      height: 2.6,
      head: 'arch',
      frame: granite,
      sill: granite,
      glass: kit.mat('#3b3127'),
      bars: 0,
      depth: 0.5,
    });
    // seven coupled windows across the facade (pairs under relieving arches)
    for (let k = 0; k < na; k++) {
      const s = A0 + 1.0 + ((A1 - A0 - 2) * (k + 0.5)) / na;
      wins(front, s - 1.5, s + 1.5, 6.4, {
        count: 2,
        margin: 0.2,
        width: 0.9,
        height: 4.4,
        head: 'arch',
        frame: portland,
        sill: portland,
        glass,
        bars: 1,
      });
      ebox(portland, front, s - 1.55, s + 1.55, 0, 0.3, 11.5, 11.8);
    }
    // pierced parapet (balustrade) along the front
    kit.balustrade(batch, portland, [at(front, A0 + 0.3, 0.3), at(front, A1 - 0.3, 0.3)], FH, {
      height: 1.0,
      spacing: 0.45,
    });
    // polygonal sheet-metal roof over the auditorium
    {
      const fr = kit.ringFrame(ring);
      const c = [fr.cx - front.nx * 3, fr.cy - front.ny * 3];
      cyl(stock, c[0], c[1], H - 0.2, 10, 10, 1.8, 8);
      lathe(
        metal,
        [
          [0.01, 0],
          [10.6, 0],
          [9.5, 1.5],
          [6.5, 3.2],
          [2.2, 4.2],
          [0.01, 4.4],
        ],
        c[0],
        c[1],
        H + 1.6,
        8,
      );
      cyl(metal, c[0], c[1], H + 6.0, 1.2, 1.0, 1.4, 8);
    }
    // domed campanile at the east end of the front
    {
      const p = at(front, t0 ? 3.2 : L - 3.2, -2.8);
      const t = rect(p[0], p[1], front.ang, 5.6, 5.6);
      kit.walls(batch, portland, [[t]], 0, 24);
      kit.cap(batch, portland, [[t]], 24);
      for (const z of [4.6, FH - 0.6, 20])
        kit.cornice(batch, portland, t, z, { height: 0.4, projection: 0.2 });
      for (const e of edges(t)) {
        wins(e, 0, e.len, 6.4, {
          count: 1,
          margin: 1.6,
          width: 1.0,
          height: 4.0,
          head: 'arch',
          frame: portland,
          sill: portland,
          glass,
          bars: 0,
        });
        // open arcaded belfry stage
        wins(e, 0, e.len, 20.6, {
          count: 2,
          margin: 0.8,
          width: 1.3,
          height: 2.4,
          head: 'arch',
          frame: portland,
          sill: portland,
          glass: kit.mat('#23262a'),
          bars: 0,
          depth: 0.3,
        });
      }
      kit.cornice(batch, portland, t, 23.6, { height: 0.5, projection: 0.4 });
      cyl(portland, p[0], p[1], 24, 2.6, 2.6, 1.2, 12);
      lathe(
        copper,
        [
          [0.01, 0],
          [2.8, 0],
          [2.6, 1.2],
          [1.9, 2.4],
          [0.8, 3.2],
          [0.3, 3.5],
          [0.01, 3.6],
        ],
        p[0],
        p[1],
        25.2,
        16,
      );
      cyl(kit.mat('gold'), p[0], p[1], 28.8, 0.12, 0.03, 1.8, 6);
    }
    g.add(batch.toGroup('cadogan_hall'));
    return g;
  },
};
