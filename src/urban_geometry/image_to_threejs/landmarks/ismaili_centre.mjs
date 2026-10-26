// The Ismaili Centre, 1-7 Cromwell Gardens, South Kensington (Casson Conder Partnership;
// ground broken 1979, opened 1985). Island site opposite the V&A bounded by Cromwell
// Gardens / Cromwell Road, Thurloe Place and the Exhibition Road junction. Clad in white,
// light grey and blue granite with stainless-steel and teak framed windows; "not-quite
// colonnades" around the bottom two floors with bow windows poking out between them,
// overhanging teak oriels above the main entrance, a chamfered corner, prayer hall on
// the third floor and a set-back top floor of offices around a roof-top chahar bagh
// (four-part garden by Sasaki Associates) with a central fountain and corner pools.
export default {
  id: 'ismaili_centre',
  name: 'The Ismaili Centre, London',
  claims: ['6ee5bdcc-1f0d-4623-8d99-a91ca507c14f'],
  references: [
    {
      title: 'Ismaili Centre, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Ismaili_Centre,_London',
      used_for:
        'architects Casson Conder, groundbreaking 1979, completion 1985, island site on Cromwell Road',
    },
    {
      title: 'The Ismaili Centre, London - Twentieth Century Society building of the month',
      url: 'https://c20society.org.uk/building-of-the-month/the-ismaili-centre-london',
      used_for:
        'bow windows between not-quite colonnades on the bottom two floors; floor uses; set-back top floor; limited garden wall height',
    },
    {
      title: 'Ismaili Centre London Cromwell Gardens Building - e-architect',
      url: 'https://www.e-architect.com/london/ismaili-centre-building',
      used_for:
        'white, light grey and blue granite cladding, stainless steel and teak window frames, roof-top garden',
    },
    {
      title: 'Ismaili Centre: overhanging teak oriels above the entrance - RIBApix',
      url: 'https://www.architecture.com/image-library/RIBApix/licensed-image/poster/ismaili-centre-cromwell-gardens-south-kensington-london-closeup-of-the-overhanging-teak-oriels-above/posterid/RIBA56894.html',
      used_for: 'teak oriels above the main entrance',
    },
    {
      title: 'The Ismaili Centre, London - Archnet',
      url: 'https://archnet.org/sites/3053',
      used_for:
        'palette of whites, light greys and blues compatible with the surrounding buildings',
    },
    {
      title: 'Ismaili Centre London celebrates 35 years - the.ismaili',
      url: 'https://the.ismaili/global/news/institutional-news/ismaili-centre-london-celebrates-35-years',
      used_for: 'chamfered corner, chahar bagh roof garden, central fountain and pools',
    },
  ],
  notes:
    'Overture h=7.2 m is wrong; storey heights are estimates (ground 5 m, first 3.8 m, second 4.4 m, third/prayer ' +
    'hall 5.8 m to a 19 m garden wall, set-back fourth floor to 22.6 m). The footprint hole is used as the roof ' +
    'garden court. Cladding courses, the pier rhythm (2.6 m), window shapes (paired tall slots with pointed heads) ' +
    'and the oriel count are approximations; the main entrance is placed mid-way along Cromwell Gardens.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b = byId['6ee5bdcc-1f0d-4623-8d99-a91ca507c14f'];
    if (!b) return g;
    const ring = T.ccw(b.polys[0][0]);
    let hole = (b.polys[0][1] ?? []).slice();
    if (hole.length && kit.ringArea(hole) > 0) hole.reverse(); // CW
    const E = T.edges(ring);
    const white = kit.mat('#e9e8e3', { roughness: 0.6 });
    const grey = kit.mat('#c4c8cc', { roughness: 0.6 });
    const blue = kit.mat('#8d9cad', { roughness: 0.55 });
    const steel = kit.mat('#a9adb0', { roughness: 0.35, metalness: 0.7 });
    const teak = kit.mat('#7a5535', { roughness: 0.7 });
    const glass = kit.mat('#26323b', { roughness: 0.12, metalness: 0.4 });
    const Z1 = 8.8, // top of colonnaded bottom two floors
      Z3 = 19.0, // top of main body / garden wall
      ZT = 22.6; // set-back top floor
    // --- bottom two floors: recessed glazing behind granite piers ----------------
    const inner = kit.offsetRing(ring, -1.2);
    for (const e of T.edges(inner)) {
      T.quad(glass, e.a, e.b, 0, Z1);
      const n = Math.max(1, Math.round(e.len / 1.3));
      for (let k = 0; k <= n; k++)
        T.ebox(steel, e, (k * e.len) / n - 0.04, (k * e.len) / n + 0.04, 0, 0.12, 0, Z1);
      T.ebox(steel, e, 0, e.len, 0, 0.12, 4.9, 5.05);
    }
    kit.cap(batch, white, [[ring, inner.slice().reverse()]], Z1, { down: true });
    for (const e of E) {
      const n = Math.max(2, Math.round(e.len / 2.6));
      for (let k = 0; k <= n; k++) {
        const s = 0.5 + ((e.len - 1) * k) / n;
        T.ebox(grey, e, s - 0.35, s + 0.35, -1.2, 0, 0, Z1);
        T.ebox(white, e, s - 0.42, s + 0.42, -1.2, 0.05, Z1 - 0.6, Z1); // capital block
      }
      // bow windows between the piers on the first floor (every third bay)
      for (let k = 1; k < n; k += 3) {
        const s = 0.5 + ((e.len - 1) * (k + 0.5)) / n;
        const p = T.at(e, s, -0.3);
        const bow = new THREE.CylinderGeometry(0.95, 0.95, 3.0, 12, 1, false, 0, Math.PI).rotateX(
          Math.PI / 2,
        );
        const m = new THREE.Matrix4().makeRotationZ(e.ang + Math.PI).setPosition(p[0], p[1], 6.9);
        batch.addGeometry(glass, bow, m);
        bow.dispose();
        T.ebox(steel, e, s - 1.0, s + 1.0, -1.2, 0.7, 8.4, 8.6);
        T.ebox(steel, e, s - 1.0, s + 1.0, -1.2, 0.7, 5.3, 5.45);
      }
    }
    // plinth step
    kit.cornice(batch, grey, ring, 0, { height: 0.25, projection: 0.4 });
    // --- second and third floors: banded granite with paired slot windows ----------
    for (const e of E) T.quad(white, e.a, e.b, Z1, Z3);
    kit.cornice(batch, blue, ring, Z1, { height: 0.35, projection: 0.12 });
    for (let z = Z1 + 1.2; z < Z3 - 0.5; z += 1.25)
      kit.cornice(batch, grey, ring, z, { height: 0.18, projection: 0.03 });
    kit.cornice(batch, blue, ring, Z3 - 0.5, { height: 0.5, projection: 0.15 });
    for (const e of E) {
      const n = Math.max(2, Math.round(e.len / 2.6));
      for (let k = 0; k < n; k++) {
        const s = 0.5 + ((e.len - 1) * (k + 0.5)) / n;
        // second floor: paired slots
        for (const ds of [-0.32, 0.32])
          T.win(e, s + ds - 0.3, s + ds + 0.3, 9.8, {
            width: 0.42,
            height: 2.4,
            count: 1,
            margin: 0.05,
            glass,
            frame: steel,
            sill: blue,
            head: 'arch',
            bars: 0,
          });
        // third floor (prayer hall): taller slots
        T.win(e, s - 0.4, s + 0.4, 13.6, {
          width: 0.55,
          height: 3.8,
          count: 1,
          margin: 0.1,
          glass,
          frame: steel,
          sill: blue,
          head: 'arch',
          bars: 2,
        });
      }
    }
    // chamfered blue granite corner at the western tip
    // --- set-back top floor around the roof garden ----------------------------------
    const top = kit.offsetRing(ring, -2.4);
    kit.cap(batch, kit.mat('#9a9c98'), [[ring, top.slice().reverse()]], Z3);
    const zTop = (poly) => {
      kit.walls(batch, white, [[poly]], Z3, ZT);
    };
    zTop(top);
    if (hole.length) kit.walls(batch, white, [[hole]], Z3, ZT);
    kit.cap(batch, kit.mat('#a3a5a2'), hole.length ? [[top, hole]] : [[top]], ZT);
    kit.cornice(batch, blue, top, ZT - 0.35, { height: 0.35, projection: 0.2 });
    for (const e of T.edges(top)) {
      if (e.len < 3) continue;
      T.win(e, 0, e.len, Z3 + 0.6, {
        width: 0.9,
        height: 2.0,
        bay: 2.6,
        glass,
        frame: steel,
        sill: blue,
        head: 'segment',
        bars: 0,
      });
    }
    // garden wall / parapet at the main roof edge
    kit.walls(batch, white, [[ring]], Z3, Z3 + 0.6);
    // roof garden (chahar bagh) in the court: paving, four beds, channels, fountain
    if (hole.length) {
      const hr = hole.slice().reverse();
      kit.cap(batch, kit.mat('#d9d3c4'), [[hr]], Z3 + 0.05);
      const f = kit.ringFrame(hr);
      const ca = Math.cos(f.angle),
        sa = Math.sin(f.angle);
      const P = (u, v) => [f.cx + ca * u - sa * v, f.cy + sa * u + ca * v];
      const qL = f.length / 2 - 1.2,
        qW = f.width / 2 - 1.2;
      for (const su of [-1, 1])
        for (const sv of [-1, 1]) {
          const c = P((su * qL) / 2 + su * 0.4, (sv * qW) / 2 + sv * 0.4);
          kit.box(batch, kit.mat('grass'), c[0], c[1], Z3, qL - 1.2, qW - 1.2, 0.35, f.angle);
          const cp = P(su * (qL + 0.3), sv * (qW + 0.3));
          kit.box(batch, kit.mat('water'), cp[0], cp[1], Z3, 1.2, 1.2, 0.12, f.angle);
        }
      const c0 = P(0, 0);
      kit.box(batch, kit.mat('water'), c0[0], c0[1], Z3, f.length - 2, 0.5, 0.11, f.angle);
      kit.box(batch, kit.mat('water'), c0[0], c0[1], Z3, 0.5, f.width - 2, 0.11, f.angle);
      T.cyl(white, c0[0], c0[1], Z3, 0.4, 1.2, 1.2, 7);
      T.cyl(kit.mat('water'), c0[0], c0[1], Z3 + 0.4, 0.02, 1.05, 1.05, 7);
    }
    // --- main entrance on Cromwell Gardens with teak oriels above ----------------------
    const north = E.filter((e) => e.ny > 0.7).sort((p, q) => q.len - p.len)[0];
    {
      const s = north.len / 2;
      T.ebox(blue, north, s - 3.6, s + 3.6, -1.2, 0.3, Z1 - 1.0, Z1); // entrance lintel
      T.ebox(
        kit.mat('#3a3f44', { metalness: 0.5, roughness: 0.4 }),
        north,
        s - 2.0,
        s + 2.0,
        -1.3,
        -1.15,
        0,
        3.6,
      );
      for (const ds of [-2.4, 0, 2.4]) {
        T.ebox(teak, north, s + ds - 1.0, s + ds + 1.0, 0, 1.1, Z1 + 0.6, Z1 + 3.4);
        T.ebox(glass, north, s + ds - 0.8, s + ds + 0.8, 1.1, 1.14, Z1 + 0.9, Z1 + 3.1);
        for (const k of [-0.4, 0, 0.4])
          T.ebox(teak, north, s + ds + k - 0.04, s + ds + k + 0.04, 1.1, 1.18, Z1 + 0.9, Z1 + 3.1);
        T.ebox(teak, north, s + ds - 1.1, s + ds + 1.1, 0, 1.25, Z1 + 3.4, Z1 + 3.6);
      }
      for (let i = 0; i < 3; i++)
        T.ebox(grey, north, s - 3.0, s + 3.0, -1.2, 0.9 - i * 0.3, i * 0.15, (i + 1) * 0.15);
    }
    // rooftop plant on the top floor
    const pf = kit.ringFrame(top);
    kit.box(
      batch,
      kit.mat('#b9bbb7'),
      pf.cx + Math.cos(pf.angle) * pf.length * 0.36,
      pf.cy + Math.sin(pf.angle) * pf.length * 0.36,
      ZT,
      5,
      4,
      1.8,
      pf.angle,
    );
    g.add(batch.toGroup('ismaili_centre'));
    return g;
  },
};

