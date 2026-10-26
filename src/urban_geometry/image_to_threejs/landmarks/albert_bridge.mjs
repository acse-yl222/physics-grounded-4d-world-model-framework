// Albert Bridge (Rowland Mason Ordish, 1873; Ordish-Lefeuvre rigid-stay system,
// suspension chains added by Bazalgette 1884-87, central piers added by the GLC in
// 1973). Four ornate cast-iron towers (a central column ringed by octagonal
// columns) on cast-iron cylinder piers carry fans of straight inclined stays plus a
// catenary chain with hangers; the bridge is painted pastel pink, blue and green
// (scheme of 1992) and keeps its octagonal tollbooths at the ends.
export default {
  id: 'albert_bridge',
  name: 'Albert Bridge',
  claims: [
    // the four tower-base footprints in the river (otherwise extruded as 20 m blocks)
    'd85ba4b8-44a7-4d37-bd3e-8c49705ca880',
    '7f266239-05fb-47c4-8063-8c80e884cecb',
    '200b92cb-9e77-415b-a259-73864e007937',
    '25ff9683-288c-4324-92ab-553213b0e403',
  ],
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
      title:
        'Albert Bridge including tollbooths, lamp standards and stairs - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101358138',
      used_for:
        '16 octagonal cast-iron lamp standards with dog-tooth mouldings and crown finials, Gothic embellishment',
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
    'gentle 4 m camber that returns to road level at the banks. Tower positions from the four Overture tower-base ' +
    'footprints (claimed so they are not extruded twice; main span ~122 m there vs 384 ft quoted). ' +
    'Parapet lattice, deck cross-girders, portal lattice, tower brackets/pinnacles and the 16 lamp standards are ' +
    'drawn from the listing text and general photo knowledge; the troops-break-step notice is from general knowledge. ' +
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
        rod(cream, P(sa, t, za + 1.2), P(sb, t, zb + 1.2), 0.07, 4);
        rod(cream, P(sa, t, za + 0.25), P(sb, t, zb + 0.25), 0.05, 4);
        rod(pink, P(sa, t, za + 0.75), P(sb, t, zb + 0.75), 0.035, 3);
        // fascia mouldings
        rod(cream, P(sa, t + side * 0.05, za + 0.1), P(sb, t + side * 0.05, zb + 0.1), 0.08, 4);
        rod(cream, P(sa, t + side * 0.05, za - fz), P(sb, t + side * 0.05, zb - fz), 0.08, 4);
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
    // tower positions from the four Overture tower-base footprints (claimed)
    const towerS = [47.1, 169.2];
    const TW = 8.0; // tower / chain plane offset from the centreline
    const edge = (t) => Math.sign(t) * (W / 2 + 0.1);
    const TOP = 20; // above water
    const tops = [];
    for (const s of towerS) {
      const zd = deckZ(s);
      for (const side of [-1, 1]) {
        const t = side * TW;
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
          rod(cream, [...P(tp.s, tp.t, tp.z)], P(s, edge(tp.t), deckZ(s) + 1.2), 0.09, 4);
        }
      }
    }
    // chains: main span catenary and side-span backstays to the banks
    for (const side of [-1, 1]) {
      const t = side * TW;
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
        rod(
          cream,
          P(pts[k][0], t, pts[k][1]),
          P(pts[k][0], edge(t), deckZ(pts[k][0]) + 1.2),
          0.05,
          3,
        );
      for (const [st, se] of [
        [sa, -4],
        [sb, L + 4],
      ])
        rod(green, P(st, t, TOP - 1.8), P(se, edge(t), Z0 + 1.2), 0.2, 6);
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

    // ---------------------------------------------------------------- detail pass
    // Cast-iron parapet: close balusters with a diagonal lattice between the rails.
    for (const side of [-1, 1]) {
      const t = (side * W) / 2;
      for (let s = s0 + 0.2; s < s1; s += 0.42) {
        const z = deckZ(s);
        rod(cream, P(s, t, z + 0.25), P(s, t, z + 1.2), 0.025, 3);
      }
      for (let s = s0; s < s1 - 1.4; s += 1.4) {
        const za = deckZ(s),
          zb = deckZ(s + 1.4);
        rod(pink, P(s, t, za + 0.3), P(s + 1.4, t, zb + 1.15), 0.03, 3);
        rod(pink, P(s, t, za + 1.15), P(s + 1.4, t, zb + 0.3), 0.03, 3);
      }
      // parapet newel posts every 9 m
      for (let s = s0 + 2; s < s1; s += 9) {
        const [x, y] = P(s, t, 0);
        kit.box(batch, blue, x, y, deckZ(s) + 0.1, 0.32, 0.32, 1.3, ang);
        put(cream, new THREE.SphereGeometry(0.16, 8, 5), x, y, deckZ(s) + 1.5, 0);
      }
    }
    // Deck structure seen from the river: cross-girders and longitudinal stringers.
    for (let s = s0 + 1; s < s1; s += 3.2) {
      const [x, y] = P(s, 0, 0);
      const z = deckZ(s);
      kit.box(batch, iron, x, y, z - 1.1, 0.35, W - 0.2, 0.9, ang);
    }
    for (const t of [-4.5, -1.5, 1.5, 4.5])
      for (let k = 0; k < N; k++) {
        const sa = s0 + ((s1 - s0) * k) / N,
          sb = s0 + ((s1 - s0) * (k + 1)) / N;
        rod(iron, P(sa, t, deckZ(sa) - 0.95), P(sb, t, deckZ(sb) - 0.95), 0.18, 4);
      }

    // Tower ornament: deck-level plinths, Gothic bracket capitals, crown pinnacles,
    // cable saddles, and a lattice portal girder with a cusped arch beneath.
    const lattice = kit.paintedMaterial('albert_bridge:portal', 512, 64, (c, w, h) => {
      c.fillStyle = '#7fa3cc';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#e9b7c3';
      for (let k = 0; k < 16; k++) {
        const x = k * 32 + 16;
        c.beginPath();
        c.arc(x, 32, 11, 0, Math.PI * 2);
        c.fill();
      }
      c.fillStyle = '#2d3c4a';
      for (let k = 0; k < 16; k++) {
        const x = k * 32 + 16;
        for (let j = 0; j < 4; j++) {
          const a = (j * Math.PI) / 2 + Math.PI / 4;
          c.beginPath();
          c.arc(x + Math.cos(a) * 4.5, 32 + Math.sin(a) * 4.5, 3.6, 0, Math.PI * 2);
          c.fill();
        }
      }
      c.fillStyle = '#f3efe4';
      c.fillRect(0, 0, w, 6);
      c.fillRect(0, h - 6, w, 6);
    });
    for (const s of towerS) {
      const zd = deckZ(s);
      for (const side of [-1, 1]) {
        const [x, y] = P(s, side * TW, 0);
        put(
          blue,
          new THREE.CylinderGeometry(1.9, 2.1, 1.6, 8).rotateX(Math.PI / 2),
          x,
          y,
          zd + 0.8,
          ang + Math.PI / 8,
        );
        put(
          cream,
          new THREE.CylinderGeometry(1.95, 1.95, 0.2, 8).rotateX(Math.PI / 2),
          x,
          y,
          zd + 1.7,
          ang + Math.PI / 8,
        );
        // iron cylinder pier bands and cap
        for (const z of [0.6, zd * 0.5, zd - 0.3])
          put(
            blue,
            new THREE.CylinderGeometry(2.2, 2.2, 0.25, 16).rotateX(Math.PI / 2),
            x,
            y,
            z,
            0,
          );
        // bracket capitals on the eight outer shafts
        for (let k = 0; k < 8; k++) {
          const a = (k * Math.PI) / 4;
          const bx = x + Math.cos(a) * 1.2,
            by = y + Math.sin(a) * 1.2;
          put(
            cream,
            new THREE.CylinderGeometry(0.48, 0.3, 0.8, 6).rotateX(Math.PI / 2),
            bx,
            by,
            TOP - 2.6,
            0,
          );
          put(
            pink,
            new THREE.CylinderGeometry(0.36, 0.36, 0.25, 6).rotateX(Math.PI / 2),
            bx,
            by,
            zd + 2.0,
            0,
          );
          // crown pinnacles round the spire
          const px = x + Math.cos(a + Math.PI / 8) * 1.45,
            py = y + Math.sin(a + Math.PI / 8) * 1.45;
          put(
            green,
            new THREE.ConeGeometry(0.16, 1.1, 4).rotateX(Math.PI / 2),
            px,
            py,
            TOP + 0.55,
            0,
          );
          put(kit.mat('gold'), new THREE.SphereGeometry(0.08, 5, 3), px, py, TOP + 1.15, 0);
        }
        // pointed Gothic panels on the spire faces
        for (let k = 0; k < 8; k++) {
          const a = ang + Math.PI / 8 + (k * Math.PI) / 4 + Math.PI / 8;
          const r0 = 1.5 * Math.cos(Math.PI / 8) + 0.02;
          kit.box(
            batch,
            cream,
            x + Math.cos(a) * r0,
            y + Math.sin(a) * r0,
            TOP - 1.4,
            0.35,
            0.05,
            1.0,
            a + Math.PI / 2,
          );
        }
        // cable saddle
        kit.box(batch, cream, x, y, TOP - 2.2, 1.1, 1.1, 0.7, ang);
      }
      const [x, y] = P(s, 0, 0);
      kit.box(batch, lattice, x, y, TOP - 4.6, 0.8, W + 1.4, 0.9, ang);
      // cusped arch spandrels under the portal
      for (let k = 0; k <= 12; k++) {
        const t = -W / 2 + (k * W) / 12;
        const z = TOP - 5.2 - 1.6 * (1 - (t / (W / 2)) ** 2);
        const [xx, yy] = P(s, t, 0);
        kit.box(batch, pink, xx, yy, z, 0.35, W / 12 + 0.05, 0.25, ang);
        if (k % 2 === 0) kit.box(batch, cream, xx, yy, z + 0.25, 0.25, 0.18, TOP - 5.2 - z, ang);
      }
      kit.box(batch, cream, x, y, TOP - 3.7, 1.2, W + 2, 0.15, ang);
      put(kit.mat('gold'), new THREE.SphereGeometry(0.35, 10, 6), x, y, TOP - 3.2, 0);
    }

    // Sixteen octagonal cast-iron lamp standards with crown finials along the parapets.
    const lampGlass = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.45,
      roughness: 0.25,
    });
    for (const side of [-1, 1])
      for (let k = 0; k < 8; k++) {
        let s = (L * (k + 0.5)) / 8;
        for (const ts of towerS) if (Math.abs(s - ts) < 4) s += s < ts ? -4 : 4;
        const [x, y] = P(s, side * (W / 2 - 0.25), 0);
        const z = deckZ(s) + 0.15;
        put(
          green,
          new THREE.CylinderGeometry(0.26, 0.32, 1.0, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 0.5,
          0,
        );
        put(
          green,
          new THREE.CylinderGeometry(0.09, 0.13, 3.0, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 2.5,
          0,
        );
        put(
          cream,
          new THREE.CylinderGeometry(0.2, 0.15, 0.25, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 4.05,
          0,
        );
        put(
          lampGlass,
          new THREE.CylinderGeometry(0.3, 0.2, 0.7, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 4.5,
          0,
        );
        put(green, new THREE.ConeGeometry(0.36, 0.35, 8).rotateX(Math.PI / 2), x, y, z + 5.02, 0);
        for (let j = 0; j < 4; j++) {
          const a = (j * Math.PI) / 2;
          put(
            kit.mat('gold'),
            new THREE.ConeGeometry(0.05, 0.25, 4).rotateX(Math.PI / 2),
            x + Math.cos(a) * 0.14,
            y + Math.sin(a) * 0.14,
            z + 5.3,
            0,
          );
        }
        put(kit.mat('gold'), new THREE.SphereGeometry(0.07, 6, 4), x, y, z + 5.45, 0);
      }

    // Tollbooth detail and the "break step" notices at both ends.
    const notice = kit.paintedMaterial('albert_bridge:notice', 256, 128, (c, w, h) => {
      c.fillStyle = '#f2efe6';
      c.fillRect(0, 0, w, h);
      c.strokeStyle = '#1e2a40';
      c.lineWidth = 6;
      c.strokeRect(4, 4, w - 8, h - 8);
      c.fillStyle = '#1e2a40';
      c.font = 'bold 17px serif';
      c.textAlign = 'center';
      const lines = [
        'OFFICERS IN COMMAND',
        'OF TROOPS ARE REQUESTED',
        'TO BREAK STEP WHEN',
        'PASSING OVER THIS BRIDGE',
      ];
      lines.forEach((t, i) => c.fillText(t, w / 2, 30 + i * 25));
    });
    for (const [s, side] of [
      [-5, -1],
      [-5, 1],
      [L + 5, -1],
      [L + 5, 1],
    ]) {
      const [x, y] = P(s, side * (W / 2 + 1.6), 0);
      for (let k = 0; k < 8; k++) {
        const a = ang + (k * Math.PI) / 4;
        kit.box(
          batch,
          cream,
          x + Math.cos(a) * 1.25,
          y + Math.sin(a) * 1.25,
          Z0,
          0.14,
          0.14,
          2.9,
          a,
        );
      }
      put(
        cream,
        new THREE.CylinderGeometry(1.45, 1.45, 0.25, 8).rotateX(Math.PI / 2),
        x,
        y,
        Z0 + 2.95,
        ang + Math.PI / 8,
      );
      const [dx, dy] = P(s + (s < 0 ? 1.28 : -1.28), side * (W / 2 + 1.6), 0);
      kit.box(batch, kit.mat('#2e4f6e'), dx, dy, Z0, 0.08, 0.8, 2.0, ang);
      const [nx2, ny2] = P(s + (s < 0 ? 2.5 : -2.5), side * (W / 2 + 3.2), 0);
      for (const o of [-0.45, 0.45]) {
        const [px, py] = P(s + (s < 0 ? 2.5 : -2.5), side * (W / 2 + 3.2) + o, 0);
        put(
          green,
          new THREE.CylinderGeometry(0.04, 0.04, 2.2, 6).rotateX(Math.PI / 2),
          px,
          py,
          Z0 + 1.1,
          0,
        );
      }
      kit.box(batch, notice, nx2, ny2, Z0 + 1.4, 0.04, 1.0, 0.55, ang);
    }

    g.add(batch.toGroup('albert_bridge'));
    return g;
  },
};
