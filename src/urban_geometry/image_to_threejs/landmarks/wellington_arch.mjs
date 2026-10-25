// Wellington Arch, Hyde Park Corner (Decimus Burton 1826-30, moved and rebuilt
// 1883-85), with the two monuments that share its island: the Royal Artillery
// Memorial (C. S. Jagger / L. Pearson, 1925) and the Duke of Wellington
// equestrian statue (J. E. Boehm, 1888). The arch is a Portland stone triumphal
// arch with a single wide round-headed opening, pairs of free-standing
// Corinthian columns standing well forward on both faces (east down
// Constitution Hill, west to Hyde Park Corner), a blank attic that serves as
// the pedestal for Adrian Jones's bronze quadriga "Peace descending on the
// Quadriga of War" (1912).
function tools(THREE, kit) {
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const M = new THREE.Matrix4(),
    Q = new THREE.Quaternion(),
    E = new THREE.Euler();
  function put(batch, mat, geo, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1, rx = 0, ry = 0) {
    E.set(rx, ry, rz, 'ZYX');
    Q.setFromEuler(E);
    M.compose(V(x, y, z), Q, V(sx, sy, sz));
    batch.addGeometry(mat, geo, M);
    geo.dispose();
  }
  /** Cylinder between two 3D points. */
  function rod(batch, mat, p, q, r0, r1 = r0, seg = 6) {
    const a = V(...p),
      b = V(...q);
    const d = b.clone().sub(a),
      len = d.length();
    const geo = new THREE.CylinderGeometry(r1, r0, len, seg, 1, true);
    Q.setFromUnitVectors(V(0, 1, 0), d.normalize());
    M.compose(a.add(b).multiplyScalar(0.5), Q, V(1, 1, 1));
    batch.addGeometry(mat, geo, M);
    geo.dispose();
  }
  function frame(cx, cy, ang) {
    const c = Math.cos(ang),
      s = Math.sin(ang);
    const P = (u, v) => [cx + u * c - v * s, cy + u * s + v * c];
    return {
      ang,
      P,
      P3: (u, v, z) => [...P(u, v), z],
      box: (batch, mat, u, v, z0, w, d, h, rz = 0) => {
        const [x, y] = P(u, v);
        kit.box(batch, mat, x, y, z0, w, d, h, ang + rz);
      },
      put: (batch, mat, geo, u, v, z, rz = 0, sx, sy, sz, rx, ry) => {
        const [x, y] = P(u, v);
        put(batch, mat, geo, x, y, z, ang + rz, sx, sy, sz, rx, ry);
      },
    };
  }
  /** Profile drawn in the (u, z) plane, extruded d along v and centred on v. */
  function slab(F, batch, mat, shape, u, v, z, d, curve = 12) {
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: d,
      bevelEnabled: false,
      curveSegments: curve,
    })
      .rotateX(Math.PI / 2)
      .translate(0, d / 2, 0);
    F.put(batch, mat, g, u, v, z);
  }
  /** Wall w x h (u from -w/2) with round-headed openings [{c, w, s}] (s = springing height). */
  function archShape(w, h, openings) {
    const sh = new THREE.Shape();
    sh.moveTo(-w / 2, 0);
    for (const o of openings.slice().sort((a, b) => a.c - b.c)) {
      sh.lineTo(o.c - o.w / 2, 0);
      sh.lineTo(o.c - o.w / 2, o.s);
      sh.absarc(o.c, o.s, o.w / 2, Math.PI, 0, true);
      sh.lineTo(o.c + o.w / 2, 0);
    }
    sh.lineTo(w / 2, 0);
    sh.lineTo(w / 2, h);
    sh.lineTo(-w / 2, h);
    sh.lineTo(-w / 2, 0);
    return sh;
  }
  function column(F, batch, mat, u, v, z0, h, r, kind = 'corinthian', seg = 12) {
    const bh = r * 0.9,
      ch = kind === 'corinthian' ? r * 2.3 : kind === 'ionic' ? r * 1.1 : r * 0.7;
    F.box(batch, mat, u, v, z0, r * 2.7, r * 2.7, bh * 0.4);
    F.put(
      batch,
      mat,
      new THREE.CylinderGeometry(r * 1.12, r * 1.3, bh * 0.6, seg).rotateX(Math.PI / 2),
      u,
      v,
      z0 + bh * 0.7,
    );
    const sh = h - bh - ch;
    const pts = [
      new THREE.Vector2(r, 0),
      new THREE.Vector2(r * 0.985, sh * 0.35),
      new THREE.Vector2(r * 0.86, sh),
    ];
    F.put(batch, mat, new THREE.LatheGeometry(pts, seg).rotateX(Math.PI / 2), u, v, z0 + bh);
    const zc = z0 + bh + sh;
    if (kind === 'corinthian') {
      F.put(
        batch,
        mat,
        new THREE.CylinderGeometry(r * 1.32, r * 0.88, ch * 0.78, seg).rotateX(Math.PI / 2),
        u,
        v,
        zc + ch * 0.39,
      );
      F.box(batch, mat, u, v, zc + ch * 0.78, r * 2.9, r * 2.9, ch * 0.22);
    } else if (kind === 'ionic') {
      F.box(batch, mat, u, v, zc, r * 2.1, r * 1.9, ch * 0.45);
      for (const s of [-1, 1])
        F.put(
          batch,
          mat,
          new THREE.CylinderGeometry(ch * 0.33, ch * 0.33, r * 1.9, 8).rotateZ(0),
          u + s * r * 1.15,
          v,
          zc + ch * 0.3,
          0,
          1,
          1,
          1,
          0,
          0,
        );
      F.box(batch, mat, u, v, zc + ch * 0.6, r * 2.6, r * 2.6, ch * 0.4);
    } else F.box(batch, mat, u, v, zc, r * 2.5, r * 2.5, ch);
  }
  /** Simple standing statue (body, shoulders, head) of height h. */
  function figure(batch, mat, x, y, z, h, heading = 0) {
    rod(batch, mat, [x, y, z], [x, y, z + h * 0.78], h * 0.13, h * 0.09, 7);
    put(batch, mat, new THREE.SphereGeometry(h * 0.075, 8, 6), x, y, z + h * 0.87);
    const c = Math.cos(heading + Math.PI / 2) * h * 0.13,
      s = Math.sin(heading + Math.PI / 2) * h * 0.13;
    rod(
      batch,
      mat,
      [x + c, y + s, z + h * 0.74],
      [x + c * 1.2, y + s * 1.2, z + h * 0.42],
      h * 0.035,
      h * 0.03,
      5,
    );
    rod(
      batch,
      mat,
      [x - c, y - s, z + h * 0.74],
      [x - c * 1.2, y - s * 1.2, z + h * 0.42],
      h * 0.035,
      h * 0.03,
      5,
    );
  }
  /** Horse of withers height ~1.45*s, heading in radians, rear = front legs raised (0..1). */
  function horse(batch, mat, x, y, z, heading, s, rear = 0) {
    const c = Math.cos(heading),
      sn = Math.sin(heading);
    const L = (a, b, h) => [x + a * c - b * sn, y + a * sn + b * c, z + h];
    const pitch = rear * 0.45;
    const lift = (a) => a * Math.sin(pitch);
    put(
      batch,
      mat,
      new THREE.SphereGeometry(1, 12, 8),
      ...L(0, 0, 1.45 * s),
      heading,
      0.95 * s,
      0.36 * s,
      0.4 * s,
      0,
      -pitch,
    );
    // neck and head
    const n0 = L(0.7 * s, 0, 1.55 * s + lift(0.7 * s)),
      n1 = L(1.05 * s, 0, 2.15 * s + lift(1.0 * s));
    rod(batch, mat, n0, n1, 0.24 * s, 0.17 * s, 7);
    const hd = L(1.28 * s, 0, 2.05 * s + lift(1.1 * s));
    put(
      batch,
      mat,
      new THREE.BoxGeometry(0.6 * s, 0.2 * s, 0.24 * s),
      ...hd,
      heading,
      1,
      1,
      1,
      0,
      0.75 - rear * 0.3,
    );
    // ears
    rod(
      batch,
      mat,
      L(1.08 * s, 0.06 * s, 2.25 * s + lift(1.0 * s)),
      L(1.06 * s, 0.07 * s, 2.42 * s + lift(1.0 * s)),
      0.04 * s,
      0.01 * s,
      4,
    );
    // hind legs
    for (const b of [-0.18, 0.18]) {
      rod(
        batch,
        mat,
        L(-0.7 * s, b * s, 1.25 * s),
        L(-0.85 * s, b * s, 0.55 * s),
        0.13 * s,
        0.08 * s,
        6,
      );
      rod(
        batch,
        mat,
        L(-0.85 * s, b * s, 0.55 * s),
        L(-0.72 * s + b * 0.4 * s, b * s, 0),
        0.07 * s,
        0.06 * s,
        6,
      );
    }
    // front legs: planted or raised and bent
    for (const [k, b] of [
      [0, -0.18],
      [1, 0.18],
    ]) {
      const top = L(0.72 * s, b * s, 1.25 * s + lift(0.72 * s));
      if (rear < 0.2) {
        rod(batch, mat, top, L(0.78 * s, b * s, 0.55 * s), 0.11 * s, 0.07 * s, 6);
        rod(batch, mat, L(0.78 * s, b * s, 0.55 * s), L(0.8 * s, b * s, 0), 0.07 * s, 0.06 * s, 6);
      } else {
        const knee = L((1.15 + k * 0.1) * s, b * s, (1.0 + rear * 0.45 - k * 0.15) * s);
        rod(batch, mat, top, knee, 0.11 * s, 0.07 * s, 6);
        rod(
          batch,
          mat,
          knee,
          L((1.05 + k * 0.1) * s, b * s, (0.5 + rear * 0.35 - k * 0.15) * s),
          0.07 * s,
          0.06 * s,
          6,
        );
      }
    }
    // tail
    rod(
      batch,
      mat,
      L(-0.92 * s, 0, 1.6 * s - lift(0.9 * s)),
      L(-1.15 * s, 0, 0.85 * s),
      0.08 * s,
      0.05 * s,
      5,
    );
  }
  return { put, rod, frame, slab, archShape, column, figure, horse, V };
}

