// London bus stop: red roundel flag on a pole plus a glazed shelter with a dark
// grey frame, roof canopy and advertising panel; faces the kerb (+y).
export default {
  id: 'bus_stop',
  kind: 'street',
  name: 'Bus stop with shelter',
  size: [3.6, 1.6, 2.9],
  references: [
    {
      title: 'TfL Accessible Bus Stop Design Guidance (copy)',
      url: 'https://www.slideshare.net/slideshow/busstopaccessible-designguidancepdf/256817600',
      used_for: 'stop elements: post and flag, shelter, kerb',
    },
    {
      title: 'Surrey bus stop technical specifications',
      url: 'https://www.surreycc.gov.uk/land-planning-and-development/healthy-streets/requirements-and-guidance/section?id=12.7',
      used_for: 'clear area between flag and shelter',
    },
  ],
  notes: 'Overture records the stop, not whether it has a shelter; every stop gets one.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const frame = kit.mat('#3a3f44', { roughness: 0.5, metalness: 0.4 });
    const glass = kit.mat('#a9c2cf', { transparent: true, opacity: 0.35, roughness: 0.1 });
    const add = (geo, m, x, y, z) => {
      const o = new THREE.Mesh(geo, m);
      o.position.set(x, y, z);
      g.add(o);
      return o;
    };
    for (const x of [-1.2, 1.2])
      for (const y of [-0.5, 0.4]) add(new THREE.BoxGeometry(0.06, 0.06, 2.45), frame, x, y, 1.23);
    add(new THREE.BoxGeometry(2.6, 1.3, 0.08), frame, 0, -0.05, 2.5);
    add(new THREE.BoxGeometry(2.4, 0.02, 2.0), glass, 0, -0.5, 1.2);
    const ad = kit.paintedMaterial(
      'asset:bus_stop:ad',
      64,
      128,
      (c, w, h) => {
        const gr = c.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#f2f2f2');
        gr.addColorStop(1, '#5d87a8');
        c.fillStyle = gr;
        c.fillRect(0, 0, w, h);
      },
      { emissive: new THREE.Color('#222'), roughness: 0.3 },
    );
    add(new THREE.BoxGeometry(0.08, 1.3, 1.9), ad, 1.25, -0.05, 1.15);
    add(new THREE.BoxGeometry(1.6, 0.35, 0.05), kit.mat('timber'), -0.3, -0.35, 0.5);
    add(
      new THREE.CylinderGeometry(0.04, 0.04, 2.9, 6).rotateX(Math.PI / 2),
      frame,
      -1.8,
      0.6,
      1.45,
    );
    const flag = kit.paintedMaterial('asset:bus_stop:flag', 64, 64, (c, w, h) => {
      c.fillStyle = '#f5f5f5';
      c.fillRect(0, 0, w, h);
      c.strokeStyle = '#dc241f';
      c.lineWidth = 9;
      c.beginPath();
      c.arc(w / 2, h / 2, 20, 0, Math.PI * 2);
      c.stroke();
      c.fillStyle = '#0019a8';
      c.fillRect(6, h / 2 - 6, w - 12, 12);
    });
    add(new THREE.BoxGeometry(0.03, 0.5, 0.5), flag, -1.8, 0.85, 2.6);
    return g;
  },
};
