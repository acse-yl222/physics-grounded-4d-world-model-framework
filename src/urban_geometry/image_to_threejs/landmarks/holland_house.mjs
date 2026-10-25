// Holland House, Holland Park: Jacobean mansion of c.1605 (Sir Walter Cope), largely
// destroyed by incendiary bombs on 27 September 1940. What survives is the restored
// three-storey east wing (youth hostel since 1957-59) - red brick with stone
// dressings, an enclosed ground-floor arcade with round-headed arches, pilastered
// upper storeys and shaped gables to a tiled roof - and the ruined shell of the
// ground floor and south facade of the main range (open-air theatre backdrop),
// laid out on the old E-plan with the west wing stub.
export default {
  id: 'holland_house',
  name: 'Holland House',
  claims: ['a91fcdf0-5939-466f-b8f3-dc92f10ced7e'],
  references: [
    {
      title: 'Holland House - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Holland_House',
      used_for:
        'Jacobean mansion c.1605 for Sir Walter Cope; destroyed 1940; east wing and ground-floor/south facade ruins remain',
    },
    {
      title: 'Holland House Garden - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record?ID=KAC075',
      used_for:
        'three-storey east wing; ground-floor enclosed arcade with round-headed arches; pilasters and shaped gables to a tiled roof; youth hostel; ruin used as theatre backdrop',
    },
    {
      title: 'Holland Park - Historic England list entry',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1000811',
      used_for: 'east wing restored and converted to youth hostel 1957',
    },
    {
      title: 'London Library survives Blitz (1940) - Flashbak',
      url: 'https://flashbak.com/london-library-miraculously-survives-blitz-1940-416988/',
      used_for: 'bombing of 27 September 1940',
    },
  ],
  notes:
    'E-plan read from the Overture outline (wings to the south-south-east). East wing eaves 11 m and gables to ~15 m ' +
    'are estimates (Overture 8.9 m). Ruin wall heights and the extent of surviving fabric in the centre/west are ' +
    'approximated; the 1950s hostel block (Safestay) is a separate footprint left to the generic layer.',
  build(ctx) {
    const { THREE, kit } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const OX = -120,
      OY = -425;
    const A = (22 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const L = (x, y) => [OX + x * ca - y * sa, OY + x * sa + y * ca];
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const lbox = (m, x, y, z0, w, d, h, rz = 0) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A + rz);
    };
    const lgeo = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      batch.addGeometry(
        m,
        geo,
        new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], z),
      );
      geo.dispose();
    };
    const brickC = '#9b5a43';
    const brick = kit.mat(brickC, { roughness: 0.95 });
    const stone = kit.mat('#d9cfb8', { roughness: 0.85 });
    const tiles = kit.roof('clay', 0);
    const dark = kit.mat('#2b3138');
    const lead = kit.mat('lead');

    const wingTex = kit.paintedMaterial('holland_house:wing', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1605);
      c.fillStyle = brickC;
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          const col = new THREE.Color(brickC).multiplyScalar(0.85 + r() * 0.27);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let k = 0; k < 4; k++) {
          // stone-mullioned and transomed window
          const x0 = k * bw + bw * 0.24,
            ww = bw * 0.52,
            y0 = f * fh + fh * 0.2,
            wh = fh * 0.58;
          c.fillStyle = '#d9cfb8';
          c.fillRect(x0 - 5, y0 - 6, ww + 10, wh + 10);
          c.fillStyle = '#323a42';
          c.fillRect(x0, y0, ww, wh);
          c.fillStyle = '#d9cfb8';
          c.fillRect(x0 + ww / 2 - 2, y0, 4, wh);
          c.fillRect(x0, y0 + wh * 0.35, ww, 3);
          // pilaster
          c.fillStyle = '#c7b9a0';
          c.fillRect(k * bw - 4, f * fh, 8, fh);
        }
      c.fillStyle = '#d9cfb8';
      c.fillRect(0, fh - 4, w, 5);
      c.fillRect(0, h - 4, w, 4);
    });

    // Arcade of round-headed arches along a local line (x varies at fixed y, or y at fixed x).
    const arcade = (u0, u1, fixed, alongX, n, zs, zt, depth, open) => {
      const bay = (u1 - u0) / n;
      const pier = Math.min(0.9, bay * 0.25);
      const rA = bay / 2 - pier / 2;
      const shape = new THREE.Shape();
      shape.moveTo(-bay / 2, 0);
      shape.lineTo(-bay / 2, zt - zs);
      shape.lineTo(bay / 2, zt - zs);
      shape.lineTo(bay / 2, 0);
      shape.lineTo(rA, 0);
      shape.absarc(0, 0, rA, 0, Math.PI, false);
      shape.lineTo(-bay / 2, 0);
      for (let i = 0; i < n; i++) {
        const u = u0 + (i + 0.5) * bay;
        const [x, y] = alongX ? [u, fixed] : [fixed, u];
        const rz = alongX ? 0 : Math.PI / 2;
        const geo = new THREE.ExtrudeGeometry(shape, {
          depth,
          bevelEnabled: false,
          curveSegments: 8,
        })
          .rotateX(Math.PI / 2)
          .translate(0, depth / 2, 0);
        lgeo(geo, stone, x, y, zs, rz);
        // piers
        const [px, py] = alongX ? [u - bay / 2 + pier / 2, fixed] : [fixed, u - bay / 2 + pier / 2];
        lbox(stone, px, py, 0, alongX ? pier : depth, alongX ? depth : pier, zs, 0);
        if (!open) {
          const [gx, gy] = alongX ? [u, fixed] : [fixed, u];
          lbox(
            dark,
            gx,
            gy,
            0,
            alongX ? bay - pier : 0.1,
            alongX ? 0.1 : bay - pier,
            zs + rA * 0.9,
          );
        }
      }
      const [ex, ey] = alongX ? [u1 - pier / 2, fixed] : [fixed, u1 - pier / 2];
      lbox(stone, ex, ey, 0, alongX ? pier : depth, alongX ? depth : pier, zs);
    };

    // ---- east wing (restored, roofed) ---------------------------------------------------
    {
      const EAV = 11;
      const body = rect(4, -14.9, 15, 19.9);
      kit.walls(batch, wingTex, [[body]], 4.4, EAV, { bay: 3.4, storey: 3.3, uvBase: 4.4 });
      kit.walls(batch, brick, [[body]], 0, 4.4);
      // enclosed arcade on the west (court) side and the south end
      arcade(-14.9, 19.9, 3.7, false, 9, 2.8, 4.4, 0.6, false);
      arcade(4, 15, -15.2, true, 3, 2.8, 4.4, 0.6, false);
      // string course, cornice, strapwork parapet
      const o = kit.offsetRing(body, 0.25);
      kit.walls(batch, stone, [[o]], 4.3, 4.7);
      kit.walls(batch, stone, [[o]], EAV - 0.4, EAV);
      kit.cap(batch, stone, [[o, body.slice().reverse()]], EAV);
      kit.pitchedRoof(batch, tiles, brick, body, A + Math.PI / 2, EAV, 4.2, 'gabled', {
        overhang: 0.2,
      });
      // shaped (Dutch) gables: south end and three along each long side
      const shapedGable = (x, y, rz, w) => {
        const s = new THREE.Shape();
        const hw = w / 2;
        s.moveTo(-hw, 0);
        s.lineTo(-hw, 1.0);
        s.quadraticCurveTo(-hw * 0.55, 1.2, -hw * 0.5, 2.0);
        s.lineTo(-hw * 0.5, 2.6);
        s.quadraticCurveTo(-hw * 0.2, 2.9, -hw * 0.25, 3.8);
        s.lineTo(-0.45, 4.2);
        s.lineTo(0, 4.8);
        s.lineTo(0.45, 4.2);
        s.lineTo(hw * 0.25, 3.8);
        s.quadraticCurveTo(hw * 0.2, 2.9, hw * 0.5, 2.6);
        s.lineTo(hw * 0.5, 2.0);
        s.quadraticCurveTo(hw * 0.55, 1.2, hw, 1.0);
        s.lineTo(hw, 0);
        s.lineTo(-hw, 0);
        const geo = new THREE.ExtrudeGeometry(s, {
          depth: 0.5,
          bevelEnabled: false,
          curveSegments: 4,
        })
          .rotateX(Math.PI / 2)
          .translate(0, 0.25, 0);
        lgeo(geo, brick, x, y, EAV, rz);
        lbox(stone, x, y, EAV + 4.75, 0.35, 0.35, 0.9, rz);
        lbox(dark, x, y - 0.27 * Math.cos(rz), EAV + 1.0, 1.1, 0.06, 1.6, rz);
      };
      shapedGable(9.5, -15.0, 0, 11);
      shapedGable(9.5, 19.95, 0, 11);
      for (const y of [-6, 3, 12]) {
        shapedGable(3.95, y, Math.PI / 2, 3.6);
        shapedGable(15.05, y, Math.PI / 2, 3.6);
      }
      // tall clustered chimney stacks
      for (const y of [-9, 7.5, 16]) {
        lbox(brick, 9.5, y, EAV, 2.6, 1.2, 7.4);
        lbox(stone, 9.5, y, EAV + 7.4, 3.0, 1.5, 0.35);
      }
      // corner quoins
      for (const [x, y] of [
        [4, -14.9],
        [15, -14.9],
        [15, 19.9],
        [4, 19.9],
      ])
        lbox(stone, x, y, 0, 0.7, 0.7, EAV);
    }

    // ---- ruined main range: open ground-floor arcade and the south facade shell --------------
    {
      const Z1 = 4.6;
      // south arcade (open) across the centre range
      arcade(-21.6, -16.7, -2.3, true, 2, 3.0, Z1, 0.7, true);
      arcade(-3.1, 4.0, -2.3, true, 2, 3.0, Z1, 0.7, true);
      arcade(-16.7, -3.1, -5.0, true, 4, 3.0, Z1, 0.7, true);
      // strapwork balustrade fragments above the arcade
      for (const [x0, x1, y] of [
        [-21.6, -16.7, -2.3],
        [-16.7, -3.1, -5.0],
        [-3.1, 4.0, -2.3],
      ]) {
        lbox(stone, (x0 + x1) / 2, y, Z1, x1 - x0, 0.7, 0.3);
        const n = Math.floor((x1 - x0) / 0.8);
        for (let i = 0; i < n; i++)
          lbox(stone, x0 + (i + 0.5) * ((x1 - x0) / n), y, Z1 + 0.3, 0.28, 0.4, 0.7);
      }
      // the shell of the central porch bay (the theatre backdrop): two storeys of wall with
      // empty window openings, rising to a broken top
      const shell = (x0, x1, y, zTop, rz = 0) => {
        const len = x1 - x0;
        const n = Math.max(1, Math.round(len / 3.2));
        const bw = len / n;
        for (let i = 0; i < n; i++) {
          const cx = x0 + (i + 0.5) * bw;
          const top = zTop - (i % 2 ? 0.6 : 0) - (i === 0 || i === n - 1 ? 1.2 : 0);
          const P = (u, v) => (rz ? [y, u] : [u, v]);
          // pier between openings
          const [px, py] = P(x0 + i * bw + 0.45, y);
          lbox(brick, px, py, Z1 + 0.3, rz ? 0.6 : 0.9, rz ? 0.9 : 0.6, top - Z1 - 0.3);
          // sill and head bands (openings left empty)
          const [mx, my] = P(cx, y);
          lbox(brick, mx, my, Z1 + 0.3, rz ? 0.6 : bw, rz ? bw : 0.6, 0.8);
          lbox(stone, mx, my, Z1 + 2.9, rz ? 0.62 : bw, rz ? bw : 0.62, 0.35);
          lbox(brick, mx, my, Z1 + 3.25, rz ? 0.6 : bw, rz ? bw : 0.6, 0.9);
          if (top > Z1 + 6.5)
            lbox(brick, mx, my, Z1 + 6.0, rz ? 0.6 : bw, rz ? bw : 0.6, top - Z1 - 6.0);
        }
        const [ex, ey] = rz ? [y, x1 - 0.45] : [x1 - 0.45, y];
        lbox(brick, ex, ey, Z1 + 0.3, rz ? 0.6 : 0.9, rz ? 0.9 : 0.6, zTop - Z1 - 1.5);
      };
      shell(-16.7, -3.1, -5.0, 12.0);
      // back (north) wall of the centre range survives low
      lbox(brick, -8.4, 5.7, 0, 25.4, 0.6, 3.2);
      lbox(brick, -10, 3.0, 0, 13.8, 0.5, 2.4);
      // ruined west wing stub: low walls on its outline
      const west = rect(-29, -14.8, -21.6, 3.4);
      kit.walls(batch, brick, [[west]], 0, 3.6);
      kit.walls(batch, brick, [[kit.offsetRing(west, -0.6).slice().reverse()]], 0, 3.6);
      kit.cap(batch, stone, [[west, kit.offsetRing(west, -0.6).slice().reverse()]], 3.6);
      for (let k = 0; k < 4; k++) lbox(dark, -29.02, -12 + k * 4.4, 1.0, 0.1, 1.6, 2.0);
      // stage platform of the open-air theatre in front of the ruin
      lbox(kit.mat('timber'), -9.9, -9.5, 0, 18, 7, 0.9);
      // floor of the roofless rooms
      kit.cap(batch, kit.mat('gravel'), [[rect(-21.6, -2.3, 4.0, 5.7)]], 0.05);
      void lead;
    }
    g.add(batch.toGroup('holland_house'));
    return g;
  },
};
