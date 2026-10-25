// BBC Broadcasting House, Portland Place / Langham Place (G. Val Myer with M. T.
// Tudsbery, opened 1932) and its 2005-13 extensions. The original Art Deco
// block is a steel frame clad in Portland stone; its rounded "ship's prow" south
// end faces All Souls Langham Place, with Eric Gill's Prospero and Ariel over
// the entrance, the clock and the roof-top lattice mast. The massing steps back
// in the upper floors. East of the piazza stands the John Peel Wing (former Egton
// Wing) in matching Portland stone, linked to the old building at the rear by a
// glass-fronted extension.
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

function bldTools(THREE, kit) {
  /** Wall quads along a ring between z0 and z1; the texture repeats every tileW metres
   * (integer repeats per edge) and spans tileH metres vertically (default: z0..z1 once). */
  function wallsTex(
    batch,
    mat,
    ring,
    z0,
    z1,
    tileW,
    { tileH = null, vBase = z0, color, skip } = {},
  ) {
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05 || (skip && skip(k, a, b, len))) continue;
      const n = Math.round(len / tileW);
      const u1 = n >= 1 ? n : len / tileW;
      const v0 = tileH ? (z0 - vBase) / tileH : 0,
        v1 = tileH ? (z1 - vBase) / tileH : 1;
      batch.quad(
        mat,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, v0],
        [u1, v0],
        [u1, v1],
        [0, v1],
        color,
      );
    }
  }
  /** Projecting horizontal band (cornice, string course) around a ring. */
  function band(batch, mat, ring, z0, z1, d) {
    const r = kit.offsetRing(ring, d);
    wallsTex(batch, mat, r, z0, z1, 4);
    const hole = ring.slice().reverse();
    kit.cap(batch, mat, [[r, hole]], z1);
    kit.cap(batch, mat, [[r, hole]], z0, { down: true });
  }
  /** Balustrade from a to b (2D points) on level z. */
  function balustrade(batch, mat, a, b, z, h = 1.0, step = 0.5) {
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (len < 0.3) return;
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const mx = (a[0] + b[0]) / 2,
      my = (a[1] + b[1]) / 2;
    kit.box(batch, mat, mx, my, z, len, 0.45, 0.18, ang);
    kit.box(batch, mat, mx, my, z + h - 0.16, len, 0.5, 0.16, ang);
    const n = Math.floor(len / step);
    const geo = new THREE.CylinderGeometry(0.09, 0.12, h - 0.34, 5, 1, true).rotateX(Math.PI / 2);
    const m = new THREE.Matrix4();
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5) / n;
      m.makeTranslation(
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        z + 0.18 + (h - 0.34) / 2,
      );
      batch.addGeometry(mat, geo, m);
    }
    geo.dispose();
  }
  /** Sash / casement window drawing helper for canvases. */
  function sash(
    g,
    x,
    y,
    w,
    h,
    { frame = '#efe9dc', glass = '#2f3a42', cols = 2, rows = 3, arch = false } = {},
  ) {
    g.fillStyle = frame;
    g.beginPath();
    if (arch) {
      g.moveTo(x, y + h);
      g.lineTo(x, y + w / 2);
      g.arc(x + w / 2, y + w / 2, w / 2, Math.PI, 0);
      g.lineTo(x + w, y + h);
    } else g.rect(x, y, w, h);
    g.fill();
    const f = Math.max(1, w * 0.07);
    g.fillStyle = glass;
    g.beginPath();
    if (arch) {
      g.moveTo(x + f, y + h - f);
      g.lineTo(x + f, y + w / 2);
      g.arc(x + w / 2, y + w / 2, w / 2 - f, Math.PI, 0);
      g.lineTo(x + w - f, y + h - f);
    } else g.rect(x + f, y + f, w - 2 * f, h - 2 * f);
    g.fill();
    g.strokeStyle = frame;
    g.lineWidth = Math.max(1, w * 0.035);
    for (let c = 1; c < cols; c++) {
      g.beginPath();
      g.moveTo(x + (w * c) / cols, y + (arch ? w / 2 : 0));
      g.lineTo(x + (w * c) / cols, y + h);
      g.stroke();
    }
    for (let r = 1; r < rows; r++) {
      const yy = y + (arch ? w / 2 : 0) + ((h - (arch ? w / 2 : 0)) * r) / rows;
      g.beginPath();
      g.moveTo(x, yy);
      g.lineTo(x + w, yy);
      g.stroke();
    }
  }
  /** Stone base with faint ashlar joints. */
  function ashlar(g, w, h, base, joint, courseH, blockW, seed = 0.37) {
    const r = kit.rng(seed);
    g.fillStyle = base;
    g.fillRect(0, 0, w, h);
    for (let y = 0, row = 0; y < h; y += courseH, row++) {
      g.fillStyle = `rgba(0,0,0,${0.02 + r() * 0.03})`;
      g.fillRect(0, y, w, courseH);
      g.fillStyle = joint;
      g.fillRect(0, y, w, 1);
      for (let x = (row % 2) * blockW * 0.5; x < w; x += blockW) g.fillRect(x, y, 1, courseH);
    }
  }
  return { wallsTex, band, balustrade, sash, ashlar };
}

