// The Lanesborough, Hyde Park Corner (William Wilkins, 1827-c.1844, built as St George's
// Hospital; a hotel since 1991). Severe Greek Revival block in cream stucco: rusticated
// ground floor, raised porticoes on the Hyde Park Corner and Knightsbridge fronts
// (answering Apsley House opposite), plain pilaster strips, entablature and attic.
export default {
  id: 'the_lanesborough',
  name: 'The Lanesborough',
  claims: ['fa77d331-57b0-4b84-9ee8-000475671327'],
  references: [
    {
      title: 'The Lanesborough - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Lanesborough',
      used_for:
        "William Wilkins, begun 1827, St George's Hospital until the 1980s, hotel opened 1991",
    },
    {
      title: 'The history of The Lanesborough - Oetker Hotels',
      url: 'https://www.oetkerhotels.com/hotels/the-lanesborough/the-hotel/history/',
      used_for:
        'severe neo-Classicism inspired by the Choragic Monument of Thrasyllus; raised porticoes complementing Apsley House',
    },
    {
      title: 'The Lanesborough - Wallpaper*',
      url: 'https://www.wallpaper.com/travel/uk/london/hotels/the-lanesborough',
      used_for: 'Regency-period Greek Revival building at Hyde Park Corner',
    },
  ],
  notes:
    'Height ~17.5 m (Overture 17.2 m) split as rusticated ground floor 4.8 m, two principal storeys and an ' +
    'attic above the entablature. Portico column count (four, square-capitalled Greek Doric), their ' +
    'positions at the centre of the east (Hyde Park Corner) and north (Knightsbridge) fronts, the pilaster ' +
    'rhythm and window sizes are approximations; stucco colour from general photographs.',
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
    const stucco = kit.mat('#e8dfc9', { roughness: 0.78 });
    const stucco2 = kit.mat('#ddd2b8', { roughness: 0.8 });
    const glass = kit.mat('#2b3842', { roughness: 0.15, metalness: 0.35 });
    const frame = kit.mat('#f5f3ec');
    const roofM = kit.mat('#7c7f80');
    const slate = kit.mat('slate');
    const iron = kit.mat('#222426', { roughness: 0.5, metalness: 0.5 });

    const ring = ccw(buildings[0].polys[0][0]);
    const G = 4.8,
      ST = 3.9,
      ENT = G + 2 * ST, // 12.6 top of principal storeys
      ATT = ENT + 1.4, // entablature
      TOP = ATT + 3.4; // attic parapet ~17.4
    kit.walls(batch, stucco2, [[ring]], 0, G);
    kit.walls(batch, stucco, [[ring]], G, TOP);
    kit.cap(batch, roofM, [[ring]], TOP - 0.2);
    // rustication grooves on the ground floor
    for (let z = 0.6; z < G - 0.4; z += 0.55)
      kit.cornice(batch, stucco2, ring, z, { height: 0.42, projection: 0.06 });
    kit.cornice(batch, stucco, ring, G - 0.1, { height: 0.45, projection: 0.25 });
    kit.cornice(batch, stucco, ring, ENT, { height: ATT - ENT, projection: 0.45, steps: 3 });
    kit.cornice(batch, stucco, ring, TOP - 0.4, { height: 0.4, projection: 0.2 });
    // low slate roofs behind the parapet
    const fr = kit.ringFrame(ring);
    const rr = rect(fr.cx, fr.cy, fr.angle, fr.length - 16, fr.width - 16);
    kit.pitchedRoof(batch, slate, stucco, rr, fr.angle, TOP - 0.2, 3.2, 'hipped', { overhang: 0 });

    const E = edges(ring);
    const east = E.reduce((p, q) =>
      q.len * Math.max(0, q.nx) > p.len * Math.max(0, p.nx) ? q : p,
    );
    const north = E.reduce((p, q) =>
      q.len * Math.max(0, q.ny) > p.len * Math.max(0, p.ny) ? q : p,
    );
    for (const e of E) {
      if (e.len < 5) continue;
      const nb = Math.max(1, Math.round(e.len / 3.4));
      // pilaster strips through the principal storeys
      for (let k = 0; k <= nb; k++) {
        const s = (k * e.len) / nb;
        ebox(stucco, e, Math.max(0, s - 0.35), Math.min(e.len, s + 0.35), 0, 0.2, G, ENT);
      }
      const o = { count: nb, margin: 0.3, frame, sill: stucco, glass, bars: 1, depth: 0.14 };
      wins(e, 0, e.len, 1.0, { ...o, width: 1.25, height: 2.6, head: 'arch' });
      wins(e, 0, e.len, G + 0.6, {
        ...o,
        width: 1.35,
        height: 2.8,
        head: 'pediment',
        surround: 0.12,
        surroundMat: stucco,
      });
      wins(e, 0, e.len, G + ST + 0.6, { ...o, width: 1.35, height: 2.4, head: 'lintel' });
      wins(e, 0, e.len, ATT + 0.6, { ...o, width: 1.1, height: 1.6, head: 'none', bars: 1 });
      // first-floor balconettes
      ebox(iron, e, 0.4, e.len - 0.4, 0.15, 0.6, G + 0.35, G + 0.45);
    }
    // raised porticoes: four Greek Doric columns on the rusticated base, entablature and
    // a blocking course above
    for (const e of [east, north]) {
      const sm = e.len / 2,
        half = Math.min(9, e.len / 2 - 3);
      const d = 2.6;
      ebox(stucco2, e, sm - half - 0.6, sm + half + 0.6, 0, d + 0.4, 0, G); // podium
      for (let z = 0.6; z < G - 0.4; z += 0.55)
        ebox(stucco2, e, sm - half - 0.65, sm + half + 0.65, d + 0.4, d + 0.46, z, z + 0.42);
      kit.colonnade(
        batch,
        stucco,
        at(e, sm - half + 0.8, d),
        at(e, sm + half - 0.8, d),
        G,
        ENT - G,
        { count: 4, radius: 0.62, capital: 'doric' },
      );
      // antae at the ends
      for (const s of [sm - half - 0.2, sm + half + 0.2])
        ebox(stucco, e, s - 0.55, s + 0.55, 0, d + 0.4, G, ENT);
      ebox(stucco, e, sm - half - 0.8, sm + half + 0.8, 0, d + 0.8, ENT, ATT);
      ebox(stucco, e, sm - half - 0.8, sm + half + 0.8, d + 0.6, d + 0.9, ATT - 0.4, ATT);
      ebox(stucco, e, sm - half - 0.2, sm + half + 0.2, 0, d + 0.4, ATT, ATT + 1.4);
      // entrance doors beneath
      ebox(glass, e, sm - 1.4, sm + 1.4, d + 0.4, d + 0.46, 0.2, 3.3);
      ebox(frame, e, sm - 1.6, sm + 1.6, d + 0.4, d + 0.5, 3.3, 3.55);
      // inscription panel on the blocking course
      const sign = kit.paintedMaterial('lanesborough:sign', 512, 64, (c, w, h) => {
        c.fillStyle = '#e8dfc9';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#5c5442';
        c.font = '30px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('THE LANESBOROUGH', w / 2, h / 2 + 2);
      });
      const a = at(e, sm - 5, d + 0.42),
        b = at(e, sm + 5, d + 0.42);
      batch.quad(
        sign,
        [a[0], a[1], ATT + 0.2],
        [b[0], b[1], ATT + 0.2],
        [b[0], b[1], ATT + 1.2],
        [a[0], a[1], ATT + 1.2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    g.add(batch.toGroup('the_lanesborough'));
    return g;
  },
};
