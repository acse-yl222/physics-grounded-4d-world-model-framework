// LEVC TX London taxi: tall upright body (4.86 x 1.87 x 1.89 m, 2.99 m wheelbase),
// black, large rounded glasshouse, yellow TAXI roof sign. Front faces +y.
export default {
  id: 'black_cab',
  kind: 'vehicle',
  name: 'London taxi (LEVC TX)',
  size: [1.87, 4.86, 1.89],
  references: [
    {
      title: 'LEVC TX - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/LEVC_TX',
      used_for: 'length 4857 mm, width 1874 mm, height 1888 mm, wheelbase 2986 mm',
    },
    {
      title: 'LEVC TX review - CAR magazine',
      url: 'https://carmagazine.co.uk/car-reviews/levc/levc-tx-review-londons-new-electric-black-taxi-cab-driven',
      used_for: 'body form and roof sign',
    },
  ],
  notes:
    'Not placed by the default build: there is no recorded vehicle position data for this scene.',
  build({ THREE, kit }) {
    return vehicle(THREE, kit, {
      L: 4.86,
      W: 1.87,
      H: 1.89,
      wb: 2.99,
      body: '#16181a',
      cabin: 0.72,
      sign: '#f4c400',
    });
  },
};

function vehicle(THREE, kit, o) {
  const g = new THREE.Group();
  const body = kit.mat(o.body, { roughness: 0.35, metalness: 0.4 });
  const glass = kit.mat('dark_glass');
  const tyre = kit.mat('#141414');
  const add = (geo, m, x, y, z) => {
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(x, y, z);
    g.add(mesh);
    return mesh;
  };
  add(new THREE.BoxGeometry(o.W, o.L, o.H * 0.5), body, 0, 0, 0.3 + o.H * 0.25);
  add(
    new THREE.BoxGeometry(o.W * 0.96, o.L * o.cabin, o.H * 0.42),
    glass,
    0,
    -o.L * 0.06,
    0.3 + o.H * 0.71,
  );
  add(new THREE.BoxGeometry(o.W * 0.94, o.L * o.cabin * 0.95, 0.06), body, 0, -o.L * 0.06, o.H);
  add(
    new THREE.BoxGeometry(o.W * 0.6, 0.05, 0.2),
    kit.mat('#e9e7df', { emissive: new THREE.Color('#ccc'), emissiveIntensity: 0.3 }),
    0,
    o.L / 2,
    0.75,
  );
  if (o.sign)
    add(
      new THREE.BoxGeometry(0.5, 0.18, 0.14),
      kit.mat(o.sign, { emissive: new THREE.Color(o.sign), emissiveIntensity: 0.4 }),
      0,
      0.2,
      o.H + 0.1,
    );
  for (const x of [-o.W / 2 + 0.12, o.W / 2 - 0.12])
    for (const y of [-o.wb / 2, o.wb / 2]) {
      const w = add(new THREE.CylinderGeometry(0.36, 0.36, 0.24, 12), tyre, x, y, 0.36);
      w.rotation.z = Math.PI / 2;
    }
  return g;
}
