// Apsley House, "Number One London", Hyde Park Corner (Robert Adam 1771-78,
// enlarged and refaced in Bath stone by Benjamin Dean and Philip Wyatt,
// 1828-29), with Decimus Burton's Hyde Park Corner Screen (Apsley Gate, c.1825)
// beside it. The house: rusticated ground-floor podium, centre three bays
// breaking forward to carry a pedimented portico of four Corinthian columns,
// Corinthian pilasters on the corners and sides, dentil cornice and parapet.
// The screen: Portland stone colonnade of Greek Ionic columns pierced by three
// entrances, the central one largest with a carved attic frieze.
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
  id: 'apsley_house',
  name: 'Apsley House',
  claims: [
    '969b00fe-17d4-439f-85d2-144c564d460f', // Apsley House
    '738895ec-7e67-4243-839b-587c2faaf7b9', // Apsley Gate (Hyde Park Corner Screen)
  ],
  references: [
    {
      title: 'Apsley House - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Apsley_House',
      used_for: 'Adam house refaced in Bath stone with pedimented portico by the Wyatts (1828-29)',
    },
    {
      title: 'Apsley House - Historic England list entry 1226873',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1226873',
      used_for:
        'rusticated podium, centre 3 bays breaking forward with pedimented Corinthian portico, Corinthian pilasters on corners/sides, dentil cornice',
    },
    {
      title: 'Mirror of Literature No. 381 (1829), Project Gutenberg',
      url: 'https://gutenberg.org/cache/epub/11332/pg11332-images.html',
      used_for: 'principal front: pediment on four Corinthian columns, Palladian style',
    },
    {
      title: 'Decimus Burton Screen, Apsley Gate - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101278089-decimus-burton-screen-apsley-gate-west-end-ward',
      used_for:
        'screen: Portland stone Greek Ionic colonnade pierced by three entrances, central archway largest with attic frieze',
    },
    {
      title: 'Decimus Burton screen - Victorian Web',
      url: 'https://victorianweb.org/art/architecture/burton/2.html',
      used_for: 'frieze of horsemen and chariots after the Elgin marbles',
    },
  ],
  notes:
    'House walls follow the Overture outline; storey heights (podium 5.6 m, cornice 16 m) are proportioned, not measured ' +
    '(Overture h = 20 m includes roof structures). Window rhythm is a painted 3.3 m bay; the west Waterloo Gallery ' +
    'skylight and chimneys are approximate. Screen column count/spacing and heights estimated from its footprint.',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const bath = kit.mat('#d5c095', { roughness: 0.85 });
    const bathDk = kit.mat('#c4ae82', { roughness: 0.85 });
    const stone = kit.mat('portland_stone');
    const lead = kit.mat('lead');
    const dark = kit.mat('#5d584c');
    const iron = kit.paintedMaterial(
      'apsley_house:gate',
      128,
      128,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.fillStyle = '#1d1f21';
        for (let x = 2; x < w; x += 8) c.fillRect(x, 0, 3, h);
        c.fillRect(0, 0, w, 6);
        c.fillRect(0, h * 0.55, w, 4);
        c.fillRect(0, h - 6, w, 6);
      },
      { transparent: true, alphaTest: 0.5, side: THREE.DoubleSide },
    );
    const BAY = 3.3;
    const upper = kit.paintedMaterial('apsley_house:upper', 512, 388, (c, w, h) => {
      B.ashlar(c, w, h, '#d6c297', 'rgba(120,100,70,0.35)', h / 26, w / 10, 0.41);
      const px = w / 4,
        m = h / 10; // metres -> px vertically (10 m tile)
      for (let k = 0; k < 4; k++) {
        const x0 = k * px;
        // faint pilaster strip at the bay edge
        c.fillStyle = 'rgba(255,245,220,0.18)';
        c.fillRect(x0, 0, px * 0.09, h);
        const ww = px * 0.4,
          wx = x0 + (px - ww) / 2;
        // piano nobile window (z 1.0 - 4.4 m of the tile) with cornice hood
        c.fillStyle = '#c7b080';
        c.fillRect(wx - px * 0.06, h - 4.9 * m, ww + px * 0.12, 0.35 * m);
        B.sash(c, wx, h - 4.45 * m, ww, 3.4 * m, { cols: 3, rows: 4 });
        c.fillStyle = '#c3ad7e';
        c.fillRect(wx - px * 0.04, h - 1.05 * m, ww + px * 0.08, 0.22 * m);
        // balustered sill band
        // second floor window (z 6.4 - 8.6)
        B.sash(c, wx + ww * 0.05, h - 8.7 * m, ww * 0.9, 2.2 * m, { cols: 3, rows: 2 });
      }
      c.fillStyle = 'rgba(90,70,40,0.25)';
      c.fillRect(0, h - 5.6 * m, w, 0.12 * m); // string course
    });
    const ground = kit.paintedMaterial('apsley_house:ground', 512, 217, (c, w, h) => {
      c.fillStyle = '#ccb78a';
      c.fillRect(0, 0, w, h);
      const m = h / 5.6;
      c.fillStyle = 'rgba(80,60,35,0.55)';
      for (let y = 0.55 * m; y < h; y += 0.55 * m) c.fillRect(0, y, w, 2); // rustication grooves
      for (let k = 0; k < 4; k++) {
        const px = w / 4,
          ww = px * 0.38,
          wx = k * px + (px - ww) / 2;
        c.fillStyle = '#ccb78a';
        c.fillRect(wx - 6, h - 4.6 * m, ww + 12, 4.0 * m);
        B.sash(c, wx, h - 4.4 * m, ww, 3.4 * m, { cols: 3, rows: 4, arch: true });
      }
      c.fillStyle = '#b39f74';
      c.fillRect(0, h - 0.6 * m, w, 0.6 * m); // plinth
    });

    // ---------------- house ----------------
    const house = byId['969b00fe-17d4-439f-85d2-144c564d460f'];
    let ring = house.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const near = (p, x, y) => Math.hypot(p[0] - x, p[1] - y) < 0.6;
    const bumpPts = [
      [3376.9, -343.3],
      [3377.5, -345.0],
      [3389.3, -340.8],
      [3388.6, -338.9],
    ];
    const isBump = (p) => bumpPts.some(([x, y]) => near(p, x, y));
    const upperRing = ring.filter((p) => !isBump(p));
    const front = ring.filter((p) => isBump(p));
    const Z1 = 5.6,
      Z2 = 15.6,
      Z3 = 16.4,
      Z4 = 17.4;
    B.wallsTex(batch, ground, ring, 0, Z1, 4 * BAY);
    B.band(batch, bathDk, ring, Z1 - 0.1, Z1 + 0.35, 0.18);
    B.wallsTex(batch, upper, upperRing, Z1, Z2, 4 * BAY);
    B.band(batch, bath, upperRing, Z2, Z2 + 0.35, 0.25);
    B.band(batch, bathDk, upperRing, Z2 + 0.35, Z3, 0.55); // dentil cornice
    const par = kit.offsetRing(upperRing, -0.05);
    B.wallsTex(batch, bath, par, Z3, Z4, 4);
    kit.cap(batch, lead, [[kit.offsetRing(upperRing, -0.4)]], Z4 - 0.35);
    B.wallsTex(batch, bath, kit.offsetRing(upperRing, -0.4), Z4 - 0.35, Z4, 4);
    // corner pilasters (Corinthian treatment on corners)
    for (let k = 0; k < upperRing.length; k++) {
      const p = upperRing[k],
        a = upperRing[(k - 1 + upperRing.length) % upperRing.length],
        b = upperRing[(k + 1) % upperRing.length];
      const cr = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]);
      if (cr <= 0) continue; // convex corners only
      const ang = Math.atan2(b[1] - p[1], b[0] - p[0]);
      kit.box(batch, bath, p[0], p[1], Z1 + 0.35, 0.9, 0.9, Z2 - Z1 - 0.35, ang);
    }
    // portico on the podium: 4 Corinthian columns, entablature and pediment
    {
      const fr = front.length === 4 ? front : bumpPts;
      // front edge = the two bump points furthest from the main facade line
      const A = fr[1],
        Bp = fr[2];
      const len = Math.hypot(Bp[0] - A[0], Bp[1] - A[1]);
      const ang = Math.atan2(Bp[1] - A[1], Bp[0] - A[0]);
      const depth = Math.hypot(fr[1][0] - fr[0][0], fr[1][1] - fr[0][1]) + 0.2;
      const mx = (A[0] + Bp[0]) / 2,
        my = (A[1] + Bp[1]) / 2;
      let n = [Math.sin(ang), -Math.cos(ang)];
      if ((mx - house.c[0]) * n[0] + (my - house.c[1]) * n[1] < 0) n = [-n[0], -n[1]];
      const F = T.frame(mx, my, ang); // u along the front, v positive inwards? check sign below
      const vIn = -n[0] * -Math.sin(ang) + -n[1] * Math.cos(ang) > 0 ? 1 : -1; // +v towards the house when vIn = 1
      let poly = fr.slice();
      if (kit.ringArea(poly) < 0) poly.reverse();
      kit.cap(batch, bathDk, [[poly]], Z1 + 0.35);
      for (const t of [-0.42, -0.14, 0.14, 0.42])
        T.column(
          F,
          batch,
          bath,
          t * len,
          vIn * 0.65,
          Z1 + 0.35,
          Z2 - Z1 - 0.75,
          0.42,
          'corinthian',
          12,
        );
      F.box(batch, bath, 0, vIn * (depth / 2 - 0.25), Z2 - 0.4, len + 0.4, depth + 0.4, 0.75);
      F.box(batch, bathDk, 0, vIn * (depth / 2 - 0.25), Z2 + 0.35, len + 0.9, depth + 0.9, 0.45);
      const ped = new THREE.Shape([
        new THREE.Vector2(-len / 2 - 0.45, 0),
        new THREE.Vector2(len / 2 + 0.45, 0),
        new THREE.Vector2(0, 2.7),
      ]);
      T.slab(F, batch, bath, ped, 0, vIn * (depth / 2 - 0.25), Z2 + 0.8, depth + 0.9);
      const tym = new THREE.Shape([
        new THREE.Vector2(-len / 2 + 0.3, 0),
        new THREE.Vector2(len / 2 - 0.3, 0),
        new THREE.Vector2(0, 2.05),
      ]);
      T.slab(F, batch, bathDk, tym, 0, vIn * -0.5, Z2 + 0.95, 0.1);
    }
    // chimney stacks and the Waterloo Gallery roof light
    {
      const fr = kit.ringFrame(upperRing);
      const F = T.frame(fr.cx, fr.cy, fr.angle);
      for (const [u, v] of [
        [-fr.length * 0.3, fr.width * 0.3],
        [fr.length * 0.05, fr.width * 0.35],
        [fr.length * 0.3, -fr.width * 0.25],
        [-fr.length * 0.05, -fr.width * 0.3],
      ])
        F.box(batch, bath, u, v, Z4 - 0.35, 1.0, 2.6, 2.4);
      F.box(
        batch,
        kit.mat('glass'),
        -fr.length * 0.12,
        fr.width * 0.05,
        Z4 - 0.35,
        fr.length * 0.35,
        5.0,
        1.4,
      );
    }

    // ---------------- Hyde Park Corner Screen ----------------
    {
      const sc = byId['738895ec-7e67-4243-839b-587c2faaf7b9'];
      const fr = kit.ringFrame(sc.polys[0][0]);
      const F = T.frame(fr.cx, fr.cy, fr.angle);
      const L = fr.length,
        hz = L / 2;
      const zc = 0.6,
        colH = 8.2,
        zE = zc + colH;
      F.box(batch, stone, 0, 0, 0, L, 2.4, zc); // stylobate
      // central gateway: four columns per face, attic with frieze
      const gw = 11.2;
      for (const v of [-1.15, 1.15])
        for (const u of [-4.6, -1.7, 1.7, 4.6])
          T.column(F, batch, stone, u, v, zc, colH, 0.4, 'ionic', 10);
      for (const s of [-1, 1]) F.box(batch, stone, s * 5.4, 0, zc, 1.3, 2.0, colH); // end piers of gateway
      F.box(batch, stone, 0, 0, zE, gw + 0.6, 3.2, 1.3);
      F.box(batch, stone, 0, 0, zE + 1.3, gw + 1.1, 3.6, 0.45);
      F.box(batch, stone, 0, 0, zE + 1.75, gw - 0.6, 2.6, 2.4); // attic
      for (const s of [-1, 1])
        F.box(batch, kit.mat('#c9c0aa'), 0, s * 1.31, zE + 2.05, gw - 1.6, 0.04, 1.6); // frieze relief
      F.box(batch, stone, 0, 0, zE + 4.15, gw - 0.2, 3.0, 0.45);
      // flanking colonnades and the two side entrances with end piers
      for (const s of [-1, 1]) {
        const u0 = gw / 2 + 1.3,
          u1 = hz - 4.2;
        const n = Math.max(2, Math.round((u1 - u0) / 2.6));
        for (let k = 0; k <= n; k++)
          T.column(F, batch, stone, s * (u0 + ((u1 - u0) * k) / n), 0, zc, colH, 0.36, 'ionic', 10);
        F.box(batch, stone, (s * (u0 + u1)) / 2, 0, zE, u1 - u0 + 1.0, 1.4, 1.1);
        F.box(batch, stone, (s * (u0 + u1)) / 2, 0, zE + 1.1, u1 - u0 + 1.2, 1.7, 0.35);
        // side entrance: two columns between solid piers
        for (const u of [hz - 3.4, hz - 1.4])
          T.column(F, batch, stone, s * u, 0, zc, colH, 0.36, 'ionic', 10);
        F.box(batch, stone, s * (hz - 0.45), 0, zc, 0.9, 2.3, colH);
        F.box(batch, stone, s * (hz - 4.25), 0, zc, 0.9, 2.0, colH);
        F.box(batch, stone, s * (hz - 2.3), 0, zE, 4.6, 2.4, 1.1);
        F.box(batch, stone, s * (hz - 2.3), 0, zE + 1.1, 4.9, 2.7, 0.35);
        // iron gates in the side entrance
        F.box(batch, iron, s * (hz - 2.4), 0, zc, 3.0, 0.08, 3.2);
      }
      // gates in the central opening
      F.box(batch, iron, 0, 0, zc, 2.9, 0.08, 4.0);
    }
    g.add(batch.toGroup('apsley_house'));
    return g;
  },
};
