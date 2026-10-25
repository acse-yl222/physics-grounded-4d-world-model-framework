// Eighty-Eight Wood Lane, Imperial College White City Campus (PLP Architecture with
// Aukett Swanke masterplan; facade by Lindner, completed ~2018). 34-storey residential
// tower for Imperial staff / key workers at the corner of Wood Lane and the Westway,
// part of the Imperial West scheme with Wood Lane Studios. Unitised facade of ~1.5 m
// panels mixing glass and terracotta plates; clear horizontal bands split the tower
// into four stacked sections and the form tapers as it rises.
export default {
  id: 'eighty_eight_wood_lane',
  name: 'Eighty-Eight Wood Lane (Imperial West tower)',
  claims: ['afb20d8e-65e4-4afd-9763-e88e74c3c86f'],
  references: [
    {
      title: 'Eighty Eight Wood Lane - PLP Architecture',
      url: 'https://plparchitecture.com/?p=5788',
      used_for:
        '34-storey residential tower, glass and terracotta cladding, four sections divided by horizontal bands, tapering form',
    },
    {
      title: 'Imperial College White City Campus Block F - Lindner',
      url: 'https://www.lindner-group.com/en/references/imperial-college-white-city-campus-block-f',
      used_for:
        'facade panels mostly 1.5 m wide mixing glass and terracotta plates, 80 Wood Lane, 2018',
    },
    {
      title: 'Imperial West masterplan - Aukett Swanke',
      url: 'https://www.aukettswanke.com/projects/imperial-west-masterplan/',
      used_for: 'masterplan context with Wood Lane Studios',
    },
  ],
  notes:
    'Overture h=7.7 m is wrong; height 34 storeys x 3.15 m + crown = ~111 m (no metric height found). ' +
    'Taper modelled as four stepped sections (1.1 m inset per section) on the oriented rectangle of the ' +
    'footprint; the terracotta / glass panel mix and band design are approximations.',
  build({ THREE, kit, buildings, frame }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring0 = buildings[0].polys[0][0];
    const e = kit.orientedExtent(ring0, frame.angle);
    const L = e.u1 - e.u0,
      W = e.v1 - e.v0;
    const uc = (e.u0 + e.u1) / 2,
      vc = (e.v0 + e.v1) / 2;
    const rect0 = (l, w) =>
      [
        e.at(uc - l / 2, vc - w / 2, 0),
        e.at(uc + l / 2, vc - w / 2, 0),
        e.at(uc + l / 2, vc + w / 2, 0),
        e.at(uc - l / 2, vc + w / 2, 0),
      ].map((p) => [p[0], p[1]]);
    const rect = (l, w) => {
      const r = rect0(l, w);
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const ST = 3.15,
      NS = 34,
      G = 5;

    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return { a, b, len };
      });
    const skin = (mat, r, z0, z1, tw, th, base = 0) => {
      let s = 0;
      for (const ed of edgesOf(r)) {
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [ed.a[0], ed.a[1], z0],
          [ed.b[0], ed.b[1], z0],
          [ed.b[0], ed.b[1], z1],
          [ed.a[0], ed.a[1], z1],
          [s / tw, v0],
          [(s + ed.len) / tw, v0],
          [(s + ed.len) / tw, v1],
          [s / tw, v1],
        );
        s += ed.len;
      }
    };

    // 12 m x 2 storeys tile: 8 x 1.5 m panels, each glass or terracotta, slab line per storey.
    const facade = kit.paintedMaterial(
      '88wl:facade',
      1024,
      512,
      (c, w, h) => {
        const r = kit.rng(0.8812);
        const pw = w / 8,
          sh = h / 2;
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 8; k++) {
            const x = k * pw,
              y = s * sh;
            const terra = r() < 0.45;
            if (terra) {
              c.fillStyle = ['#b86a47', '#c27752', '#a95f3f'][Math.floor(r() * 3)];
              c.fillRect(x, y, pw, sh);
              c.fillStyle = 'rgba(0,0,0,0.12)';
              for (let yy = y + 14; yy < y + sh; yy += 18) c.fillRect(x, yy, pw, 2); // plate joints
            } else {
              const grd = c.createLinearGradient(x, y, x + pw, y + sh);
              grd.addColorStop(0, '#5a7385');
              grd.addColorStop(1, '#33475a');
              c.fillStyle = grd;
              c.fillRect(x, y, pw, sh);
              c.fillStyle = 'rgba(200,220,235,0.18)';
              c.fillRect(x + 6, y + 10, pw * 0.3, sh - 50);
            }
            c.fillStyle = '#cfcac0';
            c.fillRect(x, y, 4, sh); // mullion
          }
        c.fillStyle = '#d8d4ca';
        c.fillRect(0, sh - 22, w, 22);
        c.fillRect(0, h - 22, w, 22);
      },
      { roughness: 0.55, metalness: 0.1 },
    );
    const band = kit.mat('#e2ded5', { roughness: 0.6 });
    const base = kit.mat('dark_glass');
    const roofM = kit.mat('#8f918e');

    // Glazed double-height base on the actual footprint.
    let br = ring0.slice();
    if (kit.ringArea(br) < 0) br.reverse();
    skin(base, kit.offsetRing(br, -0.8), 0, G, 6, 8);
    kit.walls(batch, band, [[br]], G - 0.8, G);
    kit.cap(batch, band, [[br]], G - 0.8, { down: true });

    // Four stacked, tapering sections separated by recessed light bands.
    const per = [9, 9, 8, 8];
    let z = G,
      lvl = 0;
    for (let sct = 0; sct < 4; sct++) {
      const inset = sct * 1.1;
      const r = rect(L - 2 * inset, W - 2 * inset);
      const z1 = z + per[sct] * ST;
      skin(facade, r, z, z1 - 0.9, 12, 2 * ST, G);
      // band: recessed storey-line with projecting white edge
      const rr = rect(L - 2 * inset - 0.8, W - 2 * inset - 0.8);
      skin(kit.mat('dark_glass'), rr, z1 - 0.9, z1, 6, 4);
      kit.walls(batch, band, [[rect(L - 2 * inset + 0.4, W - 2 * inset + 0.4)]], z1 - 0.35, z1);
      kit.cap(batch, band, [[rect(L - 2 * inset + 0.4, W - 2 * inset + 0.4)]], z1);
      kit.cap(batch, band, [[rect(L - 2 * inset + 0.4, W - 2 * inset + 0.4)]], z1 - 0.35, {
        down: true,
      });
      kit.cap(batch, band, [[r]], z1 - 0.9, { down: true });
      z = z1;
      lvl += per[sct];
    }
    // Crown: plant enclosure in vertical aluminium louvres.
    const top = rect(L - 2 * 3.3 - 6, W - 2 * 3.3 - 2);
    const louvre = kit.paintedMaterial('88wl:louvre', 256, 256, (c, w, h) => {
      c.fillStyle = '#b9bdbd';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#878c8e';
      for (let x = 0; x < w; x += 16) c.fillRect(x, 0, 6, h);
    });
    skin(louvre, top, z, z + 4.5, 4, 4.5, z);
    kit.cap(batch, roofM, [[top]], z + 4.5);
    kit.cap(batch, roofM, [[rect(L - 2 * 3.3 + 0.4, W - 2 * 3.3 + 0.4)]], z + 0.01);
    g.add(batch.toGroup('eighty_eight_wood_lane'));
    return g;
  },
};
