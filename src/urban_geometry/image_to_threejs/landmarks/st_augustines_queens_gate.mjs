// St Augustine's, Queen's Gate, South Kensington (William Butterfield, 1865-77). Grade
// II* Anglican church in yellow brick with bands of red and black brick and stone: a
// five-bay aisled nave and chancel under a steep slate roof, the west front to Queen's
// Gate with a Gothic bellcote flanked by pinnacles. The rich polychromy was whitewashed
// in the 20th century and has since been restored.
export default {
  id: 'st_augustines_queens_gate',
  name: "St Augustine's, Queen's Gate",
  claims: ['e49f8324-a028-4223-b1ec-c909ec4b0da3'],
  references: [
    {
      title:
        'Church of St Augustine - British Listed Buildings (Historic England list entry 1226161)',
      url: 'https://britishlistedbuildings.co.uk/101226161-church-of-st-augustine-courtfield-ward',
      used_for:
        'Butterfield 1865; yellow brick with red and black brick and stone bands; Gothic bellcote flanked by pinnacles at the west end; five-bay aisled nave; polychromy repainted after whitewash',
    },
    {
      title: "St Augustine's, Queen's Gate - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Augustine%27s,_Queen%27s_Gate',
      used_for: "Grade II*, Butterfield, Queen's Gate site",
    },
    {
      title: "St Augustine's Queen's Gate - victorianweb.org",
      url: 'https://victorianweb.org/art/architecture/butterfield/16.html',
      used_for: 'listing text reproduction',
    },
  ],
  notes:
    "Church aligned with the footprint long axis (~25 deg), west front on Queen's Gate. Section (aisles 7.5 m, " +
    'clerestory 15 m, steep roof ridge 23.5 m), the band spacing, window sizes and the bellcote height are ' +
    'estimates; the stepped west footprint edges (porches/buttresses) are walls with buttresses. Polychrome ' +
    'banding is modelled as thin projecting courses of red and black brick and stone on the yellow brick.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b = byId['e49f8324-a028-4223-b1ec-c909ec4b0da3'];
    if (!b) return g;
    const th = (24.8 * Math.PI) / 180;
    const ringW = T.ccw(b.polys[0][0]);
    const ext = kit.orientedExtent(ringW, th);
    const vm = (ext.v0 + ext.v1) / 2;
    const O = ext.at(ext.u0, vm, 0);
    g.position.set(O[0], O[1], 0);
    g.rotation.z = th;
    const c = Math.cos(th),
      s = Math.sin(th);
    const loc = ([x, y]) => [(x - O[0]) * c + (y - O[1]) * s, -(x - O[0]) * s + (y - O[1]) * c];
    const ring = T.ccw(ringW.map(loc));
    const L = ext.u1 - ext.u0,
      W2 = (ext.v1 - ext.v0) / 2;
    const yellow = kit.mat('#cfb57c', { roughness: 0.9 });
    const red = kit.mat('#8e3a2b', { roughness: 0.9 });
    const black = kit.mat('#2c2828', { roughness: 0.9 });
    const stone = kit.mat('#ddd3bd', { roughness: 0.85 });
    const slate = kit.mat('#525860', { roughness: 0.8 });
    const glass = kit.mat('#383d4a', { roughness: 0.2, metalness: 0.3 });
    const ZA = 7.5,
      ZC = 15.0,
      NV = 5.2,
      ZR = 23.5;
    // aisles: the footprint walls
    kit.walls(batch, yellow, [[ring]], 0, ZA);
    kit.cornice(batch, stone, ring, 0, { height: 0.6, projection: 0.12 });
    const bands = (rg, z0, z1) => {
      for (let z = z0 + 1.0, i = 0; z < z1 - 0.4; z += 1.1, i++)
        kit.cornice(batch, i % 3 === 2 ? stone : i % 2 ? black : red, rg, z, {
          height: i % 3 === 2 ? 0.22 : 0.3,
          projection: 0.02,
        });
    };
    bands(ring, 0, ZA);
    kit.cornice(batch, stone, ring, ZA - 0.35, { height: 0.35, projection: 0.2 });
    // aisle lean-to roofs
    for (const [v0, v1] of [
      [NV, W2 + 0.3],
      [-NV, -W2 - 0.3],
    ])
      batch.add(
        slate,
        [
          [0.3, v1, ZA],
          [L, v1, ZA],
          [L, v0, ZA + 3.2],
          [0.3, v0, ZA + 3.2],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        v0 > 0 ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3],
      );
    // nave + chancel clerestory, polychrome bands, steep roof
    const nave = [
      [0.3, -NV],
      [L - 0.2, -NV],
      [L - 0.2, NV],
      [0.3, NV],
    ];
    kit.walls(batch, yellow, [[nave]], ZA, ZC);
    bands(nave, ZA + 2, ZC);
    kit.cornice(batch, stone, nave, ZC - 0.35, { height: 0.35, projection: 0.2 });
    T.gableRoof(
      slate,
      yellow,
      { a: [0.3, -NV], b: [L - 0.2, -NV], len: L - 0.5, dx: 1, dy: 0, nx: 0, ny: -1, ang: 0 },
      0,
      L - 0.5,
      0,
      -2 * NV,
      ZC,
      ZR - ZC,
      0.35,
    );
    kit.box(batch, kit.mat('#8a3b2a'), L / 2, 0, ZR - 0.05, L - 1, 0.25, 0.3); // red ridge tiles
    // clerestory windows (paired lancets per bay) and aisle windows
    const bay = (L - 4) / 7;
    for (const side of [-1, 1]) {
      const a = side > 0 ? [L - 2, NV] : [2, -NV],
        b2 = side > 0 ? [2, NV] : [L - 2, -NV];
      kit.windowRow(batch, a, b2, ZA + 3.6, {
        width: 0.6,
        height: 2.4,
        count: 14,
        margin: 0.2,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 0,
      });
      const a2 = side > 0 ? [L - 2, W2] : [2, -W2],
        b3 = side > 0 ? [2, W2] : [L - 2, -W2];
      kit.windowRow(batch, a2, b3, 2.4, {
        width: 1.5,
        height: 3.4,
        count: 7,
        margin: 0.4,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 1,
      });
      // buttresses
      for (let k = 0; k <= 7; k++)
        kit.box(batch, yellow, 2 + k * bay, side * (W2 + 0.45), 0, 0.7, 0.9, ZA - 1.2);
    }
    // east window
    kit.windowRow(batch, [L - 0.15, -2.4], [L - 0.15, 2.4], ZA + 1.0, {
      width: 4.0,
      height: 6.0,
      count: 1,
      glass,
      frame: stone,
      sill: stone,
      head: 'arch',
      bars: 2,
      depth: 0.2,
    });
    // west front: gable with banding, great window, bellcote flanked by pinnacles
    {
      kit.box(batch, yellow, 0.0, 0, ZA, 0.6, 2 * NV + 0.4, ZC - ZA + 0.3);
      const z0 = ZC + 0.3;
      T.tri(yellow, [-0.3, NV + 0.2, z0], [-0.3, -NV - 0.2, z0], [-0.3, 0, ZR + 0.5]);
      T.tri(yellow, [0.3, -NV - 0.2, z0], [0.3, NV + 0.2, z0], [0.3, 0, ZR + 0.5]);
      // chequer/diaper band in red and black across the gable
      for (let i = -4; i <= 4; i++)
        kit.box(batch, i % 2 ? red : black, -0.33, i * 1.0, ZC + 0.6, 0.06, 0.95, 0.5);
      for (let z = ZA + 0.8, i = 0; z < ZC; z += 1.1, i++)
        kit.box(batch, i % 2 ? red : black, -0.32, 0, z, 0.05, 2 * NV + 0.4, 0.28);
      kit.windowRow(batch, [-0.3, 3.0], [-0.3, -3.0], ZA + 0.6, {
        width: 4.8,
        height: 4.8,
        count: 1,
        glass,
        frame: stone,
        sill: stone,
        head: 'arch',
        bars: 2,
        depth: 0.25,
      });
      // stone coping on the gable
      for (const sg of [-1, 1]) {
        const len = Math.hypot(NV + 0.2, ZR + 0.5 - z0);
        const bx = new THREE.BoxGeometry(0.9, len + 0.3, 0.3);
        const m = new THREE.Matrix4()
          .makeTranslation(-0.05, (sg * (NV + 0.2)) / 2, (z0 + ZR + 0.5) / 2)
          .multiply(new THREE.Matrix4().makeRotationX(-sg * Math.atan2(ZR + 0.5 - z0, NV + 0.2)));
        batch.addGeometry(stone, bx, m);
        bx.dispose();
      }
      // bellcote
      kit.box(batch, stone, 0, 0, ZR + 0.2, 1.0, 2.4, 3.6);
      for (const dv of [-0.5, 0.5])
        kit.box(batch, kit.mat('#1e2024'), 0, dv, ZR + 1.0, 1.02, 0.6, 1.8);
      const cap = new THREE.ConeGeometry(1.3, 2.4, 4).rotateX(Math.PI / 2).rotateZ(Math.PI / 4);
      batch.addGeometry(stone, cap, T.M(0, 0, ZR + 5.0));
      cap.dispose();
      T.cyl(kit.mat('#3a3d40', { metalness: 0.6 }), 0, 0, ZR + 6.2, 1.0, 0.04, 0.04, 6);
      // flanking pinnacles and corner buttresses of the nave front
      for (const sg of [-1, 1]) {
        kit.box(batch, yellow, -0.5, sg * (NV + 0.3), 0, 1.2, 1.2, ZC + 1.0);
        const pn = new THREE.ConeGeometry(0.7, 3.4, 4).rotateX(Math.PI / 2).rotateZ(Math.PI / 4);
        batch.addGeometry(stone, pn, T.M(-0.5, sg * (NV + 0.3), ZC + 2.7));
        pn.dispose();
      }
      // west door
      kit.box(batch, stone, -0.5, 0, 0, 0.6, 3.2, 4.0);
      kit.box(batch, kit.mat('#3b2a1f'), -0.82, 0, 0, 0.06, 2.0, 3.2);
    }
    g.add(batch.toGroup('st_augustines_queens_gate'));
    return g;
  },
};

