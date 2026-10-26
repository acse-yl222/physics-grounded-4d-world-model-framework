// Fulham Palace, Bishop's Avenue, Fulham - for centuries the country residence of the
// Bishops of London (Grade I). West court: red-brick Tudor quadrangle (great hall c.1480
// for Bishop Kempe, porch and courtyard c.1500, south range rebuilt 1853) entered through a
// battlemented brick gate tower. East court: rebuilt in Gothick style by Stiff Leadbetter
// in 1764-66 and remodelled and refronted in a plain late-Georgian manner by
// S. P. Cockerell in 1814-18 (Leadbetter's crenellations removed).
export default {
  id: 'fulham_palace',
  name: 'Fulham Palace',
  claims: ['8786a828-ddba-4707-82d8-8b2547c4f282'],
  references: [
    {
      title: 'Fulham Palace - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Fulham_Palace',
      used_for: 'history, Tudor west court, Georgian east court',
    },
    {
      title: 'Fulham Palace - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101286903',
      used_for:
        'Grade I; great hall c.1480 for Bishop Kemp; porch and west courtyard c.1500; south range rebuilt 1853; east court by Stiff Leadbetter 1764-6, remodelled and refronted 1814-18 by S P Cockerell',
    },
    {
      title: 'Fulham Palace and Bishops Park - Parks & Gardens',
      url: 'https://www.parksandgardens.org/places/fulham-palace-and-bishops-park',
      used_for: 'red-brick Tudor courtyard; Leadbetter’s gothic crenellations removed',
    },
    {
      title: 'Fulham Palace - Historic England (registered park and garden)',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1000133',
      used_for: 'setting, moat and grounds',
    },
  ],
  notes:
    'The single Overture footprint is split into the west court quadrangle (north-west part, courtyard ' +
    '~27 x 30 m assumed) and the east court block (south-east part). Ridge and eave heights, gate tower ' +
    'height (15 m), the diaper brickwork, chimney positions, the east front’s window pattern and the ' +
    'courtyard fountain are estimates. The 1866 chapel and the walled garden are not modelled.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const a = (149.63 * Math.PI) / 180,
      CX = -1054.18,
      CY = -3998.13;
    const ca = Math.cos(a),
      sa = Math.sin(a);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca]; // u: NW, v: SW
    const rect = (u0, u1, v0, v1) => {
      const r = [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const tudor = kit.paintedMaterial(
      'fulham_palace:tudor',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.61);
        c.fillStyle = '#9c8a74';
        c.fillRect(0, 0, w, h);
        const rows = 44,
          bw = 22;
        for (let i = 0; i < rows; i++)
          for (let x = -(i % 2) * (bw / 2), j = 0; x < w; x += bw, j++) {
            const t = 0.8 + r() * 0.3;
            // blue-black diaper pattern of burnt headers
            const di = (i + j * 2) % 8 === 0 || (i - j * 2 + 64) % 8 === 0;
            const col = di ? [64, 52, 58] : [150, 70, 50];
            c.fillStyle = `rgb(${Math.round(col[0] * t)},${Math.round(col[1] * t)},${Math.round(col[2] * t)})`;
            c.fillRect(x + 0.6, (i * h) / rows + 0.6, bw - 1.2, h / rows - 1.2);
          }
      },
      { roughness: 0.92 },
    );
    const stock = kit.mat('#c2ad86', { roughness: 0.9 });
    const stone = kit.mat('#d9cfb6', { roughness: 0.8 });
    const tiles = kit.mat('#8a4a36', { roughness: 0.85 });
    const slate = kit.mat('#56595d', { roughness: 0.75 });
    const glass = kit.mat('#2b333a', { roughness: 0.3, metalness: 0.2 });
    const frameW = kit.mat('#ece8dc');
    const wo = { bay: 1, storey: 2 };
    const box = (m, u, v, z, w, d, h, rot = 0) => {
      const p = L(u, v);
      kit.box(batch, m, p[0], p[1], z, w, d, h, a + rot);
    };

    // ---- west court (Tudor quadrangle) -------------------------------------------------
    const OU0 = -8.5,
      OU1 = 37.5,
      OV0 = -24.5,
      OV1 = 22.0;
    const IU0 = -0.5,
      IU1 = 29.0,
      IV0 = -16.0,
      IV1 = 14.0;
    const EAVE = 8.2;
    const outer = rect(OU0, OU1, OV0, OV1);
    const inner = rect(IU0, IU1, IV0, IV1);
    kit.walls(batch, tudor, [[outer]], 0, EAVE, wo);
    kit.walls(batch, tudor, [[inner.slice().reverse()]], 0, EAVE, wo);
    kit.cap(batch, kit.mat('#7c7467'), [[outer, inner.slice().reverse()]], EAVE - 0.05);
    kit.cornice(batch, stone, outer, 0, { height: 0.5, projection: 0.1 });
    // pitched tiled roofs over the four ranges
    const ranges = [
      [OU0, OU1, OV0, IV0, 'u'],
      [OU0, OU1, IV1, OV1, 'u'],
      [OU0, IU0, IV0, IV1, 'v'],
      [IU1, OU1, IV0, IV1, 'v'],
    ];
    for (const [u0, u1, v0, v1, ax] of ranges) {
      const r = rect(u0, u1, v0, v1);
      const span = ax === 'u' ? v1 - v0 : u1 - u0;
      kit.pitchedRoof(
        batch,
        tiles,
        tudor,
        r,
        ax === 'u' ? a : a + Math.PI / 2,
        EAVE,
        span * 0.45,
        'hipped',
        { overhang: 0.3 },
      );
    }
    // windows: mullioned stone-framed lights on both faces of every range
    const wopts = (z, w) => ({
      glass,
      frame: stone,
      sill: stone,
      head: 'lintel',
      width: w,
      height: z < 3 ? 1.8 : 1.6,
      bay: 4.2,
      margin: 1.5,
      bars: 2,
    });
    const faces = (r, outward) => {
      for (let k = 0; k < r.length; k++) {
        const p = outward ? r[k] : r[(k + 1) % r.length],
          q = outward ? r[(k + 1) % r.length] : r[k];
        kit.windowRow(batch, p, q, 1.2, wopts(1.2, 1.5));
        kit.windowRow(batch, p, q, 5.0, wopts(5.0, 1.3));
      }
    };
    faces(outer, true);
    faces(inner, false);
    // great hall in the east range: taller windows, louvre on the ridge
    {
      const p = L(-4.5, -1);
      const lv = new THREE.CylinderGeometry(0.9, 1.1, 2.2, 6).rotateX(Math.PI / 2);
      batch.addGeometry(
        kit.mat('#5a4a3c'),
        lv,
        new THREE.Matrix4().makeTranslation(p[0], p[1], EAVE + 3.2 + 1.1),
      );
      lv.dispose();
      const cap = new THREE.CylinderGeometry(0, 1.3, 1.6, 6).rotateX(Math.PI / 2);
      batch.addGeometry(
        kit.mat('lead'),
        cap,
        new THREE.Matrix4().makeTranslation(p[0], p[1], EAVE + 3.2 + 2.2 + 0.8),
      );
      cap.dispose();
    }
    // gate tower in the north-west range: battlemented brick tower with a timber gate
    {
      const tu0 = IU1 - 0.5,
        tu1 = OU1 + 1.0,
        tv0 = -4.2,
        tv1 = 4.2,
        TH = 15;
      const t = rect(tu0, tu1, tv0, tv1);
      kit.walls(batch, tudor, [[t]], 0, TH, wo);
      kit.cap(batch, kit.mat('#7c7467'), [[t]], TH);
      kit.cornice(batch, stone, t, TH - 1.6, { height: 0.3, projection: 0.15 });
      // crenellations
      for (let k = 0; k < 4; k++) {
        const p = t[k],
          q = t[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]),
          ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
        const n = Math.floor(len / 1.2);
        for (let i = 0; i < n; i += 2) {
          const s = (i + 0.5) * (len / n);
          kit.box(
            batch,
            tudor,
            p[0] + ((q[0] - p[0]) * s) / len,
            p[1] + ((q[1] - p[1]) * s) / len,
            TH,
            len / n,
            0.6,
            1.0,
            ang,
          );
        }
      }
      // octagonal corner turrets
      for (const [u, v] of [
        [tu1, tv0],
        [tu1, tv1],
      ]) {
        const p = L(u, v);
        const tr = new THREE.CylinderGeometry(1.0, 1.0, TH + 1.6, 8).rotateX(Math.PI / 2);
        batch.addGeometry(
          tudor,
          tr,
          new THREE.Matrix4().makeTranslation(p[0], p[1], (TH + 1.6) / 2),
        );
        tr.dispose();
      }
      // gateway arch and timber gates (outer face, u = tu1)
      box(kit.mat('#4a3324'), tu1 + 0.03, 0, 0, 0.08, 3.6, 4.2);
      box(stone, tu1 + 0.05, 0, 4.2, 0.12, 4.4, 0.5);
      kit.windowRow(batch, L(tu1, tv0), L(tu1, tv1), 7.5, {
        glass,
        frame: stone,
        head: 'lintel',
        count: 1,
        width: 2.4,
        height: 1.8,
        bars: 3,
      });
      kit.windowRow(batch, L(tu1, tv0), L(tu1, tv1), 11.0, {
        glass,
        frame: stone,
        head: 'lintel',
        count: 1,
        width: 1.6,
        height: 1.4,
        bars: 2,
      });
      // clock and bell turret on the courtyard side
      const cp = L(tu0 - 0.05, 0);
      const disc = new THREE.CircleGeometry(0.9, 20).rotateX(-Math.PI / 2).rotateZ(a + Math.PI / 2);
      batch.addGeometry(
        kit.mat('#1f2c3a'),
        disc,
        new THREE.Matrix4().makeTranslation(cp[0], cp[1], 11.5),
      );
      disc.dispose();
    }
    // Tudor chimney stacks
    for (const [u, v] of [
      [8, -20.5],
      [20, -20.5],
      [8, 18],
      [24, 18],
      [-4.5, 9],
      [33, -10],
    ]) {
      for (const dv of [-0.5, 0.5]) box(tudor, u, v + dv, EAVE + 2, 0.8, 0.8, 4.2);
      box(stone, u, v, EAVE + 6.2, 1.2, 2.0, 0.3);
    }
    // courtyard: paving and the fountain
    {
      const cr = rect(IU0, IU1, IV0, IV1);
      kit.cap(batch, kit.mat('#bcb3a2', { roughness: 0.95 }), [[cr]], 0.05);
      const c = L((IU0 + IU1) / 2, (IV0 + IV1) / 2);
      const basin = new THREE.CylinderGeometry(2.0, 2.1, 0.6, 16).rotateX(Math.PI / 2);
      batch.addGeometry(stone, basin, new THREE.Matrix4().makeTranslation(c[0], c[1], 0.3));
      basin.dispose();
      const w = new THREE.CylinderGeometry(1.8, 1.8, 0.05, 16).rotateX(Math.PI / 2);
      batch.addGeometry(kit.mat('water'), w, new THREE.Matrix4().makeTranslation(c[0], c[1], 0.62));
      w.dispose();
      const col = new THREE.CylinderGeometry(0.15, 0.25, 1.8, 8).rotateX(Math.PI / 2);
      batch.addGeometry(stone, col, new THREE.Matrix4().makeTranslation(c[0], c[1], 1.5));
      col.dispose();
    }

    // ---- east court (Leadbetter / Cockerell) ----------------------------------------------
    {
      const r = rect(-38.9, OU0, -25.5, 7.8);
      const H = 11.5;
      kit.walls(batch, stock, [[r]], 0, H, wo);
      kit.cap(batch, kit.mat('#7c7467'), [[r]], H);
      kit.cornice(batch, stone, r, H - 1.4, { height: 0.35, projection: 0.3 });
      kit.cornice(batch, stone, r, 0, { height: 0.6, projection: 0.1 });
      kit.cornice(batch, stone, r, 3.9, { height: 0.15, projection: 0.06 });
      kit.pitchedRoof(
        batch,
        slate,
        stock,
        kit.offsetRing(r, -1.0),
        a + Math.PI / 2,
        H,
        3.2,
        'hipped',
        { overhang: 0 },
      );
      for (let k = 0; k < 4; k++) {
        const p = r[k],
          q = r[(k + 1) % 4];
        for (const [z, hgt] of [
          [1.0, 2.4],
          [5.0, 2.6],
          [8.6, 1.6],
        ])
          kit.windowRow(batch, p, q, z, {
            glass,
            frame: frameW,
            sill: stone,
            head: 'lintel',
            width: 1.2,
            height: hgt,
            bay: 3.3,
            margin: 1.4,
            bars: 2,
          });
      }
      // canted bay on the garden (south-east) front
      const bay = [L(-38.9, -14), L(-41.4, -12.3), L(-41.4, -6.2), L(-38.9, -4.5)];
      const br = kit.ringArea(bay) < 0 ? bay.slice().reverse() : bay;
      kit.walls(batch, stock, [[br]], 0, H - 1.4, wo);
      kit.cap(batch, slate, [[br]], H - 1.4);
      kit.windowRow(batch, L(-41.45, -6.2), L(-41.45, -12.3), 1.0, {
        glass,
        frame: frameW,
        head: 'lintel',
        count: 1,
        width: 1.4,
        height: 2.6,
        bars: 2,
      });
      kit.windowRow(batch, L(-41.45, -6.2), L(-41.45, -12.3), 5.0, {
        glass,
        frame: frameW,
        head: 'lintel',
        count: 1,
        width: 1.4,
        height: 2.6,
        bars: 2,
      });
      for (const [u, v] of [
        [-30, -25.0],
        [-16, 7.4],
        [-30, 7.4],
      ])
        box(stock, u, v, H + 1.0, 1.0, 1.6, 3.4);
    }

    g.add(batch.toGroup('fulham_palace'));
    return g;
  },
};
