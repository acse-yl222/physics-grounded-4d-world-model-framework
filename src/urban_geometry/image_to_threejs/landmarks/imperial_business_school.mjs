// Imperial College Business School (Tanaka Building) and Main Entrance, Exhibition
// Road (Foster and Partners, opened by the Queen 24 June 2004). A 24 m high glass
// facade hung from the roof, fronted on Exhibition Road by a grand colonnade of slim
// white tubular steel columns; behind it a six-storey stainless-steel drum (clad in
// horizontal 12 mm stainless tubes) stacks the circular lecture theatres inside an atrium capped
// with white translucent ETFE pillows. The south bay is the College's glass-fronted
// Main Entrance with a weather canopy.
export default {
  id: 'imperial_business_school',
  name: 'Imperial College Business School and Main Entrance',
  claims: [
    'a07c23b2-0d99-4c41-9835-130bfda2187c', // Imperial College Business School
    '45aceb4e-13a5-49e2-a6b1-8ead0cb3a394', // Imperial College Main Entrance
  ],
  references: [
    {
      title: 'Imperial College Business School - Foster + Partners',
      url: 'https://www.fosterandpartners.com/projects/imperial-college-business-school',
      used_for:
        'six-storey stainless steel drum with lecture theatres, grand colonnade on Exhibition Road',
    },
    {
      title: 'The Queen opens Tanaka Business School - Foster + Partners (24 June 2004)',
      url: 'https://www.fosterandpartners.com/news/the-queen-opens-tanaka-business-school-at-imperial-college-london',
      used_for: 'opening date, highly visible College entrance on Exhibition Road',
    },
    {
      title: 'Tanaka Business School topping out - Foster + Partners',
      url: 'https://www.fosterandpartners.com/news/tanaka-business-school-at-imperial-college-london-topping-out',
      used_for:
        'drum clad with 12 mm stainless-steel tubes; glass facade hung from the roof with wind loads taken to ' +
        'the columns by slender T-section struts; ETFE pillows 20 x 4.2 m',
    },
    {
      title: 'Imperial history - Building magazine',
      url: 'https://www.building.co.uk/focus/imperial-history/3032948.article',
      used_for:
        'drum sheathed in narrow horizontal stainless-steel tubes acting as acoustic baffles',
    },
    {
      title: 'Imperial College (Tanaka) Business School - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2000/imperialcollege.html',
      used_for: 'row of white columns in front of a 24 m high glass facade; ETFE atrium roof',
    },
    {
      title: 'Imperial College London Main Entrance - venue page',
      url: 'https://www.imperial.ac.uk/events-and-hospitality/venues/main-entrance/',
      used_for: 'glass-fronted main entrance',
    },
    {
      title: 'Access guide: Main Entrance building - AccessAble',
      url: 'https://www.accessable.co.uk/imperial-college-london/south-kensington-campus/access-guides/main-entrance-building',
      used_for: 'canopy / recess over the entrance',
    },
  ],
  notes:
    'Height raised from the footprint value (15-17 m) to the documented 24 m glass facade. Drum diameter, ' +
    'position inside the atrium, column spacing (3.6 m), strut levels, mullion module (1.5 m) and the sign ' +
    'lettering are proportioned, not measured. Rear (west) elevations abut older college buildings and are ' +
    'given a plain painted glazed/panel facade. Bollards, cycle stands and benches on the Exhibition Road ' +
    'footway are indicative.',
  build({ THREE, kit, byId, placeAssets }) {
    const root = new THREE.Group();
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const M = new THREE.Matrix4();
    const bs = byId['a07c23b2-0d99-4c41-9835-130bfda2187c'].polys[0][0];
    const me = byId['45aceb4e-13a5-49e2-a6b1-8ead0cb3a394'].polys[0][0];
    const pick = (ring, fx, fy) =>
      ring.reduce((best, p) => (fx(p) + fy(p) > fx(best) + fy(best) ? p : best));
    const NE = pick(
      bs,
      (p) => p[0],
      (p) => p[1],
    );
    const NW = pick(
      bs,
      (p) => -p[0],
      (p) => p[1],
    );
    const SE = pick(
      me,
      (p) => p[0],
      (p) => -p[1],
    );
    const SW = pick(
      me,
      (p) => -p[0],
      (p) => -p[1],
    );
    // Local frame: u along the Exhibition Road (east) front from S to N, w inward (west).
    const ux = NE[0] - SE[0],
      uy = NE[1] - SE[1];
    const L = Math.hypot(ux, uy);
    const u = [ux / L, uy / L],
      wv = [-u[1], u[0]];
    const P = (a, b) => [SE[0] + u[0] * a + wv[0] * b, SE[1] + u[1] * a + wv[1] * b];
    const ang = Math.atan2(u[1], u[0]);
    const depthAt = (p) => (p[0] - SE[0]) * wv[0] + (p[1] - SE[1]) * wv[1];
    const D = Math.min(depthAt(NW), depthAt(SW));
    const H = 24;
    const Bx = (m, a, b, z0, w, d, h, rot = 0) => {
      const [x, y] = P(a, b);
      kit.box(batch, m, x, y, z0, w, d, h, ang + rot);
    };
    const cyl = (m, r0, r1, h, a, b, z0, seg = 12) => {
      const [x, y] = P(a, b);
      const geo = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, geo, M.makeTranslation(x, y, z0 + h / 2));
      geo.dispose();
    };

    // Materials.
    const white = kit.mat('#f2f3f1', { roughness: 0.5 });
    const whiteSteel = kit.mat('white_steel');
    const steelTubes = kit.paintedMaterial(
      'imperial_business_school:tubes_h',
      128,
      512,
      (c, w, h) => {
        // horizontal 12 mm tubes with dark vent gaps
        for (let y = 0; y < h; y += 4) {
          const k = 0.5 + 0.5 * Math.sin((y / 4) * 1.3);
          const v = Math.round(180 + 60 * k);
          c.fillStyle = `rgb(${v},${v + 3},${v + 7})`;
          c.fillRect(0, y, w, 3);
          c.fillStyle = '#4f565b';
          c.fillRect(0, y + 3, w, 1);
        }
      },
      { metalness: 0.45, roughness: 0.3 },
    );
    const rearFacade = kit.paintedMaterial('imperial_business_school:rear', 512, 512, (c, w, h) => {
      c.fillStyle = '#c9cdcf';
      c.fillRect(0, 0, w, h);
      for (let s = 0; s < 2; s++) {
        const y = s * (h / 2);
        c.fillStyle = '#3b4952';
        c.fillRect(0, y + h * 0.06, w, h * 0.3);
        c.fillStyle = '#9ea4a8';
        for (let k = 0; k <= 8; k++) c.fillRect((k * w) / 8 - 2, y + h * 0.06, 4, h * 0.3);
      }
    });
    const curtain = kit.mat('#86a6b6', {
      transparent: true,
      opacity: 0.38,
      depthWrite: false,
      roughness: 0.05,
      metalness: 0.4,
      side: THREE.DoubleSide,
    });
    const balGlass = kit.mat('#b9d0d8', {
      transparent: true,
      opacity: 0.3,
      depthWrite: false,
      roughness: 0.05,
      side: THREE.DoubleSide,
    });
    const interior = kit.paintedMaterial(
      'imperial_business_school:interior',
      512,
      512,
      (c, w, h) => {
        c.fillStyle = '#4a5157';
        c.fillRect(0, 0, w, h);
        for (let s = 0; s < 2; s++) {
          const y = s * (h / 2);
          c.fillStyle = '#e9e5dc';
          c.fillRect(0, y + h * 0.4, w, h * 0.1);
          c.fillStyle = '#d7c39a';
          for (let k = 0; k < 8; k++) c.fillRect(k * 64 + 8, y + 10, 46, h * 0.36);
        }
      },
    );
    const etfe = kit.mat('#eef0ef', { roughness: 0.35, transparent: true, opacity: 0.92 });
    const roofMat = kit.mat('#9b9a95');
    const slabMat = kit.mat('#e9e5dc');
    const floorMat = kit.mat('#d8d2c6', { roughness: 0.5 });
    const plant = kit.mat('#b8bbbb');
    const navy = '#003e74';
    const sign = kit.paintedMaterial('imperial_business_school:sign', 1024, 128, (c, w, h) => {
      c.fillStyle = '#f4f4f2';
      c.fillRect(0, 0, w, h);
      c.fillStyle = navy;
      c.font = 'bold 74px sans-serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('Imperial College London', w / 2, h / 2 + 4);
    });

    const set = 3.0; // glass line set back behind the colonnade
    const eW = (a, b, m, z0, z1, uScale = 14.4, vScale = 6.4) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      batch.quad(
        m,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, z0 / vScale],
        [len / uScale, z0 / vScale],
        [len / uScale, z1 / vScale],
        [0, z1 / vScale],
      );
    };
    // Envelope back + sides.
    eW(NE, NW, rearFacade, 0, H);
    eW(NW, SW, rearFacade, 0, H);
    eW(SW, SE, rearFacade, 0, H);
    const atriumDepth = Math.min(12, D - 4);
    eW(P(0, atriumDepth), P(L, atriumDepth), interior, 0, H - 0.5);
    // Gallery floors visible through the glass: slab, edge fascia, glass balustrade, handrail.
    for (let z = 4.5; z < H - 2; z += 4) {
      const slab = [
        P(0.4, atriumDepth - 2.5),
        P(L - 0.4, atriumDepth - 2.5),
        P(L - 0.4, atriumDepth),
        P(0.4, atriumDepth),
      ];
      kit.cap(batch, slabMat, [[kit.ringArea(slab) < 0 ? slab.slice().reverse() : slab]], z);
      eW(slab[1], slab[0], slabMat, z - 0.35, z);
      eW(slab[0], slab[1], balGlass, z, z + 1.1);
      Bx(whiteSteel, L / 2, atriumDepth - 2.5, z + 1.1, L - 0.8, 0.08, 0.06);
    }
    kit.cap(batch, floorMat, [[[P(0, 0), P(L, 0), P(L, atriumDepth), P(0, atriumDepth)]]], 0.05);

    // Glass curtain wall hung from the roof: clear glass plus real mullions and transoms.
    const gA = P(0, set),
      gB = P(L, set);
    eW(gA, gB, curtain, 0, H, 6, 6);
    eW(P(0, set), P(0, 0), curtain, 0, H, 6, 6);
    eW(P(L, 0), P(L, set), curtain, 0, H, 6, 6);
    const nM = Math.round(L / 1.5);
    for (let i = 0; i <= nM; i++) Bx(whiteSteel, (i * L) / nM, set - 0.1, 0, 0.07, 0.22, H);
    for (let z = 0; z <= H + 0.01; z += 3) Bx(whiteSteel, L / 2, set - 0.1, z - 0.05, L, 0.18, 0.1);

    // Roof: solid over the offices, ETFE pillows over the atrium, deep overhang to the colonnade.
    kit.cap(
      batch,
      roofMat,
      [[[P(0, atriumDepth), P(L, atriumDepth), NW, SW].map((p) => [p[0], p[1]])]],
      H,
    );
    kit.cap(
      batch,
      white,
      [[[P(0, -0.6), P(L, -0.6), P(L, atriumDepth), P(0, atriumDepth)]]],
      H + 0.5,
      { down: true },
    );
    eW(P(-0.2, -0.8), P(L + 0.2, -0.8), white, H - 0.2, H + 1.0);
    eW(P(L + 0.2, -0.8), P(L + 0.2, atriumDepth), white, H - 0.2, H + 1.0);
    eW(P(-0.2, atriumDepth), P(-0.2, -0.8), white, H - 0.2, H + 1.0);
    kit.cap(
      batch,
      white,
      [[[P(-0.2, -0.8), P(L + 0.2, -0.8), P(L + 0.2, atriumDepth), P(-0.2, atriumDepth)]]],
      H + 0.5,
    );
    // ETFE pillows (4.2 m wide, spanning the atrium) between white steel ribs.
    const nP = Math.max(1, Math.round(L / 4.2));
    const pw = L / nP;
    for (let i = 0; i < nP; i++) {
      const a = (i + 0.5) * pw;
      const geo = new THREE.CylinderGeometry(
        pw / 2 - 0.15,
        pw / 2 - 0.15,
        atriumDepth + 0.4,
        12,
        1,
        false,
        -Math.PI / 2,
        Math.PI,
      );
      geo.rotateZ(Math.PI / 2); // axis along x (local), then lies flat
      geo.scale(1, 1, 1);
      const [x, y] = P(a, atriumDepth / 2 - 0.4);
      const mm = new THREE.Matrix4()
        .makeRotationZ(ang + Math.PI / 2)
        .multiply(new THREE.Matrix4().makeScale(1, 1, 0.22));
      mm.setPosition(x, y, H + 1.0);
      batch.addGeometry(etfe, geo, mm);
      geo.dispose();
      Bx(whiteSteel, i * pw, atriumDepth / 2 - 0.4, H + 0.6, 0.3, atriumDepth + 0.8, 0.55);
    }
    Bx(whiteSteel, L, atriumDepth / 2 - 0.4, H + 0.6, 0.3, atriumDepth + 0.8, 0.55);
    // Roof plant and lift overruns on the solid office roof.
    for (const [a, b, w, d, h] of [
      [L * 0.25, (atriumDepth + D) / 2, 8, 5, 2.6],
      [L * 0.7, (atriumDepth + D) / 2, 10, 5.5, 3.0],
    ]) {
      Bx(plant, a, b, H, w, d, h);
      for (let z = H + 0.4; z < H + h - 0.2; z += 0.35)
        Bx(kit.mat('#8f9496'), a, b, z, w + 0.05, d + 0.05, 0.08);
      Bx(white, a, b, H + h, w + 0.3, d + 0.3, 0.15);
    }
    // Parapet with handrail around the solid roof.
    kit.balustrade(
      batch,
      whiteSteel,
      [P(0, atriumDepth), NW, SW, P(0, atriumDepth)].map((p) => [p[0], p[1]]),
      H,
      { height: 1.0, spacing: 1.4 },
    );

    // Grand colonnade of slim white tubular columns with shoes and heads; T-section
    // wind struts from the hung glass back to each column every 3 m.
    const nCol = Math.round(L / 3.6);
    for (let i = 0; i <= nCol; i++) {
      const a = (i * L) / nCol;
      cyl(white, 0.3, 0.26, H - 0.2, a, -0.3, 0.2, 14);
      cyl(whiteSteel, 0.42, 0.36, 0.2, a, -0.3, 0, 14);
      cyl(whiteSteel, 0.27, 0.4, 0.4, a, -0.3, H - 0.4, 14);
      for (let z = 3; z < H - 1; z += 3) {
        Bx(whiteSteel, a, set / 2 - 0.15, z - 0.05, 0.06, set - 0.3, 0.22);
        Bx(whiteSteel, a, set / 2 - 0.15, z + 0.15, 0.18, set - 0.3, 0.04);
      }
    }

    // Stainless-steel drum of lecture theatres inside the atrium: horizontal tube skin,
    // vertical ribs, floor bands and a rim above the ETFE.
    const R = 5.6;
    const dU = L * 0.62,
      dW = R + set + 0.6;
    const [dx, dy] = P(dU, dW);
    const drumH = H + 1.6;
    const drum = new THREE.CylinderGeometry(R, R, drumH, 48, 1, true).rotateX(Math.PI / 2);
    const uv = drum.attributes.uv;
    for (let k = 0; k < uv.count; k++) uv.setY(k, uv.getY(k) * 6);
    batch.addGeometry(steelTubes, drum, M.makeTranslation(dx, dy, drumH / 2));
    drum.dispose();
    const lid = new THREE.CircleGeometry(R, 48);
    batch.addGeometry(kit.mat('aluminium'), lid, M.makeTranslation(dx, dy, drumH));
    lid.dispose();
    for (let i = 0; i < 24; i++) {
      const t = (i / 24) * Math.PI * 2;
      kit.box(
        batch,
        kit.mat('steel'),
        dx + Math.cos(t) * (R + 0.06),
        dy + Math.sin(t) * (R + 0.06),
        0,
        0.12,
        0.12,
        drumH,
        t,
      );
    }
    for (let z = 4.5; z < drumH; z += 4) {
      const band = new THREE.TorusGeometry(R + 0.05, 0.12, 4, 48);
      batch.addGeometry(kit.mat('steel'), band, M.makeTranslation(dx, dy, z));
      band.dispose();
    }
    const rim = new THREE.TorusGeometry(R, 0.18, 6, 48);
    batch.addGeometry(white, rim, M.makeTranslation(dx, dy, drumH));
    rim.dispose();
    const sky = new THREE.CylinderGeometry(1.6, 2.0, 0.6, 16).rotateX(Math.PI / 2);
    batch.addGeometry(
      kit.mat('#9db9c6', { roughness: 0.1, metalness: 0.3 }),
      sky,
      M.makeTranslation(dx, dy, drumH + 0.3),
    );
    sky.dispose();

    // Main Entrance bay (southern footprint): canopy, sign, revolving door and glass doors.
    const meNE = pick(
      me,
      (p) => p[0],
      (p) => p[1],
    );
    const meDepth = Math.hypot(SE[0] - meNE[0], SE[1] - meNE[1]);
    const eLen = Math.min(meDepth, 18);
    Bx(white, eLen / 2, -0.6, 4.6, eLen - 1, 4.4, 0.45);
    Bx(kit.mat('#2c3339'), eLen / 2, -0.6, 4.5, eLen - 1.4, 4.2, 0.1);
    for (let a = 1.5; a < eLen - 1; a += 1.6)
      Bx(
        kit.mat('#fff6dc', { emissive: new THREE.Color('#fff0c8'), emissiveIntensity: 0.4 }),
        a,
        -0.6,
        4.48,
        0.25,
        0.25,
        0.03,
      );
    const s0 = P(1, -2.85),
      s1 = P(eLen - 1, -2.85);
    batch.quad(
      sign,
      [s0[0], s0[1], 5.05],
      [s1[0], s1[1], 5.05],
      [s1[0], s1[1], 6.25],
      [s0[0], s0[1], 6.25],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );
    // revolving door drum with a canopy disc, sliding doors either side
    cyl(kit.mat('dark_glass'), 1.4, 1.4, 2.6, eLen / 2, set - 0.4, 0, 20);
    cyl(whiteSteel, 1.5, 1.5, 0.3, eLen / 2, set - 0.4, 2.6, 20);
    for (const off of [-3.2, 3.2]) {
      Bx(kit.mat('dark_glass'), eLen / 2 + off, set - 0.08, 0, 2.4, 0.06, 2.8);
      Bx(whiteSteel, eLen / 2 + off, set - 0.12, 2.8, 2.6, 0.1, 0.12);
    }
    // Paving under the colonnade and along the frontage with a granite kerb line.
    kit.cap(
      batch,
      kit.mat('paving'),
      [[[P(-1, -4.5), P(L + 1, -4.5), P(L + 1, set), P(-1, set)]]],
      0.04,
    );
    for (let a = 0; a < L; a += 1.2) Bx(kit.mat('#a59f93'), a + 0.6, -2.0, 0.04, 1.1, 0.5, 0.02);

    g.add(batch.toGroup('imperial_business_school'));
    root.add(g);
    // Street furniture on the Exhibition Road footway.
    const bol = [];
    for (let a = eLen + 2; a < L - 1; a += 2.4) {
      const [x, y] = P(a, -4.0);
      bol.push([x, y, ang]);
    }
    root.add(placeAssets('bollard', bol));
    const stands = [];
    for (let a = 2; a < eLen - 1; a += 1.2) {
      const [x, y] = P(a, -3.6);
      stands.push([x, y, ang + Math.PI / 2]);
    }
    root.add(placeAssets('bicycle_stand', stands.slice(0, 6)));
    const [b1x, b1y] = P(L * 0.55, -3.4),
      [b2x, b2y] = P(L * 0.8, -3.4);
    root.add(
      placeAssets('bench', [
        [b1x, b1y, ang - Math.PI],
        [b2x, b2y, ang - Math.PI],
      ]),
    );
    return root;
  },
};
