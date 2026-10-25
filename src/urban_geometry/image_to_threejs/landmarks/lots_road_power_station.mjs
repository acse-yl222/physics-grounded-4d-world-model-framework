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
    '(glazed over the north turbine-hall atrium), bay rhythm and chimney positions (two middle positions of the ' +
    'original row of four, on the creek side) are estimates.',
  build({ THREE, kit, buildings, frame }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ca = Math.cos(frame.angle),
      sa = Math.sin(frame.angle);
    const W = (u, v) => [frame.cx + u * ca - v * sa, frame.cy + u * sa + v * ca];
    const EAVE = 28;

    const brick = kit.paintedMaterial(
      'lots_road_power_station:brick',
      512,
      512,
      (c, w, h) => {
        // tile: 4 bays (28 m) x 28 m
        c.fillStyle = '#9a4e3a';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.913);
        for (let y = 0; y < h; y += 4)
          for (let x = (y / 4) % 2 ? 0 : 5; x < w; x += 10) {
            const k = 0.86 + r() * 0.24;
            c.fillStyle = `rgb(${(156 * k) | 0},${(80 * k) | 0},${(58 * k) | 0})`;
            c.fillRect(x, y, 9, 3);
          }
        const terracotta = '#c98a5e';
        for (let k = 0; k < 4; k++) {
          const x = k * 128;
          // ground arcade
          c.fillStyle = '#2c2a28';
          c.fillRect(x + 22, h - 104, 84, 104);
          c.beginPath();
          c.arc(x + 64, h - 104, 42, Math.PI, 0);
          c.fill();
          // three-storey glazed arched openings
          c.fillStyle = terracotta;
          c.fillRect(x + 26, 70, 76, 300);
          c.beginPath();
          c.arc(x + 64, 72, 38, Math.PI, 0);
          c.fill();
          c.fillStyle = '#3b4b57';
          c.fillRect(x + 32, 76, 64, 290);
          c.beginPath();
          c.arc(x + 64, 78, 32, Math.PI, 0);
          c.fill();
          c.fillStyle = '#8b9aa3';
          for (let y = 120; y < 366; y += 46) c.fillRect(x + 32, y, 64, 4);
          c.fillRect(x + 62, 46, 4, 320);
          // pilaster
          c.fillStyle = 'rgba(60,25,15,0.25)';
          c.fillRect(x, 0, 12, h);
        }
        c.fillStyle = terracotta;
        c.fillRect(0, h - 140, w, 10);
        c.fillRect(0, 0, w, 16);
        c.fillRect(0, 30, w, 6);
      },
      { roughness: 0.9 },
    );
    const brickPlain = kit.mat('#93503c', { roughness: 0.92 });
    const roofM = kit.roof('slate', 1);
    const glassRoof = kit.mat('#8aa0ad', { roughness: 0.15, metalness: 0.3 });

    kit.walls(batch, brick, b.polys, 0, EAVE, { bay: 7, storey: 14 });

    // Twin pitched roofs along the long axis: glazed atrium (north) and boiler house (south).
    const ring = b.polys[0][0];
    const e = kit.orientedExtent(ring, frame.angle);
    const vm = (e.v0 + e.v1) / 2;
    // north side (Lots Road) = turbine hall atrium; south side (creek) = boiler house
    const northIsV1 = e.at((e.u0 + e.u1) / 2, e.v1, 0)[1] > e.at((e.u0 + e.u1) / 2, e.v0, 0)[1];
    const vN = northIsV1 ? e.v1 : e.v0,
      vS = northIsV1 ? e.v0 : e.v1,
      sN = northIsV1 ? 1 : -1;
    const halves = [
      [Math.min(vm, vN), Math.max(vm, vN), glassRoof],
      [Math.min(vm, vS), Math.max(vm, vS), roofM],
    ];
    for (const [v0, v1, m] of halves) {
      const r = [e.at(e.u0, v0, 0), e.at(e.u1, v0, 0), e.at(e.u1, v1, 0), e.at(e.u0, v1, 0)].map(
        ([x, y]) => [x, y],
      );
      kit.pitchedRoof(batch, m, brick, r, frame.angle, EAVE, 7.5, 'gabled', {
        overhang: 0.2,
        storey: 14,
      });
    }
    kit.cap(batch, brickPlain, b.polys, EAVE - 0.05);
    // atrium glazing bars
    for (let u = e.u0 + 6; u < e.u1 - 3; u += 6) {
      const p0 = e.at(u, vN + 0.2 * sN, EAVE),
        p1 = e.at(u, vm, EAVE + 7.5);
      const a = new THREE.Vector3(...p0),
        bq = new THREE.Vector3(...p1);
      const len = a.distanceTo(bq);
      const m = new THREE.Matrix4().compose(
        a.clone().add(bq).multiplyScalar(0.5),
        new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          bq.clone().sub(a).normalize(),
        ),
        new THREE.Vector3(1, 1, 1),
      );
      batch.addGeometry(kit.mat('dark_steel'), new THREE.BoxGeometry(0.3, len, 0.3), m);
    }

    // Two restored brick chimneys with dark bands and glass caps.
    const vC = (vS + vm) / 2;
    const um = (e.u0 + e.u1) / 2,
      L = e.u1 - e.u0;
    const m4 = new THREE.Matrix4();
    for (const u of [um - L * 0.12, um + L * 0.12]) {
      const [x, y] = e.at(u, vC, 0);
      const z0 = EAVE + 5,
        z1 = b.h;
      kit.box(batch, brickPlain, x, y, EAVE - 1, 11, 11, 8, frame.angle);
      const shaft = new THREE.CylinderGeometry(3.5, 4.3, z1 - z0, 24, 1, true).rotateX(Math.PI / 2);
      batch.addGeometry(brickPlain, shaft, m4.makeTranslation(x, y, (z0 + z1) / 2));
      for (const z of [z1 - 6, z1 - 3.5]) {
        const band = new THREE.CylinderGeometry(3.85, 3.85, 1.2, 24, 1, true).rotateX(Math.PI / 2);
        batch.addGeometry(kit.mat('#3a3330'), band, m4.makeTranslation(x, y, z));
      }
      const capG = new THREE.CylinderGeometry(3.4, 3.6, 1.6, 24).rotateX(Math.PI / 2);
      batch.addGeometry(kit.mat('glass'), capG, m4.makeTranslation(x, y, z1 - 0.8));
    }

    g.add(batch.toGroup('lots_road_power_station'));
    return g;
  },
};
