// Hammersmith Apollo (Eventim Apollo), Queen Caroline Street - the former Gaumont
// Palace cinema of 1932 by Robert Cromie, Grade II*. Brick-clad steel frame with an
// artificial-stone curved centrepiece: a two-storey centre of fifteen giant engaged
// columns flanked by slightly projecting pavilions, a rendered ground floor forming a
// plinth, nine pairs of doors under a canopy, and the brick auditorium and stage
// house behind, beside the Hammersmith Flyover.
export default {
  id: 'hammersmith_apollo',
  name: 'Hammersmith Apollo (Eventim Apollo)',
  claims: ['a910f569-b25a-44d9-be36-9041d6fdb727'],
  references: [
    {
      title: 'Former Odeon Cinema - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101252993-former-odeon-cinema-hammersmith-broadway-ward',
      used_for:
        'brick cladding, artificial stone curved centrepiece with 15 giant engaged columns, projecting pavilions, rendered plinth, nine pairs of doors under canopy',
    },
    {
      title: 'Hammersmith Apollo - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_Apollo',
      used_for:
        '1932 Robert Cromie Gaumont Palace, Art Deco, Queen Caroline Street site by the flyover',
    },
    {
      title: 'Hammersmith Odeon - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/hammersmith-odeon.html',
      used_for: 'Cromie Art Deco treatment and context',
    },
    {
      title: 'Hammersmith Apollo - Theatres Trust database',
      url: 'https://database.theatrestrust.org.uk/resources/theatres/show/2575',
      used_for: 'cinema-theatre with full stage (stage house behind auditorium)',
    },
  ],
  notes:
    'Heights estimated (front 15 m, auditorium 19 m, stage house 24 m) - Overture gives 11.8 m. The curved front is ' +
    'taken as the north-west outline edge facing Queen Caroline Street; column count from the listing, window and ' +
    'signage details approximate (no photos available).',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = b.polys[0][0];
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    const brickCol = '#8c5a43';
    const brickWall = kit.paintedMaterial('hammersmith_apollo:brick', 256, 256, (c, w, h) => {
      c.fillStyle = brickCol;
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4) {
        c.fillStyle = 'rgba(40,20,10,0.25)';
        c.fillRect(0, y, w, 1);
        for (let x = ((y / 4) % 2) * 8; x < w; x += 16) c.fillRect(x, y, 1, 4);
      }
      // stepped Art Deco brick pier bands and a cornice
      c.fillStyle = '#d8ceb6';
      c.fillRect(0, 0, w, 10);
      c.fillStyle = 'rgba(30,15,8,0.3)';
      for (let x = 0; x < w; x += 64) c.fillRect(x + 28, 14, 8, h - 40);
      c.fillStyle = '#e6e0d2';
      c.fillRect(0, h - 26, w, 26); // rendered plinth
    });
    const stone = kit.mat('#ddd3bd', { roughness: 0.75 });
    const render = kit.mat('white_render');
    const dark = kit.mat('dark_glass');
    const roof = kit.mat('#6b6e70', { roughness: 0.9 });

    const cx = b.c[0],
      cy = b.c[1];
    const H = 19;
    kit.walls(batch, brickWall, b.polys, 0, H, { bay: 16, storey: H / 2 });
    kit.cap(batch, roof, b.polys, H);
    // parapet coping
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 0.5) continue;
      addGeo(
        stone,
        new THREE.BoxGeometry(len + 0.3, 0.7, 0.6),
        new THREE.Matrix4()
          .makeRotationZ(Math.atan2(q[1] - p[1], q[0] - p[0]))
          .setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, H + 0.3),
      );
    }

    // Curved front: the run of outline vertices facing north-west (Queen Caroline St).
    let front = ring.slice(2, 8);
    if (Math.hypot(front[0][0] + 1645.4, front[0][1] + 1710.0) > 3) {
      // fall back: vertices most distant from the centroid along the north-west direction
      const d = [-0.6, 0.8];
      const s = ring.map((p) => (p[0] - cx) * d[0] + (p[1] - cy) * d[1]);
      const mx = Math.max(...s);
      front = ring.filter((_, k) => s[k] > mx - 14);
    }
    // Resample the front polyline into a smooth curve.
    const pts = [];
    for (let k = 0; k < front.length - 1; k++) {
      const [a, c2] = [front[k], front[k + 1]];
      for (let t = 0; t < 1; t += 0.25)
        pts.push([a[0] + (c2[0] - a[0]) * t, a[1] + (c2[1] - a[1]) * t]);
    }
    pts.push(front[front.length - 1]);
    const cum = [0];
    for (let k = 1; k < pts.length; k++)
      cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
    const total = cum[cum.length - 1];
    const at = (s) => {
      let k = 1;
      while (k < pts.length - 1 && cum[k] < s) k++;
      const t = (s - cum[k - 1]) / (cum[k] - cum[k - 1] || 1);
      const p = pts[k - 1],
        q = pts[k];
      const dx = q[0] - p[0],
        dy = q[1] - p[1],
        l = Math.hypot(dx, dy) || 1;
      // outward normal for CCW ring: (dy, -dx)
      return {
        x: p[0] + dx * t,
        y: p[1] + dy * t,
        nx: dy / l,
        ny: -dx / l,
        rot: Math.atan2(dy, dx),
      };
    };
    const pav = 8; // pavilion width at each end
    const s0 = pav,
      s1 = total - pav;
    const frontH = 15;
    // Stone centrepiece face (curved band) with tall windows between columns.
    const centreFace = kit.paintedMaterial('hammersmith_apollo:centre', 512, 256, (c, w, h) => {
      c.fillStyle = '#e2d9c4';
      c.fillRect(0, 0, w, h);
      // 4 bays per tile: tall recessed windows with Deco spandrels
      for (let i = 0; i < 4; i++) {
        const x = i * (w / 4);
        c.fillStyle = '#c9bea6';
        c.fillRect(x + 22, 18, w / 4 - 44, h - 50);
        c.fillStyle = '#34404a';
        c.fillRect(x + 32, 30, w / 4 - 64, 120);
        c.fillStyle = '#b9ad94';
        for (let k = 0; k < 4; k++) c.fillRect(x + 32, 160 + k * 14, w / 4 - 64, 6);
        c.fillStyle = '#e2d9c4';
        c.fillRect(x + 32 + (w / 4 - 64) / 2 - 2, 30, 4, 120);
      }
    });
    const N = 30;
    for (let k = 0; k < N; k++) {
      const a = at(s0 + ((s1 - s0) * k) / N),
        c2 = at(s0 + ((s1 - s0) * (k + 1)) / N);
      const o = 0.8;
      const A0 = [a.x + a.nx * o, a.y + a.ny * o],
        B0 = [c2.x + c2.nx * o, c2.y + c2.ny * o];
      const u0 = (k / N) * 3.75,
        u1 = ((k + 1) / N) * 3.75;
      batch.quad(
        centreFace,
        [A0[0], A0[1], 4.2],
        [B0[0], B0[1], 4.2],
        [B0[0], B0[1], frontH],
        [A0[0], A0[1], frontH],
        [u0, 0],
        [u1, 0],
        [u1, 1],
        [u0, 1],
      );
      // rendered plinth
      batch.quad(
        render,
        [A0[0], A0[1], 0],
        [B0[0], B0[1], 0],
        [B0[0], B0[1], 4.2],
        [A0[0], A0[1], 4.2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // entablature / attic band
      const o2 = 1.6;
      const A2 = [a.x + a.nx * o2, a.y + a.ny * o2],
        B2 = [c2.x + c2.nx * o2, c2.y + c2.ny * o2];
      batch.quad(
        stone,
        [A2[0], A2[1], frontH],
        [B2[0], B2[1], frontH],
        [B2[0], B2[1], frontH + 2.6],
        [A2[0], A2[1], frontH + 2.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        stone,
        [A2[0], A2[1], frontH + 2.6],
        [B2[0], B2[1], frontH + 2.6],
        [B0[0], B0[1], frontH + 2.6],
        [A0[0], A0[1], frontH + 2.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        stone,
        [A0[0], A0[1], frontH],
        [B0[0], B0[1], frontH],
        [B2[0], B2[1], frontH],
        [A2[0], A2[1], frontH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // attic infill between front and the auditorium wall above
      batch.quad(
        stone,
        [A0[0], A0[1], frontH + 2.6],
        [B0[0], B0[1], frontH + 2.6],
        [B0[0], B0[1], H + 1.5],
        [A0[0], A0[1], H + 1.5],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // Fifteen giant engaged columns.
    for (let i = 0; i < 15; i++) {
      const p = at(s0 + ((s1 - s0) * (i + 0.5)) / 15);
      const col = new THREE.CylinderGeometry(0.62, 0.7, frontH - 4.2, 12).rotateX(Math.PI / 2);
      addGeo(
        stone,
        col,
        new THREE.Matrix4().setPosition(
          p.x + p.nx * 1.3,
          p.y + p.ny * 1.3,
          4.2 + (frontH - 4.2) / 2,
        ),
      );
      addGeo(
        stone,
        new THREE.BoxGeometry(1.6, 1.6, 0.6),
        new THREE.Matrix4()
          .makeRotationZ(p.rot)
          .setPosition(p.x + p.nx * 1.3, p.y + p.ny * 1.3, frontH - 0.3),
      );
    }
    // Canopy over the nine pairs of doors, with the illuminated name fascia.
    const sign = kit.paintedMaterial(
      'hammersmith_apollo:sign',
      1024,
      64,
      (c, w, h) => {
        c.fillStyle = '#16181c';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#ffffff';
        c.font = 'bold 40px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('eventim  APOLLO', w / 2, h / 2 + 2);
        c.fillStyle = '#e03a3e';
        c.fillRect(0, h - 6, w, 6);
      },
      { emissive: new THREE.Color('#222222') },
    );
    const doorMat = kit.paintedMaterial('hammersmith_apollo:doors', 512, 64, (c, w, h) => {
      c.fillStyle = '#efe9dc';
      c.fillRect(0, 0, w, h);
      for (let i = 0; i < 9; i++) {
        const x = (i + 0.5) * (w / 9);
        c.fillStyle = '#2a2622';
        c.fillRect(x - 20, 14, 40, h - 14);
        c.fillStyle = '#b08d4a';
        c.fillRect(x - 1, 14, 2, h - 14);
      }
    });
    for (let k = 0; k < N; k++) {
      const a = at(s0 + ((s1 - s0) * k) / N),
        c2 = at(s0 + ((s1 - s0) * (k + 1)) / N);
      const P = (p, o, z) => [p.x + p.nx * o, p.y + p.ny * o, z];
      const u0 = k / N,
        u1 = (k + 1) / N;
      batch.quad(
        doorMat,
        P(a, 0.9, 0),
        P(c2, 0.9, 0),
        P(c2, 0.9, 3.6),
        P(a, 0.9, 3.6),
        [u0, 0],
        [u1, 0],
        [u1, 1],
        [u0, 1],
      );
      // canopy slab (top, bottom) and sign fascia
      batch.quad(
        render,
        P(a, 4.6, 4.4),
        P(c2, 4.6, 4.4),
        P(c2, 0.8, 4.4),
        P(a, 0.8, 4.4),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        render,
        P(a, 0.8, 3.9),
        P(c2, 0.8, 3.9),
        P(c2, 4.6, 3.9),
        P(a, 4.6, 3.9),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        sign,
        P(a, 4.6, 3.9),
        P(c2, 4.6, 3.9),
        P(c2, 4.6, 6.2),
        P(a, 4.6, 6.2),
        [u0, 0],
        [u1, 0],
        [u1, 1],
        [u0, 1],
      );
      batch.quad(
        sign,
        P(c2, 4.4, 6.2),
        P(a, 4.4, 6.2),
        P(a, 4.4, 3.9),
        P(c2, 4.4, 3.9),
        [0, 0],
        [0, 0],
        [0, 0],
        [0, 0],
      );
      batch.quad(
        render,
        P(a, 4.6, 6.2),
        P(c2, 4.6, 6.2),
        P(c2, 4.4, 6.2),
        P(a, 4.4, 6.2),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // Projecting end pavilions: brick with stone dressings and vertical Deco fins.
    for (const s of [pav / 2, total - pav / 2]) {
      const p = at(s);
      const m = (dz, o = 1.6) =>
        new THREE.Matrix4().makeRotationZ(p.rot).setPosition(p.x + p.nx * o, p.y + p.ny * o, dz);
      addGeo(kit.mat(brickCol), new THREE.BoxGeometry(pav, 3.2, frontH + 4), m((frontH + 4) / 2));
      addGeo(stone, new THREE.BoxGeometry(pav + 0.6, 3.6, 1.2), m(frontH + 4.4));
      addGeo(render, new THREE.BoxGeometry(pav + 0.2, 3.4, 4.2), m(2.1));
      for (const off of [-1.6, 0, 1.6]) {
        const fin = new THREE.BoxGeometry(0.5, 0.6, frontH - 2);
        const mm = new THREE.Matrix4()
          .makeRotationZ(p.rot)
          .setPosition(
            p.x + p.nx * 3.4 + Math.cos(p.rot) * off,
            p.y + p.ny * 3.4 + Math.sin(p.rot) * off,
            4.2 + (frontH - 2) / 2,
          );
        addGeo(stone, fin, mm);
      }
      addGeo(
        dark,
        new THREE.BoxGeometry(2.4, 0.2, frontH - 7),
        new THREE.Matrix4()
          .makeRotationZ(p.rot)
          .setPosition(p.x + p.nx * 3.25, p.y + p.ny * 3.25, 4.2 + (frontH - 7) / 2 + 1.5),
      );
    }

    // Stage house (fly tower) at the narrow south-east end.
    const d = [
      front.reduce((s, p) => s + p[0], 0) / front.length - cx,
      front.reduce((s, p) => s + p[1], 0) / front.length - cy,
    ];
    const dl = Math.hypot(...d);
    const ux = d[0] / dl,
      uy = d[1] / dl;
    const fx = cx - ux * 24,
      fy = cy - uy * 24;
    const rot = Math.atan2(uy, ux) + Math.PI / 2;
    addGeo(
      kit.mat(brickCol),
      new THREE.BoxGeometry(19, 12, 6),
      new THREE.Matrix4().makeRotationZ(rot).setPosition(fx, fy, H + 3),
    );
    addGeo(
      stone,
      new THREE.BoxGeometry(19.6, 12.6, 0.6),
      new THREE.Matrix4().makeRotationZ(rot).setPosition(fx, fy, H + 6.3),
    );
    // Shallow roof light / vents over the auditorium.
    addGeo(
      roof,
      new THREE.BoxGeometry(14, 22, 1.6),
      new THREE.Matrix4().makeRotationZ(rot).setPosition(cx + ux * 2, cy + uy * 2, H + 0.8),
    );

    g.add(batch.toGroup('hammersmith_apollo'));
    return g;
  },
};
