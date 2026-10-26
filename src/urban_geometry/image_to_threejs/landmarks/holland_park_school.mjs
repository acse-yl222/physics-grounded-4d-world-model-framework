// Holland Park School, Airlie Gardens, Campden Hill (Aedas, 2010-12). A 1,500-pupil
// academy designed "not to look or feel like a school": a single north-south block of
// five storeys over a full basement (sports hall, 25 m pool), organised around a
// full-length central atrium with teaching wings either side. The west face, towards
// Holland Park, is wrapped in an undulating skin of bronze and copper fins; the east
// face has a curved wire-mesh brise soleil.
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
  id: 'holland_park_school',
  name: 'Holland Park School',
  claims: ['16be01b1-921e-42ed-963a-1820165e1ea3'],
  references: [
    {
      title: 'Holland Park School - Lang and Fulton',
      url: 'https://langandfulton.co.uk/projects/holland-park-school/',
      used_for: 'new six-storey school for 1,500 pupils',
    },
    {
      title: 'Holland Park School - Haver & Boecker',
      url: 'https://www.haverboecker.com/en/products/wire-mesh-products/architectural-wire-mesh/references/details/holland-park-school/',
      used_for:
        'undulating skin of bronze and copper fins (west), curved wire-mesh brise soleil (east)',
    },
    {
      title: 'Holland Park School, London - SteelConstruction.info',
      url: 'https://steelconstruction.info/Holland_Park_School,_London',
      used_for: 'five above-ground levels plus basement across the whole footprint, steel frame',
    },
    {
      title: 'Holland Park School - architectsdatafile',
      url: 'https://architectsdatafile.co.uk/?p=52821',
      used_for:
        'north-south block with full-length central atrium, classrooms east, specialist rooms and sports west',
    },
    {
      title: 'Holland Park School - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Holland_Park_School',
      used_for: 'school identity and location',
    },
  ],
  notes:
    'Five storeys of 4.2 m (21 m) above ground instead of the Overture 14.8 m. Fin pitch (0.6 m), undulation ' +
    'period (~24 m) and depth, the bronze/copper alternation, the mesh-band curvature on the east face, the ' +
    'atrium rooflight width (8 m) and the glazed ends are estimated from the descriptions; the basement is ' +
    'not visible and not modelled.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const ring = T.ccw(buildings[0].polys[0][0]);
    const E = T.edges(ring);
    const west = T.facing(E, [-0.94, -0.33], 30);
    const east = T.facing(E, [0.94, 0.33], 30);
    const ST = 4.2,
      NF = 5,
      H = ST * NF;
    const glass = kit.mat('#3a4b56', { roughness: 0.12, metalness: 0.4 });
    const panel = kit.mat('#d9d6cf', { roughness: 0.7 });
    const bronze = kit.mat('#8a5f38', { roughness: 0.45, metalness: 0.6 });
    const copper = kit.mat('#b07048', { roughness: 0.45, metalness: 0.55 });
    const mesh = kit.mat('#b9b3a6', {
      roughness: 0.5,
      metalness: 0.6,
      transparent: true,
      opacity: 0.65,
    });
    const mull = kit.mat('#4a4f52', { roughness: 0.5, metalness: 0.5 });
    const roofM = kit.mat('#8b8a86');
    const atr = kit.mat('#9fb8c4', {
      roughness: 0.1,
      metalness: 0.2,
      transparent: true,
      opacity: 0.7,
    });

    kit.walls(batch, glass, [[kit.offsetRing(ring, -0.4)]], 0, H, { bay: 1e6 });
    for (let f = 0; f <= NF; f++)
      kit.cornice(batch, panel, ring, f === 0 ? 0 : f * ST - 0.5, {
        height: f === NF ? 1.0 : 0.5,
        projection: 0.0,
      });
    for (const e of T.edges(kit.offsetRing(ring, -0.4))) {
      const n = Math.round(e.len / 1.5);
      for (let k = 0; k <= n; k++)
        T.ebox(mull, e, (k * e.len) / n - 0.04, (k * e.len) / n + 0.04, 0, 0.12, 0, H);
    }
    // west: undulating bronze and copper fins
    {
      const e = west;
      const n = Math.floor(e.len / 0.6);
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        const d = 0.5 + 0.45 * Math.sin((s / 24) * Math.PI * 2);
        const tw = 0.35 * Math.cos((s / 24) * Math.PI * 2);
        const c = T.at(e, s, 0.15 + d / 2);
        kit.box(
          batch,
          k % 3 === 1 ? copper : bronze,
          c[0],
          c[1],
          0.6,
          0.06,
          d,
          H - 0.6 + 0.4,
          e.ang + tw,
        );
      }
      T.ebox(panel, e, 0, e.len, 0, 1.2, H, H + 0.4);
    }
    // east: curved wire-mesh brise soleil bands at each floor
    {
      const e = east;
      const seg = 24;
      for (let f = 1; f <= NF; f++) {
        const z = f * ST - 1.8;
        for (let k = 0; k < seg; k++) {
          const s0 = (k * e.len) / seg,
            s1 = ((k + 1) * e.len) / seg;
          const bulge = (s) => 0.6 + 0.9 * Math.sin((s / e.len) * Math.PI);
          const p = T.at(e, s0, bulge(s0)),
            q = T.at(e, s1, bulge(s1));
          batch.quad(
            mesh,
            [p[0], p[1], z],
            [q[0], q[1], z],
            [q[0], q[1], z + 1.3],
            [p[0], p[1], z + 1.3],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          batch.quad(
            mesh,
            [q[0], q[1], z],
            [p[0], p[1], z],
            [p[0], p[1], z + 1.3],
            [q[0], q[1], z + 1.3],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
        }
        for (let s = 0; s <= e.len; s += e.len / 12) {
          const bu = 0.6 + 0.9 * Math.sin((s / e.len) * Math.PI);
          T.ebox(mull, e, s - 0.04, s + 0.04, 0, bu, z + 0.6, z + 0.7);
        }
      }
    }
    // roof with full-length atrium rooflight and plant
    kit.cap(batch, roofM, [[ring]], H);
    const F = T.frame(ring);
    const at = T.rect(F, F.u0 + 4, F.u1 - 4, F.cv - 4, F.cv + 4);
    kit.walls(batch, panel, [[at]], H, H + 0.8, { bay: 1e6 });
    kit.pitchedRoof(batch, atr, panel, at, F.angle, H + 0.8, 1.6, 'gabled', { overhang: 0 });
    for (const du of [-1, 1]) {
      const pl = T.rect(F, F.cu + du * 22 - 5, F.cu + du * 22 + 5, F.v1 - 9, F.v1 - 4.5);
      kit.walls(batch, kit.mat('#9c9a95'), [[pl]], H, H + 2.6, { bay: 1e6 });
      kit.cap(batch, roofM, [[pl]], H + 2.6);
    }
    g.add(batch.toGroup('holland_park_school'));
    return g;
  },
};
