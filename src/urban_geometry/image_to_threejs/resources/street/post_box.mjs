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
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const red = kit.mat('#c8102e', { roughness: 0.45 });
    const add = (geo, m, z) => {
      const o = new THREE.Mesh(geo.rotateX(Math.PI / 2), m);
      o.position.z = z;
      g.add(o);
      return o;
    };
    add(new THREE.CylinderGeometry(0.3, 0.32, 0.18, 14), kit.mat('black'), 0.09);
    add(new THREE.CylinderGeometry(0.26, 0.28, 1.2, 14), red, 0.78);
    add(new THREE.CylinderGeometry(0.31, 0.31, 0.08, 14), red, 1.42);
    add(new THREE.SphereGeometry(0.29, 14, 5, 0, Math.PI * 2, 0, Math.PI / 2), red, 1.46).scale.z =
      0.55;
    const slot = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.06, 0.04), kit.mat('black'));
    slot.position.set(0, 0.26, 1.27);
    const plate = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.02, 0.12), kit.mat('white'));
    plate.position.set(0, 0.27, 1.08);
    g.add(slot, plate);
    return g;
  },
};
