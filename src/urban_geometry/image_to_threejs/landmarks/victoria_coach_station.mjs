// Victoria Coach Station, 164 Buckingham Palace Road (Wallis, Gilbert & Partners, opened
// 10 March 1932). Grade II (2014). Art Deco perimeter building on the corner of
// Buckingham Palace Road and Elizabeth Street around the coach yard, with a distinctive
// corner tower; painted cream; the top storey was added in the 1960s.
export default {
  id: 'victoria_coach_station',
  name: 'Victoria Coach Station',
  claims: ['233d1e08-bda0-4a03-80d8-e5218e7287e4'],
  references: [
    {
      title: 'Victoria Coach Station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Victoria_Coach_Station',
      used_for:
        'opened 10 March 1932, Wallis Gilbert and Partners Art Deco, corner of Buckingham Palace Road and Elizabeth Street, Grade II 2014',
    },
    {
      title: "Vaizey on London's Art Deco Victoria Coach Station, listed GII - IHBC",
      url: 'https://newsblogs.ihbc.org.uk/?p=8544',
      used_for: "corner tower one of London's most distinctive Art Deco landmarks",
    },
    {
      title: 'Victoria Coach Station - Manchester History (architecture)',
      url: 'https://manchesterhistory.net/architecture/1930/victoriacoach.html',
      used_for:
        'central tower; topmost storey added in the 1960s; concrete with coloured glass aggregate; cream paint',
    },
    {
      title: 'Linking London and country: Victoria Coach Station - London Transport Museum',
      url: 'https://ltmuseum.co.uk/collections/stories/transport/linking-london-and-country-victoria-coach-station',
      used_for: 'opened with 66 departure bays around the yard',
    },
  ],
  notes:
    'Three 1932 storeys (11.6 m) plus the set-back 1960s storey to 15.4 m (Overture). Tower at the ' +
    'Buckingham Palace Road / Elizabeth Street corner rising to ~26 m with stepped fins and flagpole; the ' +
    'window bands, vertical piers, lettering and corner entrance canopy are drawn from the general Art ' +
    'Deco character, not traced. The covered yard/departure hall inside the C-shaped plan is not modelled.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // ---- local helpers (modules have no imports) -----------------------------------
    const ccw = (r) => {
      const o = r.slice();
      if (kit.ringArea(o) < 0) o.reverse();
      return o;
    };
    const edges = (r) =>
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
          mx: (a[0] + b[0]) / 2,
          my: (a[1] + b[1]) / 2,
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box on edge e from s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
      const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, p[0], p[1], z0, Math.abs(s1 - s0), Math.abs(d1 - d0), z1 - z0, e.ang, c);
    };
    const prism = (m, ring, z0, z1, top = m) => {
      kit.walls(batch, m, [[ring]], z0, z1);
      if (top) kit.cap(batch, top, [[ring]], z1);
    };
    const wins = (e, s0, s1, z, o) => kit.windowRow(batch, at(e, s0), at(e, s1), z, o);
    const cyl = (m, x, y, z0, r0, r1, h, seg = 12) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) => {
      const g = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
      g.dispose();
    };
    // Rectangle ring (CCW) centred at (cx, cy), long axis at angle ang.
    const rect = (cx, cy, ang, L, W) => {
      const c = Math.cos(ang),
        s = Math.sin(ang);
      return [
        [-L / 2, -W / 2],
        [L / 2, -W / 2],
        [L / 2, W / 2],
        [-L / 2, W / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    // Triangular gable (pediment) standing on edge e between s0..s1, base z, rise, from d0..d1.
    const gable = (m, e, s0, s1, z, rise, d0 = 0, d1 = 0.4) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, 0);
      sh.lineTo(s1, 0);
      sh.lineTo((s0 + s1) / 2, rise);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d1 - d0, bevelEnabled: false });
      // shape x along edge, y up, extrude z outward -> map to world
      const m4 = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m4.setPosition(e.a[0] + e.nx * d0, e.a[1] + e.ny * d0, z);
      batch.addGeometry(m, g, m4);
      g.dispose();
    };
    // Facing test: cosine between an edge's outward normal and a direction (dx, dy).
    const facing = (e, dx, dy) => (e.nx * dx + e.ny * dy) / (Math.hypot(dx, dy) || 1);
    // Sloped band (mansard / hipped roof) from ring at z0 to the ring inset by `inset` at z1.
    // Returns the inner ring; capped with topMat unless topMat is null.
    const mansard = (m, ring, z0, inset, z1, topMat = m) => {
      const inner = kit.offsetRing(ring, -inset);
      for (let k = 0; k < ring.length; k++) {
        const j = (k + 1) % ring.length;
        const a = ring[k],
          b = ring[j],
          c = inner[j],
          d = inner[k];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [d[0], d[1], z1],
          [0, 0],
          [l / 3, 0],
          [l / 3, 1],
          [0, 1],
        );
      }
      if (topMat) kit.cap(batch, topMat, [[inner]], z1);
      return inner;
    };
    // Rows of windows on edge e at each sill height in zs.
    const rows = (e, s0, s1, zs, o) => {
      for (const z of zs)
        kit.windowRow(batch, at(e, s0), at(e, s1), z, typeof o === 'function' ? o(z) : o);
    };
    // ---------------------------------------------------------------------------------
    const cream = kit.mat('#ece2c6', { roughness: 0.75 });
    const cream2 = kit.mat('#ddd1b0', { roughness: 0.8 });
    const glass = kit.mat('#2d3a43', { roughness: 0.12, metalness: 0.4 });
    const frame = kit.mat('#3e4a3f', { roughness: 0.5, metalness: 0.3 });
    const roofM = kit.mat('#878681');
    const black = kit.mat('#1e2022');
    const ring = ccw(buildings[0].polys[0][0]);
    const Z3 = 11.6,
      H = 15.4;
    kit.walls(batch, cream, [[ring]], 0, Z3);
    kit.cornice(batch, cream2, ring, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(batch, cream2, ring, Z3 - 0.5, { height: 0.5, projection: 0.35 });
    kit.cap(batch, roofM, [[ring]], Z3);
    const top = kit.offsetRing(ring, -1.2);
    prism(cream2, top, Z3, H, roofM);
    kit.cornice(batch, cream, top, H - 0.4, { height: 0.4, projection: 0.2 });
    const E = edges(ring);
    for (const e of E) {
      if (e.len < 6) continue;
      // continuous horizontal window bands between vertical piers
      const np = Math.max(1, Math.round(e.len / 4.2));
      for (let k = 0; k <= np; k++) {
        const s = (k * e.len) / np;
        ebox(cream, e, Math.max(0, s - 0.3), Math.min(e.len, s + 0.3), 0, 0.3, 4.6, Z3 - 0.5);
      }
      for (const [z0, z1] of [
        [5.2, 7.4],
        [8.6, 10.6],
      ]) {
        ebox(glass, e, 0.3, e.len - 0.3, -0.05, 0.02, z0, z1);
        for (let k = 0; k < np; k++)
          for (let m = 1; m < 4; m++) {
            const s = ((k + m / 4) * e.len) / np;
            ebox(frame, e, s - 0.04, s + 0.04, 0, 0.08, z0, z1);
          }
        ebox(
          frame,
          e,
          0.3,
          e.len - 0.3,
          0,
          0.08,
          z0 + (z1 - z0) * 0.62,
          z0 + (z1 - z0) * 0.62 + 0.06,
        );
        ebox(cream2, e, 0, e.len, 0, 0.18, z0 - 0.25, z0);
      }
      // ground floor: shop fronts / booking hall glazing with fascia
      ebox(glass, e, 0.5, e.len - 0.5, -0.05, 0.02, 0.5, 3.6);
      ebox(cream2, e, 0, e.len, 0, 0.35, 3.6, 4.6);
      ebox(black, e, 0, e.len, 0, 0.1, 0, 0.5);
      // 1960s top storey: plain windows
      const t = edges(top)[e.k];
      if (t && t.len > 4)
        wins(t, 0, t.len, Z3 + 0.8, {
          bay: 2.4,
          margin: 0.6,
          width: 1.5,
          height: 1.9,
          head: 'none',
          frame,
          sill: cream,
          glass,
          bars: 1,
        });
    }
    // corner tower at Buckingham Palace Road / Elizabeth Street (north-east tip)
    const tip = ring.reduce((p, q) => (q[0] - 0.3 * q[1] > p[0] - 0.3 * p[1] ? q : p));
    const fr = kit.ringFrame(ring);
    const dx = fr.cx - tip[0],
      dy = fr.cy - tip[1],
      dl = Math.hypot(dx, dy);
    const tc = [tip[0] + (dx / dl) * 5, tip[1] + (dy / dl) * 5];
    const tang = Math.atan2(dy, dx);
    const T = rect(tc[0], tc[1], tang, 8, 8);
    prism(cream, T, 0, 21, roofM);
    kit.cornice(batch, cream2, T, 20.5, { height: 0.5, projection: 0.3 });
    const T2 = rect(tc[0], tc[1], tang, 5.6, 5.6);
    prism(cream, T2, 21, 24, roofM);
    const T3 = rect(tc[0], tc[1], tang, 3.4, 3.4);
    prism(cream2, T3, 24, 26, roofM);
    cyl(kit.mat('white'), tc[0], tc[1], 26, 0.08, 0.05, 6, 6);
    for (const e of edges(T)) {
      // stepped vertical fins and a tall window slot up the tower face
      for (const s of [1.2, 2.2, e.len - 2.2, e.len - 1.2])
        ebox(cream2, e, s - 0.18, s + 0.18, 0, 0.55, 4.6, 20.5);
      ebox(glass, e, 2.6, e.len - 2.6, -0.05, 0.03, 5.0, 19.0);
      for (let z = 6.4; z < 19; z += 1.6) ebox(frame, e, 2.6, e.len - 2.6, 0, 0.07, z, z + 0.08);
      ebox(frame, e, e.len / 2 - 0.04, e.len / 2 + 0.04, 0, 0.07, 5.0, 19.0);
    }
    for (const e of edges(T2))
      for (const s of [0.9, e.len - 0.9]) ebox(cream2, e, s - 0.15, s + 0.15, 0, 0.35, 21, 23.6);
    // lettering bands on both street fronts and an entrance canopy at the corner
    const sign = kit.paintedMaterial('victoria_coach_station:sign', 1024, 64, (c, w, h) => {
      c.fillStyle = '#ece2c6';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#1f3b6b';
      c.font = 'bold 40px sans-serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('VICTORIA COACH STATION', w / 2, h / 2 + 2);
    });
    const fronts = E.filter((e) => e.len > 25)
      .sort(
        (p, q) =>
          Math.hypot(p.a[0] - tip[0], p.a[1] - tip[1]) +
          Math.hypot(p.b[0] - tip[0], p.b[1] - tip[1]) -
          Math.hypot(q.a[0] - tip[0], q.a[1] - tip[1]) -
          Math.hypot(q.b[0] - tip[0], q.b[1] - tip[1]),
      )
      .slice(0, 2);
    for (const e of fronts) {
      const near =
        Math.hypot(e.a[0] - tip[0], e.a[1] - tip[1]) < Math.hypot(e.b[0] - tip[0], e.b[1] - tip[1]);
      const s0 = near ? 10 : e.len - 26,
        s1 = s0 + 16;
      const a = at(e, s0, 0.37),
        b = at(e, s1, 0.37);
      batch.quad(
        sign,
        [a[0], a[1], 3.75],
        [b[0], b[1], 3.75],
        [b[0], b[1], 4.45],
        [a[0], a[1], 4.45],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const cs = near ? 1 : e.len - 9;
      ebox(cream2, e, cs, cs + 8, 0, 2.4, 3.3, 3.6);
    }
    g.add(batch.toGroup('victoria_coach_station'));
    return g;
  },
};
