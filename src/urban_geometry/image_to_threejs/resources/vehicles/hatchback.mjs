// Generic European hatchback (~4.2 x 1.8 x 1.45 m), colour variants via kit.mat.
export default {
  id: 'hatchback',
  kind: 'vehicle',
  name: 'Hatchback car',
  size: [1.8, 4.2, 1.45],
  references: [
    {
      title: 'LEVC dimensions table - VehicleScore',
      url: 'https://vehiclescore.co.uk/car-dimensions-check/levc',
      used_for: 'dimension conventions (length/width/height) used for UK vehicle data',
    },
  ],
  notes:
    'Generic proportions, not a specific model. Not placed by default (no vehicle position data).',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const body = kit.mat('#6b7f99', { roughness: 0.35, metalness: 0.4 });
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    add(new THREE.BoxGeometry(1.8, 4.2, 0.65), body, 0, 0, 0.6);
    add(new THREE.BoxGeometry(1.62, 2.3, 0.55), kit.mat('dark_glass'), 0, -0.35, 1.18);
    add(new THREE.BoxGeometry(1.6, 2.2, 0.05), body, 0, -0.35, 1.45);
    for (const x of [-0.78, 0.78])
      for (const y of [-1.3, 1.3]) {
        const w = add(
          new THREE.CylinderGeometry(0.32, 0.32, 0.22, 12),
          kit.mat('#141414'),
          x,
          y,
          0.32,
        );
        w.rotation.z = Math.PI / 2;
      }
    return g;
  },
};
