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
    {
      title: 'Buckingham Palace - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101239087-buckingham-palace-st-jamess-ward',
      used_for:
        'Webb east front: channelled ground floor with semicircular arched central gateway, first-floor architraved sashes with open pediments, fluted Corinthian pilasters, paired columns and blind attics on the centrepiece and terminal pavilions, balustraded parapet and balcony',
    },
  ],
  notes:
    'Plan, quadrangle and wing heights from the Overture footprint and its 12 parts; the unparted east, north and south ranges use 22 m. East front now follows the footprint steps (main face 2.4 m behind the centrepiece, terminal pavilions 1.45 m forward of it) with modelled bays: arched rusticated ground floor, piano nobile windows with alternating triangular/segmental open pediments and aprons, second-floor sashes, fluted Corinthian pilasters, paired columns, three arched gateways with gilded gates, the balcony on consoles, modillion cornice, roof balustrade, blind attics with urns, pediment with relief arms and lion/unicorn supporters (schematic). Bay counts (7 + 3 + 3 per side) are estimated from photographs remembered, not measured. Nash/Blore ranges keep the painted bay texture with added 3D cornices, modillions and roof balustrades. Forecourt railings, pier lanterns, gates, sentry boxes and guardsmen are approximate (20 m deep strip); the Victoria Memorial lies outside the domain. The east end extends ~100 m past the x = 4000 m domain edge and is kept whole.',
  build({ THREE, kit, byId, placeAssets }) {
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
    // ---- painted materials ----
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
    const rangeEdges = []; // [a, b, top] wall edges of the Nash/Blore ranges for 3D cornices
    for (const ring of mainPoly)
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 0.05 || isFrontEdge(a, b)) continue;
        const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        const inward = [mid[0] - ((b[1] - a[1]) / len) * 0.6, mid[1] + ((b[0] - a[0]) / len) * 0.6];
        if (partAt(inward)) continue;
        rangeEdges.push([a, b, H]);
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
      if (p.h > 10)
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k],
            b = ring[(k + 1) % ring.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          if (len < 1.5) continue;
          const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          const out = [mid[0] + ((b[1] - a[1]) / len) * 0.8, mid[1] - ((b[0] - a[0]) / len) * 0.8];
          const q = partAt(out);
          if (q ? q.h >= p.h - 0.5 : inPoly(out, mainPoly)) continue;
          rangeEdges.push([a, b, p.h]);
        }
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

    // ---- 3D cornice, roof balustrade and window sills on the Nash / Blore ranges ----
    {
      const bathDk = kit.mat('#c8b78f', { roughness: 0.85 });
      for (const [a, b, top] of rangeEdges) {
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 1.2) continue;
        const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        const nx = Math.sin(ang),
          ny = -Math.cos(ang);
        const P = (t, d) => [a[0] + Math.cos(ang) * t + nx * d, a[1] + Math.sin(ang) * t + ny * d];
        T.mould(
          batch,
          bathDk,
          a,
          b,
          top - 2.85,
          [
            [0.12, 0.25],
            [0.2, 0.35],
            [0.35, 0.2],
            [0.55, 0.3],
            [0.6, 0.12],
          ],
          false,
        );
        T.mould(batch, bathDk, a, b, top - 16.9, [[0.12, 0.3]], false); // first-floor band
        if (len > 3) {
          T.blocks(batch, bath, P(0, 0.3), P(len, 0.3), top - 2.25, {
            w: 0.14,
            h: 0.2,
            proj: 0.25,
            gap: 0.55,
            inset: 0.3,
          });
          kit.balustrade(batch, bath, [P(0.15, 0.18), P(len - 0.15, 0.18)], top - 1.6, {
            height: 1.0,
            spacing: 0.42,
          });
          const np = Math.max(1, Math.round(len / 9));
          for (let i = 0; i <= np; i++)
            kit.box(
              batch,
              bath,
              ...P(0.3 + ((len - 0.6) * i) / np, 0.18),
              top - 1.6,
              0.55,
              0.55,
              1.15,
              ang,
            );
        }
      }
    }
    // ---- Aston Webb east front ----
    // Plan from the footprint: main face at v = -2.4, terminal pavilions at v = -0.95
    // (|u| 40.3-53.8), centrepiece at v = 0 (|u| < 9.4).
    const HF = 21.0; // top of main cornice
    const ZG = 7.2; // top of the channelled ground floor
    const VM = -2.4,
      VP = -0.95,
      VC = 0;
    const half = Lf / 2;
    const UP0 = 40.3,
      UC = 9.4;
    const ashlarW = kit.paintedMaterial(
      'buckingham_palace:portland_ashlar',
      512,
      512,
      (c, w, h) => {
        B.ashlar(c, w, h, '#e3ddcc', 'rgba(110,100,80,0.22)', h / 8, w / 3.4, 0.53);
      },
    );
    const rustic = kit.paintedMaterial('buckingham_palace:channelled', 512, 512, (c, w, h) => {
      c.fillStyle = '#dcd5c2';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.61);
      const ch = h / 7.33; // 0.6 m courses on a 4.4 m tile
      for (let k = 0; k < 8; k++) {
        c.fillStyle = `rgba(90,80,60,${0.02 + r() * 0.04})`;
        c.fillRect(0, k * ch, w, ch);
        c.fillStyle = 'rgba(70,64,52,0.6)';
        c.fillRect(0, k * ch, w, 4);
        c.fillStyle = 'rgba(255,255,245,0.35)';
        c.fillRect(0, k * ch + 4, w, 2);
      }
    });
    const glassF = kit.mat('#27313a', { roughness: 0.15, metalness: 0.3 });
    const sashF = kit.mat('#f2efe6', { roughness: 0.6 });
    const iron = kit.mat('#17191b', { roughness: 0.45, metalness: 0.5 });
    const scarlet = kit.mat('#b01e23', { roughness: 0.7 });
    const bearskin = kit.mat('#141414', { roughness: 0.9 });
    const sentry = kit.mat('#2b2e33', { roughness: 0.6 });
    const face = (ua, ub, v, z0, z1, mat, tile = 4.4) => {
      const a = F.P(ua, v),
        b = F.P(ub, v);
      B.wallsTex(batch, mat, [b, a, a], z0, z1, tile, {
        tileH: tile,
        vBase: 0,
        skip: (i) => i !== 0,
      });
    };
    const side = (u, v0, v1, z1, sgn) => {
      // return wall at u from v0 to v1 facing sgn*u
      const a = F.P(u, v0),
        b = F.P(u, v1);
      B.wallsTex(batch, ashlarW, sgn > 0 ? [a, b, b] : [b, a, a], 0, z1, 4.4, {
        tileH: 4.4,
        vBase: 0,
        skip: (i) => i !== 0,
      });
    };
    // massing: back block, terminal pavilions, centrepiece
    F.box(batch, portland, 0, VM - 2.5, 0, Lf - 0.2, 5, HF - 0.05);
    const segs = [
      [-half, -UP0, VP],
      [-UP0, -UC, VM],
      [-UC, UC, VC],
      [UC, UP0, VM],
      [UP0, half, VP],
    ];
    for (const [ua, ub, v] of segs) {
      face(ua, ub, v, 0, ZG, rustic);
      face(ua, ub, v, ZG, HF, ashlarW);
      if (v > VM) {
        F.box(batch, portland, (ua + ub) / 2, (v + VM) / 2, 0, ub - ua - 0.05, v - VM, HF - 0.05);
        side(ua, VM, v, HF, -1);
        side(ub, VM, v, HF, 1);
      }
    }
    // plinth, ground-floor cornice / balcony band, sill band
    for (const [ua, ub, v] of segs) {
      const cu = (ua + ub) / 2,
        L = ub - ua;
      F.box(batch, portlandDk, cu, v - 0.2, 0, L + 0.4, 0.8, 0.6);
      F.box(batch, portlandDk, cu, v - 0.2, ZG - 0.35, L + 0.3, 0.75, 0.35);
      F.box(batch, portland, cu, v - 0.15, ZG, L + 0.2, 0.6, 0.25);
      F.box(batch, portland, cu, v - 0.2, 14.9, L + 0.1, 0.5, 0.2); // second-floor sill band
    }
    // bays: arched ground-floor windows, piano nobile with open pediments, second floor
    let bayIdx = 0;
    const bays = (ua, ub, v, n, { arches = true } = {}) => {
      const a = F.P(ub, v),
        b = F.P(ua, v);
      if (arches)
        T.archWin(batch, a, b, 1.1, {
          count: n,
          width: 1.6,
          height: 4.4,
          glass: glassF,
          frame: sashF,
          stone: portlandDk,
          bars: 2,
          surround: 0.2,
        });
      const cs = kit.windowRow(batch, a, b, 8.1, {
        count: n,
        margin: 0,
        width: 1.7,
        height: 4.6,
        glass: glassF,
        frame: sashF,
        sill: portlandDk,
        bars: 2,
        head: 'lintel',
        surround: 0.2,
        surroundMat: portland,
        depth: 0.14,
      });
      kit.windowRow(batch, a, b, 15.3, {
        count: n,
        margin: 0,
        width: 1.5,
        height: 2.7,
        glass: glassF,
        frame: sashF,
        sill: portlandDk,
        bars: 2,
        head: 'none',
        surround: 0.16,
        surroundMat: portland,
        depth: 0.12,
      });
      for (const [x, y] of cs) {
        const ang = angF;
        const local = (du, dv) => [
          x + Math.cos(ang) * du - Math.sin(ang) * dv,
          y + Math.sin(ang) * du + Math.cos(ang) * dv,
        ];
        // apron panel and consoles
        kit.box(batch, portlandDk, ...local(0, 0.08), 7.45, 1.9, 0.16, 0.55, ang);
        for (const sd of [-1, 1])
          kit.box(batch, portlandDk, ...local(sd * 1.12, 0.12), 12.55, 0.18, 0.26, 0.55, ang);
        kit.box(batch, portland, ...local(0, 0.18), 12.95, 2.5, 0.38, 0.16, ang); // hood cornice
        if (bayIdx++ % 2 === 0) {
          // open triangular pediment
          for (const sd of [-1, 1])
            T.put(
              batch,
              portland,
              new THREE.BoxGeometry(1.15, 0.36, 0.14),
              ...local(sd * 0.72, 0.18),
              13.32,
              ang,
              1,
              1,
              1,
              0,
              sd * 0.38,
            );
          T.urn(batch, portland, ...local(0, 0.18), 13.1, 0.55);
        } else {
          // segmental pediment
          T.put(
            batch,
            portland,
            new THREE.TorusGeometry(1.75, 0.09, 4, 10, 1.25).rotateZ(Math.PI / 2 - 0.625),
            ...local(0, 0.18),
            13.1 - 1.75 * Math.cos(0.625) + 0.18,
            ang,
            1,
            1,
            2.2,
            Math.PI / 2,
            0,
          );
        }
      }
    };
    const pilasterRun = (ua, ub, v, n) => {
      for (let k = 0; k <= n; k++) {
        const u = ua + ((ub - ua) * k) / n;
        T.pilaster(
          F,
          batch,
          portland,
          u,
          v + 0.1,
          ZG + 0.25,
          HF - 1.4 - ZG - 0.25,
          0.85,
          0.2,
          'corinthian',
        );
        for (let f = -2; f <= 2; f++)
          F.box(batch, portlandDk, u + f * 0.14, v + 0.205, ZG + 0.7, 0.05, 0.02, 10.2); // flutes
      }
    };
    for (const s of [-1, 1]) {
      const [ua, ub] = s < 0 ? [-UP0, -UC] : [UC, UP0];
      bays(ua, ub, VM, 7);
      pilasterRun(ua, ub, VM, 7);
      // terminal pavilion: paired columns at both ends, three bays, blind attic
      const [pa, pb] = s < 0 ? [-half, -UP0] : [UP0, half];
      bays(pa + 1.8, pb - 1.8, VP, 3);
      for (const uu of [pa + 0.65, pa + 1.75, pb - 1.75, pb - 0.65]) {
        T.column(
          F,
          batch,
          portland,
          uu,
          VP + 0.35,
          ZG + 0.25,
          HF - 1.4 - ZG - 0.25,
          0.45,
          'corinthian',
          16,
        );
      }
      F.box(batch, portland, (pa + pb) / 2, VP - 0.6, HF, pb - pa - 1.0, 1.4, 3.0); // attic
      F.box(batch, portlandDk, (pa + pb) / 2, VP - 0.55, HF, pb - pa - 0.6, 1.5, 0.35);
      F.box(batch, portlandDk, (pa + pb) / 2, VP - 0.5, HF + 2.7, pb - pa - 0.4, 1.6, 0.25);
      F.box(batch, portland, (pa + pb) / 2, VP - 0.5, HF + 2.95, pb - pa - 0.2, 1.7, 0.3);
      F.box(batch, portlandDk, (pa + pb) / 2, VP + 0.11, HF + 0.7, pb - pa - 5.0, 0.04, 1.7); // sunk panel
      for (const uu of [pa + 1.2, pb - 1.2]) {
        F.box(batch, portland, uu, VP - 0.4, HF, 1.6, 1.6, 3.0);
        T.urn(batch, portland, ...F.P(uu, VP - 0.4), HF + 3.25, 1.4);
      }
      // trophy / garland on the attic panel
      T.put(
        batch,
        portland,
        new THREE.TorusGeometry(0.75, 0.16, 5, 16),
        ...F.P((pa + pb) / 2, VP + 0.2),
        HF + 1.55,
        angF,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
    }
    // centrepiece: paired columns, three arched gateways, balcony, pediment with the royal arms
    bays(-UC + 2.2, UC - 2.2, VC, 3, { arches: false });
    for (const uu of [-UC + 0.65, -UC + 1.75, -3.0, -1.9, 1.9, 3.0, UC - 1.75, UC - 0.65])
      T.column(
        F,
        batch,
        portland,
        uu,
        VC + 0.38,
        ZG + 0.25,
        HF - 1.4 - ZG - 0.25,
        0.47,
        'corinthian',
        16,
      );
    for (const uu of [-5.6, 0, 5.6]) {
      const w = uu === 0 ? 3.6 : 3.0,
        hs = uu === 0 ? 4.1 : 3.6;
      const arch = new THREE.Shape();
      arch.moveTo(-w / 2, 0);
      arch.lineTo(w / 2, 0);
      arch.lineTo(w / 2, hs);
      arch.absarc(0, hs, w / 2, 0, Math.PI, false);
      arch.lineTo(-w / 2, 0);
      T.slab(F, batch, voidm, arch, uu, VC + 0.03, 0, 0.04, 12);
      // archivolt, keystone
      F.put(
        batch,
        portlandDk,
        new THREE.TorusGeometry(w / 2 + 0.15, 0.17, 4, 14, Math.PI),
        uu,
        VC + 0.08,
        hs,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      F.box(batch, portland, uu, VC + 0.15, hs + w / 2, 0.55, 0.3, 0.75);
      // gilded gates in the archway
      const gv = VC + 0.12;
      F.box(batch, iron, uu, gv, 0, w, 0.06, 0.12);
      F.box(batch, iron, uu, gv, hs * 0.55, w, 0.06, 0.1);
      F.box(batch, gold, uu, gv, hs, w, 0.07, 0.1);
      for (let k = 0; k <= 14; k++)
        F.box(batch, iron, uu - w / 2 + (w * k) / 14, gv, 0, 0.035, 0.035, hs);
      F.put(
        batch,
        gold,
        new THREE.TorusGeometry(0.4, 0.05, 4, 12),
        uu,
        gv + 0.02,
        hs * 0.78,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      F.put(
        batch,
        gold,
        new THREE.TorusGeometry(w / 2 - 0.05, 0.04, 4, 12, Math.PI),
        uu,
        gv,
        hs,
        0,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
    }
    // the balcony: stone slab on consoles with a balustrade
    {
      const bw = 10.6,
        bd = 2.4,
        z = ZG + 0.2;
      F.box(batch, portlandDk, 0, VC + bd / 2, z, bw, bd, 0.3);
      F.box(batch, portland, 0, VC + bd / 2, z + 0.3, bw + 0.1, bd + 0.05, 0.12);
      for (const uu of [-4.8, -2.4, 2.4, 4.8]) {
        const cs = new THREE.Shape();
        cs.moveTo(0, 0);
        cs.lineTo(bd - 0.2, 0);
        cs.quadraticCurveTo(0.4, -0.2, 0, -1.4);
        const g2 = new THREE.ExtrudeGeometry(cs, {
          depth: 0.4,
          bevelEnabled: false,
          curveSegments: 5,
        })
          .rotateX(Math.PI / 2)
          .rotateZ(Math.PI / 2)
          .translate(0, 0, 0);
        F.put(batch, portlandDk, g2, uu - 0.2, VC, z);
      }
      const p0 = F.P(-bw / 2 + 0.1, VC + 0.1),
        p1 = F.P(-bw / 2 + 0.1, VC + bd - 0.15),
        p2 = F.P(bw / 2 - 0.1, VC + bd - 0.15),
        p3 = F.P(bw / 2 - 0.1, VC + 0.1);
      kit.balustrade(batch, portland, [p0, p1, p2, p3], z + 0.42, { height: 1.0, spacing: 0.28 });
      for (const p of [p1, p2])
        kit.box(batch, portland, p[0], p[1], z + 0.42, 0.45, 0.45, 1.1, angF);
    }
    // entablature with modillion cornice following the breaks, roof balustrade with piers
    for (const [ua, ub, v] of segs) {
      const cu = (ua + ub) / 2,
        L = ub - ua;
      F.box(batch, portland, cu, v - 0.3, HF - 1.4, L + 0.2, 0.9, 0.45); // architrave
      F.box(batch, portland, cu, v - 0.25, HF - 0.95, L + 0.25, 1.0, 0.45); // frieze
      F.box(batch, portlandDk, cu, v - 0.1, HF - 0.5, L + 0.6, 1.3, 0.15);
      F.box(batch, portland, cu, v, HF - 0.35, L + 0.9, 1.5, 0.25);
      F.box(batch, portlandDk, cu, v, HF - 0.1, L + 1.0, 1.6, 0.1);
      T.blocks(batch, portland, F.P(ub + 0.3, v + 0.35), F.P(ua - 0.3, v + 0.35), HF - 0.55, {
        w: 0.14,
        h: 0.2,
        proj: 0.35,
        gap: 0.6,
      });
      T.blocks(batch, portlandDk, F.P(ub + 0.2, v + 0.3), F.P(ua - 0.2, v + 0.3), HF - 0.7, {
        w: 0.09,
        h: 0.13,
        proj: 0.1,
        gap: 0.08,
      });
      if (Math.abs(cu) > UC + 1 && v === VM) {
        const line = [F.P(ua + 0.4, v + 0.1), F.P(ub - 0.4, v + 0.1)];
        kit.balustrade(batch, portland, line, HF, { height: 1.15, spacing: 0.3 });
        const n = 7;
        for (let k = 0; k <= n; k++)
          F.box(batch, portland, ua + ((ub - ua) * k) / n, v + 0.1, HF, 0.7, 0.7, 1.3);
      }
    }
    // pediment with the royal arms supported by the lion and the unicorn
    {
      const pw = 2 * UC + 1.0;
      const ped = new THREE.Shape([
        new THREE.Vector2(-pw / 2, 0),
        new THREE.Vector2(pw / 2, 0),
        new THREE.Vector2(0, 4.2),
      ]);
      T.slab(F, batch, portland, ped, 0, VC - 0.6, HF, 1.6);
      const rake = Math.atan2(4.2, pw / 2),
        rl = Math.hypot(4.2, pw / 2);
      for (const sd of [-1, 1])
        F.put(
          batch,
          portlandDk,
          new THREE.BoxGeometry(rl + 0.5, 1.9, 0.35),
          (sd * pw) / 4,
          VC - 0.55,
          HF + 2.1 + 0.18,
          0,
          1,
          1,
          1,
          0,
          sd * rake,
        );
      F.box(batch, portlandDk, 0, VC + 0.21, HF + 0.6, 0.02, 0.02, 0.02);
      // arms: shield, crown and supporters in relief
      const shield = new THREE.Shape();
      shield.moveTo(-0.8, 1.0);
      shield.lineTo(0.8, 1.0);
      shield.lineTo(0.8, 0.0);
      shield.quadraticCurveTo(0.75, -0.75, 0, -1.0);
      shield.quadraticCurveTo(-0.75, -0.75, -0.8, 0.0);
      T.slab(F, batch, portland, shield, 0, VC + 0.25, HF + 1.6, 0.25, 6);
      T.put(
        batch,
        portland,
        new THREE.TorusGeometry(1.2, 0.12, 4, 16),
        ...F.P(0, VC + 0.28),
        HF + 1.6,
        angF,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      ); // garter
      T.lathePut(
        batch,
        gold,
        [
          [0.35, 0],
          [0.45, 0.25],
          [0.3, 0.5],
          [0.1, 0.65],
          [0, 0.75],
        ],
        ...F.P(0, VC + 0.3),
        HF + 2.85,
        8,
      ); // crown
      for (const sd of [-1, 1])
        T.xform(
          batch,
          (b) => T.horse(b, portland, 0, 0, 0, 0, 0.75, 0.9),
          T.at(F, sd * 2.3, VC + 0.2, HF + 0.2, sd > 0 ? Math.PI : 0, 1, 0.3, 1),
        );
      for (const sd of [-1, 1])
        T.urn(batch, portland, ...F.P(sd * (pw / 2 - 0.3), VC - 0.5), HF + 0.1, 1.6);
      T.urn(batch, portland, ...F.P(0, VC - 0.5), HF + 4.3, 1.4);
    }
    // flagstaff with the Union Flag on the roof behind the centrepiece
    {
      const [x, y] = F.P(0, VM - 4.5);
      F.box(batch, lead, 0, VM - 4.5, HF, 2.0, 2.0, 1.0);
      T.flag(batch, kit.mat('white'), union, x, y, HF + 1.0, 13, angF, 6.0, 3.0);
    }
    // forecourt: gravel, railings with gilded spear heads, gate piers with lanterns, gates, sentry boxes, guards
    {
      const D = 20;
      const q = [F.P(-half - 3, VM), F.P(half + 3, VM), F.P(half + 3, D), F.P(-half - 3, D)];
      batch.add(
        gravel,
        q.map(([x, y]) => [x, y, 0.06]),
        q.map(([x, y]) => [x / 6, y / 6]),
        [0, 1, 2, 0, 2, 3],
      );
      const piers = [-half - 3, -46.5, -42.5, -26, -22, -3.2, 3.2, 22, 26, 42.5, 46.5, half + 3];
      const gates = new Set([1, 3, 5, 7, 9]); // gaps between piers k and k+1 that hold gates
      for (let k = 0; k < piers.length - 1; k++) {
        const ua = piers[k] + 0.85,
          ub = piers[k + 1] - 0.85;
        if (gates.has(k)) {
          const tall = k === 5 ? 4.6 : 3.8;
          T.railing(batch, iron, [F.P(ua, D), F.P(ub, D)], 0.06, {
            height: tall,
            spacing: 0.12,
            post: 20,
            finial: gold,
            bar: 0.03,
          });
          const cu = (ua + ub) / 2;
          F.box(batch, gold, cu, D, tall * 0.62, ub - ua, 0.06, 0.08);
          F.box(batch, gold, cu, D, tall - 0.3, ub - ua, 0.06, 0.08);
          for (const sd of [-1, 1])
            F.put(
              batch,
              gold,
              new THREE.TorusGeometry(0.42, 0.05, 4, 14),
              cu + (sd * (ub - ua)) / 4,
              D,
              tall * 0.4,
              angF,
              1,
              1,
              1,
              Math.PI / 2,
              0,
            );
          // overthrow with the royal arms and crown
          F.put(
            batch,
            gold,
            new THREE.TorusGeometry((ub - ua) / 2, 0.05, 4, 16, Math.PI),
            cu,
            D,
            tall,
            0,
            1,
            1,
            0.5,
            Math.PI / 2,
            0,
          );
          T.slab(
            F,
            batch,
            gold,
            new THREE.Shape([
              new THREE.Vector2(-0.45, 0),
              new THREE.Vector2(0.45, 0),
              new THREE.Vector2(0.45, 0.6),
              new THREE.Vector2(0, 1.0),
              new THREE.Vector2(-0.45, 0.6),
            ]),
            cu,
            D,
            tall + 0.3,
            0.08,
            4,
          );
        } else {
          F.box(batch, portlandDk, (ua + ub) / 2, D, 0, ub - ua, 0.7, 0.6);
          T.railing(batch, iron, [F.P(ua, D), F.P(ub, D)], 0.6, {
            height: 2.3,
            spacing: 0.13,
            post: 3.2,
            finial: gold,
          });
        }
      }
      for (const uu of piers) {
        F.box(batch, portlandDk, uu, D, 0, 1.9, 1.9, 0.5);
        F.box(batch, portland, uu, D, 0.5, 1.6, 1.6, 3.4);
        F.box(batch, portlandDk, uu, D, 3.9, 1.9, 1.9, 0.35);
        // gilded lantern bracket on top of each pier
        T.lathePut(
          batch,
          iron,
          [
            [0.35, 0],
            [0.12, 0.2],
            [0.08, 0.9],
            [0.0, 0.95],
          ],
          ...F.P(uu, D),
          4.25,
          8,
        );
        T.lathePut(
          batch,
          gold,
          [
            [0.22, 0],
            [0.32, 0.45],
            [0.26, 0.6],
            [0.12, 0.8],
            [0.0, 0.95],
          ],
          ...F.P(uu, D),
          5.1,
          8,
        );
      }
      for (const s of [-1, 1]) {
        F.box(batch, portlandDk, s * (half + 3), (D + VM) / 2, 0, 0.7, D - VM, 0.6);
        T.railing(batch, iron, [F.P(s * (half + 3), VM), F.P(s * (half + 3), D - 1)], 0.6, {
          height: 2.3,
          spacing: 0.13,
          post: 3.2,
          finial: gold,
        });
      }
      // sentry boxes with guardsmen in scarlet tunics and bearskins
      for (const uu of [-17, -12, 12, 17]) {
        const [x, y] = F.P(uu, 4.0);
        kit.box(batch, sentry, x, y, 0.06, 1.25, 1.25, 2.6, angF);
        kit.pitchedRoof(
          batch,
          sentry,
          sentry,
          [F.P(uu - 0.7, 3.3), F.P(uu + 0.7, 3.3), F.P(uu + 0.7, 4.7), F.P(uu - 0.7, 4.7)],
          angF,
          2.66,
          0.55,
          'pyramidal',
          { overhang: 0.05 },
        );
        F.box(batch, voidm, uu, 4.64, 0.3, 0.8, 0.02, 2.1);
        if (Math.abs(uu) === 12) {
          const [gx, gy] = F.P(uu + Math.sign(uu) * 1.4, 4.9);
          T.figure(batch, scarlet, gx, gy, 0.06, 1.85, angF + Math.PI / 2);
          T.lathePut(
            batch,
            bearskin,
            [
              [0.14, 0],
              [0.17, 0.2],
              [0.15, 0.38],
              [0.0, 0.45],
            ],
            gx,
            gy,
            1.72,
            8,
          );
          T.rod(
            batch,
            iron,
            [gx + 0.25 * Math.cos(angF), gy + 0.25 * Math.sin(angF), 0.6],
            [gx + 0.25 * Math.cos(angF), gy + 0.25 * Math.sin(angF), 1.9],
            0.02,
            0.02,
            4,
            true,
          );
        }
      }
      if (placeAssets) {
        const lamps = [];
        for (const u of [-50, -34, -12, 12, 34, 50])
          lamps.push([...F.P(u, D + 3.5), angF + Math.PI]);
        g.add(placeAssets('street_lamp', lamps));
      }
    }
    g.add(batch.toGroup('buckingham_palace'));
    return g;
  },
};
