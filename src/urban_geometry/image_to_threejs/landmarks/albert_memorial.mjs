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
        'mass of gilt, mosaic and coloured stones; ornamented spire with a cross at the top; canopy about thirty feet square on groups of polished granite columns',
    },
    {
      title: 'The Albert Memorial - A London Inheritance',
      url: 'https://alondoninheritance.com/london-monuments/albert-memorial-19th-century-world-view',
      used_for: 'octagonal grey-banded crocketed spire, gilded crown, angels round the spire base',
    },
    {
      title: 'Prince Consort National Memorial - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101217741-prince-consort-national-memorial-albert-memorial-knightsbridge-and-belgravia-ward',
      used_for:
        'sculptured band breaking outward at the corners for the Agriculture, Manufacture, Commerce and Engineering groups; continent groups at the outer corners',
    },
  ],
  notes:
    'Placed on the Overture canopy footprint and the four continent-group footprints (orientation ~7 deg from the group layout). ' +
    'Step and podium dimensions, stage heights (arches springing ~13 m, gables to ~25 m, spire 32-51 m, cross to ~54 m) are ' +
    'proportioned from descriptions. Canopy in 3D: four piers of four polished granite columns with gilt capitals and shaft rings, ' +
    'moulded two-order pointed arches, mosaic gables with crocketed rakes and pierced roundels, groined blue-and-gold vault, ' +
    'corner tabernacles with bronze science figures, cross-gabled lead roof with gilt cresting; flèche with gilt virtues, an ' +
    'arcaded lantern, winged angels, banded crocketed spire, crown, orb and cross. Sculpture (Albert, industrial arts and continent ' +
    'groups) is built from simple robed figures and animal stand-ins, not portraits; mosaics and the Parnassus frieze are painted. ' +
    'Two small unnamed 2 x 8 m strips ~35 m south-east/south-west of the memorial (identity unknown, generic extrusion gave 17 m ' +
    'towers in the park) are claimed and drawn as low granite plinths.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const granite = kit.mat('#8f7f7a', { roughness: 0.45 }),
      greyGranite = kit.mat('#a19d98', { roughness: 0.7 }),
      stepGranite = kit.mat('#b4aea6', { roughness: 0.8 }),
      stone = kit.mat('#d9d0bf'),
      stoneD = kit.mat('#c9bfab'),
      marble = kit.mat('#ece8df', { roughness: 0.6 }),
      lead = kit.mat('#5d6266', { roughness: 0.5, metalness: 0.35 }),
      gold = kit.mat('#e2b94f', { roughness: 0.35, metalness: 0.35 }),
      leadL = kit.mat('#767c80', { roughness: 0.5, metalness: 0.3 }),
      bronze = kit.mat('#5a4630', { roughness: 0.45, metalness: 0.6 }),
      redStone = kit.mat('#9c5e52', { roughness: 0.3 }),
      pinkGranite = kit.mat('#b98b80', { roughness: 0.3 }),
      darkVoid = kit.mat('#1c2126'),
      shade = kit.mat('#3b4146'),
      blueMosaic = kit.mat('#2c4f86', { roughness: 0.5 });
    const M4 = () => new THREE.Matrix4();
    const Q = (rz) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz);
    const put = (geo, m, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) =>
      batch.addGeometry(
        m,
        geo,
        M4().compose(new THREE.Vector3(x, y, z), Q(rz), new THREE.Vector3(sx, sy, sz)),
      );
    const B = (m, x, y, z0, w, d, h, a = 0) => kit.box(batch, m, x, y, z0, w, d, h, a);
    const cyl = (rt, rb, h, n = 8) => new THREE.CylinderGeometry(rt, rb, h, n).rotateX(Math.PI / 2);
    const cone = (r, h, n = 8) => new THREE.ConeGeometry(r, h, n).rotateX(Math.PI / 2);
    const sph = (r, n = 8) => new THREE.SphereGeometry(r, n, Math.max(4, n / 2));
    const latheG = (prof, n = 10) =>
      new THREE.LatheGeometry(
        prof.map(([r, z]) => new THREE.Vector2(Math.max(0.001, r), z)),
        n,
      ).rotateX(Math.PI / 2);
    // Geometry cache for repeated profiles.
    const cache = new Map();
    const memo = (key, make) => (cache.has(key) ? cache.get(key) : cache.set(key, make()).get(key));

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

    // ---- Figures: robed standing / seated figure built from a lathe, head and arms.
    const robeGeo = memo('robe', () =>
      latheG(
        [
          [0, 0],
          [0.3, 0],
          [0.27, 0.35],
          [0.21, 0.9],
          [0.17, 1.2],
          [0.22, 1.38],
          [0.12, 1.5],
          [0.07, 1.55],
          [0, 1.56],
        ],
        8,
      ),
    );
    const headGeo = memo('head', () => sph(0.12, 8));
    const armGeo = memo('arm', () => cyl(0.05, 0.06, 0.62, 5));
    const figure = (m, x, y, z, h, rz = 0, pose = 0) => {
      const s = h / 1.8;
      put(robeGeo, m, x, y, z, rz, s, s * 0.8, s);
      put(headGeo, m, x, y, z + 1.66 * s, rz, s, s, s * 1.1);
      const c = Math.cos(rz),
        sn = Math.sin(rz);
      for (const side of [-1, 1]) {
        const lift = side === 1 ? pose : 0;
        const ax = x + c * side * 0.24 * s,
          ay = y + sn * side * 0.24 * s;
        batch.addGeometry(
          m,
          armGeo,
          M4().compose(
            new THREE.Vector3(ax, ay, z + (1.15 + lift * 0.3) * s),
            new THREE.Quaternion().setFromEuler(new THREE.Euler(lift * 1.2 - 0.15, side * 0.2, rz)),
            new THREE.Vector3(s, s, s),
          ),
        );
      }
    };
    const seated = (m, x, y, z, h, rz = 0) => {
      // seat block, thighs forward, lower robe, torso, head
      const s = h / 1.4;
      const c = Math.cos(rz),
        sn = Math.sin(rz);
      const fwd = (d) => [x - sn * d * s * -1, y + c * d * s * -1]; // facing -y local when rz = 0
      put(robeGeo, m, x, y, z + 0.35 * s, rz, s * 1.1, s * 0.9, s * 0.62);
      const [kx, ky] = fwd(0.32);
      B(m, kx, ky, z + 0.3 * s, 0.5 * s, 0.55 * s, 0.22 * s, rz);
      const [fx, fy] = fwd(0.55);
      B(m, fx, fy, z, 0.5 * s, 0.22 * s, 0.45 * s, rz);
      put(headGeo, m, x, y, z + 1.38 * s, rz, s, s, s * 1.1);
    };

    // ---- Steps on all four sides and the lower platform.
    const nSteps = 9,
      rise = 0.33,
      base = 16.2,
      top = 11.4;
    for (let k = 0; k < nSteps; k++) {
      const hs = base - ((base - top) * k) / (nSteps - 1);
      B(k % 3 === 2 ? greyGranite : stepGranite, 0, 0, k * rise, hs * 2, hs * 2, rise);
      // nosing line
      B(greyGranite, 0, 0, k * rise + rise - 0.05, hs * 2 + 0.06, hs * 2 + 0.06, 0.05);
    }
    const zP = nSteps * rise; // ~3.0
    // Paved platform pattern (polychrome bands) on the lower terrace.
    const paveMat = kit.paintedMaterial('albert_memorial:pave', 256, 256, (c, w, h) => {
      c.fillStyle = '#bdb6aa';
      c.fillRect(0, 0, w, h);
      c.strokeStyle = '#8f8379';
      c.lineWidth = 3;
      for (let k = 0; k <= 8; k++) {
        c.beginPath();
        c.moveTo((k * w) / 8, 0);
        c.lineTo((k * w) / 8, h);
        c.moveTo(0, (k * h) / 8);
        c.lineTo(w, (k * h) / 8);
        c.stroke();
      }
      c.fillStyle = '#9a6e62';
      for (let i = 0; i < 8; i++)
        for (let j = 0; j < 8; j++)
          if ((i + j) % 2 === 0) c.fillRect((i * w) / 8 + 10, (j * h) / 8 + 10, 12, 12);
    });
    kit.cap(
      batch,
      paveMat,
      [
        [
          [
            [-top, -top],
            [top, -top],
            [top, top],
            [-top, top],
          ],
        ],
      ],
      zP + 0.005,
      {
        scale: 4,
      },
    );

    // ---- Parnassus podium: granite base, marble frieze in relief (painted), cornice.
    const friezeMat = kit.paintedMaterial('albert_memorial:parnassus2', 1024, 128, (c, w, h) => {
      c.fillStyle = '#e8e3d8';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(4.2);
      c.fillStyle = '#d3cbbb';
      c.fillRect(0, 0, w, 14);
      c.fillRect(0, h - 14, w, 14);
      for (let x = 14; x < w - 14; x += 38 + r() * 16) {
        const hh = 74 + r() * 16,
          base = h - 16,
          fw = 9 + r() * 4,
          lean = (r() - 0.5) * 6;
        // shadow side then lit side of a robed figure in relief
        c.fillStyle = 'rgba(95,85,70,0.5)';
        c.beginPath();
        c.moveTo(x - fw + 3, base);
        c.lineTo(x + fw + 3, base);
        c.lineTo(x + fw * 0.5 + 3 + lean, base - hh * 0.8);
        c.lineTo(x - fw * 0.5 + 3 + lean, base - hh * 0.8);
        c.fill();
        c.fillStyle = '#f6f3ec';
        c.beginPath();
        c.moveTo(x - fw, base);
        c.lineTo(x + fw, base);
        c.lineTo(x + fw * 0.5 + lean, base - hh * 0.8);
        c.lineTo(x - fw * 0.5 + lean, base - hh * 0.8);
        c.fill();
        c.beginPath();
        c.arc(x + lean, base - hh * 0.88, 5.5, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = 'rgba(95,85,70,0.45)';
        c.fillRect(x + lean + 2, base - hh * 0.88, 3, 5);
        c.fillRect(x - fw * 0.3, base - hh * 0.5, fw * 0.9, 2); // drapery fold
        if (r() < 0.4) {
          c.fillStyle = '#f6f3ec';
          c.fillRect(x + fw * 0.4, base - hh * 0.72, 10, 3); // arm / attribute
        }
      }
    });
    const ph = 9.4;
    B(granite, 0, 0, zP, ph * 2 + 0.6, ph * 2 + 0.6, 0.6);
    B(greyGranite, 0, 0, zP + 0.6, ph * 2 + 0.3, ph * 2 + 0.3, 0.15);
    {
      const geo = new THREE.BoxGeometry(ph * 2, ph * 2, 2.0);
      const uv = geo.attributes.uv;
      for (let k = 0; k < uv.count; k++) uv.setX(k, uv.getX(k) * 2);
      put(geo, friezeMat, 0, 0, zP + 0.75 + 1.0);
      geo.dispose();
    }
    B(stoneD, 0, 0, zP + 2.75, ph * 2 + 0.3, ph * 2 + 0.3, 0.12);
    B(stone, 0, 0, zP + 2.87, ph * 2 + 0.6, ph * 2 + 0.6, 0.25);
    const zC = zP + 3.12; // canopy floor
    // Corner projections carrying the Industrial Arts groups.
    for (const sx of [-1, 1])
      for (const sy of [-1, 1]) {
        const x = sx * (ph - 0.4),
          y = sy * (ph - 0.4);
        B(granite, x, y, zP, 4.4, 4.4, 0.6);
        B(marble, x, y, zP + 0.6, 4.1, 4.1, 2.27);
        B(stone, x, y, zP + 2.87, 4.6, 4.6, 0.25);
      }
    // Upper flight to the canopy on the south (front) and inlaid floor.
    for (let k = 0; k < 6; k++)
      B(greyGranite, 0, -ph - 0.5 - (5 - k) * 0.45, zP + k * 0.52, 7.4, 0.45, 0.52);
    const floorMat = kit.paintedMaterial('albert_memorial:floor', 256, 256, (c, w, h) => {
      c.fillStyle = '#c8bfae';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#8a5a4e';
      c.fillRect(20, 20, w - 40, h - 40);
      c.fillStyle = '#d9cfbd';
      c.fillRect(34, 34, w - 68, h - 68);
      const r = kit.rng(6.6);
      for (let i = 0; i < 6; i++)
        for (let j = 0; j < 6; j++) {
          c.fillStyle =
            (i + j) % 2 ? '#cdc3b1' : ['#b39a8c', '#a7a49e', '#bba78a'][Math.floor(r() * 3)];
          c.fillRect(40 + i * 29.3, 40 + j * 29.3, 27, 27);
        }
      c.beginPath();
      c.fill();
    });
    {
      const e = ph + 0.3;
      batch.quad(
        floorMat,
        [-e, -e, zC + 0.01],
        [e, -e, zC + 0.01],
        [e, e, zC + 0.01],
        [-e, e, zC + 0.01],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // ---- Canopy geometry.
    const hw = 4.7, // half spacing of pier centres
      zSpring = zC + 7.3,
      zWall = zC + 13.3,
      zApex = zC + 19.0;
    const faceW = 2 * hw + 1.4,
      a = hw - 1.3, // arch half-span at the springing
      R = 1.6 * a,
      c0 = R - a;
    // Pointed arch outline offset by g (same centres), from left foot to right foot.
    const archPts = (g, n = 9) => {
      const r = R + g,
        yA = Math.sqrt(r * r - c0 * c0);
      const t1 = Math.atan2(yA, -c0);
      const left = [];
      for (let k = 0; k <= n; k++) {
        const t = Math.PI + ((t1 - Math.PI) * k) / n;
        left.push([c0 + r * Math.cos(t), r * Math.sin(t)]);
      }
      const right = left
        .slice(0, -1)
        .reverse()
        .map(([x, y]) => [-x, y]);
      return [...left, ...right];
    };
    const archTop = (g) => Math.sqrt((R + g) * (R + g) - c0 * c0);
    const H1 = zWall - zSpring,
      H2 = zApex - zSpring;
    const extr = (pts, depth, holes = []) => {
      const s = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
      for (const h of holes)
        s.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
      const geo = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false });
      geo.rotateX(Math.PI / 2); // shape y -> z, extrusion -> -y
      return geo;
    };
    const G = 0.95;
    const plateGeo = extr(
      [[-faceW / 2, 0], ...archPts(G), [faceW / 2, 0], [faceW / 2, H1], [0, H2], [-faceW / 2, H1]],
      1.4,
    );
    const ringGeo = (g0, g1, d) => extr([...archPts(g1), ...archPts(g0).reverse()], d);
    const order1 = ringGeo(0.5, G, 1.1),
      order2 = ringGeo(0.12, 0.5, 0.9),
      order3 = ringGeo(0, 0.12, 1.3);
    // Triangle mosaic in the gable and a pierced roundel above the arch.
    const mosaic = kit.paintedMaterial('albert_memorial:mosaic2', 512, 256, (c, w, h) => {
      c.fillStyle = '#c9a640';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(9.1);
      for (let k = 0; k < 900; k++) {
        c.fillStyle = `rgba(${150 + r() * 80},${120 + r() * 60},${30 + r() * 30},0.5)`;
        c.fillRect(r() * w, r() * h, 3, 3);
      }
      // seated central figure under a throne and flanking standing figures
      c.fillStyle = '#efe2c0';
      c.fillRect(w / 2 - 30, 120, 60, 90);
      c.fillStyle = '#7a2630';
      c.fillRect(w / 2 - 22, 140, 44, 90);
      c.fillStyle = '#efd9b8';
      c.beginPath();
      c.arc(w / 2, 128, 12, 0, Math.PI * 2);
      c.fill();
      const robes = ['#264f7a', '#3d6b3a', '#7a2630', '#5a3d6e', '#264f7a', '#3d6b3a'];
      for (let k = 0; k < 6; k++) {
        const side = k < 3 ? -1 : 1,
          j = k % 3;
        const x = w / 2 + side * (70 + j * 52),
          hh = 100 - j * 22;
        c.fillStyle = robes[k];
        c.fillRect(x - 11, h - 18 - hh, 22, hh);
        c.fillStyle = '#efd9b8';
        c.beginPath();
        c.arc(x, h - 26 - hh, 9, 0, Math.PI * 2);
        c.fill();
      }
      c.fillStyle = '#8a6a20';
      c.fillRect(0, h - 14, w, 14);
    });
    const triGeo = (() => {
      const geo = new THREE.BufferGeometry();
      const y0 = archTop(G) + 0.15,
        y1 = H2 - 0.9;
      const xs = (y) => (faceW / 2 - 0.5) * Math.min(1, (H2 - y) / (H2 - H1));
      const p = [-xs(y0), 0, y0, xs(y0), 0, y0, xs(H1), 0, H1, 0, 0, y1, -xs(H1), 0, H1];
      geo.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
      const uv = [];
      for (let k = 0; k < 5; k++)
        uv.push(p[k * 3] / (faceW - 1) + 0.5, (p[k * 3 + 2] - y0) / (y1 - y0));
      geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      geo.setIndex([0, 1, 2, 0, 2, 4, 4, 2, 3]);
      return geo;
    })();
    const roundel = new THREE.TorusGeometry(0.75, 0.12, 5, 16);
    roundel.rotateX(Math.PI / 2);
    const roundelVoid = cyl(0.72, 0.72, 0.1, 16);
    roundelVoid.rotateX(0);
    const crocket = memo('crocket', () => cone(0.18, 0.5, 5));
    // Faces: rotate the south face (outward -y) by k * 90 degrees.
    const faceM = (k, x, y, z, extra = M4()) =>
      M4()
        .makeRotationZ((k * Math.PI) / 2)
        .multiply(M4().makeTranslation(x, y, z))
        .multiply(extra);
    const yF = -(hw + 0.7); // outer face plane
    for (let k = 0; k < 4; k++) {
      const add = (geo, m, x, y, z, extra) => batch.addGeometry(m, geo, faceM(k, x, y, z, extra));
      add(plateGeo, stone, 0, -(hw - 0.7), zSpring);
      add(order1, stoneD, 0, yF + 0.25 + 1.1, zSpring);
      add(order2, pinkGranite, 0, yF + 0.45 + 0.9, zSpring);
      add(order3, gold, 0, yF + 0.6 + 1.3, zSpring);
      add(triGeo, mosaic, 0, yF - 0.02, zSpring);
      // Roundel above the arch apex (in the upper gable).
      const rz = zSpring + H2 - 2.0;
      add(roundelVoid, darkVoid, 0, yF - 0.01, rz, M4().makeRotationX(Math.PI / 2));
      add(roundel, gold, 0, yF - 0.08, rz);
      // Raking copings with crockets and the gable finial.
      for (const side of [-1, 1]) {
        const L = Math.hypot(faceW / 2, H2 - H1),
          t = Math.atan2(H2 - H1, faceW / 2);
        const geo = memo('rake', () => new THREE.BoxGeometry(L + 0.3, 1.7, 0.4));
        add(
          geo,
          stoneD,
          (side * faceW) / 4,
          yF + 0.7,
          zSpring + (H1 + H2) / 2 + 0.2,
          M4().makeRotationY(side * t),
        );
        for (let i = 1; i < 7; i++) {
          const u = i / 7;
          add(
            crocket,
            gold,
            side * (faceW / 2) * (1 - u),
            yF - 0.05,
            zSpring + H1 + (H2 - H1) * u + 0.5,
          );
        }
      }
      // Cusped arcade band (blind arcading) under the gable foot.
      for (let i = 0; i < 2; i++) {
        const x = (i ? 1 : -1) * (faceW / 2 - 0.9);
        add(
          memo('blind', () => new THREE.BoxGeometry(0.9, 0.12, 2.6)),
          darkVoid,
          x,
          yF - 0.02,
          zSpring + 1.1,
        );
      }
      // Gable finial: gilt cross-flower.
      add(
        memo('fin1', () => cyl(0.18, 0.25, 1.6, 8)),
        stone,
        0,
        yF + 0.6,
        zApex + 0.7,
      );
      add(
        memo('fin2', () => sph(0.42, 10)),
        gold,
        0,
        yF + 0.6,
        zApex + 1.7,
      );
      add(
        memo('fin3', () => new THREE.BoxGeometry(0.16, 0.16, 1.5)),
        gold,
        0,
        yF + 0.6,
        zApex + 2.6,
      );
      add(
        memo('fin4', () => new THREE.BoxGeometry(0.9, 0.16, 0.16)),
        gold,
        0,
        yF + 0.6,
        zApex + 2.8,
      );
      // Inscription band along the cornice at the foot of the gables.
      add(
        memo('frieze', () => new THREE.BoxGeometry(faceW - 0.4, 0.2, 0.7)),
        blueMosaic,
        0,
        yF - 0.05,
        zSpring + H1 - 0.4,
      );
      add(
        memo('friezeL', () => new THREE.BoxGeometry(faceW - 0.4, 0.22, 0.08)),
        gold,
        0,
        yF - 0.06,
        zSpring + H1 - 0.36,
      );
    }

    // ---- Corner piers: four polished granite columns round a core, gilt capitals.
    const shaft = memo('shaft', () =>
      latheG(
        [
          [0, 0],
          [0.48, 0],
          [0.48, 0.18],
          [0.4, 0.28],
          [0.34, 0.4],
          [0.31, 0.5],
          [0.3, 1],
        ],
        12,
      ),
    );
    const colH = zSpring - 0.9 - (zC + 1.2);
    const shaftBody = memo('shaftBody', () => cyl(0.3, 0.3, 1, 12));
    const capital = memo('capital', () =>
      latheG(
        [
          [0.3, 0],
          [0.36, 0.12],
          [0.48, 0.45],
          [0.6, 0.7],
          [0.62, 0.82],
          [0, 0.82],
        ],
        12,
      ),
    );
    const ringBand = memo('ringBand', () => cyl(0.36, 0.36, 0.14, 12));
    for (const sx of [-1, 1])
      for (const sy of [-1, 1]) {
        const px = sx * hw,
          py = sy * hw;
        // moulded pier base
        B(granite, px, py, zC, 3.0, 3.0, 0.7);
        B(stoneD, px, py, zC + 0.7, 2.8, 2.8, 0.5);
        B(stone, px, py, zC + 1.2, 1.5, 1.5, zSpring - zC - 1.2); // core
        for (const [ox, oy] of [
          [-0.72, -0.72],
          [0.72, -0.72],
          [-0.72, 0.72],
          [0.72, 0.72],
        ]) {
          const x = px + ox,
            y = py + oy;
          put(shaft, granite, x, y, zC + 1.2, 0, 1, 1, 1);
          put(
            shaftBody,
            ox * sx > 0 && oy * sy > 0 ? pinkGranite : redStone,
            x,
            y,
            zC + 1.2 + 0.5 + (colH - 0.5) / 2,
            0,
            1,
            1,
            colH - 0.5,
          );
          put(ringBand, gold, x, y, zC + 1.2 + colH * 0.5);
          put(capital, gold, x, y, zSpring - 0.9);
        }
        // abacus and the pier block above (with niches and bronze sciences)
        B(stone, px, py, zSpring - 0.1, 3.0, 3.0, 0.35);
        B(stone, px, py, zSpring + 0.25, 2.6, 2.6, H1 + 0.6);
        for (const [ox, oy] of [
          [-1.3, -1.3],
          [1.3, -1.3],
          [-1.3, 1.3],
          [1.3, 1.3],
        ]) {
          put(
            memo('colt', () => cyl(0.13, 0.13, H1 + 0.6, 8)),
            pinkGranite,
            px + ox,
            py + oy,
            zSpring + 0.25 + (H1 + 0.6) / 2,
          );
          put(
            memo('coltC', () => cyl(0.22, 0.14, 0.25, 8)),
            gold,
            px + ox,
            py + oy,
            zWall + 0.72,
          );
        }
        B(stoneD, px, py, zWall - 0.5, 2.8, 2.8, 0.25);
        for (const [nx, ny] of [
          [sx, 0],
          [0, sy],
        ]) {
          const fx = px + nx * 1.31,
            fy = py + ny * 1.31;
          const rz = Math.atan2(ny, nx) + Math.PI / 2;
          B(darkVoid, fx, fy, zSpring + 1.0, 1.0, 0.06, 3.1, rz);
          B(stoneD, fx + nx * 0.05, fy + ny * 0.05, zSpring + 0.8, 1.4, 0.2, 0.2, rz);
          put(
            memo('canopyN', () => cone(0.75, 1.0, 4)),
            stoneD,
            fx + nx * 0.1,
            fy + ny * 0.1,
            zSpring + 4.6,
            Math.PI / 4 + rz,
          );
          figure(bronze, fx + nx * 0.25, fy + ny * 0.25, zSpring + 1.0, 2.2, rz - Math.PI, 0.6);
        }
        // Corner tabernacle: octagonal open stage with gilt shafts and a crocketed spirelet.
        const zt = zWall + 0.85;
        put(
          memo('tab0', () => cyl(1.35, 1.45, 0.4, 8)),
          stoneD,
          px,
          py,
          zt + 0.2,
          Math.PI / 8,
        );
        put(
          memo('tab1', () => cyl(1.0, 1.0, 3.2, 8)),
          shade,
          px,
          py,
          zt + 2.0,
          Math.PI / 8,
        );
        for (let j = 0; j < 8; j++) {
          const t = (j * Math.PI) / 4 + Math.PI / 8;
          put(
            memo('tabShaft', () => cyl(0.13, 0.13, 3.2, 6)),
            gold,
            px + Math.cos(t) * 1.15,
            py + Math.sin(t) * 1.15,
            zt + 2.0,
          );
        }
        put(
          memo('tab2', () => cyl(1.3, 1.25, 0.45, 8)),
          stone,
          px,
          py,
          zt + 3.8,
          Math.PI / 8,
        );
        figure(bronze, px, py, zt + 0.4, 2.4, Math.atan2(sy, sx) + Math.PI / 2, 0.3);
        put(
          memo('tab3', () => cone(1.15, 5.6, 8)),
          stone,
          px,
          py,
          zt + 4.0 + 2.8,
          Math.PI / 8,
        );
        for (let j = 0; j < 8; j++) {
          const t = (j * Math.PI) / 4 + Math.PI / 8;
          for (let i = 1; i < 4; i++) {
            const u = i / 4.5;
            put(
              crocket,
              gold,
              px + Math.cos(t) * 1.15 * (1 - u),
              py + Math.sin(t) * 1.15 * (1 - u),
              zt + 4.0 + 5.6 * u,
            );
          }
        }
        put(
          memo('tabOrb', () => sph(0.3, 8)),
          gold,
          px,
          py,
          zt + 9.75,
        );
        put(
          memo('tabFin', () => cone(0.14, 0.9, 6)),
          gold,
          px,
          py,
          zt + 10.4,
        );
        // four little corner pinnacles round the tabernacle
        for (const [ox, oy] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ]) {
          B(stone, px + ox * 1.1, py + oy * 1.1, zWall + 0.85, 0.45, 0.45, 1.6);
          put(
            memo('pinC', () => cone(0.3, 2.0, 6)),
            stone,
            px + ox * 1.1,
            py + oy * 1.1,
            zWall + 2.45 + 1.0,
          );
          put(
            memo('pinO', () => sph(0.12, 6)),
            gold,
            px + ox * 1.1,
            py + oy * 1.1,
            zWall + 4.5,
          );
        }
      }

    // ---- Groined vault (blue mosaic with gilt stars) and gilt diagonal ribs.
    const vaultMat = kit.paintedMaterial('albert_memorial:vault', 256, 256, (c, w, h) => {
      c.fillStyle = '#284a80';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(3.3);
      c.fillStyle = '#e0c060';
      for (let k = 0; k < 70; k++) {
        const x = r() * w,
          y = r() * h;
        c.fillRect(x - 3, y - 0.8, 6, 1.6);
        c.fillRect(x - 0.8, y - 3, 1.6, 6);
      }
    });
    const archH = (s) => {
      const d = c0 + Math.abs(s);
      return Math.sqrt(Math.max(0, R * R - d * d));
    };
    {
      const n = 12,
        S = a;
      const pts = [],
        uvs = [];
      for (let i = 0; i <= n; i++)
        for (let j = 0; j <= n; j++) {
          const x = -S + (2 * S * i) / n,
            y = -S + (2 * S * j) / n;
          pts.push([x, y, zSpring + Math.min(archH(x), archH(y))]);
          uvs.push([i / n, j / n]);
        }
      const idx = [];
      for (let i = 0; i < n; i++)
        for (let j = 0; j < n; j++) {
          const p = i * (n + 1) + j;
          idx.push(p, p + 1, p + n + 2, p, p + n + 2, p + n + 1); // facing down
        }
      batch.add(vaultMat, pts, uvs, idx);
      for (const d of [1, -1])
        for (let i = 0; i < n; i++) {
          const x0 = -S + (2 * S * i) / n,
            x1 = -S + (2 * S * (i + 1)) / n;
          const za = zSpring + archH(x0) - 0.12,
            zb = zSpring + archH(x1) - 0.12;
          const mx = (x0 + x1) / 2;
          const L = Math.hypot((x1 - x0) * Math.SQRT2, zb - za);
          const geo = new THREE.BoxGeometry(L, 0.18, 0.18);
          const m = M4().compose(
            new THREE.Vector3(mx, d * mx, (za + zb) / 2),
            new THREE.Quaternion().setFromEuler(
              new THREE.Euler(
                0,
                -Math.atan2(zb - za, (x1 - x0) * Math.SQRT2),
                (d * Math.PI) / 4,
                'ZYX',
              ),
            ),
            new THREE.Vector3(1, 1, 1),
          );
          batch.addGeometry(gold, geo, m);
          geo.dispose();
        }
      // flat soffits between vault and gables
      B(blueMosaic, 0, 0, zWall - 0.3, 2 * hw + 0.4, 2 * hw + 0.4, 0.3);
    }
    // Cross-gabled lead roof behind the gables, gilt ridge cresting.
    const sq = [
      [-hw, -hw],
      [hw, -hw],
      [hw, hw],
      [-hw, hw],
    ];
    const roofRise = zApex - zWall - 1.2;
    for (const ra of [0, Math.PI / 2])
      kit.pitchedRoof(batch, lead, stone, sq, ra, zWall + 0.4, roofRise, 'gabled', { overhang: 0 });
    for (let i = -6; i <= 6; i++) {
      if (Math.abs(i) < 2) continue;
      const t = i / 7;
      B(gold, t * hw, 0, zWall + 0.4 + roofRise, 0.12, 0.12, 0.55);
      B(gold, 0, t * hw, zWall + 0.4 + roofRise, 0.12, 0.12, 0.55);
    }

    // ---- Flèche: virtues stage, arcaded lantern, angels, banded crocketed spire, cross.
    const z1 = zApex - 0.8;
    put(
      memo('sp0', () =>
        latheG(
          [
            [0, 0],
            [3.2, 0],
            [3.2, 0.5],
            [2.95, 0.7],
            [2.95, 2.6],
            [3.2, 2.8],
            [3.25, 3.1],
            [0, 3.1],
          ],
          8,
        ),
      ),
      stone,
      0,
      0,
      z1 - 1.5,
      Math.PI / 8,
    );
    for (let k = 0; k < 8; k++) {
      const t = (k * Math.PI) / 4 + Math.PI / 8;
      const x = Math.cos(t) * 3.35,
        y = Math.sin(t) * 3.35;
      put(
        memo('brk', () => cyl(0.45, 0.32, 0.5, 8)),
        stoneD,
        x,
        y,
        z1 + 1.85,
      );
      figure(gold, x, y, z1 + 2.1, 2.1, t + Math.PI / 2 - Math.PI, k % 3 === 0 ? 0.8 : 0.2); // virtues
    }
    // Arcaded lantern stage.
    const zl = z1 + 1.6;
    put(
      memo('lan0', () => cyl(2.6, 2.6, 3.4, 8)),
      darkVoid,
      0,
      0,
      zl + 1.7,
      Math.PI / 8,
    );
    for (let k = 0; k < 8; k++) {
      const t = (k * Math.PI) / 4;
      put(
        memo('lanP', () => new THREE.BoxGeometry(0.5, 0.5, 3.4)),
        stone,
        Math.cos(t) * 2.7,
        Math.sin(t) * 2.7,
        zl + 1.7,
        t,
      );
      put(
        memo('lanS', () => cyl(0.1, 0.1, 2.6, 6)),
        gold,
        Math.cos(t + Math.PI / 8) * 2.75,
        Math.sin(t + Math.PI / 8) * 2.75,
        zl + 1.3,
      );
      // little gablet over each opening
      put(
        memo('lanG', () => cone(0.95, 1.1, 3).rotateY(0)),
        stone,
        Math.cos(t + Math.PI / 8) * 2.6,
        Math.sin(t + Math.PI / 8) * 2.6,
        zl + 3.7,
        t + Math.PI / 8 + Math.PI / 2,
        1,
        0.35,
        1,
      );
    }
    put(
      memo('lan1', () => cyl(2.85, 2.75, 0.4, 8)),
      gold,
      0,
      0,
      zl + 3.6,
      Math.PI / 8,
    );
    put(
      memo('lan2', () => cyl(2.4, 2.6, 1.2, 8)),
      lead,
      0,
      0,
      zl + 4.4,
      Math.PI / 8,
    );
    // Angels with outspread wings.
    const zAng = zl + 4.0;
    for (let k = 0; k < 8; k++) {
      const t = (k * Math.PI) / 4 + Math.PI / 8;
      const x = Math.cos(t) * 2.75,
        y = Math.sin(t) * 2.75;
      figure(gold, x, y, zAng, 1.8, t - Math.PI / 2, 0.9);
      for (const side of [-1, 1])
        put(
          memo('wing', () => new THREE.BoxGeometry(0.6, 0.05, 1.3)),
          gold,
          x - Math.sin(t) * side * 0.45 - Math.cos(t) * 0.15,
          y + Math.cos(t) * side * 0.45 - Math.sin(t) * 0.15,
          zAng + 1.55,
          t + Math.PI / 2 + side * 0.35,
        );
    }
    // Spire: banded octagonal frusta with gilt rings and crockets on the arrises.
    const zs = zl + 5.0,
      zt = 51.2;
    const nb = 12;
    const r0s = 2.2;
    for (let k = 0; k < nb; k++) {
      const za = zs + ((zt - zs) * k) / nb,
        zb = zs + ((zt - zs) * (k + 1)) / nb;
      const ra = r0s * (1 - k / nb) + 0.12,
        rb = r0s * (1 - (k + 1) / nb) + 0.12;
      put(
        cyl(rb, ra, zb - za, 8),
        k % 3 === 2 ? gold : k % 2 ? leadL : lead,
        0,
        0,
        (za + zb) / 2,
        Math.PI / 8,
      );
      put(cyl(ra + 0.06, ra + 0.06, 0.14, 8), gold, 0, 0, za + 0.07, Math.PI / 8);
      if (k > 0 && k < nb - 1)
        for (let j = 0; j < 8; j++) {
          const t = (j * Math.PI) / 4;
          put(
            crocket,
            gold,
            Math.cos(t) * (ra + 0.05),
            Math.sin(t) * (ra + 0.05),
            za + 0.6,
            0,
            0.8,
            0.8,
            0.8,
          );
        }
    }
    // Lucarnes (gabled openings) on the lower spire.
    for (let k = 0; k < 4; k++) {
      const t = (k * Math.PI) / 2 + Math.PI / 8;
      const r = r0s * 0.86;
      const x = Math.cos(t) * r,
        y = Math.sin(t) * r;
      B(stone, x, y, zs + 0.6, 0.8, 0.8, 1.4, t);
      B(darkVoid, x + Math.cos(t) * 0.41, y + Math.sin(t) * 0.41, zs + 0.8, 0.04, 0.4, 0.9, t);
      put(
        memo('luc', () => cone(0.6, 1.0, 4)),
        stone,
        x,
        y,
        zs + 2.5,
        t + Math.PI / 4,
      );
    }
    // Gilt crown, orb and cross.
    put(
      memo('crown', () =>
        latheG(
          [
            [0.3, 0],
            [0.62, 0.15],
            [0.7, 0.6],
            [0.55, 0.7],
            [0.0, 0.7],
          ],
          10,
        ),
      ),
      gold,
      0,
      0,
      zt - 0.2,
    );
    for (let j = 0; j < 8; j++) {
      const t = (j * Math.PI) / 4;
      put(
        memo('fleur', () => cone(0.12, 0.45, 4)),
        gold,
        Math.cos(t) * 0.62,
        Math.sin(t) * 0.62,
        zt + 0.72,
      );
    }
    put(
      memo('stem', () => cyl(0.1, 0.16, 0.8, 8)),
      gold,
      0,
      0,
      zt + 0.9,
    );
    put(
      memo('orb', () => sph(0.42, 12)),
      gold,
      0,
      0,
      zt + 1.6,
    );
    B(gold, 0, 0, zt + 1.9, 0.22, 0.22, 2.0);
    B(gold, 0, 0, zt + 3.0, 1.1, 0.22, 0.22);

    // ---- Seated gilt statue of Albert (faces south, -y local) on a granite pedestal.
    const zs0 = zC;
    B(granite, 0, 0.3, zs0, 3.8, 3.8, 0.4);
    B(greyGranite, 0, 0.3, zs0 + 0.4, 3.4, 3.4, 0.3);
    B(stone, 0, 0.3, zs0 + 0.7, 3.0, 3.0, 1.4);
    B(gold, 0, 0.3 - 1.51, zs0 + 1.1, 1.8, 0.04, 0.5); // inscription panel
    B(stone, 0, 0.3, zs0 + 2.1, 3.3, 3.3, 0.2);
    const zb = zs0 + 2.3;
    // chair with arms and a tall back
    B(gold, 0, 0.9, zb, 2.1, 1.3, 1.0);
    B(gold, 0, 1.5, zb, 2.1, 0.3, 3.3);
    for (const sx of [-1, 1]) B(gold, sx * 1.0, 0.7, zb + 1.0, 0.25, 1.2, 0.5);
    // Garter robe falling from the shoulders over the chair back and seat.
    put(
      memo('robeA', () =>
        latheG(
          [
            [0, 0],
            [1.0, 0],
            [0.95, 0.4],
            [0.7, 0.9],
            [0.62, 1.4],
            [0.68, 1.85],
            [0.5, 2.15],
            [0.2, 2.3],
            [0, 2.32],
          ],
          12,
        ),
      ),
      gold,
      0,
      0.8,
      zb + 1.0,
      0,
      1,
      0.75,
      1,
    );
    put(
      memo('cloak', () =>
        latheG(
          [
            [1.1, 0],
            [1.05, 0.6],
            [0.8, 1.6],
            [0.72, 2.3],
            [0.0, 2.35],
          ],
          12,
        ),
      ),
      gold,
      0,
      1.15,
      zb,
      0,
      1,
      0.45,
      1,
    );
    put(
      memo('neck', () => cyl(0.15, 0.18, 0.3, 8)),
      gold,
      0,
      0.72,
      zb + 3.4,
    );
    put(
      memo('headA', () => sph(0.3, 12)),
      gold,
      0,
      0.68,
      zb + 3.78,
      0,
      1,
      1.05,
      1.18,
    );
    for (const sx of [-0.4, 0.4]) {
      B(gold, sx, 0.1, zb + 0.85, 0.55, 1.55, 0.5); // thighs
      put(
        memo('knee', () => sph(0.3, 8)),
        gold,
        sx,
        -0.62,
        zb + 1.1,
      );
      B(gold, sx, -0.66, zb, 0.48, 0.46, 1.05); // shins
      B(gold, sx, -0.86, zb, 0.4, 0.42, 0.16); // feet
    }
    // arms: right hand holding the Great Exhibition catalogue on the knee
    put(
      memo('uarm', () => cyl(0.16, 0.19, 1.0, 8)),
      gold,
      0.72,
      0.6,
      zb + 2.35,
      0,
      1,
      1,
      1,
    );
    B(gold, 0.62, 0.0, zb + 1.7, 0.3, 1.1, 0.3, 0);
    B(gold, 0.45, -0.55, zb + 1.35, 0.6, 0.1, 0.8, 0);
    put(
      memo('uarm', () => cyl(0.16, 0.19, 1.0, 8)),
      gold,
      -0.72,
      0.6,
      zb + 2.35,
      0,
      1,
      1,
      1,
    );
    B(gold, -0.72, 0.15, zb + 1.75, 0.3, 0.9, 0.3, 0.1);

    // ---- Industrial Arts groups at the podium corners (marble, at canopy-floor level).
    const props = [
      (x, y, z) => B(marble, x + 0.6, y, z, 1.4, 0.3, 0.4), // Agriculture: plough
      (x, y, z) => B(marble, x - 0.5, y + 0.4, z, 0.7, 0.5, 0.7), // Manufacture: anvil
      (x, y, z) =>
        put(
          memo('bale', () => cyl(0.35, 0.35, 0.9, 8).rotateY(Math.PI / 2)),
          marble,
          x + 0.4,
          y - 0.5,
          z + 0.35,
        ), // Commerce
      (x, y, z) =>
        put(
          memo('wheel', () => new THREE.TorusGeometry(0.5, 0.08, 4, 12)),
          marble,
          x - 0.6,
          y - 0.3,
          z + 0.6,
        ), // Engineering
    ];
    [
      [-1, -1],
      [1, -1],
      [-1, 1],
      [1, 1],
    ].forEach(([sx, sy], k) => {
      const x = sx * (ph - 0.4),
        y = sy * (ph - 0.4),
        z = zC;
      B(marble, x, y, z, 3.2, 3.2, 0.4);
      const r = kit.rng(2.1 + k);
      const face = Math.atan2(sy, sx) - Math.PI / 2;
      figure(marble, x, y, z + 0.4, 2.6, face, 0.7);
      for (let i = 0; i < 3; i++) {
        const t = face + Math.PI / 2 + (i - 1) * 1.6 + (r() - 0.5) * 0.4;
        const fx = x + Math.cos(t) * 1.05,
          fy = y + Math.sin(t) * 1.05;
        if (i === 1) seated(marble, fx, fy, z + 0.4, 1.7, face);
        else figure(marble, fx, fy, z + 0.4, 2.2 - r() * 0.3, face + (r() - 0.5), r());
      }
      props[k](x, y, z + 0.4);
    });

    // ---- Continent groups on their footprints: stepped granite pedestal, animal, figures.
    const animal = (kind, x, y, z, rz, s) => {
      const c = Math.cos(rz),
        sn = Math.sin(rz);
      const at = (u, v) => [x + c * u - sn * v, y + sn * u + c * v];
      const P = (geo, u, v, w, sx = 1, sy = 1, sz = 1) => {
        const [px, py] = at(u * s, v * s);
        put(geo, marble, px, py, z + w * s, rz, sx * s, sy * s, sz * s);
      };
      const body = memo('body', () => sph(1, 12));
      const leg = memo('leg', () => cyl(0.16, 0.2, 1, 6));
      const kneel = kind === 'elephant';
      const legH = kneel ? 0.5 : kind === 'camel' ? 1.5 : 1.0;
      const bl = kind === 'elephant' ? 1.4 : kind === 'camel' ? 1.05 : 1.2;
      const bh = kind === 'elephant' ? 1.0 : 0.72;
      const bz = legH + bh * 0.8;
      P(body, 0, 0, bz, bl, 0.68 * (kind === 'elephant' ? 1.3 : 1), bh);
      for (const [lu, lv] of [
        [-0.65, -0.35],
        [0.65, -0.35],
        [-0.65, 0.35],
        [0.65, 0.35],
      ])
        P(leg, lu * bl, lv, (legH + 0.2) / 2, kneel ? 1.6 : 1, kneel ? 1.6 : 1, legH + 0.2);
      if (kind === 'elephant') {
        P(
          memo('eh', () => sph(0.6, 10)),
          -bl - 0.2,
          0,
          bz + 0.3,
        );
        P(
          memo('trunk', () => cyl(0.12, 0.2, 1.4, 6)),
          -bl - 0.65,
          0,
          bz - 0.5,
        );
        for (const v of [-0.55, 0.55])
          P(
            memo('ear', () => cyl(0.5, 0.5, 0.06, 10).rotateY(Math.PI / 2)),
            -bl - 0.05,
            v,
            bz + 0.3,
          );
        // howdah with rider
        P(
          memo('howdah', () => new THREE.BoxGeometry(1.2, 1.0, 0.6)),
          0,
          0,
          bz + bh * 0.95,
        );
      } else if (kind === 'camel') {
        P(
          memo('hump', () => sph(0.45, 8)),
          0.1,
          0,
          bz + bh * 0.85,
        );
        P(
          memo('cneck', () => cyl(0.16, 0.24, 1.3, 6).rotateY(-0.7)),
          -bl - 0.2,
          0,
          bz + 0.55,
        );
        P(
          memo('chead', () => sph(0.25, 8)),
          -bl - 0.65,
          0,
          bz + 1.15,
          1.6,
          0.9,
          0.9,
        );
      } else {
        // bison / bull: heavy shoulder hump, low head with horns
        if (kind === 'bison')
          P(
            memo('bhump', () => sph(0.6, 8)),
            -0.55,
            0,
            bz + 0.4,
            1,
            1,
            0.9,
          );
        P(
          memo('bhead', () => sph(0.4, 8)),
          -bl - 0.15,
          0,
          bz - 0.1,
          1.2,
          1,
          1,
        );
        for (const v of [-0.3, 0.3])
          P(
            memo('horn', () => cone(0.07, 0.45, 5)),
            -bl - 0.2,
            v,
            bz + 0.3,
          );
      }
      // rider seated on the back
      const [rx, ry] = at(0.1 * s, 0);
      seated(
        marble,
        rx,
        ry,
        z + (bz + bh * (kind === 'elephant' ? 1.6 : 0.85)) * s,
        1.3 * s,
        rz + Math.PI / 2,
      );
    };
    const kinds = {
      'a8cfc47f-900b-451f-a15e-c92c0ef63be0': 'bison', // America
      '6ff7d995-360f-4bc4-8d89-8ecb29b3d08b': 'camel', // Africa
      'c8159e6a-0e6d-4454-ad80-950285fe166d': 'bull', // Europe
      '93e65965-7e61-49fc-9473-1ff35f5b0360': 'elephant', // Asia
    };
    let seed = 11;
    for (const b of grp) {
      if (!b) continue;
      const [x, y] = local(b);
      const r = kit.rng(seed++);
      const s = 1.15;
      B(granite, x, y, 0, 4.3, 4.3, 0.5);
      B(greyGranite, x, y, 0.5, 4.0, 4.0, 0.9);
      B(granite, x, y, 1.4, 4.2, 4.2, 0.2);
      B(marble, x, y, 1.6, 3.8, 3.8, 0.45);
      const zf = 2.05;
      const out = Math.atan2(y, x); // facing outwards from the memorial
      animal(kinds[b.id], x, y, zf, out + Math.PI / 2, 0.95 * s);
      for (let k = 0; k < 4; k++) {
        const t = out + Math.PI / 4 + (k * Math.PI) / 2 + (r() - 0.5) * 0.3;
        const fx = x + Math.cos(t) * 1.45,
          fy = y + Math.sin(t) * 1.45;
        if (k === 1) seated(marble, fx, fy, zf, 1.45, t + Math.PI / 2);
        else figure(marble, fx, fy, zf, 1.95 + r() * 0.25, t + Math.PI / 2, r());
      }
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
