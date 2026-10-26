// St Mary Abbots, Kensington Church Street / Kensington High Street (Sir George
// Gilbert Scott, 1869-72; spire completed 1879 under John Oldrid Scott). Gothic
// Revival parish church of Kentish ragstone with Bath stone dressings: aisled nave
// with clerestory under a steep slate roof, lower chancel, and a tower at the east
// end on Kensington Church Street carrying a broach spire with double corner
// pinnacles and lucarnes, 278 ft (~85 m), the tallest spire in London.
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
  id: 'st_mary_abbots',
  name: 'St Mary Abbots',
  claims: ['c9132e61-7dfb-4fc7-9ca8-a11586fae9f2'],
  references: [
    {
      title: 'St Mary Abbots - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/St_Mary_Abbots',
      used_for: 'Scott design, consecration 1872, tallest spire in London',
    },
    {
      title: 'Parish Church of St Mary Abbot and railings to churchyard - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101239529-parish-church-of-st-mary-abbot-and-railings-to-churchyard-campden-ward',
      used_for:
        'rebuilt 1869-72 by Scott; eastern tower with broach spire, double corner pinnacles and lucarnes; entrance cloister 1889-93',
    },
    {
      title: 'St Mary Abbots, Kensington - Ship of Fools',
      url: 'https://shipoffools.com/?p=1264',
      used_for: 'tower and spire 278 ft high',
    },
    {
      title: 'St Mary Abbots - manchestervictorianarchitects.org.uk',
      url: 'https://manchestervictorianarchitects.org.uk/buildings/church-of-st-mary-abbot-kensington',
      used_for: 'spire modelled on St Mary Redcliffe, Bristol; completion 1879',
    },
  ],
  notes:
    'Total height 85 m (278 ft) from the references; the split (tower 36 m, spire 49 m) and the tower ' +
    'plan size (9.5 m) are estimated. Tower placed at the north-east corner of the footprint on Kensington ' +
    'Church Street. Aisle walls 9.5 m, clerestory to 17 m and a 50-degree nave roof are proportioned, not ' +
    'measured; aisle roofs are flat leaded caps rather than lean-to slopes. Window tracery is reduced to ' +
    'framed lancets; the 1889-93 cloister to the High Street is a separate footprint and not modelled.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    let F = T.frame(ring);
    if (Math.cos(F.angle) < 0) F = T.frame(ring, F.angle + Math.PI); // u runs west -> east

    const rag = kit.mat('#8f8a79', { roughness: 0.95 });
    const dress = kit.mat('#cdbd98', { roughness: 0.85 });
    const slate = kit.mat('#4a5058', { roughness: 0.8 });
    const lead = kit.mat('lead');
    const glass = kit.mat('#2f3a42', { roughness: 0.2, metalness: 0.3 });
    const louvre = kit.mat('#3b3631');
    const AIS = 9.5;

    // ---- aisles / outer walls ----------------------------------------------------
    kit.walls(batch, rag, [[ring]], 0, AIS, { bay: 1e6 });
    kit.cornice(batch, dress, ring, 0, { height: 0.6, projection: 0.25 });
    kit.cornice(batch, dress, ring, AIS - 0.5, { height: 0.5, projection: 0.3 });
    kit.cap(batch, lead, [[ring]], AIS);
    const E = T.edges(ring);
    for (const e of E) {
      if (e.len < 4) continue;
      kit.windowRow(batch, e.a, e.b, 2.6, {
        width: 1.3,
        height: 4.6,
        bay: 4.4,
        margin: 1.4,
        head: 'arch',
        glass,
        frame: dress,
        bars: 1,
      });
      // buttresses between the bays
      const n = Math.max(1, Math.round((e.len - 2.8) / 4.4));
      for (let k = 0; k <= n; k++) {
        const s = 1.4 + ((e.len - 2.8) * k) / n;
        T.ebox(dress, e, s - 0.35, s + 0.35, 0, 0.9, 0, AIS - 1.8);
        T.ebox(dress, e, s - 0.3, s + 0.3, 0, 0.5, AIS - 1.8, AIS - 0.6);
      }
    }

    // ---- nave with clerestory and steep roof; lower chancel -------------------------
    const NW = Math.min(12, F.W * 0.45);
    const tw = 9.5; // tower plan
    const nu0 = F.u0 + 1,
      nu1 = F.u1 - 14;
    const nv0 = F.cv - NW / 2,
      nv1 = F.cv + NW / 2;
    const nave = T.rect(F, nu0, nu1, nv0, nv1);
    const CLR = 17;
    kit.walls(batch, rag, [[nave]], AIS, CLR, { bay: 1e6 });
    kit.cornice(batch, dress, nave, CLR - 0.4, { height: 0.4, projection: 0.25 });
    for (const e of T.edges(nave))
      if (e.len > NW + 1)
        kit.windowRow(batch, e.a, e.b, AIS + 2, {
          width: 1.1,
          height: 3.6,
          bay: 4.4,
          margin: 1.5,
          head: 'arch',
          glass,
          frame: dress,
          bars: 0,
        });
    kit.pitchedRoof(batch, slate, rag, nave, F.angle, CLR, NW * 0.6, 'gabled', { overhang: 0.4 });
    // west gable: great five-light window and copings
    {
      const a = F.w(nu0, nv1),
        b = F.w(nu0, nv0);
      kit.windowRow(batch, a, b, AIS + 1, {
        count: 1,
        width: NW * 0.5,
        height: 8,
        head: 'arch',
        glass,
        frame: dress,
        bars: 3,
        margin: 0,
      });
      const c = F.w(nu0 - 0.2, F.cv);
      T.cyl(dress, c[0], c[1], CLR + NW * 0.6, 0.25, 0.1, 2.4, 6); // apex cross shaft
    }
    // chancel
    const CW = NW * 0.82;
    const ch = T.rect(F, nu1, F.u1 - 0.8, F.cv - CW / 2, F.cv + CW / 2);
    kit.walls(batch, rag, [[ch]], AIS, 14, { bay: 1e6 });
    kit.pitchedRoof(batch, slate, rag, ch, F.angle, 14, CW * 0.6, 'gabled', { overhang: 0.3 });
    {
      const a = F.w(F.u1 - 0.75, F.cv - CW / 2),
        b = F.w(F.u1 - 0.75, F.cv + CW / 2);
      kit.windowRow(batch, a, b, 5, {
        count: 1,
        width: CW * 0.55,
        height: 9.5,
        head: 'arch',
        glass,
        frame: dress,
        bars: 3,
        margin: 0,
      });
    }
    // ridge crests
    for (const [u0, u1, v, z] of [
      [nu0, nu1, F.cv, CLR + NW * 0.6],
      [nu1, F.u1 - 0.8, F.cv, 14 + CW * 0.6],
    ])
      T.fbox(dress, F, (u0 + u1) / 2, v, z - 0.1, u1 - u0, 0.25, 0.35);

    // ---- tower and broach spire at the north-east corner ------------------------------
    let tc = null;
    for (const [du, dv] of [
      [0, 0],
      [-3, 0],
      [0, -3],
      [-3, -3],
      [-6, -2],
    ]) {
      const u = F.u1 - tw / 2 - 0.5 + du,
        v = F.v1 - tw / 2 - 0.5 + dv;
      const corners = T.rect(F, u - tw / 2, u + tw / 2, v - tw / 2, v + tw / 2);
      if (corners.filter((p) => T.inside(p, ring)).length >= 3) {
        tc = [u, v];
        break;
      }
    }
    tc = tc ?? [F.u1 - tw / 2 - 1, F.v1 - tw / 2 - 1];
    const TT = 36; // top of tower parapet
    const tr = T.rect(F, tc[0] - tw / 2, tc[0] + tw / 2, tc[1] - tw / 2, tc[1] + tw / 2);
    kit.walls(batch, rag, [[tr]], 0, TT, { bay: 1e6 });
    kit.cap(batch, lead, [[tr]], TT);
    for (const z of [0, AIS, 20, 27.5])
      kit.cornice(batch, dress, tr, z, { height: 0.5, projection: 0.25 });
    kit.cornice(batch, dress, tr, TT - 1.2, { height: 1.2, projection: 0.45, steps: 2 });
    const TE = T.edges(tr);
    for (const e of TE) {
      // clasping corner buttresses, stepped
      for (const s of [0.6, e.len - 0.6]) {
        T.ebox(dress, e, s - 0.7, s + 0.7, 0, 0.9, 0, 18);
        T.ebox(dress, e, s - 0.55, s + 0.55, 0, 0.6, 18, 30);
      }
      // ringing-chamber lancets, belfry pairs with louvres
      kit.windowRow(batch, e.a, e.b, 11.5, {
        count: 1,
        width: 1.3,
        height: 4.0,
        head: 'arch',
        glass,
        frame: dress,
        margin: 2,
      });
      kit.windowRow(batch, e.a, e.b, 21.5, {
        count: 2,
        width: 1.5,
        height: 5.2,
        head: 'arch',
        glass: louvre,
        frame: dress,
        bars: 3,
        margin: 2.2,
        surround: 0.25,
        surroundMat: dress,
      });
      // clock face below the belfry
      const c = T.at(e, e.len / 2, 0.08);
      T.geo(
        kit.mat('#e8e0c8'),
        new THREE.CylinderGeometry(1.1, 1.1, 0.12, 20).rotateX(Math.PI / 2).rotateY(Math.PI / 2),
        c[0],
        c[1],
        18.0,
        e.ang + Math.PI / 2,
      );
    }
    // Broach spire: octagon from the tower top to ~85 m.
    const sc = F.w(tc[0], tc[1]);
    const SH = 85 - TT - 1.2;
    const r8 = (tw / 2 - 0.6) / Math.cos(Math.PI / 8);
    T.spire(rag, sc[0], sc[1], TT, r8, SH, 8, F.angle + Math.PI / 8);
    // broaches: corner half-pyramids from the square to the octagon
    for (const [su, sv] of [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ]) {
      const p = F.w(tc[0] + su * (tw / 2 - 1.3), tc[1] + sv * (tw / 2 - 1.3));
      T.spire(rag, p[0], p[1], TT, 1.9, 5.5, 4, F.angle + Math.PI / 4);
      // double corner pinnacles
      for (const [a, b] of [
        [su * (tw / 2 - 0.5), sv * (tw / 2 - 1.6)],
        [su * (tw / 2 - 1.6), sv * (tw / 2 - 0.5)],
      ]) {
        const q = F.w(tc[0] + a, tc[1] + b);
        T.fbox(dress, F, tc[0] + a, tc[1] + b, TT, 0.7, 0.7, 2.2);
        T.spire(dress, q[0], q[1], TT + 2.2, 0.55, 3.8, 4, F.angle + Math.PI / 4);
      }
    }
    // lucarnes on the cardinal faces at three levels
    for (const [z, sz] of [
      [TT + 2.5, 1],
      [TT + 14, 0.7],
      [TT + 26, 0.45],
    ]) {
      const rr = r8 * Math.cos(Math.PI / 8) * (1 - (z - TT) / SH);
      for (let k = 0; k < 4; k++) {
        const a = F.angle + (k * Math.PI) / 2;
        const x = sc[0] + Math.cos(a) * rr,
          y = sc[1] + Math.sin(a) * rr;
        kit.box(batch, dress, x, y, z, 1.0 * sz, 1.6 * sz, 2.6 * sz, a);
        kit.box(
          batch,
          louvre,
          x + Math.cos(a) * 0.8 * sz,
          y + Math.sin(a) * 0.8 * sz,
          z + 0.3 * sz,
          0.05,
          0.9 * sz,
          1.6 * sz,
          a,
        );
        const gab = new THREE.ConeGeometry(1.0 * sz, 1.4 * sz, 4, 1).rotateX(Math.PI / 2);
        T.geo(dress, gab, x, y, z + 2.6 * sz + 0.7 * sz, a + Math.PI / 4);
      }
    }
    // spire bands and finial cross
    for (const f of [0.35, 0.62]) {
      const z = TT + SH * f;
      T.cyl(dress, sc[0], sc[1], z, r8 * (1 - f) * 1.04, r8 * (1 - f) * 1.02, 0.5, 8);
    }
    T.cyl(kit.mat('bronze'), sc[0], sc[1], TT + SH - 0.5, 0.12, 0.08, 3.5, 6);
    T.fbox(kit.mat('bronze'), F, tc[0], tc[1], TT + SH + 1.9, 1.2, 0.12, 0.12);

    g.add(batch.toGroup('st_mary_abbots'));
    return g;
  },
};
