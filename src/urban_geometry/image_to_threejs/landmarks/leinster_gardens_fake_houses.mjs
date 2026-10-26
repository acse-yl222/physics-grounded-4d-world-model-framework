// 23-24 Leinster Gardens, Bayswater: the false house fronts built after the Metropolitan
// Railway's Paddington-Bayswater line opened in 1868. The two houses were demolished for
// the open cutting (where steam locomotives vented); a thin facade was built to match the
// stucco terrace either side, complete with balconies, columns and porches - but its
// windows are painted on and there are no rooms behind. Owned by TfL, Grade II.
export default {
  id: 'leinster_gardens_fake_houses',
  name: '23-24 Leinster Gardens (false facades)',
  claims: ['b56a88ab-9e6f-447a-99aa-04c5e48edf94'],
  references: [
    {
      title: 'Leinster Gardens - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Leinster_Gardens',
      used_for:
        'nos 23 and 24 demolished for the Metropolitan Railway (1868); 5 ft thick false front matching the five-storey terrace; venting of steam locomotives',
    },
    {
      title: 'A deceptive facade at 23/24 Leinster Gardens - urban75',
      url: 'https://www.urban75.org/blog/the-incredible-fake-houses-in-paddington/amp/',
      used_for:
        'facade copies the neighbours (balconies, columns, decoration); windows painted on, no rooms behind',
    },
    {
      title: 'Leinster Gardens False Facades - Atlas Obscura',
      url: 'https://Www.atlasobscura.com/places/leinster-gardens-false-facades',
      used_for: 'exposed section still used by the Circle line; owned by TfL; listed',
    },
    {
      title: 'The fake houses at 23 and 24 Leinster Gardens - urban75',
      url: 'https://www.urban75.org/blog/the-fake-houses-at-23-and-24-leinster-gardens-bayswater-london-w2/',
      used_for:
        'wall thickness ~1.5 m, only about six inches at the windows; rear view of the bracing',
    },
  ],
  notes:
    'Modelled on the 1.8 m deep Overture strip between the Henry Hotel and the Blakemore Hyde Park. Ornament follows the generic Leinster Gardens stucco terrace (porches, balcony, pedimented first-floor windows, cornice, parapet); exact mouldings approximated. The rear (cutting side) is shown as bare brick with iron stays; the railway cutting itself is not modelled.',
  build(ctx) {
    // ---- local helpers (no imports: kept inline) ---------------------------------
    const { THREE, kit } = ctx;
    const B = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r.slice());
    const ringOf = (id) => ccw(ctx.byId[id].polys[0][0]);
    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1e-9;
        return {
          a,
          b,
          k,
          len,
          ux: dx / len,
          uy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.ux * s + e.nx * d, e.a[1] + e.uy * s + e.ny * d];
    // Box on edge e: along-edge span s0..s1, outward offset d0..d1, height z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(B, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const prism = (m, ring, z0, z1, topM = m) => {
      kit.walls(B, m, [[ring]], z0, z1, { bay: 1e6 });
      if (topM) kit.cap(B, topM, [[ring]], z1);
    };
    // Local rectangle (centre cx, cy, size w x d, rotated a) as a CCW ring.
    const rect = (cx, cy, w, d, a = 0) => {
      const c = Math.cos(a),
        s = Math.sin(a);
      return [
        [-w / 2, -d / 2],
        [w / 2, -d / 2],
        [w / 2, d / 2],
        [-w / 2, d / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    const geo = (m, g, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    // Upright cylinder / cone / pyramid (axis +z) from z0 to z1.
    const cyl = (m, x, y, z0, z1, r0, r1 = r0, seg = 12, rz = 0) =>
      geo(
        m,
        new THREE.CylinderGeometry(r1, r0, z1 - z0, seg).rotateX(Math.PI / 2),
        x,
        y,
        (z0 + z1) / 2,
        rz,
      );
    // Curtain wall on every edge of ring: glass, vertical mullions and storey bands.
    const curtain = (ring, z0, z1, o = {}) => {
      const {
        glass = kit.mat('glass'),
        frame = kit.mat('aluminium'),
        mull = 1.5,
        storey = 3.6,
        fin = 0.12,
        band = 0.25,
        bandMat = frame,
        minLen = 0.3,
        finMat = frame,
        edgeFilter = () => true,
      } = o;
      for (const e of edgesOf(ring)) {
        if (e.len < minLen || !edgeFilter(e)) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        if (mull > 0) {
          const n = Math.max(1, Math.round(e.len / mull));
          for (let i = 0; i < n; i++) {
            const s = (i * e.len) / n;
            ebox(finMat, e, s - 0.04, s + 0.04, 0, fin, z0, z1);
          }
        }
        if (band > 0)
          for (let z = z0 + storey; z < z1 - 0.3; z += storey)
            ebox(bandMat, e, 0, e.len, 0, fin * 0.8, z - band / 2, z + band / 2);
      }
    };
    // Punched windows storey by storey on edges passing filter.
    const punched = (ring, z0, storeys, storey, opts, filter = (e) => e.len > 2.5) => {
      for (const e of edgesOf(ring)) {
        if (!filter(e)) continue;
        for (let s = 0; s < storeys; s++) {
          const o = typeof opts === 'function' ? opts(s, e) : opts;
          if (o) kit.windowRow(B, e.a, e.b, z0 + s * storey, o);
        }
      }
    };
    // Distance from point to the nearest named road centreline (scene roads).
    const roadSegs = (names) => {
      const out = [];
      for (const r of ctx.scene.roads || []) {
        if (r.cls === 'footway' || (names && !names.includes(r.name))) continue;
        for (let i = 1; i < r.line.length; i++) out.push([r.line[i - 1], r.line[i]]);
      }
      return out;
    };
    // Nearest point on the road centrelines: [distance, x, y].
    const segNearest = (p, segs) => {
      let best = [Infinity, 0, 0];
      for (const [a, b] of segs) {
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          l = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l));
        const x = a[0] + t * dx,
          y = a[1] + t * dy,
          d = Math.hypot(p[0] - x, p[1] - y);
        if (d < best[0]) best = [d, x, y];
      }
      return best;
    };
    // Does edge e face a road: the nearest road point lies within maxD and in front of the
    // edge (within ~50 degrees of its outward normal)?
    const facesRoad = (e, segs, maxD = 22, cosMin = 0.64) => {
      const m = at(e, e.len / 2, 0);
      const [d, x, y] = segNearest(m, segs);
      if (!(d < maxD) || d < 1e-6) return false;
      return ((x - m[0]) * e.nx + (y - m[1]) * e.ny) / d > cosMin;
    };
    // ------------------------------------------------------------------------------
    const ring = ringOf('b56a88ab-9e6f-447a-99aa-04c5e48edf94');
    const stucco = kit.mat('#efe9dc', { roughness: 0.75 });
    const trim = kit.mat('#f6f2e8', { roughness: 0.7 });
    const brick = kit.mat('#6f5e4c', { roughness: 0.95 });
    const iron = kit.mat('#2b2e30', { roughness: 0.5, metalness: 0.5 });
    const door = kit.mat('#1f2a23', { roughness: 0.5 });
    // painted (blind) windows: grey panes with white glazing bars, flat on the wall
    const painted = kit.paintedMaterial(
      'leinster_gardens:painted_window',
      128,
      256,
      (c, w, h) => {
        c.fillStyle = '#f2eee4';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#4a4f53';
        c.fillRect(w * 0.08, h * 0.04, w * 0.84, h * 0.92);
        c.fillStyle = '#f2eee4';
        c.fillRect(w * 0.47, h * 0.04, w * 0.06, h * 0.92);
        for (const t of [0.35, 0.5, 0.65]) c.fillRect(w * 0.08, h * t, w * 0.84, h * 0.025);
      },
      { roughness: 0.8 },
    );
    const E = edgesOf(ring);
    const front = E.slice()
      .sort((p, q) => q.len - p.len)
      .filter((e) => e.nx > 0)[0]; // faces Leinster Gardens (east)
    const back = E.filter((e) => e.len > 5 && e !== front)[0];
    const ST = [4.0, 4.3, 3.6, 3.3, 3.0];
    const zs = [0];
    for (const h of ST) zs.push(zs[zs.length - 1] + h);
    const H = zs[zs.length - 1];
    // wall body: stucco to the street, brick to the cutting
    for (const e of E) {
      const m = e === front ? stucco : brick;
      B.quad(
        m,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], H + 1],
        [e.a[0], e.a[1], H + 1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    kit.cap(B, kit.mat('lead'), [[ring]], H + 1);
    const e = front;
    const hw = e.len / 2;
    // rusticated ground storey
    for (let z = 0.6; z < ST[0] - 0.3; z += 0.55) ebox(stucco, e, 0, e.len, 0, 0.05, z, z + 0.06);
    for (let hI = 0; hI < 2; hI++) {
      const s0 = hI * hw;
      // painted-on windows (flat panels with mouldings) per storey
      const win = (s, z, w, h, head) => {
        ebox(painted, e, s - w / 2, s + w / 2, 0.005, 0.02, z, z + h);
        ebox(trim, e, s - w / 2 - 0.12, s + w / 2 + 0.12, 0, 0.12, z - 0.12, z);
        for (const sg of [-1, 1])
          ebox(
            trim,
            e,
            s + sg * (w / 2 + 0.06) - 0.06,
            s + sg * (w / 2 + 0.06) + 0.06,
            0,
            0.08,
            z,
            z + h,
          );
        if (head === 'pediment') {
          ebox(trim, e, s - w / 2 - 0.25, s + w / 2 + 0.25, 0, 0.25, z + h, z + h + 0.18);
          const g = new THREE.CylinderGeometry(w * 0.7, w * 0.7, 0.22, 3, 1).rotateX(Math.PI / 2);
          g.scale(1, 0.3, 1);
          const c = at(e, s, 0.11);
          const M = new THREE.Matrix4()
            .makeRotationZ(e.ang)
            .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
          M.setPosition(c[0], c[1], z + h + 0.18 + w * 0.12);
          B.addGeometry(trim, g, M);
          g.dispose();
        } else if (head === 'lintel')
          ebox(trim, e, s - w / 2 - 0.15, s + w / 2 + 0.15, 0, 0.18, z + h, z + h + 0.16);
      };
      const doorS = s0 + (hI ? hw * 0.75 : hw * 0.25);
      const winS = s0 + (hI ? hw * 0.3 : hw * 0.7);
      ebox(door, e, doorS - 0.6, doorS + 0.6, 0.01, 0.06, 0.6, 3.2);
      win(winS, 1.2, 1.3, 2.2, 'none');
      // paired Doric porch columns with an entablature and balustraded top
      for (const ds of [-1.05, 1.05]) {
        const c = at(e, doorS + ds, 1.7);
        cyl(trim, c[0], c[1], 0.3, ST[0] - 0.7, 0.2, 0.17, 10);
        kit.box(B, trim, c[0], c[1], 0, 0.55, 0.55, 0.3, e.ang);
        kit.box(B, trim, c[0], c[1], ST[0] - 0.75, 0.5, 0.5, 0.12, e.ang);
      }
      ebox(trim, e, doorS - 1.45, doorS + 1.45, 0, 2.0, ST[0] - 0.65, ST[0] - 0.15);
      ebox(trim, e, doorS - 1.45, doorS + 1.45, 0, 2.0, 0, 0.3);
      kit.balustrade(B, trim, [at(e, doorS - 1.4, 1.9), at(e, doorS + 1.4, 1.9)], ST[0] - 0.15, {
        height: 0.9,
        spacing: 0.3,
      });
      for (let k = 1; k < ST.length; k++) {
        const wh = Math.min(ST[k] - 1.0, k === 1 ? 2.9 : ST[k] * 0.62);
        for (const t of [0.25, 0.75])
          win(
            s0 + hw * t,
            zs[k] + (k === 1 ? 0.35 : 0.6),
            k === 1 ? 1.25 : 1.1,
            wh,
            k === 1 ? 'pediment' : k === 2 ? 'lintel' : 'none',
          );
      }
    }
    // first-floor balcony across both fronts
    ebox(trim, e, 0, e.len, 0, 0.9, zs[1] - 0.2, zs[1] + 0.05);
    kit.balustrade(B, trim, [at(e, 0.1, 0.8), at(e, e.len - 0.1, 0.8)], zs[1] + 0.05, {
      height: 0.9,
      spacing: 0.3,
    });
    // cornices and parapet (party pilasters between the two "houses")
    for (const z of [zs[1] - 0.25, zs[4] - 0.2]) ebox(trim, e, 0, e.len, 0, 0.2, z, z + 0.25);
    ebox(trim, e, -0.1, e.len + 0.1, 0, 0.5, H - 0.55, H);
    ebox(trim, e, -0.1, e.len + 0.1, 0, 0.3, H, H + 1.0);
    for (const s of [0.15, hw, e.len - 0.15])
      ebox(trim, e, s - 0.15, s + 0.15, 0, 0.12, zs[1], H - 0.55);
    // rear: iron stays bracing the facade across the cutting
    if (back) {
      for (const z of [5, 10.5, 15.5]) {
        ebox(iron, back, 0.3, back.len - 0.3, 0, 0.35, z, z + 0.4);
        for (const s of [1.5, back.len / 2, back.len - 1.5]) {
          const p0 = at(back, s, 0.2),
            p1 = at(back, s, 3.0);
          const L = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const g = new THREE.BoxGeometry(Math.hypot(L, 3.5), 0.18, 0.25);
          const M = new THREE.Matrix4()
            .makeRotationZ(Math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
            .multiply(new THREE.Matrix4().makeRotationY(Math.atan2(3.5, L)));
          M.setPosition((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, z - 1.75);
          B.addGeometry(iron, g, M);
          g.dispose();
        }
      }
    }
    return B.toGroup('leinster_gardens_fake_houses');
  },
};