export default {
  id: 'bbc_broadcasting_house',
  name: 'BBC Broadcasting House',
  claims: ['8f1d5a24-abeb-4827-b54c-da1e75bba49c'],
  references: [
    {
      title: 'Broadcasting House - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Broadcasting_House',
      used_for:
        'Art Deco HQ on Portland Place/Langham Place, John Peel (Egton) wing on the east side, extension at the rear, piazza',
    },
    {
      title: 'Broadcasting House, London - Modernist Britain',
      url: 'https://www.modernistbritain.co.uk/post/building/Broadcasting+House/',
      used_for: 'Val Myer / Tudsbery, steel frame clad in Portland stone, Gill sculpture',
    },
    {
      title: 'Broadcasting House - Regent Street - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1930/broadcasthouse.html',
      used_for:
        'nine storeys stepping down to six on the Langham Street side; main facade topped by an ornamental clock tower; lattice mast (replica)',
    },
    {
      title: 'BBC Broadcasting House - A London Inheritance',
      url: 'https://alondoninheritance.com/london-books/bbc-broadcasting-house',
      used_for: 'Prospero and Ariel above the entrance; general appearance',
    },
    {
      title: 'The historical building of BBC Broadcasting House - World Construction Network',
      url: 'https://worldconstructionnetwork.com/?p=5337',
      used_for: 'John Peel wing in the same Portland stone; glass-fronted link extension',
    },
  ],
  notes:
    'Outline from Overture; the old building is taken as the west arm of the U-shaped footprint (west of the piazza ' +
    'line) and the rest as the Peel wing / link extension. Old BH heights: 24.2 m (Overture) to the main parapet, ' +
    'then two set-back storeys to 31.5 m and the clock stage to ~33 m - set-back depths are estimated. The lattice ' +
    'mast, clock and Gill group are schematic. The Peel wing is drawn at a single 24.2 m height (the 16.8 m part ' +
    'lies inside the taller part in the source data).',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['8f1d5a24-abeb-4827-b54c-da1e75bba49c'];
    const stone = kit.mat('#e3ddcc', { roughness: 0.8 });
    const stoneDk = kit.mat('#cbc4af');
    const roofm = kit.mat('#9a9b96');
    const steel = kit.mat('#d4d6d6', { roughness: 0.5, metalness: 0.4 });
    const H = 24.2;
    const deco = kit.paintedMaterial('bbc_broadcasting_house:deco', 128, 448, (c, w, h) => {
      // 2 bays x 14 m tile: Portland stone with regular punched windows, deep reveals
      const m = h / 14,
        Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#e4decd', 'rgba(110,100,80,0.22)', 0.7 * m, w / 2, 0.19);
      for (let k = 0; k < 2; k++) {
        const x0 = (k * w) / 2;
        for (let z = 0.9; z < 14; z += 3.5) {
          c.fillStyle = '#cfc8b4';
          c.fillRect(x0 + w * 0.13, Y(z + 2.05), w * 0.24, 2.0 * m);
          B.sash(c, x0 + w * 0.15, Y(z + 1.95), w * 0.2, 1.8 * m, {
            cols: 2,
            rows: 3,
            frame: '#d8d6cc',
            glass: '#2a333a',
          });
        }
      }
    });
    const ground = kit.paintedMaterial('bbc_broadcasting_house:ground', 128, 160, (c, w, h) => {
      const m = h / 5,
        Y = (z) => h - z * m;
      c.fillStyle = '#d9d2bf';
      c.fillRect(0, 0, w, h);
      for (let k = 0; k < 2; k++)
        B.sash(c, (k * w) / 2 + w * 0.1, Y(4.3), w * 0.3, 3.6 * m, {
          cols: 3,
          rows: 2,
          frame: '#4b4436',
          glass: '#2a333a',
        });
      c.fillStyle = 'rgba(0,0,0,0.25)';
      c.fillRect(0, Y(5), w, 3);
    });
    const peel = kit.paintedMaterial('bbc_broadcasting_house:peel', 192, 256, (c, w, h) => {
      // stone frame with storey-height glazing and fins
      c.fillStyle = '#e1dbc9';
      c.fillRect(0, 0, w, h);
      const fl = h / 4;
      for (let k = 0; k < 4; k++) {
        c.fillStyle = '#4c5c66';
        c.fillRect(w * 0.06, k * fl + fl * 0.18, w * 0.88, fl * 0.72);
        c.fillStyle = '#7f939c';
        for (let x = w * 0.06; x < w * 0.94; x += w * 0.22)
          c.fillRect(x, k * fl + fl * 0.18, 3, fl * 0.72);
      }
    });
    const linkGlass = kit.facade('glass', 1);

    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    // dividing line along the west side of the piazza (vertex 10 -> 11 direction), extended
    const pA = [3952.57, 1323.27],
      pB = [3941.81, 1361.13];
    const d = [pB[0] - pA[0], pB[1] - pA[1]];
    const side = (p) => d[0] * (p[1] - pA[1]) - d[1] * (p[0] - pA[0]); // > 0 west of the line
    const clip = (r, f) => {
      const out = [];
      for (let i = 0; i < r.length; i++) {
        const a = r[i],
          c = r[(i + 1) % r.length];
        const fa = f(a),
          fc = f(c);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fc >= 0) {
          const t = fa / (fa - fc);
          out.push([a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const oldBH = ccw(clip(ring, (p) => side(p) + 0.01));
    const east = ccw(clip(ring, (p) => -side(p) + 0.01));

    // ---------------- old Broadcasting House ----------------
    B.wallsTex(batch, ground, oldBH, 0, 5, 4.8);
    B.wallsTex(batch, deco, oldBH, 5, H, 4.8, { tileH: 14, vBase: 5 });
    B.band(batch, stoneDk, oldBH, 4.8, 5.2, 0.15);
    B.band(batch, stone, oldBH, H - 0.2, H + 0.58, 0.1);
    kit.cap(batch, roofm, [[oldBH]], H + 0.6);
    const s1 = kit.offsetRing(oldBH, -4.5),
      s2 = kit.offsetRing(oldBH, -9.5);
    B.wallsTex(batch, deco, s1, H + 0.6, 28.2, 4.8, { tileH: 14, vBase: 5 });
    B.band(batch, stone, s1, 28.0, 28.48, 0.1);
    kit.cap(batch, roofm, [[s1]], 28.5);
    B.wallsTex(batch, deco, s2, 28.5, 31.5, 4.8, { tileH: 14, vBase: 5 });
    kit.cap(batch, roofm, [[s2]], 31.5);
    // clock stage, mast, Gill group: the prow is the rounded south end facing All Souls
    const axis = Math.atan2(d[1], d[0]); // along the arm, pointing north
    const CF = T.frame(3935.0, 1325.0, axis - Math.PI / 2); // +u east-ish, +v north along the arm
    CF.box(batch, stone, 0, 0, H + 0.6, 11, 8, 8.4);
    CF.box(batch, stoneDk, 0, 0, H + 9.0, 11.6, 8.6, 0.6);
    CF.box(batch, stone, 0, 0, H + 9.6, 6, 4.5, 2.0);
    const clock = kit.paintedMaterial('bbc_broadcasting_house:clock', 128, 128, (c, w, h) => {
      c.fillStyle = '#e3ddcc';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#f3f0e6';
      c.beginPath();
      c.arc(w / 2, h / 2, w * 0.4, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#c2a14d';
      c.lineWidth = 6;
      c.stroke();
      c.fillStyle = '#c2a14d';
      for (let k = 0; k < 12; k++) {
        const a2 = (k * Math.PI) / 6;
        c.fillRect(w / 2 + Math.cos(a2) * w * 0.32 - 3, h / 2 + Math.sin(a2) * w * 0.32 - 3, 6, 6);
      }
      c.strokeStyle = '#222';
      c.lineWidth = 4;
      c.beginPath();
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.5, h * 0.22);
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.68, h * 0.58);
      c.stroke();
    });
    {
      // clock face on the south side of the clock stage (faces -v)
      const qa = CF.P(-2.6, -4.03),
        qb = CF.P(2.6, -4.03);
      batch.quad(
        clock,
        [qa[0], qa[1], H + 2.4],
        [qb[0], qb[1], H + 2.4],
        [qb[0], qb[1], H + 7.6],
        [qa[0], qa[1], H + 7.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // lattice radio mast on the roof behind the clock stage
    {
      const [mx, my] = CF.P(-3, 24);
      const z0 = 31.5,
        hM = 17,
        r0 = 1.6,
        r1 = 0.35;
      const leg = (k, t) => {
        const a2 = (k * Math.PI * 2) / 3 + 0.3,
          r = r0 + (r1 - r0) * t;
        return [mx + Math.cos(a2) * r, my + Math.sin(a2) * r, z0 + hM * t];
      };
      for (let k = 0; k < 3; k++) {
        T.rod(batch, steel, leg(k, 0), leg(k, 1), 0.09, 0.06, 4);
        for (let j = 0; j < 8; j++) {
          T.rod(batch, steel, leg(k, j / 8), leg((k + 1) % 3, (j + 1) / 8), 0.04, 0.04, 3);
          T.rod(batch, steel, leg(k, (j + 1) / 8), leg((k + 1) % 3, (j + 1) / 8), 0.04, 0.04, 3);
        }
      }
      T.rod(batch, steel, [mx, my, z0 + hM], [mx, my, z0 + hM + 4], 0.06, 0.03, 4);
    }
    // Prospero and Ariel in a tall niche over the bronze entrance at the prow tip (faces south)
    {
      const tip = [3943.7, 1311.0];
      kit.box(batch, stoneDk, tip[0], tip[1] + 0.25, 5.2, 5.4, 0.6, 8.2, 0);
      kit.box(
        batch,
        kit.mat('#3b3529', { metalness: 0.5, roughness: 0.45 }),
        tip[0],
        tip[1] - 0.1,
        0,
        4.4,
        0.4,
        4.8,
        0,
      );
      kit.box(batch, stoneDk, tip[0], tip[1] - 0.6, 5.0, 4.8, 1.4, 0.45, 0);
      T.figure(batch, stone, tip[0] - 0.9, tip[1] - 0.6, 5.45, 3.8, -Math.PI / 2);
      T.figure(batch, stone, tip[0] + 0.9, tip[1] - 0.7, 6.4, 2.1, -Math.PI / 2);
    }
    {
      const [fx, fy] = CF.P(0, 2);
      T.rod(batch, kit.mat('white'), [fx, fy, H + 11.6], [fx, fy, H + 17], 0.08, 0.05, 5);
    }

    // ---------------- John Peel wing and link extension ----------------
    const yCut = 1379; // piazza head: south = Peel wing (stone), north = glass link
    for (let k = 0; k < east.length; k++) {
      const a = east[k],
        c = east[(k + 1) % east.length];
      const my = (a[1] + c[1]) / 2;
      const onCut = Math.abs(side(a)) < 0.05 && Math.abs(side(c)) < 0.05;
      if (onCut) continue; // shared with the old building
      if (my < yCut)
        B.wallsTex(batch, peel, [a, c, c], 0, H, 4.5, {
          tileH: 14,
          vBase: 0,
          skip: (i) => i !== 0,
        });
      else kit.walls(batch, linkGlass, [[[a, c]]], 0, H, { bay: 3.4, storey: 3.5 });
    }
    // kit.walls on a 2-point ring also emits the closing edge c->a; acceptable (inside the volume)
    B.band(batch, stone, east, H - 0.4, H + 0.28, 0.1);
    kit.cap(batch, roofm, [[east]], H + 0.3);
    const eu = kit.offsetRing(east, -6);
    if (Math.abs(kit.ringArea(eu)) > 200) {
      kit.walls(batch, kit.facade('portland_stone', 3), [[eu]], H + 0.3, H + 3.6, {
        bay: 3.4,
        storey: 3.3,
        uvBase: H + 0.3,
      });
      kit.cap(batch, roofm, [[eu]], H + 3.6);
    }
    g.add(batch.toGroup('bbc_broadcasting_house'));
    return g;
  },
};
