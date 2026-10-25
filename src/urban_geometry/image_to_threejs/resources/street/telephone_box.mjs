// K6 telephone kiosk (Giles Gilbert Scott, 1935): cast iron, Post Office red,
// ~0.91 m square, 2.51 m tall, shallow domed roof with crowns in the pediments,
// glazed in 8 x 3 small panes on three sides, white TELEPHONE fascias.
export default {
  id: 'telephone_box',
  kind: 'street',
  name: 'K6 telephone kiosk',
  size: [0.91, 0.91, 2.51],
  references: [
    {
      title: 'Post Office telephone kiosk No. 6 - Science Museum Group',
      url: 'https://collection.sciencemuseum.org.uk/objects/co33578/post-office-telephone-kiosk-no-6-1936-1968-telephone-box',
      used_for: 'K6 design and date',
    },
    {
      title: 'K6 Telephone Box - Timberscombe',
      url: 'https://timberscombevillage.com/k6-telephone-box/',
      used_for: 'height 8 ft 3 in (2.51 m)',
    },
    {
      title: 'RBKC listed building description',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=1415684',
      used_for: 'three feet square plan, shallow domed roof, cast iron painted red',
    },
  ],
  notes: 'Pane glazing drawn as texture; crown reliefs omitted.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const red = kit.mat('#c8102e', { roughness: 0.45 });
    const panes = kit.paintedMaterial(
      'asset:k6:panes',
      64,
      192,
      (c, w, h) => {
        c.fillStyle = '#c8102e';
        c.fillRect(0, 0, w, h);
        for (let r = 0; r < 8; r++)
          for (let k = 0; k < 3; k++) {
            c.fillStyle = r % 3 ? '#3c4a55' : '#4a5a66';
            c.fillRect(6 + k * 18, 8 + r * 22, 15, 19);
          }
      },
      { roughness: 0.3 },
    );
    const fascia = kit.paintedMaterial('asset:k6:fascia', 128, 32, (c, w, h) => {
      c.fillStyle = '#f4f1e8';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#111';
      c.font = 'bold 18px sans-serif';
      c.textAlign = 'center';
      c.fillText('TELEPHONE', w / 2, 23);
    });
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    add(new THREE.BoxGeometry(0.95, 0.95, 0.14), red, 0, 0, 0.07);
    add(new THREE.BoxGeometry(0.84, 0.84, 1.95), panes, 0, 0, 1.1);
    for (const sx of [-1, 1])
      for (const sy of [-1, 1])
        add(new THREE.BoxGeometry(0.1, 0.1, 2.0), red, sx * 0.43, sy * 0.43, 1.1);
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2;
      const f = add(
        new THREE.BoxGeometry(0.62, 0.02, 0.13),
        fascia,
        Math.sin(a) * 0.43,
        -Math.cos(a) * 0.43,
        2.18,
      );
      f.rotation.z = a;
    }
    add(new THREE.BoxGeometry(0.93, 0.93, 0.18), red, 0, 0, 2.2);
    const dome = add(
      new THREE.SphereGeometry(0.62, 12, 4, 0, Math.PI * 2, 0, 0.75).rotateX(Math.PI / 2),
      red,
      0,
      0,
      1.96,
    );
    dome.scale.set(0.75, 0.75, 1);
    return g;
  },
};
