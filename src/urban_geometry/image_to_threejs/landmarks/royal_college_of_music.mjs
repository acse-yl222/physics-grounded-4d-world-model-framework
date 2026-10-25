// Royal College of Music, Prince Consort Road (Sir Arthur Blomfield, 1890-94), with the
// Amaryllis Fleming Concert Hall behind (Sidney Smith, 1899-1901) and the later
// Britten Theatre block. Symmetrical twelve-bay red brick front with buff stone
// banding and dressings, a steep slate roof with dormers, end towers capped by
// pyramidal roofs with corner tourelles, and a projecting two-bay centre with a stone
// gable holding a clock flanked by finials over a central arched entrance.
export default {
  id: 'royal_college_of_music',
  name: 'Royal College of Music',
  claims: [
    '9e685150-c49b-4687-89d0-5391bdc51b65', // Blomfield building (front range)
    'd8830a31-a66e-49d9-8059-c1ee4c3aef03', // Amaryllis Fleming Concert Hall
    '8a4fa60d-dd46-4859-9c06-770968c77ed3', // Britten Theatre block (west of the courtyard)
  ],
  references: [
    {
      title: 'Royal College of Music - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101265501-royal-college-of-music-knightsbridge-and-belgravia-ward',
      used_for:
        'twelve-bay symmetrical front, red brick with stone banding, steep slate roof, end towers with pyramidal tops and tourelles, centre gable with clock, concert hall 1899-1901 by Sidney Smith',
    },
    {
      title: 'Royal College of Music - victorianweb.org',
      url: 'https://victorianweb.org/art/architecture/blomfield/2.html',
      used_for: 'Blomfield design opposite the Royal Albert Hall',
    },
    {
      title: 'Royal College of Music, London - penang-traveltips',
      url: 'https://www.penang-traveltips.com/europe/uk/england/london/royal-college-of-music.htm',
      used_for: 'Flemish Mannerist style, red brick dressed with buff stone',
    },
    {
      title: 'Royal College of Music dramatic new - Planet Hugill',
      url: 'https://www.planethugill.com/2015/04/royal-college-of-music-dramatic-new.html',
      used_for: 'Britten Theatre lies west of the courtyard behind the front range',
    },
  ],
  notes:
    'Eaves raised to ~17 m with a ~6 m slate roof; towers to ~25 m walls plus pyramidal caps (~33 m) proportioned from the ' +
    'listing description, not measured. The 8a4fa60d footprint is assumed to be the Britten Theatre block (modelled as a plain ' +
    'brick volume). Window rhythm is a painted 4-bay tile; the clock gable is simplified.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const BRICK = '#9c4a36',
      STONE = '#d8c49a';
    const stone = kit.mat(STONE),
      slate = kit.mat('#4f565d'),
      lead = kit.mat('#5f676c', { roughness: 0.5, metalness: 0.3 }),
      brick = kit.mat(BRICK);

    // Facade tile: 4 bays (3.6 m) x full eaves height H (17 m), drawn bottom-up.
    const H = 17;
    const facadeMat = (key, hgt, opts = {}) =>
      kit.paintedMaterial(`royal_college_of_music:${key}`, 512, 512, (c, w, h) => {
        const P = h / hgt,
          Y = (m) => h - m * P,
          bw = w / 4;
        c.fillStyle = BRICK;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(0,0,0,0.06)';
        for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
        const band = (z0, z1, col = STONE) => {
          c.fillStyle = col;
          c.fillRect(0, Y(z1), w, (z1 - z0) * P);
        };
        // Ground storey banded in stone and brick.
        for (let z = 0.4; z < 4.4; z += 0.6) band(z, z + 0.3);
        band(0, 0.6, '#b7a27c');
        const win = (x, z0, z1, ww, arch) => {
          c.fillStyle = STONE;
          c.fillRect(x - ww / 2 - 4, Y(z1) - 4, ww + 8, (z1 - z0) * P + 8);
          c.fillStyle = '#28303a';
          c.fillRect(x - ww / 2, Y(z1), ww, (z1 - z0) * P);
          if (arch) {
            c.fillStyle = STONE;
            c.beginPath();
            c.arc(x, Y(z1), ww / 2 + 4, Math.PI, 0);
            c.fill();
            c.fillStyle = '#28303a';
            c.beginPath();
            c.arc(x, Y(z1), ww / 2, Math.PI, 0);
            c.fill();
          }
          // stone mullion and transom
          c.fillStyle = STONE;
          c.fillRect(x - 2, Y(z1), 4, (z1 - z0) * P);
          c.fillRect(x - ww / 2, Y(z0 + (z1 - z0) * 0.62), ww, 4);
        };
        for (let b = 0; b < 4; b++) {
          const x = bw * (b + 0.5);
          if (opts.ground !== false) win(x, 1.0, 3.6, 46, true);
          win(x, 5.4, 8.4, 52, false);
          win(x, 9.6, 12.2, 52, false);
          win(x, 13.4, 15.4, 46, false);
          // pilaster strips between bays
          c.fillStyle = 'rgba(60,20,10,0.25)';
          c.fillRect(b * bw, Y(16), 6, 11.6 * P);
        }
        band(4.6, 5.0);
        band(8.9, 9.2);
        band(12.7, 13.0);
        band(16.0, 17.0);
        if (hgt > 17) for (let b = 0; b < 4; b++) win(bw * (b + 0.5), 18, 22, 40, true);
      });
    const front = facadeMat('front', H);

    // ---- Front range.
    const main = byId['9e685150-c49b-4687-89d0-5391bdc51b65'];
    let fr = null;
    if (main) {
      const ring = ccw(main.polys[0][0]);
      fr = kit.ringFrame(ring);
      let ang = fr.angle;
      if (Math.cos(ang) < 0) ang += Math.PI;
      const e = kit.orientedExtent(ring, ang);
      kit.walls(batch, front, [[ring]], 0, H, { bay: 3.6, storey: H / 2 });
      kit.cap(batch, kit.mat('#5d6268'), [[ring]], H);
      // projecting stone cornice
      const ro = kit.offsetRing(ring, 0.35);
      kit.walls(batch, stone, [[ro]], H - 0.6, H);
      kit.cap(batch, stone, [[ro, ring.slice().reverse()]], H);
      const L = e.u1 - e.u0;
      const tw = Math.min(11.5, L * 0.18); // tower width along the front
      const at = (u, v, z) => e.at(u, v, z);
      const rect = (ua, ub, va, vb) =>
        [at(ua, va, 0), at(ub, va, 0), at(ub, vb, 0), at(ua, vb, 0)].map((p) => [p[0], p[1]]);
      // Steep slate roof over the range between the towers, with dormers.
      const ru0 = e.u0 + tw,
        ru1 = e.u1 - tw;
      kit.pitchedRoof(
        batch,
        slate,
        brick,
        rect(ru0, ru1, e.v0 + 0.5, e.v1 - 0.6),
        ang,
        H,
        6.2,
        'hipped',
        { overhang: 0.3 },
      );
      // Dormers on the front (north, +v) slope.
      const nd = 8;
      for (let k = 0; k < nd; k++) {
        const u = ru0 + 3 + ((ru1 - ru0 - 6) * (k + 0.5)) / nd;
        const p = at(u, e.v1 - 2.0, 0);
        kit.box(batch, stone, p[0], p[1], H, 2.0, 2.2, 2.4, ang);
        kit.box(
          batch,
          kit.mat('#28303a'),
          at(u, e.v1 - 0.9, 0)[0],
          at(u, e.v1 - 0.9, 0)[1],
          H + 0.4,
          1.2,
          0.1,
          1.5,
          ang,
        );
        kit.pitchedRoof(
          batch,
          slate,
          stone,
          rectAround(p, 2.0, 2.2),
          ang + Math.PI / 2,
          H + 2.4,
          1.0,
          'gabled',
          { overhang: 0.1 },
        );
      }
      function rectAround(p, w, d) {
        const c = Math.cos(ang),
          s = Math.sin(ang);
        return [
          [-w / 2, -d / 2],
          [w / 2, -d / 2],
          [w / 2, d / 2],
          [-w / 2, d / 2],
        ].map(([x, y]) => [p[0] + x * c - y * s, p[1] + x * s + y * c]);
      }
      // End towers: walls rising to 25 m, pyramidal slate caps with four tourelles.
      const towerMat = facadeMat('tower', 26);
      for (const [ua, ub] of [
        [e.u0, e.u0 + tw],
        [e.u1 - tw, e.u1],
      ]) {
        const tr = rect(ua, ub, e.v0 + 1.0, e.v1);
        const tH = 26;
        kit.walls(batch, towerMat, [[kit.offsetRing(tr, 0.08)]], H - 0.6, tH, {
          bay: tw / 2 + 0.01,
          storey: tH / 2,
        });
        const tro = kit.offsetRing(tr, 0.4);
        kit.walls(batch, stone, [[tro]], tH - 0.7, tH);
        kit.cap(batch, stone, [[tro]], tH);
        kit.pitchedRoof(batch, slate, brick, tr, ang, tH, 9.5, 'pyramidal', { overhang: 0 });
        const tc = at((ua + ub) / 2, (e.v0 + 1 + e.v1) / 2, 0);
        const fin = new THREE.Mesh(
          new THREE.CylinderGeometry(0.06, 0.12, 2.4, 6).rotateX(Math.PI / 2),
          lead,
        );
        fin.position.set(tc[0], tc[1], tH + 10.6);
        g.add(fin);
        for (const [u, v] of [
          [ua, e.v0 + 1.0],
          [ub, e.v0 + 1.0],
          [ua, e.v1],
          [ub, e.v1],
        ]) {
          const p = at(u, v, 0);
          const t = new THREE.Mesh(
            new THREE.CylinderGeometry(0.9, 0.9, 6, 10).rotateX(Math.PI / 2),
            brick,
          );
          t.position.set(p[0], p[1], tH - 3 + 3 + 0.0);
          const band = new THREE.Mesh(
            new THREE.CylinderGeometry(1.0, 1.0, 0.4, 10).rotateX(Math.PI / 2),
            stone,
          );
          band.position.set(p[0], p[1], tH + 2.6);
          const cone = new THREE.Mesh(
            new THREE.ConeGeometry(1.05, 3.6, 10).rotateX(Math.PI / 2),
            slate,
          );
          cone.position.set(p[0], p[1], tH + 4.6);
          g.add(t, band, cone);
        }
      }
      // Projecting centre (two bays) with stone gable, clock and finials; arched entrance.
      const um = (e.u0 + e.u1) / 2;
      const cw = 8.6;
      const gz0 = H,
        gz1 = H + 7.5;
      const shape = new THREE.Shape();
      shape.moveTo(-cw / 2, 0);
      shape.lineTo(cw / 2, 0);
      shape.lineTo(cw / 2, 1.2);
      shape.quadraticCurveTo(cw / 2 - 0.3, 3.2, cw / 2 - 1.6, 3.6);
      shape.lineTo(cw / 2 - 1.6, 5.2);
      shape.quadraticCurveTo(1.6, 6.2, 0, gz1 - gz0);
      shape.quadraticCurveTo(-1.6, 6.2, -cw / 2 + 1.6, 5.2);
      shape.lineTo(-cw / 2 + 1.6, 3.6);
      shape.quadraticCurveTo(-cw / 2 + 0.3, 3.2, -cw / 2, 1.2);
      shape.lineTo(-cw / 2, 0);
      const gab = new THREE.ExtrudeGeometry(shape, {
        depth: 1.2,
        bevelEnabled: false,
        curveSegments: 5,
      });
      gab.rotateX(Math.PI / 2);
      gab.rotateZ(ang);
      const gp = at(um, e.v1 + 0.3, 0);
      gab.translate(gp[0], gp[1], gz0);
      batch.addGeometry(stone, gab, null);
      // clock face
      const clock = kit.paintedMaterial('royal_college_of_music:clock', 64, 64, (c, w, h) => {
        c.fillStyle = STONE;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#1c2a3a';
        c.beginPath();
        c.arc(w / 2, h / 2, 28, 0, Math.PI * 2);
        c.fill();
        c.strokeStyle = '#d6b04c';
        c.lineWidth = 3;
        c.beginPath();
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2, 10);
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2 + 14, h / 2 + 6);
        c.stroke();
      });
      const cp = at(um, e.v1 + 0.36, 0);
      const cg = new THREE.Mesh(new THREE.CircleGeometry(1.0, 20), clock);
      cg.rotation.set(-Math.PI / 2, 0, 0);
      const holder = new THREE.Group();
      holder.add(cg);
      holder.position.set(cp[0], cp[1], gz0 + 3.6);
      holder.rotation.z = ang;
      g.add(holder);
      for (const s of [-1, 1]) {
        const p = at(um + s * (cw / 2 - 0.3), e.v1 - 0.3, 0);
        const f = new THREE.Mesh(new THREE.ConeGeometry(0.35, 2.4, 6).rotateX(Math.PI / 2), stone);
        f.position.set(p[0], p[1], gz0 + 1.2 + 1.2);
        g.add(f);
      }
      // Gable roof behind the centre gable.
      kit.pitchedRoof(
        batch,
        slate,
        brick,
        rect(um - cw / 2 + 0.5, um + cw / 2 - 0.5, e.v1 - 8, e.v1 - 0.2),
        ang + Math.PI / 2,
        H,
        6.4,
        'gabled',
        { overhang: 0 },
      );
      // Entrance arches (central and two smaller) in stone.
      for (const [du, wdt, ht] of [
        [0, 3.2, 4.6],
        [-3.0, 1.6, 3.2],
        [3.0, 1.6, 3.2],
      ]) {
        const p = at(um + du, e.v1 + 0.3, 0);
        kit.box(batch, stone, p[0], p[1], 0, wdt + 0.8, 0.5, ht + 0.6, ang);
        const q = at(um + du, e.v1 + 0.56, 0);
        kit.box(batch, kit.mat('#2b2420'), q[0], q[1], 0, wdt, 0.05, ht, ang);
      }
    }

    // ---- Amaryllis Fleming Concert Hall: brick hall with tall arched windows, slate roof.
    const hall = byId['d8830a31-a66e-49d9-8059-c1ee4c3aef03'];
    if (hall) {
      const ring = ccw(hall.polys[0][0]);
      const hf = kit.ringFrame(ring);
      const hH = 13.6;
      const hallMat = kit.paintedMaterial('royal_college_of_music:hall', 512, 256, (c, w, h) => {
        const P = h / hH,
          Y = (m) => h - m * P;
        c.fillStyle = BRICK;
        c.fillRect(0, 0, w, h);
        c.fillStyle = STONE;
        c.fillRect(0, Y(1), w, P);
        c.fillRect(0, Y(13.6), w, 0.8 * P);
        for (let b = 0; b < 4; b++) {
          const x = (w / 4) * (b + 0.5);
          c.fillStyle = STONE;
          c.fillRect(x - 26, Y(11), 52, 8 * P);
          c.beginPath();
          c.arc(x, Y(11), 26, Math.PI, 0);
          c.fill();
          c.fillStyle = '#2a323c';
          c.fillRect(x - 20, Y(10.8), 40, 7.6 * P);
          c.beginPath();
          c.arc(x, Y(10.8), 20, Math.PI, 0);
          c.fill();
        }
      });
      kit.walls(batch, hallMat, [[ring]], 0, hH, { bay: 4.0, storey: hH / 2 });
      kit.pitchedRoof(batch, slate, brick, ring, hf.angle, hH, 5.0, 'gabled', { overhang: 0.2 });
      // roof lantern / ventilator along the ridge
      const p = [hf.cx, hf.cy];
      kit.box(batch, lead, p[0], p[1], hH + 4.6, hf.length * 0.5, 1.6, 1.0, hf.angle);
    }

    // ---- Britten Theatre block: plain brick fly-tower volume.
    const bt = byId['8a4fa60d-dd46-4859-9c06-770968c77ed3'];
    if (bt) {
      const ring = ccw(bt.polys[0][0]);
      kit.walls(batch, kit.facade('red_brick', 2), [[ring]], 0, bt.h ?? 16.5, {
        bay: 3.6,
        storey: 3.4,
      });
      kit.cap(batch, kit.mat('#6a6c6e'), [[ring]], bt.h ?? 16.5);
    }
    g.add(batch.toGroup('royal_college_of_music'));
    return g;
  },
};
