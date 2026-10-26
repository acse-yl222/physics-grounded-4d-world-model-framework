// Peter Jones, Sloane Square (William Crabtree with Slater, Moberly & Reilly, 1936-39).
// Grade II*. One of the first glass curtain walls in England: a seven-storey concrete and
// steel frame wrapping the corner of Sloane Square and King's Road in a smooth curve;
// plate glass to the ground floor under a cantilevered canopy, narrowly spaced mullions
// with glass and white panels on the first to fourth floors, a recessed fifth floor with
// metal railings, and "Peter Jones" lettering on the white panels.
export default {
  id: 'peter_jones',
  name: 'Peter Jones',
  claims: ['d6002410-8efa-4257-94ee-aa5b216f0fca'],
  references: [
    {
      title: 'Peter Jones - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=423991',
      used_for:
        'Grade II*, 1936-39, Crabtree/Slater Moberly/Reilly; concrete, glass and metal; seven storeys; curved corner; canopy; mullions with glass and white panels; recessed fifth floor; railings; lettering',
    },
    {
      title: 'William Crabtree (architect) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/William_Crabtree_(architect)',
      used_for: 'one of the first uses of the glass curtain wall in England',
    },
    {
      title: 'The rebuilding of Peter Jones, 1932-1936 - John Lewis Memory Store',
      url: 'https://johnlewismemorystore.org.uk/content/branch_finder/branches_o-r/peter_jones/the_rebuilding_of_peter_jones_1932-1936',
      used_for: 'rebuilding history and curved corner on Sloane Square',
    },
  ],
  notes:
    'Storey heights (5.2 m ground, 3.6 m upper) and the set-back depths of the fifth and sixth floors are ' +
    'estimates giving ~27 m overall (Overture parts 20-23 m). Mullion pitch 1.05 m, the spandrel panel ' +
    'proportions, the position of the lettering above the canopy on the curved corner and the rooftop ' +
    'plant are approximations.',
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
    const white = kit.mat('#f0efe9', { roughness: 0.55 });
    const glass = kit.mat('#3f5562', { roughness: 0.08, metalness: 0.45 });
    const shopGlass = kit.mat('#2c3a42', { roughness: 0.08, metalness: 0.4 });
    const bronze = kit.mat('#5d4a36', { roughness: 0.45, metalness: 0.6 });
    const mull = kit.mat('#d9dbd8', { roughness: 0.4, metalness: 0.4 });
    const roofM = kit.mat('#8d8c87');
    const conc = kit.mat('#cfccc3');

    const ring = ccw(buildings[0].polys[0][0]);
    const G = 5.2,
      ST = 3.6,
      CW = G + 4 * ST; // 19.6 top of curtain wall
    const R5 = kit.offsetRing(clean(ring, 1.5), -1.8);
    const f6 = kit.ringFrame(ring);
    const R6 = rect(f6.cx, f6.cy, f6.angle, f6.length - 44, f6.width - 34);
    // ground floor: plate glass behind slender piers, cantilevered canopy
    kit.walls(batch, shopGlass, [[kit.offsetRing(ring, -0.4)]], 0, G - 0.9);
    kit.walls(batch, white, [[ring]], G - 0.9, G);
    kit.cap(batch, white, [[kit.offsetRing(ring, 2.2), ring.slice().reverse()]], G - 1.2);
    kit.cap(batch, white, [[kit.offsetRing(ring, 2.2), ring.slice().reverse()]], G - 1.5, {
      down: true,
    });
    kit.walls(batch, white, [[kit.offsetRing(ring, 2.2)]], G - 1.5, G - 1.2);
    // curtain wall storeys
    kit.walls(batch, glass, [[kit.offsetRing(ring, -0.15)]], G, CW);
    for (const e of edges(ring)) {
      if (e.len < 0.3) continue;
      for (let f = 0; f < 4; f++) {
        const z = G + f * ST;
        ebox(white, e, 0, e.len, -0.15, 0.02, z, z + 1.05); // white spandrel panel
      }
      ebox(white, e, 0, e.len, -0.15, 0.05, CW - 0.2, CW + 0.9); // top band (lettering zone)
      const nm = Math.max(1, Math.round(e.len / 1.05));
      for (let k = 0; k <= nm; k++) {
        const s = (k * e.len) / nm;
        ebox(mull, e, s - 0.04, s + 0.04, -0.05, 0.12, G, CW - 0.2);
      }
      // ground-floor piers
      const np = Math.max(1, Math.round(e.len / 6));
      for (let k = 0; k <= np; k++) {
        const s = (k * e.len) / np;
        ebox(white, e, Math.max(0, s - 0.25), Math.min(e.len, s + 0.25), -0.45, -0.1, 0, G - 0.9);
      }
    }
    kit.cap(batch, roofM, [[ring]], CW + 0.9);
    // recessed fifth floor with railings
    kit.walls(batch, glass, [[R5]], CW + 0.9, CW + 0.9 + ST);
    kit.cap(batch, white, [[R5]], CW + 0.9 + ST);
    kit.cornice(batch, white, R5, CW + ST + 0.5, { height: 0.4, projection: 0.5 });
    for (const e of edges(R5)) {
      if (e.len < 0.3) continue;
      const nm = Math.max(1, Math.round(e.len / 1.6));
      for (let k = 0; k <= nm; k++)
        ebox(
          mull,
          e,
          (k * e.len) / nm - 0.05,
          (k * e.len) / nm + 0.05,
          0,
          0.1,
          CW + 0.9,
          CW + 0.9 + ST,
        );
    }
    for (const e of edges(kit.offsetRing(ring, -0.3))) {
      if (e.len < 0.3) continue;
      ebox(bronze, e, 0, e.len, -0.04, 0.04, CW + 1.9, CW + 1.98);
      const nr = Math.max(1, Math.round(e.len / 1.8));
      for (let k = 0; k <= nr; k++)
        ebox(
          bronze,
          e,
          (k * e.len) / nr - 0.03,
          (k * e.len) / nr + 0.03,
          -0.04,
          0.04,
          CW + 0.9,
          CW + 1.95,
        );
    }
    // sixth floor (further set back) where the plan allows
    if (kit.ringArea(R6) > 200) {
      const z0 = CW + 0.9 + ST;
      prism(conc, R6, z0, z0 + 3.2, roofM);
      kit.cornice(batch, white, R6, z0 + 2.9, { height: 0.3, projection: 0.3 });
      const fr = kit.ringFrame(R6);
      kit.box(
        batch,
        conc,
        fr.cx,
        fr.cy,
        z0 + 3.2,
        Math.min(18, fr.length / 3),
        Math.min(8, fr.width / 2),
        2.6,
        fr.angle,
      );
    }
    // "PETER JONES" lettering on the top band of the Sloane Square front and King's Road
    const sign = kit.paintedMaterial('peter_jones:sign', 512, 64, (c, w, h) => {
      c.fillStyle = '#f0efe9';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#1c1c1c';
      c.font = 'bold 40px sans-serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('PETER JONES', w / 2, h / 2 + 2);
    });
    const E = edges(ring).filter((e) => e.len > 15);
    const east = E.reduce((p, q) => (q.nx > p.nx ? q : p));
    const south = E.reduce((p, q) => (q.len * -q.ny > p.len * -p.ny ? q : p));
    for (const [e, w] of [
      [east, 12],
      [south, 18],
    ]) {
      const sm = e.len / 2;
      const a = at(e, sm - w / 2, 0.07),
        b = at(e, sm + w / 2, 0.07);
      batch.quad(
        sign,
        [a[0], a[1], CW - 0.1],
        [b[0], b[1], CW - 0.1],
        [b[0], b[1], CW + 0.8],
        [a[0], a[1], CW + 0.8],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    g.add(batch.toGroup('peter_jones'));
    return g;
  },
};
