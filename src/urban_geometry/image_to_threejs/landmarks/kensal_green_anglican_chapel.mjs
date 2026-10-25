// Anglican Chapel, Kensal Green (All Souls) Cemetery (John Griffith for the
// General Cemetery Company, 1835-37; Grade I). Greek Doric temple-fronted chapel
// in Portland stone and stucco on a stepped podium: tetrastyle portico of
// fluted, baseless Doric columns under a pediment facing Centre Avenue, a raised
// attic over the domed central space, and colonnades of paired Doric columns
// between pilasters running out to either side and ending in square
// pavilions, above the catacombs.
export default {
  id: 'kensal_green_anglican_chapel',
  name: 'Kensal Green Cemetery Anglican Chapel',
  claims: ['368ef81d-0e6a-4858-a272-88e90318cb8c'],
  references: [
    {
      title: 'The Anglican Chapel, Kensal Green - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101190995-the-anglican-chapel-kensal-green-ward',
      used_for:
        'Griffith 1835-36, Portland stone and stucco, tetrastyle Doric portico and pediment, stepped podium, colonnades of paired columns between pilasters with anthemia, end pavilions',
    },
    {
      title: 'Kensal Green Cemetery - Parks and Gardens',
      url: 'https://www.parksandgardens.org/places/kensal-green-cemetery',
      used_for: 'chapel setting on Centre Avenue, catacombs beneath',
    },
    {
      title: 'Kensal Green Cemetery - Victorian Web',
      url: 'https://www.victorianweb.org/art/parks/kensalgreen/2.html',
      used_for: 'western pavilions with memorials, domed central interior',
    },
    {
      title: 'Kensal Green (All Souls) Cemetery - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1000817',
      used_for: 'registered landscape context',
    },
  ],
  notes:
    'Plan from the Overture outline (chapel, portico bay, two L-shaped colonnade wings). Heights (cornice 10 m, ' +
    'pediment apex 13.5 m, colonnades 7 m) and column counts are estimates; the westward return arms are shown as ' +
    'lower colonnaded walks; anthemion ornament and the catacomb entrances are omitted.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const O = [-1750, 2460],
      A = (1.3 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // u: east (portico front), v: north
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const b = new kit.MeshBatch();
    const stone = kit.mat('#e3ddcf');
    const stoneShade = kit.mat('#cfc8b7');
    const lead = kit.mat('#7c8488', { roughness: 0.6 });
    const dark = kit.mat('#2c3236');
    const box = (u0, u1, v0, v1, z0, z1, m) => {
      const [x, y] = W((u0 + u1) / 2, (v0 + v1) / 2);
      kit.box(b, m, x, y, z0, u1 - u0, v1 - v0, z1 - z0, A);
    };
    const add = (geo, m, u, v, z, rot = 0) => {
      const [x, y] = W(u, v);
      b.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(A + rot).setPosition(x, y, z));
      geo.dispose();
    };
    const column = (u, v, z0, h, r) =>
      add(
        new THREE.CylinderGeometry(r * 0.82, r, h, 12).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        z0 + h / 2,
      );
    // Doric frieze strip: triglyphs and metopes, repeated per 1.6 m
    const frieze = kit.paintedMaterial(
      'kensal_green_anglican_chapel:frieze',
      128,
      64,
      (c, w, h) => {
        c.fillStyle = '#e3ddcf';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#b8b09e';
        c.fillRect(8, 6, 44, h - 12);
        c.fillStyle = '#e3ddcf';
        for (const x of [18, 32]) c.fillRect(x, 6, 4, h - 12);
        c.fillStyle = '#d3ccba';
        c.fillRect(0, 0, w, 5);
        c.fillRect(0, h - 4, w, 4);
      },
    );
    const friezeQuad = (p, q, z0, z1) => {
      const P = W(...p),
        Q = W(...q);
      const len = Math.hypot(Q[0] - P[0], Q[1] - P[1]);
      b.quad(
        frieze,
        [P[0], P[1], z0],
        [Q[0], Q[1], z0],
        [Q[0], Q[1], z1],
        [P[0], P[1], z1],
        [0, 0],
        [len / 1.6, 0],
        [len / 1.6, 1],
        [0, 1],
      );
    };
    const friezeBox = (u0, u1, v0, v1, z0, z1) => {
      const c = [
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      ];
      for (let k = 0; k < 4; k++) friezeQuad(c[k], c[(k + 1) % 4], z0, z1);
      box(u0 - 0.35, u1 + 0.35, v0 - 0.35, v1 + 0.35, z1, z1 + 0.55, stoneShade); // cornice
    };
    // stuccoed wall with pilasters and a blind panel per bay
    const wallM = kit.paintedMaterial('kensal_green_anglican_chapel:wall', 128, 256, (c, w, h) => {
      c.fillStyle = '#e1dacb';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(150,140,120,0.35)';
      for (let y = 16; y < h; y += 16) c.fillRect(0, y, w, 1.5);
      c.fillStyle = '#ece6da';
      c.fillRect(0, 0, 18, h);
      c.fillRect(w - 18, 0, 18, h);
      c.fillStyle = '#d0c8b6';
      c.fillRect(38, 60, w - 76, h - 110);
    });
    const wallBox = (u0, u1, v0, v1, z0, z1) => {
      const c = [
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      ];
      for (let k = 0; k < 4; k++) {
        const P = W(...c[k]),
          Q = W(...c[(k + 1) % 4]);
        const len = Math.hypot(Q[0] - P[0], Q[1] - P[1]);
        const ur = Math.max(1, Math.round(len / 3.6));
        b.quad(
          wallM,
          [P[0], P[1], z0],
          [Q[0], Q[1], z0],
          [Q[0], Q[1], z1],
          [P[0], P[1], z1],
          [0, 0],
          [ur, 0],
          [ur, 1],
          [0, 1],
        );
      }
      box(u0 + 0.05, u1 - 0.05, v0 + 0.05, v1 - 0.05, z1 - 0.01, z1, lead);
    };
    // pediment prism along v (gable facing +u or -u)
    const pediment = (u0, u1, v0, v1, z, ph, m) => {
      const pw = (v1 - v0) / 2;
      const pa = [
        [0, -pw, 0],
        [0, pw, 0],
        [0, 0, ph],
        [u1 - u0, -pw, 0],
        [u1 - u0, pw, 0],
        [u1 - u0, 0, ph],
      ];
      const idx = [0, 1, 2, 3, 5, 4, 0, 4, 1, 0, 3, 4, 1, 5, 2, 1, 4, 5, 2, 3, 0, 2, 5, 3];
      const geo = new THREE.BufferGeometry();
      geo.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(
          idx.flatMap((i) => pa[i]),
          3,
        ),
      );
      geo.setAttribute(
        'uv',
        new THREE.Float32BufferAttribute(
          idx.flatMap(() => [0, 0]),
          2,
        ),
      );
      add(geo, m, u0, (v0 + v1) / 2, z);
    };

    // ---------------- central chapel ----------------
    const PZ = 1.2; // stepped podium
    for (let k = 0; k < 3; k++)
      box(
        -11.5 + k * 0.4,
        16 - k * 0.4,
        -7.8 + k * 0.4,
        6.0 - k * 0.4,
        k * 0.4,
        (k + 1) * 0.4,
        stoneShade,
      );
    wallBox(-11, 12.4, -6.8, 5.4, PZ, 8.6);
    friezeBox(-11, 12.4, -6.8, 5.4, 8.6, 9.9);
    // raised attic over the domed central space
    wallBox(-7, 7, -4.6, 3.2, 10.4, 12.6);
    box(-7.3, 7.3, -4.9, 3.5, 12.6, 13.0, stoneShade);
    add(
      new THREE.SphereGeometry(3.4, 16, 6, 0, Math.PI * 2, 0, Math.PI / 2)
        .rotateX(Math.PI / 2)
        .scale(1, 1, 0.35),
      lead,
      0,
      -0.7,
      13.0,
    );
    // tetrastyle portico facing east
    const pv0 = -6.6,
      pv1 = 5.2,
      pu = 15.0;
    for (let k = 0; k < 4; k++) column(pu, pv0 + 0.8 + (k * (pv1 - pv0 - 1.6)) / 3, PZ, 7.4, 0.62);
    for (const v of [pv0 + 0.8, pv1 - 0.8]) column(12.9, v, PZ, 7.4, 0.55); // returns
    box(pu - 0.75, pu + 0.75, pv0 + 0.1, pv1 - 0.1, PZ + 7.4, PZ + 7.8, stoneShade); // abacus line / architrave base
    friezeBox(12.2, pu + 0.75, pv0 + 0.1, pv1 - 0.1, PZ + 7.8, PZ + 9.1);
    pediment(12.0, pu + 1.1, pv0 - 0.25, pv1 + 0.25, PZ + 9.65, 3.1, stone);
    // pediment roof slopes (lead) back over the chapel body
    {
      const ridge = PZ + 9.65 + 3.1,
        eave = PZ + 9.65;
      const vm = (pv0 + pv1) / 2;
      const pts = [
        [pu + 1.1, pv0 - 0.25, eave],
        [-11.3, pv0 - 0.25, eave],
        [-11.3, vm, ridge - 0.4],
        [pu + 1.1, vm, ridge],
      ];
      const pts2 = [
        [-11.3, pv1 + 0.25, eave],
        [pu + 1.1, pv1 + 0.25, eave],
        [pu + 1.1, vm, ridge],
        [-11.3, vm, ridge - 0.4],
      ];
      for (const P of [pts, pts2]) {
        const w = P.map(([u, v, z]) => [...W(u, v), z]);
        b.add(
          lead,
          w,
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
    }
    // door in the portico
    box(12.3, 12.45, -1.9, 0.5, PZ, PZ + 5.2, dark);

    // ---------------- colonnade wings ----------------
    const CZ = 0.8,
      CH = 5.0;
    const colonnade = (u0, u1, v0, v1, along, nPairs) => {
      // podium, back wall, paired columns along the open side, entablature, flat roof
      box(u0 - 0.3, u1 + 0.3, v0 - 0.3, v1 + 0.3, 0, CZ, stoneShade);
      if (along === 'v') {
        wallBox(u0, u0 + 1.0, v0, v1, CZ, CZ + CH);
        for (let k = 0; k < nPairs; k++) {
          const v = v0 + ((k + 0.5) * (v1 - v0)) / nPairs;
          for (const dv of [-0.65, 0.65]) column(u1 - 0.6, v + dv, CZ, CH, 0.38);
          if (k > 0)
            box(
              u1 - 1.0,
              u1 - 0.2,
              v0 + (k * (v1 - v0)) / nPairs - 0.4,
              v0 + (k * (v1 - v0)) / nPairs + 0.4,
              CZ,
              CZ + CH,
              stone,
            ); // pilaster pier
        }
      } else {
        const front = v1 > 0 ? v0 : v1; // open side faces the forecourt (towards the chapel axis)
        const back = v1 > 0 ? v1 - 1.0 : v0;
        wallBox(u0, u1, back, back + 1.0, CZ, CZ + CH);
        for (let k = 0; k < nPairs; k++) {
          const u = u0 + ((k + 0.5) * (u1 - u0)) / nPairs;
          for (const du of [-0.65, 0.65])
            column(u + du, front + (v1 > 0 ? 0.6 : -0.6), CZ, CH, 0.38);
        }
      }
      friezeBox(u0, u1, v0, v1, CZ + CH, CZ + CH + 1.0);
      box(u0 + 0.1, u1 - 0.1, v0 + 0.1, v1 - 0.1, CZ + CH + 0.5, CZ + CH + 1.05, lead);
    };
    // north and south colonnades from the chapel to the corner pavilions
    colonnade(6.2, 13.2, 5.9, 19.6, 'v', 3);
    colonnade(5.0, 12.0, -20.4, -7.6, 'v', 3);
    // westward return walks
    colonnade(-21.3, 6.2, 20.6, 27.0, 'u', 7);
    colonnade(-23.6, 5.0, -27.0, -20.6, 'u', 7);
    // square pavilions at the corners and the western ends
    const pavilion = (u0, u1, v0, v1) => {
      box(u0 - 0.3, u1 + 0.3, v0 - 0.3, v1 + 0.3, 0, CZ, stoneShade);
      wallBox(u0, u1, v0, v1, CZ, CZ + CH + 0.6);
      friezeBox(u0, u1, v0, v1, CZ + CH + 0.6, CZ + CH + 1.7);
      box(u0 + 0.6, u1 - 0.6, v0 + 0.6, v1 - 0.6, CZ + CH + 2.25, CZ + CH + 3.0, stone); // blocking course
    };
    pavilion(6.4, 14.0, 19.6, 26.2);
    pavilion(5.0, 12.0, -27.4, -20.4);
    pavilion(-22.0, -16.0, 20.4, 27.4);
    pavilion(-24.2, -18.2, -26.6, -19.6);
    g.add(b.toGroup('kensal_green_anglican_chapel'));
    return g;
  },
};
