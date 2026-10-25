// New Routemaster (Wright / Heatherwick): 11.23 x 2.52 x 4.39 m, London red,
// asymmetric diagonal glazing over the staircases, black glazing bands on both decks.
export default {
  id: 'double_decker_bus',
  kind: 'vehicle',
  name: 'New Routemaster bus',
  size: [2.52, 11.23, 4.39],
  references: [
    {
      title: 'New Routemaster - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/New_Routemaster',
      used_for: 'length 11.23 m, width 2.52 m, height 4.39 m',
    },
    {
      title: 'New London Bus | Heatherwick Studio',
      url: 'https://archilovers.com/projects/62870/new-london-bus.html',
      used_for: 'wrap-around stair glazing',
    },
  ],
  notes:
    'Not placed by the default build: there is no recorded vehicle position data for this scene.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const red = kit.mat('#d6211f', { roughness: 0.4, metalness: 0.2 });
    const glass = kit.mat('dark_glass');
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    const L = 11.23,
      W = 2.52,
      H = 4.39;
    add(new THREE.BoxGeometry(W, L, 0.9), red, 0, 0, 0.8);
    add(new THREE.BoxGeometry(W * 0.98, L * 0.97, 1.05), glass, 0, 0, 1.8);
    add(new THREE.BoxGeometry(W, L, 0.55), red, 0, 0, 2.6);
    add(new THREE.BoxGeometry(W * 0.98, L * 0.97, 1.0), glass, 0, 0, 3.4);
    add(new THREE.BoxGeometry(W, L, 0.3), red, 0, 0, H - 0.15);
    // Diagonal stair glazing ribbons at front and rear.
    for (const y of [L / 2 - 0.9, -L / 2 + 0.9])
      add(new THREE.BoxGeometry(W * 1.01, 1.2, 0.5), glass, 0, y, 2.6);
    add(
      new THREE.BoxGeometry(1.4, 0.05, 0.3),
      kit.mat('#ffcc00', { emissive: new THREE.Color('#ffcc00'), emissiveIntensity: 0.4 }),
      0,
      L / 2 + 0.01,
      3.95,
    );
    for (const x of [-W / 2 + 0.15, W / 2 - 0.15])
      for (const y of [L / 2 - 2.4, -L / 2 + 3.0]) {
        const w = add(new THREE.CylinderGeometry(0.5, 0.5, 0.3, 12), kit.mat('#141414'), x, y, 0.5);
        w.rotation.z = Math.PI / 2;
      }
    return g;
  },
};
