// Leighton House, 12 Holland Park Road (George Aitchison for Frederic Leighton, built
// in stages 1865-95). A two-storey Suffolk red brick house with Caen stone dressings and
// a heavy modillion cornice, whose plain street front hides the Arab Hall (1877): its
// projection to the left (west) carries a Turkish-style tiled dome with a crescent
// finial. The great studio with its north light is on the first floor at the back, and
// the glazed Winter Studio (1889-95) projects at the east end.
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
  id: 'leighton_house',
  name: 'Leighton House',
  claims: ['d55e13ca-0c77-4e83-8684-557adf082917'],
  references: [
    {
      title: 'Leighton House - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=203946',
      used_for:
        'Grade II*, Aitchison 1865-95, red brick with tiled dome on the left projection and modillion cornice to the right',
    },
    {
      title: 'Leighton House - victorianweb.org',
      url: 'https://victorianweb.org/art/architecture/london/72.html',
      used_for: 'Suffolk red brick and Caen stone dressings; plain front, picturesque garden side',
    },
    {
      title: 'Leighton House - Hidden London',
      url: 'https://hidden-london.com/?p=8798',
      used_for: 'dome at one side topped by a crescent, modelled on Arab mosque domes',
    },
    {
      title: "'An Oriental Kiosk': The Building of the 'Arab Hall' - Orientations",
      url: 'https://www.orientations.com.hk/highlights/an-oriental-kiosk-the-building-of-the-arab-hall-at-leighton-house-in-london',
      used_for: 'Arab Hall added 1877',
    },
  ],
  notes:
    'Eaves at 9 m (two tall storeys) instead of the Overture 7.85 m. The Arab Hall projection is placed at the ' +
    'south-west, jagged part of the footprint; its dome profile (springing 9.5 m, apex ~13.5 m) and the tile ' +
    'colour are estimates. Hipped slate roof over the main body only; studio north window, Winter Studio ' +
    'glazing at the east end and window positions are schematic.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    let F = T.frame(ring, Math.atan2(0.5, 0.86));
    const brick = kit.mat('#9b4d37', { roughness: 0.92 });
    const stone = kit.mat('#e0d4b8', { roughness: 0.8 });
    const glass = kit.mat('#2e3a42', { roughness: 0.2, metalness: 0.3 });
    const frame = kit.mat('#efe9dc');
    const slate = kit.mat('slate');
    const tile = kit.mat('#3f7f86', { roughness: 0.5 });
    const gold = kit.mat('gold');
    const EAV = 9;

    kit.walls(batch, brick, [[ring]], 0, EAV, { bay: 1e6 });
    kit.cornice(batch, stone, ring, 0, { height: 0.5, projection: 0.1 });
    kit.cornice(batch, stone, ring, 4.4, { height: 0.3, projection: 0.12 });
    kit.cornice(batch, stone, ring, EAV - 0.6, { height: 0.6, projection: 0.5, steps: 3 });
    kit.cap(batch, kit.mat('#7a7f83'), [[ring]], EAV);
    // modillions under the cornice
    const E = T.edges(ring);
    for (const e of E) {
      if (e.len < 2) continue;
      for (let s = 0.4; s < e.len - 0.2; s += 0.7)
        T.ebox(stone, e, s - 0.1, s + 0.1, 0, 0.45, EAV - 0.9, EAV - 0.6);
    }
    // main roof
    const main = T.rect(F, F.u0 + 6, F.u1 - 3, F.v0 + 4, F.v1 - 1);
    kit.pitchedRoof(batch, slate, brick, main, F.angle, EAV, 3.2, 'hipped', { overhang: 0.2 });
    // chimneys
    for (const [u, v] of [
      [F.u0 + 9, F.v1 - 3],
      [F.u1 - 6, F.v1 - 3],
    ]) {
      T.fbox(brick, F, u, v, EAV, 1.2, 0.8, 4.4);
      T.fbox(stone, F, u, v, EAV + 4.4, 1.4, 1.0, 0.3);
    }
    // windows
    const front = T.facing(E, [0.5, -0.86], 4);
    const back = T.facing(E, [-0.5, 0.86], 4);
    for (const e of E) {
      if (e.len < 3.5) continue;
      const o = {
        glass,
        frame,
        bars: 2,
        bay: 3.2,
        margin: 0.9,
        surround: 0.18,
        surroundMat: stone,
      };
      kit.windowRow(batch, e.a, e.b, 1.0, {
        ...o,
        width: 1.2,
        height: 2.4,
        head: e === front ? 'arch' : 'lintel',
      });
      if (e === back && e.len > 8) {
        // great studio north light
        kit.windowRow(batch, e.a, e.b, 5.0, {
          ...o,
          count: 1,
          width: Math.min(9, e.len * 0.55),
          height: 3.6,
          bars: 5,
          head: 'none',
        });
        const m = T.at(e, e.len / 2, 0);
        T.ebox(glass, e, e.len / 2 - 4.5, e.len / 2 + 4.5, -2, 0.1, EAV, EAV + 0.06);
        void m;
      } else
        kit.windowRow(batch, e.a, e.b, 5.1, { ...o, width: 1.1, height: 2.2, head: 'segment' });
    }
    // studio north-light glazed roof slope
    {
      const sr = T.rect(F, F.cu - 5, F.cu + 5, F.v1 - 4, F.v1 - 0.2);
      kit.pitchedRoof(batch, glass, brick, sr, F.angle, EAV, 1.6, 'gabled', { overhang: 0.1 });
    }
    // Winter Studio: glazed first-floor box at the east end on iron posts
    {
      const u = F.u1 - 2.2;
      T.fbox(glass, F, u, F.cv - 1, 4.5, 4.2, 6, 3.6);
      T.fbox(kit.mat('dark_steel'), F, u, F.cv - 1, 8.1, 4.4, 6.2, 0.25);
    }

    // Arab Hall projection with Turkish tiled dome and crescent finial (south-west)
    const sw = ring.filter((p) => {
      const [u, v] = F.uv(p);
      return u < F.u0 + 8 && v < F.cv;
    });
    const hc = sw.length
      ? [sw.reduce((s, p) => s + p[0], 0) / sw.length, sw.reduce((s, p) => s + p[1], 0) / sw.length]
      : F.w(F.u0 + 4, F.v0 + 4);
    const [hu, hv] = F.uv(hc);
    const HS = 6.4,
      HZ = 9.6;
    const hall = T.rect(F, hu - HS / 2, hu + HS / 2, hv - HS / 2, hv + HS / 2);
    kit.walls(batch, brick, [[hall]], 0, HZ, { bay: 1e6 });
    kit.cornice(batch, stone, hall, HZ - 0.6, { height: 0.6, projection: 0.4, steps: 2 });
    kit.cap(batch, kit.mat('#7a7f83'), [[hall]], HZ);
    for (const e of T.edges(hall))
      kit.windowRow(batch, e.a, e.b, 5.6, {
        count: 2,
        width: 0.9,
        height: 2.0,
        head: 'arch',
        glass,
        frame: stone,
        bars: 0,
        margin: 1.4,
      });
    T.cyl(brick, hc[0], hc[1], HZ, 2.8, 2.8, 1.3, 8);
    T.cyl(stone, hc[0], hc[1], HZ + 1.3, 3.0, 3.0, 0.25, 8);
    T.lathe(
      tile,
      [
        [2.75, 0],
        [2.9, 0.8],
        [2.8, 1.6],
        [2.4, 2.4],
        [1.7, 3.1],
        [0.9, 3.55],
        [0.25, 3.8],
        [0.0, 3.85],
      ],
      hc[0],
      hc[1],
      HZ + 1.55,
      20,
    );
    T.cyl(gold, hc[0], hc[1], HZ + 5.3, 0.08, 0.05, 1.4, 6);
    T.geo(
      gold,
      new THREE.TorusGeometry(0.32, 0.06, 6, 12, Math.PI * 1.4).rotateX(Math.PI / 2),
      hc[0],
      hc[1],
      HZ + 6.95,
      F.angle,
    );

    g.add(batch.toGroup('leighton_house'));
    return g;
  },
};
