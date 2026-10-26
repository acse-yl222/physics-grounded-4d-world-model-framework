// Charing Cross Hospital, Fulham Palace Road (Ralph Tubbs, opened by the Queen in
// 1973). A cruciform ward tower - fifteen hospital floors plus two machine floors -
// whose four wings radiate from a central lift/stair core so every ward gets outside
// windows, standing on lower brick-faced treatment and teaching blocks.
export default {
  id: 'charing_cross_hospital',
  name: 'Charing Cross Hospital',
  claims: ['8f126f1f-67b4-4d8f-8426-a753559bb6f0'],
  references: [
    {
      title: 'Charing Cross Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Charing_Cross_Hospital',
      used_for:
        'Ralph Tubbs cross-shaped main block, 17 storeys including two machine floors, 1973 opening',
    },
    {
      title: '200 years of Charing Cross Hospital in ten pictures - Imperial College',
      url: 'https://www.imperial.ac.uk/news/188812/200-years-charing-cross-hospital-pictures/',
      used_for: '15-storey building in the shape of a cross',
    },
    {
      title: 'Charing Cross Hospital - Mainstream Modern',
      url: 'https://mainstreammodern.co.uk/CaseStudies.aspx/Detail/295/charing-cross-hospital',
      used_for:
        'cruciform plan with central core maximising ward windows; lower sections faced in brick',
    },
    {
      title: 'Ralph Tubbs - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Ralph_Tubbs',
      used_for: 'architect; hospital as his late major work',
    },
    {
      title: 'Inventory Site Record - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record/?ID=HAF009',
      used_for: '17 storeys, cruciform arrangement',
    },
  ],
  notes:
    'The Overture outline is a single 15 m podium without tower parts; the tower position (-1352, -2138) and ' +
    'orientation (site grid, 26 deg) were fitted to the widest cross that lies inside the outline, wing length ' +
    '36 m from the centre and width 19 m are estimates. Height 59 m to the ward roof plus a 9 m louvred plant/core top ' +
    '(~68 m) from the storey count. Tower: recessed glazing behind one projecting precast spandrel band per floor and ' +
    'mullions at 1.8 m (no published facade description found - approximate); wing ends solid with a painted window ' +
    'column. Podium: brick with real framed window bands on the outer elevations (painted in courtyards); the entrance ' +
    'canopy position on Fulham Palace Road, NHS sign and roof plant layout are approximate.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    // Podium: lower blocks, brown brick with window bands, at the Overture height.
    const podiumH = Math.max(12, b.h || 15);
    const podWall = kit.paintedMaterial('charing_cross_hospital:podium', 512, 256, (c, w, h) => {
      c.fillStyle = '#7d5643';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(30,15,8,0.25)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      for (const y0 of [24, 152]) {
        c.fillStyle = '#c9c4ba';
        c.fillRect(0, y0 - 8, w, 8);
        c.fillStyle = '#2d3a44';
        c.fillRect(0, y0, w, 64);
        c.fillStyle = '#b8b4ab';
        for (let x = 0; x < w; x += 32) c.fillRect(x, y0, 4, 64);
      }
    });
    // Outer elevations: plain brick with real framed window bands; courtyard
    // elevations keep the painted window bands.
    const podBrick = kit.paintedMaterial('charing_cross_hospital:podbrick', 256, 256, (c, w, h) => {
      c.fillStyle = '#7d5643';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(11);
      for (let y = 0; y < h; y += 4)
        for (let x = ((y / 4) % 2) * 8; x < w; x += 16) {
          const t = r();
          c.fillStyle = `rgba(${95 + t * 35},${62 + t * 20},${45 + t * 14},0.6)`;
          c.fillRect(x, y, 15, 3);
        }
    });
    const outerRing = b.polys[0][0];
    kit.walls(batch, podBrick, [[outerRing]], 0, podiumH, { bay: 4, storey: 4 });
    kit.walls(batch, podWall, [b.polys[0].slice(1)], 0, podiumH, { bay: 4, storey: podiumH / 4 });
    const winFrame = kit.mat('#3d4246', { roughness: 0.5, metalness: 0.4 });
    const cill = kit.mat('#c9c4ba', { roughness: 0.85 });
    const podStorey = podiumH / 4;
    for (let st = 0; st < 4; st++)
      for (let k = 0; k < outerRing.length; k++) {
        const p = outerRing[k],
          q = outerRing[(k + 1) % outerRing.length];
        if (Math.hypot(q[0] - p[0], q[1] - p[1]) < 5) continue;
        kit.windowRow(batch, p, q, st * podStorey + 1.1, {
          width: 2.6,
          height: 1.7,
          bay: 3.6,
          margin: 0.8,
          bars: 0,
          head: 'none',
          glass: kit.mat('dark_glass'),
          frame: winFrame,
          sill: cill,
        });
      }
    // concrete floor-edge bands on the outer elevations
    for (let st = 1; st < 4; st++)
      kit.cornice(batch, cill, outerRing, st * podStorey - 0.15, {
        height: 0.35,
        projection: 0.12,
      });
    kit.cornice(batch, cill, outerRing, 0, { height: 0.6, projection: 0.15 });
    // Main entrance from Fulham Palace Road: canopy, NHS sign, glazed doors, steps.
    {
      let best = null;
      for (let k = 0; k < outerRing.length; k++) {
        const p = outerRing[k],
          q = outerRing[(k + 1) % outerRing.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        const m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
        const dFPR = Math.hypot(m[0] + 1440, m[1] + 2112);
        if (len > 25 && (!best || dFPR < best.d)) best = { p, q, len, d: dFPR };
      }
      if (best) {
        const { p, q, len } = best;
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len;
        const nx = uy,
          ny = -ux,
          rot = Math.atan2(uy, ux);
        const E = (t, o, z, w, d, h, m) =>
          addGeo(
            m,
            new THREE.BoxGeometry(w, d, h),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(p[0] + ux * t + nx * o, p[1] + uy * t + ny * o, z + h / 2),
          );
        const t0 = len / 2;
        E(t0, 4, 4.2, 22, 8, 0.6, kit.mat('#e6e4df'));
        for (const dt of [-10, -3.5, 3.5, 10])
          E(
            t0 + dt,
            7.4,
            0,
            0.35,
            0.35,
            4.2,
            kit.mat('#9aa1a6', { metalness: 0.5, roughness: 0.4 }),
          );
        E(
          t0,
          7.9,
          4.0,
          14,
          0.12,
          0.9,
          kit.paintedMaterial(
            'charing_cross_hospital:sign',
            512,
            64,
            (c, w, h) => {
              c.fillStyle = '#005eb8';
              c.fillRect(0, 0, w, h);
              c.fillStyle = '#ffffff';
              c.font = 'bold 30px sans-serif';
              c.textAlign = 'center';
              c.textBaseline = 'middle';
              c.fillText('Charing Cross Hospital', w / 2 - 40, h / 2 + 2);
              c.fillStyle = '#ffffff';
              c.fillRect(w - 86, 12, 72, 40);
              c.fillStyle = '#005eb8';
              c.font = 'bold italic 30px sans-serif';
              c.fillText('NHS', w - 50, h / 2 + 2);
            },
            { emissive: new THREE.Color('#0a2a55') },
          ),
        );
        E(t0, 0.15, 0, 16, 0.3, 3.6, kit.mat('dark_glass'));
        for (let i = 0; i <= 8; i++) E(t0 - 8 + i * 2, 0.32, 0, 0.12, 0.12, 3.6, winFrame);
        E(t0, 0.3, 3.6, 16.4, 0.3, 0.25, winFrame);
        E(t0, 3, 0, 24, 6, 0.15, kit.mat('paving'));
        const bl = [];
        for (let i = 0; i <= 10; i++) {
          const t = t0 - 14 + i * 2.8;
          bl.push([p[0] + ux * t + nx * 10, p[1] + uy * t + ny * 10, rot]);
        }
        g.add(ctx.placeAssets('bollard', bl));
        g.add(
          ctx.placeAssets('bench', [
            [p[0] + ux * (t0 - 16) + nx * 4, p[1] + uy * (t0 - 16) + ny * 4, rot],
            [p[0] + ux * (t0 + 16) + nx * 4, p[1] + uy * (t0 + 16) + ny * 4, rot],
          ]),
        );
      }
    }
    kit.cap(batch, kit.mat('#8c8d8a', { roughness: 0.95 }), b.polys, podiumH);
    // parapet
    for (const ring of b.polys[0])
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 0.5) continue;
        addGeo(
          kit.mat('concrete'),
          new THREE.BoxGeometry(len + 0.2, 0.5, 0.9),
          new THREE.Matrix4()
            .makeRotationZ(Math.atan2(q[1] - p[1], q[0] - p[0]))
            .setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, podiumH + 0.45),
        );
      }

    // Cruciform ward tower.
    const C = [-1352, -2138],
      A = (26.3 * Math.PI) / 180;
    const ca = Math.cos(A),
      sa = Math.sin(A);
    const P = (u, v) => [C[0] + u * ca - v * sa, C[1] + u * sa + v * ca];
    const Lw = 36,
      Hw = 9.5;
    const cross = [
      [Lw, -Hw],
      [Lw, Hw],
      [Hw, Hw],
      [Hw, Lw],
      [-Hw, Lw],
      [-Hw, Hw],
      [-Lw, Hw],
      [-Lw, -Hw],
      [-Hw, -Hw],
      [-Hw, -Lw],
      [Hw, -Lw],
      [Hw, -Hw],
    ].map(([u, v]) => P(u, v));
    const storey = 3.9;
    const wardTop = 15 * storey; // 58.5 m
    const towerWall = kit.paintedMaterial('charing_cross_hospital:tower', 512, 256, (c, w, h) => {
      // 4 bays x 2 storeys: pale precast spandrel panels, continuous window bands.
      c.fillStyle = '#d9d6cf';
      c.fillRect(0, 0, w, h);
      for (const y0 of [18, 146]) {
        c.fillStyle = '#33414c';
        c.fillRect(0, y0, w, 62);
        c.fillStyle = '#5c6d78';
        c.fillRect(0, y0, w, 10);
        c.fillStyle = '#cfcbc3';
        for (let x = 0; x < w; x += 32) c.fillRect(x, y0, 5, 62);
        c.fillStyle = '#c3bfb6';
        c.fillRect(0, y0 + 62, w, 6);
      }
      c.fillStyle = 'rgba(120,115,105,0.25)';
      for (let x = 0; x < w; x += 128) c.fillRect(x, 0, 3, h); // panel joints
    });
    const endWall = kit.paintedMaterial('charing_cross_hospital:end', 256, 256, (c, w, h) => {
      // wing ends: mostly solid panels with a central column of windows
      c.fillStyle = '#d3d0c8';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(120,115,105,0.3)';
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 2, h);
      c.fillStyle = '#33414c';
      for (const y0 of [24, 152]) c.fillRect(w * 0.38, y0, w * 0.24, 56);
    });
    // Long elevations: recessed glazing behind precast spandrel bands and mullions;
    // wing ends: solid panels (painted) with a central window column.
    const tGlass = kit.mat('#3a4955', { roughness: 0.15, metalness: 0.3 });
    const panel = kit.mat('#dedbd3', { roughness: 0.8 });
    const fin = kit.mat('#cfcbc3', { roughness: 0.8 });
    for (let k = 0; k < cross.length; k++) {
      const p = cross[k],
        q = cross[(k + 1) % cross.length];
      const isEnd = k % 3 === 0;
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const z0 = podiumH - 1;
      if (isEnd) {
        const v1 = wardTop / (2 * storey);
        batch.quad(
          endWall,
          [p[0], p[1], z0],
          [q[0], q[1], z0],
          [q[0], q[1], wardTop],
          [p[0], p[1], wardTop],
          [0, z0 / (2 * storey)],
          [1, z0 / (2 * storey)],
          [1, v1],
          [0, v1],
        );
        continue;
      }
      batch.quad(
        tGlass,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], wardTop],
        [p[0], p[1], wardTop],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const ux = (q[0] - p[0]) / len,
        uy = (q[1] - p[1]) / len,
        rot = Math.atan2(uy, ux);
      const nm = Math.round(len / 1.8);
      for (let f = Math.ceil(podiumH / storey); f < 15; f++) {
        const zf = f * storey + 0.9;
        for (let i = 1; i < nm; i++) {
          const t = (len * i) / nm;
          addGeo(
            fin,
            new THREE.BoxGeometry(0.14, 0.3, storey - 1.2),
            new THREE.Matrix4()
              .makeRotationZ(rot)
              .setPosition(
                p[0] + ux * t + uy * 0.15,
                p[1] + uy * t - ux * 0.15,
                zf + (storey - 1.2) / 2,
              ),
          );
        }
        // transom (opening lights) line
        addGeo(
          fin,
          new THREE.BoxGeometry(len, 0.12, 0.1),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition((p[0] + q[0]) / 2 + uy * 0.08, (p[1] + q[1]) / 2 - ux * 0.08, zf + 2.0),
        );
      }
    }
    // precast spandrel bands, one per floor, wrapping the whole cross
    for (let f = Math.ceil(podiumH / storey); f <= 15; f++)
      kit.cornice(batch, panel, cross, f * storey - 0.3, { height: 1.2, projection: 0.35 });
    const crossPoly = [[cross]];
    kit.cap(batch, kit.mat('#9c9d99', { roughness: 0.95 }), crossPoly, wardTop);
    // roof edge fascia
    for (let k = 0; k < cross.length; k++) {
      const p = cross[k],
        q = cross[(k + 1) % cross.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      addGeo(
        kit.mat('#e3e0d8'),
        new THREE.BoxGeometry(len + 0.6, 0.6, 1.4),
        new THREE.Matrix4()
          .makeRotationZ(Math.atan2(q[1] - p[1], q[0] - p[0]))
          .setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, wardTop + 0.5),
      );
    }
    // Two machine floors: central core block and plant on the inner wing ends.
    const plant = kit.paintedMaterial('charing_cross_hospital:plant', 256, 128, (c, w, h) => {
      c.fillStyle = '#c9c6bf';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#6f777c';
      for (let x = 8; x < w; x += 16) c.fillRect(x, 20, 9, h - 40);
    });
    const core = [P(13, -13), P(13, 13), P(-13, 13), P(-13, -13)];
    {
      const z0 = wardTop,
        z1 = wardTop + 8.5;
      for (let k = 0; k < 4; k++) {
        const p = core[k],
          q = core[(k + 1) % 4];
        batch.quad(
          plant,
          [p[0], p[1], z0],
          [q[0], q[1], z0],
          [q[0], q[1], z1],
          [p[0], p[1], z1],
          [0, 0],
          [4, 0],
          [4, 1],
          [0, 1],
        );
      }
      kit.cap(batch, kit.mat('#8f908c'), [[core]], z1);
      // vertical louvre fins on the two machine floors and a coping band
      for (let k = 0; k < 4; k++) {
        const p = core[k],
          q = core[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len;
        for (let t = 0.4; t < len; t += 0.8)
          addGeo(
            kit.mat('#b4b2ab'),
            new THREE.BoxGeometry(0.1, 0.5, z1 - z0 - 1.2),
            new THREE.Matrix4()
              .makeRotationZ(Math.atan2(uy, ux))
              .setPosition(
                p[0] + ux * t + uy * 0.25,
                p[1] + uy * t - ux * 0.25,
                z0 + 0.6 + (z1 - z0 - 1.2) / 2,
              ),
          );
      }
      kit.cornice(batch, kit.mat('#e3e0d8'), core, z1 - 0.6, { height: 0.8, projection: 0.4 });
      kit.cornice(batch, kit.mat('#e3e0d8'), core, z0 + 4.1, { height: 0.4, projection: 0.3 });
      // window-cleaning cradle rail and gantry around the ward roof
      kit.cornice(
        batch,
        kit.mat('#8a8f93', { metalness: 0.5, roughness: 0.4 }),
        kit.offsetRing(cross, -1.2),
        wardTop + 1.1,
        { height: 0.12, projection: 0.08 },
      );
      // lift motor rooms and flues
      const mtx = (u, v, z) => new THREE.Matrix4().makeRotationZ(A).setPosition(...P(u, v), z);
      addGeo(kit.mat('#d5d2ca'), new THREE.BoxGeometry(12, 7, 3.5), mtx(0, 0, z1 + 1.75));
      for (const [u, v] of [
        [-8, -8],
        [8, 8],
      ])
        addGeo(
          kit.mat('#7c7f80'),
          new THREE.CylinderGeometry(0.9, 0.9, 5, 10).rotateX(Math.PI / 2),
          mtx(u, v, z1 + 2.5),
        );
    }
    // Rooftop plant boxes on the wings.
    for (let k = 0; k < 4; k++) {
      const a = A + (k * Math.PI) / 2;
      const u = 26,
        x = C[0] + Math.cos(a) * u,
        y = C[1] + Math.sin(a) * u;
      addGeo(
        kit.mat('#b9b7b0'),
        new THREE.BoxGeometry(8, 10, 2.6),
        new THREE.Matrix4().makeRotationZ(a).setPosition(x, y, wardTop + 1.3),
      );
    }
    // Podium roof plant rooms, AHUs and rooflights (positions random but seeded).
    {
      const inside = (x, y) => {
        let c = false;
        for (const r of b.polys[0])
          for (let i = 0, j = r.length - 1; i < r.length; j = i++)
            if (
              r[i][1] > y !== r[j][1] > y &&
              x < ((r[j][0] - r[i][0]) * (y - r[i][1])) / (r[j][1] - r[i][1]) + r[i][0]
            )
              c = !c;
        return c;
      };
      const rnd = kit.rng(1973);
      let placed = 0;
      for (let tries = 0; tries < 400 && placed < 22; tries++) {
        const x = -1450 + rnd() * 235,
          y = -2280 + rnd() * 265;
        if (Math.hypot(x - C[0], y - C[1]) < 42) continue;
        const w = 3 + rnd() * 5,
          d = 2.5 + rnd() * 4;
        const ok = [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ].every(([sx, sy]) => {
          const lx = sx * (w / 2 + 2),
            ly = sy * (d / 2 + 2);
          return inside(x + lx * ca - ly * sa, y + lx * sa + ly * ca);
        });
        if (!ok) continue;
        placed++;
        const kind = placed % 3;
        const mtx = new THREE.Matrix4()
          .makeRotationZ(A)
          .setPosition(x, y, podiumH + (kind === 2 ? 0.4 : 1.2));
        if (kind === 2)
          addGeo(
            kit.mat('#a9bcc6', { roughness: 0.25, metalness: 0.3 }),
            new THREE.BoxGeometry(w, d, 0.8),
            mtx,
          );
        else
          addGeo(
            kit.mat(kind ? '#b9b7b0' : '#9ea3a6', { roughness: 0.7, metalness: kind ? 0 : 0.3 }),
            new THREE.BoxGeometry(w, d, 2.4),
            mtx,
          );
      }
    }
    g.add(batch.toGroup('charing_cross_hospital'));
    return g;
  },
};
