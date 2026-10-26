// Imperial College Faculty of Medicine, St Mary's campus: the former St Mary's Hospital Medical
// School and Pathological Institute on Norfolk Place / Praed Street, opened by King George V and
// Queen Mary on 12 December 1933 (Cooper). A five-storey courtyard block - modelled as inter-war
// stripped-classical red brick over a Portland-stone ground floor with a stone entrance
// frontispiece to Norfolk Place, stone cornice and parapet.
export default {
  id: 'st_marys_medical_school',
  name: "St Mary's Medical School building (Imperial College)",
  claims: ['ea80ba4f-05f6-48f9-b8b3-e05421e127a6', '993edad6-52bf-4507-b78a-b21b36fe96d5'],
  references: [
    {
      title: "St Mary's Hospital Medical School records - AIM25",
      url: 'https://atom.aim25.com/index.php/st-marys-hospital-medical-school-10',
      used_for: 'school moved from South Wharf Road to Norfolk Place in 1933',
    },
    {
      title:
        "Opening of the new medical school and pathological institute, St Mary's Hospital (1933) - Wellcome Collection",
      url: 'https://content.www.wellcomecollection.org/works/e72nwjw2',
      used_for: 'opened by the King and Queen on 12 December 1933',
    },
    {
      title: 'The architecture of labour - Twentieth Century Society',
      url: 'https://c20society.org.uk/2013/07/22/the-architecture-of-labour',
      used_for: "Cooper did the medical school at St Mary's in 1933",
    },
    {
      title: "St Mary's Hospital, London - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Mary%27s_Hospital,_London',
      used_for: 'hospital history and buildings on the Praed Street / South Wharf Road site',
    },
    {
      title: "St Mary's Hospital site map - Imperial College",
      url: 'https://t4awstest.cc.ic.ac.uk/media/imperial-college/visit/public/stmarysmap.pdf',
      used_for: 'building names and positions on the campus',
    },
  ],
  notes:
    'Two duplicate Overture footprints (one with the courtyard hole) are claimed; the holed one is ' +
    'modelled. Five storeys from the data (17.2 m): 4.4 m ground + 4 x 3.3 m, parapet to ~18.6 m. ' +
    'Materials (red brick, Portland stone base and dressings, multi-pane steel windows), the entrance ' +
    'frontispiece on Norfolk Place and the attic set-back are assumptions in the Cooper idiom; the sources ' +
    'found do not describe the elevations.',
  build({ THREE, kit, byId, buildings }) {
    const L = makeLib(THREE, kit, 0.7753);
    const g = new THREE.Group();
    const b = new kit.MeshBatch();
    const rec = buildings.find((q) => q.polys[0].length > 1) || buildings[0];
    const ring = L.ccw(rec.polys[0][0]);
    const holes = rec.polys[0].slice(1).map((h) => {
      const r = L.ccw(h);
      return r.reverse();
    });
    const brick = L.brick('smms:brick', '#9b4f3a', { var: 0.14 });
    const stoneP = L.panels('smms:stone', '#ddd5c2', {
      cols: 6,
      rows: 6,
      joint: 'rgba(90,85,70,0.3)',
      v: 0.05,
    });
    const stone = kit.mat('#ddd5c2', { roughness: 0.85 });
    const frame = kit.mat('#3d4244');
    const glass = kit.mat('#2c3a44', { roughness: 0.15, metalness: 0.3 });
    const G = 4.4,
      ST = 3.3,
      H = G + 4 * ST;
    const fl = L.levels(0, G, ST, 5);
    for (const r of [ring, ...holes]) {
      L.walls(b, stoneP, r, 0, G);
      L.walls(b, brick, r, G, H);
      kit.cornice(b, stone, r, G - 0.25, { height: 0.45, projection: 0.15 });
      L.windows(
        b,
        r,
        fl,
        (s) => ({
          width: 1.5,
          height: s === 0 ? 2.5 : 2.0,
          bay: 3.3,
          margin: 0.8,
          head: s === 0 ? 'arch' : 'lintel',
          frame,
          glass,
          sill: stone,
          bars: 1,
          sillZ: s === 0 ? 0.9 : 0.85,
          surround: s === 4 ? 0.12 : 0,
          surroundMat: stone,
        }),
        { minEdge: 3 },
      );
    }
    kit.cornice(b, stone, ring, H - 0.6, { height: 0.6, projection: 0.45, steps: 2 });
    // parapet + roof with courtyard
    const inner = L.safeOffset(ring, -0.3) || ring;
    L.walls(b, brick, ring, H, H + 1.0);
    L.walls(b, brick, L.rev(inner), H, H + 1.0);
    kit.cap(b, stone, [[kit.offsetRing(ring, 0.05), L.rev(inner)]], H + 1.0);
    kit.cap(b, kit.mat('#666866'), [[inner, ...holes]], H + 0.05);
    L.plant(b, inner, H, { n: 3, mat: kit.mat('#8f918e'), lou: kit.mat('#b4b6b2'), size: 0.12 });
    // stone frontispiece and entrance on Norfolk Place (south-west face)
    const e = L.edges(ring)
      .filter((q) => -q.nx * 0.74 - q.ny * 0.67 > 0.9)
      .sort((p, q) => q.len - p.len)[0];
    if (e) {
      const s = e.len / 2,
        w = 12;
      L.ebox(b, stone, e, s - w / 2, s + w / 2, 0, 0.6, 0, H + 1.6);
      for (let k = 0; k < 4; k++)
        L.ebox(
          b,
          stone,
          e,
          s - w / 2 + 1 + k * ((w - 2) / 3) - 0.35,
          s - w / 2 + 1 + k * ((w - 2) / 3) + 0.35,
          0.6,
          0.95,
          G,
          H - 0.6,
        );
      kit.windowRow(b, L.at(e, s - w / 2 + 1, 0.62), L.at(e, s + w / 2 - 1, 0.62), G + 0.9, {
        count: 3,
        width: 1.6,
        height: 3 * ST - 1.4,
        head: 'none',
        frame,
        glass,
        sill: stone,
        bars: 3,
        margin: 0.2,
      });
      L.ebox(b, kit.mat('#2b2622'), e, s - 1.8, s + 1.8, 0.55, 0.7, 0.4, 3.6);
      L.ebox(b, stone, e, s - 3.2, s + 3.2, 0.6, 1.2, 3.6, 4.3);
      for (let k = 0; k < 3; k++)
        L.ebox(
          b,
          stone,
          e,
          s - 3 + k * 0.2,
          s + 3 - k * 0.2,
          0.6,
          2.2 - k * 0.4,
          k * 0.14,
          (k + 1) * 0.14,
        );
      const sign = kit.paintedMaterial('smms:sign', 512, 64, (c, ww, h) => {
        c.fillStyle = '#ddd5c2';
        c.fillRect(0, 0, ww, h);
        c.fillStyle = '#3b3a36';
        c.font = 'bold 21px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText("ST MARY'S HOSPITAL MEDICAL SCHOOL", ww / 2, h / 2 + 2);
      });
      L.quad(
        b,
        sign,
        L.at(e, s - w / 2 + 0.3, 0.62),
        L.at(e, s + w / 2 - 0.3, 0.62),
        H - 0.2,
        H + 0.9,
      );
    }
    g.add(b.toGroup('st_marys_medical_school'));
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
