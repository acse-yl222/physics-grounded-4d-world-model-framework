// Former Royal College of Organists, 1 Kensington Gore (Lt H. H. Cole RE, built 1874-75
// for the National Training School for Music). Four storeys and three main bays in
// stucco covered with sgraffito panels by F. W. Moody and his students: cream, pale
// blue and maroon friezes of putti carrying musical instruments and scrolls. Entrance in
// a full-height canted bay with oriels above, mullion-and-transom windows and a
// bracketed eaves cornice under a slate roof.
export default {
  id: 'royal_college_of_organists',
  name: 'Royal College of Organists (former)',
  claims: ['f4fa2cad-6f80-4d7f-9e80-67a3eee60414'],
  references: [
    {
      title: 'Royal College of Organists - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101217773-royal-college-of-organists-knightsbridge-and-belgravia-ward',
      used_for:
        'four storeys, three main bays, full-height canted entrance bay with oriels, mullion-and-transom windows, bracketed eaves cornice, stucco with sgraffito panels by F. W. Moody',
    },
    {
      title: 'Royal College of Organists - Survey of London (british-history.ac.uk)',
      url: 'https://www.british-history.ac.uk/node/40140',
      used_for:
        "built 1874-5 for the National Training School for Music; sgraffito executed by Moody's students",
    },
    {
      title: 'Organs and archaeology - Adam Yamey',
      url: 'https://adam-yamey-writes.com/tag/organ/',
      used_for:
        'cream, pale blue and maroon sgraffito; bands of putti carrying musical instruments',
    },
    {
      title: 'Royal College of Organists - victorianweb.org',
      url: 'https://www.victorianweb.org/art/architecture/misc/4.html',
      used_for: 'H. H. Cole as architect, Moody sgraffiti',
    },
  ],
  notes:
    'The Overture footprint is larger than the narrow street building and is decorated throughout; the canted bay is placed ' +
    'at the centre of the street (north) frontage. Sgraffito figures are abstracted to putti silhouettes and scrolls; ' +
    'slate roof pitch is assumed. Eaves at the data height (17.9 m less roof). Windows are 3D mullion-and-transom frames ' +
    'placed on the painted sgraffito panels (bay rhythm 3.4 m assumed on every elevation); chimney and door positions are assumed.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['f4fa2cad-6f80-4d7f-9e80-67a3eee60414'];
    if (!b) return g;
    let ring = b.polys[0][0];
    if (kit.ringArea(ring) < 0) ring = ring.slice().reverse();
    const H = Math.max(14, (b.h ?? 17.9) - 2.6);
    const CREAM = '#e9dcc0',
      MAROON = '#7a2e2c',
      BLUE = '#9db7c6',
      DARK = '#262d35';
    // Painted sgraffito facade: 4 bays (3.4 m) x full height (4 storeys).
    const mat = kit.paintedMaterial('royal_college_of_organists:sgraffito', 512, 512, (c, w, h) => {
      const P = h / H,
        Y = (m) => h - m * P,
        bw = w / 4;
      c.fillStyle = CREAM;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(3.7);
      const st = [0, H * 0.27, H * 0.52, H * 0.76, H];
      // Storey friezes of putti on maroon / blue grounds.
      for (let s = 0; s < 4; s++) {
        const z = st[s + 1] - 1.0;
        c.fillStyle = s % 2 ? BLUE : MAROON;
        c.fillRect(0, Y(z + 0.9), w, 0.9 * P);
        c.fillStyle = CREAM;
        for (let x = 6; x < w; x += 22) {
          const y0 = Y(z + 0.15);
          c.beginPath();
          c.arc(x + 6, y0 - 18, 4, 0, Math.PI * 2); // head
          c.fill();
          c.fillRect(x + 3, y0 - 14, 7, 10); // body
          c.fillRect(x + (r() < 0.5 ? -2 : 10), y0 - 16, 6, 2); // instrument / scroll
        }
      }
      // Panels flanking the windows with scroll ornament.
      for (let s = 0; s < 4; s++)
        for (let bb = 0; bb < 4; bb++) {
          const x = bw * (bb + 0.5),
            z0 = st[s] + (s ? 0.4 : 1.0),
            z1 = st[s + 1] - 1.3;
          c.fillStyle = s ? MAROON : '#b98e6e';
          c.fillRect(x - 46, Y(z1), 92, (z1 - z0) * P);
          c.strokeStyle = CREAM;
          c.lineWidth = 2;
          for (const sx of [-38, 30]) {
            c.beginPath();
            c.arc(x + sx + 4, Y((z0 + z1) / 2), 5, 0, Math.PI * 1.6);
            c.stroke();
          }
          // mullion-and-transom window
          c.fillStyle = '#f1e8d2';
          c.fillRect(x - 28, Y(z1 - 0.15), 56, (z1 - z0 - 0.3) * P);
          c.fillStyle = DARK;
          c.fillRect(x - 24, Y(z1 - 0.35), 48, (z1 - z0 - 0.7) * P);
          c.fillStyle = '#f1e8d2';
          c.fillRect(x - 2, Y(z1 - 0.35), 4, (z1 - z0 - 0.7) * P);
          c.fillRect(x - 24, Y(z0 + (z1 - z0) * 0.66), 48, 4);
        }
      // Rusticated base.
      c.fillStyle = '#cbbd9e';
      c.fillRect(0, Y(0.8), w, 0.8 * P);
    });
    kit.walls(batch, mat, [[ring]], 0, H, { bay: 3.4, storey: H / 2 });
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
    const glass = kit.mat('#252c34', { roughness: 0.15, metalness: 0.3 }),
      frameC = kit.mat('#f1e8d2'),
      stuccoD = kit.mat('#d8c9a8');
    const ST = [0, H * 0.27, H * 0.52, H * 0.76, H];
    // 3D mullion-and-transom windows matching the painted panels (one per 3.4 m bay).
    const winEdges = (r, minLen = 2.5) => {
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          bb = r[(k + 1) % r.length];
        const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
        if (l < minLen) continue;
        const n = Math.max(1, Math.round(l / 3.4));
        for (let st = 0; st < 4; st++) {
          const z0 = ST[st] + (st ? 0.4 : 1.0),
            z1 = ST[st + 1] - 1.3;
          winKit.row(a, bb, z0 + 0.35, n, 0, {
            w: Math.min(1.35, (l / n) * 0.38),
            h: z1 - z0 - 0.7,
            head: st === 3 ? 'flat' : 'lintel',
            glass,
            sur: frameC,
            bar: frameC,
            f: 0.12,
            depth: 0.1,
          });
        }
      }
    };
    winEdges(ring);
    kit.cornice(batch, stuccoD, ring, 0, { height: 0.8, projection: 0.12, steps: 1 });
    for (const st of [1, 2, 3])
      kit.cornice(batch, stuccoD, ring, ST[st] - 0.12, { height: 0.12, projection: 0.08 });
    // Bracketed eaves cornice.
    const ro = kit.offsetRing(ring, 0.6);
    const cornice = kit.mat('#ddd0b2');
    kit.walls(batch, cornice, [[ro]], H - 0.5, H);
    kit.cap(batch, cornice, [[ro, ring.slice().reverse()]], H - 0.5, { down: true });
    // Brackets along the cornice.
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        bb = ring[(k + 1) % ring.length];
      const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      const ang = Math.atan2(bb[1] - a[1], bb[0] - a[0]);
      const n = Math.floor(l / 1.2);
      for (let j = 1; j < n; j++) {
        const t = j / n;
        const x = a[0] + (bb[0] - a[0]) * t + Math.sin(ang) * 0.3,
          y = a[1] + (bb[1] - a[1]) * t - Math.cos(ang) * 0.3;
        kit.box(batch, cornice, x, y, H - 1.1, 0.25, 0.6, 0.6, ang);
      }
    }
    // Slate roof: hipped over the oriented frame (low enough to stay under the data height).
    const fr = kit.ringFrame(ring);
    const slate = kit.roof('slate', 2);
    // Slate roof following the footprint: slopes from the eaves to an inset flat top.
    const inner = kit.offsetRing(ring, -1.8);
    const rise = 2.5;
    for (let k = 0; k < ro.length; k++) {
      const j = (k + 1) % ro.length;
      batch.quad(
        slate,
        [ro[k][0], ro[k][1], H],
        [ro[j][0], ro[j][1], H],
        [inner[j][0], inner[j][1], H + rise],
        [inner[k][0], inner[k][1], H + rise],
        [0, 0],
        [Math.hypot(ro[j][0] - ro[k][0], ro[j][1] - ro[k][1]) / 3, 0],
        [Math.hypot(inner[j][0] - inner[k][0], inner[j][1] - inner[k][1]) / 3, 1],
        [0, 1],
      );
    }
    kit.cap(batch, kit.mat('#5d6268'), [[inner]], H + rise);

    // Chimney stacks.
    for (const t of [0.2, 0.6]) {
      const p = inner[Math.floor(t * inner.length)];
      kit.box(batch, kit.mat('#d9cbab'), p[0], p[1], H + 1, 0.9, 2.0, rise + 1.5, fr.angle);
      kit.box(batch, stuccoD, p[0], p[1], H + rise + 2.5, 1.1, 2.2, 0.25, fr.angle);
      for (const d of [-0.6, 0, 0.6]) {
        const c = Math.cos(fr.angle + Math.PI / 2),
          sn = Math.sin(fr.angle + Math.PI / 2);
        const pm = kit.lathe(
          kit.mat('#9a5a3e'),
          [
            [0.17, 0],
            [0.13, 0.6],
            [0.16, 0.7],
          ],
          { x: p[0] + c * d, y: p[1] + sn * d, z: H + rise + 2.75, segments: 8 },
        );
        pm.updateMatrix();
        batch.addGeometry(pm.material, pm.geometry, pm.matrix);
      }
    }

    // Canted full-height entrance bay at the centre of the north (street) frontage.
    let best = null;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        bb = ring[(k + 1) % ring.length];
      const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      const nx = (bb[1] - a[1]) / l,
        ny = -(bb[0] - a[0]) / l; // outward normal of a CCW ring
      if (l > 6 && ny > 0.8 && (!best || (a[1] + bb[1]) / 2 > best.my))
        best = { a, b: bb, l, nx, ny, my: (a[1] + bb[1]) / 2 };
    }
    if (best) {
      const { a, b: bb, l, nx, ny } = best;
      const tx = (bb[0] - a[0]) / l,
        ty = (bb[1] - a[1]) / l;
      const mx = (a[0] + bb[0]) / 2,
        my = (a[1] + bb[1]) / 2;
      const W = Math.min(4.6, l * 0.42),
        D = 1.3;
      const P = (s, d) => [mx + tx * s + nx * d, my + ty * s + ny * d];
      // CCW outline of the bay: wall base corners and the canted front.
      const bay = [
        P(-W / 2, -0.05),
        P(W / 2, -0.05),
        P(W / 2 - D * 0.8, D),
        P(-W / 2 + D * 0.8, D),
      ].reverse();
      let bayR = bay;
      if (kit.ringArea(bayR) < 0) bayR = bayR.slice().reverse();
      kit.walls(batch, mat, [[bayR]], 0, H - 0.5, { bay: 1.7, storey: H / 2 });
      kit.cap(batch, cornice, [[bayR]], H - 0.5);
      // Oriel windows on the three canted faces (upper storeys), sill bands.
      for (let k = 0; k < bayR.length; k++) {
        const a2 = bayR[k],
          b2 = bayR[(k + 1) % bayR.length];
        const l2 = Math.hypot(b2[0] - a2[0], b2[1] - a2[1]);
        const e2 = winKit.edge(a2, b2);
        if (e2.nx * nx + e2.ny * ny < -0.2 || l2 < 1) continue;
        for (let st = 1; st < 4; st++) {
          const z0 = ST[st] + 0.4,
            z1 = ST[st + 1] - 1.3;
          winKit.row(a2, b2, z0 + 0.35, 1, 0.2, {
            w: Math.min(1.6, l2 * 0.6),
            h: z1 - z0 - 0.7,
            head: 'lintel',
            glass,
            sur: frameC,
            bar: frameC,
            f: 0.12,
            bars: 2,
          });
          winKit.band(a2, b2, ST[st] - 0.15, 0.3, 0.15, stuccoD);
        }
      }
      // Entrance door at the foot of the bay.
      const dp = P(0, D + 0.03);
      kit.box(batch, kit.mat('#3a2a22'), dp[0], dp[1], 0, 1.6, 0.06, 2.9, Math.atan2(ty, tx));
      winKit.row(P(-1.4, D + 0.02), P(1.4, D + 0.02), 0.3, 1, 0.2, {
        w: 1.5,
        h: 2.4,
        head: 'arch',
        glass: kit.mat('#3a2a22'),
        sur: stuccoD,
        bar: kit.mat('#2a1c14'),
        f: 0.25,
      });
      for (let k = 0; k < 2; k++) {
        const sp = P(0, D + 0.35 + (1 - k) * 0.3);
        kit.box(
          batch,
          kit.mat('#b8b0a2'),
          sp[0],
          sp[1],
          k * 0.15,
          2.4 + (1 - k) * 0.4,
          0.3,
          0.15,
          Math.atan2(ty, tx),
        );
      }
      kit.box(
        batch,
        cornice,
        P(0, D + 0.15)[0],
        P(0, D + 0.15)[1],
        3.0,
        2.6,
        0.3,
        0.35,
        Math.atan2(ty, tx),
      );
      // Small lead cap on the bay.
      const capGeo = new THREE.ConeGeometry(W * 0.45, 1.6, 6).rotateX(Math.PI / 2);
      const m = new THREE.Mesh(capGeo, kit.mat('lead'));
      const cp = P(0, D * 0.4);
      m.position.set(cp[0], cp[1], H - 0.5 + 0.8);
      m.rotation.z = Math.atan2(ty, tx) + Math.PI / 6;
      g.add(m);
    }
    g.add(batch.toGroup('royal_college_of_organists'));
    return g;
  },
};
