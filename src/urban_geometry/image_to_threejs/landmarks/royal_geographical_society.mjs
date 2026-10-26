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
      title: 'Lowther Lodge - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Lowther_Lodge',
      used_for: 'Shaw 1873-75 for William Lowther; RGS home since 1913, Grade II*',
    },
    {
      title: 'What London cabbies call hot-cold corner - London Shoes',
      url: 'https://www.londonshoes.blog/2019/06/22/what-london-cabbies-call-hot-cold-corner-the-kensington-gore/',
      used_for: 'Livingstone and Shackleton statues set into the walls either side of the corner',
    },
    {
      title: 'Shackleton statue - London Remembers',
      url: 'https://www.londonremembers.com/memorial_types/statue?page=33',
      used_for:
        'Shackleton in a niche on the Exhibition Road facade; Livingstone on the Kensington Gore facade',
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
    'The 1928-30 and 2004 additions are not differentiated. Outer elevations have 3D white sashes under rubbed-brick heads ' +
    '(3.4 m bays assumed), string courses and quoin strips; the Livingstone and Shackleton statues stand in stone niches ' +
    'either side of the north-east corner (heights and niche form assumed; figures are simple robed stand-ins).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const BRICK = '#a5543c';
    const brick = kit.mat(BRICK),
      slate = kit.roof('clay', 0),
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
    const plainBrick = kit.paintedMaterial(
      'royal_geographical_society:plain',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = BRICK;
        c.fillRect(0, 0, w, h);
        const r = kit.rng(6.4);
        for (let y = 0; y < h; y += 4) {
          c.fillStyle = `rgba(0,0,0,${0.05 + r() * 0.04})`;
          c.fillRect(0, y, w, 1);
        }
        for (let k = 0; k < 300; k++) {
          c.fillStyle = r() < 0.5 ? 'rgba(255,200,170,0.07)' : 'rgba(60,15,5,0.07)';
          c.fillRect(r() * w, r() * h, 8, 3);
        }
      },
    );
    const glass = kit.mat('#26303a', { roughness: 0.15, metalness: 0.3 }),
      rubbed = kit.mat('#c47a5e'),
      potMat = kit.mat('#9a5a3e'),
      bronze = kit.mat('#4f4434', { roughness: 0.45, metalness: 0.55 });
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
          out.push([lt, spec.headMat ?? sur]);
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
    const sash = {
      w: 1.25,
      h: 2.1,
      head: 'lintel',
      glass,
      sur: white,
      headMat: rubbed,
      bar: white,
      bars: 2,
      f: 0.08,
      depth: 0.1,
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
      kit.cap(batch, kit.roof('clay', 1), [[inner, ...holes]], zr, { scale: 4 });
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
      const ux = Math.cos(ang),
        uy = Math.sin(ang);
      winKit.row(
        [cx - ux * w * 0.3 + nx * 0.02, cy - uy * w * 0.3 + ny * 0.02],
        [cx + ux * w * 0.3 + nx * 0.02, cy + uy * w * 0.3 + ny * 0.02],
        z + hgt * 0.12,
        2,
        0.25,
        { ...sash, w: Math.min(1.1, w * 0.18), h: hgt * 0.3 },
      );
      winKit.row(
        [cx - ux * 0.8 + nx * 0.02, cy - uy * 0.8 + ny * 0.02],
        [cx + ux * 0.8 + nx * 0.02, cy + uy * 0.8 + ny * 0.02],
        z + hgt * 0.56,
        1,
        0.2,
        { ...sash, w: 0.8, h: hgt * 0.18, head: 'arch' },
      );
      kit.box(batch, stoneMat, cx, cy, z + hgt - 0.1, w * 0.3, 0.9, 0.35, ang);
    };
    const block = (id, eave, rise, opts = {}) => {
      const b = byId[id];
      if (!b) return;
      for (const poly of b.polys) {
        const outer = ccw(poly[0]);
        const holes = poly.slice(1).map((h) => (kit.ringArea(h) > 0 ? h.slice().reverse() : h));
        if (holes.length) kit.walls(batch, facade, [holes], 0, eave, { bay: 3.4, storey: 3.4 });
        const storeys = Math.floor((eave - 0.6) / 3.4);
        for (let k = 0; k < outer.length; k++) {
          const a = outer[k],
            c2 = outer[(k + 1) % outer.length];
          const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
          if (L < 1.9) {
            kit.walls(batch, facade, [[[a, c2]]], 0, eave, { bay: 3.4, storey: 3.4 });
            continue;
          }
          batch.quad(
            plainBrick,
            [a[0], a[1], 0],
            [c2[0], c2[1], 0],
            [c2[0], c2[1], eave],
            [a[0], a[1], eave],
            [0, 0],
            [L / 6, 0],
            [L / 6, eave / 6],
            [0, eave / 6],
          );
          const n = Math.max(1, Math.round(L / 3.4));
          for (let st = 0; st < storeys; st++) {
            winKit.row(a, c2, st * 3.4 + 1.0, n, 0, st === 0 ? { ...sash, h: 2.3 } : sash);
            if (st > 0) winKit.band(a, c2, st * 3.4 + 0.45, 0.25, 0.08, rubbed);
          }
          // rubbed-brick quoin strips at the corners
          const ed = winKit.edge(a, c2);
          for (const pt of [a, c2])
            kit.box(
              batch,
              rubbed,
              pt[0] + ed.nx * 0.04,
              pt[1] + ed.ny * 0.04,
              1.0,
              0.5,
              0.08,
              eave - 1.45,
              ed.ang,
            );
        }
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
            kit.box(batch, brick, sx, sy, roof.zr - 0.5, 2.6, 1.4, 1.4, ang);
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
            kit.box(batch, kit.mat('#7d3e2c'), sx, sy, roof.zr + 5.0, 2.8, 1.3, 0.4, ang);
            kit.box(batch, kit.mat('#7d3e2c'), sx, sy, roof.zr + 4.3, 2.7, 1.2, 0.25, ang);
            for (const o of [-0.7, 0.7]) {
              const pm = kit.lathe(
                potMat,
                [
                  [0.2, 0],
                  [0.16, 0.6],
                  [0.2, 0.7],
                ],
                {
                  x: sx + Math.cos(ang) * o,
                  y: sy + Math.sin(ang) * o,
                  z: roof.zr + 5.4,
                  segments: 8,
                },
              );
              pm.updateMatrix();
              batch.addGeometry(potMat, pm.geometry, pm.matrix);
              pm.geometry.dispose();
            }
          }
        }
      }
    };
    block('3a4b3304-873e-4e63-8bd0-8a65761eb461', 11.5, 6, { inset: 4.5, stacks: 9 });
    // Livingstone (Kensington Gore front) and Shackleton (Exhibition Road front) in niches
    // either side of the north-east corner.
    const rb = byId['3a4b3304-873e-4e63-8bd0-8a65761eb461'];
    if (rb) {
      const outer = ccw(rb.polys[0][0]);
      let ci = 0;
      for (let k = 1; k < outer.length; k++)
        if (outer[k][0] + outer[k][1] > outer[ci][0] + outer[ci][1]) ci = k;
      const n = outer.length;
      // edges meeting at the corner: prev -> corner and corner -> next
      const edges = [
        winKit.edge(outer[(ci - 1 + n) % n], outer[ci]),
        winKit.edge(outer[ci], outer[(ci + 1) % n]),
      ];
      const robe = new THREE.LatheGeometry(
        [
          [0.001, 0],
          [0.32, 0],
          [0.3, 0.3],
          [0.24, 0.95],
          [0.2, 1.3],
          [0.26, 1.55],
          [0.14, 1.68],
          [0.001, 1.7],
        ].map(([r, z]) => new THREE.Vector2(r, z)),
        10,
      ).rotateX(Math.PI / 2);
      const head = new THREE.SphereGeometry(0.13, 10, 6);
      for (const [k, ed] of edges.entries()) {
        if (ed.L < 3) continue;
        const t = k === 0 ? ed.L - 2.2 : 2.2; // near the corner
        const px = ed.a[0] + ed.ux * t,
          py = ed.a[1] + ed.uy * t;
        // stone niche: surround, shell head, dark recess, corbelled plinth
        winKit.place(
          ed,
          new THREE.BoxGeometry(1.5, 3.2, 0.05).translate(0, 1.6, 0.02),
          kit.mat('#3a2d27'),
          t,
          3.2,
        );
        winKit.row(
          [px - ed.ux * 1.0, py - ed.uy * 1.0],
          [px + ed.ux * 1.0, py + ed.uy * 1.0],
          3.2,
          1,
          0.25,
          {
            w: 1.5,
            h: 2.5,
            head: 'arch',
            glass: kit.mat('#3a2d27'),
            sur: stoneMat,
            bar: stoneMat,
            bars: 0,
            f: 0.22,
          },
        );
        kit.box(batch, stoneMat, px + ed.nx * 0.3, py + ed.ny * 0.3, 2.7, 1.8, 0.6, 0.5, ed.ang);
        const s2 = 2.7 / 1.7;
        const rz = ed.ang + Math.PI / 2; // facing outwards
        const m = new THREE.Matrix4().compose(
          new THREE.Vector3(px + ed.nx * 0.35, py + ed.ny * 0.35, 3.2),
          new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz),
          new THREE.Vector3(s2, s2 * 0.8, s2),
        );
        batch.addGeometry(bronze, robe, m);
        batch.addGeometry(
          bronze,
          head,
          new THREE.Matrix4().makeTranslation(
            px + ed.nx * 0.35,
            py + ed.ny * 0.35,
            3.2 + 1.82 * s2,
          ),
        );
      }
      robe.dispose();
      head.dispose();
    }
    g.add(batch.toGroup('royal_geographical_society'));
    return g;
  },
};
