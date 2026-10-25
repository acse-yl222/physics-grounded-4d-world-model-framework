// Battersea Power Station (J. Theo Halliday and Sir Giles Gilbert Scott, engineer
// Leonard Pearce; A station 1929-35, B station 1937-41, completed 1955). Steel frame
// clad in brown Blockley brick with Art Deco ("jazz modern") vertical fluting, a
// tall central boiler house flanked by the lower turbine halls / switch houses,
// stepped brick corner towers and four white pre-cast concrete fluted chimneys
// (~103 m). Since the 2022 redevelopment the outer blocks carry glazed apartment
// storeys and the boiler house roof holds sky villas around a garden square.
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
  ],
  notes:
    'Massing from the Overture parts (30 m outer halls, 50 m boiler house, 55 m corner towers, 103 m chimneys). ' +
    'Brick fluting, window strips and stepped tower tiers are proportioned from general photo knowledge, not measured; ' +
    'rooftop villas and glazed top storeys are schematic. Jetty cranes omitted.',
  build({ THREE, kit, buildings, frame }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = frame.angle;
    const brickC = '#8a5a40';

    const brickWall = kit.paintedMaterial(
      'battersea_power_station:brick',
      256,
      512,
      (c, w, h) => {
        // One tile = 4 bays x 2 "storeys" (16 m x 24 m): brick ground with vertical fluting.
        c.fillStyle = brickC;
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.371);
        for (let y = 0; y < h; y += 3)
          for (let x = (y / 3) % 2 ? 0 : 4; x < w; x += 8) {
            const k = 0.88 + r() * 0.2;
            c.fillStyle = `rgb(${(138 * k) | 0},${(90 * k) | 0},${(64 * k) | 0})`;
            c.fillRect(x, y, 7, 2);
          }
        for (let bay = 0; bay < 4; bay++) {
          const x0 = bay * (w / 4);
          // fluting: alternating light/dark vertical ribs
          for (let k = 0; k < 8; k++) {
            c.fillStyle = k % 2 ? 'rgba(0,0,0,0.16)' : 'rgba(255,230,200,0.08)';
            c.fillRect(x0 + 4 + k * 7, 0, 3, h);
          }
          // tall narrow recessed window strip
          c.fillStyle = '#2b2d30';
          c.fillRect(x0 + 22, 40, 20, h - 80);
          c.fillStyle = 'rgba(120,140,150,0.5)';
          for (let y = 40; y < h - 40; y += 24) c.fillRect(x0 + 22, y, 20, 2);
          c.fillRect(x0 + 31, 40, 2, h - 80);
        }
        // horizontal band courses
        c.fillStyle = 'rgba(40,20,10,0.35)';
        c.fillRect(0, 0, w, 6);
        c.fillRect(0, h - 10, w, 10);
      },
      { roughness: 0.9 },
    );
    const brickPlain = kit.mat(brickC, { roughness: 0.92 });
    const brickDark = kit.mat('#6e4632', { roughness: 0.92 });
    const white = kit.mat('#ecebe5', { roughness: 0.6 });
    const glass = kit.mat('dark_glass');
    const roofGarden = kit.mat('#5f7a4b', { roughness: 1 });
    const roofDeck = kit.mat('#9a948a', { roughness: 0.95 });
    const chimMat = kit.paintedMaterial(
      'battersea_power_station:chimney',
      256,
      64,
      (c, w, h) => {
        c.fillStyle = '#f0efea';
        c.fillRect(0, 0, w, h);
        for (let k = 0; k < 24; k++) {
          const x = (k * w) / 24;
          const grd = c.createLinearGradient(x, 0, x + w / 24, 0);
          grd.addColorStop(0, '#c9c8c2');
          grd.addColorStop(0.5, '#f7f6f2');
          grd.addColorStop(1, '#d6d5cf');
          c.fillStyle = grd;
          c.fillRect(x, 0, w / 24, h);
        }
      },
      { roughness: 0.55 },
    );

    const area = (ring) => Math.abs(kit.ringArea(ring));
    const centroid = (ring) => {
      let x = 0,
        y = 0;
      for (const p of ring) {
        x += p[0];
        y += p[1];
      }
      return [x / ring.length, y / ring.length];
    };
    const parts = b.parts ?? [];
    const chimneys = parts.filter((p) => p.minh >= 40);
    const towers = parts.filter((p) => p.minh < 40 && p.h >= 54);
    const blocks = parts.filter((p) => p.minh < 40 && p.h < 54);

    // Main brick volumes.
    for (const p of blocks) {
      const ring = p.polys[0][0];
      const isBoiler = p.h >= 45;
      const isCore = area(ring) < 300; // small stair tower block
      if (isBoiler || isCore) {
        kit.walls(batch, brickWall, p.polys, 0, p.h - 1.5, { bay: 4, storey: 12 });
        kit.walls(batch, brickDark, p.polys, p.h - 1.5, p.h, { bay: 4, storey: 12 });
        kit.cap(batch, roofDeck, p.polys, p.h);
        if (isBoiler) {
          // rooftop garden square ringed by low glazed sky villas
          const inner = kit.offsetRing(ring, -9);
          kit.cap(batch, roofGarden, [[inner]], p.h + 0.4);
          const villa = kit.offsetRing(ring, -2);
          kit.walls(batch, glass, [[villa]], p.h, p.h + 3.2, { bay: 4, storey: 12 });
          kit.walls(batch, glass, [[inner.slice().reverse()]], p.h, p.h + 3.2, {
            bay: 4,
            storey: 12,
          });
          kit.cap(
            batch,
            kit.mat('#6b6e70', { roughness: 0.8 }),
            [[villa, inner.slice().reverse()]],
            p.h + 3.2,
          );
        }
      } else {
        // outer halls / switch houses: brick to 24 m, set-back glazed top storeys
        const top = p.h;
        const brickTop = top - 6;
        kit.walls(batch, brickWall, p.polys, 0, brickTop, { bay: 4, storey: 12 });
        kit.walls(batch, brickDark, p.polys, brickTop - 1, brickTop, { bay: 4, storey: 12 });
        kit.cap(batch, roofDeck, p.polys, brickTop);
        const setb = kit.offsetRing(ring, -1.6);
        kit.walls(batch, kit.facade('glass', 1), [[setb]], brickTop, top, { bay: 3.6, storey: 3 });
        kit.cap(batch, roofGarden, [[setb]], top);
      }
    }

    // Stepped corner towers (chimney bases) with vertical fluting.
    for (const p of towers) {
      const ring = p.polys[0][0];
      kit.walls(batch, brickWall, p.polys, 0, p.h - 5, { bay: 4, storey: 12 });
      const t1 = kit.offsetRing(ring, -0.9);
      kit.walls(batch, brickPlain, [[t1]], p.h - 5, p.h - 2, {});
      const t2 = kit.offsetRing(ring, -1.8);
      kit.cap(batch, brickPlain, [[t1]], p.h - 2);
      kit.walls(batch, brickDark, [[t2]], p.h - 2, p.h, {});
      kit.cap(batch, roofDeck, [[t2]], p.h);
      kit.cap(batch, brickPlain, p.polys, p.h - 5);
    }

    // Four white fluted chimneys on stepped plinths.
    const m4 = new THREE.Matrix4();
    const cyl = (r0, r1, hgt, seg = 24) =>
      new THREE.CylinderGeometry(r1, r0, hgt, seg, 1, true).rotateX(Math.PI / 2);
    for (const p of chimneys) {
      const ring = p.polys[0][0];
      const [cx, cy] = centroid(ring);
      let R = 0;
      for (const q of ring) R = Math.max(R, Math.hypot(q[0] - cx, q[1] - cy));
      R = Math.min(Math.max(R, 4), 5);
      const z0 = 50;
      // stepped square plinth tiers
      const tiers = [
        [R * 2.9, z0, 5.5],
        [R * 2.55, z0 + 5.5, 2.2],
        [R * 2.25, z0 + 7.7, 1.6],
      ];
      tiers.forEach(([s, z, hh], k) =>
        kit.box(batch, k === 0 ? brickPlain : white, cx, cy, z, s, s, hh, ang),
      );
      // octagonal collar
      batch.addGeometry(
        white,
        new THREE.CylinderGeometry(R * 1.12, R * 1.12, 2.4, 8).rotateX(Math.PI / 2),
        m4.makeRotationZ(ang + Math.PI / 8).setPosition(cx, cy, z0 + 10.5),
      );
      // fluted shaft (tapering)
      const zs = z0 + 11.7,
        ze = p.h - 4.5;
      const shaft = cyl(R, R * 0.88, ze - zs, 32);
      batch.addGeometry(chimMat, shaft, m4.makeRotationZ(0).setPosition(cx, cy, (zs + ze) / 2));
      // capital band and rim
      batch.addGeometry(
        white,
        new THREE.CylinderGeometry(R * 0.98, R * 0.92, 3.2, 32).rotateX(Math.PI / 2),
        m4.makeRotationZ(0).setPosition(cx, cy, ze + 1.6),
      );
      batch.addGeometry(
        white,
        new THREE.CylinderGeometry(R * 1.02, R * 1.02, 1.3, 32).rotateX(Math.PI / 2),
        m4.makeRotationZ(0).setPosition(cx, cy, p.h - 0.65),
      );
      // dark flue opening
      batch.addGeometry(
        kit.mat('black'),
        new THREE.CircleGeometry(R * 0.82, 24),
        m4.makeRotationZ(0).setPosition(cx, cy, p.h + 0.02),
      );
    }

    g.add(batch.toGroup('battersea_power_station'));
    return g;
  },
};
