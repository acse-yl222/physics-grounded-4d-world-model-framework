// Peter Pan statue, Kensington Gardens (Sir George Frampton, 1912, commissioned by
// J. M. Barrie and put up overnight on 30 April / 1 May 1912) on the west side of the
// Long Water. A bronze boy blowing a pipe stands on top of a tall tree-stump base whose
// sides swarm with fairies, squirrels, rabbits, mice and frogs; about 4.3 m high, inside
// a small circular path.
export default {
  id: 'peter_pan_statue',
  name: 'Peter Pan statue',
  claims: [],
  references: [
    {
      title: 'Peter Pan statue - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Peter_Pan_statue',
      used_for:
        'Frampton 1912, about 14 ft (4.3 m) high, boy blowing a pipe on a tree-stump base decorated with squirrels, rabbits, mice and fairies; west of the Long Water',
    },
    {
      title: 'Peter Pan statue, west of Serpentine - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101217595-peter-pan-statue-west-of-serpentine-lancaster-gate-ward',
      used_for: 'Grade II*, position 51.5086, -0.176',
    },
    {
      title: 'Peter Pan in Kensington Gardens - London Remembers',
      url: 'https://www.londonremembers.com/memorials/peter-pan-in-kensington-gardens',
      used_for: 'placed 1 May 1912, gift of J. M. Barrie',
    },
  ],
  notes:
    'Centred in the small circular footway of the scene beside the listed coordinates. Total height 4.3 m: ' +
    'stump base ~3.1 m with root buttresses, boy figure ~1.2 m. Fairies and animals are small bronze lumps ' +
    'scattered round the stump; the boy faces east towards the Long Water (assumption).',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const C = [1701.2, 244.0];
    const bronze = kit.mat('#5a4a33', { roughness: 0.5, metalness: 0.6 });
    const verd = kit.mat('#6e7d5c', { roughness: 0.55, metalness: 0.4 });
    const stone = kit.mat('#b9b2a4');
    const rnd = kit.rng(1912);
    const put = (geo, mat, x, y, z, rz = 0, ry = 0) => {
      const m = new THREE.Matrix4()
        .makeTranslation(C[0] + x, C[1] + y, z)
        .multiply(new THREE.Matrix4().makeRotationZ(rz))
        .multiply(new THREE.Matrix4().makeRotationY(ry));
      batch.addGeometry(mat, geo, m);
      geo.dispose();
    };
    // low stone kerb pad
    put(new THREE.CylinderGeometry(1.7, 1.75, 0.25, 20).rotateX(Math.PI / 2), stone, 0, 0, 0.125);
    // tree stump: bumpy tapering lathe with root buttresses
    const prof = [];
    for (let i = 0; i <= 12; i++) {
      const t = i / 12;
      const r = 1.15 - 0.75 * t + 0.08 * Math.sin(t * 17);
      prof.push([Math.max(0.25, r), 0.25 + t * 2.9]);
    }
    prof.unshift([1.3, 0.25]);
    prof.push([0.38, 3.2], [0, 3.22]);
    const stump = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(r, h)),
      14,
    ).rotateX(Math.PI / 2);
    const pos = stump.attributes.position;
    for (let k = 0; k < pos.count; k++) {
      const x = pos.getX(k),
        y = pos.getY(k),
        z = pos.getZ(k);
      const a = Math.atan2(y, x);
      const f = 1 + 0.12 * Math.sin(a * 5 + z * 2.3);
      pos.setXYZ(k, x * f, y * f, z);
    }
    put(stump, bronze, 0, 0, 0);
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + 0.3;
      put(
        new THREE.ConeGeometry(0.35, 1.2, 6).rotateX(Math.PI / 2),
        bronze,
        Math.cos(a) * 1.05,
        Math.sin(a) * 1.05,
        0.75,
        a,
        0.5,
      );
    }
    // fairies, rabbits, mice and squirrels clinging to the stump
    for (let i = 0; i < 26; i++) {
      const z = 0.5 + rnd() * 2.5;
      const t = (z - 0.25) / 2.9;
      const r = 1.15 - 0.75 * t + 0.1;
      const a = rnd() * Math.PI * 2;
      const s = 0.1 + rnd() * 0.12;
      put(
        new THREE.SphereGeometry(s, 6, 4).scale(1, 1, 1.4),
        rnd() < 0.3 ? verd : bronze,
        Math.cos(a) * r,
        Math.sin(a) * r,
        z,
      );
    }
    // Peter: legs, tunic, arms raised to the pipe, head
    const Z = 3.2,
      face = 0; // facing east
    put(
      new THREE.CylinderGeometry(0.06, 0.07, 0.55, 8).rotateX(Math.PI / 2),
      bronze,
      0.0,
      0.09,
      Z + 0.28,
      face,
      0.1,
    );
    put(
      new THREE.CylinderGeometry(0.06, 0.07, 0.55, 8).rotateX(Math.PI / 2),
      bronze,
      -0.05,
      -0.09,
      Z + 0.28,
      face,
      -0.15,
    );
    put(
      new THREE.CylinderGeometry(0.13, 0.17, 0.5, 10).rotateX(Math.PI / 2),
      bronze,
      0,
      0,
      Z + 0.78,
    );
    put(new THREE.SphereGeometry(0.12, 10, 8), bronze, 0.03, 0, Z + 1.13);
    for (const sd of [-1, 1])
      put(
        new THREE.CylinderGeometry(0.035, 0.04, 0.38, 6).rotateX(Math.PI / 2),
        bronze,
        0.1,
        sd * 0.12,
        Z + 0.92,
        0,
        1.0,
      );
    put(
      new THREE.CylinderGeometry(0.015, 0.02, 0.32, 6).rotateX(Math.PI / 2),
      bronze,
      0.27,
      0,
      Z + 1.05,
      0,
      1.4,
    );

    g.add(batch.toGroup('peter_pan_statue'));
    return g;
  },
};
