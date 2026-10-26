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
    {
      title: 'Grosvenor Bridge - Structurae',
      url: 'https://structurae.net/en/structures/grosvenor-bridge',
      used_for:
        'ten separate bridges joined together, each holding one line; maintained by Network Rail',
    },
  ],
  notes:
    'No footprint; extent from the scene rail segments (level 1, deck 6.5 m) crossing the Thames at x~3657-3698 and ' +
    'pier positions from the gaps in the scene river polygons. Arch rise, rib count and colour (grey steel) are ' +
    'approximate. Rib pairs per track, spandrel post spacing, bracing, handrails and signal posts are schematic. ' +
    'The generic rail layer still draws solid brick sides under each elevated track ribbon.',
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
    // Arch spans: 10 parallel single-track steel arch bridges. Each has two
    // plate-girder arch ribs with open spandrels (vertical posts up to the deck),
    // cross-bracing between the ribs and a fascia girder under the deck edge.
    const bounds = [0, ...piers, L];
    const PL = 5; // pier length along the bridge
    const trackT = (r) => -20.5 + (r * 41) / 9;
    const seg = (mat, p, q, w, h) => {
      const dx = q[0] - p[0],
        dy = q[1] - p[1],
        dz = q[2] - p[2];
      const len = Math.hypot(dx, dy, dz);
      const geo = new THREE.BoxGeometry(len, w, h);
      m4.makeRotationZ(ang).multiply(
        new THREE.Matrix4().makeRotationY(-Math.atan2(dz, Math.hypot(dx, dy))),
      );
      m4.setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2);
      batch.addGeometry(mat, geo, m4);
      geo.dispose();
    };
    for (let k = 0; k < bounds.length - 1; k++) {
      const sa = bounds[k] + (k === 0 ? 1 : PL / 2),
        sb = bounds[k + 1] - (k === bounds.length - 2 ? 1 : PL / 2);
      const mid = (sa + sb) / 2,
        half = (sb - sa) / 2;
      const spring = 0.3,
        crown = DECK - 1.6;
      const arch = (s) => spring + (crown - spring) * (1 - ((s - mid) / half) ** 2);
      const M = 18;
      const ribTs = [];
      for (let r = 0; r < 10; r++) ribTs.push(trackT(r) - 1.25, trackT(r) + 1.25);
      for (const t of ribTs) {
        const outerRib = Math.abs(t) > W / 2 - 3;
        const mat = outerRib ? steel : steelDark;
        for (let j = 0; j < M; j++) {
          const a = sa + ((sb - sa) * j) / M,
            b = sa + ((sb - sa) * (j + 1)) / M;
          // rib depth grows towards the springings
          const da = 0.9 + 0.7 * ((a - mid) / half) ** 2;
          const db = 0.9 + 0.7 * ((b - mid) / half) ** 2;
          seg(
            mat,
            P(a, t, arch(a) - da / 2 + 0.45),
            P(b, t, arch(b) - db / 2 + 0.45),
            outerRib ? 0.5 : 0.4,
            (da + db) / 2,
          );
        }
        // spandrel posts
        for (let j = 1; j < 8; j++) {
          const s = sa + ((sb - sa) * j) / 8;
          const z = arch(s) + 0.45;
          if (DECK - 1.1 - z < 0.3) continue;
          const [x, y] = P(s, t, 0);
          kit.box(batch, mat, x, y, z, 0.35, outerRib ? 0.45 : 0.3, DECK - 1.1 - z, ang);
        }
      }
      // cross-bracing between the two ribs of each track bridge, and the bracing
      // struts at the crown
      for (let r = 0; r < 10; r++) {
        const t = trackT(r);
        for (let j = 1; j < M; j += 2) {
          const s = sa + ((sb - sa) * j) / M;
          const [x, y] = P(s, t, 0);
          kit.box(batch, steelDark, x, y, arch(s) - 0.2, 0.25, 2.5, 0.35, ang);
        }
      }
      // outer fascia girders (deck edge), with stiffener lines
      for (const side of [-1, 1]) {
        const [x, y] = P(mid, side * (W / 2 - 0.3), 0);
        kit.box(batch, steel, x, y, DECK - 1.15, sb - sa, 0.4, 1.15, ang);
        for (let s = sa + 1.5; s < sb; s += 3) {
          const [qx, qy] = P(s, side * (W / 2 - 0.05), 0);
          kit.box(batch, steelDark, qx, qy, DECK - 1.1, 0.12, 0.1, 1.05, ang);
        }
      }
    }

    // Parapet handrails and posts, walkway edge, signal posts and cable troughs.
    for (const side of [-1, 1]) {
      const t = side * (W / 2 - 0.25);
      for (const z of [DECK + 0.55, DECK + 1.1]) {
        const [x, y] = P(L / 2, t, 0);
        kit.box(batch, steel, x, y, z, L + 8, 0.08, 0.08, ang);
      }
      for (let s = -3; s < L + 4; s += 2) {
        const [x, y] = P(s, t, 0);
        kit.box(batch, steel, x, y, DECK + 0.1, 0.1, 0.1, 1.1, ang);
      }
      const [cx, cy] = P(L / 2, side * (W / 2 - 1.2), 0);
      kit.box(batch, conc, cx, cy, DECK, L + 8, 0.6, 0.35, ang);
    }
    for (const s of [L * 0.25, L * 0.75]) {
      for (const r of [1, 4, 7]) {
        const [x, y] = P(s, (trackT(r) + trackT(r + 1)) / 2, 0);
        kit.box(batch, kit.mat('#2b2e30'), x, y, DECK, 0.25, 0.25, 4.2, ang);
        kit.box(batch, kit.mat('#111213'), x, y, DECK + 3.4, 0.4, 0.3, 1.0, ang);
        put(
          kit.mat('#e0412f', { emissive: new THREE.Color('#8a1a10') }),
          new THREE.SphereGeometry(0.1, 6, 4),
          ...P(s - 0.2, (trackT(r) + trackT(r + 1)) / 2, 0).slice(0, 2),
          DECK + 4.1,
          0,
        );
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
