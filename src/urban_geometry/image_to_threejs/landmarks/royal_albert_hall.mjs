// Royal Albert Hall, Kensington Gore (Francis Fowke and Henry Y. D. Scott, 1867-1871).
// Elliptical amphitheatre in Fareham red brick with buff terracotta dressings: an
// arcaded drum of three storeys of round-arched windows, an open gallery loggia under
// a continuous mosaic frieze ("The Triumph of Arts and Sciences", ~25 m above ground)
// with the dedication inscription and a balustraded cornice, and a shallow wrought
// iron and glass dome (~41 m) with a small central lantern. Four projecting porches
// (north to Kensington Gore, south to Prince Consort Road, east and west).
export default {
  id: 'royal_albert_hall',
  name: 'Royal Albert Hall',
  claims: ['f8dc8756-8083-4501-8b2d-1ec37d51d0a3', '7bb7d9b1-86fb-4516-914a-32d48fcffcc0'],
  references: [
    {
      title: 'Royal Albert Hall - Designing Buildings Wiki',
      url: 'https://designingbuildings.co.uk/wiki/Royal_Albert_Hall',
      used_for:
        'elliptical plan 83 x 72 m, glass and wrought-iron dome ~41 m high, Fareham red brick',
    },
    {
      title: 'Royal Albert Hall - victorianweb.org',
      url: 'https://victorianweb.org/art/architecture/alberthall',
      used_for:
        'red brick and terracotta facade, view from the Albert Memorial across Kensington Gore',
    },
    {
      title: 'The Royal Albert Hall frieze - Art UK',
      url: 'https://artuk.org/discover/stories/the-royal-albert-hall-frieze-the-art-that-surrounds-the-worlds-most-famous-stage',
      used_for: 'mosaic frieze about 25 m above ground running round the whole 244 m circumference',
    },
    {
      title: 'Royal Albert Hall - Archivision (CU Digital Library)',
      url: 'https://cudl.colorado.edu/luna/servlet/detail/ARCHIVISIONBASETO9~1~1~59565~1206427:Royal-Albert-Hall',
      used_for: 'terracotta inscription letters along the top of the drum',
    },
    {
      title: 'Royal Albert Hall - Bluffton University photo page',
      url: 'https://homepages.bluffton.edu/~sullivanm/england/london/alberthall/alberthall.html',
      used_for: 'terracotta frieze of 16 allegorical groups; south porch rebuilt 1996-2004',
    },
  ],
  notes:
    'Drum, porches and dome follow the 11 Overture parts (drum 25 m, dome springing ~29 m to 43.8 m, lantern 46.6 m). ' +
    'Bay count (40) and storey divisions of the facade are proportioned from photo descriptions, not measured. ' +
    'Frieze figures are suggested by an abstract buff-on-brown pattern; porch elevations are simplified (arched ground floor, ' +
    'windows, pediment). Chimney stack height kept at the data value.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const hall = byId['f8dc8756-8083-4501-8b2d-1ec37d51d0a3'];
    const parts = Object.fromEntries((hall?.parts ?? []).map((p) => [p.id.slice(0, 8), p]));
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const ringOf = (id) => ccw(parts[id].polys[0][0]);
    const drum = ringOf('39a1fefa');
    const inner = ringOf('8650298d');
    const lantern = ringOf('33326746');

    const BRICK = '#9a4a34',
      TC = '#d2b48a',
      TC_D = '#b89a70',
      DARK = '#2a2f36';
    // ---- Drum facade: one 6.2 m bay x 25 m painted from photo descriptions.
    const PX = 41; // px per metre
    const drumMat = kit.paintedMaterial('royal_albert_hall:bay', 256, 1024, (c, w, h) => {
      const Y = (m) => h - m * PX;
      const band = (z0, z1, col) => {
        c.fillStyle = col;
        c.fillRect(0, Y(z1), w, (z1 - z0) * PX);
      };
      const arch = (x, z0, z1, ww, col) => {
        const r = ww / 2;
        c.fillStyle = col;
        c.fillRect(x - r, Y(z1) + r, ww, Y(z0) - Y(z1) - r);
        c.beginPath();
        c.arc(x, Y(z1) + r, r, Math.PI, 0);
        c.fill();
      };
      band(0, 25, BRICK);
      // brick coursing texture
      c.fillStyle = 'rgba(0,0,0,0.06)';
      for (let y = 0; y < h; y += 5) c.fillRect(0, y, w, 1);
      band(0, 1.1, '#b9a689'); // plinth
      // Ground storey: tall round arched doorway / window with terracotta surround.
      arch(w / 2, 1.1, 6.2, 92, TC);
      arch(w / 2, 1.1, 5.9, 76, '#3a2f2a');
      band(6.4, 7.1, TC);
      // First storey: paired arched windows.
      for (const dx of [-46, 46]) {
        arch(w / 2 + dx, 7.6, 11.8, 64, TC);
        arch(w / 2 + dx, 7.7, 11.6, 50, DARK);
      }
      band(12.1, 12.7, TC);
      // Second storey: smaller arched windows.
      for (const dx of [-62, 0, 62]) {
        arch(w / 2 + dx, 13.1, 15.4, 40, TC_D);
        arch(w / 2 + dx, 13.2, 15.3, 30, DARK);
      }
      band(15.6, 16.4, TC); // balcony line
      c.fillStyle = TC_D;
      for (let x = 4; x < w; x += 10) c.fillRect(x, Y(16.4) - 0, 4, 6);
      // Gallery loggia: terracotta columns with three arched openings per bay.
      band(16.4, 21.4, TC);
      for (const dx of [-80, 0, 80]) arch(w / 2 + dx, 16.6, 21.0, 58, '#1f2328');
      c.fillStyle = TC_D;
      for (const dx of [-120, -40, 40, 120]) c.fillRect(w / 2 + dx - 5, Y(21.0), 10, 4.4 * PX);
      // Mosaic frieze (buff figures on chocolate ground).
      band(21.4, 23.6, '#5a3a2a');
      band(21.4, 21.6, TC);
      band(23.4, 23.6, TC);
      const r = kit.rng(7.31);
      for (let k = 0; k < 9; k++) {
        const x = 10 + k * 27 + r() * 6;
        c.fillStyle = r() < 0.5 ? '#e2cfa6' : '#cdb07c';
        c.fillRect(x, Y(23.2), 9, 1.4 * PX);
        c.beginPath();
        c.arc(x + 4.5, Y(23.2) - 2, 5, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = '#a9483a';
        c.fillRect(x + 9, Y(22.6), 8, 0.7 * PX);
      }
      // Inscription band and cornice.
      band(23.6, 24.3, '#e3d3b2');
      c.fillStyle = '#6a4a35';
      for (let x = 3; x < w - 4; x += 9) if (r() > 0.18) c.fillRect(x, Y(24.2), 6, 0.5 * PX);
      band(24.3, 25, '#d9c6a0');
      // Pilasters between bays.
      c.fillStyle = 'rgba(70,25,15,0.35)';
      c.fillRect(0, Y(16.4), 7, 15.3 * PX);
      c.fillRect(w - 7, Y(16.4), 7, 15.3 * PX);
    });

    // Walls along a ring with u measured in bays (rounded so the pattern closes).
    const ringWalls = (mat, ring, z0, z1, bay, v0 = 0, v1 = 1) => {
      let per = 0;
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        per += Math.hypot(b[0] - a[0], b[1] - a[1]);
      }
      const unit = per / Math.max(1, Math.round(per / bay));
      let s = 0;
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          mat,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [s / unit, v0],
          [(s + l) / unit, v0],
          [(s + l) / unit, v1],
          [s / unit, v1],
        );
        s += l;
      }
    };
    const annulus = (mat, outer, innerR, z, down = false) =>
      kit.cap(batch, mat, [[outer, innerR.slice().reverse()]], z, { down });

    const stone = kit.mat('#d6c39c');
    const lead = kit.mat('#8d9295', { roughness: 0.6 });
    const brick = kit.mat(BRICK);
    // Ground apron slivers (h 4 parts) between the drum and the outline.
    for (const id of ['015af447', 'ceebc7bc', '37db8146', '97354f8b']) {
      if (!parts[id]) continue;
      const r = ringOf(id);
      kit.walls(batch, kit.mat('#b39f80'), [[r]], 0, 1.2);
      kit.cap(batch, kit.mat('#b39f80'), [[r]], 1.2);
    }
    ringWalls(drumMat, drum, 0, 25, 6.2);
    // Projecting string course at the balcony line and the main cornice.
    const band = (d, z0, z1, mat) => {
      const o = kit.offsetRing(drum, d);
      ringWalls(mat, o, z0, z1, 6.2, 0, 0.05);
      annulus(mat, o, drum, z1);
      annulus(mat, o, drum, z0, true);
    };
    band(0.35, 15.9, 16.4, stone);
    band(0.6, 24.6, 25.2, stone);
    // Balustraded parapet.
    const balMat = kit.paintedMaterial('royal_albert_hall:balustrade', 128, 64, (c, w, h) => {
      c.fillStyle = '#d9c6a0';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#6b5a48';
      for (let x = 6; x < w; x += 16) c.fillRect(x, 14, 8, 38);
      c.fillStyle = '#c8b38c';
      c.fillRect(0, 0, w, 10);
    });
    const par = kit.offsetRing(drum, 0.4),
      parIn = kit.offsetRing(drum, 0.05);
    ringWalls(balMat, par, 25.2, 26.3, 1.2);
    ringWalls(stone, parIn.slice().reverse(), 25.2, 26.3, 6);
    annulus(stone, par, parIn, 26.3);
    // Lead roof terrace between the parapet and the dome drum.
    annulus(lead, parIn, inner, 25.15);
    // Dome base wall (stepped attic ring) in brick with a stone coping.
    ringWalls(brick, inner, 25.15, 27.8, 4);
    const innerOut = kit.offsetRing(inner, 0.5);
    ringWalls(stone, innerOut, 27.8, 28.6, 4);
    annulus(stone, innerOut, inner, 28.6);

    // ---- Porches: brick with terracotta arches, pediment roofs.
    const porchMat = kit.paintedMaterial('royal_albert_hall:porch', 128, 512, (c, w, h) => {
      const P = h / 20;
      const Y = (m) => h - m * P;
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#b9a689';
      c.fillRect(0, Y(1), w, P);
      const arch = (z0, z1, ww, col) => {
        c.fillStyle = col;
        c.fillRect(w / 2 - ww / 2, Y(z1) + ww / 2, ww, Y(z0) - Y(z1) - ww / 2);
        c.beginPath();
        c.arc(w / 2, Y(z1) + ww / 2, ww / 2, Math.PI, 0);
        c.fill();
      };
      arch(0, 7, 96, TC);
      arch(0, 6.6, 80, '#2c2622');
      c.fillStyle = TC;
      c.fillRect(0, Y(8), w, 0.8 * P);
      arch(8.8, 13.2, 64, TC_D);
      arch(9, 13, 48, DARK);
      c.fillStyle = TC;
      c.fillRect(0, Y(14.2), w, 0.6 * P);
      arch(14.8, 17, 40, DARK);
      c.fillStyle = '#d9c6a0';
      c.fillRect(0, Y(18.4), w, 1.2 * P);
      c.fillStyle = 'rgba(0,0,0,0.07)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
    });
    const centre = [
      drum.reduce((s, p) => s + p[0], 0) / drum.length,
      drum.reduce((s, p) => s + p[1], 0) / drum.length,
    ];
    const roofMat = kit.mat('#7b6f69');
    for (const [id, eave] of [
      ['4defd046', 17],
      ['c4e3f555', 18.4],
      ['ef8b8230', 18],
      ['d05eac5f', 18],
    ]) {
      if (!parts[id]) continue;
      const r = ringOf(id);
      const pc = [
        r.reduce((s, p) => s + p[0], 0) / r.length,
        r.reduce((s, p) => s + p[1], 0) / r.length,
      ];
      const ang = Math.atan2(pc[1] - centre[1], pc[0] - centre[0]);
      // u per edge in 4 m bays (porch elevation repeated).
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = Math.max(1, Math.round(l / 4.5));
        batch.quad(
          porchMat,
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], eave],
          [a[0], a[1], eave],
          [0, 0],
          [n, 0],
          [n, eave / 20],
          [0, eave / 20],
        );
      }
      kit.pitchedRoof(batch, roofMat, kit.mat('#d2b48a'), r, ang, eave, 2.6, 'gabled', {
        overhang: 0.3,
      });
      // Porch balustrade at first floor (projecting balcony) on the outer face.
      const e = kit.orientedExtent(r, ang);
      const at = (u, v, z) => e.at(u, v, z);
      const fw = e.v1 - e.v0;
      const p = at(e.u1 + 0.6, (e.v0 + e.v1) / 2, 0);
      kit.box(batch, stone, p[0], p[1], 7.6, 1.6, fw * 0.92, 0.5, ang);
      kit.box(batch, balMat, p[0], p[1], 8.1, 1.4, fw * 0.9, 1.0, ang);
      // Pilaster columns flanking the carriage arch.
      for (const v of [e.v0 + 1, e.v1 - 1]) {
        const q = at(e.u1 + 0.3, v, 0);
        kit.box(batch, kit.mat('#d2b48a'), q[0], q[1], 0, 0.9, 0.9, 7.6, ang);
      }
    }

    g.add(batch.toGroup('royal_albert_hall'));

    // ---- Dome: elliptical shallow dome fitted to the inner part, lead ribs and glazing.
    const fr = kit.ringFrame(inner);
    const domeMat = kit.paintedMaterial(
      'royal_albert_hall:dome',
      1024,
      256,
      (c, w, h) => {
        c.fillStyle = '#b4b5af';
        c.fillRect(0, 0, w, h);
        // glazed ring (upper part of the dome), canvas top = dome top
        c.fillStyle = '#4c606b';
        c.fillRect(0, h * 0.16, w, h * 0.3);
        c.fillStyle = 'rgba(190,210,220,0.3)';
        for (let y = h * 0.18; y < h * 0.46; y += 9) c.fillRect(0, y, w, 2);
        c.fillStyle = '#d0d0c8';
        c.fillRect(0, h * 0.46, w, 5);
        c.fillStyle = '#9fa19c';
        for (let y = h * 0.55; y < h; y += 22) c.fillRect(0, y, w, 2);
        // ring of small vents near the springing
        c.fillStyle = '#5b5f60';
        for (let k = 0; k < 96; k++) c.fillRect((k * w) / 96 + 3, h * 0.86, 4, 10);
        // radial ribs
        c.fillStyle = '#6d7275';
        for (let k = 0; k < 64; k++) c.fillRect((k * w) / 64, 0, 3, h);
      },
      { roughness: 0.45, metalness: 0.25 },
    );
    const z0 = 28.6,
      z1 = 43.2;
    // Segmental (shallow) dome: spherical cap of half-angle 62 degrees.
    const prof = [];
    const tm = (62 * Math.PI) / 180;
    for (let k = 0; k <= 14; k++) {
      const th = tm * (1 - k / 14);
      prof.push(
        new THREE.Vector2(
          Math.max(0.001, Math.sin(th) / Math.sin(tm)),
          (Math.cos(th) - Math.cos(tm)) / (1 - Math.cos(tm)),
        ),
      );
    }
    const domeGeo = new THREE.LatheGeometry(prof, 64);
    domeGeo.rotateX(Math.PI / 2);
    domeGeo.scale((fr.length / 2) * 1.01, (fr.width / 2) * 1.01, z1 - z0);
    domeGeo.rotateZ(fr.angle);
    domeGeo.translate(fr.cx, fr.cy, z0);
    domeGeo.computeVertexNormals();
    g.add(new THREE.Mesh(domeGeo, domeMat));
    // Central lantern (glazed drum + lead cap).
    const lf = kit.ringFrame(lantern);
    const lr = Math.min(lf.length, lf.width) / 2;
    const lan = new THREE.Mesh(
      new THREE.CylinderGeometry(lr * 0.8, lr, 2.4, 16).rotateX(Math.PI / 2),
      kit.mat('dark_glass'),
    );
    lan.position.set(lf.cx, lf.cy, 43.0 + 1.2);
    const lcap = new THREE.Mesh(
      new THREE.ConeGeometry(lr * 0.95, 1.6, 16).rotateX(Math.PI / 2),
      lead,
    );
    lcap.position.set(lf.cx, lf.cy, 45.4 + 0.8 - 0.2);
    const fin = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.12, 1.4, 6).rotateX(Math.PI / 2),
      kit.mat('gold'),
    );
    fin.position.set(lf.cx, lf.cy, 47.2);
    g.add(lan, lcap, fin);

    // ---- Boiler chimney stack (separate footprint south-west of the hall).
    const ch = byId['7bb7d9b1-86fb-4516-914a-32d48fcffcc0'];
    if (ch) {
      const b2 = new kit.MeshBatch();
      const r = ccw(ch.polys[0][0]);
      const H = ch.h ?? 15.5;
      kit.walls(b2, brick, [[r]], 0, H - 1);
      const ro = kit.offsetRing(r, 0.25);
      kit.walls(b2, stone, [[ro]], H - 1, H);
      kit.cap(b2, kit.mat('#2a2a2a'), [[ro]], H);
      g.add(b2.toGroup('rah_chimney'));
    }
    return g;
  },
};
