// Chelsea and Westminster Hospital, 369 Fulham Road (Sheppard Robson, 1989-93, on
// the St Stephen's Hospital site). A deep-plan block of office-like construction
// wrapped round a full-height central "street" and atrium under one of the first
// ETFE cushion roofs; light clad elevations with continuous window bands and a
// glazed entrance on Fulham Road.
export default {
  id: 'chelsea_westminster_hospital',
  name: 'Chelsea and Westminster Hospital',
  claims: ['3348b0f2-e92b-4e04-860b-bdf95db229df'],
  references: [
    {
      title: 'Chelsea and Westminster Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Chelsea_and_Westminster_Hospital',
      used_for: "Sheppard Robson design, St Stephen's site, opened May 1993",
    },
    {
      title: 'Art and surgery - Building magazine',
      url: 'https://www.building.co.uk/focus/art-surgery/1014174.article',
      used_for:
        '(search summary only) central street and atrium, early ETFE membrane roof, office-type construction',
    },
    {
      title: 'Chapel, Chelsea and Westminster Hospital - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2024/04/18/chapel-chelsea-westminster-hospital-fulham-road-chelsea/',
      used_for: 'building context on Fulham Road',
    },
    {
      title: 'Atrium lights - Historic England Archive',
      url: 'https://images.historicenglandservices.org.uk/industry/engineering-construction-building-hospitals/atrium-lights-jlp01-10-55176-24318220.html',
      used_for: 'existence of the large atrium (Laing construction photo record, caption only)',
    },
  ],
  notes:
    'Footprint and 16.9 m height from Overture; atrium position/size (about 120 x 28 m along the long axis) and the ' +
    'vaulted ETFE roof are inferred from descriptions, not measured. Cladding colour (light panels with blue-grey ' +
    'window bands) is approximate: no returned source specified the materials.',
  build({ THREE, kit, buildings, frame }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const H = b.h;
    const ca = Math.cos(frame.angle),
      sa = Math.sin(frame.angle);
    const W = (u, v) => [frame.cx + u * ca - v * sa, frame.cy + u * sa + v * ca];

    const clad = kit.paintedMaterial(
      'chelsea_westminster_hospital:clad',
      256,
      256,
      (c, w, h) => {
        // tile: 4 bays x 2 storeys
        c.fillStyle = '#e6e3da';
        c.fillRect(0, 0, w, h);
        for (let s = 0; s < 2; s++) {
          const y = s * 128;
          c.fillStyle = '#4f6878';
          c.fillRect(0, y + 34, w, 58);
          c.fillStyle = '#8fa6b3';
          for (let k = 0; k < 16; k++) c.fillRect(k * 16, y + 34, 2, 58);
          c.fillStyle = '#cfcbc0';
          c.fillRect(0, y + 92, w, 6);
        }
        c.fillStyle = 'rgba(0,0,0,0.06)';
        for (let k = 0; k < 4; k++) c.fillRect(k * 64, 0, 3, h);
      },
      { roughness: 0.6 },
    );
    const ground = kit.facade('glass', 2);
    const white = kit.mat('#ecebe6', { roughness: 0.6 });
    const roofM = kit.mat('#9a9893', { roughness: 0.95 });
    const glassM = kit.mat('glass');
    const etfe = kit.paintedMaterial(
      'chelsea_westminster_hospital:etfe',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#7f8d96';
        c.fillRect(0, 0, w, h);
        for (let y = 0; y < 2; y++)
          for (let x = 0; x < 2; x++) {
            const grd = c.createRadialGradient(
              x * 64 + 32,
              y * 64 + 32,
              4,
              x * 64 + 32,
              y * 64 + 32,
              34,
            );
            grd.addColorStop(0, '#e8eef1');
            grd.addColorStop(1, '#a9b8c0');
            c.fillStyle = grd;
            c.fillRect(x * 64 + 3, y * 64 + 3, 58, 58);
          }
      },
      { roughness: 0.3, metalness: 0.1 },
    );

    // Perimeter walls: glazed ground floor, clad upper storeys, parapet.
    kit.walls(batch, ground, b.polys, 0, 4.6, { bay: 3.6, storey: 4.6 });
    kit.walls(batch, clad, b.polys, 4.6, H - 0.9, { bay: 3.6, storey: 3.6, uvBase: 4.6 });
    kit.walls(batch, white, b.polys, H - 0.9, H + 0.4, {});

    // Roof with the atrium cut out.
    const AU = Math.min(60, frame.length / 2 - 18),
      AV = Math.min(14, frame.width / 2 - 18);
    const atrium = [W(-AU, -AV), W(AU, -AV), W(AU, AV), W(-AU, AV)];
    const outer = b.polys[0][0];
    const ccw = kit.ringArea(outer) > 0;
    const outerCCW = ccw ? outer : outer.slice().reverse();
    kit.cap(batch, roofM, [[outerCCW, atrium.slice().reverse()]], H);
    // atrium inner glazed walls (facing inward)
    kit.walls(batch, kit.facade('glass', 0), [[atrium.slice().reverse()]], 0, H, {
      bay: 3.6,
      storey: 3.6,
    });
    kit.cap(batch, kit.mat('paving'), [[atrium]], 0.2);

    // Vaulted ETFE roof over the atrium (barrel along the long axis) with steel ribs.
    const rise = 6.5,
      M = 10;
    const prof = [];
    for (let k = 0; k <= M; k++) {
      const v = -AV + (2 * AV * k) / M;
      prof.push([v, H + 0.4 + rise * (1 - (v / AV) ** 2)]);
    }
    for (let k = 0; k < M; k++) {
      const [v0, z0] = prof[k],
        [v1, z1] = prof[k + 1];
      const a = W(-AU, v0),
        bq = W(AU, v0),
        c = W(AU, v1),
        d = W(-AU, v1);
      batch.quad(
        etfe,
        [...a, z0],
        [...bq, z0],
        [...c, z1],
        [...d, z1],
        [0, v0 / 4],
        [AU / 2, v0 / 4],
        [AU / 2, v1 / 4],
        [0, v1 / 4],
      );
    }
    // gable ends
    for (const u of [-AU, AU]) {
      const verts = prof.map(([v, z]) => [...W(u, v), z]);
      const base = [
        [...W(u, AV), H + 0.4],
        [...W(u, -AV), H + 0.4],
      ];
      const all = [...verts, ...base];
      const tris = [];
      const ci = all.length - 1; // fan from one base corner
      for (let k = 0; k < verts.length - 1; k++) tris.push(ci, k, k + 1);
      tris.push(ci, verts.length - 1, verts.length);
      const back = [];
      for (let i = 0; i < tris.length; i += 3) back.push(tris[i], tris[i + 2], tris[i + 1]);
      batch.add(
        glassM,
        all,
        all.map(() => [0, 0]),
        [...tris, ...back],
      );
    }
    for (let u = -AU; u <= AU + 1e-6; u += 7.5) {
      for (let k = 0; k < M; k++) {
        const [v0, z0] = prof[k],
          [v1, z1] = prof[k + 1];
        const p = new THREE.Vector3(...W(u, v0), z0 + 0.15),
          q = new THREE.Vector3(...W(u, v1), z1 + 0.15);
        const len = p.distanceTo(q);
        const geo = new THREE.BoxGeometry(0.35, len, 0.35);
        const m = new THREE.Matrix4().compose(
          p.clone().add(q).multiplyScalar(0.5),
          new THREE.Quaternion().setFromUnitVectors(
            new THREE.Vector3(0, 1, 0),
            q.clone().sub(p).normalize(),
          ),
          new THREE.Vector3(1, 1, 1),
        );
        batch.addGeometry(white, geo, m);
      }
    }

    // Rooftop plant enclosures and lift overruns.
    const r = kit.rng(0.4242);
    for (const [u, v, lw, lv] of [
      [-AU - 9, 0, 10, 22],
      [AU + 9, 0, 10, 22],
      [0, AV + 10, 26, 7],
      [0, -AV - 10, 26, 7],
      [-40, AV + 10, 12, 6],
      [40, -AV - 10, 12, 6],
    ]) {
      const [x, y] = W(u, v);
      kit.box(batch, kit.mat('#b7b4ac'), x, y, H, lw, lv, 2.8 + r() * 1.2, frame.angle);
    }

    // Glazed entrance canopy on the Fulham Road (north-west) front.
    {
      // pick the end of the long axis nearer Fulham Road (to the north-west)
      const uEnd =
        W(frame.length / 2, 0)[1] > W(-frame.length / 2, 0)[1]
          ? frame.length / 2
          : -frame.length / 2;
      const sgn = Math.sign(uEnd);
      const [x, y] = W(uEnd + sgn * 2.5, 0);
      kit.box(batch, glassM, x, y, 4.2, 5, 22, 0.3, frame.angle);
      for (const v of [-10, 10]) {
        const [px, py] = W(uEnd + sgn * 4.6, v);
        kit.box(batch, white, px, py, 0, 0.4, 0.4, 4.2, frame.angle);
      }
      const [ex, ey] = W(uEnd + sgn * 0.15, 0);
      kit.box(batch, kit.mat('dark_glass'), ex, ey, 0, 0.4, 16, 9, frame.angle);
    }

    g.add(batch.toGroup('chelsea_westminster_hospital'));
    return g;
  },
};
