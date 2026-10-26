// Royal Albert Hall, Kensington Gore (Francis Fowke and Henry Y. D. Scott, 1867-1871).
// Elliptical amphitheatre in Fareham red brick with buff terracotta dressings: an
// arcaded drum of three storeys of round-arched windows between terracotta pilasters,
// a balustraded balcony in front of an open arcaded gallery loggia (the "smoking
// gallery"), a continuous mosaic frieze ("The Triumph of Arts and Sciences", ~25 m above
// ground), the dedication inscription and a modillioned cornice under a balustraded
// parapet; a shallow wrought iron and glass dome (~41 m, R. M. Ordish) with a central
// lantern. Four projecting two-storey porches (north to Kensington Gore, south, east and
// west) with moulded pilasters, arched carriage openings, balustrades and cornices.
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
    {
      title: 'Royal Albert Hall - Historic England list entry 1217742',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1217742',
      used_for:
        'red brick and buff terracotta, five stages with two tiers of windows and decorative pilasters, ' +
        'mosaic frieze; four projecting two-storey porches with moulded pilasters, balustrades and cornices',
    },
    {
      title: 'ROYAL ALBERT HALL (Londres) - amithe.es',
      url: 'https://amithe.es/?p=370',
      used_for:
        'about 6 million bricks and 80,000 terracotta blocks; frieze runs above the balustraded smoking gallery',
    },
    {
      title: 'Royal Albert Hall - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Albert_Hall',
      used_for: 'dome of wrought iron and glazing designed by Rowland Mason Ordish',
    },
  ],
  notes:
    'Drum, porches and dome follow the 11 Overture parts (drum 25 m, dome springing ~29 m to 43.8 m, lantern 46.6 m). ' +
    'Bay count (~40 bays of ~6.2 m) and the storey levels are proportioned from photo descriptions, not measured. ' +
    'Windows, pilasters, string courses, balcony and parapet balustrades, the open gallery arcade with columns, ' +
    'modillioned cornice, dome ribs and porches are real geometry; the mosaic frieze and inscription are painted ' +
    '(figures abstracted). Porches are generic two-storey blocks with arched openings, the rebuilt south porch is ' +
    'not distinguished. Porch roofs are flat behind balustrades at the part heights (18-20 m). Ground is flat, so ' +
    'the south steps down to Prince Consort Road are not modelled. Chimney stack height kept at the data value.',
  build({ THREE, kit, byId, placeAssets }) {
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
      TC_D = '#b89a70';
    const brick = kit.mat(BRICK);
    const brickDark = kit.mat('#7c3a29');
    const tc = kit.mat(TC);
    const tcD = kit.mat(TC_D);
    const tcL = kit.mat('#ddc59e');
    const stone = kit.mat('#d6c39c');
    const lead = kit.mat('#8d9295', { roughness: 0.6 });
    const doorMat = kit.mat('#3a2a20', { roughness: 0.7 });
    const glass = kit.mat('#26323a', { roughness: 0.15, metalness: 0.3 });
    const frameMat = kit.mat('#e8e2d2');
    const soffit = kit.mat('#5e4a3e');

    // ---- Perimeter parametrisation of the drum ring.
    const segs = [];
    let per = 0;
    for (let k = 0; k < drum.length; k++) {
      const a = drum[k],
        b = drum[(k + 1) % drum.length];
      const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      segs.push({ a, b, l, s0: per });
      per += l;
    }
    const at = (s) => {
      s = ((s % per) + per) % per;
      let i = 0;
      while (i < segs.length - 1 && segs[i].s0 + segs[i].l < s) i++;
      const q = segs[i],
        t = q.l ? (s - q.s0) / q.l : 0;
      return [q.a[0] + (q.b[0] - q.a[0]) * t, q.a[1] + (q.b[1] - q.a[1]) * t];
    };
    const centre = [
      drum.reduce((s, p) => s + p[0], 0) / drum.length,
      drum.reduce((s, p) => s + p[1], 0) / drum.length,
    ];
    const NB = Math.round(per / 6.2);
    const unit = per / NB;
    // Start so that a bay is centred on the north (Kensington Gore) axis.
    let sNorth = 0,
      best = -Infinity;
    for (let k = 0; k < 400; k++) {
      const p = at((k / 400) * per);
      if (p[1] > best) ((best = p[1]), (sNorth = (k / 400) * per));
    }
    const off = sNorth - unit / 2;
    const bays = [];
    for (let k = 0; k < NB; k++) {
      let a = at(off + k * unit),
        b = at(off + (k + 1) * unit);
      const m = at(off + (k + 0.5) * unit);
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        L = Math.hypot(dx, dy);
      const ux = dx / L,
        uy = dy / L,
        nx = uy,
        ny = -ux;
      const d = (m[0] - (a[0] + b[0]) / 2) * nx + (m[1] - (a[1] + b[1]) / 2) * ny;
      a = [a[0] + nx * d, a[1] + ny * d];
      b = [b[0] + nx * d, b[1] + ny * d];
      bays.push({ a, b, L, ux, uy, nx, ny, ang: Math.atan2(uy, ux), m: [m[0], m[1]] });
    }
    const porchIds = ['4defd046', 'c4e3f555', 'ef8b8230', 'd05eac5f'].filter((id) => parts[id]);
    const inside = (p, ring) => {
      let c = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i],
          [xj, yj] = ring[j];
        if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
      }
      return c;
    };
    const porchRings = porchIds.map((id) => ({ id, r: ringOf(id), h: parts[id].h ?? 18 }));
    const porchAt = (p) => {
      for (const pr of porchRings) {
        const grown = kit.offsetRing(pr.r, 1.2);
        if (inside(p, grown)) return pr;
      }
      return null;
    };
    for (const bay of bays) {
      const probe = [bay.m[0] + bay.nx * 1.0, bay.m[1] + bay.ny * 1.0];
      bay.porch = porchAt(probe);
    }

    // ---- Drum facade texture: one bay x 25 m (brick, frieze, inscription).
    const PX = 41;
    const drumMat = kit.paintedMaterial('royal_albert_hall:bay2', 256, 1024, (c, w, h) => {
      const Y = (m) => h - m * PX;
      const band = (z0, z1, col) => {
        c.fillStyle = col;
        c.fillRect(0, Y(z1), w, (z1 - z0) * PX);
      };
      band(0, 25, BRICK);
      const r = kit.rng(4.17);
      // brick coursing and tone variation
      for (let y = 0; y < h; y += 4) {
        c.fillStyle = `rgba(0,0,0,${0.04 + r() * 0.05})`;
        c.fillRect(0, y, w, 1);
      }
      for (let k = 0; k < 500; k++) {
        c.fillStyle = r() < 0.5 ? 'rgba(255,210,180,0.07)' : 'rgba(60,15,5,0.08)';
        c.fillRect(r() * w, r() * h, 10, 3);
      }
      band(0, 1.1, '#b9a689');
      // Window reveals (dark), matching the 3D windows.
      const arch = (x, z0, z1, ww, col) => {
        const rr = ww / 2;
        c.fillStyle = col;
        c.fillRect(x - rr, Y(z1) + rr, ww, Y(z0) - Y(z1) - rr);
        c.beginPath();
        c.arc(x, Y(z1) + rr, rr, Math.PI, 0);
        c.fill();
      };
      // Frieze (buff, white and red-brown figures on chocolate ground), 21.4-23.6.
      band(21.4, 23.6, '#4e3324');
      band(21.4, 21.62, TC);
      band(23.38, 23.6, TC);
      const fr = kit.rng(7.31);
      const robes = ['#e6d6b2', '#d4b98a', '#b9573f', '#efe6d0', '#8a6b4a', '#c99b5a'];
      for (let k = 0; k < 11; k++) {
        const x = 8 + k * 22.5 + fr() * 5;
        const hh = (1.45 + fr() * 0.25) * PX;
        const base = Y(21.75);
        c.fillStyle = robes[Math.floor(fr() * robes.length)];
        c.beginPath();
        c.moveTo(x - 6, base);
        c.lineTo(x + 6, base);
        c.lineTo(x + 3.5, base - hh * 0.78);
        c.lineTo(x - 3.5, base - hh * 0.78);
        c.closePath();
        c.fill();
        c.fillStyle = '#e8c9a4';
        c.beginPath();
        c.arc(x, base - hh * 0.86, 3.2, 0, Math.PI * 2);
        c.fill();
        if (fr() < 0.5) {
          c.fillStyle = robes[Math.floor(fr() * robes.length)];
          c.fillRect(x + 4, base - hh * 0.62, 7, 3);
        }
      }
      // Inscription band: buff letters on darker ground.
      band(23.6, 24.4, '#7a5338');
      c.fillStyle = '#ead9b6';
      for (let x = 3; x < w - 4; x += 8.5) if (fr() > 0.15) c.fillRect(x, Y(24.28), 5.5, 0.6 * PX);
      band(24.4, 25, '#d9c6a0');
    });
    const ringWalls = (mat, ring, z0, z1, bay, v0, v1) => {
      let pp = 0;
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        pp += Math.hypot(b[0] - a[0], b[1] - a[1]);
      }
      const u = pp / Math.max(1, Math.round(pp / bay));
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
          [s / u, v0],
          [(s + l) / u, v0],
          [(s + l) / u, v1],
          [s / u, v1],
        );
        s += l;
      }
    };
    const annulus = (mat, outer, innerR, z, down = false) =>
      kit.cap(batch, mat, [[outer, innerR.slice().reverse()]], z, { down });

    // Ground apron slivers (h 4 parts) between the drum and the outline.
    const apron = kit.mat('#b39f80');
    for (const id of ['015af447', 'ceebc7bc', '37db8146', '97354f8b']) {
      if (!parts[id]) continue;
      const r = ringOf(id);
      kit.walls(batch, apron, [[r]], 0, 1.2);
      kit.cap(batch, kit.mat('#a99a86'), [[r]], 1.2);
    }

    // ---- Drum walls: lower storeys, recessed loggia back wall, frieze zone.
    const LZ0 = 16.4,
      LZ1 = 21.4;
    ringWalls(drumMat, drum, 0, LZ0, 6.2, 0, LZ0 / 25);
    ringWalls(drumMat, drum, LZ1, 25, 6.2, LZ1 / 25, 1);
    const loggiaBack = kit.offsetRing(drum, -1.6);
    ringWalls(brickDark, loggiaBack, LZ0, LZ1, 6.2, 0, 1);
    annulus(soffit, drum, loggiaBack, LZ1, true);
    annulus(kit.mat('#8f8476'), drum, loggiaBack, LZ0 + 0.02);
    // Plinth, string courses, balcony, main cornice.
    kit.cornice(batch, kit.mat('#b9a689'), drum, 0, { height: 1.1, projection: 0.25, steps: 2 });
    kit.cornice(batch, tc, drum, 6.4, { height: 0.7, projection: 0.28, steps: 2 });
    kit.cornice(batch, tc, drum, 12.1, { height: 0.6, projection: 0.25, steps: 2 });
    kit.cornice(batch, stone, drum, 15.6, { height: 0.8, projection: 1.0, steps: 3 });
    kit.cornice(batch, stone, drum, 24.4, { height: 0.8, projection: 0.75, steps: 3 });
    kit.cornice(batch, tc, drum, 21.2, { height: 0.25, projection: 0.15 });
    // Balcony balustrade (in front of the gallery) and the parapet balustrade.
    const close = (r) => [...r, r[0]];
    kit.balustrade(batch, tcL, close(kit.offsetRing(drum, 0.88)), LZ0, {
      height: 1.0,
      spacing: 0.58,
    });
    kit.balustrade(batch, stone, close(kit.offsetRing(drum, 0.45)), 25.2, {
      height: 0.95,
      spacing: 0.7,
    });

    // ---- Per bay: pilasters, windows, arcade, modillions.
    const W = 6.2,
      H = LZ1 - LZ0;
    const arcShape = new THREE.Shape();
    arcShape.moveTo(0, 0);
    arcShape.lineTo(W, 0);
    arcShape.lineTo(W, H);
    arcShape.lineTo(0, H);
    arcShape.closePath();
    const ARW = 1.42,
      SPR = 3.0;
    for (const cxA of [W / 6, W / 2, (5 * W) / 6]) {
      const hole = new THREE.Path();
      hole.moveTo(cxA - ARW / 2, 0.05);
      hole.lineTo(cxA + ARW / 2, 0.05);
      hole.lineTo(cxA + ARW / 2, SPR);
      hole.absarc(cxA, SPR, ARW / 2, 0, Math.PI, false);
      hole.lineTo(cxA - ARW / 2, 0.05);
      arcShape.holes.push(hole);
    }
    const arcGeo = new THREE.ExtrudeGeometry(arcShape, {
      depth: 0.5,
      bevelEnabled: false,
      curveSegments: 7,
    });
    const archRing = new THREE.TorusGeometry(ARW / 2 + 0.1, 0.1, 4, 9, Math.PI);
    const M = new THREE.Matrix4();
    const placeLocal = (bay, geo, mat, lx, lz, out, sx = 1) => {
      // local x along the bay, y up, z outward
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(bay.ux * sx, bay.uy * sx, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(bay.nx, bay.ny, 0),
      );
      m.setPosition(
        bay.a[0] + bay.ux * lx + bay.nx * out,
        bay.a[1] + bay.uy * lx + bay.ny * out,
        lz,
      );
      batch.addGeometry(mat, geo, m);
    };
    // Lean framed window (local x along wall, y up, z outward), cached per spec:
    // glass, moulded surround, glazing bars, sill and arch keystone / pediment.
    const winCache = new Map();
    const outline = (w, h, head, grow) => {
      const s = new THREE.Shape();
      const x0 = -w / 2 - grow,
        x1 = w / 2 + grow;
      s.moveTo(x0, -grow);
      s.lineTo(x1, -grow);
      if (head === 'arch') {
        s.lineTo(x1, h);
        s.absarc(0, h, w / 2 + grow, 0, Math.PI, false);
      } else (s.lineTo(x1, h + grow), s.lineTo(x0, h + grow));
      s.lineTo(x0, -grow);
      return s;
    };
    const winParts = (spec) => {
      const key = JSON.stringify(spec);
      if (winCache.has(key)) return winCache.get(key);
      const {
        w,
        h,
        head = 'arch',
        bars = 1,
        f = 0.2,
        glassMat = glass,
        sur = tc,
        bar = frameMat,
      } = spec;
      const out = [];
      const gs = new THREE.ShapeGeometry(outline(w, h, head, 0), 5);
      gs.translate(0, 0, 0.02);
      out.push([gs, glassMat]);
      const ring = outline(w, h, head, f);
      const hole = outline(w, h, head, 0);
      ring.holes.push(new THREE.Path(hole.getPoints(5).reverse()));
      out.push([
        new THREE.ExtrudeGeometry(ring, { depth: 0.13, bevelEnabled: false, curveSegments: 5 }),
        sur,
      ]);
      const top = head === 'arch' ? h + w / 2 : h;
      if (bars) {
        const vb = new THREE.BoxGeometry(0.06, top, 0.06);
        vb.translate(0, top / 2, 0.06);
        out.push([vb, bar]);
        const hb = new THREE.BoxGeometry(w, 0.06, 0.06);
        hb.translate(0, head === 'arch' ? h : h * 0.62, 0.06);
        out.push([hb, bar]);
      }
      const sill = new THREE.BoxGeometry(w + 2 * f + 0.25, 0.16, 0.3);
      sill.translate(0, -f - 0.08, 0.15);
      out.push([sill, sur]);
      if (head === 'arch') {
        const ks = new THREE.BoxGeometry(Math.max(0.22, w * 0.18), f + 0.12, 0.2);
        ks.translate(0, top + f / 2, 0.1);
        out.push([ks, sur]);
      } else if (head === 'pediment') {
        const t = new THREE.Shape();
        const hw = w / 2 + f + 0.2;
        t.moveTo(-hw, 0);
        t.lineTo(hw, 0);
        t.lineTo(0, hw * 0.42);
        t.closePath();
        const pg = new THREE.ExtrudeGeometry(t, { depth: 0.25, bevelEnabled: false });
        pg.translate(0, h + f + 0.14, 0);
        out.push([pg, sur]);
        const lt = new THREE.BoxGeometry(2 * hw, 0.14, 0.26);
        lt.translate(0, h + f + 0.07, 0.13);
        out.push([lt, sur]);
      }
      winCache.set(key, out);
      return out;
    };
    const edgeOf = (a, b) => {
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ux = (b[0] - a[0]) / L,
        uy = (b[1] - a[1]) / L;
      return { a, b, L, ux, uy, nx: uy, ny: -ux, ang: Math.atan2(uy, ux) };
    };
    const winRow = (e, z, n, margin, spec) => {
      const usable = e.L - 2 * margin;
      for (let k = 0; k < n; k++) {
        const lx = margin + (usable * (k + 0.5)) / n;
        for (const [geo, m] of winParts(spec)) placeLocal(e, geo, m, lx, z, 0);
      }
    };
    for (const bay of bays) {
      const sx = bay.L / W;
      // Gallery arcade (visible above any porch roof).
      placeLocal(bay, arcGeo, tc, 0, LZ0, -0.5, sx);
      for (const cxA of [W / 6, W / 2, (5 * W) / 6])
        placeLocal(bay, archRing, tcD, cxA * sx, LZ0 + SPR, 0.03);
      const p1 = [bay.a[0] + bay.ux * (W / 3) * sx, bay.a[1] + bay.uy * (W / 3) * sx];
      const p2 = [bay.a[0] + bay.ux * ((2 * W) / 3) * sx, bay.a[1] + bay.uy * ((2 * W) / 3) * sx];
      kit.colonnade(batch, tcL, p1, p2, LZ0 + 0.05, SPR - 0.05, {
        count: 2,
        radius: 0.17,
        offset: 0.2,
        capital: 'corinthian',
        segments: 6,
      });
      // Pier pilasters at the bay boundary in the gallery.
      kit.box(batch, tcD, bay.a[0], bay.a[1], LZ0, 0.7, 0.3, H, bay.ang);
      // Modillions under the main cornice.
      for (let i = 0; i < 6; i++) {
        const t = (i + 0.5) / 6;
        const x = bay.a[0] + (bay.b[0] - bay.a[0]) * t + bay.nx * 0.25,
          y = bay.a[1] + (bay.b[1] - bay.a[1]) * t + bay.ny * 0.25;
        kit.box(batch, stone, x, y, 24.15, 0.25, 0.5, 0.25, bay.ang);
      }
      if (bay.porch && bay.porch.h > 15) continue;
      // Terracotta pilasters between bays (two orders).
      const bx = bay.a[0] + bay.nx * 0.1,
        by = bay.a[1] + bay.ny * 0.1;
      kit.box(batch, tc, bx, by, 1.1, 0.7, 0.3, 5.3, bay.ang);
      kit.box(batch, tcD, bx, by, 5.9, 0.9, 0.42, 0.45, bay.ang);
      kit.box(batch, tc, bx, by, 7.1, 0.6, 0.28, 8.5, bay.ang);
      kit.box(batch, tcD, bx, by, 11.6, 0.8, 0.38, 0.4, bay.ang);
      kit.box(batch, tcD, bx, by, 15.1, 0.8, 0.38, 0.45, bay.ang);
      // Windows: arched ground-floor doors, paired first-storey windows, triplets.
      winRow(bay, 1.4, 1, 0.6, { w: 2.1, h: 3.3, bars: 1, f: 0.3, glassMat: doorMat, bar: tcD });
      winRow(bay, 7.8, 2, 0.7, { w: 1.35, h: 2.9, bars: 1, f: 0.22 });
      winRow(bay, 13.2, 3, 0.7, { w: 0.8, h: 1.35, bars: 0, f: 0.14, sur: tcD });
    }
    arcGeo.dispose();
    archRing.dispose();

    // Lead roof terrace between the parapet and the dome drum; brick attic ring.
    const parIn = kit.offsetRing(drum, 0.05);
    annulus(kit.roof('lead'), parIn, inner, 25.15);
    ringWalls(brick, inner, 25.15, 27.8, 4, 0, 1);
    kit.cornice(batch, stone, inner, 27.6, { height: 1.0, projection: 0.5, steps: 2 });
    // Small round-headed vents in the attic ring.
    {
      const ip = [];
      for (let k = 0; k < inner.length; k++) ip.push([inner[k], inner[(k + 1) % inner.length]]);
      for (const [a, b] of ip) {
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (l < 3) continue;
        kit.windowRow(batch, a, b, 25.8, {
          glass: soffit,
          frame: stone,
          count: Math.max(1, Math.round(l / 5)),
          width: 0.7,
          height: 1.0,
          head: 'arch',
          bars: 0,
          depth: 0.1,
        });
      }
    }

    // ---- Porches: two storeys, arched openings, pilasters, cornices, balustrades.
    const porchMat = kit.paintedMaterial('royal_albert_hall:porch2', 128, 256, (c, w, h) => {
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(2.2);
      for (let y = 0; y < h; y += 3) {
        c.fillStyle = `rgba(0,0,0,${0.05 + r() * 0.05})`;
        c.fillRect(0, y, w, 1);
      }
    });
    for (const pr of porchRings) {
      const r = pr.r,
        top = pr.h;
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          porchMat,
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], top - 1.0],
          [a[0], a[1], top - 1.0],
          [0, 0],
          [l / 4, 0],
          [l / 4, (top - 1) / 4],
          [0, (top - 1) / 4],
        );
      }
      kit.cap(batch, kit.roof('lead'), [[r]], top - 1.0);
      kit.cornice(batch, kit.mat('#b9a689'), r, 0, { height: 0.9, projection: 0.2, steps: 2 });
      kit.cornice(batch, tc, r, 7.3, { height: 0.8, projection: 0.35, steps: 2 });
      kit.cornice(batch, stone, r, top - 2.2, { height: 1.2, projection: 0.55, steps: 3 });
      // Outer edges: not buried in the drum.
      const outer = [];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const ux = (b[0] - a[0]) / l,
          uy = (b[1] - a[1]) / l;
        const probe = [mid[0] + uy * 0.6, mid[1] - ux * 0.6];
        if (inside(probe, drum)) continue;
        outer.push({ a, b, l, ux, uy, ang: Math.atan2(uy, ux) });
      }
      // Balustrade on the outer edges at the top.
      for (const e of outer) {
        kit.balustrade(batch, tcL, [e.a, e.b], top - 1.0, { height: 1.0, spacing: 0.42 });
        // Moulded pilasters (piers) at the edge ends.
        for (const p of [e.a, e.b]) {
          kit.box(
            batch,
            tc,
            p[0] + e.uy * 0.12,
            p[1] - e.ux * 0.12,
            0.9,
            0.8,
            0.8,
            top - 3.1,
            e.ang,
          );
          kit.box(batch, tcD, p[0], p[1], top - 1.0, 0.7, 0.7, 1.25, e.ang);
        }
        if (e.l < 2.4) continue;
        const big = e.l >= 7,
          mid = e.l >= 4.5;
        const eo = { ...e, ...edgeOf(e.a, e.b) };
        winRow(eo, big || mid ? 0.6 : 1.4, big ? 3 : 1, 0.55, {
          w: big ? 1.9 : mid ? 2.5 : 1.2,
          h: big ? 3.6 : mid ? 3.7 : 2.4,
          bars: 1,
          f: 0.3,
          bar: tcD,
          glassMat: big || mid ? doorMat : glass,
        });
        winRow(eo, 9.2, big ? 3 : 1, 0.55, {
          w: 1.25,
          h: Math.min(3.0, top - 13.6),
          head: 'pediment',
          bars: 1,
          f: 0.16,
        });
        if (big) {
          // Paired pilasters between the arches.
          for (const t of [1 / 3, 2 / 3]) {
            const x = e.a[0] + (e.b[0] - e.a[0]) * t + e.uy * 0.12,
              y = e.a[1] + (e.b[1] - e.a[1]) * t - e.ux * 0.12;
            kit.box(batch, tc, x, y, 0.9, 0.55, 0.3, top - 3.1, e.ang);
          }
          // Name panel over the central arch.
          const x = (e.a[0] + e.b[0]) / 2 + e.uy * 0.1,
            y = (e.a[1] + e.b[1]) / 2 - e.ux * 0.1;
          kit.box(batch, stone, x, y, 6.2, 3.0, 0.15, 0.8, e.ang);
        }
      }
    }

    // ---- Boiler chimney stack (separate footprint south-west of the hall).
    const ch = byId['7bb7d9b1-86fb-4516-914a-32d48fcffcc0'];
    if (ch) {
      const r = ccw(ch.polys[0][0]);
      const Hc = ch.h ?? 15.5;
      kit.walls(batch, brick, [[r]], 0, Hc - 1);
      kit.cornice(batch, tc, r, Hc * 0.55, { height: 0.4, projection: 0.12 });
      const ro = kit.offsetRing(r, 0.25);
      kit.walls(batch, stone, [[ro]], Hc - 1, Hc);
      kit.cap(batch, stone, [[ro, kit.offsetRing(r, -0.3).slice().reverse()]], Hc);
      kit.cap(batch, kit.mat('#1e1e1e'), [[kit.offsetRing(r, -0.3)]], Hc - 0.6);
    }

    // ---- Dome: elliptical shallow dome fitted to the inner part, lead ribs and glazing.
    const fr = kit.ringFrame(inner);
    const domeMat = kit.paintedMaterial(
      'royal_albert_hall:dome2',
      1024,
      256,
      (c, w, h) => {
        c.fillStyle = '#b1b3ae';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(5.5);
        for (let y = 0; y < h; y += 4) {
          c.fillStyle = `rgba(0,0,0,${0.02 + r() * 0.04})`;
          c.fillRect(0, y, w, 2);
        }
        // glazed ring (upper part of the dome), canvas top = dome top
        c.fillStyle = '#3f525d';
        c.fillRect(0, h * 0.14, w, h * 0.32);
        c.fillStyle = 'rgba(200,220,230,0.35)';
        for (let y = h * 0.16; y < h * 0.46; y += 8) c.fillRect(0, y, w, 1.5);
        for (let x = 0; x < w; x += 8) c.fillRect(x, h * 0.14, 1, h * 0.32);
        c.fillStyle = '#d0d0c8';
        c.fillRect(0, h * 0.46, w, 5);
        c.fillRect(0, h * 0.13, w, 4);
        c.fillStyle = '#9a9c97';
        for (let y = h * 0.52; y < h; y += 18) c.fillRect(0, y, w, 2);
      },
      { roughness: 0.45, metalness: 0.25 },
    );
    const z0 = 28.6,
      z1 = 43.2;
    const tm = (62 * Math.PI) / 180;
    const prof = [];
    for (let k = 0; k <= 16; k++) {
      const th = tm * (1 - k / 16);
      prof.push([
        Math.max(0.001, Math.sin(th) / Math.sin(tm)),
        (Math.cos(th) - Math.cos(tm)) / (1 - Math.cos(tm)),
      ]);
    }
    const A = (fr.length / 2) * 1.01,
      Bm = (fr.width / 2) * 1.01;
    const domeGeo = new THREE.LatheGeometry(
      prof.map(([r, z]) => new THREE.Vector2(r, z)),
      96,
    );
    domeGeo.rotateX(Math.PI / 2);
    domeGeo.scale(A, Bm, z1 - z0);
    domeGeo.rotateZ(fr.angle);
    domeGeo.translate(fr.cx, fr.cy, z0);
    domeGeo.computeVertexNormals();
    g.add(new THREE.Mesh(domeGeo, domeMat));
    // 3D ribs following the dome profile.
    const ca = Math.cos(fr.angle),
      sa = Math.sin(fr.angle);
    const domePt = (phi, k, lift, dw) => {
      const [r, z] = prof[k];
      const lx = A * r * Math.cos(phi) - dw * Math.sin(phi),
        ly = Bm * r * Math.sin(phi) + dw * Math.cos(phi);
      // approximate normal: radial weight falls with height
      const nr = Math.sin(tm * (1 - k / 16)),
        nz = Math.cos(tm * (1 - k / 16));
      const ox = Math.cos(phi) * nr * lift,
        oy = Math.sin(phi) * nr * lift;
      return [
        fr.cx + (lx + ox) * ca - (ly + oy) * sa,
        fr.cy + (lx + ox) * sa + (ly + oy) * ca,
        z0 + (z1 - z0) * z + nz * lift,
      ];
    };
    const ribMat = kit.mat('#62686b', { roughness: 0.5, metalness: 0.4 });
    const NR = 48;
    for (let i = 0; i < NR; i++) {
      const phi = (i / NR) * Math.PI * 2;
      for (let k = 0; k < 15; k++) {
        const L0 = domePt(phi, k, 0.02, -0.16),
          R0 = domePt(phi, k, 0.02, 0.16),
          T0 = domePt(phi, k, 0.22, 0),
          L1 = domePt(phi, k + 1, 0.02, -0.16),
          R1 = domePt(phi, k + 1, 0.02, 0.16),
          T1 = domePt(phi, k + 1, 0.22, 0);
        batch.quad(ribMat, L0, T0, T1, L1, [0, 0], [1, 0], [1, 1], [0, 1]);
        batch.quad(ribMat, T0, R0, R1, T1, [0, 0], [1, 0], [1, 1], [0, 1]);
      }
    }
    // Central lantern: glazed drum with ribs, lead cap, finial.
    const lf = kit.ringFrame(lantern);
    const lr = Math.min(lf.length, lf.width) / 2;
    g.add(
      kit.lathe(
        lead,
        [
          [0.001, 0],
          [lr * 1.05, 0],
          [lr * 1.05, 0.5],
          [lr * 0.95, 0.6],
        ],
        { x: lf.cx, y: lf.cy, z: 43.0, segments: 32 },
      ),
      kit.lathe(
        glass,
        [
          [lr * 0.95, 0.6],
          [lr * 0.9, 2.6],
        ],
        { x: lf.cx, y: lf.cy, z: 43.0, segments: 24 },
      ),
      kit.lathe(
        lead,
        [
          [lr * 1.0, 2.6],
          [lr * 1.02, 2.85],
          [lr * 0.75, 3.3],
          [lr * 0.3, 3.9],
          [0.25, 4.1],
          [0.001, 4.15],
        ],
        { x: lf.cx, y: lf.cy, z: 43.0, segments: 32 },
      ),
    );
    for (let i = 0; i < 16; i++) {
      const phi = (i / 16) * Math.PI * 2;
      kit.box(
        batch,
        ribMat,
        lf.cx + Math.cos(phi) * lr * 0.93,
        lf.cy + Math.sin(phi) * lr * 0.93,
        43.6,
        0.12,
        0.12,
        2.0,
        phi,
      );
    }
    const fin = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.12, 1.6, 8).rotateX(Math.PI / 2),
      kit.mat('gold'),
    );
    fin.position.set(lf.cx, lf.cy, 47.9);
    g.add(fin);

    g.add(batch.toGroup('royal_albert_hall'));

    // ---- Lamps flanking each porch front.
    const lamps = [];
    for (const pr of porchRings.filter((q) => q.id === '4defd046' || q.id === 'c4e3f555')) {
      const pf = kit.ringFrame(pr.r);
      const dir = Math.atan2(pf.cy - centre[1], pf.cx - centre[0]);
      const e = kit.orientedExtent(pr.r, dir);
      for (const v of [e.v0 - 1.2, e.v1 + 1.2]) {
        const p = e.at(e.u1 - 1.0, v, 0);
        lamps.push([p[0], p[1], dir - Math.PI / 2]);
      }
    }
    if (placeAssets && lamps.length) g.add(placeAssets('street_lamp', lamps));
    return g;
  },
};
