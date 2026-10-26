// Hyde Park Chapel, Church of Jesus Christ of Latter-day Saints, 64-68 Exhibition Road
// (Princes Gate), South Kensington. T. P. Bennett & Son (Thomas Bennett), contractors
// McLaughlin and Harvey; dedicated by David O. McKay on 26 February 1961. Reinforced
// concrete clad in Portland stone; four storeys with a six-storey tower whose west face
// carries a 75 ft spire covered in gold leaf, above a dalle de verre window by Pierre
// Fourmaintraux (Whitefriars). Chapel, font and cultural hall on the ground floor.
export default {
  id: 'hyde_park_chapel',
  name: 'Hyde Park Chapel (LDS)',
  claims: ['19ea7996-da2b-4900-970b-c3195c5b7daf'],
  references: [
    {
      title: 'Hyde Park Chapel - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hyde_Park_Chapel',
      used_for:
        'T. P. Bennett and Son; McLaughlin and Harvey; reinforced concrete with Portland stone; four storeys, six-storey tower, 75 ft gold-leaf spire on the tower west face; dalle de verre window by Fourmaintraux',
    },
    {
      title: 'Hyde Park Chapel on Exhibition Road - Heritage Open Days',
      url: 'https://www.heritageopendays.org.uk/submission-event/hyde-park-chapel-on-exibition-road.html',
      used_for: 'completed 26 February 1961 at a cost of 300,000 pounds; structure and spire',
    },
    {
      title: 'Hyde Park Chapel - Manchester History (architecture 1960)',
      url: 'https://manchesterhistory.net/architecture/1960/hydeparkchapel.html',
      used_for: 'T. P. Bennett & Son, 1961',
    },
    {
      title: 'The strange new chapel - Church of Jesus Christ UK',
      url: 'https://uk.churchofjesuschrist.org/the-strange-new-chapel',
      used_for: 'dedication by David O McKay; building history',
    },
  ],
  notes:
    'Storey heights (5.0 m ground, 3.6 m above; main parapet 16.2 m, tower 24 m) are estimates from the storey ' +
    'counts (Overture 14.2 m). The tower is placed at the north end of the Exhibition Road front; the spire is a ' +
    'slender gilded square needle from the tower top (23 m, i.e. 75 ft). Stone fin rhythm, window grid, the ' +
    'entrance canopy and the colours of the dalle de verre panel are assumptions.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const b = byId['19ea7996-da2b-4900-970b-c3195c5b7daf'];
    if (!b) return g;
    const ring = T.ccw(b.polys[0][0]);
    const E = T.edges(ring);
    const portland = kit.mat('#e6e0d2', { roughness: 0.8 });
    const portlandD = kit.mat('#d8d1c0', { roughness: 0.8 });
    const glass = kit.mat('#27313a', { roughness: 0.12, metalness: 0.4 });
    const mull = kit.mat('#9fa4a6', { roughness: 0.35, metalness: 0.7 });
    const gold = kit.mat('gold');
    const H = 16.2,
      G = 5.0,
      ST = 3.6;
    const west = E.filter((e) => e.nx < -0.7).sort((p, q) => q.len - p.len)[0];
    // main body
    for (const e of E) {
      if (e.len < 0.5) continue;
      T.quad(portland, e.a, e.b, 0, H);
      const front = e === west || e.ny < -0.7;
      // ground floor: tall glazing
      if (front) {
        const n = Math.max(1, Math.round(e.len / 4));
        for (let k = 0; k < n; k++) {
          const s0 = (k * e.len) / n + 0.5,
            s1 = ((k + 1) * e.len) / n - 0.5;
          T.ebox(glass, e, s0, s1, -0.05, 0.03, 0.6, G - 0.6);
          for (let j = 1; j < 3; j++)
            T.ebox(
              mull,
              e,
              s0 + ((s1 - s0) * j) / 3 - 0.04,
              s0 + ((s1 - s0) * j) / 3 + 0.04,
              0,
              0.06,
              0.6,
              G - 0.6,
            );
        }
      }
      // upper floors: vertical stone fins with windows between
      const n = Math.max(2, Math.round(e.len / 1.8));
      for (let k = 0; k <= n; k++) {
        const s = (k * e.len) / n;
        T.ebox(portlandD, e, s - 0.18, s + 0.18, 0, front ? 0.45 : 0.25, G, H - 0.9);
      }
      for (let st = 0; st < 3; st++) {
        const z = G + st * ST;
        for (let k = 0; k < n; k++) {
          const s0 = (k * e.len) / n + 0.3,
            s1 = ((k + 1) * e.len) / n - 0.3;
          T.ebox(glass, e, s0, s1, -0.05, 0.02, z + 0.8, z + ST - 0.4);
          T.ebox(portlandD, e, s0, s1, 0, 0.12, z + 0.7, z + 0.8);
        }
      }
    }
    kit.cornice(batch, portlandD, ring, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(batch, portlandD, ring, G - 0.5, { height: 0.5, projection: 0.5 });
    kit.cornice(batch, portlandD, ring, H - 0.9, { height: 0.9, projection: 0.25 });
    kit.cap(batch, kit.mat('#8f908c'), [[kit.offsetRing(ring, -0.2)]], H - 0.3);
    // entrance canopy on Exhibition Road
    T.ebox(portlandD, west, west.len * 0.45, west.len * 0.8, -0.2, 3.0, 3.5, 3.85);
    for (const s of [west.len * 0.47, west.len * 0.78])
      T.cyl(mull, ...T.at(west, s, 2.7), 0, 3.5, 0.1, 0.1, 8);
    for (let i = 0; i < 3; i++)
      T.ebox(
        portlandD,
        west,
        west.len * 0.45,
        west.len * 0.8,
        0,
        2.6 - i * 0.6,
        i * 0.15,
        (i + 1) * 0.15,
      );
    // tower at the north end of the front
    const tw = 8.0,
      td = 8.0,
      TH = 24.0;
    const p0 = T.at(west, 0.0, 0.0);
    const tr = [T.at(west, 0, 0.6), T.at(west, 0, -td), T.at(west, tw, -td), T.at(west, tw, 0.6)];
    const tower = T.ccw(tr);
    T.prism(portland, tower, H - 1, TH);
    kit.walls(batch, portland, [[tower]], 0, H);
    kit.cornice(batch, portlandD, tower, TH - 0.8, { height: 0.8, projection: 0.2 });
    for (const e of T.edges(tower)) {
      if (e.len < 2 || e.nx * west.nx + e.ny * west.ny > 0.7) continue;
      for (let z = H + 0.6; z < TH - 1.5; z += 3.0)
        T.win(e, 0, e.len, z, {
          width: 0.7,
          height: 1.8,
          bay: 1.6,
          margin: 1.0,
          glass,
          frame: mull,
          sill: portlandD,
          head: 'none',
          bars: 0,
        });
    }
    // dalle de verre window on the west face of the tower
    const dv = kit.paintedMaterial(
      'hyde_park_chapel:dalle',
      128,
      512,
      (c, w, h) => {
        const r = kit.rng(7.1);
        c.fillStyle = '#1b1f2a';
        c.fillRect(0, 0, w, h);
        const cols = ['#2c63b8', '#e0b23a', '#c63d32', '#3a9a5a', '#7fb7e6', '#f2e4a0'];
        for (let y = 0; y < h; y += 16)
          for (let x = 0; x < w; x += 16) {
            c.fillStyle = cols[Math.floor(r() * cols.length)];
            c.fillRect(x + 2, y + 2, 12 + r() * 2, 12 + r() * 2);
          }
      },
      { roughness: 0.3, emissive: '#151515' },
    );
    const wa = T.at(west, tw / 2 - 1.3, 0.62),
      wb = T.at(west, tw / 2 + 1.3, 0.62);
    // face points outward: quad from b to a with normal to the right of a->b which is outward (west)
    T.quad(dv, wa, wb, 6.0, TH - 3.5);
    T.ebox(portlandD, west, tw / 2 - 1.6, tw / 2 + 1.6, 0.6, 0.8, 5.7, 6.0);
    // gilded spire, 75 ft, rising from the tower's west face
    const sp = T.at(west, tw / 2, 0.2);
    const needle = new THREE.CylinderGeometry(0.04, 0.55, 23, 4, 1)
      .rotateX(Math.PI / 2)
      .rotateZ(Math.PI / 4);
    batch.addGeometry(gold, needle, T.M(sp[0], sp[1], TH - 1.0 + 11.5));
    needle.dispose();
    kit.box(batch, portlandD, sp[0], sp[1], TH - 1.2, 1.4, 1.4, 1.4, west.ang);
    void p0;
    g.add(batch.toGroup('hyde_park_chapel'));
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
