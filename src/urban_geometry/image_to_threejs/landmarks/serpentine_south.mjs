// Serpentine South (former Serpentine Gallery), Kensington Gardens: the 1933-34 tea
// pavilion by James Grey West (Office of Works). Square single-storey body in grey
// brick with red brick dressings, nine bays a side with paired Doric columns under a
// balustrade in the centre three bays, a two-storey central core with a tall hipped
// tiled roof and a white timber cupola. Entrance recessed on the north side.
export default {
  id: 'serpentine_south',
  name: 'Serpentine South Gallery',
  claims: ['f73fb7b1-58cd-4c43-8e02-0d756e86dc14'],
  references: [
    {
      title: 'Serpentine Galleries - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Serpentine_Galleries',
      used_for: 'Grade II listed 1933-34 tea pavilion by James Grey West, gallery since 1970',
    },
    {
      title: 'Serpentine Gallery - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101217605',
      used_for:
        'grey brick, red dressings, hipped tiled roof; single storey with two-storey core, tall hipped roof and timber cupola; nine bays, paired Doric columns in centre three bays with balustrade; entrance recessed to north',
    },
    {
      title: 'Our History - Serpentine',
      url: 'https://www.serpentinegalleries.org/our-history/',
      used_for: 'history of the pavilion and gallery',
    },
  ],
  notes:
    'Plan square fitted to the Overture outline; body/core heights (4.8 m / 8.6 m) and core size proportioned ' +
    'from the listing description, not measured. Windows are a painted generic sash bay; the missing balustrade on ' +
    'the core is omitted as stated in the listing.',
  build(ctx) {
    const { THREE, kit, frame, buildings } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0];
    const A = frame.angle,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // Area centroid (the bounding-box centre is skewed by small jags on the west side).
    let cx = 0,
      cy = 0,
      ar = 0;
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length],
        cr = p[0] * q[1] - q[0] * p[1];
      ar += cr;
      cx += (p[0] + q[0]) * cr;
      cy += (p[1] + q[1]) * cr;
    }
    cx /= 3 * ar;
    cy /= 3 * ar;
    const L = (x, y) => [cx + x * ca - y * sa, cy + x * sa + y * ca];
    const lbox = (m, x, y, z0, w, d, h, rz = 0) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A + rz);
    };
    const add = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      const mm = new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], z);
      batch.addGeometry(m, geo, mm);
      geo.dispose();
    };
    const e = kit.orientedExtent(ring, A);
    // half extents of the main rectangle (outline minus the small jags)
    const hx = Math.min((e.u1 - e.u0) / 2, 16.7),
      hy = Math.min((e.v1 - e.v0) / 2, 13.7);
    // local frame centred on the oriented box
    const half = Math.min(hx, hy) - 0.2;

    const grey = '#8d8a83';
    const brickTex = kit.paintedMaterial('serpentine_south:bay', 512, 256, (c, w, h) => {
      const r = kit.rng(0.913);
      c.fillStyle = grey;
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          const col = new THREE.Color(grey).multiplyScalar(0.88 + r() * 0.24);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      // one storey per half tile (bottom half used for the single-storey body)
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++) {
          const ww = bw * 0.46,
            wh = fh * 0.62,
            x0 = b * bw + (bw - ww) / 2,
            y0 = f * fh + fh * 0.18;
          c.fillStyle = '#9c4a36'; // red brick dressings
          c.fillRect(x0 - 6, y0 - 8, ww + 12, wh + 10);
          c.fillStyle = '#eeeae2';
          c.fillRect(x0 - 1, y0 - 1, ww + 2, wh + 2);
          c.fillStyle = '#2f3a42';
          c.fillRect(x0 + 2, y0 + 2, ww - 4, wh - 4);
          c.fillStyle = '#eeeae2';
          c.fillRect(x0 + ww / 2 - 1, y0, 2, wh);
          for (let i = 1; i < 4; i++) c.fillRect(x0, y0 + (wh * i) / 4 - 1, ww, 2);
          // red brick band at sill and below the cornice
          c.fillStyle = '#9c4a36';
          c.fillRect(0, f * fh + fh * 0.9, w, 5);
          c.fillRect(0, f * fh + 2, w, 4);
        }
    });
    const brick = kit.mat(grey);
    const red = kit.mat('#9c4a36');
    const stone = kit.mat('portland_stone');
    const white = kit.mat('white_render');
    const tiles = kit.roof('clay', 1);
    const lead = kit.mat('lead');
    const dark = kit.mat('dark_glass');

    const H1 = 4.8,
      H2 = 8.6;
    const body = [[L(-half, -half), L(half, -half), L(half, half), L(-half, half)]];
    // Use the real outline for the body walls so it sits on its footprint.
    kit.walls(batch, brickTex, [[ring]], 0, H1, { bay: (2 * half) / 9, storey: H1 });
    kit.walls(batch, red, [[kit.offsetRing(ring, 0.12)]], 0, 0.5);
    // cornice and parapet
    {
      const o = kit.offsetRing(ring, 0.35);
      kit.walls(batch, stone, [[o]], H1 - 0.45, H1);
      kit.cap(batch, stone, [[o, ring.slice().reverse()]], H1);
      kit.cap(batch, stone, [[o, ring.slice().reverse()]], H1 - 0.45, { down: true });
      const inner = kit.offsetRing(ring, -0.3);
      kit.walls(batch, brick, [[ring]], H1, H1 + 0.6);
      kit.walls(batch, brick, [[inner.slice().reverse()]], H1, H1 + 0.6);
      kit.cap(batch, stone, [[ring, inner.slice().reverse()]], H1 + 0.6);
      kit.cap(batch, lead, [[ring]], H1 + 0.05);
    }
    void body;
    // Centre three bays of each side: paired Doric columns under a balustrade.
    const bayW = (2 * half) / 9;
    // side whose outward normal points closest to north (recessed entrance)
    let north = 0,
      best = -2;
    for (let s = 0; s < 4; s++) {
      const rz = (s * Math.PI) / 2,
        nx = Math.sin(rz),
        ny = -Math.cos(rz);
      const wy = nx * sa + ny * ca;
      if (wy > best) ((best = wy), (north = s));
    }
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      const rot = (x, y) => [
        x * Math.cos(rz) - y * Math.sin(rz),
        x * Math.sin(rz) + y * Math.cos(rz),
      ];
      const half = (side % 2 ? hx : hy) - 0.15;
      const bayW = (2 * (side % 2 ? hy : hx)) / 9;
      const out = half + 1.2;
      // recessed opening behind the columns
      const [ox, oy] = rot(0, -half - 0.02);
      lbox(
        side === north ? kit.mat('#1e2328') : dark,
        ox,
        oy,
        0.4,
        bayW * 3 - 0.6,
        0.08,
        H1 - 1.2,
        rz,
      );
      // floor of the loggia and entablature
      const [px, py] = rot(0, -half - 0.6);
      lbox(stone, px, py, 0, bayW * 3 + 0.8, 1.4, 0.35, rz);
      lbox(stone, px, py, H1 - 0.9, bayW * 3 + 0.8, 1.4, 0.9, rz);
      // balustrade
      lbox(stone, px, py, H1, bayW * 3 + 0.8, 1.2, 0.15, rz);
      for (let k = 0; k <= 14; k++) {
        const t = -bayW * 1.5 + (k * bayW * 3) / 14;
        const [bx, by] = rot(t, -half - 1.1);
        add(
          new THREE.CylinderGeometry(0.09, 0.12, 0.7, 6).rotateX(Math.PI / 2),
          stone,
          bx,
          by,
          H1 + 0.5,
          rz,
        );
      }
      const [tx, ty] = rot(0, -half - 0.6);
      lbox(stone, tx, ty, H1 + 0.85, bayW * 3 + 0.8, 1.2, 0.2, rz);
      // paired columns at the four bay divisions
      for (const t of [-1.5, -0.5, 0.5, 1.5]) {
        for (const d of [-0.28, 0.28]) {
          const [cx, cy] = rot(t * bayW + d * Math.sign(t), -out + 0.2);
          add(
            new THREE.CylinderGeometry(0.2, 0.24, H1 - 1.25, 12).rotateX(Math.PI / 2),
            white,
            cx,
            cy,
            0.35 + (H1 - 1.25) / 2,
            rz,
          );
          lbox(white, cx, cy, H1 - 0.98, 0.55, 0.55, 0.1, rz);
        }
      }
      void out;
    }
    // Two-storey central core with tall hipped tiled roof and cupola.
    const C = half * 0.42;
    const core = [L(-C, -C), L(C, -C), L(C, C), L(-C, C)];
    kit.walls(batch, brickTex, [[core]], H1, H2, {
      bay: (2 * C) / 3,
      storey: H2 - H1,
      uvBase: H1 - (H2 - H1),
    });
    kit.walls(batch, stone, [[kit.offsetRing(core, 0.3)]], H2 - 0.35, H2);
    const roof = kit.pitchedRoof(batch, tiles, brick, core, A, H2, C * 1.25, 'pyramidal', {
      overhang: 0.6,
    });
    const top = roof.top;
    // timber cupola: square base, open arched stage, ogee lead cap, finial
    lbox(white, 0, 0, top - 1.2, 2.6, 2.6, 1.6);
    for (const [dx, dy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ])
      lbox(white, dx * 1.05, dy * 1.05, top + 0.4, 0.35, 0.35, 1.8);
    lbox(dark, 0, 0, top + 0.4, 1.9, 1.9, 1.8);
    lbox(white, 0, 0, top + 2.2, 2.8, 2.8, 0.3);
    const cap = new THREE.LatheGeometry(
      [
        [1.5, 0],
        [1.4, 0.4],
        [0.9, 0.9],
        [0.45, 1.5],
        [0.25, 1.9],
        [0, 2.0],
      ].map(([a, b]) => new THREE.Vector2(a, b)),
      8,
    ).rotateX(Math.PI / 2);
    add(cap, lead, 0, 0, top + 2.5, Math.PI / 8);
    add(
      new THREE.CylinderGeometry(0.05, 0.05, 1.4, 4).rotateX(Math.PI / 2),
      kit.mat('gold'),
      0,
      0,
      top + 5.0,
    );
    // core windows facing each way (two per side)
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      for (const t of [-C / 2.2, C / 2.2]) {
        const x = t * Math.cos(rz) - (-C - 0.02) * Math.sin(rz),
          y = t * Math.sin(rz) + (-C - 0.02) * Math.cos(rz);
        lbox(red, x, y, H1 + 1.0, 1.9, 0.06, 2.4, rz);
        lbox(dark, x, y, H1 + 1.15, 1.3, 0.1, 2.0, rz);
      }
    }
    g.add(batch.toGroup('serpentine_south'));
    return g;
  },
};
