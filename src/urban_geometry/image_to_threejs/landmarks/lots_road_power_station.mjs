// Lots Road Power Station (1902-05, the Underground Electric Railways' generating
// station on Chelsea Creek), converted by Farrells into "Powerhouse", Chelsea
// Waterfront (completed 2024). Steel-framed red-brick halls with terracotta
// detailing and tall arched window bays, now glazed three storeys high above a
// ground-floor arcade cut between the columns; the turbine hall is a 100 m
// top-lit atrium, and two restored ~84 m chimneys (glass-capped) survive of the
// original four.
export default {
  id: 'lots_road_power_station',
  name: 'Lots Road Power Station (Powerhouse)',
  claims: ['209e903b-012d-4744-89a5-4249311fcea8'],
  references: [
    {
      title: 'Lots Road Power Station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Lots_Road_Power_Station',
      used_for: 'history, four original chimneys of which two remain',
    },
    {
      title: 'Powerhouse, Chelsea Waterfront - Architecture Today',
      url: 'https://architecturetoday.co.uk/?p=380395',
      used_for: 'Farrells conversion, two restored ~84 m chimneys, 260 apartments',
    },
    {
      title: 'Lots Road Power Station Development - Buro Happold',
      url: 'https://www.burohappold.com/projects/lots-road-power-station/',
      used_for: 'existing fabric retained as facade, glass-capped chimneys',
    },
    {
      title: 'From power station to modern living - The Spaces',
      url: 'https://thespaces.com/chelsea-powerhouse-apartments-london/',
      used_for:
        'terracotta detailing, ground-level arcade, three-storey glazed openings, 100 m atrium',
    },
    {
      title: "The history behind London's latest power-station conversion - Country Life",
      url: 'https://countrylife.co.uk/property/the-history-behind-londons-latest-power-station-conversion-267648',
      used_for: 'large red-brick structure with arched windows',
    },
  ],
  notes:
    'Overture footprint (named "Metropolitan Building", h 85 m = chimney height). Eaves (28 m), twin pitched roofs ' +
    '(rise 7.5 m), 7 m bay rhythm with pilasters, arcade/arched-window sizes, terracotta courses, attic windows, ' +
    'chimney banding and corbelled caps are estimates from descriptions. Street lamps, plane trees and benches ' +
    'are reused assets placed schematically. ' +
    '(glazed over the north turbine-hall atrium), bay rhythm and chimney positions (two middle positions of the ' +
    'original row of four, on the creek side) are estimates.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ca = Math.cos(frame.angle),
      sa = Math.sin(frame.angle);
    const W = (u, v) => [frame.cx + u * ca - v * sa, frame.cy + u * sa + v * ca];
    const EAVE = 28;
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = frame.angle) => {
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));
      geo.dispose();
    };

    const brick = kit.paintedMaterial(
      'lots_road_power_station:brick2',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#9a4e3a';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.913);
        for (let y = 0; y < h; y += 2)
          for (let x = (y / 2) % 2 ? 0 : 3; x < w; x += 6) {
            const k = 0.86 + r() * 0.24;
            c.fillStyle = `rgb(${(156 * k) | 0},${(80 * k) | 0},${(58 * k) | 0})`;
            c.fillRect(x, y, 5, 1);
          }
      },
      { roughness: 0.9 },
    );
    const brickPlain = kit.mat('#93503c', { roughness: 0.92 });
    const brickDark = kit.mat('#7a3f30', { roughness: 0.92 });
    const terracotta = kit.mat('#c98a5e', { roughness: 0.75 });
    const roofM = kit.roof('slate', 1);
    const glassRoof = kit.mat('#8aa0ad', { roughness: 0.15, metalness: 0.3 });
    const glass = kit.mat('#3b4b57', { roughness: 0.15, metalness: 0.3 });
    const frameM = kit.mat('#2b2d2f', { roughness: 0.5, metalness: 0.4 });
    const shopGlass = kit.mat('dark_glass');

    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    // Walls, plinth, terracotta string courses, eaves cornice and parapet.
    kit.walls(batch, brick, [[ring]], 0, EAVE, { bay: 7, storey: 7 });
    kit.cornice(batch, brickDark, ring, 0, { height: 1.0, projection: 0.25 });
    kit.cornice(batch, terracotta, ring, 5.6, { height: 0.5, projection: 0.3, steps: 2 });
    kit.cornice(batch, terracotta, ring, 21.4, { height: 0.4, projection: 0.25 });
    kit.cornice(batch, terracotta, ring, EAVE - 1.2, { height: 1.2, projection: 0.6, steps: 3 });

    // Bays: brick pilasters; ground-floor arcade of round arches; three-storey
    // glazed arched openings above with steel transoms and mullions.
    const strip = (a, q, z0, z1, opts) => {
      const n = 3;
      const ph = (z1 - z0) / n;
      for (let k = 0; k < n; k++)
        kit.windowRow(batch, a, q, z0 + k * ph, {
          glass,
          frame: frameM,
          sill: k === 0 ? terracotta : frameM,
          head: k === n - 1 ? 'arch' : 'none',
          bars: 2,
          depth: 0.2,
          ...opts,
          height: k === n - 1 ? ph - opts.width / 2 - 0.1 : ph - 0.12,
        });
    };
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      if (len < 10) continue;
      const ux = (q[0] - a[0]) / len,
        uy = (q[1] - a[1]) / len;
      const nx = uy,
        ny = -ux,
        ang = Math.atan2(uy, ux);
      const n = Math.max(1, Math.round(len / 7));
      const bay = len / n;
      const long = len > 80;
      for (let i = 0; i <= n; i++) {
        const t = i * bay;
        const px = a[0] + ux * t + nx * 0.3,
          py = a[1] + uy * t + ny * 0.3;
        kit.box(batch, brickPlain, px, py, 1.0, 1.3, 0.6, EAVE - 2.2, ang);
        kit.box(batch, terracotta, px, py, EAVE - 2.6, 1.5, 0.75, 0.5, ang);
      }
      for (let i = 0; i < n; i++) {
        const t0 = i * bay,
          t1 = (i + 1) * bay;
        const A0 = [a[0] + ux * (t0 + 0.7), a[1] + uy * (t0 + 0.7)],
          A1 = [a[0] + ux * (t1 - 0.7), a[1] + uy * (t1 - 0.7)];
        if (long) {
          // ground arcade
          kit.windowRow(batch, A0, A1, 0.3, {
            count: 1,
            width: bay - 2.6,
            height: 3.2,
            margin: 0,
            glass: shopGlass,
            frame: frameM,
            sill: brickDark,
            head: 'arch',
            bars: 1,
            depth: 0.3,
          });
          strip(A0, A1, 7.2, 20.8, { count: 1, width: bay - 3.0, margin: 0 });
          // attic windows between the string course and the cornice
          kit.windowRow(batch, A0, A1, 22.6, {
            count: 2,
            width: 1.2,
            height: 2.2,
            margin: 0.8,
            glass,
            frame: frameM,
            sill: terracotta,
            head: 'segment',
            bars: 1,
          });
        } else {
          // gable ends: tall arched windows over a pair of entrances
          strip(A0, A1, 7.2, 24.5, { count: 1, width: bay - 3.2, margin: 0 });
          kit.windowRow(batch, A0, A1, 0.3, {
            count: 1,
            width: 2.6,
            height: 3.8,
            margin: 0,
            glass: shopGlass,
            frame: frameM,
            sill: brickDark,
            head: 'arch',
            bars: 1,
          });
        }
      }
    }

    // Twin pitched roofs along the long axis: glazed atrium (north) and boiler house (south).
    const e = kit.orientedExtent(ring, frame.angle);
    const vm = (e.v0 + e.v1) / 2;
    const northIsV1 = e.at((e.u0 + e.u1) / 2, e.v1, 0)[1] > e.at((e.u0 + e.u1) / 2, e.v0, 0)[1];
    const vN = northIsV1 ? e.v1 : e.v0,
      vS = northIsV1 ? e.v0 : e.v1,
      sN = northIsV1 ? 1 : -1;
    const halves = [
      [Math.min(vm, vN), Math.max(vm, vN), glassRoof],
      [Math.min(vm, vS), Math.max(vm, vS), roofM],
    ];
    const RISE = 7.5;
    for (const [v0, v1, m] of halves) {
      const r = [e.at(e.u0, v0, 0), e.at(e.u1, v0, 0), e.at(e.u1, v1, 0), e.at(e.u0, v1, 0)].map(
        ([x, y]) => [x, y],
      );
      kit.pitchedRoof(batch, m, brick, r, frame.angle, EAVE, RISE, 'gabled', {
        overhang: 0.2,
        storey: 7,
      });
      // stepped terracotta gable copings
      const vc = (v0 + v1) / 2,
        hw = (v1 - v0) / 2;
      for (const u of [e.u0 - 0.1, e.u1 + 0.1])
        for (const sgn of [-1, 1]) {
          const p0 = e.at(u, vc + sgn * (hw + 0.3), EAVE),
            p1 = e.at(u, vc, EAVE + RISE + 0.3);
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]);
          const geo = new THREE.BoxGeometry(1.0, len, 0.5);
          const mm = new THREE.Matrix4().compose(
            new THREE.Vector3((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2 + 0.2),
            new THREE.Quaternion().setFromUnitVectors(
              new THREE.Vector3(0, 1, 0),
              new THREE.Vector3(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]).normalize(),
            ),
            new THREE.Vector3(1, 1, 1),
          );
          batch.addGeometry(terracotta, geo, mm);
          geo.dispose();
        }
      // ridge capping
      const [rx, ry] = e.at((e.u0 + e.u1) / 2, vc, 0);
      kit.box(
        batch,
        m === roofM ? kit.mat('#3d4247') : frameM,
        rx,
        ry,
        EAVE + RISE - 0.1,
        e.u1 - e.u0,
        0.5,
        0.35,
        frame.angle,
      );
    }
    kit.cap(batch, brickPlain, [[ring]], EAVE - 0.05);
    // atrium glazing bars (rafters both slopes, and purlins)
    const vR = (vN + vm) / 2;
    const bar = (p0, p1, w) => {
      const a = new THREE.Vector3(...p0),
        bq = new THREE.Vector3(...p1);
      const mm = new THREE.Matrix4().compose(
        a.clone().add(bq).multiplyScalar(0.5),
        new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          bq.clone().sub(a).normalize(),
        ),
        new THREE.Vector3(1, 1, 1),
      );
      batch.addGeometry(frameM, new THREE.BoxGeometry(w, a.distanceTo(bq), w), mm);
    };
    for (let u = e.u0 + 3; u < e.u1 - 1; u += 3) {
      bar(e.at(u, vN + 0.1 * sN, EAVE + 0.08), e.at(u, vR, EAVE + RISE + 0.08), 0.16);
      bar(e.at(u, vR, EAVE + RISE + 0.08), e.at(u, vm, EAVE + 0.08), 0.16);
    }
    for (const f of [0.33, 0.66]) {
      for (const v of [vN + (vR - vN) * f, vm + (vR - vm) * f]) {
        const [x, y] = e.at((e.u0 + e.u1) / 2, v, 0);
        kit.box(batch, frameM, x, y, EAVE + RISE * f + 0.05, e.u1 - e.u0, 0.15, 0.15, frame.angle);
      }
    }
    // rooflights on the slate (boiler house) roof
    for (let u = e.u0 + 6; u < e.u1 - 4; u += 7) {
      const v = vS + ((vS + vm) / 2 - vS) * 0.55;
      const [x, y] = e.at(u, v, 0);
      kit.box(batch, glassRoof, x, y, EAVE + RISE * 0.55 - 0.55, 3.2, 1.8, 1.0, frame.angle);
    }

    // Two restored brick chimneys: moulded brick bases, banded shafts, corbelled
    // caps and glass tops.
    const vC = (vS + vm) / 2;
    const um = (e.u0 + e.u1) / 2,
      L = e.u1 - e.u0;
    for (const u of [um - L * 0.12, um + L * 0.12]) {
      const [x, y] = e.at(u, vC, 0);
      const z0 = EAVE + 5,
        z1 = b.h;
      kit.box(batch, brickPlain, x, y, EAVE - 1, 11, 11, 7, frame.angle);
      kit.box(batch, terracotta, x, y, EAVE + 6, 11.6, 11.6, 0.6, frame.angle);
      kit.box(batch, brickPlain, x, y, EAVE + 6.6, 10, 10, 1.6, frame.angle);
      put(
        brickDark,
        new THREE.CylinderGeometry(4.5, 4.7, 1.6, 32).rotateX(Math.PI / 2),
        x,
        y,
        z0 + 3.6,
        0,
      );
      const shaft = new THREE.CylinderGeometry(3.5, 4.3, z1 - z0 - 4.4, 32, 1, true).rotateX(
        Math.PI / 2,
      );
      put(brickPlain, shaft, x, y, (z0 + 4.4 + z1) / 2, 0);
      const rAt = (z) => 4.3 - 0.8 * ((z - z0 - 4.4) / (z1 - z0 - 4.4));
      for (const z of [z0 + 20, z0 + 34, z1 - 9, z1 - 6, z1 - 3.5]) {
        const rr = rAt(z) + 0.12;
        put(
          kit.mat('#3a3330'),
          new THREE.CylinderGeometry(rr, rr, 0.8, 32, 1, true).rotateX(Math.PI / 2),
          x,
          y,
          z,
          0,
        );
      }
      // corbelled cap
      const capG = new THREE.LatheGeometry(
        [
          [3.55, 0],
          [3.9, 0.4],
          [3.9, 0.9],
          [4.15, 1.3],
          [4.15, 1.9],
          [3.4, 1.9],
        ].map(([r, h]) => new THREE.Vector2(r, h)),
        32,
      ).rotateX(Math.PI / 2);
      put(brickDark, capG, x, y, z1 - 2.6, 0);
      put(
        kit.mat('#9fb6c4', { roughness: 0.1, metalness: 0.3 }),
        new THREE.CylinderGeometry(3.3, 3.4, 1.4, 32).rotateX(Math.PI / 2),
        x,
        y,
        z1 - 0.2,
        0,
      );
      put(
        frameM,
        new THREE.CylinderGeometry(3.45, 3.45, 0.15, 32).rotateX(Math.PI / 2),
        x,
        y,
        z1 + 0.5,
        0,
      );
    }

    // Street frontage: lamps and trees along the north (Lots Road) side, benches on
    // the creek-side walk.
    const lamps = [],
      trees = [],
      benches = [];
    for (let u = e.u0 + 6; u < e.u1; u += 16) {
      const [lx, ly] = e.at(u, vN + sN * 3.2, 0);
      lamps.push([lx, ly, frame.angle + (sN > 0 ? 0 : Math.PI)]);
      const [tx, ty] = e.at(u + 8, vN + sN * 4.2, 0);
      trees.push([tx, ty, u]);
      const [bx, by] = e.at(u + 4, vS - sN * 4, 0);
      benches.push([bx, by, frame.angle + (sN > 0 ? 0 : Math.PI)]);
    }
    g.add(placeAssets('street_lamp', lamps, { name: 'lots_road_power_station:lamps' }));
    g.add(
      placeAssets('london_plane', trees, {
        scaleOf: (p) => 9 + (Math.abs(p[2]) % 3),
        name: 'lots_road_power_station:trees',
      }),
    );
    g.add(placeAssets('bench', benches, { name: 'lots_road_power_station:benches' }));

    g.add(batch.toGroup('lots_road_power_station'));
    return g;
  },
};
