// Albert Bridge (Rowland Mason Ordish, 1873; Ordish-Lefeuvre rigid-stay system,
// suspension chains added by Bazalgette 1884-87, central piers added by the GLC in
// 1973). Four ornate cast-iron towers (a central column ringed by octagonal
// columns) on cast-iron cylinder piers carry fans of straight inclined stays plus a
// catenary chain with hangers; the bridge is painted pastel pink, blue and green
// (scheme of 1992) and keeps its octagonal tollbooths at the ends.
export default {
  id: 'albert_bridge',
  name: 'Albert Bridge',
  claims: [],
  references: [
    {
      title: 'Albert Bridge, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Albert_Bridge,_London',
      used_for: 'length 710 ft, width 41 ft, height 66 ft, 1973 central piers, four spans',
    },
    {
      title: 'Ordish-Lefeuvre system - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Ordish%E2%80%93Lefeuvre_system',
      used_for: 'rigid inclined stays from the towers',
    },
    {
      title: 'Albert Bridge - Institution of Civil Engineers',
      url: 'https://www.ice.org.uk/what-is-civil-engineering/infrastructure-projects/albert-bridge',
      used_for:
        'towers of a central column surrounded by eight octagonal ones, cast-iron cylinder foundations, 1992 colour scheme',
    },
    {
      title: 'The Glorious Albert Bridge - Battersea Society',
      url: 'https://www.batterseasociety.org.uk/heritage-blog/the-glorious-albert-bridge',
      used_for: 'octagonal tollbooths, pink blue and green paintwork',
    },
  ],
  notes:
    'No footprint; centreline taken from the scene "Albert Bridge" road segment and the Thames polygon (banks at ' +
    'about (2310,-2587) and (2373,-2797)). The scene is flat (water at ground level), so the deck is drawn with a ' +
    'gentle 4 m camber that returns to road level at the banks. Tower spacing from the 384 ft original main span; ' +
    'stay count, tower ornament and the exact distribution of pink/blue/green are approximate.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = [2309.5, -2587],
      B = [2373, -2797];
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const d = [(B[0] - A[0]) / L, (B[1] - A[1]) / L],
      n = [-d[1], d[0]];
    const ang = Math.atan2(d[1], d[0]);
    const P = (s, t, z) => [A[0] + d[0] * s + n[0] * t, A[1] + d[1] * s + n[1] * t, z];
    const HM = 4,
      Z0 = 0.3;
    const deckZ = (s) => (s <= 0 || s >= L ? Z0 : Z0 + HM * 4 * (s / L) * (1 - s / L));
    const W = 12.5,
      CW = 8; // overall and carriageway width

    const pink = kit.mat('#e9b7c3', { roughness: 0.6 });
    const blue = kit.mat('#7fa3cc', { roughness: 0.6 });
    const green = kit.mat('#9cc8a6', { roughness: 0.6 });
    const cream = kit.mat('#f3efe4', { roughness: 0.6 });
    const asphalt = kit.mat('asphalt');
    const paving = kit.mat('paving');
    const iron = kit.mat('#5d6d7a', { roughness: 0.6, metalness: 0.3 });
    const m4 = new THREE.Matrix4();
    const up = new THREE.Vector3(0, 1, 0);
    const rod = (mat, p, q, r = 0.12, seg = 4) => {
      const a = new THREE.Vector3(...p),
        b = new THREE.Vector3(...q);
      const len = a.distanceTo(b);
      if (len < 0.01) return;
      const geo = new THREE.CylinderGeometry(r, r, len, seg, 1, true);
      const quat = new THREE.Quaternion().setFromUnitVectors(up, b.clone().sub(a).normalize());
      m4.compose(a.clone().add(b).multiplyScalar(0.5), quat, new THREE.Vector3(1, 1, 1));
      batch.addGeometry(mat, geo, m4);
    };
    const put = (mat, geo, x, y, z, rz = ang) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));

    // Deck: carriageway, footways, painted fascia girders, railings.
    const N = 48,
      s0 = -8,
      s1 = L + 8;
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
        const fz = 1.1; // fascia depth
        const o =
          side > 0
            ? [P(sb, t, zb - fz), P(sa, t, za - fz), P(sa, t, za + 0.15), P(sb, t, zb + 0.15)]
            : [P(sa, t, za - fz), P(sb, t, zb - fz), P(sb, t, zb + 0.15), P(sa, t, za + 0.15)];
        batch.quad(blue, ...o, [0, 0], [1, 0], [1, 1], [0, 1]);
        // railing: top rail and posts
        rod(cream, P(sa, t, za + 1.2), P(sb, t, zb + 1.2), 0.06, 4);
        rod(cream, P(sa, t, za + 0.15), P(sa, t, za + 1.2), 0.05, 4);
      }
      // underside
      batch.quad(
        iron,
        P(sa, W / 2, za - 1.1),
        P(sb, W / 2, zb - 1.1),
        P(sb, -W / 2, zb - 1.1),
        P(sa, -W / 2, za - 1.1),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // Towers: pairs of clustered cast-iron columns at the ends of the main span.
    const towerS = [(L - 117) / 2, (L + 117) / 2];
    const TOP = 20; // above water
    const tops = [];
    for (const s of towerS) {
      const zd = deckZ(s);
      for (const side of [-1, 1]) {
        const t = side * (W / 2 + 0.9);
        const [x, y] = P(s, t, 0);
        // cast-iron cylinder pier
        put(iron, new THREE.CylinderGeometry(1.9, 2.1, zd, 12).rotateX(Math.PI / 2), x, y, zd / 2);
        // central column ringed by eight octagonal shafts
        const h = TOP - zd;
        put(
          pink,
          new THREE.CylinderGeometry(1.0, 1.1, h, 8).rotateX(Math.PI / 2),
          x,
          y,
          zd + h / 2,
        );
        for (let k = 0; k < 8; k++) {
          const a = (k * Math.PI) / 4;
          put(
            pink,
            new THREE.CylinderGeometry(0.3, 0.34, h - 2, 6).rotateX(Math.PI / 2),
            x + Math.cos(a) * 1.2,
            y + Math.sin(a) * 1.2,
            zd + (h - 2) / 2,
          );
        }
        // banding, capitals and pinnacle
        for (const z of [zd + 0.5, zd + 6, zd + 11, TOP - 2])
          put(
            blue,
            new THREE.CylinderGeometry(1.65, 1.65, 0.6, 8).rotateX(Math.PI / 2),
            x,
            y,
            z,
            ang + Math.PI / 8,
          );
        put(
          green,
          new THREE.CylinderGeometry(1.5, 1.7, 1.6, 8).rotateX(Math.PI / 2),
          x,
          y,
          TOP - 0.8,
          ang + Math.PI / 8,
        );
        put(
          green,
          new THREE.ConeGeometry(1.35, 3.6, 8).rotateX(Math.PI / 2),
          x,
          y,
          TOP + 1.6,
          ang + Math.PI / 8,
        );
        put(kit.mat('gold'), new THREE.SphereGeometry(0.3, 8, 6), x, y, TOP + 3.4, 0);
        tops.push({ s, t, z: TOP - 1.8 });
      }
      // decorative portal girder between the tower pair, above the carriageway
      const [x, y] = P(s, 0, 0);
      kit.box(batch, blue, x, y, TOP - 3.8, 1.0, W + 1.8, 0.9, ang);
      kit.box(batch, pink, x, y, TOP - 5.2, 0.6, W + 0.6, 0.5, ang);
      for (let k = -3; k <= 3; k++) {
        const [xx, yy] = P(s, k * 1.6, 0);
        kit.box(batch, cream, xx, yy, TOP - 4.7, 0.3, 0.25, 0.9, ang);
      }
    }

    // Central 1973 concrete piers under mid-span.
    for (const s of [L / 2 - 4, L / 2 + 4]) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, kit.mat('concrete'), x, y, 0, 2.2, W - 2, deckZ(s) - 1.1, ang);
    }

    // Rigid Ordish stays fanning from each tower top, and the Bazalgette chain.
    for (const tp of tops) {
      const dirs = [-1, 1];
      for (const dir of dirs) {
        for (let k = 1; k <= 7; k++) {
          const s = tp.s + dir * k * 7.2;
          if (s < -2 || s > L + 2) continue;
          rod(cream, [...P(tp.s, tp.t, tp.z)], P(s, tp.t, deckZ(s) + 1.2), 0.09, 4);
        }
      }
    }
    // chains: main span catenary and side-span backstays to the banks
    for (const side of [-1, 1]) {
      const t = side * (W / 2 + 0.9);
      const sa = towerS[0],
        sb = towerS[1];
      const pts = [];
      for (let k = 0; k <= 24; k++) {
        const s = sa + ((sb - sa) * k) / 24;
        const u = (s - sa) / (sb - sa);
        const z = TOP - 1.8 - (TOP - 1.8 - (deckZ(s) + 2.0)) * (1 - (2 * u - 1) ** 2);
        pts.push([s, z]);
      }
      for (let k = 1; k < pts.length; k++)
        rod(green, P(pts[k - 1][0], t, pts[k - 1][1]), P(pts[k][0], t, pts[k][1]), 0.2, 6);
      for (let k = 1; k < pts.length - 1; k++)
        rod(cream, P(pts[k][0], t, pts[k][1]), P(pts[k][0], t, deckZ(pts[k][0]) + 1.2), 0.05, 3);
      for (const [st, se] of [
        [sa, -4],
        [sb, L + 4],
      ])
        rod(green, P(st, t, TOP - 1.8), P(se, t, Z0 + 1.2), 0.2, 6);
    }

    // Octagonal tollbooths at both ends.
    for (const [s, side] of [
      [-5, -1],
      [-5, 1],
      [L + 5, -1],
      [L + 5, 1],
    ]) {
      const [x, y] = P(s, side * (W / 2 + 1.6), 0);
      put(
        kit.mat('#dfe8d8'),
        new THREE.CylinderGeometry(1.3, 1.3, 2.8, 8).rotateX(Math.PI / 2),
        x,
        y,
        Z0 + 1.4,
        ang + Math.PI / 8,
      );
      put(
        kit.mat('dark_glass'),
        new THREE.CylinderGeometry(1.32, 1.32, 1.0, 8).rotateX(Math.PI / 2),
        x,
        y,
        Z0 + 1.9,
        ang + Math.PI / 8,
      );
      put(
        green,
        new THREE.ConeGeometry(1.6, 1.6, 8).rotateX(Math.PI / 2),
        x,
        y,
        Z0 + 3.6,
        ang + Math.PI / 8,
      );
      put(kit.mat('gold'), new THREE.SphereGeometry(0.18, 6, 4), x, y, Z0 + 4.5, 0);
    }

    g.add(batch.toGroup('albert_bridge'));
    return g;
  },
};
