// Royal Hospital Chelsea (Sir Christopher Wren, 1682-92). Red brick ranges with
// stone dressings and hipped slate roofs around three courts: Figure Court, open
// to the river, flanked by College Court and Light Horse Court. The north range of
// Figure Court holds the Great Hall and Chapel either side of a central octagon
// vestibule fronted by a giant Doric portico under a pediment, crowned by Wren's
// cupola/lantern; a Tuscan loggia with a Latin inscription along its cornice runs
// either side of the portico. Grinling Gibbons' gilt statue of Charles II stands in
// the court.
export default {
  id: 'royal_hospital_chelsea',
  name: 'Royal Hospital Chelsea',
  claims: ['f5e5b611-fb1c-4626-9198-3abae1f5bfab'],
  references: [
    {
      title: 'The Royal Hospital: Architectural description - British History Online',
      url: 'https://prod.british-history.ac.uk/node/84422',
      used_for: 'central cupola over the vestibule between Great Hall and Chapel, court layout',
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
      used_for: 'general building description',
    },
  ],
  notes:
    'Footprint from Overture (h 7.5 m there is too low; eaves set to 12 m for the three-storey wards and 16 m for ' +
    'the Hall/Chapel range). Roofs are hipped volumes over hand-fitted rectangles, so junctions are simplified. ' +
    'Cupola height (~38 m) and dormer/chimney rhythm estimated; not measured.',
  build({ THREE, kit, buildings }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = (46.2 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const CX = 2955,
      CY = -2144;
    const W = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const rectRing = (u0, u1, v0, v1) => [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)];

    const brick = kit.facade('red_brick', 1);
    const brickSolid = kit.mat('#8f4c37', { roughness: 0.9 });
    const stone = kit.mat('portland_stone');
    const slate = kit.roof('slate', 0);
    const lead = kit.mat('lead');
    const gold = kit.mat('#e0b43a', { roughness: 0.35, metalness: 0.25 });
    const dark = kit.mat('dark_glass');
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = A) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));

    const EAVE = 12;
    // Brick walls on the real footprint with a stone cornice band.
    kit.walls(batch, brick, b.polys, 0, EAVE - 0.7, { bay: 3.4, storey: 3.6 });
    kit.walls(batch, stone, b.polys, EAVE - 0.7, EAVE, {});
    kit.cap(batch, kit.mat('#5a5f64'), b.polys, EAVE - 0.05);

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
      const along = u1 - u0 >= v1 - v0 ? A : A + Math.PI / 2;
      kit.pitchedRoof(batch, slate, brick, ring, along, e, r, 'hipped', { overhang: 0.4 });
      // chimney stacks along the ridge
      const n = Math.max(1, Math.floor(Math.max(u1 - u0, v1 - v0) / 22));
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n;
        const [x, y] =
          u1 - u0 >= v1 - v0
            ? W(u0 + 8 + t * (u1 - u0 - 16), (v0 + v1) / 2 + 3)
            : W((u0 + u1) / 2 + 3, v0 + 8 + t * (v1 - v0 - 16));
        kit.box(batch, brickSolid, x, y, e + 1, 1.2, 4.2, r + 2.6, A);
      }
      // dormers on the long slopes
      const L = Math.max(u1 - u0, v1 - v0),
        D = Math.min(u1 - u0, v1 - v0);
      for (let s = 4; s < L - 4; s += 6.8)
        for (const side of [-1, 1]) {
          const off = side * (D / 2 - 2.2);
          const [x, y] =
            u1 - u0 >= v1 - v0 ? W(u0 + s, (v0 + v1) / 2 + off) : W((u0 + u1) / 2 + off, v0 + s);
          kit.box(batch, lead, x, y, e + 0.4, 1.6, 1.6, 1.8, A);
        }
    }

    // Hall and Chapel range: taller brick block with tall round-headed windows.
    const hallMat = kit.paintedMaterial('royal_hospital_chelsea:hall', 256, 256, (c, w, h) => {
      c.fillStyle = '#8f4c37';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.77);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? 0 : 5; x < w; x += 10) {
          const k = 0.85 + r() * 0.25;
          c.fillStyle = `rgb(${(150 * k) | 0},${(78 * k) | 0},${(56 * k) | 0})`;
          c.fillRect(x, y, 9, 3);
        }
      for (let k = 0; k < 4; k++) {
        const x = k * 64 + 18;
        c.fillStyle = '#e4dccb';
        c.fillRect(x - 4, 30, 36, 190);
        c.fillStyle = '#e9e5da';
        c.beginPath();
        c.arc(x + 14, 46, 18, Math.PI, 0);
        c.fill();
        c.fillStyle = '#2f3940';
        c.fillRect(x, 46, 28, 170);
        c.beginPath();
        c.arc(x + 14, 46, 14, Math.PI, 0);
        c.fill();
        c.fillStyle = '#d8d0c0';
        for (let y = 70; y < 216; y += 26) c.fillRect(x, y, 28, 2);
        c.fillRect(x + 13, 40, 2, 176);
      }
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, h - 12, w, 12);
      c.fillRect(0, 0, w, 8);
    });
    const HALL = 17;
    const hall = rectRing(-35, 35, 30.5, 49.5);
    kit.walls(batch, hallMat, [[hall]], 0, HALL - 0.8, { bay: 4.4, storey: HALL / 2 });
    kit.walls(batch, stone, [[hall]], HALL - 0.8, HALL, {});
    kit.pitchedRoof(batch, slate, brick, hall, A, HALL, 6.5, 'hipped', { overhang: 0.5 });

    // Giant Doric portico with pediment on the Figure Court side (v = 29).
    const pv = 29,
      pd = 6.5; // front at v = pv - pd
    const colH = 9.75;
    for (const u of [-5.4, -1.8, 1.8, 5.4]) {
      const [x, y] = W(u, pv - pd + 0.9);
      put(
        stone,
        new THREE.CylinderGeometry(0.62, 0.72, colH, 16).rotateX(Math.PI / 2),
        x,
        y,
        0.6 + colH / 2,
      );
      kit.box(batch, stone, x, y, 0, 1.7, 1.7, 0.6, A);
      kit.box(batch, stone, x, y, 0.6 + colH, 1.6, 1.6, 0.5, A);
    }
    {
      const [x, y] = W(0, pv - pd / 2);
      kit.box(batch, stone, x, y, colH + 1.1, 13.4, pd + 0.6, 1.8, A); // entablature
      // pediment
      const tri = new THREE.Shape([
        new THREE.Vector2(-7, 0),
        new THREE.Vector2(7, 0),
        new THREE.Vector2(0, 3.4),
      ]);
      const pg = new THREE.ExtrudeGeometry(tri, { depth: pd + 0.6, bevelEnabled: false });
      pg.translate(0, 0, -(pd + 0.6) / 2).rotateX(Math.PI / 2);
      put(stone, pg, x, y, colH + 2.9);
      const [x2, y2] = W(0, pv - 0.5);
      kit.box(batch, dark, x2, y2, 0, 3, 0.4, 6.5, A); // central doorway
    }

    // Tuscan loggia either side of the portico with an inscribed frieze.
    const frieze = kit.paintedMaterial('royal_hospital_chelsea:frieze', 512, 32, (c, w, h) => {
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#5a5248';
      c.font = 'bold 18px serif';
      c.fillText('IN SUBSIDIUM ET LEVAMEN EMERITORUM SENIO BELLOQUE FRACTORUM', 6, 22);
    });
    for (const side of [-1, 1]) {
      const u0 = side < 0 ? -34 : 8,
        u1 = side < 0 ? -8 : 34;
      for (let u = u0 + 1; u <= u1 - 1 + 1e-6; u += (u1 - u0 - 2) / 8) {
        const [x, y] = W(u, 26.2);
        put(stone, new THREE.CylinderGeometry(0.32, 0.36, 4.6, 10).rotateX(Math.PI / 2), x, y, 2.3);
      }
      const [x, y] = W((u0 + u1) / 2, 27.6);
      kit.box(batch, frieze, x, y, 4.6, u1 - u0, 3.4, 1.4, A);
      kit.box(batch, lead, x, y, 6.0, u1 - u0, 3.6, 0.3, A);
    }

    // Wren's cupola: square stone base, octagonal drum, lead dome and lantern.
    {
      const [x, y] = W(0, 40);
      const z0 = HALL + 4.5;
      kit.box(batch, stone, x, y, HALL, 9, 9, 4.8, A);
      put(
        stone,
        new THREE.CylinderGeometry(3.6, 3.6, 6, 8).rotateX(Math.PI / 2),
        x,
        y,
        z0 + 3,
        A + Math.PI / 8,
      );
      for (let k = 0; k < 8; k++) {
        const t = A + Math.PI / 8 + (k * Math.PI) / 4 + Math.PI / 8;
        const wx = x + Math.cos(t) * 3.35,
          wy = y + Math.sin(t) * 3.35;
        kit.box(batch, dark, wx, wy, z0 + 1, 1.4, 0.4, 3.8, t + Math.PI / 2);
      }
      const dome = new THREE.SphereGeometry(3.9, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      dome.scale(1, 1, 1.15);
      put(lead, dome, x, y, z0 + 6, 0);
      put(
        lead,
        new THREE.CylinderGeometry(1.1, 1.2, 2.6, 8).rotateX(Math.PI / 2),
        x,
        y,
        z0 + 11.6,
        A,
      );
      put(lead, new THREE.ConeGeometry(1.3, 2.2, 8).rotateX(Math.PI / 2), x, y, z0 + 14, A);
      put(gold, new THREE.SphereGeometry(0.45, 10, 6), x, y, z0 + 15.4, 0);
      put(
        gold,
        new THREE.CylinderGeometry(0.07, 0.07, 1.6, 4).rotateX(Math.PI / 2),
        x,
        y,
        z0 + 16.3,
        0,
      );
    }

    // Gilt statue of Charles II on a stone pedestal in Figure Court.
    {
      const [x, y] = W(0, -15);
      kit.box(batch, stone, x, y, 0, 3.2, 3.2, 0.6, A);
      kit.box(batch, stone, x, y, 0.6, 2, 2, 2.6, A);
      put(gold, new THREE.CylinderGeometry(0.35, 0.5, 2.2, 8).rotateX(Math.PI / 2), x, y, 4.3, A);
      put(gold, new THREE.SphereGeometry(0.3, 8, 6), x, y, 5.7, 0);
      // court lawns
      const lawn = kit.mat('grass');
      for (const s of [-1, 1]) {
        const ring = rectRing(s < 0 ? -31 : 4, s < 0 ? -4 : 31, -62, 20);
        kit.cap(batch, lawn, [[ring]], 0.06);
      }
    }

    g.add(batch.toGroup('royal_hospital_chelsea'));
    return g;
  },
};
