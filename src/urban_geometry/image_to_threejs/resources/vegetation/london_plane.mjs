// London plane (Platanus x hispanica): tall clear trunk with mottled bark and a
// broad, rounded, semi-open crown; the dominant London street and park tree.
// Unit-height prototype (1 m); the instancer scales it per tree.
export default {
  id: 'london_plane',
  kind: 'vegetation',
  name: 'London plane',
  size: [0.65, 0.65, 1],
  references: [
    {
      title: 'Platanus x hispanica - Ebben nurseries',
      url: 'https://www.ebben.nl/en/treeebb/plhispan-platanus-x-hispanica/',
      used_for: 'height 20-40 m, crown 18-25 m wide, rounded semi-open crown',
    },
    {
      title: 'The London Plane (treetree.co.uk)',
      url: 'https://www.treetree.co.uk/treetree_downloads/The_London_Plane.pdf',
      used_for: 'London street tree form',
    },
  ],
  notes: 'Crown as three overlapping low-poly lobes.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const bark = kit.mat('#8a8070'),
      leaf = kit.mat('#5a7f3f', { roughness: 0.95 });
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.018, 0.03, 0.55, 6).rotateX(Math.PI / 2),
      bark,
    );
    trunk.position.z = 0.275;
    g.add(trunk);
    for (const [x, y, z, r] of [
      [0, 0, 0.66, 0.3],
      [0.13, 0.06, 0.58, 0.22],
      [-0.11, -0.08, 0.6, 0.23],
    ]) {
      const lobe = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), leaf);
      lobe.position.set(x, y, z);
      lobe.scale.z = 0.85;
      g.add(lobe);
    }
    return g;
  },
};
