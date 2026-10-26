// Craven Cottage, Stevenage Road, Fulham - home of Fulham FC. The Johnny Haynes
// (Stevenage Road) Stand of 1905 by Archibald Leitch (Grade II): a three-storey red-brick
// street front with stone dressings, 27 bays, shaped gables over the centre three bays and
// over bays five and six from each end, a steel and corrugated-iron roof with a central
// triangular pediment facing the pitch and timber seating. In the south-east corner the
// Leitch pavilion ("the Cottage", 1905, Grade II), with a central gable with bargeboards
// and mock timber framing and a balcony overlooking the pitch. Single-tier roofed
// Hammersmith End and Putney End stands close the ends of the ground. The new Riverside
// Stand is a separate module (craven_cottage_riverside_stand).
export default {
  id: 'craven_cottage',
  name: 'Craven Cottage',
  claims: [
    '18bb69ac-8025-4556-9b39-61592a8d5940',
    '2e85782f-23b7-41dc-806f-5af23e717187',
    '37c26bb3-bcb5-4c94-99c8-740b3507fca5',
    'c4e6c905-1b1d-4918-8de7-f64a4f36c19a',
  ],
  references: [
    {
      title: 'Craven Cottage - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Craven_Cottage',
      used_for:
        'stand names, Johnny Haynes Stand renamed after 2005, Leitch 1905, cottage pavilion in the corner',
    },
    {
      title: 'Grandstand and Turnstiles to Fulham Football Club - Historic England',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1079754',
      used_for:
        'Leitch 1905; red brick with stone dressings; steel and corrugated iron roof; street front three storeys of 27 bays, nearly symmetrical, shaped gables over centre three bays and bays 5-6 from each end; central triangular pediment on the roof',
    },
    {
      title: 'Office to South of Grandstand at Fulham Football Club - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1358582',
      used_for:
        'the Cottage pavilion, Leitch 1905, central gable with bargeboarding and mock timber framing',
    },
    {
      title: 'Grandstand and Turnstiles to Fulham Football Club - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101079754-grandstand-and-turnstiles-to-fulham-football-club-palace-riverside-ward',
      used_for: 'listing text (turnstiles on Stevenage Road)',
    },
  ],
  notes:
    'Stand sections (seating rake, roof heights: Haynes Stand street front 11.5 m, roof 13.5 m falling to 10 m ' +
    'at the pitch; end stands 12 m at the back with roofs at 14.5 m) are estimates; Overture heights (3-9 m) ' +
    'are far too low. Shaped-gable outlines, window types per storey and the Cottage’s exact form are ' +
    'interpretive. Pitch, goals and markings are unclaimed ground-level geometry.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const frameOf = (deg, cx, cy) => {
      const a = (deg * Math.PI) / 180,
        c = Math.cos(a),
        s = Math.sin(a);
      return { a, L: (u, v) => [cx + u * c - v * s, cy + u * s + v * c] };
    };
    const rectOf = (F, u0, u1, v0, v1) => {
      const r = [F.L(u0, v0), F.L(u1, v0), F.L(u1, v1), F.L(u0, v1)];
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const brick = kit.paintedMaterial(
      'craven_cottage:brick',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.205);
        c.fillStyle = '#b8a894';
        c.fillRect(0, 0, w, h);
        const rows = 48,
          bw = 21;
        for (let i = 0; i < rows; i++)
          for (let x = -(i % 2) * (bw / 2); x < w; x += bw) {
            const t = 0.84 + r() * 0.28;
            c.fillStyle = `rgb(${Math.round(160 * t)},${Math.round(66 * t)},${Math.round(48 * t)})`;
            c.fillRect(x + 0.6, (i * h) / rows + 0.6, bw - 1.2, h / rows - 1.2);
          }
      },
      { roughness: 0.9 },
    );
    const stone = kit.mat('#ddd2b8', { roughness: 0.8 });
    const glass = kit.mat('#29333b', { roughness: 0.3, metalness: 0.2 });
    const whiteF = kit.mat('#f2efe6');
    const corr = kit.mat('#5e6669', { roughness: 0.6, metalness: 0.3 });
    const steel = kit.mat('#e9e7e1', { roughness: 0.5, metalness: 0.3 });
    const seatW = kit.mat('#f0f0ee', { roughness: 0.6 });
    const seatB = kit.mat('#1d1f21', { roughness: 0.6 });
    const timber = kit.mat('#5a3b26', { roughness: 0.8 });
    const conc = kit.mat('#a7a6a1', { roughness: 0.9 });
    const geo = (m, gm, mtx) => {
      batch.addGeometry(m, gm, mtx);
      gm.dispose();
    };

    // Seating rake from the front (vF, zF) up to the back (vB, zB) in frame F, u0..u1.
    const rake = (F, u0, u1, vF, vB, zF, zB, rows, mats) => {
      const dv = (vB - vF) / rows;
      for (let i = 0; i < rows; i++) {
        const v = vF + dv * (i + 0.5);
        const z = zF + ((zB - zF) * (i + 1)) / rows;
        const c = F.L((u0 + u1) / 2, v);
        kit.box(batch, conc, c[0], c[1], 0, u1 - u0, Math.abs(dv), z, F.a);
        const s = F.L((u0 + u1) / 2, v - dv * 0.2);
        kit.box(
          batch,
          mats[i % mats.length],
          s[0],
          s[1],
          z,
          u1 - u0 - 0.4,
          Math.abs(dv) * 0.35,
          0.45,
          F.a,
        );
      }
    };

    // ---- Johnny Haynes Stand ---------------------------------------------------------------
    const JH = frameOf(113.74, -1419.78, -3490.27); // u: NNW along Stevenage Road; v+: towards the pitch
    {
      const U = 58.4,
        VS = -10.5, // street front
        VP = 10.5, // pitch side
        HS = 11.5;
      // street block (offices, turnstiles, staircases) under the rear of the stand
      const back = rectOf(JH, -U, U, VS, VS + 5.0);
      kit.walls(batch, brick, [[back]], 0, HS, { bay: 1, storey: 2 });
      kit.cap(batch, corr, [[back]], HS);
      for (const [z, h] of [
        [0, 0.8],
        [3.9, 0.3],
        [7.6, 0.3],
        [HS - 0.6, 0.6],
      ]) {
        const r = rectOf(JH, -U - 0.05, U + 0.05, VS - 0.12, VS + 0.05);
        kit.walls(batch, stone, [[r]], z, z + h, { bay: 1e6 });
        kit.cap(batch, stone, [[r]], z + h);
      }
      const sa = JH.L(-U, VS - 0.05),
        sb = JH.L(U, VS - 0.05); // a -> b with outward normal towards Stevenage Road
      const bayW = (2 * U) / 27;
      const isGable = (k) => [4, 5, 12, 13, 14, 21, 22].includes(k); // bays 5-6 from each end and centre 3
      for (let k = 0; k < 27; k++) {
        const t0 = (k * bayW) / (2 * U),
          t1 = ((k + 1) * bayW) / (2 * U);
        const a = [sa[0] + (sb[0] - sa[0]) * t0, sa[1] + (sb[1] - sa[1]) * t0],
          b = [sa[0] + (sb[0] - sa[0]) * t1, sa[1] + (sb[1] - sa[1]) * t1];
        // ground floor: turnstile doorways in alternate bays, windows otherwise
        if (k % 3 === 1) {
          const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          const nx = (sb[1] - sa[1]) / (2 * U),
            ny = -(sb[0] - sa[0]) / (2 * U);
          kit.box(batch, timber, m[0] + nx * 0.04, m[1] + ny * 0.04, 0.2, 1.6, 0.08, 2.6, JH.a);
          kit.box(batch, stone, m[0] + nx * 0.1, m[1] + ny * 0.1, 2.8, 2.0, 0.2, 0.35, JH.a);
        } else
          kit.windowRow(batch, a, b, 1.1, {
            glass,
            frame: whiteF,
            sill: stone,
            head: 'segment',
            count: 1,
            width: 1.3,
            height: 2.0,
            margin: 0.2,
            bars: 1,
          });
        kit.windowRow(batch, a, b, 4.8, {
          glass,
          frame: whiteF,
          sill: stone,
          head: 'lintel',
          count: 1,
          width: 1.5,
          height: 2.0,
          margin: 0.2,
          bars: 2,
        });
        kit.windowRow(batch, a, b, 8.4, {
          glass,
          frame: whiteF,
          sill: stone,
          head: isGable(k) ? 'arch' : 'lintel',
          count: 1,
          width: 1.3,
          height: 1.8,
          margin: 0.2,
          bars: 1,
        });
        // brick pilasters between bays
        const nx = (sb[1] - sa[1]) / (2 * U),
          ny = -(sb[0] - sa[0]) / (2 * U);
        kit.box(batch, brick, a[0] + nx * 0.15, a[1] + ny * 0.15, 0, 0.45, 0.3, HS - 0.6, JH.a);
      }
      // shaped (Dutch) gables rising above the parapet
      const gableShape = (w, h) => {
        const s = new THREE.Shape();
        s.moveTo(-w / 2, 0);
        s.lineTo(-w / 2, h * 0.3);
        s.quadraticCurveTo(-w / 2, h * 0.55, -w * 0.3, h * 0.55);
        s.lineTo(-w * 0.3, h * 0.75);
        s.quadraticCurveTo(-w * 0.3, h * 0.92, -w * 0.12, h * 0.95);
        s.lineTo(-w * 0.12, h);
        s.lineTo(w * 0.12, h);
        s.lineTo(w * 0.12, h * 0.95);
        s.quadraticCurveTo(w * 0.3, h * 0.92, w * 0.3, h * 0.75);
        s.lineTo(w * 0.3, h * 0.55);
        s.quadraticCurveTo(w / 2, h * 0.55, w / 2, h * 0.3);
        s.lineTo(w / 2, 0);
        s.closePath();
        return s;
      };
      for (const [k0, n] of [
        [4, 2],
        [12, 3],
        [21, 2],
      ]) {
        const uc = -U + (k0 + n / 2) * bayW;
        const w = n * bayW,
          h = 4.2;
        const gm = new THREE.ExtrudeGeometry(gableShape(w, h), {
          depth: 0.6,
          bevelEnabled: false,
          curveSegments: 4,
        });
        gm.rotateX(Math.PI / 2); // shape y -> z, extrude along -y
        const p = JH.L(uc, VS - 0.1);
        geo(
          brick,
          gm,
          new THREE.Matrix4().makeRotationZ(JH.a + Math.PI).setPosition(p[0], p[1], HS),
        );
        const cp = new THREE.ExtrudeGeometry(gableShape(w + 0.3, h + 0.3), {
          depth: 0.2,
          bevelEnabled: false,
          curveSegments: 4,
        });
        cp.rotateX(Math.PI / 2);
        const p2 = JH.L(uc, VS + 0.05);
        geo(
          stone,
          cp,
          new THREE.Matrix4().makeRotationZ(JH.a + Math.PI).setPosition(p2[0], p2[1], HS - 0.15),
        );
        const r = JH.L(uc, VS - 0.15);
        kit.box(batch, glass, r[0], r[1], HS + 0.8, w * 0.28, 0.06, 1.6, JH.a);
      }
      // stand roof: corrugated iron sloping down to the pitch, white steel fascia
      const zB = 13.5,
        zF = 10.0;
      {
        const p0 = JH.L(-U, VS + 0.2),
          p1 = JH.L(U, VS + 0.2),
          p2 = JH.L(U, VP + 0.8),
          p3 = JH.L(-U, VP + 0.8);
        const verts = [
          [...p0, zB],
          [...p1, zB],
          [...p2, zF],
          [...p3, zF],
        ];
        const nz = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]);
        batch.add(
          corr,
          verts,
          [
            [0, 0],
            [12, 0],
            [12, 2],
            [0, 2],
          ],
          nz > 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2],
        );
        batch.add(
          steel,
          verts.map(([x, y, z]) => [x, y, z - 0.08]),
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          nz > 0 ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3],
        );
        // rear wall between the street block and the roof
        const rr = rectOf(JH, -U, U, VS, VS + 0.4);
        kit.walls(batch, brick, [[rr]], HS, zB, { bay: 1, storey: 2 });
      }
      const fr = JH.L(0, VP + 0.8);
      kit.box(batch, steel, fr[0], fr[1], zF - 1.0, 2 * U, 0.15, 1.0, JH.a);
      // ends of the stand
      for (const u of [-U, U]) {
        const e = rectOf(JH, u < 0 ? u : u - 0.4, u < 0 ? u + 0.4 : u, VS, VP + 0.8);
        kit.walls(batch, brick, [[e]], 0, zF, { bay: 1, storey: 2 });
        kit.cap(batch, brick, [[e]], zF);
      }
      // central triangular pediment on the roof facing the pitch, with the club name
      {
        const w = 16,
          h = 3.6;
        const pc = JH.L(0, VP + 0.6);
        const tri = new THREE.Shape();
        tri.moveTo(-w / 2, 0);
        tri.lineTo(w / 2, 0);
        tri.lineTo(0, h);
        tri.closePath();
        const gm = new THREE.ExtrudeGeometry(tri, { depth: 0.3, bevelEnabled: false });
        gm.rotateX(Math.PI / 2);
        geo(steel, gm, new THREE.Matrix4().makeRotationZ(JH.a).setPosition(pc[0], pc[1], zF));
        const sign = kit.paintedMaterial(
          'craven_cottage:pediment',
          512,
          96,
          (c, w2, h2) => {
            c.fillStyle = '#f2efe6';
            c.fillRect(0, 0, w2, h2);
            c.fillStyle = '#111111';
            c.font = 'bold 44px serif';
            c.textAlign = 'center';
            c.textBaseline = 'middle';
            c.fillText('FULHAM FOOTBALL CLUB', w2 / 2, h2 / 2 + 2);
          },
          { roughness: 0.6 },
        );
        const a = JH.L(-6, VP + 0.95),
          b = JH.L(6, VP + 0.95);
        // quad facing the pitch (+v): edge a->b along +u has its normal on +v side? ensure by ordering
        batch.quad(
          sign,
          [b[0], b[1], zF - 0.95],
          [a[0], a[1], zF - 0.95],
          [a[0], a[1], zF - 0.05],
          [b[0], b[1], zF - 0.05],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      // roof columns along the front and the seating (upper stand over a paddock)
      for (let u = -U + 6; u <= U - 6; u += 9) {
        const c = JH.L(u, VP - 0.4);
        kit.box(batch, steel, c[0], c[1], 0, 0.3, 0.3, zF - 0.2, JH.a);
      }
      rake(JH, -U + 0.5, U - 0.5, VP - 0.2, VS + 5.0, 0.4, 7.0, 16, [timber, kit.mat('#6b4a32')]);
      const fw = rectOf(JH, -U + 0.5, U - 0.5, VP - 0.25, VP);
      kit.walls(batch, whiteF, [[fw]], 0, 1.2, { bay: 1e6 });
    }

    // ---- the Cottage (pavilion), Leitch 1905 ------------------------------------------------
    {
      const C = frameOf(-13.47, -1391.91, -3557.31); // u- face looks across the pitch corner
      const body = rectOf(C, -10.0, 3.6, -7.7, 7.7);
      const wing = rectOf(C, 3.6, 10.0, -3.8, 6.8);
      const render = kit.mat('#f1ece0', { roughness: 0.85 });
      kit.walls(batch, brick, [[body]], 0, 3.6, { bay: 1, storey: 2 });
      kit.walls(batch, render, [[body]], 3.6, 7.0, { bay: 1e6 });
      kit.pitchedRoof(batch, kit.mat('#7a3d2e'), render, body, C.a, 7.0, 3.8, 'gabled', {
        overhang: 0.5,
      });
      kit.walls(batch, brick, [[wing]], 0, 6.6, { bay: 1, storey: 2 });
      kit.pitchedRoof(
        batch,
        kit.mat('#7a3d2e'),
        brick,
        wing,
        C.a + Math.PI / 2,
        6.6,
        2.6,
        'hipped',
        { overhang: 0.4 },
      );
      // mock timber framing and bargeboards on the pitch-facing gable
      for (let k = -3; k <= 3; k++) {
        const p = C.L(-10.06, k * 2.1);
        kit.box(batch, timber, p[0], p[1], 3.6, 0.08, 0.22, 3.4, C.a);
      }
      for (const z of [3.6, 5.2, 7.0]) {
        const p = C.L(-10.06, 0);
        kit.box(batch, timber, p[0], p[1], z, 0.08, 15.4, 0.2, C.a);
      }
      for (const s of [-1, 1]) {
        const len = Math.hypot(8.2, 3.8);
        const p = C.L(-10.5, s * 4.1);
        const bb = new THREE.BoxGeometry(0.12, len, 0.45);
        geo(
          timber,
          bb,
          new THREE.Matrix4()
            .makeRotationZ(C.a)
            .multiply(new THREE.Matrix4().makeRotationX(s * Math.atan2(3.8, 8.2)))
            .setPosition(p[0], p[1], 7.0 + 1.9),
        );
      }
      // balcony overlooking the pitch
      const bal = rectOf(C, -12.2, -10.0, -6.5, 6.5);
      kit.cap(batch, timber, [[bal]], 3.5);
      kit.cap(batch, timber, [[bal]], 3.3, { down: true });
      kit.balustrade(batch, whiteF, [C.L(-12.2, -6.5), C.L(-12.2, 6.5)], 3.5, {
        height: 1.0,
        spacing: 0.25,
      });
      for (const v of [-6.4, 6.4]) {
        const p = C.L(-12.1, v);
        kit.box(batch, whiteF, p[0], p[1], 0, 0.2, 0.2, 3.3, C.a);
      }
      kit.windowRow(batch, C.L(-10.05, 7.7), C.L(-10.05, -7.7), 4.0, {
        glass,
        frame: whiteF,
        head: 'none',
        count: 3,
        width: 2.2,
        height: 2.0,
        margin: 1.0,
        bars: 3,
      });
      kit.windowRow(batch, C.L(-10.05, 7.7), C.L(-10.05, -7.7), 0.8, {
        glass,
        frame: whiteF,
        head: 'none',
        count: 3,
        width: 1.8,
        height: 2.2,
        margin: 1.4,
        bars: 1,
      });
      for (const [a, b] of [
        [C.L(-10, -7.7), C.L(3.6, -7.7)],
        [C.L(3.6, 7.7), C.L(-10, 7.7)],
      ]) {
        kit.windowRow(batch, a, b, 0.9, {
          glass,
          frame: whiteF,
          head: 'segment',
          width: 1.2,
          height: 1.8,
          bay: 3.2,
          margin: 1.0,
          bars: 1,
        });
        kit.windowRow(batch, a, b, 4.4, {
          glass,
          frame: whiteF,
          head: 'none',
          width: 1.2,
          height: 1.6,
          bay: 3.2,
          margin: 1.0,
          bars: 1,
        });
      }
      // chimney stacks
      for (const u of [-2.5, 2.5]) {
        const p = C.L(u, 0);
        kit.box(batch, brick, p[0], p[1], 9.0, 0.9, 0.7, 2.6, C.a);
      }
    }

    // ---- Hammersmith End and Putney End -----------------------------------------------------
    const endStand = (deg, cx, cy, u0, u1, vF, vB, name) => {
      const F = frameOf(deg, cx, cy);
      const s = Math.sign(vB - vF);
      rake(F, u0, u1, vF, vB - s * 1.0, 0.6, 11.0, 22, [seatW, seatW, seatB]);
      const bw = rectOf(F, u0, u1, vB - s * 1.0, vB);
      const clad = kit.mat('#d9dadb', { roughness: 0.6, metalness: 0.2 });
      kit.walls(batch, clad, [[bw]], 0, 14.5, { bay: 1e6 });
      kit.cap(batch, clad, [[bw]], 14.5);
      // horizontal cladding ribs on the back
      for (let z = 1.5; z < 14.5; z += 1.5) {
        const r = rectOf(F, u0 - 0.05, u1 + 0.05, vB - s * 0.02 - 0.06 * s, vB + 0.06 * s);
        kit.walls(batch, kit.mat('#b7b9bb'), [[r]], z, z + 0.12, { bay: 1e6 });
      }
      // cantilever roof
      const roof = rectOf(F, u0, u1, vB, vF - s * 1.0);
      kit.cap(batch, kit.mat('#e8e8e6'), [[roof]], 14.5);
      kit.cap(batch, kit.mat('#cfd0d0'), [[roof]], 14.0, { down: true });
      kit.walls(batch, kit.mat('#ffffff'), [[roof]], 14.0, 14.5, { bay: 1e6 });
      for (let u = u0 + 2; u <= u1 - 2; u += 8) {
        const p = F.L(u, (vB + vF) / 2);
        kit.box(batch, steel, p[0], p[1], 14.5, 0.5, Math.abs(vB - vF), 0.9, F.a);
      }
      // side screens
      for (const u of [u0, u1]) {
        const e = rectOf(
          F,
          u === u0 ? u0 : u1 - 0.4,
          u === u0 ? u0 + 0.4 : u1,
          Math.min(vF, vB),
          Math.max(vF, vB),
        );
        kit.walls(batch, clad, [[e]], 0, 14.0, { bay: 1e6 });
      }
      const sign = kit.paintedMaterial(
        `craven_cottage:${name}`,
        512,
        64,
        (c, w, h) => {
          c.fillStyle = '#111111';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#ffffff';
          c.font = 'bold 36px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(name, w / 2, h / 2 + 2);
        },
        { roughness: 0.6 },
      );
      const a = F.L(s > 0 ? -12 : 12, vF - s * 1.05),
        b = F.L(s > 0 ? 12 : -12, vF - s * 1.05);
      batch.quad(
        sign,
        [a[0], a[1], 14.0],
        [b[0], b[1], 14.0],
        [b[0], b[1], 14.5],
        [a[0], a[1], 14.5],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    };
    endStand(-156.23, -1496.31, -3439.31, -39.5, 37.1, 18.4, -18.4, 'HAMMERSMITH END');
    endStand(-156.24, -1441.27, -3582.42, -42.1, 37.0, -16.9, 16.9, 'PUTNEY END');

    // ---- pitch ------------------------------------------------------------------------------
    {
      const pitch = kit.paintedMaterial(
        'craven_cottage:pitch',
        512,
        1024,
        (c, w, h) => {
          for (let k = 0; k < 14; k++) {
            c.fillStyle = k % 2 ? '#4f8f3a' : '#5b9c43';
            c.fillRect(0, (k * h) / 14, w, h / 14 + 1);
          }
          c.strokeStyle = '#f4f4f0';
          c.lineWidth = 4;
          const m = 0.06;
          c.strokeRect(w * m, h * m, w * (1 - 2 * m), h * (1 - 2 * m));
          c.beginPath();
          c.moveTo(w * m, h / 2);
          c.lineTo(w * (1 - m), h / 2);
          c.stroke();
          c.beginPath();
          c.arc(w / 2, h / 2, w * 0.13, 0, Math.PI * 2);
          c.stroke();
          for (const y of [h * m, h * (1 - m)]) {
            const d = y < h / 2 ? 1 : -1;
            c.strokeRect(w * 0.28, Math.min(y, y + d * h * 0.14), w * 0.44, h * 0.14);
            c.strokeRect(w * 0.4, Math.min(y, y + d * h * 0.05), w * 0.2, h * 0.05);
          }
        },
        { roughness: 0.95 },
      );
      const u0 = -57.5,
        u1 = 58.0,
        v0 = 11.5,
        v1 = 85.5;
      const p = [JH.L(u0, v0), JH.L(u1, v0), JH.L(u1, v1), JH.L(u0, v1)];
      batch.add(
        pitch,
        p.map(([x, y]) => [x, y, 0.3]),
        [
          [1, 0],
          [1, 1],
          [0, 1],
          [0, 0],
        ],
        kit.ringArea(p) > 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2],
      );
      // goals
      const vm = (v0 + v1) / 2;
      for (const u of [u0 + 0.06 * (u1 - u0), u1 - 0.06 * (u1 - u0)]) {
        const s = u < 0 ? -1 : 1;
        for (const v of [vm - 3.66, vm + 3.66]) {
          const q = JH.L(u, v);
          kit.box(batch, steel, q[0], q[1], 0, 0.12, 0.12, 2.44, JH.a);
        }
        const q = JH.L(u, vm);
        kit.box(batch, steel, q[0], q[1], 2.38, 0.12, 7.44, 0.12, JH.a);
        const n = JH.L(u + s * 1.0, vm);
        kit.box(
          batch,
          kit.mat('#e8e8e8', { transparent: true, opacity: 0.35 }),
          n[0],
          n[1],
          0,
          2.0,
          7.3,
          2.3,
          JH.a,
        );
      }
    }

    g.add(batch.toGroup('craven_cottage'));
    return g;
  },
};
