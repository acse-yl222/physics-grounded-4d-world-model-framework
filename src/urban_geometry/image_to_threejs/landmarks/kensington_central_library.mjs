// Kensington Central Library, Phillimore Walk / Hornton Street (E. Vincent Harris,
// 1958-60, opened 13 July 1960). Post-war classical public library: steel frame
// clad in hand-made red brick with Bath and Portland stone; rectangular plan with a
// six-bay centre between projecting end pavilions, two storeys over a basement plus
// an attic, Portland stone base, cornice and parapet; the walnut-panelled reference
// library on the first floor. Stone pylons stand either side of the entrance.
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
  id: 'kensington_central_library',
  name: 'Kensington Central Library',
  claims: ['f0820754-c7d6-4b7d-9cbe-d53b54f87d1c'],
  references: [
    {
      title: 'Kensington Central Library Including Adjoining Pylons - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1119724',
      used_for:
        'Grade II*, 1958-60 by E Vincent Harris, steel frame with hand-made brick and Bath/Portland stone, six-bay centre ' +
        'with projecting end pavilions, two storeys over basement and attic, stone base, cornice and parapet, pylons',
    },
    {
      title: 'Kensington Central Library - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Central_Library',
      used_for: 'opening 13 July 1960, location on Phillimore Walk',
    },
    {
      title: 'Vincent Harris - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Vincent_Harris',
      used_for: 'architect and his civic classical style',
    },
  ],
  notes:
    'Height kept near the Overture 15.6 m (5.2 m + 5.6 m storeys, attic, parapet). The main front is taken as ' +
    'the Phillimore Walk side; pavilion projection follows the footprint notches. Window sizes, arched ground ' +
    'floor openings, doorcase, the low hipped slate roof behind the parapet, and the pylon size and the ' +
    'abstracted heraldic beasts on them are estimates.',
  build({ THREE, kit, buildings, scene }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const nb = T.neighbours(scene, [b0.id], b0.c, 120);
    const brick = kit.mat('#8f4a35', { roughness: 0.92 });
    const stone = kit.mat('#ddd5c1', { roughness: 0.8 });
    const glass = kit.mat('#2e3a42', { roughness: 0.2, metalness: 0.3 });
    const white = kit.mat('#efece4');
    const slate = kit.mat('slate');
    const door = kit.mat('#3a2b1f');
    const G1 = 5.2,
      G2 = G1 + 5.6,
      CZ = G2 + 0.9, // cornice top
      AT = CZ + 2.6; // attic parapet top

    kit.walls(batch, brick, [[ring]], 1.2, G2, { bay: 1e6 });
    kit.walls(batch, stone, [[ring]], 0, 1.2, { bay: 1e6 });
    kit.cornice(batch, stone, ring, 0, { height: 1.2, projection: 0.15 });
    kit.cornice(batch, stone, ring, G1 - 0.3, { height: 0.35, projection: 0.12 });
    kit.walls(batch, stone, [[ring]], G2, CZ, { bay: 1e6 });
    kit.cornice(batch, stone, ring, G2 + 0.3, { height: 0.6, projection: 0.55, steps: 2 });
    // attic storey set back slightly, stone parapet
    const att = kit.offsetRing(ring, -0.3);
    kit.walls(batch, brick, [[att]], CZ, AT - 0.8, { bay: 1e6 });
    kit.walls(batch, stone, [[att]], AT - 0.8, AT, { bay: 1e6 });
    kit.cornice(batch, stone, att, AT - 0.25, { height: 0.25, projection: 0.15 });
    kit.cap(batch, kit.mat('#8a8985'), [[att]], AT - 0.6);
    const F = T.frame(ring);
    kit.pitchedRoof(
      batch,
      slate,
      brick,
      T.rect(F, F.u0 + 4, F.u1 - 4, F.v0 + 4, F.v1 - 4),
      F.angle,
      AT - 0.6,
      2.0,
      'hipped',
      { overhang: 0 },
    );

    const E = T.edges(ring);
    const front = T.facing(E, [0.45, -0.89], 25);
    for (const e of E) {
      if (e.len < 3) continue;
      const party = !T.exposed(e, nb);
      if (party) continue;
      const opt = {
        glass,
        frame: white,
        bars: 1,
        margin: 1.0,
        bay: 3.6,
        surround: 0.22,
        surroundMat: stone,
      };
      kit.windowRow(batch, e.a, e.b, 1.6, {
        ...opt,
        width: 1.5,
        height: 3.0,
        head: e === front ? 'arch' : 'lintel',
      });
      kit.windowRow(batch, e.a, e.b, G1 + 0.7, {
        ...opt,
        width: 1.6,
        height: 3.8,
        head: 'pediment',
      });
      kit.windowRow(batch, T.at(e, 0, -0.3), T.at(e, e.len, -0.3), CZ + 0.35, {
        ...opt,
        width: 1.1,
        height: 1.1,
        head: 'none',
        surround: 0,
        bars: 1,
      });
    }
    // corner quoins on every exposed corner
    for (const e of E) {
      if (e.len < 2) continue;
      for (let z = 1.2, k = 0; z < G2 - 0.4; z += 0.6, k++)
        T.ebox(stone, e, 0, k % 2 ? 0.5 : 0.9, -0.02, 0.05, z, z + 0.3);
    }

    // central doorcase on the front and the two pylons
    if (front) {
      const m = front.len / 2;
      T.ebox(stone, front, m - 3.5, m + 3.5, 0, 0.9, 0, G1 + 0.6);
      T.ebox(stone, front, m - 4, m + 4, 0, 1.1, G1 + 0.6, G1 + 1.3);
      T.ebox(door, front, m - 1.5, m + 1.5, 0.9, 0.95, 0.3, 4.0);
      kit.colonnade(
        batch,
        stone,
        T.at(front, m - 2.8, 1.2),
        T.at(front, m + 2.8, 1.2),
        0,
        G1 + 0.6,
        { count: 2, radius: 0.35, capital: 'doric' },
      );
      for (const s of [m - 9, m + 9]) {
        const c = T.at(front, s, 5.5);
        kit.box(batch, stone, c[0], c[1], 0, 1.6, 1.6, 5.6, front.ang);
        kit.box(batch, stone, c[0], c[1], 5.6, 2.0, 2.0, 0.4, front.ang);
        // heraldic beast (lion / unicorn), abstracted: body block and head
        kit.box(batch, stone, c[0], c[1], 6.0, 0.8, 1.5, 1.0, front.ang);
        const h = T.at(front, s, 6.1);
        kit.box(batch, stone, h[0], h[1], 6.8, 0.6, 0.6, 0.8, front.ang);
      }
      kit.cap(
        batch,
        kit.mat('paving'),
        [
          [
            [
              T.at(front, m - 11, 8),
              T.at(front, m + 11, 8),
              T.at(front, m + 11, 0.05),
              T.at(front, m - 11, 0.05),
            ],
          ],
        ],
        0.04,
      );
    }
    g.add(batch.toGroup('kensington_central_library'));
    return g;
  },
};
