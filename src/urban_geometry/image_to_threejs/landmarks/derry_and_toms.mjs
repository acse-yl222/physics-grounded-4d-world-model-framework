// Derry & Toms, 99-121 Kensington High Street (Bernard George for Barkers, 1929-33),
// with the Kensington Roof Gardens (Ralph Hancock, opened 1938) on top. Steel-framed
// Art Deco department store faced in Portland stone: a symmetrical High Street front
// of seven storeys, nine bays wide (2:5:2) divided by staircase bays, bronze glazing
// bars and shopfront, bronze panels between floors, splayed balconettes above the
// first floor, and a top storey treated as an entablature frieze with reliefs and
// Walter Gilbert's zodiac grilles. On the roof, the Spanish garden (white arcaded
// pavilions under pantiles, a canal), the Tudor garden and the English woodland garden.
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
  id: 'derry_and_toms',
  name: 'Derry & Toms and the Kensington Roof Gardens',
  claims: ['7e685d1e-46bc-44dd-a638-0950af3d4ba4'],
  references: [
    {
      title: 'Derry & Toms - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Derry_%26_Toms',
      used_for:
        'seven-storey Art Deco store opened 1933, Bernard George, Walter Gilbert metalwork, Mabey reliefs',
    },
    {
      title:
        'Marks and Spencers, British Home Stores and the Roof Garden - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101222781-marks-and-spencers-british-home-stores-and-the-roof-garden-queens-gate-ward',
      used_for:
        'Portland stone front and sides, bronze glazing bars and shopfront, 7 storeys 9 bays 2:5:2 divided by staircase bays, ' +
        'bronze panels between floors, splayed balconettes, top storey frieze with metopes and zodiac grilles',
    },
    {
      title: 'The Roof Garden, 99 High St, Kensington - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1001406',
      used_for: 'roof garden by Ralph Hancock covering the whole roof, opened May 1938',
    },
    {
      title: 'Kensington Roof Gardens - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Roof_Gardens',
      used_for: 'Spanish, Tudor and English woodland gardens on the roof',
    },
  ],
  notes:
    'Main roof at 24.5 m (seven storeys: 5.5 m shop floor, five 3.4 m floors and a 2 m frieze storey) instead ' +
    'of the Overture 23.2 m. The roof-garden pavilions follow the Overture roof parts, raised onto the roof ' +
    'slab; their arcades, pantiled hipped roofs and the woodland trees, lawns and canal are schematic. Bay ' +
    'widths are an even split of each facade; reliefs, metopes and zodiac grilles are reduced to stone ' +
    'panels and bronze grilles. Rear (party) walls are left plain.',
  build({ THREE, kit, buildings, scene, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b0 = buildings[0];
    const ring = T.ccw(b0.polys[0][0]);
    const nb = T.neighbours(scene, [b0.id], b0.c, 200);
    const rng = kit.rng(0.5133);

    const stone = kit.mat('#ddd5c2', { roughness: 0.8 });
    const stoneD = kit.mat('#c9c0aa', { roughness: 0.85 });
    const bronze = kit.mat('#5e4a33', { roughness: 0.45, metalness: 0.6 });
    const glass = kit.mat('#2c3a44', { roughness: 0.15, metalness: 0.35 });
    const shop = kit.mat('#40535f', { roughness: 0.1, metalness: 0.3 });
    const render = kit.mat('#f1ece0', { roughness: 0.85 });
    const pantile = kit.mat('#b0563a', { roughness: 0.8 });
    const grass = kit.mat('grass');
    const paving = kit.mat('#cbbfa6', { roughness: 0.9 });
    const water = kit.mat('water');
    const roofM = kit.mat('#8b8a86');
    const G0 = 5.5,
      ST = 3.4,
      NF = 5,
      FR = G0 + NF * ST, // 22.5: frieze storey
      ROOF = 24.5;

    kit.walls(batch, stone, [[ring]], 0, ROOF + 1.1, { bay: 1e6 });
    kit.cap(batch, roofM, [[ring]], ROOF);
    const pin = kit.offsetRing(ring, -0.35);
    kit.walls(batch, stone, [[pin.slice().reverse()]], ROOF, ROOF + 1.1, { bay: 1e6 });
    kit.cap(batch, stone, [[ring, pin.slice().reverse()]], ROOF + 1.1);
    kit.cornice(batch, stoneD, ring, FR - 0.6, { height: 0.6, projection: 0.45, steps: 2 });
    kit.cornice(batch, stoneD, ring, ROOF + 0.6, { height: 0.5, projection: 0.35 });
    kit.cornice(batch, stoneD, ring, G0 - 0.5, { height: 0.5, projection: 0.3 });

    const E = T.edges(ring);
    const front = T.facing(E, [-0.56, 0.83], 20);
    for (const e of E) {
      if (e.len < 4 || !T.exposed(e, nb)) continue;
      const isFront = e === front;
      // bay layout: front 2:5:2 with two staircase bays, others even
      let bays = [];
      if (isFront) {
        const sw = 5.5,
          bw = (e.len - 2 * sw) / 9;
        let s = 0;
        for (let k = 0; k < 9; k++) {
          bays.push({ s0: s, s1: s + bw, stair: false });
          s += bw;
          if (k === 1 || k === 6) {
            bays.push({ s0: s, s1: s + sw, stair: true });
            s += sw;
          }
        }
      } else {
        const n = Math.max(1, Math.round(e.len / 6.5));
        for (let k = 0; k < n; k++) bays.push({ s0: (k * e.len) / n, s1: ((k + 1) * e.len) / n });
      }
      // ground floor: bronze shopfront recessed under a cantilevered canopy
      T.ebox(shop, e, 0.2, e.len - 0.2, -0.3, 0.02, 0.4, G0 - 1.2);
      for (const bay of bays) {
        T.ebox(stoneD, e, bay.s0 - 0.35, bay.s0 + 0.35, 0, 0.35, 0, G0);
        T.ebox(bronze, e, bay.s0 + 0.4, bay.s1 - 0.4, 0.02, 0.1, G0 - 1.3, G0 - 0.6);
        T.ebox(
          bronze,
          e,
          (bay.s0 + bay.s1) / 2 - 0.05,
          (bay.s0 + bay.s1) / 2 + 0.05,
          0,
          0.08,
          0.4,
          G0 - 1.3,
        );
      }
      if (isFront || e.len > 20) {
        T.ebox(stoneD, e, 0, e.len, 0, 2.2, G0 - 1.9, G0 - 1.5);
        T.ebox(bronze, e, 0, e.len, 2.1, 2.25, G0 - 2.0, G0 - 1.45);
      }
      for (const bay of bays) {
        const w = bay.s1 - bay.s0;
        const a = T.at(e, bay.s0),
          b = T.at(e, bay.s1);
        if (bay.stair) {
          // staircase bay: tall vertical strip window, projecting stone fins
          T.ebox(stone, e, bay.s0, bay.s1, 0, 0.6, G0, FR);
          const p = T.at(e, bay.s0, 0.6),
            q = T.at(e, bay.s1, 0.6);
          kit.windowRow(batch, p, q, G0 + 1.2, {
            count: 1,
            width: 1.6,
            height: FR - G0 - 2.4,
            glass,
            frame: bronze,
            bars: 8,
            head: 'none',
            margin: 0,
          });
          continue;
        }
        // stone piers between bays
        T.ebox(stone, e, bay.s0 - 0.45, bay.s0 + 0.45, 0, 0.4, G0, FR);
        for (let f = 0; f < NF; f++) {
          const z = G0 + f * ST;
          kit.windowRow(batch, a, b, z + 0.75, {
            count: 2,
            width: Math.min(2.6, w * 0.36),
            height: 2.15,
            glass,
            frame: bronze,
            bars: 1,
            head: 'none',
            margin: 0.6,
            depth: 0.1,
          });
          // bronze spandrel panel under each window
          T.ebox(bronze, e, bay.s0 + 0.9, bay.s1 - 0.9, 0.02, 0.07, z + 0.1, z + 0.6);
          if (f === 0 && isFront) {
            // splayed balconette above the first floor
            T.ebox(stoneD, e, bay.s0 + 0.8, bay.s1 - 0.8, 0, 0.7, z + ST - 0.05, z + ST + 0.15);
            T.ebox(bronze, e, bay.s0 + 0.8, bay.s1 - 0.8, 0.62, 0.68, z + ST + 0.15, z + ST + 1.0);
          }
        }
        // frieze storey: relief panel and bronze zodiac grilles over small windows
        kit.windowRow(batch, a, b, FR + 0.25, {
          count: 2,
          width: Math.min(2.2, w * 0.3),
          height: 1.3,
          glass: bronze,
          frame: bronze,
          bars: 1,
          head: 'none',
          margin: 0.8,
        });
        T.ebox(
          stoneD,
          e,
          (bay.s0 + bay.s1) / 2 - 0.5,
          (bay.s0 + bay.s1) / 2 + 0.5,
          0,
          0.15,
          FR + 0.2,
          FR + 1.7,
        );
      }
      // name band over the canopy on the front
    }
    // rear and party walls: string courses only (already continuous cornices)

    // ---- roof garden -------------------------------------------------------------
    const lawn = kit.offsetRing(ring, -2.5);
    kit.cap(batch, grass, [[lawn]], ROOF + 0.25);
    kit.walls(batch, stoneD, [[lawn]], ROOF, ROOF + 0.25, { bay: 1e6 });
    const pav = [];
    const dz = ROOF - (b0.h ?? 23.2);
    for (const p of b0.parts ?? []) {
      const r = T.ccw(p.polys[0][0]);
      const z0 = ROOF + 0.25,
        z1 = Math.max(z0 + 3.2, (p.h ?? 26) + dz);
      pav.push(r);
      kit.walls(batch, render, [[r]], z0, z1, { bay: 1e6 });
      kit.cornice(batch, render, r, z1 - 0.3, { height: 0.3, projection: 0.2 });
      kit.cap(batch, roofM, [[r]], z1);
      const F = T.frame(r);
      if (F.W > 2 && F.W < 14 && F.L < 60)
        kit.pitchedRoof(
          batch,
          pantile,
          render,
          r,
          F.angle,
          z1,
          Math.min(2.6, F.W * 0.3),
          'hipped',
          {
            overhang: 0.4,
          },
        );
      // arcades of round arches on each edge
      for (const e of T.edges(r))
        if (e.len > 3)
          kit.windowRow(batch, e.a, e.b, z0, {
            width: 1.6,
            height: Math.min(2.6, z1 - z0 - 0.6),
            bay: 2.4,
            margin: 0.5,
            head: 'arch',
            glass: kit.mat('#3b342c'),
            frame: render,
            bars: 0,
          });
    }
    // paths, a canal (Spanish garden) and woodland trees
    const F = T.frame(ring);
    const canal = T.rect(F, F.cu - 10, F.cu + 10, F.cv - 0.9, F.cv + 0.9);
    if (canal.every((p) => T.inside(p, lawn))) {
      kit.cap(batch, paving, [[kit.offsetRing(canal, 1.2)]], ROOF + 0.3);
      kit.cap(batch, water, [[canal]], ROOF + 0.33);
    }
    const trees = [];
    for (let k = 0; k < 200 && trees.length < 24; k++) {
      const u = F.u0 + 4 + rng() * (F.L - 8),
        v = F.v0 + 4 + rng() * (F.W - 8);
      const p = F.w(u, v);
      if (!T.inside(p, kit.offsetRing(lawn, -2))) continue;
      if (pav.some((r) => T.inside(p, kit.offsetRing(r, 3)))) continue;
      if (Math.abs(v - F.cv) < 3.5 && Math.abs(u - F.cu) < 13) continue;
      if (trees.some((t) => Math.hypot(t[0] - p[0], t[1] - p[1]) < 4.5)) continue;
      trees.push([p[0], p[1], rng() * 6.28]);
    }
    const half = Math.ceil(trees.length / 2);
    g.add(
      placeAssets('english_oak', trees.slice(0, half), {
        scaleOf: () => 6 + rng() * 2,
        z: ROOF + 0.25,
        detail: 'low',
      }),
    );
    g.add(
      placeAssets('silver_birch', trees.slice(half), {
        scaleOf: () => 6 + rng() * 2,
        z: ROOF + 0.25,
        detail: 'low',
      }),
    );

    g.add(batch.toGroup('derry_and_toms'));
    return g;
  },
};
