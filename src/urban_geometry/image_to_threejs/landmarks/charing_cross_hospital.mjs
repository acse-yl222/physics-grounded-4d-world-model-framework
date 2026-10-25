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
      title: 'Inventory Site Record - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record/?ID=HAF009',
      used_for: '17 storeys, cruciform arrangement',
    },
  ],
  notes:
    'The Overture outline is a single 15 m podium without tower parts; the tower position (-1352, -2138) and ' +
    'orientation (site grid, 26 deg) were fitted to the widest cross that lies inside the outline, wing length ' +
    '36 m from the centre and width 19 m are estimates. Height 59 m to the ward roof plus a 9 m plant/core top ' +
    '(~68 m) from the storey count. Facade (precast concrete with continuous window bands) is approximate.',
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
    kit.walls(batch, podWall, b.polys, 0, podiumH, { bay: 4, storey: podiumH / 4 });
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
    // Walls edge by edge so the wing ends get the end texture.
    for (let k = 0; k < cross.length; k++) {
      const p = cross[k],
        q = cross[(k + 1) % cross.length];
      const isEnd = k % 3 === 0;
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const nb = Math.max(1, Math.round(len / 3.6));
      const m = isEnd ? endWall : towerWall;
      const v1 = wardTop / (2 * storey);
      batch.quad(
        m,
        [p[0], p[1], podiumH - 1],
        [q[0], q[1], podiumH - 1],
        [q[0], q[1], wardTop],
        [p[0], p[1], wardTop],
        [0, (podiumH - 1) / (2 * storey)],
        [isEnd ? 1 : nb / 4, (podiumH - 1) / (2 * storey)],
        [isEnd ? 1 : nb / 4, v1],
        [0, v1],
      );
    }
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
    g.add(batch.toGroup('charing_cross_hospital'));
    return g;
  },
};
