// Embassy of Russia, 6-7 and 5 Kensington Palace Gardens (north end of the private
// road, at the junction with Bayswater Road). Nos 6 and 7 (T. H. Wyatt and D. Brandon,
// 1844-46) are a semi-detached pair treated as one symmetrical Italianate stucco
// composition: three storeys over a basement, seven windows wide with the central one
// blind, square bay windows in the outer bays, pediments over the first-floor windows,
// Ionic and Corinthian orders on the central windows, a cornice and an openwork
// parapet; entrances in the side returns. No. 5 houses the consular section.
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
  id: 'russian_embassy',
  name: 'Embassy of Russia (6-7 and 5 Kensington Palace Gardens)',
  claims: ['e81adfcf-25b4-4ae3-868f-e022e64f0cfd', '2dd73431-5edd-4d36-87b7-62f9beafbc60'],
  references: [
    {
      title: '6 and 7 Kensington Palace Gardens W8 - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101223939-6-and-7-kensington-palace-gardens-w8-campden-ward',
      used_for:
        '1844-6 by T H Wyatt and Brandon; symmetrical semi-detached pair, stucco, Italianate, three storeys over basement, ' +
        'seven windows with central blind window, square bays to outer bays, first-floor pediments, Ionic/Corinthian orders ' +
        'on central windows, cornice and openwork parapet, entrances in the returns',
    },
    {
      title: 'Embassy of Russia, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Embassy_of_Russia,_London',
      used_for:
        'main building and consular section at 5 and 6-7 Kensington Palace Gardens, junction with Bayswater Road',
    },
  ],
  notes:
    'Storey heights (basement 1.0 m exposed, 4.2 / 4.2 / 3.4 m) fitted to the Overture 14.2 m. The front is the ' +
    'long west face on Kensington Palace Gardens. No. 5 (consular section) is modelled as a plainer three-storey ' +
    'stucco block with cornice and parapet at the Overture 11.8 m; its detailing is not researched. The flag ' +
    'and flagpole position are assumptions; railings, security fences and the forecourt are omitted.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const stucco = kit.mat('#eee8da', { roughness: 0.75 });
    const stuccoD = kit.mat('#ddd5c3', { roughness: 0.8 });
    const glass = kit.mat('#2c363e', { roughness: 0.2, metalness: 0.3 });
    const white = kit.mat('white');
    const slate = kit.mat('slate');
    const door = kit.mat('#2a2c2c');

    // ---- 6-7 Kensington Palace Gardens ---------------------------------------------
    {
      const ring = T.ccw(byId['e81adfcf-25b4-4ae3-868f-e022e64f0cfd'].polys[0][0]);
      const E = T.edges(ring);
      const front = T.facing(E, [-0.95, 0.3], 10);
      const B0 = 1.0,
        Z1 = B0 + 4.2,
        Z2 = Z1 + 4.2,
        Z3 = Z2 + 3.4; // 12.8 cornice
      kit.walls(batch, stucco, [[ring]], 0, Z3, { bay: 1e6 });
      kit.cornice(batch, stuccoD, ring, 0, { height: B0, projection: 0.12 });
      kit.cornice(batch, stuccoD, ring, Z1 - 0.2, { height: 0.35, projection: 0.15 });
      kit.cornice(batch, stuccoD, ring, Z2 - 0.2, { height: 0.3, projection: 0.12 });
      kit.cornice(batch, stucco, ring, Z3 - 0.6, { height: 0.6, projection: 0.6, steps: 3 });
      // openwork parapet
      const pr = kit.offsetRing(ring, -0.1);
      for (const e of T.edges(pr))
        if (e.len > 1)
          kit.balustrade(batch, stucco, [e.a, e.b], Z3, { height: 1.0, spacing: 0.35 });
      kit.cap(batch, kit.mat('#7d8184'), [[ring]], Z3);
      const F = T.frame(ring);
      kit.pitchedRoof(
        batch,
        slate,
        stucco,
        T.rect(F, F.u0 + 1.5, F.u1 - 1.5, F.v0 + 1.5, F.v1 - 1.5),
        F.angle,
        Z3,
        2.6,
        'hipped',
        { overhang: 0 },
      );
      // channelled rustication on the ground storey of all faces
      for (const e of E)
        if (e.len > 1.5)
          for (let z = B0 + 0.45; z < Z1 - 0.3; z += 0.5)
            T.ebox(stuccoD, e, 0, e.len, 0, 0.04, z, z + 0.06);
      // front: 7 window positions, outer bays with square bay windows
      const W = front.len,
        bw = W / 7;
      for (let k = 0; k < 7; k++) {
        const s0 = k * bw,
          s1 = (k + 1) * bw,
          sm = (s0 + s1) / 2;
        const a = T.at(front, s0),
          b = T.at(front, s1);
        const blind = k === 3;
        const outer = k === 0 || k === 6;
        if (outer) {
          // square two-storey bay window
          T.ebox(stucco, front, s0 + 0.3, s1 - 0.3, 0, 1.3, 0, Z2 - 0.2);
          T.ebox(stuccoD, front, s0 + 0.2, s1 - 0.2, 0, 1.45, Z2 - 0.4, Z2 - 0.1);
          kit.balustrade(
            batch,
            stucco,
            [T.at(front, s0 + 0.3, 1.2), T.at(front, s1 - 0.3, 1.2)],
            Z2 - 0.1,
            { height: 0.8, spacing: 0.3 },
          );
          const p = T.at(front, s0 + 0.3, 1.3),
            q = T.at(front, s1 - 0.3, 1.3);
          kit.windowRow(batch, p, q, B0 + 0.9, {
            count: 1,
            width: bw * 0.5,
            height: 2.6,
            glass,
            frame: white,
            bars: 1,
            head: 'none',
            margin: 0,
          });
          kit.windowRow(batch, p, q, Z1 + 0.7, {
            count: 1,
            width: bw * 0.5,
            height: 2.6,
            glass,
            frame: white,
            bars: 1,
            head: 'pediment',
            margin: 0,
          });
        } else {
          kit.windowRow(batch, a, b, B0 + 0.9, {
            count: 1,
            width: 1.3,
            height: 2.6,
            glass: blind ? stuccoD : glass,
            frame: white,
            bars: 1,
            head: 'arch',
            margin: 0,
            surround: 0.2,
            surroundMat: stuccoD,
          });
          kit.windowRow(batch, a, b, Z1 + 0.7, {
            count: 1,
            width: 1.3,
            height: 2.6,
            glass: blind ? stuccoD : glass,
            frame: white,
            bars: 1,
            head: 'pediment',
            margin: 0,
            surround: 0.2,
            surroundMat: stuccoD,
          });
          // balconette in front of first-floor windows
          kit.balustrade(
            batch,
            stucco,
            [T.at(front, sm - 0.9, 0.5), T.at(front, sm + 0.9, 0.5)],
            Z1,
            { height: 0.7, spacing: 0.25 },
          );
          T.ebox(stuccoD, front, sm - 1.0, sm + 1.0, 0, 0.6, Z1 - 0.15, Z1);
        }
        kit.windowRow(batch, a, b, Z2 + 0.6, {
          count: 1,
          width: 1.1,
          height: 1.9,
          glass: blind ? stuccoD : glass,
          frame: white,
          bars: 1,
          head: 'lintel',
          margin: 0,
          surround: 0.18,
          surroundMat: stuccoD,
        });
        // central windows framed by orders: Ionic (first floor) / Corinthian (second)
        if (k >= 2 && k <= 4) {
          for (const s of [sm - 1.0, sm + 1.0]) {
            kit.colonnade(
              batch,
              stucco,
              T.at(front, s, 0.2),
              T.at(front, s, 0.2),
              Z1,
              Z2 - Z1 - 0.2,
              { count: 1, radius: 0.17, capital: 'doric' },
            );
            kit.colonnade(
              batch,
              stucco,
              T.at(front, s, 0.2),
              T.at(front, s, 0.2),
              Z2,
              Z3 - Z2 - 0.6,
              { count: 1, radius: 0.15, capital: 'corinthian' },
            );
          }
        }
      }
      // side returns: entrances with porches, windows
      for (const e of E) {
        if (e === front || e.len < 4) continue;
        kit.windowRow(batch, e.a, e.b, B0 + 0.9, {
          width: 1.2,
          height: 2.5,
          bay: 3.4,
          margin: 1.2,
          glass,
          frame: white,
          bars: 1,
          head: 'lintel',
        });
        kit.windowRow(batch, e.a, e.b, Z1 + 0.7, {
          width: 1.2,
          height: 2.5,
          bay: 3.4,
          margin: 1.2,
          glass,
          frame: white,
          bars: 1,
          head: 'pediment',
        });
        kit.windowRow(batch, e.a, e.b, Z2 + 0.6, {
          width: 1.0,
          height: 1.8,
          bay: 3.4,
          margin: 1.2,
          glass,
          frame: white,
          bars: 1,
        });
        if (e.len > 10) {
          const m = e.len / 2;
          T.ebox(stucco, e, m - 1.8, m + 1.8, 0, 2.2, 0, Z1);
          T.ebox(stuccoD, e, m - 2.0, m + 2.0, 0, 2.4, Z1, Z1 + 0.4);
          T.ebox(door, e, m - 0.8, m + 0.8, 2.2, 2.25, B0, B0 + 3.0);
          kit.colonnade(batch, stucco, T.at(e, m - 1.5, 2.3), T.at(e, m + 1.5, 2.3), 0, Z1, {
            count: 2,
            radius: 0.22,
            capital: 'doric',
          });
        }
      }
      // chimney stacks and flagpole with the Russian flag
      for (const [u, v] of [
        [F.u0 + 3, F.cv],
        [F.u1 - 3, F.cv],
      ]) {
        T.fbox(stucco, F, u, v, Z3, 2.4, 0.9, 3.6);
        T.fbox(stuccoD, F, u, v, Z3 + 3.6, 2.6, 1.1, 0.3);
      }
      const fp = T.at(front, front.len / 2, -1.0);
      T.cyl(white, fp[0], fp[1], Z3 + 1.0, 0.06, 0.04, 6, 6);
      const flag = kit.paintedMaterial(
        'russian_embassy:flag',
        96,
        64,
        (c, w, h) => {
          c.fillStyle = '#ffffff';
          c.fillRect(0, 0, w, h / 3);
          c.fillStyle = '#0039a6';
          c.fillRect(0, h / 3, w, h / 3);
          c.fillStyle = '#d52b1e';
          c.fillRect(0, (2 * h) / 3, w, h / 3);
        },
        { roughness: 0.8, side: THREE.DoubleSide },
      );
      const f0 = T.at(front, front.len / 2, -1.0),
        f1 = T.at(front, front.len / 2 + 2.1, -1.0);
      batch.quad(
        flag,
        [f0[0], f0[1], Z3 + 5.6],
        [f1[0], f1[1], Z3 + 5.6],
        [f1[0], f1[1], Z3 + 7.0],
        [f0[0], f0[1], Z3 + 7.0],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // ---- No. 5: consular section ---------------------------------------------------
    {
      const ring = T.ccw(byId['2dd73431-5edd-4d36-87b7-62f9beafbc60'].polys[0][0]);
      const Z3 = 11.0;
      kit.walls(batch, stucco, [[ring]], 0, Z3, { bay: 1e6 });
      kit.cornice(batch, stuccoD, ring, 0, { height: 0.9, projection: 0.1 });
      kit.cornice(batch, stuccoD, ring, 4.4, { height: 0.3, projection: 0.12 });
      kit.cornice(batch, stucco, ring, Z3 - 0.5, { height: 0.5, projection: 0.45, steps: 2 });
      kit.walls(batch, stucco, [[ring]], Z3, Z3 + 0.85, { bay: 1e6 });
      kit.cap(batch, kit.mat('#7d8184'), [[ring]], Z3 + 0.6);
      for (const e of T.edges(ring)) {
        if (e.len < 4) continue;
        const o = {
          bay: 3.2,
          margin: 1.0,
          glass,
          frame: white,
          bars: 1,
          surround: 0.18,
          surroundMat: stuccoD,
        };
        kit.windowRow(batch, e.a, e.b, 1.6, { ...o, width: 1.2, height: 2.3, head: 'arch' });
        kit.windowRow(batch, e.a, e.b, 5.4, { ...o, width: 1.2, height: 2.3, head: 'pediment' });
        kit.windowRow(batch, e.a, e.b, 8.5, { ...o, width: 1.0, height: 1.7 });
      }
    }
    g.add(batch.toGroup('russian_embassy'));
    return g;
  },
};
