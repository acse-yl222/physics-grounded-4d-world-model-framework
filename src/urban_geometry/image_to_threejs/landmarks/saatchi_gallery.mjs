// Saatchi Gallery, Duke of York's Headquarters, King's Road, Chelsea (John Sanders, 1801-03,
// built as the Royal Military Asylum for soldiers' children; gallery since 2008).
// Grade II*. Long yellow-brick range facing the lawn, with a stone pedimented Roman Doric
// tetrastyle portico at the centre.
export default {
  id: 'saatchi_gallery',
  name: "Saatchi Gallery (Duke of York's Headquarters)",
  claims: ['dc09f143-ed44-4f72-9d02-08614e1c398d'],
  references: [
    {
      title: "Duke of York's Headquarters - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Duke_of_York%27s_Headquarters',
      used_for: 'John Sanders 1801, Royal Military Asylum, now the Saatchi Gallery',
    },
    {
      title: "Duke of York's Headquarters - RBKC listed buildings",
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=420754',
      used_for: 'Grade II*; yellow brick with stone pedimented Roman Doric tetrastyle portico',
    },
    {
      title: "Duke of York's Barracks, Chelsea: the entrance portico - RIBApix",
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/duke-of-yorks-barracks-chelsea-london-the-entrance-portico/posterid/RIBA58400.html',
      used_for: 'central entrance portico on the main front',
    },
    {
      title: 'John Sanders (architect) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/John_Sanders_(architect)',
      used_for: 'building dates 1801-03, Saatchi Gallery',
    },
  ],
  notes:
    'Wing height 11.5 m (three storeys, Overture 10.4 m) and a raised 14 m centre block are estimates; the ' +
    'portico is drawn projecting from the small forward break in the footprint on the south-west front. ' +
    'Window counts follow a 3.4 m bay; parapet, hipped slate roofs and the gallery signage are generic.',
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
    const brick = kit.mat('#c4ab7c', { roughness: 0.9 });
    const stone = kit.mat('#e3dccb', { roughness: 0.8 });
    const slate = kit.mat('#545b62', { roughness: 0.75 });
    const glass = kit.mat('#2e3a43', { roughness: 0.15, metalness: 0.3 });
    const frame = kit.mat('#f6f5f0');
    const roofM = kit.mat('#7d7f80');
    const ring = ccw(buildings[0].polys[0][0]);
    const H = 11.5;
    kit.walls(batch, brick, [[ring]], 0, H);
    kit.cap(batch, roofM, [[ring]], H - 0.2);
    kit.cornice(batch, stone, ring, 0, { height: 0.5, projection: 0.12 });
    kit.cornice(batch, stone, ring, 3.9, { height: 0.25, projection: 0.08 });
    kit.cornice(batch, stone, ring, H - 1.2, { height: 0.5, projection: 0.35 });
    kit.cornice(batch, stone, ring, H - 0.15, { height: 0.15, projection: 0.06 });
    const E = edges(ring);
    for (const e of E) {
      if (e.len < 5) continue;
      const o = { bay: 3.4, margin: 1.2, frame, sill: stone, glass, bars: 2, depth: 0.12 };
      wins(e, 0, e.len, 0.9, { ...o, width: 1.3, height: 2.4, head: 'arch' });
      wins(e, 0, e.len, 4.7, { ...o, width: 1.3, height: 2.5, head: 'lintel' });
      wins(e, 0, e.len, 8.0, { ...o, width: 1.3, height: 1.6, head: 'none', bars: 1 });
    }
    // front: the SW-facing edges; portico on the short forward break nearest the centre
    const sw = [-0.6, -0.8];
    const fronts = E.filter((e) => facing(e, ...sw) > 0.9);
    const fwd = (e) => e.mx * sw[0] + e.my * sw[1];
    const portE = fronts.filter((e) => e.len > 8).sort((p, q) => fwd(q) - fwd(p))[0];
    // raised centre block with a hipped slate roof
    {
      const c = at(portE, portE.len / 2, -9);
      const cb = rect(c[0], c[1], portE.ang, portE.len + 4, 16);
      kit.walls(batch, brick, [[cb]], H - 0.2, 14);
      kit.cornice(batch, stone, cb, 13.4, { height: 0.6, projection: 0.4 });
      kit.pitchedRoof(batch, slate, brick, cb, portE.ang, 14, 3.2, 'hipped', { overhang: 0.2 });
      for (const e of edges(cb))
        if (e.len > 10)
          wins(e, 0, e.len, H + 0.2, {
            bay: 3.4,
            margin: 1.5,
            width: 1.1,
            height: 1.4,
            head: 'none',
            frame,
            sill: stone,
            glass,
            bars: 1,
          });
    }
    // tetrastyle Roman Doric portico with pediment
    {
      const e = portE,
        sm = e.len / 2,
        half = 6.8,
        d = 3.2,
        CH = 9.0;
      ebox(stone, e, sm - half - 0.5, sm + half + 0.5, -0.5, d + 1.0, 0, 0.45);
      ebox(stone, e, sm - half - 0.3, sm + half + 0.3, -0.5, d + 0.6, 0.45, 0.9);
      kit.colonnade(batch, stone, at(e, sm - half + 0.9, d), at(e, sm + half - 0.9, d), 0.9, CH, {
        count: 4,
        radius: 0.6,
        capital: 'doric',
      });
      // antae against the wall
      for (const s of [sm - half + 0.6, sm + half - 0.6])
        ebox(stone, e, s - 0.5, s + 0.5, 0, 0.35, 0.9, 0.9 + CH);
      const zE = 0.9 + CH;
      ebox(stone, e, sm - half, sm + half, -0.3, d + 0.8, zE, zE + 1.5); // entablature
      ebox(stone, e, sm - half - 0.2, sm + half + 0.2, -0.3, d + 1.0, zE + 1.3, zE + 1.6);
      gable(stone, e, sm - half - 0.2, sm + half + 0.2, zE + 1.6, 2.6, -0.3, d + 1.0);
      // roof of the portico (lead) between pediment and wall
      ebox(kit.mat('lead'), e, sm - half, sm + half, -0.3, d + 0.8, zE + 1.5, zE + 1.62);
      // doors
      wins(e, sm - 4, sm + 4, 0.9, {
        width: 1.9,
        height: 3.6,
        count: 1,
        margin: 0.4,
        head: 'arch',
        frame,
        sill: stone,
        glass: kit.mat('#2b2b2b'),
        bars: 0,
        depth: 0.2,
      });
      // gallery banner
      const sign = kit.paintedMaterial('saatchi:sign', 512, 64, (c, w, h) => {
        c.fillStyle = '#e3dccb';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#2a2a2a';
        c.font = '34px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('SAATCHI GALLERY', w / 2, h / 2 + 2);
      });
      const a = at(e, sm - 4.5, d + 0.82),
        b = at(e, sm + 4.5, d + 0.82);
      batch.quad(
        sign,
        [a[0], a[1], zE + 0.3],
        [b[0], b[1], zE + 0.3],
        [b[0], b[1], zE + 1.2],
        [a[0], a[1], zE + 1.2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // hipped slate roofs over the long wings (behind the parapet)
    for (const e of fronts.filter((q) => q.len > 15 && q !== portE)) {
      const c = at(e, e.len / 2, -7);
      kit.pitchedRoof(
        batch,
        slate,
        brick,
        rect(c[0], c[1], e.ang, e.len - 4, 12),
        e.ang,
        H - 0.2,
        2.6,
        'hipped',
        { overhang: 0 },
      );
    }
    // chimney stacks
    for (const e of fronts)
      for (let s = 6; s < e.len - 4; s += 13)
        ebox(brick, e, s - 0.8, s + 0.8, -8, -6.8, H, H + 4.2);
    g.add(batch.toGroup('saatchi_gallery'));
    return g;
  },
};