export default {
  id: 'wellington_arch',
  name: 'Wellington Arch',
  claims: [
    'cc9ab33d-299e-4224-8dbb-c15280b83611', // Wellington Arch
    'a822a7e4-0f9b-48ad-b8e4-3f6fc9e534a5', // Royal Artillery Memorial
    '4018db4a-7677-49a0-b25b-d2c569902f22', // Wellington Monument (equestrian statue)
  ],
  references: [
    {
      title: 'Wellington Arch - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Wellington_Arch',
      used_for: 'Burton design, 1883 relocation to the top of Constitution Hill, quadriga history',
    },
    {
      title: 'Description of Wellington Arch - English Heritage',
      url: 'https://www.english-heritage.org.uk/visit/places/wellington-arch/history/description/',
      used_for:
        'single wide opening flanked by pairs of Corinthian columns standing well forward, blank attic as quadriga pedestal, Portland stone facing, faces east down Constitution Hill',
    },
    {
      title: 'Wellington Arch and Quadriga - Art UK',
      url: 'https://batch.artuk.org/discover/artworks/wellington-arch-and-quadriga-265475',
      used_for: 'materials: bronze quadriga, Portland stone',
    },
    {
      title: "The Wellington Arch - Sotheby's Realty journal",
      url: 'https://sothebysrealty.co.uk/the-journal/wellington-arch-london',
      used_for: 'quadriga: winged Victory in a chariot drawn by four horses',
    },
    {
      title: 'Wellington Arch - The Unfinished City',
      url: 'https://www.theunfinishedcity.co.uk/2025/08/wellington-arch.html',
      used_for: 'quadriga size (about 12 m high incl. pedestal reading)',
    },
  ],
  notes:
    'Arch massing from the Overture footprint (22 m x 13 m body plus column porticoes); heights proportioned ' +
    '(cornice 15 m, attic 19.7 m, Victory ~28 m) - no measured elevation was found. Quadriga horses and figures ' +
    'are schematic bronze forms; heading (east, towards the Palace) is assumed. Royal Artillery Memorial and ' +
    'Wellington statue are simplified (cruciform pedestal + stone howitzer; granite plinth + horse and rider) ' +
    'and are included so Hyde Park Corner does not show generic boxes.',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const stone = kit.mat('portland_stone');
    const stoneDk = kit.mat('#cfc7b2', { roughness: 0.85 });
    const voidm = kit.mat('#5a5648', { roughness: 0.9 });
    const bronze = kit.mat('#4a5245', { roughness: 0.45, metalness: 0.55 });
    const granite = kit.mat('#8b817b', { roughness: 0.7 });
    const paving = kit.mat('paving');

    // ---------------- Wellington Arch ----------------
    const arch = byId['cc9ab33d-299e-4224-8dbb-c15280b83611'];
    const fr = kit.ringFrame(arch.polys[0][0]);
    let ang = fr.angle;
    if (Math.sin(ang) < 0) ang += Math.PI; // u axis points north along the facade
    const F = T.frame(fr.cx, fr.cy, ang);
    const W = 21.8,
      D = 12.6;
    // podium and arch body with the single round-headed opening
    F.box(batch, stoneDk, 0, 0, 0, W + 0.6, D + 0.6, 0.9);
    T.slab(F, batch, stone, T.archShape(W, 12.3, [{ c: 0, w: 6.8, s: 8.4 }]), 0, 0, 0, D, 16);
    // dark soffit inside the passage so it reads as an opening from afar
    F.box(batch, voidm, 0, 0, 0, 6.7, D - 0.2, 0.05);
    // impost band and string courses
    for (const s of [-1, 1]) {
      F.box(batch, stoneDk, s * 7.1, 0, 8.1, 7.4, D + 0.3, 0.45);
      F.box(batch, stoneDk, s * 10.95, 0, 0.9, 0.5, D + 0.25, 11.4); // corner pilasters
      // blind panels on the piers
      for (const fv of [-1, 1]) {
        F.box(batch, voidm, s * 9.4, fv * (D / 2 + 0.02), 0.9, 1.5, 0.06, 3.0); // pier doors
        F.box(batch, stoneDk, s * 9.4, fv * (D / 2 + 0.05), 5.0, 2.2, 0.12, 2.4); // blind panels
      }
    }
    // archivolt
    const av = new THREE.Shape();
    av.absarc(0, 8.4, 4.0, 0, Math.PI, false);
    av.lineTo(-3.4, 8.4);
    av.absarc(0, 8.4, 3.4, Math.PI, 0, true);
    av.lineTo(4.0, 8.4);
    for (const fv of [-1, 1]) T.slab(F, batch, stoneDk, av, 0, fv * (D / 2 + 0.12), 0, 0.25, 16);
    // free-standing Corinthian column pairs on both faces with breakforward entablature
    for (const fv of [-1, 1]) {
      const vc = fv * (D / 2 + 1.35);
      for (const s of [-1, 1]) {
        F.box(batch, stoneDk, s * 5.5, vc, 0.9, 4.0, 2.0, 1.4); // pedestal
        F.box(batch, stone, s * 5.5, (fv * D) / 2 + fv * 0.15, 0.9, 4.6, 0.3, 11.4); // pilaster backing
        for (const uu of [4.45, 6.55])
          T.column(F, batch, stone, s * uu, vc, 2.3, 10.0, 0.52, 'corinthian', 14);
        F.box(batch, stone, s * 5.5, fv * (D / 2 + 0.75), 12.3, 4.4, 3.2, 1.0); // architrave
        F.box(batch, stoneDk, s * 5.5, fv * (D / 2 + 0.75), 13.3, 4.4, 3.2, 1.0); // frieze
        F.box(batch, stone, s * 5.5, fv * (D / 2 + 0.85), 14.3, 4.9, 3.6, 0.7); // cornice
        // statue-less attic breakforward block above the columns
        F.box(batch, stone, s * 5.5, fv * (D / 2 + 0.3), 15.0, 4.2, 2.0, 3.4);
      }
    }
    // main entablature
    F.box(batch, stone, 0, 0, 12.3, W + 0.2, D + 0.2, 1.0);
    F.box(batch, stoneDk, 0, 0, 13.3, W + 0.2, D + 0.2, 1.0);
    F.box(batch, stone, 0, 0, 14.3, W + 1.0, D + 1.0, 0.7);
    // attic and its cornice; quadriga pedestal
    F.box(batch, stone, 0, 0, 15.0, W - 2.4, D - 1.4, 3.9);
    F.box(batch, stoneDk, 0, 0, 18.4, W - 1.8, D - 0.8, 0.6);
    F.box(batch, stone, 0, 0, 19.0, 12.5, 6.4, 0.8);

    // Quadriga: four rearing horses abreast, chariot, boy driver and winged Peace.
    const z0 = 19.8;
    const head = ang - Math.PI / 2 + (Math.cos(ang - Math.PI / 2) < 0 ? Math.PI : 0); // east-facing heading
    const hdir = [Math.cos(head), Math.sin(head)];
    const at = (a, b) => {
      const [x, y] = F.P(0, 0);
      return [x + a * hdir[0] - b * hdir[1], y + a * hdir[1] + b * hdir[0]];
    };
    for (const [k, b] of [
      [0, -2.7],
      [1, -0.95],
      [2, 0.95],
      [3, 2.7],
    ]) {
      const [x, y] = at(1.4 + (k % 2) * 0.3, b);
      T.horse(batch, bronze, x, y, z0, head + b * 0.06, 2.4, k === 0 || k === 3 ? 0.9 : 0.6);
    }
    // chariot: car body and wheels
    {
      const [x, y] = at(-2.0, 0);
      T.put(batch, bronze, new THREE.BoxGeometry(1.8, 2.2, 1.6), x, y, z0 + 1.9, head);
      for (const b of [-1.25, 1.25]) {
        const [wx, wy] = at(-2.1, b);
        T.put(
          batch,
          bronze,
          new THREE.TorusGeometry(1.0, 0.12, 6, 18),
          wx,
          wy,
          z0 + 1.05,
          head,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
      }
      T.rod(batch, bronze, [...at(-1.2, 0), z0 + 1.6], [...at(1.0, 0), z0 + 2.6], 0.12, 0.1, 5);
      // boy charioteer
      const [bx, by] = at(-1.5, 0.3);
      T.figure(batch, bronze, bx, by, z0 + 2.4, 2.0, head);
      // Peace: tall winged figure standing in the car, arm raised with a wreath
      const [px, py] = at(-2.4, 0);
      T.figure(batch, bronze, px, py, z0 + 2.6, 4.4, head);
      T.rod(batch, bronze, [px, py, z0 + 5.9], [...at(-1.9, 0.35), z0 + 7.6], 0.13, 0.1, 5);
      T.put(
        batch,
        bronze,
        new THREE.TorusGeometry(0.4, 0.08, 4, 10),
        ...at(-1.85, 0.4),
        z0 + 7.9,
        head + Math.PI / 2,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      for (const s of [-1, 1]) {
        const shape = new THREE.Shape();
        shape.moveTo(0, 0);
        shape.quadraticCurveTo(1.6, 1.0, 2.2, 3.2);
        shape.quadraticCurveTo(1.2, 1.8, 0, 1.0);
        const wg = new THREE.ExtrudeGeometry(shape, {
          depth: 0.12,
          bevelEnabled: false,
          curveSegments: 5,
        })
          .rotateX(Math.PI / 2)
          .scale(s, 1, 1);
        const [wx, wy] = at(-2.65, s * 0.2);
        T.put(batch, bronze, wg, wx, wy, z0 + 5.6, head + Math.PI / 2 + s * 0.35);
      }
    }

    // ---------------- Royal Artillery Memorial ----------------
    {
      const b = byId['a822a7e4-0f9b-48ad-b8e4-3f6fc9e534a5'];
      const f = kit.ringFrame(b.polys[0][0]);
      let a = f.angle;
      if (Math.sin(a) < 0) a += Math.PI; // +u points north-north-west, howitzer aims at -u (south-south-east)
      const R = T.frame(f.cx, f.cy, a);
      const L = Math.min(f.length, 22),
        Wd = Math.min(f.width, 10);
      R.box(batch, paving, 0, 0, 0, L, Wd, 0.5);
      R.box(batch, stoneDk, 0, 0, 0.5, L - 2.2, 4.6, 0.8);
      // cruciform pedestal: long block plus transverse arms
      R.box(batch, stone, 0, 0, 1.3, 11.5, 3.8, 4.6);
      R.box(batch, stone, 0, 0, 1.3, 4.4, 7.0, 4.0);
      R.box(batch, stoneDk, 0, 0, 5.9, 12.2, 4.4, 0.5); // cornice
      R.box(batch, stoneDk, 0, 0, 5.3, 4.9, 7.4, 0.45);
      R.box(batch, voidm, 0, 1.92, 2.0, 9.5, 0.05, 1.6); // relief frieze panels
      R.box(batch, voidm, 0, -1.92, 2.0, 9.5, 0.05, 1.6);
      // stone howitzer: carriage, wheels, cradle and barrel elevated toward the south end
      R.box(batch, stone, 0.6, 0, 6.4, 5.2, 2.4, 0.9);
      R.box(batch, stone, 1.8, 0, 7.3, 2.4, 1.6, 0.8);
      for (const s of [-1, 1])
        R.put(batch, stone, new THREE.CylinderGeometry(0.9, 0.9, 0.35, 12), 0.6, s * 1.35, 7.2);
      {
        const [x0, y0] = R.P(1.5, 0),
          [x1, y1] = R.P(-4.0, 0);
        T.rod(batch, stone, [x0, y0, 8.1], [x1, y1, 9.7], 0.6, 0.42, 12);
      }
      // bronze figures: officer and driver at the ends, shell carrier and recumbent soldier on the sides
      for (const [u, v, h] of [
        [-L / 2 + 2.4, 0, 2.9],
        [L / 2 - 2.4, 0, 2.9],
        [0, 3.0, 2.8],
      ]) {
        const [x, y] = R.P(u, v);
        R.box(batch, stoneDk, u, v, 0.5, 1.6, 1.4, 1.1);
        T.figure(batch, bronze, x, y, 1.6, h, a);
      }
      R.box(batch, stoneDk, 0, -3.0, 0.5, 3.2, 1.4, 1.1);
      const [dx, dy] = R.P(-1.1, -3.0),
        [ex, ey] = R.P(1.1, -3.0);
      T.rod(batch, bronze, [dx, dy, 1.85], [ex, ey, 1.85], 0.28, 0.22, 7); // recumbent figure under a cape
    }

    // ---------------- Wellington statue (Boehm) ----------------
    {
      const b = byId['4018db4a-7677-49a0-b25b-d2c569902f22'];
      const f = kit.ringFrame(b.polys[0][0]);
      let a = f.angle;
      if (Math.sin(a) < 0) a += Math.PI; // horse faces north towards Apsley House
      const S = T.frame(f.cx, f.cy, a);
      S.box(batch, granite, 0, 0, 0, 6.2, 4.7, 0.8);
      S.box(batch, granite, 0, 0, 0.8, 4.6, 2.9, 3.4);
      S.box(batch, granite, 0, 0, 4.2, 5.0, 3.3, 0.45);
      const [x, y] = S.P(0, 0);
      T.horse(batch, bronze, x - Math.cos(a) * 0.3, y - Math.sin(a) * 0.3, 4.65, a, 1.35, 0);
      // rider in cocked hat
      const [rx, ry] = S.P(-0.2, 0);
      T.figure(batch, bronze, rx, ry, 6.35, 2.2, a);
      // four soldiers at the corners (Grenadier, Highlander, Welsh Fusilier, Inniskilling Dragoon)
      for (const [u, v] of [
        [2.6, 1.9],
        [2.6, -1.9],
        [-2.6, 1.9],
        [-2.6, -1.9],
      ]) {
        const [sx, sy] = S.P(u, v);
        T.figure(batch, bronze, sx, sy, 0.8, 2.0, a);
      }
    }
    g.add(batch.toGroup('wellington_arch'));
    return g;
  },
};
