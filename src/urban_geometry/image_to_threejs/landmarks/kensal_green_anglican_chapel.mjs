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
    'lower colonnaded walks. 3D detail: baseless fluted Doric columns with necking, echinus and abacus; triglyphs, ' +
    'taenia, bed moulding, corona and cymatium on every entablature; pilasters on the walls; raking cornices, ' +
    'palmette acroteria and eaves antefixes (the listing mentions anthemia; their exact positions are assumed); ' +
    'doorway with architrave and consoles; podium steps; ribbed lead dome with a small lantern (assumed). ' +
    'Surrounding monuments are a deterministic scatter of generic headstones and chest tombs kept off mapped paths, ' +
    'not a survey; catacomb entrances are omitted',
  build({ THREE, kit, byId, placeAssets, scene }) {
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
    // baseless fluted Greek Doric column: 20-sided tapering shaft with arris lines,
    // necking, echinus and square abacus
    const column = (u, v, z0, h, r) => {
      const hs = h - 0.45 * (r / 0.62);
      add(
        new THREE.CylinderGeometry(r * 0.8, r, hs, 20).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        z0 + hs / 2,
      );
      add(
        new THREE.CylinderGeometry(r * 0.83, r * 0.83, 0.08, 20).rotateX(Math.PI / 2),
        stoneShade,
        u,
        v,
        z0 + hs - 0.25,
      );
      const ec = 0.25 * (r / 0.62);
      add(
        new THREE.CylinderGeometry(r * 1.18, r * 0.8, ec, 20).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        z0 + hs + ec / 2,
      );
      add(
        new THREE.BoxGeometry(r * 2.45, r * 2.45, h - hs - ec),
        stoneShade,
        u,
        v,
        z0 + hs + ec + (h - hs - ec) / 2,
      );
    };
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
      const fz0 = z0 + (z1 - z0) * 0.38; // frieze above the architrave band
      // triglyphs standing proud of the frieze at the 1.6 m rhythm
      for (let k = 0; k < 4; k++) {
        const [pu, pv] = c[k],
          [qu, qv] = c[(k + 1) % 4];
        const len = Math.hypot(qu - pu, qv - pv);
        const du = (qu - pu) / len,
          dv = (qv - pv) / len;
        const nu = dv,
          nv = -du; // outward
        for (let t = 0.375; t < len - 0.2; t += 1.6) {
          const cu = pu + du * t + nu * 0.05,
            cv = pv + dv * t + nv * 0.05;
          const hw = du !== 0 ? 0.36 : 0.1,
            hd = du !== 0 ? 0.1 : 0.36;
          box(cu - hw, cu + hw, cv - hd, cv + hd, fz0, z1 - 0.05, stone);
        }
        // taenia between architrave and frieze
        box(
          Math.min(pu, qu) - Math.abs(nu) * 0.08,
          Math.max(pu, qu) + Math.abs(nu) * 0.08,
          Math.min(pv, qv) - Math.abs(nv) * 0.08,
          Math.max(pv, qv) + Math.abs(nv) * 0.08,
          fz0 - 0.1,
          fz0,
          stoneShade,
        );
      }
      box(u0 - 0.12, u1 + 0.12, v0 - 0.12, v1 + 0.12, z1, z1 + 0.12, stone); // bed moulding
      box(u0 - 0.45, u1 + 0.45, v0 - 0.45, v1 + 0.45, z1 + 0.12, z1 + 0.45, stoneShade); // corona
      box(u0 - 0.5, u1 + 0.5, v0 - 0.5, v1 + 0.5, z1 + 0.45, z1 + 0.6, stone); // cymatium
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
      // 3D pilasters with capitals at the bay divisions, plinth course
      for (let k = 0; k < 4; k++) {
        const [pu, pv] = c[k],
          [qu, qv] = c[(k + 1) % 4];
        const len = Math.hypot(qu - pu, qv - pv);
        const n = Math.max(1, Math.round(len / 3.6));
        const du = (qu - pu) / len,
          dv = (qv - pv) / len;
        for (let j = 0; j <= n; j++) {
          const t = (len * j) / n;
          const cu = pu + du * t + dv * 0.1,
            cv = pv + dv * t - du * 0.1;
          const hw = Math.abs(du) * 0.36 + 0.1,
            hd = Math.abs(dv) * 0.36 + 0.1;
          box(cu - hw, cu + hw, cv - hd, cv + hd, z0, z1 - 0.35, stone);
          box(
            cu - hw - 0.08,
            cu + hw + 0.08,
            cv - hd - 0.08,
            cv + hd + 0.08,
            z1 - 0.35,
            z1,
            stoneShade,
          );
        }
      }
      box(u0 - 0.15, u1 + 0.15, v0 - 0.15, v1 + 0.15, z0, z0 + 0.45, stoneShade);
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
    // dome ribs and a small glazed lantern over the central space
    for (let k = 0; k < 12; k++) {
      const a = (k / 12) * Math.PI * 2;
      const rib = new THREE.TorusGeometry(3.4, 0.07, 4, 10, Math.PI / 2)
        .rotateX(Math.PI / 2)
        .rotateZ(a);
      rib.scale(1, 1, 0.35);
      add(rib, kit.mat('#6c7478'), 0, -0.7, 13.0);
    }
    add(
      new THREE.CylinderGeometry(0.75, 0.8, 0.7, 12).rotateX(Math.PI / 2),
      kit.mat('#8fa3ad', { roughness: 0.2 }),
      0,
      -0.7,
      14.5,
    );
    add(new THREE.ConeGeometry(0.85, 0.5, 12).rotateX(Math.PI / 2), lead, 0, -0.7, 15.1);
    // tetrastyle portico facing east
    const pv0 = -6.6,
      pv1 = 5.2,
      pu = 15.0;
    for (let k = 0; k < 4; k++) column(pu, pv0 + 0.8 + (k * (pv1 - pv0 - 1.6)) / 3, PZ, 7.4, 0.62);
    for (const v of [pv0 + 0.8, pv1 - 0.8]) column(12.9, v, PZ, 7.4, 0.55); // returns
    box(pu - 0.75, pu + 0.75, pv0 + 0.1, pv1 - 0.1, PZ + 7.4, PZ + 7.8, stoneShade); // abacus line / architrave base
    friezeBox(12.2, pu + 0.75, pv0 + 0.1, pv1 - 0.1, PZ + 7.8, PZ + 9.1);
    pediment(
      12.0,
      pu + 1.1,
      pv0 - 0.25,
      pv1 + 0.25,
      PZ + 9.65,
      3.1,
      kit.mat('#e3ddcf', { side: THREE.DoubleSide }),
    );
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
    // raking cornices, acroteria and antefixes of the portico pediment
    {
      const pz = PZ + 9.65,
        vm = (pv0 + pv1) / 2,
        hw = (pv1 - pv0) / 2 + 0.25;
      const uF = pu + 1.25;
      const len = Math.hypot(hw, 3.1);
      for (const sg of [-1, 1]) {
        const [x, y] = W(uF - 0.2, vm + (sg * hw) / 2);
        const m = new THREE.Matrix4()
          .makeRotationZ(A)
          .multiply(new THREE.Matrix4().makeRotationX(-sg * Math.atan2(3.1, hw)));
        m.setPosition(x, y, pz + 1.55 + 0.2);
        const g2 = new THREE.BoxGeometry(0.8, len + 0.5, 0.45);
        b.addGeometry(stoneShade, g2, m);
        g2.dispose();
      }
      box(uF - 0.6, uF + 0.25, pv0 - 0.4, pv1 + 0.4, pz - 0.05, pz + 0.3, stoneShade);
      // acroteria: plinth blocks with anthemion palmettes
      const palm = (u, v, z, s2) => {
        box(u - 0.35, u + 0.35, v - 0.45, v + 0.45, z, z + 0.45, stone);
        const pg = new THREE.CircleGeometry(0.55 * s2, 9, 0, Math.PI);
        const [x, y] = W(u + 0.38, v);
        const m = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(-Math.sin(A), Math.cos(A), 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(Math.cos(A), Math.sin(A), 0),
        );
        m.setPosition(x, y, z + 0.45);
        b.addGeometry(kit.mat('#e3ddcf', { side: THREE.DoubleSide }), pg, m);
        pg.dispose();
      };
      palm(uF - 0.4, vm, pz + 3.15, 1.4);
      palm(uF - 0.4, pv0 - 0.1, pz + 0.3, 1);
      palm(uF - 0.4, pv1 + 0.1, pz + 0.3, 1);
      // antefixes along the eaves of the chapel roof
      for (let u = -10.5; u < 12; u += 1.6)
        for (const v of [pv0 - 0.55, pv1 + 0.55]) {
          const pg = new THREE.CircleGeometry(0.28, 7, 0, Math.PI);
          const [x, y] = W(u, v);
          const m = new THREE.Matrix4().makeBasis(
            new THREE.Vector3(Math.cos(A), Math.sin(A), 0),
            new THREE.Vector3(0, 0, 1),
            new THREE.Vector3(-Math.sin(A), Math.cos(A), 0).multiplyScalar(v < 0 ? -1 : 1),
          );
          m.setPosition(x, y, pz);
          b.addGeometry(kit.mat('#e3ddcf', { side: THREE.DoubleSide }), pg, m);
          pg.dispose();
        }
    }
    // doorway in the portico: battered architrave surround, cornice on consoles, panelled doors
    {
      const v0 = -2.9,
        v1 = -0.9,
        dz = PZ + 5.0;
      box(12.3, 12.42, v0, v1, PZ, dz, dark);
      for (const [a0, a1] of [
        [v0 - 0.45, v0],
        [v1, v1 + 0.45],
      ])
        box(12.35, 12.55, a0, a1, PZ, dz + 0.45, stone);
      box(12.35, 12.55, v0 - 0.45, v1 + 0.45, dz, dz + 0.45, stone);
      box(12.35, 12.85, v0 - 0.8, v1 + 0.8, dz + 0.6, dz + 0.9, stoneShade);
      for (const v of [v0 - 0.6, v1 + 0.6])
        box(12.4, 12.8, v - 0.12, v + 0.12, dz + 0.1, dz + 0.6, stone);
      for (let k = 0; k < 2; k++)
        for (let j = 0; j < 3; j++)
          box(
            12.42,
            12.46,
            v0 + 0.12 + k * 1.0,
            v0 + 0.88 + k * 1.0,
            PZ + 0.4 + j * 1.5,
            PZ + 1.6 + j * 1.5,
            kit.mat('#3a3f41'),
          );
    }
    // steps up the podium in front of the portico
    for (let k = 0; k < 4; k++)
      box(
        pu + 0.75 + k * 0.4,
        pu + 1.15 + k * 0.4,
        pv0 + 0.3,
        pv1 - 0.3,
        0,
        PZ - k * 0.3,
        stoneShade,
      );

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
    // Monuments of the cemetery around the chapel: headstones and chest tombs
    // (deterministic scatter outside the forecourt and Centre Avenue axis).
    {
      const r = kit.rng(0.517);
      const headM = [kit.mat('#a9a69e'), kit.mat('#8d8a83'), kit.mat('#c4c0b5')];
      // keep monuments off the mapped paths and avenues
      const segs = [];
      for (const rd of scene?.roads ?? [])
        for (let k = 1; k < rd.line.length; k++) {
          const p = rd.line[k - 1],
            q = rd.line[k];
          if (Math.min(Math.abs(p[0] - O[0]), Math.abs(q[0] - O[0])) > 120) continue;
          if (Math.min(Math.abs(p[1] - O[1]), Math.abs(q[1] - O[1])) > 120) continue;
          segs.push([p, q, (rd.w ?? 3) / 2 + 1.2]);
        }
      const clear = (x, y) =>
        segs.every(([p, q, w]) => {
          const dx = q[0] - p[0],
            dy = q[1] - p[1];
          const t = Math.max(
            0,
            Math.min(1, ((x - p[0]) * dx + (y - p[1]) * dy) / (dx * dx + dy * dy || 1)),
          );
          return Math.hypot(x - p[0] - dx * t, y - p[1] - dy * t) > w;
        });
      for (let k = 0; k < 260; k++) {
        const a = r() * Math.PI * 2,
          d = 31 + r() * 22;
        const u = Math.cos(a) * d - 4,
          v = Math.sin(a) * d;
        if (u > 10 && Math.abs(v) < 9) continue; // Centre Avenue and forecourt
        const rot = Math.round(r() * 2) * 0.05 - 0.05;
        const [x, y] = W(u, v);
        if (!clear(x, y)) continue;
        const m = headM[k % 3];
        if (r() < 0.2) {
          kit.box(b, m, x, y, 0, 2.0, 0.9, 0.85, A + rot);
          kit.box(b, m, x, y, 0.85, 2.2, 1.05, 0.12, A + rot);
        } else {
          const h = 0.7 + r() * 0.6;
          kit.box(b, m, x, y, 0, 0.7, 0.14, h, A + rot + Math.PI / 2);
          kit.box(b, m, x, y, 0, 0.9, 0.5, 0.12, A + rot + Math.PI / 2);
        }
      }
    }
    if (placeAssets) {
      const benches = [
        [...W(19, -8), A + Math.PI / 2],
        [...W(19, 8), A + Math.PI / 2],
      ];
      g.add(placeAssets('bench', benches, { name: 'kensal_green_anglican_chapel:benches' }));
    }
    g.add(b.toGroup('kensal_green_anglican_chapel'));
    return g;
  },
};
