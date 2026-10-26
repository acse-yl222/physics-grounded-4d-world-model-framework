// Beit Quadrangle: Imperial College Union and Beit Hall, Prince Consort Road (Sir Aston
// Webb; Union building 1910-11, east, west, north and south ranges of the quad added
// 1912-1931). Red brick Edwardian Tudor-style ranges with Portland stone dressings
// (mullioned windows, string courses, coped parapets) under steep slate roofs with
// dormers and chimney stacks, enclosing a courtyard entered through a stone archway
// on Prince Consort Road whose pediment carries the Imperial College coat of arms.
export default {
  id: 'beit_quad',
  name: 'Beit Quad (Imperial College Union and Beit Hall)',
  claims: [
    '0a73225b-2a74-4c94-a906-3845d038da31', // Imperial College Union (north range)
    '5a9ce829-61dc-447f-a41d-2307b207d1ff', // Beit Hall (east, south, west ranges)
  ],
  references: [
    {
      title: 'Beit Hall - Wikipedia',
      url: 'https://www.Wikipedia.com/wiki/Beit_Hall',
      used_for: 'Aston Webb design, built 1910; Union 1910-11, quad ranges 1912-1931',
    },
    {
      title: 'About: Beit Hall - DBpedia',
      url: 'https://dbpedia.org/page/Beit_Hall',
      used_for: 'history and capacity',
    },
    {
      title: 'A Quick Tour of the Union Bar - PocketSights',
      url: 'https://pocketsights.stqry.com/tour/53093/preview',
      used_for:
        'archway with the Imperial College coat of arms in the pediment above the entrance; keystone carved ' +
        'as the head of Athena with her owl headdress; Tudor style',
    },
    {
      title: "Design for Students' Union, Imperial College - RIBApix",
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/design-for-students-union-imperial-college-kensington-london-perspective-of-entrance-facade/posterid/RIBA35495.html',
      used_for: "Aston Webb's entrance facade design",
    },
  ],
  notes:
    'No listing text with materials was returned by search; the red brick with Portland stone dressings, ' +
    "slate roofs, dormers and chimneys follow the well-known appearance of the quad and Webb's Imperial work " +
    'and are approximate. Ranges are split into hipped-roof rectangles fitted to the footprints; eaves at ' +
    '~13.5 m (Union 14.5 m) so ridges match the footprint heights (16.8 / 17.8 m). Windows are modelled as ' +
    'stone mullion-and-transom cross windows on every storey (rhythm 3.6 m, not traced); the gatehouse ' +
    'turrets, oriel and pediment proportions, the coat of arms and the Athena keystone are simplified. ' +
    'The courtyard garden (lawns, hedges, paths, trees) comes from the mapped ground layer and is not ' +
    'duplicated here.',
  build({ THREE, kit, byId }) {
    const root = new THREE.Group();
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const union = byId['0a73225b-2a74-4c94-a906-3845d038da31'];
    const beit = byId['5a9ce829-61dc-447f-a41d-2307b207d1ff'];
    const M = new THREE.Matrix4();
    // windowRow with a vertical round-arch head (glass tympanum + moulded ring).
    const win = (bt, a, b, z, o) => {
      if (o.head !== 'arch') return kit.windowRow(bt, a, b, z, o);
      const centres = kit.windowRow(bt, a, b, z, { ...o, head: 'none' });
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ux = (b[0] - a[0]) / len,
        uy = (b[1] - a[1]) / len;
      const an = Math.atan2(uy, ux);
      const r = (o.width ?? 1.2) / 2,
        dep = o.depth ?? 0.12,
        zc = z + (o.height ?? 2.0);
      const rot = new THREE.Matrix4()
        .makeRotationZ(an)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      for (const [cx, cy] of centres) {
        const disc = new THREE.CircleGeometry(r, 12, 0, Math.PI);
        const m1 = rot.clone().setPosition(cx + uy * 0.03, cy - ux * 0.03, zc);
        bt.addGeometry(o.glass ?? kit.mat('dark_glass'), disc, m1);
        disc.dispose();
        const tor = new THREE.TorusGeometry(r + 0.04, 0.08, 4, 12, Math.PI);
        const m2 = rot.clone().setPosition(cx + uy * dep * 0.6, cy - ux * dep * 0.6, zc);
        bt.addGeometry(o.sill ?? o.frame ?? kit.mat('white'), tor, m2);
        tor.dispose();
        if (o.bars) {
          const g2 = new THREE.BoxGeometry(0.05, dep * 0.6, r);
          bt.addGeometry(
            o.frame ?? kit.mat('white'),
            g2,
            new THREE.Matrix4()
              .makeRotationZ(an)
              .setPosition(cx + uy * dep * 0.5, cy - ux * dep * 0.5, zc + r / 2),
          );
          g2.dispose();
        }
      }
      return centres;
    };

    // Plain red brick in English bond (windows are real geometry).
    const brickTex = (key, base, seed) =>
      kit.paintedMaterial(key, 512, 512, (c, w, h) => {
        const r = kit.rng(seed);
        c.fillStyle = '#7d6f62';
        c.fillRect(0, 0, w, h);
        for (let y = 0, row = 0; y < h; y += 8, row++) {
          const header = row % 2 === 1;
          const bw = header ? 10 : 22;
          for (let x = header ? -5 : 0; x < w; x += bw) {
            const k = 0.84 + r() * 0.26;
            const burnt = r() < 0.08 ? 0.78 : 1;
            c.fillStyle = `rgb(${Math.round(base[0] * k * burnt)},${Math.round(base[1] * k * burnt)},${Math.round(base[2] * k * burnt)})`;
            c.fillRect(x + 1, y + 1, bw - 2, 6);
          }
        }
      });
    const brick = brickTex('beit_quad:brick', [158, 78, 56], 1910);
    const brickU = brickTex('beit_quad:brick_union', [148, 72, 52], 1911);
    const stone = kit.mat('portland_stone');
    const stoneW = kit.mat('#cfc8b4', { roughness: 0.85 }); // weathered stone
    const slate = kit.mat('#4f565d', { roughness: 0.8 });
    const lead = kit.mat('lead');
    const brickSolid = kit.mat('#93503b');
    const dark = kit.mat('#20272c', { roughness: 0.3 });
    const glass = kit.mat('#34434d', { roughness: 0.15, metalness: 0.3 });
    const frameW = kit.mat('#ece9e0', { roughness: 0.6 });
    const door = kit.mat('#3a2b20', { roughness: 0.7 });
    const pot = kit.mat('#a0573c');

    const unionRing = union.polys[0][0];
    const beitRing = beit.polys[0][0];
    const eaveB = 13.5,
      eaveU = 14.5;
    kit.walls(batch, brick, [[beitRing]], 0, eaveB, { bay: 3.6, storey: 3.375 });
    kit.walls(batch, brickU, [[unionRing]], 0, eaveU, { bay: 3.6, storey: 3.625 });

    // Stone plinth, string courses at every floor, sill band and coped parapet.
    for (const [ring, eave, st] of [
      [beitRing, eaveB, 3.375],
      [unionRing, eaveU, 3.625],
    ]) {
      kit.cornice(batch, stoneW, ring, 0, { height: 1.0, projection: 0.15 });
      kit.cornice(batch, stone, ring, 0.95, { height: 0.15, projection: 0.22 });
      for (let s = 1; s < 4; s++)
        kit.cornice(batch, stone, ring, s * st - 0.05, { height: 0.28, projection: 0.12 });
      kit.cornice(batch, stone, ring, eave - 0.75, { height: 0.75, projection: 0.35, steps: 3 });
      kit.walls(batch, brick, [[kit.offsetRing(ring, 0.05)]], eave, eave + 0.6, {
        bay: 3.6,
        storey: 3.375,
      });
      kit.cornice(batch, stone, kit.offsetRing(ring, 0.05), eave + 0.6, {
        height: 0.18,
        projection: 0.12,
      });
      kit.cap(batch, kit.mat('#7d7f80'), [[ring]], eave + 0.05);
    }

    // Stone-mullioned cross windows on every face and storey. Edges shared between the
    // two footprints, and the gateway bay of the north front, get none.
    const inside = (p, ring) => {
      let c = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i],
          [xj, yj] = ring[j];
        if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
      }
      return c;
    };
    const GATE = { s0: 1540.5, s1: 1553.5 }; // x-range of the gateway on the north front
    const winOpts = (storey, st) => ({
      width: storey === 0 ? 1.7 : 1.6,
      height: storey === 0 ? 2.1 : storey === 3 ? 1.7 : 2.0,
      bay: 3.6,
      margin: 0.9,
      depth: 0.16,
      glass,
      frame: stone,
      sill: stone,
      head: 'lintel',
      bars: 1,
      surround: 0.2,
      surroundMat: stone,
    });
    for (const [ring, other, st] of [
      [beitRing, unionRing, 3.375],
      [unionRing, beitRing, 3.625],
    ]) {
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 3.4) continue;
        const nx = (b[1] - a[1]) / len,
          ny = -(b[0] - a[0]) / len;
        const mid = [(a[0] + b[0]) / 2 + nx * 1.0, (a[1] + b[1]) / 2 + ny * 1.0];
        if (inside(mid, other)) continue;
        // Split the north front around the gateway.
        const segs = [];
        if (ring === unionRing && len > 60) {
          const tAt = (x) => (x - a[0]) / (b[0] - a[0]);
          const lerp = (t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
          const t0 = Math.min(tAt(GATE.s0), tAt(GATE.s1)),
            t1 = Math.max(tAt(GATE.s0), tAt(GATE.s1));
          segs.push([a, lerp(t0)], [lerp(t1), b]);
        } else segs.push([a, b]);
        for (const [p, q] of segs)
          for (let s = 0; s < 4; s++) kit.windowRow(batch, p, q, 1.25 + s * st, winOpts(s, st));
      }
    }

    // Hipped slate roofs on rectangles fitted to each range.
    const ranges = [
      {
        ring: [
          [1513, -731],
          [1589, -724],
          [1588, -714.5],
          [1512.5, -721],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // south
      {
        ring: [
          [1514.5, -721],
          [1531, -719.5],
          [1527.6, -684],
          [1512, -685],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // west
      {
        ring: [
          [1571.5, -716],
          [1588, -715],
          [1583.5, -678.5],
          [1569.5, -680],
        ],
        eave: eaveB,
        rise: 3.3,
      }, // east
      {
        ring: [
          [1509.5, -691],
          [1517.5, -691],
          [1517, -676],
          [1509.5, -677],
        ],
        eave: eaveB,
        rise: 2.4,
      }, // north-west wing
      {
        ring: [
          [1510.5, -667],
          [1581, -659.5],
          [1582, -678.5],
          [1511, -676],
        ],
        eave: eaveU,
        rise: 3.25,
      }, // Union, north
    ];
    const fitted = [];
    for (const R of ranges) {
      const ring = kit.ringArea(R.ring) < 0 ? R.ring.slice().reverse() : R.ring;
      const fr = kit.ringFrame(ring);
      kit.pitchedRoof(batch, slate, brickSolid, ring, fr.angle, R.eave + 0.6, R.rise, 'hipped', {
        overhang: 0.1,
      });
      fitted.push({ fr, R });
    }
    // Lead-capped ridges.
    for (const { fr, R } of fitted) {
      const ca = Math.cos(fr.angle),
        sa = Math.sin(fr.angle);
      const L = Math.max(fr.length - fr.width, 0.5);
      kit.box(
        batch,
        lead,
        fr.cx,
        fr.cy,
        R.eave + 0.6 + R.rise - 0.08,
        L + 0.3,
        0.3,
        0.18,
        fr.angle,
      );
      void ca;
      void sa;
    }
    // Gabled stone-faced dormers with cross windows and brick chimney stacks with pots.
    for (const { fr, R } of fitted) {
      if (fr.length < 20) continue;
      const ca = Math.cos(fr.angle),
        sa = Math.sin(fr.angle);
      const at = (u, v) => [fr.cx + u * ca - v * sa, fr.cy + u * sa + v * ca];
      const zE = R.eave + 0.6;
      const n = Math.floor((fr.length - 10) / 5.4);
      for (let i = 0; i < n; i++) {
        const u = -((n - 1) * 5.4) / 2 + i * 5.4;
        for (const side of [-1, 1]) {
          const v = side * (fr.width / 2 - 1.5);
          const [x, y] = at(u, v);
          kit.box(batch, stoneW, x, y, zE - 0.2, 2.1, 1.6, 2.2, fr.angle);
          const dr = [
            at(u - 1.15, v - 0.9),
            at(u + 1.15, v - 0.9),
            at(u + 1.15, v + 0.9),
            at(u - 1.15, v + 0.9),
          ];
          kit.pitchedRoof(
            batch,
            slate,
            stone,
            dr,
            fr.angle + Math.PI / 2,
            zE + 2.0,
            1.0,
            'gabled',
            { overhang: 0.12 },
          );
          // front face of the dormer, edge oriented so the outward side is on the right
          const f0 = at(u + (side < 0 ? -0.9 : 0.9), v + side * 0.8),
            f1 = at(u + (side < 0 ? 0.9 : -0.9), v + side * 0.8);
          kit.windowRow(batch, f0, f1, zE + 0.25, {
            count: 1,
            margin: 0.1,
            width: 1.3,
            height: 1.45,
            depth: 0.12,
            glass,
            frame: frameW,
            sill: stone,
            head: 'none',
            bars: 1,
          });
        }
      }
      for (const u of [-fr.length / 2 + 7, 0, fr.length / 2 - 7]) {
        const [x, y] = at(u, 0);
        const zc = R.eave + 0.6 + R.rise - 0.6;
        kit.box(batch, brickSolid, x, y, zc, 1.2, 3.4, 3.0, fr.angle);
        kit.box(batch, stone, x, y, zc + 2.2, 1.45, 3.65, 0.22, fr.angle);
        kit.box(batch, stone, x, y, zc + 3.0, 1.5, 3.7, 0.25, fr.angle);
        for (let j = 0; j < 4; j++) {
          const [px, py] = at(u, -1.2 + j * 0.8);
          const geo = new THREE.CylinderGeometry(0.16, 0.2, 0.8, 8).rotateX(Math.PI / 2);
          batch.addGeometry(pot, geo, M.makeTranslation(px, py, zc + 3.65));
          geo.dispose();
        }
      }
    }

    // ---- Gatehouse on Prince Consort Road -------------------------------------
    const front = [
      [1510, -667],
      [1581, -659],
    ];
    const fx = front[1][0] - front[0][0],
      fy = front[1][1] - front[0][1];
    const fl = Math.hypot(fx, fy);
    const ex = fx / fl,
      ey = fy / fl,
      nx = -ey,
      ny = ex; // outward (north)
    const ang = Math.atan2(ey, ex);
    const gx0 = (GATE.s0 + GATE.s1) / 2;
    const tmid = (gx0 - front[0][0]) / fx;
    const mid = [front[0][0] + fx * tmid, front[0][1] + fy * tmid];
    const G = (s, t) => [mid[0] + ex * s + nx * t, mid[1] + ey * s + ny * t];
    const GW = 10.4,
      GH = eaveU + 2.6;
    const B = (m, s, t, z0, w, d, h) => {
      const [x, y] = G(s, t);
      kit.box(batch, m, x, y, z0, w, d, h, ang);
    };
    B(stone, 0, 0.5, 0, GW, 1.6, GH);
    // rusticated ground storey
    {
      const pw = GW / 2 - (4.6 / 2 + 0.95);
      for (let z = 0; z < 7.4; z += 0.6)
        for (const sg of [-1, 1])
          B(
            z % 1.2 < 0.6 ? stone : stoneW,
            sg * (GW / 2 - pw / 2 + 0.03),
            1.32,
            z,
            pw + 0.06,
            0.06,
            0.5,
          );
    }
    kit.cornice(
      batch,
      stone,
      [G(-GW / 2, -0.3), G(GW / 2, -0.3), G(GW / 2, 1.3), G(-GW / 2, 1.3)].reverse(),
      7.4,
      {
        height: 0.5,
        projection: 0.25,
        steps: 2,
      },
    );
    // Octagonal turrets with lead ogee caps.
    for (const s of [-GW / 2 - 0.5, GW / 2 + 0.5]) {
      const [x, y] = G(s, 0.9);
      const oct = (r, z0, h, m) => {
        const geo = new THREE.CylinderGeometry(r, r, h, 8).rotateX(Math.PI / 2);
        batch.addGeometry(m, geo, M.makeRotationZ(ang + Math.PI / 8).setPosition(x, y, z0 + h / 2));
        geo.dispose();
      };
      oct(1.5, 0, 1.0, stoneW);
      oct(1.3, 1.0, GH + 1.8, stone);
      for (let z = 4; z < GH; z += 3.6) oct(1.38, z, 0.3, stoneW);
      oct(1.55, GH + 2.0, 0.6, stone);
      // narrow slit windows
      for (let z = 3; z < GH; z += 3.6) {
        const [wx, wy] = G(s, 0.9 + 1.25);
        kit.box(batch, dark, wx, wy, z, 0.35, 0.1, 1.5, ang);
      }
      // battlemented top and ogee cap
      for (let i = 0; i < 8; i += 2) {
        const a = ang + (i / 8) * Math.PI * 2 + Math.PI / 8;
        kit.box(
          batch,
          stone,
          x + Math.cos(a) * 1.3,
          y + Math.sin(a) * 1.3,
          GH + 2.6,
          0.6,
          0.35,
          0.6,
          a + Math.PI / 2,
        );
      }
      const prof = [
        [1.15, 0],
        [1.15, 0.2],
        [1.05, 0.7],
        [0.75, 1.4],
        [0.35, 2.0],
        [0.18, 2.5],
        [0.25, 2.65],
        [0.06, 3.0],
        [0, 3.6],
      ];
      const lg = new THREE.LatheGeometry(
        prof.map(([r, z]) => new THREE.Vector2(r, z)),
        8,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(lead, lg, M.makeRotationZ(ang + Math.PI / 8).setPosition(x, y, GH + 2.6));
      lg.dispose();
      const ball = new THREE.SphereGeometry(0.16, 8, 6);
      batch.addGeometry(kit.mat('gold'), ball, M.makeTranslation(x, y, GH + 6.3));
      ball.dispose();
    }
    // Arched carriage entrance: dark passage, reveals, voussoir ring and Athena keystone.
    const AW = 4.6,
      AH = 6.2;
    {
      const p0 = G(AW / 2, 1.34),
        p1 = G(-AW / 2, 1.34);
      batch.quad(
        door,
        [p0[0], p0[1], 0],
        [p1[0], p1[1], 0],
        [p1[0], p1[1], AH - AW / 2],
        [p0[0], p0[1], AH - AW / 2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const [x, y] = G(0, 1.345);
      const semi = new THREE.CircleGeometry(AW / 2, 20, 0, Math.PI);
      const mm = new THREE.Matrix4()
        .makeRotationZ(ang + Math.PI)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      mm.setPosition(x, y, AH - AW / 2);
      batch.addGeometry(dark, semi, mm);
      semi.dispose();
      const ring = new THREE.TorusGeometry(AW / 2 + 0.3, 0.3, 4, 20, Math.PI);
      const mr = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      const [rx, ry] = G(0, 1.4);
      mr.setPosition(rx, ry, AH - AW / 2);
      batch.addGeometry(stone, ring, mr);
      ring.dispose();
      B(stone, 0, 1.45, AH + 0.1, 0.8, 0.4, 0.9);
      const head = new THREE.SphereGeometry(0.28, 8, 6);
      const [hx, hy] = G(0, 1.7);
      batch.addGeometry(stoneW, head, M.makeTranslation(hx, hy, AH + 0.5));
      head.dispose();
      // jamb pilasters and the iron gates
      for (const s of [-AW / 2 - 0.6, AW / 2 + 0.6]) B(stone, s, 1.45, 0, 0.7, 0.3, AH - AW / 2);
      const iron = kit.mat('#1f2326', { roughness: 0.5, metalness: 0.4 });
      for (let s = -AW / 2 + 0.15; s < AW / 2; s += 0.18) B(iron, s, 1.42, 0, 0.04, 0.04, 3.6);
      B(iron, 0, 1.42, 3.4, AW, 0.06, 0.08);
      B(iron, 0, 1.42, 1.0, AW, 0.06, 0.08);
    }
    // Two-storey stone oriel over the arch with mullioned lights.
    {
      const s0 = -3.1,
        s1 = 3.1,
        t0 = 1.3,
        t1 = 2.1;
      B(stone, 0, (t0 + t1) / 2, 8.2, s1 - s0, t1 - t0, 5.8);
      B(stone, 0, (t0 + t1) / 2 - 0.05, 7.9, s1 - s0 - 0.8, t1 - t0 - 0.2, 0.3);
      kit.cornice(batch, stone, [G(s0, t0), G(s1, t0), G(s1, t1), G(s0, t1)].reverse(), 13.9, {
        height: 0.4,
        projection: 0.15,
      });
      for (const z of [8.7, 11.5])
        kit.windowRow(batch, G(s1, t1), G(s0, t1), z, {
          count: 4,
          margin: 0.25,
          width: 1.15,
          height: 2.2,
          depth: 0.14,
          glass,
          frame: stone,
          sill: stone,
          head: 'lintel',
          bars: 1,
        });
      // crested parapet of the oriel
      for (let s = s0 + 0.3; s < s1; s += 0.7) B(stone, s, t1 - 0.1, 14.3, 0.35, 0.2, 0.45);
    }
    // Upper window pair and pediment with the coat of arms.
    win(batch, G(GW / 2 - 1, 1.31), G(-GW / 2 + 1, 1.31), 15.0, {
      count: 3,
      margin: 0.5,
      width: 1.0,
      height: 1.5,
      depth: 0.12,
      glass,
      frame: stone,
      sill: stone,
      head: 'arch',
      bars: 0,
    });
    {
      const s0 = -GW / 2,
        s1 = GW / 2,
        t0 = -0.3,
        t1 = 1.3;
      const z0 = GH,
        z1 = GH + 3.0;
      const A = (s, t, z) => {
        const [x, y] = G(s, t);
        return [x, y, z];
      };
      kit.cornice(batch, stone, [G(s0, t0), G(s1, t0), G(s1, t1), G(s0, t1)].reverse(), GH - 0.5, {
        height: 0.5,
        projection: 0.3,
        steps: 2,
      });
      batch.add(
        stone,
        [A(s1, t1, z0), A(s0, t1, z0), A(0, t1, z1)],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        stone,
        [A(s0, t0, z0), A(s1, t0, z0), A(0, t0, z1)],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      batch.quad(
        stone,
        A(s0, t1 + 0.25, z0 - 0.1),
        A(s0, t0, z0 - 0.1),
        A(0, t0, z1 + 0.15),
        A(0, t1 + 0.25, z1 + 0.15),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        stone,
        A(s1, t0, z0 - 0.1),
        A(s1, t1 + 0.25, z0 - 0.1),
        A(0, t1 + 0.25, z1 + 0.15),
        A(0, t0, z1 + 0.15),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const fin = new THREE.SphereGeometry(0.3, 8, 6);
      batch.addGeometry(stone, fin, M.makeTranslation(...A(0, 0.5, z1 + 0.45)));
      fin.dispose();
    }
    const arms = kit.paintedMaterial('beit_quad:arms', 128, 128, (c, w, h) => {
      c.fillStyle = '#d9d1bd';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#2a4f86';
      c.beginPath();
      c.moveTo(24, 16);
      c.lineTo(104, 16);
      c.lineTo(104, 70);
      c.quadraticCurveTo(104, 108, 64, 120);
      c.quadraticCurveTo(24, 108, 24, 70);
      c.closePath();
      c.fill();
      c.fillStyle = '#c9a54a';
      c.fillRect(24, 16, 80, 26);
      c.fillStyle = '#f2efe6';
      c.fillRect(42, 66, 44, 22);
      c.fillStyle = '#9a3a2a';
      c.fillRect(60, 22, 10, 14);
    });
    {
      const [x, y] = G(0, 1.33);
      const z = GH - 0.2;
      const a = [x - ex * 1.1, y - ey * 1.1],
        b = [x + ex * 1.1, y + ey * 1.1];
      const o = 0.05;
      batch.quad(
        arms,
        [b[0] + nx * o, b[1] + ny * o, z],
        [a[0] + nx * o, a[1] + ny * o, z],
        [a[0] + nx * o, a[1] + ny * o, z + 2.2],
        [b[0] + nx * o, b[1] + ny * o, z + 2.2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // Paved passage through the gateway.
    {
      const p = [G(-AW / 2, -6), G(AW / 2, -6), G(AW / 2, 4), G(-AW / 2, 4)];
      kit.cap(
        batch,
        kit.mat('#bdb4a2', { roughness: 0.95 }),
        [[kit.ringArea(p) < 0 ? p.slice().reverse() : p]],
        0.05,
      );
    }
    g.add(batch.toGroup('beit_quad'));
    root.add(g);
    return root;
  },
};
