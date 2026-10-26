// Whiteleys / The Whiteley, Queensway, Bayswater. Edwardian department store by
// John Belcher and J. J. Joass (1911), extended north by W. Curtis Green
// (1925-27) in the same style; Grade II listed. Long Portland stone Queensway
// frontage with a giant colonnade framing large upper-floor glazing above the
// shopfronts, an attic and balustrade, the stone tower and cupola over the
// south-east corner entrance (Queensway / Porchester Gardens) and the
// re-modelled cupola at the northern corner. Behind the retained facade, Foster +
// Partners' 2016-25 scheme added residential/hotel storeys around a central
// courtyard, keeping the glass dome over the old atrium.
export default {
  id: 'whiteleys',
  name: 'Whiteleys (The Whiteley)',
  claims: ['bad19412-57bd-4789-b9cc-12a13f944ba4'],
  references: [
    {
      title: 'Whiteleys - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Whiteleys',
      used_for: 'Belcher & Joass 1911, extension 1925-27, retained 1911 facade',
    },
    {
      title: 'The Whiteley - Foster + Partners',
      url: 'https://fosterandpartners.com/projects/the-whiteley',
      used_for:
        'Grade II listed, Curtis Green phase, remodelled cupola on the northern corner, restored Queensway facade glazing',
    },
    {
      title: 'Whiteleys - AKT II',
      url: 'https://akt-uk.com/projects/whiteleys',
      used_for: 'listed south-eastern corner with stone cupola and stone tower over the entrance',
    },
    {
      title: 'The Whiteley - Radmat case study',
      url: 'https://radmat.com/?p=18745',
      used_for: 'colonnaded facade and rooftop cupolas',
    },
    {
      title: 'Whiteleys shopping centre report - GLA',
      url: 'https://data.london.gov.uk/download/2zw6q/5e02b63e-524f-44fc-8e61-938bf8699a15/whiteleys_shopping_centre_report.pdf',
      used_for:
        'retained facade, clock and glass dome, new central courtyard, up to 10 upper levels',
    },
    {
      title: 'Tour of architectural sculpture - Victorian Web',
      url: 'https://victorianweb.org/victorian/sculpture/architectural/102.html',
      used_for:
        'Belcher & Joass building carries the Summer and Winter sculpture by Paul Gasq (not modelled)',
    },
    {
      title: 'The Whiteley in London - Baunetz Wissen',
      url: 'https://www.baunetzwissen.de/bauen-im-bestand/objekte/wohnen/the-whiteley-in-london-10396176',
      used_for:
        'Portland stone construction with large upper-floor windows, Grade II listing, extension 1925-27',
    },
  ],
  notes:
    'Overture height (14 m) replaced: facade cornice 22 m, attic 25.5 m, rear new-build blocks 30-36 m ' +
    '(storey counts from planning reports, exact profile unknown). Queensway, Porchester Gardens and Redan Place ' +
    'faces in 3D: bronze shopfronts with fascia, string course, giant-order columns on pedestals with pilaster ' +
    'responds framing tall bronze-framed glazing, architrave/frieze/dentilled cornice, attic windows and a ' +
    'balustrade with urn pedestals; corner towers with quoins, arched windows, clock and colonnaded cupolas. ' +
    'Column order (shown with a generic flared capital), bay rhythm (7.5 m), cupola proportions, dome position, ' +
    'the colour of the cupola roofs and the rear blocks (storey bands, glass balustrade, roof plant) are estimates ' +
    'from textual descriptions only; the Gasq "Summer and Winter" sculpture is not modelled',
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const O = [871.6, 827.92],
      A = (100 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // u: north along Queensway, v: west, into the block
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const b = new kit.MeshBatch();
    const clip = (ring, f) => {
      const out = [];
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const fp = f(p),
          fq = f(q);
        if (fp >= 0) out.push(p);
        if (fp >= 0 !== fq >= 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    const toW = (r) => {
      let w = r.map(([u, v]) => W(u, v));
      if (kit.ringArea(w) < 0) w = w.slice().reverse();
      return w;
    };
    const box = (u, v, z0, du, dv, h, m) => {
      const [x, y] = W(u, v);
      kit.box(b, m, x, y, z0, du, dv, h, A);
    };
    const add = (geo, m, u, v, z) => {
      const [x, y] = W(u, v);
      b.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(A).setPosition(x, y, z));
      geo.dispose();
    };
    // kit.windowRow with round / segmental heads built as vertical glass sectors and
    // projecting archivolts with a keystone (lintel, pediment and plain heads pass through).
    const archRow = (batch, a, c, z, opts) => {
      const head = opts.head;
      if (head !== 'arch' && head !== 'segment') return kit.windowRow(batch, a, c, z, opts);
      const cs = kit.windowRow(batch, a, c, z, { ...opts, head: 'none' });
      const w = opts.width ?? 1.2,
        h = opts.height ?? 2.0,
        d = opts.depth ?? 0.12;
      const glassM = opts.glass ?? kit.mat('dark_glass'),
        trimM = opts.sill ?? opts.frame ?? kit.mat('white');
      const L = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
      const ux = (c[0] - a[0]) / L,
        uy = (c[1] - a[1]) / L;
      const seg = head === 'arch' ? Math.PI : Math.PI / 2.5;
      const R = head === 'arch' ? w / 2 : w / 2 / Math.sin(seg / 2);
      const zc = z + h - (head === 'arch' ? 0 : R * Math.cos(seg / 2));
      const X = new THREE.Vector3(ux, uy, 0),
        Y = new THREE.Vector3(0, 0, 1),
        Z = new THREE.Vector3(uy, -ux, 0);
      const gl = new THREE.CircleGeometry(R, 12, Math.PI / 2 - seg / 2, seg);
      const tor = new THREE.TorusGeometry(R + 0.06, 0.08, 4, 12, seg).rotateZ(
        Math.PI / 2 - seg / 2,
      );
      const key = new THREE.BoxGeometry(0.28, 0.34, d * 1.6);
      const m = new THREE.Matrix4();
      for (const [cx, cy] of cs) {
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * 0.03, cy + Z.y * 0.03, zc);
        batch.addGeometry(glassM, gl, m);
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * d * 0.8, cy + Z.y * d * 0.8, zc);
        batch.addGeometry(trimM, tor, m);
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * d * 0.8, cy + Z.y * d * 0.8, zc + R + 0.08);
        batch.addGeometry(trimM, key, m);
      }
      [gl, tor, key].forEach((q) => q.dispose());
      return cs;
    };
    const stone = kit.mat('#e3dccb');
    const stoneDark = kit.mat('#cfc6b2');
    const lead = kit.mat('#5f676b', { roughness: 0.6, metalness: 0.3 });
    const flat = kit.mat('#77766f');
    const glassDome = kit.mat('#9fb6c2', { roughness: 0.15, metalness: 0.3 });

    const H = 22,
      ATT = 25.5;
    const sideM = kit.facade('portland_stone', 0);
    const rearM = kit.facade('modern_clad', 1);

    let lr = byId['bad19412-57bd-4789-b9cc-12a13f944ba4'].polys[0][0].map(toL);
    if (kit.ringArea(lr) < 0) lr = lr.slice().reverse();
    const FD = 22; // depth of the historic range behind the Queensway facade
    const front = clip(lr, (p) => FD - p[1]);
    // historic range walls: Portland stone; the Queensway, Porchester Gardens and
    // Redan Place faces carry the 3D order, glazing and shopfronts below.
    const stoneWall = kit.paintedMaterial('whiteleys:stone', 256, 256, (c, w, h) => {
      c.fillStyle = '#e4ddcc';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.91);
      for (let k = 0; k < 1200; k++) {
        c.fillStyle = `rgba(120,110,90,${r() * 0.07})`;
        c.fillRect(r() * w, r() * h, 2, 2);
      }
      c.fillStyle = 'rgba(140,128,105,0.35)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 2); // ashlar courses (0.5 m)
      for (let y = 0; y < h; y += 64) {
        c.fillRect(64, y, 2, 32);
        c.fillRect(192, y + 32, 2, 32);
      }
    });
    for (let k = 0; k < front.length; k++) {
      const p = front[k],
        q = front[(k + 1) % front.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 0.1) continue;
      const P = W(...p),
        Q = W(...q);
      if (p[1] > FD - 0.1 && q[1] > FD - 0.1) {
        kit.walls(b, sideM, [[[P, Q]]], 0, ATT, { bay: 3.75, storey: 3.6 });
        continue;
      }
      b.quad(
        stoneWall,
        [P[0], P[1], 0],
        [Q[0], Q[1], 0],
        [Q[0], Q[1], ATT],
        [P[0], P[1], ATT],
        [0, 0],
        [len / 4, 0],
        [len / 4, ATT / 4],
        [0, ATT / 4],
      );
    }
    kit.cap(b, flat, [[toW(front)]], ATT);
    const bronze = kit.mat('#5e4a33', { roughness: 0.45, metalness: 0.6 });
    const shopGlass = kit.mat('#46565e', { roughness: 0.1, metalness: 0.3 });
    const upperGlass = kit.mat('#5a6f7b', { roughness: 0.12, metalness: 0.3 });
    const fasciaM = kit.mat('#23362e', { roughness: 0.5 });
    // band along a local edge p -> q at outward offset `off`, z0..z0+h, projecting `dep`
    const band = (p, q, off, z0, h, dep, m) => {
      const L = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const nu = (q[1] - p[1]) / L,
        nv = -(q[0] - p[0]) / L; // outward (right-hand) normal in local coords
      const [x, y] = W(
        (p[0] + q[0]) / 2 + nu * (off + dep / 2),
        (p[1] + q[1]) / 2 + nv * (off + dep / 2),
      );
      kit.box(b, m, x, y, z0, L, dep, h, A + Math.atan2(q[1] - p[1], q[0] - p[0]));
    };
    const lerpL = (p, q, t) => [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
    const facadeSegs = [
      [
        [12.0, 0.29],
        [41.0, 1.0],
      ],
      [
        [41.0, 1.0],
        [159.5, 0.64],
      ],
      [
        [1.33, 22],
        [0.72, 12.2],
      ],
      [
        [170.15, 11],
        [169.8, 22],
      ],
    ];
    const urnG = new THREE.LatheGeometry(
      [
        [0, 0],
        [0.32, 0],
        [0.22, 0.15],
        [0.36, 0.5],
        [0.3, 0.75],
        [0.12, 0.85],
        [0.18, 1.0],
        [0, 1.05],
      ].map(([r, h]) => new THREE.Vector2(r, h)),
      10,
    ).rotateX(Math.PI / 2);
    for (const [p, q] of facadeSegs) {
      const L = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const n = Math.max(1, Math.round(L / 7.5));
      const M = 0.7;
      const a = W(...p),
        c = W(...q);
      const nrm = [(c[1] - a[1]) / L, -(c[0] - a[0]) / L];
      // plinth, shopfronts with stall risers, fascia and cornice over the ground floor
      band(p, q, 0, 0, 0.5, 0.25, stoneDark);
      archRow(b, a, c, 0.5, {
        count: n,
        margin: M,
        width: 7.5 * (L / n / 7.5) - 2.0,
        height: 3.7,
        bars: 2,
        glass: shopGlass,
        frame: bronze,
        sill: stoneDark,
        head: 'none',
        depth: 0.2,
      });
      band(p, q, 0, 4.4, 0.9, 0.18, fasciaM);
      band(p, q, 0, 5.3, 0.25, 0.3, kit.mat('gold'));
      band(p, q, 0, 5.55, 0.65, 0.45, stoneDark); // string course
      // giant order: columns at the bay divisions framing the tall bronze-framed glazing
      const pa = lerpL(p, q, M / L),
        pb = lerpL(p, q, 1 - M / L);
      kit.colonnade(b, stone, W(...pa), W(...pb), 6.8, 12.4, {
        count: n + 1,
        radius: 0.55,
        offset: 0.75,
        capital: 'corinthian',
      });
      for (let j = 0; j <= n; j++) {
        const [x, y] = W(...lerpL(pa, pb, j / n));
        const ang = A + Math.atan2(q[1] - p[1], q[0] - p[0]);
        kit.box(b, stoneDark, x + nrm[0] * 0.75, y + nrm[1] * 0.75, 6.2, 1.5, 1.5, 0.6, ang); // pedestal
        kit.box(b, stoneDark, x + nrm[0] * 0.75, y + nrm[1] * 0.75, 19.0, 1.6, 1.6, 0.3, ang); // abacus
        kit.box(b, stoneDark, x + nrm[0] * 0.1, y + nrm[1] * 0.1, 6.8, 1.2, 0.2, 12.4, ang); // pilaster
      }
      archRow(b, a, c, 7.0, {
        count: n,
        margin: M,
        width: L / n - 2.2,
        height: 11.6,
        bars: 3,
        glass: upperGlass,
        frame: bronze,
        sill: stone,
        head: 'none',
        depth: 0.25,
      });
      // entablature: architrave, frieze, dentilled cornice
      band(p, q, 0, 19.2, 0.9, 0.55, stoneDark);
      band(p, q, 0, 20.1, 1.0, 0.35, stone);
      band(p, q, 0, 21.1, 0.25, 0.85, stoneDark);
      band(p, q, 0, 21.35, 0.65, 1.15, stone);
      for (let t = 0.2; t < L - 0.1; t += 0.45) {
        const d0 = lerpL(p, q, t / L),
          d1 = lerpL(p, q, (t + 0.22) / L);
        band(d0, d1, 0.85, 21.05, 0.3, 0.2, stone);
      }
      // attic: paired small windows per bay, balustrade with pedestals at the bays
      archRow(b, a, c, 22.7, {
        count: 2 * n,
        margin: M + 0.8,
        width: 1.5,
        height: 1.7,
        bars: 1,
        glass: shopGlass,
        frame: kit.mat('white'),
        sill: stone,
        head: 'lintel',
        depth: 0.15,
      });
      const pa2 = a,
        pb2 = c;
      kit.balustrade(
        b,
        stone,
        [
          [pa2[0] + nrm[0] * 0.25, pa2[1] + nrm[1] * 0.25],
          [pb2[0] + nrm[0] * 0.25, pb2[1] + nrm[1] * 0.25],
        ],
        ATT,
        { height: 1.1, spacing: 0.38 },
      );
      for (let j = 0; j <= n; j++) {
        const t = (M + ((L - 2 * M) * j) / n) / L;
        const [x, y] = W(...lerpL(p, q, t));
        kit.box(
          b,
          stoneDark,
          x + nrm[0] * 0.25,
          y + nrm[1] * 0.25,
          ATT,
          0.9,
          0.9,
          1.5,
          A + Math.atan2(q[1] - p[1], q[0] - p[0]),
        );
        b.addGeometry(
          stone,
          urnG,
          new THREE.Matrix4().makeTranslation(x + nrm[0] * 0.25, y + nrm[1] * 0.25, ATT + 1.5),
        );
      }
    }
    // central feature: raised attic over the middle bays
    box(85, 1.5, ATT, 22, 3, 3.5, stone);
    box(85, 0.3, ATT + 3.5, 23, 3.6, 0.6, stoneDark);
    // Queensway street lamps on the pavement
    if (placeAssets) {
      const lamps = [];
      const hd = Math.atan2(-sa, -ca); // arm towards -v (the carriageway)
      for (let u = 20; u < 160; u += 22) lamps.push([...W(u, -6.0), hd]);
      g.add(placeAssets('street_lamp', lamps, { name: 'whiteleys:lamps' }));
    }

    // Rear new-build blocks stepping up behind the facade, around a central courtyard.
    const rear = clip(lr, (p) => p[1] - FD);
    const blocks = [
      { f: (p) => 62 - p[0], h: 33 },
      { f: (p) => p[0] - 108, h: 36 },
      { f: (p) => ((p[0] - 62) * (108 - p[0]) >= 0 ? p[1] - 62 : -1), h: 30, mid: true },
    ];
    for (const bl of blocks) {
      let r;
      if (bl.mid)
        r = clip(
          clip(
            clip(rear, (p) => p[0] - 62),
            (p) => 108 - p[0],
          ),
          (p) => p[1] - 64,
        );
      else r = clip(rear, bl.f);
      if (r.length < 3) continue;
      const wr = toW(r);
      kit.walls(b, rearM, [[wr]], 0, bl.h - 3, { bay: 3.4, storey: 3.2 });
      kit.walls(b, kit.mat('#8f9599'), [[kit.offsetRing(wr, -2.0)]], bl.h - 3, bl.h);
      kit.cap(b, flat, [[wr]], bl.h - 3);
      kit.cap(b, flat, [[kit.offsetRing(wr, -2.0)]], bl.h);
      for (let z = 3.6; z < bl.h - 3.2; z += 3.2)
        kit.cornice(b, kit.mat('#d8d3c6'), wr, z, { height: 0.3, projection: 0.35 });
      kit.cornice(b, kit.mat('#d8d3c6'), wr, bl.h - 3.4, { height: 0.4, projection: 0.5 });
      kit.walls(
        b,
        kit.mat('#a9bcc6', { roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0.55 }),
        [[wr]],
        bl.h - 3,
        bl.h - 1.9,
      );
      {
        const fr = kit.ringFrame(kit.offsetRing(wr, -2.0));
        kit.box(
          b,
          kit.mat('#8f9599'),
          fr.cx,
          fr.cy,
          bl.h,
          Math.min(12, fr.length * 0.4),
          Math.min(6, fr.width * 0.5),
          2.2,
          fr.angle,
        );
      }
    }
    // low courtyard infill (retail) between the rear blocks, with the retained glass dome
    {
      const r = clip(
        clip(
          clip(rear, (p) => p[0] - 62),
          (p) => 108 - p[0],
        ),
        (p) => 64 - p[1],
      );
      const wr = toW(r);
      kit.walls(b, sideM, [[wr]], 0, 12, { bay: 3.6, storey: 3.4 });
      kit.cap(b, kit.mat('#9aa39a'), [[wr]], 12);
      const R = 9.5;
      add(new THREE.CylinderGeometry(R, R, 2.4, 24).rotateX(Math.PI / 2), stone, 85, 43, 13.2);
      const dome = new THREE.SphereGeometry(R, 24, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      dome.scale(1, 1, 0.7);
      add(dome, glassDome, 85, 43, 14.4);
      for (let k = 0; k < 12; k++) {
        const a = (k / 12) * Math.PI * 2;
        const rib = new THREE.BoxGeometry(0.25, 0.25, 7).rotateY(-0.9);
        const m = new THREE.Matrix4()
          .makeRotationZ(a)
          .multiply(new THREE.Matrix4().makeTranslation(R * 0.55, 0, 3.2));
        rib.applyMatrix4(m);
        add(rib, lead, 85, 43, 14.4);
      }
      add(new THREE.CylinderGeometry(1.2, 1.4, 1.6, 12).rotateX(Math.PI / 2), lead, 85, 43, 21.8);
    }

    // Corner tower with cupola (south-east, over the entrance) and the northern cupola.
    const cupola = (u, v, s, base, scale, clock) => {
      // square stone tower rising above the attic
      box(u, v, 0, s, s, base, stone);
      box(u, v, base - 1.0, s + 1.2, s + 1.2, 1.0, stoneDark);
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ])
        box(
          u + (du * s) / 2.2,
          v + (dv * s) / 2.2,
          base,
          1.4 * scale,
          1.4 * scale,
          2.5 * scale,
          stoneDark,
        );
      if (clock) {
        const face = kit.paintedMaterial('whiteleys:clock', 128, 128, (c, w, h) => {
          c.fillStyle = '#e4ddcc';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#f5f1e6';
          c.beginPath();
          c.arc(64, 64, 56, 0, 7);
          c.fill();
          c.strokeStyle = '#1d2a33';
          c.lineWidth = 6;
          c.stroke();
          c.fillStyle = '#1d2a33';
          for (let k = 0; k < 12; k++) {
            const a = (k * Math.PI) / 6;
            c.fillRect(64 + Math.cos(a) * 46 - 3, 64 + Math.sin(a) * 46 - 3, 6, 6);
          }
          c.lineWidth = 5;
          c.beginPath();
          c.moveTo(64, 64);
          c.lineTo(64, 24);
          c.moveTo(64, 64);
          c.lineTo(92, 74);
          c.stroke();
        });
        for (const [pu, pv, du, dv] of [
          [u, v - s / 2 - 0.05, 3.6, 0.05],
          [u - s / 2 - 0.05, v, 0.05, 3.6],
        ])
          box(pu, pv, base - 6, du, dv, 3.6, face);
      }
      // drum with ring of columns, dome and lantern
      const R = (s / 2) * 0.82;
      add(
        new THREE.CylinderGeometry(R + 0.4, R + 0.4, 0.8, 24).rotateX(Math.PI / 2),
        stoneDark,
        u,
        v,
        base + 0.4,
      );
      add(
        new THREE.CylinderGeometry(R * 0.78, R * 0.78, 5.2 * scale, 16).rotateX(Math.PI / 2),
        kit.mat('#3a454c'),
        u,
        v,
        base + 0.8 + 2.6 * scale,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        add(
          new THREE.CylinderGeometry(0.32 * scale, 0.36 * scale, 5.2 * scale, 8).rotateX(
            Math.PI / 2,
          ),
          stone,
          u + Math.cos(a) * R,
          v + Math.sin(a) * R,
          base + 0.8 + 2.6 * scale,
        );
      }
      const top = base + 0.8 + 5.2 * scale;
      add(
        new THREE.CylinderGeometry(R + 0.5, R + 0.5, 1.0, 24).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        top + 0.5,
      );
      const dome = new THREE.SphereGeometry(R, 24, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      dome.scale(1, 1, 1.15);
      add(dome, lead, u, v, top + 1.0);
      add(
        new THREE.CylinderGeometry(0.8 * scale, 0.9 * scale, 2.2 * scale, 8).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        top + 1 + R * 1.15 + 1.1 * scale,
      );
      add(
        new THREE.ConeGeometry(0.9 * scale, 1.6 * scale, 8).rotateX(Math.PI / 2),
        lead,
        u,
        v,
        top + 1 + R * 1.15 + 2.2 * scale + 0.8 * scale,
      );
      add(
        new THREE.SphereGeometry(0.35 * scale, 8, 6),
        kit.mat('gold'),
        u,
        v,
        top + 1 + R * 1.15 + 3.4 * scale,
      );
    };
    cupola(5.8, 5.8, 12.2, 32, 1.0, true);
    cupola(165, 5.3, 11, 29, 0.85, false);
    // tower elevations: arched corner entrance, tall arched windows, quoins
    for (const [u, v, s, base, faces] of [
      [5.8, 5.8, 12.2, 32, ['front', 'south']],
      [165, 5.3, 11, 29, ['front', 'north']],
    ]) {
      const h = s / 2 + 0.02;
      const edges = {
        front: [W(u - h, v - h), W(u + h, v - h)],
        south: [W(u - h, v + h), W(u - h, v - h)],
        north: [W(u + h, v - h), W(u + h, v + h)],
      };
      for (const f of faces) {
        const [a, c] = edges[f];
        const wo = { glass: upperGlass, frame: bronze, sill: stoneDark, depth: 0.25, margin: 1.2 };
        archRow(b, a, c, 0.3, { ...wo, count: 1, width: 4.2, height: 4.4, head: 'arch', bars: 2 });
        archRow(b, a, c, 7.2, { ...wo, count: 2, width: 2.4, height: 9.6, head: 'arch', bars: 3 });
        archRow(b, a, c, 22.6, {
          ...wo,
          count: 2,
          width: 1.6,
          height: 2.2,
          head: 'pediment',
          bars: 1,
        });
      }
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [-1, 1],
        [1, 1],
      ])
        for (let z = 6.2; z < base - 1.2; z += 1.0)
          box(
            u + du * (h - 0.3),
            v + dv * (h - 0.3),
            z,
            ((z | 0) % 2 ? 1.4 : 0.9) + 0.1,
            ((z | 0) % 2 ? 0.9 : 1.4) + 0.1,
            0.5,
            stoneDark,
          );
      box(u, v, base - 7.6, s + 0.8, s + 0.8, 0.6, stoneDark); // string course under the clock stage
      box(u, v, 6.0, s + 0.6, s + 0.6, 0.6, stoneDark);
    }
    // entrance canopy at the Queensway / Porchester Gardens corner
    box(5.8, -1.6, 4.9, 7.5, 2.6, 0.35, fasciaM);
    box(-1.6, 5.8, 4.9, 2.6, 7.5, 0.35, fasciaM);
    g.add(b.toGroup('whiteleys'));
    return g;
  },
};
