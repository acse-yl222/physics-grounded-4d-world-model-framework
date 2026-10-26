// St Mary's Hospital, Paddington: the Clarence Memorial Wing on Praed Street (Sir William Emerson,
// designed 1892, opened 1904; Grade II). Eclectic Renaissance: ashlar semi-basement and ground
// floor, red brick upper floors with ashlar dressings, a centre block with Ionic pilasters and
// columns and a two-tier loggia on the first and second floors, flanked by octagonal turrets; a
// canted bay forms an angle turret at the right; double mansard slate roof with dormers. Alexander
// Fleming discovered penicillin in his laboratory here in 1928 (plaque).
export default {
  id: 'st_marys_clarence_memorial_wing',
  name: "Clarence Memorial Wing, St Mary's Hospital",
  claims: ['e3ecca62-3f84-403d-b38c-6fbcaaaad174'],
  references: [
    {
      title:
        "Clarence Memorial Wing of St Mary's Hospital - British Listed Buildings (list entry 1265525)",
      url: 'https://britishlistedbuildings.co.uk/101265525-clarence-memorial-wing-of-st-marys-hospital-hyde-park-ward',
      used_for:
        'Emerson, Eclectic Renaissance; ashlar ground floor and basement, red brick with ashlar dressings and loggias; slate double mansard with dormers; 4 storeys, basement, semi-basement and attic; centre with Ionic pilasters/columns, octagonal turrets, 2-tier loggia, canted angle bay; Fleming plaque',
    },
    {
      title: "Clarence Memorial Wing, St Mary's Hospital - Victorian Web",
      url: 'https://victorianweb.org/victorian/art/architecture/emerson/2.html',
      used_for:
        '1892 design by Sir William Emerson, opened 1904; Pevsner: "florid glories of late Victorian Baroque"',
    },
    {
      title: "1896 Clarence Memorial Wing, St Mary's Hospital - Archiseek",
      url: 'https://www.archiseek.com/1896-clarence-memorial-wing-st-marys-hospital-paddington-london',
      used_for: 'main frontage on Praed Street',
    },
    {
      title: "St Mary's Hospital, London - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Mary%27s_Hospital,_London',
      used_for: 'hospital history, Fleming laboratory',
    },
  ],
  notes:
    'Overture footprint; heights from the listing storey count rather than the data (12.4 m): 5.6 m ashlar ' +
    'base (semi-basement + ground), three 3.9 m brick storeys to an 18.5 m cornice, double mansard to ' +
    '~24.5 m, turrets to ~29 m. Turret caps (lead ogee domes), loggia bay widths, dormer rhythm and the ' +
    'colour of the brick are estimates; Ionic orders are represented by the kit column with a simple ' +
    'capital. Rear wings are modelled with the same materials but plainer detail.',
  build({ THREE, kit, byId }) {
    const L = makeLib(THREE, kit, 0.2087);
    const g = new THREE.Group();
    const b = new kit.MeshBatch();
    const ring = L.ccw(byId['e3ecca62-3f84-403d-b38c-6fbcaaaad174'].polys[0][0]);
    const brick = L.brick('cmw:brick', '#a04a35', { var: 0.15 });
    const ashlar = L.panels('cmw:ashlar', '#d6c9ac', {
      cols: 8,
      rows: 8,
      joint: 'rgba(90,80,60,0.35)',
      v: 0.06,
    });
    const stone = kit.mat('#d9cdb2', { roughness: 0.85 });
    const slate = kit.roof('slate', 1);
    const lead = kit.mat('lead');
    const frame = kit.mat('#efece4');
    const glass = kit.mat('#2a3640', { roughness: 0.15, metalness: 0.3 });
    const dark = kit.mat('#2b2622');
    const B = 5.6,
      ST = 3.9,
      C = B + 3 * ST; // cornice height 17.3
    // base and brick body
    L.walls(b, ashlar, ring, 0, B);
    for (const z of [1.2, 2.6, 4.0])
      kit.cornice(b, stone, ring, z, { height: 0.12, projection: 0.05 });
    kit.cornice(b, stone, ring, B - 0.3, { height: 0.45, projection: 0.2, steps: 2 });
    L.walls(b, brick, ring, B, C);
    kit.cornice(b, stone, ring, B + ST - 0.1, { height: 0.3, projection: 0.08 });
    kit.cornice(b, stone, ring, B + 2 * ST - 0.1, { height: 0.25, projection: 0.06 });
    kit.cornice(b, stone, ring, C - 0.2, { height: 0.9, projection: 0.55, steps: 3 });
    const E = L.edges(ring);
    const front = E.reduce((p, q) =>
      q.len * (q.nx * 0.67 - q.ny * 0.74 > 0.9 ? 1 : 0) >
      p.len * (p.nx * 0.67 - p.ny * 0.74 > 0.9 ? 1 : 0)
        ? q
        : p,
    );
    const mid = front.len * 0.45,
      CW = 14; // centre block
    const inCentre = (e, s) => e === front && Math.abs(s - mid) < CW / 2 + 2.5;
    // windows: arched in the ashlar ground floor, lintel+stone surrounds above
    for (const e of E) {
      if (e.len < 3.5) continue;
      const fr = e === front;
      const segs = fr
        ? [
            [0, mid - CW / 2 - 2.6],
            [mid + CW / 2 + 2.6, e.len],
          ]
        : [[0, e.len]];
      for (const [s0, s1] of segs) {
        if (s1 - s0 < 3) continue;
        const a = L.at(e, s0),
          c = L.at(e, s1);
        kit.windowRow(b, a, c, 1.5, {
          width: 1.3,
          height: 2.6,
          bay: 3.4,
          head: 'arch',
          frame,
          glass,
          sill: stone,
          bars: 1,
          margin: 0.9,
        });
        for (let k = 0; k < 3; k++)
          kit.windowRow(b, a, c, B + k * ST + 0.8, {
            width: 1.25,
            height: k === 0 ? 2.5 : 2.3,
            bay: 3.4,
            head: k === 0 ? 'pediment' : k === 1 ? 'segment' : 'lintel',
            frame,
            glass,
            sill: stone,
            bars: 1,
            margin: 0.9,
            surround: 0.18,
            surroundMat: stone,
          });
      }
    }
    // centre block: projecting ashlar-dressed frontispiece with two-tier loggia and order
    {
      const e = front,
        s0 = mid - CW / 2,
        s1 = mid + CW / 2;
      L.ebox(b, stone, e, s0, s1, 0, 0.9, 0, B);
      L.ebox(b, brick, e, s0, s1, 0, 0.6, B, C);
      for (const s of [s0, s1]) L.ebox(b, stone, e, s - 0.5, s + 0.5, 0, 1.0, B, C); // stone piers
      // loggias: dark recess with columns and balustrades on floors 1 and 2
      for (let k = 0; k < 2; k++) {
        const z = B + k * ST;
        L.ebox(b, dark, e, s0 + 0.6, s1 - 0.6, 0.55, 0.62, z + 0.3, z + ST - 0.3);
        kit.colonnade(
          b,
          stone,
          L.at(e, s0 + 1.2, 0.95),
          L.at(e, s1 - 1.2, 0.95),
          z + 0.3,
          ST - 0.6,
          { count: 6, radius: 0.24, capital: 'corinthian' },
        );
        L.ebox(b, stone, e, s0 + 0.6, s1 - 0.6, 0.6, 1.25, z + ST - 0.45, z + ST - 0.1);
        kit.balustrade(b, stone, [L.at(e, s0 + 0.8, 1.05), L.at(e, s1 - 0.8, 1.05)], z + 0.2, {
          height: 0.95,
          spacing: 0.32,
        });
      }
      // top storey: pilasters and windows
      for (let k = 0; k <= 4; k++)
        L.ebox(
          b,
          stone,
          e,
          s0 + 1 + (k * (CW - 2)) / 4 - 0.25,
          s0 + 1 + (k * (CW - 2)) / 4 + 0.25,
          0.6,
          0.85,
          B + 2 * ST,
          C - 0.2,
        );
      kit.windowRow(b, L.at(e, s0 + 1, 0.62), L.at(e, s1 - 1, 0.62), B + 2 * ST + 0.8, {
        count: 4,
        width: 1.3,
        height: 2.2,
        head: 'arch',
        frame,
        glass,
        sill: stone,
        margin: 0.3,
      });
      // entrance: rusticated arch with steps
      L.ebox(b, dark, e, mid - 1.6, mid + 1.6, 0.85, 0.95, 0.6, 3.8);
      const arch = new THREE.TorusGeometry(1.75, 0.3, 6, 12, Math.PI)
        .rotateX(Math.PI / 2)
        .rotateZ(e.ang);
      const c = L.at(e, mid, 0.95);
      b.addGeometry(stone, arch, new THREE.Matrix4().makeTranslation(c[0], c[1], 3.8));
      arch.dispose();
      for (let k = 0; k < 4; k++)
        L.ebox(
          b,
          stone,
          e,
          mid - 2.6 + k * 0.2,
          mid + 2.6 - k * 0.2,
          0.9,
          2.6 - k * 0.4,
          k * 0.15,
          (k + 1) * 0.15,
        );
      // segmental pediment / attic gable over the centre
      L.gable(b, stone, stone, e, s0 - 0.3, s1 + 0.3, C + 0.7, 2.6, 1.0);
      L.ebox(b, stone, e, s0 - 0.3, s1 + 0.3, 0.2, 1.1, C, C + 0.7);
      // octagonal turrets flanking the centre
      for (const s of [s0 - 1.9, s1 + 1.9]) {
        const p = L.at(e, s, 0.4);
        const oct = new THREE.CylinderGeometry(1.9, 1.9, C + 2.5 - B, 8).rotateX(Math.PI / 2);
        b.addGeometry(
          brick,
          oct,
          new THREE.Matrix4().makeTranslation(p[0], p[1], B + (C + 2.5 - B) / 2),
        );
        oct.dispose();
        const base = new THREE.CylinderGeometry(2.05, 2.05, B, 8).rotateX(Math.PI / 2);
        b.addGeometry(stone, base, new THREE.Matrix4().makeTranslation(p[0], p[1], B / 2));
        base.dispose();
        for (const z of [B + ST, C - 0.2, C + 2.3]) {
          const band = new THREE.CylinderGeometry(2.15, 2.15, 0.4, 8).rotateX(Math.PI / 2);
          b.addGeometry(stone, band, new THREE.Matrix4().makeTranslation(p[0], p[1], z + 0.2));
          band.dispose();
        }
        // slit windows on the turret faces toward the street
        for (let k = 0; k < 3; k++) {
          const w = L.at(e, s, 0.4 + 1.85);
          kit.box(b, glass, w[0], w[1], B + 0.9 + k * ST, 0.7, 0.1, 2.0, e.ang);
        }
        g.add(
          kit.lathe(
            lead,
            [
              [2.1, 0],
              [2.0, 0.5],
              [1.6, 1.6],
              [0.9, 2.6],
              [0.35, 3.3],
              [0.12, 3.9],
              [0.0, 4.6],
            ],
            { x: p[0], y: p[1], z: C + 2.7, segments: 8 },
          ),
        );
      }
    }
    // angle turret: canted bay at the right-hand (north-east) end of the front
    {
      const e = front,
        s = front.len - 2.2,
        p = L.at(e, s, 0.2);
      const oct = new THREE.CylinderGeometry(2.4, 2.4, C - B, 6).rotateX(Math.PI / 2);
      b.addGeometry(brick, oct, new THREE.Matrix4().makeTranslation(p[0], p[1], B + (C - B) / 2));
      oct.dispose();
      g.add(
        kit.lathe(
          kit.mat('slate'),
          [
            [2.6, 0],
            [2.3, 1.0],
            [1.3, 3.0],
            [0.2, 4.6],
            [0, 5.2],
          ],
          { x: p[0], y: p[1], z: C + 0.6, segments: 6 },
        ),
      );
    }
    // double mansard: steep lower slope with dormers, shallow upper slope
    const m1 = L.hipRoof(b, slate, ring, C + 0.6, 4.2, 1.3, {
      overhang: 0.1,
      top: slate,
      soffit: stone,
    });
    const m2 = L.hipRoof(b, slate, m1.inner, m1.top, 1.4, 3.5, {
      overhang: 0.0,
      top: kit.mat('#525860'),
    });
    for (const e of L.edges(m1.inner)) {
      if (e.len < 4) continue;
      const n = Math.floor((e.len - 1) / 3.6);
      for (let k = 0; k < n; k++) {
        const s = ((k + 0.5) * e.len) / n;
        if (inCentre(e, s)) continue;
        const c = L.at(e, s, 0.35);
        kit.box(b, stone, c[0], c[1], C + 1.4, 1.5, 0.9, 2.0, e.ang);
        const w = L.at(e, s, 0.82);
        kit.box(b, glass, w[0], w[1], C + 1.6, 0.95, 0.05, 1.4, e.ang);
        const cap = L.at(e, s, 0.3);
        kit.box(b, lead, cap[0], cap[1], C + 3.4, 1.8, 1.1, 0.25, e.ang);
      }
    }
    // chimney stacks on the upper roof
    for (const e of L.edges(m2.inner))
      if (e.len > 10)
        for (let s = 4; s < e.len - 2; s += 12) {
          const c = L.at(e, s, 0.4);
          L.chimney(b, brick, stone, c[0], c[1], m2.top - 0.5, 2.6, e.ang, 1.8, 0.9);
        }
    // blue plaque by the entrance (Fleming)
    {
      const plaque = kit.paintedMaterial('cmw:plaque', 128, 128, (c, w, h) => {
        c.fillStyle = '#d9cdb2';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#1f4f8f';
        c.beginPath();
        c.arc(w / 2, h / 2, w / 2 - 4, 0, Math.PI * 2);
        c.fill();
        c.fillStyle = '#fff';
        c.font = 'bold 13px sans-serif';
        c.textAlign = 'center';
        c.fillText('PENICILLIN', w / 2, h / 2 - 4);
        c.fillText('FLEMING 1928', w / 2, h / 2 + 14);
      });
      const e = front;
      L.quad(
        b,
        plaque,
        L.at(e, mid + CW / 2 + 3.2, 0.03),
        L.at(e, mid + CW / 2 + 4.0, 0.03),
        2.4,
        3.2,
      );
    }
    g.add(b.toGroup('st_marys_clarence_memorial_wing'));
    return g;
  },
};

