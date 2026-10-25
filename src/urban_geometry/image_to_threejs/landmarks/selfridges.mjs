// Selfridges, Oxford Street (Daniel Burnham for H. Gordon Selfridge, opened
// 1909; facade by Francis Swales; completed in phases to 1928 with Sir John
// Burnet and Thomas Tait). Portland stone block with a Giant Order of Ionic
// columns over the ground-floor display windows, metal-and-glass panels between
// the columns spanning three storeys, a heavy entablature, an attic storey and
// a set-back top floor; the main Oxford Street entrance carries Gilbert Bayes's
// polychrome "Queen of Time" under a bronze canopy.
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
  id: 'selfridges',
  name: 'Selfridges',
  claims: ['c3680bda-49e6-402d-b146-8f293b960995'],
  references: [
    {
      title: 'Selfridges flagship store - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Selfridges_flagship_store',
      used_for:
        'Burnham/Swales design, Giant Order of Ionic columns on the ground-floor base with metal and glass panels between, phases 1906-1928',
    },
    {
      title: 'Selfridges, Oxford Street - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1920/selfridges.html',
      used_for:
        'Swales frontispiece, Burnet influence, Queen of Time sculpture by Gilbert Bayes above the entrance',
    },
    {
      title: 'Selfridges, 398-454 Oxford Street - UCL Survey of London blog',
      url: 'https://blogs.ucl.ac.uk/survey-of-london/2020/12/23/selfridges-398-454-oxford-street',
      used_for: 'building history and phasing; columns hiding the steel frame',
    },
    {
      title: 'Selfridges Oxford Street - Arch Journey',
      url: 'https://archjourney.org/projects/selfridges-oxford-street/',
      used_for: 'general architectural description',
    },
  ],
  notes:
    'Plan from the Overture outline. Heights are proportioned from the elevation (ground floor 6.6 m, giant order to ' +
    '23 m, cornice 26 m, attic 29.5 m, set-back top floor 33 m) because Overture h = 18.2 m is clearly too low; ' +
    'no measured section was found. Column spacing (~6 m bays) is an estimate. The Wigmore Street (north) side and ' +
    'the later rear additions use a plainer painted elevation. Queen of Time is a schematic gilded figure.',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['c3680bda-49e6-402d-b146-8f293b960995'];
    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const stone = kit.mat('#ddd6c4', { roughness: 0.8 });
    const stoneDk = kit.mat('#cbc3ae', { roughness: 0.85 });
    const bronze = kit.mat('#3c3a2e', { roughness: 0.45, metalness: 0.5 });
    const roofm = kit.mat('#a3a39c', { roughness: 0.9 });
    const gold = kit.mat('gold');
    const yellow = kit.mat('#f2d21b', { roughness: 0.6, side: THREE.DoubleSide });
    const BAY = 6.0,
      Z1 = 6.6,
      Z2 = 23.0,
      Z3 = 26.0,
      Z4 = 29.5,
      Z5 = 33.0,
      TH = Z3; // painted tile covers 0..26 m
    const main = kit.paintedMaterial('selfridges:bay', 192, 832, (c, w, h) => {
      const m = h / TH,
        Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#ddd6c4', 'rgba(120,110,90,0.25)', 0.7 * m, w / 2, 0.29);
      // ground floor display window in a bronze frame
      c.fillStyle = '#3b392e';
      c.fillRect(w * 0.14, Y(5.0), w * 0.72, 4.6 * m);
      c.fillStyle = '#d9cfa8';
      c.fillRect(w * 0.18, Y(4.7), w * 0.64, 3.9 * m);
      c.fillStyle = 'rgba(40,46,52,0.55)';
      c.fillRect(w * 0.18, Y(4.7), w * 0.64, 3.9 * m);
      c.fillStyle = '#3b392e';
      c.fillRect(w * 0.14, Y(6.0), w * 0.72, 0.8 * m); // transom / fascia
      // three-storey metal-and-glass panel between the columns
      const x0 = w * 0.17,
        x1 = w * 0.83;
      c.fillStyle = '#3d4038';
      c.fillRect(x0, Y(22.4), x1 - x0, 15.4 * m);
      const floors = [
        [7.6, 11.4],
        [12.4, 16.2],
        [17.2, 21.6],
      ];
      for (const [za, zb] of floors) {
        c.fillStyle = '#26313a';
        c.fillRect(x0 + 4, Y(zb), x1 - x0 - 8, (zb - za) * m);
        c.fillStyle = '#5a5c4e';
        for (const f of [1 / 3, 2 / 3]) c.fillRect(x0 + (x1 - x0) * f - 2, Y(zb), 4, (zb - za) * m);
        c.fillRect(x0, Y(za + (zb - za) * 0.7), x1 - x0, 3);
      }
      c.fillStyle = '#6a6650';
      for (const z of [11.9, 16.7]) c.fillRect(x0, Y(z + 0.5), x1 - x0, 1.0 * m); // decorated spandrels
      // pilaster responds at bay edges
      c.fillStyle = '#e4ddcc';
      c.fillRect(0, Y(Z2), w * 0.09, (Z2 - Z1) * m);
      c.fillRect(w * 0.91, Y(Z2), w * 0.09, (Z2 - Z1) * m);
      // entablature with frieze
      c.fillStyle = '#d3cbb6';
      c.fillRect(0, Y(TH), w, (TH - Z2) * m);
      c.fillStyle = 'rgba(0,0,0,0.12)';
      c.fillRect(0, Y(24.2), w, 2);
    });
    const attic = kit.paintedMaterial('selfridges:attic', 192, 112, (c, w, h) => {
      B.ashlar(c, w, h, '#ddd6c4', 'rgba(120,110,90,0.25)', h / 5, w / 2, 0.61);
      for (const x of [0.12, 0.56])
        B.sash(c, w * x, h * 0.25, w * 0.32, h * 0.5, {
          cols: 2,
          rows: 1,
          frame: '#4a4a3c',
          glass: '#26313a',
        });
    });
    const plain = kit.paintedMaterial('selfridges:rear', 192, 832, (c, w, h) => {
      const m = h / TH,
        Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#d7d0be', 'rgba(120,110,90,0.25)', 0.7 * m, w / 2, 0.83);
      c.fillStyle = '#3b392e';
      c.fillRect(w * 0.2, Y(4.8), w * 0.6, 3.8 * m);
      for (let z = 7.6; z < 22; z += 4.8)
        B.sash(c, w * 0.22, Y(z + 3.0), w * 0.56, 3.0 * m, {
          cols: 3,
          rows: 2,
          frame: '#4a4a3c',
          glass: '#26313a',
        });
      c.fillStyle = '#cbc3ae';
      c.fillRect(0, Y(TH), w, (TH - Z2) * m);
    });
    const top = kit.facade('portland_stone', 1);

    const isNorth = (a, bb) => {
      const len = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      return -(bb[0] - a[0]) / len > 0.6; // outward normal y > 0.6
    };
    // walls: grand order on Oxford Street / Orchard Street / Duke Street, plainer rear
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        c = ring[(k + 1) % ring.length];
      B.wallsTex(batch, isNorth(a, c) ? plain : main, [a, c, c], 0, Z3, BAY, {
        skip: (i) => i !== 0,
      });
    }
    B.band(batch, stoneDk, ring, Z3 - 0.9, Z3 - 0.02, 0.9); // cornice
    B.band(batch, stone, ring, Z2 - 0.1, Z2 + 0.6, 0.35); // architrave
    const att = kit.offsetRing(ring, -0.4);
    B.wallsTex(batch, attic, att, Z3, Z4, BAY);
    B.band(batch, stoneDk, att, Z4 - 0.5, Z4 - 0.02, 0.4);
    const set = kit.offsetRing(ring, -3.5);
    kit.cap(batch, roofm, [[att]], Z4);
    kit.walls(batch, top, [[set]], Z4, Z5, { bay: 3.0, storey: 3.5, uvBase: Z4 });
    kit.cap(batch, roofm, [[set]], Z5);
    {
      // rooftop plant rooms and lift overruns
      const fr = kit.ringFrame(set);
      const F = T.frame(fr.cx, fr.cy, fr.angle);
      const r = kit.rng(0.417);
      for (let k = 0; k < 7; k++) {
        const u = (r() - 0.5) * fr.length * 0.7,
          v = (r() - 0.5) * fr.width * 0.6;
        F.box(batch, kit.mat('#9a9b97'), u, v, Z5, 4 + r() * 10, 3 + r() * 6, 1.5 + r() * 2.5);
      }
    }
    // giant Ionic columns, canopy and flags along the street faces
    let mainEdge = null;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        c = ring[(k + 1) % ring.length];
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
      if (len < 12 || isNorth(a, c)) continue;
      const ang = Math.atan2(c[1] - a[1], c[0] - a[0]);
      const n = [Math.sin(ang), -Math.cos(ang)]; // outward for a CCW ring
      if (n[1] < -0.8) {
        if (!mainEdge) mainEdge = { a, c, len, ang, n };
        else
          mainEdge = {
            a: mainEdge.a,
            c,
            len: mainEdge.len + len,
            ang: Math.atan2(c[1] - mainEdge.a[1], c[0] - mainEdge.a[0]),
            n: mainEdge.n,
          };
      }
      const nb = Math.round(len / BAY);
      for (let j = 0; j <= nb; j++) {
        const t = j / nb;
        const corner = j === 0 || j === nb;
        const x = a[0] + (c[0] - a[0]) * t + n[0] * (corner ? 0.55 : 0.75),
          y = a[1] + (c[1] - a[1]) * t + n[1] * (corner ? 0.55 : 0.75);
        const F = T.frame(x, y, ang);
        if (corner) F.box(batch, stone, 0, 0, Z1, 1.6, 1.6, Z2 - Z1);
        else T.column(F, batch, stone, 0, 0, Z1, Z2 - Z1, 0.62, 'ionic', 12);
      }
      // continuous ground-floor plinth band and bronze canopy over the display windows
      const F = T.frame((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, ang);
      F.box(batch, stoneDk, 0, -0.35, Z1 - 0.6, len, 1.2, 0.6);
      F.box(batch, bronze, 0, -1.3, 4.9, len - 1.0, 2.2, 0.25);
    }
    // main Oxford Street entrance: recessed bronze-and-glass screen, canopy and Queen of Time
    if (mainEdge) {
      const { a, c, ang, n } = mainEdge;
      const mx = (a[0] + c[0]) / 2,
        my = (a[1] + c[1]) / 2;
      const F = T.frame(mx + n[0] * 0.05, my + n[1] * 0.05, ang); // -v is outward here
      const vo = -1; // outward sign in this frame (v axis = left of the edge = inward)
      F.box(batch, bronze, 0, vo * 0.02, 0, 9.0, 0.1, Z2 - 0.8);
      F.box(batch, kit.mat('glass'), 0, vo * 0.1, 7.0, 7.0, 0.06, Z2 - 8.6);
      F.box(
        batch,
        kit.mat('#2a3640', { roughness: 0.2, metalness: 0.3 }),
        0,
        vo * 0.08,
        0.3,
        7.6,
        0.06,
        5.8,
      );
      F.box(batch, bronze, 0, vo * 2.2, 6.0, 10.0, 4.2, 0.45); // entrance canopy
      F.box(batch, gold, 0, vo * 2.2, 6.45, 10.0, 4.2, 0.12);
      const [qx, qy] = F.P(0, vo * 1.2);
      F.box(batch, stoneDk, 0, vo * 1.2, 6.5, 2.6, 1.6, 1.0);
      T.figure(batch, gold, qx, qy, 7.5, 3.6, ang + Math.PI / 2);
      // Queen of Time's clock in its bronze surround
      T.put(
        batch,
        gold,
        new THREE.CylinderGeometry(0.75, 0.75, 0.2, 16),
        ...F.P(0, vo * 0.7),
        12.2,
        ang,
        1,
        1,
        1,
        0,
        0,
      );
      // flagpoles above the canopies with yellow Selfridges flags
      for (const s of [-3, -2, -1, 1, 2, 3]) {
        const [px, py] = F.P(s * 18, vo * 1.0);
        T.rod(
          batch,
          kit.mat('white'),
          [px, py, 6.0],
          [px + n[0] * 4.5, py + n[1] * 4.5, 8.8],
          0.07,
          0.05,
          5,
        );
        const q0 = [px + n[0] * 2.4, py + n[1] * 2.4],
          q1 = [px + n[0] * 4.4, py + n[1] * 4.4];
        batch.quad(
          yellow,
          [q0[0], q0[1], 6.1],
          [q1[0], q1[1], 7.4],
          [q1[0], q1[1], 8.7],
          [q0[0], q0[1], 7.4],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    g.add(batch.toGroup('selfridges'));
    return g;
  },
};
