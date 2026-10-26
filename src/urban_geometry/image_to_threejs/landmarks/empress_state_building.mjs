// Empress State Building, Lillie Road, Earl's Court (Stone, Toms & Partners for the
// Admiralty, 1959-61; refurbished and extended by Wilkinson Eyre, 2001-03). A Y-shaped
// office tower: three stone-clad corner towers at the tips of the plan with concave,
// curving curtain walls between them; the south facade was pushed out 5.5 m and given
// horizontal aluminium sun louvres; a lightweight three-storey top holds the revolving
// 'Orbit' bar; the base was widened into a two-storey drum. ~117 m, 31 floors.
export default {
  id: 'empress_state_building',
  name: 'Empress State Building',
  claims: ['f5233a36-9cd0-4152-946e-2bbbac3036c9'],
  references: [
    {
      title: 'Empress State Building - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Empress_State_Building',
      used_for:
        'Stone, Toms & Partners, 1959-61, originally 100 m / 28 floors, Orbit revolving bar',
    },
    {
      title: 'Empress State Building - Structurae',
      url: 'https://structurae.net/structures/20009442',
      used_for: '117 m, 31 floors above ground',
    },
    {
      title: 'Extending the Empress State Building - New Steel Construction',
      url: 'https://www.newsteelconstruction.com/wp/extending-the-empress-state-building/',
      used_for:
        'south facade pushed out ~5 m, steel-and-glass extension, lightweight three-storey top',
    },
    {
      title: 'The Empress strikes back - Building',
      url: 'https://building.co.uk/news/the-empress-strikes-back/1021296.article',
      used_for:
        'curtain walls curving between three stone-clad corner towers; two-storey drum at the base',
    },
    {
      title: 'Wilkinson Eyre revamps office - Design Week',
      url: 'https://designweek.co.uk/issues/17-july-2003/wilkinson-eyre-revamps-office',
      used_for:
        'recladding of the three concave facades, horizontal aluminium louvres on the south facade',
    },
    {
      title: 'Sanierung Empress State Building - BauNetz Wissen',
      url: 'https://www.baunetzwissen.de/bauen-im-bestand/objekte/buero-verwaltung/sanierung-empress-state-building-in-london-gb-69172',
      used_for: 'three-wing layout around a central service core',
    },
  ],
  notes:
    'Wing directions from the tips of the Overture base footprint (the drum). Wing width (20 m), tip radius ' +
    '(36 m), the depth of the concave curves, storey height (3.3 m) and the form of the glazed top, the bar ' +
    'drum and mast are estimates; mullion pitch and louvre spacing are schematic. Height kept at 117 m (Structurae).',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r.slice());
    const base = ccw(buildings[0].polys[0][0]);
    const C = [52, -2116];
    const H = 117,
      Z0 = 10.5, // top of the drum
      ST = 3.3,
      NST = 27, // office floors above the drum
      ZT = Z0 + NST * ST; // ~99.6, start of the lightweight top
    const stone = kit.mat('#d9d2c3', { roughness: 0.8 });
    const stoneD = kit.mat('#bdb5a5', { roughness: 0.85 });
    const glass = kit.mat('#4f6a7d', { roughness: 0.1, metalness: 0.55 });
    const glassL = kit.mat('#7d98a8', { roughness: 0.12, metalness: 0.5 });
    const alu = kit.mat('#c8ccce', { roughness: 0.4, metalness: 0.6 });
    const dark = kit.mat('#2e3438', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#8d8f8c');

    const P = (ang, r) => [C[0] + Math.cos(ang) * r, C[1] + Math.sin(ang) * r];
    const deg = Math.PI / 180;
    const wings = [3, 123, 243].map((d) => d * deg);
    const R = 36,
      W = 10, // half width of a wing
      CORE = 8; // radial depth of the stone corner tower
    // Point at radial distance r, lateral offset l (CCW positive) of wing i.
    const WP = (i, r, l) => {
      const a = wings[i];
      return [C[0] + Math.cos(a) * r - Math.sin(a) * l, C[1] + Math.sin(a) * r + Math.cos(a) * l];
    };
    // Concave facades between wing i (left side) and wing i+1 (right side).
    // sag: distance of the curve midpoint from the centre (south face pushed out).
    const faces = [];
    for (let i = 0; i < 3; i++) {
      const j = (i + 1) % 3;
      const p0 = WP(i, R - CORE, W),
        p2 = WP(j, R - CORE, -W);
      const bis = wings[i] + 60 * deg;
      const south = i === 2; // between the S and E wings, faces SSE
      const mid = P(bis, south ? 21 : 15.5);
      const c1 = [2 * mid[0] - (p0[0] + p2[0]) / 2, 2 * mid[1] - (p0[1] + p2[1]) / 2];
      const pts = [];
      const N = 14;
      for (let k = 0; k <= N; k++) {
        const t = k / N,
          u = 1 - t;
        pts.push([
          u * u * p0[0] + 2 * u * t * c1[0] + t * t * p2[0],
          u * u * p0[1] + 2 * u * t * c1[1] + t * t * p2[1],
        ]);
      }
      faces.push({ pts, south });
    }
    // Full tower outline: core tips + concave faces.
    const outline = [];
    for (let i = 0; i < 3; i++) {
      outline.push(WP(i, R - CORE, -W), WP(i, R, -W), WP(i, R, W));
      outline.push(...faces[i].pts.slice(0, -1));
    }
    const ring = ccw(outline);

    const seg = (a, b) => {
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        a,
        b,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
      };
    };
    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const ebox = (m, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const quad = (m, p, q, z0, z1) =>
      batch.quad(
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

    // ---- base drum (two storeys) -------------------------------------------------
    {
      const inner = kit.offsetRing(base, -0.8);
      for (let k = 0; k < inner.length; k++) {
        const e = seg(inner[k], inner[(k + 1) % inner.length]);
        if (e.len < 0.1) continue;
        quad(glassL, e.a, e.b, 0, Z0 - 1.4);
        const n = Math.max(1, Math.round(e.len / 1.8));
        for (let m = 0; m <= n; m++)
          ebox(alu, e, (m * e.len) / n - 0.05, (m * e.len) / n + 0.05, 0, 0.15, 0, Z0 - 1.4);
        ebox(alu, e, 0, e.len, 0, 0.2, 4.6, 4.9);
      }
      kit.walls(batch, alu, [[base]], Z0 - 1.4, Z0, { bay: 1e6 });
      kit.cap(batch, roofM, [[base]], Z0);
      kit.cap(batch, alu, [[base]], Z0 - 1.4, { down: true });
      kit.cornice(batch, alu, base, Z0 - 0.3, { height: 0.3, projection: 0.3 });
    }

    // ---- stone corner towers ----------------------------------------------------
    for (let i = 0; i < 3; i++) {
      const r = ccw([WP(i, R - CORE - 1, -W), WP(i, R, -W), WP(i, R, W), WP(i, R - CORE - 1, W)]);
      kit.walls(batch, stone, [[r]], Z0, ZT + 4, { bay: 1e6 });
      kit.cap(batch, stoneD, [[r]], ZT + 4);
      // tip face: a narrow vertical slot window on every floor, dark recessed strip
      const e = seg(WP(i, R, -W), WP(i, R, W));
      ebox(dark, e, e.len / 2 - 0.7, e.len / 2 + 0.7, -0.05, 0.04, Z0 + 1, ZT + 2);
      for (let s = 0; s <= NST; s++)
        ebox(stoneD, e, e.len / 2 - 0.9, e.len / 2 + 0.9, 0, 0.08, Z0 + s * ST, Z0 + s * ST + 0.25);
      // side faces: fine vertical stone ribs
      for (const side of [
        seg(WP(i, R - CORE - 1, W), WP(i, R, W)),
        seg(WP(i, R, -W), WP(i, R - CORE - 1, -W)),
      ])
        for (let s = 1.2; s < side.len - 0.5; s += 1.6)
          ebox(stoneD, side, s - 0.12, s + 0.12, 0, 0.12, Z0, ZT + 4);
    }

    // ---- concave curtain walls --------------------------------------------------
    for (const f of faces) {
      for (let k = 0; k < f.pts.length - 1; k++) {
        const e = seg(f.pts[k], f.pts[k + 1]);
        // glass set 0.25 m behind slab edge
        quad(glass, at(e, 0, -0.25), at(e, e.len, -0.25), Z0, ZT);
        ebox(alu, e, -0.05, 0.05, -0.25, 0.1, Z0, ZT); // mullion at each facet joint
        ebox(alu, e, e.len / 2 - 0.04, e.len / 2 + 0.04, -0.25, 0.0, Z0, ZT);
        for (let s = 0; s <= NST; s++) {
          const z = Z0 + s * ST;
          ebox(alu, e, 0, e.len, -0.25, 0.15, z - 0.45, z + 0.15); // spandrel band
          if (f.south && s < NST)
            for (const dz of [1.1, 1.8, 2.5])
              ebox(alu, e, 0, e.len, 0.5, 1.2, z + dz, z + dz + 0.06); // louvres
        }
        if (f.south)
          for (const s of [0.1, e.len - 0.1]) ebox(alu, e, s - 0.04, s + 0.04, 0.1, 1.25, Z0, ZT);
      }
    }
    kit.cap(batch, roofM, [[ring]], ZT);

    // ---- lightweight top, revolving bar, mast ---------------------------------------
    const top = kit.offsetRing(ring, -3);
    kit.walls(batch, glassL, [[top]], ZT, ZT + 7.5, { bay: 1e6 });
    for (let k = 0; k < top.length; k++) {
      const e = seg(top[k], top[(k + 1) % top.length]);
      if (e.len < 0.2) continue;
      ebox(alu, e, 0, e.len, 0, 0.25, ZT + 3.5, ZT + 3.8);
      ebox(alu, e, -0.08, 0.08, 0, 0.25, ZT, ZT + 7.5);
    }
    kit.cap(batch, alu, [[top]], ZT + 7.5);
    const cyl = (m, r0, r1, z0, h, n = 40, open = false) => {
      const geo = new THREE.CylinderGeometry(r1, r0, h, n, 1, open).rotateX(Math.PI / 2);
      batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(C[0], C[1], z0 + h / 2));
      geo.dispose();
    };
    cyl(glassL, 15, 15, ZT + 7.5, 3.6); // Orbit revolving bar
    cyl(alu, 15.6, 15.6, ZT + 7.3, 0.35);
    cyl(alu, 15.6, 14.5, ZT + 11.1, 0.6);
    cyl(roofM, 13, 13, ZT + 11.7, 2.2);
    cyl(alu, 13.3, 13.3, ZT + 13.7, 0.3);
    // radial fins on the bar
    for (let k = 0; k < 24; k++) {
      const a = (k / 24) * Math.PI * 2;
      const p = P(a, 15.2);
      kit.box(batch, alu, p[0], p[1], ZT + 7.5, 0.6, 0.08, 3.6, a + Math.PI / 2);
    }
    // plant and the mast to ~117 m
    kit.box(batch, roofM, C[0] - 3, C[1] + 2, ZT + 14, 5, 4, 1.6, 0.3);
    {
      const zb = ZT + 14;
      const geo = new THREE.CylinderGeometry(0.12, 0.35, H - zb, 8).rotateX(Math.PI / 2);
      batch.addGeometry(
        alu,
        geo,
        new THREE.Matrix4().makeTranslation(C[0] + 2, C[1] - 1, zb + (H - zb) / 2),
      );
      geo.dispose();
    }
    // entrance canopy on the north (Empress Approach) side of the drum
    {
      const a = 75 * deg;
      const p = P(a, 34.5);
      kit.box(batch, alu, p[0], p[1], 4.2, 12, 5, 0.4, a + Math.PI / 2);
    }

    g.add(batch.toGroup('empress_state_building'));
    return g;
  },
};
