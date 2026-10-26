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
    {
      title: 'Queen of Time - Hidden London',
      url: 'https://hidden-london.com/?p=16276',
      used_for:
        "Queen of Time standing on a ship's prow with attendant figures over the main entrance",
    },
    {
      title: 'Gilbert Bayes',
      url: 'https://gilbertbayes.com/',
      used_for: 'Queen of Time clock combining bronze and ceramics (gilding, blue faience)',
    },
  ],
  notes:
    'Plan from the Overture outline. Heights are proportioned from the elevation (ground floor 6.6 m, giant order to 23 m, cornice 26 m, attic 29.5 m, set-back top floor 33 m) because Overture h = 18.2 m is clearly too low; no measured section was found. Column spacing (~6 m bays) is an estimate; columns are modelled unfluted. Detail pass: bronze-framed display windows with transom lights and fascias, three tiers of tripartite bronze-and-glass panels with decorated spandrels between the columns, plinth blocks, stepped entablature and corona, attic windows and pilaster strips, bronze plaques on the corner piers, bronze-and-glass shop canopy; main entrance centred on the bay east of the mid-frontage column (position estimated) with doors, gilded grille, canopy, the Queen of Time on a blue-faience prow with two attendant figures and clock (schematic). The Wigmore Street (north) side and rear additions keep a plainer painted elevation.',
  build({ THREE, kit, byId, placeAssets }) {
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
    const bronzeLt = kit.mat('#6b5a3a', { roughness: 0.4, metalness: 0.6 });
    const roofm = kit.mat('#a3a39c', { roughness: 0.9 });
    const gold = kit.mat('gold');
    const glassS = kit.mat('#26313a', { roughness: 0.12, metalness: 0.35 });
    const display = kit.mat('#bfae86', { roughness: 0.5, emissive: new THREE.Color('#3a3020') });
    const yellow = kit.mat('#f2d21b', { roughness: 0.6, side: THREE.DoubleSide });
    const BAY = 6.0,
      Z1 = 6.6,
      Z2 = 23.0,
      Z3 = 26.0,
      Z4 = 29.5,
      Z5 = 33.0;
    const ashlar = kit.paintedMaterial('selfridges:ashlar', 256, 512, (c, w, h) => {
      B.ashlar(c, w, h, '#ddd6c4', 'rgba(120,110,90,0.25)', h / 11.4, w / 2.5, 0.29); // 4 m x 8 m, 0.7 m courses
    });
    const plain = kit.paintedMaterial('selfridges:rear', 192, 832, (c, w, h) => {
      const TH = Z3,
        m = h / TH,
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
    const plaque = kit.paintedMaterial(
      'selfridges:plaque',
      128,
      180,
      (c, w, h) => {
        c.translate(w, h); // the box face maps the canvas rotated by 180 degrees
        c.rotate(Math.PI);
        c.fillStyle = '#4a3f2a';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = '#b89a5a';
        c.lineWidth = 4;
        c.strokeRect(6, 6, w - 12, h - 12);
        c.fillStyle = '#d2b872';
        c.font = 'bold 22px serif';
        c.textAlign = 'center';
        ['SELFRIDGE', '& CO', 'LIMITED'].forEach((t, k) => c.fillText(t, w / 2, 55 + k * 40));
      },
      { metalness: 0.5, roughness: 0.45 },
    );
    const clockFace = kit.paintedMaterial('selfridges:clock', 128, 128, (c, w, h) => {
      c.fillStyle = '#1d2b4a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#d9b44a';
      for (let k = 0; k < 12; k++) {
        const a = (k * Math.PI) / 6;
        c.beginPath();
        c.arc(w / 2 + Math.cos(a) * w * 0.38, h / 2 + Math.sin(a) * w * 0.38, 4, 0, Math.PI * 2);
        c.fill();
      }
      c.strokeStyle = '#d9b44a';
      c.lineWidth = 5;
      c.beginPath();
      c.moveTo(w / 2, h / 2);
      c.lineTo(w / 2, h * 0.2);
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.68, h * 0.6);
      c.stroke();
    });

    const isNorth = (a, bb) => {
      const len = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      return -(bb[0] - a[0]) / len > 0.6; // outward normal y > 0.6
    };
    // walls: grand order on Oxford Street / Orchard Street / Duke Street, plainer rear
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        c = ring[(k + 1) % ring.length];
      if (isNorth(a, c)) B.wallsTex(batch, plain, [a, c, c], 0, Z3, BAY, { skip: (i) => i !== 0 });
      else
        B.wallsTex(batch, ashlar, [a, c, c], 0, Z3, 4, {
          tileH: 8,
          vBase: 0,
          skip: (i) => i !== 0,
        });
    }
    // plinth, entablature (three-fascia architrave, frieze, modillion cornice)
    kit.cornice(batch, stoneDk, ring, 0, { height: 0.5, projection: 0.15 });
    kit.cornice(batch, stone, ring, Z2 - 0.1, { height: 0.35, projection: 0.12 });
    kit.cornice(batch, stone, ring, Z2 + 0.25, { height: 0.35, projection: 0.2 });
    kit.cornice(batch, stone, ring, Z2 + 0.6, { height: 0.3, projection: 0.28 });
    kit.cornice(batch, stoneDk, ring, Z2 + 0.9, { height: 1.1, projection: 0.18 }); // frieze
    kit.cornice(batch, stone, ring, Z3 - 1.0, { height: 0.25, projection: 0.4 });
    kit.cornice(batch, stoneDk, ring, Z3 - 0.5, { height: 0.35, projection: 1.0 }); // corona
    kit.cornice(batch, stone, ring, Z3 - 0.15, { height: 0.15, projection: 1.1 });
    const att = kit.offsetRing(ring, -0.4);
    B.wallsTex(batch, ashlar, att, Z3, Z4, 4, { tileH: 8, vBase: 0 });
    kit.cornice(batch, stoneDk, att, Z4 - 0.5, { height: 0.5, projection: 0.45, steps: 2 });
    const set = kit.offsetRing(ring, -3.5);
    kit.cap(batch, roofm, [[att]], Z4);
    kit.walls(batch, top, [[set]], Z4, Z5, { bay: 3.0, storey: 3.5, uvBase: Z4 });
    kit.cornice(batch, stoneDk, set, Z5 - 0.35, { height: 0.35, projection: 0.3 });
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
    // giant Ionic columns, bronze-and-glass bays, display windows along the street faces
    let mainEdge = null;
    const lamps = [];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        c = ring[(k + 1) % ring.length];
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
      if (len < 12 || isNorth(a, c)) continue;
      const ang = Math.atan2(c[1] - a[1], c[0] - a[0]);
      const n = [Math.sin(ang), -Math.cos(ang)]; // outward for a CCW ring
      if (n[1] < -0.8) {
        if (!mainEdge) mainEdge = { a, c, len, ang, n, joint: c, jang: ang };
        else
          mainEdge = {
            a: mainEdge.a,
            c,
            len: mainEdge.len + len,
            ang: Math.atan2(c[1] - mainEdge.a[1], c[0] - mainEdge.a[0]),
            n,
            joint: a, // the mid-frontage vertex where the two street edges meet
            jang: ang,
          };
      }
      const nb = Math.round(len / BAY);
      const bw = len / nb;
      const P = (t, d) => [
        a[0] + ((c[0] - a[0]) * t) / len + n[0] * d,
        a[1] + ((c[1] - a[1]) * t) / len + n[1] * d,
      ];
      // straight joints between collinear edges carry an ordinary column, not a corner pier
      const dirAt = (i) => {
        const p = ring[(i + ring.length) % ring.length],
          q = ring[(i + 1 + ring.length) % ring.length];
        return Math.atan2(q[1] - p[1], q[0] - p[0]);
      };
      const straight = (d1, d2) => Math.abs(Math.atan2(Math.sin(d1 - d2), Math.cos(d1 - d2))) < 0.2;
      const prevStraight = straight(dirAt(k - 1), ang),
        nextStraight = straight(dirAt(k + 1), ang);
      for (let j = prevStraight ? 1 : 0; j <= nb; j++) {
        const t = j * bw;
        const corner = (j === 0 && !prevStraight) || (j === nb && !nextStraight);
        const F = T.frame(...P(t, corner ? 0.55 : 0.75), ang + Math.PI); // +v outward
        if (corner) {
          F.box(batch, stone, 0, 0, Z1, 1.6, 1.6, Z2 - Z1);
          T.pilaster(F, batch, stone, 0, 0.85, Z1, Z2 - Z1, 1.2, 0.12, 'ionic');
          F.box(batch, plaque, 0, 0.97, Z1 + 1.2, 1.0, 0.04, 1.4); // bronze SELFRIDGE & CO LIMITED plaque
        } else {
          F.box(batch, stoneDk, 0, 0, Z1 - 0.1, 1.75, 1.75, 0.5); // plinth block
          T.column(F, batch, stone, 0, 0, Z1 + 0.4, Z2 - Z1 - 0.4, 0.62, 'ionic', 14, {
            fluted: false,
          });
        }
        // ground-floor stone pier between the display windows
        const G = T.frame(...P(t, 0), ang + Math.PI);
        G.box(batch, stone, 0, 0.12, 0, 1.3, 0.24, Z1 - 0.6);
      }
      for (let j = 0; j < nb; j++) {
        const tc = (j + 0.5) * bw;
        const F = T.frame(...P(tc, 0), ang + Math.PI); // +v outward, u along -edge
        const pw = bw - 1.6; // panel width between the columns
        // display window: granite stall riser, bronze frame, lit display, transom light, fascia
        F.box(batch, kit.mat('#3b3a38', { roughness: 0.5 }), 0, 0.1, 0, bw - 1.3, 0.2, 0.45);
        F.box(batch, display, 0, 0.03, 0.45, bw - 1.4, 0.04, 3.6);
        F.box(batch, glassS, 0, 0.03, 4.05, bw - 1.4, 0.04, 0.8);
        for (const s of [-1, 1])
          F.box(batch, bronze, (s * (bw - 1.4)) / 2, 0.08, 0.45, 0.12, 0.14, 4.4);
        F.box(batch, bronze, 0, 0.08, 4.05, bw - 1.4, 0.14, 0.1);
        for (const s of [-1, 0, 1])
          F.box(batch, bronze, (s * (bw - 1.4)) / 3, 0.08, 4.15, 0.06, 0.1, 0.7);
        F.box(batch, bronze, 0, 0.1, 4.85, bw - 1.3, 0.2, 0.55); // fascia
        F.box(batch, gold, 0, 0.21, 5.0, bw - 2.2, 0.02, 0.22);
        // metal-and-glass panel spanning three storeys, decorated bronze spandrels
        F.box(batch, glassS, 0, 0.03, Z1 + 0.6, pw, 0.05, Z2 - Z1 - 1.2);
        F.box(batch, bronze, 0, 0.08, Z1 + 0.5, pw + 0.2, 0.16, 0.18);
        F.box(batch, bronze, 0, 0.08, Z2 - 0.65, pw + 0.2, 0.16, 0.18);
        for (const s of [-1, 1])
          F.box(batch, bronze, (s * pw) / 2, 0.08, Z1 + 0.5, 0.18, 0.16, Z2 - Z1 - 1.0);
        for (const f of [-1 / 6, 1 / 6])
          F.box(batch, bronze, f * pw * 2, 0.07, Z1 + 0.6, 0.1, 0.12, Z2 - Z1 - 1.2);
        for (const z of [11.4, 16.2]) {
          F.box(batch, bronze, 0, 0.09, z, pw, 0.16, 1.0);
          F.box(batch, bronzeLt, 0, 0.18, z + 0.2, pw * 0.5, 0.04, 0.6);
          for (const s of [-1, 1])
            F.box(batch, bronzeLt, s * pw * 0.36, 0.18, z + 0.25, 0.5, 0.04, 0.5);
        }
        for (const z of [9.6, 14.4, 19.6]) F.box(batch, bronze, 0, 0.07, z, pw, 0.1, 0.06);
        // attic: two windows per bay
        const A0 = P(tc - bw / 2, -0.4),
          A1 = P(tc + bw / 2, -0.4);
        kit.windowRow(batch, A0, A1, Z3 + 0.7, {
          count: 2,
          margin: 0.5,
          width: 1.5,
          height: 1.9,
          glass: glassS,
          frame: bronze,
          sill: stoneDk,
          bars: 1,
          head: 'none',
          surround: 0.15,
          surroundMat: stone,
          depth: 0.1,
        });
        if (j % 3 === 1 && n[1] < -0.8) lamps.push([...P(tc, 4.8), ang + Math.PI]);
      }
      // attic pilaster strips over the columns
      for (let j = 0; j <= nb; j++) {
        const F = T.frame(...P(j * bw, -0.4), ang + Math.PI);
        F.box(batch, stone, 0, 0.1, Z3, 0.9, 0.2, Z4 - Z3 - 0.5);
      }
      // bronze-and-glass canopy over the display windows
      const F = T.frame(...P(len / 2, 0), ang + Math.PI);
      F.box(batch, bronze, 0, 1.25, 5.4, len - 1.0, 2.3, 0.22);
      F.box(batch, gold, 0, 2.38, 5.42, len - 1.0, 0.04, 0.18);
      for (let u = -len / 2 + 3; u < len / 2 - 2; u += bw)
        T.rod(batch, bronze, [...F.P(u, 0.1), 7.0], [...F.P(u, 2.3), 5.62], 0.04, 0.04, 4, true); // tie rods
    }
    // main Oxford Street entrance: recessed bronze-and-glass screen, canopy and the Queen of Time
    if (mainEdge) {
      const { joint, jang: ang, n } = mainEdge;
      // centred on the bay just east of the mid-frontage column
      const mx = joint[0] + Math.cos(ang) * 3.0,
        my = joint[1] + Math.sin(ang) * 3.0;
      const F = T.frame(mx + n[0] * 0.05, my + n[1] * 0.05, ang); // -v is outward here
      const vo = -1;
      F.box(batch, bronze, 0, vo * 0.12, 0, 4.6, 0.1, Z2 - 0.8);
      F.box(batch, glassS, 0, vo * 0.2, 7.0, 4.2, 0.06, Z2 - 8.6);
      for (let k = -2; k <= 2; k++)
        F.box(batch, bronze, k * 1.0, vo * 0.25, 7.0, 0.08, 0.08, Z2 - 8.6);
      for (let z = 9; z < Z2 - 1.5; z += 2.0)
        F.box(batch, bronze, 0, vo * 0.25, z, 4.2, 0.08, 0.08);
      // two pairs of bronze doors under the canopy
      for (const u of [-1.1, 1.1]) {
        F.box(batch, glassS, u, vo * 0.22, 0.05, 2.0, 0.08, 3.4);
        F.box(batch, bronzeLt, u, vo * 0.28, 0.05, 2.2, 0.06, 0.15);
        F.box(batch, bronzeLt, u, vo * 0.28, 3.4, 2.2, 0.06, 0.15);
        for (const s of [-1, 0, 1])
          F.box(batch, bronzeLt, u + s * 1.0, vo * 0.28, 0.05, 0.1, 0.06, 3.5);
      }
      F.box(batch, gold, 0, vo * 0.24, 3.8, 4.4, 0.05, 1.8); // gilded grille panel
      // canopy with gilded edge, Queen of Time on her plinth, clock below
      F.box(batch, bronze, 0, vo * 2.2, 6.0, 10.0, 4.2, 0.45);
      F.box(batch, gold, 0, vo * 4.28, 6.0, 10.0, 0.06, 0.45);
      F.box(batch, gold, 0, vo * 2.2, 6.45, 10.0, 4.2, 0.12);
      const [qx, qy] = F.P(0, vo * 1.6);
      // ship's prow plinth
      const prow = new THREE.Shape([
        new THREE.Vector2(-1.4, 0),
        new THREE.Vector2(1.4, 0),
        new THREE.Vector2(0.9, 1.1),
        new THREE.Vector2(-0.9, 1.1),
      ]);
      T.slab(F, batch, kit.mat('#2f5f9a', { roughness: 0.35 }), prow, 0, vo * 1.6, 6.57, 2.0, 2); // blue faience prow
      T.put(batch, gold, new THREE.SphereGeometry(0.55, 12, 8), ...F.P(0, vo * 1.6), 8.0);
      T.figure(batch, gold, qx, qy, 8.2, 3.6, ang - Math.PI / 2, {
        robe: true,
        armUp: true,
        wreath: true,
      });
      for (const s of [-1, 1])
        T.figure(batch, bronzeLt, ...F.P(s * 1.2, vo * 1.7), 7.67, 1.7, ang - Math.PI / 2, {
          robe: true,
          armOut: true,
        });
      const [cx2, cy2] = F.P(0, vo * 0.32);
      T.put(
        batch,
        clockFace,
        new THREE.CircleGeometry(0.8, 24).rotateX(Math.PI / 2),
        cx2,
        cy2,
        12.6,
        ang,
      );
      T.put(
        batch,
        gold,
        new THREE.TorusGeometry(0.88, 0.1, 5, 24),
        cx2,
        cy2,
        12.6,
        ang,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      // flagpoles above the canopies with yellow Selfridges flags
      for (const s of [-3, -2, -1, 1, 2, 3]) {
        const [px, py] = F.P(s * 18, vo * 1.0);
        T.rod(
          batch,
          kit.mat('white'),
          [px, py, 7.0],
          [px + n[0] * 4.5, py + n[1] * 4.5, 9.8],
          0.07,
          0.05,
          5,
        );
        const q0 = [px + n[0] * 2.4, py + n[1] * 2.4],
          q1 = [px + n[0] * 4.4, py + n[1] * 4.4];
        batch.quad(
          yellow,
          [q0[0], q0[1], 7.1],
          [q1[0], q1[1], 8.4],
          [q1[0], q1[1], 9.7],
          [q0[0], q0[1], 8.4],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    if (placeAssets && lamps.length) g.add(placeAssets('street_lamp', lamps));
    g.add(batch.toGroup('selfridges'));
    return g;
  },
};
