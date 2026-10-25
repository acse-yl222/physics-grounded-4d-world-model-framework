// Marble Arch (John Nash, 1827-33; moved to the north-east corner of Hyde Park
// in 1851). A white Carrara / Seravezza marble triumphal arch after the Arch of
// Constantine and the Arc du Carrousel: a large central round-headed arch and
// two smaller side arches, four Corinthian columns on pedestals on each face,
// a breakforward entablature, relief panels and a panelled attic; about 45 ft
// (13.7 m) high.
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
  id: 'marble_arch',
  name: 'Marble Arch',
  claims: ['a344548c-782b-4847-a56a-7e242d693a39'],
  references: [
    {
      title: 'Marble Arch - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Marble_Arch',
      used_for: 'Nash design, Arch of Constantine model, three arches with Corinthian columns',
    },
    {
      title: 'Marble Arch - A View On Cities',
      url: 'https://aviewoncities.com/london/marble-arch',
      used_for: 'height 45 ft, white Carrara marble cladding',
    },
    {
      title: 'Marble Arch - Victorian Web',
      url: 'https://victorianweb.org/art/architecture/nash/1.html',
      used_for: 'Carrara vs Seravezza marble; Arc du Carrousel influence',
    },
    {
      title: 'Marble Arch - London Remembers',
      url: 'https://www.londonremembers.com/memorials/marble-arch',
      used_for: 'general appearance and relocation to Hyde Park corner',
    },
  ],
  notes:
    'Overall height 13.7 m from the 45 ft figure (Overture h = 10.4 m is too low). Plan and column positions from ' +
    'the Overture outline; opening widths, springing heights and attic proportions estimated. Sculpted reliefs are ' +
    'flat inset panels; the bronze gates are a painted grille.',
  build({ THREE, kit, frame }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const marble = kit.mat('#eeece6', { roughness: 0.45 });
    const marbleDk = kit.mat('#dedad0', { roughness: 0.5 });
    const shadow = kit.mat('#b9b5aa', { roughness: 0.6 });
    const gate = kit.paintedMaterial(
      'marble_arch:gate',
      256,
      256,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.strokeStyle = '#2b2a24';
        c.fillStyle = '#2b2a24';
        for (let x = 4; x < w; x += 14) c.fillRect(x, 0, 4, h);
        c.fillRect(0, 0, w, 8);
        c.fillRect(0, h * 0.45, w, 10);
        c.fillRect(0, h - 10, w, 10);
        c.lineWidth = 5;
        for (const cx of [w * 0.25, w * 0.75]) {
          c.beginPath();
          c.arc(cx, h * 0.3, w * 0.12, 0, Math.PI * 2);
          c.stroke();
        }
      },
      { transparent: true, alphaTest: 0.5, side: THREE.DoubleSide, metalness: 0.5, roughness: 0.5 },
    );
    const F = T.frame(frame.cx, frame.cy, frame.angle);
    const L = Math.min(frame.length, 18),
      D = Math.max(frame.width - 2.2, 5.2);
    const Z0 = 0.5,
      ZE = 10.0,
      ZA = 11.4,
      ZT = 13.7;
    F.box(batch, marbleDk, 0, 0, 0, L + 0.4, D + 2.6, Z0);
    // arched body: large central arch and two lower side arches
    const shape = T.archShape(L - 0.4, ZE - Z0, [
      { c: 0, w: 4.5, s: 5.9 },
      { c: -5.25, w: 2.5, s: 4.1 },
      { c: 5.25, w: 2.5, s: 4.1 },
    ]);
    T.slab(F, batch, marble, shape, 0, 0, Z0, D, 14);
    // impost mouldings and keystone blocks
    for (const fv of [-1, 1]) {
      const vf = fv * (D / 2 + 0.06);
      for (const [c, w, s] of [
        [0, 4.5, 5.9],
        [-5.25, 2.5, 4.1],
        [5.25, 2.5, 4.1],
      ]) {
        const av = new THREE.Shape();
        av.absarc(c, Z0 + s, w / 2 + 0.35, 0, Math.PI, false);
        av.lineTo(c - w / 2, Z0 + s);
        av.absarc(c, Z0 + s, w / 2, Math.PI, 0, true);
        av.lineTo(c + w / 2 + 0.35, Z0 + s);
        T.slab(F, batch, marbleDk, av, 0, vf, 0, 0.14, 14);
        F.box(batch, marbleDk, c, vf, Z0 + s + w / 2 - 0.1, 0.6, 0.3, 0.75); // keystone
        F.box(batch, marbleDk, c - w / 2 - 0.2, vf, Z0 + s - 0.3, 0.4, 0.2, 0.3);
        F.box(batch, marbleDk, c + w / 2 + 0.2, vf, Z0 + s - 0.3, 0.4, 0.2, 0.3);
      }
      // relief panels: spandrels of the central arch, panels above the side arches
      for (const s of [-1, 1]) {
        F.box(batch, shadow, s * 1.9, fv * (D / 2 + 0.03), 8.65, 1.4, 0.06, 1.0);
        F.box(batch, shadow, s * 5.25, fv * (D / 2 + 0.03), 6.4, 1.9, 0.06, 2.2);
        F.box(batch, marble, s * 5.25, fv * (D / 2 + 0.07), 6.6, 1.5, 0.06, 1.8);
      }
      // bronze gates across the central arch
      F.box(batch, gate, 0, fv * (D / 2 - 0.6), Z0, 4.5, 0.06, 5.9);
      // free-standing Corinthian columns on pedestals with breakforward entablature
      for (const u of [-7.4, -3.0, 3.0, 7.4]) {
        const vc = fv * (D / 2 + 0.75);
        F.box(batch, marbleDk, u, vc, Z0, 1.5, 1.5, 1.9);
        F.box(batch, marble, u, vc, Z0 + 1.9, 1.6, 1.6, 0.2);
        T.column(F, batch, marble, u, vc, Z0 + 2.1, ZE - Z0 - 2.1, 0.42, 'corinthian', 14);
        F.box(batch, marble, u, fv * (D / 2 + 0.55), ZE, 1.5, 1.4, 0.75);
        F.box(batch, marbleDk, u, fv * (D / 2 + 0.6), ZE + 0.75, 1.7, 1.6, 0.6);
        F.box(batch, marble, u, fv * (D / 2 + 0.45), ZA, 1.5, 1.0, ZT - ZA - 0.7); // attic pedestal over column
      }
      // attic inscription / relief panels
      for (const s of [-1, 0, 1])
        F.box(batch, shadow, s * 5.2, fv * (D / 2 - 0.25), ZA + 0.45, s ? 2.4 : 3.8, 0.06, 1.35);
    }
    // entablature, cornice and attic
    F.box(batch, marble, 0, 0, ZE, L, D + 0.1, 0.75);
    F.box(batch, marbleDk, 0, 0, ZE + 0.75, L + 0.4, D + 0.6, 0.65);
    F.box(batch, marble, 0, 0, ZA, L - 0.6, D - 0.6, ZT - ZA - 0.4);
    F.box(batch, marbleDk, 0, 0, ZT - 0.4, L - 0.2, D - 0.2, 0.4);
    F.box(batch, marble, 0, 0, ZT, 6.0, D - 1.2, 0.35);
    g.add(batch.toGroup('marble_arch'));
    return g;
  },
};