// ---- local geometry helpers (modules have no imports) -------------------------------
function tools(THREE, kit, batch) {
  const ccw = (r) => {
    r = r.slice();
    if (kit.ringArea(r) < 0) r.reverse();
    return r;
  };
  const edges = (r) =>
    r.map((a, k) => {
      const b = r[(k + 1) % r.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        a,
        b,
        k,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
      };
    });
  // point along edge e at distance s, offset d outward
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  // box aligned with edge e: s0..s1 along, d0..d1 outward, z0..z1
  const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
    const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(
      batch,
      m,
      p[0],
      p[1],
      z0,
      Math.max(0.01, s1 - s0),
      Math.max(0.01, d1 - d0),
      Math.max(0.01, z1 - z0),
      e.ang,
      c,
    );
  };
  const prism = (m, ring, z0, z1, opts) => {
    kit.walls(batch, m, [[ring]], z0, z1, opts);
    kit.cap(batch, m, [[ring]], z1);
  };
  const M = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
  const cyl = (m, x, y, z0, h, r0, r1 = r0, seg = 12) => {
    const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z0 + h / 2));
    g.dispose();
  };
  const lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(Math.max(0.001, r), h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z));
    g.dispose();
  };
  // windows on the sub-span s0..s1 of edge e
  const win = (e, s0, s1, z, opts) => kit.windowRow(batch, at(e, s0), at(e, s1), z, opts);
  const quad = (m, p, q, z0, z1, c) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      c,
    );
  const tri = (m, p, q, r, c) =>
    batch.add(
      m,
      [p, q, r],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
      c,
    );
  // sloped band from ring at z0 to the ring inset by d at z1 (mansards, hips); returns inner ring
  const slope = (m, ring, z0, d, z1, capTop = true) => {
    const inn = kit.offsetRing(ring, -d);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inn[(k + 1) % ring.length],
        e = inn[k];
      batch.add(
        m,
        [
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [e[0], e[1], z1],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    if (capTop) kit.cap(batch, m, [[inn]], z1);
    return inn;
  };
  // pitched gable roof over an edge-aligned rectangle: along e from s0..s1, depth d0..d1 (outward
  // negative = inward), ridge parallel to e. Gable triangles in wall material.
  const gableRoof = (roofM, wallM, e, s0, s1, d0, d1, z, rise, ov = 0.3) => {
    const dm = (d0 + d1) / 2;
    const P = (s, d, zz) => {
      const p = at(e, s, d);
      return [p[0], p[1], zz];
    };
    const A = P(s0 - ov, d0 - ov * Math.sign(d1 - d0), z),
      B = P(s1 + ov, d0 - ov * Math.sign(d1 - d0), z);
    const C = P(s1 + ov, dm, z + rise),
      D = P(s0 - ov, dm, z + rise);
    const A2 = P(s0 - ov, d1 + ov * Math.sign(d1 - d0), z),
      B2 = P(s1 + ov, d1 + ov * Math.sign(d1 - d0), z);
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    // undersides so the roof reads from below/behind
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    for (const s of [s0, s1]) {
      const p = P(s, d0, z),
        q = P(s, d1, z),
        r = P(s, dm, z + rise);
      tri(wallM, p, q, r);
      tri(wallM, q, p, r);
    }
  };
  const hasRoad = (e) => e; // placeholder for symmetry
  return { ccw, edges, at, ebox, prism, cyl, lathe, win, quad, tri, slope, gableRoof, M, hasRoad };
}

// Stucco terrace house fronts (Kensington type): rusticated raised ground floor,
// porches, first-floor balcony, moulded window surrounds, cornice, attic, mansard.
function stuccoTerrace(T, kit, batch, ring, o) {
  const { edges, at, ebox, win, cyl, slope } = T;
  const wall = o.wall ?? kit.mat('#ece6da');
  const back = o.back ?? kit.mat('#c9b48e');
  const trim = o.trim ?? kit.mat('#f6f2ea');
  const roofM = o.roofM ?? kit.mat('slate');
  const glass = o.glass ?? kit.mat('#2c3640', { roughness: 0.2, metalness: 0.3 });
  const frame = o.frame ?? kit.mat('#f4f4f0');
  const black = kit.mat('#1d1f22', { roughness: 0.5, metalness: 0.4 });
  const Z = o.levels; // floor lines e.g. [0, 1.2, 5.2, 9.4, 12.8, 15.9] ; last = main cornice
  const top = Z[Z.length - 1];
  const fronts = new Set(o.fronts);
  const E = edges(ring);
  // body
  for (const e of E) {
    const m = fronts.has(e.k) || (o.stuccoAll ?? false) ? wall : back;
    T.quad(m, e.a, e.b, 0, top);
  }
  // basement area / plinth band
  kit.cornice(batch, trim, ring, 0, { height: Z[1], projection: 0.08 });
  // string courses
  for (let i = 2; i < Z.length - 1; i++)
    kit.cornice(batch, trim, ring, Z[i] - 0.2, { height: 0.22, projection: 0.1 });
  // main cornice + blocking course
  kit.cornice(batch, trim, ring, top - 0.55, { height: 0.55, projection: 0.45, steps: 2 });
  kit.walls(batch, wall, [[ring]], top, top + 0.9);
  const pin = kit.offsetRing(ring, -0.3);
  kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + 0.9);
  kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + 0.9);
  // roof
  const zr = top + 0.6;
  let roofTop = zr;
  if (o.mansard !== false) {
    const mh = o.mansardH ?? 3.0;
    const inn = slope(roofM, pin, zr, mh * 0.35, zr + mh, false);
    const inn2 = kit.offsetRing(inn, -0.3);
    kit.cap(batch, kit.mat('lead'), [[inn]], zr + mh);
    roofTop = zr + mh;
    // dormers on fronts
    for (const e of E) {
      if (!fronts.has(e.k) || e.len < 4) continue;
      const n = Math.max(1, Math.round((e.len - 2) / (o.bay ?? 2.6)));
      for (let i = 0; i < n; i++) {
        const s = 1 + ((e.len - 2) * (i + 0.5)) / n;
        ebox(roofM, e, s - 0.75, s + 0.75, -1.6, -0.55, zr, zr + 2.2);
        ebox(trim, e, s - 0.8, s + 0.8, -1.6, -0.5, zr + 2.2, zr + 2.35);
        ebox(glass, e, s - 0.45, s + 0.45, -0.58, -0.5, zr + 0.4, zr + 1.9);
      }
    }
  } else {
    kit.cap(batch, kit.mat('#8a8a86'), [[pin]], zr);
  }
  // chimney stacks along party walls (short edges perpendicular to the front) or spaced
  let chim = o.chimneys ?? [];
  if (o.autoChimneys)
    for (const e of E)
      if (!fronts.has(e.k) && e.len > 6) {
        const p = at(e, e.len / 2, -0.7);
        chim = chim.concat([[p[0], p[1], e.ang + Math.PI / 2]]);
      }
  if (chim.length) {
    const pot = kit.mat('#b0603e');
    for (const [x, y, ang] of chim) {
      kit.box(batch, back, x, y, roofTop - 1, 0.7, 2.4, 2.4, ang);
      kit.box(batch, trim, x, y, roofTop + 1.4, 0.85, 2.6, 0.2, ang);
      for (let k = -1; k <= 1; k++)
        cyl(
          pot,
          x - Math.sin(ang) * k * 0.7,
          y + Math.cos(ang) * k * 0.7,
          roofTop + 1.6,
          0.6,
          0.14,
          0.11,
          6,
        );
    }
  }
  // fenestration
  const bay = o.bay ?? 2.6;
  for (const e of E) {
    if (e.len < 1.6) continue;
    const front = fronts.has(e.k);
    for (let s = 1; s < Z.length - 1; s++) {
      const h = Z[s + 1] - Z[s];
      const first = s === 2;
      const opts = front
        ? {
            width: 1.15,
            height: Math.min(h - 1.0, first ? 2.9 : 2.3),
            bay,
            margin: 0.7,
            glass,
            frame,
            sill: trim,
            surround: 0.16,
            surroundMat: trim,
            head: first ? 'pediment' : s === 1 ? 'lintel' : 'lintel',
            bars: 1,
          }
        : {
            width: 1.0,
            height: Math.min(h - 1.0, 2.0),
            bay: bay + 0.6,
            margin: 0.8,
            glass,
            frame,
            sill: trim,
            head: 'none',
            bars: 1,
          };
      if (!front && o.plainBack === 'blank') continue;
      win(e, 0, e.len, Z[s] + (first ? 0.25 : 0.7), opts);
    }
    if (!front) continue;
    // rusticated ground floor: horizontal grooves
    for (let z = Z[1] + 0.5; z < Z[2] - 0.3; z += 0.5)
      ebox(trim, e, 0, e.len, 0, 0.06, z, z + 0.08);
    // first-floor balcony with balustrade
    if (o.balcony !== false) {
      ebox(trim, e, 0.2, e.len - 0.2, 0, 0.9, Z[2] - 0.22, Z[2]);
      kit.balustrade(batch, trim, [at(e, 0.3, 0.8), at(e, e.len - 0.3, 0.8)], Z[2], {
        height: 0.95,
        spacing: 0.32,
      });
    }
    // area railings at pavement edge
    if (o.railings !== false) {
      for (let s = 0.2; s < e.len; s += 0.25)
        ebox(black, e, s - 0.015, s + 0.015, 2.4, 2.43, 0, 1.1);
      ebox(black, e, 0, e.len, 2.38, 2.45, 1.05, 1.1);
    }
  }
  // porches
  for (const [k, s] of o.porches ?? []) {
    const e = E[k];
    const w = 2.4,
      z0 = Z[1],
      zc = Z[2] - 0.3;
    for (const ds of [-w / 2, w / 2]) cyl(trim, ...at(e, s + ds, 1.9), z0, zc - z0, 0.22, 0.2, 10);
    for (const ds of [-w / 2, w / 2]) ebox(trim, e, s + ds - 0.2, s + ds + 0.2, 0, 0.4, z0, zc);
    ebox(trim, e, s - w / 2 - 0.35, s + w / 2 + 0.35, 0, 2.3, zc, Z[2] - 0.22);
    // steps up from pavement across the area
    for (let i = 0; i < 5; i++)
      ebox(trim, e, s - 0.9, s + 0.9, 1.6 + i * 0.3, 2.5 + 0.3 * i, 0, z0 - i * (z0 / 5));
    ebox(kit.mat('#1f2a30'), e, s - 0.6, s + 0.6, 0, 0.05, z0, zc - 0.5);
  }
  return { top, roofTop };
}

