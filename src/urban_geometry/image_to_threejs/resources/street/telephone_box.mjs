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
  notes: 'Glazing bars, pediments and fascias modelled; crown reliefs simplified to blocks.',
  build({ THREE, kit, detail = 'high' }) {
    const g = new THREE.Group();
    const red = kit.mat('#c8102e', { roughness: 0.45 });
    const glass = kit.mat('#3c4a55', { roughness: 0.15, metalness: 0.1 });
    const fascia = kit.paintedMaterial('asset:k6:fascia', 128, 32, (c, w, h) => {
      c.fillStyle = '#f4f1e8';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#111';
      c.font = 'bold 18px sans-serif';
      c.textAlign = 'center';
      c.fillText('TELEPHONE', w / 2, 23);
    });
    const add = (geo, m, x = 0, y = 0, z = 0) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    const W = 0.91;
    add(new THREE.BoxGeometry(W + 0.04, W + 0.04, 0.14), red, 0, 0, 0.07);
    if (detail === 'low') {
      add(new THREE.BoxGeometry(0.84, 0.84, 1.95), glass, 0, 0, 1.1);
      add(new THREE.BoxGeometry(0.93, 0.93, 0.3), red, 0, 0, 2.2);
      return g;
    }
    add(new THREE.BoxGeometry(0.8, 0.8, 1.95), glass, 0, 0, 1.1);
    for (const sx of [-1, 1])
      for (const sy of [-1, 1])
        add(new THREE.BoxGeometry(0.11, 0.11, 2.02), red, (sx * W) / 2.15, (sy * W) / 2.15, 1.12);
    // Door and side frames with 8 x 3 small panes (glazing bars) on three faces; back panel solid.
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2;
      const nx = Math.sin(a),
        ny = -Math.cos(a),
        ux = Math.cos(a),
        uy = Math.sin(a);
      const face = (dx, dz, w, h) => {
        const b = add(
          new THREE.BoxGeometry(w, 0.05, h),
          red,
          nx * 0.41 + ux * dx,
          ny * 0.41 + uy * dx,
          dz,
        );
        b.rotation.z = a;
      };
      if (k === 2) {
        face(0, 1.1, 0.72, 1.92);
        continue;
      }
      face(0, 0.2, 0.72, 0.18);
      face(0, 2.0, 0.72, 0.12);
      for (const dx of [-0.36, 0.36]) face(dx, 1.1, 0.06, 1.9);
      for (const dx of [-0.12, 0.12]) face(dx, 1.12, 0.025, 1.6);
      for (let r = 1; r < 8; r++) face(0, 0.32 + r * 0.205, 0.72, 0.025);
      if (k === 0) {
        const hnd = add(
          new THREE.BoxGeometry(0.03, 0.06, 0.3),
          kit.mat('#8a7a5a', { metalness: 0.6, roughness: 0.4 }),
          0.3,
          -0.45,
          1.05,
        );
        hnd.rotation.z = a;
      }
      const f = add(new THREE.BoxGeometry(0.6, 0.02, 0.12), fascia, nx * 0.44, ny * 0.44, 2.2);
      f.rotation.z = a;
      // Crown motif in the pediment, as a gilt-free embossed block.
      const crown = add(new THREE.BoxGeometry(0.14, 0.03, 0.12), red, nx * 0.47, ny * 0.47, 2.43);
      crown.rotation.z = a;
    }
    add(new THREE.BoxGeometry(0.97, 0.97, 0.06), red, 0, 0, 2.12);
    add(new THREE.BoxGeometry(0.95, 0.95, 0.22), red, 0, 0, 2.25);
    // Shallow segmental pediments on each face and the domed roof.
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2;
      const p = add(
        new THREE.CylinderGeometry(0.5, 0.5, 0.06, 16, 1, false, -0.7, 1.4).rotateX(Math.PI / 2),
        red,
        Math.sin(a) * 0.46,
        -Math.cos(a) * 0.46,
        2.08,
      );
      p.rotation.set(Math.PI / 2, 0, a + Math.PI / 2);
    }
    const dome = add(
      new THREE.SphereGeometry(0.62, 16, 6, 0, Math.PI * 2, 0, 0.75).rotateX(Math.PI / 2),
      red,
      0,
      0,
      1.96,
    );
    dome.scale.set(0.75, 0.75, 1);
    return g;
  },
};
