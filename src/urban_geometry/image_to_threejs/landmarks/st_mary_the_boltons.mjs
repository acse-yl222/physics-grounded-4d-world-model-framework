// St Mary The Boltons, West Brompton (George Godwin the younger, 1849-50; spire added
// 1854-56; Grade II). Decorated Gothic church in rubblestone with ashlar dressings and
// slate roofs, standing in the oval garden of The Boltons: aisleless five-bay nave,
// crossing and transepts, a crossing tower with an ashlar broach spire that has a
// curious octagonal stage instead of lucarnes, and a bellcote at the west end.
export default {
  id: 'st_mary_the_boltons',
  name: 'St Mary The Boltons',
  claims: ['3ea05633-2580-4b2d-a63e-b7f1ddd7412d'],
  references: [
    {
      title: 'St Mary The Boltons - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/St_Mary_The_Boltons',
      used_for: 'George Godwin the younger, consecrated 1850, Grade II',
    },
    {
      title: 'Church of St Mary - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101294362-church-of-st-mary-redcliffe-ward',
      used_for:
        'rubblestone, ashlar dressings, slate roof, aisleless five-bay nave, crossing and transepts, crossing tower with ashlar broach spire with octagonal stage, west bellcote',
    },
    {
      title: "Plate 93: St. Mary's Church, The Boltons, exterior - Survey of London",
      url: 'https://prod.british-history.ac.uk/node/42037',
      used_for: 'spire added 1856 (caption)',
    },
    {
      title: 'History - St Mary The Boltons',
      url: 'https://www.stmarytheboltons.org.uk/history',
      used_for: 'spire added 1854',
    },
  ],
  notes:
    'Cruciform plan fitted to the Overture footprint (chancel and vestry outlines simplified). Heights are ' +
    'estimates: nave eave 9 m, ridge 17 m, tower to 22 m, octagonal stage and spire tip ~46 m. Window ' +
    'tracery simplified to two- and three-light arched windows.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = (216.77 * Math.PI) / 180,
      CX = 1129.62,
      CY = -1925.64;
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const rect = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];

    const stoneTex = (key, base, joint, seed) =>
      kit.paintedMaterial(
        key,
        256,
        256,
        (c, w, h) => {
          const r = kit.rng(seed);
          c.fillStyle = joint;
          c.fillRect(0, 0, w, h);
          const rows = 14;
          for (let i = 0; i < rows; i++) {
            const y0 = (i * h) / rows;
            let x = -r() * 30;
            while (x < w) {
              const bw = 14 + r() * 26;
              const t = 0.85 + r() * 0.3;
              const col = base.map((v) => Math.min(255, Math.round(v * t)));
              c.fillStyle = `rgb(${col[0]},${col[1]},${col[2]})`;
              c.fillRect(x + 1, y0 + 1, bw - 2, h / rows - 2);
              x += bw;
            }
          }
        },
        { roughness: 0.92 },
      );
    const rag = stoneTex('st_mary_boltons:rubble', [168, 160, 140], '#958c78', 0.57);
    const ashlar = kit.mat('#cdbf9c', { roughness: 0.8 });
    const slate = kit.mat('#4f5459', { roughness: 0.75 });
    const glass = kit.mat('#2c3640', { roughness: 0.3, metalness: 0.2 });
    const wopt = { bay: 1, storey: 2 };

    const block = (u0, u1, v0, v1, eave, rise, axis = 'u', kind = 'gabled', z0 = 0) => {
      const r = rect(u0, u1, v0, v1);
      kit.walls(batch, rag, [[r]], z0, eave, wopt);
      kit.cornice(batch, ashlar, r, eave - 0.35, { height: 0.35, projection: 0.15 });
      kit.cornice(batch, ashlar, r, z0, { height: 0.6, projection: 0.12 });
      return kit.pitchedRoof(
        batch,
        slate,
        rag,
        r,
        axis === 'u' ? ang : ang + Math.PI / 2,
        eave,
        rise,
        kind,
        {
          overhang: 0.3,
          storey: 2,
        },
      );
    };
    const lancets = (ua, ub, v, z, opts) => {
      // wall edge along u at side v; outward normal must be on the right of a->b
      const a = v < 0 ? L(ua, v) : L(ub, v),
        b = v < 0 ? L(ub, v) : L(ua, v);
      kit.windowRow(batch, a, b, z, {
        glass,
        frame: ashlar,
        head: 'arch',
        bars: 1,
        depth: 0.18,
        ...opts,
      });
    };
    const lancetsU = (u, va, vb, z, opts) => {
      const a = u > 0 ? L(u, va) : L(u, vb),
        b = u > 0 ? L(u, vb) : L(u, va);
      kit.windowRow(batch, a, b, z, {
        glass,
        frame: ashlar,
        head: 'arch',
        bars: 1,
        depth: 0.18,
        ...opts,
      });
    };
    const geo = (m, gm, x, y, z, rz = 0) => {
      batch.addGeometry(m, gm, new THREE.Matrix4().makeRotationZ(rz).setPosition(x, y, z));
      gm.dispose();
    };

    // u > 0: the nave towards the west (south-west) end; v > 0 north side
    const EAVE = 9,
      RISE = 8;
    block(-1.6, 25.5, -5.8, 5.7, EAVE, RISE); // aisleless five-bay nave
    block(-10.7, -1.6, -13.3, 13.3, EAVE, RISE, 'v'); // transepts
    block(-22.0, -10.7, -4.6, 4.6, EAVE - 1, RISE - 1); // chancel
    block(-23.1, -10.7, 5.7, 13.2, 5.5, 2.2); // north chapel / vestry
    block(-19.1, -10.7, -10.3, -4.6, 5.0, 2.0); // south vestry
    // nave windows: five bays of two-light Decorated windows
    for (const v of [-5.8, 5.7])
      lancets(0.0, 24.5, v, 2.6, { width: 1.5, height: 4.4, count: 5, bars: 1 });
    // west window and door
    lancetsU(25.5, -5.8, 5.7, 5.0, { width: 3.0, height: 5.6, count: 1, bars: 2 });
    {
      const d = L(25.6, 0);
      kit.box(batch, kit.mat('#3b2a1f'), d[0], d[1], 0, 1.8, 0.1, 3.4, ang + Math.PI / 2);
      kit.box(batch, ashlar, d[0], d[1], 3.4, 2.6, 0.4, 0.5, ang + Math.PI / 2);
    }
    // transept end windows (big three-light)
    for (const v of [-13.3, 13.3]) {
      const a = v < 0 ? L(-10.7, v) : L(-1.6, v),
        b = v < 0 ? L(-1.6, v) : L(-10.7, v);
      kit.windowRow(batch, a, b, 3.0, {
        glass,
        frame: ashlar,
        head: 'arch',
        count: 1,
        width: 2.8,
        height: 5.2,
        bars: 2,
      });
    }
    // east window
    lancetsU(-22.0, -4.6, 4.6, 3.0, { width: 2.6, height: 5.0, count: 1, bars: 2 });
    for (const v of [-4.6, 4.6])
      lancets(-21.5, -11.5, v, 3.0, { width: 1.1, height: 3.2, count: 2 });
    // buttresses along the nave
    for (let u = 0.2; u <= 25.4; u += 25.2 / 5)
      for (const v of [-6.2, 6.1]) {
        const p = L(u, v);
        kit.box(batch, rag, p[0], p[1], 0, 0.7, 0.8, EAVE - 1.5, ang);
      }
    // west bellcote on the gable apex
    {
      const p = L(25.3, 0),
        z = EAVE + RISE - 0.4;
      kit.box(batch, ashlar, p[0], p[1], z, 0.7, 1.6, 2.4, ang);
      kit.box(batch, kit.mat('#2a2622'), p[0], p[1], z + 0.7, 0.72, 0.7, 1.1, ang);
      const cap = new THREE.CylinderGeometry(0, 1.15, 1.2, 4).rotateX(Math.PI / 2);
      geo(ashlar, cap, p[0], p[1], z + 3.0, ang + Math.PI / 4);
    }

    // ---- crossing tower, octagonal stage and broach spire -------------------------------
    {
      const tu = -6.15,
        tv = 0,
        TS = 7.6,
        TH = 22;
      const t = rect(tu - TS / 2, tu + TS / 2, tv - TS / 2, tv + TS / 2);
      kit.walls(batch, rag, [[t]], EAVE, TH, wopt);
      kit.cap(batch, slate, [[t]], TH);
      kit.cornice(batch, ashlar, t, TH - 0.5, { height: 0.5, projection: 0.2 });
      kit.cornice(batch, ashlar, t, EAVE + RISE + 0.2, { height: 0.3, projection: 0.12 });
      for (let k = 0; k < 4; k++)
        kit.windowRow(batch, t[k], t[(k + 1) % 4], TH - 5, {
          glass: kit.mat('#2a2622'),
          frame: ashlar,
          head: 'arch',
          count: 2,
          width: 0.9,
          height: 3.4,
          bars: 3,
          margin: 1.6,
        });
      const c = L(tu, tv);
      // corner broaches
      for (const [su, sv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const p = L(tu + su * (TS / 2 - 1.0), tv + sv * (TS / 2 - 1.0));
        const b = new THREE.CylinderGeometry(0, 1.45, 3.4, 4).rotateX(Math.PI / 2);
        geo(ashlar, b, p[0], p[1], TH + 1.7, ang + Math.PI / 4);
      }
      // the 'curious octagonal stage' in place of lucarnes: an open arcaded octagon
      const R8 = TS / 2 / Math.cos(Math.PI / 8) - 0.6;
      const oct = new THREE.CylinderGeometry(R8, R8, 4.2, 8).rotateX(Math.PI / 2);
      geo(ashlar, oct, c[0], c[1], TH + 2.1, ang + Math.PI / 8);
      for (let k = 0; k < 8; k++) {
        const a = ang + (k * Math.PI) / 4;
        const p = [
          c[0] + Math.cos(a) * (R8 * Math.cos(Math.PI / 8) + 0.02),
          c[1] + Math.sin(a) * (R8 * Math.cos(Math.PI / 8) + 0.02),
        ];
        kit.box(batch, kit.mat('#2a2622'), p[0], p[1], TH + 0.9, 0.9, 0.05, 2.6, a + Math.PI / 2);
      }
      kit.box(batch, ashlar, c[0], c[1], TH + 4.2, R8 * 1.9, R8 * 1.9, 0.35, ang + Math.PI / 8);
      const SH = 19;
      const sp = new THREE.CylinderGeometry(0.12, R8 - 0.2, SH, 8).rotateX(Math.PI / 2);
      geo(ashlar, sp, c[0], c[1], TH + 4.55 + SH / 2, ang + Math.PI / 8);
      kit.box(batch, kit.mat('gold'), c[0], c[1], TH + 4.55 + SH, 0.1, 0.1, 1.6, ang);
      kit.box(batch, kit.mat('gold'), c[0], c[1], TH + 4.55 + SH + 1.0, 0.8, 0.1, 0.1, ang);
    }

    g.add(batch.toGroup('st_mary_the_boltons'));
    return g;
  },
};
