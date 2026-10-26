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
      title: 'Chelsea Bridge - Historic England list entry 1393009',
      url: 'https://HistoricEngland.org.uk/listing/the-list/list-entry/1393009',
      used_for:
        'mostly white with red trim and greyish blue balustrades, five sets of lampposts either side, heraldic designs on the towers',
    },
    {
      title: 'Secrets Of Chelsea Bridge - Londonist',
      url: 'https://londonist.com/london/features/secrets-of-chelsea-bridge',
      used_for: 'gilt galleons with shields on the lamp posts, red and white repaint',
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
    'finials and the red/white/blue paint split are approximate. Galleons, shields, lamp-standard design and their ' +
    'exact positions are schematic; the listing only says five sets of lampposts either side.',
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
        // red trim along the top and bottom of the stiffening girder
        rod(red, P(sa, t + side * 0.04, za + 0.05), P(sb, t + side * 0.04, zb + 0.05), 0.09, 4);
        rod(red, P(sa, t + side * 0.04, za - 1.75), P(sb, t + side * 0.04, zb - 1.75), 0.09, 4);
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

    // ---------------------------------------------------------------- detail pass
    const bal = kit.mat('#8297a6', { roughness: 0.5, metalness: 0.2 }); // greyish-blue balustrade
    // Balustrade: close vertical bars, top and bottom rails, white newels every 6 m.
    for (const side of [-1, 1]) {
      const t = side * (W / 2 - 0.15);
      for (let k = 0; k < N; k++) {
        const sa = s0 + ((s1 - s0) * k) / N,
          sb = s0 + ((s1 - s0) * (k + 1)) / N;
        rod(bal, P(sa, t, deckZ(sa) + 1.2), P(sb, t, deckZ(sb) + 1.2), 0.07, 4);
        rod(bal, P(sa, t, deckZ(sa) + 0.25), P(sb, t, deckZ(sb) + 0.25), 0.05, 4);
      }
      for (let s = s0 + 0.15; s < s1; s += 0.3)
        rod(bal, P(s, t, deckZ(s) + 0.2), P(s, t, deckZ(s) + 1.2), 0.022, 3);
      for (let s = s0 + 3; s < s1; s += 6) {
        const [x, y] = P(s, t, 0);
        kit.box(batch, white, x, y, deckZ(s) + 0.1, 0.35, 0.35, 1.3, ang);
      }
    }
    // Cross-girders under the deck.
    for (let s = s0 + 1; s < s1; s += 3) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, blue, x, y, deckZ(s) - 1.75, 0.35, W - 0.4, 1.4, ang);
    }
    // Tower legs: recessed panels, red edge trim, heraldic shields, cable saddles
    // and lantern tops.
    const shield = kit.paintedMaterial('chelsea_bridge:arms', 64, 80, (c, w, h) => {
      c.fillStyle = '#eeeeea';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#d6b04c';
      c.beginPath();
      c.moveTo(6, 6);
      c.lineTo(58, 6);
      c.lineTo(58, 44);
      c.quadraticCurveTo(58, 70, 32, 76);
      c.quadraticCurveTo(6, 70, 6, 44);
      c.closePath();
      c.fill();
      c.fillStyle = '#2e4f7c';
      c.beginPath();
      c.moveTo(11, 11);
      c.lineTo(53, 11);
      c.lineTo(53, 43);
      c.quadraticCurveTo(53, 64, 32, 70);
      c.quadraticCurveTo(11, 64, 11, 43);
      c.closePath();
      c.fill();
      c.fillStyle = '#ffffff';
      for (let k = 0; k < 3; k++) c.fillRect(16, 20 + k * 14, 32, 6); // wavy bars (LCC)
      c.fillStyle = '#b3332d';
      c.fillRect(11, 11, 42, 8);
    });
    const lampGlass = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.45,
      roughness: 0.25,
    });
    for (const s of towerS) {
      for (const side of [-1, 1]) {
        const [lx, ly] = P(s, side * CT, 0);
        const z0 = deckZ(s) - 1.8;
        for (const face of [-1, 1]) {
          // recessed panel lines and red trim on the up/downstream faces
          const [fx, fy] = P(s + face * 1.12, side * CT, 0);
          kit.box(batch, red, fx, fy, z0 + 2, 0.05, 1.2, 0.12, ang);
          kit.box(batch, red, fx, fy, TOP - 5, 0.05, 1.2, 0.12, ang);
          for (const o of [-0.6, 0.6]) {
            const [ex, ey] = P(s + face * 1.12, side * CT + o, 0);
            kit.box(batch, red, ex, ey, z0 + 2, 0.05, 0.08, TOP - 7 - z0, ang);
          }
          const [hx, hy] = P(s + face * 1.13, side * CT, 0);
          put(shield, new THREE.BoxGeometry(0.04, 1.0, 1.25), hx, hy, deckZ(s) + 4.5);
        }
        // saddle housing
        kit.box(batch, white, lx, ly, TOP - 0.8, 1.8, 1.4, 0.8, ang);
        put(
          red,
          new THREE.CylinderGeometry(0.5, 0.5, 1.5, 12, 1, false, 0, Math.PI).rotateZ(Math.PI / 2),
          lx,
          ly,
          TOP - 0.2,
          ang + Math.PI / 2,
        );
        // tower-top lanterns (four small lamps around the finial)
        for (let k = 0; k < 4; k++) {
          const a = ang + Math.PI / 4 + (k * Math.PI) / 2;
          const px = lx + Math.cos(a) * 1.0,
            py = ly + Math.sin(a) * 1.0;
          put(
            blue,
            new THREE.CylinderGeometry(0.06, 0.08, 1.2, 6).rotateX(Math.PI / 2),
            px,
            py,
            TOP + 0.6,
            0,
          );
          put(lampGlass, new THREE.SphereGeometry(0.22, 8, 6), px, py, TOP + 1.35, 0);
        }
      }
      // portal beam ornament: red band and central shield
      const [x, y] = P(s, 0, 0);
      for (const face of [-1, 1]) {
        const [fx, fy] = P(s + face * 0.82, 0, 0);
        kit.box(batch, red, fx, fy, TOP - 3.25, 0.05, 2 * CT - 2, 0.15, ang);
        put(shield, new THREE.BoxGeometry(0.04, 1.4, 1.6), fx, fy, TOP - 4.25 + 0.6);
      }
      (void x, y);
    }

    // Five lamp standards on either side, and the galleon lamp posts at the entrances.
    for (const side of [-1, 1]) {
      const ts = [];
      const gap = (towerS[1] - towerS[0]) / 4;
      for (let k = 1; k <= 3; k++) ts.push(towerS[0] + k * gap);
      ts.push(towerS[0] / 2, (towerS[1] + L) / 2);
      for (const s of ts) {
        const [x, y] = P(s, side * (W / 2 - 0.15), 0);
        const z = deckZ(s) + 0.15;
        put(
          white,
          new THREE.CylinderGeometry(0.22, 0.3, 0.9, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 0.45,
        );
        put(
          white,
          new THREE.CylinderGeometry(0.09, 0.13, 4.6, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 3.2,
        );
        put(
          red,
          new THREE.CylinderGeometry(0.16, 0.16, 0.2, 8).rotateX(Math.PI / 2),
          x,
          y,
          z + 1.0,
        );
        kit.box(
          batch,
          white,
          ...P(s, side * (W / 2 - 0.9), 0).slice(0, 2),
          z + 5.45,
          0.08,
          1.5,
          0.08,
          ang,
        );
        const [ax, ay] = P(s, side * (W / 2 - 1.6), 0);
        put(
          lampGlass,
          new THREE.CylinderGeometry(0.28, 0.2, 0.5, 8).rotateX(Math.PI / 2),
          ax,
          ay,
          z + 5.2,
        );
        put(blue, new THREE.ConeGeometry(0.34, 0.3, 8).rotateX(Math.PI / 2), ax, ay, z + 5.6);
      }
    }
    for (const [s, side] of [
      [-3, -1],
      [-3, 1],
      [L + 3, -1],
      [L + 3, 1],
    ]) {
      const [x, y] = P(s, side * (W / 2 + 0.6), 0);
      const z = Z0;
      kit.box(batch, granite, x, y, z, 1.6, 1.6, 1.2, ang);
      put(
        white,
        new THREE.CylinderGeometry(0.28, 0.4, 6.5, 8).rotateX(Math.PI / 2),
        x,
        y,
        z + 4.45,
      );
      put(
        shield,
        new THREE.BoxGeometry(0.9, 0.9, 1.1).rotateZ(Math.PI / 4),
        x,
        y,
        z + 2.6,
        ang + Math.PI / 4,
      );
      for (const o of [-0.7, 0.7]) {
        const [ax, ay] = P(s + o, side * (W / 2 + 0.6), 0);
        put(lampGlass, new THREE.SphereGeometry(0.3, 10, 6), ax, ay, z + 7.2, 0);
      }
      kit.box(batch, white, x, y, z + 7.0, 1.6, 0.12, 0.12, ang);
      // gilt galleon: hull, three masts and sails
      const zg = z + 7.8;
      put(gold, new THREE.BoxGeometry(1.4, 0.45, 0.4), x, y, zg);
      put(
        gold,
        new THREE.CylinderGeometry(0.0, 0.25, 0.4, 4).rotateZ(Math.PI / 2),
        ...P(s - 0.85, side * (W / 2 + 0.6), 0).slice(0, 2),
        zg,
        ang,
      );
      for (const [o, hgt] of [
        [-0.45, 1.0],
        [0, 1.3],
        [0.45, 0.9],
      ]) {
        const [mx, my] = P(s + o, side * (W / 2 + 0.6), 0);
        put(
          gold,
          new THREE.CylinderGeometry(0.03, 0.03, hgt, 4).rotateX(Math.PI / 2),
          mx,
          my,
          zg + 0.2 + hgt / 2,
          0,
        );
        put(gold, new THREE.BoxGeometry(0.05, 0.55, hgt * 0.6), mx, my, zg + 0.3 + hgt * 0.45);
      }
    }

    g.add(batch.toGroup('chelsea_bridge'));
    return g;
  },
};
