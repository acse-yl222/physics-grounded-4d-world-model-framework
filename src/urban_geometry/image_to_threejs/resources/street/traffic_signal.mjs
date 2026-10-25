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
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 3.1, 8).rotateX(Math.PI / 2),
      kit.mat('#2b2e31'),
    );
    pole.position.z = 1.55;
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.25, 0.95), kit.mat('black'));
    head.position.set(0, 0.12, 2.9);
    const board = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.02, 1.15), kit.mat('#1a1a1a'));
    board.position.set(0, 0.0, 2.9);
    g.add(pole, head, board);
    ['#d42a1f', '#e8a317', '#2aa84a'].forEach((c, k) => {
      const lens = new THREE.Mesh(
        new THREE.CylinderGeometry(0.09, 0.09, 0.03, 10),
        kit.mat(c, { emissive: new THREE.Color(c), emissiveIntensity: 0.35 }),
      );
      lens.position.set(0, 0.26, 3.2 - k * 0.3);
      g.add(lens);
    });
    return g;
  },
};
