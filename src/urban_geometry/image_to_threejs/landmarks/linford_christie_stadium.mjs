// Linford Christie Stadium, Artillery Way off Du Cane Road, Wormwood Scrubs (opened 1967 as
// the West London Stadium, renamed 1993). Council athletics stadium, home of Thames Valley
// Harriers: an eight-lane 400 m synthetic track with field-event areas, an elevated
// spectator stand over changing rooms, a single-storey pavilion block, the Harriers'
// clubhouse, a covered practice straight and floodlit training areas.
export default {
  id: 'linford_christie_stadium',
  name: 'Linford Christie Stadium',
  claims: [
    'c1f25d0e-32f2-487f-bd1d-fa6a3c3eee8e',
    '80554d52-cf6f-4712-a15d-fe2128bfc713',
    '1706f9b7-8cf4-42ba-bd72-cab6fa404a6e',
    'b33da4fb-cea8-4437-9258-4f1263ae7428',
  ],
  references: [
    {
      title: 'Linford Christie Stadium - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Linford_Christie_Stadium',
      used_for:
        'opened 1967 as West London Stadium, renamed 1993, eight-lane 400 m track, two 100 m straights, elevated stand, Thames Valley Harriers, location',
    },
    {
      title: 'Linford Christie Outdoor Sports Centre - LBHF',
      url: 'https://www.lbhf.gov.uk/sports-and-parks/leisure-centres/linford-christie-outdoor-sports-centre',
      used_for: 'stand, floodlit training areas and changing rooms',
    },
    {
      title: 'Linford Christie Stadium Proposal - LBHF Appendix 2',
      url: 'https://democracy.lbhf.gov.uk/documents/s122549/Appendix%202%20-%20Linford%20Christie%20Stadium%20Proposal.pdf',
      used_for: 'condition of the track and the tired viewing stand with space beneath',
    },
  ],
  notes:
    'Track geometry is a standard 400 m layout (36.5 m inner radius, 84.39 m straights, 8 x 1.22 m lanes) fitted ' +
    'to the mapped track area; the red surface itself comes from the ground layer. Stand rake, roof height ' +
    '(~10 m), seat rows, the pavilion and clubhouse heights, the practice-straight roof and the number and ' +
    'height (22 m) of floodlight masts are assumptions; Overture h=39 m for the stand is wrong.',
  build({ THREE, kit, buildings, scene }) {
    const g = new THREE.Group();
    // ---- local helpers (edge frames, boxes along edges, prisms, glazing) ----
    const B = new kit.MeshBatch();
    const ccw = (r) => {
      r = r.slice();
      if (kit.ringArea(r) < 0) r.reverse();
      return r;
    };
    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          a,
          b,
          k,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box along edge e: s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, col) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(
        B,
        m,
        c[0],
        c[1],
        z0,
        Math.max(0.01, s1 - s0),
        Math.max(0.01, d1 - d0),
        z1 - z0,
        e.ang,
        col,
      );
    };
    const quad = (m, p, q, z0, z1, d = 0) =>
      B.quad(
        m,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    const prism = (wall, roof, ring, z0, z1, o = {}) => {
      kit.walls(B, wall, [[ring]], z0, z1, o);
      if (roof) kit.cap(B, roof, [[ring]], z1);
    };
    const parapet = (m, ring, z, h = 0.9, t = 0.3) => {
      const inn = kit.offsetRing(ring, -t).reverse();
      kit.walls(B, m, [[ring]], z, z + h, { bay: 1e6 });
      kit.walls(B, m, [[inn]], z, z + h, { bay: 1e6 });
      kit.cap(B, m, [[ring, inn]], z + h);
    };
    // Lofted band between two rings with equal vertex counts (sloped walls / roofs).
    const loft = (m, r0, z0, r1, z1) => {
      for (let k = 0; k < r0.length; k++) {
        const j = (k + 1) % r0.length;
        B.add(
          m,
          [
            [r0[k][0], r0[k][1], z0],
            [r0[j][0], r0[j][1], z0],
            [r1[j][0], r1[j][1], z1],
            [r1[k][0], r1[k][1], z1],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
    };
    // Windows on every edge longer than minLen, storey by storey.
    const winRows = (ring, z0, n, st, opts, minLen = 4, filter) => {
      for (let s = 0; s < n; s++)
        for (const e of edgesOf(ring)) {
          if (e.len < minLen || (filter && !filter(e, s))) continue;
          kit.windowRow(B, e.a, e.b, z0 + s * st, typeof opts === 'function' ? opts(s, e) : opts);
        }
    };
    // Continuous glazing band with mullions on every edge of a ring.
    const ribbon = (ring, z0, z1, glass, mull, pitch = 1.5, minLen = 0.5, filter) => {
      for (const e of edgesOf(ring)) {
        if (e.len < minLen || (filter && !filter(e))) continue;
        quad(glass, e.a, e.b, z0, z1);
        const n = Math.max(1, Math.round(e.len / pitch));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(mull, e, Math.max(0, s - 0.05), Math.min(e.len, s + 0.05), 0, 0.12, z0, z1);
        }
      }
    };
    const frameAt = (f, u, v) => [
      f.cx + Math.cos(f.angle) * u - Math.sin(f.angle) * v,
      f.cy + Math.sin(f.angle) * u + Math.cos(f.angle) * v,
    ];
    const signMat = (key, text, bg, fg, font = 'bold 40px sans-serif', w = 512, h = 64) =>
      kit.paintedMaterial(
        key,
        w,
        h,
        (c, W, H) => {
          c.fillStyle = bg;
          c.fillRect(0, 0, W, H);
          c.fillStyle = fg;
          c.font = font;
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(text, W / 2, H / 2 + 2);
        },
        { roughness: 0.6 },
      );
    const cyl = (m, x, y, z0, r0, r1, h, seg = 16) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      B.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    // Rooftop plant boxes scattered within a ring's oriented frame.
    const plantBoxes = (ring, z, rnd, n, m, spread = 0.55) => {
      const f = kit.ringFrame(ring);
      for (let i = 0; i < n; i++) {
        const p = frameAt(f, (rnd() - 0.5) * f.length * spread, (rnd() - 0.5) * f.width * spread);
        kit.box(B, m, p[0], p[1], z, 2 + rnd() * 3, 1.5 + rnd() * 2, 1.2 + rnd() * 1.5, f.angle);
      }
    };
    // ---- end helpers ----
    const rec = (p) => ccw(buildings.find((b) => b.id.startsWith(p)).polys[0][0]);
    const stand = rec('c1f25d0e'),
      pav = rec('80554d52'),
      club = rec('1706f9b7'),
      shed = rec('b33da4fb');
    const conc = kit.mat('concrete');
    const brick = kit.mat('#8d5b47', { roughness: 0.9 });
    const roofM = kit.mat('#7e8285', { roughness: 0.5, metalness: 0.4 });
    const seat = kit.mat('#2f5d8c', { roughness: 0.6 });
    const steel = kit.mat('#d8dadb', { roughness: 0.4, metalness: 0.5 });
    const glass = kit.mat('#3a4952', { roughness: 0.15, metalness: 0.3 });
    const white = kit.mat('#f3f3f1', { roughness: 0.6 });
    const door = kit.mat('#4f5a63');

    // ---- track frame from the mapped track area ------------------------------------------
    let tf = { cx: -2418, cy: 1433, angle: 0.18, length: 174, width: 108 };
    const areas = (scene && scene.areas) || [];
    let best = null;
    for (const a of areas) {
      if (a.kind !== 'track') continue;
      const r = a.poly[0];
      const c = r.reduce((s, p) => [s[0] + p[0] / r.length, s[1] + p[1] / r.length], [0, 0]);
      const d = Math.hypot(c[0] + 2418, c[1] - 1433);
      if (d < 40 && (!best || r.length > best.r.length)) best = { r, c };
    }
    if (best) tf = kit.ringFrame(best.r);
    // lane lines: 9 lines from the kerb outwards
    {
      const R0 = 36.5,
        Sx = 84.39 / 2;
      const segs = 22;
      for (let l = 0; l <= 8; l++) {
        const R = R0 + l * 1.22;
        const pts = [];
        for (let k = 0; k <= segs; k++) {
          const t = -Math.PI / 2 + (Math.PI * k) / segs;
          pts.push([Sx + Math.cos(t) * R, Math.sin(t) * R]);
        }
        for (let k = 0; k <= segs; k++) {
          const t = Math.PI / 2 + (Math.PI * k) / segs;
          pts.push([-Sx + Math.cos(t) * R, Math.sin(t) * R]);
        }
        const P = pts.map(([u, v]) => frameAt(tf, u, v));
        for (let k = 0; k < P.length; k++) {
          const a = P[k],
            b = P[(k + 1) % P.length];
          const e = edgesOf([a, b])[0];
          ebox(white, e, 0, e.len, -0.025, 0.025, 0.06, 0.08);
        }
      }
      // finish line across the home straight end
      const a = frameAt(tf, Sx, R0),
        b = frameAt(tf, Sx, R0 + 8 * 1.22);
      const e = edgesOf([a, b])[0];
      ebox(white, e, 0, e.len, -0.05, 0.05, 0.06, 0.08);
    }
    // floodlight masts around the arena
    for (const [u, v] of [
      [-70, -60],
      [70, -60],
      [-70, 60],
      [70, 60],
      [0, -62],
    ]) {
      const p = frameAt(tf, u, v);
      cyl(steel, p[0], p[1], 0, 0.35, 0.18, 22, 8);
      kit.box(B, steel, p[0], p[1], 22, 3.2, 0.5, 1.6, tf.angle);
      kit.box(
        B,
        kit.mat('#fffbe8', { emissive: '#fff6d0', emissiveIntensity: 0.3 }),
        p[0],
        p[1],
        22.15,
        3.0,
        0.6,
        1.3,
        tf.angle,
      );
    }

    // ---- elevated stand: changing rooms beneath, raked seating, cantilever roof -------------
    {
      const sf = kit.ringFrame(stand);
      // facing direction: towards the track centre
      const toT = [tf.cx - sf.cx, tf.cy - sf.cy];
      const nx = -Math.sin(sf.angle),
        ny = Math.cos(sf.angle);
      const sgn = toT[0] * nx + toT[1] * ny > 0 ? 1 : -1; // +v towards the track
      const L = sf.length,
        W = sf.width;
      const V = (u, v) => frameAt(sf, u, sgn * v);
      // base block
      kit.walls(B, brick, [[stand]], 0, 3.0, { bay: 1e6 });
      kit.cap(B, conc, [[stand]], 3.0);
      const front = edgesOf(stand)
        .sort((a, b) => b.len - a.len)
        .find((e) => e.nx * toT[0] + e.ny * toT[1] > 0);
      if (front) {
        const n = Math.floor(front.len / 3.6);
        for (let k = 0; k < n; k++) {
          const c = ((k + 0.5) * front.len) / n;
          if (k % 3 === 1) ebox(door, front, c - 0.6, c + 0.6, 0, 0.05, 0, 2.2);
          else ebox(glass, front, c - 0.7, c + 0.7, 0, 0.05, 1.2, 2.2);
        }
      }
      // seating tiers rising away from the track
      const rows = 8;
      for (let r = 0; r < rows; r++) {
        const v0 = W / 2 - 0.4 - (r * (W - 1.2)) / rows,
          v1 = v0 - (W - 1.2) / rows;
        const z = 3.0 + r * 0.42;
        const a = V(-L / 2, v0),
          b = V(L / 2, v0);
        const e = edgesOf([a, b])[0];
        const mid = V(0, (v0 + v1) / 2);
        kit.box(B, conc, mid[0], mid[1], 3.0, L, Math.abs(v1 - v0), z + 0.42 - 3.0, sf.angle);
        // seats
        for (let s = 0.5; s < e.len - 0.3; s += 0.55) {
          const c = at(e, s, -sgn * sgn * 0); // along the row
          const p = frameAt(sf, -L / 2 + s, sgn * ((v0 + v1) / 2 + 0.05));
          kit.box(B, seat, p[0], p[1], z + 0.42, 0.45, 0.4, 0.42, sf.angle);
          void c;
        }
      }
      // back wall, side walls and roof
      const bw0 = V(-L / 2, -W / 2),
        bw1 = V(L / 2, -W / 2);
      const be = edgesOf([bw0, bw1])[0];
      ebox(brick, be, 0, be.len, -0.15, 0.15, 3.0, 10.0);
      for (const u of [-L / 2, L / 2]) {
        const p = V(u, 0);
        kit.box(B, brick, p[0], p[1], 3.0, 0.3, W, 4.5, sf.angle);
      }
      // cantilever roof projecting over the seats towards the track, on back columns
      const rc = V(0, 1.2);
      kit.box(B, roofM, rc[0], rc[1], 10.0, L + 1.2, W + 3.0, 0.3, sf.angle);
      const fc = V(0, W / 2 + 2.6);
      kit.box(B, white, fc[0], fc[1], 9.6, L + 1.2, 0.2, 0.7, sf.angle); // fascia
      for (let u = -L / 2; u <= L / 2 + 0.01; u += L / 4) {
        const p = V(u, -W / 2 - 0.3);
        cyl(steel, p[0], p[1], 0, 0.22, 0.22, 10.0, 8);
      }
    }
    // ---- pavilion and clubhouse (single storey brick, flat roofs) ---------------------------
    for (const [r, h] of [
      [pav, 4.6],
      [club, 4.0],
    ]) {
      kit.walls(B, brick, [[r]], 0, h, { bay: 1e6 });
      kit.cap(B, roofM, [[r]], h);
      parapet(kit.mat('#d6d3cb'), r, h, 0.4, 0.25);
      winRows(
        r,
        1.0,
        1,
        0,
        {
          width: 1.6,
          height: 1.6,
          bay: 4.0,
          margin: 1.0,
          glass,
          frame: white,
          sill: white,
          head: 'none',
          bars: 1,
        },
        6,
      );
    }
    // ---- covered practice straight: long shed with a shallow curved metal roof -------------
    {
      const f = kit.ringFrame(shed);
      kit.walls(B, kit.mat('#b9b7b0'), [[shed]], 0, 4.2, { bay: 1e6 });
      const segs = 6;
      for (let k = 0; k < segs; k++) {
        const t0 = k / segs,
          t1 = (k + 1) / segs;
        const v0 = -f.width / 2 + f.width * t0,
          v1 = -f.width / 2 + f.width * t1;
        const z = (t) => 4.2 + Math.sin(Math.PI * t) * 1.5;
        const a0 = frameAt(f, -f.length / 2, v0),
          a1 = frameAt(f, f.length / 2, v0),
          b1 = frameAt(f, f.length / 2, v1),
          b0 = frameAt(f, -f.length / 2, v1);
        B.add(
          roofM,
          [
            [...a0, z(t0)],
            [...a1, z(t0)],
            [...b1, z(t1)],
            [...b0, z(t1)],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
        B.add(
          roofM,
          [
            [...a0, z(t0)],
            [...b0, z(t1)],
            [...b1, z(t1)],
            [...a1, z(t0)],
          ],
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
      // translucent side strip
      ribbon(
        kit.offsetRing(shed, 0.02),
        2.6,
        4.1,
        kit.mat('#c9d6da', { roughness: 0.3 }),
        roofM,
        5.0,
        4,
      );
    }
    g.add(B.toGroup('linford_christie_stadium'));
    return g;
  },
};
