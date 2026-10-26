// Royal Court Theatre, Sloane Square (Walter Emden with Bertie Crewe, opened 24 September
// 1888 as the New Court Theatre; rebuilt behind the facade by Haworth Tompkins, 2000).
// Grade II. Free Italianate front of red brick and moulded brick with stone dressings and a
// painted ground floor: four storeys in three main bays, central pediment, applied
// Corinthian columns on the upper floor, carved cambered pediments over the outer bays,
// round-headed first- and fourth-floor windows and a balustraded parapet.
export default {
  id: 'royal_court_theatre',
  name: 'Royal Court Theatre',
  claims: ['fdd18601-b9bb-4f1d-9d44-cd9f9b49e4ab'],
  references: [
    {
      title: 'Royal Court Theatre - Historic England list entry 1226628 (British Listed Buildings)',
      url: 'https://britishlistedbuildings.co.uk/101226628-royal-court-theatre-royal-hospital-ward',
      used_for:
        'Grade II, 1888 Emden and Crewe; red brick, stone dressings, painted ground floor; 4 storeys, 3 bays, central pediment, Corinthian columns, cambered pediments, round-headed windows, balustraded parapet',
    },
    {
      title: 'Royal Court Theatre - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Court_Theatre',
      used_for:
        'opened 24 September 1888 as the New Court Theatre; fine red brick and stone facade in a free Italianate style',
    },
    {
      title: 'Royal Court Theatre - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=1226628',
      used_for: 'interior reconstructed 1952, altered 1956 and 1980',
    },
  ],
  notes:
    'Facade height ~17 m with storey split 4.6 / 4.2 / 3.4 / 3.4 m, the auditorium/fly-tower massing behind ' +
    '(19 m) and the modern canopy with the name in lights are estimates. Corinthian columns are applied ' +
    'three-quarter columns on the second-floor storey of the centre bay; the carved pediments are drawn ' +
    'as segmental heads.',
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
    const brick = kit.mat('#a3503b', { roughness: 0.88 });
    const stone = kit.mat('#e2d9c4', { roughness: 0.8 });
    const paint = kit.mat('#eeebe3', { roughness: 0.7 });
    const glass = kit.mat('#2a353d', { roughness: 0.15, metalness: 0.35 });
    const frame = kit.mat('#f4f2ec');
    const roofM = kit.mat('#7f8180');
    const dark = kit.mat('#3c3f42');

    const ring = ccw(buildings[0].polys[0][0]);
    const E = edges(ring);
    const front = E.reduce((p, q) => (q.len * -q.nx > p.len * -p.nx ? q : p)); // west, onto Sloane Square
    const zs = [0, 4.6, 8.8, 12.2, 15.6];
    const TOP = 16.8;
    // auditorium and stage house behind
    kit.walls(batch, kit.mat('#8f4a39'), [[ring]], 0, 14);
    kit.cap(batch, roofM, [[ring]], 14);
    const fr = kit.ringFrame(ring);
    const sg = Math.sign(Math.cos(fr.angle)) || 1;
    const fly = rect(
      fr.cx + Math.cos(fr.angle) * 5 * sg,
      fr.cy + Math.sin(fr.angle) * 5 * sg,
      fr.angle,
      12,
      12,
    );
    prism(kit.mat('#8f4a39'), fly, 14, 19.5, roofM);
    // front block (6 m deep) carrying the listed facade
    const f0 = at(front, 0),
      f1 = at(front, front.len);
    const fb = ccw([f0, f1, at(front, front.len, -6), at(front, 0, -6)]);
    kit.walls(batch, paint, [[fb]], 0, zs[1]);
    kit.walls(batch, brick, [[fb]], zs[1], TOP);
    kit.cap(batch, roofM, [[fb]], TOP - 0.2);
    const e = front,
      L = e.len;
    // painted ground floor: entrance doors and canopy with the name in lights
    wins(e, 0, L, 0.1, {
      width: 1.8,
      height: 3.0,
      count: 4,
      margin: 1.2,
      head: 'none',
      frame: dark,
      sill: paint,
      glass,
      bars: 1,
    });
    ebox(dark, e, 0.6, L - 0.6, 0, 2.2, 3.4, 3.75);
    {
      const a = at(e, 2, 2.25),
        b = at(e, L - 2, 2.25);
      const sign = kit.paintedMaterial(
        'royal_court:sign',
        512,
        64,
        (c, w, h) => {
          c.fillStyle = '#1b1b1d';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#e8463c';
          c.font = 'bold 40px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('ROYAL COURT', w / 2, h / 2 + 2);
        },
        { emissive: new THREE.Color('#401010'), roughness: 0.5 },
      );
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
    }
    // string courses and cornice
    for (const z of [zs[1], zs[2], zs[3]]) ebox(stone, e, 0, L, 0, 0.3, z - 0.25, z + 0.1);
    ebox(stone, e, -0.2, L + 0.2, 0, 0.55, zs[4] - 0.4, zs[4] + 0.1);
    // three bays: outer bays 4.6 m, centre the rest
    const ob = 4.6;
    const bays = [
      [0, ob],
      [ob, L - ob],
      [L - ob, L],
    ];
    // brick pilasters with stone quoins between bays
    for (const s of [0.4, ob, L - ob, L - 0.4]) {
      ebox(brick, e, s - 0.45, s + 0.45, 0, 0.35, zs[1], zs[4]);
      for (let z = zs[1] + 0.2; z < zs[4] - 0.5; z += 0.9)
        ebox(stone, e, s - 0.5, s + 0.5, 0.3, 0.4, z, z + 0.45);
    }
    for (const [s0, s1] of bays) {
      const centre = s0 > 0.1 && s1 < L - 0.1;
      // first floor: round-headed windows
      wins(e, s0, s1, zs[1] + 0.7, {
        width: 1.4,
        height: 2.4,
        count: centre ? 3 : 1,
        margin: 0.6,
        head: 'arch',
        frame,
        sill: stone,
        glass,
        bars: 1,
        surround: 0.15,
        surroundMat: stone,
      });
      // second floor: centre bay behind applied Corinthian columns; outer with cambered pediments
      wins(e, s0, s1, zs[2] + 0.5, {
        width: 1.3,
        height: 2.2,
        count: centre ? 3 : 1,
        margin: 0.6,
        head: centre ? 'lintel' : 'segment',
        frame,
        sill: stone,
        glass,
        bars: 1,
      });
      if (!centre) {
        const sm = (s0 + s1) / 2;
        gable(stone, e, sm - 1.1, sm + 1.1, zs[2] + 3.05, 0.55, 0, 0.35);
      }
      // third floor
      wins(e, s0, s1, zs[3] + 0.5, {
        width: 1.1,
        height: 1.9,
        count: centre ? 3 : 1,
        margin: 0.6,
        head: 'lintel',
        frame,
        sill: stone,
        glass,
        bars: 1,
      });
    }
    // applied Corinthian columns across the centre bay, second floor
    kit.colonnade(
      batch,
      stone,
      at(e, ob + 0.6, 0.35),
      at(e, L - ob - 0.6, 0.35),
      zs[2],
      zs[3] - zs[2] - 0.25,
      { count: 4, radius: 0.25, capital: 'corinthian' },
    );
    // fourth (attic) storey: round-headed windows, central pediment
    ebox(brick, e, 0, L, -0.1, 0.05, zs[4], TOP);
    wins(e, 0, L, zs[4] + 0.2, {
      width: 0.8,
      height: 0.8,
      count: 5,
      margin: 1.0,
      head: 'arch',
      frame,
      sill: stone,
      glass,
      bars: 0,
    });
    gable(stone, e, ob - 0.3, L - ob + 0.3, TOP, 2.2, -0.1, 0.5);
    ebox(stone, e, ob - 0.4, L - ob + 0.4, -0.1, 0.55, TOP - 0.3, TOP);
    // balustraded parapet over the outer bays
    for (const [s0, s1] of [
      [0, ob - 0.3],
      [L - ob + 0.3, L],
    ])
      kit.balustrade(batch, stone, [at(e, s0, 0.25), at(e, s1, 0.25)], TOP, {
        height: 1.0,
        spacing: 0.32,
      });
    g.add(batch.toGroup('royal_court_theatre'));
    return g;
  },
};
