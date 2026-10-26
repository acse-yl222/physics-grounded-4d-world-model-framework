// Kensington Temple, Kensington Park Road / Ladbroke Road, Notting Hill Gate (built
// 1848-49 as Horbury Chapel, Congregational, architect J. Tarring; Elim Pentecostal
// since 1930-31). Geometrical Gothic chapel of random rubble Kentish ragstone with
// ashlar dressings on a cruciform plan - a four-bay nave, transepts and a shallow
// sanctuary - its gabled front to Kensington Park Road flanked by square towers
// capped by low spires; galleries on three sides inside.
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
  id: 'kensington_temple',
  name: 'Kensington Temple',
  claims: ['0af4842f-09f7-461f-9e91-0b5d4ee0a30b'],
  references: [
    {
      title: 'Kensington Temple - British Listed Buildings',
      url: 'https://www.britishlistedbuildings.co.uk/101224188-kensington-temple-pembridge-ward',
      used_for:
        'Grade II 1974; Geometrical Gothic, square towers capped by low spires, cruciform plan with 4-bay nave, transepts and ' +
        'shallow sanctuary, random rubble Kentish ragstone with ashlar dressings, galleries on three sides',
    },
    {
      title: 'Kensington Temple - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Temple',
      used_for: 'founded 1848 as Horbury Chapel, bought by George Jeffreys 1930, Elim opening 1931',
    },
    {
      title: 'Horbury Chapel, Kensington Park Road - AIM25',
      url: 'https://atom.aim25.com/index.php/horbury-chapel-kensington-park-road-notting-hill-gate-kensington',
      used_for:
        'architect J Tarring, built 1848-49 at the junction of Ladbroke Road and Kensington Park Road',
    },
  ],
  notes:
    'Front taken as the north-east face on Kensington Park Road (the projecting centre of the footprint), with ' +
    'the towers at its two corners; tower height 18 m and spires to 24 m are estimates for "low spires". ' +
    'Nave eaves 9.5 m with a 7 m roof, the transept across the middle of the plan and the window tracery ' +
    '(simplified to framed pointed windows) are proportioned, not measured.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    const F = T.frame(ring, Math.PI / 4); // u towards Kensington Park Road (north-east)
    const rag = kit.mat('#9e9884', { roughness: 0.95 });
    const ash = kit.mat('#d6c9a6', { roughness: 0.85 });
    const slate = kit.mat('#4c535a', { roughness: 0.8 });
    const glass = kit.mat('#2f3a42', { roughness: 0.2, metalness: 0.3 });
    const door = kit.mat('#3c2a1e');
    const EAV = 9.5;
    // the projecting front: vertices whose u is within 1 m of the maximum
    const fr = ring.map(F.uv).filter(([u]) => u > F.u1 - 1.2);
    const fv0 = Math.min(...fr.map((p) => p[1])),
      fv1 = Math.max(...fr.map((p) => p[1]));
    const vC = (fv0 + fv1) / 2,
      NW = Math.max(10, fv1 - fv0);

    kit.walls(batch, rag, [[ring]], 0, EAV, { bay: 1e6 });
    kit.cornice(batch, ash, ring, 0, { height: 0.6, projection: 0.2 });
    kit.cornice(batch, ash, ring, EAV - 0.4, { height: 0.4, projection: 0.3 });
    kit.cap(batch, kit.mat('lead'), [[ring]], EAV);
    for (const e of T.edges(ring)) {
      if (e.len < 3) continue;
      kit.windowRow(batch, e.a, e.b, 1.2, {
        width: 1.0,
        height: 2.4,
        bay: 3.4,
        margin: 0.9,
        head: 'arch',
        glass,
        frame: ash,
        bars: 1,
      });
      kit.windowRow(batch, e.a, e.b, 4.6, {
        width: 1.3,
        height: 3.6,
        bay: 3.4,
        margin: 0.9,
        head: 'arch',
        glass,
        frame: ash,
        bars: 1,
      });
      for (const s of [0.3, e.len - 0.3]) T.ebox(ash, e, s - 0.35, s + 0.35, 0, 0.6, 0, EAV - 1.2);
    }
    // nave roof along u, transept roof across
    const nave = T.rect(F, F.u0, F.u1, vC - NW / 2, vC + NW / 2);
    kit.pitchedRoof(batch, slate, rag, nave, F.angle, EAV, 7, 'gabled', { overhang: 0.3 });
    const tr = T.rect(F, F.cu - 5.5, F.cu + 5.5, F.v0, F.v1);
    kit.pitchedRoof(batch, slate, rag, tr, F.angle + Math.PI / 2, EAV, 6, 'gabled', {
      overhang: 0.3,
    });
    // front gable: great Geometrical window over the door
    {
      const a = F.w(F.u1 + 0.05, vC - NW / 2 + 2),
        b = F.w(F.u1 + 0.05, vC + NW / 2 - 2);
      kit.windowRow(batch, a, b, 5.0, {
        count: 1,
        width: NW * 0.36,
        height: 7.5,
        head: 'arch',
        glass,
        frame: ash,
        bars: 3,
        margin: 0,
      });
      const d = F.w(F.u1 + 0.4, vC);
      kit.box(batch, ash, d[0], d[1], 0, 3.6, 0.8, 4.4, F.angle + Math.PI / 2);
      const dd = F.w(F.u1 + 0.82, vC);
      kit.box(batch, door, dd[0], dd[1], 0.2, 2.2, 0.05, 3.2, F.angle + Math.PI / 2);
      T.geo(
        ash,
        new THREE.ConeGeometry(2.6, 1.6, 4, 1).rotateX(Math.PI / 2),
        d[0],
        d[1],
        5.2,
        F.angle + Math.PI / 4,
      );
    }
    // twin towers with low spires at the front corners
    const TS = 4.6,
      TZ = 18,
      SP = 6;
    for (const v of [vC - NW / 2 + TS / 2 - 0.3, vC + NW / 2 - TS / 2 + 0.3]) {
      const u = F.u1 - TS / 2 + 0.3;
      const r = T.rect(F, u - TS / 2, u + TS / 2, v - TS / 2, v + TS / 2);
      kit.walls(batch, rag, [[r]], 0, TZ, { bay: 1e6 });
      kit.cap(batch, kit.mat('lead'), [[r]], TZ);
      for (const z of [EAV, TZ - 0.7])
        kit.cornice(batch, ash, r, z, { height: 0.6, projection: 0.25 });
      for (const e of T.edges(r)) {
        kit.windowRow(batch, e.a, e.b, EAV + 2.2, {
          count: 1,
          width: 1.0,
          height: 3.6,
          head: 'arch',
          glass: kit.mat('#3b3631'),
          frame: ash,
          bars: 2,
          margin: 1.2,
        });
        for (const s of [0.25, e.len - 0.25]) T.ebox(ash, e, s - 0.3, s + 0.3, 0, 0.4, 0, TZ - 0.7);
      }
      const c = F.w(u, v);
      T.spire(slate, c[0], c[1], TZ, (TS / 2) * Math.SQRT2 * 0.95, SP, 4, F.angle + Math.PI / 4);
      for (const [a, b] of [
        [1, 1],
        [1, -1],
        [-1, 1],
        [-1, -1],
      ]) {
        const p = F.w(u + a * (TS / 2 - 0.25), v + b * (TS / 2 - 0.25));
        T.spire(ash, p[0], p[1], TZ, 0.35, 1.8, 4, F.angle + Math.PI / 4);
      }
      T.cyl(kit.mat('bronze'), c[0], c[1], TZ + SP - 0.3, 0.06, 0.04, 1.3, 6);
    }
    g.add(batch.toGroup('kensington_temple'));
    return g;
  },
};
