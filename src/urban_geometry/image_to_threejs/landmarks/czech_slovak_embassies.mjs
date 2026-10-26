// Czech and Slovak Embassies, 26-30 Kensington Palace Gardens / Notting Hill Gate
// (Jan Bočan, Jan Šrámek and Karel Štěpánský with Robert Matthew, Johnson-Marshall &
// Partners, 1965-70; RIBA award). The former Czechoslovak embassy, shared by the two
// states since 1993: a Brutalist concrete skeleton punctuated by banks of dark glass -
// a long slab along Notting Hill Gate over a recessed base and a lower block to the
// south - with Stanislav Kolíbal's curved concrete wall facing Notting Hill Gate.
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
  id: 'czech_slovak_embassies',
  name: 'Czech and Slovak Embassies',
  claims: ['2ec1ce3d-f03e-4ce0-926b-d24f1eaecc00', 'd8212253-04f9-4470-b4a7-6f1bf09cd77e'],
  references: [
    {
      title: 'Embassy of the Czech Republic, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Embassy_of_the_Czech_Republic,_London',
      used_for:
        'Brutalist building begun 1965, architects Bočan, Šrámek and Štěpánský, shared with Slovakia, RIBA award',
    },
    {
      title: 'Czech and Slovak Embassies - C20 Society',
      url: 'https://c20society.org.uk/botm/czech-and-slovak-embassies-london/',
      used_for: '1965-70, statement of the new style adopted by Czech architects: Brutalism',
    },
    {
      title: 'Czechoslovak Embassies Under Communism - Sigmar',
      url: 'https://www.sigmarlondon.com/products/czechoslovak-embassies-under-communism',
      used_for: 'concrete skeleton punctuated by banks of glass; RMJM collaboration',
    },
    {
      title: 'Czech and Slovak Embassies - Mainstream Modern',
      url: 'https://mainstreammodern.co.uk/CaseStudies.aspx/Detail/229/czech-and-slovak-embassies',
      used_for: 'curved concrete wall facing Notting Hill Gate by Stanislav Kolíbal',
    },
    {
      title: 'About the embassy building - Embassy of the Czech Republic in London',
      url: 'https://mzv.gov.cz/london/en/about_us/about_the_embassy_building/x26_30_kensington_palace_gardens.html',
      used_for: 'address 26-30 Kensington Palace Gardens, Czechoslovak embassy there from 1970',
    },
  ],
  notes:
    'Heights from Overture (slab 23.2 m as six 3.6 m storeys over a 1.6 m plinth; south block 13.6 m). The ' +
    'facade rhythm - ribbed precast spandrels, slender mullions with deep fins every 7.2 m and dark bronze glazing bands - and ' +
    'the recessed ground floor are a generic reading of the "concrete skeleton with banks of glass"; the ' +
    'Kolíbal wall is placed along the slab front with an assumed 20 m length and 3 m height.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const conc = kit.mat('#b9b4aa', { roughness: 0.95 });
    const concD = kit.mat('#8f8b83', { roughness: 0.95 });
    const glass = kit.mat('#2a2d2c', { roughness: 0.1, metalness: 0.5 });
    const bronzeGl = kit.mat('#4a3e33', { roughness: 0.12, metalness: 0.5 });
    const roofM = kit.mat('#8b8a86');

    const block = (ring, H, plinth, ST) => {
      const rec = kit.offsetRing(ring, -2.0);
      kit.walls(batch, glass, [[rec]], 0, plinth + ST, { bay: 1e6 });
      kit.cap(batch, concD, [[ring]], plinth + ST, { down: true });
      for (const e of T.edges(ring)) {
        if (e.len < 6) continue;
        const n = Math.round(e.len / 7.2);
        for (let k = 0; k <= n; k++) {
          const s = 0.6 + ((e.len - 1.2) * k) / n;
          T.ebox(conc, e, s - 0.45, s + 0.45, -2.4, -1.5, 0, plinth + ST);
        }
      }
      const nf = Math.round((H - plinth - ST) / ST);
      const inner = kit.offsetRing(ring, -0.6);
      kit.walls(batch, bronzeGl, [[inner]], plinth + ST, H, { bay: 1e6 });
      for (let f = 0; f <= nf; f++) {
        const z = plinth + ST + f * ST;
        kit.cornice(batch, conc, ring, z - 0.05, {
          height: f === nf ? H - z + 0.05 : 1.15,
          projection: 0.0,
        });
      }
      kit.cap(batch, roofM, [[ring]], H);
      for (const e of T.edges(ring)) {
        if (e.len < 3) continue;
        const n = Math.round(e.len / 1.8);
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          // slender mullion ribs in the glazing, deep precast fins every 7.2 m
          if (k % 4 === 0) T.ebox(conc, e, s - 0.2, s + 0.2, -0.6, 0.7, plinth + ST, H);
          else T.ebox(concD, e, s - 0.06, s + 0.06, -0.6, -0.45, plinth + ST, H);
        }
      }
    };
    const czech = T.ccw(byId['2ec1ce3d-f03e-4ce0-926b-d24f1eaecc00'].polys[0][0]);
    const slovak = T.ccw(byId['d8212253-04f9-4470-b4a7-6f1bf09cd77e'].polys[0][0]);
    block(czech, 23.2, 1.6, 3.6);
    block(slovak, 13.6, 1.6, 3.6);
    // roof plant on the slab
    const F = T.frame(czech);
    const pl = T.rect(F, F.cu - 9, F.cu + 9, F.v0 + 3, F.v1 - 3);
    kit.walls(batch, concD, [[pl]], 23.2, 26.2, { bay: 1e6 });
    kit.cap(batch, roofM, [[pl]], 26.2);
    // Kolíbal's curved wall in front of the north face
    const north = T.facing(T.edges(czech), [-0.3, 0.95], 20);
    const seg = 16,
      L = 20,
      s0 = north.len / 2 - L / 2;
    for (let k = 0; k < seg; k++) {
      const sa = s0 + (k * L) / seg,
        sb = s0 + ((k + 1) * L) / seg;
      const off = (s) => 4 + 2.5 * Math.sin(((s - s0) / L) * Math.PI);
      const p = T.at(north, sa, off(sa)),
        q = T.at(north, sb, off(sb));
      const m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
      kit.box(
        batch,
        conc,
        m[0],
        m[1],
        0,
        Math.hypot(q[0] - p[0], q[1] - p[1]) + 0.05,
        0.4,
        3.0,
        Math.atan2(q[1] - p[1], q[0] - p[0]),
      );
    }
    g.add(batch.toGroup('czech_slovak_embassies'));
    return g;
  },
};
