// Royal College of Art, Darwin Building, Kensington Gore (H. T. Cadbury-Brown with Hugh
// Casson and Robert Goodden, 1960-63; Grade II). Eight-storey block of glass and
// sombre purple-brown brick with an exposed-aggregate concrete frame opposite the Royal
// Albert Hall: a dense grid of brick piers and concrete floor bands framing large
// studio windows, a glazed top-floor studio storey and north-light roof glazing.
export default {
  id: 'rca_darwin_building',
  name: 'Royal College of Art – Darwin Building',
  claims: ['fbe9fd1c-d1c5-4d60-b6cc-7e8668ed3fd0'],
  references: [
    {
      title: 'Royal College of Art - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_College_of_Art',
      used_for:
        'designed by RCA staff Cadbury-Brown, Casson and Goodden, 1960-63, Grade II listed 2001',
    },
    {
      title: 'Darwin Building, RCA, seen from the north-east - RIBApix',
      url: 'https://www.architecture.com/image-library/RIBApix/licensed-image/poster/darwin-building-royal-college-of-art-kensington-gore-london-seen-from-the-northeast/posterid/RIBA4149.html',
      used_for: 'concrete frame and brickwork massing on Kensington Gore',
    },
    {
      title: 'Royal College of Art - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/royal-college-of-art.html',
      used_for: 'Nairn: sombre purple-toned facing brick with concrete aggregate',
    },
    {
      title: 'Darwin Building, RCA: fenestration detail - RIBApix',
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/darwin-building-royal-college-of-art-kensington-gore-london-fenestration-detail/posterid/RIBA45859.html',
      used_for: 'concrete, brickwork and metal windows (photo subject tags)',
    },
    {
      title: 'Twentieth Century Society - Royal College of Art',
      url: 'https://c20society.org.uk/news/twentieth-century-society-stands-alone-in-fight-to-save-royal-college-of-art',
      used_for: 'the east elevation is the most conspicuous part of the listed building',
    },
    {
      title: 'Darwin Building, Royal College of Art - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1960/collegeofart.html',
      used_for:
        'eight-storey building of glass and dark brick for workshops and studios, opposite the Albert Hall',
    },
  ],
  notes:
    'Height from the data (26.4 m). Pier/bay rhythm and the glazed top storey with north-light roof glazing are approximations ' +
    'from descriptions; the staggered internal section is not modelled. Elevations are 3D: brick piers proud of the panels, ' +
    'exposed-aggregate floor bands and metal-framed studio windows (bay 3.2 m, storey 3.25 m assumed); the glazed top storey ' +
    'has 3D mullions; a terrace rail on the setback is assumed.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['fbe9fd1c-d1c5-4d60-b6cc-7e8668ed3fd0'];
    if (!b) return g;
    let ring = b.polys[0][0];
    if (kit.ringArea(ring) < 0) ring = ring.slice().reverse();
    const H = b.h ?? 26.4;
    const top = H - 3.4;
    const BRICK = '#4d3431',
      CONC = '#a39e93';
    const facade = kit.paintedMaterial('rca_darwin_building:bay', 512, 256, (c, w, h) => {
      // 4 bays (3.2 m) x 2 storeys (3.25 m)
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.04)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      const bw = w / 4,
        sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        c.fillStyle = CONC;
        c.fillRect(0, y0 + sh - 16, w, 16); // exposed aggregate floor band
        c.fillStyle = 'rgba(80,75,70,0.35)';
        for (let x = 0; x < w; x += 6) c.fillRect(x, y0 + sh - 14 + ((x * 7) % 11), 2, 2);
        for (let b2 = 0; b2 < 4; b2++) {
          const x = b2 * bw;
          c.fillStyle = '#2a3540';
          c.fillRect(x + 26, y0 + 22, bw - 52, sh - 48);
          c.fillStyle = '#7d858a';
          c.fillRect(x + 26, y0 + 22 + (sh - 48) * 0.3, bw - 52, 3);
          c.fillRect(x + bw / 2 - 1, y0 + 22, 3, sh - 48);
        }
      }
    });
    const plainBrick = kit.paintedMaterial('rca_darwin_building:plain', 256, 256, (c, w, h) => {
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(2.9);
      for (let y = 0; y < h; y += 4) {
        c.fillStyle = `rgba(255,255,255,${0.02 + r() * 0.03})`;
        c.fillRect(0, y, w, 1);
      }
      for (let k = 0; k < 300; k++) {
        c.fillStyle = r() < 0.5 ? 'rgba(120,80,110,0.10)' : 'rgba(20,10,10,0.10)';
        c.fillRect(r() * w, r() * h, 8, 3);
      }
    });
    const concMat = kit.mat(CONC, { roughness: 0.95 }),
      steelF = kit.mat('#3d4347', { roughness: 0.45, metalness: 0.5 }),
      winGlass = kit.mat('#2a3540', { roughness: 0.12, metalness: 0.35 }),
      pierBrick = kit.mat('#55393a');
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
    const ST = 3.25;
    const NS = Math.round(top / ST);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        c2 = ring[(k + 1) % ring.length];
      const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
      if (L < 2.5) {
        kit.walls(batch, facade, [[[a, c2]]], 0, top, { bay: 3.2, storey: ST });
        continue;
      }
      batch.quad(
        plainBrick,
        [a[0], a[1], 0],
        [c2[0], c2[1], 0],
        [c2[0], c2[1], top],
        [a[0], a[1], top],
        [0, 0],
        [L / 6, 0],
        [L / 6, top / 6],
        [0, top / 6],
      );
      const ed = winKit.edge(a, c2);
      const n = Math.max(1, Math.round(L / 3.2));
      for (let st = 0; st < NS; st++) {
        const z = st * ST;
        // exposed-aggregate concrete floor band
        if (st > 0) winKit.band(a, c2, z - 0.2, 0.42, 0.16, concMat);
        winKit.row(a, c2, z + (st === 0 ? 0.6 : 0.85), n, 0, {
          w: (L / n) * 0.62,
          h: st === 0 ? 2.35 : 1.95,
          head: 'flat',
          glass: winGlass,
          sur: steelF,
          bar: steelF,
          bars: 1,
          f: 0.06,
          depth: 0.08,
        });
      }
      // brick piers between the bays, proud of the panels
      for (let i = 0; i <= n; i++) {
        const t = (i / n) * L;
        kit.box(
          batch,
          pierBrick,
          a[0] + ed.ux * t + ed.nx * 0.08,
          a[1] + ed.uy * t + ed.ny * 0.08,
          0,
          (L / n) * 0.2,
          0.18,
          top - 0.7,
          ed.ang,
        );
      }
    }
    // Recessed ground-floor glazing line and concrete plinth.
    kit.walls(batch, kit.mat(CONC), [[kit.offsetRing(ring, 0.05)]], 0, 0.6);
    // Concrete roof band.
    const o = kit.offsetRing(ring, 0.3);
    const conc = kit.mat(CONC);
    kit.walls(batch, conc, [[o]], top - 0.7, top);
    kit.cap(batch, conc, [[o, ring.slice().reverse()]], top);
    kit.cap(batch, kit.mat('#6f6c68'), [[ring]], top);
    // Glazed top studio storey set back from the frontage.
    const inner = kit.offsetRing(ring, -1.2);
    const studio = kit.paintedMaterial('rca_darwin_building:studio', 256, 64, (c, w, h) => {
      c.fillStyle = '#3b4d5a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#c9ccc9';
      for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 3, h);
      c.fillRect(0, 0, w, 4);
      c.fillRect(0, h - 4, w, 4);
    });
    kit.walls(batch, studio, [[inner]], top, H - 0.6, { bay: 3.2, storey: (H - 0.6 - top) / 2 });
    for (let k = 0; k < inner.length; k++) {
      const a = inner[k],
        c2 = inner[(k + 1) % inner.length];
      const L = Math.hypot(c2[0] - a[0], c2[1] - a[1]);
      if (L < 1.5) continue;
      const ed = winKit.edge(a, c2);
      const n = Math.max(1, Math.round(L / 1.6));
      for (let i = 0; i <= n; i++) {
        const t = (i / n) * L;
        kit.box(
          batch,
          kit.mat('#c9ccc9'),
          a[0] + ed.ux * t + ed.nx * 0.05,
          a[1] + ed.uy * t + ed.ny * 0.05,
          top,
          0.1,
          0.12,
          H - 0.6 - top,
          ed.ang,
        );
      }
      winKit.band(a, c2, top + 1.3, 0.08, 0.1, kit.mat('#c9ccc9'));
      winKit.band(a, c2, H - 0.9, 0.3, 0.25, concMat);
    }
    // roof terrace edge rail along the setback
    kit.balustrade(
      batch,
      steelF,
      [...kit.offsetRing(ring, -0.25), kit.offsetRing(ring, -0.25)[0]],
      top,
      { height: 1.0, spacing: 1.6 },
    );
    kit.cap(batch, kit.mat('#5f5e5c'), [[inner]], H - 0.6);
    // North-light roof glazing ridges across the top.
    const fr = kit.ringFrame(ring);
    let ang = fr.angle;
    if (Math.cos(ang) < 0) ang += Math.PI; // +v points north
    const e = kit.orientedExtent(inner, ang);
    const glass = kit.mat('#56707e', { roughness: 0.2, metalness: 0.3 });
    const z0 = H - 0.6,
      z1 = H + 1.1;
    const span = e.v1 - e.v0 - 3;
    const n = Math.max(1, Math.floor(span / 4.0));
    const step = span / n;
    const u0 = e.u0 + 2,
      u1 = e.u1 - 2;
    for (let k = 0; k < n; k++) {
      const va = e.v0 + 1.5 + k * step,
        vb = va + step;
      // solid back slope rising from the south (va) to the ridge (vb), vertical glazing facing north
      const A = e.at(u0, va, z0),
        B = e.at(u1, va, z0),
        Ct = e.at(u1, vb, z1),
        Dt = e.at(u0, vb, z1),
        C = e.at(u1, vb, z0),
        D = e.at(u0, vb, z0);
      batch.quad(conc, A, B, Ct, Dt, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.quad(glass, C, D, Dt, Ct, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.add(
        conc,
        [D, A, Dt],
        [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        conc,
        [B, C, Ct],
        [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
        [0, 1, 2],
      );
    }
    g.add(batch.toGroup('rca_darwin_building'));
    return g;
  },
};
