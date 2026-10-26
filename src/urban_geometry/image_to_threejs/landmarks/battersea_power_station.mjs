// Battersea Power Station (J. Theo Halliday and Sir Giles Gilbert Scott, engineer
// Leonard Pearce; A station 1929-35, B station 1937-41, completed 1955). Steel frame
// clad in brown Blockley brick with Art Deco ("jazz modern") vertical fluting, a
// tall central boiler house flanked by the lower turbine halls / switch houses,
// stepped brick corner (wash) towers and four white pre-cast concrete fluted
// chimneys (~103 m). Since the 2022 redevelopment the outer blocks carry glazed
// apartment storeys, the boiler house roof holds sky villas around a garden square
// and the north-west chimney houses the Lift 109 glass lift.
export default {
  id: 'battersea_power_station',
  name: 'Battersea Power Station',
  claims: ['42c2cb32-5a3e-438c-b441-94251d9888bd'],
  references: [
    {
      title: 'Battersea Power Station - Historic England list entry 1357620',
      url: 'https://HistoricEngland.org.uk/listing/the-list/list-entry/1357620',
      used_for:
        'steel frame clad in brown Blockley brick in English bond, concrete roofs, pre-cast concrete chimneys, phasing',
    },
    {
      title: 'Battersea Power Station - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101357620-battersea-power-station-queenstown-ward',
      used_for: 'listing text: Halliday / Scott, boiler house between turbine halls',
    },
    {
      title: 'Battersea Power Station - The Twentieth Century Society',
      url: 'https://c20society.org.uk/100-buildings/1933-battersea-power-station-london',
      used_for: 'column-like chimneys on modelled bases, jazz modern brickwork of the vast walls',
    },
    {
      title: 'Battersea Power Station - Gilbert Scott',
      url: 'https://gilbertscott.org/battersea-power-station',
      used_for: 'vertical striations accentuating height',
    },
    {
      title: 'Battersea Power Station - WilkinsonEyre',
      url: 'https://www.wilkinsoneyre.com/projects/battersea-power-station',
      used_for: 'sky villas around rooftop garden squares above the boiler house and turbine halls',
    },
    {
      title: 'Michaelis Boyd unveils apartments inside Battersea Power Station - Dezeen',
      url: 'https://www.dezeen.com/?p=1763325',
      used_for: 'glazed floors added on top of the switch houses',
    },
    {
      title: 'Battersea Power Station Chimney Rebuild Project - e-architect',
      url: 'https://www.e-architect.com/london/battersea-power-station-chimney-rebuild',
      used_for:
        'rebuilt chimneys: jump-form shuttering rings, hand-poured concrete, original design',
    },
    {
      title: 'Was it worth spending £48m on Battersea Power Station chimneys? - BD Online',
      url: 'https://bdonline.co.uk/opinion/was-it-worth-spending-48m-on-battersea-power-stations-chimneys/5089447.article',
      used_for: 'fluted, slightly rippled chimney finish, ivory paint colour',
    },
    {
      title: 'Lift 109 - Battersea Power Station',
      url: 'https://batterseapowerstation.co.uk/retailers/lift-109/',
      used_for: 'circular glass lift in the north-west chimney, 109 m viewpoint',
    },
    {
      title:
        'Temporary Removal of Historic Cranes from Power Station Jetty - Port of London Authority',
      url: 'https://server1.pla.co.uk/Temporary-Removal-of-Historic-Cranes-from-Power-Station-Jetty',
      used_for:
        'Stothert & Pitt jetty cranes removed in 2014 (so the jetty is drawn without cranes)',
    },
    {
      title: 'Battersea cranes - The Twentieth Century Society',
      url: 'https://c20society.org.uk/?p=24237',
      used_for: 'cranes still in storage at Tilbury, not reinstated',
    },
  ],
  notes:
    'Massing from the Overture parts (30 m outer halls, 50 m boiler house, 55 m corner towers, 103 m chimneys), ' +
    'modelled in a local frame (u north along 77.5 deg, v west). Brick fluting ribs, window strip sizes, tower step ' +
    'tiers, entrance canopies and sky-villa layout are proportioned from general photo knowledge, not measured. ' +
    'Lift 109 capsule drawn rising ~6 m above the north-west chimney rim (109 m). Jetty drawn without its cranes ' +
    '(removed 2014, in storage). Riverside lamps/benches are reused generic assets.',
  build({ THREE, kit, buildings, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = (77.5 * Math.PI) / 180,
      CX = 3875.4,
      CY = -2742.9;
    const ca = Math.cos(A),
      sa = Math.sin(A);
    // local frame: u towards the river (north), v west
    const toLocal = ([x, y]) => [(x - CX) * ca + (y - CY) * sa, -(x - CX) * sa + (y - CY) * ca];
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = 0) => {
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));
      geo.dispose();
    };
    const latheB = (mat, prof, x, y, z, seg = 40) =>
      put(
        mat,
        new THREE.LatheGeometry(
          prof.map(([r, h]) => new THREE.Vector2(r, h)),
          seg,
        ).rotateX(Math.PI / 2),
        x,
        y,
        z,
      );
    const R = (a, z0, z1) => new THREE.CylinderGeometry(a, a, z1 - z0, 32).rotateX(Math.PI / 2);

    // ---------------------------------------------------------------- materials
    const brickC = '#8a5a40';
    const brickWall = kit.paintedMaterial(
      'battersea_power_station:brick2',
      256,
      256,
      (c, w, h) => {
        // tile 16 m x 12 m: warm Blockley brick, coursing and soft vertical striation
        c.fillStyle = brickC;
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.371);
        for (let y = 0; y < h; y += 2)
          for (let x = (y / 2) % 2 ? 0 : 3; x < w; x += 6) {
            const k = 0.9 + r() * 0.17;
            c.fillStyle = `rgb(${(138 * k) | 0},${(90 * k) | 0},${(64 * k) | 0})`;
            c.fillRect(x, y, 5, 1);
          }
        for (let x = 0; x < w; x += 8) {
          c.fillStyle = 'rgba(40,20,10,0.10)';
          c.fillRect(x, 0, 2, h);
        }
      },
      { roughness: 0.92 },
    );
    const brickPlain = kit.mat(brickC, { roughness: 0.92 });
    const brickDark = kit.mat('#6e4632', { roughness: 0.92 });
    const brickLight = kit.mat('#9c6a4c', { roughness: 0.92 });
    const ivory = kit.mat('#efece2', { roughness: 0.6 });
    const glass = kit.mat('dark_glass');
    const frameM = kit.mat('#2d2f31', { roughness: 0.5, metalness: 0.4 });
    const villaClad = kit.mat('#c9c5bc', { roughness: 0.6 });
    const roofGarden = kit.mat('#5f7a4b', { roughness: 1 });
    const roofDeck = kit.mat('#9a948a', { roughness: 0.95 });
    const paving = kit.mat('paving');
    const black = kit.mat('#1d2024', { roughness: 0.5, metalness: 0.3 });
    const chimMat = kit.paintedMaterial(
      'battersea_power_station:chimney2',
      64,
      256,
      (c, w, h) => {
        // jump-form pour rings (one tile = 12 m of shaft)
        c.fillStyle = '#efece2';
        c.fillRect(0, 0, w, h);
        for (let y = 0; y < h; y += 32) {
          c.fillStyle = 'rgba(120,115,100,0.35)';
          c.fillRect(0, y, w, 2);
          c.fillStyle = 'rgba(255,255,250,0.5)';
          c.fillRect(0, y + 2, w, 1);
        }
        const r = kit.rng(0.55);
        for (let k = 0; k < 120; k++) {
          c.fillStyle = `rgba(150,145,130,${0.05 + r() * 0.08})`;
          c.fillRect(r() * w, r() * h, 2 + r() * 6, 1 + r() * 3);
        }
      },
      { roughness: 0.6 },
    );
    const sign = kit.paintedMaterial('battersea_power_station:sign', 512, 64, (c, w, h) => {
      c.fillStyle = '#1e1f21';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#e9d9a6';
      c.font = 'bold 34px sans-serif';
      c.textAlign = 'center';
      c.fillText('BATTERSEA POWER STATION', w / 2, 45);
    });

    // ---------------------------------------------------------------- helpers
    const edges = (ring, fn) => {
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
        if (len > 0.5) fn(a, q, len, k);
      }
    };
    // vertical brick ribs (fluting) projecting from wall edge a -> b
    const ribs = (a, q, z0, z1, { spacing = 0.9, depth = 0.22, width = 0.4, m = margin0 } = {}) => {
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      const ux = (q[0] - a[0]) / len,
        uy = (q[1] - a[1]) / len;
      const nx = uy,
        ny = -ux,
        ang = Math.atan2(uy, ux);
      const n = Math.floor((len - 2 * m) / spacing);
      for (let i = 0; i <= n; i++) {
        const t = m + (len - 2 * m - n * spacing) / 2 + i * spacing;
        kit.box(
          batch,
          i % 2 ? brickPlain : brickLight,
          a[0] + ux * t + nx * depth * 0.5,
          a[1] + uy * t + ny * depth * 0.5,
          z0,
          width,
          depth,
          z1 - z0,
          ang,
        );
      }
    };
    const margin0 = 0.3;
    const along = (a, q, t, d = 0) => {
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      const ux = (q[0] - a[0]) / len,
        uy = (q[1] - a[1]) / len;
      return [a[0] + ux * t + uy * d, a[1] + uy * t - ux * d, Math.atan2(uy, ux)];
    };
    // vertically stacked windows forming one tall glazed strip with transoms
    const strip = (a, q, z0, z1, opts) => {
      const n = Math.max(1, Math.round((z1 - z0) / (opts.panel ?? 4.5)));
      const ph = (z1 - z0) / n;
      for (let s = 0; s < n; s++)
        kit.windowRow(batch, a, q, z0 + s * ph, {
          glass,
          frame: frameM,
          sill: s === 0 ? brickDark : frameM,
          head: s === n - 1 ? 'lintel' : 'none',
          bars: 1,
          depth: 0.18,
          ...opts,
          height: ph - 0.12,
        });
    };
    const block = (ring, z0, z1, wallMat, roofMat, opts = {}) => {
      kit.walls(batch, wallMat, [[ring]], z0, z1, opts);
      if (roofMat) kit.cap(batch, roofMat, [[ring]], z1);
    };

    // ---------------------------------------------------------------- volumes
    const parts = (b.parts ?? []).map((p) => ({
      ...p,
      ring: ccw(p.polys[0][0].map(toLocal)),
    }));
    const chimneys = parts.filter((p) => p.minh >= 40);
    const towers = parts.filter((p) => p.minh < 40 && p.h >= 54);
    const blocks = parts.filter((p) => p.minh < 40 && p.h < 54);
    const centroid = (ring) => {
      let x = 0,
        y = 0;
      for (const p of ring) {
        x += p[0];
        y += p[1];
      }
      return [x / ring.length, y / ring.length];
    };

    for (const p of blocks) {
      const ring = p.ring;
      const isBoiler = p.h >= 45;
      const isCore = Math.abs(kit.ringArea(ring)) < 300;
      // plinth, walls, string course and stepped parapet coping
      kit.cornice(batch, brickDark, ring, 0, { height: 1.4, projection: 0.35 });
      if (isBoiler || isCore) {
        block(ring, 0, p.h - 2.2, brickWall, null, { bay: 4, storey: 6 });
        kit.cornice(batch, brickDark, ring, p.h - 2.2, { height: 1.2, projection: 0.45, steps: 2 });
        kit.walls(batch, brickPlain, [[ring]], p.h - 1, p.h, {});
        kit.cornice(batch, ivory, ring, p.h - 0.2, { height: 0.25, projection: 0.5 });
        kit.cap(batch, roofDeck, [[ring]], p.h);
        if (isBoiler) {
          // upper boiler house walls above the halls: fluted piers and tall window strips
          edges(ring, (a, q, len) => {
            const n = Math.floor(len / 9);
            if (n < 1) return;
            for (let i = 0; i < n; i++) {
              const t0 = (len - n * 9) / 2 + i * 9;
              const [x0, y0] = along(a, q, t0);
              const [x1, y1] = along(a, q, t0 + 9);
              // fluted pier group at each bay boundary
              ribs([x0, y0], [x1, y1], 31, p.h - 2.2, { spacing: 0.8, m: 0.2 });
            }
          });
          // tall window strips in each bay of the long elevations (above the hall roofs)
          edges(ring, (a, q, len) => {
            if (len < 40) {
              // north / south end walls between the wash towers: full-height window strips
              const fu = Math.abs((q[1] - a[1]) / len);
              if (len < 20 || fu < 0.9) return;
              for (const t of [len / 2 - 6.5, len / 2, len / 2 + 6.5]) {
                const [x0, y0] = along(a, q, t - 1.6, 0.25);
                const [x1, y1] = along(a, q, t + 1.6, 0.25);
                strip([x0, y0], [x1, y1], 9, p.h - 5, {
                  count: 1,
                  width: 2.8,
                  panel: 4.4,
                  bars: 2,
                });
              }
              return;
            }
            const n = Math.floor(len / 9);
            for (let i = 0; i < n; i++) {
              const t0 = (len - n * 9) / 2 + i * 9;
              const [x0, y0] = along(a, q, t0 + 2.5, 0.25);
              const [x1, y1] = along(a, q, t0 + 6.5, 0.25);
              strip([x0, y0], [x1, y1], 33, p.h - 4, { count: 1, width: 3.2, panel: 4.6, bars: 2 });
            }
          });
          // sky villas around the rooftop garden square
          const inner = kit.offsetRing(ring, -11);
          kit.cap(batch, roofGarden, [[inner]], p.h + 0.5);
          kit.walls(batch, brickPlain, [[inner]], p.h, p.h + 0.5, {});
          const e = kit.orientedExtent(ring, 0);
          const u0 = e.u0 + 2.5,
            u1 = e.u1 - 2.5,
            v0 = e.v0 + 2.5,
            v1 = e.v1 - 2.5;
          const villas = [];
          const runU = (vA, vB) => {
            for (let u = u0; u + 11 <= u1 + 0.1; u += 13) villas.push([u, u + 11, vA, vB]);
          };
          runU(v0, v0 + 7.5);
          runU(v1 - 7.5, v1);
          for (let v = v0 + 10; v + 9 <= v1 - 9.5; v += 12) {
            villas.push([u0, u0 + 7.5, v, v + 9]);
            villas.push([u1 - 7.5, u1, v, v + 9]);
          }
          const rr = kit.rng(0.6181);
          for (const [a0, a1, b0, b1] of villas) {
            const vr = [
              [a0, b0],
              [a1, b0],
              [a1, b1],
              [a0, b1],
            ];
            const two = rr() > 0.35;
            const top = p.h + (two ? 6.4 : 3.4);
            block(vr, p.h, top, villaClad, kit.mat('#6b6e70', { roughness: 0.8 }));
            kit.cornice(batch, villaClad, vr, top - 0.3, { height: 0.3, projection: 0.35 });
            kit.windowGrid(batch, vr, p.h + 0.3, two ? 2 : 1, 3.1, {
              width: 2.8,
              height: 2.5,
              bay: 3.6,
              margin: 0.4,
              glass,
              frame: frameM,
              sill: villaClad,
              head: 'none',
              bars: 1,
            });
          }
          // garden planting (instanced trees)
          const ie = kit.orientedExtent(inner, 0);
          const tr = [];
          const rt = kit.rng(0.913);
          for (let u = ie.u0 + 6; u < ie.u1 - 4; u += 16)
            for (const v of [ie.v0 + 5, (ie.v0 + ie.v1) / 2, ie.v1 - 5])
              tr.push([u + (rt() - 0.5) * 3, v + (rt() - 0.5) * 3, rt() * 6]);
          g.add(
            placeAssets('lime_tree', tr, {
              z: p.h + 0.5,
              scaleOf: (q) => 5 + (Math.abs(q[2]) % 2),
              name: 'battersea_power_station:roof_trees',
            }),
          );
        }
      } else {
        // outer turbine halls / switch houses: brick to 24 m, set-back glazed top storeys
        const top = p.h;
        const brickTop = top - 6;
        block(ring, 0, brickTop - 1.4, brickWall, null, { bay: 4, storey: 6 });
        kit.cornice(batch, brickDark, ring, brickTop - 1.4, {
          height: 1.0,
          projection: 0.4,
          steps: 2,
        });
        kit.walls(batch, brickPlain, [[ring]], brickTop - 0.4, brickTop, {});
        kit.cornice(batch, ivory, ring, brickTop - 0.15, { height: 0.25, projection: 0.45 });
        kit.cap(batch, roofDeck, [[ring]], brickTop);
        const setb = kit.offsetRing(ring, -1.8);
        block(setb, brickTop, top, kit.mat('#3b4045', { roughness: 0.5 }), roofGarden);
        kit.cornice(batch, kit.mat('#5b5f62'), setb, top - 0.4, { height: 0.4, projection: 0.6 });
        kit.windowGrid(batch, setb, brickTop + 0.35, 2, 2.95, {
          width: 2.9,
          height: 2.5,
          bay: 3.5,
          margin: 0.6,
          glass: kit.mat('glass'),
          frame: frameM,
          sill: kit.mat('#5b5f62'),
          head: 'none',
          bars: 1,
          depth: 0.16,
        });
        // terrace balustrade along the brick parapet
        kit.balustrade(
          batch,
          frameM,
          [...kit.offsetRing(ring, -0.3), kit.offsetRing(ring, -0.3)[0]],
          brickTop,
          {
            height: 1.1,
            spacing: 1.2,
          },
        );
        // tall window strips with fluted piers between them on the long elevations
        edges(ring, (a, q, len) => {
          if (len < 12) return;
          const n = Math.floor(len / 9.5);
          for (let i = 0; i < n; i++) {
            const t0 = (len - n * 9.5) / 2 + i * 9.5;
            const [x0, y0] = along(a, q, t0);
            const [x1, y1] = along(a, q, t0 + 9.5);
            // fluted pier pair (2.4 m) at the bay start
            const [px0, py0] = along(a, q, t0 + 0.2);
            const [px1, py1] = along(a, q, t0 + 2.6);
            ribs([px0, py0], [px1, py1], 1.4, brickTop - 1.4, {
              spacing: 0.6,
              width: 0.32,
              m: 0.1,
            });
            const [wx0, wy0] = along(a, q, t0 + 3.2, 0.1);
            const [wx1, wy1] = along(a, q, t0 + 9.0, 0.1);
            const endWall = Math.abs((q[1] - a[1]) / len) > 0.9;
            strip([wx0, wy0], [wx1, wy1], endWall ? 9.5 : 6, brickTop - 3, {
              count: 2,
              width: 2.2,
              margin: 0.3,
              panel: 4,
            });
            (void x0, y0, x1, y1);
          }
        });
      }
    }

    // Stepped corner (wash) towers with deep vertical fluting and ziggurat tops.
    for (const p of towers) {
      const ring = p.ring;
      kit.cornice(batch, brickDark, ring, 0, { height: 1.4, projection: 0.4 });
      block(ring, 0, p.h - 6, brickWall, null, { bay: 4, storey: 6 });
      edges(ring, (a, q) =>
        ribs(a, q, 1.4, p.h - 7, { spacing: 0.9, depth: 0.3, width: 0.38, m: 0.5 }),
      );
      // corner piers proud of the faces
      for (const c of ring) kit.box(batch, brickPlain, c[0], c[1], 0, 1.6, 1.6, p.h - 6.5, 0);
      kit.cornice(batch, brickDark, ring, p.h - 7, { height: 1.0, projection: 0.5, steps: 2 });
      // three set-back tiers, each fluted
      let tierRing = ring;
      const tiers = [
        [p.h - 6, p.h - 3.6, -0.6],
        [p.h - 3.6, p.h - 1.6, -1.4],
        [p.h - 1.6, p.h, -2.2],
      ];
      for (const [z0, z1, off] of tiers) {
        tierRing = kit.offsetRing(ring, off);
        block(tierRing, z0, z1, brickPlain, brickDark);
        edges(tierRing, (a, q) =>
          ribs(a, q, z0, z1 - 0.25, { spacing: 0.6, depth: 0.15, width: 0.3 }),
        );
      }
      // tall slit windows in the tower faces
      edges(ring, (a, q, len) => {
        if (len < 8) return;
        strip(
          ...[along(a, q, len / 2 - 1.2, 0.32), along(a, q, len / 2 + 1.2, 0.32)].map((v) => [
            v[0],
            v[1],
          ]),
          12,
          p.h - 12,
          {
            count: 1,
            width: 1.4,
            margin: 0.2,
            panel: 5,
            bars: 1,
          },
        );
      });
    }

    // Four ivory fluted chimneys on stepped concrete plinths.
    const flute = (r0, r1, z0, z1, flutes = 24, depth = 0.05) => {
      const seg = flutes * 4;
      const geo = new THREE.CylinderGeometry(r1, r0, z1 - z0, seg, 1, true);
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i),
          z = pos.getZ(i);
        const th = Math.atan2(z, x);
        const k = 1 - depth * (0.5 + 0.5 * Math.cos(flutes * th));
        pos.setX(i, x * k);
        pos.setZ(i, z * k);
      }
      // texture: v repeats every 12 m of height
      const uv = geo.attributes.uv;
      for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 4, (uv.getY(i) * (z1 - z0)) / 12);
      geo.rotateX(Math.PI / 2);
      return geo;
    };
    for (const p of chimneys) {
      const [cx, cy] = centroid(p.ring);
      let Rm = 0;
      for (const q of p.ring) Rm = Math.max(Rm, Math.hypot(q[0] - cx, q[1] - cy));
      const Rb = Math.min(Math.max(Rm, 4), 4.6);
      const zt = 55; // tower top
      // square stepped plinth: brick, then two concrete tiers
      kit.box(batch, brickPlain, cx, cy, zt, Rb * 2.7, Rb * 2.7, 1.2, 0);
      kit.box(batch, ivory, cx, cy, zt + 1.2, Rb * 2.5, Rb * 2.5, 1.8, 0);
      kit.box(batch, ivory, cx, cy, zt + 3.0, Rb * 2.28, Rb * 2.28, 0.6, 0);
      // moulded column base (torus / scotia / fillet)
      latheB(
        ivory,
        [
          [0, 0],
          [Rb * 1.12, 0],
          [Rb * 1.12, 0.6],
          [Rb * 1.08, 1.0],
          [Rb * 1.12, 1.4],
          [Rb * 1.04, 1.9],
          [Rb * 0.98, 2.2],
          [Rb * 1.03, 2.6],
          [Rb * 1.0, 3.0],
        ],
        cx,
        cy,
        zt + 3.6,
      );
      const zs = zt + 6.6,
        ze = p.h - 4.2,
        Rt = Rb * 0.86;
      batch.addGeometry(chimMat, flute(Rb, Rt, zs, ze), m4.makeTranslation(cx, cy, (zs + ze) / 2));
      // capital: necking ring, plain frieze, projecting cornice and lip
      const capProfile = [
        [Rt * 0.98, 0],
        [Rt * 1.05, 0.15],
        [Rt * 1.05, 0.55],
        [Rt * 0.99, 0.7],
        [Rt * 0.99, 2.6],
        [Rt * 1.08, 2.9],
        [Rt * 1.12, 3.4],
        [Rt * 1.12, 3.9],
        [Rt * 1.02, 4.2],
        [Rt * 0.86, 4.2],
        [Rt * 0.86, 2.0],
      ];
      latheB(ivory, capProfile, cx, cy, ze);
      // dark flue inside the rim
      put(kit.mat('#141516'), new THREE.CircleGeometry(Rt * 0.86, 24), cx, cy, ze + 2.05);
      // inspection ladder up the shaft (on the outward face)
      const out = Math.atan2(cy, cx);
      const lx = Math.cos(out),
        ly = Math.sin(out);
      for (const s of [-0.25, 0.25]) {
        const ox = -ly * s,
          oy = lx * s;
        const rl = (Rb + Rt) / 2 + 0.12;
        kit.box(
          batch,
          kit.mat('#8d9090'),
          cx + lx * rl + ox,
          cy + ly * rl + oy,
          zs,
          0.06,
          0.06,
          ze - zs,
          0,
        );
      }
      // Lift 109: circular glass capsule rising from the north-west chimney (u > 0, v > 0)
      if (cx > 0 && cy > 0) {
        const zc = p.h;
        put(
          kit.mat('#9fb6c4', { roughness: 0.1, metalness: 0.3, transparent: true, opacity: 0.6 }),
          R(1.6, zc, zc + 4.4),
          cx,
          cy,
          zc + 2.2,
        );
        put(frameM, R(1.75, 0, 0.3), cx, cy, zc + 4.5);
        put(frameM, R(1.75, 0, 0.3), cx, cy, zc + 0.15);
        for (let k = 0; k < 6; k++) {
          const t = (k * Math.PI) / 3;
          kit.box(
            batch,
            frameM,
            cx + Math.cos(t) * 1.62,
            cy + Math.sin(t) * 1.62,
            zc,
            0.12,
            0.12,
            4.6,
            t,
          );
        }
        put(
          kit.mat('#d9d6cf'),
          new THREE.CylinderGeometry(0.4, 1.8, 0.8, 16).rotateX(Math.PI / 2),
          cx,
          cy,
          zc + 5,
        );
      }
    }

    // ---------------------------------------------------------------- entrances
    // River (north) and Electric Boulevard (south) entrances to Turbine Halls A and B:
    // glazed screens, steel-and-glass canopies and signage, on the end walls of the halls.
    for (const p of blocks.filter((q) => q.h < 45 && Math.abs(kit.ringArea(q.ring)) > 300)) {
      edges(p.ring, (a, q, len) => {
        const [mx, my] = [(a[0] + q[0]) / 2, (a[1] + q[1]) / 2];
        const ux = (q[0] - a[0]) / len,
          uy = (q[1] - a[1]) / len;
        const nx = uy,
          ny = -ux;
        // end walls face +u / -u
        if (Math.abs(nx) < 0.9 || len < 18) return;
        const ang = Math.atan2(uy, ux);
        const W0 = Math.min(14, len - 6);
        kit.box(batch, glass, mx + nx * 0.1, my + ny * 0.1, 0, W0, 0.2, 5.6, ang);
        for (let k = 0; k <= 7; k++) {
          const t = -W0 / 2 + (k * W0) / 7;
          kit.box(
            batch,
            frameM,
            mx + ux * t + nx * 0.25,
            my + uy * t + ny * 0.25,
            0,
            0.14,
            0.2,
            5.6,
            ang,
          );
        }
        kit.box(batch, frameM, mx + nx * 0.25, my + ny * 0.25, 2.8, W0, 0.2, 0.12, ang);
        // canopy on slim posts
        kit.box(
          batch,
          kit.mat('#9fb6c4', { roughness: 0.1, metalness: 0.3 }),
          mx + nx * 2.6,
          my + ny * 2.6,
          6.1,
          W0 + 2,
          5,
          0.12,
          ang,
        );
        kit.box(batch, frameM, mx + nx * 2.6, my + ny * 2.6, 5.85, W0 + 2.2, 5.2, 0.25, ang);
        for (const s of [-1, 1])
          kit.box(
            batch,
            frameM,
            mx + ux * s * (W0 / 2) + nx * 4.8,
            my + uy * s * (W0 / 2) + ny * 4.8,
            0,
            0.25,
            0.25,
            5.9,
            ang,
          );
        kit.box(batch, sign, mx + nx * 0.3, my + ny * 0.3, 7.0, 12, 0.12, 1.5, ang);
        // forecourt paving
        kit.box(batch, paving, mx + nx * 6, my + ny * 6, 0, len - 2, 12, 0.06, ang);
      });
    }

    // ---------------------------------------------------------------- surroundings
    // Restored coal jetty on the river (cranes removed in 2014) and the riverside walk.
    const RIVER = 169;
    const jetty = [
      [RIVER + 1, -62],
      [RIVER + 11, -62],
      [RIVER + 11, 62],
      [RIVER + 1, 62],
    ];
    kit.box(batch, kit.mat('#8d8a83'), RIVER + 6, 0, 0.9, 10, 124, 0.5, 0);
    kit.box(batch, kit.mat('#6c6761'), RIVER + 6, 0, 0.6, 10.4, 124.4, 0.3, 0);
    for (const [a0, b0] of [
      [RIVER + 1.5, -40],
      [RIVER + 1.5, 40],
    ])
      kit.box(batch, kit.mat('#8d8a83'), (RIVER + a0) / 2, b0, 0.9, a0 - RIVER + 1, 6, 0.5, 0);
    for (let v = -60; v <= 60; v += 6)
      for (const u of [RIVER + 1.6, RIVER + 10.4])
        put(kit.mat('#4a4540'), R(0.35, -1.5, 0.6), u, v, -0.45);
    kit.balustrade(batch, black, [jetty[1], jetty[2]], 1.4, { height: 1.1, spacing: 1.5 });
    kit.balustrade(
      batch,
      black,
      [
        [RIVER - 0.4, -80],
        [RIVER - 0.4, 80],
      ],
      0,
      { height: 1.1, spacing: 1.5 },
    );
    const lamps = [],
      benches = [];
    for (let v = -75; v <= 75; v += 18) {
      lamps.push([RIVER - 1.2, v, -Math.PI / 2]);
      benches.push([RIVER - 3.2, v + 9, -Math.PI / 2]);
    }
    for (let v = -54; v <= 54; v += 18) lamps.push([RIVER + 10.4, v, Math.PI / 2]);
    // lamps along the north forecourt
    for (const v of [-70, -45, 45, 70]) lamps.push([90, v, Math.PI / 2]);
    const jl = lamps.filter((q) => q[0] > RIVER),
      gl = lamps.filter((q) => q[0] <= RIVER);
    g.add(placeAssets('street_lamp', gl, { name: 'battersea_power_station:lamps' }));
    g.add(placeAssets('street_lamp', jl, { z: 1.4, name: 'battersea_power_station:jetty_lamps' }));
    g.add(placeAssets('bench', benches, { name: 'battersea_power_station:benches' }));

    g.add(batch.toGroup('battersea_power_station'));
    g.position.set(CX, CY, 0);
    g.rotation.z = A;
    return g;
  },
};
