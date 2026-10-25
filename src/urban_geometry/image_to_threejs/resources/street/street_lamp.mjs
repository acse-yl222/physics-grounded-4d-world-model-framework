// Kensington & Chelsea style residential lamp column: black cast-metal column on a
// fluted base, swan-neck bracket and a lantern; ~6 m mounting height.
export default {
  id: 'street_lamp',
  kind: 'street',
  name: 'Street lamp column',
  size: [0.5, 1.4, 6.4],
  references: [
    {
      title: 'RBKC Streetscape guide, part 2 - street furniture',
      url: 'https://www.rbkc.gov.uk/media/document/part-2---street-furniture',
      used_for: 'DW Windsor Chester column with Chelsea Coronet lantern on residential roads',
    },
    {
      title: 'Essex design guide - street lighting',
      url: 'https://www.essexdesignguide.co.uk/design-details/highways-technical-manual/street-lighting',
      used_for: 'typical 6 m mounting height',
    },
  ],
  notes:
    'One generic heritage column for all roads; lantern simplified. The arm points along +y (towards the road).',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const black = kit.mat('#1d2024', { roughness: 0.5, metalness: 0.3 });
    const lamp = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.4,
      roughness: 0.3,
    });
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    add(new THREE.CylinderGeometry(0.17, 0.22, 1.1, 8).rotateX(Math.PI / 2), black, 0, 0, 0.55);
    add(new THREE.CylinderGeometry(0.06, 0.09, 5.2, 8).rotateX(Math.PI / 2), black, 0, 0, 3.6);
    add(new THREE.BoxGeometry(0.05, 0.9, 0.05), black, 0, 0.45, 6.12);
    add(new THREE.TorusGeometry(0.18, 0.025, 4, 8, Math.PI), black, 0, 0.18, 6.0).rotation.set(
      Math.PI / 2,
      Math.PI / 2,
      0,
    );
    add(new THREE.CylinderGeometry(0.16, 0.1, 0.36, 6).rotateX(Math.PI / 2), lamp, 0, 0.9, 5.88);
    add(new THREE.ConeGeometry(0.22, 0.2, 6).rotateX(Math.PI / 2), black, 0, 0.9, 6.15);
    return g;
  },
};
