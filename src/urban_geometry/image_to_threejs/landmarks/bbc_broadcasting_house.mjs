// BBC Broadcasting House, Portland Place / Langham Place (G. Val Myer with M. T.
// Tudsbery, opened 1932) and its 2005-13 extensions. The original Art Deco
// block is a steel frame clad in Portland stone; its rounded "ship's prow" south
// end faces All Souls Langham Place, with Eric Gill's Prospero and Ariel over
// the entrance, the clock and the roof-top lattice mast. The massing steps back
// in the upper floors. East of the piazza stands the John Peel Wing (former Egton
// Wing) in matching Portland stone, linked to the old building at the rear by a
// glass-fronted extension.
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
  id: 'bbc_broadcasting_house',
  name: 'BBC Broadcasting House',
  claims: ['8f1d5a24-abeb-4827-b54c-da1e75bba49c'],
  references: [
    {
      title: 'Broadcasting House - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Broadcasting_House',
      used_for:
        'Art Deco HQ on Portland Place/Langham Place, John Peel (Egton) wing on the east side, extension at the rear, piazza',
    },
    {
      title: 'Broadcasting House, London - Modernist Britain',
      url: 'https://www.modernistbritain.co.uk/post/building/Broadcasting+House/',
      used_for: 'Val Myer / Tudsbery, steel frame clad in Portland stone, Gill sculpture',
    },
    {
      title: 'Broadcasting House - Regent Street - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1930/broadcasthouse.html',
      used_for:
        'nine storeys stepping down to six on the Langham Street side; main facade topped by an ornamental clock tower; lattice mast (replica)',
    },
    {
      title: 'BBC Broadcasting House - A London Inheritance',
      url: 'https://alondoninheritance.com/london-books/bbc-broadcasting-house',
      used_for: 'Prospero and Ariel above the entrance; general appearance',
    },
    {
      title: 'The historical building of BBC Broadcasting House - World Construction Network',
      url: 'https://worldconstructionnetwork.com/?p=5337',
      used_for: 'John Peel wing in the same Portland stone; glass-fronted link extension',
    },
    {
      title: 'Breathing (memorial sculpture) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Breathing_(memorial_sculpture)',
      used_for: '10 m inverted glass-and-steel spire by Jaume Plensa on the roof of the Peel wing',
    },
  ],
  notes:
    'Outline from Overture; the old building is taken as the west arm of the U-shaped footprint (west of the piazza line) and the rest as the Peel wing / link extension. Old BH heights: 24.2 m (Overture) to the main parapet, then two set-back storeys to 31.5 m and the clock stage to ~33 m - set-back depths are estimated. Detail pass: ashlar walls with modelled metal casements on a 2.4 m bay (five storeys plus tall ground-floor windows and the set-back storeys), terrace railings, bronze entrance with Prospero and Ariel (on a globe) in a moulded niche, a 3D clock with gilt ring and numerals; the lattice mast and Gill group remain schematic. Peel wing: ashlar frame with storey-height tripartite glazing; Breathing spire position on the roof is approximate. Piazza paving, bollards, benches and lamps are approximate (resources assets).',
  build({ THREE, kit, byId, placeAssets }) {
    const T = tools(THREE, kit),
      B = bldTools(THREE, kit);
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['8f1d5a24-abeb-4827-b54c-da1e75bba49c'];
    const stone = kit.mat('#e3ddcc', { roughness: 0.8 });
    const stoneDk = kit.mat('#cbc4af');
    const roofm = kit.mat('#9a9b96');
    const steel = kit.mat('#d4d6d6', { roughness: 0.5, metalness: 0.4 });
    const H = 24.2;
    const glassB = kit.mat('#29323a', { roughness: 0.15, metalness: 0.3 });
    const metal = kit.mat('#3b3f3c', { roughness: 0.45, metalness: 0.5 });
    const bronzeB = kit.mat('#3b3529', { metalness: 0.5, roughness: 0.45 });
    const gilt = kit.mat('gold');
    const ashB = kit.paintedMaterial('bbc_broadcasting_house:ashlar', 256, 512, (c, w, h) => {
      B.ashlar(c, w, h, '#e4decd', 'rgba(110,100,80,0.22)', h / 11.4, w / 2.5, 0.19); // 4 m x 8 m
    });
    const linkGlass = kit.facade('glass', 1);

    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    // dividing line along the west side of the piazza (vertex 10 -> 11 direction), extended
    const pA = [3952.57, 1323.27],
      pB = [3941.81, 1361.13];
    const d = [pB[0] - pA[0], pB[1] - pA[1]];
    const side = (p) => d[0] * (p[1] - pA[1]) - d[1] * (p[0] - pA[0]); // > 0 west of the line
    const clip = (r, f) => {
      const out = [];
      for (let i = 0; i < r.length; i++) {
        const a = r[i],
          c = r[(i + 1) % r.length];
        const fa = f(a),
          fc = f(c);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fc >= 0) {
          const t = fa / (fa - fc);
          out.push([a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const oldBH = ccw(clip(ring, (p) => side(p) + 0.01));
    const east = ccw(clip(ring, (p) => -side(p) + 0.01));

    // ---------------- old Broadcasting House ----------------
    // Portland ashlar with modelled metal casements in plain reveals, set-back upper storeys
    const inRing = (p, r) => {
      let ins = false;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const A = r[i],
          C = r[j];
        if (
          A[1] > p[1] !== C[1] > p[1] &&
          p[0] < ((C[0] - A[0]) * (p[1] - A[1])) / (C[1] - A[1]) + A[0]
        )
          ins = !ins;
      }
      return ins;
    };
    // an edge is internal when the point 1 m outside it still lies inside the whole footprint
    const isCut = (a, c) => {
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
      const p = [
        (a[0] + c[0]) / 2 + ((c[1] - a[1]) / len) * 1.0,
        (a[1] + c[1]) / 2 - ((c[0] - a[0]) / len) * 1.0,
      ];
      return inRing(p, ring);
    };
    const wins = (r, z0, rows, storey, opts) => {
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          c = r[(k + 1) % r.length];
        const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
        if (len < 1.6 || isCut(a, c)) continue;
        const n = Math.max(1, Math.round(len / 2.4));
        for (let j = 0; j < rows; j++)
          kit.windowRow(batch, a, c, z0 + j * storey, {
            count: n,
            margin: 0.2,
            glass: glassB,
            frame: metal,
            sill: stoneDk,
            head: 'none',
            depth: 0.1,
            ...opts,
          });
      }
    };
    B.wallsTex(batch, ashB, oldBH, 0, H, 4, { tileH: 8, vBase: 0 });
    B.band(batch, stoneDk, oldBH, 0, 0.6, 0.12); // granite-coloured plinth
    B.band(batch, stoneDk, oldBH, 4.8, 5.2, 0.15);
    B.band(batch, stone, oldBH, H - 0.2, H + 0.58, 0.1);
    wins(oldBH, 0.9, 1, 0, { width: 1.4, height: 3.5, bars: 2, sill: stoneDk });
    wins(oldBH, 5.9, 5, 3.5, { width: 0.96, height: 1.8, bars: 1 });
    kit.cap(batch, roofm, [[oldBH]], H + 0.6);
    const s1 = kit.offsetRing(oldBH, -4.5),
      s2 = kit.offsetRing(oldBH, -9.5);
    B.wallsTex(batch, ashB, s1, H + 0.6, 28.2, 4, { tileH: 8, vBase: 0 });
    wins(s1, H + 1.4, 1, 0, { width: 0.96, height: 1.8, bars: 1 });
    B.band(batch, stone, s1, 28.0, 28.48, 0.1);
    kit.cap(batch, roofm, [[s1]], 28.5);
    B.wallsTex(batch, ashB, s2, 28.5, 31.5, 4, { tileH: 8, vBase: 0 });
    wins(s2, 29.2, 1, 0, { width: 0.96, height: 1.6, bars: 1 });
    B.band(batch, stone, s2, 31.3, 31.6, 0.08);
    kit.cap(batch, roofm, [[s2]], 31.6);
    // roof-terrace railings on the set-backs
    for (const [r, z] of [
      [kit.offsetRing(oldBH, -0.3), H + 0.6],
      [kit.offsetRing(s1, -0.3), 28.5],
    ])
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          c = r[(k + 1) % r.length];
        if (isCut(oldBH[k] ?? a, oldBH[(k + 1) % oldBH.length] ?? c)) continue;
        if (Math.hypot(c[0] - a[0], c[1] - a[1]) > 0.5)
          T.railing(batch, metal, [a, c], z, {
            height: 1.0,
            spacing: 0.6,
            post: 3,
            spear: false,
            bar: 0.03,
          });
      }
    // clock stage, mast, Gill group: the prow is the rounded south end facing All Souls
    const axis = Math.atan2(d[1], d[0]); // along the arm, pointing north
    const CF = T.frame(3935.0, 1325.0, axis - Math.PI / 2); // +u east-ish, +v north along the arm
    CF.box(batch, stone, 0, 0, H + 0.6, 11, 8, 8.4);
    CF.box(batch, stoneDk, 0, 0, H + 9.0, 11.6, 8.6, 0.6);
    CF.box(batch, stone, 0, 0, H + 9.6, 6, 4.5, 2.0);
    const clock = kit.paintedMaterial('bbc_broadcasting_house:clock', 128, 128, (c, w, h) => {
      c.fillStyle = '#e3ddcc';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#f3f0e6';
      c.beginPath();
      c.arc(w / 2, h / 2, w * 0.4, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#c2a14d';
      c.lineWidth = 6;
      c.stroke();
      c.fillStyle = '#c2a14d';
      for (let k = 0; k < 12; k++) {
        const a2 = (k * Math.PI) / 6;
        c.fillRect(w / 2 + Math.cos(a2) * w * 0.32 - 3, h / 2 + Math.sin(a2) * w * 0.32 - 3, 6, 6);
      }
      c.strokeStyle = '#222';
      c.lineWidth = 4;
      c.beginPath();
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.5, h * 0.22);
      c.moveTo(w / 2, h / 2);
      c.lineTo(w * 0.68, h * 0.58);
      c.stroke();
    });
    {
      // clock on the south face of the clock stage (faces -v): face, gilt ring and numerals, hands
      const [cx, cy] = CF.P(0, -4.03);
      T.put(
        batch,
        clock,
        new THREE.CircleGeometry(2.4, 32).rotateX(Math.PI / 2),
        cx,
        cy,
        H + 5.0,
        CF.ang,
      );
      T.put(
        batch,
        gilt,
        new THREE.TorusGeometry(2.5, 0.14, 5, 32),
        cx,
        cy,
        H + 5.0,
        CF.ang,
        1,
        1,
        1,
        Math.PI / 2,
        0,
      );
      CF.box(batch, stoneDk, 0, -4.1, H + 2.3, 6.0, 0.2, 0.3);
      for (let k = 0; k < 12; k++) {
        const a2 = (k * Math.PI) / 6;
        const [nx, ny] = CF.P(Math.cos(a2) * 2.1, -4.1);
        T.put(
          batch,
          gilt,
          new THREE.BoxGeometry(0.12, 0.08, 0.38),
          nx,
          ny,
          H + 5.0 + Math.sin(a2) * 2.1,
          CF.ang,
          1,
          1,
          1,
          0,
          -a2 + Math.PI / 2,
        );
      }
      T.put(
        batch,
        metal,
        new THREE.BoxGeometry(0.16, 0.06, 1.7),
        ...CF.P(0.3, -4.12),
        H + 5.75,
        CF.ang,
        1,
        1,
        1,
        0,
        0.4,
      );
      T.put(
        batch,
        metal,
        new THREE.BoxGeometry(0.14, 0.06, 2.1),
        ...CF.P(-0.55, -4.14),
        H + 4.7,
        CF.ang,
        1,
        1,
        1,
        0,
        -2.1,
      );
      // stepped Art Deco crown of the clock stage
      CF.box(batch, stone, 0, 0, H + 8.4, 10.4, 7.4, 0.6);
      for (const s of [-1, 1]) CF.box(batch, stoneDk, s * 5.4, -3.95, H + 0.6, 0.3, 0.2, 8.4);
    }
    // lattice radio mast on the roof behind the clock stage
    {
      const [mx, my] = CF.P(-3, 24);
      const z0 = 31.5,
        hM = 17,
        r0 = 1.6,
        r1 = 0.35;
      const leg = (k, t) => {
        const a2 = (k * Math.PI * 2) / 3 + 0.3,
          r = r0 + (r1 - r0) * t;
        return [mx + Math.cos(a2) * r, my + Math.sin(a2) * r, z0 + hM * t];
      };
      for (let k = 0; k < 3; k++) {
        T.rod(batch, steel, leg(k, 0), leg(k, 1), 0.09, 0.06, 4);
        for (let j = 0; j < 8; j++) {
          T.rod(batch, steel, leg(k, j / 8), leg((k + 1) % 3, (j + 1) / 8), 0.04, 0.04, 3);
          T.rod(batch, steel, leg(k, (j + 1) / 8), leg((k + 1) % 3, (j + 1) / 8), 0.04, 0.04, 3);
        }
      }
      T.rod(batch, steel, [mx, my, z0 + hM], [mx, my, z0 + hM + 4], 0.06, 0.03, 4);
    }
    // Prospero and Ariel in a tall niche over the bronze entrance at the prow tip (faces south)
    {
      const tip = [3943.7, 1311.0];
      kit.box(batch, stoneDk, tip[0], tip[1] + 0.25, 5.2, 5.4, 0.6, 8.2, 0);
      kit.box(batch, kit.mat('#bdb6a2'), tip[0], tip[1] - 0.06, 5.6, 4.4, 0.04, 7.4, 0); // niche back
      kit.box(batch, stone, tip[0] - 2.5, tip[1] - 0.5, 5.2, 0.5, 1.0, 8.2, 0);
      kit.box(batch, stone, tip[0] + 2.5, tip[1] - 0.5, 5.2, 0.5, 1.0, 8.2, 0);
      kit.box(batch, stone, tip[0], tip[1] - 0.5, 13.0, 5.5, 1.0, 0.5, 0);
      // bronze entrance doors and canopy
      kit.box(batch, bronzeB, tip[0], tip[1] - 0.1, 0, 4.4, 0.4, 4.8, 0);
      for (const dx of [-1.5, -0.5, 0.5, 1.5])
        kit.box(batch, glassB, tip[0] + dx, tip[1] - 0.32, 0.1, 0.8, 0.04, 3.2, 0);
      kit.box(batch, gilt, tip[0], tip[1] - 0.32, 3.6, 4.0, 0.04, 0.6, 0);
      kit.box(batch, stoneDk, tip[0], tip[1] - 0.6, 5.0, 4.8, 1.4, 0.45, 0);
      // Prospero (robed, standing) sending Ariel (smaller, arms outspread) out into the world
      T.figure(batch, stone, tip[0] - 0.7, tip[1] - 0.55, 5.45, 3.8, -Math.PI / 2, {
        robe: true,
        armOut: true,
      });
      T.lathePut(
        batch,
        stone,
        [
          [0.55, 0],
          [0.62, 0.4],
          [0.4, 0.9],
          [0, 1.0],
        ],
        tip[0] + 0.9,
        tip[1] - 0.7,
        5.45,
        10,
      ); // globe
      T.figure(batch, stone, tip[0] + 0.9, tip[1] - 0.7, 6.4, 2.1, -Math.PI / 2, {
        armUp: true,
        armOut: true,
      });
    }
    {
      const [fx, fy] = CF.P(0, 2);
      T.rod(batch, kit.mat('white'), [fx, fy, H + 11.6], [fx, fy, H + 17], 0.08, 0.05, 5);
    }

    // ---------------- John Peel wing and link extension ----------------
    const yCut = 1379; // piazza head: south = Peel wing (stone), north = glass link
    for (let k = 0; k < east.length; k++) {
      const a = east[k],
        c = east[(k + 1) % east.length];
      const my = (a[1] + c[1]) / 2;
      const onCut = Math.abs(side(a)) < 0.05 && Math.abs(side(c)) < 0.05;
      if (onCut) continue; // shared with the old building
      if (my < yCut) {
        B.wallsTex(batch, ashB, [a, c, c], 0, H, 4, { tileH: 8, vBase: 0, skip: (i) => i !== 0 });
        const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
        if (len > 3) {
          const n = Math.max(1, Math.round(len / 4.5));
          kit.windowRow(batch, a, c, 0.6, {
            count: n,
            margin: 0.2,
            width: 3.4,
            height: 3.6,
            glass: glassB,
            frame: metal,
            sill: stoneDk,
            head: 'none',
            bars: 2,
            depth: 0.12,
          });
          for (let j = 0; j < 6; j++)
            kit.windowRow(batch, a, c, 5.3 + j * 3.15, {
              count: n,
              margin: 0.2,
              width: 3.4,
              height: 2.5,
              glass: glassB,
              frame: metal,
              sill: stoneDk,
              head: 'none',
              bars: 2,
              depth: 0.12,
            });
        }
      } else kit.walls(batch, linkGlass, [[[a, c]]], 0, H, { bay: 3.4, storey: 3.5 });
    }
    // kit.walls on a 2-point ring also emits the closing edge c->a; acceptable (inside the volume)
    B.band(batch, stone, east, H - 0.4, H + 0.28, 0.1);
    kit.cap(batch, roofm, [[east]], H + 0.3);
    const eu = kit.offsetRing(east, -6);
    if (Math.abs(kit.ringArea(eu)) > 200) {
      kit.walls(batch, kit.facade('portland_stone', 3), [[eu]], H + 0.3, H + 3.6, {
        bay: 3.4,
        storey: 3.3,
        uvBase: H + 0.3,
      });
      kit.cap(batch, roofm, [[eu]], H + 3.6);
    }
    // "Breathing" (Jaume Plensa, 2008): 10 m inverted glass-and-steel spire on the Peel wing roof
    {
      const [bx, by] = [3974.0, 1342.0];
      const glassSp = kit.mat('#bcd6df', {
        roughness: 0.1,
        metalness: 0.2,
        transparent: true,
        opacity: 0.75,
      });
      T.lathePut(
        batch,
        steel,
        [
          [0.25, 0],
          [0.18, 0.6],
          [0.05, 1.2],
          [0, 1.25],
        ].map(([r, z]) => [r, 1.25 - z]),
        bx,
        by,
        H + 0.3,
        8,
      );
      T.lathePut(
        batch,
        glassSp,
        [
          [0.05, 0],
          [0.6, 3.5],
          [1.2, 7.0],
          [1.55, 9.0],
          [0, 9.0],
        ],
        bx,
        by,
        H + 1.5,
        16,
      );
      T.put(batch, steel, new THREE.TorusGeometry(1.55, 0.06, 4, 20), bx, by, H + 10.5);
      for (let k = 0; k < 8; k++) {
        const a2 = (k * Math.PI) / 4;
        T.rod(
          batch,
          steel,
          [bx, by, H + 1.5],
          [bx + Math.cos(a2) * 1.55, by + Math.sin(a2) * 1.55, H + 10.5],
          0.03,
          0.03,
          3,
          true,
        );
      }
    }
    // the piazza between the old building and the Peel wing: paving, bollards, benches, lamps
    {
      const pz = [
        [3952.6, 1323.3],
        [3971.2, 1334.5],
        [3959.4, 1365.8],
        [3941.8, 1361.1],
      ];
      kit.cap(batch, kit.mat('#c9c3b6', { roughness: 0.9 }), [[ccw(pz)]], 0.04);
      if (placeAssets) {
        g.add(
          placeAssets('bollard', [
            [3953.5, 1318.5, 0.3],
            [3957.0, 1320.5, 0.3],
            [3960.5, 1322.6, 0.3],
            [3964.0, 1324.7, 0.3],
            [3967.5, 1326.8, 0.3],
          ]),
        );
        g.add(
          placeAssets('bench', [
            [3950.5, 1340.0, -1.3],
            [3962.5, 1345.0, 1.9],
          ]),
        );
        g.add(
          placeAssets('street_lamp', [
            [3948.5, 1330.0, 0.3],
            [3966.0, 1338.0, 0.3],
          ]),
        );
      }
    }
    g.add(batch.toGroup('bbc_broadcasting_house'));
    return g;
  },
};
