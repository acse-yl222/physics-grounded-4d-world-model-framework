// London Victoria station: the two former companies' stations side by side on
// the forecourt (Terminus Place). West: the LB&SCR "Brighton side" by Sir
// Charles Morgan (1906-08) - red brick with stone bands, ashlar centrepiece and
// end pavilions, five main storeys with two more in a French mansard roof, the
// lower floors hidden by a projecting iron-and-timber canopy, and a large clock
// set in a scroll; behind it the concourse with five ridged roofs running back
// on cast-iron columns. East: the SE&CR "Chatham side" frontage by A. W.
// Blomfield (1909-10), Portland stone Edwardian Baroque with H. C. Fehr's
// mermaid caryatids holding the pediments, in front of John Fowler's 1862
// train shed.
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
  id: 'victoria_station',
  name: 'Victoria Station',
  claims: [
    '160e783b-6903-4167-9405-46269ea09d30', // Victoria Station (frontages, concourse, Wilton Road range)
    'ac3d2c7f-62cc-4092-9bc4-b4715b99bd70', // train shed roof (west span)
    '3fbdf097-fc5e-4b81-9945-add8ecd9b420', // train shed roof (east span)
  ],
  references: [
    {
      title: 'The history of London Victoria station - Network Rail',
      url: 'https://www.networkrail.co.uk/who-we-are/our-history/iconic-infrastructure/the-history-of-london-victoria-station/',
      used_for:
        'LB&SCR frontage in red brick with a large clock set in a scroll; Chatham side Portland stone frontage with mermaid caryatids; Brighton-side roof removed for Victoria Place',
    },
    {
      title:
        'Victoria Railway Station (former LB&SCR station and rear concourse) - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101389322-victoria-railway-station-the-former-london-brighton-and-south-coast-railway-station-and-rear-concourse-warwick-ward',
      used_for:
        'ashlar centrepiece and end pavilions, red brick with stone bands, 5 storeys plus 2 attic storeys in the mansard, canopy over the bottom 2 storeys, five ridged concourse roofs on cast-iron Corinthian columns',
    },
    {
      title: 'Victoria Station - Victorian Web',
      url: 'https://victorianweb.org/technology/railways/75.html',
      used_for: 'Blomfield / Ancell Chatham frontage, Fowler 1862 south-east train shed',
    },
    {
      title: 'Architectural Sculpture at Victoria Station by H. C. Fehr - Victorian Web',
      url: 'https://victorianweb.org/sculpture/fehr/5.html',
      used_for: 'pediments each held by a pair of mermaid caryatids with a wreath and cartouche',
    },
  ],
  notes:
    'Plan split from the Overture outline: Brighton side west of the chord between the two frontages, Chatham side ' +
    "and the Wilton Road range east of it; the two claimed roof footprints are modelled as Fowler's train shed as " +
    'two segmental glazed spans (span form and 18 m crown height assumed). Brighton frontage height (20.5 m + mansard ' +
    'to ~27 m), Chatham frontage height (15 m), bay rhythm, canopy depth and the concourse ridge heights are estimates. ' +
    'Sculpture (caryatids) is schematic; the Grosvenor Hotel and Victoria Place are separate footprints not claimed here.',
  build({ THREE, kit, byId }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const main = byId['160e783b-6903-4167-9405-46269ea09d30'];
    const shedW = byId['ac3d2c7f-62cc-4092-9bc4-b4715b99bd70'];
    const shedE = byId['3fbdf097-fc5e-4b81-9945-add8ecd9b420'];
    const stone = kit.mat('portland_stone');
    const stoneDk = kit.mat('#cbc4b0');
    const brick = kit.mat('#9a4a36');
    const slate = kit.mat('slate');
    const iron = kit.mat('#3a4a45', { roughness: 0.6, metalness: 0.3 });
    const glassRoof = kit.paintedMaterial(
      'victoria_station:glazing',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#7f9099';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#9fb0b6';
        for (let x = 0; x < w; x += 16) c.fillRect(x + 2, 0, 12, h);
        c.fillStyle = '#3d4a4c';
        c.fillRect(0, 0, 10, h); // main rib
        for (let y = 0; y < h; y += 64) c.fillRect(0, y, w, 3);
      },
      { side: THREE.DoubleSide, roughness: 0.6, metalness: 0 },
    );
    const shedRoof = kit.paintedMaterial(
      'victoria_station:shed',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#4f555b';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#6f7f86';
        c.fillRect(0, h * 0.25, w, h * 0.5); // glazed central band
        c.fillStyle = '#8a9a9f';
        for (let x = 0; x < w; x += 14) c.fillRect(x + 3, h * 0.25, 8, h * 0.5);
        c.fillStyle = '#2f3437';
        c.fillRect(0, 0, 12, h); // arched rib
        c.fillRect(0, h * 0.25, w, 3);
        c.fillRect(0, h * 0.75, w, 3);
      },
      { side: THREE.DoubleSide, roughness: 0.75, metalness: 0 },
    );
    const FTH = 20.5;
    const brickBay = kit.paintedMaterial('victoria_station:brick', 144, 656, (c, w, h) => {
      const m = h / FTH,
        Y = (z) => h - z * m;
      c.fillStyle = '#9a4b37';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.77);
      for (let y = 0; y < h; y += 3)
        for (let x = (y / 3) % 2 ? 0 : 4; x < w; x += 8) {
          c.fillStyle = `rgba(${60 + r() * 50},${25 + r() * 20},${20 + r() * 15},0.35)`;
          c.fillRect(x, y, 7, 2);
        }
      c.fillStyle = '#e0d8c4';
      for (const z of [7.6, 11.2, 14.6, 17.8]) c.fillRect(0, Y(z), w, 0.35 * m); // stone bands
      c.fillRect(0, Y(FTH), w, 1.2 * m); // cornice
      c.fillStyle = '#cfc6b1';
      c.fillRect(0, Y(7.6), w, 7.6 * m); // stone ground floors (behind canopy)
      B.sash(c, w * 0.18, Y(6.8), w * 0.64, 5.0 * m, {
        arch: true,
        cols: 3,
        rows: 3,
        frame: '#e8e2d4',
        glass: '#2c363d',
      });
      for (const [za, zb] of [
        [8.3, 10.8],
        [11.9, 14.2],
        [15.3, 17.5],
      ]) {
        c.fillStyle = '#e0d8c4';
        c.fillRect(w * 0.27, Y(zb + 0.3), w * 0.46, (zb - za + 0.6) * m);
        B.sash(c, w * 0.31, Y(zb), w * 0.38, (zb - za) * m, {
          cols: 2,
          rows: 3,
          frame: '#efe9dc',
          glass: '#2c363d',
        });
      }
    });
    const ashlarBay = kit.paintedMaterial('victoria_station:ashlar', 144, 656, (c, w, h) => {
      const m = h / FTH,
        Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#ddd5c0', 'rgba(110,100,80,0.3)', 0.55 * m, w / 2, 0.13);
      c.fillStyle = 'rgba(80,70,55,0.4)';
      for (let z = 0.55; z < 7.6; z += 0.55) c.fillRect(0, Y(z), w, 2);
      B.sash(c, w * 0.18, Y(6.8), w * 0.64, 5.0 * m, {
        arch: true,
        cols: 3,
        rows: 3,
        frame: '#efe9dc',
        glass: '#2c363d',
      });
      c.fillStyle = '#ebe5d6';
      c.fillRect(0, Y(19.2), w * 0.1, 11.4 * m);
      c.fillRect(w * 0.9, Y(19.2), w * 0.1, 11.4 * m);
      B.sash(c, w * 0.3, Y(13.8), w * 0.4, 5.4 * m, {
        cols: 2,
        rows: 4,
        frame: '#efe9dc',
        glass: '#2c363d',
        arch: true,
      });
      c.fillStyle = '#cfc6b1';
      c.fillRect(w * 0.24, Y(14.4), w * 0.52, 0.5 * m);
      B.sash(c, w * 0.32, Y(17.9), w * 0.36, 2.6 * m, {
        cols: 2,
        rows: 2,
        frame: '#efe9dc',
        glass: '#2c363d',
      });
      c.fillStyle = '#d0c8b3';
      c.fillRect(0, Y(FTH), w, 1.3 * m);
    });
    const CTH = 15.0;
    const chatham = kit.paintedMaterial('victoria_station:chatham', 192, 480, (c, w, h) => {
      const m = h / CTH,
        Y = (z) => h - z * m;
      B.ashlar(c, w, h, '#e2dccb', 'rgba(110,100,80,0.3)', 0.6 * m, w / 2, 0.21);
      c.fillStyle = 'rgba(80,70,55,0.35)';
      for (let z = 0.6; z < 8.6; z += 0.6) c.fillRect(0, Y(z), w, 2);
      // big arched ground-floor opening with keystone
      c.fillStyle = '#d4ccb7';
      c.beginPath();
      c.moveTo(w * 0.14, Y(0));
      c.lineTo(w * 0.14, Y(5.4));
      c.arc(w / 2, Y(5.4), w * 0.36, Math.PI, 0);
      c.lineTo(w * 0.86, Y(0));
      c.fill();
      B.sash(c, w * 0.2, Y(7.8), w * 0.6, 7.8 * m, {
        arch: true,
        cols: 4,
        rows: 4,
        frame: '#3d3f3a',
        glass: '#28323a',
      });
      c.fillStyle = '#cfc7b1';
      c.fillRect(w * 0.45, Y(8.4), w * 0.1, 1.0 * m);
      // upper storey window between paired pilasters
      c.fillStyle = '#eee9dc';
      c.fillRect(0, Y(13.4), w * 0.08, 4.6 * m);
      c.fillRect(w * 0.92, Y(13.4), w * 0.08, 4.6 * m);
      B.sash(c, w * 0.3, Y(12.8), w * 0.4, 3.2 * m, {
        cols: 2,
        rows: 3,
        frame: '#efe9dc',
        glass: '#28323a',
      });
      c.fillStyle = '#d6cfba';
      c.fillRect(0, Y(13.9), w, 0.9 * m);
      c.fillStyle = 'rgba(70,60,45,0.45)';
      for (let x = 5; x < w; x += 12) c.fillRect(x, Y(14.9), 5, 0.9 * m);
    });
    const lettering = kit.paintedMaterial('victoria_station:sec_lettering', 1024, 48, (c, w, h) => {
      c.fillStyle = '#dfd8c6';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#4a4436';
      c.font = 'bold 34px serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('SOUTH EASTERN AND CHATHAM RAILWAY', w / 2, h / 2 + 2);
    });
    const clockFace = kit.paintedMaterial('victoria_station:clock', 128, 128, (c, w, h) => {
      c.fillStyle = '#d8cfb6';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#f4f1e8';
      c.beginPath();
      c.arc(w / 2, h / 2, w * 0.42, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#222';
      c.lineWidth = 4;
      c.stroke();
      for (let k = 0; k < 12; k++) {
        const a = (k * Math.PI) / 6;
        c.beginPath();
        c.moveTo(w / 2 + Math.cos(a) * w * 0.34, h / 2 + Math.sin(a) * w * 0.34);
        c.lineTo(w / 2 + Math.cos(a) * w * 0.4, h / 2 + Math.sin(a) * w * 0.4);
        c.stroke();
      }
      c.beginPath();
      c.moveTo(w / 2, h / 2);
      c.lineTo(w / 2, h * 0.2);
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.7, h / 2);
      c.stroke();
    });

    // ---- station frame: u along the platforms (towards the forecourt), v across (west +) ----
    const ang = Math.atan2(-1204.89 + 1299.08, 3921.39 - 3877.7);
    const C = [3905, -1270];
    const F = T.frame(C[0], C[1], ang);
    const cu = Math.cos(ang),
      su = Math.sin(ang);
    const uOf = (p) => (p[0] - C[0]) * cu + (p[1] - C[1]) * su;
    const clip = (ring, f) => {
      const out = [];
      for (let i = 0; i < ring.length; i++) {
        const a = ring[i],
          b = ring[(i + 1) % ring.length];
        const fa = f(a),
          fb = f(b);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fb >= 0) {
          const t = fa / (fa - fb);
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    // split the main outline along the chord between the two frontages
    const ring = main.polys[0][0];
    const near = (p, x, y) => Math.hypot(p[0] - x, p[1] - y) < 0.5;
    const i0 = ring.findIndex((p) => near(p, 3921.39, -1204.89));
    const i1 = ring.findIndex((p) => near(p, 3926.17, -1189.74));
    const seg = (a, b) => {
      const out = [];
      for (let k = a; ; k = (k + 1) % ring.length) {
        out.push(ring[k]);
        if (k === b) break;
      }
      return out;
    };
    const chathamPoly = ccw(seg(i0, i1));
    const brightonPoly = ccw(seg(i1, i0));
    const U_FRONT = 66,
      U_CONC = 18;
    const brFront = ccw(clip(brightonPoly, (p) => uOf(p) - U_FRONT));
    const brConc = ccw(
      clip(
        clip(brightonPoly, (p) => U_FRONT + 0.01 - uOf(p)),
        (p) => uOf(p) - U_CONC,
      ),
    );
    const brSouth = ccw(clip(brightonPoly, (p) => U_CONC + 0.01 - uOf(p)));

    // ---- Brighton side frontage building ----
    B.wallsTex(batch, brickBay, brFront, 0, FTH, 4.5);
    kit.cap(batch, slate, [[brFront]], FTH);
    // identify the forecourt face (edge with the largest u)
    let fe = null;
    for (let k = 0; k < brFront.length; k++) {
      const a = brFront[k],
        b = brFront[(k + 1) % brFront.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const um = (uOf(a) + uOf(b)) / 2;
      if (len > 20 && (!fe || um > fe.um)) fe = { a, b, len, um };
    }
    {
      // mansard roof with dormers, French pavilion roofs over centre and ends
      const fr = kit.ringFrame(brFront);
      kit.pitchedRoof(batch, slate, stone, brFront, fr.angle, FTH, 6.5, 'hipped', {
        overhang: -0.6,
      });
      const fa = Math.atan2(fe.b[1] - fe.a[1], fe.b[0] - fe.a[0]);
      const FF = T.frame((fe.a[0] + fe.b[0]) / 2, (fe.a[1] + fe.b[1]) / 2, fa); // -v outward
      const L = fe.len;
      // ashlar centrepiece and end pavilions projecting 0.8 m
      for (const [c0, w] of [
        [0, 15],
        [-(L / 2 - 5.5), 11],
        [L / 2 - 5.5, 11],
      ]) {
        const a = FF.P(c0 + w / 2, -0.8),
          b = FF.P(c0 - w / 2, -0.8);
        B.wallsTex(batch, ashlarBay, [b, a, a], 0, FTH + 0.6, 3.75, {
          tileH: FTH,
          vBase: 0,
          skip: (i) => i !== 0,
        });
        const a0 = FF.P(c0 + w / 2, 0.2),
          b0 = FF.P(c0 - w / 2, 0.2);
        B.wallsTex(batch, stone, [a, a0, a0], 0, FTH + 0.6, 4, { skip: (i) => i !== 0 });
        B.wallsTex(batch, stone, [b0, b, b], 0, FTH + 0.6, 4, { skip: (i) => i !== 0 });
        // pavilion roof
        const pr = [
          FF.P(c0 - w / 2, -0.8),
          FF.P(c0 + w / 2, -0.8),
          FF.P(c0 + w / 2, 10),
          FF.P(c0 - w / 2, 10),
        ];
        kit.pitchedRoof(batch, slate, stone, ccw(pr), fa, FTH + 0.6, c0 === 0 ? 9 : 8, 'hipped', {
          overhang: 0.2,
        });
        FF.box(batch, stoneDk, c0, -0.5, FTH + 0.2, w + 0.6, 1.6, 0.6);
      }
      // dormers on the front slope
      for (let u = -L / 2 + 12; u <= L / 2 - 12; u += 4.5) {
        if (Math.abs(u) < 9) continue;
        FF.box(batch, stone, u, 1.6, FTH, 1.8, 1.6, 3.2);
        FF.box(batch, kit.mat('dark_glass'), u, 0.79, FTH + 0.6, 1.0, 0.04, 1.8);
      }
      // the large clock set in a scroll on the centrepiece
      const ca = FF.P(1.8, -0.86),
        cb = FF.P(-1.8, -0.86);
      batch.quad(
        clockFace,
        [ca[0], ca[1], 9.2],
        [cb[0], cb[1], 9.2],
        [cb[0], cb[1], 12.8],
        [ca[0], ca[1], 12.8],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      FF.box(batch, stoneDk, 0, -0.95, 12.8, 5.6, 0.4, 1.2);
      // iron-and-timber canopy over the forecourt
      FF.box(batch, iron, 0, -4.5, 7.4, L - 2, 7.4, 0.35);
      FF.box(batch, kit.mat('#d9d4c6'), 0, -8.15, 6.6, L - 2, 0.12, 1.15); // valance
      for (let u = -L / 2 + 3; u <= L / 2 - 3; u += 6) {
        const [x, y] = FF.P(u, -7.6);
        T.rod(batch, iron, [x, y, 0], [x, y, 7.4], 0.14, 0.12, 6);
      }
      FF.box(batch, kit.mat('glass'), 0, -4.5, 7.75, L - 4, 6.4, 0.08);
    }
    // ---- Brighton concourse: walls and five ridged roofs running back ----
    {
      B.wallsTex(batch, brick, brConc, 0, 11, 4);
      const vs = brConc.map((p) => -(p[0] - C[0]) * su + (p[1] - C[1]) * cu);
      const us = brConc.map(uOf);
      const v0 = Math.min(...vs),
        v1 = Math.max(...vs),
        u0 = Math.min(...us),
        u1 = Math.max(...us);
      const n = 5,
        bw = (v1 - v0) / n;
      for (let k = 0; k < n; k++) {
        const va = v0 + k * bw,
          vb = va + bw;
        const r = [F.P(u0, va), F.P(u1, va), F.P(u1, vb), F.P(u0, vb)];
        kit.pitchedRoof(batch, glassRoof, brick, ccw(r), ang, 11, 4.5, 'gabled', { overhang: 0 });
      }
      kit.cap(batch, iron, [[brConc]], 10.9, { down: true });
    }
    // ---- Brighton platform canopies (ridge and furrow on columns) ----
    {
      const vs = brSouth.map((p) => -(p[0] - C[0]) * su + (p[1] - C[1]) * cu);
      const us = brSouth.map(uOf);
      const v0 = Math.min(...vs),
        v1 = Math.max(...vs),
        u0 = Math.min(...us),
        u1 = Math.max(...us);
      const n = Math.round((v1 - v0) / 7);
      const bw = (v1 - v0) / n;
      for (let k = 0; k < n; k++) {
        const va = v0 + k * bw,
          vb = va + bw;
        const r = [F.P(u0 + 2, va), F.P(u1, va), F.P(u1, vb), F.P(u0 + 2, vb)];
        kit.pitchedRoof(batch, glassRoof, iron, ccw(r), ang, 7, 2.0, 'gabled', { overhang: 0 });
        for (let u = u0 + 6; u < u1; u += 12) {
          const [x, y] = F.P(u, (va + vb) / 2);
          T.rod(batch, iron, [x, y, 0], [x, y, 7], 0.16, 0.13, 6);
        }
      }
    }
    // ---- Chatham side: Portland stone frontage range and Wilton Road offices ----
    {
      const fr = chathamPoly;
      for (let k = 0; k < fr.length; k++) {
        const a = fr[k],
          b = fr[(k + 1) % fr.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = [(b[1] - a[1]) / len, -(b[0] - a[0]) / len];
        const nu = n[0] * cu + n[1] * su; // component along +u (towards the forecourt)
        const nv = -n[0] * su + n[1] * cu;
        const isFront = nu > 0.45 && Math.min(uOf(a), uOf(b)) > 40;
        const isWilton = nv < -0.9;
        B.wallsTex(
          batch,
          isFront ? chatham : isWilton ? kit.facade('portland_stone', 2) : stone,
          [a, b, b],
          0,
          CTH,
          isFront ? 6 : 3.6,
          isFront ? { skip: (i) => i !== 0 } : { tileH: 6.4, skip: (i) => i !== 0 },
        );
        if (isFront && len > 20) {
          // lettered frieze, pediments with mermaid caryatids over the main entrances
          const fa = Math.atan2(b[1] - a[1], b[0] - a[0]);
          const FF = T.frame((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, fa);
          const pa = FF.P(len / 2 - 2, -0.06),
            pb = FF.P(-len / 2 + 2, -0.06);
          batch.quad(
            lettering,
            [pb[0], pb[1], 8.75],
            [pa[0], pa[1], 8.75],
            [pa[0], pa[1], 9.65],
            [pb[0], pb[1], 9.65],
            [1, 0],
            [0, 0],
            [0, 1],
            [1, 1],
          );
          const reverseOk = true;
          void reverseOk;
          for (const c0 of len > 40 ? [-len / 4, len / 4] : [0]) {
            FF.box(batch, stone, c0, -0.7, 9.8, 7.5, 1.4, 4.6);
            const ped = new THREE.Shape();
            ped.moveTo(-4.4, 0);
            ped.lineTo(4.4, 0);
            ped.lineTo(4.4, 0.8);
            ped.absarc(0, -3.0, 5.85, Math.atan2(3.8, 4.4), Math.PI - Math.atan2(3.8, 4.4), false);
            ped.lineTo(-4.4, 0);
            T.slab(FF, batch, stone, ped, c0, -0.9, 14.4, 1.8, 10);
            FF.box(batch, stoneDk, c0, -1.5, 15.6, 2.0, 0.6, 1.6); // cartouche
            for (const s of [-1, 1]) {
              const [x, y] = FF.P(c0 + s * 2.6, -1.55);
              T.figure(batch, stone, x, y, 10.2, 4.0, fa - Math.PI / 2);
              FF.box(batch, stoneDk, c0 + s * 2.6, -1.4, 9.6, 1.2, 1.0, 0.6);
            }
            FF.box(batch, kit.mat('#3c3e3a'), c0, -1.45, 11.0, 2.6, 0.1, 2.6); // wreath panel
          }
        }
      }
      kit.cap(batch, slate, [[fr]], CTH);
      B.band(batch, stoneDk, fr, CTH - 1.1, CTH - 0.6, 0.35);
    }
    // ---- Fowler train shed: two segmental glazed spans over the claimed roof outlines ----
    for (const shed of [shedW, shedE]) {
      const r = ccw(shed.polys[0][0]);
      const us = r.map(uOf),
        vs = r.map((p) => -(p[0] - C[0]) * su + (p[1] - C[1]) * cu);
      const u0 = Math.min(...us),
        u1 = Math.max(...us),
        v0 = Math.min(...vs),
        v1 = Math.max(...vs);
      const span = v1 - v0,
        vc = (v0 + v1) / 2;
      const zs = 9.0,
        rise = 9.5;
      const R = ((span * span) / 4 + rise * rise) / (2 * rise);
      const half = Math.asin(span / 2 / R);
      const N = 18;
      const pt = (t, u) => {
        const th = -half + 2 * half * t;
        const v = vc + R * Math.sin(th);
        const z = zs + R * Math.cos(th) - (R - rise);
        return [...F.P(u, v), z];
      };
      // southern end of the west span is cut on the slant: trim with the outline's southern-most u at each v
      const bays = Math.round((u1 - u0) / 6);
      for (let i = 0; i < N; i++) {
        const t0 = i / N,
          t1 = (i + 1) / N;
        batch.quad(
          shedRoof,
          pt(t0, u0),
          pt(t0, u1),
          pt(t1, u1),
          pt(t1, u0),
          [0, t0],
          [bays, t0],
          [bays, t1],
          [0, t1],
        );
      }
      // side walls (brick) up to the springing, glazed north screen, arched ribs at the ends
      const side = [F.P(u0, v0), F.P(u1, v0), F.P(u1, v1), F.P(u0, v1)];
      B.wallsTex(batch, brick, [side[0], side[1], side[1]], 0, zs, 4, { skip: (i) => i !== 0 });
      B.wallsTex(batch, brick, [side[2], side[3], side[3]], 0, zs, 4, { skip: (i) => i !== 0 });
      for (const u of [u0, u1]) {
        const ptsA = [],
          ptsB = [];
        for (let i = 0; i <= N; i++) {
          ptsA.push(pt(i / N, u));
          ptsB.push(pt(i / N, u));
        }
        for (let i = 0; i < N; i++) T.rod(batch, iron, ptsA[i], ptsA[i + 1], 0.35, 0.35, 5);
      }
      for (let k = 1; k < bays; k++) {
        const u = u0 + ((u1 - u0) * k) / bays;
        for (const s of [0, 1]) {
          const [x, y] = F.P(u, s ? v1 - 0.6 : v0 + 0.6);
          T.rod(batch, iron, [x, y, 0], [x, y, zs], 0.25, 0.25, 6);
        }
      }
      // glazed screen closing the forecourt end
      const scr = [];
      for (let i = 0; i <= N; i++) scr.push(pt(i / N, u1 - 0.3));
      const base0 = [...F.P(u1 - 0.3, v0), zs],
        base1 = [...F.P(u1 - 0.3, v1), zs];
      const verts = [base0, base1, ...scr],
        uvs = verts.map(() => [0, 0]),
        idx = [];
      for (let i = 0; i < N; i++) idx.push(0, 2 + i, 2 + i + 1);
      for (let i = 0; i < N; i++) idx.push(1, 2 + i + 1, 2 + i);
      batch.add(kit.mat('#5e6f78', { side: THREE.DoubleSide, roughness: 0.3 }), verts, uvs, idx);
    }
    g.add(batch.toGroup('victoria_station'));
    return g;
  },
};
