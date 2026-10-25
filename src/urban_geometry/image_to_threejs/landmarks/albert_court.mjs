// Albert Court, Prince Consort Road (Frederick Hemings 1890-94, completed by R. J. Worley
// 1896-1900). Large D-shaped mansion block whose north and east fronts follow the curve
// of the former Royal Horticultural Society garden. Seven storeys over a semi-basement,
// red brick with horizontal stone bands and dressings, iron basement railings, a south
// front with balconies carried on Corinthian columns and conical-roofed turrets at
// either end, and internal light wells.
export default {
  id: 'albert_court',
  name: 'Albert Court',
  claims: ['74c835dc-626d-4ed5-854f-f0ee4cf054ff'],
  references: [
    {
      title: 'Albert Court - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Albert_Court',
      used_for:
        'Hemings design begun 1890, finished by Worley 1896-1900; D-shaped plan following the RHS garden curve; red brick with stone banding',
    },
    {
      title: 'Albert Court - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101227161-albert-court-knightsbridge-and-belgravia-ward',
      used_for:
        'red brick with horizontal stone bands and dressings, 7 storeys and semi-basement, south facade balconies on Corinthian columns, conical roofed turrets at either end',
    },
    {
      title: 'Albert Court in Prince Consort Road - London Picture Archive',
      url: 'https://www.londonpicturearchive.org.uk/view-item?i=170008',
      used_for: 'street view of the Prince Consort Road front',
    },
  ],
  notes:
    'Eaves raised to 22.5 m (7 storeys + semi-basement) above the 19.3 m data height, with a 4 m slate roof slope following the ' +
    'footprint. Light wells are the footprint holes. Balcony and turret positions are placed on the south (Prince Consort Road ' +
    'side) frontage ends; dimensions are estimated.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const BRICK = '#a14c37',
      STONE = '#ddd0b4';
    const slate = kit.mat('#4f565d'),
      stone = kit.mat(STONE),
      brick = kit.mat(BRICK),
      iron = kit.mat('#1f2224');
    const facade = kit.paintedMaterial('albert_court:bay', 512, 256, (c, w, h) => {
      // 4 bays x 2 storeys (3.2 m): brick with stone band per storey, stone-dressed sashes.
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(0,0,0,0.06)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      const bw = w / 4,
        sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        c.fillStyle = STONE;
        c.fillRect(0, y0 + sh - 14, w, 9);
        c.fillRect(0, y0 + 10, w, 4);
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw / 2;
          c.fillStyle = STONE;
          c.fillRect(x - 28, y0 + 22, 56, 86);
          c.fillStyle = '#f0ece2';
          c.fillRect(x - 23, y0 + 27, 46, 76);
          c.fillStyle = '#28313b';
          c.fillRect(x - 20, y0 + 30, 40, 34);
          c.fillRect(x - 20, y0 + 67, 40, 33);
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
      kit.cap(batch, kit.mat('#5d6369'), [[inner, ...holes]], zr);
      return { inner, zr };
    };
    const b = byId['74c835dc-626d-4ed5-854f-f0ee4cf054ff'];
    if (!b) return g;
    const eave = 22.5,
      rise = 4.0;
    for (const poly of b.polys) {
      const outer = ccw(poly[0]);
      const holes = poly.slice(1).map((h) => (kit.ringArea(h) > 0 ? h.slice().reverse() : h));
      kit.walls(batch, facade, [[outer, ...holes]], 0, eave, {
        bay: 3.5,
        storey: 3.2,
        uvBase: -0.6,
      });
      // semi-basement plinth with railings
      kit.walls(batch, stone, [[kit.offsetRing(outer, 0.06)]], 0, 1.4);
      const rail = kit.offsetRing(outer, 1.6);
      kit.walls(
        batch,
        kit.paintedMaterial(
          'albert_court:rail',
          64,
          32,
          (c, w, h) => {
            c.clearRect(0, 0, w, h);
            c.fillStyle = '#1f2224';
            c.fillRect(0, 0, w, 3);
            for (let x = 2; x < w; x += 8) c.fillRect(x, 0, 2, h);
          },
          { transparent: true, alphaTest: 0.5, side: 2 },
        ),
        [[rail]],
        0,
        1.1,
        { bay: 2, storey: 0.55 },
      );
      // stone eaves cornice and parapet
      const o = kit.offsetRing(outer, 0.35);
      kit.walls(batch, stone, [[o]], eave - 0.6, eave);
      kit.cap(batch, stone, [[o, outer.slice().reverse()]], eave);
      const s = simplify(outer, 0.8);
      const roof = mansard(s, holes, eave, rise, 2.6);
      if (roof && holes.length)
        kit.walls(batch, facade, [holes], eave, roof.zr, { bay: 3.5, storey: 3.2 });
      // Dormers on the roof slope, every ~6 m along simplified edges.
      if (roof)
        for (let k = 0; k < s.length; k++) {
          const a = s[k],
            c2 = s[(k + 1) % s.length],
            ia = roof.inner[k],
            ic = roof.inner[(k + 1) % s.length];
          const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
          const ang = Math.atan2(c2[1] - a[1], c2[0] - a[0]);
          const n = Math.floor(L / 6.5);
          for (let j = 0; j < n; j++) {
            const t = (j + 0.5) / n;
            const x = (a[0] + (c2[0] - a[0]) * t) * 0.55 + (ia[0] + (ic[0] - ia[0]) * t) * 0.45,
              y = (a[1] + (c2[1] - a[1]) * t) * 0.55 + (ia[1] + (ic[1] - ia[1]) * t) * 0.45;
            kit.box(batch, stone, x, y, eave + 0.3, 1.6, 1.4, 2.0, ang);
            kit.box(
              batch,
              kit.mat('#28313b'),
              x + Math.sin(ang) * 0.71,
              y - Math.cos(ang) * 0.71,
              eave + 0.6,
              1.0,
              0.04,
              1.3,
              ang,
            );
          }
        }
      // Chimney stacks.
      if (roof) {
        const step = Math.max(1, Math.floor(roof.inner.length / 9));
        for (let k = 0; k < roof.inner.length; k += step) {
          const p = roof.inner[k];
          kit.box(batch, brick, p[0], p[1], roof.zr - 0.4, 1.2, 2.6, 3.0, 0.1);
        }
      }
    }
    // South front (longest edge with outward normal pointing south): turrets and balconies.
    const outer = ccw(b.polys[0][0]);
    let best = null;
    for (let k = 0; k < outer.length; k++) {
      const a = outer[k],
        c2 = outer[(k + 1) % outer.length];
      const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
      const ny = -(c2[0] - a[0]) / L;
      if (ny < -0.8 && (!best || L > best.L)) best = { a, c: c2, L };
    }
    if (best) {
      const { a, c: c2, L } = best;
      const tx = (c2[0] - a[0]) / L,
        ty = (c2[1] - a[1]) / L,
        nx = ty,
        ny = -tx,
        ang = Math.atan2(ty, tx);
      const P = (s, d) => [a[0] + tx * s + nx * d, a[1] + ty * s + ny * d];
      for (const s of [2.8, L - 2.8]) {
        const p = P(s, 0.6);
        const t = new THREE.Mesh(
          new THREE.CylinderGeometry(3.0, 3.0, eave + 3, 16).rotateX(Math.PI / 2),
          facade,
        );
        // cylinder UVs: wrap 3 bays round, storeys up
        const uv = t.geometry.attributes.uv;
        for (let k = 0; k < uv.count; k++)
          uv.setXY(k, uv.getX(k) * 1.5, uv.getY(k) * ((eave + 3) / 6.4));
        t.geometry.setAttribute(
          'color',
          new THREE.Float32BufferAttribute(new Array(uv.count * 3).fill(1), 3),
        );
        t.position.set(p[0], p[1], (eave + 3) / 2);
        const band = new THREE.Mesh(
          new THREE.CylinderGeometry(3.25, 3.25, 0.6, 16).rotateX(Math.PI / 2),
          stone,
        );
        band.position.set(p[0], p[1], eave + 2.8);
        const cone = new THREE.Mesh(
          new THREE.ConeGeometry(3.4, 6.5, 16).rotateX(Math.PI / 2),
          slate,
        );
        cone.position.set(p[0], p[1], eave + 3.1 + 3.25);
        const fin = new THREE.Mesh(
          new THREE.CylinderGeometry(0.06, 0.1, 1.6, 6).rotateX(Math.PI / 2),
          kit.mat('lead'),
        );
        fin.position.set(p[0], p[1], eave + 3.1 + 6.5 + 0.6);
        g.add(t, band, cone, fin);
      }
      // Balconies on Corinthian columns across the middle of the south front.
      const s0 = 9,
        s1 = L - 9;
      const col = new THREE.CylinderGeometry(0.22, 0.26, 1, 10).rotateX(Math.PI / 2);
      for (let z = 4.4; z < eave - 2; z += 3.2) {
        const p = P((s0 + s1) / 2, 0.75);
        kit.box(batch, stone, p[0], p[1], z, s1 - s0, 1.5, 0.3, ang);
        const q = P((s0 + s1) / 2, 1.45);
        kit.box(batch, iron, q[0], q[1], z + 0.3, s1 - s0, 0.06, 0.9, ang);
      }
      for (let s = s0 + 0.3; s <= s1 - 0.2; s += 4.2) {
        const p = P(s, 1.3);
        const m = new THREE.Matrix4()
          .makeScale(1, 1, eave - 6)
          .setPosition(p[0], p[1], 1.4 + (eave - 6) / 2);
        batch.addGeometry(stone, col, m);
      }
    }
    g.add(batch.toGroup('albert_court'));
    return g;
  },
};
