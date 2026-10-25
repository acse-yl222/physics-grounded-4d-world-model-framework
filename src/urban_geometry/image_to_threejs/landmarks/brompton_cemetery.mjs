// Brompton Cemetery (Benjamin Baud, 1839-44), Grade I registered: the octagonal
// domed Anglican chapel of Bath stone with a lead dome (loosely modelled on St
// Peter's, Rome) and its flanking colonnade wings closing the south end of the main
// avenue, the Great Circle of rusticated sandstone arcaded colonnades (about 92 m
// across, backed with brick, catacombs beneath), the avenue colonnades and the long
// Western Catacombs wall.
export default {
  id: 'brompton_cemetery',
  name: 'Brompton Cemetery chapel, Great Circle colonnades and catacombs',
  claims: [
    'bb91a7ce-3c52-4c4b-b7d3-3680eac1fd55', // Brompton Cemetery Chapel with its wings
    '95f15d8a-a4f2-4ad0-a60d-16278479c565', // Great Circle colonnade, west arc + north-west arm
    'a3ff1cea-6445-4452-b2d5-88588811604c', // Great Circle colonnade, north arc + north arm
    'f5362b4a-511f-4b1a-9c9a-12ce770e9f8c', // Great Circle colonnade, east arc + south-east arm
    '23bdbeab-014b-4dcd-aefe-fd7f059e7d9a', // Great Circle colonnade, south arc + south arm
    'c6acc3c6-570f-4038-b8ce-6b9afd0d321d', // Western Catacombs
  ],
  references: [
    {
      title: 'Brompton Cemetery - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Brompton_Cemetery',
      used_for: 'Baud design, domed chapel, colonnades and catacombs, layout',
    },
    {
      title: 'Brompton Cemetery - Historic England',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1000248',
      used_for:
        'octagonal Bath stone chapel with lead dome and Roman Doric pilasters; Great Circle ~92 m; rusticated sandstone arcades backed with brick',
    },
    {
      title: 'Brompton Cemetery - Parks and Gardens UK',
      url: 'https://www.parksandgardens.org/places/brompton-cemetery',
      used_for: 'chapel closing the southern end of the avenue, colonnades',
    },
    {
      title: 'Brompton Cemetery catacombs - Subterranea Britannica',
      url: 'https://www.subbrit.org.uk/sites/brompton-cemetery-catacombs/',
      used_for: 'catacomb vaults beneath the colonnades entered through cast-iron gates',
    },
  ],
  notes:
    'Heights estimated (colonnades 6.5 m with balustraded terrace, chapel drum 12 m, dome crown ~21 m with lantern); ' +
    'Overture heights (6-11 m) ignored. The arcade faces the avenue / circle side and the backs are brick, as in ' +
    'the listing; arch rhythm, portico size and the Western Catacombs treatment are approximate.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    const stoneCol = '#cbb990';
    const stone = kit.mat(stoneCol, { roughness: 0.85 });
    const paleStone = kit.mat('#d8c9a3', { roughness: 0.8 });
    const lead = kit.mat('lead');
    const arcade = kit.paintedMaterial('brompton_cemetery:arcade', 512, 128, (c, w, h) => {
      // 4 arched bays per tile: rusticated sandstone piers, dark open arches,
      // Doric pilasters, entablature.
      c.fillStyle = stoneCol;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(90,70,40,0.35)';
      for (let y = 30; y < h; y += 9) c.fillRect(0, y, w, 2);
      c.fillStyle = '#e0d3b2';
      c.fillRect(0, 0, w, 12);
      c.fillStyle = 'rgba(90,70,40,0.4)';
      c.fillRect(0, 12, w, 3);
      const bw = w / 4;
      for (let i = 0; i < 4; i++) {
        const x = i * bw;
        c.fillStyle = '#d9cba6';
        c.fillRect(x, 15, 10, h - 15);
        const ax = x + 26,
          aw = bw - 42;
        c.fillStyle = '#2b2a27';
        c.fillRect(ax, 58, aw, h - 58);
        c.beginPath();
        c.arc(ax + aw / 2, 58, aw / 2, Math.PI, 0);
        c.fill();
        c.strokeStyle = '#e2d5b4';
        c.lineWidth = 4;
        c.beginPath();
        c.arc(ax + aw / 2, 58, aw / 2 + 2, Math.PI, 0);
        c.stroke();
        c.fillStyle = '#5c5f5e'; // cast-iron gate to the catacomb below
        if (i % 2 === 0)
          for (let k = 0; k < 6; k++) c.fillRect(ax + 4 + (k * (aw - 8)) / 5, h - 30, 2, 30);
      }
    });
    const brickBack = kit.paintedMaterial('brompton_cemetery:back', 256, 128, (c, w, h) => {
      c.fillStyle = '#8d6248';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(40,20,10,0.25)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      c.fillStyle = '#d8c9a3';
      c.fillRect(0, 0, w, 12);
      c.fillRect(0, h - 10, w, 10);
    });

    const chapel = byId['bb91a7ce-3c52-4c4b-b7d3-3680eac1fd55'];
    // Chapel octagon centre: mean of outline vertices within 11 m of the centroid.
    let oc = [794.6, -2574.1];
    if (chapel) {
      const near = chapel.polys[0][0].filter(
        (p) => Math.hypot(p[0] - chapel.c[0], p[1] - chapel.c[1]) < 11,
      );
      if (near.length >= 4)
        oc = [
          near.reduce((s, p) => s + p[0], 0) / near.length,
          near.reduce((s, p) => s + p[1], 0) / near.length,
        ];
    }
    // Great Circle centre and the avenue axis towards the chapel.
    const C = [743, -2503];
    const ax = [oc[0] - C[0], oc[1] - C[1]];
    const al = Math.hypot(...ax);
    const axu = [ax[0] / al, ax[1] / al];
    const facesAvenue = (m, n) => {
      const dC = Math.hypot(m[0] - C[0], m[1] - C[1]);
      if (dC < 50) return n[0] * (C[0] - m[0]) + n[1] * (C[1] - m[1]) > 0;
      // foot of the perpendicular on the avenue axis
      const t = (m[0] - C[0]) * axu[0] + (m[1] - C[1]) * axu[1];
      const f = [C[0] + axu[0] * t, C[1] + axu[1] * t];
      return n[0] * (f[0] - m[0]) + n[1] * (f[1] - m[1]) > 0;
    };

    const colH = 6.5;
    const colonnade = (b, H) => {
      const ring = b.polys[0][0];
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 0.05) continue;
        const n = [(q[1] - p[1]) / len, -(q[0] - p[0]) / len];
        const m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
        const front = len > 3 && facesAvenue(m, n);
        const mat = front ? arcade : brickBack;
        const nb = Math.max(1, Math.round(len / 3.4));
        const u1 = front ? nb / 4 : len / 8;
        batch.quad(
          mat,
          [p[0], p[1], 0],
          [q[0], q[1], 0],
          [q[0], q[1], H],
          [p[0], p[1], H],
          [0, 0],
          [u1, 0],
          [u1, 1],
          [0, 1],
        );
        // cornice and balustrade of the terrace walk on top
        const rot = Math.atan2(q[1] - p[1], q[0] - p[0]);
        addGeo(
          paleStone,
          new THREE.BoxGeometry(len + 0.25, 0.55, 0.5),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition(m[0] + n[0] * 0.1, m[1] + n[1] * 0.1, H + 0.25),
        );
        if (len > 1.5) {
          addGeo(
            paleStone,
            new THREE.BoxGeometry(len, 0.3, 0.16),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(m[0] - n[0] * 0.15, m[1] - n[1] * 0.15, H + 1.35),
          );
          for (let t = 0.6; t < len - 0.3; t += 1.8)
            addGeo(
              paleStone,
              new THREE.BoxGeometry(0.45, 0.3, 0.8),
              new THREE.Matrix4()
                .makeRotationZ(rot)
                .setPosition(
                  p[0] + ((q[0] - p[0]) * t) / len - n[0] * 0.15,
                  p[1] + ((q[1] - p[1]) * t) / len - n[1] * 0.15,
                  H + 0.9,
                ),
            );
        }
      }
      kit.cap(batch, kit.mat('#a99d86', { roughness: 0.95 }), b.polys, H);
    };
    for (const id of [
      '95f15d8a-a4f2-4ad0-a60d-16278479c565',
      'a3ff1cea-6445-4452-b2d5-88588811604c',
      'f5362b4a-511f-4b1a-9c9a-12ce770e9f8c',
      '23bdbeab-014b-4dcd-aefe-fd7f059e7d9a',
    ])
      if (byId[id]) colonnade(byId[id], colH);
    if (byId['c6acc3c6-570f-4038-b8ce-6b9afd0d321d'])
      colonnade(byId['c6acc3c6-570f-4038-b8ce-6b9afd0d321d'], 5.2);

    // Chapel wings (the rest of the chapel outline) as colonnades, then the octagon.
    if (chapel) colonnade(chapel, colH);
    const R = 8.3;
    const drumH = 12.5;
    const octWall = kit.paintedMaterial('brompton_cemetery:octagon', 256, 256, (c, w, h) => {
      c.fillStyle = '#d6c59c';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(100,80,45,0.25)';
      for (let y = 0; y < h; y += 12) c.fillRect(0, y, w, 2);
      c.fillStyle = '#e4d7b7';
      c.fillRect(0, 0, 22, h); // Doric pilasters at the angles
      c.fillRect(w - 22, 0, 22, h);
      c.fillRect(0, 0, w, 26); // entablature
      c.fillStyle = '#2d2c29';
      const ww = 54;
      c.fillRect(w / 2 - ww / 2, 70, ww, 100); // tall round-headed window
      c.beginPath();
      c.arc(w / 2, 70, ww / 2, Math.PI, 0);
      c.fill();
      c.fillStyle = '#e4d7b7';
      c.fillRect(w / 2 - ww / 2 - 6, 170, ww + 12, 8);
    });
    const rot0 = Math.PI / 8 + Math.atan2(axu[1], axu[0]);
    const oct = [];
    for (let k = 0; k < 8; k++) {
      const a = rot0 + (k * Math.PI) / 4;
      oct.push([oc[0] + Math.cos(a) * R, oc[1] + Math.sin(a) * R]);
    }
    for (let k = 0; k < 8; k++) {
      const p = oct[k],
        q = oct[(k + 1) % 8];
      batch.quad(
        octWall,
        [p[0], p[1], 0],
        [q[0], q[1], 0],
        [q[0], q[1], drumH],
        [p[0], p[1], drumH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    const mAt = (x, y, z, r = 0) => new THREE.Matrix4().makeRotationZ(r).setPosition(x, y, z);
    // cornice, attic and dome
    addGeo(
      paleStone,
      new THREE.CylinderGeometry(R * 1.1, R * 1.1, 0.9, 8).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], drumH + 0.45, rot0 - Math.PI / 8 + Math.PI / 8),
    );
    addGeo(
      stone,
      new THREE.CylinderGeometry(R * 0.86, R * 0.9, 2.2, 16).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], drumH + 2.0),
    );
    const dome = new THREE.SphereGeometry(R * 0.86, 20, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
      Math.PI / 2,
    );
    dome.scale(1, 1, 0.85);
    addGeo(lead, dome, mAt(oc[0], oc[1], drumH + 3.1));
    // lantern with small dome and cross
    addGeo(
      paleStone,
      new THREE.CylinderGeometry(1.2, 1.3, 2.4, 8).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], drumH + 3.1 + R * 0.86 * 0.85 + 0.9),
    );
    const lz = drumH + 3.1 + R * 0.86 * 0.85 + 2.1;
    addGeo(
      lead,
      new THREE.SphereGeometry(1.25, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], lz),
    );
    addGeo(kit.mat('#3c3f40'), new THREE.BoxGeometry(0.15, 0.15, 1.6), mAt(oc[0], oc[1], lz + 1.9));
    addGeo(
      kit.mat('#3c3f40'),
      new THREE.BoxGeometry(0.8, 0.15, 0.15),
      mAt(oc[0], oc[1], lz + 2.2, Math.atan2(axu[1], axu[0])),
    );
    // Doric portico facing up the avenue (towards the Great Circle)
    const fx = oc[0] - axu[0] * (R + 2.2),
      fy = oc[1] - axu[1] * (R + 2.2);
    const pr = Math.atan2(axu[1], axu[0]);
    const px = [-axu[1], axu[0]];
    for (const off of [-3.3, -1.1, 1.1, 3.3])
      addGeo(
        paleStone,
        new THREE.CylinderGeometry(0.38, 0.45, 7, 12).rotateX(Math.PI / 2),
        mAt(fx + px[0] * off, fy + px[1] * off, 3.5),
      );
    addGeo(
      paleStone,
      new THREE.BoxGeometry(4.6, 8.4, 1.0),
      mAt(fx + axu[0] * 0.9, fy + axu[1] * 0.9, 7.5, pr),
    );
    const ped = new THREE.Shape([
      new THREE.Vector2(-4.4, 0),
      new THREE.Vector2(4.4, 0),
      new THREE.Vector2(0, 1.9),
    ]);
    const pg = new THREE.ExtrudeGeometry(ped, { depth: 4.2, bevelEnabled: false });
    pg.rotateX(Math.PI / 2);
    pg.rotateZ(Math.PI / 2);
    addGeo(paleStone, pg, mAt(fx - axu[0] * 1.2, fy - axu[1] * 1.2, 8.0, pr));
    addGeo(
      paleStone,
      new THREE.BoxGeometry(4.8, 9.0, 0.5),
      mAt(fx + axu[0] * 0.9, fy + axu[1] * 0.9, 0.25, pr),
    );

    g.add(batch.toGroup('brompton_cemetery'));
    return g;
  },
};
