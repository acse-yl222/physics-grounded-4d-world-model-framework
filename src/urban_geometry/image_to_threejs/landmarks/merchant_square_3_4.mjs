// 3 and 4 Merchant Square, Paddington Basin: the two residential blocks at the head of
// the basin by Harbet Road. 3 Merchant Square (Robin Partington Architects, 2014) is a
// 21-storey canal-side block of 201 flats with double-height stone bays over layers of
// bronze cladding and glazing and recessed balconies; 4 Merchant Square (Tryfon
// Kalyvides Partnership, 2013) is a 16-storey block of 196 flats on a lower podium,
// clad in Carea mineral panels in a chequerboard pattern.
export default {
  id: 'merchant_square_3_4',
  name: '3 and 4 Merchant Square',
  claims: ['b4b7ddfd-e745-4403-8cc1-ae3c45662e91', 'e53c4a1b-8645-4c10-9de9-194848d44da5'],
  references: [
    {
      title: '3 Merchant Square, Paddington, London - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2010/3merchantsquare.html',
      used_for:
        'Robin Partington Architects, 2014; 21 storeys, 201 flats; double-height stone bays with bronze cladding and glazing; recessed balconies, Juliet balconies and winter gardens',
    },
    {
      title: 'Paddington Basin - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Basin',
      used_for: '4 Merchant Square: 16 storeys, 196 flats, Tryfon Kalyvides Partnership, 2013',
    },
    {
      title: 'Carea Cladding holds the key to Merchant Square Development - Specification Online',
      url: 'https://www.specificationonline.co.uk/articles/2016-03-22/general/carea-cladding-holds-the-key-to-merchant-square-development',
      used_for:
        'glass, curtain walling and Carea mineral rainscreen panels (Acantha and Artema) forming a chequerboard pattern',
    },
    {
      title: 'Mace to build next stage of Paddington Basin scheme - The Construction Index',
      url: 'https://www.theconstructionindex.co.uk/news/view/mace-to-build-next-stage-of-paddington-basin-scheme',
      used_for: 'Mace contract, 159 private + 42 affordable flats at 3 Merchant Square',
    },
  ],
  notes:
    '3 Merchant Square height set from 21 storeys at ~3.1 m (66 m) rather than the Overture 50 m; 4 Merchant Square tower height (50 m) from the Overture part, podium 14.5 m. Bay rhythm, balcony positions and the chequerboard colours are approximate.',
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
    const stone = kit.mat('#ddd4c0', { roughness: 0.75 });
    const bronze = kit.mat('#7a5d3e', { roughness: 0.45, metalness: 0.6 });
    const glass = kit.mat('#3e505d', { roughness: 0.1, metalness: 0.4 });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8a8984');

    // --- 3 Merchant Square -------------------------------------------------------
    {
      const ring = ringOf('b4b7ddfd-e745-4403-8cc1-ae3c45662e91');
      const ST = 3.1,
        N = 21,
        H = N * ST + 1.0;
      for (const e of edgesOf(ring)) {
        if (e.len < 0.3) continue;
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
        if (e.len < 3) {
          ebox(stone, e, 0, e.len, 0, 0.3, 0, H);
          continue;
        }
        // stone frame: piers every ~6 m, bands every two storeys
        const n = Math.max(1, Math.round(e.len / 6.2));
        for (let i = 0; i <= n; i++) {
          const s = (i * e.len) / n;
          ebox(stone, e, s - 0.45, s + 0.45, 0, 0.7, 0, H);
          if (i < n) {
            // bronze mullions and single-storey bronze transoms inside each bay
            for (const t of [0.33, 0.67])
              ebox(
                bronze,
                e,
                s + (t * e.len) / n - 0.05,
                s + (t * e.len) / n + 0.05,
                0.1,
                0.3,
                4.5,
                H - 1.5,
              );
            // recessed balconies in alternating bays
            if ((i + e.k) % 3 === 0)
              for (let k = 2; k < N - 1; k += 2)
                ebox(
                  dark,
                  e,
                  s + 0.5,
                  s + e.len / n - 0.5,
                  -0.4,
                  -0.05,
                  1.2 + k * ST,
                  1.2 + k * ST + 2.4,
                );
          }
        }
        for (let k = 0; k <= N; k += 2)
          ebox(stone, e, 0, e.len, 0, 0.65, 1.0 + k * ST - 0.35, 1.0 + k * ST + 0.35);
        for (let k = 1; k < N; k += 2)
          ebox(bronze, e, 0, e.len, 0.05, 0.3, 1.0 + k * ST - 0.12, 1.0 + k * ST + 0.12);
        // double-height ground-floor glazing behind the piers
        ebox(dark, e, 0.6, e.len - 0.6, 0.01, 0.04, 0, 0.3);
      }
      kit.cap(B, roofM, [[ring]], H);
      kit.cornice(B, stone, ring, H - 0.4, { height: 0.8, projection: 0.5 });
      const f = kit.ringFrame(ring);
      prism(stone, rect(f.cx, f.cy, f.length * 0.5, f.width * 0.45, f.angle), H, H + 3.5, roofM);
    }

    // --- 4 Merchant Square -------------------------------------------------------
    {
      const b = ctx.byId['e53c4a1b-8645-4c10-9de9-194848d44da5'];
      const ring = ccw(b.polys[0][0]);
      const tower = ccw(b.parts[0].polys[0][0]);
      const PH = 14.5,
        H = 50;
      const chequer = kit.paintedMaterial(
        'merchant_square_4:chequer',
        512,
        256,
        (c, w, h) => {
          const cw = w / 4,
            ch = h / 2;
          for (let i = 0; i < 4; i++)
            for (let j = 0; j < 2; j++) {
              c.fillStyle = (i + j) % 2 ? '#e9e5dc' : '#c4bdb0';
              c.fillRect(i * cw, j * ch, cw, ch);
              c.fillStyle = '#2f3d47';
              const ww = (i + j) % 2 ? cw * 0.42 : cw * 0.62;
              c.fillRect(i * cw + (cw - ww) / 2, j * ch + ch * 0.18, ww, ch * 0.62);
              c.fillStyle = 'rgba(255,255,255,0.12)';
              c.fillRect(i * cw + (cw - ww) / 2, j * ch + ch * 0.18, ww * 0.3, ch * 0.62);
            }
        },
        { vertexColors: true },
      );
      kit.walls(B, chequer, [[ring]], 0, PH, { bay: 3.0, storey: 3.0 });
      kit.cap(B, roofM, [[ring]], PH);
      kit.walls(B, chequer, [[tower]], PH, H, { bay: 3.0, storey: 3.0, uvBase: 0 });
      kit.cap(B, roofM, [[tower]], H);
      kit.cornice(B, stone, tower, H - 0.5, { height: 0.5, projection: 0.3 });
      kit.cornice(B, stone, ring, PH - 0.4, { height: 0.4, projection: 0.3 });
      // glazed corners and shopfront at canal level
      for (const e of edgesOf(ring)) {
        if (e.len < 4) continue;
        ebox(glass, e, 0.5, e.len - 0.5, 0.01, 0.06, 0.2, 4.0);
        ebox(dark, e, 0, e.len, 0, 0.3, 4.0, 4.3);
      }
      // projecting balconies on the tower
      for (const e of edgesOf(tower)) {
        if (e.len < 8) continue;
        for (let k = 0; k < 11; k++) {
          const z = PH + 3 + k * 3.0;
          const s = e.len * (k % 2 ? 0.3 : 0.65);
          ebox(glass, e, s - 2, s + 2, 0, 1.3, z, z + 1.05);
          ebox(stone, e, s - 2, s + 2, 0, 1.35, z - 0.2, z);
        }
      }
      prism(kit.mat('#a5a4a0'), rect(2036, 1407.5, 9, 4, 0.27), H, H + 3, roofM);
    }
    return B.toGroup('merchant_square_3_4');
  },
};
