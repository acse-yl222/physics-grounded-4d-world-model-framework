// The Electric Cinema, 191 Portobello Road (Gerald Seymour Valentin, 1910-11; one of
// the oldest working cinemas in Britain). Edwardian Baroque front faced in glazed white
// faience tiles over machine brick with a rendered upper floor: Ionic pilasters and
// Baroque swags on the ground floor, a central raised bay, and a small dome on the
// upper storey to one side; behind it the brick auditorium under a low pitched roof.
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
  id: 'electric_cinema',
  name: 'Electric Cinema',
  claims: ['81045757-e336-417f-98a6-7db78a4259e1'],
  references: [
    {
      title: 'The Electric Cinema - Historic England',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1266083',
      used_for: 'Grade II*, 1910-12 by G S Valentin',
    },
    {
      title: 'The Electric Cinema - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=423089',
      used_for:
        'glazed white tile front over machine brick, rendered upper floor, Ionic pilasters and Baroque swags to ground floor, ' +
        'dome on upper storey to one side of the central bay',
    },
    {
      title: 'Electric Cinema, Notting Hill - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Electric_Cinema,_Notting_Hill',
      used_for: 'architect Gerald Seymour Valentin, opening 1910',
    },
    {
      title: 'Designer icon: Electric Cinema - Livingetc',
      url: 'https://www.livingetc.com/spaces/design-destination/designer-icon-electric-cinema-london-188233',
      used_for: 'domed corner roof as the telltale feature',
    },
  ],
  notes:
    'Front 10.5 m high with the raised central bay to 12.2 m and the dome (on the Overture round part at the ' +
    'south end of the front) to ~15 m; the auditorium eaves at 9 m under a 2.5 m pitched roof. Pilaster count, ' +
    'swags (reduced to small panels), the red name sign and canopy, and the dome profile are estimated.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const E = T.edges(ring);
    const front = T.facing(E, [0.94, 0.33], 10);
    const tile = kit.mat('#f3f1ea', { roughness: 0.35 });
    const renderM = kit.mat('#ebe5d6', { roughness: 0.8 });
    const brick = kit.mat('#8a5a44', { roughness: 0.92 });
    const glass = kit.mat('#2c363e', { roughness: 0.2, metalness: 0.3 });
    const white = kit.mat('white');
    const lead = kit.mat('#6c7577', { roughness: 0.55, metalness: 0.3 });
    const slate = kit.mat('slate');
    const door = kit.mat('#4a1f1c');
    const HF = 10.5,
      G1 = 4.6;

    // auditorium
    kit.walls(batch, brick, [[ring]], 0, 9, { bay: 1e6 });
    kit.cap(batch, kit.mat('#7d8184'), [[ring]], 9);
    const F = T.frame(ring, front.ang + Math.PI / 2);
    kit.pitchedRoof(batch, slate, brick, kit.offsetRing(ring, -0.3), F.angle, 9, 2.5, 'gabled', {
      overhang: 0.2,
    });
    // front block (3.5 m deep) in faience and render
    const W = front.len;
    const fr = T.ccw([
      T.at(front, 0, 0.2),
      T.at(front, W, 0.2),
      T.at(front, W, -3.5),
      T.at(front, 0, -3.5),
    ]);
    kit.walls(batch, tile, [[fr]], 0, G1, { bay: 1e6 });
    kit.walls(batch, renderM, [[fr]], G1, HF, { bay: 1e6 });
    kit.cap(batch, kit.mat('#7d8184'), [[fr]], HF);
    kit.cornice(batch, tile, fr, G1 - 0.3, { height: 0.4, projection: 0.25 });
    kit.cornice(batch, renderM, fr, HF - 0.6, { height: 0.6, projection: 0.4, steps: 2 });
    const fe = front;
    const d0 = 0.2;
    // ground floor: Ionic pilasters, swags, central entrance
    const n = 6;
    for (let k = 0; k <= n; k++) {
      const s = (k * W) / n;
      T.ebox(tile, fe, s - 0.28, s + 0.28, d0, d0 + 0.3, 0, G1 - 0.3);
      T.ebox(tile, fe, s - 0.4, s + 0.4, d0, d0 + 0.38, G1 - 0.75, G1 - 0.45); // volute capital
      if (k < n) T.ebox(tile, fe, s + 0.6, s + W / n - 0.6, d0, d0 + 0.15, G1 - 1.2, G1 - 0.75); // swag panel
    }
    T.ebox(door, fe, W / 2 - 2.2, W / 2 + 2.2, d0 - 0.05, d0 + 0.02, 0, 3.0);
    for (const s of [W / 2 - 5, W / 2 + 5])
      T.ebox(glass, fe, s - 1.2, s + 1.2, d0, d0 + 0.03, 0.8, 3.0);
    // canopy and red ELECTRIC sign
    T.ebox(renderM, fe, W / 2 - 3.6, W / 2 + 3.6, d0, d0 + 1.6, 3.15, 3.45);
    const sign = kit.paintedMaterial(
      'electric_cinema:sign',
      512,
      96,
      (c, w, h) => {
        c.fillStyle = '#f3f1ea';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#c0281f';
        c.font = 'bold 64px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('ELECTRIC', w / 2, h / 2 + 4);
      },
      { roughness: 0.5 },
    );
    const sa = T.at(fe, W / 2 - 3.4, d0 + 0.06),
      sb = T.at(fe, W / 2 + 3.4, d0 + 0.06);
    batch.quad(
      sign,
      [sa[0], sa[1], G1 + 0.2],
      [sb[0], sb[1], G1 + 0.2],
      [sb[0], sb[1], G1 + 1.4],
      [sa[0], sa[1], G1 + 1.4],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );
    // upper floor windows, raised central bay with pediment
    kit.windowRow(batch, T.at(fe, 0, d0), T.at(fe, W, d0), G1 + 1.7, {
      count: 5,
      width: 1.3,
      height: 2.2,
      glass,
      frame: white,
      bars: 1,
      head: 'segment',
      margin: 1.2,
      surround: 0.2,
      surroundMat: tile,
    });
    T.ebox(renderM, fe, W / 2 - 3, W / 2 + 3, d0 - 0.2, d0 + 0.1, HF, HF + 1.3);
    {
      const a = T.at(fe, W / 2 - 3.2, d0 + 0.1),
        b = T.at(fe, W / 2 + 3.2, d0 + 0.1),
        m = T.at(fe, W / 2, d0 + 0.1);
      batch.add(
        renderM,
        [
          [a[0], a[1], HF + 1.3],
          [b[0], b[1], HF + 1.3],
          [m[0], m[1], HF + 2.4],
        ],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
    }
    // dome on the round part
    const pr = (b0.parts ?? [])[0];
    const pts = pr ? pr.polys[0][0] : [T.at(fe, 2, -1.5)];
    const c = [
      pts.reduce((s, p) => s + p[0], 0) / pts.length,
      pts.reduce((s, p) => s + p[1], 0) / pts.length,
    ];
    const R = pr
      ? Math.max(1.6, Math.max(...pts.map((p) => Math.hypot(p[0] - c[0], p[1] - c[1]))))
      : 2.2;
    T.cyl(renderM, c[0], c[1], HF - 0.6, R, R, 1.6, 16);
    T.cyl(tile, c[0], c[1], HF + 1.0, R + 0.2, R + 0.2, 0.3, 16);
    T.lathe(
      lead,
      [
        [R, 0],
        [R * 0.95, 0.7],
        [R * 0.75, 1.5],
        [R * 0.4, 2.2],
        [0, 2.4],
      ],
      c[0],
      c[1],
      HF + 1.3,
      16,
    );
    T.cyl(tile, c[0], c[1], HF + 3.6, 0.3, 0.2, 0.8, 8);
    T.cyl(lead, c[0], c[1], HF + 4.4, 0.06, 0.03, 0.9, 6);
    g.add(batch.toGroup('electric_cinema'));
    return g;
  },
};
