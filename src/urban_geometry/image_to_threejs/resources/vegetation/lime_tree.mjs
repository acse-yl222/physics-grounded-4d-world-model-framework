// Common lime (Tilia x europaea): tall, narrower ovoid crown on a straight trunk;
// widely planted in London parks and avenues. Unit-height prototype.
export default {
  id: 'lime_tree',
  kind: 'vegetation',
  name: 'Common lime',
  size: [0.45, 0.45, 1],
  references: [
    {
      title: 'London Plane (Yale Nature Walk)',
      url: 'https://naturewalk.yale.edu/node/126',
      used_for: 'contrast: plane spreading crown vs. narrower avenue trees',
    },
  ],
  notes: 'Generic ovoid broadleaf used for variety.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.015, 0.025, 0.5, 6).rotateX(Math.PI / 2),
      kit.mat('bark'),
    );
    trunk.position.z = 0.25;
    const crown = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.24, 1),
      kit.mat('#4d7a3a', { roughness: 0.95 }),
    );
    crown.position.z = 0.68;
    crown.scale.z = 1.35;
    g.add(trunk, crown);
    return g;
  },
};
