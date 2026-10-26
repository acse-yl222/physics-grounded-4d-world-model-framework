// Royal Garden Hotel, 2-24 Kensington High Street (Richard Seifert & Partners, opened
// 1965 on the site of the 1893 Royal Palace Hotel). Ten-storey concrete hotel on the
// edge of Kensington Gardens: an L-shaped slab with one wing along the High Street and
// one along the park beside Kensington Palace Gardens' gate, raised on a two-storey
// podium with a recessed glazed ground floor, and continuous horizontal bands of
// concrete spandrels and ribbon windows; rooftop plant/restaurant level.
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
  id: 'royal_garden_hotel',
  name: 'Royal Garden Hotel',
  claims: ['f1f01b9a-0526-44ad-ae0a-a1f48a5927f8'],
  references: [
    {
      title: 'Royal Garden Hotel - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Garden_Hotel',
      used_for: 'Seifert, Brutalist rebuild opened 1965, floor count 10',
    },
    {
      title: 'The notorious work of Richard Seifert - Building',
      url: 'https://www.building.co.uk/buildings/the-notorious-work-of-richard-seifert/5027597.article',
      used_for: '11-storey hotel on the edge of Hyde Park',
    },
    {
      title: 'Royal Garden Hotel - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1960/royalgarden.html',
      used_for: 'concrete massing, criticism of materials and proportions',
    },
  ],
  notes:
    'Height 31.2 m for ten storeys (4.5 m lobby + 2.7 m mezzanine podium, eight 3.0 m bedroom floors) replaces ' +
    'the Overture 7.2 / 23.2 m; both wings are given the same height as the Overture part. Spandrel/ribbon ' +
    'rhythm, the 1.5 m mullion module, podium recess, entrance canopy position (middle of the High Street ' +
    'wing) and the plant room height are estimated from general descriptions, not measured.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const conc = kit.mat('#d3cfc6', { roughness: 0.9 });
    const concD = kit.mat('#a9a59c', { roughness: 0.9 });
    const glass = kit.mat('#34434e', { roughness: 0.12, metalness: 0.4 });
    const mull = kit.mat('#4b4f52', { roughness: 0.5, metalness: 0.5 });
    const roofM = kit.mat('#8c8b87');
    const P = 7.2,
      ST = 3.0,
      NF = 8,
      H = P + NF * ST;

    // podium: recessed glazed lobby, solid mezzanine band
    const rec = kit.offsetRing(ring, -1.5);
    kit.walls(batch, glass, [[rec]], 0, 4.5, { bay: 1e6 });
    kit.cap(batch, concD, [[ring]], 4.5, { down: true });
    kit.walls(batch, conc, [[ring]], 4.5, P, { bay: 1e6 });
    for (const e of T.edges(rec)) {
      const n = Math.floor(e.len / 2);
      for (let k = 1; k < n; k++)
        T.ebox(mull, e, (k * e.len) / n - 0.05, (k * e.len) / n + 0.05, 0, 0.12, 0, 4.5);
    }
    // podium columns under the slab edge
    for (const e of T.edges(ring)) {
      if (e.len < 6) continue;
      const n = Math.round(e.len / 6);
      for (let k = 0; k <= n; k++)
        T.ebox(concD, e, (k * e.len) / n - 0.35, (k * e.len) / n + 0.35, -1.2, -0.5, 0, 4.5);
      kit.windowRow(batch, e.a, e.b, 5.1, {
        width: 2.2,
        height: 1.4,
        bay: 3,
        margin: 0.8,
        glass,
        frame: mull,
        bars: 0,
        head: 'none',
      });
    }

    // bedroom floors: continuous ribbon glazing between projecting spandrel bands
    const inner = kit.offsetRing(ring, -0.35);
    kit.walls(batch, glass, [[inner]], P, H, { bay: 1e6 });
    for (let f = 0; f <= NF; f++) {
      const z = P + f * ST;
      kit.cornice(batch, conc, ring, f === 0 ? P - 0.01 : z - 0.95, {
        height: f === 0 ? 1.0 : 1.1,
        projection: 0.1,
      });
    }
    for (const e of T.edges(inner)) {
      if (e.len < 1.2) continue;
      const n = Math.max(1, Math.round(e.len / 1.5));
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        T.ebox(mull, e, s - 0.04, s + 0.04, 0, 0.12, P, H);
      }
      // party-wall fins every 4 bays (room divisions)
      for (let k = 0; k <= n; k += 4) {
        const s = (k * e.len) / n;
        T.ebox(conc, e, s - 0.15, s + 0.15, 0, 0.45, P, H);
      }
    }
    // roof: parapet, roof slab, plant / restaurant room on the Overture roof part
    kit.cap(batch, roofM, [[ring]], H);
    kit.cornice(batch, concD, ring, H, { height: 1.0, projection: 0.05 });
    for (const p of b0.parts ?? []) {
      const r = T.ccw(p.polys[0][0]);
      if (Math.abs(kit.ringArea(r)) > 0.6 * Math.abs(kit.ringArea(ring))) continue;
      kit.walls(batch, concD, [[r]], H, H + 3.6, { bay: 1e6 });
      kit.cap(batch, roofM, [[r]], H + 3.6);
      for (const e of T.edges(r))
        if (e.len > 2)
          kit.windowRow(batch, e.a, e.b, H + 0.8, {
            width: 1.1,
            height: 1.8,
            bay: 1.5,
            margin: 0.4,
            glass,
            frame: mull,
            bars: 0,
            head: 'none',
          });
    }
    // entrance canopy on the High Street wing
    const E = T.edges(ring).filter((e) => e.len > 20);
    const street = T.facing(E, [0.3, -0.95], 20);
    if (street) {
      T.ebox(concD, street, street.len / 2 - 8, street.len / 2 + 8, -1.5, 4.5, 3.6, 4.1);
      for (const s of [street.len / 2 - 7.5, street.len / 2 + 7.5])
        T.ebox(mull, street, s - 0.12, s + 0.12, 4.0, 4.3, 0, 3.6);
    }
    g.add(batch.toGroup('royal_garden_hotel'));
    return g;
  },
};
