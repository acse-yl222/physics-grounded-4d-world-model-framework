// Campden Hill Towers, 112 Notting Hill Gate. 1960s residential tower of the post-war
// Notting Hill Gate redevelopment, rising above the six-lane road opposite Newcombe
// House (together the "ugly sisters"): a nineteen-storey slab of flats over a shop
// frontage on Notting Hill Gate, its long faces banded by continuous concrete balcony
// fronts, with a marble and mosaic lined lobby and rooftop plant.
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
  id: 'campden_hill_towers',
  name: 'Campden Hill Towers',
  claims: ['7e653d9a-578e-4633-b906-285f5a411677'],
  references: [
    {
      title: 'Campden Hill Towers - Buildington',
      url: 'https://www.buildington.co.uk/buildings/2331/england/london-w11/112-notting-hill-gate/campden-hill-towers',
      used_for: 'address 112 Notting Hill Gate W11',
    },
    {
      title: 'Campden Hill Towers - Domus Nova',
      url: 'https://domusnova.com/london-lettings/campden-hill-towers/',
      used_for: '1960s modernist landmark, marble-clad lobby with glass mosaic panels',
    },
    {
      title: 'Notting Hill tower rejected - Building',
      url: 'https://www.building.co.uk/news/notting-hill-tower-rejected/5080969.article',
      used_for: "the two towers dubbed the 'ugly sisters' above the six-lane trunk road",
    },
  ],
  notes:
    'Height and floor count from Overture (61.6 m, 19 floors: 3.2 m shop floor + 18 x 3.2 m + plant). The ' +
    'Overture part raised from 3.2 m along Notting Hill Gate is read as a shop canopy/undercroft. Balcony ' +
    'bands on the two long faces, the window module, the solid gable ends and the plant-room size are ' +
    'assumptions from the general type; the architect is not identified in the sources.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const conc = kit.mat('#cdc8bc', { roughness: 0.9 });
    const concD = kit.mat('#9d998f', { roughness: 0.9 });
    const brick = kit.mat('#7d6a5a', { roughness: 0.9 });
    const glass = kit.mat('#34424c', { roughness: 0.12, metalness: 0.4 });
    const shop = kit.mat('#3b4a54', { roughness: 0.1, metalness: 0.3 });
    const mull = kit.mat('#e6e3dc', { roughness: 0.6 });
    const rail = kit.mat('dark_steel');
    const roofM = kit.mat('#8b8a86');
    const G = 3.2,
      ST = 3.2,
      NF = 18,
      H = G + NF * ST - 3.2; // 57.6 roof, plant to 61.6

    const E = T.edges(ring);
    const longE = E.filter((e) => e.len > 25);
    const shortE = E.filter((e) => e.len <= 25);
    // ground floor shops and canopy
    const rec = kit.offsetRing(ring, -0.8);
    kit.walls(batch, shop, [[rec]], 0, G, { bay: 1e6 });
    kit.cap(batch, concD, [[ring]], G, { down: true });
    for (const e of T.edges(rec))
      for (let s = 0; s < e.len; s += 2.4) T.ebox(mull, e, s - 0.06, s + 0.06, 0, 0.1, 0, G);
    const south = T.facing(E, [0.25, -0.97], 5);
    T.ebox(concD, south, -0.5, south.len + 0.5, 0, 2.5, G - 0.45, G);
    // upper body
    kit.walls(batch, glass, [[kit.offsetRing(ring, -1.3)]], G, H, { bay: 1e6 });
    for (const e of shortE) {
      // solid gable walls (brick-faced) with a single window stack
      T.ebox(brick, e, -1.4, e.len + 1.4, -1.4, 0, G, H);
      T.ebox(glass, e, e.len / 2 - 0.7, e.len / 2 + 0.7, 0, 0.04, G + 0.9, H - 0.4);
    }
    for (const e of longE) {
      for (let f = 0; f < NF - 1; f++) {
        const z = G + f * ST;
        // balcony slab and solid balcony front
        T.ebox(conc, e, 0, e.len, -1.3, 0.05, z - 0.2, z);
        T.ebox(conc, e, 0, e.len, -0.05, 0.08, z, z + 1.0);
        // balcony dividers
        for (let s = 0; s <= e.len; s += e.len / 6)
          T.ebox(concD, e, s - 0.1, s + 0.1, -1.3, 0, z, z + ST - 0.2);
        // windows / doors behind
        const p = T.at(e, 0, -1.3),
          q = T.at(e, e.len, -1.3);
        kit.windowRow(batch, p, q, z + 0.2, {
          width: 1.6,
          height: 2.3,
          bay: 2.2,
          margin: 0.6,
          glass,
          frame: mull,
          bars: 1,
          head: 'none',
          depth: 0.06,
        });
      }
      T.ebox(rail, e, 0, e.len, -0.05, 0.02, H - 0.2, H + 1.0);
    }
    kit.cap(batch, roofM, [[ring]], H);
    kit.cornice(batch, conc, ring, H - 0.3, { height: 0.6, projection: 0.1 });
    // plant room / lift overrun
    const F = T.frame(ring);
    const pl = T.rect(F, F.cu - 8, F.cu + 8, F.v0 + 2.5, F.v1 - 2.5);
    kit.walls(batch, concD, [[pl]], H, b0.h ?? 61.6, { bay: 1e6 });
    kit.cap(batch, roofM, [[pl]], b0.h ?? 61.6);
    g.add(batch.toGroup('campden_hill_towers'));
    return g;
  },
};
