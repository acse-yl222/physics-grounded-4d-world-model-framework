// The Coronet, 103 Notting Hill Gate (W. G. R. Sprague, 1898; cinema 1923-2013,
// theatre again since 2014). Corner theatre of three and four storeys in painted,
// once-rendered stone: a symmetrical nine-bay elevation to Notting Hill Gate under a
// giant order of fluted Composite pilasters, the corner with Hillgate Street turned by
// three round-arched bays and dominated by a tall cupola - a short round tower with
// columns on heavy console brackets, crowned by a dome and the figure on its top.
// Shared local helpers (edge frames, oriented boxes, roofs, spires) for this module.
function tools(THREE, kit, batch) {
  const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r.slice());
  const edges = (r) =>
    r.map((a, k) => {
      const b = r[(k + 1) % r.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        k,
        a,
        b,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
        mid: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
      };
    });
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  // Box along edge e: s0..s1 along it, d0..d1 outward, z0..z1.
  const ebox = (mat, e, s0, s1, d0, d1, z0, z1, color) => {
    const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang, color);
  };
  // Oriented frame of a ring: absolute (u, v) along / across `angle`.
  const frame = (ring, angle) => {
    const a = angle ?? kit.ringFrame(ring).angle;
    const ex = kit.orientedExtent(ring, a);
    const w = (u, v) => {
      const p = ex.at(u, v, 0);
      return [p[0], p[1]];
    };
    return {
      ...ex,
      angle: a,
      w,
      cu: (ex.u0 + ex.u1) / 2,
      cv: (ex.v0 + ex.v1) / 2,
      L: ex.u1 - ex.u0,
      W: ex.v1 - ex.v0,
      uv: (p) => [p[0] * ex.c + p[1] * ex.s, -p[0] * ex.s + p[1] * ex.c],
    };
  };
  const rect = (F, u0, u1, v0, v1) => [F.w(u0, v0), F.w(u1, v0), F.w(u1, v1), F.w(u0, v1)];
  const fbox = (mat, F, u, v, z0, lu, lv, h, color) => {
    const p = F.w(u, v);
    kit.box(batch, mat, p[0], p[1], z0, lu, lv, h, F.angle, color);
  };
  const geo = (mat, g, x, y, z, rz = 0, color) => {
    batch.addGeometry(mat, g, new THREE.Matrix4().makeRotationZ(rz).setPosition(x, y, z), color);
    g.dispose();
  };
  const lathe = (mat, prof, x, y, z, seg = 24) =>
    geo(
      mat,
      new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2),
      x,
      y,
      z,
    );
  // Pyramid / cone with `sides` faces, base radius r (to the corners), apex at z + h.
  const spire = (mat, x, y, z, r, h, sides = 8, rot = 0) =>
    geo(
      mat,
      new THREE.ConeGeometry(r, h, sides, 1, true).rotateX(Math.PI / 2),
      x,
      y,
      z + h / 2,
      rot,
    );
  const cyl = (mat, x, y, z, r0, r1, h, seg = 16) =>
    geo(mat, new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2), x, y, z + h / 2);
  const prism = (mat, ring, z0, z1, top = mat) => {
    kit.walls(batch, mat, [[ring]], z0, z1, { bay: 1e6 });
    kit.cap(batch, top, [[ring]], z1);
  };
  // Point-in-ring test.
  const inside = (p, ring) => {
    let c = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i],
        [xj, yj] = ring[j];
      if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  };
  // Edge facing direction (unit vector) best: max dot of outward normal, weighted by length.
  const facing = (E, dir, minLen = 3) =>
    E.filter((e) => e.len >= minLen).sort(
      (p, q) => q.nx * dir[0] + q.ny * dir[1] - (p.nx * dir[0] + p.ny * dir[1]),
    )[0];
  // Neighbouring footprints (outer rings) within R of c, excluding the claimed ids.
  const neighbours = (scene, ids, c, R = 150) =>
    (scene?.buildings ?? [])
      .filter((b) => !ids.includes(b.id) && Math.hypot(b.c[0] - c[0], b.c[1] - c[1]) < R)
      .map((b) => b.polys[0][0]);
  // True when the ground just outside edge e is not covered by a neighbour (street / yard face).
  const exposed = (e, rings, d = 2.0) =>
    [0.2, 0.5, 0.8].filter((t) => {
      const p = at(e, e.len * t, d);
      return !rings.some((r) => inside(p, r));
    }).length >= 2;
  return {
    neighbours,
    exposed,
    ccw,
    edges,
    at,
    ebox,
    frame,
    rect,
    fbox,
    geo,
    lathe,
    spire,
    cyl,
    prism,
    inside,
    facing,
  };
}
export default {
  id: 'coronet_theatre',
  name: 'The Coronet Theatre',
  claims: ['46881efd-b826-4857-acc1-908c09a37f8f'],
  references: [
    {
      title: 'Coronet Cinema - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101227644-coronet-cinema-campden-ward',
      used_for:
        'Sprague 1898; painted once-rendered stone, three and four storeys, giant fluted Composite pilasters, nine-bay ' +
        'elevation, three round-arched corner bays, tall corner cupola with columns on console brackets',
    },
    {
      title: 'Coronet Theatre, Notting Hill - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Coronet_Theatre,_Notting_Hill',
      used_for: 'dates of theatre and cinema use',
    },
    {
      title: 'Coronet Theatre - Cinema Treasures',
      url: 'https://www.cinematreasures.org/theaters/1463',
      used_for:
        "statue on the dome: Gavin Turk's 'The Spirit of Painting' replacing the lost winged figure",
    },
    {
      title: 'Coronet Theatre - Theatres Trust database',
      url: 'https://database.theatrestrust.org.uk/resources/theatres/show/440',
      used_for: 'short round corner tower crowned by a dome',
    },
  ],
  notes:
    'Front parapet at 15 m and the rear stage house at the Overture 13.6 m; the cupola follows the Overture ' +
    'round part (radius ~3.6 m) with the drum to 20 m and the dome to ~24 m (estimated). Pilaster rhythm is an ' +
    'even nine-bay split of the Notting Hill Gate front; the statue is a simple standing figure. Painted stone ' +
    'colour (cream) and the canopy over the entrance are assumptions.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const cream = kit.mat('#ece2c8', { roughness: 0.75 });
    const creamD = kit.mat('#d8cba9', { roughness: 0.8 });
    const glass = kit.mat('#2c363e', { roughness: 0.2, metalness: 0.3 });
    const white = kit.mat('white');
    const lead = kit.mat('#5f6a6c', { roughness: 0.6, metalness: 0.3 });
    const slate = kit.mat('slate');
    const door = kit.mat('#3a2a20');
    const bronze = kit.mat('bronze');
    const HF = 15,
      G1 = 4.6;

    kit.walls(batch, cream, [[ring]], 0, HF, { bay: 1e6 });
    kit.cornice(batch, creamD, ring, 0, { height: 0.6, projection: 0.1 });
    kit.cornice(batch, creamD, ring, G1, { height: 0.5, projection: 0.25 });
    kit.cornice(batch, cream, ring, HF - 2.6, { height: 0.8, projection: 0.6, steps: 3 });
    kit.cornice(batch, creamD, ring, HF - 0.3, { height: 0.3, projection: 0.15 });
    kit.cap(batch, kit.mat('#7d8184'), [[ring]], HF);
    // auditorium / stage-house roof
    const F = T.frame(ring);
    kit.pitchedRoof(
      batch,
      slate,
      cream,
      T.rect(F, F.u0 + 4, F.u1 - 9, F.v0 + 3, F.v1 - 4),
      F.angle,
      HF,
      3.5,
      'hipped',
      { overhang: 0 },
    );

    const E = T.edges(ring);
    const front = T.facing(E, [-0.25, 0.97], 12);
    const side = T.facing(E, [0.97, 0.25], 8);
    for (const e of [front, side]) {
      const n = e === front ? 9 : Math.max(3, Math.round(e.len / 3.4));
      const bw = e.len / n;
      for (let k = 0; k <= n; k++) {
        const s = k * bw;
        // giant fluted pilasters from the first floor to the entablature
        T.ebox(cream, e, s - 0.35, s + 0.35, 0, 0.35, G1 + 0.5, HF - 2.6);
        for (const d of [-0.18, 0, 0.18])
          T.ebox(creamD, e, s + d - 0.03, s + d + 0.03, 0.35, 0.39, G1 + 0.9, HF - 3.2);
        T.ebox(creamD, e, s - 0.5, s + 0.5, 0, 0.5, HF - 3.2, HF - 2.6); // capital
        T.ebox(creamD, e, s - 0.45, s + 0.45, 0, 0.45, G1 + 0.5, G1 + 1.0); // base
      }
      for (let k = 0; k < n; k++) {
        const a = T.at(e, k * bw),
          b = T.at(e, (k + 1) * bw);
        const mid = e === front && k === 4;
        kit.windowRow(batch, a, b, G1 + 1.4, {
          count: 1,
          width: bw * 0.45,
          height: 2.6,
          glass,
          frame: white,
          bars: 1,
          head: mid ? 'pediment' : 'segment',
          margin: 0,
          surround: 0.15,
          surroundMat: creamD,
        });
        kit.windowRow(batch, a, b, G1 + 4.8, {
          count: 1,
          width: bw * 0.4,
          height: 1.8,
          glass,
          frame: white,
          bars: 1,
          head: 'none',
          margin: 0,
        });
        // ground floor: arched entrances and openings
        kit.windowRow(batch, a, b, 0.6, {
          count: 1,
          width: bw * 0.6,
          height: 3.2,
          glass: mid || k === 3 || k === 5 ? door : glass,
          frame: bronze,
          bars: 1,
          head: 'arch',
          margin: 0,
        });
      }
      if (e === front) {
        // canopy over the entrance bays
        T.ebox(creamD, e, 3 * bw, 6 * bw, 0, 2.2, G1 - 0.6, G1 - 0.2);
        T.ebox(bronze, e, 3 * bw, 6 * bw, 2.1, 2.25, G1 - 0.9, G1 - 0.2);
      }
      // balustraded parapet over the front
      kit.balustrade(batch, cream, [T.at(e, 0.2, 0.1), T.at(e, e.len - 0.2, 0.1)], HF, {
        height: 0.9,
        spacing: 0.32,
      });
    }

    // corner cupola on the round part
    const part = (b0.parts ?? [])[0];
    const pr = part ? T.ccw(part.polys[0][0]) : null;
    const c = pr
      ? [pr.reduce((s, p) => s + p[0], 0) / pr.length, pr.reduce((s, p) => s + p[1], 0) / pr.length]
      : F.w(F.u1 - 4, F.v1 - 4);
    const R = pr ? Math.max(...pr.map((p) => Math.hypot(p[0] - c[0], p[1] - c[1]))) : 3.6;
    // three arched corner bays rising through the facade, round tower above the parapet
    T.cyl(cream, c[0], c[1], 0, R, R, HF + 0.5, 24);
    kit.cornice(
      batch,
      creamD,
      Array.from({ length: 24 }, (_, k) => [
        c[0] + R * Math.cos((k / 24) * 6.283),
        c[1] + R * Math.sin((k / 24) * 6.283),
      ]),
      HF - 2.6,
      { height: 0.8, projection: 0.5, steps: 2 },
    );
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + F.angle;
      const p = [c[0] + Math.cos(a) * (R + 0.02), c[1] + Math.sin(a) * (R + 0.02)];
      kit.box(batch, glass, p[0], p[1], G1 + 1.4, 0.06, 1.4, 5.4, a);
      kit.box(batch, glass, p[0], p[1], 0.6, 0.06, 1.6, 3.2, a);
    }
    const RT = R * 0.82,
      Z0 = HF + 0.5,
      Z1 = Z0 + 4.6;
    T.cyl(cream, c[0], c[1], Z0, RT, RT, Z1 - Z0, 24);
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2 + F.angle;
      const p = [c[0] + Math.cos(a) * (RT + 0.45), c[1] + Math.sin(a) * (RT + 0.45)];
      // columns standing on heavy console brackets
      kit.box(batch, creamD, p[0], p[1], Z0 - 1.2, 0.7, 0.7, 1.4, a);
      T.cyl(cream, p[0], p[1], Z0 + 0.2, 0.22, 0.2, Z1 - Z0 - 0.6, 10);
      const q = [c[0] + Math.cos(a + 0.39) * (RT + 0.02), c[1] + Math.sin(a + 0.39) * (RT + 0.02)];
      kit.box(batch, glass, q[0], q[1], Z0 + 1.0, 0.06, 0.9, 2.4, a + 0.39);
    }
    T.cyl(creamD, c[0], c[1], Z1 - 0.4, RT + 0.85, RT + 0.85, 0.7, 24);
    T.lathe(
      lead,
      [
        [RT + 0.3, 0],
        [RT + 0.25, 0.5],
        [RT * 0.9, 1.6],
        [RT * 0.6, 2.7],
        [RT * 0.25, 3.3],
        [0, 3.45],
      ],
      c[0],
      c[1],
      Z1 + 0.3,
      24,
    );
    T.cyl(creamD, c[0], c[1], Z1 + 3.6, 0.45, 0.35, 0.6, 10);
    // standing figure on the dome
    T.cyl(kit.mat('#c8c2b4'), c[0], c[1], Z1 + 4.2, 0.22, 0.28, 1.4, 8);
    T.lathe(
      kit.mat('#c8c2b4'),
      [
        [0, 0],
        [0.16, 0.05],
        [0.18, 0.2],
        [0.12, 0.35],
        [0, 0.4],
      ],
      c[0],
      c[1],
      Z1 + 5.6,
      8,
    );
    g.add(batch.toGroup('coronet_theatre'));
    return g;
  },
};
