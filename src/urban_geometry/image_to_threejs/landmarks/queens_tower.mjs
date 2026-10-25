// Queen's Tower, Imperial College South Kensington (T. E. Collcutt, 1887-1893).
// 87 m Neo-Renaissance campanile in Portland stone with red brick bands, the
// sole surviving part of the Imperial Institute. Square shaft with quoins and
// banded courses, an open arcaded belfry stage with paired round arches and
// balconies, then an octagonal lantern under a copper-green dome and cupola.
export default {
  id: 'queens_tower',
  name: "Queen's Tower",
  claims: ['75b30aaa-f0c6-43f7-b5c7-9b93db7dab9e'],
  references: [
    {
      title: "Queen's Tower, London - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Queen%27s_Tower,_London',
      used_for: 'height 87 m, Portland stone cladding, copper-covered dome',
    },
    {
      title: "Queen's Tower - Imperial College history",
      url: 'https://www.imperial.ac.uk/about/history/queens-tower/',
      used_for: 'Collcutt neo-renaissance design, belfry and dome stages',
    },
    {
      title: "Queen's Tower - British Listed Buildings",
      url: 'https://britishlistedbuildings.co.uk/101231643-queens-tower-knightsbridge-and-belgravia-ward',
      used_for: 'listing description: Portland stone with red brick bands, copper dome',
    },
  ],
  notes: 'Footprint orientation from the Overture outline; stage heights proportioned from photos.',
  build({ THREE, kit, frame }) {
    const g = new THREE.Group();
    const brick = kit.mat('red_brick'),
      stone = kit.mat('portland_stone'),
      copper = kit.mat('copper_green'),
      dark = kit.mat('dark_glass');
    const W = Math.min(frame.width, 14.5);
    const add = (geo, m, x, y, z) => {
      const mesh = new THREE.Mesh(geo, m);
      mesh.position.set(x, y, z);
      g.add(mesh);
      return mesh;
    };
    // Portland stone shaft with red brick bands every 3 m.
    add(new THREE.BoxGeometry(W + 1.2, W + 1.2, 4), stone, 0, 0, 2);
    add(new THREE.BoxGeometry(W, W, 50), stone, 0, 0, 29);
    for (let z = 6; z < 53; z += 3)
      add(new THREE.BoxGeometry(W + 0.08, W + 0.08, 1.1), brick, 0, 0, z);
    // Stone quoins at the corners.
    for (const sx of [-1, 1])
      for (const sy of [-1, 1])
        add(new THREE.BoxGeometry(1.4, 1.4, 50), stone, (sx * W) / 2, (sy * W) / 2, 29);
    // Narrow slit windows on each face of the shaft.
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2;
      for (let z = 14; z < 50; z += 12) {
        const w = add(
          new THREE.BoxGeometry(1.1, 0.2, 3.5),
          dark,
          Math.sin(a) * (W / 2 + 0.05),
          -Math.cos(a) * (W / 2 + 0.05),
          z,
        );
        w.rotation.z = a;
      }
    }
    // Belfry: stone stage with paired round-arched openings and a balcony cornice.
    add(new THREE.BoxGeometry(W + 2.2, W + 2.2, 1.2), stone, 0, 0, 54.6);
    add(new THREE.BoxGeometry(W, W, 12), stone, 0, 0, 61);
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2;
      for (const off of [-W / 4.2, W / 4.2]) {
        const arch = new THREE.Group();
        const open = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.2, 7), dark);
        open.position.z = 3.5;
        const top = new THREE.Mesh(
          new THREE.CylinderGeometry(1.3, 1.3, 1.2, 16, 1, false, 0, Math.PI),
          dark,
        );
        top.rotation.x = Math.PI / 2;
        top.rotation.y = Math.PI / 2;
        top.position.z = 7;
        arch.add(open, top);
        arch.position.set(
          Math.sin(a) * (W / 2) + Math.cos(a) * off,
          -Math.cos(a) * (W / 2) + Math.sin(a) * off,
          56,
        );
        arch.rotation.z = a;
        g.add(arch);
      }
    }
    add(new THREE.BoxGeometry(W + 2.6, W + 2.6, 1.4), stone, 0, 0, 67.7);
    // Corner pinnacles around the lantern stage.
    for (const sx of [-1, 1])
      for (const sy of [-1, 1]) {
        add(
          new THREE.CylinderGeometry(0.9, 0.9, 5, 8).rotateX(Math.PI / 2),
          stone,
          (sx * W) / 2.3,
          (sy * W) / 2.3,
          70.9,
        );
        add(
          new THREE.ConeGeometry(1.1, 3.4, 8).rotateX(Math.PI / 2),
          copper,
          (sx * W) / 2.3,
          (sy * W) / 2.3,
          75.1,
        );
      }
    // Octagonal lantern, copper dome and cupola.
    const lantern = add(
      new THREE.CylinderGeometry(W * 0.36, W * 0.38, 8, 8).rotateX(Math.PI / 2),
      stone,
      0,
      0,
      72.4,
    );
    lantern.rotation.z = Math.PI / 8;
    const dome = add(
      new THREE.SphereGeometry(W * 0.36, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      ),
      copper,
      0,
      0,
      76.4,
    );
    dome.scale.z = 1.35;
    add(new THREE.CylinderGeometry(1.2, 1.4, 3.2, 8).rotateX(Math.PI / 2), copper, 0, 0, 83.4);
    add(new THREE.SphereGeometry(1.25, 12, 8).rotateX(Math.PI / 2), copper, 0, 0, 85.4);
    add(
      new THREE.CylinderGeometry(0.12, 0.12, 2, 6).rotateX(Math.PI / 2),
      kit.mat('gold'),
      0,
      0,
      87,
    );
    g.position.set(frame.cx, frame.cy, 0);
    g.rotation.z = frame.angle;
    return g;
  },
};
