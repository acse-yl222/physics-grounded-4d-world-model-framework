// Grosvenor Bridge (Victoria Railway Bridge): Sir John Fowler's 1860 crossing into
// Victoria, widened 1865-66 and 1907, rebuilt in steel 1963-67 as ten separate
// side-by-side arch bridges, one per track, on the original piers encased in
// concrete. Four main arch spans of 53.3 m between three river piers.
export default {
  id: 'grosvenor_bridge',
  name: 'Grosvenor Bridge',
  claims: [],
  references: [
    {
      title: 'Grosvenor Bridge - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Grosvenor_Bridge',
      used_for: 'history, 1963-67 rebuild, width 54 m, longest span 53.3 m',
    },
    {
      title: 'Grosvenor Bridge (1967) - Structurae',
      url: 'https://structurae.net/en/structures/grosvenor-bridge-1967',
      used_for: 'span list (4 x 53.34 m), ten tracks',
    },
    {
      title: '9 secrets of the Grosvenor railway bridge - Londonist',
      url: 'https://londonist.com/london/transport/9-secrets-of-the-grosvenor-railway-bridge',
      used_for: 'new steel arches replacing the old structure',
    },
    {
      title: 'Two Bridges in One - Shady Old Lady',
      url: 'https://www.shadyoldlady.com/location/1438',
      used_for: 'ten separate bridges, one per line, original piers encased in concrete',
    },
  ],
  notes:
    'No footprint; extent from the scene rail segments (level 1, deck 6.5 m) crossing the Thames at x~3657-3698 and ' +
    'pier positions from the gaps in the scene river polygons. Arch rise, rib count and colour (grey steel) are ' +
    'approximate. The generic rail layer still draws solid brick sides under each elevated track ribbon.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = [3677.5, -2312],
      B = [3679.5, -2549];
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const d = [(B[0] - A[0]) / L, (B[1] - A[1]) / L],
      n = [-d[1], d[0]];
    const ang = Math.atan2(d[1], d[0]);
    const P = (s, t, z) => [A[0] + d[0] * s + n[0] * t, A[1] + d[1] * s + n[1] * t, z];
    const proj = ([x, y]) => (x - A[0]) * d[0] + (y - A[1]) * d[1];
    const piers = [
      [3689, -2372.5],
      [3690, -2429.5],
      [3690, -2487],
    ].map(proj);
    const W = 48,
      DECK = 6.35;

    const steel = kit.mat('#7d878d', { roughness: 0.55, metalness: 0.4 });
    const steelDark = kit.mat('#566066', { roughness: 0.6, metalness: 0.4 });
    const conc = kit.mat('#a39f97', { roughness: 0.9 });
    const ballast = kit.mat('#6d665c', { roughness: 1 });
    const ribPanel = kit.paintedMaterial(
      'grosvenor_bridge:spandrel',
      256,
      64,
      (c, w, h) => {
        c.fillStyle = '#7d878d';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#4c555a';
        for (let k = 0; k < 8; k++) c.fillRect(k * 32 + 14, 0, 4, h); // spandrel posts
        c.fillStyle = '#9aa3a8';
        c.fillRect(0, 0, w, 6);
      },
      { roughness: 0.55, metalness: 0.3 },
    );
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = ang) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));

    // Deck slab (ballast top just under the scene's rail ribbons).
    const deck = [P(-4, -W / 2, 0), P(L + 4, -W / 2, 0), P(L + 4, W / 2, 0), P(-4, W / 2, 0)];
    kit.cap(batch, ballast, [[deck.map(([x, y]) => [x, y])]], DECK);
    kit.walls(batch, steelDark, [[deck.map(([x, y]) => [x, y])]], DECK - 1.1, DECK + 0.1, {});
    kit.cap(batch, steelDark, [[deck.map(([x, y]) => [x, y])]], DECK - 1.1, { down: true });
    // ten tracks (the scene's rail ribbons over the river are mostly at ground level)
    const rail = kit.road('rail');
    for (let r = 0; r < 10; r++) {
      const t = -20.5 + (r * 41) / 9;
      batch.quad(
        rail,
        P(-4, t - 1.7, DECK + 0.05),
        P(L + 4, t - 1.7, DECK + 0.05),
        P(L + 4, t + 1.7, DECK + 0.05),
        P(-4, t + 1.7, DECK + 0.05),
        [1, 0],
        [1, (L + 8) / 6],
        [0, (L + 8) / 6],
        [0, 0],
      );
    }
    // parapets
    for (const side of [-1, 1]) {
      const [x, y] = P(L / 2, side * (W / 2 - 0.2), 0);
      kit.box(batch, steel, x, y, DECK, L + 8, 0.4, 1.2, ang);
    }

    // Arch spans: 10 parallel bridges; each outer face carries a spandrel panel.
    const bounds = [0, ...piers, L];
    const PL = 5; // pier length along the bridge
    const ribs = 10;
    for (let k = 0; k < bounds.length - 1; k++) {
      const sa = bounds[k] + (k === 0 ? 1 : PL / 2),
        sb = bounds[k + 1] - (k === bounds.length - 2 ? 1 : PL / 2);
      const mid = (sa + sb) / 2,
        half = (sb - sa) / 2;
      const spring = 0.3,
        crown = DECK - 1.4;
      const arch = (s) => spring + (crown - spring) * (1 - ((s - mid) / half) ** 2);
      const M = 18;
      for (let j = 0; j < M; j++) {
        const a = sa + ((sb - sa) * j) / M,
          b = sa + ((sb - sa) * (j + 1)) / M;
        const za = arch(a),
          zb = arch(b);
        for (const side of [-1, 1]) {
          const t = side * (W / 2 - 0.5);
          const q = [P(a, t, za), P(b, t, zb), P(b, t, DECK - 1.1), P(a, t, DECK - 1.1)];
          const uv = [
            [a / 8, za / 4],
            [b / 8, zb / 4],
            [b / 8, (DECK - 1.1) / 4],
            [a / 8, (DECK - 1.1) / 4],
          ];
          if (side > 0) batch.quad(ribPanel, q[1], q[0], q[3], q[2], uv[1], uv[0], uv[3], uv[2]);
          else batch.quad(ribPanel, ...q, ...uv);
        }
        // inner arch ribs, one pair of flanges per track bridge
        for (let r = 0; r < ribs; r++) {
          const t = -W / 2 + 2.4 + (r * (W - 4.8)) / (ribs - 1);
          const ma = P(a, t, za),
            mb = P(b, t, zb);
          const len = Math.hypot(mb[0] - ma[0], mb[1] - ma[1], mb[2] - ma[2]);
          const pitch = Math.atan2(zb - za, b - a);
          const geo = new THREE.BoxGeometry(len, 0.7, 1.1);
          m4.makeRotationZ(ang).multiply(new THREE.Matrix4().makeRotationY(-pitch));
          m4.setPosition((ma[0] + mb[0]) / 2, (ma[1] + mb[1]) / 2, (za + zb) / 2);
          batch.addGeometry(steelDark, geo, m4);
        }
      }
    }

    // Concrete-encased piers with rounded cutwaters, and abutments.
    for (const s of piers) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, conc, x, y, 0, PL, W + 1, DECK - 1.1, ang);
      for (const side of [-1, 1]) {
        const [cx, cy] = P(s, side * (W / 2 + 0.5), 0);
        put(
          conc,
          new THREE.CylinderGeometry(PL / 2, PL / 2, DECK - 1.1, 12, 1, false, 0, Math.PI).rotateX(
            Math.PI / 2,
          ),
          cx,
          cy,
          (DECK - 1.1) / 2,
          ang + (side > 0 ? -Math.PI / 2 : Math.PI / 2),
        );
      }
      kit.box(batch, steel, x, y, DECK - 1.1, PL + 0.4, W + 0.4, 0.3, ang);
    }
    for (const s of [-1.5, L + 1.5]) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, conc, x, y, 0, 5, W + 2, DECK - 1.1, ang);
    }

    g.add(batch.toGroup('grosvenor_bridge'));
    return g;
  },
};