// ---- local geometry helpers (modules have no imports) -------------------------------
function tools(THREE, kit, batch) {
  const ccw = (r) => {
    r = r.slice();
    if (kit.ringArea(r) < 0) r.reverse();
    return r;
  };
  const edges = (r) =>
    r.map((a, k) => {
      const b = r[(k + 1) % r.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        a,
        b,
        k,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
      };
    });
  // point along edge e at distance s, offset d outward
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  // box aligned with edge e: s0..s1 along, d0..d1 outward, z0..z1
  const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
    const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(
      batch,
      m,
      p[0],
      p[1],
      z0,
      Math.max(0.01, s1 - s0),
      Math.max(0.01, d1 - d0),
      Math.max(0.01, z1 - z0),
      e.ang,
      c,
    );
  };
  const prism = (m, ring, z0, z1, opts) => {
    kit.walls(batch, m, [[ring]], z0, z1, opts);
    kit.cap(batch, m, [[ring]], z1);
  };
  const M = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
  const cyl = (m, x, y, z0, h, r0, r1 = r0, seg = 12) => {
    const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z0 + h / 2));
    g.dispose();
  };
  const lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(Math.max(0.001, r), h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z));
    g.dispose();
  };
  // windows on the sub-span s0..s1 of edge e
  const win = (e, s0, s1, z, opts) => kit.windowRow(batch, at(e, s0), at(e, s1), z, opts);
  const quad = (m, p, q, z0, z1, c) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      c,
    );
  const tri = (m, p, q, r, c) =>
    batch.add(
      m,
      [p, q, r],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
      c,
    );
  // sloped band from ring at z0 to the ring inset by d at z1 (mansards, hips); returns inner ring
  const slope = (m, ring, z0, d, z1, capTop = true) => {
    const inn = kit.offsetRing(ring, -d);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inn[(k + 1) % ring.length],
        e = inn[k];
      batch.add(
        m,
        [
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [e[0], e[1], z1],
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    if (capTop) kit.cap(batch, m, [[inn]], z1);
    return inn;
  };
  // pitched gable roof over an edge-aligned rectangle: along e from s0..s1, depth d0..d1 (outward
  // negative = inward), ridge parallel to e. Gable triangles in wall material.
  const gableRoof = (roofM, wallM, e, s0, s1, d0, d1, z, rise, ov = 0.3) => {
    const dm = (d0 + d1) / 2;
    const P = (s, d, zz) => {
      const p = at(e, s, d);
      return [p[0], p[1], zz];
    };
    const A = P(s0 - ov, d0 - ov * Math.sign(d1 - d0), z),
      B = P(s1 + ov, d0 - ov * Math.sign(d1 - d0), z);
    const C = P(s1 + ov, dm, z + rise),
      D = P(s0 - ov, dm, z + rise);
    const A2 = P(s0 - ov, d1 + ov * Math.sign(d1 - d0), z),
      B2 = P(s1 + ov, d1 + ov * Math.sign(d1 - d0), z);
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    // undersides so the roof reads from below/behind
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    for (const s of [s0, s1]) {
      const p = P(s, d0, z),
        q = P(s, d1, z),
        r = P(s, dm, z + rise);
      tri(wallM, p, q, r);
      tri(wallM, q, p, r);
    }
  };
  const hasRoad = (e) => e; // placeholder for symmetry
  return { ccw, edges, at, ebox, prism, cyl, lathe, win, quad, tri, slope, gableRoof, M, hasRoad };
}

// Stucco terrace house fronts (Kensington type): rusticated raised ground floor,
// porches, first-floor balcony, moulded window surrounds, cornice, attic, mansard.
function stuccoTerrace(T, kit, batch, ring, o) {
  const { edges, at, ebox, win, cyl, slope } = T;
  const wall = o.wall ?? kit.mat('#ece6da');
  const back = o.back ?? kit.mat('#c9b48e');
  const trim = o.trim ?? kit.mat('#f6f2ea');
  const roofM = o.roofM ?? kit.mat('slate');
  const glass = o.glass ?? kit.mat('#2c3640', { roughness: 0.2, metalness: 0.3 });
  const frame = o.frame ?? kit.mat('#f4f4f0');
  const black = kit.mat('#1d1f22', { roughness: 0.5, metalness: 0.4 });
  const Z = o.levels; // floor lines e.g. [0, 1.2, 5.2, 9.4, 12.8, 15.9] ; last = main cornice
  const top = Z[Z.length - 1];
  const fronts = new Set(o.fronts);
  const E = edges(ring);
  // body
  for (const e of E) {
    const m = fronts.has(e.k) || (o.stuccoAll ?? false) ? wall : back;
    T.quad(m, e.a, e.b, 0, top);
  }
  // basement area / plinth band
  kit.cornice(batch, trim, ring, 0, { height: Z[1], projection: 0.08 });
  // string courses
  for (let i = 2; i < Z.length - 1; i++)
    kit.cornice(batch, trim, ring, Z[i] - 0.2, { height: 0.22, projection: 0.1 });
  // main cornice + blocking course
  kit.cornice(batch, trim, ring, top - 0.55, { height: 0.55, projection: 0.45, steps: 2 });
  kit.walls(batch, wall, [[ring]], top, top + 0.9);
  const pin = kit.offsetRing(ring, -0.3);
  kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + 0.9);
  kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + 0.9);
  // roof
  const zr = top + 0.6;
  let roofTop = zr;
  if (o.mansard !== false) {
    const mh = o.mansardH ?? 3.0;
    const inn = slope(roofM, pin, zr, mh * 0.35, zr + mh, false);
    const inn2 = kit.offsetRing(inn, -0.3);
    kit.cap(batch, kit.mat('lead'), [[inn]], zr + mh);
    roofTop = zr + mh;
    // dormers on fronts
    for (const e of E) {
      if (!fronts.has(e.k) || e.len < 4) continue;
      const n = Math.max(1, Math.round((e.len - 2) / (o.bay ?? 2.6)));
      for (let i = 0; i < n; i++) {
        const s = 1 + ((e.len - 2) * (i + 0.5)) / n;
        ebox(roofM, e, s - 0.75, s + 0.75, -1.6, -0.55, zr, zr + 2.2);
        ebox(trim, e, s - 0.8, s + 0.8, -1.6, -0.5, zr + 2.2, zr + 2.35);
        ebox(glass, e, s - 0.45, s + 0.45, -0.58, -0.5, zr + 0.4, zr + 1.9);
      }
    }
  } else {
    kit.cap(batch, kit.mat('#8a8a86'), [[pin]], zr);
  }
  // chimney stacks along party walls (short edges perpendicular to the front) or spaced
  let chim = o.chimneys ?? [];
  if (o.autoChimneys)
    for (const e of E)
      if (!fronts.has(e.k) && e.len > 6) {
        const p = at(e, e.len / 2, -0.7);
        chim = chim.concat([[p[0], p[1], e.ang + Math.PI / 2]]);
      }
  if (chim.length) {
    const pot = kit.mat('#b0603e');
    for (const [x, y, ang] of chim) {
      kit.box(batch, back, x, y, roofTop - 1, 0.7, 2.4, 2.4, ang);
      kit.box(batch, trim, x, y, roofTop + 1.4, 0.85, 2.6, 0.2, ang);
      for (let k = -1; k <= 1; k++)
        cyl(
          pot,
          x - Math.sin(ang) * k * 0.7,
          y + Math.cos(ang) * k * 0.7,
          roofTop + 1.6,
          0.6,
          0.14,
          0.11,
          6,
        );
    }
  }
  // fenestration
  const bay = o.bay ?? 2.6;
  for (const e of E) {
    if (e.len < 1.6) continue;
    const front = fronts.has(e.k);
    for (let s = 1; s < Z.length - 1; s++) {
      const h = Z[s + 1] - Z[s];
      const first = s === 2;
      const opts = front
        ? {
            width: 1.15,
            height: Math.min(h - 1.0, first ? 2.9 : 2.3),
            bay,
            margin: 0.7,
            glass,
            frame,
            sill: trim,
            surround: 0.16,
            surroundMat: trim,
            head: first ? 'pediment' : s === 1 ? 'lintel' : 'lintel',
            bars: 1,
          }
        : {
            width: 1.0,
            height: Math.min(h - 1.0, 2.0),
            bay: bay + 0.6,
            margin: 0.8,
            glass,
            frame,
            sill: trim,
            head: 'none',
            bars: 1,
          };
      if (!front && o.plainBack === 'blank') continue;
      win(e, 0, e.len, Z[s] + (first ? 0.25 : 0.7), opts);
    }
    if (!front) continue;
    // rusticated ground floor: horizontal grooves
    for (let z = Z[1] + 0.5; z < Z[2] - 0.3; z += 0.5)
      ebox(trim, e, 0, e.len, 0, 0.06, z, z + 0.08);
    // first-floor balcony with balustrade
    if (o.balcony !== false) {
      ebox(trim, e, 0.2, e.len - 0.2, 0, 0.9, Z[2] - 0.22, Z[2]);
      kit.balustrade(batch, trim, [at(e, 0.3, 0.8), at(e, e.len - 0.3, 0.8)], Z[2], {
        height: 0.95,
        spacing: 0.32,
      });
    }
    // area railings at pavement edge
    if (o.railings !== false) {
      for (let s = 0.2; s < e.len; s += 0.25)
        ebox(black, e, s - 0.015, s + 0.015, 2.4, 2.43, 0, 1.1);
      ebox(black, e, 0, e.len, 2.38, 2.45, 1.05, 1.1);
    }
  }
  // porches
  for (const [k, s] of o.porches ?? []) {
    const e = E[k];
    const w = 2.4,
      z0 = Z[1],
      zc = Z[2] - 0.3;
    for (const ds of [-w / 2, w / 2]) cyl(trim, ...at(e, s + ds, 1.9), z0, zc - z0, 0.22, 0.2, 10);
    for (const ds of [-w / 2, w / 2]) ebox(trim, e, s + ds - 0.2, s + ds + 0.2, 0, 0.4, z0, zc);
    ebox(trim, e, s - w / 2 - 0.35, s + w / 2 + 0.35, 0, 2.3, zc, Z[2] - 0.22);
    // steps up from pavement across the area
    for (let i = 0; i < 5; i++)
      ebox(trim, e, s - 0.9, s + 0.9, 1.6 + i * 0.3, 2.5 + 0.3 * i, 0, z0 - i * (z0 / 5));
    ebox(kit.mat('#1f2a30'), e, s - 0.6, s + 0.6, 0, 0.05, z0, zc - 0.5);
  }
  return { top, roofTop };
}

