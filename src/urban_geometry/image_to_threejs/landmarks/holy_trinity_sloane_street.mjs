// Holy Trinity Sloane Street (John Dando Sedding, 1888-90, paid for by the 5th Earl
// Cadogan). Grade I, the "cathedral of the Arts and Crafts movement". Late Gothic in red
// brick with stone panels and banding; the Sloane Street (west) front has an eight-light
// flowing-traceried window between corner turrets. Said to be the widest church in London.
export default {
  id: 'holy_trinity_sloane_street',
  name: 'Holy Trinity Sloane Street',
  claims: ['267459f4-7e2e-4bc9-ae85-0155ba879695'],
  references: [
    {
      title: 'Holy Trinity Sloane Street - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Holy_Trinity_Sloane_Street',
      used_for: 'Sedding 1888-90, Arts and Crafts Gothic, 5th Earl Cadogan, Grade I',
    },
    {
      title: 'Holy Trinity - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=423999',
      used_for:
        'red brick with stone panels and banding, late Gothic, 8-light flowing traceried west window, corner turrets',
    },
    {
      title: 'Holy Trinity Sloane Street - Victorian Web',
      url: 'https://victorianweb.org/victorian/art/architecture/trinity/22.html',
      used_for: 'huge west and east windows with flowing tracery (Cherry and Pevsner)',
    },
    {
      title: "Holy Trinity Sloane Square is John Betjeman's cathedral - Patrick Comerford",
      url: 'https://www.patrickcomerford.com/2022/09/holy-trinity-sloane-square-is-john.html?m=1',
      used_for: 'widest church in London',
    },
  ],
  notes:
    'Wall height 15 m, ridge ~24 m and turret height ~27 m are estimates (Overture 16.6 m). Turret form ' +
    '(octagonal with stone caps and short spirelets), window tracery (drawn as a mullioned arched window), ' +
    'the side-aisle windows, buttress rhythm and the low vestry strip at the east end are simplified.',
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
    const brick = kit.mat('#9b4a38', { roughness: 0.88 });
    const stone = kit.mat('#dcd3bd', { roughness: 0.8 });
    const slate = kit.mat('#4c535a', { roughness: 0.75 });
    const glass = kit.mat('#34404b', { roughness: 0.2, metalness: 0.25 });
    const lead = kit.mat('lead');
    const b = buildings[0];
    const ring = ccw(b.polys[0][0]);
    const H = 15.0;
    // main body (west of the vestry strip at x > 3009)
    const body = ccw([
      [2963, -1465],
      [2968, -1497],
      [3013, -1489],
      [3009, -1456],
    ]);
    const vestry = ccw([
      [3009, -1459],
      [3013, -1485],
      [3017, -1484],
      [3012, -1458],
    ]);
    kit.walls(batch, brick, [[ring]], 0, 4.6);
    kit.cap(batch, lead, [[vestry]], 4.6);
    kit.walls(batch, brick, [[body]], 4.6, H);
    kit.cap(batch, lead, [[body]], H - 0.2);
    kit.cornice(batch, stone, ring, 0, { height: 0.7, projection: 0.15 });
    for (const z of [4.6, 9.5])
      kit.cornice(batch, stone, body, z, { height: 0.35, projection: 0.1 });
    kit.cornice(batch, stone, body, H - 0.6, { height: 0.6, projection: 0.3 });
    const E = edges(body);
    const west = E.reduce((p, q) => (q.nx < p.nx ? q : p));
    const east = E.reduce((p, q) => (q.nx > p.nx ? q : p));
    const ang = Math.atan2(east.my - west.my, east.mx - west.mx);
    // great roof, ridge along the axis
    kit.pitchedRoof(batch, slate, brick, body, ang, H - 0.2, 9.0, 'gabled', { overhang: 0.3 });
    for (const e of E) {
      if (e === west || e === east) {
        // huge traceried window with stone surround and gable banding
        const w = Math.min(12, e.len - 9);
        wins(e, 0, e.len, 4.2, {
          width: w,
          height: H - 4.6,
          count: 1,
          margin: (e.len - w) / 2,
          head: 'arch',
          frame: stone,
          sill: stone,
          glass,
          bars: 7,
          depth: 0.3,
        });
        // stone banding across the gable
        for (let k = 0; k < 6; k++) {
          const z = H + 0.6 + k * 1.4;
          const half = (e.len / 2) * (1 - (z - H + 0.2) / 9.2);
          if (half > 0.5) ebox(stone, e, e.len / 2 - half, e.len / 2 + half, 0, 0.08, z, z + 0.3);
        }
        if (e === west) {
          // west doors under the window and a stone panel band
          wins(e, 0, e.len, 0.15, {
            width: 2.0,
            height: 3.2,
            count: 3,
            margin: e.len / 2 - 6,
            head: 'arch',
            frame: stone,
            sill: stone,
            glass: kit.mat('#4b3526'),
            bars: 0,
            depth: 0.3,
          });
          ebox(stone, e, 2, e.len - 2, 0, 0.15, 3.6, 4.0);
          // corner turrets: octagonal, banded, with stone caps and spirelets
          for (const s of [0.6, e.len - 0.6]) {
            const p = at(e, s, 0.6);
            cyl(brick, p[0], p[1], 0, 1.8, 1.8, H + 7, 8);
            for (let z = 3; z < H + 7; z += 3.2) cyl(stone, p[0], p[1], z, 1.88, 1.88, 0.45, 8);
            cyl(stone, p[0], p[1], H + 7, 2.05, 2.05, 0.8, 8);
            // open lantern stage
            for (let k = 0; k < 8; k++) {
              const a = (k * Math.PI) / 4;
              cyl(
                stone,
                p[0] + Math.cos(a) * 1.5,
                p[1] + Math.sin(a) * 1.5,
                H + 7.8,
                0.2,
                0.2,
                2.2,
                5,
              );
            }
            cyl(stone, p[0], p[1], H + 10, 1.9, 1.9, 0.6, 8);
            cyl(lead, p[0], p[1], H + 10.6, 1.6, 0.05, 3.6, 8);
          }
        } else {
          // east end: buttresses each side of the window
          for (const s of [1.5, e.len - 1.5]) ebox(stone, e, s - 0.7, s + 0.7, 0, 1.1, 0, H + 2);
        }
        continue;
      }
      if (e.len < 8) continue;
      // side elevations: buttresses, aisle windows and clerestory-height windows
      const nb = Math.round(e.len / 5.5);
      for (let k = 0; k <= nb; k++) {
        const s = (k * e.len) / nb;
        ebox(stone, e, Math.max(0, s - 0.45), Math.min(e.len, s + 0.45), 0, 0.9, 0, 4.6);
        ebox(brick, e, Math.max(0, s - 0.35), Math.min(e.len, s + 0.35), 0, 0.6, 4.6, H - 0.6);
      }
      wins(e, 0, e.len, 1.4, {
        width: 2.4,
        height: 2.6,
        count: nb,
        margin: 0,
        head: 'segment',
        frame: stone,
        sill: stone,
        glass,
        bars: 1,
        depth: 0.15,
      });
      wins(e, 0, e.len, 6.0, {
        width: 3.0,
        height: 7.4,
        count: nb,
        margin: 0,
        head: 'arch',
        frame: stone,
        sill: stone,
        glass,
        bars: 2,
        depth: 0.15,
      });
    }
    // small fleche on the ridge
    {
      const c = [(west.mx + east.mx) / 2, (west.my + east.my) / 2];
      cyl(lead, c[0], c[1], H + 8.6, 0.9, 0.9, 2.2, 8);
      cyl(lead, c[0], c[1], H + 10.8, 0.95, 0.04, 4.0, 8);
    }
    g.add(batch.toGroup('holy_trinity_sloane_street'));
    return g;
  },
};
