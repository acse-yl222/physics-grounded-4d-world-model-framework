// The Point, 37 North Wharf Road, Paddington Basin (Farrells, 2000-03). The first
// building completed in the Paddington Basin regeneration: a 10-storey wedge-shaped office
// block inspired by a ship's prow, its two curved facades following the canal and
// clad in full-height glazing behind vertical metal fins.
export default {
  id: 'the_point_paddington',
  name: 'The Point, Paddington Basin',
  claims: ['c4ffe861-68ca-4c1f-a2c3-a4f5069f4e92'],
  references: [
    {
      title: 'The Point - Farrells',
      url: 'https://farrells.com/project/the-point/',
      used_for: '222,000 sq ft of offices over 10 storeys in a wedge shape',
    },
    {
      title: 'The Point, Paddington - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2000/point.html',
      used_for:
        "ship's-prow form following the canal curve; full-height glazing behind vertical metal fins; 2000-2003",
    },
    {
      title: 'Paddington Basin - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Basin',
      used_for: 'first building completed in the basin, Terry Farrell masterplan',
    },
  ],
  notes:
    'Height from 10 office storeys at ~3.7 m (Overture gives 28 m, too low for 10 office floors). Fin spacing, the recessed top storey and the roof plant are approximate; the flat (west) end is treated as a solid stone-clad core.',
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
    const ring = ringOf('c4ffe861-68ca-4c1f-a2c3-a4f5069f4e92');
    const glass = kit.mat('#4a6170', { roughness: 0.1, metalness: 0.45 });
    const fin = kit.mat('#c9ccce', { roughness: 0.35, metalness: 0.6 });
    const core = kit.mat('#d3cdbf', { roughness: 0.8 });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8d8c88');
    const ST = 3.7,
      N = 10,
      H = N * ST;
    const E = edgesOf(ring);
    // Short straight edges at the east (Harrow Road / North Wharf Road) end read as cores.
    const isCore = (e) => e.len < 9 && Math.abs(e.ux) < 0.45;
    // ground floor: recessed glazing under the overhang
    const inner = kit.offsetRing(ring, -1.2);
    for (const e of edgesOf(inner)) {
      if (e.len < 0.3) continue;
      B.quad(
        dark,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], 4.6],
        [e.a[0], e.a[1], 4.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      ebox(glass, e, 0.2, e.len - 0.2, 0.01, 0.04, 0.2, 4.4);
    }
    kit.cap(B, core, [[ring]], 4.6, { down: true });
    // upper storeys
    for (const e of E) {
      if (e.len < 0.3) continue;
      const m = isCore(e) ? core : glass;
      B.quad(
        m,
        [e.a[0], e.a[1], 4.6],
        [e.b[0], e.b[1], 4.6],
        [e.b[0], e.b[1], H - ST],
        [e.a[0], e.a[1], H - ST],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      if (isCore(e)) continue;
      const n = Math.max(1, Math.round(e.len / 0.9));
      for (let i = 0; i < n; i++) {
        const s = ((i + 0.5) * e.len) / n;
        ebox(fin, e, s - 0.04, s + 0.04, 0.05, 0.5, 4.6, H - ST);
      }
      for (let k = 1; k < N - 1; k++)
        ebox(dark, e, 0, e.len, 0, 0.15, 4.6 + k * ST - 0.3, 4.6 + k * ST);
    }
    kit.cornice(B, fin, ring, 4.6, { height: 0.5, projection: 0.55 });
    // recessed top storey with a projecting roof blade
    const top = kit.offsetRing(ring, -2.2);
    kit.cap(B, roofM, [[ring, top.slice().reverse()]], H - ST);
    for (const e of edgesOf(top)) {
      if (e.len < 0.3) continue;
      B.quad(
        glass,
        [e.a[0], e.a[1], H - ST],
        [e.b[0], e.b[1], H - ST],
        [e.b[0], e.b[1], H],
        [e.a[0], e.a[1], H],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const n = Math.max(1, Math.round(e.len / 1.8));
      for (let i = 0; i < n; i++)
        ebox(
          dark,
          e,
          ((i + 0.5) * e.len) / n - 0.05,
          ((i + 0.5) * e.len) / n + 0.05,
          0,
          0.1,
          H - ST,
          H,
        );
    }
    kit.balustrade(B, fin, [...ring, ring[0]], H - ST, { height: 1.1, spacing: 1.5 });
    const blade = kit.offsetRing(ring, 0.6);
    prism(fin, blade, H, H + 0.45, roofM);
    // roof plant enclosure
    const f = kit.ringFrame(ring);
    const plant = rect(f.cx, f.cy, f.length * 0.35, f.width * 0.35, f.angle);
    prism(kit.mat('#a6a7a4'), plant, H + 0.45, H + 4.0, roofM);
    for (const e of edgesOf(plant)) {
      const n = Math.round(e.len / 0.6);
      for (let i = 1; i < n; i++)
        ebox(dark, e, (i * e.len) / n - 0.03, (i * e.len) / n + 0.03, 0, 0.1, H + 0.6, H + 3.8);
    }
    return B.toGroup('the_point_paddington');
  },
};