// Generic masonry block: walls, storey windows on every edge long enough, string
// courses, cornice, parapet and a flat or slated (mansard / hipped) roof.
function masonryBlock(T, kit, batch, ring, o) {
  const wall = o.wall,
    trim = o.trim ?? wall;
  const Z = o.levels;
  const top = Z[Z.length - 1];
  const E = T.edges(ring);
  for (const e of E) T.quad(o.wallFor ? o.wallFor(e) : wall, e.a, e.b, 0, top);
  if (o.plinth) kit.cornice(batch, trim, ring, 0, { height: o.plinth, projection: 0.08 });
  for (const z of o.bands ?? [])
    kit.cornice(batch, trim, ring, z, { height: 0.25, projection: 0.1 });
  kit.cornice(batch, trim, ring, top - (o.corniceH ?? 0.45), {
    height: o.corniceH ?? 0.45,
    projection: o.corniceP ?? 0.35,
    steps: 2,
  });
  const par = o.parapet ?? 0.8;
  const pin = kit.offsetRing(ring, -0.3);
  if (par > 0) {
    kit.walls(batch, wall, [[ring]], top, top + par);
    kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + par);
    kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + par);
  }
  let roofTop = top;
  if (o.roof === 'slope') {
    const inn = T.slope(
      o.roofM ?? kit.mat('slate'),
      pin,
      top + 0.2,
      o.roofInset ?? 2.5,
      top + (o.roofRise ?? 3.5),
      false,
    );
    kit.cap(batch, kit.mat('lead'), [[inn]], top + (o.roofRise ?? 3.5));
    roofTop = top + (o.roofRise ?? 3.5);
  } else kit.cap(batch, o.roofM ?? kit.mat('#8b8b87'), [[pin]], top + 0.15);
  for (const e of E) {
    if (e.len < (o.minEdge ?? 2.5)) continue;
    for (let s = 0; s < Z.length - 1; s++) {
      const w = typeof o.win === 'function' ? o.win(s, e, Z[s + 1] - Z[s]) : o.win;
      if (!w) continue;
      T.win(e, 0, e.len, Z[s] + (w.sillOff ?? 0.9), w);
    }
  }
  return { top, roofTop, E };
}