// Generic masonry block: walls, storey windows on every edge long enough, string
// courses, cornice, parapet and a flat or slated (mansard / hipped) roof.
function masonryBlock(T, kit, batch, ring, o) {
  const wall = o.wall,
    trim = o.trim ?? wall;
  const Z = o.levels;
  const top = Z[Z.length - 1];
  const E = T.edges(ring);
  for (const e of E) T.quad(o.wallFor ? o.wallFor(e) : wall, e.a, e.b, 0, top);
  if (o.plinth) kit.cornice(batch, trim, ring, 0, { height: o.plinth, projection: 0.08 });
  for (const z of o.bands ?? [])
    kit.cornice(batch, trim, ring, z, { height: 0.25, projection: 0.1 });
  kit.cornice(batch, trim, ring, top - (o.corniceH ?? 0.45), {
    height: o.corniceH ?? 0.45,
    projection: o.corniceP ?? 0.35,
    steps: 2,
  });
  const par = o.parapet ?? 0.8;
  const pin = kit.offsetRing(ring, -0.3);
  if (par > 0) {
    kit.walls(batch, wall, [[ring]], top, top + par);
    kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + par);
    kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + par);
  }
  let roofTop = top;
  if (o.roof === 'slope') {
    const inn = T.slope(
      o.roofM ?? kit.mat('slate'),
      pin,
      top + 0.2,
      o.roofInset ?? 2.5,
      top + (o.roofRise ?? 3.5),
      false,
    );
    kit.cap(batch, kit.mat('lead'), [[inn]], top + (o.roofRise ?? 3.5));
    roofTop = top + (o.roofRise ?? 3.5);
  } else kit.cap(batch, o.roofM ?? kit.mat('#8b8b87'), [[pin]], top + 0.15);
  for (const e of E) {
    if (e.len < (o.minEdge ?? 2.5)) continue;
    for (let s = 0; s < Z.length - 1; s++) {
      const w = typeof o.win === 'function' ? o.win(s, e, Z[s + 1] - Z[s]) : o.win;
      if (!w) continue;
      T.win(e, 0, e.len, Z[s] + (w.sillOff ?? 0.9), w);
    }
  }
  return { top, roofTop, E };
}

