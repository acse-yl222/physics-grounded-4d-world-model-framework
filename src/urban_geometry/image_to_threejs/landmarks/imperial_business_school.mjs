// Imperial College Business School (Tanaka Building) and Main Entrance, Exhibition
// Road (Foster and Partners, opened by the Queen 24 June 2004). A 24 m high glass
// facade hung from the roof, fronted on Exhibition Road by a grand colonnade of slim
// white tubular steel columns; behind it a six-storey stainless-steel drum (clad in
// 12 mm stainless tubes) stacks the circular lecture theatres inside an atrium capped
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
      used_for: 'drum clad with 12 mm diameter stainless-steel tubes',
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
    'position inside the atrium, column spacing and the sign lettering are proportioned, not measured. ' +
    'Rear (west) elevations abut older college buildings and are given a plain glazed/panel facade.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const bs = byId['a07c23b2-0d99-4c41-9835-130bfda2187c'].polys[0][0];
    const me = byId['45aceb4e-13a5-49e2-a6b1-8ead0cb3a394'].polys[0][0];
    // Combined outline from both footprints (they share the edge at y ~ -810).
    const pick = (ring, fx, fy) =>
      ring.reduce((best, p) => (fx(p) * 1 + fy(p) > fx(best) + fy(best) ? p : best));
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
    const ring = [SE, NE, NW, SW].map((p) => [p[0], p[1]]);
    if (kit.ringArea(ring) < 0) ring.reverse();

    // Materials.
    const white = kit.mat('#f2f3f1', { roughness: 0.5 });
    const steelTubes = kit.paintedMaterial(
      'imperial_business_school:tubes',
      512,
      128,
      (c, w, h) => {
        for (let x = 0; x < w; x += 4) {
          const k = 0.5 + 0.5 * Math.sin((x / 4) * 1.7);
          const v = Math.round(185 + 60 * k);
          c.fillStyle = `rgb(${v},${v + 3},${v + 6})`;
          c.fillRect(x, 0, 3, h);
          c.fillStyle = '#5c6266';
          c.fillRect(x + 3, 0, 1, h);
        }
      },
      { metalness: 0.25, roughness: 0.35 },
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
    const curtain = kit.paintedMaterial(
      'imperial_business_school:curtain',
      512,
      512,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.fillStyle = 'rgba(120,150,165,0.55)';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#e8ecee';
        for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 4, 0, 8, h); // mullions
        for (let k = 0; k <= 4; k++) c.fillRect(0, (k * h) / 4 - 3, w, 6); // transoms
        c.fillStyle = 'rgba(235,240,242,0.5)';
        for (let k = 0; k < 4; k++) c.fillRect((k * w) / 4 + w / 8 - 1, 0, 2, h);
      },
      {
        transparent: true,
        depthWrite: false,
        roughness: 0.1,
        metalness: 0.3,
        side: THREE.DoubleSide,
      },
    );
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
          c.fillRect(0, y + h * 0.4, w, h * 0.1); // slab edges / balustrades
          c.fillStyle = '#d7c39a';
          for (let k = 0; k < 8; k++) c.fillRect(k * 64 + 8, y + 10, 46, h * 0.36); // lit offices
        }
      },
    );
    const etfe = kit.paintedMaterial('imperial_business_school:etfe', 256, 256, (c, w, h) => {
      c.fillStyle = '#d9dcdc';
      c.fillRect(0, 0, w, h);
      for (let k = 0; k < 4; k++) {
        const grd = c.createLinearGradient(0, (k * h) / 4, 0, ((k + 1) * h) / 4);
        grd.addColorStop(0, '#c4c8c9');
        grd.addColorStop(0.5, '#fbfbfa');
        grd.addColorStop(1, '#c4c8c9');
        c.fillStyle = grd;
        c.fillRect(0, (k * h) / 4 + 3, w, h / 4 - 6);
      }
      c.fillStyle = '#9da3a6';
      for (let k = 0; k <= 4; k++) c.fillRect(0, (k * h) / 4 - 2, w, 4);
    });
    const roofMat = kit.mat('#9b9a95');
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

    // Rear block: solid walls on all sides except the Exhibition Road front.
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
    // Interior back wall of the atrium (offices behind) at w = 12.
    const atriumDepth = Math.min(12, D - 4);
    eW(P(0, atriumDepth), P(L, atriumDepth), interior, 0, H - 0.5);
    // Floor slabs visible through the glass between the front and the drum.
    for (let z = 4.5; z < H - 2; z += 4) {
      const slab = [
        P(0.4, atriumDepth - 2.5),
        P(L - 0.4, atriumDepth - 2.5),
        P(L - 0.4, atriumDepth),
        P(0.4, atriumDepth),
      ];
      kit.cap(batch, kit.mat('#e9e5dc'), [[slab]], z);
      eW(slab[0], slab[1], kit.mat('#e9e5dc'), z - 0.35, z);
    }
    // Ground floor of atrium.
    kit.cap(
      batch,
      kit.mat('paving'),
      [[[P(0, 0), P(L, 0), P(L, atriumDepth), P(0, atriumDepth)]]],
      0.05,
    );

    // Glass curtain wall hung from the roof, set back from the colonnade line.
    const gA = P(0, set),
      gB = P(L, set);
    eW(gA, gB, curtain, 0, H, 6, 6);
    // Return glass on the short ends of the setback zone.
    eW(P(0, set), P(0, 0), curtain, 0, H, 6, 6);
    eW(P(L, 0), P(L, set), curtain, 0, H, 6, 6);

    // Roof: solid over the offices, ETFE over the atrium, deep overhang to the colonnade.
    kit.cap(
      batch,
      roofMat,
      [[[P(0, atriumDepth), P(L, atriumDepth), NW, SW].map((p) => [p[0], p[1]])]],
      H,
    );
    kit.cap(
      batch,
      etfe,
      [[[P(0, -0.6), P(L, -0.6), P(L, atriumDepth), P(0, atriumDepth)]]],
      H + 0.6,
      { scale: 6 },
    );
    kit.cap(
      batch,
      white,
      [[[P(0, -0.6), P(L, -0.6), P(L, atriumDepth), P(0, atriumDepth)]]],
      H + 0.5,
      { down: true },
    );
    // Fascia of the roof canopy and roof edge.
    eW(P(-0.2, -0.8), P(L + 0.2, -0.8), white, H - 0.2, H + 1.0);
    eW(P(L + 0.2, -0.8), P(L + 0.2, atriumDepth), white, H - 0.2, H + 1.0);
    eW(P(-0.2, atriumDepth), P(-0.2, -0.8), white, H - 0.2, H + 1.0);
    // ETFE roof ribs.
    for (let a = 2; a < L; a += 4) {
      const [x, y] = P(a, atriumDepth / 2 - 0.3);
      kit.box(batch, white, x, y, H + 0.55, 0.3, atriumDepth + 0.6, 0.5, ang);
    }

    // Grand colonnade of slim white tubular columns on the street line.
    const colGeo = new THREE.CylinderGeometry(0.28, 0.28, H, 10).rotateX(Math.PI / 2);
    const nCol = Math.round(L / 3.6);
    for (let i = 0; i <= nCol; i++) {
      const [x, y] = P((i * L) / nCol, -0.3);
      batch.addGeometry(white, colGeo, new THREE.Matrix4().makeTranslation(x, y, H / 2));
    }
    // Brise-soleil fins between colonnade and glass at two upper levels.
    for (const z of [9, 15, 21]) {
      const [x, y] = P(L / 2, set / 2 - 0.2);
      kit.box(batch, white, x, y, z, L, set - 0.4, 0.15, ang);
    }

    // Stainless-steel drum of lecture theatres inside the atrium.
    const R = 5.6;
    const [dx, dy] = P(L * 0.62, R + set + 0.6);
    const drumH = H + 1.6;
    const drum = new THREE.CylinderGeometry(R, R, drumH, 48, 1, true).rotateX(Math.PI / 2);
    // Scale UVs so the tube texture repeats around the drum.
    const uv = drum.attributes.uv;
    for (let k = 0; k < uv.count; k++) uv.setX(k, uv.getX(k) * 8);
    batch.addGeometry(steelTubes, drum, new THREE.Matrix4().makeTranslation(dx, dy, drumH / 2));
    const lid = new THREE.CircleGeometry(R, 48);
    batch.addGeometry(
      kit.mat('aluminium'),
      lid,
      new THREE.Matrix4().makeTranslation(dx, dy, drumH),
    );
    // Drum projects above the ETFE roof: rim ring.
    const rim = new THREE.TorusGeometry(R, 0.18, 6, 48);
    batch.addGeometry(white, rim, new THREE.Matrix4().makeTranslation(dx, dy, drumH));

    // Main Entrance bay (southern footprint): canopy and Imperial sign.
    const meDepth = Math.hypot(
      SE[0] -
        pick(
          me,
          (p) => p[0],
          (p) => p[1],
        )[0],
      SE[1] -
        pick(
          me,
          (p) => p[0],
          (p) => p[1],
        )[1],
    );
    const eLen = Math.min(meDepth, 18);
    const [cx, cy] = P(eLen / 2, -0.6);
    kit.box(batch, white, cx, cy, 4.6, eLen - 1, 4.4, 0.45, ang);
    kit.box(batch, kit.mat('#2c3339'), cx, cy, 4.5, eLen - 1.4, 4.2, 0.1, ang);
    // Sign band on the canopy front edge.
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
    // Entrance doors (dark recess in the glass line).
    const d0 = P(eLen * 0.3, set - 0.05),
      d1 = P(eLen * 0.7, set - 0.05);
    batch.quad(
      kit.mat('dark_glass'),
      [d0[0], d0[1], 0],
      [d1[0], d1[1], 0],
      [d1[0], d1[1], 3.6],
      [d0[0], d0[1], 3.6],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );
    // Paving under the colonnade.
    kit.cap(batch, kit.mat('paving'), [[[P(0, -1.2), P(L, -1.2), P(L, set), P(0, set)]]], 0.04);

    g.add(batch.toGroup('imperial_business_school'));
    return g;
  },
};
