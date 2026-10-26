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
    {
      title: 'Apsley House - British Listed Buildings (list entry 1226873)',
      url: 'https://britishlistedbuildings.co.uk/101226873-apsley-house-west-end-ward',
      used_for:
        'arched entrances in the podium, square-headed architraved sashes, French casements to the first floor, Corinthian pilaster treatment on corners and sides',
    },
  ],
  notes:
    'House walls follow the Overture outline; storey heights (podium 5.6 m, cornice 16 m) are proportioned, not measured (Overture h = 20 m includes roof structures). Detail pass: modelled windows on every elevation (round-headed ground floor in channelled rustication, French casements with cornice hoods, consoles and iron balconettes, architraved second-floor sashes on an assumed 3.3 m bay), Corinthian pilasters on both faces of each convex corner, dentil and modillion cornice, portico with raking cornices, acroteria plinths and a podium balustrade, chimney stacks and a glazed Waterloo Gallery lantern (approximate). Forecourt railings, gate piers with urns and lamps are approximate. Screen: Ionic colonnade with railings between columns, gilded spear-headed gates and a low-relief horsemen frieze after the Parthenon; column count/spacing estimated from its footprint.',
  build({ THREE, kit, byId, placeAssets }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const bath = kit.mat('#d5c095', { roughness: 0.85 });
    const bathDk = kit.mat('#c4ae82', { roughness: 0.85 });
    const bathLt = kit.mat('#dfcda5', { roughness: 0.85 });
    const stone = kit.mat('portland_stone');
    const stoneDk = kit.mat('#c9c0aa', { roughness: 0.85 });
    const lead = kit.mat('lead');
    const slate = kit.mat('slate');
    const glass = kit.mat('#2c3640', { roughness: 0.15, metalness: 0.3 });
    const sashW = kit.mat('#f1ece0', { roughness: 0.6 });
    const iron = kit.mat('#1d1f21', { roughness: 0.5, metalness: 0.4 });
    const gilt = kit.mat('gold');
    const doorM = kit.mat('#2e2a25', { roughness: 0.55 });
    const pot = kit.mat('#9b5a3c', { roughness: 0.8 });
    const gravel = kit.mat('#c9bea6', { roughness: 1 });
    const BAY = 3.3;
    // jointed Bath-stone ashlar (no painted windows: the windows are modelled)
    const upper = kit.paintedMaterial('apsley_house:ashlar', 512, 388, (c, w, h) => {
      B.ashlar(c, w, h, '#d6c297', 'rgba(120,100,70,0.35)', h / 26, w / 10, 0.41);
    });
    const ground = kit.paintedMaterial('apsley_house:rustic', 512, 217, (c, w, h) => {
      c.fillStyle = '#ccb78a';
      c.fillRect(0, 0, w, h);
      const m = h / 5.6;
      const r = kit.rng(0.27);
      for (let y = 0, row = 0; y < h; y += 0.55 * m, row++) {
        c.fillStyle = `rgba(90,70,40,${0.03 + r() * 0.05})`;
        c.fillRect(0, y, w, 0.55 * m);
        c.fillStyle = 'rgba(80,60,35,0.6)';
        c.fillRect(0, y, w, 3); // channelled rustication
        c.fillStyle = 'rgba(255,245,220,0.25)';
        c.fillRect(0, y + 3, w, 1);
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
    B.band(batch, bathDk, ring, 0, 0.5, 0.12); // plinth
    B.band(batch, bathDk, ring, Z1 - 0.1, Z1 + 0.35, 0.18); // podium cornice / first-floor band
    B.band(batch, bath, ring, Z1 - 0.25, Z1 - 0.1, 0.1);
    B.wallsTex(batch, upper, upperRing, Z1, Z2, 4 * BAY);
    B.band(batch, bathLt, upperRing, Z1 + 6.1, Z1 + 6.35, 0.1); // second-floor sill band
    // entablature: architrave, frieze, dentil and modillion cornice
    B.band(batch, bath, upperRing, Z2 - 0.7, Z2 - 0.45, 0.06);
    B.band(batch, bath, upperRing, Z2, Z2 + 0.35, 0.25);
    B.band(batch, bathDk, upperRing, Z2 + 0.35, Z2 + 0.55, 0.35);
    B.band(batch, bathDk, upperRing, Z2 + 0.55, Z3, 0.62);
    B.band(batch, bath, upperRing, Z3 - 0.08, Z3 + 0.04, 0.68);
    for (let k = 0; k < upperRing.length; k++) {
      const a = upperRing[k],
        b = upperRing[(k + 1) % upperRing.length];
      if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 1.5) continue;
      const ao = kit.offsetRing(upperRing, 0.25)[k],
        bo = kit.offsetRing(upperRing, 0.25)[(k + 1) % upperRing.length];
      T.blocks(batch, bathLt, ao, bo, Z2 + 0.37, {
        w: 0.1,
        h: 0.16,
        proj: 0.1,
        gap: 0.09,
        inset: 0.4,
      });
      const am = kit.offsetRing(upperRing, 0.35)[k],
        bm = kit.offsetRing(upperRing, 0.35)[(k + 1) % upperRing.length];
      T.blocks(batch, bath, am, bm, Z2 + 0.55, {
        w: 0.14,
        h: 0.2,
        proj: 0.27,
        gap: 0.55,
        inset: 0.4,
      });
    }
    // parapet with coping and lead flats behind
    const par = kit.offsetRing(upperRing, -0.05);
    B.wallsTex(batch, bath, par, Z3, Z4, 4);
    B.band(batch, bathDk, par, Z4 - 0.15, Z4, 0.1);
    kit.cap(batch, lead, [[kit.offsetRing(upperRing, -0.4)]], Z4 - 0.35);
    B.wallsTex(batch, bath, kit.offsetRing(upperRing, -0.4), Z4 - 0.35, Z4, 4);

    // modelled windows: arched ground floor, French casements (first floor), sashes (second floor)
    const edgeLen = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
    const frontA = front.length === 4 ? front[1] : bumpPts[1],
      frontB = front.length === 4 ? front[2] : bumpPts[2];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = edgeLen(a, b);
      if (len < 2.6) continue;
      const isFront =
        (near(a, ...frontA) && near(b, ...frontB)) || (near(a, ...frontB) && near(b, ...frontA));
      if (isFront)
        // three arched entrances in the podium under the portico
        T.archWin(batch, a, b, 0.35, {
          width: 1.7,
          height: 4.0,
          count: 3,
          glass: doorM,
          frame: sashW,
          stone: bathLt,
          bars: 1,
          surround: 0.22,
        });
      else
        T.archWin(batch, a, b, 1.25, {
          width: 1.25,
          height: 3.0,
          bay: BAY,
          glass,
          frame: sashW,
          stone: bathLt,
          bars: 2,
        });
    }
    for (let k = 0; k < upperRing.length; k++) {
      const a = upperRing[k],
        b = upperRing[(k + 1) % upperRing.length];
      const len = edgeLen(a, b);
      if (len < 2.6) continue;
      const n = Math.max(1, Math.round(len / BAY));
      const opt = { count: n, margin: 0.3, glass, frame: sashW, sill: bathLt, surroundMat: bathLt };
      // first floor: French casements with architraves and cornice hoods, balustered aprons
      const cs = kit.windowRow(batch, a, b, Z1 + 0.85, {
        ...opt,
        width: 1.3,
        height: 3.4,
        bars: 2,
        head: 'lintel',
        surround: 0.16,
        depth: 0.14,
      });
      const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const nx = Math.sin(ang),
        ny = -Math.cos(ang);
      for (const [x, y] of cs) {
        kit.box(batch, bathDk, x + nx * 0.14, y + ny * 0.14, Z1 + 4.45, 1.95, 0.32, 0.12, ang); // cornice hood
        kit.box(batch, bathDk, x + nx * 0.1, y + ny * 0.1, Z1 + 4.57, 1.85, 0.2, 0.06, ang);
        for (const sd of [-1, 1])
          kit.box(
            batch,
            bathLt,
            x + Math.cos(ang) * sd * 0.92 + nx * 0.12,
            y + Math.sin(ang) * sd * 0.92 + ny * 0.12,
            Z1 + 4.05,
            0.14,
            0.24,
            0.42,
            ang,
          ); // consoles
        T.railing(
          batch,
          iron,
          [
            [x - Math.cos(ang) * 0.75 + nx * 0.28, y - Math.sin(ang) * 0.75 + ny * 0.28],
            [x + Math.cos(ang) * 0.75 + nx * 0.28, y + Math.sin(ang) * 0.75 + ny * 0.28],
          ],
          Z1 + 0.35,
          { height: 0.9, spacing: 0.12, post: 5, spear: false },
        );
      }
      // second floor: square-headed architraved sashes
      kit.windowRow(batch, a, b, Z1 + 6.6, {
        ...opt,
        width: 1.15,
        height: 2.2,
        bars: 2,
        head: 'none',
        surround: 0.14,
        depth: 0.12,
      });
    }
    // Corinthian pilasters on both faces of every convex corner
    for (let k = 0; k < upperRing.length; k++) {
      const n = upperRing.length;
      const p = upperRing[k],
        a = upperRing[(k - 1 + n) % n],
        b = upperRing[(k + 1) % n];
      const cr = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]);
      if (cr <= 0) continue; // convex corners only
      for (const [q, dir] of [
        [a, -1],
        [b, 1],
      ]) {
        const len = edgeLen(p, q);
        if (len < 2) continue;
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len;
        // outward normal of the edge (right of the CCW direction)
        const e = dir > 0 ? [ux, uy] : [-ux, -uy];
        const nx = e[1],
          ny = -e[0];
        const cx = p[0] + ux * 0.5 + nx * 0.1,
          cy = p[1] + uy * 0.5 + ny * 0.1;
        const F = T.frame(cx, cy, Math.atan2(e[1], e[0]) + Math.PI);
        T.pilaster(F, batch, bath, 0, 0, Z1 + 0.35, Z2 - Z1 - 0.35, 0.85, 0.2, 'corinthian');
      }
    }
    // portico on the podium: 4 Corinthian columns, entablature and pediment
    {
      const fr = front.length === 4 ? front : bumpPts;
      const A = fr[1],
        Bp = fr[2];
      const len = Math.hypot(Bp[0] - A[0], Bp[1] - A[1]);
      const ang = Math.atan2(Bp[1] - A[1], Bp[0] - A[0]);
      const depth = Math.hypot(fr[1][0] - fr[0][0], fr[1][1] - fr[0][1]) + 0.2;
      const mx = (A[0] + Bp[0]) / 2,
        my = (A[1] + Bp[1]) / 2;
      let n = [Math.sin(ang), -Math.cos(ang)];
      if ((mx - house.c[0]) * n[0] + (my - house.c[1]) * n[1] < 0) n = [-n[0], -n[1]];
      const F = T.frame(mx, my, ang);
      const vIn = -n[0] * -Math.sin(ang) + -n[1] * Math.cos(ang) > 0 ? 1 : -1; // +v towards the house when vIn = 1
      let poly = fr.slice();
      if (kit.ringArea(poly) < 0) poly.reverse();
      kit.cap(batch, bathDk, [[poly]], Z1 + 0.35);
      for (const t of [-0.42, -0.14, 0.14, 0.42]) {
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
          16,
        );
        T.pilaster(
          F,
          batch,
          bath,
          t * len,
          vIn * (depth - 0.05),
          Z1 + 0.35,
          Z2 - Z1 - 0.75,
          0.75,
          0.12,
          'corinthian',
        );
      }
      // balustrade between the column plinths on the podium roof
      T.railing(
        batch,
        iron,
        [F.P(-len / 2 + 0.3, vIn * 0.05), F.P(len / 2 - 0.3, vIn * 0.05)],
        Z1 + 0.35,
        { height: 1.0, spacing: 0.14, post: 2.6, spear: false },
      );
      const ev = vIn * (depth / 2 - 0.25);
      F.box(batch, bath, 0, ev, Z2 - 0.4, len + 0.4, depth + 0.4, 0.4); // architrave
      F.box(batch, bathLt, 0, ev, Z2, len + 0.5, depth + 0.5, 0.35); // frieze
      F.box(batch, bathDk, 0, ev, Z2 + 0.35, len + 0.9, depth + 0.9, 0.45); // cornice
      T.blocks(
        batch,
        bathLt,
        F.P(-vIn * (len / 2 + 0.42), -vIn * 0.5),
        F.P(vIn * (len / 2 + 0.42), -vIn * 0.5),
        Z2 + 0.37,
        { w: 0.1, h: 0.16, proj: 0.12, gap: 0.09 },
      );
      const ped = new THREE.Shape([
        new THREE.Vector2(-len / 2 - 0.45, 0),
        new THREE.Vector2(len / 2 + 0.45, 0),
        new THREE.Vector2(0, 2.7),
      ]);
      T.slab(F, batch, bath, ped, 0, ev, Z2 + 0.8, depth + 0.9);
      // raking cornices
      const rake = Math.atan2(2.7, len / 2 + 0.45);
      const rl = Math.hypot(2.7, len / 2 + 0.45);
      for (const sd of [-1, 1])
        F.put(
          batch,
          bathDk,
          new THREE.BoxGeometry(rl + 0.2, depth + 1.1, 0.3),
          (sd * (len / 2 + 0.45)) / 2,
          ev,
          Z2 + 0.95 + 1.35,
          0,
          1,
          1,
          1,
          0,
          sd * rake,
        );
      const tym = new THREE.Shape([
        new THREE.Vector2(-len / 2 + 0.3, 0),
        new THREE.Vector2(len / 2 - 0.3, 0),
        new THREE.Vector2(0, 2.05),
      ]);
      T.slab(F, batch, bathDk, tym, 0, vIn * -0.5, Z2 + 0.95, 0.1);
      // acroteria plinths
      for (const sd of [-1, 0, 1])
        F.box(batch, bath, sd * (len / 2 + 0.3), ev, Z2 + 0.8 + (sd ? 0.1 : 2.75), 0.7, 0.9, 0.45);
      // forecourt: gravel, railings with gate piers and lamps, central gates opposite the portico
      const dF = 7.5; // railing distance in front of the portico
      kit.cap(batch, gravel, [[kit.offsetRing(poly, 0.02)]], 0.03);
      F.box(batch, gravel, 0, -vIn * (dF / 2), 0, len + 18, dF, 0.04);
      const rl0 = F.P(-len / 2 - 9, -vIn * dF),
        rl1 = F.P(-2.2, -vIn * dF),
        rr0 = F.P(2.2, -vIn * dF),
        rr1 = F.P(len / 2 + 9, -vIn * dF);
      for (const [p, q] of [
        [rl0, rl1],
        [rr0, rr1],
      ]) {
        kit.box(
          batch,
          bathDk,
          (p[0] + q[0]) / 2,
          (p[1] + q[1]) / 2,
          0,
          Math.hypot(q[0] - p[0], q[1] - p[1]),
          0.45,
          0.45,
          ang,
        );
        T.railing(batch, iron, [p, q], 0.45, {
          height: 1.5,
          spacing: 0.13,
          post: 3.0,
          finial: gilt,
        });
      }
      for (const sd of [-1, 1]) {
        F.box(batch, bath, sd * 2.4, -vIn * dF, 0, 0.8, 0.8, 2.6);
        F.box(batch, bathDk, sd * 2.4, -vIn * dF, 2.6, 1.0, 1.0, 0.25);
        T.urn(batch, bath, ...F.P(sd * 2.4, -vIn * dF), 2.85, 0.9);
        T.railing(batch, iron, [F.P(sd * 2.0, -vIn * dF), F.P(sd * 0.03, -vIn * dF)], 0.05, {
          height: 2.2,
          spacing: 0.12,
          post: 5,
          finial: gilt,
        });
      }
      if (placeAssets) {
        const lamps = [-1, 1].map((sd) => [...F.P(sd * (len / 2 + 1.5), -vIn * (dF - 0.8)), ang]);
        g.add(placeAssets('street_lamp', lamps));
      }
    }
    // chimney stacks and the Waterloo Gallery roof lantern
    {
      const fr = kit.ringFrame(upperRing);
      const F = T.frame(fr.cx, fr.cy, fr.angle);
      for (const [u, v] of [
        [-fr.length * 0.3, fr.width * 0.3],
        [fr.length * 0.05, fr.width * 0.35],
        [fr.length * 0.3, -fr.width * 0.25],
        [-fr.length * 0.05, -fr.width * 0.3],
      ]) {
        const [x, y] = F.P(u, v);
        T.chimney(batch, bath, pot, x, y, Z4 - 0.35, 1.0, 2.6, 2.3, fr.angle + Math.PI / 2, 4);
      }
      // glazed lantern with hipped lead roof over the gallery
      const lu = -fr.length * 0.12,
        lv = fr.width * 0.05,
        lw = fr.length * 0.35;
      F.box(batch, lead, lu, lv, Z4 - 0.35, lw + 0.6, 5.6, 0.5);
      F.box(batch, kit.mat('glass'), lu, lv, Z4 + 0.15, lw, 5.0, 1.0);
      for (let k = 0; k <= 12; k++)
        F.box(batch, sashW, lu - lw / 2 + (lw * k) / 12, lv, Z4 + 0.15, 0.08, 5.06, 1.0);
      const lr = [
        F.P(lu - lw / 2, lv - 2.5),
        F.P(lu + lw / 2, lv - 2.5),
        F.P(lu + lw / 2, lv + 2.5),
        F.P(lu - lw / 2, lv + 2.5),
      ];
      kit.pitchedRoof(
        batch,
        kit.mat('glass'),
        kit.mat('glass'),
        lr,
        fr.angle,
        Z4 + 1.15,
        1.4,
        'hipped',
        { overhang: 0.2 },
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
      F.box(batch, stoneDk, 0, 0, 0, L + 0.3, 2.7, 0.25); // steps
      F.box(batch, stone, 0, 0, 0.25, L, 2.4, zc - 0.25); // stylobate
      const gw = 11.2;
      // central gateway: four columns per face, attic with the Elgin-marbles frieze
      for (const v of [-1.15, 1.15])
        for (const u of [-4.6, -1.7, 1.7, 4.6])
          T.column(F, batch, stone, u, v, zc, colH, 0.4, 'ionic', 12);
      for (const s of [-1, 1]) {
        F.box(batch, stone, s * 5.4, 0, zc, 1.3, 2.0, colH); // end piers of gateway
        T.pilaster(F, batch, stone, s * 5.4, 1.05, zc, colH, 0.9, 0.08, 'ionic');
        T.pilaster(F, batch, stone, s * 5.4, -1.05, zc, colH, 0.9, 0.08, 'ionic', Math.PI);
      }
      F.box(batch, stone, 0, 0, zE, gw + 0.6, 3.2, 0.45); // architrave
      F.box(batch, stone, 0, 0, zE + 0.45, gw + 0.7, 3.3, 0.5); // frieze
      F.box(batch, stoneDk, 0, 0, zE + 0.95, gw + 1.0, 3.5, 0.12);
      F.box(batch, stone, 0, 0, zE + 1.07, gw + 1.1, 3.6, 0.23);
      F.box(batch, stoneDk, 0, 0, zE + 1.3, gw + 1.2, 3.7, 0.15);
      T.blocks(batch, stone, F.P(gw / 2 + 0.5, 1.75), F.P(-gw / 2 - 0.5, 1.75), zE + 0.95, {
        w: 0.09,
        h: 0.12,
        proj: 0.1,
        gap: 0.08,
      });
      T.blocks(batch, stone, F.P(-gw / 2 - 0.5, -1.75), F.P(gw / 2 + 0.5, -1.75), zE + 0.95, {
        w: 0.09,
        h: 0.12,
        proj: 0.1,
        gap: 0.08,
      });
      F.box(batch, stoneDk, 0, 0, zE + 1.45, gw - 0.3, 2.8, 0.3);
      F.box(batch, stone, 0, 0, zE + 1.75, gw - 0.6, 2.6, 2.4); // attic
      for (const s of [-1, 1]) {
        F.box(batch, kit.mat('#c9c0aa'), 0, s * 1.31, zE + 2.05, gw - 1.6, 0.04, 1.6); // frieze ground
        // procession of horsemen and chariots after the Parthenon frieze (low relief)
        for (let k = 0; k < 5; k++) {
          const u = -gw / 2 + 1.6 + k * ((gw - 3.2) / 4);
          T.xform(
            batch,
            (b) => {
              T.horse(b, stone, 0, 0, 0, 0, 0.42, k % 3 === 0 ? 0.45 : 0);
              T.figure(b, stone, -0.1, 0, 0.55, 0.75, 0, { cloak: true });
            },
            T.at(F, u, s * 1.33, zE + 2.1, s > 0 ? 0 : Math.PI, 1, 0.18, 1),
          );
        }
      }
      F.box(batch, stoneDk, 0, 0, zE + 4.15, gw - 0.2, 3.0, 0.2);
      F.box(batch, stone, 0, 0, zE + 4.35, gw, 3.1, 0.3);
      // flanking colonnades and the two side entrances with end piers
      for (const s of [-1, 1]) {
        const u0 = gw / 2 + 1.3,
          u1 = hz - 4.2;
        const n = Math.max(2, Math.round((u1 - u0) / 2.6));
        const us = [];
        for (let k = 0; k <= n; k++) {
          const u = s * (u0 + ((u1 - u0) * k) / n);
          us.push(u);
          T.column(F, batch, stone, u, 0, zc, colH, 0.36, 'ionic', 12);
        }
        // iron railings between the columns
        for (let k = 1; k < us.length; k++)
          T.railing(batch, iron, [F.P(us[k - 1] + s * 0.45, 0), F.P(us[k] - s * 0.45, 0)], zc, {
            height: 2.4,
            spacing: 0.14,
            post: 9,
            finial: gilt,
          });
        F.box(batch, stone, (s * (u0 + u1)) / 2, 0, zE, u1 - u0 + 1.0, 1.4, 0.45);
        F.box(batch, stone, (s * (u0 + u1)) / 2, 0, zE + 0.45, u1 - u0 + 1.05, 1.45, 0.45);
        F.box(batch, stoneDk, (s * (u0 + u1)) / 2, 0, zE + 0.9, u1 - u0 + 1.2, 1.7, 0.12);
        F.box(batch, stone, (s * (u0 + u1)) / 2, 0, zE + 1.02, u1 - u0 + 1.25, 1.75, 0.25);
        // side entrance: two columns between solid piers
        for (const u of [hz - 3.4, hz - 1.4])
          T.column(F, batch, stone, s * u, 0, zc, colH, 0.36, 'ionic', 12);
        F.box(batch, stone, s * (hz - 0.45), 0, zc, 0.9, 2.3, colH);
        F.box(batch, stone, s * (hz - 4.25), 0, zc, 0.9, 2.0, colH);
        F.box(batch, stone, s * (hz - 2.3), 0, zE, 4.6, 2.4, 1.1);
        F.box(batch, stone, s * (hz - 2.3), 0, zE + 1.1, 4.9, 2.7, 0.35);
        // iron gates in the side entrance
        gate(F, s * (hz - 2.4), 0, zc, 3.0, 3.4);
      }
      // gates in the central opening
      gate(F, 0, 0, zc, 2.9, 5.2);
      for (const u of [-3.15, 3.15]) gate(F, u, 0, zc, 2.3, 4.2);
    }
    function gate(F, u, v, z, w, h) {
      const n = Math.round(w / 0.13);
      F.box(batch, iron, u, v, z, w, 0.08, 0.1);
      F.box(batch, iron, u, v, z + h * 0.55, w, 0.08, 0.08);
      F.box(batch, iron, u, v, z + h - 0.1, w, 0.08, 0.1);
      F.box(batch, iron, u, v, z, 0.08, 0.1, h);
      for (let k = 0; k <= n; k++) {
        const uu = u - w / 2 + (w * k) / n;
        F.box(batch, iron, uu, v, z, 0.03, 0.03, h + 0.15);
        F.put(
          batch,
          gilt,
          new THREE.ConeGeometry(0.04, 0.14, 4).rotateX(Math.PI / 2),
          uu,
          v,
          z + h + 0.22,
        );
      }
      for (const sd of [-1, 1])
        F.put(
          batch,
          gilt,
          new THREE.TorusGeometry(Math.min(0.35, w / 6), 0.03, 4, 12),
          u + (sd * w) / 4,
          v,
          z + h * 0.75,
          0,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
    }
    g.add(batch.toGroup('apsley_house'));
    return g;
  },
};
