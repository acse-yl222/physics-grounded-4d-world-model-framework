// Novotel London West, 1 Shortlands, Hammersmith (opened c.1973-76). One of London's
// largest hotels (~630 rooms, major conference centre): a nine-storey concrete-and-brick
// complex of long bedroom wings with continuous horizontal bands of precast spandrels and
// strip windows over a two-storey podium, with a lower central lobby/conference block,
// beside the Hammersmith Flyover and the A4.
export default {
  id: 'novotel_london_west',
  name: 'Novotel London West',
  claims: ['7a32c3e8-9b17-47ce-9766-0d89c33b3ab3'],
  references: [
    {
      title: 'Novotel London West - Successful Meetings venue listing',
      url: 'https://www.successfulmeetings.com/Meeting-Event-Venues/Hammersmith-England/Convention-Hotel/Novotel-London-West-p5226159',
      used_for: '630 rooms, build year, convention hotel',
    },
    {
      title: 'Novotel London West - Meetings & Conventions',
      url: 'https://www.meetings-conventions.com/Meeting-Event-Venues/Hammersmith-England/Convention-Hotel/Novotel-London-West-p2009386',
      used_for: 'concrete and brick hotel in a nine-storey complex near Hammersmith station',
    },
    {
      title: 'Meeting and event venues in H&F for business - LBHF',
      url: 'https://www.lbhf.gov.uk/sites/default/files/section_attachments/meeting_and_event_venues_in_hf_for_business.pdf',
      used_for: '629 bedrooms, conference venue',
    },
  ],
  notes:
    'No architectural description was found beyond "concrete and brick, nine storeys". The model assigns the two ' +
    'long footprint rings to nine-storey bedroom wings (4.5 m + 3.6 m podium, 7 x 2.9 m bedroom floors, ~29 m) and ' +
    'the central rectangle to a two-storey lobby/conference block with rooflights; spandrel colour, window ' +
    'proportions, podium glazing, rooftop plant and the sign positions are assumptions. Overture h=7 m is too low.',
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
    const rings = buildings[0].polys.map((p) => ccw(p[0]));
    const area = (r) => Math.abs(kit.ringArea(r));
    // central rectangle = the 4-vertex ring
    const centre = rings.find((r) => r.length === 4) || rings[0];
    const wings = rings.filter((r) => r !== centre);

    const spandrel = kit.mat('#8f7f6c', { roughness: 0.85 }); // brown-buff precast
    const brick = kit.mat('#6e4b3c', { roughness: 0.9 });
    const conc = kit.mat('concrete');
    const glass = kit.mat('#3f505b', { roughness: 0.12, metalness: 0.35 });
    const frame = kit.mat('#2e2e2e', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#8a8a86');
    const plant = kit.mat('#a3a5a3');
    const rnd = kit.rng(0.7313);
    const G1 = 4.5,
      G2 = 8.1,
      ST = 2.9,
      NB = 7;
    const H = G2 + NB * ST;

    for (const r of wings) {
      // podium: recessed dark glazing between brick piers, concrete fascia
      const rec = kit.offsetRing(r, -0.6);
      ribbon(rec, 0, G1 - 0.5, glass, frame, 2.4);
      kit.walls(B, conc, [[r]], G1 - 0.5, G1 + 0.4, { bay: 1e6 });
      kit.cap(B, conc, [[r]], G1 - 0.5, { down: true });
      for (const e of edgesOf(r)) {
        if (e.len < 5) continue;
        const n = Math.max(1, Math.round(e.len / 7.2));
        for (let k = 0; k <= n; k++) {
          const s = 0.4 + ((e.len - 0.8) * k) / n;
          ebox(brick, e, s - 0.45, s + 0.45, -0.6, 0, 0, G1 - 0.5);
        }
      }
      ribbon(kit.offsetRing(r, -0.2), G1 + 0.4, G2 - 0.6, glass, frame, 1.8);
      kit.walls(B, conc, [[r]], G2 - 0.6, G2, { bay: 1e6 });
      // bedroom floors: continuous spandrel bands and strip windows with mullions
      for (let s = 0; s < NB; s++) {
        const z = G2 + s * ST;
        kit.walls(B, spandrel, [[r]], z, z + 1.05, { bay: 1e6 });
        ribbon(kit.offsetRing(r, -0.15), z + 1.05, z + ST, glass, spandrel, 3.6);
        kit.cornice(B, spandrel, r, z + ST - 0.12, { height: 0.12, projection: 0.12 });
      }
      kit.walls(B, spandrel, [[r]], H, H + 1.2, { bay: 1e6 });
      kit.cap(B, roofM, [[r]], H + 0.3);
      parapet(spandrel, r, H + 0.3, 0.9, 0.3);
      // brick stair / lift towers at the ends of the long edges, rising above the roof
      const long = edgesOf(r).filter((e) => e.len > 45);
      for (const e of long) {
        ebox(brick, e, 1.0, 5.5, -5.5, 0.3, 0, H + 2.6);
        ebox(brick, e, e.len - 5.5, e.len - 1.0, -5.5, 0.3, 0, H + 2.6);
      }
      plantBoxes(r, H + 0.3, rnd, 6, plant, 0.5);
    }
    // central lobby / conference block with rooflights
    {
      const r = centre;
      ribbon(kit.offsetRing(r, -0.3), 0, G1, glass, frame, 2.0);
      kit.walls(B, conc, [[r]], G1, G2 - 0.6, { bay: 1e6 });
      kit.cap(B, roofM, [[r]], G2 - 0.6);
      parapet(conc, r, G2 - 0.6, 0.8, 0.3);
      const f = kit.ringFrame(r);
      for (let k = -2; k <= 2; k++) {
        const p = frameAt(f, (k * f.length) / 6, 0);
        const sq = [
          frameAt(f, (k * f.length) / 6 - 3, -5),
          frameAt(f, (k * f.length) / 6 + 3, -5),
          frameAt(f, (k * f.length) / 6 + 3, 5),
          frameAt(f, (k * f.length) / 6 - 3, 5),
        ];
        kit.pitchedRoof(
          B,
          kit.mat('#9fb4bd', { roughness: 0.1, metalness: 0.3 }),
          frame,
          ccw(sq),
          f.angle + Math.PI / 2,
          G2 - 0.5,
          1.6,
          'hipped',
          { overhang: 0 },
        );
        void p;
      }
    }
    // NOVOTEL signs on the roofline of the largest wing
    {
      const big = wings.slice().sort((a, b) => area(b) - area(a))[0];
      const sign = signMat('novotel:sign', 'NOVOTEL', '#ffffff', '#1f2b57', 'bold 46px sans-serif');
      for (const e of edgesOf(big).filter((e) => e.len > 40)) {
        ebox(sign, e, e.len / 2 - 8, e.len / 2 + 8, 0.35, 0.45, H + 1.4, H + 3.4);
      }
    }
    g.add(B.toGroup('novotel_london_west'));
    return g;
  },
};
