// Linley Sambourne House, 18 Stafford Terrace (c. 1870; home of the Punch cartoonist
// Edward Linley Sambourne from 1875). Mid-terrace Italianate townhouse of three storeys
// over a basement with an attic: London stock brick with stucco dressings, a two-bay
// front of unequal widths, the narrower bay holding the entrance up a short flight of
// steps flanked by urns inside a rusticated porch with Doric half-columns, a canted
// bay window rising from the basement to the first floor in the wider bay, cornice and
// balustrade, and a slated mansard with segmental-headed dormers.
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
  id: 'linley_sambourne_house',
  name: 'Linley Sambourne House',
  claims: ['24f4e68d-7188-482b-b8df-16a98e433058'],
  references: [
    {
      title: 'Linley Sambourne House - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101409861-linley-sambourne-house-campden-ward',
      used_for:
        'three storeys plus basement and attic, stock brick and stucco, slated mansard, two unequal bays, porch with rustication ' +
        'and Doric half-columns, steps with urns, polygonal bay basement to first floor, cornice and balustrade, segmental dormers',
    },
    {
      title: 'Stafford Terrace - victorianweb.org',
      url: 'https://victorianweb.org/victorian/art/architecture/homes/40.html',
      used_for: 'big mid-Victorian brick townhouses with Italianate stucco trim',
    },
    {
      title: 'Linley Sambourne House - Atlas Obscura',
      url: 'https://wWw.atlasobscura.Com/places/linley-sambourne-house',
      used_for: 'house museum of the Sambourne family',
    },
  ],
  notes:
    'Front taken as the north-north-west short edge on Stafford Terrace. Storey heights (raised ground 3.6 m ' +
    'from 1.2 m, first 3.4 m, second 2.9 m), the 2.5 m entrance bay, bay-window projection (1.1 m) and ' +
    'mansard pitch are estimated. The rear is plain brick; the basement area is shown as a sunken strip with ' +
    'railings.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    const E = T.edges(ring);
    const front = T.facing(E, [-0.5, 0.86], 2);
    const back = E[(front.k + 2) % 4];
    const stock = kit.mat('#b49d78', { roughness: 0.92 });
    const stucco = kit.mat('#ece6d8', { roughness: 0.75 });
    const glass = kit.mat('#2b363e', { roughness: 0.2, metalness: 0.3 });
    const white = kit.mat('white');
    const slate = kit.mat('slate');
    const black = kit.mat('black');
    const door = kit.mat('#1f2a24');
    const lead = kit.mat('lead');
    const Z0 = 1.2,
      Z1 = Z0 + 3.6,
      Z2 = Z1 + 3.4,
      Z3 = Z2 + 2.9; // 11.1 cornice

    kit.walls(batch, stock, [[ring]], 0, Z3, { bay: 1e6 });
    kit.cornice(batch, stucco, ring, Z3 - 0.5, { height: 0.5, projection: 0.4, steps: 2 });
    // front: stucco ground floor, string courses, balustrade
    const W = front.len;
    T.ebox(stucco, front, 0, W, 0, 0.05, 0, Z1);
    for (let z = 0.3; z < Z1; z += 0.45) T.ebox(stucco, front, 0, W, 0.05, 0.08, z, z + 0.05); // channelled rustication
    T.ebox(stucco, front, 0, W, 0, 0.18, Z1, Z1 + 0.35);
    T.ebox(stucco, front, 0, W, 0, 0.12, Z2 - 0.1, Z2 + 0.15);
    kit.balustrade(batch, stucco, [T.at(front, 0.1, 0.25), T.at(front, W - 0.1, 0.25)], Z3, {
      height: 0.85,
      spacing: 0.3,
    });
    // narrower entrance bay on the left, wider bay with canted window on the right
    const EB = 2.5;
    // porch: rusticated piers, Doric half-columns, entablature
    T.ebox(stucco, front, 0.2, EB - 0.1, 0, 0.9, Z0, Z1 + 0.2);
    T.ebox(stucco, front, 0.1, EB, 0, 1.05, Z1 + 0.2, Z1 + 0.6);
    T.ebox(door, front, 0.75, EB - 0.65, 0.88, 0.95, Z0, Z0 + 2.6);
    for (const s of [0.45, EB - 0.35]) {
      const c = T.at(front, s, 0.95);
      T.cyl(stucco, c[0], c[1], Z0, 0.2, 0.17, Z1 - Z0 + 0.2, 10);
    }
    // steps with urns
    for (let k = 0; k < 5; k++)
      T.ebox(stucco, front, 0.4, EB - 0.3, 0.9 + k * 0.3, 1.2 + k * 0.3, 0, Z0 - k * 0.24);
    for (const s of [0.45, EB - 0.35]) {
      const c = T.at(front, s, 2.3);
      T.lathe(
        stucco,
        [
          [0.0, 0],
          [0.18, 0],
          [0.12, 0.2],
          [0.28, 0.45],
          [0.22, 0.7],
          [0.0, 0.72],
        ],
        c[0],
        c[1],
        Z0,
        10,
      );
    }
    // canted bay window, basement to first floor
    {
      const s0 = EB + 0.6,
        s1 = W - 0.4,
        P = 1.1;
      const a = T.at(front, s0, 0),
        b = T.at(front, s0 + 0.7, P),
        c = T.at(front, s1 - 0.7, P),
        d = T.at(front, s1, 0);
      const bay = [d, c, b, a];
      const br = T.ccw(bay);
      kit.walls(batch, stucco, [[br]], -0.01, Z2 - 0.2, { bay: 1e6 });
      kit.cap(batch, stucco, [[br]], Z2 - 0.2);
      kit.cornice(batch, stucco, br, Z2 - 0.5, { height: 0.3, projection: 0.15 });
      for (const z of [Z0 + 0.9, Z1 + 0.6]) {
        for (const [p, q] of [
          [a, b],
          [b, c],
          [c, d],
        ]) {
          kit.windowRow(batch, p, q, z, {
            count: 1,
            width: Math.hypot(q[0] - p[0], q[1] - p[1]) * 0.62,
            height: 2.3,
            glass,
            frame: white,
            bars: 1,
            head: 'none',
            margin: 0.1,
          });
        }
      }
      // fern case (glazed box) on the first-floor bay
      kit.box(
        batch,
        glass,
        (b[0] + c[0]) / 2,
        (b[1] + c[1]) / 2,
        Z1 + 0.35,
        0.5,
        0.4,
        0.4,
        front.ang,
      );
    }
    // upper windows
    kit.windowRow(batch, front.a, T.at(front, EB), Z1 + 0.6, {
      count: 1,
      width: 1.05,
      height: 2.3,
      glass,
      frame: white,
      bars: 1,
      head: 'pediment',
      margin: 0.4,
      surround: 0.15,
      surroundMat: stucco,
    });
    kit.windowRow(batch, front.a, front.b, Z2 + 0.4, {
      count: 2,
      width: 1.0,
      height: 1.8,
      glass,
      frame: white,
      bars: 1,
      head: 'lintel',
      margin: 0.9,
      surround: 0.15,
      surroundMat: stucco,
    });
    // rear windows
    kit.windowRow(batch, back.a, back.b, Z0 + 0.8, {
      count: 2,
      width: 1.1,
      height: 2.4,
      glass,
      frame: white,
      bars: 1,
      margin: 1.0,
    });
    kit.windowRow(batch, back.a, back.b, Z1 + 0.6, {
      count: 2,
      width: 1.0,
      height: 2.2,
      glass,
      frame: white,
      bars: 1,
      margin: 1.0,
    });
    kit.windowRow(batch, back.a, back.b, Z2 + 0.4, {
      count: 2,
      width: 0.9,
      height: 1.7,
      glass,
      frame: white,
      bars: 1,
      margin: 1.0,
    });
    // basement area with railings
    const ra = T.at(front, 0, 1.6),
      rb = T.at(front, W, 1.6);
    T.ebox(stucco, front, 0, W, 1.55, 1.7, 0, 0.45);
    for (let s = EB; s < W; s += 0.14)
      T.ebox(black, front, s - 0.015, s + 0.015, 1.6, 1.63, 0.45, 1.4);
    void ra;
    void rb;
    // mansard attic with segmental dormers, party-wall chimney stacks
    const mr = kit.offsetRing(ring, -0.2);
    kit.pitchedRoof(batch, slate, stock, mr, front.ang + Math.PI / 2, Z3, 3.0, 'mansard', {
      overhang: 0,
    });
    for (const s of [W * 0.28, W * 0.72]) {
      const c = T.at(front, s, -1.2);
      kit.box(batch, stucco, c[0], c[1], Z3 + 0.3, 1.2, 1.4, 1.7, front.ang);
      kit.box(
        batch,
        glass,
        T.at(front, s, -0.48)[0],
        T.at(front, s, -0.48)[1],
        Z3 + 0.5,
        0.8,
        0.05,
        1.2,
        front.ang,
      );
      kit.box(batch, stucco, c[0], c[1], Z3 + 2.0, 1.45, 1.6, 0.25, front.ang);
      kit.box(batch, lead, c[0], c[1], Z3 + 2.25, 1.1, 1.4, 0.15, front.ang);
    }
    for (const e of E)
      if (e !== front && e !== back)
        for (const s of [e.len * 0.3, e.len * 0.7]) {
          T.ebox(stock, e, s - 0.6, s + 0.6, -0.8, 0.0, Z3, Z3 + 4.0);
          T.ebox(stucco, e, s - 0.7, s + 0.7, -0.9, 0.1, Z3 + 4.0, Z3 + 4.2);
          for (let k = 0; k < 3; k++) {
            const c = T.at(e, s - 0.35 + k * 0.35, -0.4);
            T.cyl(kit.mat('terracotta'), c[0], c[1], Z3 + 4.2, 0.12, 0.1, 0.6, 6);
          }
        }
    g.add(batch.toGroup('linley_sambourne_house'));
    return g;
  },
};
