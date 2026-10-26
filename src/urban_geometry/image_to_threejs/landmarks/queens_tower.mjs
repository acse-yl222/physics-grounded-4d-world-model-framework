// Queen's Tower, Imperial College South Kensington (T. E. Collcutt, 1887-1893).
// 87 m Neo-Renaissance campanile in Portland stone with red brick bands, the sole
// surviving part of the Imperial Institute. Listing: four main stages separated by
// balustraded balconies; tall square shaft with pilaster strips and an archway near
// the base; octagonal stage under the dome with semicircular turrets and flying
// buttresses above the four corners; copper dome, cupola and gilded finial. Two of
// Harry Dixon's 1892 stone lions from the Institute entrance stand by the door.
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
      used_for:
        'Collcutt neo-renaissance design; two Imperial Institute lions by the entrance; 324 steps',
    },
    {
      title: "Queen's Tower - British Listed Buildings",
      url: 'https://britishlistedbuildings.co.uk/101231643-queens-tower-knightsbridge-and-belgravia-ward',
      used_for:
        'listing: Portland stone with red brick bands, four stages with balustraded balconies, pilaster strips, ' +
        'archway near base, octagonal stage with semicircular turrets and flying buttresses, cupola, gilded finial',
    },
    {
      title: 'Around London in lions - Londonist',
      url: 'https://londonist.com/london/great-outdoors/around-london-in-lions',
      used_for: 'lions sculpted by Harry Dixon (1892), originally a quartet',
    },
    {
      title: "Queen's Tower renovation - Imperial College property",
      url: 'https://www.imperial.ac.uk/admin-services/property/current-projects/queens-tower/',
      used_for: 'stone steps around the base of the tower',
    },
  ],
  notes:
    'Footprint orientation from the Overture outline; entrance on the south (former Imperial Institute) side. ' +
    'Stage heights (balconies at 30, 50 and 62 m, octagon 71-77 m, dome to 84 m, cupola to 87.5 m), pilaster ' +
    'and window rhythm, arch counts and the lion carving are proportioned from general knowledge of photographs, ' +
    'not measured. The listing wording on whether the turrets sit on the corners or the octagon is ambiguous; ' +
    'turrets are placed on the corners with buttresses flying to the octagon.',
  build({ THREE, kit, frame, placeAssets }) {
    const root = new THREE.Group();
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const stone = kit.mat('portland_stone');
    const stone2 = kit.mat('#d3ccb8', { roughness: 0.85 }); // weathered recesses
    const stoneLight = kit.mat('#e6e0cf', { roughness: 0.75 }); // dressings, balustrades
    const brick = kit.mat('#9a4b36', { roughness: 0.9 });
    const copper = kit.mat('#6fa08b', { roughness: 0.6, metalness: 0.2 });
    const copperDark = kit.mat('#5b8a77', { roughness: 0.6, metalness: 0.2 });
    const gold = kit.mat('gold');
    const dark = kit.mat('#1d252b', { roughness: 0.4 });
    const louvre = kit.mat('#5a6064', { roughness: 0.7 });
    const door = kit.mat('#3b2a1e', { roughness: 0.7 });
    const W = Math.min(frame.width, 15);
    // windowRow with a vertical round-arch head (glass tympanum + moulded ring).
    const win = (bt, a, b, z, o) => {
      if (o.head !== 'arch') return kit.windowRow(bt, a, b, z, o);
      const centres = kit.windowRow(bt, a, b, z, { ...o, head: 'none' });
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ux = (b[0] - a[0]) / len,
        uy = (b[1] - a[1]) / len;
      const an = Math.atan2(uy, ux);
      const r = (o.width ?? 1.2) / 2,
        dep = o.depth ?? 0.12,
        zc = z + (o.height ?? 2.0);
      const rot = new THREE.Matrix4()
        .makeRotationZ(an)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      for (const [cx, cy] of centres) {
        const disc = new THREE.CircleGeometry(r, 12, 0, Math.PI);
        const m1 = rot.clone().setPosition(cx + uy * 0.03, cy - ux * 0.03, zc);
        bt.addGeometry(o.glass ?? kit.mat('dark_glass'), disc, m1);
        disc.dispose();
        const tor = new THREE.TorusGeometry(r + 0.04, 0.08, 4, 12, Math.PI);
        const m2 = rot.clone().setPosition(cx + uy * dep * 0.6, cy - ux * dep * 0.6, zc);
        bt.addGeometry(o.sill ?? o.frame ?? kit.mat('white'), tor, m2);
        tor.dispose();
        if (o.bars) {
          const g2 = new THREE.BoxGeometry(0.05, dep * 0.6, r);
          bt.addGeometry(
            o.frame ?? kit.mat('white'),
            g2,
            new THREE.Matrix4()
              .makeRotationZ(an)
              .setPosition(cx + uy * dep * 0.5, cy - ux * dep * 0.5, zc + r / 2),
          );
          g2.dispose();
        }
      }
      return centres;
    };
    const h = W / 2;
    const M = new THREE.Matrix4();
    const B = (m, x, y, z0, w, d, hh, a = 0) => kit.box(batch, m, x, y, z0, w, d, hh, a);
    const add = (m, geo, x, y, z, rz = 0) => {
      M.makeRotationZ(rz).setPosition(x, y, z);
      batch.addGeometry(m, geo, M);
      geo.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) =>
      add(
        m,
        new THREE.LatheGeometry(
          prof.map(([r, zz]) => new THREE.Vector2(r, zz)),
          seg,
        ).rotateX(Math.PI / 2),
        x,
        y,
        z,
      );
    const cyl = (m, r0, r1, hh, x, y, z0, seg = 12) =>
      add(m, new THREE.CylinderGeometry(r1, r0, hh, seg).rotateX(Math.PI / 2), x, y, z0 + hh / 2);
    const beam = (m, p0, p1, w, d) => {
      const dir = new THREE.Vector3(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]);
      const len = dir.length();
      dir.normalize();
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
      const geo = new THREE.BoxGeometry(len, w, d);
      M.compose(
        new THREE.Vector3((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2),
        q,
        new THREE.Vector3(1, 1, 1),
      );
      batch.addGeometry(m, geo, M);
      geo.dispose();
    };
    const sq = (s) => [
      [-s, -s],
      [s, -s],
      [s, s],
      [-s, s],
    ];
    // Faces: k = 0 south, 1 east, 2 north, 3 west (local frame). Point on face k at
    // lateral offset t and outward offset o.
    const FACE = [
      [0, -1, 1, 0],
      [1, 0, 0, 1],
      [0, 1, -1, 0],
      [-1, 0, 0, -1],
    ];
    const onFace = (k, t, o, s = h) => {
      const [nx, ny, tx, ty] = FACE[k];
      return [nx * (s + o) + tx * t, ny * (s + o) + ty * t];
    };
    const faceAng = (k) => (k * Math.PI) / 2;
    const faceEdge = (k, s, t0 = -s, t1 = s) => [onFace(k, t0, 0, s), onFace(k, t1, 0, s)];

    // ---- Steps, rusticated plinth and entrance -------------------------------
    B(stone2, 0, 0, 0, W + 4.2, W + 4.2, 0.18);
    B(stone2, 0, 0, 0, W + 3.4, W + 3.4, 0.36);
    B(stone2, 0, 0, 0, W + 2.6, W + 2.6, 0.54);
    for (let i = 0; i < 9; i++) {
      const z = 0.54 + i * 0.6;
      B(i % 2 ? stone2 : stone, 0, 0, z, W + (i % 2 ? 1.5 : 1.7), W + (i % 2 ? 1.5 : 1.7), 0.6);
    }
    kit.cornice(batch, stoneLight, sq(h + 0.85), 5.94, { height: 0.5, projection: 0.35, steps: 2 });
    // Archway on the south face with voussoirs, keystone and panelled door; blind arches elsewhere.
    for (let k = 0; k < 4; k++) {
      const [a, b] = faceEdge(k, h + 0.86, -2, 2);
      win(batch, a, b, 0.54, {
        count: 1,
        margin: 0,
        width: 3.0,
        height: 3.4,
        depth: 0.3,
        bars: 0,
        head: 'arch',
        glass: k === 0 ? door : dark,
        frame: stoneLight,
        sill: stoneLight,
        surround: 0.45,
        surroundMat: stoneLight,
      });
      const [kx, ky] = onFace(k, 0, 0.98);
      B(stoneLight, kx, ky, 5.3, 0.6, 0.3, 0.7, faceAng(k));
    }
    // Door panels and fanlight bars on the south door.
    for (const t of [-0.75, 0.75]) {
      const [x, y] = onFace(0, t, 0.93);
      B(kit.mat('#4a3626'), x, y, 0.8, 1.2, 0.06, 2.8);
    }

    // ---- Shaft (two stages) ---------------------------------------------------
    const shaft = (z0, z1, winLevels) => {
      B(stone2, 0, 0, z0, W, W, z1 - z0);
      // Red brick bands in the panels between the pilaster strips.
      for (let z = z0 + 1.2; z < z1 - 1.4; z += 2.6) B(brick, 0, 0, z, W + 0.06, W + 0.06, 0.85);
      for (let k = 0; k < 4; k++) {
        const ang = faceAng(k);
        // corner piers (quoined) and two intermediate pilaster strips
        for (const t of [-h + 0.9, h - 0.9]) {
          const [x, y] = onFace(k, t, 0.17);
          B(stone, x, y, z0, 1.8, 0.34, z1 - z0, ang);
          for (let z = z0 + 0.4; z < z1 - 0.6; z += 1.3) {
            const [qx, qy] = onFace(k, t + (Math.floor(z) % 2 ? 0.12 : -0.12), 0.36);
            B(stoneLight, qx, qy, z, 1.7, 0.06, 0.62, ang);
          }
        }
        for (const t of [-2.7, 2.7]) {
          const [x, y] = onFace(k, t, 0.11);
          B(stone, x, y, z0, 0.9, 0.22, z1 - z0, ang);
        }
        // Round-arched windows in the central panel, paired on the upper stage.
        for (const [z, n, hh] of winLevels) {
          const [a, b] = faceEdge(k, h, -2.2, 2.2);
          win(batch, a, b, z, {
            count: n,
            margin: 0.2,
            width: n > 1 ? 1.0 : 1.2,
            height: hh,
            depth: 0.22,
            bars: 1,
            head: 'arch',
            glass: dark,
            frame: stoneLight,
            sill: stoneLight,
          });
        }
        // Blind recessed side panels with small stone roundels.
        for (const t of [-4.6, 4.6]) {
          const [x, y] = onFace(k, t, 0.05);
          B(stone, x, y, z1 - 3.2, 1.6, 0.12, 2.2, ang);
        }
      }
    };
    shaft(6.44, 30, [
      [9.5, 1, 3.0],
      [15.5, 1, 3.0],
      [21.5, 1, 3.0],
      [26.0, 2, 2.6],
    ]);
    const balcony = (z, s, pr = 1.1) => {
      kit.cornice(batch, stoneLight, sq(s), z - 0.9, { height: 0.9, projection: pr, steps: 3 });
      const slab = s + pr;
      B(stoneLight, 0, 0, z, 2 * slab, 2 * slab, 0.12);
      // brackets under the balcony slab
      for (let k = 0; k < 4; k++)
        for (let t = -s + 1; t <= s - 1 + 1e-6; t += (2 * s - 2) / 6) {
          const [x, y] = onFace(k, t, pr / 2, s);
          B(stone, x, y, z - 1.6, 0.4, pr, 0.7, faceAng(k));
        }
      const r = s + pr - 0.15;
      kit.balustrade(batch, stoneLight, [...sq(r), sq(r)[0]], z + 0.12, {
        height: 1.05,
        spacing: 0.32,
      });
      for (const [x, y] of sq(r)) B(stone, x, y, z + 0.12, 0.45, 0.45, 1.2);
    };
    balcony(30, h);
    shaft(30.12, 50, [
      [33.5, 2, 3.6],
      [40.5, 2, 3.6],
      [46.0, 2, 2.4],
    ]);
    balcony(50, h);

    // ---- Belfry stage: three tall arched louvred openings per face -------------
    const zb0 = 50.12,
      zb1 = 61.0;
    B(stone2, 0, 0, zb0, W - 1.2, W - 1.2, zb1 - zb0);
    for (let k = 0; k < 4; k++) {
      const ang = faceAng(k);
      const [a, b] = faceEdge(k, h - 0.6, -h + 1.6, h - 1.6);
      win(batch, a, b, zb0 + 1.6, {
        count: 3,
        margin: 0.3,
        width: 2.3,
        height: 5.6,
        depth: 0.25,
        bars: 0,
        head: 'arch',
        glass: dark,
        frame: stoneLight,
        sill: stoneLight,
      });
      // louvre slats inside the openings
      for (let i = 0; i < 3; i++) {
        const t = -h + 1.6 + 0.3 + ((2 * h - 3.2 - 0.6) * (i + 0.5)) / 3;
        for (let z = zb0 + 2.0; z < zb0 + 7.0; z += 0.55) {
          const [x, y] = onFace(k, t, -0.48);
          B(louvre, x, y, z, 2.2, 0.08, 0.14, ang);
        }
      }
      // piers and engaged columns at the outer face
      const piers = [-h + 0.8, -2.55, 2.55, h - 0.8];
      piers.forEach((t, i) => {
        const wide = i === 0 || i === 3;
        const [x, y] = onFace(k, t, -0.3);
        B(stone, x, y, zb0, wide ? 1.6 : 0.9, 0.6, zb1 - zb0, ang);
        const [cx, cy] = onFace(k, t, 0.15);
        cyl(stoneLight, 0.36, 0.3, 7.6, cx, cy, zb0 + 0.6, 10);
        B(stoneLight, cx, cy, zb0 + 0.1, 0.9, 0.5, 0.5, ang);
        B(stoneLight, cx, cy, zb0 + 8.2, 0.9, 0.5, 0.45, ang);
      });
      // spandrel panel with brick inlay and entablature
      const [sx, sy] = onFace(k, 0, -0.32);
      B(stone, sx, sy, zb0 + 8.65, W - 0.2, 0.6, zb1 - zb0 - 8.65, ang);
      const [bx, by] = onFace(k, 0, 0.0);
      B(brick, bx, by, zb0 + 9.3, W - 2.6, 0.06, 0.7, ang);
    }
    kit.cornice(batch, stoneLight, sq(h), zb0 + 8.65, { height: 0.35, projection: 0.15 });
    balcony(62.2, h, 1.0);

    // ---- Top square stage with corner turrets and flying buttresses -----------
    const zt0 = 62.32,
      zt1 = 70.6;
    B(stone2, 0, 0, zt0, W - 2.4, W - 2.4, zt1 - zt0);
    for (let k = 0; k < 4; k++) {
      const [a, b] = faceEdge(k, h - 1.2, -3.2, 3.2);
      win(batch, a, b, zt0 + 1.0, {
        count: 2,
        margin: 0.3,
        width: 1.6,
        height: 4.4,
        depth: 0.2,
        bars: 1,
        head: 'arch',
        glass: dark,
        frame: stoneLight,
        sill: stoneLight,
      });
      const [px, py] = onFace(k, 0, -1.0);
      B(stone, px, py, zt0, 0.8, 0.5, zt1 - zt0, faceAng(k));
    }
    kit.cornice(batch, stoneLight, sq(h - 1.2), zt1 - 0.6, {
      height: 0.6,
      projection: 0.5,
      steps: 2,
    });
    const tR = 1.5;
    const turrets = sq(h - 1.3);
    for (const [x, y] of turrets) {
      cyl(stone, tR, tR, 9.6, x, y, zt0, 16);
      for (let z = zt0 + 1.2; z < zt0 + 9; z += 2.2)
        cyl(brick, tR + 0.03, tR + 0.03, 0.4, x, y, z, 16);
      cyl(stoneLight, tR + 0.3, tR + 0.15, 0.5, x, y, zt0 + 9.6, 16);
      // small arcaded top, ribbed copper cap and finial
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        cyl(
          stoneLight,
          0.12,
          0.12,
          1.6,
          x + Math.cos(a) * (tR - 0.15),
          y + Math.sin(a) * (tR - 0.15),
          zt0 + 10.1,
          6,
        );
      }
      cyl(dark, tR - 0.35, tR - 0.35, 1.6, x, y, zt0 + 10.1, 12);
      lathe(
        copper,
        [
          [tR + 0.2, 0],
          [tR + 0.2, 0.25],
          [tR * 0.95, 0.6],
          [tR * 0.7, 1.3],
          [tR * 0.35, 1.9],
          [0.12, 2.4],
          [0.05, 2.9],
          [0, 3.0],
        ],
        x,
        y,
        zt0 + 11.7,
        16,
      );
      cyl(gold, 0.16, 0.16, 0.32, x, y, zt0 + 14.4, 8);
    }

    // ---- Octagonal stage, buttresses, copper dome, cupola ----------------------
    const zo0 = zt1,
      zo1 = 77.2;
    const Ro = h - 2.0;
    const oct = (r, z0, hh, m) =>
      add(
        m,
        new THREE.CylinderGeometry(r, r, hh, 8).rotateX(Math.PI / 2),
        0,
        0,
        z0 + hh / 2,
        Math.PI / 8,
      );
    oct(Ro, zo0, zo1 - zo0, stone2);
    const octPt = (i, r) => {
      const a = (i / 8) * Math.PI * 2;
      return [Math.cos(a) * r, Math.sin(a) * r];
    };
    for (let i = 0; i < 8; i++) {
      // octagon vertices sit at pi/8 + i*pi/4 (cylinder rotated by pi/8)
      const a0 = Math.PI / 8 + (i * Math.PI) / 4,
        a1 = a0 + Math.PI / 4;
      const va = [Math.cos(a0) * Ro, Math.sin(a0) * Ro],
        vb = [Math.cos(a1) * Ro, Math.sin(a1) * Ro];
      win(batch, va, vb, zo0 + 1.4, {
        count: 1,
        margin: 0.5,
        width: 1.5,
        height: 3.2,
        depth: 0.2,
        bars: 1,
        head: 'arch',
        glass: dark,
        frame: stoneLight,
        sill: stoneLight,
      });
      // angle pilaster at each vertex
      const [px, py] = [Math.cos(a0) * (Ro + 0.05), Math.sin(a0) * (Ro + 0.05)];
      B(stone, px, py, zo0, 0.6, 0.6, zo1 - zo0, a0);
    }
    oct(Ro + 0.55, zo1 - 0.8, 0.8, stoneLight);
    oct(Ro + 0.25, zo1 - 1.2, 0.4, stone);
    oct(Ro + 0.3, zo0, 0.6, stoneLight);
    // Flying buttresses from the corner turrets to the octagon (two ribs each).
    for (const [x, y] of turrets) {
      const d = Math.hypot(x, y);
      const ux = x / d,
        uy = y / d;
      for (const zz of [0, 1.1]) {
        beam(
          stone,
          [x - ux * 0.6, y - uy * 0.6, zt0 + 9.0 + zz],
          [ux * (Ro - 0.1), uy * (Ro - 0.1), zo1 - 2.4 + zz],
          0.5,
          0.5,
        );
      }
      beam(
        stoneLight,
        [x - ux * 0.6, y - uy * 0.6, zt0 + 10.4],
        [ux * (Ro - 0.1), uy * (Ro - 0.1), zo1 - 0.8],
        0.6,
        0.25,
      );
    }
    // Dome: ogee profile with ribs and four lucarnes.
    const Rd = Ro + 0.2;
    const domeProf = [
      [Rd + 0.4, 0],
      [Rd + 0.4, 0.3],
      [Rd, 0.45],
      [Rd * 0.99, 1.2],
      [Rd * 0.94, 2.2],
      [Rd * 0.83, 3.3],
      [Rd * 0.66, 4.3],
      [Rd * 0.46, 5.1],
      [Rd * 0.28, 5.6],
      [Rd * 0.2, 5.85],
      [Rd * 0.2, 6.0],
    ];
    lathe(copper, domeProf, 0, 0, zo1, 32);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      const pts = domeProf
        .slice(1, -1)
        .map(
          ([r, z]) =>
            new THREE.Vector3(Math.cos(a) * (r + 0.06), Math.sin(a) * (r + 0.06), zo1 + z),
        );
      const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 16, 0.13, 4, false);
      batch.addGeometry(copperDark, tube, null);
      tube.dispose();
    }
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + Math.PI / 8;
      const r = Rd * 0.9;
      const x = Math.cos(a) * r,
        y = Math.sin(a) * r;
      B(copperDark, x, y, zo1 + 1.4, 0.9, 0.9, 1.3, a);
      add(
        dark,
        new THREE.CircleGeometry(0.32, 10).rotateY(Math.PI / 2),
        x + Math.cos(a) * 0.46,
        y + Math.sin(a) * 0.46,
        zo1 + 2.05,
        a,
      );
      add(
        copper,
        new THREE.ConeGeometry(0.65, 0.7, 4).rotateX(Math.PI / 2),
        x,
        y,
        zo1 + 3.05,
        Math.PI / 4 + a,
      );
    }
    // Cupola: open lantern of eight columns, cap dome, ball and gilded finial.
    const zc = zo1 + 5.9;
    cyl(stoneLight, 1.5, 1.4, 0.4, 0, 0, zc, 16);
    for (let i = 0; i < 8; i++) {
      const [x, y] = octPt(i, 1.15);
      cyl(stoneLight, 0.13, 0.11, 1.9, x, y, zc + 0.4, 6);
    }
    cyl(dark, 0.8, 0.8, 1.9, 0, 0, zc + 0.4, 10);
    cyl(stoneLight, 1.45, 1.5, 0.35, 0, 0, zc + 2.3, 16);
    lathe(
      copper,
      [
        [1.4, 0],
        [1.25, 0.4],
        [0.9, 0.85],
        [0.4, 1.15],
        [0.12, 1.25],
        [0, 1.3],
      ],
      0,
      0,
      zc + 2.65,
      16,
    );
    lathe(
      gold,
      [
        [0.001, 0],
        [0.18, 0.05],
        [0.28, 0.25],
        [0.2, 0.45],
        [0.06, 0.55],
        [0.06, 0.9],
        [0.16, 1.0],
        [0.03, 1.35],
        [0, 1.4],
      ],
      0,
      0,
      zc + 3.85,
      12,
    );

    // ---- Lions on plinths flanking the south door, paved apron ---------------
    const lionStone = kit.mat('#cfc7b2', { roughness: 0.9 });
    const lion = (t) => {
      const [x, y] = onFace(0, t, 4.2, h);
      B(stone2, x, y, 0, 1.4, 2.6, 1.1);
      B(stoneLight, x, y, 1.1, 1.55, 2.75, 0.12);
      const part = (geo, px, py, pz) => {
        M.makeTranslation(x + px, y + py, 1.22 + pz);
        batch.addGeometry(lionStone, geo, M);
        geo.dispose();
      };
      part(new THREE.CapsuleGeometry(0.42, 1.1, 4, 8).rotateX(Math.PI / 2), 0, 0.2, 0.55);
      part(new THREE.SphereGeometry(0.55, 10, 8), 0, -0.55, 0.95);
      part(new THREE.SphereGeometry(0.32, 8, 6), 0, -0.88, 0.95);
      part(new THREE.BoxGeometry(0.28, 0.3, 0.2), 0, -1.1, 0.85);
      for (const sx of [-0.25, 0.25]) {
        part(new THREE.BoxGeometry(0.22, 0.9, 0.24), sx, -0.8, 0.12);
        part(new THREE.BoxGeometry(0.24, 0.5, 0.5), sx, 0.75, 0.25);
      }
      part(new THREE.CylinderGeometry(0.06, 0.08, 0.9, 5).rotateZ(Math.PI / 2.4), 0.55, 0.9, 0.12);
    };
    lion(-3.4);
    lion(3.4);
    const pave = kit.mat('#c4bcab', { roughness: 0.95 });
    B(pave, 0, 0, 0, W + 9, W + 9, 0.04);
    const [px, py] = onFace(0, 0, 9, h);
    B(pave, px, py, 0, 4, 9, 0.04);

    g.add(batch.toGroup('queens_tower'));
    // Snap the frame rotation to the face nearest true south so the door faces the old Institute front.
    const quarter = Math.PI / 2;
    const rot = frame.angle - Math.round(frame.angle / quarter) * quarter;
    g.position.set(frame.cx, frame.cy, 0);
    g.rotation.z = rot;
    root.add(g);
    // Benches and lamps around the apron (scene coordinates).
    const c = Math.cos(rot),
      s = Math.sin(rot);
    const P = (x, y, hd) => [frame.cx + x * c - y * s, frame.cy + x * s + y * c, hd + rot];
    const R = h + 4.6;
    root.add(
      placeAssets('bench', [
        P(-R, 3, -Math.PI / 2),
        P(-R, -3, -Math.PI / 2),
        P(R, 3, Math.PI / 2),
        P(R, -3, Math.PI / 2),
        P(-3, R, Math.PI),
        P(3, R, Math.PI),
      ]),
    );
    root.add(
      placeAssets('street_lamp', [P(-R, -R, 0), P(R, -R, 0), P(R, R, Math.PI), P(-R, R, Math.PI)]),
    );
    return root;
  },
};
