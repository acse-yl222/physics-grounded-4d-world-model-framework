// Hammersmith Apollo (Eventim Apollo), Queen Caroline Street - the former Gaumont
// Palace cinema of 1932 by Robert Cromie, Grade II*. Brick-clad steel frame with an
// artificial-stone curved centrepiece: a two-storey centre of fifteen giant engaged
// columns flanked by slightly projecting pavilions, a rendered ground floor forming a
// plinth, nine pairs of doors between piers under a canopy, set-back flanks with
// vertical bands of glazing, and the brick auditorium and stage house behind, beside
// the Hammersmith Flyover.
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
      title: 'Former Odeon Cinema - Historic England list entry 1252993',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1252993',
      used_for:
        'nine pairs of double doors separated by piers; set-back flanks with vertical bands of glazing',
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
    {
      title: 'Eventim Apollo Hammersmith - Cinema Treasures',
      url: 'https://cinematreasures.org/theaters/3774',
      used_for: 'history of the Gaumont Palace / Odeon / Apollo names',
    },
  ],
  notes:
    'Heights estimated (front 15 m, auditorium 19 m, stage house 25 m) - Overture gives 11.8 m. The curved front is ' +
    'taken as the north outline run facing the flyover / Queen Caroline Street junction. Column count, door pairs ' +
    'and glazed flank bands follow the listing; window sizes between the columns, the Deco capitals, the canopy ' +
    'depth and the present eventim signage are approximations (no photographs available). Rear elevations are ' +
    'plain brick with pilaster strips; roof plant is generic.',
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
    const brickWall = kit.paintedMaterial('hammersmith_apollo:brick2', 256, 256, (c, w, h) => {
      c.fillStyle = brickCol;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(7);
      for (let y = 0; y < h; y += 4)
        for (let x = ((y / 4) % 2) * 8; x < w; x += 16) {
          const t = r();
          c.fillStyle = `rgba(${110 + t * 40},${60 + t * 25},${40 + t * 15},0.55)`;
          c.fillRect(x, y, 15, 3);
        }
      c.fillStyle = 'rgba(40,20,10,0.25)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y + 3, w, 1);
    });
    const brick = kit.mat(brickCol, { roughness: 0.9 });
    const brickDark = kit.mat('#7a4a36', { roughness: 0.9 });
    const stone = kit.mat('#ddd3bd', { roughness: 0.75 });
    const stoneShade = kit.mat('#c9bfa8', { roughness: 0.8 });
    const render = kit.mat('#ebe6da', { roughness: 0.7 });
    const glass = kit.mat('dark_glass');
    const bronze = kit.mat('#4a3a2a', { roughness: 0.5, metalness: 0.5 });
    const frameMat = kit.mat('#2f3134', { roughness: 0.5, metalness: 0.4 });
    const roofMat = kit.mat('#6b6e70', { roughness: 0.9 });
    const plant = kit.mat('#a7abad', { roughness: 0.6, metalness: 0.3 });
    const lightMat = kit.mat('#fff4d6', { emissive: new THREE.Color('#ffe9b0'), roughness: 0.4 });

    const cx = b.c[0],
      cy = b.c[1];
    const H = 19;
    kit.walls(batch, brickWall, b.polys, 0, H, { bay: 4, storey: 4 });
    kit.cap(batch, roofMat, b.polys, H);
    // Rendered plinth band and stone parapet coping around the whole block.
    kit.cornice(batch, render, ring, 0, { height: 1.1, projection: 0.18 });
    kit.cornice(batch, stone, ring, H - 0.6, { height: 0.6, projection: 0.12 });
    kit.cornice(batch, stone, ring, H, { height: 0.7, projection: 0.3, steps: 2 });

    // Curved front: the run of outline vertices facing north (flyover / Queen
    // Caroline Street junction).
    let front = ring.slice(2, 8);
    if (Math.hypot(front[0][0] + 1645.4, front[0][1] + 1710.0) > 3) {
      const d = [-0.6, 0.8];
      const s = ring.map((p) => (p[0] - cx) * d[0] + (p[1] - cy) * d[1]);
      const mx = Math.max(...s);
      front = ring.filter((_, k) => s[k] > mx - 14);
    }
    // Smooth the front polyline (Chaikin) so the centrepiece reads as a curve.
    let pts = front.map((p) => p.slice());
    for (let it = 0; it < 3; it++) {
      const n = [pts[0]];
      for (let k = 0; k < pts.length - 1; k++) {
        const a = pts[k],
          q = pts[k + 1];
        n.push([0.75 * a[0] + 0.25 * q[0], 0.75 * a[1] + 0.25 * q[1]]);
        n.push([0.25 * a[0] + 0.75 * q[0], 0.25 * a[1] + 0.75 * q[1]]);
      }
      n.push(pts[pts.length - 1]);
      pts = n;
    }
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
      return {
        x: p[0] + dx * t,
        y: p[1] + dy * t,
        nx: dy / l,
        ny: -dx / l,
        tx: dx / l,
        ty: dy / l,
        rot: Math.atan2(dy, dx),
      };
    };
    // Box on the front at arc length s, outward offset o, lateral offset l.
    const fbox = (m, s, o, z0, w, d, h, l = 0) => {
      const p = at(s);
      addGeo(
        m,
        new THREE.BoxGeometry(w, d, h),
        new THREE.Matrix4()
          .makeRotationZ(p.rot)
          .setPosition(p.x + p.nx * o + p.tx * l, p.y + p.ny * o + p.ty * l, z0 + h / 2),
      );
    };
    // Curved band between arc lengths s0..s1: outer face at offset o, z0..z1, with
    // top / bottom caps back to offset oi.
    const band = (m, s0, s1, oi, o, z0, z1, n = 24) => {
      for (let k = 0; k < n; k++) {
        const a = at(s0 + ((s1 - s0) * k) / n),
          c2 = at(s0 + ((s1 - s0) * (k + 1)) / n);
        const P = (p, off, z) => [p.x + p.nx * off, p.y + p.ny * off, z];
        const uv = [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ];
        batch.quad(m, P(a, o, z0), P(c2, o, z0), P(c2, o, z1), P(a, o, z1), ...uv);
        batch.quad(m, P(a, oi, z1), P(a, o, z1), P(c2, o, z1), P(c2, oi, z1), ...uv);
        batch.quad(m, P(a, oi, z0), P(c2, oi, z0), P(c2, o, z0), P(a, o, z0), ...uv);
      }
    };

    const pav = 8; // pavilion width at each end
    const s0 = pav,
      s1 = total - pav;
    const plinthH = 4.4;
    const frontH = 15;
    // Centre wall (artificial stone), rendered plinth, entablature, stepped cornice
    // and attic up to the auditorium parapet.
    band(stone, s0, s1, 0, 0.8, plinthH, frontH);
    band(render, s0, s1, 0, 0.85, 0, plinthH);
    band(stoneShade, s0, s1, 0.8, 1.45, frontH, frontH + 0.5); // architrave
    band(stone, s0, s1, 0.8, 1.55, frontH + 0.5, frontH + 1.9); // frieze
    band(stone, s0, s1, 0.8, 1.9, frontH + 1.9, frontH + 2.3); // cornice steps
    band(stone, s0, s1, 0.8, 2.15, frontH + 2.3, frontH + 2.6);
    band(stone, s0, s1, 0, 1.0, frontH + 2.6, H + 1.4); // attic
    band(stoneShade, s0, s1, 0, 1.2, H + 1.4, H + 1.8);
    // Frieze: Deco reeded panels.
    for (let k = 0; k < 15; k++) {
      const s = s0 + ((s1 - s0) * (k + 0.5)) / 15;
      for (const l of [-0.45, -0.15, 0.15, 0.45])
        fbox(stoneShade, s, 1.6, frontH + 0.7, 0.12, 0.12, 1.0, l);
    }

    // Fifteen giant engaged columns with bases and stepped Deco capitals; tall
    // windows on two storeys between them.
    const colPitch = (s1 - s0) / 15;
    const shaft = new THREE.CylinderGeometry(0.6, 0.66, frontH - plinthH - 1.4, 16).rotateX(
      Math.PI / 2,
    );
    for (let i = 0; i < 15; i++) {
      const s = s0 + colPitch * (i + 0.5);
      const p = at(s);
      const ox = p.x + p.nx * 1.35,
        oy = p.y + p.ny * 1.35;
      batch.addGeometry(
        stone,
        shaft,
        new THREE.Matrix4().makeTranslation(ox, oy, plinthH + 0.6 + (frontH - plinthH - 1.4) / 2),
      );
      fbox(stoneShade, s, 1.35, plinthH, 1.6, 1.6, 0.35);
      fbox(stone, s, 1.35, plinthH + 0.35, 1.45, 1.45, 0.25);
      fbox(stone, s, 1.35, frontH - 0.8, 1.45, 1.45, 0.3);
      fbox(stoneShade, s, 1.4, frontH - 0.5, 1.7, 1.7, 0.5);
      // flutes (three proud reeds on the face of each shaft)
      for (const l of [-0.28, 0, 0.28])
        fbox(stoneShade, s, 1.35 + 0.6, plinthH + 1.2, 0.1, 0.08, frontH - plinthH - 2.6, l);
    }
    shaft.dispose();
    for (let i = 0; i < 14; i++) {
      const s = s0 + colPitch * (i + 1);
      const ww = colPitch - 1.5;
      // reveal (dark recess), glass, steel frame with bars, stone sill / spandrel
      for (const [z0, hh] of [
        [plinthH + 1.1, 3.6],
        [plinthH + 5.6, 3.9],
      ]) {
        fbox(glass, s, 0.83, z0, ww, 0.05, hh);
        fbox(frameMat, s, 0.87, z0, ww, 0.06, 0.08);
        fbox(frameMat, s, 0.87, z0 + hh - 0.08, ww, 0.06, 0.08);
        for (const l of [-ww / 2, 0, ww / 2]) fbox(frameMat, s, 0.87, z0, 0.07, 0.06, hh, l);
        for (let k = 1; k < 4; k++) fbox(frameMat, s, 0.87, z0 + (hh * k) / 4, ww, 0.05, 0.05);
        fbox(stoneShade, s, 0.95, z0 - 0.15, ww + 0.2, 0.35, 0.15);
      }
      // spandrel panel between the storeys with three Deco ribs
      for (const l of [-ww / 3, 0, ww / 3])
        fbox(stoneShade, s, 0.9, plinthH + 4.9, 0.14, 0.15, 0.55, l);
    }

    // Nine pairs of double doors between piers on the rendered plinth.
    const ds = (s1 - s0) / 9;
    for (let i = 0; i <= 9; i++) fbox(render, s0 + ds * i, 1.05, 0, 1.0, 0.5, plinthH - 0.4);
    for (let i = 0; i < 9; i++) {
      const s = s0 + ds * (i + 0.5);
      const dw = ds - 1.1;
      fbox(bronze, s, 0.88, 0, dw, 0.06, 2.7);
      for (const l of [-dw / 4, dw / 4]) fbox(glass, s, 0.92, 0.9, dw / 2 - 0.35, 0.04, 1.6, l);
      fbox(frameMat, s, 0.93, 0, 0.06, 0.06, 2.7); // meeting stiles
      for (const l of [-dw / 4, dw / 4])
        fbox(kit.mat('gold'), s, 0.97, 1.0, 0.04, 0.06, 0.9, l + (l < 0 ? 0.3 : -0.3));
      fbox(glass, s, 0.88, 2.85, dw, 0.05, 0.95); // transom light
      fbox(frameMat, s, 0.9, 2.7, dw, 0.08, 0.15);
      for (const l of [-dw / 3, 0, dw / 3]) fbox(frameMat, s, 0.9, 2.85, 0.05, 0.06, 0.95, l);
    }
    // Canopy over the doors with the illuminated name fascia and soffit lights.
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
    const N = 30;
    for (let k = 0; k < N; k++) {
      const a = at(s0 - 1 + ((s1 - s0 + 2) * k) / N),
        c2 = at(s0 - 1 + ((s1 - s0 + 2) * (k + 1)) / N);
      const P = (p, o, z) => [p.x + p.nx * o, p.y + p.ny * o, z];
      const u0 = k / N,
        u1 = (k + 1) / N;
      const uv = [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ];
      batch.quad(render, P(a, 5, 4.6), P(c2, 5, 4.6), P(c2, 1.3, 4.6), P(a, 1.3, 4.6), ...uv);
      batch.quad(render, P(a, 1.3, 4.1), P(c2, 1.3, 4.1), P(c2, 5, 4.1), P(a, 5, 4.1), ...uv);
      batch.quad(
        sign,
        P(a, 5, 4.0),
        P(c2, 5, 4.0),
        P(c2, 5, 6.1),
        P(a, 5, 6.1),
        [u0, 0],
        [u1, 0],
        [u1, 1],
        [u0, 1],
      );
      batch.quad(
        sign,
        P(c2, 4.8, 6.1),
        P(a, 4.8, 6.1),
        P(a, 4.8, 4.0),
        P(c2, 4.8, 4.0),
        [0, 0],
        [0, 0],
        [0, 0],
        [0, 0],
      );
      batch.quad(render, P(a, 5, 6.1), P(c2, 5, 6.1), P(c2, 4.8, 6.1), P(a, 4.8, 6.1), ...uv);
      batch.quad(render, P(a, 4.8, 4.0), P(c2, 4.8, 4.0), P(c2, 5, 4.0), P(a, 5, 4.0), ...uv);
    }
    for (let i = 0; i < 18; i++)
      fbox(lightMat, s0 + ((s1 - s0) * (i + 0.5)) / 18, 3.1, 4.02, 0.6, 0.6, 0.08);
    // tie rods from the canopy to the facade
    for (let i = 0; i <= 6; i++) {
      const s = s0 + ((s1 - s0) * i) / 6;
      const p = at(s);
      const len = Math.hypot(4.2, 2.6);
      const geo = new THREE.CylinderGeometry(0.05, 0.05, len, 5);
      const m = new THREE.Matrix4()
        .makeRotationZ(p.rot)
        .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(2.6, 4.2)))
        .setPosition(p.x + p.nx * 2.9, p.y + p.ny * 2.9, 6.1 + 1.3);
      addGeo(frameMat, geo, m);
    }

    // Projecting end pavilions: brick with stone dressings, vertical Deco fins and a
    // tall glazed slot, a stepped stone crown and a side entrance under the canopy.
    for (const [s, sgn] of [
      [pav / 2, 1],
      [total - pav / 2, -1],
    ]) {
      fbox(brick, s, 1.6, 0, pav, 3.2, frontH + 4);
      fbox(stone, s, 1.6, frontH + 4, pav + 0.6, 3.6, 0.5);
      fbox(stone, s, 1.6, frontH + 4.5, pav - 1.2, 3.0, 0.6);
      fbox(stone, s, 1.6, frontH + 5.1, pav - 3.2, 2.6, 0.6);
      fbox(render, s, 1.6, 0, pav + 0.2, 3.4, plinthH);
      fbox(stone, s, 1.6, plinthH, pav + 0.4, 3.5, 0.35);
      // stone quoin strips at the pavilion edges
      for (const l of [-pav / 2 + 0.3, pav / 2 - 0.3])
        fbox(stone, s, 1.65, plinthH, 0.6, 3.35, frontH - plinthH + 4, l);
      // glazed slot with fins
      fbox(glass, s, 3.22, plinthH + 1, 2.6, 0.06, frontH - 4.5);
      for (let k = 1; k < 10; k++)
        fbox(frameMat, s, 3.26, plinthH + 1 + ((frontH - 4.5) * k) / 10, 2.6, 0.05, 0.06);
      for (const off of [-1.75, -0.55, 0.55, 1.75])
        fbox(stone, s, 3.35, plinthH + 0.6, 0.35, 0.5, frontH - 3.2, off);
      // side entrance door in the plinth
      fbox(bronze, s, 3.32, 0, 2.4, 0.06, 2.6, sgn * 0.6);
      fbox(glass, s, 3.36, 0.9, 1.8, 0.04, 1.4, sgn * 0.6);
    }

    // Set-back flanks either side of the front: vertical glazing bands with stone
    // mullions in the brick (listing).
    for (const k of [0, 1, 7, 8]) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 4) continue;
      const nb = Math.max(1, Math.floor(len / 4));
      kit.windowRow(batch, p, q, 5.2, {
        count: nb,
        width: 1.3,
        height: 9.5,
        margin: 1,
        bars: 0,
        glass,
        frame: frameMat,
        sill: stone,
        head: 'lintel',
      });
      const ux = (q[0] - p[0]) / len,
        uy = (q[1] - p[1]) / len;
      // horizontal transoms in each band
      for (let i = 0; i < nb; i++) {
        const t = 1 + ((len - 2) * (i + 0.5)) / nb;
        for (let j = 1; j < 8; j++)
          addGeo(
            frameMat,
            new THREE.BoxGeometry(1.3, 0.14, 0.06),
            new THREE.Matrix4()
              .makeRotationZ(Math.atan2(uy, ux))
              .setPosition(
                p[0] + ux * t + uy * 0.08,
                p[1] + uy * t - ux * 0.08,
                5.2 + (9.5 * j) / 8,
              ),
          );
      }
    }

    // Brick pilaster strips on the plain auditorium walls (skip the front run).
    for (let k = 9; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 6) continue;
      const ux = (q[0] - p[0]) / len,
        uy = (q[1] - p[1]) / len;
      const n = Math.floor(len / 6);
      for (let i = 0; i <= n; i++) {
        const t = 1 + ((len - 2) * i) / n;
        addGeo(
          brickDark,
          new THREE.BoxGeometry(1.2, 0.5, H - 1.1),
          new THREE.Matrix4()
            .makeRotationZ(Math.atan2(uy, ux))
            .setPosition(p[0] + ux * t + uy * 0.2, p[1] + uy * t - ux * 0.2, 1.1 + (H - 1.1) / 2),
        );
      }
      // fire-exit doors
      if (len > 12)
        addGeo(
          kit.mat('#3b4a57', { roughness: 0.6 }),
          new THREE.BoxGeometry(2.0, 0.2, 2.4),
          new THREE.Matrix4()
            .makeRotationZ(Math.atan2(uy, ux))
            .setPosition(p[0] + ux * len * 0.5 + uy * 0.05, p[1] + uy * len * 0.5 - ux * 0.05, 1.2),
        );
    }

    // Stage house (fly tower) at the narrow south end, with pilasters and coping.
    const d = [
      front.reduce((s, p) => s + p[0], 0) / front.length - cx,
      front.reduce((s, p) => s + p[1], 0) / front.length - cy,
    ];
    const dl = Math.hypot(...d);
    const ux = d[0] / dl,
      uy = d[1] / dl;
    const rot = Math.atan2(uy, ux) + Math.PI / 2;
    const R = (lx, ly, z) =>
      new THREE.Matrix4()
        .makeRotationZ(rot)
        .setPosition(
          cx - ux * 24 + Math.cos(rot) * lx - Math.sin(rot) * ly,
          cy - uy * 24 + Math.sin(rot) * lx + Math.cos(rot) * ly,
          z,
        );
    addGeo(brick, new THREE.BoxGeometry(19, 12, 6.4), R(0, 0, H + 3.2));
    addGeo(stone, new THREE.BoxGeometry(19.6, 12.6, 0.6), R(0, 0, H + 6.7));
    for (const lx of [-9.6, -4.8, 0, 4.8, 9.6])
      for (const ly of [-6.15, 6.15])
        addGeo(brickDark, new THREE.BoxGeometry(1.0, 0.4, 6.4), R(lx, ly, H + 3.2));
    addGeo(roofMat, new THREE.BoxGeometry(18.6, 11.6, 0.2), R(0, 0, H + 7.05));
    // smoke vents on the fly tower roof
    for (const lx of [-5, 5])
      addGeo(plant, new THREE.BoxGeometry(2.4, 2.4, 1.2), R(lx, 0, H + 7.6));

    // Auditorium roof: raised roof light, ventilators, air-handling plant, ladders.
    const A = (lx, ly, z) =>
      new THREE.Matrix4()
        .makeRotationZ(rot)
        .setPosition(
          cx + ux * 2 + Math.cos(rot) * lx - Math.sin(rot) * ly,
          cy + uy * 2 + Math.sin(rot) * lx + Math.cos(rot) * ly,
          z,
        );
    addGeo(roofMat, new THREE.BoxGeometry(14, 22, 1.2), A(0, 0, H + 0.6));
    addGeo(
      kit.mat('#8d9295', { roughness: 0.7 }),
      new THREE.BoxGeometry(14.4, 22.4, 0.25),
      A(0, 0, H + 1.3),
    );
    for (let k = -3; k <= 3; k++) {
      const vent = new THREE.CylinderGeometry(0.55, 0.7, 1.4, 10).rotateX(Math.PI / 2);
      addGeo(plant, vent, A(-10, k * 3.2, H + 0.7));
      addGeo(
        plant,
        new THREE.CylinderGeometry(0.8, 0.8, 0.2, 10).rotateX(Math.PI / 2),
        A(-10, k * 3.2, H + 1.5),
      );
    }
    for (const ly of [-6, 0, 6]) {
      addGeo(plant, new THREE.BoxGeometry(4, 2.4, 2.2), A(10.5, ly, H + 1.1));
      addGeo(
        kit.mat('#55595c'),
        new THREE.CylinderGeometry(0.7, 0.7, 0.3, 12).rotateX(Math.PI / 2),
        A(10.5, ly, H + 2.35),
      );
    }
    // ductwork run between plant and the auditorium vent
    addGeo(plant, new THREE.BoxGeometry(0.8, 14, 0.8), A(8, 0, H + 0.6));

    // Street furniture: bollards along the forecourt kerb, lamps either side.
    const bollards = [],
      lamps = [];
    for (let i = 0; i <= 12; i++) {
      const p = at(s0 + ((s1 - s0) * i) / 12);
      bollards.push([p.x + p.nx * 6.2, p.y + p.ny * 6.2, p.rot]);
    }
    for (const s of [pav / 2, total - pav / 2]) {
      const p = at(s);
      lamps.push([p.x + p.nx * 7, p.y + p.ny * 7, p.rot]);
    }
    g.add(ctx.placeAssets('bollard', bollards));
    g.add(ctx.placeAssets('street_lamp', lamps));

    g.add(batch.toGroup('hammersmith_apollo'));
    return g;
  },
};
