// Litter bin: black cylindrical bin with a domed lid and gold band.
export default {
  id: 'waste_basket',
  kind: 'street',
  name: 'Litter bin',
  size: [0.6, 0.6, 1.05],
  references: [
    {
      title: 'RBKC Streetscape guide, chapter 4 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/chapter-4---street-furniture',
      used_for: 'black litter bins as part of the standard street furniture palette',
    },
  ],
  notes: '',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.28, 0.26, 0.9, 10).rotateX(Math.PI / 2),
      kit.mat('#1d2024'),
    );
    body.position.z = 0.45;
    const band = new THREE.Mesh(
      new THREE.CylinderGeometry(0.285, 0.285, 0.05, 10).rotateX(Math.PI / 2),
      kit.mat('gold'),
    );
    band.position.z = 0.78;
    const lid = new THREE.Mesh(
      new THREE.SphereGeometry(0.29, 10, 4, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2),
      kit.mat('#1d2024'),
    );
    lid.position.z = 0.9;
    lid.scale.z = 0.5;
    g.add(body, band, lid);
    return g;
  },
};
