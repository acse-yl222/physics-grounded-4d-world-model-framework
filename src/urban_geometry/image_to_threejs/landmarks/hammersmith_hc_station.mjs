// Hammersmith station (Circle and Hammersmith & City lines), Beadon Road. Western terminus
// of the Hammersmith & City Railway, moved here in 1868 and reconstructed in 1908: a low
// street building on Beadon Road fronting the terminal platforms, which run north under
// canopies.
export default {
  id: 'hammersmith_hc_station',
  name: 'Hammersmith station (Circle and Hammersmith & City lines)',
  claims: ['aacf332d-d056-4c82-b113-b9b3cf81bf9e', 'a8583a5b-7334-4a82-85fd-74d10361eb75'],
  references: [
    {
      title: 'Hammersmith tube station (Circle and Hammersmith & City lines) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_tube_station_(Circle_and_Hammersmith_%26_City_lines)',
      used_for:
        'opened 1 December 1868 on Beadon Road, western terminus of the Circle and H&C lines',
    },
    {
      title: 'Hammersmith and City Railway - AIM25',
      url: 'https://atom.aim25.com/index.php/hammersmith-and-city-railway-4',
      used_for: 'station moved 150 yards south in 1868 and reconstructed in 1908',
    },
    {
      title: 'Hammersmith Station, Beadon Road - Buildington',
      url: 'https://www.buildington.co.uk/buildings/5266/england/london-w6/beadon-road/hammersmith-station',
      used_for: 'station building on Beadon Road',
    },
  ],
  notes:
    'No description of the facade was found. The street building is modelled as a single tall storey of red ' +
    'brick with stone dressings and a parapet (Edwardian, consistent with the 1908 rebuild), with a glazed ' +
    'entrance, canopy and roundels; the second footprint is modelled as the platform canopy. Heights (5.5 m ' +
    'building, 4.0 m canopy) and all details are assumptions.',
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
    const stn = ccw(buildings.find((b) => b.id.startsWith('aacf332d')).polys[0][0]);
    const roofR = ccw(buildings.find((b) => b.id.startsWith('a8583a5b')).polys[0][0]);
    const brick = kit.mat('#93473a', { roughness: 0.9 });
    const stone = kit.mat('portland_stone');
    const glass = kit.mat('#3a4952', { roughness: 0.15, metalness: 0.3 });
    const canopy = kit.mat('#d8dadb', { roughness: 0.4, metalness: 0.3 });
    const green = kit.mat('#2f5d45');
    const roofM = kit.mat('#7d7f80');
    const luRed = kit.mat('#dc241f', { roughness: 0.5 });
    const luBlue = kit.mat('#0019a8', { roughness: 0.5 });
    const H = 5.5;
    kit.walls(B, brick, [[stn]], 0, H, { bay: 1e6 });
    kit.cap(B, roofM, [[stn]], H);
    kit.cornice(B, stone, stn, 0, { height: 0.5, projection: 0.1 });
    kit.cornice(B, stone, stn, H - 0.6, { height: 0.35, projection: 0.25 });
    parapet(brick, stn, H, 0.8, 0.3);
    kit.cornice(B, stone, stn, H + 0.7, { height: 0.12, projection: 0.06 });
    winRows(
      stn,
      1.2,
      1,
      0,
      {
        width: 1.4,
        height: 2.6,
        bay: 3.4,
        margin: 0.8,
        glass,
        frame: kit.mat('white'),
        sill: stone,
        head: 'segment',
        bars: 2,
      },
      6,
    );
    // main entrance on the longest edge facing south (Beadon Road)
    const ent =
      edgesOf(stn)
        .filter((e) => e.ny < -0.3 && e.len > 5)
        .sort((a, b) => b.len - a.len)[0] || edgesOf(stn).sort((a, b) => b.len - a.len)[0];
    const m = ent.len / 2;
    ebox(glass, ent, m - 3, m + 3, 0.0, 0.32, 0, 3.4);
    ebox(stone, ent, m - 3.5, m + 3.5, 0, 0.4, 3.4, 4.0);
    ebox(canopy, ent, m - 4, m + 4, 0, 2.0, 3.5, 3.7);
    ebox(
      signMat('hmc:sign', 'HAMMERSMITH STATION', '#93473a', '#f4efe2', 'bold 34px serif'),
      ent,
      m - 4,
      m + 4,
      0.4,
      0.45,
      4.1,
      4.9,
    );
    for (const s of [m - 5.2, m + 5.2]) {
      const c = at(ent, s, 0.45);
      const rg = new THREE.TorusGeometry(0.6, 0.15, 6, 20).rotateX(Math.PI / 2);
      B.addGeometry(
        luRed,
        rg,
        new THREE.Matrix4().makeRotationZ(ent.ang).setPosition(c[0], c[1], 3.0),
      );
      rg.dispose();
      kit.box(B, luBlue, c[0], c[1], 2.87, 1.6, 0.1, 0.27, ent.ang);
    }
    // platform canopy over the concourse/platform ends: pitched glazed strip on green columns
    {
      const f = kit.ringFrame(roofR);
      kit.cap(B, canopy, [[roofR]], 4.0);
      kit.cap(B, canopy, [[roofR]], 3.95, { down: true });
      kit.walls(B, green, [[roofR]], 3.6, 4.0, { bay: 1e6 });
      for (let u = -f.length / 2 + 1.5; u <= f.length / 2 - 1.5; u += 5)
        for (const v of [-f.width / 4, f.width / 4]) {
          const p = frameAt(f, u, v);
          cyl(green, p[0], p[1], 0, 0.12, 0.12, 3.95, 8);
        }
      const a = frameAt(f, -f.length / 2 + 1, 0),
        b = frameAt(f, f.length / 2 - 1, 0);
      const e = edgesOf([a, b])[0];
      ebox(
        kit.mat('#a9bcc4', { roughness: 0.1, metalness: 0.3 }),
        e,
        0,
        e.len,
        -1.5,
        1.5,
        4.0,
        4.6,
      );
    }
    g.add(B.toGroup('hammersmith_hc_station'));
    return g;
  },
};
