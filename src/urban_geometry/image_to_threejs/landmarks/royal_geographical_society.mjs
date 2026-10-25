// Royal Geographical Society, Lowther Lodge, Kensington Gore at Exhibition Road
// (Richard Norman Shaw, 1874-75, for William and Alice Lowther; lecture-hall extension
// 1928-30 by G. L. Kennedy and F. B. Nightingale; Exhibition Road pavilion 2004).
// One of the earliest and most influential Queen Anne Revival houses: red brick with
// gauged and rubbed brick dressings, white sash windows, steep tiled roofs with shaped
// gables and pediments, and very tall fluted brick chimney stacks.
export default {
  id: 'royal_geographical_society',
  name: 'Royal Geographical Society (Lowther Lodge)',
  claims: ['3a4b3304-873e-4e63-8bd0-8a65761eb461'],
  references: [
    {
      title: 'Royal Geographical Society - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101217774-royal-geographical-society-knightsbridge-and-belgravia-ward',
      used_for:
        '1874-5 by Norman Shaw for the Lowthers, 1928-30 extension; red brick with gauged and rubbed dressings, tile roofs, tall fluted brick stacks',
    },
    {
      title: '1875 - Lowther Lodge, Kensington, London - Archiseek',
      url: 'https://www.archiseek.com/1875-lowther-lodge-kensington-london/',
      used_for: 'early Queen Anne work, gables and pediments',
    },
    {
      title: 'Royal Geographical Society - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Geographical_Society',
      used_for: 'Lowther Lodge as RGS headquarters, 1928-30 lecture room and 2004 extension',
    },
    {
      title: 'Richard Norman Shaw - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Richard_Norman_Shaw',
      used_for: 'Shaw Queen Anne style context',
    },
  ],
  notes:
    'The whole footprint (house plus later extensions) is treated in the Lodge idiom: eaves 11.5 m with a 6 m tiled roof slope ' +
    'following the simplified outline (data height 15.7 m), shaped gables placed procedurally on longer edges and tall stacks. ' +
    'The 1928-30 and 2004 additions are not differentiated; the Livingstone and Shackleton statues are not modelled.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const BRICK = '#a5543c';
    const brick = kit.mat(BRICK),
      slate = kit.mat('#7e4636'),
      white = kit.mat('#ece8de'),
      stoneMat = kit.mat('#d9cdb2');
    const facade = kit.paintedMaterial('royal_geographical_society:bay', 512, 256, (c, w, h) => {
      // 4 bays x 2 storeys (3.4 m storeys): white small-paned sashes, rubbed brick heads, string courses.
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(0,0,0,0.07)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      const bw = w / 4,
        sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        c.fillStyle = '#c47a5e';
        c.fillRect(0, y0 + sh - 10, w, 6); // string course
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw / 2;
          c.fillStyle = '#c47a5e';
          c.fillRect(x - 30, y0 + 22, 60, 10); // gauged brick head
          c.fillStyle = '#f2efe6';
          c.fillRect(x - 26, y0 + 32, 52, 76);
          c.fillStyle = '#26303a';
          for (let i = 0; i < 3; i++)
            for (let j = 0; j < 4; j++) c.fillRect(x - 23 + i * 16, y0 + 35 + j * 18, 14, 16);
          c.fillStyle = '#e8e2d6';
          c.fillRect(x - 30, y0 + 108, 60, 5); // sill
        }
      }
    });
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    // Douglas-Peucker simplification of a closed ring.
    const simplify = (ring, tol) => {
      const dp = (pts) => {
        if (pts.length < 3) return pts;
        const [a, b] = [pts[0], pts[pts.length - 1]];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1e-9;
        let im = 0,
          dm = 0;
        for (let k = 1; k < pts.length - 1; k++) {
          const d =
            Math.abs((b[0] - a[0]) * (a[1] - pts[k][1]) - (a[0] - pts[k][0]) * (b[1] - a[1])) / L;
          if (d > dm) ((dm = d), (im = k));
        }
        if (dm <= tol) return [a, b];
        return [...dp(pts.slice(0, im + 1)).slice(0, -1), ...dp(pts.slice(im))];
      };
      // split at the vertex farthest from the first
      let far = 0,
        fd = 0;
      for (let k = 1; k < ring.length; k++) {
        const d = Math.hypot(ring[k][0] - ring[0][0], ring[k][1] - ring[0][1]);
        if (d > fd) ((fd = d), (far = k));
      }
      const A = dp(ring.slice(0, far + 1)),
        B = dp([...ring.slice(far), ring[0]]);
      const out = [...A.slice(0, -1), ...B.slice(0, -1)];
      return out.length >= 3 ? out : ring;
    };
    const segX = (p, q, r, s) => {
      const d = (q[0] - p[0]) * (s[1] - r[1]) - (q[1] - p[1]) * (s[0] - r[0]);
      if (Math.abs(d) < 1e-12) return false;
      const t = ((r[0] - p[0]) * (s[1] - r[1]) - (r[1] - p[1]) * (s[0] - r[0])) / d,
        u = ((r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])) / d;
      return t > 1e-6 && t < 1 - 1e-6 && u > 1e-6 && u < 1 - 1e-6;
    };
    const simple = (ring) => {
      const n = ring.length;
      for (let i = 0; i < n; i++)
        for (let j = i + 2; j < n; j++) {
          if (i === 0 && j === n - 1) continue;
          if (segX(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n])) return false;
        }
      return true;
    };
    // Mansard-style roof following the ring: slope from eaves to an inset top.
    const mansard = (ring, holes, z, rise, d) => {
      let inner = null;
      for (let dd = d; dd > 0.6; dd *= 0.6) {
        const cand = kit.offsetRing(ring, -dd);
        if (simple(cand) && kit.ringArea(cand) > 0.2 * kit.ringArea(ring)) {
          inner = cand;
          d = dd;
          break;
        }
      }
      if (!inner) {
        kit.cap(batch, slate, [[ring, ...holes]], z);
        return null;
      }
      const zr = z + rise * Math.min(1, d / 2.2);
      for (let k = 0; k < ring.length; k++) {
        const j = (k + 1) % ring.length;
        batch.quad(
          slate,
          [ring[k][0], ring[k][1], z],
          [ring[j][0], ring[j][1], z],
          [inner[j][0], inner[j][1], zr],
          [inner[k][0], inner[k][1], zr],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      kit.cap(batch, kit.mat('#6f4234'), [[inner, ...holes]], zr);
      return { inner, zr };
    };
    // Shaped ("scrolly") gable plate in an edge plane.
    const gableShape = (w, hgt) => {
      const s = new THREE.Shape();
      s.moveTo(-w / 2, 0);
      s.lineTo(w / 2, 0);
      s.lineTo(w / 2, hgt * 0.18);
      s.quadraticCurveTo(w / 2 - w * 0.05, hgt * 0.42, w / 2 - w * 0.22, hgt * 0.45);
      s.lineTo(w / 2 - w * 0.22, hgt * 0.62);
      s.quadraticCurveTo(w * 0.12, hgt * 0.7, w * 0.12, hgt * 0.9);
      s.lineTo(w * 0.12, hgt);
      s.lineTo(-w * 0.12, hgt);
      s.lineTo(-w * 0.12, hgt * 0.9);
      s.quadraticCurveTo(-w * 0.12, hgt * 0.7, -(w / 2 - w * 0.22), hgt * 0.62);
      s.lineTo(-(w / 2 - w * 0.22), hgt * 0.45);
      s.quadraticCurveTo(-(w / 2 - w * 0.05), hgt * 0.42, -w / 2, hgt * 0.18);
      s.lineTo(-w / 2, 0);
      return s;
    };
    const gableGeos = new Map();
    const gable = (cx, cy, ang, z, w, hgt) => {
      const key = `${w.toFixed(1)}:${hgt.toFixed(1)}`;
      if (!gableGeos.has(key)) {
        const geo = new THREE.ExtrudeGeometry(gableShape(w, hgt), {
          depth: 0.7,
          bevelEnabled: false,
          curveSegments: 4,
        });
        geo.rotateX(Math.PI / 2); // in x-z plane, extruded towards -y (inwards when rotated by edge angle)
        gableGeos.set(key, geo);
      }
      // edge direction ang; outward normal of a CCW ring is (sin, -cos): local -y = outward? rotate so local +y is inward
      const m = new THREE.Matrix4().makeRotationZ(ang + Math.PI).setPosition(cx, cy, z);
      batch.addGeometry(brick, gableGeos.get(key), m);
      // window and stone coping strip on the gable face
      const nx = Math.sin(ang),
        ny = -Math.cos(ang);
      kit.box(
        batch,
        white,
        cx + nx * 0.05,
        cy + ny * 0.05,
        z + hgt * 0.15,
        w * 0.32,
        0.08,
        hgt * 0.32,
        ang,
      );
      kit.box(
        batch,
        kit.mat('#26303a'),
        cx + nx * 0.1,
        cy + ny * 0.1,
        z + hgt * 0.18,
        w * 0.26,
        0.04,
        hgt * 0.26,
        ang,
      );
      kit.box(batch, stoneMat, cx, cy, z + hgt - 0.1, w * 0.3, 0.9, 0.35, ang);
    };
    const block = (id, eave, rise, opts = {}) => {
      const b = byId[id];
      if (!b) return;
      for (const poly of b.polys) {
        const outer = ccw(poly[0]);
        const holes = poly.slice(1).map((h) => (kit.ringArea(h) > 0 ? h.slice().reverse() : h));
        kit.walls(batch, facade, [[outer, ...holes]], 0, eave, { bay: 3.4, storey: 3.4 });
        // ground-floor stone band and eaves cornice
        const o = kit.offsetRing(outer, 0.25);
        kit.walls(batch, white, [[o]], eave - 0.45, eave);
        kit.cap(batch, white, [[o, outer.slice().reverse()]], eave);
        kit.walls(batch, kit.mat('#8a4632'), [[kit.offsetRing(outer, 0.08)]], 0, 1.0);
        const s = simplify(outer, 0.8);
        const roof = mansard(s, holes, eave, rise, opts.inset ?? 3.0);
        // light wells rise through the roof storeys
        if (roof && holes.length)
          kit.walls(batch, facade, [holes], eave, roof.zr, { bay: 3.4, storey: 3.4 });
        // Gables on long outward edges of the simplified outline.
        for (let k = 0; k < s.length; k++) {
          const a = s[k],
            c2 = s[(k + 1) % s.length];
          const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
          if (L < 6.5) continue;
          const ang = Math.atan2(c2[1] - a[1], c2[0] - a[0]);
          const n = L < 13 ? 1 : Math.floor(L / 11);
          const w = Math.min(5.6, L * 0.6);
          for (let j = 0; j < n; j++) {
            const t = n === 1 ? 0.5 : (j + 0.5) / n;
            gable(a[0] + (c2[0] - a[0]) * t, a[1] + (c2[1] - a[1]) * t, ang, eave, w, rise + 1.2);
          }
        }
        // Tall chimney stacks along the roof ridge line.
        if (roof) {
          const step = Math.max(1, Math.floor(roof.inner.length / (opts.stacks ?? 6)));
          for (let k = 0; k < roof.inner.length; k += step) {
            const p = roof.inner[k],
              q = roof.inner[(k + 1) % roof.inner.length];
            const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
            const sx = p[0] + (q[0] - p[0]) * 0.5,
              sy = p[1] + (q[1] - p[1]) * 0.5;
            kit.box(batch, brick, sx, sy, roof.zr - 0.5, 1.4, 2.6, 1.4, ang);
            for (const o of [-0.7, 0.7]) {
              const fl = new THREE.CylinderGeometry(0.45, 0.5, 4.2, 8).rotateX(Math.PI / 2);
              batch.addGeometry(
                brick,
                fl,
                new THREE.Matrix4().setPosition(
                  sx + Math.cos(ang) * o,
                  sy + Math.sin(ang) * o,
                  roof.zr + 0.9 + 2.1,
                ),
              );
            }
            kit.box(batch, kit.mat('#7d3e2c'), sx, sy, roof.zr + 5.0, 1.3, 2.8, 0.4, ang);
          }
        }
      }
    };
    block('3a4b3304-873e-4e63-8bd0-8a65761eb461', 11.5, 6, { inset: 4.5, stacks: 9 });
    g.add(batch.toGroup('royal_geographical_society'));
    return g;
  },
};
