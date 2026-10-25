// Santander Cycles docking station: a terminal plus a row of docking points
// (0.75 m pitch) holding red hire bikes.
export default {
  id: 'cycle_hire_dock',
  kind: 'street',
  name: 'Santander Cycles docking station',
  size: [6.0, 1.8, 2.3],
  references: [
    {
      title: 'Santander Cycles - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Santander_Cycles',
      used_for: 'scheme, red bikes, 8D Technologies docks',
    },
    {
      title: 'TfL guidance for suspending cycle hire docking stations',
      url: 'https://www.TfL.gov.uk/cdn/static/cms/documents/guidance-for-suspending-cycle-hire-docking-stations-final-20210816.pdf',
      used_for: '0.75 m per docking point, 2.0 m allowance',
    },
  ],
  notes: 'Fixed 6 docking points; real station sizes vary.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const grey = kit.mat('#5b6066', { metalness: 0.4, roughness: 0.4 });
    const red = kit.mat('#e2001a', { roughness: 0.5 });
    const black = kit.mat('#1d2024');
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    add(new THREE.BoxGeometry(0.7, 0.4, 2.2), grey, -2.6, 0, 1.1);
    add(new THREE.BoxGeometry(0.5, 0.05, 0.35), kit.mat('dark_glass'), -2.6, 0.22, 1.5);
    for (let k = 0; k < 6; k++) {
      const x = -1.6 + k * 0.75;
      add(new THREE.BoxGeometry(0.15, 0.25, 0.75), grey, x, 0, 0.38);
      add(new THREE.BoxGeometry(0.06, 1.2, 0.06), red, x, 0.65, 0.75);
      for (const y of [0.15, 1.2])
        add(new THREE.TorusGeometry(0.33, 0.04, 4, 10), black, x, y, 0.36).rotation.y = Math.PI / 2;
      add(new THREE.BoxGeometry(0.06, 0.4, 0.05), black, x, 1.1, 1.05);
    }
    return g;
  },
};
