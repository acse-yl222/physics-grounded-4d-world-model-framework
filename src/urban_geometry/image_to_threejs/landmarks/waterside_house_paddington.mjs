// Waterside House, 35 North Wharf Road, Paddington Basin (Richard Rogers Partnership,
// completed 2003-04): the Marks & Spencer headquarters. One highly glazed office building
// of two triangular wings joined by a ground-floor entrance hall, with two full-height
// atria either side of a canal inlet that is crossed by Heatherwick Studio's Rolling
// Bridge (2004), which curls up into an octagon.
export default {
  id: 'waterside_house_paddington',
  name: 'Waterside House (Marks & Spencer HQ) and the Rolling Bridge',
  claims: ['ec3b52b5-3b94-47a5-9c3d-ce83d507f1c6'],
  references: [
    {
      title: 'Waterside House - Buildington',
      url: 'https://www.buildington.co.uk/buildings/1847/england/london-w2/35-north-wharf-road/waterside-house',
      used_for: 'Richard Rogers Partnership; two interlinking wings; M&S corporate headquarters',
    },
    {
      title: 'Waterside House, M&S Paddington Basin - e-architect',
      url: 'https://e-architect.com/london/waterside-house-paddington',
      used_for: '220,000 sq ft of offices over 11 floors',
    },
    {
      title: 'Waterside - Paddington, London, UK - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2000/waterside.html',
      used_for:
        'two triangular wings joined by the entrance hall and linked floor plates; two full-height atria; canal inlet between the wings spanned by the Heatherwick curling bridge',
    },
    {
      title: 'Paddington Basin - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Basin',
      used_for: 'Rolling Bridge by Heatherwick Studio curling into an octagon',
    },
  ],
  notes:
    'Height from 11 office storeys (~41 m; Overture 26 m); a 13-storey figure also appears in one source. Facade detailing (mullion pitch, floor-edge bands, roof plant) is generic. The Rolling Bridge is shown curled up on the east bank of the inlet; its exact position and colours are approximate.',
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
    const ring = ringOf('ec3b52b5-3b94-47a5-9c3d-ce83d507f1c6');
    const glass = kit.mat('#557080', { roughness: 0.08, metalness: 0.5 });
    const atrium = kit.mat('#8fa9b5', { roughness: 0.06, metalness: 0.4 });
    const frame = kit.mat('#b9bec2', { roughness: 0.4, metalness: 0.6 });
    const steel = kit.mat('#8d9499', { roughness: 0.4, metalness: 0.7 });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8d8c88');
    const ST = 3.6,
      N = 11,
      H = 1.4 + N * ST;
    // Inlet-facing edges (between x 1770 and 1790) are the glazed atria.
    const inInlet = (e) => {
      const m = at(e, e.len / 2);
      return m[0] > 1771 && m[0] < 1790 && m[1] > 1328 && m[1] < 1356;
    };
    curtain(ring, 0, H, {
      glass,
      frame,
      mull: 1.5,
      storey: ST,
      fin: 0.18,
      band: 0.45,
      bandMat: frame,
      edgeFilter: (e) => !inInlet(e),
    });
    for (const e of edgesOf(ring)) {
      if (!inInlet(e) || e.len < 0.3) continue;
      B.quad(
        atrium,
        [e.a[0], e.a[1], 0],
        [e.b[0], e.b[1], 0],
        [e.b[0], e.b[1], H],
        [e.a[0], e.a[1], H],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const n = Math.max(1, Math.round(e.len / 2.4));
      for (let i = 0; i <= n; i++)
        ebox(steel, e, (i * e.len) / n - 0.1, (i * e.len) / n + 0.1, 0, 0.35, 0, H);
      for (let z = 4.8; z < H; z += 2 * ST) ebox(steel, e, 0, e.len, 0, 0.25, z, z + 0.15);
    }
    // ground floor: dark glazed base with a stone-coloured plinth
    for (const e of edgesOf(ring))
      if (e.len > 2 && !inInlet(e)) ebox(dark, e, 0.3, e.len - 0.3, 0, 0.22, 0, 0.5);
    kit.cornice(B, frame, ring, H, { height: 0.9, projection: 0.6 });
    kit.cap(B, roofM, [[ring]], H + 0.9);
    // rooftop plant on each wing
    for (const [cx, cy, a] of [
      [1752, 1352, -0.52],
      [1802, 1366, 1.05],
    ]) {
      const p = rect(cx, cy, 18, 7, a);
      prism(kit.mat('#a7a8a6'), p, H + 0.9, H + 4.3, roofM);
      for (const e of edgesOf(p)) {
        const n = Math.round(e.len / 0.7);
        for (let i = 1; i < n; i++)
          ebox(dark, e, (i * e.len) / n - 0.03, (i * e.len) / n + 0.03, 0, 0.08, H + 1.3, H + 4.0);
      }
    }
    // Heatherwick Rolling Bridge, curled into an octagon on the east bank of the inlet
    {
      const ang = Math.atan2(1331.0 - 1329.0, 1788.9 - 1779.5);
      const seg = 1.5,
        Rr = seg / (2 * Math.tan(Math.PI / 8));
      const cx = 1789.6 - Math.cos(ang) * 0.2,
        cy = 1332.0;
      const deck = kit.mat('#6d5a44', { roughness: 0.8 });
      for (let i = 0; i < 8; i++) {
        const th = (i * Math.PI) / 4; // octagon in the vertical plane along the bridge axis
        const u = Math.sin(th) * Rr,
          z = Rr - Math.cos(th) * Rr + 0.6;
        const x = cx + Math.cos(ang) * u,
          y = cy + Math.sin(ang) * u;
        const g = new THREE.BoxGeometry(seg, 1.4, 0.18);
        const M = new THREE.Matrix4()
          .makeRotationZ(ang)
          .multiply(new THREE.Matrix4().makeRotationY(-th));
        M.setPosition(x, y, z);
        B.addGeometry(deck, g, M);
        g.dispose();
        // handrail posts (the hydraulic rams sit in the balustrade)
        for (const side of [-0.7, 0.7]) {
          const g2 = new THREE.BoxGeometry(0.08, 0.08, 1.0);
          const M2 = new THREE.Matrix4()
            .makeRotationZ(ang)
            .multiply(new THREE.Matrix4().makeRotationY(-th));
          const off = new THREE.Vector3(0, side, 0.55).applyMatrix4(
            new THREE.Matrix4().makeRotationZ(ang).multiply(new THREE.Matrix4().makeRotationY(-th)),
          );
          M2.setPosition(x + off.x, y + off.y, z + off.z);
          B.addGeometry(steel, g2, M2);
          g2.dispose();
        }
      }
    }
    return B.toGroup('waterside_house_paddington');
  },
};
