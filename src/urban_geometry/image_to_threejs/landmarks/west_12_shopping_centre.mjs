// West 12 shopping centre, south side of Shepherd's Bush Green (opened 1967 as the Shepherd's
// Bush Centre; substantially redeveloped in the 1990s; Warner Village / Vue 12-screen
// multiplex added 2001). Low retail podium fronting the Green with a glazed entrance, rooftop
// car park, and the taller multiplex block in the southern (rear) half; the 1970s Bush Court
// and Shepherds Court towers rise from the site corners (generic layer).
export default {
  id: 'west_12_shopping_centre',
  name: 'West 12 Shopping Centre',
  claims: ['9ca26cb4-0427-4bb6-9693-223eb3e5cd6a'],
  references: [
    {
      title: 'West 12 - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/West_12',
      used_for:
        'opened 1967, joint venture, redeveloped in the 1990s, shopping centre on Shepherd’s Bush Green',
    },
    {
      title: "Vue Shepherd's Bush - Cinema Treasures",
      url: 'https://www.cinematreasures.org/theaters/21154',
      used_for: 'Warner Village 12-screen multiplex opened 2001, rebranded Vue 2004',
    },
    {
      title: 'West 12 Centre Owner Reveals Radical Plan to Redevelop Site - fulhamsw6.com',
      url: 'https://fulhamsw6.com/page/shared/common/west12centre002.htm',
      used_for: 'front half facing the Green vs. rear half containing the Vue',
    },
    {
      title: 'Local Plan Regulation 18 - South of Shepherds Bush Green - LBHF',
      url: 'https://www.lbhf.gov.uk/planning/planning-policy/local-plan/local-plan-regulation-18/Area%20strategies/south-shepherds-bush-green',
      used_for: 'rolling refurbishment programme of the centre',
    },
  ],
  notes:
    'The rear footprint part (h=16.4 m) is modelled as the multiplex block and the remainder as a two-storey ' +
    'podium (9.5 m) with a rooftop car park; the car-park layout, ramp, cladding colours, the Green-facing ' +
    'glazed entrance and signage positions are assumptions. The residential towers that stand on the site ' +
    'corners are left to the generic layer.',
  build({ THREE, kit, buildings, placeAssets }) {
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
    const b = buildings[0];
    const ring = ccw(b.polys[0][0]);
    const rear = ccw(b.parts[0].polys[0][0]);
    const clad = kit.mat('#cfcbc2', { roughness: 0.7 });
    const cladDark = kit.mat('#5e6266', { roughness: 0.6, metalness: 0.3 });
    const brick = kit.mat('#8f5545', { roughness: 0.9 });
    const glass = kit.mat('#3c5865', { roughness: 0.1, metalness: 0.35 });
    const shop = kit.mat('#32424a', { roughness: 0.1, metalness: 0.3 });
    const frame = kit.mat('#4a4f53', { roughness: 0.4, metalness: 0.5 });
    const deck = kit.mat('#5b5d60', { roughness: 0.95 });
    const line = kit.mat('#f1f1ef');
    const rnd = kit.rng(0.3127);
    const Z = 9.5,
      HC = 16.4;
    // podium: shopfronts under a fascia band, brick upper storey with sparse windows
    ribbon(kit.offsetRing(ring, -0.4), 0, 4.6, shop, frame, 3.2);
    kit.walls(B, cladDark, [[ring]], 4.6, 5.4, { bay: 1e6 });
    kit.cap(B, cladDark, [[ring]], 4.6, { down: true });
    kit.walls(B, brick, [[ring]], 5.4, Z, { bay: 1e6 });
    kit.cap(B, deck, [[ring]], Z);
    parapet(clad, ring, Z, 1.2, 0.3);
    // car park: bay lines and parked cars over the front part of the roof
    const f = kit.ringFrame(ring);
    const cars = [];
    const inRing = (p, r) => {
      let c = false;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const [xi, yi] = r[i],
          [xj, yj] = r[j];
        if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
      }
      return c;
    };
    const inner = kit.offsetRing(ring, -4);
    for (let v = -f.width / 2 + 6; v < f.width / 2 - 5; v += 16)
      for (let u = -f.length / 2 + 4; u < f.length / 2 - 4; u += 2.6) {
        for (const dv of [-2.6, 2.6]) {
          const p = frameAt(f, u, v + dv);
          if (!inRing(p, inner) || inRing(p, kit.offsetRing(rear, 3))) continue;
          kit.box(B, line, p[0], p[1], Z + 0.01, 0.1, 5.0, 0.02, f.angle);
          if (rnd() < 0.55)
            cars.push([...frameAt(f, u + 1.3, v + dv), f.angle + (dv > 0 ? Math.PI : 0)]);
        }
      }
    if (cars.length) {
      const cg = placeAssets('hatchback', cars);
      cg.position.z = Z;
      g.add(cg);
    }
    // stair / lift cores on the roof
    for (const t of [0.2, 0.8]) {
      const p = frameAt(f, -f.length / 2 + f.length * t, f.width / 2 - 8);
      if (inRing(p, ring)) kit.box(B, clad, p[0], p[1], Z, 6, 5, 3.5, f.angle);
    }
    // multiplex block in the rear part
    {
      kit.walls(B, cladDark, [[rear]], Z, HC, { bay: 1e6 });
      for (const e of edgesOf(rear)) {
        if (e.len < 6) continue;
        for (let z = Z + 1.2; z < HC - 0.5; z += 1.4) ebox(clad, e, 0, e.len, 0, 0.08, z, z + 0.7);
      }
      kit.cap(B, kit.mat('#8a8a86'), [[rear]], HC);
      parapet(clad, rear, HC, 0.8, 0.3);
      plantBoxes(rear, HC, rnd, 5, kit.mat('#a3a5a3'), 0.5);
      const e = edgesOf(rear).sort((a, b) => b.len - a.len)[0];
      ebox(
        signMat('w12:vue', 'vue', '#1d1d1b', '#ffffff', 'bold 52px sans-serif', 256, 64),
        e,
        e.len / 2 - 5,
        e.len / 2 + 5,
        0.1,
        0.18,
        HC - 3.4,
        HC - 0.9,
      );
    }
    // Green frontage: glazed double-height entrance with a canopy and the WEST 12 sign
    {
      const fe = edgesOf(ring)
        .filter((e) => e.ny > 0.6)
        .sort((a, b) => b.len - a.len)[0];
      if (fe) {
        const m = fe.len / 2;
        ebox(glass, fe, m - 8, m + 8, 0.0, 1.2, 0, Z + 2.5);
        for (let k = 0; k <= 8; k++)
          ebox(frame, fe, m - 8 + 2 * k - 0.06, m - 8 + 2 * k + 0.06, 1.2, 1.35, 0, Z + 2.5);
        ebox(frame, fe, m - 8, m + 8, 0, 1.35, Z + 2.5, Z + 2.8);
        ebox(cladDark, fe, m - 9, m + 9, 1.2, 4.0, 4.4, 4.75);
        ebox(
          signMat('w12:sign', 'WEST 12', '#2b2b2b', '#ffffff', 'bold 48px sans-serif', 256, 64),
          fe,
          m - 3.5,
          m + 3.5,
          1.36,
          1.42,
          Z - 0.5,
          Z + 2.0,
        );
      }
    }
    g.add(B.toGroup('west_12_shopping_centre'));
    return g;
  },
};
