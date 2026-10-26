// Riverside Studios and Queen's Wharf, Crisp Road / Queen Caroline Street, Hammersmith
// (Assael Architecture for A2Dominion and Mount Anvil, completed 2018-19). Mixed-use block
// beside Hammersmith Bridge that rebuilt the Riverside Studios (three TV studios, theatre,
// cinema, bar) at its base: an eight-storey glass-fronted curved river elevation with a
// metal facade echoing the bridge, terminating against a six/seven-storey brick element,
// stepping down to four storeys on Crisp Road, around a raised courtyard over the studios.
export default {
  id: 'riverside_studios',
  name: "Riverside Studios / Queen's Wharf",
  claims: ['fdf14190-8e4f-416a-a585-751a22f12deb'],
  references: [
    {
      title: "Assael wins planning consent for Queen's Wharf riverside development",
      url: 'https://www.assael.co.uk/?p=6530',
      used_for: 'four storeys on Crisp Road rising to seven facing the river, curved form',
    },
    {
      title: "Queen's Wharf - Assael (RIBA Find an Architect)",
      url: 'https://find-an-architect.architecture.com/assael-architecture-limited/london/queen39s-wharf',
      used_for:
        'eight-storey glass-fronted curved building, glazing terminating at a six-storey brick element',
    },
    {
      title: "Hammersmith's award-winning riverside walkway - Mount Anvil",
      url: 'https://mountanvil.com/news/hammersmiths-award-winning-riverside-walkway',
      used_for:
        'eight storeys; river-facing metal facade echoing Hammersmith Bridge; riverside walk',
    },
    {
      title: 'Queens Wharf - A2Dominion',
      url: 'https://www.a2dominiongroup.co.uk/content/fspdf/Queens_Wharf.pdf',
      used_for: '165 homes, Riverside Studios rebuilt within the scheme, completion 2018',
    },
    {
      title: 'Riverside Studios to be Redeveloped - fulhamsw6.com',
      url: 'https://fulhamsw6.com/page/hammersmithtoday/info/riverside002.htm',
      used_for: 'studios, theatre, cinema and bar programme',
    },
  ],
  notes:
    'Part heights follow the described storey counts (8 on the curved river block, 7 on the river-side brick ' +
    'range, 4-6 stepping down towards Crisp Road) rather than Overture (20-23 m); the 7.2 m centre part is ' +
    'modelled as the studio box under a landscaped podium. Brick colour, the gold-bronze tone of the metal ' +
    'fins, balcony positions, window rhythm and the signage position are assumptions.',
  build({ THREE, kit, buildings }) {
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
    const parts = buildings[0].parts.map((p) => ({ ring: ccw(p.polys[0][0]), h: p.h }));
    const byH = (h) => parts.filter((p) => Math.abs(p.h - h) < 0.5);
    const studio = byH(7.2)[0];
    const [p20a, p20b] = byH(20.0);
    const river7 = byH(23.2)[0];
    // the curved river block is the 20 m part furthest west
    const cx = (r) => r.reduce((s, p) => s + p[0], 0) / r.length;
    const curved = cx(p20a.ring) < cx(p20b.ring) ? p20a : p20b;
    const crisp = curved === p20a ? p20b : p20a;

    const brick = kit.mat('#a5826a', { roughness: 0.9 });
    const brickDark = kit.mat('#6d5446', { roughness: 0.9 });
    const glass = kit.mat('#5d7480', { roughness: 0.1, metalness: 0.35 });
    const fin = kit.mat('#b59a63', { roughness: 0.4, metalness: 0.6 }); // gold-bronze metal
    const frame = kit.mat('#3a3a3a', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#8c8c88');
    const green = kit.mat('grass');
    const rail = kit.mat('#d0d3d4', { roughness: 0.3, metalness: 0.5 });
    const G = 4.5,
      ST = 3.15;

    // ---- curved glass river block: 8 storeys, metal fins and slab bands ------------------
    {
      const r = curved.ring,
        H = G + 7 * ST;
      ribbon(r, 0.0, G - 0.3, kit.mat('#3b4c55', { roughness: 0.1, metalness: 0.3 }), frame, 2.0);
      kit.walls(B, brickDark, [[r]], G - 0.3, G, { bay: 1e6 });
      for (let s = 0; s < 7; s++) {
        const z = G + s * ST;
        const rg = kit.offsetRing(r, -0.25);
        ribbon(rg, z, z + ST - 0.35, glass, frame, 1.6);
        kit.cornice(B, fin, r, z + ST - 0.35, { height: 0.35, projection: 0.15 });
      }
      // vertical metal fins on the river (long west) edges
      for (const e of edgesOf(r)) {
        if (e.len < 2 || e.nx > 0.3) continue; // fins only on west/south facing faces
        const n = Math.max(1, Math.round(e.len / 1.6));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(fin, e, s - 0.07, s + 0.07, 0, 0.55, G, H);
        }
        // balcony glass balustrades every storey
        for (let s = 1; s < 7; s++)
          ebox(rail, e, 0, e.len, 0.55, 0.6, G + s * ST, G + s * ST + 1.05);
      }
      kit.cap(B, roofM, [[r]], H);
      parapet(fin, r, H, 0.6, 0.2);
      kit.cap(B, roofM, [[kit.offsetRing(r, -0.2)]], G - 0.3, { down: true });
      // Riverside Studios sign on the riverside ground floor
      const long = edgesOf(r)
        .filter((e) => e.nx < 0)
        .sort((a, b) => b.len - a.len)[0];
      if (long)
        ebox(
          signMat(
            'riverside:sign',
            'RIVERSIDE STUDIOS',
            '#1b1b1b',
            '#f2c94c',
            'bold 40px sans-serif',
          ),
          long,
          long.len / 2 - 7,
          long.len / 2 + 7,
          0.6,
          0.65,
          G - 1.4,
          G - 0.4,
        );
    }
    // ---- brick ranges with punched windows --------------------------------------------------
    const brickBlock = (r, n, setTop) => {
      const H = G + (n - 1) * ST;
      ribbon(
        kit.offsetRing(r, -0.3),
        0,
        G - 0.4,
        kit.mat('#3b4c55', { roughness: 0.1, metalness: 0.3 }),
        frame,
        2.2,
      );
      kit.walls(B, brick, [[r]], G - 0.4, setTop ? H - ST : H, { bay: 1e6 });
      // brick piers at ground
      for (const e of edgesOf(r)) {
        if (e.len < 5) continue;
        const m = Math.max(1, Math.round(e.len / 6.5));
        for (let k = 0; k <= m; k++) {
          const s = 0.3 + ((e.len - 0.6) * k) / m;
          ebox(brick, e, s - 0.35, s + 0.35, -0.3, 0.05, 0, G - 0.4);
        }
      }
      winRows(
        r,
        G + 0.5,
        n - 1 - (setTop ? 1 : 0),
        ST,
        {
          width: 1.5,
          height: 2.3,
          bay: 3.3,
          margin: 0.8,
          glass,
          frame,
          sill: brickDark,
          head: 'none',
          bars: 0,
          depth: 0.18,
        },
        4,
      );
      // projecting balconies on alternate bays of the long faces
      for (const e of edgesOf(r)) {
        if (e.len < 12) continue;
        const nb = Math.floor(e.len / 6.6);
        for (let s = 1; s < n - 1; s++)
          for (let k = 0; k < nb; k += 2) {
            const c = ((k + 0.5) * e.len) / nb;
            ebox(
              kit.mat('#d8d8d6'),
              e,
              c - 1.6,
              c + 1.6,
              0,
              1.4,
              G + (s - 1) * ST + 0.2 + ST - 0.2,
              G + (s - 1) * ST + ST + 0.05,
            );
            ebox(rail, e, c - 1.6, c + 1.6, 1.35, 1.4, G + s * ST + 0.05, G + s * ST + 1.1);
          }
      }
      if (setTop) {
        const t = kit.offsetRing(r, -1.8);
        kit.cap(B, roofM, [[r]], H - ST);
        ribbon(t, H - ST, H - 0.2, glass, frame, 1.5);
        kit.cap(B, roofM, [[t]], H - 0.2);
        parapet(frame, t, H - 0.2, 0.3, 0.1);
      } else {
        kit.cap(B, roofM, [[r]], H);
        parapet(brickDark, r, H, 0.7, 0.3);
      }
      kit.cornice(B, brickDark, r, G - 0.4, { height: 0.4, projection: 0.12 });
    };
    brickBlock(river7.ring, 7, false);
    brickBlock(crisp.ring, 6, true);

    // ---- studio box under the landscaped podium ----------------------------------------
    {
      const r = studio.ring;
      kit.walls(B, brickDark, [[r]], 0, 7.2, { bay: 1e6 });
      kit.cap(B, green, [[kit.offsetRing(r, -0.4)]], 7.25);
      parapet(rail, r, 7.2, 1.1, 0.05);
      const rnd = kit.rng(0.913);
      const f = kit.ringFrame(r);
      for (let k = 0; k < 7; k++) {
        const p = frameAt(f, (rnd() - 0.5) * f.length * 0.6, (rnd() - 0.5) * f.width * 0.5);
        cyl(kit.mat('#6b5040'), p[0], p[1], 7.2, 0.12, 0.12, 2, 6);
        const tree = new THREE.IcosahedronGeometry(1.4 + rnd() * 0.6, 0);
        B.addGeometry(
          kit.mat('foliage'),
          tree,
          new THREE.Matrix4().makeTranslation(p[0], p[1], 9.6),
        );
        tree.dispose();
      }
      // plant / smoke vents of the studios
      plantBoxes(r, 7.2, rnd, 3, kit.mat('#9a9c99'));
    }
    g.add(B.toGroup('riverside_studios'));
    return g;
  },
};
