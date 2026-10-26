// 5 Merchant Square, Paddington Basin (formerly "Carmine"; Mossessian & Partners,
// c. 2010-12). A 14-storey office building of three contrasting triangular elements: the
// corporate box is pierced by a red shard - the central triangle, a 15-storey atrium clad
// in red screen-printed glass frit - which bursts through the side and the top.
export default {
  id: 'five_merchant_square',
  name: '5 Merchant Square',
  claims: ['02705216-4086-4199-9ae6-e66c568a6456'],
  references: [
    {
      title: '5 Merchant Square - Mossessian',
      url: 'https://www.mossessian.com/projects/5-merchant-square/',
      used_for:
        'three contrasting triangular elements; red shard bursting through the side and top; suspended aluminium-profile facade',
    },
    {
      title: 'Paddington Basin - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Basin',
      used_for:
        '14-storey, 255,000 sq ft office block (formerly Carmine) by Mossessian and Partners',
    },
    {
      title: 'European Land by Mossessian Partners - OnOffice',
      url: 'https://www.onofficemagazine.com/architecture/european-land-by-mossessian-partners',
      used_for:
        '15-storey atrium covered in red screen-printed glass frit panels; 14 floors including an executive penthouse',
    },
    {
      title: 'Administrative Building 5 Merchant Square - archiweb',
      url: 'https://www.archiweb.cz/en/b/administrativna-budova-5-merchant-square',
      used_for: 'completion date and triangular-prism massing',
    },
  ],
  notes:
    'Height from 14 office storeys (~54 m to the main roof; the Overture 25 m is too low). The split of the footprint into the three triangles, the shard outline and its sloping top are reconstructed from descriptions; frit pattern drawn procedurally.',
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
    const ring = ringOf('02705216-4086-4199-9ae6-e66c568a6456');
    const glassA = kit.mat('#4f6573', { roughness: 0.08, metalness: 0.5 });
    const glassB = kit.mat('#7f949f', { roughness: 0.1, metalness: 0.4 });
    const alu = kit.mat('#d6d9db', { roughness: 0.35, metalness: 0.6 });
    const red = kit.paintedMaterial(
      'five_merchant_square:red_frit',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#a3141c';
        c.fillRect(0, 0, w, h);
        for (let y = 0; y < h; y += 8)
          for (let x = (y / 8) % 2 ? 4 : 0; x < w; x += 8) {
            c.fillStyle = 'rgba(255,90,90,0.35)';
            c.fillRect(x, y, 4, 4);
          }
        c.fillStyle = 'rgba(40,0,0,0.35)';
        for (let y = 0; y < h; y += 64) c.fillRect(0, y, w, 4);
      },
      { roughness: 0.2, metalness: 0.3 },
    );
    const roofM = kit.mat('#8d8c88');
    const dark = kit.mat('dark_steel');
    const ST = 3.75,
      N = 14,
      H = 1.5 + N * ST;

    // Body: two grey triangles either side of the shard, horizontal aluminium profiles.
    let idx = 0;
    for (const e of edgesOf(ring)) {
      if (e.len < 0.3) continue;
      const m = idx++ % 2 ? glassA : glassB;
      B.quad(
        m,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], H],
        [e.a[0], e.a[1], H],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      for (let z = 1.5 + ST; z < H - 0.5; z += ST)
        ebox(alu, e, 0, e.len, 0, 0.35, z - 0.35, z + 0.1);
      for (let z = 1.5 + ST * 1.5; z < H - 0.5; z += ST)
        ebox(alu, e, 0, e.len, 0, 0.18, z - 0.06, z + 0.06);
      const n = Math.max(1, Math.round(e.len / 3));
      for (let i = 0; i <= n; i++)
        ebox(alu, e, (i * e.len) / n - 0.06, (i * e.len) / n + 0.06, 0, 0.25, 0, H);
      ebox(dark, e, 0.4, e.len - 0.4, 0, 0.05, 0.2, 1.5 + ST - 0.4);
    }
    kit.cap(B, roofM, [[ring]], H);
    kit.cornice(B, alu, ring, H - 0.3, { height: 0.6, projection: 0.4 });

    // Red shard: central triangle, proud of the north-east (diagonal) face and rising
    // above the roof with a sloping top.
    const P = [
      [1846.0, 1378.0, H + 2],
      [1892.0, 1372.0, H + 5.5],
      [1873.5, 1402.5, H + 9],
    ];
    // Push the outer corner a little beyond the diagonal facade.
    P[2][0] += 3.0;
    P[2][1] += 2.5;
    const tri = P.map(([x, y]) => [x, y]);
    const ccwTri = kit.ringArea(tri) > 0 ? [0, 1, 2] : [0, 2, 1];
    const T = ccwTri.map((i) => P[i]);
    for (let k = 0; k < 3; k++) {
      const a = T[k],
        b = T[(k + 1) % 3];
      B.add(
        red,
        [
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], b[2]],
          [a[0], a[1], a[2]],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    B.add(
      red,
      T.map((p) => [p[0], p[1], p[2]]),
      [
        [0, 0],
        [1, 0],
        [0, 1],
      ],
      [0, 1, 2],
    );
    // shard edge fins
    for (let k = 0; k < 3; k++) {
      const a = T[k];
      kit.box(B, alu, a[0], a[1], 0, 0.5, 0.5, a[2], 0);
    }
    return B.toGroup('five_merchant_square');
  },
};