// Frame facade: brick piers proud of the wall, concrete floor bands, metal windows between.
function pierFrame(T, kit, batch, e, z0, z1, storey, o) {
  const n = Math.max(1, Math.round(e.len / (o.bay ?? 3.2)));
  for (let k = 0; k <= n; k++) {
    const s = (k * e.len) / n;
    T.ebox(
      o.pier,
      e,
      Math.max(0, s - (o.pierW ?? 0.3)),
      Math.min(e.len, s + (o.pierW ?? 0.3)),
      -0.05,
      o.pierD ?? 0.3,
      z0,
      z1,
    );
  }
  for (let z = z0; z < z1 - 0.5; z += storey) {
    T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z, z + (o.bandH ?? 0.4));
    for (let k = 0; k < n; k++) {
      const s0 = (k * e.len) / n + (o.pierW ?? 0.3),
        s1 = ((k + 1) * e.len) / n - (o.pierW ?? 0.3);
      if (s1 - s0 < 0.4) continue;
      const zt = Math.min(z1, z + storey);
      if (o.spandrel)
        T.ebox(
          o.spandrel,
          e,
          s0,
          s1,
          0.0,
          0.07,
          z + (o.bandH ?? 0.4),
          z + (o.bandH ?? 0.4) + o.spandrelH,
        );
      const g0 = z + (o.bandH ?? 0.4) + (o.spandrel ? o.spandrelH : 0);
      T.ebox(o.glass, e, s0, s1, 0.01, 0.05, g0, zt);
      const m = Math.max(1, Math.round((s1 - s0) / (o.mullion ?? 1.1)));
      for (let j = 1; j < m; j++) {
        const s = s0 + ((s1 - s0) * j) / m;
        T.ebox(o.frame, e, s - 0.035, s + 0.035, 0.03, 0.1, g0, zt);
      }
      T.ebox(o.frame, e, s0, s1, 0.03, 0.1, g0 + (zt - g0) * 0.62, g0 + (zt - g0) * 0.62 + 0.06);
    }
  }
  T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z1 - 0.1, z1 + 0.3);
}

// Clip a ring to the half-plane n . p >= c (Sutherland-Hodgman).
function clipHalf(ring, n, c) {
  const out = [];
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    const fp = n[0] * p[0] + n[1] * p[1] - c,
      fq = n[0] * q[0] + n[1] * q[1] - c;
    if (fp >= 0) out.push(p);
    if (fp * fq < 0) {
      const t = fp / (fp - fq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
}
