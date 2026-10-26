// National Army Museum, Royal Hospital Road, Chelsea (William Holford & Partners, begun
// 1961, opened by the Queen 11 November 1971, on part of the old Royal Hospital infirmary
// site; remodelled by BDP 2014-17 with a new entrance, a naturally lit central atrium
// running front to back and new openings and rooflights cut into the brick facades).
export default {
  id: 'national_army_museum',
  name: 'National Army Museum',
  claims: ['f6db3be3-a259-4ed3-8df1-5a81d173de32'],
  references: [
    {
      title: 'National Army Museum - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/National_Army_Museum',
      used_for:
        'brutalist building by William Holford & Partners, started 1961, opened 11 November 1971; closed 2014-17 for rebuilding',
    },
    {
      title: 'Army museum opens again after £23m revamp - Construction Management',
      url: 'https://constructionmanagement.co.uk/army-muse6um-op5en-a7gain-after-23m-revamp/',
      used_for:
        'BDP scheme: new entrance building, atrium, new glazing formed in existing walls and roof',
    },
    {
      title: 'National Army Museum Redevelopment - Gilbert-Ash',
      url: 'https://gilbert-ash.com/projects/arts-culture/national-army-museum',
      used_for: 'new two-storey extension, re-ordering of the 1970s building',
    },
    {
      title: 'The National Army Museum - Manchester History (architecture)',
      url: 'https://manchesterhistory.net/architecture/1970/armymuseum.html',
      used_for: 'Holford & Partners 1961-71 attribution',
    },
  ],
  notes:
    'Overture h 7.7 m replaced by an estimated four storeys (~17 m) of dark brick with concrete bands and ' +
    'slot windows; the entrance pavilion (glazed, two storeys, deep white canopy and lettering) is put on ' +
    'the north-west Royal Hospital Road front. Atrium rooflight strip along the axis, window rhythm and ' +
    'roof plant are approximations; no elevation drawings were found.',
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
    const brick = kit.mat('#6e4434', { roughness: 0.9 });
    const conc = kit.mat('#b9b3a6', { roughness: 0.85 });
    const glass = kit.mat('#33434e', { roughness: 0.1, metalness: 0.4 });
    const white = kit.mat('#f1f0ec', { roughness: 0.55 });
    const frame = kit.mat('#2a2d30', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#7c7b77');
    const ring = ccw(buildings[0].polys[0][0]);
    const H = 17;
    kit.walls(batch, brick, [[ring]], 0, H);
    kit.cap(batch, roofM, [[ring]], H);
    kit.cornice(batch, conc, ring, 0, { height: 0.9, projection: 0.12 });
    for (const z of [5.0, 9.0, 13.0])
      kit.cornice(batch, conc, ring, z - 0.3, { height: 0.6, projection: 0.25 });
    kit.cornice(batch, conc, ring, H - 1.2, { height: 1.2, projection: 0.6 });
    const E = edges(ring);
    const front = E.reduce((p, q) => (q.len * facing(q, -1, 1) > p.len * facing(p, -1, 1) ? q : p));
    for (const e of E) {
      if (e.len < 5) continue;
      // narrow vertical slot windows (as built) and wider cut openings (2017)
      const n = Math.max(1, Math.round(e.len / 2.4));
      for (const z of [5.6, 9.6, 13.4])
        wins(e, 0, e.len, z, {
          count: n,
          margin: 1,
          width: 0.55,
          height: 2.6,
          head: 'none',
          frame: conc,
          sill: conc,
          glass,
          bars: 0,
          depth: 0.2,
        });
      if (e !== front)
        wins(e, 0, e.len, 1.4, {
          count: Math.max(1, Math.round(e.len / 9)),
          margin: 3,
          width: 3.6,
          height: 2.6,
          head: 'none',
          frame,
          sill: conc,
          glass,
          bars: 1,
        });
    }
    // 2017 entrance pavilion: glazed two-storey box with a deep white canopy and lettering
    {
      const e = front,
        sm = e.len / 2,
        w = Math.min(22, e.len - 4);
      ebox(glass, e, sm - w / 2, sm + w / 2, 0, 3.2, 0, 8.2);
      for (let k = 0; k <= 10; k++) {
        const s = sm - w / 2 + (k * w) / 10;
        ebox(frame, e, s - 0.06, s + 0.06, 3.2, 3.3, 0, 8.2);
      }
      ebox(frame, e, sm - w / 2, sm + w / 2, 3.2, 3.3, 4.1, 4.2);
      ebox(white, e, sm - w / 2 - 1, sm + w / 2 + 1, -0.3, 6.2, 8.2, 9.2);
      const sign = kit.paintedMaterial('national_army_museum:sign', 1024, 64, (c, cw, ch) => {
        c.fillStyle = '#f1f0ec';
        c.fillRect(0, 0, cw, ch);
        c.fillStyle = '#1b1d20';
        c.font = 'bold 40px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('NATIONAL ARMY MUSEUM', cw / 2, ch / 2 + 2);
      });
      const a = at(e, sm - 9, 6.22),
        b = at(e, sm + 9, 6.22);
      batch.quad(
        sign,
        [a[0], a[1], 8.3],
        [b[0], b[1], 8.3],
        [b[0], b[1], 9.1],
        [a[0], a[1], 9.1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // central atrium rooflight running front to back
      const fr = kit.ringFrame(ring);
      const ra = Math.atan2(-e.ny, -e.nx);
      const rl = rect(fr.cx, fr.cy, ra, 40, 6);
      kit.walls(batch, frame, [[rl]], H, H + 1.2);
      kit.pitchedRoof(batch, glass, frame, rl, ra, H + 1.2, 1.4, 'gabled', { overhang: 0 });
    }
    // plant room
    {
      const fr = kit.ringFrame(ring);
      kit.box(
        batch,
        conc,
        fr.cx + Math.cos(fr.angle + 1.57) * 12,
        fr.cy + Math.sin(fr.angle + 1.57) * 12,
        H,
        12,
        6,
        2.6,
        fr.angle,
      );
    }
    g.add(batch.toGroup('national_army_museum'));
    return g;
  },
};
