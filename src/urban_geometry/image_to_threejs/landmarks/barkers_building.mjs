// Barkers of Kensington, 63-97 Kensington High Street (Bernard George, designed
// 1937-38, completed 1958). Portland stone, glass and gilded metal department store
// with a symmetrical convex front to the High Street between Derry Street and Young
// Street: seven storeys, the top two set back, the facade split by two stone stair
// towers with diagonal strip windows crowned by glass lanterns; relief sculpture on
// the towers and piers, bronze mullions on the ground floor and a cantilevered canopy.
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
  id: 'barkers_building',
  name: 'Barkers of Kensington',
  claims: ['d4583ef7-4665-42a1-b038-bdbc6831c295'],
  references: [
    {
      title: 'Messrs Barkers Store - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101222712-messers-barkers-store-queens-gate-ward',
      used_for:
        'Portland stone, glass and gilded metal; symmetrical convex facade of seven storeys, top two set back; two stone stair ' +
        'towers with diagonal strip windows and glass lanterns; reliefs, bronze ground-floor mullions, cantilevered canopy',
    },
    {
      title: 'Barkers of Kensington - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Barkers_of_Kensington',
      used_for: 'store history; Whole Foods Market in part of the building',
    },
    {
      title: 'Former Barkers Department Store - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1930/barkers.html',
      used_for: 'design 1937-38, completion 1958, Art Deco facade',
    },
    {
      title: 'Bernard George - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Bernard_George',
      used_for: 'architect, Barkers in-house chief architect 1928-62',
    },
  ],
  notes:
    'Five lower storeys to 18.6 m on the whole footprint and the two set-back storeys to 25.4 m on the Overture ' +
    'setback part (Overture gives 13.6 / 23.2 m); stair towers follow the two small Overture tower parts, ' +
    'extended to the ground and raised to 30 m with 4 m glass lanterns (heights estimated). Window bands use ' +
    'an even 1.6 m mullion module; reliefs are plain stone panels; the third small roof part is a plain lift ' +
    'motor room. Party/rear walls are plain stone.',
  build({ THREE, kit, buildings, scene }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const nb = T.neighbours(scene, [b0.id], b0.c, 200);
    const partsBy = Object.fromEntries(
      (b0.parts ?? []).map((p) => [p.id.slice(0, 4), T.ccw(p.polys[0][0])]),
    );

    const stone = kit.mat('#ddd6c3', { roughness: 0.8 });
    const stoneD = kit.mat('#cbc2ab', { roughness: 0.85 });
    const bronze = kit.mat('#6a5234', { roughness: 0.4, metalness: 0.65 });
    const gilt = kit.mat('gold');
    const glass = kit.mat('#2d3b45', { roughness: 0.15, metalness: 0.35 });
    const lantern = kit.mat('#a9c3cf', {
      roughness: 0.1,
      metalness: 0.2,
      transparent: true,
      opacity: 0.75,
    });
    const shop = kit.mat('#3c4f5a', { roughness: 0.1, metalness: 0.3 });
    const roofM = kit.mat('#8a8985');
    const G0 = 5.0,
      ST = 3.4,
      Z5 = G0 + 4 * ST, // 18.6
      Z7 = Z5 + 2 * ST; // 25.4

    const bandFacade = (r, z0, nst, onlyExposed) => {
      for (const e of T.edges(r)) {
        if (e.len < 2.5 || (onlyExposed && !T.exposed(e, nb))) continue;
        for (let f = 0; f < nst; f++) {
          const z = z0 + f * ST;
          kit.windowRow(batch, e.a, e.b, z + 0.8, {
            width: 1.35,
            height: 2.1,
            bay: 1.6,
            margin: 0.5,
            glass,
            frame: bronze,
            bars: 0,
            head: 'none',
            depth: 0.08,
          });
          T.ebox(bronze, e, 0.4, e.len - 0.4, 0.0, 0.05, z + 0.15, z + 0.7); // spandrel band
        }
        // stone piers every ~8 m
        const n = Math.max(1, Math.round(e.len / 8));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          T.ebox(stone, e, s - 0.4, s + 0.4, 0, 0.35, z0, z0 + nst * ST);
        }
      }
    };

    // ---- lower five storeys ---------------------------------------------------------
    kit.walls(batch, stone, [[ring]], 0, Z5 + 0.9, { bay: 1e6 });
    kit.cap(batch, roofM, [[ring]], Z5);
    kit.cornice(batch, stoneD, ring, Z5 + 0.4, { height: 0.5, projection: 0.4 });
    kit.cornice(batch, stoneD, ring, G0 - 0.4, { height: 0.4, projection: 0.2 });
    bandFacade(ring, G0, 4, true);
    // ground floor: bronze-mullioned shopfront and cantilevered canopy on street faces
    for (const e of T.edges(ring)) {
      if (e.len < 3 || !T.exposed(e, nb)) continue;
      T.ebox(shop, e, 0.3, e.len - 0.3, -0.2, 0.03, 0.3, G0 - 1.0);
      const n = Math.max(1, Math.round(e.len / 1.8));
      for (let k = 0; k <= n; k++) {
        const s = 0.3 + ((e.len - 0.6) * k) / n;
        T.ebox(bronze, e, s - 0.06, s + 0.06, 0, 0.1, 0.3, G0 - 1.0);
      }
      T.ebox(stoneD, e, 0, e.len, 0, 0.25, 0, 0.3);
      T.ebox(stone, e, 0, e.len, 0, 2.4, G0 - 0.95, G0 - 0.6);
      T.ebox(gilt, e, 0, e.len, 2.38, 2.45, G0 - 0.95, G0 - 0.6);
    }

    // ---- set-back top two storeys -------------------------------------------------
    const top = partsBy['5c7d'] ?? kit.offsetRing(ring, -6);
    kit.walls(batch, stone, [[top]], Z5, Z7 + 0.8, { bay: 1e6 });
    kit.cap(batch, roofM, [[top]], Z7);
    kit.cornice(batch, stoneD, top, Z7 + 0.4, { height: 0.4, projection: 0.3 });
    bandFacade(top, Z5, 2, false);
    // parapet rail on the lower roof terrace
    for (const e of T.edges(ring))
      if (e.len > 2 && T.exposed(e, nb))
        T.ebox(bronze, e, 0, e.len, -0.6, -0.55, Z5 + 0.9, Z5 + 1.6);

    // ---- stair towers with diagonal strip windows and glass lanterns ----------------
    for (const id of ['8561', 'b7ae']) {
      const r = partsBy[id];
      if (!r) continue;
      const tr = kit.offsetRing(r, 0.4);
      const TZ = 30;
      kit.walls(batch, stone, [[tr]], 0, TZ, { bay: 1e6 });
      kit.cap(batch, stoneD, [[tr]], TZ);
      kit.cornice(batch, stoneD, tr, TZ - 0.8, { height: 0.8, projection: 0.3, steps: 2 });
      for (const e of T.edges(tr)) {
        if (e.len < 3) continue;
        // diagonal strips: short glazed slots stepping up the face
        for (let z = G0 + 0.5, k = 0; z < TZ - 3; z += 1.1, k++) {
          const s = e.len * (0.25 + 0.5 * ((k % 4) / 3));
          const c = T.at(e, s, 0.03);
          kit.box(batch, glass, c[0], c[1], z, 1.4, 0.06, 0.8, e.ang + (k % 8 < 4 ? 0.6 : -0.6));
        }
        // relief panel and gilded vertical fin
        T.ebox(stoneD, e, e.len / 2 - 0.9, e.len / 2 + 0.9, 0, 0.18, G0 + 0.5, G0 + 3.2);
        T.ebox(gilt, e, e.len / 2 - 0.08, e.len / 2 + 0.08, 0, 0.25, TZ - 6, TZ - 0.8);
      }
      // stepped glass lantern
      const lr = kit.offsetRing(r, -0.6);
      kit.walls(batch, lantern, [[lr]], TZ, TZ + 3.2, { bay: 1e6 });
      kit.cap(batch, bronze, [[lr]], TZ + 3.2);
      const lr2 = kit.offsetRing(r, -1.4);
      kit.walls(batch, lantern, [[lr2]], TZ + 3.2, TZ + 4.4, { bay: 1e6 });
      kit.cap(batch, bronze, [[lr2]], TZ + 4.4);
      for (const e of T.edges(lr))
        for (let s = 0; s <= e.len; s += 0.8)
          T.ebox(bronze, e, s - 0.04, s + 0.04, 0, 0.06, TZ, TZ + 3.2);
    }
    // lift motor room
    if (partsBy['73cb']) T.prism(stoneD, partsBy['73cb'], Z7, Z7 + 3, roofM);

    g.add(batch.toGroup('barkers_building'));
    return g;
  },
};
