// Nos 10-15 Prince's Gardens, north side: the surviving part (with Nos 8-9, the Early
// Years Education Centre) of the 1859-61 stucco terrace that once lined the whole north
// side of the square. Five storeys plus basement, three windows per house, Doric
// porches, a balustrade at first-floor level and cast-iron area railings (Grade II).
// No. 15 abuts Weeks Hall to the east. Now Imperial College property.
// ---- shared helpers (inlined: modules have no imports) -------------------------------
// Edge records, offsets along walls, stucco terrace / brick mansion / modern block
// generators. Edges of a CCW ring have their outward normal on the right of a -> b.
function makeTools({ THREE, kit }, batch) {
  const T = {};
  T.ring = (b, k = 0) => {
    const r = b.polys[k][0].slice();
    if (kit.ringArea(r) < 0) r.reverse();
    return r;
  };
  T.edges = (r) =>
    r.map((a, k) => {
      const b = r[(k + 1) % r.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        k,
        a,
        b,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
      };
    });
  T.at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  T.ebox = (m, e, s0, s1, d0, d1, z0, z1, color) => {
    const c = T.at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(
      batch,
      m,
      c[0],
      c[1],
      z0,
      Math.max(0.01, s1 - s0),
      Math.max(0.01, d1 - d0),
      z1 - z0,
      e.ang,
      color,
    );
  };
  T.faces = (e, dir, thr = 0.7) => e.nx * dir[0] + e.ny * dir[1] > thr;
  T.dir = (deg) => [Math.cos((deg * Math.PI) / 180), Math.sin((deg * Math.PI) / 180)];
  // Wall quad on edge e (optionally offset d), UVs as kit.walls (4 bays x 2 storeys per tile).
  T.wall = (
    m,
    e,
    z0,
    z1,
    { d = 0, bay = 3.6, storey = 3.2, uvBase = 0, s0 = 0, s1 = e.len } = {},
  ) => {
    const p = T.at(e, s0, d),
      q = T.at(e, s1, d);
    const n = Math.round((s1 - s0) / bay);
    const u1 = n >= 1 ? n / 4 : 0.03;
    const v0 = (z0 - uvBase) / (2 * storey),
      v1 = (z1 - uvBase) / (2 * storey);
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [0, v0],
      [u1, v0],
      [u1, v1],
      [0, v1],
    );
  };
  // Ring with each edge k moved inwards by ins[k] (miter intersection of offset lines).
  T.insetVar = (ring, ins) => {
    const n = ring.length,
      E = T.edges(ring),
      out = [];
    for (let k = 0; k < n; k++) {
      const e1 = E[(k - 1 + n) % n],
        e2 = E[k];
      const d1 = ins[(k - 1 + n) % n],
        d2 = ins[k];
      const p1 = [e1.a[0] - e1.nx * d1, e1.a[1] - e1.ny * d1],
        p2 = [e2.a[0] - e2.nx * d2, e2.a[1] - e2.ny * d2];
      const den = e1.dx * e2.dy - e1.dy * e2.dx;
      if (Math.abs(den) < 0.15) {
        const d = Math.max(d1, d2);
        out.push([ring[k][0] - ((e1.nx + e2.nx) / 2) * d, ring[k][1] - ((e1.ny + e2.ny) / 2) * d]);
        continue;
      }
      const t = ((p2[0] - p1[0]) * e2.dy - (p2[1] - p1[1]) * e2.dx) / den;
      out.push([p1[0] + e1.dx * t, p1[1] + e1.dy * t]);
    }
    return out;
  };
  // Mansard whose slope depth differs per edge (0 = vertical party wall).
  T.mansardVar = (ring, z0, h, ins, roofM, topM, sideM) => {
    const inner = T.insetVar(ring, ins);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inner[(k + 1) % ring.length],
        d = inner[k];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      batch.quad(
        ins[k] > 0.05 ? roofM : (sideM ?? roofM),
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [c[0], c[1], z0 + h],
        [d[0], d[1], z0 + h],
        [0, 0],
        [len / 3, 0],
        [len / 3, h / 3],
        [0, h / 3],
      );
    }
    kit.cap(batch, topM ?? roofM, [[inner]], z0 + h);
    return inner;
  };
  // Sloped roof band from ring at z0 up to the ring inset by `inset` at z0 + h, then a flat top.
  T.mansard = (ring, z0, h, inset, roofM, topM, holes = []) => {
    const inner = kit.offsetRing(ring, -inset);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inner[(k + 1) % ring.length],
        d = inner[k];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      batch.quad(
        roofM,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [c[0], c[1], z0 + h],
        [d[0], d[1], z0 + h],
        [0, 0],
        [len / 3, 0],
        [len / 3, h / 3],
        [0, h / 3],
      );
    }
    kit.cap(batch, topM ?? roofM, [[inner, ...holes.map((r) => kit.offsetRing(r, inset))]], z0 + h);
    for (const r of holes) {
      const hi = kit.offsetRing(r, inset);
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length],
          c = hi[(k + 1) % r.length],
          d = hi[k];
        batch.quad(
          roofM,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z0 + h],
          [d[0], d[1], z0 + h],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    return inner;
  };
  // Parapet ring with a recessed flat roof.
  T.parapet = (ring, z, h, wallM, roofM, t = 0.3) => {
    const inner = kit.offsetRing(ring, -t);
    kit.walls(batch, wallM, [[ring]], z, z + h, { bay: 1e6 });
    kit.walls(batch, wallM, [[inner.slice().reverse()]], z, z + h, { bay: 1e6 });
    kit.cap(batch, wallM, [[ring, inner.slice().reverse()]], z + h);
    kit.cap(batch, roofM, [[inner]], z + 0.05);
  };
  T.railing = (e, s0, s1, d, z0, h, m, sp = 0.2) => {
    if (s1 - s0 < 0.3) return;
    T.ebox(m, e, s0, s1, d - 0.03, d + 0.03, z0 + h - 0.06, z0 + h);
    T.ebox(m, e, s0, s1, d - 0.03, d + 0.03, z0 + 0.12, z0 + 0.17);
    const n = Math.max(1, Math.round((s1 - s0) / sp));
    for (let k = 0; k <= n; k++) {
      const s = s0 + ((s1 - s0) * k) / n;
      T.ebox(m, e, s - 0.012, s + 0.012, d - 0.012, d + 0.012, z0, z0 + h + 0.08);
    }
  };
  T.cyl = (m, x, y, z0, r, h, seg = 8, r2) => {
    const g = new THREE.CylinderGeometry(r2 ?? r, r, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
    g.dispose();
  };
  T.chimney = (x, y, z, w, d, h, ang, m, potM, pots = 4) => {
    kit.box(batch, m, x, y, z, w, d, h, ang);
    kit.box(batch, m, x, y, z + h, w + 0.16, d + 0.16, 0.18, ang);
    const c = Math.cos(ang),
      s = Math.sin(ang);
    for (let k = 0; k < pots; k++) {
      const u = (k - (pots - 1) / 2) * (w / pots);
      T.cyl(potM, x + c * u, y + s * u, z + h + 0.18, 0.13, 0.55, 6, 0.1);
    }
  };
  // Doric porch on edge e centred at s, projecting d, columns of height ch.
  T.porch = (e, s, w, d, ch, m, opt = {}) => {
    const { balustrade = true, steps = 3, stepM = m, z0 = 0.6 } = opt;
    for (let k = 0; k < steps; k++)
      T.ebox(
        stepM,
        e,
        s - w / 2 - 0.2 + k * 0.05,
        s + w / 2 + 0.2 - k * 0.05,
        0,
        d + 0.9 - k * 0.3,
        (k * z0) / steps,
        ((k + 1) * z0) / steps,
      );
    const a = T.at(e, s - w / 2 + 0.25, d),
      b = T.at(e, s + w / 2 - 0.25, d);
    kit.colonnade(batch, m, a, b, z0, ch, {
      count: 2,
      radius: 0.2,
      capital: 'doric',
      segments: 10,
    });
    // pilasters against the wall
    T.ebox(m, e, s - w / 2, s - w / 2 + 0.4, 0, 0.12, z0, z0 + ch);
    T.ebox(m, e, s + w / 2 - 0.4, s + w / 2, 0, 0.12, z0, z0 + ch);
    const zt = z0 + ch;
    T.ebox(m, e, s - w / 2 - 0.15, s + w / 2 + 0.15, 0, d + 0.4, zt, zt + 0.55);
    T.ebox(m, e, s - w / 2 - 0.25, s + w / 2 + 0.25, 0, d + 0.5, zt + 0.55, zt + 0.7);
    if (balustrade)
      kit.balustrade(
        batch,
        m,
        [T.at(e, s - w / 2 - 0.1, d + 0.3), T.at(e, s + w / 2 + 0.1, d + 0.3)],
        zt + 0.7,
        { height: 0.8, spacing: 0.3 },
      );
    return zt + 0.7;
  };
  // Painted sign board on edge e from s0 to s1, z0..z1, standing d proud of the wall.
  T.sign = (
    key,
    e,
    s0,
    s1,
    z0,
    z1,
    text,
    {
      bg = '#ffffff',
      fg = '#222222',
      d = 0.08,
      font = 'bold 40px sans-serif',
      W = 512,
      H = 64,
    } = {},
  ) => {
    const m = kit.paintedMaterial(
      key,
      W,
      H,
      (c, w, h) => {
        c.fillStyle = bg;
        c.fillRect(0, 0, w, h);
        c.fillStyle = fg;
        c.font = font;
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(text, w / 2, h / 2 + 2);
      },
      { roughness: 0.6 },
    );
    const p = T.at(e, s0, d),
      q = T.at(e, s1, d);
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
    );
  };
  T.door = (e, s, w, h, z0, frameM, doorM) => {
    T.ebox(doorM, e, s - w / 2, s + w / 2, -0.1, 0.04, z0, z0 + h);
    T.ebox(frameM, e, s - w / 2 - 0.15, s - w / 2, 0, 0.1, z0, z0 + h + 0.15);
    T.ebox(frameM, e, s + w / 2, s + w / 2 + 0.15, 0, 0.1, z0, z0 + h + 0.15);
    T.ebox(frameM, e, s - w / 2 - 0.15, s + w / 2 + 0.15, 0, 0.12, z0 + h, z0 + h + 0.2);
    T.ebox(
      kit.mat('dark_glass'),
      e,
      s - w / 2 + 0.05,
      s + w / 2 - 0.05,
      0,
      0.06,
      z0 + h + 0.2,
      z0 + h + 0.8,
    );
  };
  // Dormers on a mansard face of edge e (z0 = foot of slope, inset = slope depth).
  T.dormers = (e, s0, s1, n, z0, h, inset, m, roofM) => {
    for (let k = 0; k < n; k++) {
      const s = s0 + ((s1 - s0) * (k + 0.5)) / n;
      T.ebox(m, e, s - 0.65, s + 0.65, -inset, -0.35, z0, z0 + h * 0.72);
      T.ebox(kit.mat('dark_glass'), e, s - 0.42, s + 0.42, -0.35, -0.32, z0 + 0.3, z0 + h * 0.66);
      T.ebox(m, e, s - 0.48, s + 0.48, -0.36, -0.28, z0 + 0.22, z0 + 0.3);
      T.ebox(roofM, e, s - 0.78, s + 0.78, -inset - 0.1, -0.25, z0 + h * 0.72, z0 + h * 0.8);
    }
  };
  // ---------------------------------------------------------------------------------
  // Victorian stucco terrace (Freake houses, Queen's Gate, Prince's Gardens): stucco
  // street fronts with rusticated ground floor, Doric porches, first-floor balustraded
  // balcony, sash windows diminishing upwards, main cornice, attic; stock-brick rears.
  // ---------------------------------------------------------------------------------
  T.stuccoTerrace = (ring, o) => {
    const {
      front, // outward direction(s) of the street fronts
      thr = 0.7,
      houseW = 7.5,
      groundH = 4.2,
      upper = [3.9, 3.4, 3.0], // storey heights above the ground floor (below the cornice)
      attic = 'mansard', // mansard | storey | none
      atticH = 3.0,
      atticStorey = 2.9,
      color = '#efe9dc',
      porch = true,
      porchW = 2.6,
      porchD = 1.9,
      balcony = true,
      win = 3,
      chimneys = true,
      area = true,
      mirror = true,
      bayDoorAt = 'left',
      rear = 'london_stock',
      skipPorch = [],
      porchCols = 'doric',
      quoins = false,
      piano = 'pediment',
    } = o;
    const fronts = Array.isArray(front[0]) ? front : [front];
    const stucco = kit.mat(color, { roughness: 0.72 });
    const stuccoDk = kit.mat(new THREE.Color(color).multiplyScalar(0.9).getStyle(), {
      roughness: 0.75,
    });
    const rearM = kit.facade(rear, 1);
    const black = kit.mat('#1d1f21', { roughness: 0.5, metalness: 0.3 });
    const glass = kit.mat('#26323a', { roughness: 0.15, metalness: 0.3 });
    const frameM = kit.mat('#f6f4ee', { roughness: 0.6 });
    const slate = kit.roof ? kit.roof('slate') : kit.mat('slate');
    const lead = kit.mat('#5d6366', { roughness: 0.7, metalness: 0.2 });
    const doorM = kit.mat('#1e2326', { roughness: 0.5 });
    const potM = kit.mat('#a4593c');
    const E = T.edges(ring);
    const isF = (e) => e.len > 3 && fronts.some((f) => T.faces(e, f, thr));
    const zc = groundH + upper.reduce((a, b) => a + b, 0); // main cornice
    // walls
    const isRet = (e) =>
      !isF(e) && e.len < 4.5 && !fronts.some((f) => e.nx * f[0] + e.ny * f[1] < -0.7);
    for (const e of E) {
      if (isF(e) || isRet(e)) T.wall(stucco, e, 0, zc + 0.9);
      else T.wall(rearM, e, 0, zc + 0.9, { bay: 3.4, storey: 3.2 });
    }
    // basement area lightwell look: dark strip at the foot
    let houseNo = 0;
    const longestF = E.filter(isF).sort((p, q) => q.len - p.len)[0];
    for (const e of E) {
      if (!isF(e)) continue;
      // rusticated ground floor + plinth + first-floor string course
      for (let z = 0.9; z < groundH - 0.3; z += 0.5)
        T.ebox(stuccoDk, e, 0, e.len, 0, 0.05, z, z + 0.06);
      T.ebox(stuccoDk, e, 0, e.len, 0, 0.12, 0, 0.6);
      T.ebox(stucco, e, 0, e.len, 0, 0.18, groundH - 0.3, groundH);
      let z = groundH;
      for (let k = 0; k < upper.length - 1; k++) {
        z += upper[k];
        T.ebox(stucco, e, 0, e.len, 0, 0.1, z - 0.15, z);
      }
      if (quoins)
        for (const s of [0, e.len - 0.6])
          for (let qz = groundH; qz < zc - 0.3; qz += 0.6)
            T.ebox(stuccoDk, e, s, s + 0.6, 0, 0.06, qz, qz + 0.5);
      const nh = Math.max(1, Math.round(e.len / houseW));
      const hw = e.len / nh;
      const winE = Math.max(1, Math.min(win, Math.floor((hw - 0.6) / 2.3)));
      if (hw < 6 && e !== longestF) {
        // narrow front (bay or set-back return): windows only
        let zz = groundH;
        kit.windowRow(batch, e.a, e.b, 1.2, {
          count: winE,
          width: 1.2,
          height: groundH - 2.0,
          margin: 0.4,
          glass,
          frame: frameM,
          head: 'none',
          bars: 1,
          depth: 0.1,
        });
        upper.forEach((sh, k) => {
          kit.windowRow(batch, e.a, e.b, zz + (k === 0 ? 0.25 : 0.75), {
            count: winE,
            width: 1.2,
            height: Math.max(1.2, sh - (k === 0 ? 1.1 : 1.2)),
            margin: 0.45,
            glass,
            frame: frameM,
            sill: stucco,
            head: k === 0 ? piano : 'none',
            surround: 0.12,
            surroundMat: stucco,
            bars: 1,
            depth: 0.12,
          });
          zz += sh;
        });
        if (area) T.railing(e, 0, e.len, 1.6, 0, 1.0, black);
        continue;
      }
      for (let h = 0; h < nh; h++, houseNo++) {
        const s0 = h * hw,
          s1 = s0 + hw;
        const left = mirror ? houseNo % 2 === 0 : bayDoorAt === 'left';
        const doorS = left ? s0 + Math.min(1.7, hw * 0.25) : s1 - Math.min(1.7, hw * 0.25);
        const hasPorch = porch && hw > 4.5 && !skipPorch.includes(houseNo);
        // ground floor: door + windows on the other side
        T.door(e, doorS, 1.3, 2.6, 0.6, frameM, doorM);
        if (hasPorch)
          T.porch(e, doorS, porchW, porchD, groundH - 1.0, stucco, { stepM: kit.mat('#d8d3c8') });
        const gw = left ? [s0 + hw * 0.42, s1] : [s0, s1 - hw * 0.42];
        const nW = Math.max(1, winE - 1);
        kit.windowRow(batch, T.at(e, gw[0]), T.at(e, gw[1]), 1.2, {
          count: nW,
          width: 1.25,
          height: groundH - 2.0,
          margin: 0.4,
          glass,
          frame: frameM,
          head: 'none',
          bars: 1,
          depth: 0.1,
        });
        // upper storeys
        let zz = groundH;
        upper.forEach((sh, k) => {
          const piano_ = k === 0;
          const hgt = Math.max(1.2, sh - (piano_ ? 1.1 : 1.2));
          kit.windowRow(batch, T.at(e, s0), T.at(e, s1), zz + (piano_ ? 0.25 : 0.75), {
            count: winE,
            width: 1.2,
            height: hgt,
            margin: 0.55,
            glass,
            frame: frameM,
            sill: stucco,
            head: piano_ ? piano : k === 1 ? 'lintel' : 'none',
            surround: k < 2 ? 0.14 : 0.1,
            surroundMat: stucco,
            bars: 1,
            depth: 0.12,
          });
          zz += sh;
        });
        // area railings, interrupted at the porch steps
        if (area) {
          if (hasPorch) {
            T.railing(e, s0, doorS - porchW / 2 - 0.3, 1.6, 0, 1.0, black);
            T.railing(e, doorS + porchW / 2 + 0.3, s1, 1.6, 0, 1.0, black);
            T.railing(e, doorS - porchW / 2 - 0.3, doorS - porchW / 2 - 0.29, 1.6, 0, 1.0, black);
          } else T.railing(e, s0, s1, 1.6, 0, 1.0, black);
        }
        // chimney stacks on the party walls
        if (chimneys && h > 0) {
          const c = T.at(e, s0, -4.5);
          T.chimney(
            c[0],
            c[1],
            zc + 0.9 + (attic === 'none' ? 0 : attic === 'mansard' ? atticH : atticStorey) - 0.6,
            2.2,
            0.8,
            1.9,
            e.ang + Math.PI / 2,
            kit.mat('#b29c76'),
            potM,
            5,
          );
        }
        if (attic === 'mansard')
          T.dormers(e, s0, s1, Math.min(3, winE), zc + 0.9, atticH, 1.4, lead, slate);
        if (attic === 'storey')
          kit.windowRow(batch, T.at(e, s0), T.at(e, s1), zc + 1.6, {
            count: winE,
            width: 1.0,
            height: 1.3,
            margin: 0.6,
            glass,
            frame: frameM,
            head: 'none',
            bars: 1,
            depth: 0.1,
          });
      }
      if (balcony) {
        T.ebox(stucco, e, 0.1, e.len - 0.1, 0, 0.75, groundH - 0.1, groundH + 0.1);
        kit.balustrade(
          batch,
          stucco,
          [T.at(e, 0.2, 0.6), T.at(e, e.len - 0.2, 0.6)],
          groundH + 0.1,
          { height: 0.85, spacing: 0.32 },
        );
      }
    }
    // main cornice, blocking course, attic and roof
    kit.cornice(batch, stucco, ring, zc, { height: 0.55, projection: 0.45, steps: 2 });
    kit.walls(batch, stucco, [[ring]], zc + 0.55, zc + 0.9, { bay: 1e6 });
    const isRear = (e) => fronts.some((f) => e.nx * f[0] + e.ny * f[1] < -0.7);
    if (attic === 'mansard')
      T.mansardVar(
        ring,
        zc + 0.9,
        atticH,
        E.map((e) => (isF(e) || isRear(e) ? 1.4 : 0)),
        slate,
        lead,
        kit.mat('#b29c76'),
      );
    // party-wall chimney stacks on the side walls
    if (chimneys)
      for (const e of E) {
        if (isF(e) || isRear(e) || e.len < 6) continue;
        const c = T.at(e, e.len / 2, -0.45);
        T.chimney(
          c[0],
          c[1],
          zc + 0.9 + (attic === 'none' ? 0 : attic === 'mansard' ? atticH : atticStorey) - 0.4,
          Math.min(3.2, e.len * 0.3),
          0.8,
          1.6,
          e.ang,
          kit.mat('#b29c76'),
          potM,
          6,
        );
      }
    else if (attic === 'storey') {
      const ar = kit.offsetRing(ring, -0.15);
      kit.walls(batch, stucco, [[ar]], zc + 0.9, zc + 0.9 + atticStorey, { bay: 1e6 });
      kit.cornice(batch, stucco, ar, zc + 0.6 + atticStorey, { height: 0.3, projection: 0.25 });
      kit.cap(batch, lead, [[ar]], zc + 0.9 + atticStorey);
    } else kit.cap(batch, lead, [[ring]], zc + 0.85);
    // rear chimney stacks/plant
    return {
      zc,
      top: zc + 0.9 + (attic === 'mansard' ? atticH : attic === 'storey' ? atticStorey : 0),
    };
  };

  // ---------------------------------------------------------------------------------
  // Red-brick mansion block / Queen Anne house: brick fronts with stone bands and
  // dressings, stone ground floor, sash windows, gables, slate/tile roof with dormers.
  // ---------------------------------------------------------------------------------
  T.brickBlock = (ring, o) => {
    const {
      front,
      thr = 0.6,
      storeys = 5,
      storeyH = 3.3,
      groundH = 3.8,
      brick = '#9a4b37',
      stone = '#e3d9c4',
      stoneGround = true,
      bay = 3.0,
      winW = 1.25,
      winHf = 0.6,
      roof = 'mansard',
      roofH = 3.2,
      roofM: roofMIn,
      gables = [], // [{edge, s, w, h}] stepped / shaped gables standing on the eaves
      gableStyle = 'dutch',
      dormers = true,
      rear = 'red_brick',
      heads = 'lintel',
      chimneys = [],
      bands = 'all',
      holes = [],
      roofInset,
      windows = true,
    } = o;
    const fronts = front ? (Array.isArray(front[0]) ? front : [front]) : null;
    const brickM = kit.mat(brick, { roughness: 0.9 });
    const stoneM = kit.mat(stone, { roughness: 0.8 });
    const rearM = kit.facade(rear, 1);
    const glass = kit.mat('#27323a', { roughness: 0.15, metalness: 0.3 });
    const frameM = kit.mat('#f3f1ea', { roughness: 0.6 });
    const roofM = roofMIn ?? (kit.roof ? kit.roof('slate') : kit.mat('slate'));
    const lead = kit.mat('#7b8387', { roughness: 0.6, metalness: 0.3 });
    const E = T.edges(ring);
    const isF = (e) => e.len > 2.5 && (!fronts || fronts.some((f) => T.faces(e, f, thr)));
    const zt = groundH + (storeys - 1) * storeyH;
    for (const e of E) {
      if (isF(e)) {
        if (stoneGround) {
          T.wall(stoneM, e, 0, groundH);
          T.wall(brickM, e, groundH, zt + 0.8);
        } else T.wall(brickM, e, 0, zt + 0.8);
        T.ebox(stoneM, e, 0, e.len, 0, 0.12, 0, 0.5);
        let z = groundH;
        for (let s = 1; s < storeys; s++) {
          if (bands === 'all' || s === 1) T.ebox(stoneM, e, 0, e.len, 0, 0.1, z - 0.2, z + 0.05);
          z += storeyH;
        }
        for (let s = 0; s < storeys && windows; s++) {
          const z0 = s === 0 ? 0.9 : groundH + (s - 1) * storeyH + 0.8;
          const sh = s === 0 ? groundH : storeyH;
          kit.windowRow(batch, e.a, e.b, z0, {
            bay,
            width: winW,
            height: sh * winHf + (s === 0 ? 0.2 : 0),
            margin: 0.6,
            glass,
            frame: frameM,
            sill: stoneM,
            head: s === 0 ? 'lintel' : heads,
            surround: 0.12,
            surroundMat: stoneM,
            bars: 1,
            depth: 0.12,
          });
        }
      } else T.wall(rearM, e, 0, zt + 0.8, { bay: 3.4, storey: 3.2 });
    }
    for (const r of holes)
      T.wall && kit.walls(batch, rearM, [[r]], 0, zt + 0.8, { bay: 3.4, storey: 3.2 });
    kit.cornice(batch, stoneM, ring, zt, { height: 0.45, projection: 0.35, steps: 2 });
    kit.walls(batch, brickM, [[ring]], zt + 0.45, zt + 0.8, { bay: 1e6 });
    kit.cap(batch, stoneM, [[ring, ...holes]], zt + 0.8);
    let top = zt + 0.8;
    const ins = roofInset ?? Math.min(2.2, roofH * 0.7);
    if (roof === 'mansard') {
      T.mansard(ring, zt + 0.8, roofH, ins, roofM, lead, holes);
      top += roofH;
      if (dormers)
        for (const e of E)
          if (isF(e) && e.len > 4)
            T.dormers(
              e,
              0.8,
              e.len - 0.8,
              Math.max(1, Math.round(e.len / (bay * 1.6))),
              zt + 0.8,
              roofH,
              ins,
              brickM,
              roofM,
            );
    } else if (roof === 'pitched') {
      const f = kit.ringFrame(ring);
      kit.pitchedRoof(batch, roofM, brickM, ring, f.angle, zt + 0.8, roofH, 'hipped', {
        overhang: 0.3,
      });
      top += roofH;
    }
    // shaped gables rising above the eaves
    for (const g of gables) {
      const e = E[g.edge];
      if (!e) continue;
      const sh = new THREE.Shape();
      const w = g.w,
        h = g.h;
      if (gableStyle === 'dutch') {
        sh.moveTo(-w / 2, 0);
        sh.lineTo(w / 2, 0);
        sh.lineTo(w / 2, h * 0.3);
        sh.quadraticCurveTo(w * 0.28, h * 0.35, w * 0.25, h * 0.6);
        sh.lineTo(w * 0.18, h * 0.6);
        sh.lineTo(w * 0.18, h * 0.88);
        sh.quadraticCurveTo(0, h * 1.05, -w * 0.18, h * 0.88);
        sh.lineTo(-w * 0.18, h * 0.6);
        sh.lineTo(-w * 0.25, h * 0.6);
        sh.quadraticCurveTo(-w * 0.28, h * 0.35, -w / 2, h * 0.3);
      } else {
        sh.moveTo(-w / 2, 0);
        sh.lineTo(w / 2, 0);
        sh.lineTo(0, h);
      }
      sh.closePath();
      const geo = new THREE.ExtrudeGeometry(sh, {
        depth: 0.6,
        bevelEnabled: false,
        curveSegments: 4,
      });
      geo.rotateX(Math.PI / 2); // shape y -> z, extrude along -y
      const c = T.at(e, g.s, 0.1);
      const m = new THREE.Matrix4().makeRotationZ(e.ang).setPosition(c[0], c[1], zt + 0.8);
      batch.addGeometry(brickM, geo, m);
      geo.dispose();
      T.ebox(stoneM, e, g.s - 0.3, g.s + 0.3, 0.05, 0.2, zt + 0.8 + h * 0.55, zt + 0.8 + h * 0.95);
      kit.windowRow(batch, T.at(e, g.s - w * 0.3, 0.1), T.at(e, g.s + w * 0.3, 0.1), zt + 1.2, {
        count: 2,
        width: 1.0,
        height: 1.5,
        margin: 0.2,
        glass,
        frame: frameM,
        sill: stoneM,
        head: 'lintel',
        bars: 1,
        depth: 0.1,
      });
    }
    for (const [x, y, ang] of chimneys)
      T.chimney(x, y, top - 1.0, 1.8, 0.8, 2.2, ang, brickM, kit.mat('#a4593c'), 3);
    return { zt, top, brickM, stoneM, glass, frameM };
  };

  // ---------------------------------------------------------------------------------
  // Post-war / 1960s block: concrete or stone frame, ribbon windows or punched grid,
  // recessed ground floor, flat roof with plant room.
  // ---------------------------------------------------------------------------------
  T.modernBlock = (ring, o) => {
    const {
      storeys = 5,
      storeyH = 3.4,
      groundH = 4.0,
      skin = '#d9d4c7',
      glassC = '#2c3a44',
      mode = 'ribbon', // ribbon | grid | fins
      sill = 1.0,
      mull = 1.5,
      winW = 1.4,
      recess = 0,
      plant = 0.35, // plant room footprint fraction (inset) or 0
      plantH = 3.0,
      front,
      thr = -2,
      rearTex,
      spandrelM,
    } = o;
    const skinM = kit.mat(skin, { roughness: 0.85 });
    const spM = spandrelM ?? skinM;
    const glass = kit.mat(glassC, { roughness: 0.15, metalness: 0.35 });
    const mullM = kit.mat('#4a5054', { roughness: 0.45, metalness: 0.5 });
    const roofM = kit.mat('#8d8f8c');
    const fronts = front ? (Array.isArray(front[0]) ? front : [front]) : null;
    const E = T.edges(ring);
    const isF = (e) => !fronts || fronts.some((f) => T.faces(e, f, thr));
    const H = groundH + (storeys - 1) * storeyH;
    // ground floor
    if (recess > 0) {
      const inner = kit.offsetRing(ring, -recess);
      for (const e of T.edges(inner)) {
        if (e.len < 0.1) continue;
        T.wall(glass, e, 0, groundH);
        const n = Math.max(1, Math.round(e.len / 2));
        for (let k = 0; k <= n; k++)
          T.ebox(mullM, e, (k * e.len) / n - 0.05, (k * e.len) / n + 0.05, 0, 0.1, 0, groundH);
      }
      kit.cap(batch, skinM, [[ring]], groundH, { down: true });
      for (const e of E) {
        if (e.len < 5) continue;
        const n = Math.max(1, Math.round(e.len / 6));
        for (let k = 0; k <= n; k++) {
          const s = Math.min(e.len - 0.3, Math.max(0.3, (k * e.len) / n));
          T.ebox(skinM, e, s - 0.3, s + 0.3, -0.6, 0, 0, groundH);
        }
      }
    }
    for (const e of E) {
      if (e.len < 0.1) continue;
      const fz0 = recess > 0 ? groundH : 0;
      if (!isF(e) && rearTex) {
        T.wall(kit.facade(rearTex, 1), e, fz0, H + 0.9, { bay: 3.4, storey: storeyH });
        continue;
      }
      T.wall(skinM, e, fz0, H + 0.9);
      if (e.len < 2.5) continue;
      for (let s = recess > 0 ? 1 : 0; s < storeys; s++) {
        const z0 = s === 0 ? 0 : groundH + (s - 1) * storeyH;
        const sh = s === 0 ? groundH : storeyH;
        if (mode === 'ribbon') {
          const g0 = z0 + sill,
            g1 = z0 + sh - 0.35;
          T.ebox(glass, e, 0.5, e.len - 0.5, -0.05, 0.03, g0, g1);
          T.ebox(spM, e, 0.3, e.len - 0.3, 0, 0.12, z0 - 0.05, g0);
          const n = Math.max(1, Math.round((e.len - 1) / mull));
          for (let k = 0; k <= n; k++) {
            const ss = 0.5 + ((e.len - 1) * k) / n;
            T.ebox(mullM, e, ss - 0.04, ss + 0.04, 0, 0.09, g0, g1);
          }
        } else {
          kit.windowRow(batch, e.a, e.b, z0 + sill, {
            bay: mull,
            width: winW,
            height: sh - sill - 0.45,
            margin: 0.5,
            glass,
            frame: mullM,
            sill: skinM,
            head: 'none',
            bars: mode === 'grid' ? 1 : 0,
            depth: 0.1,
          });
          if (mode === 'fins') {
            const n = Math.max(1, Math.round(e.len / mull));
            for (let k = 0; k <= n; k++)
              T.ebox(
                skinM,
                e,
                (k * e.len) / n - 0.12,
                (k * e.len) / n + 0.12,
                0,
                0.45,
                z0,
                z0 + sh,
              );
          }
        }
      }
    }
    kit.cornice(batch, skinM, ring, H + 0.6, { height: 0.3, projection: 0.15 });
    kit.cap(batch, roofM, [[ring]], H + 0.85);
    if (plant > 0) {
      const f = kit.ringFrame(ring);
      const pr = kit.offsetRing(ring, -Math.min(f.width, f.length) * plant);
      if (kit.ringArea(pr) > 8) {
        kit.walls(batch, kit.mat('#9a9a96'), [[pr]], H + 0.85, H + 0.85 + plantH, { bay: 1e6 });
        kit.cap(batch, kit.mat('#7e807e'), [[pr]], H + 0.85 + plantH);
      }
    }
    return { H, top: H + 0.9, skinM, glass, mullM };
  };
  return T;
}
// ---- end shared helpers ----------------------------------------------------------------

