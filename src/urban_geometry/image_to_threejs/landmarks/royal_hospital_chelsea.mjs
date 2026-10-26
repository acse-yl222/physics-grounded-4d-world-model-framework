// Royal Hospital Chelsea (Sir Christopher Wren, 1682-92). Red brick ranges with
// stone dressings and hipped slate roofs around three courts: Figure Court, open
// to the river, flanked by College Court and Light Horse Court. The long wards
// have three storeys of square-headed sash windows and a fourth floor of dormers.
// The north range of Figure Court holds the Great Hall and Chapel (large
// round-headed windows) either side of a central octagon vestibule fronted by a
// portico of four three-quarter Roman Doric columns under a pediment with a clock,
// crowned by Wren's cupola/lantern; a Doric loggia with a Latin inscription along
// its cornice runs either side of the portico. Grinling Gibbons' gilt statue of
// Charles II stands in the court.
export default {
  id: 'royal_hospital_chelsea',
  name: 'Royal Hospital Chelsea',
  claims: ['f5e5b611-fb1c-4626-9198-3abae1f5bfab'],
  references: [
    {
      title: 'The Royal Hospital: Architectural description - British History Online',
      url: 'https://prod.british-history.ac.uk/node/84422',
      used_for:
        'central cupola over the vestibule, court layout, portico of four three-quarter Roman Doric columns with painted-wood pediment furnished with a clock, lantern over the door',
    },
    {
      title: 'Royal Hospital Chelsea - Bluffton University photo pages',
      url: 'https://homepages.bluffton.edu/~Sullivanm/england/london/wrenchelsea/hospital.html',
      used_for:
        'Figure Court colonnade, 32 ft Doric portico columns, inscription along the loggia cornice',
    },
    {
      title:
        "The Royal Hospital Chelsea: Inside Christopher Wren's masterpiece in SW3 - Country Life",
      url: 'https://www.countrylife.co.uk/architecture/the-royal-hospital-chelsea-inside-christopher-wrens-masterpiece-in-sw3-257893',
      used_for: 'red brick with stone dressings, Figure Court as the oldest part',
    },
    {
      title: 'Royal Hospital Chelsea - Chelsea Pensioners',
      url: 'https://www.chelsea-pensioners.co.uk/node/23',
      used_for:
        'four-floor wards with square-headed windows and dormers, round-headed windows of the north building, octagon cupola and lantern rising to 130 ft',
    },
  ],
  notes:
    'Footprint from Overture (h 7.5 m there is too low; eaves set to 12 m for the three-storey wards and 17 m for ' +
    'the Hall/Chapel range). Roofs are hipped volumes over hand-fitted rectangles, so junctions are simplified. ' +
    'Cupola/lantern top at ~39 m (130 ft per the Chelsea Pensioners page). Window, dormer and chimney rhythm, quoins ' +
    'and the river-front pavilion pediments are estimated, not measured; sash glazing bars are painted on the glass.',
  build({ THREE, kit, buildings, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = (46.2 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const CX = 2955,
      CY = -2144;
    const W = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const L = ([x, y]) => [(x - CX) * ca + (y - CY) * sa, -(x - CX) * sa + (y - CY) * ca];
    const rectRing = (u0, u1, v0, v1) => [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)];

    const brickC = '#8f4c37';
    const brick = kit.paintedMaterial(
      'royal_hospital_chelsea:brick',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = brickC;
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.77);
        for (let y = 0; y < h; y += 3)
          for (let x = (y / 3) % 2 ? 0 : 4; x < w; x += 8) {
            const k = 0.85 + r() * 0.25;
            c.fillStyle = `rgb(${(150 * k) | 0},${(78 * k) | 0},${(56 * k) | 0})`;
            c.fillRect(x, y, 7, 2);
          }
      },
      { roughness: 0.9 },
    );
    const brickSolid = kit.mat(brickC, { roughness: 0.9 });
    const rubbed = kit.mat('#b0634a', { roughness: 0.85 });
    const stone = kit.mat('portland_stone');
    const paint = kit.mat('#efeae0', { roughness: 0.6 });
    const slate = kit.roof('slate', 0);
    const lead = kit.mat('lead');
    const gold = kit.mat('#e0b43a', { roughness: 0.35, metalness: 0.25 });
    const dark = kit.mat('dark_glass');
    const sash = kit.paintedMaterial(
      'royal_hospital_chelsea:sash',
      48,
      96,
      (c, w, h) => {
        // six-over-six sash: dark panes, white bars, meeting rail
        c.fillStyle = '#f1eee6';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#26313a';
        const pw = (w - 8) / 3,
          ph = (h - 14) / 4;
        for (let i = 0; i < 3; i++)
          for (let j = 0; j < 4; j++)
            c.fillRect(2 + i * (pw + 2), 2 + j * (ph + 2) + (j >= 2 ? 4 : 0), pw, ph);
      },
      { roughness: 0.3 },
    );
    const arched = kit.paintedMaterial(
      'royal_hospital_chelsea:hallglass',
      64,
      160,
      (c, w, h) => {
        c.fillStyle = '#e9e5da';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#2b353d';
        for (let i = 0; i < 4; i++)
          for (let j = 0; j < 10; j++) c.fillRect(2 + i * 15, 2 + j * 16, 13, 14);
      },
      { roughness: 0.3 },
    );
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = A) => {
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));
      geo.dispose();
    };
    const cyl = (r0, r1, h, seg = 16) =>
      new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
    const latheB = (mat, prof, x, y, z, seg = 24) =>
      put(
        mat,
        new THREE.LatheGeometry(
          prof.map(([r, h]) => new THREE.Vector2(r, h)),
          seg,
        ).rotateX(Math.PI / 2),
        x,
        y,
        z,
        0,
      );
    // triangular prism (pediment / dormer roof): base width w, rise h, depth d, along edge angle rz
    const pediment = (mat, x, y, z, w, h, d, rz) => {
      const tri = new THREE.Shape([
        new THREE.Vector2(-w / 2, 0),
        new THREE.Vector2(w / 2, 0),
        new THREE.Vector2(0, h),
      ]);
      const pg = new THREE.ExtrudeGeometry(tri, { depth: d, bevelEnabled: false });
      pg.translate(0, 0, -d / 2).rotateX(Math.PI / 2);
      put(mat, pg, x, y, z, rz);
    };

    const EAVE = 12;
    let outer = b.polys[0][0].slice();
    if (kit.ringArea(outer) < 0) outer.reverse();
    // Brick walls on the real footprint; stone plinth, first-floor band, eaves cornice.
    kit.walls(batch, brick, [[outer]], 0, EAVE - 0.7, { bay: 3.4, storey: 3.6 });
    kit.cornice(batch, stone, outer, 0, { height: 0.8, projection: 0.18 });
    kit.cornice(batch, stone, outer, 3.85, { height: 0.3, projection: 0.12 });
    kit.walls(batch, paint, [[outer]], EAVE - 0.7, EAVE, {});
    kit.cornice(batch, paint, outer, EAVE - 0.55, { height: 0.55, projection: 0.5, steps: 3 });
    kit.cap(batch, kit.mat('#5a5f64'), [[outer]], EAVE - 0.05);

    // Hall / Chapel range edges are detailed separately.
    const isHallEdge = (p, q) => {
      const a = L(p),
        c = L(q);
      return Math.abs(a[0]) < 36 && Math.abs(c[0]) < 36 && a[1] > 25 && c[1] > 25;
    };
    // Square-headed sash windows on three storeys, stone sills, rubbed-brick heads;
    // stone quoins at the corners of the main faces.
    for (let k = 0; k < outer.length; k++) {
      const p = outer[k],
        q = outer[(k + 1) % outer.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 5 || isHallEdge(p, q)) continue;
      for (let s = 0; s < 3; s++)
        kit.windowRow(batch, p, q, 1.2 + s * 3.6, {
          width: 1.25,
          height: s === 0 ? 2.3 : 2.4,
          bay: 3.5,
          margin: 1.4,
          depth: 0.14,
          glass: sash,
          frame: paint,
          sill: rubbed, // rubbed-brick sills and flat-arch heads
          head: 'lintel',
          bars: 0,
        });
      if (len > 10) {
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len;
        const ang = Math.atan2(uy, ux);
        for (const [cx, cy, sgn] of [
          [p[0], p[1], 1],
          [q[0], q[1], -1],
        ])
          for (let j = 0; j < 10; j++) {
            const wq = j % 2 ? 0.55 : 0.95;
            kit.box(
              batch,
              stone,
              cx + ux * sgn * (wq / 2) + uy * 0.04,
              cy + uy * sgn * (wq / 2) - ux * 0.04,
              0.8 + j * 1.07,
              wq,
              0.1,
              0.5,
              ang,
            );
          }
      }
    }

    // Ranges: [u0, u1, v0, v1, eave, rise]
    const ranges = [
      [-122, -35, 34, 51, EAVE, 5.5], // west main range
      [35, 123, 35, 51.5, EAVE, 5.5], // east main range
      [-49, -35, -65, 34, EAVE, 5], // west wing of Figure Court
      [35, 51, -65, 34, EAVE, 5], // east wing of Figure Court
      [-122, -49, -65, -47, EAVE, 5], // south range of College Court
      [51, 122, -63, -47, EAVE, 5], // south range of Light Horse Court
    ];
    for (const [u0, u1, v0, v1, e, r] of ranges) {
      const ring = rectRing(u0, u1, v0, v1);
      const longU = u1 - u0 >= v1 - v0;
      const along = longU ? A : A + Math.PI / 2;
      kit.pitchedRoof(batch, slate, brick, ring, along, e, r, 'hipped', { overhang: 0.4 });
      // chimney stacks along the ridge: stone caps and pots
      const n = Math.max(1, Math.floor(Math.max(u1 - u0, v1 - v0) / 22));
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n;
        const [x, y] = longU
          ? W(u0 + 8 + t * (u1 - u0 - 16), (v0 + v1) / 2 + 3)
          : W((u0 + u1) / 2 + 3, v0 + 8 + t * (v1 - v0 - 16));
        const rz = longU ? A : A + Math.PI / 2;
        kit.box(batch, brickSolid, x, y, e + 1, 4.2, 1.2, r + 2.6, rz);
        kit.box(batch, stone, x, y, e + r + 3.0, 4.5, 1.5, 0.35, rz);
        for (let j = 0; j < 4; j++) {
          const o = -1.5 + j;
          put(
            kit.mat('#b26a4c'),
            cyl(0.2, 0.16, 0.8, 8),
            x + Math.cos(rz) * o,
            y + Math.sin(rz) * o,
            e + r + 3.75,
          );
        }
      }
      // pedimented dormers with sash windows on the long slopes
      const Lr = Math.max(u1 - u0, v1 - v0),
        D = Math.min(u1 - u0, v1 - v0);
      for (let s = 5; s < Lr - 4; s += 7)
        for (const side of [-1, 1]) {
          const off = side * (D / 2 - 1.6);
          const [x, y] = longU ? W(u0 + s, (v0 + v1) / 2 + off) : W((u0 + u1) / 2 + off, v0 + s);
          const face = longU
            ? A + (side < 0 ? 0 : Math.PI)
            : A + Math.PI / 2 + (side < 0 ? Math.PI : 0);
          // face angle: dormer front faces outwards (perpendicular to the slope)
          const fx = Math.cos(face - Math.PI / 2),
            fy = Math.sin(face - Math.PI / 2);
          kit.box(batch, lead, x, y, e + 0.2, 1.7, 1.8, 2.0, face);
          kit.box(batch, paint, x + fx * 0.92, y + fy * 0.92, e + 0.45, 1.3, 0.08, 1.5, face);
          kit.box(batch, sash, x + fx * 0.96, y + fy * 0.96, e + 0.55, 1.0, 0.04, 1.3, face);
          pediment(lead, x, y, e + 2.2, 2.0, 0.8, 1.9, face);
        }
    }

    // Hall and Chapel range: taller brick block with tall round-headed windows.
    const HALL = 17;
    const hall = rectRing(-35, 35, 30.5, 49.5);
    kit.walls(batch, brick, [[hall]], 0, HALL - 0.8, { bay: 4.4, storey: 3.6 });
    kit.cornice(batch, stone, hall, 0, { height: 0.9, projection: 0.2 });
    kit.walls(batch, paint, [[hall]], HALL - 0.8, HALL, {});
    kit.cornice(batch, paint, hall, HALL - 0.7, { height: 0.7, projection: 0.6, steps: 3 });
    kit.pitchedRoof(batch, slate, brick, hall, A, HALL, 6.5, 'hipped', { overhang: 0.5 });
    // round-headed windows: north side full height, court side above the loggia roof
    for (const [a, c, sill, hgt] of [
      [W(35, 49.5), W(-35, 49.5), 4.5, 8.6],
      [W(-35, 30.5), W(-8.5, 30.5), 7.6, 6.2],
      [W(8.5, 30.5), W(35, 30.5), 7.6, 6.2],
    ])
      kit.windowRow(batch, a, c, sill, {
        width: 2.4,
        height: hgt,
        bay: 4.4,
        margin: 1.2,
        depth: 0.2,
        glass: arched,
        frame: paint,
        sill: stone,
        head: 'arch',
        bars: 0,
        surround: 0.35,
        surroundMat: stone,
      });

    // Portico of four three-quarter Roman Doric columns with entablature and a
    // pediment carrying a clock (court side, v = 29).
    const pv = 29,
      pd = 2.2; // engaged portico: shallow projection
    const colH = 9.75;
    {
      const [fx, fy] = W(-7, pv - pd + 0.9),
        [gx, gy] = W(7, pv - pd + 0.9);
      kit.colonnade(batch, stone, [fx, fy], [gx, gy], 0.6, colH, {
        count: 4,
        radius: 0.68,
        capital: 'doric',
        segments: 16,
      });
      const [x, y] = W(0, pv - pd / 2);
      kit.box(batch, stone, x, y, 0, 15, pd + 1.6, 0.6, A); // steps / stylobate
      kit.box(batch, stone, x, y - 0, 0.6, 14.4, 0.6, colH, A); // back wall plane
      kit.box(batch, paint, x, y, colH + 0.6, 14.6, pd + 0.8, 0.7, A); // architrave
      kit.box(batch, paint, x, y, colH + 1.3, 14.6, pd + 0.8, 0.8, A); // frieze
      kit.box(batch, paint, x, y, colH + 2.1, 15.4, pd + 1.2, 0.45, A); // cornice
      pediment(paint, x, y, colH + 2.55, 15.4, 3.4, pd + 1.2, A);
      // triglyphs
      for (let k = 0; k < 9; k++) {
        const [tx, ty] = W(-6.8 + k * 1.7, pv - pd - 0.42);
        kit.box(batch, stone, tx, ty, colH + 1.35, 0.5, 0.06, 0.7, A);
      }
      // clock in the tympanum
      const clock = kit.paintedMaterial('royal_hospital_chelsea:clock', 128, 128, (c, w, h) => {
        c.fillStyle = '#20252a';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#f3efe2';
        c.beginPath();
        c.arc(64, 64, 56, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = '#20252a';
        for (let k = 0; k < 12; k++) {
          const t = (k * Math.PI) / 6;
          c.fillRect(64 + Math.cos(t) * 46 - 2, 64 + Math.sin(t) * 46 - 2, 5, 5);
        }
        c.lineWidth = 5;
        c.strokeStyle = '#d6b04c';
        c.beginPath();
        c.moveTo(64, 64);
        c.lineTo(64, 22);
        c.moveTo(64, 64);
        c.lineTo(92, 72);
        c.stroke();
      });
      const [kx, ky] = W(0, pv - pd - 0.62);
      const cg = new THREE.CircleGeometry(1.0, 24).rotateX(Math.PI / 2);
      put(clock, cg, kx, ky, colH + 3.7);
      // central doorway with lantern over it
      const [x2, y2] = W(0, pv - pd - 0.35);
      kit.box(batch, dark, x2, y2, 0.6, 2.6, 0.2, 5.4, A);
      kit.box(batch, paint, x2, y2, 6.0, 3.4, 0.3, 0.4, A);
      put(dark, cyl(0.35, 0.35, 0.8, 6), ...W(0, pv - pd - 0.9), 6.9);
      put(
        lead,
        new THREE.ConeGeometry(0.45, 0.5, 6).rotateX(Math.PI / 2),
        ...W(0, pv - pd - 0.9),
        7.55,
      );
    }

    // Doric loggia either side of the portico with the inscribed frieze.
    const frieze = kit.paintedMaterial('royal_hospital_chelsea:frieze', 1024, 32, (c, w, h) => {
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#4a4238';
      c.font = 'bold 20px serif';
      c.textAlign = 'center';
      c.fillText(
        'IN SUBSIDIUM ET LEVAMEN EMERITORUM SENIO BELLOQUE FRACTORUM CONDIDIT CAROLUS SECUNDUS',
        w / 2,
        23,
      );
    });
    for (const side of [-1, 1]) {
      const u0 = side < 0 ? -34 : 8.5,
        u1 = side < 0 ? -8.5 : 34;
      const [ax, ay] = W(u0 + 0.8, 26.0),
        [bx, by] = W(u1 - 0.8, 26.0);
      kit.colonnade(batch, stone, [ax, ay], [bx, by], 0.35, 4.3, {
        count: 9,
        radius: 0.34,
        capital: 'doric',
        segments: 12,
      });
      const [x, y] = W((u0 + u1) / 2, 27.6);
      kit.box(batch, stone, x, y, 0, u1 - u0, 4.0, 0.35, A); // floor
      kit.box(batch, frieze, x, y, 4.65, u1 - u0, 3.4, 1.1, A);
      kit.box(batch, stone, x, y, 5.75, u1 - u0 + 0.3, 3.8, 0.3, A);
      kit.box(batch, lead, x, y, 6.05, u1 - u0, 3.4, 0.25, A);
      // arched doorways in the back wall
      kit.windowRow(batch, W(u0, 29.9), W(u1, 29.9), 0.35, {
        width: 1.5,
        height: 2.8,
        bay: 3.2,
        margin: 1,
        depth: 0.15,
        glass: dark,
        frame: paint,
        sill: stone,
        head: 'arch',
        bars: 0,
      });
    }

    // River-front pavilions of the Figure Court wings: stone pilasters and pediment.
    for (const [u0, u1] of [
      [-49, -35],
      [35, 51],
    ]) {
      const vf = -64.85;
      const [x, y] = W((u0 + u1) / 2, vf - 0.2);
      for (let k = 0; k < 4; k++) {
        const [px, py] = W(u0 + 1.5 + (k * (u1 - u0 - 3)) / 3, vf - 0.25);
        kit.box(batch, stone, px, py, 0.8, 0.9, 0.5, EAVE - 1.4, A);
      }
      kit.box(batch, stone, x, y, EAVE - 0.9, u1 - u0, 0.7, 0.9, A);
      pediment(stone, x, y, EAVE, u1 - u0 + 0.6, 3.0, 1.0, A);
      kit.box(batch, dark, ...W((u0 + u1) / 2, vf - 0.1), 0.8, 1.8, 0.12, 3.2, A);
    }

    // Wren's cupola: square base, octagonal arcaded drum, lead ogee dome, lantern,
    // ball and vane (top at ~39 m).
    {
      const [x, y] = W(0, 40);
      const z0 = HALL + 4.2;
      kit.box(batch, paint, x, y, HALL, 9.4, 9.4, 4.2, A);
      kit.box(batch, paint, x, y, HALL + 4.0, 10.0, 10.0, 0.45, A);
      put(lead, cyl(3.9, 3.9, 0.6, 8), x, y, z0 + 0.7, A + Math.PI / 8);
      put(paint, cyl(3.6, 3.6, 5.6, 8), x, y, z0 + 3.8, A + Math.PI / 8);
      for (let k = 0; k < 8; k++) {
        const t = A + (k * Math.PI) / 4;
        const r0 = 3.6 * Math.cos(Math.PI / 8);
        const wx = x + Math.cos(t) * (r0 + 0.02),
          wy = y + Math.sin(t) * (r0 + 0.02);
        kit.box(batch, dark, wx, wy, z0 + 1.6, 1.4, 0.1, 3.0, t + Math.PI / 2);
        // pilaster at each angle
        const tp = t + Math.PI / 8;
        const R2 = 3.62;
        kit.box(
          batch,
          paint,
          x + Math.cos(tp) * R2,
          y + Math.sin(tp) * R2,
          z0 + 1,
          0.45,
          0.45,
          5.6,
          tp,
        );
      }
      put(paint, cyl(4.0, 4.0, 0.6, 8), x, y, z0 + 6.9, A + Math.PI / 8);
      latheB(
        lead,
        [
          [3.7, 0],
          [3.75, 0.6],
          [3.5, 1.8],
          [2.9, 3.0],
          [2.0, 3.9],
          [1.4, 4.3],
          [1.0, 4.6],
          [0.9, 4.8],
        ],
        x,
        y,
        z0 + 7.2,
        24,
      );
      // open lantern with posts, ogee cap, gilt ball and vane
      const zl = z0 + 12;
      put(lead, cyl(1.2, 1.2, 0.3, 8), x, y, zl, A);
      for (let k = 0; k < 8; k++) {
        const t = A + (k * Math.PI) / 4 + Math.PI / 8;
        kit.box(
          batch,
          paint,
          x + Math.cos(t) * 1.0,
          y + Math.sin(t) * 1.0,
          zl + 0.15,
          0.22,
          0.22,
          2.2,
          t,
        );
      }
      put(dark, cyl(0.85, 0.85, 2.2, 8), x, y, zl + 1.25, A);
      put(paint, cyl(1.3, 1.3, 0.3, 8), x, y, zl + 2.45, A);
      latheB(
        lead,
        [
          [1.25, 0],
          [1.1, 0.5],
          [0.6, 1.1],
          [0.25, 1.6],
          [0.12, 2.2],
        ],
        x,
        y,
        zl + 2.6,
        16,
      );
      put(gold, new THREE.SphereGeometry(0.42, 12, 8), x, y, zl + 5.0, 0);
      put(gold, cyl(0.05, 0.05, 2.0, 4), x, y, zl + 6.2, 0);
      kit.box(batch, gold, x, y, zl + 6.4, 1.2, 0.05, 0.4, A);
    }

    // Gilt statue of Charles II (Grinling Gibbons) on a stone pedestal in Figure Court.
    {
      const [x, y] = W(0, -15);
      kit.box(batch, stone, x, y, 0, 3.6, 3.6, 0.5, A);
      kit.box(batch, stone, x, y, 0.5, 2.6, 2.6, 0.5, A);
      kit.box(batch, stone, x, y, 1.0, 2.0, 2.0, 2.2, A);
      kit.box(batch, stone, x, y, 3.2, 2.5, 2.5, 0.4, A);
      latheB(
        gold,
        [
          [0, 0],
          [0.55, 0],
          [0.5, 0.9],
          [0.38, 1.3],
          [0.42, 1.7],
          [0.3, 1.95],
          [0.12, 2.0],
          [0.16, 2.1],
          [0.2, 2.3],
          [0.15, 2.45],
          [0, 2.5],
        ],
        x,
        y,
        3.6,
        16,
      );
      kit.box(batch, gold, ...W(0.45, -15.2), 4.9, 0.18, 0.7, 0.18, A + 0.4); // baton arm
      // court lawns with gravel paths, iron railings around the statue enclosure
      const lawn = kit.mat('grass');
      for (const s of [-1, 1]) {
        const ring = rectRing(s < 0 ? -31 : 4, s < 0 ? -4 : 31, -62, 20);
        kit.cap(batch, lawn, [[ring]], 0.06);
      }
      kit.cap(batch, kit.mat('gravel'), [[rectRing(-34, 34, -64, 24)]], 0.03);
      const rr = [W(-4, -19), W(4, -19), W(4, -11), W(-4, -11), W(-4, -19)];
      kit.balustrade(batch, kit.mat('black'), rr, 0, { height: 1.0, spacing: 0.25 });
    }

    // Lamps along the central walk and benches under the loggia.
    const lamps = [];
    for (let v = -58; v <= 18; v += 12)
      for (const u of [-3.2, 3.2])
        lamps.push([...W(u, v), A + (u < 0 ? -Math.PI / 2 : Math.PI / 2)]);
    const benches = [];
    for (const u of [-26, -16, 16, 26]) benches.push([...W(u, 27.8), A + Math.PI]);
    g.add(placeAssets('street_lamp', lamps, { name: 'royal_hospital_chelsea:lamps' }));
    g.add(placeAssets('bench', benches, { name: 'royal_hospital_chelsea:benches' }));

    g.add(batch.toGroup('royal_hospital_chelsea'));
    return g;
  },
};
