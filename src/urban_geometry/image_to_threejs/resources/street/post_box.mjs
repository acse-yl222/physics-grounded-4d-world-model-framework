// Royal Mail cylindrical pillar box: cast iron, red with black base, cap with
// overhanging rim, horizontal letter aperture and a white collection plate.
export default {
  id: 'post_box',
  kind: 'street',
  name: 'Pillar box',
  size: [0.6, 0.6, 1.65],
  references: [
    {
      title: 'Pillar box - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Pillar_box',
      used_for: 'form and colours',
    },
    {
      title: 'George V pillar box, Sheffield collection',
      url: 'https://shimmer.shu.ac.uk/luna/servlet/detail/SHU~3~3~510779~150993',
      used_for: 'height about 165 cm',
    },
    {
      title: 'Pillar box, Falkirk collections',
      url: 'https://collections.falkirk.gov.uk/objects/86335766/pillar-box',
      used_for: 'base diameter about 59 cm',
    },
  ],
  notes: 'Royal cypher omitted.',
  build({ THREE, kit, detail = 'high' }) {
    const g = new THREE.Group();
    const red = kit.mat('#c8102e', { roughness: 0.45 });
    const seg = detail === 'low' ? 8 : 20;
    const add = (geo, m, x = 0, y = 0, z = 0) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    // Turned body: black plinth, red shaft with beaded bands, overhanging cap and dome.
    const profile = [
      [0, 0],
      [0.31, 0],
      [0.31, 0.16],
      [0.28, 0.2],
      [0.27, 1.2],
      [0.29, 1.24],
      [0.28, 1.28],
      [0.27, 1.34],
      [0.32, 1.38],
      [0.32, 1.44],
      [0.28, 1.47],
      [0.2, 1.56],
      [0.08, 1.62],
      [0, 1.64],
    ];
    const body = new THREE.LatheGeometry(
      profile.map(([r, h]) => new THREE.Vector2(r, h)),
      seg,
    ).rotateX(Math.PI / 2);
    add(body, red);
    add(
      new THREE.CylinderGeometry(0.315, 0.32, 0.18, seg).rotateX(Math.PI / 2),
      kit.mat('black'),
      0,
      0,
      0.09,
    );
    if (detail === 'low') return g;
    add(new THREE.BoxGeometry(0.26, 0.05, 0.05), kit.mat('black'), 0, 0.27, 1.25);
    add(new THREE.BoxGeometry(0.3, 0.06, 0.03), red, 0, 0.285, 1.29);
    add(new THREE.BoxGeometry(0.18, 0.02, 0.13), kit.mat('white'), 0, 0.28, 1.06);
    add(new THREE.BoxGeometry(0.36, 0.03, 0.62), red, 0, 0.27, 0.7);
    add(
      new THREE.BoxGeometry(0.12, 0.02, 0.1),
      kit.mat('#d6b04c', { metalness: 0.7, roughness: 0.35 }),
      0,
      0.29,
      0.86,
    );
    return g;
  },
};
