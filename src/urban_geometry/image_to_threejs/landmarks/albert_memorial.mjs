// Albert Memorial (Prince Consort National Memorial), Kensington Gardens
// (Sir George Gilbert Scott, opened 1872; statue by John Henry Foley, seated 1875-76).
// 54 m Gothic Revival ciborium: clustered polished granite columns at the corners
// carry four pointed arches under gables with gold-ground mosaics, corner pinnacles,
// a cross-gabled lead roof and a tiered, crocketed, gilded octagonal spire topped by a
// cross. The gilt bronze seated Prince Albert faces south towards the Royal Albert
// Hall. Square podium with the Parnassus frieze and the four Industrial Arts groups,
// broad granite steps on all sides and the four continent groups (Europe, Asia,
// Africa, America) at the outer corners.
export default {
  id: 'albert_memorial',
  name: 'Albert Memorial',
  claims: [
    '4807fb6d-2ebe-4de4-94ac-9122b798d3f8', // canopy
    'a8cfc47f-900b-451f-a15e-c92c0ef63be0', // America
    '6ff7d995-360f-4bc4-8d89-8ecb29b3d08b', // Africa
    'c8159e6a-0e6d-4454-ad80-950285fe166d', // Europe
    '93e65965-7e61-49fc-9473-1ff35f5b0360', // Asia
    '621d410b-ab5a-47cb-a78e-a7fdd28d9b5f', // low structure SE of the steps (unidentified)
    '7bdfa484-5fa2-47c9-87d8-414991b63209', // low structure SW of the steps (unidentified)
  ],
  references: [
    {
      title: 'Albert Memorial - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Albert_Memorial',
      used_for: 'Scott design, 1872 opening, seated gilt statue facing the Royal Albert Hall',
    },
    {
      title: 'The Albert Memorial - Google Arts & Culture',
      url: 'https://artsandculture.google.com/entity/m01j4pw',
      used_for:
        '176 ft (54 m) Gothic ciborium canopy; gilded bronze Albert by Foley; continent groups at the corners',
    },
    {
      title: 'Prince Consort National Memorial - Historic England listing',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1217741',
      used_for:
        'square paved podium, steps on all sides, clustered granite columns at the four corners, gables with pinnacles, mosaic and enamel',
    },
    {
      title: 'Victorian London - Albert Memorial',
      url: 'https://www.victorianlondon.org/buildings/albertmemorial.htm',
      used_for:
        'mass of gilt, mosaic and coloured stones; ornamented spire with a cross at the top',
    },
    {
      title: 'The Albert Memorial - A London Inheritance',
      url: 'https://alondoninheritance.com/london-monuments/albert-memorial-19th-century-world-view',
      used_for: 'octagonal grey-banded crocketed spire, gilded crown, angels round the spire base',
    },
  ],
  notes:
    'Placed on the Overture canopy footprint and the four continent-group footprints (orientation ~7 deg from the group layout). ' +
    'Step and podium dimensions, stage heights (arches, gables at ~24 m, spire 31-51 m, cross to 54 m) are proportioned from ' +
    'descriptions. Sculpture groups and the statue are blocky stand-ins (marble masses with an animal and figures; gilt seated ' +
    'figure); mosaics are painted suggestions. Two small unnamed 2 x 8 m strips ~35 m south-east/south-west of the memorial (identity unknown, generic extrusion gave 17 m towers in the park) are claimed and drawn as low granite plinths.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const granite = kit.mat('#8f7f7a', { roughness: 0.45 }),
      greyGranite = kit.mat('#a19d98', { roughness: 0.7 }),
      stone = kit.mat('#d9d0bf'),
      marble = kit.mat('#ece8df', { roughness: 0.6 }),
      lead = kit.mat('#5d6266', { roughness: 0.5, metalness: 0.35 }),
      gold = kit.mat('gold'),
      redStone = kit.mat('#9c5e52');
    const M4 = () => new THREE.Matrix4();
    const put = (geo, m, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const mat = M4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz),
        new THREE.Vector3(sx, sy, sz),
      );
      batch.addGeometry(m, geo, mat);
    };
    const B = (m, x, y, z0, w, d, h, a = 0) => kit.box(batch, m, x, y, z0, w, d, h, a);
    const cyl = (rt, rb, h, n = 8) => new THREE.CylinderGeometry(rt, rb, h, n).rotateX(Math.PI / 2);
    const cone = (r, h, n = 8) => new THREE.ConeGeometry(r, h, n).rotateX(Math.PI / 2);
    const sph = (r, n = 8) => new THREE.SphereGeometry(r, n, Math.max(4, n / 2));

    // Local frame from the four continent groups.
    const grp = [
      'a8cfc47f-900b-451f-a15e-c92c0ef63be0',
      '6ff7d995-360f-4bc4-8d89-8ecb29b3d08b',
      'c8159e6a-0e6d-4454-ad80-950285fe166d',
      '93e65965-7e61-49fc-9473-1ff35f5b0360',
    ].map((id) => byId[id]);
    const canopy = byId['4807fb6d-2ebe-4de4-94ac-9122b798d3f8'];
    let cx = canopy ? canopy.c[0] : 1578.5,
      cy = canopy ? canopy.c[1] : -446.4,
      ang = 0.12;
    if (grp.every(Boolean)) {
      cx = grp.reduce((s, b) => s + b.c[0], 0) / 4;
      cy = grp.reduce((s, b) => s + b.c[1], 0) / 4;
      ang = Math.atan2(grp[1].c[1] - grp[0].c[1], grp[1].c[0] - grp[0].c[0]); // America -> Africa (north side)
    }
    const local = (b) => {
      const dx = b.c[0] - cx,
        dy = b.c[1] - cy,
        c = Math.cos(ang),
        s = Math.sin(ang);
      return [dx * c + dy * s, -dx * s + dy * c];
    };

    // ---- Steps on all four sides and upper platform.
    const nSteps = 9,
      rise = 0.33,
      base = 16.2,
      top = 11.4;
    for (let k = 0; k < nSteps; k++) {
      const hs = base - ((base - top) * k) / (nSteps - 1);
      B(k % 3 === 2 ? greyGranite : kit.mat('#b4aea6'), 0, 0, k * rise, hs * 2, hs * 2, rise);
    }
    const zP = nSteps * rise; // ~3.0
    // Parnassus podium (marble frieze of figures) with a granite base and cornice.
    const friezeMat = kit.paintedMaterial('albert_memorial:parnassus', 512, 64, (c, w, h) => {
      c.fillStyle = '#e4dfd4';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(4.2);
      for (let x = 4; x < w; x += 9 + r() * 6) {
        c.fillStyle = `rgba(120,110,95,${0.25 + r() * 0.25})`;
        c.fillRect(x, 14 + r() * 6, 3, 34);
        c.beginPath();
        c.arc(x + 1.5, 12 + r() * 4, 3, 0, Math.PI * 2);
        c.fill();
      }
      c.fillStyle = '#cfc8b8';
      c.fillRect(0, 0, w, 6);
      c.fillRect(0, h - 6, w, 6);
    });
    const ph = 9.4;
    B(granite, 0, 0, zP, ph * 2 + 0.6, ph * 2 + 0.6, 0.6);
    {
      const geo = new THREE.BoxGeometry(ph * 2, ph * 2, 2.0);
      const uv = geo.attributes.uv;
      for (let k = 0; k < uv.count; k++) uv.setX(k, uv.getX(k) * 4);
      put(geo, friezeMat, 0, 0, zP + 0.6 + 1.0);
    }
    B(stone, 0, 0, zP + 2.6, ph * 2 + 0.5, ph * 2 + 0.5, 0.45);
    const zC = zP + 3.05; // canopy floor
    // Upper steps to the canopy on the south (front).
    for (let k = 0; k < 6; k++)
      B(greyGranite, 0, -ph - 0.4 - (5 - k) * 0.45, zP + k * 0.5, 7, 0.45, 0.5);

    // ---- Canopy: clustered granite piers, pointed arches, gables with mosaics.
    const hw = 4.7, // half spacing of pier centres
      zSpring = zC + 7.4,
      zWall = zC + 13.4,
      zApex = zC + 19.0;
    for (const sx of [-1, 1])
      for (const sy of [-1, 1]) {
        const px = sx * hw,
          py = sy * hw;
        B(stone, px, py, zC, 2.8, 2.8, 1.0);
        for (const [ox, oy] of [
          [-0.55, -0.55],
          [0.55, -0.55],
          [-0.55, 0.55],
          [0.55, 0.55],
          [0, 0],
        ])
          put(
            cyl(0.38, 0.38, zSpring - zC - 1.6, 10),
            ox || oy ? redStone : granite,
            px + ox,
            py + oy,
            (zC + 1.0 + zSpring - 0.6) / 2,
          );
        B(gold, px, py, zSpring - 0.6, 2.6, 2.6, 0.6); // gilt capitals
        B(stone, px, py, zSpring, 2.6, 2.6, zWall - zSpring + 0.6);
        // diagonal buttress (cross-shaped footprint arms)
        put(
          new THREE.BoxGeometry(2.4, 1.0, 2.4),
          granite,
          px + sx * 1.8,
          py + sy * 1.8,
          zC + 1.2,
          Math.atan2(sy, sx),
        );
        // tabernacle pinnacles above the piers
        B(stone, px, py, zWall + 0.6, 1.7, 1.7, 3.2);
        put(cone(1.15, 6.2, 8), stone, px, py, zWall + 3.8 + 3.1, Math.PI / 8);
        put(sph(0.35), gold, px, py, zWall + 7.1);
        for (const [ox, oy] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ])
          put(cone(0.28, 2.2, 6), stone, px + ox * 0.95, py + oy * 0.95, zWall + 2.4);
      }
    const mosaic = kit.paintedMaterial('albert_memorial:mosaic', 256, 128, (c, w, h) => {
      c.fillStyle = '#c9a640';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(9.1);
      for (let k = 0; k < 5; k++) {
        const x = 30 + k * 48;
        c.fillStyle = ['#7a2630', '#264f7a', '#3d6b3a', '#7a2630', '#264f7a'][k];
        c.fillRect(x, 60, 18, 58);
        c.fillStyle = '#efd9b8';
        c.beginPath();
        c.arc(x + 9, 52, 8, 0, Math.PI * 2);
        c.fill();
      }
      c.strokeStyle = '#8a6a20';
      c.lineWidth = 4;
      c.beginPath();
      c.arc(w / 2, 32, 18 + r() * 2, 0, Math.PI * 2);
      c.stroke();
    });
    const faceW = 2 * hw + 1.4,
      a = hw - 1.3; // arch half-span
    const gableShape = () => {
      const s = new THREE.Shape();
      const H0 = 0,
        H1 = zWall - zSpring,
        H2 = zApex - zSpring;
      s.moveTo(-faceW / 2, H0 - 0.0);
      s.lineTo(-a, H0);
      const R = 1.6 * a,
        c0 = R - a;
      // left arc from (-a,0) to apex (0, yA) centred at (c0, 0)
      const yA = Math.sqrt(R * R - c0 * c0);
      const t0 = Math.PI,
        t1 = Math.atan2(yA, -c0);
      for (let k = 1; k <= 8; k++) {
        const t = t0 + ((t1 - t0) * k) / 8;
        s.lineTo(c0 + R * Math.cos(t), R * Math.sin(t));
      }
      for (let k = 7; k >= 0; k--) {
        const t = t0 + ((t1 - t0) * k) / 8;
        s.lineTo(-(c0 + R * Math.cos(t)), R * Math.sin(t));
      }
      s.lineTo(faceW / 2, H0);
      s.lineTo(faceW / 2, H1);
      s.lineTo(0, H2);
      s.lineTo(-faceW / 2, H1);
      return { s, yA, H1, H2 };
    };
    const gs = gableShape();
    const plate = new THREE.ExtrudeGeometry(gs.s, {
      depth: 1.0,
      bevelEnabled: false,
      curveSegments: 4,
    });
    plate.rotateX(Math.PI / 2); // shape y -> z, extrude along -y
    // the arch opening continues down to the floor between piers: plate spans spring..apex
    const triGeo = () => {
      const geo = new THREE.BufferGeometry();
      // mosaic gable triangle (x across, z up) slightly in front of the plate
      const H1 = gs.H1 + 0.25,
        H2 = gs.H2 - 0.9,
        x1 = (faceW / 2) * (1 - 0.9 / (gs.H2 - gs.H1)) - 0.5;
      const p = [-x1, 0, H1, x1, 0, H1, 0, 0, H2];
      geo.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
      geo.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2));
      geo.setIndex([0, 1, 2]);
      return geo;
    };
    const tri = triGeo();
    for (let k = 0; k < 4; k++) {
      const rz = (k * Math.PI) / 2; // k=0: south face
      const c = Math.cos(rz),
        s = Math.sin(rz);
      // face centre at (0,-hw) rotated; plate normal facing outwards
      const fx = -(-hw - 0.2) * s,
        fy = (-hw - 0.2) * c;
      const m = M4()
        .makeRotationZ(rz)
        .setPosition(fx + -s * 0.5, fy + c * 0.5, zSpring);
      batch.addGeometry(stone, plate, m);
      const m2 = M4()
        .makeRotationZ(rz)
        .setPosition(fx + s * 0.56, fy - c * 0.56, zSpring);
      // tri lies in the x-z plane facing -y in its own frame
      batch.addGeometry(mosaic, tri, m2);
      // crockets / gilt finial on the gable apex
      put(sph(0.45), gold, fx, fy, zApex + 0.4);
      put(cone(0.5, 2.2, 6), stone, fx, fy, zApex + 1.5);
      // cresting along the rakes
      for (let t = 0.15; t < 0.95; t += 0.2)
        for (const side of [-1, 1]) {
          const u = side * (faceW / 2) * (1 - t);
          put(sph(0.22, 6), gold, fx + c * u, fy + s * u, zWall + (zApex - zWall) * t + 0.35);
        }
    }
    // Vault soffit and canopy ceiling (blue and gold mosaic).
    B(kit.mat('#2c4f86'), 0, 0, zWall - 0.4, 2 * hw + 1.0, 2 * hw + 1.0, 0.4);
    // Cross-gabled lead roof behind the gables.
    const sq = [
      [-hw, -hw],
      [hw, -hw],
      [hw, hw],
      [-hw, hw],
    ];
    kit.pitchedRoof(batch, lead, stone, sq, 0, zWall + 0.4, zApex - zWall - 1.2, 'gabled', {
      overhang: 0,
    });
    kit.pitchedRoof(
      batch,
      lead,
      stone,
      sq,
      Math.PI / 2,
      zWall + 0.4,
      zApex - zWall - 1.2,
      'gabled',
      { overhang: 0 },
    );

    // ---- Spire: square stage with figures, octagonal tiers, crocketed spire, cross.
    const z1 = zApex - 0.8;
    B(stone, 0, 0, z1 - 1.6, 5.6, 5.6, 3.2);
    for (let k = 0; k < 8; k++) {
      const t = (k * Math.PI) / 4 + Math.PI / 8;
      put(cyl(0.32, 0.4, 2.2, 6), gold, Math.cos(t) * 3.3, Math.sin(t) * 3.3, z1 + 1.1 + 0.6); // virtues/angels
      put(sph(0.3, 6), gold, Math.cos(t) * 3.3, Math.sin(t) * 3.3, z1 + 2.9);
    }
    const tiers = [
      [z1 + 1.6, 2.9, 2.6, 2.2, lead],
      [z1 + 3.8, 2.5, 2.2, 2.4, stone],
      [z1 + 6.2, 2.0, 1.8, 2.0, lead],
    ];
    for (const [z, r0, r1, h, m] of tiers) {
      put(cyl(r1, r0, h, 8), m, 0, 0, z + h / 2, Math.PI / 8);
      put(cyl(r0 + 0.12, r0 + 0.12, 0.25, 8), gold, 0, 0, z + h - 0.1, Math.PI / 8);
    }
    // Lancets around the open tier
    for (let k = 0; k < 8; k++) {
      const t = (k * Math.PI) / 4;
      put(
        new THREE.BoxGeometry(0.2, 0.7, 1.6),
        kit.mat('#1e2328'),
        Math.cos(t) * 2.4,
        Math.sin(t) * 2.4,
        z1 + 4.9,
        t,
      );
    }
    const zs = z1 + 8.2,
      zt = 51.2;
    // Banded spire: alternating dark and gold rings, tapering octagonal frusta.
    const nb = 10;
    for (let k = 0; k < nb; k++) {
      const za = zs + ((zt - zs) * k) / nb,
        zb = zs + ((zt - zs) * (k + 1)) / nb;
      const ra = 1.7 * (1 - k / nb) + 0.12,
        rb = 1.7 * (1 - (k + 1) / nb) + 0.12;
      put(cyl(rb, ra, zb - za, 8), k % 2 ? gold : lead, 0, 0, (za + zb) / 2, Math.PI / 8);
      // crockets on the eight arrises
      if (k > 1 && k < nb - 1)
        for (let j = 0; j < 8; j++) {
          const t = (j * Math.PI) / 4;
          put(sph(0.16, 4), gold, Math.cos(t) * (ra + 0.1), Math.sin(t) * (ra + 0.1), za + 0.4);
        }
    }
    // Gilt crown, orb and cross.
    put(cyl(0.55, 0.4, 0.6, 8), gold, 0, 0, zt + 0.1);
    put(sph(0.4, 10), gold, 0, 0, zt + 0.8);
    B(gold, 0, 0, zt + 1.1, 0.22, 0.22, 2.0);
    B(gold, 0, 0, zt + 2.3, 1.1, 0.22, 0.22);

    // ---- Seated gilt statue of Albert (faces south, -y local).
    const zs0 = zC;
    B(granite, 0, 0.3, zs0, 3.6, 3.6, 0.6);
    B(stone, 0, 0.3, zs0 + 0.6, 3.0, 3.0, 1.6);
    const zb = zs0 + 2.2;
    B(gold, 0, 0.9, zb, 2.0, 1.2, 1.1); // seat
    B(gold, 0, 1.4, zb, 2.0, 0.4, 3.0); // chair back
    put(
      new THREE.CylinderGeometry(0.85, 1.05, 2.0, 10).rotateX(Math.PI / 2),
      gold,
      0,
      0.7,
      zb + 1.1 + 1.0,
    ); // torso and robe
    put(sph(0.42, 10), gold, 0, 0.6, zb + 3.55); // head
    for (const sx of [-0.45, 0.45]) {
      B(gold, sx, 0.05, zb + 0.75, 0.6, 1.5, 0.6); // thighs
      B(gold, sx, -0.6, zb, 0.55, 0.5, 0.9); // shins
    }
    put(new THREE.ConeGeometry(1.25, 2.4, 10).rotateX(Math.PI / 2), gold, 0, 0.6, zb + 1.2); // Garter robe drape
    B(gold, 0.55, -0.15, zb + 1.6, 0.25, 0.9, 0.7); // catalogue in hand

    // ---- Industrial Arts groups at the podium corners (marble).
    const figureGroup = (x, y, z, scale, seed, animal) => {
      const r = kit.rng(seed);
      B(granite, x, y, z, 3.6 * scale, 3.6 * scale, 1.2 * scale);
      B(marble, x, y, z + 1.2 * scale, 3.2 * scale, 3.2 * scale, 0.5 * scale);
      const zf = z + 1.7 * scale;
      if (animal) {
        const [bl, bh, hd] = animal;
        put(sph(1, 10), marble, x, y, zf + 1.6 * scale, 0, bl * scale, 0.75 * scale, bh * scale);
        for (const [ox, oy] of [
          [-0.6, -0.4],
          [0.6, -0.4],
          [-0.6, 0.4],
          [0.6, 0.4],
        ])
          put(
            cyl(0.18 * scale, 0.2 * scale, 1.3 * scale, 6),
            marble,
            x + ox * bl * scale,
            y + oy * scale,
            zf + 0.65 * scale,
          );
        put(
          sph(hd * scale, 8),
          marble,
          x - (bl + 0.2) * scale,
          y - 0.1,
          zf + (1.6 + bh * 0.6) * scale,
        );
      }
      for (let k = 0; k < 4; k++) {
        const t = r() * Math.PI * 2,
          d = (animal ? 1.25 : 0.7) * scale;
        const fx = x + Math.cos(t) * d,
          fy = y + Math.sin(t) * d,
          fh = (animal ? 1.7 : 2.0) * scale * (0.85 + r() * 0.3);
        put(cyl(0.22 * scale, 0.36 * scale, fh, 7), marble, fx, fy, zf + fh / 2);
        put(sph(0.2 * scale, 6), marble, fx, fy, zf + fh + 0.15 * scale);
      }
    };
    for (const [sx, sy, k] of [
      [-1, -1, 0],
      [1, -1, 1],
      [-1, 1, 2],
      [1, 1, 3],
    ])
      figureGroup(sx * (ph + 0.9), sy * (ph + 0.9), zP, 0.72, 2.1 + k, null);

    // ---- Continent groups on their footprints (animal + figures).
    const animals = {
      'a8cfc47f-900b-451f-a15e-c92c0ef63be0': [1.2, 0.8, 0.4], // America: bison
      '6ff7d995-360f-4bc4-8d89-8ecb29b3d08b': [1.1, 0.9, 0.35], // Africa: camel
      'c8159e6a-0e6d-4454-ad80-950285fe166d': [1.25, 0.75, 0.45], // Europe: bull
      '93e65965-7e61-49fc-9473-1ff35f5b0360': [1.4, 1.1, 0.6], // Asia: elephant
    };
    let seed = 11;
    for (const b of grp) {
      if (!b) continue;
      const [x, y] = local(b);
      figureGroup(x, y, 0, 1.15, seed++, animals[b.id]);
    }

    const out = batch.toGroup('albert_memorial');
    g.add(out);
    g.position.set(cx, cy, 0);
    g.rotation.z = ang;
    // Unidentified low strips south of the memorial: granite plinths in scene coordinates.
    const lowB = new kit.MeshBatch();
    for (const id of [
      '621d410b-ab5a-47cb-a78e-a7fdd28d9b5f',
      '7bdfa484-5fa2-47c9-87d8-414991b63209',
    ]) {
      const b = byId[id];
      if (!b) continue;
      let r = b.polys[0][0];
      if (kit.ringArea(r) < 0) r = r.slice().reverse();
      kit.walls(lowB, granite, [[r]], 0, 0.8);
      kit.cap(lowB, greyGranite, [[r]], 0.8);
    }
    const root = new THREE.Group();
    root.add(g, lowB.toGroup('albert_memorial_plinths'));
    return root;
  },
};
