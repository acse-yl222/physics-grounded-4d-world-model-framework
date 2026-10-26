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
    'side) frontage ends; dimensions are estimated. Outer elevations carry 3D stone-dressed sashes (3.5 m bays, 3.0 m storeys ' +
    'assumed) with stone bands; light wells keep a painted tile. Balcony railings, stacked Corinthian columns, dormers and ' +
    'chimney pots are procedural.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const BRICK = '#a14c37',
      STONE = '#ddd0b4';
    const slate = kit.roof('slate', 1),
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
    const plainBrick = kit.paintedMaterial('albert_court:plain', 256, 256, (c, w, h) => {
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(5.1);
      for (let y = 0; y < h; y += 4) {
        c.fillStyle = `rgba(0,0,0,${0.05 + r() * 0.04})`;
        c.fillRect(0, y, w, 1);
      }
      for (let k = 0; k < 300; k++) {
        c.fillStyle = r() < 0.5 ? 'rgba(255,200,170,0.06)' : 'rgba(60,15,5,0.07)';
        c.fillRect(r() * w, r() * h, 8, 3);
      }
    });
    const glass = kit.mat('#28313b', { roughness: 0.15, metalness: 0.3 }),
      white = kit.mat('#f0ece2'),
      potMat = kit.mat('#9a5a3e');
    // ---- Lean framed windows (local x along the wall a -> b, y up, z outward; outward
    // normal on the right of a -> b), cached per spec: glass, moulded surround, mullion
    // and transom, sill, keystone or pediment.
    const winKit = (() => {
      const cache = new Map();
      const outline = (w, h, head, grow) => {
        const s = new THREE.Shape();
        const x0 = -w / 2 - grow,
          x1 = w / 2 + grow;
        s.moveTo(x0, -grow);
        s.lineTo(x1, -grow);
        if (head === 'arch') {
          s.lineTo(x1, h);
          s.absarc(0, h, w / 2 + grow, 0, Math.PI, false);
        } else {
          s.lineTo(x1, h + grow);
          s.lineTo(x0, h + grow);
        }
        s.lineTo(x0, -grow);
        return s;
      };
      const parts = (spec) => {
        const key = JSON.stringify(spec, (k, v) => (v && v.isMaterial ? v.uuid : v));
        if (cache.has(key)) return cache.get(key);
        const {
          w,
          h,
          head = 'flat',
          bars = 1,
          f = 0.18,
          glass,
          sur,
          bar,
          sill: sillMat,
          depth = 0.13,
        } = spec;
        const out = [];
        const gs = new THREE.ShapeGeometry(outline(w, h, head, 0), 5);
        gs.translate(0, 0, 0.02);
        out.push([gs, glass]);
        if (f > 0) {
          const ring = outline(w, h, head, f);
          ring.holes.push(new THREE.Path(outline(w, h, head, 0).getPoints(5).reverse()));
          out.push([
            new THREE.ExtrudeGeometry(ring, { depth, bevelEnabled: false, curveSegments: 5 }),
            sur,
          ]);
        }
        const top = head === 'arch' ? h + w / 2 : h;
        if (bars) {
          const nv = bars === 2 ? 2 : 1;
          for (let i = 1; i <= nv; i++) {
            const vb = new THREE.BoxGeometry(0.07, top, 0.07);
            vb.translate(-w / 2 + (w * i) / (nv + 1), top / 2, 0.06);
            out.push([vb, bar]);
          }
          const hb = new THREE.BoxGeometry(w, 0.07, 0.07);
          hb.translate(0, head === 'arch' ? h : h * 0.66, 0.06);
          out.push([hb, bar]);
        }
        const sl = new THREE.BoxGeometry(w + 2 * f + 0.2, 0.14, 0.26);
        sl.translate(0, -f - 0.07, 0.13);
        out.push([sl, sillMat ?? sur]);
        if (head === 'arch') {
          const ks = new THREE.BoxGeometry(Math.max(0.22, w * 0.18), f + 0.12, 0.2);
          ks.translate(0, top + f / 2, 0.1);
          out.push([ks, sur]);
        } else if (head === 'pediment' || head === 'lintel') {
          const hw = w / 2 + f + 0.15;
          const lt = new THREE.BoxGeometry(2 * hw, 0.16, 0.24);
          lt.translate(0, h + f + 0.08, 0.12);
          out.push([lt, sur]);
          if (head === 'pediment') {
            const t = new THREE.Shape();
            t.moveTo(-hw, 0);
            t.lineTo(hw, 0);
            t.lineTo(0, hw * 0.42);
            t.closePath();
            const pg = new THREE.ExtrudeGeometry(t, { depth: 0.22, bevelEnabled: false });
            pg.translate(0, h + f + 0.16, 0);
            out.push([pg, sur]);
          }
        }
        cache.set(key, out);
        return out;
      };
      const edge = (a, b) => {
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        const ux = (b[0] - a[0]) / L,
          uy = (b[1] - a[1]) / L;
        return { a, b, L, ux, uy, nx: uy, ny: -ux, ang: Math.atan2(uy, ux) };
      };
      const place = (e, geo, m, lx, z, out = 0) => {
        const mm = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(e.ux, e.uy, 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(e.nx, e.ny, 0),
        );
        mm.setPosition(e.a[0] + e.ux * lx + e.nx * out, e.a[1] + e.uy * lx + e.ny * out, z);
        batch.addGeometry(m, geo, mm);
      };
      const row = (a, b, z, n, margin, spec) => {
        const e = edge(a, b);
        const usable = e.L - 2 * margin;
        const xs = [];
        for (let k = 0; k < n; k++) {
          const lx = margin + (usable * (k + 0.5)) / n;
          for (const [geo, m] of parts(spec)) place(e, geo, m, lx, z);
          xs.push(lx);
        }
        return xs;
      };
      // Projecting band (string course) along an edge.
      const band = (a, b, z, h, proj, m) => {
        const e = edge(a, b);
        kit.box(
          batch,
          m,
          (a[0] + b[0]) / 2 + (e.nx * proj) / 2,
          (a[1] + b[1]) / 2 + (e.ny * proj) / 2,
          z,
          e.L + proj,
          proj,
          h,
          e.ang,
        );
      };
      return { parts, edge, place, row, band };
    })();
    const latheB = (m) => {
      m.updateMatrix();
      batch.addGeometry(m.material, m.geometry, m.matrix);
      m.geometry.dispose();
    };
    const sash = {
      w: 1.3,
      h: 1.95,
      head: 'lintel',
      glass,
      sur: stone,
      bar: white,
      bars: 1,
      f: 0.14,
      depth: 0.12,
    };
    const SB = 1.4,
      SH = 3.0; // semi-basement top, storey height
    const elevation = (a, c2, z1) => {
      const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
      batch.quad(
        plainBrick,
        [a[0], a[1], 0],
        [c2[0], c2[1], 0],
        [c2[0], c2[1], z1],
        [a[0], a[1], z1],
        [0, 0],
        [L / 6, 0],
        [L / 6, z1 / 6],
        [0, z1 / 6],
      );
      const n = Math.max(1, Math.round(L / 3.5));
      for (let st = 0; st < 7 && SB + st * SH + 2.5 < z1; st++) {
        winKit.row(a, c2, SB + 0.5 + st * SH, n, 0, sash);
        winKit.band(a, c2, SB + st * SH - 0.12, 0.26, 0.08, stone);
      }
      winKit.band(a, c2, SB + 7 * SH - 0.4, 0.3, 0.12, stone);
    };
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
          [Math.hypot(ring[j][0] - ring[k][0], ring[j][1] - ring[k][1]) / 3, 0],
          [Math.hypot(inner[j][0] - inner[k][0], inner[j][1] - inner[k][1]) / 3, rise / 3],
          [0, rise / 3],
        );
      }
      kit.cap(batch, kit.roof('flat', 1), [[inner, ...holes]], zr, { scale: 6 });
      return { inner, zr };
    };
    const b = byId['74c835dc-626d-4ed5-854f-f0ee4cf054ff'];
    if (!b) return g;
    const eave = 22.5,
      rise = 4.0;
    for (const poly of b.polys) {
      const outer = ccw(poly[0]);
      const holes = poly.slice(1).map((h) => (kit.ringArea(h) > 0 ? h.slice().reverse() : h));
      if (holes.length)
        kit.walls(batch, facade, [holes], 0, eave, { bay: 3.5, storey: 3.2, uvBase: -0.6 });
      for (let k = 0; k < outer.length; k++) {
        const a = outer[k],
          c2 = outer[(k + 1) % outer.length];
        if (Math.hypot(c2[0] - a[0], c2[1] - a[1]) >= 1.9) elevation(a, c2, eave);
        else
          kit.walls(batch, facade, [[[a, c2]]], 0, eave, { bay: 3.5, storey: 3.2, uvBase: -0.6 });
      }
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
            const ux = Math.cos(ang),
              uy = Math.sin(ang),
              nx = Math.sin(ang),
              ny = -Math.cos(ang);
            winKit.row(
              [x - ux * 0.8 + nx * 0.7, y - uy * 0.8 + ny * 0.7],
              [x + ux * 0.8 + nx * 0.7, y + uy * 0.8 + ny * 0.7],
              eave + 0.6,
              1,
              0.2,
              {
                ...sash,
                w: 0.95,
                h: 1.2,
                head: 'pediment',
                f: 0.1,
              },
            );
          }
        }
      // Chimney stacks.
      if (roof) {
        const step = Math.max(1, Math.floor(roof.inner.length / 9));
        for (let k = 0; k < roof.inner.length; k += step) {
          const p = roof.inner[k];
          kit.box(batch, brick, p[0], p[1], roof.zr - 0.4, 1.2, 2.6, 3.0, 0.1);
          kit.box(batch, stone, p[0], p[1], roof.zr + 2.4, 1.45, 2.85, 0.3, 0.1);
          for (const d of [-0.8, 0, 0.8]) {
            const pm = kit.lathe(
              potMat,
              [
                [0.17, 0],
                [0.14, 0.55],
                [0.18, 0.65],
              ],
              {
                x: p[0] - Math.sin(0.1) * d,
                y: p[1] + Math.cos(0.1) * d,
                z: roof.zr + 2.7,
                segments: 6,
              },
            );
            pm.updateMatrix();
            batch.addGeometry(potMat, pm.geometry, pm.matrix);
            pm.geometry.dispose();
          }
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
        const R = 3.0,
          tz = eave + 3;
        const cylG = new THREE.CylinderGeometry(R, R, tz, 24, 1, true).rotateX(Math.PI / 2);
        const uv = cylG.attributes.uv;
        for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) * 3, uv.getY(k) * (tz / 6));
        batch.addGeometry(
          plainBrick,
          cylG,
          new THREE.Matrix4().makeTranslation(p[0], p[1], tz / 2),
        );
        // windows round the outer half of the turret, stone bands, cornice and conical roof
        const facing = Math.atan2(ny, nx);
        for (const dphi of [-1.2, -0.4, 0.4, 1.2]) {
          const ph = facing + dphi,
            dl = 0.36;
          const A = [p[0] + Math.cos(ph - dl) * (R - 0.02), p[1] + Math.sin(ph - dl) * (R - 0.02)],
            B2 = [p[0] + Math.cos(ph + dl) * (R - 0.02), p[1] + Math.sin(ph + dl) * (R - 0.02)];
          for (let st = 0; st < 8; st++)
            winKit.row(A, B2, SB + 0.5 + st * SH, 1, 0.05, { ...sash, w: 1.0 });
        }
        for (let st = 0; st <= 7; st++)
          latheB(
            kit.lathe(
              stone,
              [
                [R, 0],
                [R + 0.09, 0.02],
                [R + 0.09, 0.26],
                [R, 0.28],
              ],
              { x: p[0], y: p[1], z: SB + st * SH - 0.12, segments: 24 },
            ),
          );
        latheB(
          kit.lathe(
            stone,
            [
              [R, 0],
              [R + 0.25, 0.1],
              [R + 0.3, 0.6],
              [R, 0.7],
            ],
            { x: p[0], y: p[1], z: tz - 0.4, segments: 24 },
          ),
        );
        latheB(
          kit.lathe(
            slate,
            [
              [R + 0.35, 0],
              [R * 0.75, 1.8],
              [R * 0.35, 4.6],
              [0.001, 6.5],
            ],
            { x: p[0], y: p[1], z: tz + 0.3, segments: 24 },
          ),
        );
        latheB(
          kit.lathe(
            kit.mat('lead'),
            [
              [0.001, 0],
              [0.25, 0],
              [0.12, 0.4],
              [0.2, 0.6],
              [0.05, 1.0],
              [0.03, 2.0],
              [0.001, 2.05],
            ],
            { x: p[0], y: p[1], z: tz + 6.6, segments: 8 },
          ),
        );
        cylG.dispose();
      }
      // Balconies on Corinthian columns across the middle of the south front.
      const s0 = 9,
        s1 = L - 9;
      for (let st = 1; st < 7; st++) {
        const z = SB + st * SH - 0.3;
        const p = P((s0 + s1) / 2, 0.75);
        kit.box(batch, stone, p[0], p[1], z, s1 - s0, 1.5, 0.3, ang);
        kit.cornice(
          batch,
          stone,
          [P(s0, 0), P(s1, 0), P(s1, 1.55), P(s0, 1.55)].reverse(),
          z - 0.12,
          { height: 0.12, projection: 0.06 },
        );
        // iron balcony railing with bars
        const r0 = P(s0, 1.42),
          r1 = P(s1, 1.42);
        kit.box(
          batch,
          iron,
          (r0[0] + r1[0]) / 2,
          (r0[1] + r1[1]) / 2,
          z + 1.25,
          s1 - s0,
          0.06,
          0.06,
          ang,
        );
        kit.box(
          batch,
          iron,
          (r0[0] + r1[0]) / 2,
          (r0[1] + r1[1]) / 2,
          z + 0.4,
          s1 - s0,
          0.04,
          0.04,
          ang,
        );
        const nb = Math.floor((s1 - s0) / 0.25);
        for (let i = 0; i <= nb; i++) {
          const q = P(s0 + ((s1 - s0) * i) / nb, 1.42);
          kit.box(batch, iron, q[0], q[1], z + 0.3, 0.025, 0.025, 0.95, ang);
        }
        // Corinthian columns carrying the balcony above
        kit.colonnade(batch, stone, P(s0 + 0.3, 1.3), P(s1 - 0.3, 1.3), z + 0.3, SH - 0.3, {
          count: Math.max(2, Math.round((s1 - s0) / 4.2) + 1),
          radius: 0.16,
          capital: 'corinthian',
          segments: 10,
        });
      }
      kit.colonnade(batch, stone, P(s0 + 0.3, 1.3), P(s1 - 0.3, 1.3), 0, SB + SH - 0.3, {
        count: Math.max(2, Math.round((s1 - s0) / 4.2) + 1),
        radius: 0.24,
        capital: 'corinthian',
        segments: 10,
      });
    }
    g.add(batch.toGroup('albert_court'));
    return g;
  },
};
