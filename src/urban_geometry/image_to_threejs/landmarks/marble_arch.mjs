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
  function rod(batch, mat, p, q, r0, r1 = r0, seg = 6, closed = false) {
    const a = V(...p),
      b = V(...q);
    const d = b.clone().sub(a),
      len = d.length();
    if (len < 1e-4) return;
    const geo = new THREE.CylinderGeometry(r1, r0, len, seg, 1, !closed);
    Q.setFromUnitVectors(V(0, 1, 0), d.normalize());
    M.compose(a.add(b).multiplyScalar(0.5), Q, V(1, 1, 1));
    batch.addGeometry(mat, geo, M);
    geo.dispose();
  }
  /** Ellipsoid blob centred at p, axis-aligned to heading (sx along heading). */
  function blob(batch, mat, p, sx, sy, sz, heading = 0, pitch = 0, seg = 8) {
    put(
      batch,
      mat,
      new THREE.SphereGeometry(1, seg, Math.max(4, seg - 3)),
      p[0],
      p[1],
      p[2],
      heading,
      sx,
      sy,
      sz,
      0,
      pitch,
    );
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
  /** Lathe about +z from [[r, z], ...] (z relative), optional flutes cut into the radius. */
  function latheZ(profile, seg = 16, flutes = 0, fluteDepth = 0.06) {
    const g = new THREE.LatheGeometry(
      profile.map(([r, z]) => new THREE.Vector2(Math.max(r, 1e-4), z)),
      seg,
    );
    if (flutes) {
      const p = g.attributes.position;
      for (let k = 0; k < p.count; k++) {
        const x = p.getX(k),
          z = p.getZ(k);
        const a = Math.atan2(z, x);
        const f = 0.5 + 0.5 * Math.cos(a * flutes);
        const s = 1 - fluteDepth * Math.pow(f, 3);
        p.setX(k, x * s);
        p.setZ(k, z * s);
      }
    }
    return g.rotateX(Math.PI / 2);
  }
  /** Attic base: plinth, lower torus, scotia, upper torus (height ~0.5 r per unit). */
  function atticBase(F, batch, mat, u, v, z0, r, bh, seg) {
    F.box(batch, mat, u, v, z0, r * 2.7, r * 2.7, bh * 0.32);
    F.put(
      batch,
      mat,
      latheZ(
        [
          [r * 1.32, 0],
          [r * 1.36, bh * 0.14],
          [r * 1.3, bh * 0.28],
          [r * 1.12, bh * 0.34],
          [r * 1.08, bh * 0.44],
          [r * 1.2, bh * 0.52],
          [r * 1.18, bh * 0.62],
          [r * 1.03, bh * 0.68],
          [r * 1.0, bh * 0.7],
          [0, bh * 0.7],
        ],
        seg,
      ),
      u,
      v,
      z0 + bh * 0.3,
    );
  }
  /** Corinthian capital: bell, two rows of acanthus, corner volutes, concave abacus, rosettes. */
  function corinthianCap(F, batch, mat, u, v, zc, r, ch, seg, rz = 0) {
    F.put(
      batch,
      mat,
      latheZ(
        [
          [r * 0.92, 0],
          [r * 0.96, ch * 0.06],
          [r * 0.9, ch * 0.1],
          [r * 0.94, ch * 0.5],
          [r * 1.08, ch * 0.82],
          [0, ch * 0.82],
        ],
        seg,
      ),
      u,
      v,
      zc,
    );
    const leaf = (rr, z, hh, n, off, tilt, w) => {
      for (let k = 0; k < n; k++) {
        const a = ((k + off) / n) * Math.PI * 2 + rz;
        const g = new THREE.CylinderGeometry(w * 0.5, w * 0.32, hh, 4, 1).scale(0.35, 1, 1);
        g.rotateX(Math.PI / 2); // axis z, flat in radial direction
        const m = new THREE.Matrix4()
          .makeRotationZ(a + F.ang)
          .multiply(new THREE.Matrix4().makeRotationY(tilt));
        const [x, y] = F.P(u + Math.cos(a) * rr, v + Math.sin(a) * rr);
        m.setPosition(x, y, z + hh / 2);
        batch.addGeometry(mat, g, m);
        g.dispose();
        // curled leaf tip
        const t = new THREE.BoxGeometry(w * 0.55, w * 0.5, hh * 0.18);
        const m2 = new THREE.Matrix4().makeRotationZ(a + F.ang);
        const [x2, y2] = F.P(
          u + Math.cos(a) * (rr + hh * 0.22),
          v + Math.sin(a) * (rr + hh * 0.22),
        );
        m2.setPosition(x2, y2, z + hh * 0.92);
        batch.addGeometry(mat, t, m2);
        t.dispose();
      }
    };
    leaf(r * 0.95, zc + ch * 0.06, ch * 0.38, 8, 0, 0.18, r * 0.62);
    leaf(r * 1.0, zc + ch * 0.3, ch * 0.36, 8, 0.5, 0.22, r * 0.62);
    // corner volutes and central helices under the abacus
    for (let k = 0; k < 4; k++) {
      const a = Math.PI / 4 + (k * Math.PI) / 2 + rz;
      const [x0, y0] = F.P(u + Math.cos(a) * r * 0.9, v + Math.sin(a) * r * 0.9);
      const [x1, y1] = F.P(u + Math.cos(a) * r * 1.5, v + Math.sin(a) * r * 1.5);
      rod(batch, mat, [x0, y0, zc + ch * 0.55], [x1, y1, zc + ch * 0.8], r * 0.12, r * 0.16, 5);
      const vg = new THREE.TorusGeometry(r * 0.16, r * 0.07, 4, 8);
      put(batch, mat, vg, x1, y1, zc + ch * 0.74, a + F.ang + Math.PI / 2, 1, 1, 1, Math.PI / 2, 0);
    }
    // concave-sided abacus (square with chamfered horns) and rosettes
    const ab = new THREE.CylinderGeometry(r * 1.62, r * 1.62, ch * 0.18, 8, 1).rotateX(Math.PI / 2);
    F.put(batch, mat, ab, u, v, zc + ch * 0.91, Math.PI / 8 + rz);
    F.box(batch, mat, u, v, zc + ch * 0.82, r * 2.15, r * 2.15, ch * 0.18, rz);
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2 + rz;
      F.box(
        batch,
        mat,
        u + Math.cos(a) * r * 1.1,
        v + Math.sin(a) * r * 1.1,
        zc + ch * 0.83,
        r * 0.3,
        r * 0.3,
        ch * 0.16,
        a,
      );
    }
  }
  /** Ionic capital: echinus with egg-and-dart band, cushion with two scroll volutes, abacus. */
  function ionicCap(F, batch, mat, u, v, zc, r, ch, seg, rz = 0) {
    F.put(
      batch,
      mat,
      latheZ(
        [
          [r * 0.9, 0],
          [r * 0.98, ch * 0.08],
          [r * 0.92, ch * 0.14],
          [r * 1.12, ch * 0.42],
          [0, ch * 0.42],
        ],
        seg,
      ),
      u,
      v,
      zc,
    );
    const c = Math.cos(rz),
      s = Math.sin(rz);
    F.box(batch, mat, u, v, zc + ch * 0.3, r * 2.5, r * 1.9, ch * 0.42, rz); // cushion
    for (const sd of [-1, 1]) {
      const uu = u + c * sd * r * 1.3,
        vv = v + s * sd * r * 1.3;
      // scroll: cylinder along v with a spiral disc on each face
      F.put(
        batch,
        mat,
        new THREE.CylinderGeometry(ch * 0.32, ch * 0.32, r * 1.95, 10),
        uu,
        vv,
        zc + ch * 0.36,
        rz,
      );
      for (const fv of [-1, 1]) {
        const g = new THREE.TorusGeometry(ch * 0.18, ch * 0.06, 3, 8);
        F.put(
          batch,
          mat,
          g,
          uu - s * fv * r * 1.0,
          vv + c * fv * r * 1.0,
          zc + ch * 0.36,
          rz,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
        F.box(
          batch,
          mat,
          uu - s * fv * r * 1.0,
          vv + c * fv * r * 1.0,
          zc + ch * 0.31,
          ch * 0.12,
          0.04,
          ch * 0.12,
          rz,
        );
      }
    }
    F.box(batch, mat, u, v, zc + ch * 0.68, r * 2.3, r * 2.3, ch * 0.32 * 0.5, rz);
  }
  /**
   * Classical column: Attic base, entasis shaft (fluted by default), order capital.
   * kind: corinthian | composite | ionic | doric | tuscan.
   */
  function column(F, batch, mat, u, v, z0, h, r, kind = 'corinthian', seg = 12, opts = {}) {
    const { fluted = kind !== 'tuscan', base = kind !== 'doric', capMat = mat, rz = 0 } = opts;
    const bh = base ? r * 1.0 : 0,
      ch =
        kind === 'corinthian' || kind === 'composite'
          ? r * 2.4
          : kind === 'ionic'
            ? r * 1.3
            : r * 0.8;
    const sg = fluted ? (seg >= 16 ? 48 : 36) : seg;
    if (base) atticBase(F, batch, mat, u, v, z0, r, bh, Math.max(seg, 12));
    const sh = h - bh - ch;
    // shaft with apophyge at foot, entasis and astragal at the neck
    F.put(
      batch,
      mat,
      latheZ(
        [
          [r * 1.06, 0],
          [r * 1.0, sh * 0.02],
          [r * 1.0, sh * 0.33],
          [r * 0.95, sh * 0.7],
          [r * 0.86, sh * 0.97],
          [r * 0.9, sh * 0.975],
          [r * 0.95, sh * 0.99],
          [r * 0.9, sh],
          [0, sh],
        ],
        sg,
        fluted ? 24 : 0,
        0.09,
      ),
      u,
      v,
      z0 + bh,
    );
    const zc = z0 + bh + sh;
    const rr = r * 0.88;
    if (kind === 'corinthian' || kind === 'composite')
      corinthianCap(F, batch, capMat, u, v, zc, rr, ch, Math.max(seg, 12), rz);
    else if (kind === 'ionic') ionicCap(F, batch, capMat, u, v, zc, rr, ch, Math.max(seg, 12), rz);
    else {
      F.put(
        batch,
        capMat,
        latheZ(
          [
            [rr, 0],
            [rr * 1.05, ch * 0.12],
            [rr * 1.0, ch * 0.2],
            [rr * 1.35, ch * 0.55],
            [0, ch * 0.55],
          ],
          Math.max(seg, 16),
        ),
        u,
        v,
        zc,
      );
      F.box(batch, capMat, u, v, zc + ch * 0.55, r * 2.7, r * 2.7, ch * 0.45, rz);
    }
  }
  /** Flat pilaster (w wide, d proud) with base and capital; outward = +v in F. */
  function pilaster(F, batch, mat, u, v, z0, h, w, d, kind = 'corinthian', rz = 0) {
    const ch = kind === 'corinthian' ? w * 1.1 : kind === 'ionic' ? w * 0.55 : w * 0.4;
    F.box(batch, mat, u, v, z0, w * 1.25, d + 0.12, w * 0.45, rz);
    F.box(batch, mat, u, v, z0 + w * 0.45, w, d, h - w * 0.45 - ch, rz);
    const zc = z0 + h - ch;
    if (kind === 'corinthian') {
      F.box(batch, mat, u, v, zc, w * 1.02, d + 0.05, ch * 0.8, rz);
      for (const t of [-0.3, 0, 0.3])
        F.box(
          batch,
          mat,
          u + t * w * Math.cos(rz),
          v + t * w * Math.sin(rz),
          zc + ch * 0.05,
          w * 0.26,
          d + 0.16,
          ch * 0.42,
          rz,
        );
      for (const t of [-0.42, 0.42])
        F.box(
          batch,
          mat,
          u + t * w * Math.cos(rz),
          v + t * w * Math.sin(rz),
          zc + ch * 0.5,
          w * 0.22,
          d + 0.2,
          ch * 0.32,
          rz,
        );
      F.box(batch, mat, u, v, zc + ch * 0.8, w * 1.35, d + 0.25, ch * 0.2, rz);
    } else if (kind === 'ionic') {
      F.box(batch, mat, u, v, zc, w * 1.05, d + 0.08, ch * 0.6, rz);
      for (const t of [-0.55, 0.55])
        F.box(
          batch,
          mat,
          u + t * w * Math.cos(rz),
          v + t * w * Math.sin(rz),
          zc + ch * 0.05,
          ch * 0.5,
          d + 0.16,
          ch * 0.5,
          rz,
        );
      F.box(batch, mat, u, v, zc + ch * 0.6, w * 1.3, d + 0.18, ch * 0.4, rz);
    } else F.box(batch, mat, u, v, zc, w * 1.3, d + 0.15, ch, rz);
  }
  /**
   * Standing figure of height h facing `heading`. pose: { robe, armUp (right arm raised),
   * armOut, wreath, wings, cloak }.
   */
  function figure(batch, mat, x, y, z, h, heading = 0, pose = {}) {
    const c = Math.cos(heading),
      s = Math.sin(heading);
    // local: a forward, b left
    const L = (a, b, hh) => [x + a * c - b * s, y + a * s + b * c, z + hh * h];
    const w = h;
    if (pose.robe) {
      // long drapery: skirt cone from the waist to the feet
      put(
        batch,
        mat,
        new THREE.CylinderGeometry(w * 0.1, w * 0.17, h * 0.55, 9, 1, true).rotateX(Math.PI / 2),
        ...L(0, 0, 0.275),
        heading,
      );
      put(batch, mat, new THREE.CircleGeometry(w * 0.17, 9), ...L(0, 0, 0.002), heading);
    } else
      for (const b of [-0.055, 0.055]) {
        rod(batch, mat, L(0, b * w, 0.02), L(0.01 * w, b * w, 0.27), w * 0.04, w * 0.05, 6, true);
        rod(
          batch,
          mat,
          L(0.01 * w, b * w, 0.27),
          L(0, b * w * 0.8, 0.52),
          w * 0.05,
          w * 0.065,
          6,
          true,
        );
        put(
          batch,
          mat,
          new THREE.BoxGeometry(w * 0.11, w * 0.06, w * 0.04),
          ...L(0.03 * w, b * w, 0.02),
          heading,
        );
      }
    // torso: hips, waist, chest
    blob(batch, mat, L(0, 0, 0.53), w * 0.075, w * 0.11, w * 0.07, heading, 0, 8);
    rod(batch, mat, L(0, 0, 0.53), L(0, 0, 0.73), w * 0.085, w * 0.11, 8, true);
    blob(batch, mat, L(0, 0, 0.74), w * 0.08, w * 0.13, w * 0.07, heading, 0, 8);
    rod(batch, mat, L(0, 0, 0.78), L(0, 0, 0.84), w * 0.03, w * 0.03, 5, true);
    blob(batch, mat, L(0.005 * w, 0, 0.885), w * 0.05, w * 0.045, w * 0.06, heading, 0, 8);
    // arms
    for (const sd of [-1, 1]) {
      const sh = L(0, sd * 0.13 * w, 0.77);
      const up = pose.armUp && sd === -1;
      const out = pose.armOut && sd === 1;
      const el = up
        ? L(0.04 * w, sd * 0.17 * w, 0.93)
        : out
          ? L(0.12 * w, sd * 0.2 * w, 0.66)
          : L(0.01 * w, sd * 0.155 * w, 0.6);
      const hd = up
        ? L(0.08 * w, sd * 0.19 * w, 1.1)
        : out
          ? L(0.28 * w, sd * 0.24 * w, 0.64)
          : L(0.07 * w, sd * 0.15 * w, 0.46);
      rod(batch, mat, sh, el, w * 0.035, w * 0.04, 5, true);
      rod(batch, mat, el, hd, w * 0.03, w * 0.035, 5, true);
      if (up && pose.wreath)
        put(
          batch,
          mat,
          new THREE.TorusGeometry(w * 0.06, w * 0.015, 4, 10),
          ...L(0.08 * w, sd * 0.19 * w, 1.15),
          heading + Math.PI / 2,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
    }
    if (pose.cloak)
      put(
        batch,
        mat,
        new THREE.CylinderGeometry(
          w * 0.12,
          w * 0.2,
          h * 0.55,
          8,
          1,
          true,
          Math.PI * 0.5,
          Math.PI,
        ).rotateX(Math.PI / 2),
        ...L(-0.02 * w, 0, 0.5),
        heading,
      );
    if (pose.wings)
      for (const sd of [-1, 1]) {
        const shape = new THREE.Shape();
        shape.moveTo(0, 0);
        shape.bezierCurveTo(0.15, 0.25, 0.35, 0.45, 0.42, 0.62);
        shape.bezierCurveTo(0.32, 0.5, 0.28, 0.3, 0.25, 0.12);
        shape.bezierCurveTo(0.22, 0.05, 0.12, -0.25, 0.08, -0.45);
        shape.lineTo(0, -0.1);
        const g = new THREE.ExtrudeGeometry(shape, {
          depth: 0.02,
          bevelEnabled: false,
          curveSegments: 5,
        })
          .rotateX(Math.PI / 2)
          .scale(sd * w, w, w);
        put(
          batch,
          mat,
          g,
          ...L(-0.08 * w, sd * 0.06 * w, 0.78),
          heading + Math.PI / 2 - sd * (pose.wingSpread ?? 0.5),
        );
      }
  }
  /** Horse of withers height ~1.45*s, heading in radians, rear = front legs raised (0..1). */
  function horse(batch, mat, x, y, z, heading, s, rear = 0) {
    const c = Math.cos(heading),
      sn = Math.sin(heading);
    const pitch = rear * 0.5;
    const cp = Math.cos(pitch),
      sp = Math.sin(pitch);
    // body pivots about the hind quarters when rearing
    const L = (a, b, h) => {
      const aa = -0.75 * s + (a + 0.75 * s) * cp - (h - 1.3 * s) * sp;
      const hh = 1.3 * s + (a + 0.75 * s) * sp + (h - 1.3 * s) * cp;
      return [x + aa * c - b * sn, y + aa * sn + b * c, z + hh];
    };
    const G = (a, b, h) => [x + a * c - b * sn, y + a * sn + b * c, z + h]; // unpitched (ground legs)
    // barrel, chest and quarters
    blob(batch, mat, L(0, 0, 1.38 * s), 0.62 * s, 0.3 * s, 0.33 * s, heading, -pitch, 9);
    blob(batch, mat, L(0.52 * s, 0, 1.42 * s), 0.34 * s, 0.27 * s, 0.36 * s, heading, -pitch, 8);
    blob(batch, mat, L(-0.6 * s, 0, 1.42 * s), 0.36 * s, 0.3 * s, 0.34 * s, heading, -pitch, 8);
    // neck, crest/mane, head with muzzle, ears
    const n0 = L(0.62 * s, 0, 1.6 * s),
      n1 = L(0.98 * s, 0, 2.18 * s);
    rod(batch, mat, n0, n1, 0.25 * s, 0.14 * s, 8, true);
    rod(
      batch,
      mat,
      L(0.55 * s, 0, 1.82 * s),
      L(0.92 * s, 0, 2.34 * s),
      0.06 * s,
      0.05 * s,
      4,
      true,
    );
    const h0 = L(1.0 * s, 0, 2.24 * s),
      h1 = L(1.38 * s, 0, 1.92 * s - rear * 0.15 * s);
    rod(batch, mat, h0, h1, 0.14 * s, 0.085 * s, 7, true);
    blob(batch, mat, h1, 0.09 * s, 0.075 * s, 0.08 * s, heading, 0, 6);
    for (const b of [-0.06, 0.06])
      rod(
        batch,
        mat,
        L(0.99 * s, b * s, 2.3 * s),
        L(0.97 * s, b * 1.3 * s, 2.4 * s),
        0.035 * s,
        0.012 * s,
        4,
        true,
      );
    // hind legs: stifle, hock, cannon, hoof
    for (const b of [-0.15, 0.15]) {
      const hip = L(-0.68 * s, b * s, 1.3 * s);
      const hock = G(-0.95 * s + (rear ? 0.15 * s : 0), b * s, 0.55 * s);
      const foot = G(-0.82 * s + (rear ? 0.25 * s : 0) + b * 0.3 * s, b * s, 0.06 * s);
      rod(batch, mat, hip, hock, 0.15 * s, 0.07 * s, 7, true);
      rod(batch, mat, hock, foot, 0.055 * s, 0.05 * s, 6, true);
      rod(batch, mat, foot, [foot[0], foot[1], z], 0.075 * s, 0.065 * s, 6, true);
    }
    // front legs: planted or raised and folded
    for (const [k, b] of [
      [0, -0.14],
      [1, 0.14],
    ]) {
      const top = L(0.55 * s, b * s, 1.25 * s);
      if (rear < 0.2) {
        const knee = G(0.62 * s + k * 0.05 * s, b * s, 0.58 * s);
        const foot = G(0.64 * s + k * 0.06 * s, b * s, 0.06 * s);
        rod(batch, mat, top, knee, 0.11 * s, 0.06 * s, 7, true);
        rod(batch, mat, knee, foot, 0.05 * s, 0.045 * s, 6, true);
        rod(batch, mat, foot, [foot[0], foot[1], z], 0.07 * s, 0.06 * s, 6, true);
      } else {
        const knee = L((0.98 + k * 0.1) * s, b * s, (1.05 - k * 0.12) * s);
        const foot = L((0.86 + k * 0.1) * s, b * s, (0.55 - k * 0.12) * s);
        rod(batch, mat, top, knee, 0.11 * s, 0.06 * s, 7, true);
        rod(batch, mat, knee, foot, 0.05 * s, 0.045 * s, 6, true);
      }
    }
    // tail
    const t0 = L(-0.95 * s, 0, 1.55 * s);
    rod(batch, mat, t0, G(-1.15 * s - rear * 0.2 * s, 0, 0.75 * s), 0.08 * s, 0.05 * s, 5, true);
  }
  /** Iron railing along a polyline: rails, square bars with spear heads, posts with finials. */
  function railing(batch, mat, line, z, opts = {}) {
    const {
      height = 1.6,
      spacing = 0.13,
      post = 3.0,
      finial = mat,
      bar = 0.022,
      spear = true,
      postMat = mat,
    } = opts;
    for (let k = 1; k < line.length; k++) {
      const a = line[k - 1],
        b = line[k];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const mx = (a[0] + b[0]) / 2,
        my = (a[1] + b[1]) / 2;
      kit.box(batch, mat, mx, my, z + 0.12, len, 0.05, 0.05, ang);
      kit.box(batch, mat, mx, my, z + height - 0.22, len, 0.05, 0.05, ang);
      const n = Math.max(1, Math.round(len / spacing));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const x = a[0] + (b[0] - a[0]) * t,
          y = a[1] + (b[1] - a[1]) * t;
        put(
          batch,
          mat,
          new THREE.CylinderGeometry(bar * 0.7, bar * 0.7, height - 0.1, 4, 1, true).rotateX(
            Math.PI / 2,
          ),
          x,
          y,
          z + (height - 0.1) / 2,
          ang + Math.PI / 4,
        );
        if (spear) {
          const g = new THREE.ConeGeometry(bar * 1.8, 0.12, 4, 1, true).rotateX(Math.PI / 2);
          put(batch, finial, g, x, y, z + height - 0.04, ang + Math.PI / 4);
        }
      }
      const np = Math.max(1, Math.round(len / post));
      for (let i = 0; i <= np; i++) {
        const t = i / np;
        const x = a[0] + (b[0] - a[0]) * t,
          y = a[1] + (b[1] - a[1]) * t;
        kit.box(batch, postMat, x, y, z, 0.09, 0.09, height + 0.1, ang);
        put(batch, finial, new THREE.SphereGeometry(0.07, 6, 4), x, y, z + height + 0.17);
      }
    }
  }
  /** Lathe solid (urn / finial / lantern) placed at x, y, z. */
  function lathePut(batch, mat, profile, x, y, z, seg = 12) {
    put(batch, mat, latheZ(profile, seg), x, y, z);
  }
  /** Stone urn of height h on its own plinth. */
  function urn(batch, mat, x, y, z, h) {
    lathePut(
      batch,
      mat,
      [
        [h * 0.2, 0],
        [h * 0.2, h * 0.12],
        [h * 0.1, h * 0.16],
        [h * 0.09, h * 0.24],
        [h * 0.25, h * 0.45],
        [h * 0.27, h * 0.62],
        [h * 0.18, h * 0.72],
        [h * 0.22, h * 0.78],
        [h * 0.06, h * 0.86],
        [h * 0.07, h * 0.95],
        [0, h],
      ],
      x,
      y,
      z,
      10,
    );
  }
  /** Stepped moulding run along wall edge a -> b (outward normal right of a -> b). steps: [[proj, h], ...] from z upward. */
  function mould(batch, mat, a, b, z, steps, ext = true) {
    const dx = b[0] - a[0],
      dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    if (len < 0.05) return;
    const ux = dx / len,
      uy = dy / len,
      nx = uy,
      ny = -ux,
      ang = Math.atan2(dy, dx);
    let zz = z;
    for (const [p, h] of steps) {
      const l = len + (ext ? 2 * p : 0);
      kit.box(
        batch,
        mat,
        (a[0] + b[0]) / 2 + (nx * p) / 2,
        (a[1] + b[1]) / 2 + (ny * p) / 2,
        zz,
        l,
        p,
        h,
        ang,
      );
      zz += h;
    }
    return zz;
  }
  /** Row of small blocks (dentils / modillions / brackets) along a -> b, proud of the wall. */
  function blocks(
    batch,
    mat,
    a,
    b,
    z,
    { w = 0.12, h = 0.18, proj = 0.2, gap = 0.12, inset = 0 } = {},
  ) {
    const dx = b[0] - a[0],
      dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    const ux = dx / len,
      uy = dy / len,
      nx = uy,
      ny = -ux,
      ang = Math.atan2(dy, dx);
    const n = Math.floor((len - 2 * inset) / (w + gap));
    const off = (len - n * (w + gap)) / 2 + (w + gap) / 2;
    for (let i = 0; i < n; i++) {
      const t = off + i * (w + gap);
      kit.box(
        batch,
        mat,
        a[0] + ux * t + (nx * proj) / 2,
        a[1] + uy * t + (ny * proj) / 2,
        z,
        w,
        proj,
        h,
        ang,
      );
    }
  }
  /** Panelled door (two leaves) with architrave, set on wall edge at point p facing outward angle. */
  function door(batch, mats, x, y, z, w, h, ang, { fan = false, surround = 0.25 } = {}) {
    const { leaf, frame, glass } = mats;
    const nx = Math.sin(ang),
      ny = -Math.cos(ang);
    const P = (t, d) => [x + Math.cos(ang) * t + nx * d, y + Math.sin(ang) * t + ny * d];
    kit.box(batch, leaf, ...P(0, 0.03), z, w, 0.06, h, ang);
    for (const t of [-0.25, 0.25])
      for (const zz of [0.12, 0.55])
        kit.box(batch, frame, ...P(t * w, 0.07), z + h * zz, w * 0.36, 0.03, h * 0.36, ang);
    kit.box(batch, frame, ...P(0, 0.06), z, 0.04, 0.05, h, ang);
    for (const sd of [-1, 1])
      kit.box(
        batch,
        frame,
        ...P(sd * (w / 2 + surround / 2), 0.08),
        z,
        surround,
        0.16,
        h + surround,
        ang,
      );
    kit.box(batch, frame, ...P(0, 0.09), z + h, w + 2 * surround, 0.18, surround, ang);
    if (fan) {
      const g = new THREE.CircleGeometry(w / 2, 12, 0, Math.PI).rotateX(Math.PI / 2);
      const m = new THREE.Matrix4().makeRotationZ(ang);
      const [gx, gy] = P(0, 0.03);
      m.setPosition(gx, gy, z + h + surround);
      batch.addGeometry(glass ?? leaf, g, m);
      g.dispose();
    }
  }
  /** Chimney stack with cornice cap and pots. */
  function chimney(batch, mat, potMat, x, y, z, w, d, h, ang, pots = 3) {
    kit.box(batch, mat, x, y, z, w, d, h, ang);
    kit.box(batch, mat, x, y, z + h, w + 0.16, d + 0.16, 0.18, ang);
    const c = Math.cos(ang),
      s = Math.sin(ang);
    for (let k = 0; k < pots; k++) {
      const t = (k + 0.5) / pots - 0.5;
      put(
        batch,
        potMat,
        new THREE.CylinderGeometry(0.13, 0.16, 0.6, 7).rotateX(Math.PI / 2),
        x + c * t * w,
        y + s * t * w,
        z + h + 0.48,
      );
    }
  }
  /** Flagpole with a flag (flagMat) flying towards angle `fly`. */
  function flag(batch, poleMat, flagMat, x, y, z, h, fly = 0, fw = 3.6, fh = 1.8) {
    rod(batch, poleMat, [x, y, z], [x, y, z + h], 0.09, 0.05, 6, true);
    put(batch, poleMat, new THREE.SphereGeometry(0.12, 6, 4), x, y, z + h + 0.08);
    const g = new THREE.PlaneGeometry(fw, fh, 4, 1);
    const p = g.attributes.position;
    for (let k = 0; k < p.count; k++)
      p.setZ(k, Math.sin((p.getX(k) / fw + 0.5) * Math.PI * 1.5) * 0.18);
    g.rotateX(Math.PI / 2).translate(fw / 2, 0, 0);
    put(batch, flagMat, g, x, y, z + h - fh / 2 - 0.1, fly);
  }
  /** Build into a scratch batch at the origin, then merge into `batch` through matrix m (relief, tilt, flatten). */
  function xform(batch, build, m) {
    const tmp = new kit.MeshBatch();
    build(tmp);
    const grp = tmp.toGroup('tmp');
    for (const mesh of grp.children) {
      batch.addGeometry(mesh.material, mesh.geometry, m);
      mesh.geometry.dispose();
    }
  }
  /** Matrix placing local (x along u, y outward v, z up) at frame point (u, v, z), scaled. */
  function at(F, u, v, z, rz = 0, sx = 1, sy = 1, sz = 1, rx = 0, ry = 0) {
    const [x, y] = F.P(u, v);
    E.set(rx, ry, F.ang + rz, 'ZYX');
    Q.setFromEuler(E);
    return new THREE.Matrix4().compose(V(x, y, z), Q, V(sx, sy, sz));
  }
  /**
   * Round-headed windows (or doors) on wall edge a -> b: arched glass, frame, glazing bars,
   * sill and keystone. height includes the semicircular head. Returns the centres.
   */
  function archWin(batch, a, b, z, o = {}) {
    const {
      width = 1.2,
      height = 2.6,
      count,
      bay = 3.3,
      margin = 0,
      glass = kit.mat('dark_glass'),
      frame = kit.mat('white'),
      stone = frame,
      bars = 2,
      keystone = true,
      sill = true,
      depth = 0.1,
      surround = 0,
    } = o;
    const dx = b[0] - a[0],
      dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    const n = count ?? Math.max(0, Math.round((len - 2 * margin) / bay));
    const ang = Math.atan2(dy, dx);
    const r = width / 2,
      hs = height - r; // springing above sill
    const sh = new THREE.Shape();
    sh.moveTo(-r, 0);
    sh.lineTo(r, 0);
    sh.lineTo(r, hs);
    sh.absarc(0, hs, r, 0, Math.PI, false);
    sh.lineTo(-r, 0);
    const gg = new THREE.ShapeGeometry(sh, 8).rotateX(Math.PI / 2).rotateZ(Math.PI); // facing local -y, mirrored
    const out = [];
    for (let k = 0; k < n; k++) {
      const t = margin + ((len - 2 * margin) * (k + 0.5)) / n;
      const x = a[0] + (dx / len) * t,
        y = a[1] + (dy / len) * t;
      const F = frame_(x, y, ang); // u along wall, v = inward; outward is -v
      const m = new THREE.Matrix4().makeRotationZ(ang + Math.PI).setPosition(...F.P(0, -0.03), z);
      batch.addGeometry(glass, gg, m);
      // frame
      for (const sd of [-1, 1]) F.box(batch, frame, sd * r, -depth / 2, z, 0.08, depth, hs);
      F.put(
        batch,
        frame,
        new THREE.TorusGeometry(r, 0.05, 4, 10, Math.PI),
        0,
        -depth / 2,
        z + hs,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      if (surround) {
        for (const sd of [-1, 1])
          F.box(
            batch,
            stone,
            sd * (r + surround / 2),
            -depth * 0.7,
            z - 0.05,
            surround,
            depth * 1.4,
            hs + 0.05,
          );
        F.put(
          batch,
          stone,
          new THREE.TorusGeometry(r + surround / 2, surround / 2, 4, 12, Math.PI),
          0,
          -depth * 0.7,
          z + hs,
          0,
          1,
          1,
          (1.4 * depth) / surround,
          Math.PI / 2,
          0,
        );
      }
      // glazing bars
      for (let i = 1; i <= bars; i++) {
        F.box(
          batch,
          frame,
          -r + (width * i) / (bars + 1),
          -depth * 0.3,
          z,
          0.04,
          depth * 0.6,
          hs + r * 0.95,
        );
        F.box(batch, frame, 0, -depth * 0.3, z + (hs * i) / (bars + 1), width, depth * 0.6, 0.04);
      }
      F.box(batch, frame, 0, -depth * 0.3, z + hs, width, depth * 0.6, 0.05);
      if (sill) F.box(batch, stone, 0, -depth, z - 0.12, width + 0.3, depth * 2, 0.12);
      if (keystone) F.box(batch, stone, 0, -depth * 0.8, z + hs + r - 0.05, 0.3, depth * 1.6, 0.4);
      out.push([x, y]);
    }
    gg.dispose();
    return out;
  }
  function frame_(x, y, ang) {
    return frame(x, y, ang);
  }
  return {
    archWin,
    xform,
    at,
    put,
    rod,
    blob,
    frame,
    slab,
    archShape,
    latheZ,
    column,
    pilaster,
    corinthianCap,
    ionicCap,
    figure,
    horse,
    railing,
    lathePut,
    urn,
    mould,
    blocks,
    door,
    chimney,
    flag,
    V,
  };
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
    {
      title: 'The Marble Arch - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101239534-the-marble-arch-bryanston-and-dorset-square-ward',
      used_for:
        'three archways flanked by Corinthian columns on plinths, Victories in the spandrels and relief panels over the side arches, inverted volute consoles rising into a blind attic',
    },
    {
      title: 'Treasures of London - Marble Arch gates (Exploring London)',
      url: 'https://exploring-london.com/tag/samuel-parker/',
      used_for:
        "Samuel Parker's bronze gates with St George and the Dragon, a lion and the royal cypher",
    },
  ],
  notes:
    'Overall height 13.7 m from the 45 ft figure (Overture h = 10.4 m is too low). Plan and column positions from the Overture outline; opening widths, springing heights and attic proportions estimated. Detail pass: veined marble ashlar, fluted Corinthian columns on panelled pedestals, moulded archivolts with scrolled keystones, coffered soffits, dentil cornice with breakforwards, attic pedestals with urn panels and inverted volute consoles; spandrel Victories and the England/Scotland/Ireland panels are low-relief schematic figures; the gates carry a relief horseman roundel, lion and cypher in simplified form. Island lamps and benches are resources assets.',
  build({ THREE, kit, frame, placeAssets }) {
    const T = tools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const marble = kit.paintedMaterial(
      'marble_arch:marble',
      512,
      512,
      (c, w, h) => {
        // white Carrara/Seravezza marble: faint grey veins, 0.6 m ashlar courses (4 m tile)
        const r = kit.rng(0.913);
        c.fillStyle = '#efede7';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = 'rgba(120,124,130,0.08)';
        for (let k = 0; k < 26; k++) {
          c.lineWidth = 0.6 + r() * 1.6;
          c.beginPath();
          let x = r() * w,
            y = r() * h;
          c.moveTo(x, y);
          for (let j = 0; j < 6; j++) {
            const x2 = x + (r() - 0.3) * 90,
              y2 = y + (r() - 0.5) * 50;
            c.quadraticCurveTo(
              (x + x2) / 2 + (r() - 0.5) * 30,
              (y + y2) / 2 + (r() - 0.5) * 30,
              x2,
              y2,
            );
            x = x2;
            y = y2;
          }
          c.stroke();
        }
        const ch = h / 6.67,
          bw = w / 2.5;
        c.fillStyle = 'rgba(140,138,130,0.35)';
        for (let row = 0; row < 7; row++) {
          c.fillRect(0, row * ch, w, 1.5);
          for (let x = (row % 2) * bw * 0.5; x < w; x += bw) c.fillRect(x, row * ch, 1.5, ch);
        }
      },
      { roughness: 0.42 },
    );
    marble.map.repeat.set(0.25, 0.25);
    const white = kit.mat('#eeece6', { roughness: 0.45 });
    const marbleDk = kit.mat('#dedad0', { roughness: 0.5 });
    const shadow = kit.mat('#c9c5ba', { roughness: 0.6 });
    const bronze = kit.mat('#5a4a32', { roughness: 0.4, metalness: 0.65 });
    const gilt = kit.mat('gold');
    const paving = kit.mat('#c2bcb0', { roughness: 0.9 });
    const F = T.frame(frame.cx, frame.cy, frame.angle);
    const L = Math.min(frame.length, 18),
      D = Math.max(frame.width - 2.2, 5.2);
    const Z0 = 0.5,
      ZE = 10.0,
      ZA = 11.4,
      ZT = 13.7;
    const arches = [
      [0, 4.5, 5.9],
      [-5.25, 2.5, 4.1],
      [5.25, 2.5, 4.1],
    ];
    // paved island and stepped plinth
    F.box(batch, paving, 0, 0, 0, L + 12, D + 14, 0.05);
    F.box(batch, marbleDk, 0, 0, 0, L + 0.9, D + 3.1, 0.2);
    F.box(batch, marbleDk, 0, 0, 0.2, L + 0.4, D + 2.6, Z0 - 0.2);
    // arched body: large central arch and two lower side arches
    const shape = T.archShape(
      L - 0.4,
      ZE - Z0,
      arches.map(([c, w, s]) => ({ c, w, s })),
    );
    T.slab(F, batch, marble, shape, 0, 0, Z0, D, 20);
    // cross passage through the piers (the arch is open on its short sides)
    for (const s of [-1, 1]) F.box(batch, shadow, s * (L / 2 - 0.2), 0, Z0, 0.04, D - 2.0, 0.02);
    // coffered soffits: transverse ribs in each arch
    for (const [c, w, s] of arches) {
      const n = 4;
      for (let k = 0; k < n; k++) {
        const v = -D / 2 + 0.55 + ((D - 1.1) * k) / (n - 1);
        F.put(
          batch,
          marbleDk,
          new THREE.TorusGeometry(w / 2 - 0.04, 0.07, 4, 16, Math.PI),
          c,
          v,
          Z0 + s,
          0,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
      }
      for (let k = 1; k < 4; k++) {
        const th = (k * Math.PI) / 4;
        F.put(
          batch,
          marbleDk,
          new THREE.BoxGeometry(0.12, D - 1.0, 0.08),
          c + Math.cos(th) * (w / 2 - 0.04),
          0,
          Z0 + s + Math.sin(th) * (w / 2 - 0.04),
          0,
          1,
          1,
          1,
          0,
          Math.PI / 2 - th,
        );
      }
    }
    for (const fv of [-1, 1]) {
      const vf = fv * (D / 2 + 0.06);
      // impost mouldings running across the piers
      for (const [c0, c1] of [
        [-L / 2 + 0.2, -6.5],
        [-4.0, -2.25],
        [2.25, 4.0],
        [6.5, L / 2 - 0.2],
      ]) {
        F.box(
          batch,
          marbleDk,
          (c0 + c1) / 2,
          fv * (D / 2 + 0.05),
          Z0 + 4.1 - 0.3,
          Math.abs(c1 - c0),
          0.12,
          0.3,
        );
      }
      for (const s of [-1, 1])
        F.box(batch, marbleDk, s * 3.125, fv * (D / 2 + 0.05), Z0 + 5.9 - 0.32, 1.75, 0.14, 0.32);
      // archivolts and scrolled keystones
      for (const [c, w, s] of arches) {
        for (const [r0, r1, d, m] of [
          [w / 2, w / 2 + 0.22, 0.12, marbleDk],
          [w / 2 + 0.22, w / 2 + 0.4, 0.2, white],
        ]) {
          const av = new THREE.Shape();
          av.absarc(c, Z0 + s, r1, 0, Math.PI, false);
          av.lineTo(c - r0, Z0 + s);
          av.absarc(c, Z0 + s, r0, Math.PI, 0, true);
          av.lineTo(c + r1, Z0 + s);
          T.slab(F, batch, m, av, 0, fv * (D / 2 + d / 2), 0, d, 18);
        }
        const ks = new THREE.Shape([
          new THREE.Vector2(-0.22, 0),
          new THREE.Vector2(0.22, 0),
          new THREE.Vector2(0.34, 0.85),
          new THREE.Vector2(-0.34, 0.85),
        ]);
        T.slab(F, batch, white, ks, c, fv * (D / 2 + 0.2), Z0 + s + w / 2 - 0.1, 0.4);
        F.box(batch, marbleDk, c, fv * (D / 2 + 0.25), Z0 + s + w / 2 + 0.75, 0.8, 0.5, 0.12);
      }
      // spandrel Victories (winged, reclining along the arch) over the central arch
      for (const s of [-1, 1])
        T.xform(
          batch,
          (b) =>
            T.figure(b, white, 0, 0, 0, 1.7, Math.PI / 2, {
              robe: true,
              wings: true,
              armOut: true,
            }),
          T.at(
            F,
            s * 2.75,
            fv * (D / 2 + 0.05),
            Z0 + 8.05,
            fv > 0 ? 0 : Math.PI,
            1,
            0.3,
            1,
            0,
            -s * fv * 1.3,
          ),
        );
      // relief panels above the side arches (England, Scotland, Ireland / Peace and Plenty)
      for (const s of [-1, 1]) {
        const u = s * 5.25;
        F.box(batch, marbleDk, u, fv * (D / 2 + 0.04), Z0 + 6.25, 2.3, 0.12, 2.75);
        F.box(batch, shadow, u, fv * (D / 2 + 0.06), Z0 + 6.4, 2.0, 0.08, 2.45);
        for (const [du, hh] of [
          [-0.6, 1.9],
          [0, 2.05],
          [0.6, 1.9],
        ])
          T.xform(
            batch,
            (b) =>
              T.figure(b, white, 0, 0, 0, hh, Math.PI / 2, {
                robe: true,
                armUp: du === 0,
                wreath: du === 0,
              }),
            T.at(
              F,
              u + du * (fv > 0 ? 1 : -1),
              fv * (D / 2 + 0.1),
              Z0 + 6.5,
              fv > 0 ? 0 : Math.PI,
              1,
              0.35,
              1,
            ),
          );
      }
      // bronze gates of the central arch: two leaves, St George roundel, lion and the royal cypher
      {
        const v = fv * (D / 2 - 0.5);
        const hg = 5.9;
        for (const s of [-1, 1]) {
          const uc = s * 1.125;
          F.box(batch, bronze, uc, v, Z0, 2.22, 0.1, 0.18);
          F.box(batch, bronze, uc, v, Z0 + hg * 0.46, 2.22, 0.1, 0.14);
          F.box(batch, bronze, uc, v, Z0 + hg - 0.15, 2.22, 0.1, 0.15);
          F.box(batch, bronze, s * 2.2, v, Z0, 0.14, 0.12, hg);
          F.box(batch, bronze, s * 0.04, v, Z0, 0.1, 0.12, hg);
          for (let k = 1; k < 10; k++)
            F.box(batch, bronze, s * (0.04 + (2.16 * k) / 10), v, Z0, 0.035, 0.05, hg);
          F.put(
            batch,
            bronze,
            new THREE.TorusGeometry(0.72, 0.07, 5, 20),
            uc,
            v,
            Z0 + 4.3,
            0,
            1,
            1,
            1,
            Math.PI / 2,
            0,
          );
          F.put(batch, bronze, new THREE.CylinderGeometry(0.66, 0.66, 0.05, 20), uc, v, Z0 + 4.3);
          // St George on horseback (north) / lion passant (south) in relief, gilt highlights
          T.xform(
            batch,
            (b) => T.horse(b, gilt, 0, 0, 0, 0, 0.32, fv > 0 ? 0.4 : 0),
            T.at(
              F,
              uc - 0.05 * s,
              v + fv * 0.06,
              Z0 + 3.7,
              (fv > 0 ? 0 : Math.PI) + (s < 0 ? Math.PI : 0),
              1,
              0.25,
              1,
            ),
          );
          F.put(
            batch,
            bronze,
            new THREE.TorusGeometry(0.42, 0.05, 4, 14),
            uc,
            v,
            Z0 + 1.45,
            0,
            1,
            1,
            1,
            Math.PI / 2,
            0,
          );
          F.box(batch, gilt, uc, v, Z0 + 1.3, 0.34, 0.14, 0.32); // cypher
        }
        F.put(
          batch,
          bronze,
          new THREE.TorusGeometry(2.2, 0.08, 4, 18, Math.PI),
          0,
          v,
          Z0 + 5.9,
          0,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
        for (let k = 1; k < 9; k++) {
          const a = (k / 9) * Math.PI;
          F.put(
            batch,
            bronze,
            new THREE.BoxGeometry(1.7, 0.04, 0.04),
            Math.cos(a) * 1.25,
            v,
            Z0 + 5.9 + Math.sin(a) * 1.25,
            0,
            1,
            1,
            1,
            0,
            -a,
          );
        }
        F.put(batch, gilt, new THREE.SphereGeometry(0.22, 8, 5), 0, v, Z0 + 6.0);
      }
      // free-standing Corinthian columns on pedestals with breakforward entablature
      for (const u of [-7.4, -3.0, 3.0, 7.4]) {
        const vc = fv * (D / 2 + 0.75);
        F.box(batch, marbleDk, u, vc, Z0, 1.7, 1.7, 0.25);
        F.box(batch, white, u, vc, Z0 + 0.25, 1.5, 1.5, 1.4);
        F.box(batch, shadow, u, fv * (D / 2 + 1.51), Z0 + 0.5, 1.1, 0.04, 0.95); // pedestal relief panel
        F.box(batch, marbleDk, u, vc, Z0 + 1.65, 1.7, 1.7, 0.25);
        T.column(F, batch, white, u, vc, Z0 + 1.9, ZE - Z0 - 1.9, 0.4, 'corinthian', 16);
        T.pilaster(
          F,
          batch,
          white,
          u,
          fv * (D / 2 + 0.06),
          Z0 + 1.9,
          ZE - Z0 - 1.9,
          0.75,
          0.1,
          'corinthian',
        );
        // entablature breakforward
        F.box(batch, white, u, fv * (D / 2 + 0.6), ZE, 1.4, 1.2, 0.25);
        F.box(batch, white, u, fv * (D / 2 + 0.62), ZE + 0.25, 1.5, 1.26, 0.3);
        F.box(batch, marbleDk, u, fv * (D / 2 + 0.66), ZE + 0.55, 1.6, 1.32, 0.2);
        F.box(batch, white, u, fv * (D / 2 + 0.7), ZE + 0.75, 1.75, 1.42, 0.32);
        F.box(batch, marbleDk, u, fv * (D / 2 + 0.78), ZE + 1.07, 1.95, 1.58, 0.18);
        F.box(batch, white, u, fv * (D / 2 + 0.78), ZE + 1.25, 1.95, 1.58, 0.15);
        // attic pedestal over the column with a carved trophy panel
        F.box(batch, white, u, fv * (D / 2 + 0.45), ZA, 1.5, 1.0, ZT - ZA - 0.7);
        F.box(batch, shadow, u, fv * (D / 2 + 0.96), ZA + 0.35, 1.0, 0.03, 1.2);
        T.xform(
          batch,
          (b) => T.urn(b, white, 0, 0, 0, 0.9),
          T.at(F, u, fv * (D / 2 + 0.98), ZA + 0.5, 0, 1, 0.25, 1),
        );
        F.box(batch, marbleDk, u, fv * (D / 2 + 0.45), ZT - 0.7, 1.7, 1.2, 0.3);
      }
      // blind attic: panels and the great inverted volute consoles flanking the centre
      for (const s of [-1, 0, 1]) {
        F.box(batch, marbleDk, s * 5.2, fv * (D / 2 - 0.27), ZA + 0.35, s ? 2.7 : 4.1, 0.08, 1.55);
        F.box(batch, shadow, s * 5.2, fv * (D / 2 - 0.24), ZA + 0.45, s ? 2.4 : 3.8, 0.06, 1.35);
      }
      for (const s of [-1, 1]) {
        const sc = new THREE.Shape();
        sc.moveTo(0, 0);
        sc.lineTo(0.55, 0);
        sc.quadraticCurveTo(0.55, 1.2, 0.2, 1.9);
        sc.lineTo(0, 1.9);
        const cg = new THREE.ExtrudeGeometry(sc, {
          depth: 0.5,
          bevelEnabled: false,
          curveSegments: 6,
        })
          .rotateX(Math.PI / 2)
          .translate(0, 0.25, 0)
          .scale(s, 1, 1);
        F.put(batch, white, cg, s * 2.0, fv * (D / 2 - 0.05), ZA);
        for (const zz of [0.35, 1.6])
          F.put(
            batch,
            white,
            new THREE.CylinderGeometry(0.22 - zz * 0.05, 0.22 - zz * 0.05, 0.55, 10),
            s * (2.0 + (zz < 1 ? 0.45 : 0.15)),
            fv * (D / 2 - 0.05),
            ZA + zz,
            Math.PI / 2,
          );
      }
    }
    // main entablature (architrave, frieze, dentil cornice) and attic
    F.box(batch, white, 0, 0, ZE, L, D + 0.1, 0.25);
    F.box(batch, white, 0, 0, ZE + 0.25, L + 0.08, D + 0.18, 0.3);
    F.box(batch, marbleDk, 0, 0, ZE + 0.55, L + 0.16, D + 0.26, 0.2); // frieze
    F.box(batch, white, 0, 0, ZE + 0.75, L + 0.3, D + 0.4, 0.32);
    F.box(batch, marbleDk, 0, 0, ZE + 1.07, L + 0.6, D + 0.7, 0.18);
    F.box(batch, white, 0, 0, ZE + 1.25, L + 0.5, D + 0.6, 0.15);
    for (const fv of [-1, 1]) {
      const [a, b] =
        fv > 0
          ? [F.P(L / 2 + 0.15, D / 2 + 0.2), F.P(-L / 2 - 0.15, D / 2 + 0.2)]
          : [F.P(-L / 2 - 0.15, -D / 2 - 0.2), F.P(L / 2 + 0.15, -D / 2 - 0.2)];
      T.blocks(batch, white, a, b, ZE + 0.85, { w: 0.08, h: 0.12, proj: 0.12, gap: 0.08 });
    }
    F.box(batch, marbleDk, 0, 0, ZA - 0.1, L - 0.4, D - 0.4, 0.25);
    F.box(batch, marble, 0, 0, ZA, L - 0.6, D - 0.6, ZT - ZA - 0.4);
    F.box(batch, marbleDk, 0, 0, ZT - 0.4, L - 0.2, D - 0.2, 0.22);
    F.box(batch, white, 0, 0, ZT - 0.18, L - 0.1, D - 0.1, 0.18);
    F.box(batch, white, 0, 0, ZT, 6.0, D - 1.2, 0.35);
    F.box(batch, marbleDk, 0, 0, ZT + 0.35, 6.2, D - 1.0, 0.1);
    F.box(batch, kit.mat('lead'), 0, 0, ZT - 0.02, L - 0.5, D - 0.5, 0.03);
    // street lamps and benches on the island
    if (placeAssets) {
      const lamps = [],
        benches = [];
      for (const s of [-1, 1])
        for (const fv of [-1, 1]) {
          const [x, y] = F.P(s * (L / 2 + 3.5), fv * (D / 2 + 4.5));
          lamps.push([x, y, frame.angle + (fv > 0 ? 0 : Math.PI)]);
          const [bx, by] = F.P(s * (L / 2 + 1.0), fv * (D / 2 + 5.0));
          benches.push([bx, by, frame.angle + (fv > 0 ? Math.PI : 0)]);
        }
      g.add(placeAssets('street_lamp', lamps));
      g.add(placeAssets('bench', benches));
    }
    g.add(batch.toGroup('marble_arch'));
    return g;
  },
};
