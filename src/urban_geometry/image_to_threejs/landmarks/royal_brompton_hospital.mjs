// Royal Brompton Hospital - Sydney Wing, Sydney Street, Chelsea. The UK's largest
// specialist heart and lung centre; its main building, the Sydney Wing, was opened by
// the Queen in February 1991 when the hospital received its Royal Charter. A large
// late-1980s brick-clad block between Sydney Street and the hospital's older wings, with
// the hospital chapel (Watkins Gray International) on the second floor.
export default {
  id: 'royal_brompton_hospital',
  name: 'Royal Brompton Hospital (Sydney Wing)',
  claims: ['09b31bf8-0049-4b08-aadb-dde4be763761'],
  references: [
    {
      title: 'Royal Brompton Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Brompton_Hospital',
      used_for: 'specialist heart and lung centre on Sydney Street; Sydney Wing opened 1991',
    },
    {
      title: 'Sydney Street - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Sydney_Street',
      used_for: 'location of the hospital on Sydney Street',
    },
    {
      title: 'Chapel, Royal Brompton Hospital, Sydney Street - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2025/11/19/chapel-royal-brompton-hospital-sydney-street-chelsea/',
      used_for: 'chapel on the second floor of the 1980s Sydney Wing by Watkins Gray International',
    },
    {
      title: 'Our hospitals - Royal Brompton & Harefield',
      url: 'https://www.rbht.nhs.uk/node/2796',
      used_for: 'Sydney Wing as the main hospital building, opened 1991',
    },
  ],
  notes:
    'No architectural description was found. Massing follows the Overture footprint; height raised to five ' +
    'storeys (20 m) with a set-back plant/top floor, which is an estimate. Brick colour, window bands, ' +
    'the entrance canopy on Sydney Street, the internal lightwells and the helipad-free roof plant are ' +
    'generic interpretations of a late-1980s hospital block.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const a = (-68.17 * Math.PI) / 180,
      CX = 2062.46,
      CY = -1892.45;
    const ca = Math.cos(a),
      sa = Math.sin(a);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca]; // v = -26.4: Sydney Street front
    const brick = kit.mat('#9a5c43', { roughness: 0.9 });
    const brickL = kit.mat('#c9a78a', { roughness: 0.9 });
    const glass = kit.mat('#2e3d47', { roughness: 0.2, metalness: 0.35 });
    const frameM = kit.mat('#e8e6df');
    const roofM = kit.mat('#878b8b');
    const plant = kit.mat('#a7abac', { roughness: 0.6, metalness: 0.3 });
    const ST = 3.75,
      NS = 5,
      H = NS * ST + 1.2; // 19.95 + parapet
    // two internal lightwells
    const holes = [
      [L(-38, -9), L(-38, 9), L(-14, 9), L(-14, -9)],
      [L(8, -9), L(8, 9), L(34, 9), L(34, -9)],
    ];
    kit.walls(batch, brick, [[ring]], 0, H, { bay: 1e6 });
    for (const h of holes) kit.walls(batch, brickL, [[h]], 0, H + 3.4, { bay: 1e6 });
    kit.cap(batch, roofM, [[ring, ...holes]], H);
    for (const z of [ST + 0.6, H - 0.5])
      kit.cornice(batch, brickL, ring, z - 0.4, { height: 0.4, projection: 0.12 });
    kit.cornice(batch, brickL, ring, 0, { height: 0.8, projection: 0.08 });
    // ribbon windows with light reconstituted-stone bands at every floor
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 4) continue;
      for (let s = 1; s < NS; s++)
        kit.windowRow(batch, p, q, s * ST + 0.95, {
          glass,
          frame: frameM,
          sill: brickL,
          head: 'none',
          width: 1.8,
          height: 1.9,
          bay: 2.4,
          margin: 1.4,
          bars: 1,
          depth: 0.1,
        });
    }
    for (const h of holes)
      for (let k = 0; k < 4; k++) {
        const p = h[k],
          q = h[(k + 1) % 4];
        for (let s = 1; s < NS; s++)
          kit.windowRow(batch, p, q, s * ST + 0.95, {
            glass,
            frame: frameM,
            head: 'none',
            width: 1.6,
            height: 1.8,
            bay: 2.6,
            margin: 1.0,
            bars: 0,
            depth: 0.1,
          });
      }
    // set-back top floor and plant
    const top = [L(-46, -20), L(46, -20), L(46, 20), L(-46, 20)];
    const topR = kit.ringArea(top) < 0 ? top.reverse() : top;
    kit.walls(batch, plant, [[topR]], H, H + 3.4, { bay: 1e6 });
    kit.cap(batch, roofM, [[topR, ...holes]], H + 3.4);
    for (let k = 0; k < 4; k++) {
      const p = topR[k],
        q = topR[(k + 1) % 4];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]),
        ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      for (let s = 0.6; s < len; s += 0.6)
        kit.box(
          batch,
          kit.mat('#8f9596'),
          p[0] + ((q[0] - p[0]) * s) / len,
          p[1] + ((q[1] - p[1]) * s) / len,
          H + 0.2,
          0.08,
          0.15,
          3.0,
          ang,
        );
    }
    for (const [u, v] of [
      [-26, -14],
      [-26, 14],
      [21, -14],
      [21, 14],
    ]) {
      const p = L(u, v);
      kit.box(batch, plant, p[0], p[1], H + 3.4, 6, 3, 1.8, a);
    }
    // main entrance on Sydney Street: glazed double-height entrance with canopy and sign
    {
      const s0 = -8,
        s1 = 8,
        v = -26.4;
      const e0 = L(s0, v - 0.05),
        e1 = L(s1, v - 0.05);
      batch.quad(
        glass,
        [e0[0], e0[1], 0.2],
        [e1[0], e1[1], 0.2],
        [e1[0], e1[1], 2 * ST - 0.4],
        [e0[0], e0[1], 2 * ST - 0.4],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const c = L(0, v - 2.5);
      kit.box(batch, frameM, c[0], c[1], 3.4, 18, 5, 0.35, a);
      for (const s of [-8.5, 8.5]) {
        const p = L(s, v - 4.6);
        kit.box(batch, kit.mat('#5a6266'), p[0], p[1], 0, 0.25, 0.25, 3.4, a);
      }
      const sign = kit.paintedMaterial(
        'royal_brompton:sign',
        1024,
        96,
        (cx, w, h) => {
          cx.fillStyle = '#005eb8';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#ffffff';
          cx.font = 'bold 52px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('Royal Brompton Hospital', w / 2, h / 2 + 3);
        },
        { roughness: 0.5 },
      );
      const p = L(-7, v - 5.02),
        q = L(7, v - 5.02);
      batch.quad(
        sign,
        [p[0], p[1], 3.75],
        [q[0], q[1], 3.75],
        [q[0], q[1], 4.6],
        [p[0], p[1], 4.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      kit.box(batch, frameM, (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, 3.75, 14.2, 0.04, 0.85, a);
    }
    g.add(batch.toGroup('royal_brompton_hospital'));
    return g;
  },
};
