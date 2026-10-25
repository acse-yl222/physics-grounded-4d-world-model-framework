// Buckingham Palace. The east front facing The Mall and the Victoria Memorial
// was refaced in Portland stone by Sir Aston Webb (completed November 1913)
// over Edward Blore's 1850 east wing: rusticated ground floor with the central
// archways into the quadrangle, giant Corinthian order through the two upper
// floors, a central pediment with the royal arms, the balcony over the centre
// arch, a balustraded roofline and the flagstaff. The other ranges around the
// quadrangle (Nash / Blore, Bath stone) are modelled from the Overture parts
// with a painted classical facade; the garden-front bow carries a shallow dome.
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
  id: 'buckingham_palace',
  name: 'Buckingham Palace',
  claims: ['2f30b3f5-eb22-4154-9404-68a976499e6d'],
  references: [
    {
      title: 'Buckingham Palace - Wikipedia (Schools edition mirror)',
      url: 'https://dlab.epfl.ch/wikispeedia/wpcd/wp/b/Buckingham_Palace.htm',
      used_for:
        'Blore 1850 east front redesigned by Aston Webb in 1913 in Portland stone as a backdrop to the Victoria Memorial; Nash west front, quadrangle plan',
    },
    {
      title: 'Buckingham Palace Architecture - thingstodoinlondon',
      url: 'https://www.thingstodoinlondon.com/attractions/buckingham-palace/architecture/',
      used_for:
        'central pediment with royal arms flanked by lion and unicorn, the balcony above the central entrance, symmetrical facade',
    },
    {
      title: 'The Victoria Memorial and Buckingham Palace 1913 - Royal Collection Trust',
      url: 'https://col.rct.uk/collection/2303715-e/the-victoria-memorial-and-buckingham-palace-1913',
      used_for: 'east front composition as completed in 1913',
    },
    {
      title: 'Buckingham Palace - Designing Buildings Wiki',
      url: 'https://www.designingbuildings.co.uk/wiki/Buckingham_Palace',
      used_for: 'building history: Nash/Blore wings around the quadrangle',
    },
  ],
  notes:
    'Plan, quadrangle and wing heights from the Overture footprint and its 12 parts; the unparted east, north and ' +
    'south ranges use 22 m. East-front bay rhythm, pavilion widths, column positions and pediment size are ' +
    'proportioned from memory of photographs (no measured elevation found); sculpture, the lion/unicorn and the ' +
    'arms are painted. The forecourt (gravel, railings, sentry boxes) is an approximate 20 m deep strip; the ' +
    'Victoria Memorial lies outside the domain and is not modelled. The east end of the palace extends ~100 m past ' +
    'the x = 4000 m domain edge and is kept whole.',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const pal = byId['2f30b3f5-eb22-4154-9404-68a976499e6d'];
    const portland = kit.mat('#e2dccb', { roughness: 0.8 });
    const portlandDk = kit.mat('#cfc8b4', { roughness: 0.85 });
    const bath = kit.mat('#d8c9a4', { roughness: 0.85 });
    const lead = kit.mat('#8a9290', { roughness: 0.7 });
    const voidm = kit.mat('#2c3034', { roughness: 0.6 });
    const gold = kit.mat('gold');
    const gravel = kit.mat('#d9cdb0', { roughness: 1 });
    const H = 22.0; // unparted ranges
    const BAYW = 4.4,
      FT = 22.4; // east-front tile: one bay wide, full height
    // ---- painted materials ----
    const front = kit.paintedMaterial('buckingham_palace:east_bay', 176, 896, (c, w, h) => {
      const m = h / FT;
      const Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#e3ddcc', 'rgba(110,100,80,0.25)', 0.6 * m, w / 2, 0.53);
      // rusticated ground floor
      c.fillStyle = '#d9d2bf';
      c.fillRect(0, Y(7.2), w, 7.2 * m);
      c.fillStyle = 'rgba(70,64,52,0.55)';
      for (let z = 0.6; z < 7.2; z += 0.6) c.fillRect(0, Y(z), w, 2);
      B.sash(c, w * 0.31, Y(5.6), w * 0.38, 4.4 * m, {
        cols: 2,
        rows: 4,
        arch: true,
        frame: '#ece7da',
      });
      c.fillStyle = '#cfc8b3';
      c.fillRect(w * 0.44, Y(6.15), w * 0.12, 0.6 * m); // keystone
      // giant pilaster at the bay edge (half on each side)
      const pil = (x) => {
        c.fillStyle = '#ebe6d8';
        c.fillRect(x, Y(19.8), w * 0.13, 12.6 * m);
        c.fillStyle = 'rgba(0,0,0,0.08)';
        c.fillRect(x + w * 0.11, Y(19.8), w * 0.02, 12.6 * m);
        c.fillStyle = '#d8d0bb';
        c.fillRect(x - w * 0.02, Y(19.8), w * 0.17, 0.9 * m); // capital
      };
      pil(-w * 0.065);
      pil(w - w * 0.065);
      // piano nobile: tall window with alternating pediment
      c.fillStyle = '#d4ccb6';
      c.fillRect(w * 0.22, Y(14.0), w * 0.56, 0.35 * m);
      c.beginPath();
      c.moveTo(w * 0.2, Y(14.0));
      c.lineTo(w * 0.5, Y(15.1));
      c.lineTo(w * 0.8, Y(14.0));
      c.fill();
      B.sash(c, w * 0.3, Y(13.6), w * 0.4, 5.6 * m, { cols: 2, rows: 5, frame: '#ece7da' });
      c.fillStyle = '#d4ccb6';
      c.fillRect(w * 0.26, Y(8.0), w * 0.48, 0.3 * m);
      // second floor
      B.sash(c, w * 0.32, Y(18.6), w * 0.36, 2.9 * m, { cols: 2, rows: 3, frame: '#ece7da' });
      // entablature + balustrade
      c.fillStyle = '#d6cfba';
      c.fillRect(0, Y(21.0), w, 1.2 * m);
      c.fillStyle = 'rgba(0,0,0,0.12)';
      c.fillRect(0, Y(20.05), w, 3);
      c.fillStyle = '#e8e2d3';
      c.fillRect(0, Y(FT), w, (FT - 21.0) * m);
    });
    const NT = 24.0;
    const nash = kit.paintedMaterial('buckingham_palace:bath_bay', 288, 768, (c, w, h) => {
      const m = h / NT;
      const Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#d9caa6', 'rgba(110,90,60,0.25)', 0.55 * m, w / 4, 0.71);
      for (let k = 0; k < 2; k++) {
        const x0 = (k * w) / 2,
          bw = w / 2;
        c.fillStyle = 'rgba(255,250,235,0.25)';
        c.fillRect(x0, Y(19.6), bw * 0.1, 12.6 * m); // pilaster
        B.sash(c, x0 + bw * 0.3, Y(5.4), bw * 0.4, 3.8 * m, { cols: 2, rows: 3, arch: true });
        B.sash(c, x0 + bw * 0.28, Y(13.2), bw * 0.44, 5.0 * m, { cols: 2, rows: 4 });
        c.fillStyle = '#c8b68e';
        c.fillRect(x0 + bw * 0.22, Y(13.7), bw * 0.56, 0.4 * m);
        B.sash(c, x0 + bw * 0.31, Y(17.6), bw * 0.38, 2.8 * m, { cols: 2, rows: 3 });
      }
      c.fillStyle = 'rgba(90,70,40,0.35)';
      c.fillRect(0, Y(7.0), w, 0.25 * m);
      c.fillStyle = '#cdbb93';
      c.fillRect(0, Y(21.2), w, 1.4 * m); // cornice
      c.fillStyle = '#d9caa6';
      c.fillRect(0, Y(NT), w, (NT - 21.2) * m);
      c.fillStyle = 'rgba(80,60,30,0.45)';
      for (let x = 4; x < w; x += 9) c.fillRect(x, Y(23.4), 4, 1.8 * m); // balusters
      c.fillRect(0, Y(23.5), w, 3);
    });
    const arms = kit.paintedMaterial('buckingham_palace:arms', 256, 96, (c, w, h) => {
      c.fillStyle = '#ddd6c3';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#c9c1aa';
      c.beginPath();
      c.ellipse(w / 2, h * 0.58, w * 0.08, h * 0.32, 0, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = '#b9b09a';
      c.fillRect(w * 0.33, h * 0.45, w * 0.1, h * 0.45); // lion
      c.fillRect(w * 0.57, h * 0.45, w * 0.1, h * 0.45); // unicorn
      c.fillStyle = '#c4a24c';
      c.fillRect(w * 0.47, h * 0.2, w * 0.06, h * 0.12); // crown
    });
    const union = kit.paintedMaterial(
      'buckingham_palace:flag',
      120,
      60,
      (c, w, h) => {
        c.fillStyle = '#1f3a7a';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = '#ffffff';
        c.lineWidth = 12;
        c.beginPath();
        c.moveTo(0, 0);
        c.lineTo(w, h);
        c.moveTo(w, 0);
        c.lineTo(0, h);
        c.stroke();
        c.strokeStyle = '#c8102e';
        c.lineWidth = 4;
        c.stroke();
        c.fillStyle = '#ffffff';
        c.fillRect(w / 2 - 10, 0, 20, h);
        c.fillRect(0, h / 2 - 10, w, 20);
        c.fillStyle = '#c8102e';
        c.fillRect(w / 2 - 6, 0, 12, h);
        c.fillRect(0, h / 2 - 6, w, 12);
      },
      { side: THREE.DoubleSide },
    );
    const railing = kit.paintedMaterial(
      'buckingham_palace:railing',
      128,
      128,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.fillStyle = '#1b1c1e';
        for (let x = 2; x < w; x += 8) c.fillRect(x, 6, 3, h);
        c.fillRect(0, 14, w, 4);
        c.fillRect(0, h - 10, w, 10);
        c.fillStyle = '#c9a646';
        for (let x = 1; x < w; x += 8) c.fillRect(x, 0, 5, 7);
      },
      { transparent: true, alphaTest: 0.5, side: THREE.DoubleSide },
    );

    // ---- geometry helpers ----
    const inRing = (p, r) => {
      let ins = false;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const a = r[i],
          b = r[j];
        if (
          a[1] > p[1] !== b[1] > p[1] &&
          p[0] < ((b[0] - a[0]) * (p[1] - a[1])) / (b[1] - a[1]) + a[0]
        )
          ins = !ins;
      }
      return ins;
    };
    const inPoly = (p, poly) => inRing(p, poly[0]) && !poly.slice(1).some((h) => inRing(p, h));
    const mainPoly = pal.polys[0];
    const parts = (pal.parts ?? []).map((p) => ({ ...p, poly: p.polys[0] }));
    const partAt = (p) => parts.find((q) => inPoly(p, q.poly));

    // ---- east front frame ----
    const outer = mainPoly[0];
    let best = null;
    for (let k = 0; k < outer.length; k++) {
      const a = outer[k],
        b = outer[(k + 1) % outer.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const n = [(b[1] - a[1]) / len, -(b[0] - a[0]) / len];
      if (n[0] * 0.8 + n[1] * 0.6 > 0.85 && (!best || len > best.len)) best = { len, n };
    }
    const nF = best.n;
    const angF = Math.atan2(-nF[0], nF[1]); // frame whose +v is the outward normal
    const cu = Math.cos(angF),
      su = Math.sin(angF);
    const toUV = (p) => [p[0] * cu + p[1] * su, -p[0] * su + p[1] * cu];
    const vMax = Math.max(...outer.map((p) => toUV(p)[1]));
    const frontPts = outer.filter((p) => toUV(p)[1] > vMax - 3.5);
    const fu = frontPts.map((p) => toUV(p)[0]);
    const u0 = Math.min(...fu),
      u1 = Math.max(...fu);
    const Lf = u1 - u0;
    const cF = [((u0 + u1) / 2) * cu - vMax * su, ((u0 + u1) / 2) * su + vMax * cu];
    const F = T.frame(cF[0], cF[1], angF); // u along the front, v outward, wall face at v = 0
    const isFrontEdge = (a, b) => {
      const ua = toUV(a),
        ub = toUV(b);
      return ua[1] > vMax - 3.6 && ub[1] > vMax - 3.6;
    };

    // ---- unparted ranges: walls + roof ----
    for (const ring of mainPoly)
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 0.05 || isFrontEdge(a, b)) continue;
        const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        const inward = [mid[0] - ((b[1] - a[1]) / len) * 0.6, mid[1] + ((b[0] - a[0]) / len) * 0.6];
        if (partAt(inward)) continue;
        B.wallsTex(batch, nash, [a, b, b], 0, H, 9, {
          tileH: NT,
          vBase: H - NT,
          skip: (i) => i !== 0,
        });
      }
    {
      // roof of the unparted area: triangulate, subdivide and drop cells inside parts
      const contour = mainPoly[0].map(([x, y]) => new THREE.Vector2(x, y));
      const holes = mainPoly.slice(1).map((r) => r.map(([x, y]) => new THREE.Vector2(x, y)));
      const pts = [...contour, ...holes.flat()];
      const tris = THREE.ShapeUtils.triangulateShape(contour, holes);
      const verts = [],
        uvs = [],
        idx = [];
      const emit = (a, b, c) => {
        const cen = [(a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3];
        if (partAt(cen)) return;
        const n = verts.length;
        for (const p of [a, b, c]) {
          verts.push([p[0], p[1], H]);
          uvs.push([p[0] / 8, p[1] / 8]);
        }
        idx.push(n, n + 1, n + 2);
      };
      const sub = (a, b, c, depth) => {
        const lab = Math.hypot(a[0] - b[0], a[1] - b[1]),
          lbc = Math.hypot(b[0] - c[0], b[1] - c[1]),
          lca = Math.hypot(c[0] - a[0], c[1] - a[1]);
        const mx = Math.max(lab, lbc, lca);
        if (mx < 3 || depth > 9) return emit(a, b, c);
        // split the longest edge
        if (mx === lab) {
          const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          sub(a, m, c, depth + 1);
          sub(m, b, c, depth + 1);
        } else if (mx === lbc) {
          const m = [(b[0] + c[0]) / 2, (b[1] + c[1]) / 2];
          sub(a, b, m, depth + 1);
          sub(a, m, c, depth + 1);
        } else {
          const m = [(c[0] + a[0]) / 2, (c[1] + a[1]) / 2];
          sub(a, b, m, depth + 1);
          sub(m, b, c, depth + 1);
        }
      };
      for (const t of tris)
        sub([pts[t[0]].x, pts[t[0]].y], [pts[t[1]].x, pts[t[1]].y], [pts[t[2]].x, pts[t[2]].y], 0);
      batch.add(lead, verts, uvs, idx);
    }
    // ---- parts ----
    for (const p of parts) {
      let ring = p.poly[0].slice();
      if (kit.ringArea(ring) < 0) ring.reverse();
      const isBow = p.roof === 'dome';
      B.wallsTex(batch, nash, ring, 0, p.h, isBow ? 4.5 : 9, { tileH: NT, vBase: p.h - NT });
      if (isBow) {
        const fr = kit.ringFrame(ring);
        const r = Math.max(fr.length, fr.width) / 2;
        kit.cap(batch, lead, [[ring]], p.h);
        T.put(
          batch,
          lead,
          new THREE.SphereGeometry(r * 0.92, 20, 6, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
            Math.PI / 2,
          ),
          fr.cx,
          fr.cy,
          p.h,
          0,
          1,
          1,
          (p.roofH || 3) / (r * 0.92),
        );
      } else if (p.roof === 'gabled') {
        const fr = kit.ringFrame(ring);
        B.wallsTex(batch, bath, ring, p.h - 0.01, p.h, 4);
        kit.pitchedRoof(batch, lead, bath, ring, fr.angle, p.h, p.roofH || 3, 'hipped', {
          overhang: 0.2,
        });
      } else kit.cap(batch, lead, [[ring]], p.h);
      // step walls where a lower part meets the taller unparted ranges
      if (p.h < H - 0.5)
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k],
            b = ring[(k + 1) % ring.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          if (len < 0.3) continue;
          const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          const out = [mid[0] + ((b[1] - a[1]) / len) * 0.8, mid[1] - ((b[0] - a[0]) / len) * 0.8];
          if (!inPoly(out, mainPoly) || partAt(out)) continue;
          // wall faces into the lower part: reverse edge direction
          B.wallsTex(batch, nash, [b, a, a], p.h, H, 9, {
            tileH: NT,
            vBase: H - NT,
            skip: (i) => i !== 0,
          });
        }
    }

    // ---- Aston Webb east front ----
    const HF = 21.0; // top of main cornice
    const face = (ua, ub, v, z0, z1, mat = front, tile = BAYW) => {
      const a = F.P(ua, v),
        b = F.P(ub, v);
      B.wallsTex(batch, mat, [b, a, a], z0, z1, tile, {
        tileH: FT,
        vBase: 0,
        skip: (i) => i !== 0,
      });
    };
    const block = (ua, ub, v0, v1, z1) => {
      face(ua, ub, v1, 0, z1);
      // side returns
      const a0 = F.P(ua, v0),
        a1 = F.P(ua, v1),
        b0 = F.P(ub, v0),
        b1 = F.P(ub, v1);
      B.wallsTex(batch, portland, [a1, a0, a0], 0, z1, 4, { skip: (i) => i !== 0 });
      B.wallsTex(batch, portland, [b0, b1, b1], 0, z1, 4, { skip: (i) => i !== 0 });
      const d = v1 - v0;
      F.box(batch, lead, (ua + ub) / 2, v0 + d / 2, z1 - 0.02, ub - ua, d, 0.02);
    };
    // back block filling the band behind the straight front line
    F.box(batch, portland, 0, -2.5, 0, Lf - 0.2, 5, HF - 0.05);
    const half = Lf / 2;
    const endW = 14,
      cenW = 26;
    // main face segments between pavilions
    for (const s of [-1, 1]) {
      const a = s * (cenW / 2),
        b = s * (half - endW);
      face(Math.min(a, b), Math.max(a, b), 0, 0, HF);
      // end pavilions: project 1.2 m, attic storey above the cornice
      const pa = s * (half - endW),
        pb = s * half;
      block(Math.min(pa, pb), Math.max(pa, pb), 0, 1.2, HF);
      F.box(batch, portland, s * (half - endW / 2), 0.2, HF, endW - 1.0, 2.0, 3.0);
      F.box(batch, portlandDk, s * (half - endW / 2), 0.25, HF + 3.0, endW - 0.6, 2.2, 0.5);
      for (const k of [0.15, 0.38, 0.62, 0.85]) {
        const uu = s * (half - endW) + s * endW * k;
        T.column(F, batch, portland, uu, 1.55, 7.2, HF - 1.2 - 7.2, 0.42, 'corinthian', 10);
      }
      F.box(batch, portlandDk, s * (half - endW / 2), 0.95, HF - 1.2, endW + 0.2, 1.9, 1.2);
    }
    // centre pavilion: projects 2 m, coupled columns, pediment, balcony and arches
    block(-cenW / 2, cenW / 2, 0, 2.0, HF);
    for (const uu of [-11.6, -10.3, -4.4, -3.1, 3.1, 4.4, 10.3, 11.6])
      T.column(F, batch, portland, uu, 2.5, 7.2, HF - 1.2 - 7.2, 0.45, 'corinthian', 12);
    F.box(batch, portlandDk, 0, 1.7, HF - 1.2, cenW + 0.4, 2.4, 1.2);
    for (const uu of [-6.0, 0, 6.0]) {
      const sh = T.archShape(3.8, 0.01, []);
      const arch = new THREE.Shape();
      arch.moveTo(-1.9, 0);
      arch.lineTo(1.9, 0);
      arch.lineTo(1.9, 4.2);
      arch.absarc(0, 4.2, 1.9, 0, Math.PI, false);
      arch.lineTo(-1.9, 0);
      void sh;
      T.slab(F, batch, voidm, arch, uu, 2.03, 0, 0.04, 10);
    }
    // pediment with the royal arms
    {
      const ped = new THREE.Shape([
        new THREE.Vector2(-13.4, 0),
        new THREE.Vector2(13.4, 0),
        new THREE.Vector2(0, 4.6),
      ]);
      T.slab(F, batch, portland, ped, 0, 1.4, HF, 2.6);
      const a = F.P(8.5, 2.72),
        b = F.P(-8.5, 2.72);
      batch.quad(
        arms,
        [a[0], a[1], HF + 0.35],
        [b[0], b[1], HF + 0.35],
        [b[0], b[1], HF + 3.0],
        [a[0], a[1], HF + 3.0],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // the balcony over the centre arch
    F.box(batch, portlandDk, 0, 3.1, 7.1, 9.6, 2.4, 0.45);
    for (const uu of [-3.8, -1.3, 1.3, 3.8]) F.box(batch, portlandDk, uu, 3.0, 6.1, 0.5, 1.6, 1.0);
    {
      const z = 7.55;
      const p = [F.P(-4.7, 4.2), F.P(4.7, 4.2), F.P(-4.7, 2.0), F.P(4.7, 2.0)];
      B.balustrade(batch, portland, p[0], p[1], z, 1.05, 0.4);
      B.balustrade(batch, portland, p[2], p[0], z, 1.05, 0.4);
      B.balustrade(batch, portland, p[1], p[3], z, 1.05, 0.4);
    }
    // main cornice and roof balustrade with urns
    F.box(batch, portlandDk, 0, 0.3, HF - 0.6, Lf - 2 * endW + 0.2, 1.0, 0.6);
    for (const [ua, ub, v] of [
      [-half + endW, -cenW / 2, 0.15],
      [cenW / 2, half - endW, 0.15],
    ]) {
      B.balustrade(batch, portland, F.P(ua, v), F.P(ub, v), HF, 1.1, 0.5);
      for (let uu = ua; uu <= ub + 0.01; uu += (ub - ua) / 4)
        F.box(batch, portland, uu, v, HF, 0.7, 0.7, 1.5);
    }
    // flagstaff with the Union Flag
    {
      const [x, y] = F.P(0, -6);
      T.rod(batch, kit.mat('white'), [x, y, HF], [x, y, HF + 13], 0.12, 0.08, 6);
      const a = F.P(0, -6),
        b = F.P(5.4, -6);
      batch.quad(
        union,
        [a[0], a[1], HF + 10.2],
        [b[0], b[1], HF + 10.2],
        [b[0], b[1], HF + 12.9],
        [a[0], a[1], HF + 12.9],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // forecourt: gravel, railings with gilded gates, sentry boxes
    {
      const D = 20;
      const q = [F.P(-half - 3, 0.05), F.P(half + 3, 0.05), F.P(half + 3, D), F.P(-half - 3, D)];
      batch.add(
        gravel,
        q.map(([x, y]) => [x, y, 0.06]),
        q.map(([x, y]) => [x / 6, y / 6]),
        [0, 1, 2, 0, 2, 3],
      );
      const rail = (ua, ub) => {
        const a = F.P(ua, D),
          b = F.P(ub, D);
        const len = ub - ua;
        batch.quad(
          railing,
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], 2.6],
          [a[0], a[1], 2.6],
          [0, 0],
          [len / 2.6, 0],
          [len / 2.6, 1],
          [0, 1],
        );
      };
      const piers = [-half - 3, -30, -9, -4, 4, 9, 30, half + 3];
      for (let k = 0; k < piers.length - 1; k++) rail(piers[k] + 0.8, piers[k + 1] - 0.8);
      for (const uu of piers) {
        F.box(batch, portland, uu, D, 0, 1.6, 1.6, 3.4);
        F.box(batch, gold, uu, D, 3.4, 0.8, 0.8, 0.8);
      }
      for (const s of [-1, 1]) F.box(batch, portland, s * (half + 3), D / 2, 0, 1.0, D, 1.0);
      for (const uu of [-14, -8, 8, 14])
        F.box(batch, kit.mat('#2a2d30'), uu, 3.5, 0, 1.3, 1.3, 2.8);
    }
    g.add(batch.toGroup('buckingham_palace'));
    return g;
  },
};
