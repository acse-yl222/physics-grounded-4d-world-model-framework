// Black cast-iron cannon bollard with a gold-free plain cap, common in central London.
export default {
  id: 'bollard',
  kind: 'street',
  name: 'Cast-iron bollard',
  size: [0.25, 0.25, 0.95],
  references: [
    {
      title: 'RBKC Streetscape guide, part 2 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/part-2---street-furniture',
      used_for: 'black cast-iron bollards in conservation areas',
    },
  ],
  notes: '',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const iron = kit.mat('#1d2024', { roughness: 0.5 });
    const shaft = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.13, 0.85, 8).rotateX(Math.PI / 2),
      iron,
    );
    shaft.position.z = 0.43;
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.11, 8, 4).rotateX(Math.PI / 2), iron);
    cap.position.z = 0.88;
    g.add(shaft, cap);
    return g;
  },
};
