// Kensington & Chelsea style residential lamp column: black cast-metal column on a
// fluted base, swan-neck bracket and a hexagonal lantern; ~6 m mounting height.
export default {
  id: 'street_lamp',
  kind: 'street',
  name: 'Street lamp column',
  size: [0.5, 1.4, 6.4],
  references: [
    {
      title: 'RBKC Streetscape guide, part 2 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/part-2---street-furniture',
      used_for: 'DW Windsor Chester column with Chelsea Coronet lantern on residential roads',
    },
    {
      title: 'Essex design guide - street lighting',
      url: 'https://www.essexdesignguide.co.uk/design-details/highways-technical-manual/street-lighting',
      used_for: 'typical 6 m mounting height',
    },
  ],
  notes:
    'One generic heritage column for all roads: fluted base, swan-neck bracket and hexagonal lantern (low detail: plain column). The arm points along +y (towards the road).',
  build({ THREE, kit, detail = 'high' }) {
    const g = new THREE.Group();
    const black = kit.mat('#1d2024', { roughness: 0.5, metalness: 0.3 });
    const lamp = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.45,
      roughness: 0.25,
    });
    const add = (geo, m, x = 0, y = 0, z = 0) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    const turn = (profile, seg) =>
      new THREE.LatheGeometry(
        profile.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
    if (detail === 'low') {
      add(new THREE.CylinderGeometry(0.17, 0.22, 1.1, 6).rotateX(Math.PI / 2), black, 0, 0, 0.55);
      add(new THREE.CylinderGeometry(0.06, 0.09, 5.2, 5).rotateX(Math.PI / 2), black, 0, 0, 3.6);
      add(new THREE.BoxGeometry(0.05, 0.9, 0.05), black, 0, 0.45, 6.12);
      add(new THREE.CylinderGeometry(0.16, 0.1, 0.36, 6).rotateX(Math.PI / 2), lamp, 0, 0.9, 5.88);
      return g;
    }
    // Fluted cast base with mouldings, tapered shaft, collar and finial.
    add(
      turn(
        [
          [0, 0],
          [0.24, 0],
          [0.24, 0.08],
          [0.2, 0.12],
          [0.19, 0.9],
          [0.22, 0.95],
          [0.15, 1.02],
          [0.1, 1.15],
          [0, 1.15],
        ],
        16,
      ),
      black,
    );
    for (let k = 0; k < 12; k++) {
      const a = (k / 12) * Math.PI * 2;
      add(
        new THREE.BoxGeometry(0.03, 0.03, 0.72),
        black,
        Math.cos(a) * 0.195,
        Math.sin(a) * 0.195,
        0.5,
      );
    }
    add(
      turn(
        [
          [0.085, 0],
          [0.06, 4.6],
          [0.08, 4.65],
          [0.08, 4.75],
          [0.05, 4.8],
          [0.05, 5.0],
          [0, 5.05],
        ],
        10,
      ),
      black,
      0,
      0,
      1.1,
    );
    add(new THREE.SphereGeometry(0.06, 10, 6), black, 0, 0, 6.2);
    // Swan-neck bracket with a scroll under it.
    const neck = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, 5.75),
      new THREE.Vector3(0, 0.25, 6.05),
      new THREE.Vector3(0, 0.6, 6.15),
      new THREE.Vector3(0, 0.85, 6.1),
      new THREE.Vector3(0, 0.95, 6.0),
    ]);
    add(new THREE.TubeGeometry(neck, 16, 0.03, 6, false), black);
    const scroll = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, 5.45),
      new THREE.Vector3(0, 0.2, 5.55),
      new THREE.Vector3(0, 0.3, 5.75),
      new THREE.Vector3(0, 0.22, 5.85),
    ]);
    add(new THREE.TubeGeometry(scroll, 10, 0.018, 5, false), black);
    // Lantern: hexagonal glazed body in a black frame, crown and finial.
    const lz = 5.62,
      ly = 0.95;
    add(new THREE.CylinderGeometry(0.17, 0.11, 0.38, 6).rotateX(Math.PI / 2), lamp, 0, ly, lz);
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + Math.PI / 6;
      const bar = add(
        new THREE.BoxGeometry(0.02, 0.02, 0.4),
        black,
        Math.cos(a) * 0.145,
        ly + Math.sin(a) * 0.145,
        lz,
      );
      bar.rotation.set(Math.sin(a) * -0.15, Math.cos(a) * 0.15, 0);
    }
    add(new THREE.CylinderGeometry(0.2, 0.2, 0.04, 6).rotateX(Math.PI / 2), black, 0, ly, lz + 0.2);
    add(
      new THREE.CylinderGeometry(0.12, 0.12, 0.04, 6).rotateX(Math.PI / 2),
      black,
      0,
      ly,
      lz - 0.2,
    );
    add(
      turn(
        [
          [0.21, 0],
          [0.16, 0.1],
          [0.06, 0.2],
          [0.03, 0.3],
          [0.05, 0.34],
          [0, 0.4],
        ],
        6,
      ),
      black,
      0,
      ly,
      lz + 0.22,
    );
    return g;
  },
};
