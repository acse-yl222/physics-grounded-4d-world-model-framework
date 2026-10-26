// UK traffic signal: grey/black pole with a three-aspect signal head facing +y,
// white-striped backing board.
export default {
  id: 'traffic_signal',
  kind: 'street',
  name: 'Traffic signal',
  size: [0.4, 0.4, 3.6],
  references: [
    {
      title: 'Reducing street clutter: shared signals and lighting (SWOV)',
      url: 'https://swov.nl/en/publicatie/reducing-street-clutter-shared-signals-and-lighting',
      used_for: 'signal pole as a separate street element',
    },
  ],
  notes: 'Aspects drawn red/amber/green, not timed.',
  build({ THREE, kit, detail = 'high' }) {
    const g = new THREE.Group();
    const grey = kit.mat('#2b2e31');
    const add = (geo, m, x = 0, y = 0, z = 0) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    add(
      new THREE.CylinderGeometry(0.06, 0.07, 3.1, detail === 'low' ? 6 : 10).rotateX(Math.PI / 2),
      grey,
      0,
      0,
      1.55,
    );
    add(new THREE.BoxGeometry(0.32, 0.25, 0.95), kit.mat('black'), 0, 0.12, 2.9);
    add(new THREE.BoxGeometry(0.52, 0.02, 1.17), kit.mat('#f2f2f2'), 0, -0.005, 2.9);
    add(new THREE.BoxGeometry(0.46, 0.025, 1.11), kit.mat('#1a1a1a'), 0, 0.0, 2.9);
    ['#d42a1f', '#e8a317', '#2aa84a'].forEach((c, k) => {
      add(
        new THREE.CylinderGeometry(0.09, 0.09, 0.03, 12),
        kit.mat(c, { emissive: new THREE.Color(c), emissiveIntensity: 0.35 }),
        0,
        0.26,
        3.2 - k * 0.3,
      );
      if (detail !== 'low')
        add(
          new THREE.CylinderGeometry(0.12, 0.12, 0.2, 12, 1, true, -Math.PI / 2, Math.PI),
          kit.mat('black'),
          0,
          0.36,
          3.24 - k * 0.3,
        ).rotation.x = Math.PI / 2;
    });
    if (detail !== 'low') {
      // Pedestrian push-button unit and the base collar.
      add(new THREE.BoxGeometry(0.16, 0.12, 0.3), kit.mat('#d8d4c8'), 0, 0.1, 1.15);
      add(new THREE.BoxGeometry(0.06, 0.02, 0.06), kit.mat('#d42a1f'), 0, 0.17, 1.1);
      add(new THREE.CylinderGeometry(0.11, 0.12, 0.25, 10).rotateX(Math.PI / 2), grey, 0, 0, 0.125);
    }
    return g;
  },
};
