// Joy of Life Fountain (now "Four Winds"), Hyde Park near Park Lane opposite Mount
// Street / Aldford Street (T. B. Huxley-Jones, unveiled 25 June 1963, the last commission
// of the Constance Fund). Two bronze figures dance hand in hand above a round pool,
// while four bronze children emerge from the water at its edges; the basins were
// redesigned in 2000-01.
export default {
  id: 'joy_of_life_fountain',
  name: 'Joy of Life Fountain',
  claims: [],
  references: [
    {
      title: 'List of public art in Hyde Park, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/List_of_public_art_in_Hyde_Park,_London',
      used_for:
        'Joy of Life / Four Winds Fountain by T. B. Huxley-Jones, 1963, near Park Lane; basins redesigned 2000-01',
    },
    {
      title: "London's Most Beautiful Fountains - Londonist",
      url: 'https://londonist.com/london/great-outdoors/londons-most-beautiful-fountains',
      used_for:
        'two bronze figures dancing above a pond, four bronze children emerging from the water at the edges; unveiled 25 June 1963',
    },
    {
      title: 'T. B. Huxley-Jones - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/T._B._Huxley-Jones',
      used_for: 'sculptor and the 1963 Hyde Park commission',
    },
    {
      title: 'Archive: pioneering women - Royal Society of Sculptors',
      url: 'https://sculptors.org.uk/blog/2019/04/archive-pioneering-women',
      used_for: 'replacement West Wind figure by Gwynneth Holt',
    },
  ],
  notes:
    'Pool aligned on the round basin of the scene water layer near Park Lane (centre ~ (3089, 231), r 8.5 m), ' +
    'which lies ~70 m east of the listed point. The tall central bronze stem carrying the dancing couple, its ' +
    'height (5.5 m to the figures), the jets and the children placed at the four points are simplified ' +
    'reconstructions from the descriptions.',
  build({ THREE, kit, scene }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let C = [3089.2, 230.7],
      R = 8.5;
    for (const w of scene.water ?? []) {
      if (!w.poly) continue;
      const r = w.poly[0];
      const cx = r.reduce((s, p) => s + p[0], 0) / r.length,
        cy = r.reduce((s, p) => s + p[1], 0) / r.length;
      if (Math.hypot(cx - 3089, cy - 231) < 6) {
        C = [cx, cy];
        R = r.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / r.length;
      }
    }
    const stone = kit.mat('#cfc8b8', { roughness: 0.8 });
    const waterM = kit.ground('water');
    const bronze = kit.mat('#4b3f30', { roughness: 0.45, metalness: 0.65 });
    const jet = kit.mat('#eaf4f7', { transparent: true, opacity: 0.55, roughness: 0.1 });
    const put = (geo, mat, x, y, z, rz = 0, ry = 0, rx = 0) => {
      const m = new THREE.Matrix4()
        .makeTranslation(C[0] + x, C[1] + y, z)
        .multiply(new THREE.Matrix4().makeRotationZ(rz))
        .multiply(new THREE.Matrix4().makeRotationY(ry))
        .multiply(new THREE.Matrix4().makeRotationX(rx));
      batch.addGeometry(mat, geo, m);
      geo.dispose();
    };
    const circ = (r, n = 40) => {
      const out = [];
      for (let k = 0; k < n; k++) {
        const a = (k / n) * Math.PI * 2;
        out.push([C[0] + r * Math.cos(a), C[1] + r * Math.sin(a)]);
      }
      return out;
    };
    // kerb and water surface
    const outer = circ(R + 0.5),
      inner = circ(R);
    kit.cap(batch, stone, [[outer, inner.slice().reverse()]], 0.5);
    kit.walls(batch, stone, [[outer]], 0, 0.5, { bay: 1e6 });
    kit.walls(batch, stone, [[inner.slice().reverse()]], 0.25, 0.5, { bay: 1e6 });
    kit.cap(batch, waterM, [[inner]], 0.3, { scale: 20 });
    // central rocky base and bronze stem
    put(new THREE.CylinderGeometry(1.0, 1.4, 0.8, 9).rotateX(Math.PI / 2), stone, 0, 0, 0.6);
    put(
      new THREE.CylinderGeometry(0.12, 0.25, 4.6, 10).rotateX(Math.PI / 2),
      bronze,
      0,
      0,
      1.0 + 2.3,
    );
    // dancing couple: two leaning figures joined at the hands, one swung outwards
    const figure = (x, y, z, rz, lean, s = 1) => {
      put(
        new THREE.CylinderGeometry(0.06 * s, 0.08 * s, 0.85 * s, 8).rotateX(Math.PI / 2),
        bronze,
        x,
        y,
        z + 0.42 * s,
        rz,
        lean,
      );
      const tx = x + Math.cos(rz) * Math.sin(lean) * 0.9 * s,
        ty = y + Math.sin(rz) * Math.sin(lean) * 0.9 * s;
      put(
        new THREE.CylinderGeometry(0.15 * s, 0.12 * s, 0.7 * s, 10).rotateX(Math.PI / 2),
        bronze,
        tx,
        ty,
        z + 1.15 * s,
        rz,
        lean,
      );
      const hx = x + Math.cos(rz) * Math.sin(lean) * 1.35 * s,
        hy = y + Math.sin(rz) * Math.sin(lean) * 1.35 * s;
      put(new THREE.SphereGeometry(0.13 * s, 10, 8), bronze, hx, hy, z + 1.62 * s);
      // arms outstretched
      put(
        new THREE.CylinderGeometry(0.035 * s, 0.04 * s, 0.75 * s, 6).rotateX(Math.PI / 2),
        bronze,
        tx,
        ty,
        z + 1.35 * s,
        rz + Math.PI / 2,
        1.2,
      );
    };
    const Z = 5.6;
    figure(0.05, 0, Z, 0.4, 0.25);
    figure(-0.2, 0.15, Z + 0.15, 0.4 + Math.PI, 0.65, 0.95);
    // splaying jets from the stem and the four children at the edge
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2;
      put(
        new THREE.ConeGeometry(0.1, 2.4, 6, 1, true).rotateX(Math.PI / 2),
        jet,
        Math.cos(a) * 1.0,
        Math.sin(a) * 1.0,
        2.0,
        a,
        0.9,
      );
    }
    for (let k = 0; k < 4; k++) {
      const a = (k / 4) * Math.PI * 2 + Math.PI / 4;
      const x = Math.cos(a) * (R - 1.0),
        y = Math.sin(a) * (R - 1.0);
      put(new THREE.SphereGeometry(0.5, 8, 6).scale(1, 1, 0.5), stone, x, y, 0.3);
      put(new THREE.SphereGeometry(0.3, 10, 8).scale(1, 1, 1.2), bronze, x, y, 0.75);
      put(new THREE.SphereGeometry(0.17, 10, 8), bronze, x, y, 1.2);
      put(
        new THREE.ConeGeometry(0.06, 1.6, 6, 1, true).rotateX(Math.PI / 2),
        jet,
        x * 0.85,
        y * 0.85,
        1.0,
        a + Math.PI,
        0.7,
      );
    }

    g.add(batch.toGroup('joy_of_life_fountain'));
    return g;
  },
};