// Frame facade: brick piers proud of the wall, concrete floor bands, metal windows between.
function pierFrame(T, kit, batch, e, z0, z1, storey, o) {
  const n = Math.max(1, Math.round(e.len / (o.bay ?? 3.2)));
  for (let k = 0; k <= n; k++) {
    const s = (k * e.len) / n;
    T.ebox(
      o.pier,
      e,
      Math.max(0, s - (o.pierW ?? 0.3)),
      Math.min(e.len, s + (o.pierW ?? 0.3)),
      -0.05,
      o.pierD ?? 0.3,
      z0,
      z1,
    );
  }
  for (let z = z0; z < z1 - 0.5; z += storey) {
    T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z, z + (o.bandH ?? 0.4));
    for (let k = 0; k < n; k++) {
      const s0 = (k * e.len) / n + (o.pierW ?? 0.3),
        s1 = ((k + 1) * e.len) / n - (o.pierW ?? 0.3);
      if (s1 - s0 < 0.4) continue;
      const zt = Math.min(z1, z + storey);
      if (o.spandrel)
        T.ebox(
          o.spandrel,
          e,
          s0,
          s1,
          0.0,
          0.07,
          z + (o.bandH ?? 0.4),
          z + (o.bandH ?? 0.4) + o.spandrelH,
        );
      const g0 = z + (o.bandH ?? 0.4) + (o.spandrel ? o.spandrelH : 0);
      T.ebox(o.glass, e, s0, s1, 0.01, 0.05, g0, zt);
      const m = Math.max(1, Math.round((s1 - s0) / (o.mullion ?? 1.1)));
      for (let j = 1; j < m; j++) {
        const s = s0 + ((s1 - s0) * j) / m;
        T.ebox(o.frame, e, s - 0.035, s + 0.035, 0.03, 0.1, g0, zt);
      }
      T.ebox(o.frame, e, s0, s1, 0.03, 0.1, g0 + (zt - g0) * 0.62, g0 + (zt - g0) * 0.62 + 0.06);
    }
  }
  T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z1 - 0.1, z1 + 0.3);
}

// Clip a ring to the half-plane n . p >= c (Sutherland-Hodgman).
function clipHalf(ring, n, c) {
  const out = [];
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    const fp = n[0] * p[0] + n[1] * p[1] - c,
      fq = n[0] * q[0] + n[1] * q[1] - c;
    if (fp >= 0) out.push(p);
    if (fp * fq < 0) {
      const t = fp / (fp - fq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
}
