// The Ark, Talgarth Road, Hammersmith (Ralph Erskine with Lennart Bergström and Rock
// Townsend, 1989-92). Ten-storey speculative office block immediately south of the
// Hammersmith Flyover, shaped like a vast boat: a bulging hull whose walls flare outward
// as they rise, clad in copper panels with bands of tinted glazing, a brick-and-timber
// base, a great copper roof and an elevated "bridge" / crow's-nest meeting room on top.
export default {
  id: 'the_ark',
  name: 'The Ark',
  claims: ['68f2e937-d306-44cf-b2bb-5c8cd59943df'],
  references: [
    {
      title: 'The Ark, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Ark,_London',
      used_for: 'architects, 1989-92 dates, 10 floors, location south of the Hammersmith Flyover',
    },
    {
      title: 'The Ark - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1990/ark.html',
      used_for:
        'boat-like appearance with an elevated bridge or crows nest; copper panels and bands of tinted glazing',
    },
    {
      title: 'The incredible hull - Building',
      url: 'https://www.building.co.uk/focus/the-incredible-hull/3106848.article',
      used_for: 'bulging copper-clad hull, steeply sloping atrium sides, open central atrium',
    },
    {
      title: 'The London Ark - AJ Buildings Library',
      url: 'https://www.ajbuildingslibrary.co.uk/projects/display/id/475',
      used_for: 'brickwork at the base, project overview',
    },
    {
      title: 'Ark office building - Rockfon case study',
      url: 'https://rockfon.com/design-inspiration/ark-office-building',
      used_for: 'iconic curvature and the Crow’s Nest panoramic meeting room',
    },
  ],
  notes:
    'Overture h=17.7 m is far too low and Wikipedia’s 76 m roof height conflicts with ten floors; the model uses ' +
    'a 4.8 m ground floor + 7 x 3.75 m hull floors (eaves ~31 m) and two further floors inside the dormered ' +
    'copper roof rising to ~44.5 m, with the crow’s nest to ~51 m. The outward flare per floor (0.32 m), the copper/glass band proportions, the ' +
    'position of the crow’s nest near the eastern bow, the atrium rooflight along the ridge and the brick ' +
    'colour of the base are estimates from descriptions, not measured drawings.',
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
    const ring0 = ccw(buildings[0].polys[0][0]);
    const f = kit.ringFrame(ring0);
    const copper = kit.mat('#7d5a43', { roughness: 0.55, metalness: 0.45 }); // weathered brown copper
    const copperDark = kit.mat('#5e4535', { roughness: 0.6, metalness: 0.4 });
    const tinted = kit.mat('#4c6672', { roughness: 0.12, metalness: 0.35 });
    const mull = kit.mat('#3b3430', { roughness: 0.5, metalness: 0.4 });
    const brick = kit.mat('#8a4a36', { roughness: 0.9 });
    const timber = kit.mat('#9a7350', { roughness: 0.8 });
    const roofGlass = kit.mat('#8fa6b0', { roughness: 0.1, metalness: 0.3 });
    const paving = kit.mat('#bdb5a6');
    const steel = kit.mat('steel');

    const G = 4.8,
      ST = 3.75,
      NUP = 7,
      FLARE = 0.32;
    const base = kit.offsetRing(ring0, -1.2);

    // ---- base: brick piers with recessed glazing and timber soffit ---------------------
    {
      const rec = kit.offsetRing(base, -1.0);
      ribbon(rec, 0, G - 0.6, tinted, mull, 1.8);
      kit.cap(B, timber, [[base]], G - 0.6, { down: true });
      kit.walls(B, brick, [[base]], G - 0.6, G, { bay: 1e6 });
      for (const e of edgesOf(base)) {
        if (e.len < 4) continue;
        const n = Math.max(1, Math.round(e.len / 6));
        for (let k = 0; k <= n; k++) {
          const s = 0.4 + ((e.len - 0.8) * k) / n;
          ebox(brick, e, s - 0.45, s + 0.45, -1.0, 0, 0, G - 0.6);
        }
      }
      kit.cap(B, paving, [[kit.offsetRing(ring0, 3), rec.slice().reverse()]], 0.03);
      // entrance canopy on the north (flyover) side, the longest north-facing edge
      const north = edgesOf(base)
        .filter((e) => e.ny > 0.5)
        .sort((a, b) => b.len - a.len)[0];
      if (north) {
        const m = north.len / 2;
        ebox(copperDark, north, m - 7, m + 7, -0.5, 3.5, G - 1.6, G - 1.2);
        ebox(steel, north, m - 6.8, m - 6.6, 3.2, 3.4, 0, G - 1.6);
        ebox(steel, north, m + 6.6, m + 6.8, 3.2, 3.4, 0, G - 1.6);
        ebox(
          signMat('ark:sign', 'THE ARK', '#5e4535', '#e8d9b5'),
          north,
          m - 3,
          m + 3,
          3.52,
          3.56,
          G - 1.55,
          G - 1.25,
        );
      }
    }

    // ---- hull: flaring floors of copper spandrels and tinted ribbon glazing -------------
    let rTop = base;
    for (let s = 0; s < NUP; s++) {
      const z = G + s * ST;
      const r0 = kit.offsetRing(base, FLARE * s);
      const r1 = kit.offsetRing(base, FLARE * (s + 1));
      const zw = z + 1.15; // top of spandrel
      // sloped copper spandrel from this floor line to the window sill
      loft(copper, r0, z, kit.offsetRing(base, FLARE * (s + 0.3)), zw);
      // tinted window band, slightly recessed, with mullions
      const rw = kit.offsetRing(base, FLARE * (s + 0.3) - 0.15);
      ribbon(rw, zw, z + ST - 0.25, tinted, mull, 1.5);
      // projecting copper drip / sun ledge at the floor line above
      loft(copperDark, kit.offsetRing(base, FLARE * (s + 0.3) - 0.15), z + ST - 0.25, r1, z + ST);
      kit.cap(B, copperDark, [[r1]], z + ST - 0.25, { down: true });
      rTop = r1;
    }
    const zE = G + NUP * ST; // hull eaves

    // ---- great copper roof: lofted slopes to a ridge plateau, roof glazing ------------
    const rr1 = kit.offsetRing(rTop, -6.0),
      rr2 = kit.offsetRing(rTop, -10.5);
    const zR1 = zE + 8.2,
      zR2 = zE + 13.4;
    loft(copper, rTop, zE, rr1, zR1);
    // two rows of dormer windows lighting the floors inside the copper roof
    for (const [off, zz] of [
      [-1.9, zE + 1.3],
      [-4.4, zE + 4.9],
    ])
      for (const e of edgesOf(kit.offsetRing(rTop, off))) {
        if (e.len < 2.5) continue;
        const n = Math.max(1, Math.floor(e.len / 2.4));
        for (let k = 0; k < n; k++) {
          const s = (e.len * (k + 0.5)) / n;
          ebox(tinted, e, s - 0.85, s + 0.85, -0.6, 0.15, zz, zz + 1.8);
          ebox(copperDark, e, s - 1.0, s + 1.0, -0.9, 0.3, zz + 1.8, zz + 2.0);
          ebox(copperDark, e, s - 1.0, s - 0.85, -0.6, 0.3, zz, zz + 1.8);
          ebox(copperDark, e, s + 0.85, s + 1.0, -0.6, 0.3, zz, zz + 1.8);
        }
      }
    loft(copperDark, rr1, zR1, rr2, zR2);
    kit.cap(B, copperDark, [[rr2]], zR2);
    const zTop = zR2;
    // atrium rooflight: glazed pitched spine along the long axis
    {
      const L = f.length * 0.5,
        W = 7;
      const ra = [
        frameAt(f, -L / 2, -W / 2),
        frameAt(f, L / 2, -W / 2),
        frameAt(f, L / 2, W / 2),
        frameAt(f, -L / 2, W / 2),
      ];
      prism(mull, null, ra, zTop, zTop + 0.5);
      kit.pitchedRoof(B, roofGlass, mull, ccw(ra), f.angle, zTop + 0.5, 2.2, 'hipped', {
        overhang: 0.1,
      });
      // glazing ribs
      for (let k = 0; k <= 10; k++) {
        const u = -L / 2 + (L * k) / 10;
        const p = frameAt(f, u, 0);
        kit.box(B, mull, p[0], p[1], zTop + 0.5, 0.12, W, 0.15, f.angle);
      }
    }

    // ---- crow's nest: elevated glazed drum with a copper cap near the eastern bow ------
    {
      const p = frameAt(f, f.length * 0.24 * (Math.cos(f.angle) >= 0 ? 1 : -1), 0);
      const zb = zTop;
      cyl(copperDark, p[0], p[1], zb, 3.2, 3.2, 1.6, 20);
      cyl(tinted, p[0], p[1], zb + 1.6, 4.2, 4.4, 3.0, 24);
      for (let k = 0; k < 12; k++) {
        const a = (k / 12) * Math.PI * 2;
        kit.box(
          B,
          mull,
          p[0] + Math.cos(a) * 4.3,
          p[1] + Math.sin(a) * 4.3,
          zb + 1.6,
          0.14,
          0.14,
          3.0,
          a,
        );
      }
      cyl(copperDark, p[0], p[1], zb + 4.6, 4.8, 4.8, 0.35, 24);
      cyl(copper, p[0], p[1], zb + 4.95, 4.8, 0.6, 1.4, 24);
      cyl(steel, p[0], p[1], zb + 6.35, 0.08, 0.08, 4.0, 6); // mast
    }
    g.add(B.toGroup('the_ark'));
    return g;
  },
};
