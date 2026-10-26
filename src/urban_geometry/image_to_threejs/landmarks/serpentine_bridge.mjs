// Serpentine Bridge, Hyde Park / Kensington Gardens (George Rennie, 1826). Carries West
// Carriage Drive over the lake where the Long Water becomes the Serpentine: five
// segmental arches in Bath stone on piers with semicircular cutwaters, a plain band
// at deck level and a balustraded parapet; the deck rises in a gentle hump.
export default {
  id: 'serpentine_bridge',
  name: 'Serpentine Bridge',
  claims: [],
  references: [
    {
      title: 'Serpentine Bridge - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101217600-serpentine-bridge-knightsbridge-and-belgravia-ward',
      used_for:
        'Grade II, 1826 by George Rennie; Bath stone, five segmental arches, semicircular cutwaters, balustraded parapet',
    },
    {
      title: 'The Serpentine - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Serpentine',
      used_for: 'bridge divides the Serpentine from the Long Water and carries West Carriage Drive',
    },
    {
      title: 'Serpentine Bridge - Structurae',
      url: 'https://structurae.net/structures/serpentine-bridge',
      used_for: 'arch bridge, Rennie design, date',
    },
    {
      title: 'Serpentine Bridge (Rennie) - Gardenvisit',
      url: 'https://www.gardenvisit.com/jcl/11_serpentine_bridge_rennie',
      used_for: 'general description of the bridge in its landscape setting',
    },
  ],
  notes:
    'No footprint: axis taken from the scene West Carriage Drive / "Serpentine Bridge" ways and the length from ' +
    'the gap between the scene water edges along it (~85 m). Span (14 m), pier width (3.4 m), deck width (13 m), ' +
    'arch rises and the 4.5 m hump of the deck are estimates for a flat scene (the real banks stand higher than ' +
    'the water), not measured. Baluster spacing, die positions over the piers and the voussoir ring width are ' +
    'typical, not counted.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // Axis: water crossing along West Carriage Drive, (1912.4,-63.3) -> (1949.4,13.2).
    const O = [1930.9, -25.05];
    const len0 = Math.hypot(37.0, 76.5);
    const u = [37.0 / len0, 76.5 / len0],
      n = [-u[1], u[0]];
    const ang = Math.atan2(u[1], u[0]);
    const P = (s, t, z) => [O[0] + u[0] * s + n[0] * t, O[1] + u[1] * s + n[1] * t, z];

    const stone = kit.mat('bath_stone');
    const stoneDark = kit.mat('#c8b48a', { roughness: 0.85 });
    const asphalt = kit.mat('asphalt');
    const paving = kit.mat('paving');
    const iron = kit.mat('#1f2326', { roughness: 0.5, metalness: 0.3 });
    const lampM = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.4,
      roughness: 0.3,
    });

    const W = 13,
      SPAN = 14,
      PIER = 3.4,
      END = 60,
      H = 4.5,
      Z0 = 0.25;
    const ABUT = (5 * SPAN + 4 * PIER) / 2; // 41.8
    const deckZ = (s) => Z0 + H * Math.max(0, 1 - (s / END) ** 2);
    const rises = [1.8, 2.5, 3.0, 2.5, 1.8];
    const arches = [];
    for (let k = 0; k < 5; k++) {
      const a = -ABUT + k * (SPAN + PIER);
      arches.push({ a, b: a + SPAN, r: rises[k] });
    }
    const archPts = (A, R0 = 0, steps = 14) => {
      // Segmental arch from (a,0) to (b,0) with rise r; R0 grows the radius (extrados).
      const w = A.b - A.a,
        c = (A.a + A.b) / 2;
      const R = (w * w) / 4 / (2 * A.r) + A.r / 2;
      const zc = A.r - R;
      const half = Math.asin(w / 2 / R);
      const pts = [];
      for (let i = 0; i <= steps; i++) {
        const th = -half + (2 * half * i) / steps;
        pts.push([c + (R + R0) * Math.sin(th), zc + (R + R0) * Math.cos(th)]);
      }
      return pts;
    };

    // ---- bridge body: side elevation with arch openings, extruded across ----------
    const shape = new THREE.Shape();
    shape.moveTo(-END, 0);
    shape.lineTo(-ABUT, 0);
    for (const A of arches) {
      for (const [s, z] of archPts(A)) shape.lineTo(s, z);
      shape.lineTo(A.b, 0);
    }
    shape.lineTo(END, 0);
    for (let s = END; s >= -END; s -= 2) shape.lineTo(s, deckZ(s));
    shape.closePath();
    const body = new THREE.ExtrudeGeometry(shape, {
      depth: W,
      bevelEnabled: false,
      curveSegments: 4,
    });
    const right = [u[1], -u[0]];
    const m = new THREE.Matrix4().makeBasis(
      new THREE.Vector3(u[0], u[1], 0),
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(right[0], right[1], 0),
    );
    m.setPosition(O[0] - (right[0] * W) / 2, O[1] - (right[1] * W) / 2, 0);
    batch.addGeometry(stone, body, m);
    body.dispose();

    // ---- voussoir rings proud of both faces ---------------------------------------
    for (const A of arches) {
      const inner = archPts(A, 0, 16),
        outer = archPts(A, 0.75, 16);
      const ring = new THREE.Shape();
      ring.moveTo(outer[0][0], outer[0][1]);
      for (const p of outer) ring.lineTo(p[0], p[1]);
      for (const p of inner.slice().reverse()) ring.lineTo(p[0], p[1]);
      ring.closePath();
      const rg = new THREE.ExtrudeGeometry(ring, { depth: 0.14, bevelEnabled: false });
      for (const side of [-1, 1]) {
        const mm = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(u[0], u[1], 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(right[0], right[1], 0),
        );
        const off = side > 0 ? W / 2 : -W / 2 - 0.14;
        mm.setPosition(O[0] + right[0] * off, O[1] + right[1] * off, 0);
        batch.addGeometry(stoneDark, rg, mm);
      }
      rg.dispose();
      // keystone
      const c = (A.a + A.b) / 2;
      for (const t of [-1, 1]) {
        const p = P(c, t * (W / 2 + 0.1), 0);
        kit.box(batch, stoneDark, p[0], p[1], A.r - 0.05, 0.7, 0.35, 0.95, ang);
      }
    }

    // ---- piers: semicircular cutwaters with domed caps ------------------------------
    for (let k = 0; k < 4; k++) {
      const s = arches[k].b + PIER / 2;
      const capZ = 1.5;
      for (const side of [-1, 1]) {
        const cyl = new THREE.CylinderGeometry(
          PIER / 2,
          PIER / 2,
          capZ,
          14,
          1,
          true,
          Math.PI / 2,
          Math.PI,
        )
          .rotateX(Math.PI / 2)
          .translate(0, 0, capZ / 2);
        const dome = new THREE.SphereGeometry(PIER / 2, 14, 4, Math.PI, Math.PI, 0, Math.PI / 2)
          .rotateX(Math.PI / 2)
          .scale(1, 1, 0.6)
          .translate(0, 0, capZ);
        const p = P(s, side * (W / 2), 0);
        const mm = new THREE.Matrix4()
          .makeRotationZ(ang + (side > 0 ? 0 : Math.PI))
          .setPosition(p[0], p[1], 0);
        batch.addGeometry(stone, cyl, mm);
        batch.addGeometry(stoneDark, dome, mm);
        cyl.dispose();
        dome.dispose();
      }
    }

    // ---- deck: carriageway, raised footways, band course ---------------------------
    const strip = (mat, t0, t1, dz, s0 = -END, s1 = END, step = 2) => {
      for (let s = s0; s < s1 - 1e-6; s += step) {
        const e = Math.min(s + step, s1);
        batch.quad(
          mat,
          P(s, t0, deckZ(s) + dz),
          P(e, t0, deckZ(e) + dz),
          P(e, t1, deckZ(e) + dz),
          P(s, t1, deckZ(s) + dz),
          [0, s / 8],
          [0, e / 8],
          [1, e / 8],
          [1, s / 8],
        );
      }
    };
    const vstrip = (mat, t, z0, z1, s0 = -END, s1 = END, step = 2) => {
      // vertical band at offset t following the deck profile (normal along sign(t)).
      for (let s = s0; s < s1 - 1e-6; s += step) {
        const e = Math.min(s + step, s1);
        const q = [
          P(s, t, deckZ(s) + z0),
          P(e, t, deckZ(e) + z0),
          P(e, t, deckZ(e) + z1),
          P(s, t, deckZ(s) + z1),
        ];
        if (t > 0) q.reverse();
        batch.quad(mat, q[0], q[1], q[2], q[3], [0, 0], [1, 0], [1, 1], [0, 1]);
      }
    };
    const CW = 4.2;
    strip(asphalt, -CW, CW, 0.03);
    for (const sd of [-1, 1]) {
      strip(paving, sd > 0 ? CW : -W / 2, sd > 0 ? W / 2 : -CW, 0.16);
      vstrip(paving, sd * CW, 0.03, 0.16);
      // band course at deck level on each face
      const t = sd * (W / 2 + 0.22);
      vstrip(stoneDark, t, -0.55, 0.0, -ABUT - 4, ABUT + 4);
      strip(
        stoneDark,
        Math.min((sd * W) / 2, t),
        Math.max((sd * W) / 2, t),
        0.0,
        -ABUT - 4,
        ABUT + 4,
      );
    }

    // ---- balustraded parapets with dies over piers and at the ends -----------------
    const dies = [-ABUT - 3, ...arches.slice(0, 4).map((A) => A.b + PIER / 2), ABUT + 3];
    for (const sd of [-1, 1]) {
      const t = sd * (W / 2 - 0.2);
      const ps = [-ABUT - 3];
      for (let s = -ABUT - 3 + 2; s < ABUT + 3; s += 2) ps.push(s);
      ps.push(ABUT + 3);
      for (let i = 1; i < ps.length; i++) {
        const sm = (ps[i - 1] + ps[i]) / 2;
        const a = P(ps[i - 1], t, 0),
          b = P(ps[i], t, 0);
        kit.balustrade(batch, stone, [a, b], deckZ(sm) + 0.16, { height: 1.05, spacing: 0.34 });
      }
      for (const s of dies) {
        const p = P(s, t, 0);
        kit.box(batch, stone, p[0], p[1], deckZ(s) + 0.1, 0.9, 0.55, 1.25, ang);
        kit.box(batch, stoneDark, p[0], p[1], deckZ(s) + 1.35, 1.05, 0.7, 0.14, ang);
      }
      // approach walls beyond the balustrades, dying into the ground
      for (const [s0, s1] of [
        [-END, -ABUT - 3],
        [ABUT + 3, END],
      ])
        for (let s = s0; s < s1 - 1e-6; s += 2) {
          const e = Math.min(s + 2, s1),
            sm = (s + e) / 2;
          const p = P(sm, t, 0);
          const h = Math.max(
            0.3,
            1.05 * (1 - Math.abs(Math.abs(sm) - ABUT - 3) / (END - ABUT - 3)),
          );
          kit.box(batch, stone, p[0], p[1], deckZ(sm), e - s + 0.02, 0.45, h, ang);
        }
    }
    // Lamp standards on the end dies and the centre piers.
    for (const sd of [-1, 1])
      for (const s of [dies[0], dies[2], dies[3], dies[5]]) {
        const p = P(s, sd * (W / 2 - 0.2), 0);
        const z = deckZ(s) + 1.49;
        const col = new THREE.CylinderGeometry(0.07, 0.12, 3.2, 8).rotateX(Math.PI / 2);
        batch.addGeometry(iron, col, new THREE.Matrix4().makeTranslation(p[0], p[1], z + 1.6));
        col.dispose();
        const lan = new THREE.CylinderGeometry(0.24, 0.16, 0.55, 6).rotateX(Math.PI / 2);
        batch.addGeometry(lampM, lan, new THREE.Matrix4().makeTranslation(p[0], p[1], z + 3.45));
        lan.dispose();
        const capG = new THREE.ConeGeometry(0.3, 0.3, 6).rotateX(Math.PI / 2);
        batch.addGeometry(iron, capG, new THREE.Matrix4().makeTranslation(p[0], p[1], z + 3.87));
        capG.dispose();
      }

    g.add(batch.toGroup('serpentine_bridge'));
    return g;
  },
};