export default {
  id: 'princes_gardens_north_terrace',
  name: "Nos 10-15 Prince's Gardens (north side terrace)",
  claims: ['8bab940d-4847-47ba-8831-4462612085ec', '5b9d5bfc-a1db-4726-83fc-3df6abb7f66e'],
  references: [
    {
      title: '8-15 Princes Gardens SW7 - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101227167-8-15-princes-gardens-sw7-knightsbridge-and-belgravia-ward',
      used_for:
        'stucco terrace, five storeys plus basement, three windows per house, Doric porches, first-floor balustrade, cast-iron area railings, Grade II 1975',
    },
    {
      title: 'Plate 97: Princes Gardens - Survey of London vol. 45',
      url: 'https://www.british-history.ac.uk/survey-london/vol45/plate-97',
      used_for: 'north side built 1859-61; all but Nos 8-15 demolished; No. 15 beside Weeks Hall',
    },
  ],
  notes:
    'House widths are taken from equal divisions of the two footprints (about 7 m each); storey heights ' +
    '(4.2 m ground, 3.9/3.4/3.0 m above, 2.9 m attic storey) and the attic treatment are estimates. ' +
    'Porch positions alternate between houses; rear elevations use a stock-brick texture.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = makeTools(ctx, batch);
    for (const b of buildings) {
      const ring = T.ring(b);
      T.stuccoTerrace(ring, {
        front: [0, -1],
        houseW: 7.2,
        upper: [3.9, 3.4, 3.0],
        attic: 'storey',
        atticStorey: 2.9,
        color: '#f0ebdf',
      });
    }
    g.add(batch.toGroup('princes_gardens_north_terrace'));
    return g;
  },
};