// ---- shared hospital-block helpers (kept in-module: landmark modules have no imports) ----
function makeLib(THREE, kit, seed) {
  const R = kit.rng(seed);
  const ccw = (r) => {
    const o = [];
    for (const p of r) {
      const q = o[o.length - 1];
      if (!q || Math.hypot(p[0] - q[0], p[1] - q[1]) > 0.25) o.push(p);
    }
    while (
      o.length > 3 &&
      Math.hypot(o[0][0] - o[o.length - 1][0], o[0][1] - o[o.length - 1][1]) < 0.25
    )
      o.pop();
    return kit.ringArea(o) < 0 ? o.reverse() : o;
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
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  const ebox = (b, m, e, s0, s1, d0, d1, z0, z1, col) => {
    const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(b, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang, col);
  };
  const okOffset = (r, o) => {
    if (kit.ringArea(o) <= 0) return false;
    for (let k = 0; k < r.length; k++) {
      const a = r[k],
        b = r[(k + 1) % r.length],
        p = o[k],
        q = o[(k + 1) % o.length];
      if ((b[0] - a[0]) * (q[0] - p[0]) + (b[1] - a[1]) * (q[1] - p[1]) <= 0) return false;
    }
    return true;
  };
  const safeOffset = (r, d) => {
    for (let t = 0; t < 7; t++, d *= 0.6) {
      const o = kit.offsetRing(r, d);
      if (okOffset(r, o)) return o;
    }
    return null;
  };
  const rev = (r) => r.slice().reverse();
  const quad = (b, m, p, q, z0, z1, z0q = z0, z1q = z1) =>
    b.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0q],
      [q[0], q[1], z1q],
      [p[0], p[1], z1],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );

  // Brick / render / cladding textures: one tile = 4 bays x 2 storeys of kit.walls UVs (14.4 x 6.4 m).
  const brick = (key, base, { var: v = 0.12, mortar = 'rgba(225,215,200,0.22)', bands } = {}) =>
    kit.paintedMaterial(key, 512, 256, (c, w, h) => {
      const r = kit.rng(key.length * 0.137 + 0.01);
      c.fillStyle = base;
      c.fillRect(0, 0, w, h);
      const ch = 4;
      for (let y = 0; y < h; y += ch) {
        const off = (y / ch) % 2 ? 0 : 4;
        for (let x = -off; x < w; x += 8) {
          const t = (r() - 0.5) * v;
          c.fillStyle = t > 0 ? `rgba(255,240,220,${t})` : `rgba(30,15,5,${-t})`;
          c.fillRect(x, y, 8, ch);
        }
        c.fillStyle = mortar;
        c.fillRect(0, y, w, 1);
      }
      if (bands)
        for (const [y0, y1, col] of bands)
          ((c.fillStyle = col), c.fillRect(0, y0 * h, w, (y1 - y0) * h));
    });
  const plain = (key, base, v = 0.06) =>
    kit.paintedMaterial(key, 256, 128, (c, w, h) => {
      const r = kit.rng(key.length * 0.31 + 0.2);
      c.fillStyle = base;
      c.fillRect(0, 0, w, h);
      for (let k = 0; k < 1400; k++) {
        const t = (r() - 0.5) * v;
        c.fillStyle = t > 0 ? `rgba(255,255,255,${t})` : `rgba(0,0,0,${-t})`;
        c.fillRect(r() * w, r() * h, 3, 2);
      }
    });
  const panels = (
    key,
    base,
    { cols = 8, rows = 4, joint = 'rgba(40,40,40,0.35)', v = 0.08 } = {},
  ) =>
    kit.paintedMaterial(key, 256, 128, (c, w, h) => {
      const r = kit.rng(key.length * 0.71 + 0.3);
      for (let i = 0; i < cols; i++)
        for (let j = 0; j < rows; j++) {
          c.fillStyle = base;
          c.fillRect((i * w) / cols, (j * h) / rows, w / cols, h / rows);
          const t = (r() - 0.5) * v;
          c.fillStyle = t > 0 ? `rgba(255,255,255,${t})` : `rgba(0,0,0,${-t})`;
          c.fillRect((i * w) / cols, (j * h) / rows, w / cols, h / rows);
        }
      c.fillStyle = joint;
      for (let i = 0; i <= cols; i++) c.fillRect((i * w) / cols - 1, 0, 2, h);
      for (let j = 0; j <= rows; j++) c.fillRect(0, (j * h) / rows - 1, w, 2);
    });
  const glassM = (key, tint = '#33434e') =>
    kit.paintedMaterial(
      key,
      128,
      256,
      (c, w, h) => {
        for (let s = 0; s < 2; s++) {
          const y0 = (s * h) / 2,
            sh = h / 2;
          const g = c.createLinearGradient(0, y0, 0, y0 + sh);
          g.addColorStop(0, '#9aa6ac');
          g.addColorStop(0.12, tint);
          g.addColorStop(1, '#40535f');
          c.fillStyle = g;
          c.fillRect(0, y0, w, sh);
        }
      },
      { roughness: 0.15, metalness: 0.35 },
    );

  const walls = (b, m, ring, z0, z1, o = {}) =>
    kit.walls(b, m, [[ring]], z0, z1, { bay: 3.6, storey: 3.2, ...o });

  // Flat roof inside a parapet.
  function parapetRoof(b, ring, z, { h = 1.0, wall, roof, coping, t = 0.3 } = {}) {
    const inner = safeOffset(ring, -t) || ring;
    walls(b, wall, ring, z, z + h);
    walls(b, wall, rev(inner), z, z + h);
    kit.cap(b, coping || wall, [[kit.offsetRing(ring, 0.05), rev(inner)]], z + h);
    kit.cap(b, roof, [[inner]], z + 0.05);
    return inner;
  }
  // Hipped (flat-topped where the plan is wide) roof following any footprint.
  function hipRoof(b, m, ring, z, rise, inset, { overhang = 0.35, top, soffit } = {}) {
    const o = kit.offsetRing(ring, overhang);
    let i = null,
      d = inset;
    for (let t = 0; t < 7; t++, d *= 0.6) {
      const c = kit.offsetRing(ring, -d);
      if (okOffset(ring, c)) {
        i = c;
        break;
      }
    }
    if (!i) {
      kit.cap(b, m, [[o]], z);
      return { inner: ring, top: z };
    }
    const zr = z + (rise * d) / inset;
    for (let n = 0; n < o.length; n++) {
      const p = o[n],
        q = o[(n + 1) % o.length],
        pi = i[n],
        qi = i[(n + 1) % i.length];
      const L = Math.hypot(q[0] - p[0], q[1] - p[1]) / 3,
        S = Math.hypot(d, zr - z) / 3;
      b.add(
        m,
        [
          [p[0], p[1], z],
          [q[0], q[1], z],
          [qi[0], qi[1], zr],
          [pi[0], pi[1], zr],
        ],
        [
          [0, 0],
          [L, 0],
          [L, S],
          [0, S],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    kit.cap(b, top || m, [[i]], zr);
    kit.cap(b, soffit || m, [[o, rev(ring)]], z, { down: true });
    return { inner: i, top: zr };
  }
  // Rooftop plant: boxes and louvred enclosure inside ring.
  function plant(b, ring, z, { n = 3, mat, lou, size = 0.25, hmax = 3 } = {}) {
    const f = kit.ringFrame(ring);
    const ca = Math.cos(f.angle),
      sa = Math.sin(f.angle);
    for (let k = 0; k < n; k++) {
      const u = (R() - 0.5) * f.length * 0.5,
        v = (R() - 0.5) * f.width * 0.35;
      const w = Math.max(2, f.length * size * (0.5 + R() * 0.5)),
        d = Math.max(2, f.width * size * (0.6 + R() * 0.4));
      kit.box(
        b,
        k % 2 ? mat : lou || mat,
        f.cx + ca * u - sa * v,
        f.cy + sa * u + ca * v,
        z,
        w,
        d,
        1.5 + R() * (hmax - 1.5),
        f.angle,
      );
    }
  }
  // Windows on every long-enough edge of a ring for the given floor levels.
  function windows(b, ring, floors, opts, { minEdge = 3, sill = 0.9 } = {}) {
    const E = edges(ring);
    floors.forEach((z, s) => {
      for (const e of E) {
        if (e.len < minEdge) continue;
        const o = typeof opts === 'function' ? opts(s, e) : opts;
        if (o) kit.windowRow(b, e.a, e.b, z + (o.sillZ ?? sill), o);
      }
    });
  }
  // Recessed ribbon glazing: solid spandrels on the ring, glass set back, mullions.
  function ribbons(
    b,
    ring,
    floors,
    storey,
    {
      spandrel,
      glass,
      mullion,
      sillH = 1.0,
      headH = 0.5,
      recess = 0.25,
      pitch = 1.5,
      minEdge = 2,
      skip,
    } = {},
  ) {
    const inner = safeOffset(ring, -recess) || ring;
    const E = edges(ring),
      EI = edges(inner);
    for (const z of floors) {
      walls(b, spandrel, ring, z, z + sillH);
      walls(b, spandrel, ring, z + storey - headH, z + storey);
      walls(b, glass, inner, z + sillH, z + storey - headH, { bay: 1.5, storey: storey / 2 });
      kit.cap(b, spandrel, [[ring, rev(inner)]], z + sillH);
      kit.cap(b, spandrel, [[ring, rev(inner)]], z + storey - headH, { down: true });
      for (const e of EI) {
        if (e.len < minEdge || (skip && skip(e))) continue;
        const n = Math.max(1, Math.round(e.len / pitch));
        for (let k = 1; k < n; k++)
          ebox(
            b,
            mullion,
            e,
            (k * e.len) / n - 0.05,
            (k * e.len) / n + 0.05,
            0,
            0.12,
            z + sillH,
            z + storey - headH,
          );
      }
    }
    return E;
  }
  // Triangular gable on edge e rising from z (in wall material, stone coping strip).
  function gable(b, wall, cope, e, s0, s1, z, rise, d = 0) {
    const p = at(e, s0, d),
      q = at(e, s1, d),
      m = at(e, (s0 + s1) / 2, d);
    const pi = at(e, s0, d - 0.5),
      qi = at(e, s1, d - 0.5),
      mi = at(e, (s0 + s1) / 2, d - 0.5);
    b.add(
      wall,
      [
        [p[0], p[1], z],
        [q[0], q[1], z],
        [m[0], m[1], z + rise],
      ],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
    );
    b.add(
      wall,
      [
        [qi[0], qi[1], z],
        [pi[0], pi[1], z],
        [mi[0], mi[1], z + rise],
      ],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
    );
    const L = Math.hypot((s1 - s0) / 2, rise),
      a = Math.atan2(rise, (s1 - s0) / 2);
    for (const [sa, sg] of [
      [s0, 1],
      [s1, -1],
    ]) {
      const g = new THREE.BoxGeometry(L + 0.3, 0.7, 0.25);
      const c = at(e, sa + (sg * (s1 - s0)) / 4, d - 0.25);
      const mtx = new THREE.Matrix4()
        .makeRotationZ(e.ang)
        .multiply(new THREE.Matrix4().makeRotationY(-sg * a));
      mtx.setPosition(c[0], c[1], z + rise / 2 + 0.12);
      b.addGeometry(cope, g, mtx);
      g.dispose();
    }
  }
  function chimney(b, m, cap, x, y, z, h, ang, w = 1.4, d = 0.8) {
    kit.box(b, m, x, y, z, w, d, h, ang);
    kit.box(b, cap, x, y, z + h, w + 0.25, d + 0.25, 0.25, ang);
    for (const t of [-0.3, 0.3])
      kit.box(
        b,
        kit.mat('#8a5a40'),
        x + Math.cos(ang) * t * w,
        y + Math.sin(ang) * t * w,
        z + h + 0.25,
        0.25,
        0.25,
        0.5,
        ang,
      );
  }
  // Entrance: recessed door with frame and canopy, centred at s on edge e.
  function entrance(b, e, s, { w = 3, h = 2.8, door, frame, canopy, cd = 2.0, ct = 0.3 } = {}) {
    ebox(b, door, e, s - w / 2, s + w / 2, -0.05, 0.08, 0.1, h);
    ebox(b, frame, e, s - w / 2 - 0.2, s - w / 2, 0, 0.2, 0, h + 0.2);
    ebox(b, frame, e, s + w / 2, s + w / 2 + 0.2, 0, 0.2, 0, h + 0.2);
    ebox(b, frame, e, s - w / 2 - 0.2, s + w / 2 + 0.2, 0, 0.2, h, h + 0.25);
    if (canopy) ebox(b, canopy, e, s - w / 2 - 1, s + w / 2 + 1, 0, cd, h + 0.35, h + 0.35 + ct);
  }

  // Edwardian red-brick ward block: stone plinth and bands, sash windows, cornice, slate hipped roof,
  // chimneys and stone-coped gables on the short ends.
  function historicBlock(b, ring, M, o = {}) {
    const {
      n = 3,
      g = 4.0,
      st = 3.8,
      roofRise = 4.5,
      inset = 5,
      gables = true,
      chim = true,
      winBay = 3.8,
      minEdge = 3.5,
      bars = 1,
      headTop = 'pediment',
      flat = false,
    } = o;
    const eave = g + (n - 1) * st + 0.6;
    walls(b, M.brick, ring, 0, eave);
    kit.cornice(b, M.stone, ring, 0, { height: 0.9, projection: 0.12 });
    for (let k = 1; k < n; k++)
      kit.cornice(b, M.band, ring, g + (k - 1) * st - 0.05, { height: 0.35, projection: 0.06 });
    kit.cornice(b, M.stone, ring, eave - 0.55, { height: 0.55, projection: 0.35, steps: 2 });
    const fl = levels(0, g, st, n);
    windows(
      b,
      ring,
      fl,
      (s, e) => ({
        width: 1.15,
        height: s === 0 ? 2.3 : 2.1,
        bay: winBay,
        margin: 1.0,
        bars,
        sillZ: s === 0 ? 1.1 : 0.85,
        frame: M.frame,
        glass: M.glass,
        sill: M.stone,
        head: s === n - 1 ? headTop : s === 0 ? 'segment' : 'lintel',
      }),
      { minEdge },
    );
    let top = eave;
    if (flat) {
      parapetRoof(b, ring, eave, { h: 0.9, wall: M.brick, roof: M.flat, coping: M.stone });
      return { eave, top: eave + 0.9, fl };
    }
    const hr = hipRoof(b, M.slate, ring, eave, roofRise, inset, {
      overhang: 0.25,
      top: M.flat || M.slate,
      soffit: M.stone,
    });
    top = hr.top;
    const E = edges(ring);
    if (gables)
      for (const e of E)
        if (e.len > 7 && e.len < 22 && R() < 0.75) {
          const w = Math.min(e.len - 1, 9);
          gable(
            b,
            M.brick,
            M.stone,
            e,
            (e.len - w) / 2,
            (e.len + w) / 2,
            eave,
            Math.min(roofRise * 0.9, w * 0.45),
            0.05,
          );
          kit.windowRow(b, at(e, (e.len - 2) / 2, 0.1), at(e, (e.len + 2) / 2, 0.1), eave + 0.4, {
            count: 1,
            width: 1.0,
            height: 1.4,
            head: 'arch',
            frame: M.frame,
            glass: M.glass,
            margin: 0.2,
            bars: 0,
          });
        }
    if (chim) {
      const I = edges(hr.inner);
      for (const e of I)
        if (e.len > 12)
          for (let s = 6; s < e.len - 3; s += 16) {
            const c = at(e, s, 0.6);
            chimney(b, M.brick, M.stone, c[0], c[1], top - 1.2, 2.6, e.ang, 1.6, 0.9);
          }
    }
    return { eave, top, fl, inner: hr.inner };
  }
  // Brick gauge materials for the Edwardian blocks.
  function edwardianMats(key) {
    return {
      brick: brick(key + ':brick', '#9a4a36', { var: 0.16 }),
      band: brick(key + ':band', '#c9a27a', { var: 0.08 }),
      stone: kit.mat('#d8cdb4', { roughness: 0.85 }),
      slate: kit.roof ? kit.roof('slate', 0) : kit.mat('slate'),
      flat: kit.mat('#5a5e62'),
      frame: kit.mat('#f2efe8'),
      glass: kit.mat('#2c3a44', { roughness: 0.15, metalness: 0.3 }),
    };
  }

  // Late-20th-century hospital block: brick/clad spandrels with recessed ribbon glazing, parapet,
  // flat roof with plant.
  function modernBlock(b, ring, o) {
    const {
      n,
      g = 4.2,
      st = 3.6,
      spandrel,
      glass,
      mullion,
      coping,
      roof,
      pitch = 1.5,
      sillH = 1.0,
      headH = 0.6,
      groundGlass = false,
      parapet = 1.1,
      plantN = 3,
      plantMat,
      lou,
      recess = 0.25,
    } = o;
    const fl = levels(0, g, st, n);
    const H = g + (n - 1) * st;
    if (groundGlass) {
      const inner = safeOffset(ring, -0.6) || ring;
      walls(b, glass, inner, 0, g - 0.6, { bay: 1.5, storey: (g - 0.6) / 2 });
      for (const e of edges(inner))
        if (e.len > 2)
          for (let s = 0; s <= e.len; s += 1.8)
            ebox(b, mullion, e, s - 0.05, s + 0.05, 0, 0.12, 0, g - 0.6);
      walls(b, spandrel, ring, g - 0.6, g);
      kit.cap(b, spandrel, [[ring, rev(inner)]], g - 0.6, { down: true });
      ribbons(b, ring, fl.slice(1), st, { spandrel, glass, mullion, pitch, sillH, headH, recess });
    } else {
      walls(b, spandrel, ring, 0, 0.6);
      ribbons(b, ring, [0.6], g - 0.6, {
        spandrel,
        glass,
        mullion,
        pitch,
        sillH: 0.5,
        headH,
        recess,
      });
      ribbons(b, ring, fl.slice(1), st, { spandrel, glass, mullion, pitch, sillH, headH, recess });
    }
    const inner = parapetRoof(b, ring, H, { h: parapet, wall: spandrel, roof, coping });
    if (plantN)
      plant(b, inner, H, {
        n: plantN,
        mat: plantMat || kit.mat('#8f918e'),
        lou: lou || kit.mat('#b4b6b2'),
        size: 0.22,
      });
    return { H, fl };
  }
  const levels = (z0, g, st, n) =>
    Array.from({ length: n }, (_, k) => (k === 0 ? z0 : z0 + g + (k - 1) * st));
  const longest = (ring, f = () => true) =>
    edges(ring)
      .filter(f)
      .sort((p, q) => q.len - p.len)[0];
  return {
    R,
    ccw,
    edges,
    at,
    ebox,
    safeOffset,
    rev,
    quad,
    brick,
    plain,
    panels,
    glassM,
    walls,
    parapetRoof,
    hipRoof,
    plant,
    windows,
    ribbons,
    gable,
    chimney,
    entrance,
    levels,
    longest,
    historicBlock,
    edwardianMats,
    modernBlock,
  };
}
