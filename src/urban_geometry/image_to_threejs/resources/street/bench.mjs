// Park / street bench: timber slats on black cast-iron ends (Royal Parks style).
export default {
  id: 'bench',
  kind: 'street',
  name: 'Bench',
  size: [1.8, 0.65, 0.85],
  references: [
    {
      title: 'RBKC Streetscape guide, chapter 4 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/chapter-4---street-furniture',
      used_for: 'standard bench types: timber seat on metal frame',
    },
  ],
  notes: 'Faces +y.',
  build({ THREE, kit, detail = 'high' }) {
    const g = new THREE.Group();
    const wood = kit.mat('timber'),
      iron = kit.mat('#1d2024', { roughness: 0.5 });
    const add = (geo, m, x, y, z, rx = 0) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      o.rotation.x = rx;
      g.add(o);
    };
    const slats = detail === 'low' ? 2 : 4;
    for (const x of [-0.82, 0.82]) {
      add(new THREE.BoxGeometry(0.06, 0.55, 0.06), iron, x, 0, 0.44);
      add(new THREE.BoxGeometry(0.06, 0.06, 0.44), iron, x, 0.22, 0.22);
      add(new THREE.BoxGeometry(0.06, 0.06, 0.84), iron, x, -0.24, 0.42);
      if (detail !== 'low') {
        add(new THREE.BoxGeometry(0.07, 0.5, 0.05), iron, x, 0.02, 0.66, -0.1);
        add(new THREE.BoxGeometry(0.06, 0.06, 0.2), iron, x, 0.24, 0.56);
        add(new THREE.BoxGeometry(0.12, 0.62, 0.04), iron, x, 0, 0.03);
      }
    }
    if (detail !== 'low') add(new THREE.BoxGeometry(0.05, 0.5, 0.06), iron, 0, 0, 0.4);
    for (let k = 0; k < slats; k++)
      add(new THREE.BoxGeometry(1.8, 0.48 / slats, 0.035), wood, 0, 0.2 - (k * 0.48) / slats, 0.46);
    for (let k = 0; k < slats - 1; k++)
      add(
        new THREE.BoxGeometry(1.8, 0.035, 0.09),
        wood,
        0,
        -0.26 - k * 0.01,
        0.6 + k * 0.12,
        -0.15,
      );
    return g;
  },
};
