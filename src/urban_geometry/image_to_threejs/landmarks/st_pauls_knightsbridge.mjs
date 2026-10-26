// St Paul's Church, Knightsbridge, 32a Wilton Place (Thomas Cundy the younger, 1840-43;
// chancel lengthened by R. J. Withers 1871-2 and by Bodley 1892, side chapel by Blomfield
// 1889). Grade II*. Perpendicular Gothic in yellow brick with Bath stone dressings, with a
// centrally placed western tower (with clock) on Wilton Place.
export default {
  id: 'st_pauls_knightsbridge',
  name: "St Paul's Knightsbridge",
  claims: ['71632c3f-9c1c-4cc0-aeb9-c9988e4a6ec9'],
  references: [
    {
      title: "St Paul's Church, Knightsbridge - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Paul%27s_Church,_Knightsbridge',
      used_for: 'Thomas Cundy the younger, 1843, Grade II*, 32a Wilton Place',
    },
    {
      title: 'Church of St Paul - Historic England list entry 1066084',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1066084',
      used_for:
        'yellow brick, Bath stone dressings, Perpendicular Gothic, centrally placed western tower with clock; later chancel and chapel',
    },
    {
      title: 'St Paul, Wilton Place, Knightsbridge - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2013/02/03/st-paul-wilton-place-knightsbridge/',
      used_for: 'Withers and Bodley chancel extensions, Blomfield side chapel',
    },
  ],
  notes:
    'Tower size (6.5 m square) and height (~29 m to the pinnacle tops), the pinnacles, the nave window count ' +
    'and buttress rhythm, the clerestory-less single roof over nave and aisles, and roof pitch are ' +
    'estimates; the Overture 11.5 m is used for the nave walls. Tower placed at the west (Wilton Place) end ' +
    'as the listing describes.',
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
    const brick = kit.mat('#c9b07c', { roughness: 0.9 });
    const bath = kit.mat('#dcc99a', { roughness: 0.8 });
    const slate = kit.mat('#525960', { roughness: 0.75 });
    const glass = kit.mat('#3a4651', { roughness: 0.2, metalness: 0.25 });
    const lead = kit.mat('lead');
    const clock = kit.paintedMaterial('st_pauls_knightsbridge:clock', 128, 128, (c, w) => {
      c.fillStyle = '#1d2a3a';
      c.beginPath();
      c.arc(w / 2, w / 2, w / 2 - 2, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#d6b04c';
      c.lineWidth = 5;
      c.stroke();
      c.fillStyle = '#d6b04c';
      for (let k = 0; k < 12; k++) {
        const a = (k * Math.PI) / 6;
        c.fillRect(w / 2 + Math.cos(a) * 48 - 3, w / 2 + Math.sin(a) * 48 - 3, 6, 6);
      }
      c.strokeStyle = '#d6b04c';
      c.lineWidth = 4;
      c.beginPath();
      c.moveTo(w / 2, w / 2);
      c.lineTo(w / 2, 22);
      c.moveTo(w / 2, w / 2);
      c.lineTo(w / 2 + 30, w / 2 + 10);
      c.stroke();
    });

    const b = buildings[0];
    const ring = ccw(b.polys[0][0]);
    const fr = kit.ringFrame(ring);
    const ux = Math.cos(fr.angle),
      uy = Math.sin(fr.angle);
    // ensure the axis points east (towards the chancel)
    const dir = ux >= 0 ? 1 : -1;
    const ax = ux * dir,
      ay = uy * dir,
      ang = Math.atan2(ay, ax);
    const P = (u, v) => [fr.cx + ax * u - ay * v, fr.cy + ay * u + ax * v];
    const L = fr.length,
      W = fr.width;
    const H = b.h; // nave wall top
    // body: brick walls with stone plinth, parapet and coping
    kit.walls(batch, brick, [[ring]], 0, H);
    kit.cornice(batch, bath, ring, 0, { height: 0.6, projection: 0.15 });
    kit.cornice(batch, bath, ring, H - 0.5, { height: 0.5, projection: 0.25 });
    kit.cap(batch, lead, [[ring]], H - 0.3);
    // pitched slate roof over the main rectangle
    const body = rect(fr.cx + ax * 3, fr.cy + ay * 3, ang, L - 8, W - 1.5);
    kit.pitchedRoof(batch, slate, brick, body, ang, H - 0.3, W * 0.28, 'gabled', { overhang: 0.2 });
    // buttresses and tall Perpendicular windows on the long sides
    for (const e of edges(ring)) {
      if (e.len < 8) continue;
      const along = Math.abs(e.dx * ax + e.dy * ay) > 0.8;
      if (along) {
        const nb = Math.round(e.len / 5.2);
        for (let k = 0; k <= nb; k++) {
          const s = (k * e.len) / nb;
          ebox(bath, e, Math.max(0, s - 0.4), Math.min(e.len, s + 0.4), 0, 0.7, 0, H - 1.2);
          ebox(bath, e, Math.max(0, s - 0.3), Math.min(e.len, s + 0.3), 0, 0.5, H - 1.2, H + 1.4);
        }
        wins(e, 0, e.len, 2.4, {
          width: 2.2,
          height: H - 5.6,
          count: nb,
          margin: 0,
          head: 'arch',
          frame: bath,
          sill: bath,
          glass,
          bars: 2,
          depth: 0.16,
        });
      } else if (facing(e, ax, ay) > 0.7) {
        // east window
        wins(e, 0, e.len, 3.0, {
          width: Math.min(6, e.len - 3),
          height: H - 4.2,
          count: 1,
          margin: 1,
          head: 'arch',
          frame: bath,
          sill: bath,
          glass,
          bars: 3,
          depth: 0.2,
        });
      }
    }
    // west tower
    const tw = 6.5,
      TH = 25.5;
    const tc = P(-L / 2 + tw / 2 - 1.5, 0);
    const tower = rect(tc[0], tc[1], ang, tw, tw);
    kit.walls(batch, brick, [[tower]], 0, TH);
    kit.cap(batch, lead, [[tower]], TH);
    kit.cornice(batch, bath, tower, 0, { height: 0.8, projection: 0.2 });
    for (const z of [H - 0.5, H + 6.5])
      kit.cornice(batch, bath, tower, z, { height: 0.4, projection: 0.15 });
    kit.cornice(batch, bath, tower, TH - 1.4, { height: 0.6, projection: 0.35 });
    // battlemented parapet
    for (const e of edges(tower)) {
      for (let k = 0; k < 5; k++)
        ebox(bath, e, 0.2 + k * 1.3, 0.85 + k * 1.3, -0.3, 0.1, TH, TH + 0.9);
      // corner pinnacles / buttresses
      ebox(bath, e, -0.5, 0.5, 0, 0.5, 0, TH - 1.4);
      const p = at(e, 0, 0.1);
      cyl(bath, p[0], p[1], TH, 0.45, 0.45, 1.2, 8);
      cyl(bath, p[0], p[1], TH + 1.2, 0.45, 0.04, 2.6, 8);
      // belfry openings and clock
      wins(e, 0, e.len, H + 7.4, {
        width: 1.1,
        height: 3.4,
        count: 2,
        margin: 1.1,
        head: 'arch',
        frame: bath,
        sill: bath,
        glass: kit.mat('#1c2025'),
        bars: 1,
        depth: 0.2,
      });
      const cpos = at(e, e.len / 2, 0.06);
      const disc = new THREE.CircleGeometry(1.05, 20);
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m.setPosition(cpos[0], cpos[1], H + 4.0);
      batch.addGeometry(clock, disc, m);
      disc.dispose();
      wins(e, 0, e.len, H + 0.6, {
        width: 0.8,
        height: 1.6,
        count: 1,
        margin: 2,
        head: 'arch',
        frame: bath,
        sill: bath,
        glass,
        bars: 0,
      });
    }
    // west door in the tower
    {
      const e = edges(tower).reduce((p, q) =>
        q.nx * -ax + q.ny * -ay > p.nx * -ax + p.ny * -ay ? q : p,
      );
      wins(e, 0, e.len, 0.2, {
        width: 2.2,
        height: 3.6,
        count: 1,
        margin: 2,
        head: 'arch',
        frame: bath,
        sill: bath,
        glass: kit.mat('#4a3424'),
        bars: 0,
        depth: 0.25,
      });
      wins(e, 0, e.len, 5.2, {
        width: 2.6,
        height: 4.4,
        count: 1,
        margin: 2,
        head: 'arch',
        frame: bath,
        sill: bath,
        glass,
        bars: 2,
        depth: 0.2,
      });
    }
    g.add(batch.toGroup('st_pauls_knightsbridge'));
    return g;
  },
};
