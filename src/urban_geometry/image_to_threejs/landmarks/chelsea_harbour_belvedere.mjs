// The Belvedere, Chelsea Harbour (Moxley Jenner & Partners, 1986-89): the ~200 ft
// residential tower that is the focal point of the Chelsea Harbour development.
// Bronze-coloured cladding with rows of dark blue metal balconies, a metallic
// pagoda-like roof and a mast carrying the gilded ball (which rises and falls with
// the tide).
export default {
  id: 'chelsea_harbour_belvedere',
  name: 'The Belvedere, Chelsea Harbour',
  claims: ['b949d968-5c44-48f1-a104-b7d8cf7521bf'],
  references: [
    {
      title: 'Chelsea Harbour - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Chelsea_Harbour',
      used_for: 'Moxley Jenner & Partners, 1986-89 development, Belvedere tower',
    },
    {
      title: 'Belvedere Tower, Chelsea Harbour, London - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1980/belvedere.html',
      used_for:
        '200 ft tower, bronze cladding, dark blue metal balconies, metallic pagoda-like roof',
    },
    {
      title: 'The Belvedere - Buildington',
      url: 'https://www.buildington.co.uk/buildings/images/10273',
      used_for: 'building record',
    },
    {
      title: 'The Belvedere residential development, Chelsea Harbour (1999) - London Museum',
      url: 'https://londonmuseum.org.uk/collections/v/object-743457/the-belvedere-residential-development-chelsea-harbour',
      used_for: 'photograph record (caption only)',
    },
  ],
  notes:
    'Square Overture footprint chamfered into an octagon; body to 52 m and pagoda roof to ~61 m (200 ft), mast and ' +
    'gilded ball above. The tide ball is drawn at mid height on its mast; it is named in the brief but no returned ' +
    'source confirmed it. Balcony rhythm and roof tier proportions estimated.',
  build({ THREE, kit, buildings, frame }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const { cx, cy } = frame;
    const ang = frame.angle;
    const S = Math.min(frame.length, frame.width); // ~16.6 m
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const W = (u, v) => [cx + u * ca - v * sa, cy + u * sa + v * ca];
    const half = S / 2,
      ch = S * 0.2;
    const oct = [
      [-half + ch, -half],
      [half - ch, -half],
      [half, -half + ch],
      [half, half - ch],
      [half - ch, half],
      [-half + ch, half],
      [-half, half - ch],
      [-half, -half + ch],
    ].map(([u, v]) => W(u, v));
    const BODY = 52;

    const clad = kit.paintedMaterial(
      'chelsea_harbour_belvedere:clad',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#9a7a55';
        c.fillRect(0, 0, w, h);
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 4; k++) {
            const x = k * 64,
              y = s * 128;
            c.fillStyle = '#2f3b44';
            c.fillRect(x + 10, y + 28, 44, 78);
            c.fillStyle = '#b89870';
            c.fillRect(x + 31, y + 28, 2, 78);
          }
        c.fillStyle = '#7d6142';
        c.fillRect(0, 120, w, 8);
        c.fillRect(0, 248, w, 8);
      },
      { roughness: 0.5, metalness: 0.3 },
    );
    const bronze = kit.mat('#8d6d4b', { roughness: 0.45, metalness: 0.5 });
    const navy = kit.mat('#1f2f52', { roughness: 0.5, metalness: 0.3 });
    const roofMetal = kit.mat('#8f9a9c', { roughness: 0.35, metalness: 0.6 });
    const gold = kit.mat('#e0b43a', { roughness: 0.35, metalness: 0.25 });

    kit.walls(batch, kit.facade('glass', 3), [[oct]], 0, 4.5, { bay: 3.4, storey: 4.5 });
    kit.walls(batch, clad, [[oct]], 4.5, BODY, { bay: 3.4, storey: 3.1, uvBase: 4.5 });
    kit.cap(batch, bronze, [[kit.offsetRing(oct, 0.6)]], BODY);
    kit.walls(batch, bronze, [[kit.offsetRing(oct, 0.6)]], BODY - 0.8, BODY, {});

    // Rows of dark blue metal balconies on the four main faces.
    for (let z = 7.6; z < BODY - 2; z += 3.1)
      for (let k = 0; k < 4; k++) {
        const a = (k * Math.PI) / 2;
        const nu = Math.cos(a),
          nv = Math.sin(a);
        const [x, y] = W(nu * (half + 0.7), nv * (half + 0.7));
        const rz = ang + a + Math.PI / 2;
        kit.box(batch, navy, x, y, z - 0.15, S - 2 * ch - 0.6, 1.4, 0.18, rz);
        const [rx, ry] = W(nu * (half + 1.35), nv * (half + 1.35));
        kit.box(batch, navy, rx, ry, z, S - 2 * ch - 0.6, 0.08, 1.05, rz);
      }

    // Pagoda-like stepped metal roof.
    const tiers = [
      [S * 0.62, BODY, 3.2],
      [S * 0.44, BODY + 3.6, 2.6],
      [S * 0.3, BODY + 6.6, 2.6],
    ];
    for (const [hs, z, rise] of tiers) {
      const sq = [W(-hs, -hs), W(hs, -hs), W(hs, hs), W(-hs, hs)];
      const inner = hs * 0.62;
      const sqi = [W(-inner, -inner), W(inner, -inner), W(inner, inner), W(-inner, inner)];
      // flared skirt: quads from outer square at z to inner square at z + rise
      for (let k = 0; k < 4; k++) {
        const a = sq[k],
          bq = sq[(k + 1) % 4],
          c = sqi[(k + 1) % 4],
          d = sqi[k];
        batch.quad(
          roofMetal,
          [...a, z],
          [...bq, z],
          [...c, z + rise],
          [...d, z + rise],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      kit.walls(batch, bronze, [[sqi]], z + rise, z + rise + 0.8, {});
      kit.cap(batch, roofMetal, [[sqi]], z + rise + 0.8);
    }
    const ztop = BODY + 6.6 + 2.6 + 0.8;
    const rr = S * 0.3 * 0.62;
    const pyr = [W(-rr, -rr), W(rr, -rr), W(rr, rr), W(-rr, rr)];
    kit.pitchedRoof(batch, roofMetal, roofMetal, pyr, ang, ztop, 2.6, 'pyramidal', {
      overhang: 0.1,
    });
    // mast with the gilded tide ball
    const m4 = new THREE.Matrix4();
    batch.addGeometry(
      kit.mat('white_steel'),
      new THREE.CylinderGeometry(0.14, 0.22, 10, 8).rotateX(Math.PI / 2),
      m4.makeTranslation(cx, cy, ztop + 2.6 + 5),
    );
    batch.addGeometry(
      gold,
      new THREE.SphereGeometry(1.0, 16, 12),
      m4.makeTranslation(cx, cy, ztop + 2.6 + 4.5),
    );
    batch.addGeometry(
      gold,
      new THREE.SphereGeometry(0.25, 8, 6),
      m4.makeTranslation(cx, cy, ztop + 2.6 + 10.1),
    );

    g.add(batch.toGroup('chelsea_harbour_belvedere'));
    return g;
  },
};
