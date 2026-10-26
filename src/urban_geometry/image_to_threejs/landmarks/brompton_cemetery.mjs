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
        'octagonal Bath stone chapel with lead dome and Roman Doric pilasters, porch projecting north-west with coupled columns, single-storey wings; Great Circle ~92 m; rusticated sandstone arcades backed with brick',
    },
    {
      title: 'Brompton Cemetery - Parks and Gardens UK',
      url: 'https://www.parksandgardens.org/places/brompton-cemetery',
      used_for: 'chapel closing the southern end of the avenue, colonnades',
    },
    {
      title: 'Brompton Cemetery chapel - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=422205',
      used_for: 'Baud 1839-40 chapel; lower flanking blocks with niches',
    },
    {
      title: 'Brompton Cemetery - Victorian Web',
      url: 'https://victorianweb.org/art/parks/brompton/2.html',
      used_for: 'chapel wings housing the cemetery offices, not prominent from the front',
    },
    {
      title: 'Brompton Cemetery catacombs - Subterranea Britannica',
      url: 'https://www.subbrit.org.uk/sites/brompton-cemetery-catacombs/',
      used_for: 'catacomb vaults beneath the colonnades entered through cast-iron gates',
    },
  ],
  notes:
    'Heights estimated (colonnades 6.5 m with balustraded terrace, chapel drum 12.5 m, dome crown ~22 m with lantern); ' +
    'Overture heights (6-11 m) ignored. Arcade fronts are real geometry: rusticated sandstone faces with round-arched ' +
    'openings at ~3.4 m bays, Doric pilasters, imposts, keystones, entablature, cornice and turned-baluster terrace ' +
    'balustrades; the walk behind has a ceiling and the backs are brick, as in the listing. Cast-iron catacomb gates ' +
    'are put in every fourth bay and every Western Catacombs bay (actual gate positions unknown). Chapel: octagon with ' +
    'Doric angle pilasters, round-headed windows, ribbed lead dome, colonnetted lantern and a north-west porch of ' +
    'coupled Doric columns with pediment and steps (column count, rib count and dimensions approximate). About 800 ' +
    'seeded monuments (headstones, crosses, chest tombs, obelisks) are scattered off the paths within 150 m of the ' +
    'Great Circle - illustrative only, not surveyed graves; benches from resources/ stand along the colonnades.',
  build(ctx) {
    const { THREE, kit, byId, scene } = ctx;
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
    const rustic = kit.paintedMaterial('brompton_cemetery:rustic', 256, 256, (c, w, h) => {
      // 2 m tile: rusticated sandstone courses 0.5 m high with deep joints.
      c.fillStyle = stoneCol;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(1839);
      for (let row = 0; row < 4; row++)
        for (let k = -1; k < 3; k++) {
          const x = k * 128 + (row % 2) * 64;
          const t = r();
          c.fillStyle = `rgba(${190 + t * 30},${170 + t * 25},${125 + t * 20},1)`;
          c.fillRect(x + 4, row * 64 + 5, 120, 54);
        }
      c.fillStyle = 'rgba(90,70,40,0.45)';
      for (let row = 0; row <= 4; row++) c.fillRect(0, row * 64 - 2, w, 5);
    });
    const darkStone = kit.mat('#6d6656', { roughness: 0.95 });
    const paving = kit.mat('#b9ad90', { roughness: 0.95 });
    const iron = kit.mat('#2e3230', { roughness: 0.5, metalness: 0.5 });
    const arcBays = []; // [x, y, rot] of every arcade opening, for gates
    const colonnade = (b, H, { gates = 0.25, balus = true } = {}) => {
      const ring = b.polys[0][0];
      const spring = H * 0.62,
        bayW = 3.4;
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 0.05) continue;
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len;
        const n = [uy, -ux];
        const m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
        const rot = Math.atan2(uy, ux);
        const facing = facesAvenue(m, n);
        const front = len > 2.6 && facing;
        if (!front) {
          const u1 = len / 8;
          if (facing) {
            batch.quad(
              rustic,
              [p[0], p[1], 0],
              [q[0], q[1], 0],
              [q[0], q[1], H],
              [p[0], p[1], H],
              [0, 0],
              [len / 2, 0],
              [len / 2, H / 2],
              [0, H / 2],
            );
            continue;
          }
          batch.quad(
            brickBack,
            [p[0], p[1], 0],
            [q[0], q[1], 0],
            [q[0], q[1], H],
            [p[0], p[1], H],
            [0, 0],
            [u1, 0],
            [u1, 1],
            [0, 1],
          );
          // inner face of the back wall, seen through the arcade
          const ip = [p[0] - n[0] * 0.5, p[1] - n[1] * 0.5],
            iq = [q[0] - n[0] * 0.5, q[1] - n[1] * 0.5];
          batch.quad(
            darkStone,
            [iq[0], iq[1], 0],
            [ip[0], ip[1], 0],
            [ip[0], ip[1], H - 0.5],
            [iq[0], iq[1], H - 0.5],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          if (len > 1.2 && balus)
            addGeo(
              paleStone,
              new THREE.BoxGeometry(len, 0.35, 0.9),
              new THREE.Matrix4()
                .makeRotationZ(rot)
                .setPosition(m[0] - n[0] * 0.2, m[1] - n[1] * 0.2, H + 0.5 + 0.45),
            );
          continue;
        }
        // Arcade face: rusticated wall with arched openings, extruded 0.8 m.
        const nb = Math.max(1, Math.round(len / bayW));
        const bl = len / nb,
          ow = Math.min(2.1, bl - 1.0);
        const sh = new THREE.Shape();
        sh.moveTo(0, 0);
        sh.lineTo(len, 0);
        sh.lineTo(len, H);
        sh.lineTo(0, H);
        sh.closePath();
        for (let i = 0; i < nb; i++) {
          const c0 = bl * (i + 0.5);
          const hole = new THREE.Path();
          hole.moveTo(c0 - ow / 2, 0.45);
          hole.lineTo(c0 + ow / 2, 0.45);
          hole.lineTo(c0 + ow / 2, spring);
          hole.absarc(c0, spring, ow / 2, 0, Math.PI, false);
          hole.lineTo(c0 - ow / 2, 0.45);
          sh.holes.push(hole);
          arcBays.push([p[0] + ux * c0, p[1] + uy * c0, rot, ow, spring, i]);
        }
        const geo = new THREE.ExtrudeGeometry(sh, {
          depth: 0.8,
          bevelEnabled: false,
          curveSegments: 5,
        });
        const uv = geo.attributes.uv;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) / 2, uv.getY(i) / 2);
        const basis = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(ux, uy, 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(n[0], n[1], 0),
        );
        basis.setPosition(p[0] - n[0] * 0.8, p[1] - n[1] * 0.8, 0);
        addGeo(rustic, geo, basis);
        // Doric pilasters on the piers, impost band, keystones
        for (let i = 0; i <= nb; i++) {
          const t = bl * i;
          addGeo(
            paleStone,
            new THREE.BoxGeometry(0.55, 0.16, H - 1.4),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(
                p[0] + ux * t + n[0] * 0.08,
                p[1] + uy * t + n[1] * 0.08,
                0.45 + (H - 1.4) / 2,
              ),
          );
          addGeo(
            paleStone,
            new THREE.BoxGeometry(0.75, 0.24, 0.25),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(p[0] + ux * t + n[0] * 0.1, p[1] + uy * t + n[1] * 0.1, H - 0.95 + 0.12),
          );
        }
        for (let i = 0; i < nb; i++) {
          const c0 = bl * (i + 0.5);
          addGeo(
            paleStone,
            new THREE.BoxGeometry(0.45, 0.2, 0.7),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(
                p[0] + ux * c0 + n[0] * 0.08,
                p[1] + uy * c0 + n[1] * 0.08,
                spring + ow / 2 + 0.25,
              ),
          );
          const arch = new THREE.TorusGeometry(ow / 2 + 0.12, 0.12, 4, 8, Math.PI);
          addGeo(
            paleStone,
            arch,
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
              .setPosition(p[0] + ux * c0 + n[0] * 0.05, p[1] + uy * c0 + n[1] * 0.05, spring),
          );
        }
        addGeo(
          paleStone,
          new THREE.BoxGeometry(len, 0.3, 0.22),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition(m[0] + n[0] * 0.05, m[1] + n[1] * 0.05, spring - 0.11),
        );
        // walk floor inside
        if (balus)
          kit.balustrade(
            batch,
            paleStone,
            [
              [p[0] + n[0] * 0.05, p[1] + n[1] * 0.05],
              [q[0] + n[0] * 0.05, q[1] + n[1] * 0.05],
            ],
            H + 0.5,
            { height: 0.95, spacing: 0.42 },
          );
        // balustrade pedestals at pier positions
        if (balus)
          for (let i = 0; i <= nb; i += 2) {
            const t = bl * i;
            addGeo(
              paleStone,
              new THREE.BoxGeometry(0.6, 0.6, 1.05),
              new THREE.Matrix4()
                .makeRotationZ(rot)
                .setPosition(
                  p[0] + ux * t + n[0] * 0.05,
                  p[1] + uy * t + n[1] * 0.05,
                  H + 0.5 + 0.52,
                ),
            );
          }
      }
      // entablature: frieze band and projecting cornice; roof terrace, walk ceiling, floor
      kit.cornice(batch, paleStone, ring, H - 0.7, { height: 0.25, projection: 0.15 });
      kit.cornice(batch, paleStone, ring, H, { height: 0.5, projection: 0.35, steps: 2 });
      kit.cap(batch, kit.mat('#a99d86', { roughness: 0.95 }), b.polys, H + 0.5);
      kit.cap(batch, darkStone, b.polys, H - 0.5, { down: true });
      kit.cap(batch, paving, b.polys, 0.45);
      gateRule.push(gates);
    };
    const gateRule = [];
    for (const id of [
      '95f15d8a-a4f2-4ad0-a60d-16278479c565',
      'a3ff1cea-6445-4452-b2d5-88588811604c',
      'f5362b4a-511f-4b1a-9c9a-12ce770e9f8c',
      '23bdbeab-014b-4dcd-aefe-fd7f059e7d9a',
    ])
      if (byId[id]) colonnade(byId[id], colH);
    // Cast-iron catacomb gates in a share of the colonnade bays.
    const gate = (x, y, rot, ow, spring) => {
      const M = (dx, z, w, d, h) =>
        addGeo(
          iron,
          new THREE.BoxGeometry(w, d, h),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition(x + Math.cos(rot) * dx, y + Math.sin(rot) * dx, z + h / 2),
        );
      for (let k = 0; k <= 7; k++)
        M(-ow / 2 + 0.1 + (k * (ow - 0.2)) / 7, 0.45, 0.04, 0.04, spring - 0.6);
      M(0, 0.6, ow - 0.1, 0.05, 0.06);
      M(0, spring - 0.6, ow - 0.1, 0.05, 0.06);
      M(0, 1.9, ow - 0.1, 0.04, 0.05);
    };
    const nColBays = arcBays.length;
    for (const [x, y, rot, ow, spring, i] of arcBays) if (i % 4 === 1) gate(x, y, rot, ow, spring);
    if (byId['c6acc3c6-570f-4038-b8ce-6b9afd0d321d']) {
      const start = arcBays.length;
      colonnade(byId['c6acc3c6-570f-4038-b8ce-6b9afd0d321d'], 5.2, { balus: false });
      for (const [x, y, rot, ow, spring] of arcBays.slice(start)) gate(x, y, rot, ow, spring);
    }

    // Chapel wings (the rest of the chapel outline) as colonnades, then the octagon.
    if (chapel) colonnade(chapel, colH);
    const R = 8.3;
    const drumH = 12.5;
    const bath = kit.mat('#d6c59c', { roughness: 0.8 });
    const rot0 = Math.PI / 8 + Math.atan2(axu[1], axu[0]);
    const oct = [];
    for (let k = 0; k < 8; k++) {
      const a = rot0 + (k * Math.PI) / 4;
      oct.push([oc[0] + Math.cos(a) * R, oc[1] + Math.sin(a) * R]);
    }
    kit.walls(batch, bath, [[oct]], 0, drumH, { bay: 1e6 });
    kit.cornice(batch, paleStone, oct, 0, { height: 0.9, projection: 0.3 });
    kit.cornice(batch, paleStone, oct, 5.0, { height: 0.3, projection: 0.12 });
    kit.cornice(batch, paleStone, oct, drumH - 1.4, { height: 0.9, projection: 0.15 }); // frieze
    kit.cornice(batch, paleStone, oct, drumH - 0.5, { height: 0.9, projection: 0.6, steps: 3 });
    const mAt = (x, y, z, r = 0) => new THREE.Matrix4().makeRotationZ(r).setPosition(x, y, z);
    for (let k = 0; k < 8; k++) {
      const p = oct[k],
        q = oct[(k + 1) % 8];
      // Roman Doric pilasters at the angles (listing)
      const a = Math.atan2(p[1] - oc[1], p[0] - oc[0]);
      addGeo(
        paleStone,
        new THREE.BoxGeometry(0.5, 1.4, drumH - 2.3),
        mAt(p[0] + Math.cos(a) * 0.2, p[1] + Math.sin(a) * 0.2, 0.9 + (drumH - 2.3) / 2, a),
      );
      addGeo(
        paleStone,
        new THREE.BoxGeometry(0.7, 1.6, 0.35),
        mAt(p[0] + Math.cos(a) * 0.22, p[1] + Math.sin(a) * 0.22, drumH - 1.75, a),
      );
      // tall round-headed window on each face, except the portico face (door)
      const mid = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
      const toC = Math.hypot(mid[0] - oc[0] + axu[0] * R, mid[1] - oc[1] + axu[1] * R);
      if (toC < 2) continue;
      kit.windowRow(batch, p, q, 5.6, {
        count: 1,
        width: 1.7,
        height: 3.6,
        head: 'arch',
        bars: 2,
        margin: 0,
        surround: 0.25,
        surroundMat: paleStone,
        frame: kit.mat('#5a5850'),
        sill: paleStone,
        glass: kit.mat('#2d3236', { roughness: 0.2 }),
      });
      kit.windowRow(batch, p, q, 1.6, {
        count: 1,
        width: 1.3,
        height: 2.2,
        head: 'segment',
        bars: 1,
        margin: 0,
        frame: kit.mat('#5a5850'),
        sill: paleStone,
        glass: kit.mat('#2d3236', { roughness: 0.2 }),
      });
    }
    // attic drum, lead dome with ribs, lantern with colonnette ring, cross
    addGeo(
      stone,
      new THREE.CylinderGeometry(R * 0.86, R * 0.9, 2.2, 24).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], drumH + 0.4 + 1.1),
    );
    addGeo(
      paleStone,
      new THREE.CylinderGeometry(R * 0.93, R * 0.93, 0.35, 24).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], drumH + 2.6 + 0.17),
    );
    const dR = R * 0.86,
      dS = 0.85,
      dz0 = drumH + 3.0;
    const dome = new THREE.SphereGeometry(dR, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
      Math.PI / 2,
    );
    dome.scale(1, 1, dS);
    addGeo(lead, dome, mAt(oc[0], oc[1], dz0));
    for (let k = 0; k < 8; k++) {
      const a = rot0 + (k * Math.PI) / 4;
      for (let j = 0; j < 8; j++) {
        const t0 = (j / 8) * (Math.PI / 2) * 0.9,
          t1 = ((j + 1) / 8) * (Math.PI / 2) * 0.9;
        const P = (t) => [
          oc[0] + Math.cos(a) * (dR + 0.08) * Math.cos(t),
          oc[1] + Math.sin(a) * (dR + 0.08) * Math.cos(t),
          dz0 + (dR + 0.08) * dS * Math.sin(t),
        ];
        const A0 = P(t0),
          A1 = P(t1);
        const len = Math.hypot(A1[0] - A0[0], A1[1] - A0[1], A1[2] - A0[2]);
        const dir = new THREE.Vector3(A1[0] - A0[0], A1[1] - A0[1], A1[2] - A0[2]).normalize();
        const geo = new THREE.BoxGeometry(0.28, 0.28, len + 0.05);
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
        const mm = new THREE.Matrix4().compose(
          new THREE.Vector3((A0[0] + A1[0]) / 2, (A0[1] + A1[1]) / 2, (A0[2] + A1[2]) / 2),
          q,
          new THREE.Vector3(1, 1, 1),
        );
        addGeo(kit.mat('#6d7478', { roughness: 0.6, metalness: 0.3 }), geo, mm);
      }
    }
    const lz0 = dz0 + dR * dS - 0.2;
    addGeo(
      paleStone,
      new THREE.CylinderGeometry(1.5, 1.6, 0.4, 12).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], lz0 + 0.2),
    );
    addGeo(
      stone,
      new THREE.CylinderGeometry(0.95, 0.95, 2.2, 12).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], lz0 + 0.4 + 1.1),
    );
    for (let k = 0; k < 8; k++) {
      const a = rot0 + (k * Math.PI) / 4;
      addGeo(
        paleStone,
        new THREE.CylinderGeometry(0.11, 0.13, 2.0, 6).rotateX(Math.PI / 2),
        mAt(oc[0] + Math.cos(a) * 1.25, oc[1] + Math.sin(a) * 1.25, lz0 + 0.4 + 1.0),
      );
    }
    addGeo(
      paleStone,
      new THREE.CylinderGeometry(1.45, 1.45, 0.35, 12).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], lz0 + 2.6 + 0.17),
    );
    const lz = lz0 + 2.95;
    addGeo(
      lead,
      new THREE.SphereGeometry(1.3, 12, 5, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2),
      mAt(oc[0], oc[1], lz),
    );
    addGeo(kit.mat('gold'), new THREE.SphereGeometry(0.25, 8, 5), mAt(oc[0], oc[1], lz + 1.45));
    addGeo(kit.mat('#3c3f40'), new THREE.BoxGeometry(0.15, 0.15, 1.6), mAt(oc[0], oc[1], lz + 2.4));
    addGeo(
      kit.mat('#3c3f40'),
      new THREE.BoxGeometry(0.8, 0.15, 0.15),
      mAt(oc[0], oc[1], lz + 2.7, Math.atan2(axu[1], axu[0]) + Math.PI / 2),
    );
    // Porch projecting north-west up the avenue, with coupled Doric columns (listing).
    const pr = Math.atan2(axu[1], axu[0]);
    const px = [-axu[1], axu[0]];
    const fx = oc[0] - axu[0] * (R + 2.6),
      fy = oc[1] - axu[1] * (R + 2.6);
    const P2 = (along, side, z) => [
      fx + axu[0] * along + px[0] * side,
      fy + axu[1] * along + px[1] * side,
      z,
    ];
    const colH2 = 7.2;
    for (const off of [-3.5, -2.6, 2.6, 3.5])
      for (const along of [-0.6, 1.8]) {
        const [x, y] = P2(along, off, 0);
        addGeo(
          paleStone,
          new THREE.CylinderGeometry(0.34, 0.4, colH2 - 0.7, 14).rotateX(Math.PI / 2),
          mAt(x, y, 1.0 + 0.3 + (colH2 - 0.7) / 2),
        );
        addGeo(paleStone, new THREE.BoxGeometry(0.95, 0.95, 0.3), mAt(x, y, 1.0 + 0.15, pr));
        addGeo(
          paleStone,
          new THREE.CylinderGeometry(0.52, 0.4, 0.25, 14).rotateX(Math.PI / 2),
          mAt(x, y, 1.0 + colH2 - 0.25),
        );
        addGeo(paleStone, new THREE.BoxGeometry(1.0, 1.0, 0.18), mAt(x, y, 1.0 + colH2 + 0.04, pr));
      }
    // podium with steps, entablature (architrave, triglyph frieze, cornice), pediment
    addGeo(paleStone, new THREE.BoxGeometry(5.2, 9.4, 1.0), mAt(...P2(0.6, 0, 0.5), pr));
    for (let k = 0; k < 4; k++)
      addGeo(
        paleStone,
        new THREE.BoxGeometry(0.4, 6.0, 0.25 * (k + 1)),
        mAt(...P2(-2.6 - (3 - k) * 0.4, 0, 0.125 * (k + 1)), pr),
      );
    const ez = 1.0 + colH2 + 0.13;
    addGeo(paleStone, new THREE.BoxGeometry(4.6, 8.4, 0.6), mAt(...P2(0.6, 0, ez + 0.3), pr));
    addGeo(stone, new THREE.BoxGeometry(4.5, 8.3, 0.7), mAt(...P2(0.6, 0, ez + 0.95), pr));
    for (let k = -6; k <= 6; k++)
      addGeo(
        paleStone,
        new THREE.BoxGeometry(0.1, 0.32, 0.6),
        mAt(...P2(-1.66, k * 0.64, ez + 0.95), pr),
      );
    addGeo(paleStone, new THREE.BoxGeometry(5.0, 9.0, 0.35), mAt(...P2(0.6, 0, ez + 1.47), pr));
    const ped = new THREE.Shape([
      new THREE.Vector2(-4.5, 0),
      new THREE.Vector2(4.5, 0),
      new THREE.Vector2(0, 1.9),
    ]);
    const pg = new THREE.ExtrudeGeometry(ped, { depth: 4.8, bevelEnabled: false });
    pg.rotateX(Math.PI / 2);
    pg.rotateZ(Math.PI / 2);
    addGeo(paleStone, pg, mAt(...P2(-1.8, 0, ez + 1.64), pr));
    // door in the octagon face behind the porch
    addGeo(
      kit.mat('#4a3a2a', { roughness: 0.6 }),
      new THREE.BoxGeometry(0.12, 2.0, 3.6),
      mAt(...P2(2.62, 0, 1.0 + 1.8), pr),
    );
    addGeo(paleStone, new THREE.BoxGeometry(0.2, 2.6, 0.35), mAt(...P2(2.58, 0, 1.0 + 3.8), pr));

    // ---- Surroundings that belong to the cemetery ----
    // Headstones, crosses, obelisks and chest tombs scattered over the burial
    // ground (seeded), avoiding paths and the buildings.
    {
      const pip = (r, x, y) => {
        let c = false;
        for (let i = 0, j = r.length - 1; i < r.length; j = i++)
          if (
            r[i][1] > y !== r[j][1] > y &&
            x < ((r[j][0] - r[i][0]) * (y - r[i][1])) / (r[j][1] - r[i][1]) + r[i][0]
          )
            c = !c;
        return c;
      };
      const outer = (a) =>
        typeof a.poly[0][0] === 'number'
          ? a.poly
          : typeof a.poly[0][0][0] === 'number'
            ? a.poly[0]
            : a.poly[0][0];
      const area = (scene.areas || []).find(
        (a) => a.kind === 'cemetery' && pip(outer(a), C[0], C[1]),
      );
      const cemRing = area ? outer(area) : null;
      if (cemRing) {
        let x0 = 1e9,
          x1 = -1e9,
          y0 = 1e9,
          y1 = -1e9;
        for (const [x, y] of cemRing) {
          x0 = Math.min(x0, x);
          x1 = Math.max(x1, x);
          y0 = Math.min(y0, y);
          y1 = Math.max(y1, y);
        }
        const segs = [];
        for (const r of scene.roads || [])
          for (let i = 1; i < r.line.length; i++) {
            const a = r.line[i - 1],
              b2 = r.line[i];
            if (
              Math.max(a[0], b2[0]) < x0 - 5 ||
              Math.min(a[0], b2[0]) > x1 + 5 ||
              Math.max(a[1], b2[1]) < y0 - 5 ||
              Math.min(a[1], b2[1]) > y1 + 5
            )
              continue;
            segs.push([a, b2, (r.w || 3) / 2 + 1.6]);
          }
        const blocked = Object.values(byId).map((bb) => kit.offsetRing(bb.polys[0][0], 3));
        const nearSeg = (x, y) =>
          segs.some(([a, b2, w]) => {
            const dx = b2[0] - a[0],
              dy = b2[1] - a[1];
            const l2 = dx * dx + dy * dy || 1;
            const t = Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / l2));
            return Math.hypot(x - a[0] - dx * t, y - a[1] - dy * t) < w;
          });
        const rnd = kit.rng(1840);
        const head = kit.mat('#a7a397', { roughness: 0.9 });
        const head2 = kit.mat('#c9c3b2', { roughness: 0.9 });
        const granite = kit.mat('#6e6c68', { roughness: 0.6 });
        let placed = 0;
        for (let t = 0; t < 9000 && placed < 800; t++) {
          const x = x0 + rnd() * (x1 - x0),
            y = y0 + rnd() * (y1 - y0);
          // keep to the zone around the Great Circle, avenue and catacombs
          if (Math.hypot(x - C[0], y - C[1]) > 150) continue;
          if (!pip(cemRing, x, y) || nearSeg(x, y) || blocked.some((r) => pip(r, x, y))) continue;
          if (Math.hypot(x - oc[0], y - oc[1]) < 16) continue;
          placed++;
          const kind = rnd();
          const h = rnd();
          const r = pr + (rnd() - 0.5) * 0.15;
          const mtx = (z) => mAt(x, y, z, r);
          if (kind < 0.55)
            addGeo(
              h < 0.5 ? head : head2,
              new THREE.BoxGeometry(0.15, 0.6 + h * 0.3, 0.7 + h * 0.6),
              mtx(0.35 + h * 0.3),
            );
          else if (kind < 0.75) {
            addGeo(head2, new THREE.BoxGeometry(0.2, 0.2, 1.4 + h * 0.6), mtx(0.7 + h * 0.3));
            addGeo(head2, new THREE.BoxGeometry(0.2, 0.8, 0.18), mtx(1.1 + h * 0.5));
            addGeo(head, new THREE.BoxGeometry(0.6, 0.6, 0.3), mtx(0.15));
          } else if (kind < 0.95) {
            addGeo(head, new THREE.BoxGeometry(2.0, 1.0, 0.8), mtx(0.4));
            addGeo(head2, new THREE.BoxGeometry(2.2, 1.15, 0.12), mtx(0.86));
          } else {
            addGeo(granite, new THREE.BoxGeometry(0.7, 0.7, 0.7), mtx(0.35));
            addGeo(
              granite,
              new THREE.CylinderGeometry(0.08, 0.3, 1.8 + h * 1.0, 4).rotateX(Math.PI / 2),
              mtx(0.7 + (1.8 + h * 1.0) / 2),
            );
          }
        }
      }
    }
    // Benches along the colonnade fronts of the Great Circle.
    {
      const benches = [];
      for (const [x, y, rot, , , i] of arcBays.slice(0, nColBays))
        if (i % 7 === 3)
          benches.push([x + Math.sin(rot) * 2.2, y - Math.cos(rot) * 2.2, rot + Math.PI]);
      g.add(ctx.placeAssets('bench', benches));
    }

    g.add(batch.toGroup('brompton_cemetery'));
    return g;
  },
};
