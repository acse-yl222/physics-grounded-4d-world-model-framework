// Mandarin Oriental Hyde Park, 66 Knightsbridge (Archer & Green, completed by Archer &
// Hooper, 1888-92; built as Hyde Park Court apartments, a hotel from 1902). A tall
// Franco-Flemish block of red brick with Portland stone dressings, turrets and balconies
// between Knightsbridge and the park; its ~100 ft height was controversial at the time.
export default {
  id: 'mandarin_oriental_hyde_park',
  name: 'Mandarin Oriental Hyde Park',
  claims: ['87acb2f0-7381-4ab0-a0df-dc0b544861a3'],
  references: [
    {
      title: 'Mandarin Oriental Hyde Park, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Mandarin_Oriental_Hyde_Park,_London',
      used_for:
        'opened 1889 as apartments, hotel from 1902, Archer & Green / Archer & Hooper, height controversy',
    },
    {
      title: 'Survey of London vol. 45 (British History Online)',
      url: 'https://prod.british-history.ac.uk/node/38591',
      used_for:
        'Hyde Park Court by Archer & Green 1888-92; 100 ft height retained after the bill to limit it to 60 ft failed',
    },
    {
      title: 'Knightsbridge and South Kensington tour - start Mandarin Oriental (VoiceMap)',
      url: 'https://voicemap.me/tour/london/knightsbridge-and-south-kensington-prince-albert-s-lasting-legacy/sites/start-mandarin-oriental',
      used_for:
        'red brick and Portland stone, eclectic Franco-Flemish style with turrets and balconies',
    },
  ],
  notes:
    'Overall height ~33 m (Overture 32.8 m, consistent with the 100 ft limit). Storey split (5 m ground + ' +
    '7 x 3.25 m), the positions of the corner turrets, the central gabled frontispieces with entrance canopy ' +
    'on Knightsbridge and the park-side central tower, dormer count and stone banding rhythm are ' +
    'approximations of the described style; no measured elevations were available.',
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
    const brick = kit.mat('#a24c36', { roughness: 0.88 });
    const stone = kit.mat('#ddd5c2', { roughness: 0.8 });
    const slate = kit.mat('#545a60', { roughness: 0.75 });
    const lead = kit.mat('lead');
    const glass = kit.mat('#2e3d47', { roughness: 0.15, metalness: 0.35 });
    const frame = kit.mat('#efeee8');
    const iron = kit.mat('#2a2c2e', { roughness: 0.5, metalness: 0.5 });
    const canopy = kit.mat('#1f2326', { roughness: 0.4, metalness: 0.4 });
    const gold = kit.mat('gold');

    const ring = ccw(buildings[0].polys[0][0]);
    const G = 5.0,
      ST = 3.25,
      NU = 7,
      CORN = G + NU * ST; // 27.75
    const E = edges(ring);
    kit.walls(batch, stone, [[ring]], 0, G);
    kit.walls(batch, brick, [[ring]], G, CORN);
    kit.cornice(batch, stone, ring, 0, { height: 0.8, projection: 0.2 });
    kit.cornice(batch, stone, ring, G - 0.4, { height: 0.6, projection: 0.35 });
    for (const f of [2, 4, 6])
      kit.cornice(batch, stone, ring, G + f * ST - 0.2, { height: 0.35, projection: 0.12 });
    kit.cornice(batch, stone, ring, CORN - 0.6, { height: 0.9, projection: 0.6, steps: 2 });
    // steep slate mansard with flat top
    const inner = mansard(slate, ring, CORN + 0.3, 3.2, CORN + 4.6, lead);
    kit.walls(batch, stone, [[ring]], CORN, CORN + 0.3);

    const main = E.filter((e) => e.len > 12);
    for (const e of main) {
      // ground: tall arched windows in stone
      wins(e, 0, e.len, 0.9, {
        width: 2.2,
        height: 3.0,
        bay: 4.2,
        margin: 2.5,
        head: 'arch',
        frame,
        sill: stone,
        glass,
        bars: 1,
      });
      // upper storeys: stone-dressed sash windows, pediments on the first floor
      rows(
        e,
        0,
        e.len,
        Array.from({ length: NU }, (_, k) => G + k * ST + 0.8),
        (z) => ({
          width: 1.3,
          height: 2.0,
          bay: 3.1,
          margin: 2.0,
          head: z < G + 1 ? 'pediment' : 'lintel',
          frame,
          sill: stone,
          glass,
          bars: 1,
          surround: 0.12,
          surroundMat: stone,
        }),
      );
      // iron balconies at first and fourth floor
      for (const f of [0, 3])
        ebox(iron, e, 2.5, e.len - 2.5, 0, 0.9, G + f * ST + 0.7, G + f * ST + 0.8);
      for (const f of [0, 3])
        ebox(iron, e, 2.5, e.len - 2.5, 0.85, 0.9, G + f * ST + 0.8, G + f * ST + 1.7);
      // dormers in the mansard with small gables
      const nd = Math.floor((e.len - 6) / 5.5);
      for (let k = 0; k < nd; k++) {
        const s = 3 + (k + 0.5) * ((e.len - 6) / nd);
        ebox(brick, e, s - 1.0, s + 1.0, -1.6, -0.4, CORN + 0.3, CORN + 3.2);
        wins(e, s - 1.0, s + 1.0, CORN + 0.8, {
          width: 1.0,
          height: 1.8,
          count: 1,
          margin: 0.5,
          head: 'none',
          frame,
          sill: stone,
          glass,
          bars: 1,
        });
        gable(stone, e, s - 1.2, s + 1.2, CORN + 3.2, 1.1, -1.6, -0.3);
      }
    }
    // Knightsbridge (south) and park (north) frontispieces: stepped Flemish gable over the centre bays
    const south = main.reduce((p, q) => (q.ny < p.ny ? q : p));
    const north = main.reduce((p, q) => (q.ny > p.ny ? q : p));
    for (const e of [south, north]) {
      const sm = e.len / 2;
      ebox(brick, e, sm - 6, sm + 6, -0.2, 0.6, G, CORN + 4);
      for (let k = 0; k < 3; k++)
        ebox(
          brick,
          e,
          sm - 6 + k * 1.6,
          sm + 6 - k * 1.6,
          -0.2,
          0.6,
          CORN + 4 + k * 1.3,
          CORN + 5.3 + k * 1.3,
        );
      ebox(stone, e, sm - 2.4, sm + 2.4, -0.25, 0.7, CORN + 6.9, CORN + 7.5);
      rows(
        e,
        sm - 6,
        sm + 6,
        Array.from({ length: NU }, (_, k) => G + k * ST + 0.8),
        {
          width: 1.6,
          height: 2.1,
          count: 3,
          margin: 1.2,
          head: 'segment',
          frame,
          sill: stone,
          glass,
          bars: 1,
          depth: 0.7,
          surround: 0.15,
          surroundMat: stone,
        },
      );
      wins(e, sm - 3, sm + 3, CORN + 1, {
        width: 1.4,
        height: 2.4,
        count: 2,
        margin: 0.5,
        head: 'arch',
        frame,
        sill: stone,
        glass,
        depth: 0.7,
      });
      // stone quoins at the frontispiece edges
      for (const s of [sm - 6, sm + 6])
        for (let z = G; z < CORN; z += 1.2)
          ebox(stone, e, s - 0.45, s + 0.45, 0.6, 0.7, z, z + 0.6);
    }
    // main entrance canopy on Knightsbridge with flagpoles
    {
      const e = south,
        sm = e.len / 2;
      ebox(canopy, e, sm - 5, sm + 5, 0, 4.5, 3.8, 4.3);
      ebox(gold, e, sm - 5, sm + 5, 4.45, 4.5, 3.8, 4.3);
      for (const s of [sm - 4.8, sm + 4.8]) {
        const p = at(e, s, 4.3);
        cyl(iron, p[0], p[1], 0, 0.08, 0.08, 3.8, 6);
      }
      ebox(glass, e, sm - 2.5, sm + 2.5, 0, 0.15, 0, 3.6);
      for (let k = -2; k <= 2; k++) {
        const p = at(e, sm + k * 2.4, 0.6);
        cyl(kit.mat('white'), p[0], p[1], G + 0.6, 0.06, 0.04, 5, 5);
      }
    }
    // corner turrets with ogee caps
    const corners = [];
    for (const e of main) corners.push(e.a);
    const fr = kit.ringFrame(ring);
    for (const c of corners) {
      const dx = fr.cx - c[0],
        dy = fr.cy - c[1],
        l = Math.hypot(dx, dy);
      const x = c[0] + (dx / l) * 1.5,
        y = c[1] + (dy / l) * 1.5;
      cyl(brick, x, y, G, 2.6, 2.6, CORN - G + 2, 8);
      for (let z = G + 2 * ST; z < CORN; z += 2 * ST) cyl(stone, x, y, z - 0.2, 2.75, 2.75, 0.4, 8);
      cyl(stone, x, y, CORN + 2, 2.9, 2.9, 0.6, 8);
      lathe(
        slate,
        [
          [0.01, 0],
          [3.0, 0],
          [2.6, 1.6],
          [1.4, 3.6],
          [0.5, 5.2],
          [0.12, 6.4],
          [0.01, 6.6],
        ],
        x,
        y,
        CORN + 2.6,
        8,
      );
      cyl(gold, x, y, CORN + 9.1, 0.05, 0.02, 1.6, 4);
    }
    // park-side central tower behind the gable
    {
      const p = at(north, north.len / 2, -5);
      const t = rect(p[0], p[1], north.ang, 7, 7);
      prism(brick, t, CORN, CORN + 7, null);
      kit.cornice(batch, stone, t, CORN + 6.4, { height: 0.6, projection: 0.4 });
      kit.pitchedRoof(batch, slate, brick, t, north.ang, CORN + 7, 4, 'pyramidal', {
        overhang: 0.3,
      });
      for (const e of edges(t))
        wins(e, 0, e.len, CORN + 4.2, {
          width: 1.0,
          height: 2.0,
          count: 2,
          margin: 1.4,
          head: 'arch',
          frame,
          sill: stone,
          glass,
          bars: 0,
        });
    }
    // chimney stacks along the roof
    const ir = edges(inner).filter((e) => e.len > 10);
    for (const e of ir) {
      for (let s = 6; s < e.len - 4; s += 11)
        ebox(brick, e, s - 0.9, s + 0.9, -1.6, -0.2, CORN + 4.6, CORN + 7.6);
    }
    g.add(batch.toGroup('mandarin_oriental_hyde_park'));
    return g;
  },
};
