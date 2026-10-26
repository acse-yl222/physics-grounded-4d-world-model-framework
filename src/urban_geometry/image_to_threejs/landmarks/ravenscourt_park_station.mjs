// Ravenscourt Park station, Ravenscourt Road (opened 1873 as Shaftesbury Road by the London
// and South Western Railway, renamed 1888; booking hall rebuilt c.1911 by the LSWR
// engineer's office). District line station on the brick viaduct beside the railway
// overpass across Ravenscourt Road: a street-level booking hall in the viaduct with
// platforms and valanced canopies above.
export default {
  id: 'ravenscourt_park_station',
  name: 'Ravenscourt Park station',
  claims: ['4f9f0492-cd84-4f07-9504-31eb5f101ea7'],
  references: [
    {
      title: 'Ravenscourt Park tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Ravenscourt_Park_tube_station',
      used_for: 'opening 1873 as Shaftesbury Road, renamed 1888, District line',
    },
    {
      title: 'Booking Hall Level drawing, LSWR Engineer’s Office 1911 - London Transport Museum',
      url: 'https://www.ltmuseum.co.uk/collections/collections-online/drawings/item/1995-1459',
      used_for: 'c.1911 rebuilding of the booking hall level',
    },
    {
      title: 'B/W print; Booking hall at Ravenscourt Park station, 1956 - London Transport Museum',
      url: 'https://www.ltmuseum.co.uk/collections/collections-online/photographs/item/1998-71432',
      used_for: 'street-level booking hall',
    },
    {
      title: 'Ravenscourt Park Tube Station - penang-traveltips',
      url: 'https://www.penang-traveltips.com/europe/uk/england/london/ravenscourt-park-tube-station.htm',
      used_for: 'station next to the railway overpass along Ravenscourt Road',
    },
  ],
  notes:
    'The footprint is treated as the viaduct station structure (booking hall in the arches, deck at ~6.5 m to ' +
    'match the road-layer rail level) with two platform canopies above. Arch spacing, brick colour, canopy ' +
    'length, valance profile, the roundel position and the frontage details are assumptions.',
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
    const ring = ccw(buildings[0].polys[0][0]);
    const f = kit.ringFrame(ring);
    const brick = kit.mat('#8a5a44', { roughness: 0.92 });
    const stock = kit.mat('london_stock');
    const stone = kit.mat('portland_stone');
    const glass = kit.mat('#3a4952', { roughness: 0.15, metalness: 0.3 });
    const green = kit.mat('#2f5d45', { roughness: 0.6 });
    const cream = kit.mat('#e9e1c9', { roughness: 0.6 });
    const canopy = kit.mat('#6e7275', { roughness: 0.6, metalness: 0.3 });
    const luRed = kit.mat('#dc241f', { roughness: 0.5 });
    const luBlue = kit.mat('#0019a8', { roughness: 0.5 });
    const ZD = 6.5;
    // viaduct body with blind arches; booking hall glazing in the arches on the street face
    kit.walls(B, stock, [[ring]], 0, ZD, { bay: 1e6 });
    kit.cap(B, kit.mat('#bcb7ad'), [[ring]], ZD);
    kit.cornice(B, brick, ring, ZD - 0.6, { height: 0.6, projection: 0.2 });
    const long = edgesOf(ring).filter((e) => e.len > 20);
    for (const e of long) {
      const n = Math.max(2, Math.round(e.len / 6.0));
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        ebox(brick, e, s - 0.55, s + 0.55, 0, 0.35, 0, ZD - 0.6);
      }
      kit.windowRow(B, e.a, e.b, 0.0, {
        width: 3.6,
        height: 3.4,
        count: n,
        margin: 0,
        glass,
        frame: brick,
        sill: brick,
        head: 'arch',
        bars: 1,
        depth: 0.3,
      });
    }
    // booking-hall frontage on the short street end: cream faience-style frame, canopy, roundel
    const ends = edgesOf(ring).filter((e) => e.len > 4 && e.len < 10);
    const fe = ends[0];
    if (fe) {
      ebox(cream, fe, -0.2, fe.len + 0.2, 0, 0.3, 0, ZD - 0.6);
      ebox(glass, fe, 0.8, fe.len - 0.8, 0.3, 0.34, 0.3, 3.6);
      ebox(green, fe, 0.4, fe.len - 0.4, 0.3, 1.8, 3.7, 4.0);
      ebox(
        signMat(
          'rvp:sign',
          'RAVENSCOURT PARK STATION',
          '#0019a8',
          '#ffffff',
          'bold 32px sans-serif',
        ),
        fe,
        0.4,
        fe.len - 0.4,
        0.31,
        0.35,
        4.3,
        5.2,
      );
      const c = at(fe, fe.len / 2, 1.95);
      const rg = new THREE.TorusGeometry(0.7, 0.18, 6, 20).rotateX(Math.PI / 2);
      B.addGeometry(
        luRed,
        rg,
        new THREE.Matrix4().makeRotationZ(fe.ang).setPosition(c[0], c[1], 3.1),
      );
      rg.dispose();
      kit.box(B, luBlue, c[0], c[1], 2.95, 1.9, 0.1, 0.32, fe.ang);
    }
    // platforms and canopies on the deck
    for (const v of [-1, 1]) {
      const vv = (v * f.width) / 4;
      const a = frameAt(f, -f.length / 2 + 2, vv),
        b = frameAt(f, f.length / 2 - 2, vv);
      const e = edgesOf([a, b])[0];
      ebox(stone, e, 0, e.len, -1.2, 1.2, ZD, ZD + 0.9);
      ebox(canopy, e, 3, e.len - 3, -1.9, 1.9, ZD + 4.0, ZD + 4.15);
      ebox(green, e, 3, e.len - 3, 1.85, 1.95, ZD + 3.6, ZD + 4.15); // valance
      ebox(green, e, 3, e.len - 3, -1.95, -1.85, ZD + 3.6, ZD + 4.15);
      for (let s = 4; s < e.len - 3; s += 5)
        ebox(green, e, s - 0.1, s + 0.1, -0.1, 0.1, ZD + 0.9, ZD + 4.0);
      ebox(kit.mat('#e8c547'), e, 0, e.len, -1.22, -1.1, ZD + 0.9, ZD + 0.92);
    }
    g.add(B.toGroup('ravenscourt_park_station'));
    return g;
  },
};
