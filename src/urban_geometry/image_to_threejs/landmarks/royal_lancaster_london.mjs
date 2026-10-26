// Royal Lancaster London, Lancaster Terrace (Richard Seifert; built as offices, opened as
// a 411-room hotel in 1967). A slender 18-storey slab on a three-storey podium over
// Lancaster Gate station, facing Kensington Gardens / Hyde Park across Bayswater Road.
// The 2017 renovation added an 8 m high glazed entrance facade (Studio Proof) and a new
// stone podium frontage (Eric Parry Architects).
export default {
  id: 'royal_lancaster_london',
  name: 'Royal Lancaster London',
  claims: ['0fadde72-f23f-49ee-bcb2-fa013415d097', 'ec3aedfe-960c-4457-a2ea-5aa77fb2cc81'],
  references: [
    {
      title: 'Royal Lancaster Hotel - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Lancaster_Hotel',
      used_for: 'opened 1 August 1967, 411 rooms on 18 floors',
    },
    {
      title: 'Our History - Royal Lancaster London',
      url: 'https://www.royallancaster.com/?p=1766',
      used_for: 'tower designed by Richard Seifert, originally intended as offices',
    },
    {
      title: 'Royal Lancaster Hotel - Eric Parry Architects',
      url: 'https://ericparryarchitects.co.uk/projects/royal-lancaster-hotel/',
      used_for: '1980s glass extensions removed, podium streamlined with a new stone facade',
    },
    {
      title: 'Royal Lancaster London unveils £80 million renovation - eHotelier',
      url: 'https://insights.ehotelier.com/properties/2017/10/11/royal-lancaster-london-unveils-80-million-renovation/',
      used_for: '8 m high glazed facade revealing a double-height reception',
    },
    {
      title: 'Royal Lancaster London to reopen in autumn - Business Traveller',
      url: 'https://www.businesstraveller.com/news/2017/03/21/royal-lancaster-london-reopen-autumn/',
      used_for: 'exterior based on a series of vertical strata',
    },
  ],
  notes:
    'Tower facade is a grid of slim vertical precast mullions and storey spandrel bands (typical Seifert treatment, approximate). Roof plant/crown height and the podium openings are estimated; podium height kept at the Overture 10.4 m.',
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
    const conc = kit.mat('#d9d6cd', { roughness: 0.8 });
    const spand = kit.mat('#bdb9af', { roughness: 0.85 });
    const stone = kit.mat('#ddd3bd', { roughness: 0.8 });
    const glass = kit.mat('#3e4f5b', { roughness: 0.12, metalness: 0.35 });
    const lobby = kit.mat('#5d5442', { roughness: 0.15, metalness: 0.3, emissive: '#2a1e0c' });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8a8984');

    const tower = ringOf('0fadde72-f23f-49ee-bcb2-fa013415d097');
    const podium = ringOf('ec3aedfe-960c-4457-a2ea-5aa77fb2cc81');
    const PH = 10.4;
    const TOPW = 61.2,
      H = 64.8;
    const ST = (TOPW - PH - 0.8) / 18;

    // --- podium: stone frontage, 8 m glazed entrance, upper storey windows ---------
    const roads = roadSegs([
      'Lancaster Terrace',
      'Bayswater Road',
      'Westbourne Street',
      'Lancaster Gate',
    ]);
    for (const e of edgesOf(podium)) {
      if (e.len < 0.2) continue;
      B.quad(
        stone,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], PH],
        [e.a[0], e.a[1], PH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      if (e.len < 4) continue;
      const front = facesRoad(e, roads, 30);
      // ground storey: glazed bays between stone piers
      const n = Math.max(1, Math.round(e.len / 4.2));
      for (let i = 0; i < n; i++) {
        const s0 = (i * e.len) / n + 0.45,
          s1 = ((i + 1) * e.len) / n - 0.45;
        ebox(front ? lobby : glass, e, s0, s1, 0.02, 0.06, 0.3, front ? 7.6 : 4.2);
        ebox(dark, e, s0, s1, 0.02, 0.12, front ? 7.6 : 4.2, (front ? 7.6 : 4.2) + 0.12);
        if (front) ebox(dark, e, (s0 + s1) / 2 - 0.05, (s0 + s1) / 2 + 0.05, 0.02, 0.12, 0.3, 7.6);
      }
      for (let i = 0; i <= n; i++)
        ebox(stone, e, (i * e.len) / n - 0.45, (i * e.len) / n + 0.45, 0, 0.35, 0, PH - 1.0);
      if (!front)
        kit.windowRow(B, e.a, e.b, 5.4, {
          bay: 4.2,
          width: 2.6,
          height: 1.6,
          glass,
          frame: dark,
          sill: stone,
          bars: 0,
          head: 'none',
        });
    }
    kit.cornice(B, stone, podium, PH - 1.0, { height: 1.0, projection: 0.45, steps: 2 });
    kit.cap(B, roofM, [[podium]], PH);
    // canopy over the main entrance on Lancaster Terrace (east side)
    {
      const e = edgesOf(podium)
        .filter((e) => e.len > 15 && e.nx > 0.5)
        .sort((p, q) => q.len - p.len)[0];
      if (e) {
        ebox(dark, e, e.len * 0.3, e.len * 0.7, 0, 4.5, 4.6, 4.9);
        for (const s of [e.len * 0.32, e.len * 0.68])
          ebox(dark, e, s - 0.12, s + 0.12, 4.2, 4.45, 0, 4.6);
      }
    }

    // --- tower: 18 storeys of glazing between precast mullions and spandrels -----
    const T = edgesOf(tower);
    for (const e of T) {
      B.quad(
        glass,
        [e.a[0], e.a[1], PH],
        [e.b[0], e.b[1], PH],
        [e.b[0], e.b[1], TOPW],
        [e.a[0], e.a[1], TOPW],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const long = e.len > 30;
      const pitch = long ? 1.62 : 1.55;
      const n = Math.round(e.len / pitch);
      for (let i = 0; i <= n; i++) {
        const s = (i * e.len) / n;
        const corner = i === 0 || i === n;
        ebox(
          conc,
          e,
          s - (corner ? 0.35 : 0.11),
          s + (corner ? 0.35 : 0.11),
          0,
          corner ? 0.4 : 0.32,
          PH,
          TOPW,
        );
      }
      for (let k = 0; k <= 18; k++) {
        const z = PH + 0.4 + k * ST;
        ebox(spand, e, 0, e.len, 0.02, 0.26, z - 0.55, z + 0.25);
      }
    }
    // base transfer band and top crown
    kit.cornice(B, conc, tower, PH, { height: 0.8, projection: 0.3 });
    kit.cornice(B, conc, tower, TOPW, { height: 1.0, projection: 0.35 });
    kit.cap(B, roofM, [[tower]], TOPW + 1.0);
    const tf = kit.ringFrame(tower);
    const inner = rect(tf.cx, tf.cy, tf.length - 10, tf.width - 4, tf.angle);
    prism(conc, inner, TOPW + 1.0, H, roofM);
    kit.cornice(B, spand, inner, H - 0.6, { height: 0.6, projection: 0.15 });
    // louvred plant bands on the crown
    for (const e of edgesOf(inner)) ebox(dark, e, 1, e.len - 1, 0, 0.08, TOPW + 1.8, H - 1.0);
    kit.box(
      B,
      roofM,
      tf.cx + Math.cos(tf.angle) * 12,
      tf.cy + Math.sin(tf.angle) * 12,
      H,
      4,
      4,
      1.8,
      tf.angle,
    );

    return B.toGroup('royal_lancaster_london');
  },
};
