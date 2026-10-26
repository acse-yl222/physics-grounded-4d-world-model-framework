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
        'single wide opening flanked by pairs of Corinthian columns standing well forward, Corinthian pilasters at corners and sides, blank frieze, blank attic as quadriga pedestal, Burton gates with garland ornament and circular panels bearing the royal arms, Portland stone facing, faces east down Constitution Hill',
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
    {
      title: 'Wellington Arch - Victorian Web (Adrian Jones quadriga)',
      url: 'https://victorianweb.org/victorian/sculpture/jones/2.html',
      used_for: 'boy charioteer leaning forward with the reins',
    },
    {
      title: 'Wellington Arch and Quadriga - Art UK',
      url: 'https://artuk.org/artworks/265475',
      used_for:
        'four rearing horses, boy driver, chariot loaded with trophies of war (flags, cannon)',
    },
  ],
  notes:
    "Arch massing from the Overture footprint (22 m x 13 m body plus column porticoes); heights proportioned (entablature 12.3-15 m, attic to 18.4 m, Victory ~28 m) - no measured elevation was found. Detail pass: jointed ashlar, fluted Corinthian columns with acanthus/volute capitals, Corinthian pilasters at corners and ends (per English Heritage), three-fascia architrave, blank frieze (garlands never carved), dentil + modillion cornice with breakforwards, moulded archivolts and keystones, coffered passage vault, pier doors, Burton's gates with garland roundels (royal arms simplified to gilt shields) and a radiating lunette; laurel wreaths in the pier panels are assumed. Quadriga horses and figures are stylised low-poly bronzes; heading (east, towards the Palace) is assumed. Royal Artillery Memorial (howitzer, reliefs, four bronzes) and Wellington statue are simplified; island lamps are resources assets.",
  build({ THREE, kit, byId, placeAssets }) {
    const T = tools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const stone = kit.mat('portland_stone');
    const stoneDk = kit.mat('#cfc7b2', { roughness: 0.85 });
    const stoneSh = kit.mat('#bdb5a0', { roughness: 0.9 });
    const voidm = kit.mat('#4a463c', { roughness: 0.9 });
    const bronze = kit.mat('#3f4a3e', { roughness: 0.42, metalness: 0.55 });
    const iron = kit.mat('#23272a', { roughness: 0.5, metalness: 0.5 });
    const gilt = kit.mat('gold');
    const granite = kit.mat('#8b817b', { roughness: 0.7 });
    const graniteDk = kit.mat('#6f6762', { roughness: 0.7 });
    const paving = kit.mat('paving');
    const setts = kit.mat('#a39c90', { roughness: 0.95 });
    const ashlar = kit.paintedMaterial('wellington_arch:ashlar', 512, 512, (c, w, h) => {
      // 4 m x 4 m of Portland ashlar: 0.5 m courses, 1.25 m blocks, faint joints
      const r = kit.rng(0.731);
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, 0, w, h);
      const ch = h / 8,
        bw = w / 3.2;
      for (let row = 0; row < 8; row++) {
        for (let x = -((row % 2) * bw) / 2; x < w; x += bw) {
          c.fillStyle = `rgba(${150 + r() * 40},${140 + r() * 40},${110 + r() * 30},${0.05 + r() * 0.07})`;
          c.fillRect(x, row * ch, bw, ch);
          c.fillStyle = 'rgba(110,100,80,0.35)';
          c.fillRect(x, row * ch, 2, ch);
        }
        c.fillStyle = 'rgba(110,100,80,0.4)';
        c.fillRect(0, row * ch, w, 2);
      }
    });
    ashlar.map.repeat.set(0.25, 0.25);

    // ---------------- Wellington Arch ----------------
    const arch = byId['cc9ab33d-299e-4224-8dbb-c15280b83611'];
    const fr = kit.ringFrame(arch.polys[0][0]);
    let ang = fr.angle;
    if (Math.sin(ang) < 0) ang += Math.PI; // u axis points north along the facade
    const F = T.frame(fr.cx, fr.cy, ang);
    const W = 21.8,
      D = 12.6;
    const AW = 6.8,
      AS = 8.4,
      AR = AW / 2; // archway width, springing, radius
    const ZE = 12.3, // top of capitals / foot of entablature
      ZC = 15.0, // top of cornice
      ZA = 18.4; // top of attic die
    // granite-sett island pad and stepped podium
    F.box(batch, setts, 0, 0, 0, W + 9, D + 12, 0.06);
    F.box(batch, stoneDk, 0, 0, 0, W + 0.9, D + 0.9, 0.3);
    F.box(batch, stoneDk, 0, 0, 0.3, W + 0.6, D + 0.6, 0.45);
    F.box(batch, stone, 0, 0, 0.75, W + 0.75, D + 0.75, 0.15);
    // arch body of jointed ashlar with the single round-headed opening
    T.slab(F, batch, ashlar, T.archShape(W, ZE, [{ c: 0, w: AW, s: AS }]), 0, 0, 0, D, 24);
    F.box(batch, setts, 0, 0, 0, AW - 0.02, D - 0.2, 0.08); // passage floor
    // impost band (continues through the passage) and archivolt with keystone
    for (const s of [-1, 1]) {
      F.box(batch, stoneDk, s * (W / 4 + AR / 2), 0, AS - 0.35, W / 2 - AR + 0.1, D + 0.25, 0.3);
      F.box(batch, stone, s * (W / 4 + AR / 2), 0, AS - 0.05, W / 2 - AR + 0.2, D + 0.35, 0.15);
      F.box(batch, stone, s * (W / 2 + 0.06), 0, 0.9, 0.12, D - 1.2, ZE - 0.9);
    }
    for (const fv of [-1, 1]) {
      for (const [r0, r1, d, m] of [
        [AR, AR + 0.35, 0.18, stoneDk],
        [AR + 0.35, AR + 0.6, 0.28, stone],
        [AR + 0.6, AR + 0.72, 0.36, stoneDk],
      ]) {
        const av = new THREE.Shape();
        av.absarc(0, AS, r1, 0, Math.PI, false);
        av.lineTo(-r0, AS);
        av.absarc(0, AS, r0, Math.PI, 0, true);
        av.lineTo(r1, AS);
        T.slab(F, batch, m, av, 0, fv * (D / 2 + d / 2), 0, d, 24);
      }
      // scrolled keystone
      const ks = new THREE.Shape([
        new THREE.Vector2(-0.35, 0),
        new THREE.Vector2(0.35, 0),
        new THREE.Vector2(0.55, 1.35),
        new THREE.Vector2(-0.55, 1.35),
      ]);
      T.slab(F, batch, stone, ks, 0, fv * (D / 2 + 0.25), AS + AR - 0.15, 0.5);
      F.box(batch, stoneDk, 0, fv * (D / 2 + 0.3), AS + AR + 1.2, 1.3, 0.62, 0.2);
    }
    // coffered vault: transverse ribs and longitudinal ribs on the soffit
    {
      const nT = 7;
      for (let k = 0; k < nT; k++) {
        const v = -D / 2 + 0.6 + ((D - 1.2) * k) / (nT - 1);
        const tor = new THREE.TorusGeometry(AR - 0.06, 0.1, 4, 20, Math.PI);
        F.put(batch, stoneDk, tor, 0, v, AS, 0, 1, 1, 1, Math.PI / 2, 0);
        for (const s of [-1, 1])
          F.box(batch, stoneDk, s * (AR - 0.06), v, 0.9, 0.12, 0.22, AS - 1.2);
      }
      for (let k = 1; k < 6; k++) {
        const th = (k * Math.PI) / 6;
        const geo = new THREE.BoxGeometry(0.16, D - 1.0, 0.12);
        F.put(
          batch,
          stoneDk,
          geo,
          Math.cos(th) * (AR - 0.06),
          0,
          AS + Math.sin(th) * (AR - 0.06),
          0,
          1,
          1,
          1,
          0,
          Math.PI / 2 - th,
        );
        // rosette in each coffer
        for (let j = 0; j < nT - 1; j++) {
          const v = -D / 2 + 0.6 + ((D - 1.2) * (j + 0.5)) / (nT - 1);
          const t2 = ((k - 0.5) * Math.PI) / 6;
          F.put(
            batch,
            stone,
            new THREE.SphereGeometry(0.16, 6, 4),
            Math.cos(t2) * (AR - 0.04),
            v,
            AS + Math.sin(t2) * (AR - 0.04),
            0,
            1,
            1,
            0.5,
            0,
            Math.PI / 2 - t2,
          );
        }
      }
      const th = (0.5 * Math.PI) / 6;
      for (let j = 0; j < nT - 1; j++) {
        const v = -D / 2 + 0.6 + ((D - 1.2) * (j + 0.5)) / (nT - 1);
        for (const t2 of [th, Math.PI - th])
          F.put(
            batch,
            stone,
            new THREE.SphereGeometry(0.16, 6, 4),
            Math.cos(t2) * (AR - 0.04),
            v,
            AS + Math.sin(t2) * (AR - 0.04),
            0,
            1,
            1,
            0.5,
            0,
            Math.PI / 2 - t2,
          );
      }
      // panelled doors into the piers from the passage
      for (const s of [-1, 1]) {
        const [x, y] = F.P(s * (AR - 0.02), 0);
        T.door(
          batch,
          { leaf: kit.mat('#3b4a3f', { roughness: 0.6 }), frame: stoneDk },
          x,
          y,
          0.9,
          1.4,
          2.9,
          ang + (s > 0 ? -Math.PI / 2 : Math.PI / 2),
          { surround: 0.22 },
        );
      }
    }
    // Burton's cast-iron gates: pairs of leaves with garland roundels and a radiating lunette
    for (const fv of [-1, 1]) {
      const v = fv * (D / 2 - 0.9);
      const zg = 0.9,
        hg = AS - 0.9;
      for (const s of [-1, 1]) {
        const uc = (s * AR) / 2;
        F.box(batch, iron, uc, v, zg, AR - 0.05, 0.12, 0.16);
        F.box(batch, iron, uc, v, zg + hg - 0.16, AR - 0.05, 0.12, 0.16);
        F.box(batch, iron, uc, v, zg + hg * 0.33, AR - 0.05, 0.1, 0.12);
        F.box(batch, iron, s * (AR - 0.1), v, zg, 0.2, 0.14, hg);
        F.box(batch, iron, s * 0.06, v, zg, 0.12, 0.14, hg);
        for (let k = 1; k < 14; k++)
          F.box(batch, iron, s * (0.06 + ((AR - 0.16) * k) / 14), v, zg, 0.04, 0.05, hg);
        // roundels with the royal arms
        for (const zz of [zg + hg * 0.62, zg + hg * 0.17]) {
          const rr = zz > zg + 2 ? 1.15 : 0.6;
          F.put(
            batch,
            iron,
            new THREE.TorusGeometry(rr, 0.09, 5, 22),
            uc,
            v,
            zz,
            0,
            1,
            1,
            1,
            Math.PI / 2,
            0,
          );
          F.put(
            batch,
            iron,
            new THREE.TorusGeometry(rr * 0.8, 0.05, 4, 20),
            uc,
            v,
            zz,
            0,
            1,
            1,
            1,
            Math.PI / 2,
            0,
          );
          if (rr > 1) {
            F.put(
              batch,
              iron,
              new THREE.CylinderGeometry(rr * 0.78, rr * 0.78, 0.05, 20),
              uc,
              v,
              zz,
              0,
              1,
              1,
              1,
              0,
              0,
            );
            const sh = new THREE.Shape();
            sh.moveTo(-0.38, 0.45);
            sh.lineTo(0.38, 0.45);
            sh.lineTo(0.38, -0.05);
            sh.quadraticCurveTo(0.35, -0.42, 0, -0.55);
            sh.quadraticCurveTo(-0.35, -0.42, -0.38, -0.05);
            for (const fs of [-1, 1]) {
              T.slab(F, batch, gilt, sh, uc, v + fs * 0.06, zz - 0.05, 0.04, 6);
              F.put(
                batch,
                gilt,
                new THREE.TorusGeometry(0.2, 0.05, 4, 10, Math.PI),
                uc,
                v + fs * 0.07,
                zz + 0.55,
                0,
                1,
                1,
                1,
                Math.PI / 2,
                0,
              );
            }
            // garland swags around the roundel
            for (let k = 0; k < 10; k++) {
              const a = (k / 10) * Math.PI * 2;
              F.put(
                batch,
                gilt,
                new THREE.SphereGeometry(0.11, 5, 3),
                uc + Math.cos(a) * (rr + 0.2),
                v,
                zz + Math.sin(a) * (rr + 0.2),
                0,
                1,
                0.6,
                1,
              );
            }
          }
        }
      }
      // fixed lunette over the gates
      for (let k = 1; k < 12; k++) {
        const a = (k / 12) * Math.PI;
        const geo = new THREE.BoxGeometry(AR - 0.5, 0.05, 0.05);
        F.put(
          batch,
          iron,
          geo,
          (Math.cos(a) * (AR + 0.4)) / 2,
          v,
          AS + (Math.sin(a) * (AR + 0.4)) / 2,
          0,
          1,
          1,
          1,
          0,
          -a,
        );
      }
      F.put(
        batch,
        iron,
        new THREE.TorusGeometry(AR - 0.08, 0.08, 4, 20, Math.PI),
        0,
        v,
        AS,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      F.put(
        batch,
        iron,
        new THREE.TorusGeometry(0.6, 0.07, 4, 12, Math.PI),
        0,
        v,
        AS,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      F.put(batch, gilt, new THREE.SphereGeometry(0.28, 8, 5), 0, v, AS + 0.15);
    }
    // corner and end Corinthian pilasters
    for (const s of [-1, 1]) {
      for (const fv of [-1, 1]) {
        T.pilaster(
          F,
          batch,
          stone,
          s * (W / 2 - 0.6),
          fv * (D / 2 + 0.1),
          0.9,
          ZE - 0.9,
          1.05,
          0.22,
          'corinthian',
        );
        T.pilaster(
          F,
          batch,
          stone,
          s * (W / 2 + 0.1),
          fv * (D / 2 - 0.6),
          0.9,
          ZE - 0.9,
          1.05,
          0.22,
          'corinthian',
          Math.PI / 2,
        );
      }
      for (const vv of [-2.1, 2.1])
        T.pilaster(
          F,
          batch,
          stone,
          s * (W / 2 + 0.1),
          vv,
          0.9,
          ZE - 0.9,
          1.05,
          0.22,
          'corinthian',
          Math.PI / 2,
        );
      // sunk panels on the end elevations
      F.box(batch, stoneSh, s * (W / 2 + 0.02), 0, 2.2, 0.1, 2.4, 5.4);
      F.box(batch, stoneDk, s * (W / 2 + 0.06), 0, 9.0, 0.12, 2.8, 2.4);
      F.put(
        batch,
        stone,
        new THREE.TorusGeometry(0.85, 0.16, 5, 16),
        s * (W / 2 + 0.16),
        0,
        10.2,
        Math.PI / 2,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      for (const fv of [-1, 1]) {
        // moulded sunk panel and laurel wreath panel on the outer piers
        const uu = s * 8.8;
        const vf = fv * (D / 2 + 0.02);
        F.box(batch, stoneDk, uu, vf, 1.7, 1.6, 0.14, 5.6);
        F.box(batch, stoneSh, uu, fv * (D / 2 + 0.05), 1.85, 1.35, 0.14, 5.3);
        F.box(batch, stoneDk, uu, vf, 9.0, 1.6, 0.14, 2.6);
        F.put(
          batch,
          stone,
          new THREE.TorusGeometry(0.55, 0.13, 5, 16),
          uu,
          fv * (D / 2 + 0.12),
          10.3,
          0,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
        for (const t of [-1, 1]) {
          const [x0, y0] = F.P(uu + t * 0.3, fv * (D / 2 + 0.12));
          const [x1, y1] = F.P(uu + t * 0.7, fv * (D / 2 + 0.12));
          T.rod(batch, stone, [x0, y0, 9.65], [x1, y1, 9.3], 0.07, 0.04, 4, true); // ribbon ends
        }
      }
    }
    // free-standing Corinthian column pairs on both faces with breakforward entablature
    const colR = 0.52;
    for (const fv of [-1, 1]) {
      const vc = fv * (D / 2 + 1.35);
      for (const s of [-1, 1]) {
        // pedestal: base, die, cornice
        F.box(batch, stoneDk, s * 5.5, vc, 0.9, 4.3, 2.3, 0.3);
        F.box(batch, stone, s * 5.5, vc, 1.2, 4.0, 2.0, 0.85);
        F.box(batch, stoneDk, s * 5.5, vc, 2.05, 4.25, 2.25, 0.25);
        F.box(batch, stone, s * 5.5, (fv * D) / 2 + fv * 0.15, 0.9, 4.6, 0.3, ZE - 0.9); // pilaster backing
        for (const uu of [4.45, 6.55]) {
          T.column(F, batch, stone, s * uu, vc, 2.3, ZE - 2.3, colR, 'corinthian', 16);
          T.pilaster(
            F,
            batch,
            stone,
            s * uu,
            (fv * D) / 2 + fv * 0.3,
            2.3,
            ZE - 2.3,
            1.0,
            0.12,
            'corinthian',
          );
        }
      }
    }
    // entablature: three-fascia architrave, blank frieze (garlands never carved), modillion cornice
    const entab = (u0, u1, v0, v1, z, depthCut = false) => {
      const cu = (u0 + u1) / 2,
        cv = (v0 + v1) / 2,
        L = u1 - u0,
        Dd = v1 - v0;
      const st = [
        [stone, 0.0, 0.3],
        [stone, 0.06, 0.32],
        [stone, 0.12, 0.33],
        [stoneDk, 0.2, 0.05],
        [stone, 0.08, 1.0], // frieze
        [stoneDk, 0.18, 0.1],
        [stone, 0.25, 0.15], // bed mould + dentil band
        [stone, 0.65, 0.22], // corona
        [stoneDk, 0.75, 0.08],
        [stone, 0.7, 0.1],
      ];
      let zz = z;
      for (const [m, p, h] of st) {
        F.box(batch, m, cu, cv, zz, L + 2 * p, Dd + 2 * p, h);
        zz += h;
      }
      // dentils under the bed mould and modillions under the corona
      const zD = z + 0.3 + 0.32 + 0.33 + 0.05 + 1.0 + 0.1;
      const corners = [
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      ];
      for (let k = 0; k < 4; k++) {
        const a = corners[k],
          b = corners[(k + 1) % 4];
        const off = (p) => {
          // move edge outwards by p in local coordinates
          const du = b[0] - a[0],
            dv = b[1] - a[1],
            l = Math.hypot(du, dv);
          const nu = dv / l,
            nv = -du / l;
          return [F.P(a[0] + nu * p, a[1] + nv * p), F.P(b[0] + nu * p, b[1] + nv * p)];
        };
        if (depthCut && (k === 0 || k === 2)) continue;
        const [A1, B1] = off(0.18);
        T.blocks(batch, stoneDk, A1, B1, zD, { w: 0.11, h: 0.14, proj: 0.12, gap: 0.1 });
        const [A2, B2] = off(0.25);
        T.blocks(batch, stone, A2, B2, zD + 0.15, { w: 0.16, h: 0.22, proj: 0.38, gap: 0.5 });
      }
      return zz;
    };
    entab(-W / 2 - 0.1, W / 2 + 0.1, -D / 2 - 0.1, D / 2 + 0.1, ZE);
    for (const fv of [-1, 1])
      for (const s of [-1, 1]) {
        const v0 = fv > 0 ? D / 2 : -D / 2 - 2.0,
          v1 = fv > 0 ? D / 2 + 2.0 : -D / 2;
        entab(s * 5.5 - 1.85, s * 5.5 + 1.85, v0, v1, ZE);
      }
    // attic: moulded base, die with breakforwards and sunk panels, cornice and blocking course
    F.box(batch, stoneDk, 0, 0, ZC, W - 1.9, D - 0.9, 0.3);
    F.box(batch, stone, 0, 0, ZC, W - 2.4, D - 1.4, ZA - ZC);
    for (const fv of [-1, 1]) {
      for (const s of [-1, 1]) {
        F.box(batch, stoneDk, s * 5.5, fv * (D / 2 - 0.2), ZC, 4.6, 1.6, 0.3);
        F.box(batch, stone, s * 5.5, fv * (D / 2 + 0.3), ZC, 4.2, 2.0, ZA - ZC);
        F.box(batch, stoneSh, s * 5.5, fv * (D / 2 + 1.31), ZC + 0.7, 3.2, 0.04, 2.0);
        F.box(batch, stoneDk, s * 5.5, fv * (D / 2 + 0.3), ZA, 4.6, 2.4, 0.25);
        F.box(batch, stone, s * 5.5, fv * (D / 2 + 0.3), ZA + 0.25, 4.8, 2.6, 0.2);
      }
      F.box(batch, stoneSh, 0, fv * (D / 2 - 0.69), ZC + 0.8, 5.4, 0.04, 2.1);
    }
    for (const s of [-1, 1])
      F.box(batch, stoneSh, s * (W / 2 - 1.19), 0, ZC + 0.8, 0.04, D - 3.6, 2.1);
    F.box(batch, stoneDk, 0, 0, ZA, W - 1.8, D - 0.8, 0.25);
    F.box(batch, stone, 0, 0, ZA + 0.25, W - 1.6, D - 0.6, 0.2);
    F.box(batch, stone, 0, 0, ZA + 0.45, W - 2.6, D - 1.6, 0.35); // blocking course
    // quadriga pedestal with mouldings
    F.box(batch, stoneDk, 0, 0, ZA + 0.8, 13.0, 6.8, 0.15);
    F.box(batch, stone, 0, 0, ZA + 0.95, 12.6, 6.4, 0.6);
    F.box(batch, stoneDk, 0, 0, ZA + 1.55, 12.9, 6.7, 0.12);
    // lead roof flats between the blocking course and the pedestal
    F.box(batch, kit.mat('lead'), 0, 0, ZA + 0.45, W - 2.7, D - 1.7, 0.37);

    // Quadriga: four rearing horses abreast, chariot, boy driver and winged Peace.
    const z0 = ZA + 1.67;
    const head = ang - Math.PI / 2 + (Math.cos(ang - Math.PI / 2) < 0 ? Math.PI : 0); // east-facing heading
    const hdir = [Math.cos(head), Math.sin(head)];
    const at = (a, b) => {
      const [x, y] = F.P(0, 0);
      return [x + a * hdir[0] - b * hdir[1], y + a * hdir[1] + b * hdir[0]];
    };
    for (const [k, b] of [
      [0, -2.6],
      [1, -0.9],
      [2, 0.9],
      [3, 2.6],
    ]) {
      const [x, y] = at(1.0 + (k % 2) * 0.35, b);
      T.horse(batch, bronze, x, y, z0, head + b * 0.07, 2.3, k === 0 || k === 3 ? 0.85 : 0.55);
      // harness: collar and reins back to the driver
      const [cx, cy] = at(2.3 + (k % 2) * 0.35, b);
      T.put(
        batch,
        bronze,
        new THREE.TorusGeometry(0.42, 0.09, 5, 10),
        cx,
        cy,
        z0 + 3.9,
        head + Math.PI / 2,
        1,
        1,
        1,
        Math.PI / 2 - 0.5,
        0,
      );
      const [rx, ry] = at(-1.3, b * 0.12);
      T.rod(batch, bronze, [cx, cy, z0 + 4.3], [rx, ry, z0 + 3.9], 0.03, 0.03, 3, true);
    }
    // chariot: curved car, spoked wheels, pole and trophies
    {
      const [x, y] = at(-2.0, 0);
      const car = new THREE.Shape();
      car.moveTo(-1.0, 0);
      car.lineTo(1.0, 0);
      car.quadraticCurveTo(1.45, 1.1, 1.2, 2.0);
      car.lineTo(0.6, 2.0);
      car.quadraticCurveTo(0.7, 0.9, -0.8, 0.9);
      car.lineTo(-1.0, 0.9);
      const cg = new THREE.ExtrudeGeometry(car, {
        depth: 2.2,
        bevelEnabled: false,
        curveSegments: 6,
      })
        .rotateX(Math.PI / 2)
        .translate(0, 1.1, 0);
      T.put(batch, bronze, cg, x, y, z0 + 0.9, head);
      for (const b of [-1.3, 1.3]) {
        const [wx, wy] = at(-2.15, b);
        T.put(
          batch,
          bronze,
          new THREE.TorusGeometry(1.0, 0.11, 6, 22),
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
        T.put(
          batch,
          bronze,
          new THREE.CylinderGeometry(0.2, 0.2, 0.35, 8),
          wx,
          wy,
          z0 + 1.05,
          head,
        );
        for (let k = 0; k < 6; k++) {
          const a = (k / 6) * Math.PI;
          T.put(
            batch,
            bronze,
            new THREE.BoxGeometry(1.95, 0.07, 0.07),
            wx,
            wy,
            z0 + 1.05,
            head,
            1,
            1,
            1,
            0,
            a,
          );
        }
      }
      T.rod(
        batch,
        bronze,
        [...at(-2.15, -1.4), z0 + 1.05],
        [...at(-2.15, 1.4), z0 + 1.05],
        0.08,
        0.08,
        6,
        true,
      );
      T.rod(
        batch,
        bronze,
        [...at(-1.2, 0), z0 + 1.4],
        [...at(2.2, 0), z0 + 3.3],
        0.1,
        0.08,
        6,
        true,
      );
      // war trophies at the back of the car: flags, cannon barrel
      T.rod(
        batch,
        bronze,
        [...at(-2.9, -0.7), z0 + 1.2],
        [...at(-3.6, -1.1), z0 + 4.4],
        0.05,
        0.05,
        4,
        true,
      );
      T.rod(
        batch,
        bronze,
        [...at(-2.9, 0.7), z0 + 1.2],
        [...at(-3.8, 1.0), z0 + 3.9],
        0.05,
        0.05,
        4,
        true,
      );
      T.rod(
        batch,
        bronze,
        [...at(-2.6, 0.2), z0 + 1.1],
        [...at(-4.0, 0.4), z0 + 0.6],
        0.22,
        0.16,
        8,
        true,
      );
      // boy charioteer leaning forward with the reins
      const [bx, by] = at(-1.25, 0.35);
      T.figure(batch, bronze, bx, by, z0 + 1.0, 2.1, head, { armOut: true });
      // Peace: winged figure with flowing robe descending into the car, wreath raised
      const [px, py] = at(-2.4, 0);
      T.figure(batch, bronze, px, py, z0 + 1.2, 4.4, head, {
        robe: true,
        armUp: true,
        wreath: true,
        wings: true,
        wingSpread: 1.0,
      });
    }
    // lamps on the island
    if (placeAssets) {
      const lamps = [];
      for (const s of [-1, 1])
        for (const fv of [-1, 1]) {
          const [x, y] = F.P(s * (W / 2 + 3.2), fv * (D / 2 + 4.5));
          lamps.push([x, y, ang + (fv > 0 ? Math.PI / 2 : -Math.PI / 2)]);
        }
      g.add(placeAssets('street_lamp', lamps));
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
      R.box(batch, paving, 0, 0, 0, L, Wd, 0.3);
      R.box(batch, stoneDk, 0, 0, 0.3, L - 1.2, Wd - 1.2, 0.2);
      R.box(batch, stoneDk, 0, 0, 0.5, L - 2.2, 4.6, 0.8);
      // cruciform pedestal: long block plus transverse arms, moulded plinth and cornice
      R.box(batch, stoneDk, 0, 0, 1.3, 11.9, 4.2, 0.3);
      R.box(batch, stoneDk, 0, 0, 1.3, 4.8, 7.4, 0.3);
      R.box(batch, stone, 0, 0, 1.6, 11.5, 3.8, 4.3);
      R.box(batch, stone, 0, 0, 1.6, 4.4, 7.0, 3.7);
      R.box(batch, stoneDk, 0, 0, 5.3, 4.9, 7.4, 0.25);
      R.box(batch, stone, 0, 0, 5.55, 5.0, 7.5, 0.2);
      R.box(batch, stoneDk, 0, 0, 5.9, 12.0, 4.3, 0.25);
      R.box(batch, stone, 0, 0, 6.15, 12.2, 4.5, 0.2);
      // carved relief friezes of battery scenes (low relief panels with figures)
      for (const sv of [-1, 1]) {
        R.box(batch, stoneSh, 3.95 * 1.0 + 0.0, sv * 1.92, 2.0, 3.5, 0.05, 3.4);
        R.box(batch, stoneSh, -3.95, sv * 1.92, 2.0, 3.5, 0.05, 3.4);
        for (let k = 0; k < 8; k++) {
          const u = (k < 4 ? -5.3 : 2.6) + (k % 4) * 0.9;
          const [x, y] = R.P(u, sv * 1.9);
          T.figure(batch, stone, x, y, 2.05, 2.0 + (k % 3) * 0.25, a + (k % 2 ? 0 : Math.PI), {
            armOut: k % 3 === 1,
            cloak: k % 4 === 2,
          });
        }
        R.box(batch, stoneDk, 0, sv * 3.52, 2.6, 3.0, 0.05, 1.4); // inscription panel on the arms
      }
      // stone 9.2-inch howitzer: carriage with trails, wheels, cradle, recuperator, barrel and shield
      R.box(batch, stone, 0.8, 0, 6.35, 5.6, 2.2, 0.55); // trail
      R.box(batch, stone, 0.2, 0, 6.9, 2.6, 2.0, 0.9); // carriage body
      R.box(batch, stone, 2.5, 0, 6.35, 1.4, 2.4, 0.4); // spade
      for (const s of [-1, 1]) {
        R.put(batch, stone, new THREE.CylinderGeometry(1.0, 1.0, 0.32, 16), -0.6, s * 1.35, 7.25);
        R.put(batch, stoneDk, new THREE.CylinderGeometry(0.3, 0.3, 0.4, 8), -0.6, s * 1.45, 7.25);
      }
      {
        const [x0, y0] = R.P(1.6, 0),
          [x1, y1] = R.P(-4.2, 0);
        T.rod(batch, stone, [x0, y0, 8.0], [x1, y1, 9.9], 0.62, 0.42, 14, true);
        const [x2, y2] = R.P(1.2, 0),
          [x3, y3] = R.P(-1.8, 0);
        T.rod(batch, stoneDk, [x2, y2, 7.55], [x3, y3, 8.6], 0.3, 0.3, 8, true); // recuperator
        const [x4, y4] = R.P(1.9, 0);
        T.rod(batch, stone, [x4, y4, 8.05], [x0, y0, 8.0], 0.75, 0.75, 14, true); // breech ring
        const [x5, y5] = R.P(-4.3, 0);
        T.rod(batch, stoneDk, [x1, y1, 9.9], [x5, y5, 9.95], 0.47, 0.47, 14, true); // muzzle band
      }
      // bronze figures: officer, driver with cape, shell carrier and the recumbent dead soldier
      for (const [u, v, h, pose] of [
        [-L / 2 + 2.6, 0, 2.9, { cloak: true }],
        [L / 2 - 2.6, 0, 2.9, { cloak: true, armOut: true }],
        [0, 3.25, 2.8, { armUp: true }],
      ]) {
        const [x, y] = R.P(u, v);
        R.box(batch, stoneDk, u, v, 0.5, 1.7, 1.5, 1.1);
        const hd = Math.abs(v) > 0 ? a + Math.PI / 2 : u < 0 ? a + Math.PI : a;
        T.figure(batch, bronze, x, y, 1.6, h, hd, pose);
      }
      R.box(batch, stoneDk, 0, -3.25, 0.5, 3.4, 1.5, 1.1);
      const [dx, dy] = R.P(-1.2, -3.25),
        [ex, ey] = R.P(1.2, -3.25);
      T.rod(batch, bronze, [dx, dy, 1.85], [ex, ey, 1.85], 0.3, 0.24, 8, true); // recumbent figure under a greatcoat
      T.blob(batch, bronze, [dx, dy, 1.85], 0.28, 0.26, 0.24, a, 0, 6);
      T.rod(batch, bronze, [ex, ey, 1.75], [...R.P(1.6, -3.0), 1.66], 0.12, 0.1, 5, true);
      // flanking bronze wreaths and helmet on the cornice ends
      for (const s of [-1, 1])
        T.put(
          batch,
          bronze,
          new THREE.TorusGeometry(0.45, 0.12, 5, 12),
          ...R.P(s * 5.75, 0),
          4.6,
          a + Math.PI / 2,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
    }

    // ---------------- Wellington statue (Boehm) ----------------
    {
      const b = byId['4018db4a-7677-49a0-b25b-d2c569902f22'];
      const f = kit.ringFrame(b.polys[0][0]);
      let a = f.angle;
      if (Math.sin(a) < 0) a += Math.PI; // horse faces north towards Apsley House
      const S = T.frame(f.cx, f.cy, a);
      S.box(batch, graniteDk, 0, 0, 0, 6.6, 5.1, 0.3);
      S.box(batch, granite, 0, 0, 0.3, 6.2, 4.7, 0.5);
      S.box(batch, graniteDk, 0, 0, 0.8, 4.9, 3.2, 0.3);
      S.box(batch, granite, 0, 0, 1.1, 4.6, 2.9, 3.0);
      S.box(batch, graniteDk, 0, 0, 4.1, 4.9, 3.2, 0.2);
      S.box(batch, granite, 0, 0, 4.3, 5.1, 3.4, 0.3);
      for (const s of [-1, 1]) S.box(batch, bronze, 0, s * 1.46, 2.4, 1.8, 0.04, 0.8); // bronze inscription panels
      const [x, y] = S.P(0, 0);
      // Copenhagen at a stand, the Duke in cloak and bicorne
      T.horse(batch, bronze, x - Math.cos(a) * 0.3, y - Math.sin(a) * 0.3, 4.6, a, 1.35, 0);
      const [rx, ry] = S.P(-0.4, 0);
      T.figure(batch, bronze, rx, ry, 5.9, 2.0, a, { cloak: true });
      T.put(batch, bronze, new THREE.BoxGeometry(0.16, 0.6, 0.2), rx, ry, 7.72, a);
      // four soldiers at the corners (Grenadier, Highlander, Welsh Fusilier, Inniskilling Dragoon)
      for (const [u, v] of [
        [2.6, 1.9],
        [2.6, -1.9],
        [-2.6, 1.9],
        [-2.6, -1.9],
      ]) {
        const [sx, sy] = S.P(u, v);
        S.box(batch, graniteDk, u, v, 0.8, 0.9, 0.9, 0.35);
        T.figure(batch, bronze, sx, sy, 1.15, 2.0, Math.atan2(v, u) + a);
        const c = Math.cos(a + Math.atan2(v, u) + Math.PI / 2) * 0.2,
          sn = Math.sin(a + Math.atan2(v, u) + Math.PI / 2) * 0.2;
        T.rod(
          batch,
          bronze,
          [sx + c, sy + sn, 1.15],
          [sx + c, sy + sn, 3.2],
          0.025,
          0.025,
          4,
          true,
        ); // musket
      }
    }
    g.add(batch.toGroup('wellington_arch'));
    return g;
  },
};
