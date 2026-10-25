// Wood Lane Studios (Gradpad), Imperial College postgraduate accommodation, White
// City Campus north site (Imperial West phase one, ISG, completed August 2012).
// 606 self-contained studios in four linked residential blocks (reported as up to ten
// storeys) wrapped around courtyards between Shinfield Street, the MSRH and the
// Hammersmith & City line.
export default {
  id: 'wood_lane_studios',
  name: 'Wood Lane Studios (Gradpad)',
  claims: ['1bb9d556-765b-4913-b2f8-bad00648e5c8'],
  references: [
    {
      title: 'Wood Lane Studios welcomes first residents - Imperial News',
      url: 'https://www.imperial.ac.uk/news/114895/wood-lane-studios-welcomes-first-residents/',
      used_for: '19,500 m2, 606 self-contained studios on the Imperial West site',
    },
    {
      title: 'Wood Lane Studios - TLOTT',
      url: 'https://www.tlottltd.co.uk/wood-lane-studios-west-london',
      used_for: '600 rooms over four blocks, completed August 2012, with ISG',
    },
    {
      title: 'Imperial West masterplan - Aukett Swanke',
      url: 'https://www.aukettswanke.com/projects/imperial-west-masterplan/',
      used_for: 'Wood Lane Studios as phase one of the Imperial West masterplan',
    },
    {
      title: 'Imperial College second campus gets green light - Construction Enquirer',
      url: 'https://constructionenquirer.com/2012/07/26/phase-two-of-imperial-college-campus-approved',
      used_for: 'first phase of four 10-storey accommodation blocks for 600 students',
    },
  ],
  notes:
    'Overture h=6.1 m is wrong. Block heights are estimates: linked blocks at 7 storeys with the railway-side ' +
    'block raised to 10 storeys (the press figure). Facade materials were not found in any source: pale grey ' +
    'rainscreen panels with storey-high window strips and coloured reveals are an assumption.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const ST = 3.05,
      G = 3.6;
    const H7 = G + 6 * ST,
      H10 = G + 9 * ST;

    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return { a, b, len, dx: dx / len, dy: dy / len, nx: dy / len, ny: -dx / len };
      });
    const skin = (mat, r, z0, z1, tw, th, base = 0) => {
      let s = 0;
      for (const e of edgesOf(r)) {
        if (e.len < 0.05) continue;
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [s / tw, v0],
          [(s + e.len) / tw, v0],
          [(s + e.len) / tw, v1],
          [s / tw, v1],
        );
        s += e.len;
      }
    };

    const facade = kit.paintedMaterial(
      'wls:facade',
      512,
      512,
      (c, w, h) => {
        // 7.2 m x 2 storeys: studio windows every 2.4 m, alternate reveal colours.
        c.fillStyle = '#d7d8d4';
        c.fillRect(0, 0, w, h);
        const bw = w / 3,
          sh = h / 2;
        const reveal = ['#7d9aa6', '#c4b48e', '#8a9e7c'];
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 3; k++) {
            const x = k * bw + bw * 0.28,
              y = s * sh + sh * 0.16,
              ww = bw * 0.44,
              hh = sh * 0.68;
            c.fillStyle = reveal[(k + s * 2) % 3];
            c.fillRect(x - 8, y - 8, ww + 16, hh + 16);
            c.fillStyle = '#34424c';
            c.fillRect(x, y, ww, hh);
            c.fillStyle = 'rgba(220,235,245,0.18)';
            c.fillRect(x + 4, y + 4, ww * 0.3, hh - 8);
          }
        c.fillStyle = 'rgba(0,0,0,0.08)';
        for (let k = 0; k <= 6; k++) c.fillRect((k * w) / 6, 0, 2, h);
        c.fillRect(0, sh - 2, w, 2);
      },
      { roughness: 0.8 },
    );
    const base = kit.paintedMaterial('wls:base', 256, 256, (c, w, h) => {
      c.fillStyle = '#5f6266';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#2c3a44';
      c.fillRect(16, 30, w / 2 - 32, h - 60);
      c.fillRect(w / 2 + 16, 30, w / 2 - 32, h - 60);
    });
    const coping = kit.mat('#b9bbb8');
    const roofM = kit.mat('#8f918d');

    // Linked 7-storey blocks on the whole footprint.
    skin(base, ring, 0, G, 6, G, 0);
    skin(facade, ring, G, H7, 7.2, 2 * ST, G);
    kit.walls(batch, coping, [[ring]], H7, H7 + 0.6);
    kit.cap(batch, roofM, [[ring]], H7 + 0.2);
    // Railway-side block (longest straight run of the footprint) raised to 10 storeys.
    const E = edgesOf(ring).sort((p, q) => q.len - p.len);
    const spine = E[0];
    // block = spine edge extruded inward by ~16 m (the block's depth on the footprint)
    const D = 15.8,
      inset = 0.0;
    const ax = spine.a,
      bx = spine.b;
    const blk = [
      ax,
      bx,
      [bx[0] - spine.nx * D, bx[1] - spine.ny * D],
      [ax[0] - spine.nx * D, ax[1] - spine.ny * D],
    ].map((p) => [p[0] + spine.nx * inset, p[1] + spine.ny * inset]);
    skin(facade, blk, H7, H10, 7.2, 2 * ST, G);
    kit.walls(batch, coping, [[blk]], H10, H10 + 0.6);
    kit.cap(batch, roofM, [[blk]], H10 + 0.2);
    // Lift / stair cores and plant boxes on the roofs.
    const rr = kit.rng(0.2012);
    for (let k = 0; k < 3; k++) {
      const t = 0.2 + 0.3 * k;
      const x = ax[0] + (bx[0] - ax[0]) * t - spine.nx * D * 0.5,
        y = ax[1] + (bx[1] - ax[1]) * t - spine.ny * D * 0.5;
      kit.box(batch, coping, x, y, H10 + 0.2, 4 + rr() * 2, 4, 2.8, Math.atan2(spine.dy, spine.dx));
    }
    g.add(batch.toGroup('wood_lane_studios'));
    return g;
  },
};
