// St John's, Notting Hill, Lansdowne Crescent (John Hargrave Stevens and George
// Alexander, 1845). Built as the centrepiece of the Ladbroke Estate on the top of
// Notting Hill: Early English church of Kentish ragstone coursed rubble with Bath stone
// ashlar dressings - aisled nave, transepts, chancel and a crossing tower carrying a
// broach stone spire 150 ft high, said to resemble that of St Mary's, Witney.
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
  id: 'st_johns_notting_hill',
  name: "St John's, Notting Hill",
  claims: ['2e10f5b4-b71e-46a3-b41c-facc657d7d36'],
  references: [
    {
      title: 'Church of St John Notting Hill - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101225121-church-of-st-john-notting-hill-norland-ward',
      used_for:
        'Kentish ragstone coursed rubble with Bath stone ashlar, Early English, aisled nave, transepts, crossing tower and ' +
        'broached stone spire 150 ft high',
    },
    {
      title: "St John's, Notting Hill - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_John%27s,_Notting_Hill',
      used_for:
        'Stevens and Alexander 1845, centrepiece of the Ladbroke Estate, spire like St Mary Witney, 1,500 seats',
    },
    {
      title: 'Church of St John Notting Hill - Historic England',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1225121',
      used_for: 'Grade II listing',
    },
  ],
  notes:
    'Spire apex 46 m (150 ft); tower to 25.5 m with the broach spire above (split estimated). Transepts and ' +
    'chancel follow the footprint projections (crossing ~27 m from the west end). Aisle walls 7.5 m, clerestory ' +
    '12 m and roof pitches are proportioned; lancet sizes and buttress rhythm are estimated, the west front ' +
    'is simplified to a triple lancet group.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    const F = T.frame(ring, (24.1 * Math.PI) / 180); // u: west -> east along the nave
    const rag = kit.mat('#a39c86', { roughness: 0.95 });
    const bath = kit.mat('#d8c8a0', { roughness: 0.85 });
    const slate = kit.mat('#4c535a', { roughness: 0.8 });
    const lead = kit.mat('lead');
    const glass = kit.mat('#2f3a42', { roughness: 0.2, metalness: 0.3 });
    const AIS = 7.5,
      CLR = 12;
    const u0 = F.u0,
      cu = u0 + 27; // crossing centre
    const vC = F.v0 + 14.5; // nave centre line (between aisle walls v0+6 .. v0+23)

    kit.walls(batch, rag, [[ring]], 0, AIS, { bay: 1e6 });
    kit.cap(batch, lead, [[ring]], AIS);
    kit.cornice(batch, bath, ring, 0, { height: 0.5, projection: 0.2 });
    kit.cornice(batch, bath, ring, AIS - 0.4, { height: 0.4, projection: 0.25 });
    for (const e of T.edges(ring)) {
      if (e.len < 3) continue;
      kit.windowRow(batch, e.a, e.b, 2.0, {
        width: 0.9,
        height: 3.8,
        bay: 3.6,
        margin: 1.0,
        head: 'arch',
        glass,
        frame: bath,
        bars: 0,
      });
      const n = Math.max(1, Math.round((e.len - 1) / 3.6));
      for (let k = 0; k <= n; k++) {
        const s = 0.5 + ((e.len - 1) * k) / n;
        T.ebox(bath, e, s - 0.3, s + 0.3, 0, 0.7, 0, AIS - 1.5);
      }
    }
    // nave + clerestory
    const NW = 9;
    const nave = T.rect(F, u0 + 0.6, cu - 4, vC - NW / 2, vC + NW / 2);
    kit.walls(batch, rag, [[nave]], AIS, CLR, { bay: 1e6 });
    for (const e of T.edges(nave))
      if (e.len > NW + 1)
        kit.windowRow(batch, e.a, e.b, AIS + 1.2, {
          count: 6,
          width: 0.8,
          height: 2.6,
          head: 'arch',
          glass,
          frame: bath,
          bars: 0,
          margin: 1.5,
        });
    kit.pitchedRoof(batch, slate, rag, nave, F.angle, CLR, NW * 0.65, 'gabled', { overhang: 0.3 });
    // west front lancet group
    {
      const a = F.w(u0 + 0.55, vC + 3.5),
        b = F.w(u0 + 0.55, vC - 3.5);
      kit.windowRow(batch, a, b, 4, {
        count: 3,
        width: 1.2,
        height: 6.5,
        head: 'arch',
        glass,
        frame: bath,
        bars: 0,
        margin: 0.8,
      });
    }
    // transepts and chancel
    const tr = T.rect(F, cu - 4, cu + 4, F.v0 + 0.3, F.v1 - 0.3);
    kit.walls(batch, rag, [[tr]], AIS, CLR - 0.5, { bay: 1e6 });
    kit.pitchedRoof(batch, slate, rag, tr, F.angle + Math.PI / 2, CLR - 0.5, 5.2, 'gabled', {
      overhang: 0.3,
    });
    for (const vv of [F.v0 + 0.25, F.v1 - 0.25]) {
      const a = F.w(cu - 2.5, vv),
        b = F.w(cu + 2.5, vv);
      const [p, q] = vv < vC ? [a, b] : [b, a];
      kit.windowRow(batch, p, q, AIS - 3, {
        count: 3,
        width: 1.0,
        height: 6,
        head: 'arch',
        glass,
        frame: bath,
        bars: 0,
        margin: 0.6,
      });
    }
    const ch = T.rect(F, cu + 4, F.u1 - 0.6, vC - 4, vC + 4);
    kit.walls(batch, rag, [[ch]], AIS, CLR - 1.5, { bay: 1e6 });
    kit.pitchedRoof(batch, slate, rag, ch, F.angle, CLR - 1.5, 4.8, 'gabled', { overhang: 0.3 });
    {
      const a = F.w(F.u1 - 0.55, vC - 3),
        b = F.w(F.u1 - 0.55, vC + 3);
      kit.windowRow(batch, a, b, 3.5, {
        count: 3,
        width: 1.1,
        height: 6.2,
        head: 'arch',
        glass,
        frame: bath,
        bars: 0,
        margin: 0.6,
      });
    }
    // crossing tower and broach spire
    const TS = 8,
      TZ = 25.5,
      TOP = 46;
    const tc = F.w(cu, vC);
    const tower = T.rect(F, cu - TS / 2, cu + TS / 2, vC - TS / 2, vC + TS / 2);
    kit.walls(batch, rag, [[tower]], AIS, TZ, { bay: 1e6 });
    kit.cap(batch, lead, [[tower]], TZ);
    kit.cornice(batch, bath, tower, CLR + 4.5, { height: 0.4, projection: 0.2 });
    kit.cornice(batch, bath, tower, TZ - 0.8, { height: 0.8, projection: 0.35, steps: 2 });
    for (const e of T.edges(tower)) {
      kit.windowRow(batch, e.a, e.b, CLR + 6.2, {
        count: 2,
        width: 1.1,
        height: 4.2,
        head: 'arch',
        glass: kit.mat('#3b3631'),
        frame: bath,
        bars: 2,
        margin: 1.4,
        surround: 0.2,
        surroundMat: bath,
      });
      for (const s of [0.5, e.len - 0.5]) T.ebox(bath, e, s - 0.5, s + 0.5, 0, 0.6, CLR, TZ - 0.8);
    }
    const r8 = (TS / 2 - 0.5) / Math.cos(Math.PI / 8);
    T.spire(rag, tc[0], tc[1], TZ, r8, TOP - TZ, 8, F.angle + Math.PI / 8);
    for (const [su, sv] of [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ]) {
      const p = F.w(cu + su * (TS / 2 - 1.2), vC + sv * (TS / 2 - 1.2));
      T.spire(rag, p[0], p[1], TZ, 1.7, 4.5, 4, F.angle + Math.PI / 4);
    }
    // spire lucarnes
    for (let k = 0; k < 4; k++) {
      const a = F.angle + (k * Math.PI) / 2,
        rr = r8 * Math.cos(Math.PI / 8) * 0.8;
      const x = tc[0] + Math.cos(a) * rr,
        y = tc[1] + Math.sin(a) * rr;
      kit.box(batch, bath, x, y, TZ + 3.5, 0.8, 1.2, 1.8, a);
      T.geo(
        bath,
        new THREE.ConeGeometry(0.8, 1.1, 4, 1).rotateX(Math.PI / 2),
        x,
        y,
        TZ + 5.85,
        a + Math.PI / 4,
      );
    }
    T.cyl(kit.mat('bronze'), tc[0], tc[1], TOP - 0.4, 0.1, 0.06, 2.2, 6);
    g.add(batch.toGroup('st_johns_notting_hill'));
    return g;
  },
};
