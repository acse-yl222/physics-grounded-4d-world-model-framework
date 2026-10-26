// St Peter's Church, Eaton Square (Henry Hakewill, 1824-27; rebuilt after fire 1837 by
// Charles Jearrad and J. H. Hakewill; recast by Arthur Blomfield 1873-75; refitted 1988-91
// after the 1987 arson). Grade II*. Neoclassical: hexastyle Ionic portico facing down Eaton
// Square with a clock tower above, yellow stock brick body with ashlar and stone dressings.
export default {
  id: 'st_peters_eaton_square',
  name: "St Peter's Eaton Square",
  claims: ['5f4af988-a80f-43b6-97d9-90addb1c2bcd'],
  references: [
    {
      title: "St Peter's Church, Eaton Square - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Peter%27s_Church,_Eaton_Square',
      used_for:
        'Henry Hakewill 1824-27, hexastyle Ionic portico and clock tower, Grade II*, 1987 fire',
    },
    {
      title: 'Church of St Peter - Historic England list entry 1356980',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1356980',
      used_for:
        'yellow stock brick, ashlar, stone dressings; 1837 rebuild; Blomfield recasting 1873-5',
    },
    {
      title: "1874 - St. Peter's Church, Eaton Square - Archiseek",
      url: 'https://www.archiseek.com/?p=566112',
      used_for: 'Blomfield enlargement 1874',
    },
  ],
  notes:
    'Portico placed on the south-west end of the footprint (facing down Eaton Square). Wall height 14 m, ' +
    'portico order height 10 m, and the tower (square clock stage, columned circular belfry, small cupola; ' +
    '~38 m) are proportioned from general photographs, not measured. The Blomfield chancel/apse at the ' +
    'north-east end is drawn as the plain stepped footprint with round-headed windows.',
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
    const brick = kit.mat('#c2a878', { roughness: 0.9 });
    const stone = kit.mat('#e4dccb', { roughness: 0.8 });
    const slate = kit.mat('#5a6066', { roughness: 0.75 });
    const lead = kit.mat('lead');
    const glass = kit.mat('#3a4652', { roughness: 0.2, metalness: 0.25 });
    const clockM = kit.paintedMaterial('st_peters_eaton:clock', 128, 128, (c, w) => {
      c.fillStyle = '#f2efe6';
      c.beginPath();
      c.arc(w / 2, w / 2, w / 2 - 3, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#222';
      c.lineWidth = 4;
      c.stroke();
      c.fillStyle = '#222';
      for (let k = 0; k < 12; k++) {
        const a = (k * Math.PI) / 6;
        c.fillRect(w / 2 + Math.cos(a) * 50 - 2, w / 2 + Math.sin(a) * 50 - 2, 4, 4);
      }
      c.beginPath();
      c.moveTo(w / 2, w / 2);
      c.lineTo(w / 2 + 2, 24);
      c.moveTo(w / 2, w / 2);
      c.lineTo(w / 2 + 28, w / 2 + 14);
      c.stroke();
    });
    const ring = ccw(buildings[0].polys[0][0]);
    const H = 14;
    kit.walls(batch, brick, [[ring]], 0, H);
    kit.cornice(batch, stone, ring, 0, { height: 0.7, projection: 0.15 });
    kit.cornice(batch, stone, ring, H - 1.0, { height: 1.0, projection: 0.45, steps: 2 });
    kit.cap(batch, lead, [[ring]], H - 0.1);
    const E = edges(ring);
    const front = E.reduce(
      (p, q) => (q.len > 12 && facing(q, -1, -1) > facing(p, -1, -1) ? q : p),
      E.find((e) => e.len > 12),
    );
    const ax = -front.nx,
      ay = -front.ny; // axis towards the north-east (chancel)
    const ang = Math.atan2(ay, ax);
    // main roof: low pitched over the nave
    {
      const fr = kit.ringFrame(ring);
      const nave = rect(fr.cx, fr.cy, ang, fr.length - 6, front.len - 2);
      kit.pitchedRoof(batch, slate, brick, nave, ang, H - 0.1, 3.6, 'gabled', { overhang: 0.1 });
    }
    for (const e of E) {
      if (e === front || e.len < 6) continue;
      const nb = Math.max(1, Math.round(e.len / 5));
      wins(e, 0, e.len, 1.4, {
        count: nb,
        margin: 0.8,
        width: 1.3,
        height: 2.2,
        head: 'segment',
        frame: stone,
        sill: stone,
        glass,
        bars: 1,
      });
      wins(e, 0, e.len, 5.8, {
        count: nb,
        margin: 0.8,
        width: 2.0,
        height: 5.4,
        head: 'arch',
        frame: stone,
        sill: stone,
        glass,
        bars: 2,
      });
      for (let k = 0; k <= nb; k++)
        ebox(
          brick,
          e,
          Math.max(0, (k * e.len) / nb - 0.4),
          Math.min(e.len, (k * e.len) / nb + 0.4),
          0,
          0.25,
          0.7,
          H - 1,
        );
    }
    // hexastyle Ionic portico with pediment
    const L = front.len,
      d = 3.4,
      CH = 10.0;
    ebox(stone, front, -0.2, L + 0.2, -0.2, d + 1.4, 0, 0.35);
    ebox(stone, front, 0, L, -0.2, d + 1.0, 0.35, 0.7);
    ebox(stone, front, 0.2, L - 0.2, -0.2, d + 0.6, 0.7, 1.05);
    kit.colonnade(batch, stone, at(front, 1.1, d), at(front, L - 1.1, d), 1.05, CH, {
      count: 6,
      radius: 0.55,
      capital: 'corinthian',
      segments: 12,
    });
    // Ionic volutes (approximated as paired scroll discs either side of each capital)
    for (let k = 0; k < 6; k++) {
      const s = 1.1 + ((L - 2.2) * k) / 5;
      for (const o of [-0.62, 0.62]) {
        const p = at(front, s + o, d);
        const disc = new THREE.CylinderGeometry(0.24, 0.24, 0.9, 10);
        const m = new THREE.Matrix4().makeRotationZ(front.ang);
        m.setPosition(p[0], p[1], 1.05 + CH - 0.35);
        batch.addGeometry(stone, disc, m);
        disc.dispose();
      }
    }
    const zE = 1.05 + CH;
    ebox(stone, front, 0, L, -0.2, d + 0.8, zE, zE + 1.6);
    ebox(stone, front, -0.2, L + 0.2, -0.2, d + 1.0, zE + 1.4, zE + 1.75);
    gable(stone, front, -0.2, L + 0.2, zE + 1.75, 3.0, -0.2, d + 1.0);
    // doors behind the portico
    wins(front, 0, L, 1.05, {
      count: 3,
      margin: 2.5,
      width: 1.8,
      height: 4.2,
      head: 'lintel',
      frame: stone,
      sill: stone,
      glass: kit.mat('#3c2c20'),
      bars: 0,
      depth: 0.25,
    });
    // clock tower rising behind the pediment
    {
      const c = at(front, L / 2, -4.2);
      const t = rect(c[0], c[1], front.ang, 6.2, 6.2);
      kit.walls(batch, stone, [[t]], H - 1, H + 8.5);
      kit.cap(batch, lead, [[t]], H + 8.5);
      kit.cornice(batch, stone, t, H + 8.0, { height: 0.5, projection: 0.4 });
      for (const e of edges(t)) {
        const p = at(e, e.len / 2, 0.04);
        const disc = new THREE.CircleGeometry(1.2, 20);
        const m = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(e.dx, e.dy, 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(e.nx, e.ny, 0),
        );
        m.setPosition(p[0], p[1], H + 5.2);
        batch.addGeometry(clockM, disc, m);
        disc.dispose();
        for (const s of [0.4, e.len - 0.4])
          ebox(stone, e, s - 0.4, s + 0.4, 0, 0.2, H - 1, H + 8.0);
      }
      // circular belfry with a ring of columns, then a small cupola and cross
      const z0 = H + 8.5;
      cyl(stone, c[0], c[1], z0, 2.3, 2.3, 6.0, 16);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        cyl(
          stone,
          c[0] + Math.cos(a) * 2.75,
          c[1] + Math.sin(a) * 2.75,
          z0 + 0.3,
          0.24,
          0.22,
          5.2,
          8,
        );
      }
      cyl(stone, c[0], c[1], z0, 3.1, 3.1, 0.35, 16);
      cyl(stone, c[0], c[1], z0 + 5.6, 3.2, 3.2, 0.7, 16);
      cyl(stone, c[0], c[1], z0 + 6.3, 2.2, 2.0, 2.4, 12);
      lathe(
        lead,
        [
          [0.01, 0],
          [2.2, 0],
          [1.9, 1.1],
          [1.1, 2.0],
          [0.35, 2.4],
          [0.01, 2.5],
        ],
        c[0],
        c[1],
        z0 + 8.7,
        16,
      );
      cyl(stone, c[0], c[1], z0 + 11.2, 0.35, 0.15, 1.8, 8);
      kit.box(batch, kit.mat('gold'), c[0], c[1], z0 + 13.0, 0.1, 0.1, 1.2, front.ang);
      kit.box(batch, kit.mat('gold'), c[0], c[1], z0 + 13.75, 0.6, 0.1, 0.1, front.ang);
    }
    g.add(batch.toGroup('st_peters_eaton_square'));
    return g;
  },
};
