// Sheldon Square, Paddington Central (Sidell Gibson, phase 1 from 2001): the curved,
// glass-clad One Sheldon Square beside the stepped lawn amphitheatre, the glass-and-steel
// 3 Sheldon Square, the small pavilion at 1a, and the two canal-side residential blocks
// (11 and 21 Sheldon Square, 219 flats in all).
export default {
  id: 'sheldon_square',
  name: 'Sheldon Square, Paddington Central',
  claims: [
    'c400f1e4-a59d-4701-af3b-8289ce8c6335',
    '2b278c4a-1f01-43b8-b43e-d84b38e608ef',
    '47fde65d-9868-4936-bed9-dd1206ba6e24',
    '687eb83b-e5d2-4113-b570-a82b2f08057b',
    '12838147-fdeb-45ec-a597-08c91bb28e1f',
  ],
  references: [
    {
      title: 'Paddington Waterside - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Waterside',
      used_for: 'Sheldon Square designed by Sidell Gibson; two large office blocks; 219 flats',
    },
    {
      title: 'Architecture Today - Paddington Central / Abundance',
      url: 'https://architecturetoday.co.uk/?p=256681',
      used_for:
        'One Sheldon Square: curved, glass-clad, ten-storey office block beside the amphitheatre, Sidell Gibson',
    },
    {
      title: 'Planted balconies will be added to one of the earliest offices - Building Design',
      url: 'https://www.bdonline.co.uk/news/morris-and-co-wins-approval-for-hanging-gardens-in-paddington/5113369.article',
      used_for:
        '3 Sheldon Square: 2001 glass-and-steel building by Sidell Gibson; nine levels of planted balconies approved on its front elevation',
    },
    {
      title: 'British Land buys 1 Sheldon Square - QuotedData',
      url: 'https://quoteddata.com/2015/04/british-land-buys-1-sheldon-square/',
      used_for: 'nearly 200,000 sq ft of offices over nine floors',
    },
    {
      title: 'Changes to Paddington Central Amphitheatre - This is Paddington',
      url: 'https://thisispaddington.com/article/changes-paddington-central-amphitheatre',
      used_for: 'amphitheatre built in phase 1, Sidell Gibson',
    },
  ],
  notes:
    'Heights: 1 Sheldon Square 10 storeys (~40 m), 3 Sheldon Square 10 storeys (~40 m), the residential blocks 13 storeys (~42 m), 1a a 4-storey pavilion. Overture heights are lower and were not used. The planted balconies of 3 Sheldon Square are shown as approved (green planters on the north-east face). Residential facade (brick/render with punched windows and balconies) is approximate.',
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
    const glass = kit.mat('#4f6573', { roughness: 0.08, metalness: 0.5 });
    const clear = kit.mat('#7590a0', { roughness: 0.06, metalness: 0.45 });
    const steel = kit.mat('#9ba2a6', { roughness: 0.35, metalness: 0.7 });
    const white = kit.mat('#e6e4de', { roughness: 0.55 });
    const brick = kit.mat('#a5765a', { roughness: 0.9 });
    const render = kit.mat('#ece8de', { roughness: 0.8 });
    const dark = kit.mat('dark_steel');
    const green = kit.mat('foliage');
    const roofM = kit.mat('#8d8c88');
    const office = (id, N, ST, opts = {}) => {
      const ring = ringOf(id);
      const H = 1.2 + N * ST;
      for (const e of edgesOf(ring)) {
        if (e.len < 0.2) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], 0],
          [e.b[0], e.b[1], 0],
          [e.b[0], e.b[1], H],
          [e.a[0], e.a[1], H],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        for (let z = 1.2 + ST; z < H; z += ST) ebox(steel, e, 0, e.len, 0, 0.35, z - 0.3, z + 0.12);
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let i = 0; i <= n; i++)
          ebox(steel, e, (i * e.len) / n - 0.05, (i * e.len) / n + 0.05, 0, 0.22, 1.2, H);
        if (e.len > 3) ebox(clear, e, 0.2, e.len - 0.2, 0.01, 0.06, 0.1, 1.2 + ST - 0.4);
        if (opts.planted && opts.planted(e))
          for (let k = 1; k <= 9; k++) {
            const z = 1.2 + k * ST;
            ebox(white, e, 0.5, e.len - 0.5, 0, 1.6, z - 0.1, z + 0.1);
            ebox(green, e, 0.8, e.len - 0.8, 1.0, 1.55, z + 0.1, z + 0.8);
          }
      }
      kit.cornice(B, white, ring, H, { height: 0.9, projection: 0.7 });
      kit.cap(B, roofM, [[ring]], H + 0.9);
      const f = kit.ringFrame(ring);
      prism(
        kit.mat('#a7a8a6'),
        rect(f.cx, f.cy, f.length * 0.4, f.width * 0.4, f.angle),
        H + 0.9,
        H + 4,
        roofM,
      );
      return ring;
    };
    office('c400f1e4-a59d-4701-af3b-8289ce8c6335', 10, 3.9);
    office('2b278c4a-1f01-43b8-b43e-d84b38e608ef', 10, 3.9, {
      planted: (e) => e.nx > 0.6 && e.len > 8,
    });
    // 1a: small curved glazed pavilion
    {
      const ring = ringOf('12838147-fdeb-45ec-a597-08c91bb28e1f');
      curtain(ring, 0, 14.4, {
        glass: clear,
        frame: steel,
        mull: 1.4,
        storey: 3.6,
        fin: 0.12,
        band: 0.3,
      });
      kit.cornice(B, white, ring, 14.4, { height: 0.6, projection: 0.8 });
      kit.cap(B, roofM, [[ring]], 15.0);
    }
    // canal-side residential blocks, 13 storeys
    for (const id of [
      '47fde65d-9868-4936-bed9-dd1206ba6e24',
      '687eb83b-e5d2-4113-b570-a82b2f08057b',
    ]) {
      const ring = ringOf(id);
      const ST = 3.15,
        N = 13,
        H = 1.5 + N * ST;
      for (const e of edgesOf(ring)) {
        if (e.len < 0.2) continue;
        const m = e.len > 12 ? brick : render;
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
        if (e.len > 3) ebox(clear, e, 0.3, e.len - 0.3, 0.01, 0.05, 0.2, 4.2);
      }
      punched(
        ring,
        1.5 + 3.15 + 0.9,
        N - 2,
        ST,
        (s, e) => ({
          bay: 2.6,
          width: 1.6,
          height: 2.0,
          glass,
          frame: dark,
          sill: white,
          head: 'none',
          bars: 0,
          depth: 0.15,
        }),
        (e) => e.len > 4,
      );
      // stacked glass balconies on the long faces
      for (const e of edgesOf(ring)) {
        if (e.len < 12) continue;
        for (let k = 2; k < N; k++)
          for (const t of [0.25, 0.75]) {
            const s = e.len * t,
              z = 1.5 + k * ST;
            ebox(white, e, s - 1.8, s + 1.8, 0, 1.4, z - 0.15, z);
            ebox(clear, e, s - 1.8, s + 1.8, 1.3, 1.4, z, z + 1.05);
          }
      }
      kit.cornice(B, white, ring, 4.4, { height: 0.35, projection: 0.25 });
      kit.cornice(B, white, ring, H - 0.6, { height: 0.6, projection: 0.4 });
      kit.cap(B, roofM, [[ring]], H);
    }
    return B.toGroup('sheldon_square');
  },
};
