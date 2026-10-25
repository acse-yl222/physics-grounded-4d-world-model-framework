// Conifer (yew / cedar group in parks and cemeteries): dark conical crown.
// Unit-height prototype.
export default {
  id: 'conifer',
  kind: 'vegetation',
  name: 'Conifer',
  size: [0.35, 0.35, 1],
  references: [
    {
      title: 'London plane - Gdansk tree trail',
      url: 'https://pg.edu.pl/en/sustainable-development/tree-trail/london-plane',
      used_for: 'contrast species set for park planting variety',
    },
  ],
  notes: 'Generic dark conical tree used sparingly for variety.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.015, 0.02, 0.2, 5).rotateX(Math.PI / 2),
      kit.mat('bark'),
    );
    trunk.position.z = 0.1;
    const crown = new THREE.Mesh(
      new THREE.ConeGeometry(0.18, 0.85, 8).rotateX(Math.PI / 2),
      kit.mat('#2f4f2a', { roughness: 0.95 }),
    );
    crown.position.z = 0.58;
    g.add(trunk, crown);
    return g;
  },
};
