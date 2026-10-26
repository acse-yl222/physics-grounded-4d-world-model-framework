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
      used_for: 'history of the pavilion (1934, replacing the 1855 refreshment rooms) and gallery',
    },
    {
      title: 'Serpentine Gallery, London - Inexhibit',
      url: 'https://www.inexhibit.com/mymuseum/serpentine-gallery-london/',
      used_for: 'general description of the pavilion in its lawn setting',
    },
  ],
  notes:
    'Plan built as the clean square fitted to the Overture outline (the small jags of the outline are ignored); ' +
    'body/core heights (4.8 m / 8.6 m) and core size proportioned from the listing description, not measured. ' +
    'Sash windows, red brick surrounds and quoins, paired Doric columns, balustrades and the cupola are real ' +
    'geometry; window and glazing-bar counts are typical of the period, not counted from photographs. The ' +
    'cupola balustrade is omitted (stated missing in the listing). The temporary summer pavilion is not modelled.',
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
    const lathe = (m, prof, x, y, z, seg = 16, rz = 0) =>
      add(
        new THREE.LatheGeometry(
          prof.map(([r, h]) => new THREE.Vector2(r, h)),
          seg,
        ).rotateX(Math.PI / 2),
        m,
        x,
        y,
        z,
        rz,
      );
    const e = kit.orientedExtent(ring, A);
    const hx = Math.min((e.u1 - e.u0) / 2, 16.7),
      hy = Math.min((e.v1 - e.v0) / 2, 13.7);

    // ---- materials ------------------------------------------------------------
    const grey = '#8f8b83';
    const brickTex = kit.paintedMaterial(
      'serpentine_south:brick2',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.913);
        c.fillStyle = '#a8a59d';
        c.fillRect(0, 0, w, h);
        for (let y = 0, row = 0; y < h; y += 4, row++)
          for (let x = row % 2 ? -6 : 0; x < w; x += 12) {
            const col = new THREE.Color(grey).multiplyScalar(0.86 + r() * 0.26);
            c.fillStyle = '#' + col.getHexString();
            c.fillRect(x + 0.5, y + 0.5, 11, 3);
          }
      },
      { vertexColors: true },
    );
    const brick = kit.mat(grey);
    const red = kit.mat('#9c4a36', { roughness: 0.88 });
    const stone = kit.mat('portland_stone');
    const white = kit.mat('#f1efe8', { roughness: 0.55 });
    const tiles = kit.roof('clay', 1);
    const lead = kit.mat('lead');
    const glass = kit.mat('#40505c', { roughness: 0.2, metalness: 0.15 });
    const doorM = kit.mat('#2b3a33', { roughness: 0.6 });
    const gold = kit.mat('gold');
    const paving = kit.mat('#c3bcab', { roughness: 0.95 });

    const H1 = 4.8,
      H2 = 8.6;
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const body = rect(-hx, -hy, hx, hy);

    // forecourt paving apron round the building
    {
      const apron = rect(-hx - 3, -hy - 3, hx + 3, hy + 3);
      kit.cap(batch, paving, [[apron, body.slice().reverse()]], 0.03);
    }
    // body walls, red brick plinth, stone cornice and brick parapet with coping
    kit.walls(batch, brickTex, [[body]], 0, H1, { bay: 1, storey: 2, color: [1, 1, 1] });
    kit.cornice(batch, red, body, 0, { height: 0.55, projection: 0.12 });
    kit.cornice(batch, red, body, H1 - 0.9, { height: 0.3, projection: 0.05 }); // red frieze band
    kit.cornice(batch, stone, body, H1 - 0.5, { height: 0.5, projection: 0.4, steps: 2 });
    {
      const inner = kit.offsetRing(body, -0.3);
      kit.walls(batch, brick, [[body]], H1, H1 + 0.6, { bay: 1e6 });
      kit.walls(batch, brick, [[inner.slice().reverse()]], H1, H1 + 0.6, { bay: 1e6 });
      kit.cap(
        batch,
        stone,
        [[kit.offsetRing(body, 0.06), kit.offsetRing(inner, -0.06).slice().reverse()]],
        H1 + 0.72,
      );
      kit.walls(batch, stone, [[kit.offsetRing(body, 0.06)]], H1 + 0.6, H1 + 0.72, { bay: 1e6 });
      kit.cap(batch, lead, [[body]], H1 + 0.05);
    }
    // red brick quoins at the corners
    for (const [sx, sy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ])
      for (let z = 0.55, k = 0; z < H1 - 0.95; z += 0.38, k++) {
        const long = k % 2 ? 0.5 : 0.85;
        lbox(red, sx * (hx - long / 2 + 0.03), sy * (hy + 0.0), z, long, 0.1, 0.34);
        lbox(
          red,
          sx * (hx + 0.0),
          sy * (hy - (k % 2 ? 0.85 : 0.5) / 2 + 0.03),
          z,
          0.1,
          k % 2 ? 0.85 : 0.5,
          0.34,
        );
      }

    // which side faces north (recessed entrance)
    let north = 0,
      best = -2;
    for (let s = 0; s < 4; s++) {
      const rz = (s * Math.PI) / 2,
        nx = Math.sin(rz),
        ny = -Math.cos(rz);
      const wy = nx * sa + ny * ca;
      if (wy > best) ((best = wy), (north = s));
    }
    const sash = {
      width: 1.3,
      height: 2.5,
      count: 1,
      margin: 0,
      depth: 0.12,
      glass,
      frame: white,
      sill: stone,
      head: 'lintel',
      bars: 2,
      surround: 0.24,
      surroundMat: red,
    };
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      const rot = (x, y) => [
        x * Math.cos(rz) - y * Math.sin(rz),
        x * Math.sin(rz) + y * Math.cos(rz),
      ];
      const half = side % 2 ? hx : hy; // distance of this face from the centre
      const span = side % 2 ? hy : hx; // half-length of this face
      const bayW = (2 * span) / 9;
      const S = (u, d = 0) => L(...rot(u, -half - d));
      // windows in the outer three bays each side
      for (let i = 0; i < 9; i++) {
        if (i >= 3 && i <= 5) continue;
        const u = -span + (i + 0.5) * bayW;
        kit.windowRow(batch, S(u - bayW / 2), S(u + bayW / 2), 1.1, sash);
        // red brick keystone over the window
        const k = S(u, 0.12);
        kit.box(batch, red, k[0], k[1], 3.75, 0.36, 0.14, 0.42, A + rz);
      }
      // centre loggia: glazed doors behind paired Doric columns
      const isN = side === north;
      kit.windowRow(batch, S(-1.5 * bayW), S(1.5 * bayW), 0.4, {
        width: 1.6,
        height: isN ? 3.0 : 2.9,
        count: 3,
        margin: 0,
        glass: isN ? doorM : glass,
        frame: white,
        sill: stone,
        head: 'none',
        bars: isN ? 1 : 2,
      });
      // stone loggia floor and steps
      const pf = S(0, 0.75);
      kit.box(batch, stone, pf[0], pf[1], 0, bayW * 3 + 0.8, 1.5, 0.35, A + rz);
      const st = S(0, 1.75);
      kit.box(batch, stone, st[0], st[1], 0, bayW * 3 - 0.4, 0.6, 0.18, A + rz);
      // entablature
      const en = S(0, 0.7);
      kit.box(batch, stone, en[0], en[1], H1 - 1.0, bayW * 3 + 0.8, 1.45, 0.55, A + rz);
      kit.box(batch, stone, en[0], en[1], H1 - 0.45, bayW * 3 + 1.0, 1.6, 0.45, A + rz);
      // paired Doric columns at the four bay divisions
      for (const t of [-1.5, -0.5, 0.5, 1.5]) {
        const u = t * bayW;
        kit.colonnade(batch, white, S(u - 0.33, 1.2), S(u + 0.33, 1.2), 0.35, H1 - 1.35, {
          count: 2,
          radius: 0.2,
          capital: 'doric',
        });
      }
      // balustrade above the loggia with end pedestals
      kit.balustrade(batch, stone, [S(-1.5 * bayW - 0.2, 1.15), S(1.5 * bayW + 0.2, 1.15)], H1, {
        height: 0.85,
        spacing: 0.32,
      });
      for (const u of [-1.5 * bayW - 0.2, 1.5 * bayW + 0.2]) {
        const p = S(u, 1.15);
        kit.box(batch, stone, p[0], p[1], H1, 0.55, 0.55, 0.95, A + rz);
      }
      // north entrance: lettering panel over the doors
      if (isN) {
        const sign = kit.paintedMaterial('serpentine_south:sign', 512, 64, (c, w, h) => {
          c.fillStyle = '#ddd6c4';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#2b2b2b';
          c.font = 'bold 34px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('SERPENTINE SOUTH', w / 2, h / 2 + 2);
        });
        const p = S(0, 1.46);
        const pl = new THREE.PlaneGeometry(bayW * 2, 0.4).rotateX(Math.PI / 2).rotateZ(Math.PI);
        batch.addGeometry(
          sign,
          pl,
          new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], H1 - 0.73),
        );
        pl.dispose();
      }
    }

    // ---- two-storey central core with tall hipped tiled roof and cupola ----------
    const C = Math.min(hx, hy) * 0.42;
    const core = rect(-C, -C, C, C);
    kit.walls(batch, brickTex, [[core]], H1, H2, { bay: 1, storey: 2, color: [0.97, 0.97, 0.97] });
    kit.cornice(batch, red, core, H1 + 0.6, { height: 0.25, projection: 0.06 });
    kit.cornice(batch, stone, core, H2 - 0.4, { height: 0.4, projection: 0.35, steps: 2 });
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      const rot = (x, y) => [
        x * Math.cos(rz) - y * Math.sin(rz),
        x * Math.sin(rz) + y * Math.cos(rz),
      ];
      kit.windowRow(batch, L(...rot(-C, -C)), L(...rot(C, -C)), H1 + 1.1, {
        ...sash,
        count: 2,
        margin: C * 0.35,
        height: 1.9,
        width: 1.2,
      });
    }
    const roof = kit.pitchedRoof(batch, tiles, brick, core, A, H2, C * 1.25, 'pyramidal', {
      overhang: 0.7,
    });
    // soffit under the eaves overhang
    kit.cap(batch, white, [[kit.offsetRing(core, 0.7), core.slice().reverse()]], H2, {
      down: true,
    });
    // hip rolls
    const top = roof.top;
    for (const [sx, sy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ]) {
      const p0 = L(sx * (C + 0.7), sy * (C + 0.7));
      const len = Math.hypot((C + 0.7) * Math.SQRT2, top - H2);
      const geo = new THREE.BoxGeometry(0.16, 0.16, len);
      const dir = new THREE.Vector3(-(p0[0] - cx), -(p0[1] - cy), top - H2).normalize();
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
      const m = new THREE.Matrix4().compose(
        new THREE.Vector3((p0[0] + cx) / 2, (p0[1] + cy) / 2, (H2 + top) / 2),
        q,
        new THREE.Vector3(1, 1, 1),
      );
      batch.addGeometry(red, geo, m);
      geo.dispose();
    }
    // timber cupola: square base, open arcaded stage, ogee lead cap, finial and vane
    lbox(white, 0, 0, top - 1.4, 2.6, 2.6, 1.8);
    lbox(white, 0, 0, top + 0.2, 2.9, 2.9, 0.22);
    for (const [dx, dy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ])
      lbox(white, dx * 1.08, dy * 1.08, top + 0.42, 0.36, 0.36, 1.9);
    lbox(kit.mat('#2f363c'), 0, 0, top + 0.42, 1.7, 1.7, 1.9);
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      const ox = Math.sin(rz) * 1.08,
        oy = -Math.cos(rz) * 1.08;
      const arch = new THREE.Shape();
      arch.moveTo(-0.9, 0);
      arch.lineTo(-0.9, 0.75);
      arch.lineTo(0.9, 0.75);
      arch.lineTo(0.9, 0);
      arch.lineTo(0.72, 0);
      arch.absarc(0, 0, 0.72, 0, Math.PI, false);
      arch.lineTo(-0.9, 0);
      const ge = new THREE.ExtrudeGeometry(arch, {
        depth: 0.2,
        bevelEnabled: false,
        curveSegments: 8,
      })
        .rotateX(Math.PI / 2)
        .translate(0, 0.1, 0);
      add(ge, white, ox, oy, top + 1.57, rz);
    }
    lbox(white, 0, 0, top + 2.32, 3.0, 3.0, 0.28);
    lathe(
      lead,
      [
        [0, 0],
        [1.45, 0],
        [1.4, 0.3],
        [1.1, 0.75],
        [0.65, 1.2],
        [0.38, 1.6],
        [0.3, 1.85],
        [0.14, 2.0],
        [0, 2.05],
      ],
      0,
      0,
      top + 2.6,
      4,
      Math.PI / 4,
    );
    lathe(
      gold,
      [
        [0, 0],
        [0.16, 0.04],
        [0.18, 0.2],
        [0.07, 0.36],
        [0, 0.4],
      ],
      0,
      0,
      top + 4.6,
      8,
    );
    add(new THREE.CylinderGeometry(0.03, 0.03, 1.6, 4).rotateX(Math.PI / 2), gold, 0, 0, top + 5.7);
    lbox(gold, 0.25, 0, top + 6.1, 0.9, 0.03, 0.3);
    lbox(gold, 0, 0, top + 5.6, 0.8, 0.03, 0.03);
    lbox(gold, 0, 0, top + 5.6, 0.03, 0.8, 0.03);

    g.add(batch.toGroup('serpentine_south'));

    // ---- lamps and benches on the apron ------------------------------------------
    const lamps = [],
      benches = [];
    for (const [sx, sy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ]) {
      const p = L(sx * (hx + 2.2), sy * (hy + 2.2));
      lamps.push([p[0], p[1], A + Math.atan2(sy, sx) + Math.PI / 2]);
    }
    for (let side = 0; side < 4; side++) {
      const rz = (side * Math.PI) / 2;
      const half = side % 2 ? hx : hy;
      const span = side % 2 ? hy : hx;
      for (const u of [-span * 0.62, span * 0.62]) {
        const x = u * Math.cos(rz) - (-half - 2.4) * Math.sin(rz),
          y = u * Math.sin(rz) + (-half - 2.4) * Math.cos(rz);
        const p = L(x, y);
        benches.push([p[0], p[1], A + rz + Math.PI]);
      }
    }
    g.add(ctx.placeAssets('street_lamp', lamps, { name: 'serpentine_south:lamps' }));
    g.add(ctx.placeAssets('bench', benches, { name: 'serpentine_south:benches' }));
    return g;
  },
};
