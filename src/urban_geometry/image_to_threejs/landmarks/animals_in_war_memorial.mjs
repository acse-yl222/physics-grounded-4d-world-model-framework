// Animals in War Memorial, Park Lane at Brook Gate / Upper Brook Street (David
// Backhouse, unveiled November 2004). A curved Portland stone wall, about 55 x 58 ft
// (16.8 x 17.7 m) in extent, symbolising the arena of war and carved in bas-relief with
// the animals that served; two heavily laden bronze mules struggle up steps towards a
// gap in the wall, and beyond the gap a bronze horse and dog gaze into the distance.
export default {
  id: 'animals_in_war_memorial',
  name: 'Animals in War Memorial',
  claims: [],
  references: [
    {
      title: 'Animals in War Memorial - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Animals_in_War_Memorial',
      used_for:
        'David Backhouse, 2004; curved Portland stone wall 55 x 58 ft; bas-relief animals; two laden bronze mules climbing steps to a gap, bronze horse and dog beyond; coordinates 51.5111 N 0.1572 W at Upper Brook Street',
    },
    {
      title: 'Animals in War Memorial - Donald Insall Associates',
      url: 'https://www.donaldinsallassociates.co.uk/projects/animals-in-war-memorial/',
      used_for: 'Brook Gate, Park Lane, on the edge of Hyde Park; carving and contractor details',
    },
    {
      title: 'Animals in War - War Memorials Online',
      url: 'https://www.warmemorialsonline.org.uk/memorial/72030',
      used_for: 'inscriptions ("Animals in War", "They had no choice") and setting',
    },
    {
      title: 'New war memorial for animals - Horse & Hound',
      url: 'https://www.horseandhound.co.uk/news/new-war-memorial-for-animals-59397',
      used_for: 'unveiling by the Princess Royal in November 2004',
    },
  ],
  notes:
    'Placed on the Park Lane central reservation beside the scene footway that runs along it (within ~15 m of ' +
    'the published coordinates). The wall is one curved arc (17.7 m chord, 0.9 m thick, 2.6-4.2 m high) with a ' +
    '2.4 m gap; reliefs and lettering are painted on its faces. Which side the mules and the horse and dog stand ' +
    'on, the number of steps and all animal forms are simplified reconstructions.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const P0 = [2996.9, 516.8],
      P1 = [2990.5, 534.2];
    const l = Math.hypot(P1[0] - P0[0], P1[1] - P0[1]);
    const D = [(P1[0] - P0[0]) / l, (P1[1] - P0[1]) / l];
    const Wn = [-D[1], D[0]]; // west-ish normal (left of the path direction)
    const C = [(P0[0] + P1[0]) / 2 + Wn[0] * 5.5, (P0[1] + P1[1]) / 2 + Wn[1] * 5.5];
    const L = (s, t) => [C[0] + D[0] * s + Wn[0] * t, C[1] + D[1] * s + Wn[1] * t];
    const ang = Math.atan2(D[1], D[0]);

    const stone = kit.mat('portland_stone');
    const relief = kit.paintedMaterial(
      'animals_in_war:relief',
      1024,
      256,
      (c, w, h) => {
        c.fillStyle = '#ddd6c4';
        c.fillRect(0, 0, w, h);
        const rnd = kit.rng(2004);
        // procession of animals in low relief: elephants, horses, camels, dogs, pigeons
        for (let i = 0; i < 26; i++) {
          const x = (i / 26) * w + rnd() * 10,
            y = h * (0.45 + rnd() * 0.3);
          const s = 14 + rnd() * 22;
          c.fillStyle = 'rgba(150,140,118,0.55)';
          c.beginPath();
          c.ellipse(x, y, s, s * 0.55, 0, 0, Math.PI * 2);
          c.fill();
          c.fillRect(x - s * 0.8, y + s * 0.3, s * 0.18, s * 0.8);
          c.fillRect(x + s * 0.6, y + s * 0.3, s * 0.18, s * 0.8);
          c.beginPath();
          c.ellipse(x + s * 1.05, y - s * 0.45, s * 0.35, s * 0.25, -0.5, 0, Math.PI * 2);
          c.fill();
          c.strokeStyle = 'rgba(120,110,92,0.6)';
          c.lineWidth = 2;
          c.stroke();
        }
        c.fillStyle = '#6f675a';
        c.font = 'bold 30px serif';
        c.textAlign = 'center';
        c.fillText('ANIMALS IN WAR', w / 2, 40);
        c.font = '22px serif';
        c.fillText('THEY HAD NO CHOICE', w * 0.78, h - 18);
      },
      { roughness: 0.85 },
    );
    const bronze = kit.mat('#4a3c2d', { roughness: 0.45, metalness: 0.65 });
    const paving = kit.mat('#cfc8b9');

    // paved arena
    const pave = [L(-10, -6), L(10, -6), L(10, 7.5), L(-10, 7.5)];
    kit.cap(batch, paving, [[kit.ringArea(pave) < 0 ? pave.reverse() : pave]], 0.15, { scale: 3 });

    // curved wall: arc through s in [-8.85, 8.85] bowing west by 3 m, gap at s in [1.6, 4.0]
    const CH = 17.7,
      SAG = 3.0,
      T = 0.9;
    const Rr = (CH * CH) / 4 / (2 * SAG) + SAG / 2;
    const arcT = (s) => Math.sqrt(Rr * Rr - s * s) - (Rr - SAG); // offset towards west
    const height = (s) => 2.6 + 1.6 * Math.max(0, 1 - Math.abs(s - 1.0) / 9);
    const GAP = [1.6, 4.0];
    const tan = (s) => {
      const k = -s / Math.sqrt(Rr * Rr - s * s);
      return Math.atan2(D[1] + Wn[1] * k, D[0] + Wn[0] * k);
    };
    const N = 40;
    for (let i = 0; i < N; i++) {
      const s0 = -CH / 2 + (CH * i) / N,
        s1 = -CH / 2 + (CH * (i + 1)) / N;
      const sm = (s0 + s1) / 2;
      if (sm > GAP[0] && sm < GAP[1]) continue;
      const h0 = height(s0),
        h1 = height(s1);
      const e0 = L(s0, arcT(s0)),
        e1 = L(s1, arcT(s1)); // east (inner, concave) face
      const w0 = L(s0, arcT(s0) + T),
        w1 = L(s1, arcT(s1) + T);
      const u0 = (s0 + CH / 2) / CH,
        u1 = (s1 + CH / 2) / CH;
      // inner face (normal towards east/path): order so the normal points to -Wn
      batch.quad(
        relief,
        [e0[0], e0[1], 0],
        [e1[0], e1[1], 0],
        [e1[0], e1[1], h1],
        [e0[0], e0[1], h0],
        [u0, 0],
        [u1, 0],
        [u1, h1 / 4.2],
        [u0, h0 / 4.2],
      );
      batch.quad(
        relief,
        [w1[0], w1[1], 0],
        [w0[0], w0[1], 0],
        [w0[0], w0[1], h0],
        [w1[0], w1[1], h1],
        [1 - u1, 0],
        [1 - u0, 0],
        [1 - u0, h0 / 4.2],
        [1 - u1, h1 / 4.2],
      );
      batch.quad(
        stone,
        [e0[0], e0[1], h0],
        [e1[0], e1[1], h1],
        [w1[0], w1[1], h1],
        [w0[0], w0[1], h0],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // wall ends and gap jambs
    for (const s of [-CH / 2, GAP[0], GAP[1], CH / 2]) {
      const p = L(s, arcT(s) + T / 2);
      kit.box(batch, stone, p[0], p[1], 0, 0.06, T, height(s), tan(s));
    }
    // coping
    for (let i = 0; i < N; i += 2) {
      const s = -CH / 2 + (CH * (i + 1)) / N;
      if (s > GAP[0] && s < GAP[1]) continue;
      const p = L(s, arcT(s) + T / 2);
      kit.box(batch, stone, p[0], p[1], height(s), (CH / N) * 2 + 0.05, T + 0.2, 0.15, tan(s));
    }
    // steps up to the gap from the east side, landing in the gap
    const gm = (GAP[0] + GAP[1]) / 2;
    for (let k = 0; k < 4; k++) {
      const p = L(gm, arcT(gm) - 3.2 + k * 0.8);
      kit.box(batch, stone, p[0], p[1], 0, 3.2, 0.8, 0.15 * (k + 1), ang);
    }
    const lp = L(gm, arcT(gm) + T / 2);
    kit.box(batch, stone, lp[0], lp[1], 0, GAP[1] - GAP[0], T + 0.4, 0.6, ang);

    // bronze animals -------------------------------------------------------------------
    const put = (geo, m) => {
      batch.addGeometry(bronze, geo, m);
      geo.dispose();
    };
    const quadruped = (p, z, heading, s, { pack = false, longNeck = false, dog = false } = {}) => {
      const M = (x, y, zz, ry = 0) =>
        new THREE.Matrix4()
          .makeTranslation(
            p[0] + Math.cos(heading) * x - Math.sin(heading) * y,
            p[1] + Math.sin(heading) * x + Math.cos(heading) * y,
            z + zz,
          )
          .multiply(new THREE.Matrix4().makeRotationZ(heading))
          .multiply(new THREE.Matrix4().makeRotationY(ry));
      const bodyH = dog ? 0.45 * s : 1.15 * s;
      put(new THREE.SphereGeometry(1, 10, 7).scale(0.75 * s, 0.3 * s, 0.32 * s), M(0, 0, bodyH));
      const legL = bodyH - 0.1 * s;
      for (const [lx, ly] of [
        [0.5, 0.17],
        [0.5, -0.17],
        [-0.5, 0.17],
        [-0.5, -0.17],
      ])
        put(
          new THREE.CylinderGeometry(0.05 * s, 0.07 * s, legL, 6).rotateX(Math.PI / 2),
          M(lx * s, ly * s, legL / 2),
        );
      put(
        new THREE.CylinderGeometry(0.1 * s, 0.17 * s, (longNeck ? 0.75 : 0.5) * s, 8).rotateX(
          Math.PI / 2,
        ),
        M(0.75 * s, 0, bodyH + 0.3 * s, 0.7),
      );
      put(
        new THREE.SphereGeometry(1, 8, 6).scale(0.28 * s, 0.13 * s, 0.14 * s),
        M(1.05 * s, 0, bodyH + (longNeck ? 0.65 : 0.5) * s, 0.4),
      );
      if (dog)
        put(
          new THREE.ConeGeometry(0.04 * s, 0.4 * s, 6).rotateZ(Math.PI / 2 + 0.5),
          M(-0.85 * s, 0, bodyH + 0.1 * s),
        );
      if (pack) {
        put(new THREE.BoxGeometry(0.7 * s, 0.85 * s, 0.4 * s), M(0, 0, bodyH + 0.35 * s));
        for (const sd of [-1, 1])
          put(
            new THREE.BoxGeometry(0.5 * s, 0.25 * s, 0.45 * s),
            M(0.05 * s, sd * 0.45 * s, bodyH + 0.05 * s),
          );
        put(
          new THREE.CylinderGeometry(0.12 * s, 0.12 * s, 1.0 * s, 8),
          M(-0.1 * s, 0, bodyH + 0.65 * s),
        );
      }
    };
    // mules climbing towards the gap (heading west-ish through the wall)
    const headIn = Math.atan2(Wn[1], Wn[0]);
    quadruped(L(gm - 0.7, arcT(gm) - 2.4), 0.45, headIn + 0.15, 1.0, { pack: true });
    quadruped(L(gm + 0.9, arcT(gm) - 4.6), 0.15, headIn - 0.1, 1.0, { pack: true });
    // horse and dog beyond the gap, gazing into the distance
    quadruped(L(gm + 0.6, arcT(gm) + T + 3.0), 0.15, headIn + 0.35, 1.3, { longNeck: true });
    quadruped(L(gm - 1.6, arcT(gm) + T + 2.2), 0.15, headIn + 0.2, 0.9, { dog: true });

    g.add(batch.toGroup('animals_in_war_memorial'));
    return g;
  },
};
