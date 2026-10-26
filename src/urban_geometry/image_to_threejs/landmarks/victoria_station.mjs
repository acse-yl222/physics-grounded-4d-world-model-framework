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
    "Plan split from the Overture outline: Brighton side west of the chord between the two frontages, Chatham side and the Wilton Road range east of it; the two claimed roof footprints are modelled as Fowler's train shed as two segmental glazed spans (span form and 18 m crown height assumed) with lattice ribs every second bay. Brighton frontage height (20.5 m + mansard to ~27 m), Chatham frontage height (15 m), bay rhythm, canopy depth and concourse ridge heights are estimates. Detail pass: Brighton side brick bays with stone-dressed sashes and keystones, stone bands and modillion cornice, ashlar pavilions with Ionic pilasters and arched windows, two attic storeys of dormers, oeil-de-boeuf windows, iron cresting, chimneys, the clock in a stone scroll; the canopy is ridge-and-furrow glazing on cast-iron columns with brackets and a fretted valance plus modern station signs. Chatham side: channelled ground storey with great arched openings, lettered frieze, paired pilasters, pedimented windows, modillion cornice and balustrade; the mermaid caryatids, cartouches and wreaths are schematic. Lamps and bollards on Terminus Place are resources assets. Grosvenor Hotel and Victoria Place are not claimed.",
  build({ THREE, kit, byId, placeAssets }) {
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
    const glassV = kit.mat('#29333b', { roughness: 0.15, metalness: 0.3 });
    const sashV = kit.mat('#efe9dc', { roughness: 0.6 });
    const ironV = kit.mat('#2f3b38', { roughness: 0.5, metalness: 0.4 });
    const canopyW = kit.mat('#e6e1d3', { roughness: 0.7 });
    const sign = kit.paintedMaterial('victoria_station:sign', 512, 92, (c, w, h) => {
      c.fillStyle = '#1d2a44';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#ffffff';
      c.font = 'bold 56px sans-serif';
      c.textBaseline = 'middle';
      c.fillText('Victoria', 120, h / 2 + 3);
      // British Rail double-arrow symbol
      c.fillStyle = '#e0262b';
      c.fillRect(18, 18, 84, 56);
      c.strokeStyle = '#ffffff';
      c.lineWidth = 7;
      c.beginPath();
      c.moveTo(26, 34);
      c.lineTo(94, 34);
      c.moveTo(26, 58);
      c.lineTo(94, 58);
      c.moveTo(50, 22);
      c.lineTo(72, 46);
      c.lineTo(50, 70);
      c.stroke();
    });
    const brickPlain = kit.paintedMaterial('victoria_station:brick_plain', 256, 512, (c, w, h) => {
      // 4 m x 8 m of red brick in Flemish-ish bond (tile mapped 1:1 by wallsTex)
      c.fillStyle = '#9a4b37';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.79);
      const ch = h / (8 / 0.075);
      for (let y = 0, row = 0; y < h; y += ch, row++)
        for (let x = (row % 2) * 4; x < w; x += 8) {
          c.fillStyle = `rgba(${70 + r() * 60},${25 + r() * 25},${20 + r() * 15},0.4)`;
          c.fillRect(x, y, 7, ch - 1);
        }
    });
    const ashPlain = kit.paintedMaterial('victoria_station:ashlar_plain', 256, 512, (c, w, h) => {
      B.ashlar(c, w, h, '#ddd5c0', 'rgba(110,100,80,0.3)', h / 14.5, w / 3.3, 0.13);
    });
    // identify the forecourt face (edge with the largest u)
    let fe = null;
    for (let k = 0; k < brFront.length; k++) {
      const a = brFront[k],
        b = brFront[(k + 1) % brFront.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const um = (uOf(a) + uOf(b)) / 2;
      if (len > 20 && (!fe || um > fe.um)) fe = { a, b, len, um, k };
    }
    B.wallsTex(batch, brickBay, brFront, 0, FTH, 4.5, { skip: (k) => k === fe.k });
    kit.cap(batch, slate, [[brFront]], FTH);
    {
      // mansard roof with dormers, French pavilion roofs over centre and ends
      const fr = kit.ringFrame(brFront);
      kit.pitchedRoof(batch, slate, stone, brFront, fr.angle, FTH, 6.5, 'hipped', {
        overhang: -0.6,
      });
      const fa = Math.atan2(fe.b[1] - fe.a[1], fe.b[0] - fe.a[0]);
      const FF = T.frame((fe.a[0] + fe.b[0]) / 2, (fe.a[1] + fe.b[1]) / 2, fa); // -v outward
      const L = fe.len;
      // brick front (plain brick with Portland bands; windows modelled), stone ground floors behind the canopy
      {
        const a = FF.P(L / 2, 0),
          b = FF.P(-L / 2, 0);
        B.wallsTex(batch, stoneDk, [b, a, a], 0, 7.6, 4, { skip: (i) => i !== 0 });
        B.wallsTex(batch, brickPlain, [b, a, a], 7.6, FTH, 4, {
          tileH: 8,
          vBase: 0,
          skip: (i) => i !== 0,
        });
        for (const z of [7.6, 11.2, 14.6, 17.8])
          FF.box(batch, stone, 0, -0.06, z - 0.1, L, 0.14, 0.35);
        FF.box(batch, stone, 0, -0.25, FTH - 1.0, L, 0.5, 0.45); // frieze
        FF.box(batch, stoneDk, 0, -0.45, FTH - 0.55, L + 0.2, 0.9, 0.3); // cornice
        FF.box(batch, stone, 0, -0.5, FTH - 0.25, L + 0.3, 1.0, 0.25);
        T.blocks(batch, stone, FF.P(-L / 2, -0.55), FF.P(L / 2, -0.55), FTH - 0.85, {
          w: 0.14,
          h: 0.3,
          proj: 0.3,
          gap: 0.5,
        });
        // brick bays between the pavilions: three storeys of stone-dressed sashes with keystones
        for (const [ua, ub] of [
          [-L / 2 + 11, -7.5],
          [7.5, L / 2 - 11],
        ]) {
          const n = Math.round((ub - ua) / 4.5);
          const pa = FF.P(ua, 0),
            pb = FF.P(ub, 0);
          for (const [z, hh] of [
            [8.3, 2.5],
            [11.9, 2.3],
            [15.3, 2.2],
          ]) {
            const cs = kit.windowRow(batch, pa, pb, z, {
              count: n,
              margin: 0.3,
              width: 1.5,
              height: hh,
              glass: glassV,
              frame: sashV,
              sill: stone,
              bars: 2,
              head: 'lintel',
              surround: 0.22,
              surroundMat: stone,
              depth: 0.12,
            });
            for (const [x, y] of cs)
              kit.box(
                batch,
                stone,
                x - Math.sin(fa) * -0.12,
                y + Math.cos(fa) * -0.12,
                z + hh + 0.05,
                0.42,
                0.16,
                0.42,
                fa,
              ); // keystone
          }
          // arched station entrances behind the canopy
          T.archWin(batch, pa, pb, 0.25, {
            count: n,
            width: 2.7,
            height: 6.0,
            glass: glassV,
            frame: ironV,
            stone: stone,
            bars: 3,
            surround: 0.3,
            depth: 0.14,
          });
        }
      }
      // ashlar centrepiece and end pavilions projecting 0.8 m
      for (const [c0, w] of [
        [0, 15],
        [-(L / 2 - 5.5), 11],
        [L / 2 - 5.5, 11],
      ]) {
        const a = FF.P(c0 + w / 2, -0.8),
          b = FF.P(c0 - w / 2, -0.8);
        B.wallsTex(batch, ashPlain, [b, a, a], 0, FTH + 0.6, 4, {
          tileH: 8,
          vBase: 0,
          skip: (i) => i !== 0,
        });
        const a0 = FF.P(c0 + w / 2, 0.2),
          b0 = FF.P(c0 - w / 2, 0.2);
        B.wallsTex(batch, stone, [a, a0, a0], 0, FTH + 0.6, 4, { skip: (i) => i !== 0 });
        B.wallsTex(batch, stone, [b0, b, b], 0, FTH + 0.6, 4, { skip: (i) => i !== 0 });
        // rusticated ground storey, banded quoins, giant pilasters and modelled windows
        for (let z = 0.6; z < 7.6; z += 0.6) FF.box(batch, stoneDk, c0, -0.82, z, w, 0.04, 0.06);
        const nb = c0 === 0 ? 4 : 3;
        const bw = w / nb;
        for (let k = 0; k <= nb; k++) {
          const uu = c0 - w / 2 + k * bw;
          const F2 = T.frame(...FF.P(uu, -0.8), fa + Math.PI); // +v outward
          T.pilaster(F2, batch, stone, 0, 0.12, 7.9, FTH - 1.2 - 7.9, 0.75, 0.22, 'ionic');
        }
        const pa = FF.P(c0 - w / 2, -0.8),
          pb = FF.P(c0 + w / 2, -0.8);
        if (c0 !== 0) {
          T.archWin(batch, pa, pb, 8.3, {
            count: nb,
            width: 1.5,
            height: 5.0,
            glass: glassV,
            frame: sashV,
            stone: stoneDk,
            bars: 2,
            surround: 0.18,
          });
          kit.windowRow(batch, pa, pb, 15.3, {
            count: nb,
            margin: 0.4,
            width: 1.3,
            height: 2.4,
            glass: glassV,
            frame: sashV,
            sill: stoneDk,
            bars: 2,
            head: 'pediment',
            surround: 0.16,
            surroundMat: stone,
            depth: 0.12,
          });
          T.archWin(batch, pa, pb, 0.25, {
            count: nb,
            width: 2.4,
            height: 6.0,
            glass: glassV,
            frame: ironV,
            stone: stone,
            bars: 3,
            surround: 0.3,
          });
        } else {
          kit.windowRow(batch, pa, pb, 15.3, {
            count: nb,
            margin: 0.4,
            width: 1.3,
            height: 2.4,
            glass: glassV,
            frame: sashV,
            sill: stoneDk,
            bars: 2,
            head: 'lintel',
            surround: 0.16,
            surroundMat: stone,
            depth: 0.12,
          });
          for (const k of [0, 3]) {
            const uu = c0 - w / 2 + (k + 0.5) * bw;
            const q0 = FF.P(uu + bw / 2, -0.8),
              q1 = FF.P(uu - bw / 2, -0.8);
            T.archWin(batch, q1, q0, 8.3, {
              count: 1,
              width: 1.5,
              height: 5.0,
              glass: glassV,
              frame: sashV,
              stone: stoneDk,
              bars: 2,
              surround: 0.18,
            });
          }
          T.archWin(batch, pa, pb, 0.25, {
            count: nb,
            width: 2.7,
            height: 6.2,
            glass: glassV,
            frame: ironV,
            stone: stone,
            bars: 3,
            surround: 0.3,
          });
        }
        // cornice and balustraded parapet of the pavilion
        FF.box(batch, stoneDk, c0, -1.1, FTH - 0.6, w + 0.6, 1.2, 0.35);
        FF.box(batch, stone, c0, -1.15, FTH - 0.25, w + 0.8, 1.3, 0.3);
        FF.box(batch, stoneDk, c0, -0.5, FTH + 0.2, w + 0.6, 1.6, 0.6);
        // pavilion roof with iron cresting and finials
        const pr = [
          FF.P(c0 - w / 2, -0.8),
          FF.P(c0 + w / 2, -0.8),
          FF.P(c0 + w / 2, 10),
          FF.P(c0 - w / 2, 10),
        ];
        const ph = c0 === 0 ? 9 : 8;
        const res = kit.pitchedRoof(batch, slate, stone, ccw(pr), fa, FTH + 0.6, ph, 'hipped', {
          overhang: 0.2,
        });
        if (res.ridge)
          T.railing(
            batch,
            ironV,
            res.ridge.map((p) => [p[0], p[1]]),
            res.top,
            { height: 0.9, spacing: 0.25, post: 2, spear: true },
          );
        for (const p of res.ridge)
          T.lathePut(
            batch,
            ironV,
            [
              [0.15, 0],
              [0.08, 0.4],
              [0.2, 0.7],
              [0.0, 1.6],
            ],
            p[0],
            p[1],
            p[2],
            6,
          );
        // pavilion dormer (oeil-de-boeuf) on the front slope
        const dz = FTH + 0.6 + ph * 0.3;
        const [dx, dy] = FF.P(c0, 0.6);
        T.put(
          batch,
          stone,
          new THREE.TorusGeometry(0.95, 0.22, 5, 16),
          dx,
          dy,
          dz + 1.0,
          fa,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
        T.put(
          batch,
          glassV,
          new THREE.CircleGeometry(0.9, 16).rotateX(Math.PI / 2),
          ...FF.P(c0, 0.45),
          dz + 1.0,
          fa,
        );
        kit.box(batch, stone, dx, dy, dz - 0.2, 2.4, 1.2, 0.3, fa);
      }
      // dormers on the mansard: two attic storeys
      for (let u = -L / 2 + 12; u <= L / 2 - 12; u += 4.5) {
        if (Math.abs(u) < 9) continue;
        for (const [vd, zd, wd, hd] of [
          [1.6, FTH, 1.8, 3.2],
          [4.6, FTH + 3.4, 1.3, 2.2],
        ]) {
          FF.box(batch, stone, u, vd, zd, wd, 1.6, hd);
          const rr = [
            FF.P(u - wd / 2 - 0.15, vd - 0.95),
            FF.P(u + wd / 2 + 0.15, vd - 0.95),
            FF.P(u + wd / 2 + 0.15, vd + 0.8),
            FF.P(u - wd / 2 - 0.15, vd + 0.8),
          ];
          kit.pitchedRoof(batch, slate, stone, ccw(rr), fa + Math.PI / 2, zd + hd, 0.8, 'gabled', {
            overhang: 0.05,
          });
          const a = FF.P(u + wd / 2, vd - 0.8),
            b = FF.P(u - wd / 2, vd - 0.8);
          kit.windowRow(batch, b, a, zd + 0.5, {
            count: 1,
            margin: 0.2,
            width: wd - 0.6,
            height: hd - 1.0,
            glass: glassV,
            frame: sashV,
            sill: stone,
            bars: 1,
            head: 'none',
            depth: 0.08,
          });
        }
      }
      // chimney stacks along the roof
      for (let u = -L / 2 + 9; u <= L / 2 - 9; u += 13.5) {
        const [x, y] = FF.P(u, 9);
        T.chimney(batch, brick, kit.mat('#8a5a3c'), x, y, FTH + 4, 1.0, 3.2, 4.0, fa, 5);
      }
      // the large clock set in a scroll on the centrepiece
      {
        const [cx, cy] = FF.P(0, -0.95);
        T.put(
          batch,
          clockFace,
          new THREE.CircleGeometry(1.75, 32).rotateX(Math.PI / 2),
          cx,
          cy,
          11.0,
          fa,
        );
        T.put(
          batch,
          stoneDk,
          new THREE.TorusGeometry(1.9, 0.22, 6, 28),
          cx,
          cy,
          11.0,
          fa,
          1,
          1,
          1,
          Math.PI / 2,
          0,
        );
        for (const s of [-1, 1]) {
          // scrolls either side and the crowning cartouche
          const [sx, sy] = FF.P(s * 2.4, -1.0);
          T.put(
            batch,
            stone,
            new THREE.TorusGeometry(0.5, 0.2, 5, 12, Math.PI * 1.5),
            sx,
            sy,
            10.1,
            fa,
            s,
            1,
            1,
            Math.PI / 2,
            0,
          );
          T.put(
            batch,
            stone,
            new THREE.TorusGeometry(0.35, 0.16, 5, 10, Math.PI * 1.5),
            sx - Math.cos(fa) * s * 0.2,
            sy - Math.sin(fa) * s * 0.2,
            12.4,
            fa + Math.PI,
            s,
            1,
            1,
            Math.PI / 2,
            0,
          );
        }
        FF.box(batch, stone, 0, -1.0, 12.9, 3.0, 0.5, 0.9);
        T.urn(batch, stone, ...FF.P(0, -1.0), 13.8, 1.0);
      }
      // iron-and-glass canopy over the forecourt: cast-iron columns, ridge-and-furrow glazing, fretted valance
      {
        const CD = 7.6,
          CZ = 7.4;
        FF.box(batch, ironV, 0, -CD / 2 - 0.4, CZ, L - 2, CD, 0.35);
        FF.box(batch, canopyW, 0, -CD - 0.55, CZ - 0.75, L - 2, 0.12, 1.15); // valance board
        for (let u = -L / 2 + 1.2; u <= L / 2 - 1.2; u += 0.5)
          FF.box(batch, canopyW, u, -CD - 0.62, CZ - 0.95, 0.14, 0.06, 0.25); // fret drops
        const nR = Math.round((L - 2) / 3);
        for (let k = 0; k < nR; k++) {
          const ua = -L / 2 + 1 + ((L - 2) * k) / nR,
            ub = ua + (L - 2) / nR;
          const rr = [FF.P(ua, -CD - 0.4), FF.P(ub, -CD - 0.4), FF.P(ub, -0.4), FF.P(ua, -0.4)];
          kit.pitchedRoof(
            batch,
            glassRoof,
            ironV,
            ccw(rr),
            fa + Math.PI / 2,
            CZ + 0.35,
            0.8,
            'gabled',
            { overhang: 0 },
          );
        }
        for (let u = -L / 2 + 3; u <= L / 2 - 3; u += 6) {
          const [x, y] = FF.P(u, -CD);
          T.rod(batch, ironV, [x, y, 0], [x, y, CZ], 0.13, 0.11, 8, true);
          T.lathePut(
            batch,
            ironV,
            [
              [0.25, 0],
              [0.25, 0.4],
              [0.15, 0.5],
              [0.12, 0.6],
              [0, 0.6],
            ],
            x,
            y,
            0,
            8,
          ); // base
          T.lathePut(
            batch,
            ironV,
            [
              [0.12, 0],
              [0.32, 0.5],
              [0.36, 0.6],
              [0, 0.6],
            ],
            x,
            y,
            CZ - 0.6,
            8,
          ); // capital
          // curved spandrel brackets
          for (const s of [-1, 1]) {
            const [bx, by] = FF.P(u + s * 0.9, -CD);
            T.rod(batch, ironV, [x, y, CZ - 1.6], [bx, by, CZ - 0.05], 0.05, 0.05, 4, true);
          }
        }
        // modern station name signs on the canopy fascia
        for (const s of [-1, 1]) {
          const [sx, sy] = FF.P(s * 18, -CD - 0.7);
          T.put(
            batch,
            sign,
            new THREE.PlaneGeometry(5.0, 0.9).rotateX(Math.PI / 2),
            sx,
            sy,
            CZ - 0.2,
            fa,
          );
        }
      }
      if (placeAssets) {
        const lamps = [],
          bol = [];
        for (let u = -L / 2 + 4; u <= L / 2 - 4; u += 12)
          lamps.push([...FF.P(u, -14), fa + Math.PI]);
        for (let u = -L / 2 + 2; u <= L / 2 - 2; u += 3) bol.push([...FF.P(u, -9.2), fa]);
        g.add(placeAssets('street_lamp', lamps));
        g.add(placeAssets('bollard', bol));
      }
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
      const chAsh = kit.paintedMaterial('victoria_station:chatham_ashlar', 256, 512, (c, w, h) => {
        B.ashlar(c, w, h, '#e2dccb', 'rgba(110,100,80,0.28)', h / 13.3, w / 3, 0.21);
      });
      const chRust = kit.paintedMaterial('victoria_station:chatham_rustic', 256, 512, (c, w, h) => {
        c.fillStyle = '#dcd5c3';
        c.fillRect(0, 0, w, h);
        const ch = h / 13.33;
        for (let k = 0; k < 14; k++) {
          c.fillStyle = 'rgba(70,64,52,0.55)';
          c.fillRect(0, k * ch, w, 4);
          c.fillStyle = 'rgba(255,255,245,0.3)';
          c.fillRect(0, k * ch + 4, w, 2);
        }
      });
      for (let k = 0; k < fr.length; k++) {
        const a = fr[k],
          b = fr[(k + 1) % fr.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = [(b[1] - a[1]) / len, -(b[0] - a[0]) / len];
        const nu = n[0] * cu + n[1] * su; // component along +u (towards the forecourt)
        const nv = -n[0] * su + n[1] * cu;
        const isFront = nu > 0.45 && Math.min(uOf(a), uOf(b)) > 40;
        const isWilton = nv < -0.9;
        if (!isFront) {
          B.wallsTex(
            batch,
            isWilton ? kit.facade('portland_stone', 2) : stone,
            [a, b, b],
            0,
            CTH,
            3.6,
            { tileH: 6.4, skip: (i) => i !== 0 },
          );
          continue;
        }
        // channelled ground storey with great arched openings, lettered frieze, upper storey
        // with paired pilasters, modillion cornice and balustrade
        B.wallsTex(batch, chRust, [a, b, b], 0, 8.6, 4, {
          tileH: 8,
          vBase: 0,
          skip: (i) => i !== 0,
        });
        B.wallsTex(batch, chAsh, [a, b, b], 8.6, CTH, 4, {
          tileH: 8,
          vBase: 0,
          skip: (i) => i !== 0,
        });
        const fa = Math.atan2(b[1] - a[1], b[0] - a[0]);
        const FF = T.frame((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, fa); // -v outward
        const nb = Math.max(1, Math.round(len / 6));
        T.archWin(batch, a, b, 0.3, {
          count: nb,
          width: 4.1,
          height: 7.5,
          glass: glassV,
          frame: ironV,
          stone: stoneDk,
          bars: 3,
          surround: 0.35,
          depth: 0.16,
        });
        FF.box(batch, stoneDk, 0, -0.12, 8.45, len, 0.3, 0.3);
        if (len > 6) {
          const pa = FF.P(len / 2 - 0.6, -0.08),
            pb = FF.P(-len / 2 + 0.6, -0.08);
          batch.quad(
            lettering,
            [pb[0], pb[1], 8.8],
            [pa[0], pa[1], 8.8],
            [pa[0], pa[1], 9.6],
            [pb[0], pb[1], 9.6],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
        }
        FF.box(batch, stoneDk, 0, -0.1, 9.65, len, 0.25, 0.2);
        kit.windowRow(batch, a, b, 10.1, {
          count: nb,
          margin: 0,
          width: 1.7,
          height: 2.9,
          glass: glassV,
          frame: sashV,
          sill: stoneDk,
          bars: 2,
          head: 'pediment',
          surround: 0.2,
          surroundMat: stone,
          depth: 0.14,
        });
        for (let i = 0; i <= nb; i++) {
          const uu = -len / 2 + (len * i) / nb;
          for (const d of [-0.45, 0.45]) {
            if ((i === 0 && d < 0) || (i === nb && d > 0)) continue;
            const F2 = T.frame(...FF.P(uu + d, 0), fa + Math.PI);
            T.pilaster(F2, batch, stone, 0, 0.1, 9.85, 3.6, 0.55, 0.2, 'ionic');
          }
        }
        FF.box(batch, stone, 0, -0.25, 13.45, len, 0.5, 0.35);
        FF.box(batch, stoneDk, 0, -0.45, 13.8, len + 0.3, 0.9, 0.25);
        T.blocks(batch, stone, FF.P(-len / 2, -0.5), FF.P(len / 2, -0.5), 13.5, {
          w: 0.12,
          h: 0.28,
          proj: 0.3,
          gap: 0.45,
        });
        kit.balustrade(
          batch,
          stone,
          [FF.P(-len / 2 + 0.3, -0.25), FF.P(len / 2 - 0.3, -0.25)],
          14.05,
          { height: 0.95, spacing: 0.3 },
        );
        for (let i = 0; i <= nb; i++)
          FF.box(batch, stone, -len / 2 + (len * i) / nb, -0.25, 14.05, 0.55, 0.55, 1.05);
        if (len > 20) {
          // segmental pediments held by pairs of Fehr's mermaid caryatids, wreath and cartouche
          for (const c0 of len > 40 ? [-len / 4, len / 4] : [0]) {
            FF.box(batch, stone, c0, -0.7, 9.8, 7.5, 1.4, 4.6);
            FF.box(batch, stoneDk, c0, -0.75, 13.6, 8.0, 1.6, 0.4);
            const ped = new THREE.Shape();
            ped.moveTo(-4.4, 0);
            ped.lineTo(4.4, 0);
            ped.lineTo(4.4, 0.8);
            ped.absarc(0, -3.0, 5.85, Math.atan2(3.8, 4.4), Math.PI - Math.atan2(3.8, 4.4), false);
            ped.lineTo(-4.4, 0);
            T.slab(FF, batch, stone, ped, c0, -0.9, 14.4, 1.8, 12);
            const ped2 = new THREE.Shape();
            ped2.moveTo(-3.8, 0);
            ped2.lineTo(3.8, 0);
            ped2.absarc(0, -3.0, 5.0, Math.atan2(3.0, 3.8), Math.PI - Math.atan2(3.0, 3.8), false);
            ped2.lineTo(-3.8, 0);
            T.slab(FF, batch, stoneDk, ped2, c0, -1.82, 14.5, 0.06, 12); // tympanum
            // cartouche with scroll ends
            T.slab(
              FF,
              batch,
              stone,
              new THREE.Shape([
                new THREE.Vector2(-0.9, 0),
                new THREE.Vector2(0.9, 0),
                new THREE.Vector2(1.1, 1.2),
                new THREE.Vector2(0, 1.9),
                new THREE.Vector2(-1.1, 1.2),
              ]),
              c0,
              -1.95,
              14.6,
              0.35,
              4,
            );
            for (const s of [-1, 1])
              T.put(
                batch,
                stone,
                new THREE.TorusGeometry(0.22, 0.09, 4, 8),
                ...FF.P(c0 + s * 1.05, -2.0),
                15.6,
                fa,
                1,
                1,
                1,
                Math.PI / 2,
                0,
              );
            for (const s of [-1, 1]) {
              const [x, y] = FF.P(c0 + s * 2.6, -1.55);
              FF.box(batch, stoneDk, c0 + s * 2.6, -1.4, 9.6, 1.2, 1.0, 0.6);
              // mermaid: robed upper body with arms raised to the pediment, scaly tail curling to the plinth
              T.figure(batch, stone, x, y, 10.4, 3.9, fa - Math.PI / 2, {
                robe: true,
                armUp: true,
              });
              const [tx, ty] = FF.P(c0 + s * 3.2, -1.9);
              T.rod(batch, stone, [x, y, 10.8], [tx, ty, 10.3], 0.3, 0.18, 7, true);
              T.put(
                batch,
                stone,
                new THREE.TorusGeometry(0.3, 0.11, 4, 8, Math.PI * 1.4),
                tx,
                ty,
                10.55,
                fa,
                1,
                1,
                1,
                Math.PI / 2,
                0,
              );
            }
            // wreath over the entrance
            T.put(
              batch,
              stone,
              new THREE.TorusGeometry(1.0, 0.24, 6, 18),
              ...FF.P(c0, -1.5),
              12.0,
              fa,
              1,
              1,
              1,
              Math.PI / 2,
              0,
            );
            FF.box(batch, kit.mat('#3c3e3a'), c0, -1.41, 11.0, 0.9, 0.04, 2.0);
          }
        }
      }
      kit.cap(batch, slate, [[fr]], CTH);
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
      // lattice arched ribs at every bay (outer and inner booms with diagonal web)
      for (let k = 0; k <= bays; k++) {
        const end = k === 0 || k === bays;
        if (!end && k % 2) continue;
        const u = u0 + ((u1 - u0) * k) / bays;
        const ptsA = [],
          ptsB = [];
        for (let i = 0; i <= N; i++) {
          const p = pt(i / N, u);
          ptsA.push([p[0], p[1], p[2] - 0.15]);
          ptsB.push([
            p[0],
            p[1],
            p[2] - 0.15 - (end ? 0.9 : 0.7) * (0.6 + 0.4 * Math.sin((Math.PI * i) / N)),
          ]);
        }
        for (let i = 0; i < N; i++) {
          T.rod(batch, iron, ptsA[i], ptsA[i + 1], end ? 0.3 : 0.12, end ? 0.3 : 0.12, 4, true);
          T.rod(batch, iron, ptsB[i], ptsB[i + 1], end ? 0.25 : 0.1, end ? 0.25 : 0.1, 4, true);
          T.rod(
            batch,
            iron,
            i % 2 ? ptsA[i] : ptsB[i],
            i % 2 ? ptsB[i + 1] : ptsA[i + 1],
            0.05,
            0.05,
            3,
            true,
          );
        }
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
