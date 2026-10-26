// Newcombe House, 45 Notting Hill Gate (Cotton, Ballard & Blow, part of the late-1950s
// redevelopment of Notting Hill Gate). Twelve-storey post-war office slab at the corner
// of Kensington Church Street, one of the two towers dubbed the "ugly sisters" with
// Campden Hill Towers across the road: a concrete-framed slab with continuous bands of
// windows and spandrel panels above a glazed shop and entrance level.
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
  id: 'newcombe_house',
  name: 'Newcombe House',
  claims: ['ee80d466-2075-41ee-9437-e2953da70eaf'],
  references: [
    {
      title: 'Notting Hill tower rejected - Building',
      url: 'https://building.co.uk/news/notting-hill-tower-rejected/5080969.article',
      used_for:
        "Cotton, Ballard & Blow's 1950s Newcombe House; the 'ugly sisters' with Campden Hill Towers",
    },
    {
      title: 'Squire and Partners Notting Hill office refurb approved - BD Online',
      url: 'https://bdonline.co.uk/news/squire-and-partners-notting-hill-office-refurb-okd-following-sites-eight-year-planning-saga/5127436.article',
      used_for: 'approved refurbishment and two-storey extension of the existing building',
    },
    {
      title:
        'Royal Borough of Kensington and Chelsea recommended to approve replacement for Newcombe House - Building',
      url: 'https://www.building.co.uk/news/notting-hill-tower-set-for-approval-despite-objections/5080598.article',
      used_for: 'site context at Notting Hill Gate / Kensington Church Street',
    },
  ],
  notes:
    'Models the existing slab at the Overture height (39.2 m: 4.4 m ground floor + eleven 3.2 m floors + plant ' +
    'room); the approved Squire & Partners refurbishment and extension and the new low-rise blocks are not ' +
    'shown, as their completion is not confirmed. Window module (1.5 m), spandrel colour and the recessed ' +
    'glazed ground floor are generic for the period, not taken from photographs.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    const conc = kit.mat('#c9c5bb', { roughness: 0.9 });
    const panel = kit.mat('#8f9a9c', { roughness: 0.7 });
    const glass = kit.mat('#34424c', { roughness: 0.12, metalness: 0.4 });
    const mull = kit.mat('#3f4448', { roughness: 0.5, metalness: 0.5 });
    const roofM = kit.mat('#8b8a86');
    const G = 4.4,
      ST = 3.2,
      NF = 11,
      H = G + NF * ST;

    const rec = kit.offsetRing(ring, -1.2);
    kit.walls(batch, glass, [[rec]], 0, G - 0.4, { bay: 1e6 });
    kit.cap(batch, conc, [[ring]], G - 0.4, { down: true });
    for (const e of T.edges(rec))
      for (let s = 1.5; s < e.len; s += 1.8)
        T.ebox(mull, e, s - 0.05, s + 0.05, 0, 0.1, 0, G - 0.4);
    for (const e of T.edges(ring)) {
      if (e.len < 5) continue;
      const n = Math.round(e.len / 6);
      for (let k = 0; k <= n; k++)
        T.ebox(conc, e, (k * e.len) / n - 0.3, (k * e.len) / n + 0.3, -0.9, -0.3, 0, G - 0.4);
    }
    // office floors: window band + spandrel band per storey, framed by end walls
    kit.walls(batch, panel, [[ring]], G - 0.4, H, { bay: 1e6 });
    for (const e of T.edges(ring)) {
      if (e.len < 3) continue;
      const long = e.len > 20;
      for (let f = 0; f < NF; f++) {
        const z = G + f * ST;
        T.ebox(conc, e, 0, e.len, 0, 0.2, z - 0.4, z + 0.05);
        if (long) T.ebox(glass, e, 0.6, e.len - 0.6, 0, 0.05, z + 0.9, z + ST - 0.45);
        else
          kit.windowRow(batch, e.a, e.b, z + 0.9, {
            width: 1.2,
            height: 1.8,
            bay: 3,
            margin: 1.2,
            glass,
            frame: mull,
            bars: 0,
            head: 'none',
          });
        if (long) {
          const n = Math.round((e.len - 1.2) / 1.5);
          for (let k = 0; k <= n; k++) {
            const s = 0.6 + ((e.len - 1.2) * k) / n;
            T.ebox(mull, e, s - 0.04, s + 0.04, 0, 0.12, z + 0.9, z + ST - 0.45);
          }
        }
      }
      // end frames of the slab
      if (long)
        for (const s of [0.3, e.len - 0.3])
          T.ebox(conc, e, s - 0.3, s + 0.3, 0, 0.3, G - 0.4, H + 0.6);
    }
    kit.cap(batch, roofM, [[ring]], H);
    kit.cornice(batch, conc, ring, H, { height: 0.6, projection: 0.15 });
    const F = T.frame(ring);
    const pl = T.rect(F, F.cu - 7, F.cu + 7, F.v0 + 3, F.v1 - 3);
    kit.walls(batch, conc, [[pl]], H, H + 3.4, { bay: 1e6 });
    kit.cap(batch, roofM, [[pl]], H + 3.4);
    for (const e of T.edges(pl))
      for (let s = 0.4; s < e.len; s += 0.4)
        T.ebox(mull, e, s - 0.03, s + 0.03, 0, 0.08, H + 0.5, H + 3.0);
    g.add(batch.toGroup('newcombe_house'));
    return g;
  },
};
