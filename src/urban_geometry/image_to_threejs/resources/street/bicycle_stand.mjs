// Sheffield cycle stand: galvanised steel inverted U tube.
export default {
  id: 'bicycle_stand',
  kind: 'street',
  name: 'Sheffield cycle stand',
  size: [0.8, 0.1, 0.8],
  references: [
    {
      title: 'RBKC Streetscape guide, chapter 4 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/chapter-4---street-furniture',
      used_for: 'cycle stands in the street furniture palette',
    },
  ],
  notes: 'One stand per mapped point; mapped capacity is not modelled.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const steel = kit.mat('aluminium');
    const arc = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.025, 5, 10, Math.PI), steel);
    arc.rotation.x = Math.PI / 2;
    arc.position.z = 0.45;
    g.add(arc);
    for (const x of [-0.35, 0.35]) {
      const leg = new THREE.Mesh(
        new THREE.CylinderGeometry(0.025, 0.025, 0.45, 5).rotateX(Math.PI / 2),
        steel,
      );
      leg.position.set(x, 0, 0.225);
      g.add(leg);
    }
    return g;
  },
};
