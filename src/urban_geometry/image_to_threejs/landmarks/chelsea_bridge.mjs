// Chelsea Bridge (Rendel, Palmer & Tritton with G. Topham Forrest and E. P.
// Wheeler, 1934-37): the first self-anchored suspension bridge in Britain. Two
// slender steel portal towers on granite-faced piers carry the main cables, which
// sweep down to anchorages in the ends of the stiffening girders; vertical hangers
// support the deck, and ornamental lamp finials crown the towers. Painted white
// with red cables and blue detailing.
export default {
  id: 'chelsea_bridge',
  name: 'Chelsea Bridge',
  claims: [],
  references: [
    {
      title: 'Chelsea Bridge - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Chelsea_Bridge',
      used_for: '1937 self-anchored suspension bridge, first in Britain, steel, dimensions',
    },
    {
      title: "Grace's Guide - Chelsea Suspension Bridge",
      url: 'https://www.gracesguide.co.uk/Chelsea_Suspension_Bridge',
      used_for: 'history of the earlier and present suspension bridges',
    },
    {
      title: "Battersea's river crossings - Battersea Society",
      url: 'https://batterseasociety.org.uk/heritage-blog/batterseas-river-crossings',
      used_for: 'general appearance',
    },
  ],
  notes:
    'No footprint; centreline from the scene "Chelsea Bridge" road, tower positions from the two gaps in the scene ' +
    'Thames polygons (main span ~108 m). Flat scene: 3.5 m deck camber. Tower height (~22 m above water), lamp ' +
    'finials and the red/white/blue paint split are approximate (one lower-quality source for the colours).',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = [3494.5, -2333],
      B = [3522.5, -2541];
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const d = [(B[0] - A[0]) / L, (B[1] - A[1]) / L],
      n = [-d[1], d[0]];
    const ang = Math.atan2(d[1], d[0]);
    const P = (s, t, z) => [A[0] + d[0] * s + n[0] * t, A[1] + d[1] * s + n[1] * t, z];
    const proj = ([x, y]) => (x - A[0]) * d[0] + (y - A[1]) * d[1];
    const towerS = [
      [3501.5, -2385.5],
      [3516.5, -2493],
    ].map(proj);
    const HM = 3.5,
      Z0 = 0.3;
    const deckZ = (s) => (s <= 0 || s >= L ? Z0 : Z0 + HM * 4 * (s / L) * (1 - s / L));
    const W = 19.5,
      CW = 13;
    const TOP = 22;

    const white = kit.mat('#eeeeea', { roughness: 0.5, metalness: 0.2 });
    const red = kit.mat('#b3332d', { roughness: 0.5, metalness: 0.2 });
    const blue = kit.mat('#2e4f7c', { roughness: 0.5 });
    const granite = kit.mat('#a9a69f', { roughness: 0.9 });
    const gold = kit.mat('gold');
    const asphalt = kit.mat('asphalt');
    const paving = kit.mat('paving');
    const m4 = new THREE.Matrix4();
    const up = new THREE.Vector3(0, 1, 0);
    const rod = (mat, p, q, r = 0.08, seg = 4) => {
      const a = new THREE.Vector3(...p),
        b = new THREE.Vector3(...q);
      const len = a.distanceTo(b);
      if (len < 0.01) return;
      const quat = new THREE.Quaternion().setFromUnitVectors(up, b.clone().sub(a).normalize());
      m4.compose(a.clone().add(b).multiplyScalar(0.5), quat, new THREE.Vector3(1, 1, 1));
      batch.addGeometry(mat, new THREE.CylinderGeometry(r, r, len, seg, 1, true), m4);
    };
    const put = (mat, geo, x, y, z, rz = ang) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));

    // Deck with white stiffening girders and parapet railings.
    const N = 50,
      s0 = -5,
      s1 = L + 5;
    for (let k = 0; k < N; k++) {
      const sa = s0 + ((s1 - s0) * k) / N,
        sb = s0 + ((s1 - s0) * (k + 1)) / N;
      const za = deckZ(sa),
        zb = deckZ(sb);
      const strip = (mat, t0, t1, dz = 0) =>
        batch.quad(
          mat,
          P(sa, t0, za + dz),
          P(sb, t0, zb + dz),
          P(sb, t1, zb + dz),
          P(sa, t1, za + dz),
          [sa / 8, t0 / 8],
          [sb / 8, t0 / 8],
          [sb / 8, t1 / 8],
          [sa / 8, t1 / 8],
        );
      strip(asphalt, -CW / 2, CW / 2);
      strip(paving, CW / 2, W / 2, 0.15);
      strip(paving, -W / 2, -CW / 2, 0.15);
      for (const side of [-1, 1]) {
        const t = (side * W) / 2;
        const q =
          side > 0
            ? [P(sb, t, zb - 1.8), P(sa, t, za - 1.8), P(sa, t, za + 0.15), P(sb, t, zb + 0.15)]
            : [P(sa, t, za - 1.8), P(sb, t, zb - 1.8), P(sb, t, zb + 0.15), P(sa, t, za + 0.15)];
        batch.quad(white, ...q, [0, 0], [1, 0], [1, 1], [0, 1]);
        const tr = side * (W / 2 - 0.2);
        rod(white, P(sa, tr, za + 1.25), P(sb, tr, zb + 1.25), 0.07);
        for (let j = 0; j < 2; j++) {
          const s = sa + ((sb - sa) * j) / 2;
          rod(blue, P(s, tr, deckZ(s) + 0.15), P(s, tr, deckZ(s) + 1.25), 0.04, 3);
        }
      }
      batch.quad(
        blue,
        P(sa, W / 2, za - 1.8),
        P(sb, W / 2, zb - 1.8),
        P(sb, -W / 2, zb - 1.8),
        P(sa, -W / 2, za - 1.8),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // Towers: twin steel legs with a portal beam, on granite piers; lamp finials.
    const CT = W / 2 + 0.4; // cable plane offset
    for (const s of towerS) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, granite, x, y, 0, 6, W + 4, deckZ(s) - 1.8, ang);
      for (const side of [-1, 1]) {
        const [cx, cy] = P(s, side * (W / 2 + 2), 0);
        put(
          granite,
          new THREE.CylinderGeometry(4.2, 4.2, deckZ(s) - 1.8, 4).rotateX(Math.PI / 2),
          cx,
          cy,
          (deckZ(s) - 1.8) / 2,
          ang + Math.PI / 4,
        );
        const [lx, ly] = P(s, side * CT, 0);
        const z0 = deckZ(s) - 1.8;
        kit.box(batch, white, lx, ly, z0, 2.2, 1.5, TOP - z0, ang);
        kit.box(batch, red, lx, ly, TOP - 1.2, 2.5, 1.8, 0.4, ang);
        // lamp finial
        put(
          blue,
          new THREE.CylinderGeometry(0.5, 0.7, 1.4, 8).rotateX(Math.PI / 2),
          lx,
          ly,
          TOP + 0.7,
        );
        put(gold, new THREE.SphereGeometry(0.6, 10, 8), lx, ly, TOP + 1.9, 0);
        put(gold, new THREE.ConeGeometry(0.25, 1.1, 6).rotateX(Math.PI / 2), lx, ly, TOP + 3, 0);
      }
      kit.box(batch, white, x, y, TOP - 4.2, 1.6, 2 * CT, 1.4, ang);
      kit.box(batch, blue, x, y, TOP - 4.6, 1.7, 2 * CT - 2, 0.4, ang);
    }

    // Main cables (self-anchored at the deck ends) with vertical hangers.
    const [ta, tb] = towerS;
    const cableZ = (s) => {
      if (s <= ta)
        return deckZ(0) + 1 + (TOP - 0.6 - (deckZ(0) + 1)) * Math.pow(Math.max(0, s) / ta, 1.25);
      if (s >= tb)
        return (
          deckZ(L) +
          1 +
          (TOP - 0.6 - (deckZ(L) + 1)) * Math.pow(Math.max(0, L - s) / (L - tb), 1.25)
        );
      const u = (s - ta) / (tb - ta);
      const low = deckZ((ta + tb) / 2) + 1.4;
      return low + (TOP - 0.6 - low) * (2 * u - 1) ** 2;
    };
    for (const side of [-1, 1]) {
      const t = side * CT;
      const M = 60;
      let prev = null;
      for (let k = 0; k <= M; k++) {
        const s = (L * k) / M;
        const p = P(s, t, cableZ(s));
        if (prev) rod(red, prev, p, 0.28, 6);
        prev = p;
      }
      for (let s = 4; s < L - 3; s += 4.5) {
        if (Math.abs(s - ta) < 2 || Math.abs(s - tb) < 2) continue;
        const z = cableZ(s);
        if (z - deckZ(s) < 1.6) continue;
        rod(white, P(s, t, z), P(s, t, deckZ(s) + 0.2), 0.05, 3);
      }
    }

    g.add(batch.toGroup('chelsea_bridge'));
    return g;
  },
};
