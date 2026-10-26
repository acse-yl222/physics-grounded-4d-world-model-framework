// Riverside Stand, Craven Cottage (Populous for Fulham FC, built 2019-2025 with WSP and
// Buckingham/Core Five). A steel-framed stand 113 m long, 30 m wide and 30 m high on the
// Thames bank: two seating tiers facing the pitch, hospitality levels behind a glazed,
// gently curved river elevation, and a sweeping cantilevered roof with a bronze-coloured
// soffit; boutique hotel, spa and a rooftop pool overlooking the river, and a public
// riverside walk beneath.
export default {
  id: 'craven_cottage_riverside_stand',
  name: 'Riverside Stand, Craven Cottage',
  claims: ['7ed55280-6f1a-4830-86af-77a3d1e11b46'],
  references: [
    {
      title: 'Riverside Development, Craven Cottage, Fulham FC - SteelConstruction.info',
      url: 'https://steelconstruction.info/case-studies/leisure-buildings/riverside-development-craven-cottage-fulham-fc',
      used_for:
        '113 m long x 30 m wide x 30 m high, six levels incl. basement, 7.4 x 9 m column grid',
    },
    {
      title: 'Fulham FC Riverside Stand - IStructE Structural Awards 2023',
      url: 'https://www.istructe.org/structural-awards/projects/2023/fulham-fc-riverside-stand/',
      used_for: 'steel frame crowned by a 35 m cantilevering roof',
    },
    {
      title: 'In focus: Fulham FC, Populous setting new standards by the riverside - FC Business',
      url: 'https://fcbusiness.co.uk/news/in-focus-fulham-fc-populous-setting-new-standards-by-the-riverside/',
      used_for: 'sweeping cantilevered roof with bronze-coloured soffit; riverside walkway',
    },
    {
      title: 'New Riverside Stand, Craven Cottage - Core Five',
      url: 'https://corefive.co.uk/project/new-riverside-stand-craven-cottage/',
      used_for:
        'event spaces, members’ club, boutique hotel (14 keys), spa with rooftop pool overlooking the Thames',
    },
    {
      title: 'Fulham FC Riverside Stand Redevelopment - Populous',
      url: 'https://populous.com/?p=27692',
      used_for: 'architect',
    },
  ],
  notes:
    'Main stand spans the footprint between u = -54 and +66 m; the lower wings at either end are modelled as ' +
    'two-storey glazed pavilions (9 m). Tier rakes, level heights, roof depth (cantilever to 4 m over the pitch ' +
    'edge, top at 30 m), terrace and pool positions and the vertical fin rhythm of the river facade are ' +
    'estimates from the descriptions, not drawings. Overture h=6 m ignored.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const a = (113.74 * Math.PI) / 180,
      CX = -1514.18,
      CY = -3538.59;
    const ca = Math.cos(a),
      sa = Math.sin(a);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca]; // v-: pitch, v+: river
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const back = [
      [-54.4, 13.3],
      [-39, 16.4],
      [-21.6, 18.3],
      [-3.6, 19.3],
      [14.6, 19.0],
      [33.0, 18.2],
      [50.9, 16.3],
      [66.3, 13.2],
    ];
    const vb = (u) => {
      if (u <= back[0][0]) return back[0][1];
      for (let k = 1; k < back.length; k++)
        if (u <= back[k][0]) {
          const [u0, v0] = back[k - 1],
            [u1, v1] = back[k];
          return v0 + ((v1 - v0) * (u - u0)) / (u1 - u0);
        }
      return back[back.length - 1][1];
    };
    const U0 = -54.4,
      U1 = 66.3,
      VP = -19.3;
    const white = kit.mat('#f1f1ee', { roughness: 0.55 });
    const bronze = kit.mat('#8a6a46', { roughness: 0.45, metalness: 0.55 });
    const conc = kit.mat('#a9a8a3', { roughness: 0.9 });
    const glass = kit.mat('#4a6372', { roughness: 0.1, metalness: 0.55 });
    const glassL = kit.mat('#86a2b1', { roughness: 0.12, metalness: 0.45 });
    const steel = kit.mat('#d6d8d8', { roughness: 0.45, metalness: 0.5 });
    const dark = kit.mat('#2b3034');
    const seatW = kit.mat('#f2f2f0'),
      seatB = kit.mat('#1c1e20');
    const water = kit.mat('#3fa3c4', { roughness: 0.1, metalness: 0.2 });

    // ---- seating tiers ---------------------------------------------------------------
    const tier = (vF, vB, zF, zB, rows, z0 = 0) => {
      const dv = (vB - vF) / rows;
      for (let i = 0; i < rows; i++) {
        const v = vF + dv * (i + 0.5),
          z = zF + ((zB - zF) * (i + 1)) / rows;
        const c = L((U0 + U1) / 2, v);
        kit.box(batch, conc, c[0], c[1], z0 ? z - 0.6 : 0, U1 - U0 - 1, dv, z0 ? 0.6 : z, a);
        const s = L((U0 + U1) / 2, v - dv * 0.2);
        kit.box(
          batch,
          i % 4 === 3 ? seatB : seatW,
          s[0],
          s[1],
          z,
          U1 - U0 - 1.6,
          dv * 0.35,
          0.45,
          a,
        );
      }
    };
    tier(VP + 0.5, -6.5, 0.6, 9.5, 20);
    tier(-5.0, 7.0, 13.5, 24.0, 18, 1);
    // stepped stair aisles and vomitory openings through both tiers
    for (let u = U0 + 6; u < U1 - 3; u += 9.2) {
      for (const [vF, vB, zF, zB, rows] of [
        [VP + 0.5, -6.5, 0.6, 9.5, 20],
        [-5.0, 7.0, 13.5, 24.0, 18],
      ]) {
        const dv = (vB - vF) / rows;
        for (let i = 0; i < rows; i++) {
          const z = zF + ((zB - zF) * (i + 1)) / rows;
          for (const h of [0, 0.5]) {
            const c = L(u, vF + dv * (i + h * 0.5 + 0.25));
            kit.box(
              batch,
              kit.mat('#c4c3be'),
              c[0],
              c[1],
              z - 0.02 + h * ((zB - zF) / rows) * 0.5,
              1.3,
              dv * 0.5,
              0.06,
              a,
            );
          }
          kit.box(batch, steel, ...L(u - 0.7, vF + dv * (i + 0.5)), z, 0.05, dv, 0.9, a);
        }
      }
      const vo = L(u + 4.6, -2.2);
      kit.box(batch, dark, vo[0], vo[1], 9.6, 3.0, 0.2, 2.6, a);
    }
    // advertising / LED ribbon along the front of the upper tier
    {
      const c = L((U0 + U1) / 2, -5.2);
      kit.box(
        batch,
        kit.mat('#101215', { roughness: 0.3, metalness: 0.4 }),
        c[0],
        c[1],
        12.6,
        U1 - U0 - 1,
        0.25,
        0.9,
        a,
      );
    }
    // hospitality balcony fronts between the tiers
    {
      const c = L((U0 + U1) / 2, -6.0);
      kit.box(batch, glass, c[0], c[1], 9.5, U1 - U0 - 1, 1.2, 3.6, a);
      kit.box(batch, white, c[0], c[1], 13.1, U1 - U0 - 1, 1.6, 0.45, a);
    }
    // side screens
    for (const u of [U0, U1]) {
      const r = ccw([
        L(u, VP),
        L(u + (u < 0 ? 0.5 : -0.5), VP),
        L(u + (u < 0 ? 0.5 : -0.5), vb(u)),
        L(u, vb(u)),
      ]);
      kit.walls(batch, white, [[r]], 0, 27.5, { bay: 1e6 });
    }

    // ---- river block: hospitality, hotel, spa ------------------------------------------
    const N = 24;
    const pts = [];
    for (let k = 0; k <= N; k++) {
      const u = U0 + ((U1 - U0) * k) / N;
      pts.push([u, vb(u)]);
    }
    const blockRing = ccw([
      L(U0, 7.0),
      L(U1, 7.0),
      ...pts
        .slice()
        .reverse()
        .map(([u, v]) => L(u, v)),
    ]);
    const ZT = 27.5;
    kit.walls(batch, dark, [[blockRing]], 0, ZT, { bay: 1e6 });
    kit.cap(batch, kit.mat('#8d908f'), [[blockRing]], ZT);
    const levels = [0, 5.5, 10.0, 14.5, 19.0, 23.2, ZT];
    for (let k = 0; k < N; k++) {
      const [u0, v0] = pts[k],
        [u1, v1] = pts[k + 1];
      // river elevation runs from u1 to u0 so its outward normal faces the river
      const p = L(u1, v1 + 0.02),
        q = L(u0, v0 + 0.02);
      batch.quad(
        glass,
        [p[0], p[1], 3.0],
        [q[0], q[1], 3.0],
        [q[0], q[1], ZT - 0.8],
        [p[0], p[1], ZT - 0.8],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const mid = L((u0 + u1) / 2, (v0 + v1) / 2);
      const nrm = [-sa, ca]; // +v
      for (const z of levels.slice(1, -1)) {
        // terrace slabs with glass balustrades
        const t = [mid[0] + nrm[0] * 1.1, mid[1] + nrm[1] * 1.1];
        kit.box(batch, white, t[0], t[1], z - 0.35, len + 0.02, 2.4, 0.35, ang);
        const gb = [mid[0] + nrm[0] * 2.25, mid[1] + nrm[1] * 2.25];
        kit.box(batch, glassL, gb[0], gb[1], z, len + 0.02, 0.06, 1.1, ang);
      }
      // curtain-wall mullions and transoms between the slabs
      for (const f of [0.25, 0.75]) {
        const fu = u0 + (u1 - u0) * f,
          fp = L(fu, vb(fu) + 0.06);
        kit.box(batch, steel, fp[0], fp[1], 3.0, 0.07, 0.12, ZT - 3.8, ang);
      }
      for (const z of levels.slice(1, -1)) {
        const tp = L((u0 + u1) / 2, (v0 + v1) / 2 + 0.06);
        kit.box(batch, steel, tp[0], tp[1], z + 2.4, len, 0.1, 0.08, ang);
      }
      // vertical bronze fins
      for (const f of [0, 0.5]) {
        const fu = u0 + (u1 - u0) * f,
          fp = L(fu, vb(fu) + 0.3);
        kit.box(batch, bronze, fp[0], fp[1], 3.0, 0.12, 0.6, ZT - 3.8, ang);
      }
    }
    // riverside walk colonnade under the block
    for (let k = 0; k <= N; k += 2) {
      const [u, v] = pts[k];
      const p = L(u, v - 0.6);
      kit.box(batch, steel, p[0], p[1], 0, 0.5, 0.5, 3.0, a);
    }
    {
      const sign = kit.paintedMaterial(
        'riverside_stand:sign',
        1024,
        96,
        (c, w, h) => {
          c.fillStyle = '#1b1d1f';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#ffffff';
          c.font = 'bold 56px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('FULHAM FOOTBALL CLUB', w / 2, h / 2 + 3);
        },
        { roughness: 0.5 },
      );
      const p = L(30, vb(30) + 2.4),
        q = L(-20, vb(-20) + 2.4);
      batch.quad(
        sign,
        [p[0], p[1], 3.2],
        [q[0], q[1], 3.2],
        [q[0], q[1], 4.6],
        [p[0], p[1], 4.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // rooftop spa pool on the river side
    {
      const pr = ccw([L(5, 10), L(35, 10), L(35, 14.5), L(5, 14.5)]);
      kit.cap(batch, water, [[pr]], ZT + 0.15);
      kit.walls(batch, glassL, [[kit.offsetRing(pr, 0.8)]], ZT, ZT + 1.2, { bay: 1e6 });
      const deck = ccw([L(-10, 8), L(48, 8), L(48, 15.5), L(-10, 15.5)]);
      kit.cap(batch, kit.mat('#a5876a', { roughness: 0.8 }), [[deck]], ZT + 0.08);
    }

    // ---- cantilevered roof --------------------------------------------------------------
    {
      const front = -23.3;
      const rpts = [];
      for (let k = 0; k <= N; k++) {
        const u = U0 - 1 + ((U1 - U0 + 2) * k) / N;
        rpts.push([u, vb(u) + 1.0]);
      }
      // roof rises slightly towards the pitch edge
      const zr = (v) => 29.2 + 0.8 * ((vb(0) + 1 - v) / (vb(0) + 1 - front));
      const ring = [
        L(U0 - 1, front),
        L(U1 + 1, front),
        ...rpts
          .slice()
          .reverse()
          .map(([u, v]) => L(u, v)),
      ];
      const loc = [[U0 - 1, front], [U1 + 1, front], ...rpts.slice().reverse()];
      const tris = THREE.ShapeUtils.triangulateShape(
        ring.map(([x, y]) => new THREE.Vector2(x, y)),
        [],
      );
      const top = ring.map(([x, y], i) => [x, y, zr(loc[i][1]) + 0.5]);
      const bot = ring.map(([x, y], i) => [x, y, zr(loc[i][1])]);
      const ccwRing = kit.ringArea(ring) > 0;
      const idxUp = [],
        idxDn = [];
      for (const t of tris) {
        if (ccwRing) {
          idxUp.push(t[0], t[1], t[2]);
          idxDn.push(t[0], t[2], t[1]);
        } else {
          idxUp.push(t[0], t[2], t[1]);
          idxDn.push(t[0], t[1], t[2]);
        }
      }
      const uv = ring.map(([x, y]) => [x / 10, y / 10]);
      batch.add(white, top, uv, idxUp);
      batch.add(bronze, bot, uv, idxDn);
      // edges
      for (let k = 0; k < ring.length; k++) {
        const p = top[k],
          q = top[(k + 1) % ring.length];
        const pb = bot[k],
          qb = bot[(k + 1) % ring.length];
        const verts = [pb, qb, q, p];
        const nz = ccwRing ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
        batch.add(
          white,
          verts,
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          nz,
        );
      }
      // white fascia beam along the pitch edge and raking roof girders seen from below
      const fb = L((U0 + U1) / 2, front + 0.3);
      kit.box(batch, white, fb[0], fb[1], zr(front) - 1.2, U1 - U0 + 2, 0.6, 1.2, a);
      for (let u = U0 + 4; u <= U1 - 4; u += 9) {
        const p = L(u, (front + 8) / 2);
        kit.box(batch, bronze, p[0], p[1], zr(-8) - 0.9, 0.5, 8 - front, 0.9, a);
      }
    }

    // ---- end pavilions -------------------------------------------------------------------
    const wings = [
      [
        [-54.4, 13.3],
        [-54.4, 11.8],
        [-65, 11.7],
        [-65, 10.3],
        [-75.6, 10.3],
        [-75.6, 0.9],
        [-87.5, -0.8],
        [-87.5, -6.3],
        [-54.4, -6.3],
      ],
      [
        [66.2, -6.3],
        [87.5, -6.3],
        [87.5, 0.6],
        [85.9, 0.6],
        [85.9, 6.9],
        [76.9, 6.9],
        [76.9, 11.1],
        [68.7, 11.1],
        [68.7, 13.2],
        [66.2, 13.2],
      ],
    ];
    for (const w of wings) {
      const r = ccw(w.map(([u, v]) => L(u, v)));
      kit.walls(batch, glassL, [[r]], 0, 8.6, { bay: 1e6 });
      kit.cap(batch, white, [[r]], 9.0);
      kit.cornice(batch, white, r, 8.6, { height: 0.4, projection: 0.6 });
      kit.cornice(batch, white, r, 4.2, { height: 0.3, projection: 0.2 });
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
        for (let s = 1.5; s < len; s += 1.5) {
          const t = s / len;
          kit.box(
            batch,
            steel,
            p[0] + (q[0] - p[0]) * t,
            p[1] + (q[1] - p[1]) * t,
            0,
            0.1,
            0.12,
            8.6,
            ang,
          );
        }
      }
    }

    g.add(batch.toGroup('craven_cottage_riverside_stand'));
    return g;
  },
};
