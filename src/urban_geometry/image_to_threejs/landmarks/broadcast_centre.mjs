// Broadcast Centre, White City Place (former BBC Media Village), Allies and Morrison with
// Buro Happold, built by Bovis Lend Lease 2001-04. The BBC's playout centre: a long,
// deliberately modest office slab. West and south elevations are fronted by projecting
// banks of louvred sunscreens; the piazza (east) elevations alternate storey-height
// glazed panels with narrow vertical strips of built-in louvres (smoke vents). The names
// of the 1908 Olympic athletes are inscribed on the building's flank and the stadium
// finish line is marked in the paving outside.
// ---- shared modelling helpers (inlined per module; no imports) -------------------
function mkHelpers(THREE, kit, batch, tag) {
  const H = {};
  H.ccw = (r) => {
    const q = r.slice();
    if (kit.ringArea(q) < 0) q.reverse();
    return q;
  };
  H.edges = (r, min = 0.05) =>
    r
      .map((a, k) => {
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
          mid: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
        };
      })
      .filter((e) => e.len >= min);
  H.at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  H.ebox = (m, e, s0, s1, d0, d1, z0, z1, col) => {
    const c = H.at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(batch, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang, col);
  };
  H.quad = (m, p, q, z0, z1, u0 = 0, u1 = 1, v0 = 0, v1 = 1, col) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
      col,
    );
  // Closed prism (walls + top cap; bottom optional).
  H.prism = (m, ring, z0, z1, { top = m, bottom = false, bay = 1e6, storey = 3.2, color } = {}) => {
    kit.walls(batch, m, [[ring]], z0, z1, { bay, storey, uvBase: z0, color });
    if (top) kit.cap(batch, top, [[ring]], z1, { color });
    if (bottom) kit.cap(batch, m, [[ring]], z0, { down: true, color });
  };
  // Box in a local frame (origin o, angle ang): centre (u, v), size (w, d), z0..z1.
  H.lbox = (m, o, ang, u, v, w, d, z0, z1, col) => {
    const c = Math.cos(ang),
      s = Math.sin(ang);
    kit.box(batch, m, o[0] + u * c - v * s, o[1] + u * s + v * c, z0, w, d, z1 - z0, ang, col);
  };
  H.cyl = (m, x, y, z0, h, r, seg = 16, r2 = r) => {
    const g = new THREE.CylinderGeometry(r2, r, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
    g.dispose();
  };
  H.lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(r, h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
    g.dispose();
  };
  // Glass seen from outside: one storey per texture tile (v), `w` metres per tile (u).
  H.glassMat = (
    key,
    {
      ceil = '#a5b0b5',
      top = '#5b6d78',
      mid = '#33444f',
      bot = '#3d505c',
      rough = 0.15,
      metal = 0.35,
      frames = 0,
      frameCol = '#555',
    } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      128,
      128,
      (c, w, h) => {
        const g = c.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, ceil);
        g.addColorStop(0.12, top);
        g.addColorStop(0.55, mid);
        g.addColorStop(1, bot);
        c.fillStyle = g;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(220,230,240,0.08)';
        c.fillRect(w * 0.15, h * 0.2, w * 0.2, h * 0.75);
        if (frames) {
          c.fillStyle = frameCol;
          for (let k = 0; k < frames; k++) c.fillRect((k * w) / frames, 0, 3, h);
        }
      },
      { roughness: rough, metalness: metal },
    );
  // Brick / panel texture: `tile` metres square per repeat (use with H.tiled()).
  H.brickMat = (
    key,
    { base = '#8f4e3a', mortar = '#b9a99a', vary = 0.12, courses = 52, seed = 1 } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(seed);
        c.fillStyle = mortar;
        c.fillRect(0, 0, w, h);
        const bh = h / courses,
          bw = bh * 3.4;
        const col = new THREE.Color(base);
        for (let y = 0; y < courses; y++)
          for (let x = -1; x < w / bw + 1; x++) {
            const k = 1 + (r() - 0.5) * 2 * vary;
            c.fillStyle = '#' + col.clone().multiplyScalar(k).getHexString();
            c.fillRect((x + (y % 2) * 0.5) * bw + 0.6, y * bh + 0.6, bw - 1.2, bh - 1.2);
          }
      },
      { roughness: 0.9 },
    );
  // Walls with world-metre UVs: `tile` metres per texture repeat.
  H.tiled = (m, ring, z0, z1, tile = 4, color) =>
    kit.walls(batch, m, [[ring]], z0, z1, { bay: tile / 4, storey: tile / 2, uvBase: 0, color });
  H.tquad = (m, e, s0, s1, d, z0, z1, tile = 4, col) =>
    H.quad(
      m,
      H.at(e, s0, d),
      H.at(e, s1, d),
      z0,
      z1,
      s0 / tile,
      s1 / tile,
      z0 / tile,
      z1 / tile,
      col,
    );
  // Curtain wall: glass set back `set`, mullions every `mod`, slab bands every storey.
  H.curtain = (ring, z0, z1, o = {}) => {
    const {
      storey = 3.6,
      glass,
      mull = kit.mat('#4b5257', { roughness: 0.4, metalness: 0.5 }),
      mod = 1.5,
      set = 0.2,
      band = null, // material of slab-edge band
      bandH = 0.5,
      bandD = 0.15,
      transom = 0.9,
      skip = () => false,
      span = (e) => [0, e.len],
      mullD = 0.15,
    } = o;
    for (const e of H.edges(ring, 0.3)) {
      if (skip(e)) continue;
      const [s0, s1] = span(e);
      if (s1 - s0 < 0.3) continue;
      H.quad(
        glass,
        H.at(e, s0, -set),
        H.at(e, s1, -set),
        z0,
        z1,
        s0 / 3,
        s1 / 3,
        0,
        (z1 - z0) / storey,
      );
      const n = Math.max(1, Math.round((s1 - s0) / mod));
      if (mod < 50)
        for (let k = 0; k <= n; k++) {
          const s = s0 + ((s1 - s0) * k) / n;
          H.ebox(mull, e, s - 0.04, s + 0.04, -set, -set + mullD, z0, z1);
        }
      const ns = Math.round((z1 - z0) / storey);
      for (let k = 0; k <= ns; k++) {
        const z = z0 + k * storey;
        if (band && k > 0 && k <= ns)
          H.ebox(band, e, s0, s1, -set, bandD, z - bandH / 2, Math.min(z1, z + bandH / 2));
        if (transom && k < ns)
          H.ebox(mull, e, s0, s1, -set, -set + 0.08, z + transom, z + transom + 0.06);
      }
    }
  };
  // Ribbon facade: solid spandrel (wall material) + recessed glazing band per storey.
  H.ribbon = (ring, z0, nst, storey, o = {}) => {
    const {
      wall,
      glass,
      sp = 1.1, // spandrel height
      set = 0.25,
      mod = 1.5,
      mull = kit.mat('#3f454a', { roughness: 0.4, metalness: 0.5 }),
      skip = () => false,
      wallCol,
    } = o;
    for (const e of H.edges(ring, 0.3)) {
      if (skip(e)) continue;
      for (let k = 0; k < nst; k++) {
        const z = z0 + k * storey;
        H.ebox(wall, e, 0, e.len, -set, 0, z, z + sp, wallCol);
        H.quad(
          glass,
          H.at(e, 0, -set),
          H.at(e, e.len, -set),
          z + sp,
          z + storey,
          0,
          e.len / 3,
          0,
          1,
        );
        if (mod && e.len > mod) {
          const n = Math.max(1, Math.round(e.len / mod));
          for (let j = 1; j < n; j++) {
            const s = (e.len * j) / n;
            H.ebox(mull, e, s - 0.04, s + 0.04, -set, -set + 0.12, z + sp, z + storey);
          }
        }
      }
    }
  };
  // Punched windows in a wall (wall faces as tiled quads, simple boxed windows).
  H.punched = (ring, z0, nst, storey, o = {}) => {
    const {
      wall,
      tile = 4,
      winW = 1.4,
      winH = 1.8,
      sill = 0.9,
      bay = 3.0,
      margin = 0.8,
      glass = kit.mat('dark_glass'),
      frame = kit.mat('#d9d9d4'),
      reveal = 0.18,
      skip = () => false,
      pattern = null, // (e, k, j) => false to omit a window
      top = z0 + nst * storey,
      wallCol,
      surround = null,
    } = o;
    for (const e of H.edges(ring, 0.05)) {
      // wall face
      H.tquad(wall, e, 0, e.len, 0, 0, top, tile, wallCol);
      if (skip(e) || e.len < winW + 2 * margin * 0.5) continue;
      const usable = e.len - 2 * margin;
      const n = Math.max(1, Math.floor(usable / bay + 0.35));
      for (let k = 0; k < nst; k++) {
        const z = z0 + k * storey + sill;
        for (let j = 0; j < n; j++) {
          if (pattern && pattern(e, k, j, n) === false) continue;
          const s = margin + (usable * (j + 0.5)) / n;
          // glass + frame/sill proud of the wall plane
          H.ebox(glass, e, s - winW / 2, s + winW / 2, 0, 0.03, z, z + winH);
          H.ebox(frame, e, s - winW / 2 - 0.08, s + winW / 2 + 0.08, 0, reveal, z - 0.1, z);
          H.ebox(frame, e, s - winW / 2 - 0.08, s - winW / 2, 0, reveal * 0.6, z, z + winH);
          H.ebox(frame, e, s + winW / 2, s + winW / 2 + 0.08, 0, reveal * 0.6, z, z + winH);
          H.ebox(
            frame,
            e,
            s - winW / 2 - 0.08,
            s + winW / 2 + 0.08,
            0,
            reveal * 0.6,
            z + winH,
            z + winH + 0.08,
          );
          if (surround) {
            H.ebox(surround, e, s - winW / 2 - 0.2, s - winW / 2 - 0.08, 0, 0.1, z, z + winH);
            H.ebox(surround, e, s + winW / 2 + 0.08, s + winW / 2 + 0.2, 0, 0.1, z, z + winH);
            H.ebox(
              surround,
              e,
              s - winW / 2 - 0.2,
              s + winW / 2 + 0.2,
              0,
              0.1,
              z + winH + 0.08,
              z + winH + 0.2,
            );
          }
        }
      }
    }
  };
  // Flat roof with parapet and coping.
  H.roof = (
    ring,
    z,
    { parapet = 1.0, wall, roof = kit.mat('#8e8f8b'), coping = null, inset = 0.35 } = {},
  ) => {
    kit.cap(batch, roof, [[ring]], z);
    if (parapet > 0) {
      const inner = kit.offsetRing(ring, -inset);
      kit.walls(batch, wall, [[ring]], z, z + parapet, { bay: 1e6 });
      kit.walls(batch, wall, [[inner.slice().reverse()]], z, z + parapet, { bay: 1e6 });
      kit.cap(batch, coping || wall, [[ring, inner.slice().reverse()]], z + parapet);
    }
  };
  // Rooftop plant enclosure with louvre stripes.
  H.plant = (
    ring,
    z,
    h,
    {
      mat = kit.mat('#8a8d8e'),
      louvre = kit.mat('#a7aaab', { metalness: 0.3, roughness: 0.6 }),
      pitch = 0.35,
    } = {},
  ) => {
    if (kit.ringArea(ring) < 4) return;
    H.prism(mat, ring, z, z + h);
    for (const e of H.edges(ring, 1)) {
      for (let zz = z + 0.3; zz < z + h - 0.2; zz += pitch)
        H.ebox(louvre, e, 0.1, e.len - 0.1, 0, 0.06, zz, zz + 0.06);
    }
  };
  // Painted text sign material.
  H.signMat = (
    key,
    text,
    {
      w = 512,
      h = 96,
      bg = '#ffffff',
      fg = '#111111',
      font = 'bold 56px sans-serif',
      transparent = false,
    } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      w,
      h,
      (c, W, Hh) => {
        if (!transparent) {
          c.fillStyle = bg;
          c.fillRect(0, 0, W, Hh);
        }
        c.fillStyle = fg;
        c.font = font;
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(text, W / 2, Hh / 2 + 2);
      },
      { roughness: 0.6, transparent },
    );
  H.sign = (m, e, sm, width, d, z0, z1) =>
    H.quad(m, H.at(e, sm - width / 2, d), H.at(e, sm + width / 2, d), z0, z1);
  // Longest edges first.
  H.byLen = (ring) => H.edges(ring).sort((p, q) => q.len - p.len);
  // Edge whose outward normal best matches a direction (radians from east).
  H.facing = (ring, dir, min = 3) => {
    let best = null,
      bd = -2;
    for (const e of H.edges(ring, min)) {
      const d = e.nx * Math.cos(dir) + e.ny * Math.sin(dir);
      if (d * Math.sqrt(e.len) > bd) {
        bd = d * Math.sqrt(e.len);
        best = e;
      }
    }
    return best;
  };
  H.dirOf = (e) => Math.atan2(e.ny, e.nx);
  // Straight member between two 3D points with a w x d cross-section.
  H.beam = (m, A, B, w = 0.4, d = 0.4) => {
    const a = new THREE.Vector3(...A),
      b = new THREE.Vector3(...B);
    const dir = b.clone().sub(a);
    const len = dir.length();
    if (len < 1e-3) return;
    const geo = new THREE.BoxGeometry(len, w, d);
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(1, 0, 0),
      dir.normalize(),
    );
    const mm = new THREE.Matrix4().compose(
      a.clone().add(b).multiplyScalar(0.5),
      q,
      new THREE.Vector3(1, 1, 1),
    );
    batch.addGeometry(m, geo, mm);
    geo.dispose();
  };
  // Clip ring to the band u0 <= (p . (ux, uy)) <= u1.
  H.clipBand = (ring, ux, uy, u0, u1) => {
    const clip = (r, sx, sy, c) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        const dp = sx * p[0] + sy * p[1] - c,
          dq = sx * q[0] + sy * q[1] - c;
        if (dp <= 0) out.push(p);
        if (dp * dq < 0) {
          const t = dp / (dp - dq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    return clip(clip(ring, ux, uy, u1), -ux, -uy, -u0);
  };
  // Saw-tooth (north-light) roof over `ring` at zt: teeth of width `period` across the
  // direction `dir` (unit vector of increasing v); each tooth rises by `rise` towards +v and
  // ends in a vertical glazed face looking along +v.
  H.sawtooth = (ring, dir, zt, period, rise, { roof, glass, wall }) => {
    const vx = Math.cos(dir),
      vy = Math.sin(dir);
    const vOf = (p) => p[0] * vx + p[1] * vy;
    let v0 = Infinity,
      v1 = -Infinity;
    for (const p of ring) {
      v0 = Math.min(v0, vOf(p));
      v1 = Math.max(v1, vOf(p));
    }
    const n = Math.max(1, Math.round((v1 - v0) / period));
    const P = (v1 - v0) / n;
    for (let k = 0; k < n; k++) {
      const a = v0 + k * P,
        b = a + P;
      const strip = H.clipBand(ring, vx, vy, a, b);
      if (strip.length < 3) continue;
      const sr = H.ccw(strip);
      const z = (p) => zt + (rise * (vOf(p) - a)) / P;
      let tris;
      try {
        tris = THREE.ShapeUtils.triangulateShape(
          sr.map(([x, y]) => new THREE.Vector2(x, y)),
          [],
        );
      } catch {
        continue;
      }
      batch.add(
        roof,
        sr.map((p) => [p[0], p[1], z(p)]),
        sr.map((p) => [p[0] / 3, p[1] / 3]),
        tris.flat(),
      );
      for (let i = 0; i < sr.length; i++) {
        const p = sr[i],
          q = sr[(i + 1) % sr.length];
        const onA = Math.abs(vOf(p) - a) < 1e-3 && Math.abs(vOf(q) - a) < 1e-3;
        const onB = Math.abs(vOf(p) - b) < 1e-3 && Math.abs(vOf(q) - b) < 1e-3;
        if (onA) continue;
        if (onB) {
          H.quad(glass, p, q, zt, zt + rise, 0, Math.hypot(q[0] - p[0], q[1] - p[1]) / 3, 0, 1);
          continue;
        }
        batch.add(
          wall,
          [
            [p[0], p[1], zt],
            [q[0], q[1], zt],
            [q[0], q[1], z(q)],
            [p[0], p[1], z(p)],
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
    }
  };
  // Drop vertices whose triangle with their neighbours is smaller than minArea (m2).
  H.simplify = (ring, minArea = 1) => {
    let r = ring.slice();
    for (let guard = 0; guard < 1000 && r.length > 3; guard++) {
      let best = -1,
        ba = Infinity;
      for (let i = 0; i < r.length; i++) {
        const a = r[(i - 1 + r.length) % r.length],
          b = r[i],
          c = r[(i + 1) % r.length];
        const ar = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
        if (ar < ba) {
          ba = ar;
          best = i;
        }
      }
      if (ba >= minArea) break;
      r.splice(best, 1);
    }
    return r;
  };
  // Folded roof over the real footprint: z = f(v) piecewise linear along direction `dir`
  // (profile [[v, z], ...] in metres along dir, sorted); walls from z0 up to the roof line.
  H.foldRoof = (ring, dir, profile, z0, { roof, wall, wallTile = 4 }) => {
    const vx = Math.cos(dir),
      vy = Math.sin(dir);
    const vOf = (p) => p[0] * vx + p[1] * vy;
    const f = (v) => {
      if (v <= profile[0][0]) return profile[0][1];
      for (let k = 1; k < profile.length; k++)
        if (v <= profile[k][0] + 1e-9) {
          const [a, za] = profile[k - 1],
            [b, zb] = profile[k];
          return za + ((zb - za) * (v - a)) / (b - a || 1);
        }
      return profile[profile.length - 1][1];
    };
    for (const e of H.edges(ring, 0.05)) {
      const va = vOf(e.a),
        vb = vOf(e.b);
      const ss = [0, e.len];
      for (const [v] of profile) {
        const t = (v - va) / (vb - va || 1e-9);
        if (t > 1e-3 && t < 1 - 1e-3) ss.push(t * e.len);
      }
      ss.sort((a, b) => a - b);
      for (let k = 1; k < ss.length; k++) {
        const p = H.at(e, ss[k - 1]),
          q = H.at(e, ss[k]);
        const zp = f(vOf(p)),
          zq = f(vOf(q));
        batch.add(
          wall,
          [
            [p[0], p[1], z0],
            [q[0], q[1], z0],
            [q[0], q[1], zq],
            [p[0], p[1], zp],
          ],
          [
            [ss[k - 1] / wallTile, z0 / wallTile],
            [ss[k] / wallTile, z0 / wallTile],
            [ss[k] / wallTile, zq / wallTile],
            [ss[k - 1] / wallTile, zp / wallTile],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
    }
    for (let k = 1; k < profile.length; k++) {
      const strip = H.clipBand(ring, vx, vy, profile[k - 1][0], profile[k][0]);
      if (strip.length < 3) continue;
      const sr = H.ccw(strip);
      let tris;
      try {
        tris = THREE.ShapeUtils.triangulateShape(
          sr.map(([x, y]) => new THREE.Vector2(x, y)),
          [],
        );
      } catch {
        continue;
      }
      batch.add(
        roof,
        sr.map((p) => [p[0], p[1], f(vOf(p)) + 0.02]),
        sr.map((p) => [p[0] / 4, p[1] / 4]),
        tris.flat(),
      );
    }
    return f;
  };
  return H;
}

export default {
  id: 'broadcast_centre',
  name: 'Broadcast Centre',
  claims: ['62687cd9-7abb-44c6-81d0-cf3c417675ab'],
  references: [
    {
      title: 'White City Place - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/White_City_Place',
      used_for:
        'Allies and Morrison / Buro Happold / Bovis Lend Lease, opened 2004; 1908 athletes inscribed on the Broadcast Centre, finish line in the paving',
    },
    {
      title: 'And now from the BBC - Building',
      url: 'https://www.building.co.uk/focus/and-now-from-the-bbc-/3032924.article',
      used_for:
        'west/south facades fronted by projecting banks of louvred sunscreens; east (piazza) facades alternate storey-height glazing with narrow louvre strips that act as smoke vents',
    },
    {
      title: 'BBC Media Village - Cayford',
      url: 'https://www.cayford.com/work/bbc-media-village/',
      used_for: 'Broadcast Centre as the BBC playout facility; RIBA award 2005',
    },
  ],
  notes:
    'Storey split (4.4 m ground + 5 x 3.12 m to the 20 m Overture height) is assumed. The ' +
    'sunscreen bank depth (1.3 m), blade pitch, outrigger spacing and the louvre-strip rhythm on ' +
    'the piazza side (3.0 m glass / 0.9 m louvre) are estimates of the described system, not ' +
    'measured. The inscription band is a painted stand-in for the athletes list. Roof plant and ' +
    'the finish-line strip position are approximate.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const H = mkHelpers(THREE, kit, batch, 'broadcast_centre');
    const ring = H.ccw(buildings[0].polys[0][0]);
    const HT = 20,
      G = 4.4,
      NS = 5,
      ST = (HT - 0.9 - G) / NS;
    const glass = H.glassMat('glass', {
      ceil: '#b9c2c4',
      top: '#6d8590',
      mid: '#3c5361',
      bot: '#4a6170',
    });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const frameM = kit.mat('#b8bdbf', { roughness: 0.4, metalness: 0.55 });
    const louvre = kit.mat('#9ea4a6', { roughness: 0.45, metalness: 0.5 });
    const slab = kit.mat('#d8d6cf', { roughness: 0.8 });
    const dark = kit.mat('#4a5054', { roughness: 0.5, metalness: 0.4 });
    const paving = kit.mat('#c4beb2');
    const east = (e) => e.nx > 0.45 && e.ny > -0.6; // piazza-facing

    // ground floor: recessed glazing behind the line of the upper floors
    const inner = kit.offsetRing(ring, -1.2);
    for (const e of H.edges(inner, 0.3)) {
      H.quad(darkGlass, e.a, e.b, 0, G - 0.4, 0, e.len / 3);
      const n = Math.max(1, Math.round(e.len / 2.4));
      for (let k = 0; k <= n; k++)
        H.ebox(frameM, e, (k * e.len) / n - 0.05, (k * e.len) / n + 0.05, 0, 0.12, 0, G - 0.4);
    }
    kit.cap(batch, slab, [[ring]], G - 0.4, { down: true });
    kit.walls(batch, slab, [[ring]], G - 0.4, G, { bay: 1e6 });
    // columns along the perimeter under the overhang
    for (const e of H.edges(ring, 6)) {
      const n = Math.max(1, Math.round(e.len / 7.5));
      for (let k = 0; k <= n; k++) {
        const s = Math.min(e.len - 0.4, Math.max(0.4, (k * e.len) / n));
        H.ebox(slab, e, s - 0.3, s + 0.3, -0.9, -0.3, 0, G - 0.4);
      }
    }

    // upper floors: glazing, slab bands and mullions
    const z1 = G + NS * ST;
    H.curtain(ring, G, z1, {
      storey: ST,
      glass,
      mull: frameM,
      mod: 1.5,
      set: 0.25,
      band: slab,
      bandH: 0.45,
      bandD: 0.1,
    });
    // piazza elevations: alternating storey-height glass and narrow louvre strips
    for (const e of H.edges(ring, 4)) {
      if (!east(e)) continue;
      const step = 3.9;
      const n = Math.floor(e.len / step);
      const off = (e.len - n * step) / 2;
      for (let k = 0; k < n; k++) {
        const s = off + k * step + 3.0;
        for (let f = 0; f < NS; f++) {
          const z = G + f * ST + 0.25;
          H.ebox(dark, e, s, s + 0.9, -0.22, -0.12, z, z + ST - 0.5);
          for (let zz = z + 0.1; zz < z + ST - 0.6; zz += 0.22)
            H.ebox(louvre, e, s + 0.04, s + 0.86, -0.12, 0.08, zz, zz + 0.05);
          H.ebox(frameM, e, s - 0.05, s, -0.25, 0.1, z, z + ST - 0.5);
          H.ebox(frameM, e, s + 0.9, s + 0.95, -0.25, 0.1, z, z + ST - 0.5);
        }
      }
    }
    // west and south elevations: projecting banks of louvred sunscreens
    for (const e of H.edges(ring, 8)) {
      if (east(e)) continue;
      const D = 1.3;
      const n = Math.max(1, Math.round(e.len / 6));
      for (let k = 0; k <= n; k++) {
        const s = Math.min(e.len - 0.2, Math.max(0.2, (k * e.len) / n));
        H.ebox(frameM, e, s - 0.06, s + 0.06, 0.1, D, G - 0.2, z1); // outrigger fin
      }
      for (let f = 0; f < NS; f++) {
        const z = G + f * ST;
        H.ebox(frameM, e, 0.2, e.len - 0.2, 0.1, D, z + 0.05, z + 0.17); // walkway grille
        for (let b = 0; b < 4; b++) {
          const zz = z + ST * 0.45 + b * 0.32;
          H.ebox(louvre, e, 0.2, e.len - 0.2, D - 0.35, D - 0.05, zz, zz + 0.06);
        }
      }
    }

    // parapet, roof and plant
    H.roof(ring, z1, { parapet: HT - z1, wall: slab, roof: kit.mat('#8b8d8a') });
    const pr = kit.offsetRing(ring, -9);
    if (kit.ringArea(pr) > 80) H.plant(pr, z1, 3.2, {});

    // athletes inscription band on the north-west flank + finish-line strip in the paving
    const flank = H.byLen(ring)[0];
    const ins = kit.paintedMaterial(
      'broadcast_centre:names',
      1024,
      64,
      (c, w, h) => {
        c.fillStyle = '#d8d6cf';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#5b5e60';
        c.font = '12px serif';
        const r = kit.rng(7);
        for (let row = 0; row < 4; row++)
          for (let x = 4; x < w - 40;) {
            const n = 4 + Math.floor(r() * 9);
            c.fillText(
              'ABCDEFGHIJKLMNOPRSTW'
                .slice(0, n)
                .split('')
                .sort(() => r() - 0.5)
                .join(''),
              x,
              14 + row * 15,
            );
            x += n * 8 + 10;
          }
      },
      { roughness: 0.8 },
    );
    H.quad(ins, H.at(flank, 6, -1.15), H.at(flank, flank.len - 6, -1.15), 1.0, 3.2, 0, 4, 0, 1);
    const pv = kit.offsetRing(ring, 6);
    kit.cap(batch, paving, [[pv, ring.slice().reverse()]], 0.03);
    const se = H.facing(ring, -Math.PI / 3);
    H.ebox(kit.mat('#f2f2ee'), se, se.len * 0.2, se.len * 0.8, 1.5, 1.9, 0.035, 0.05);

    g.add(batch.toGroup('broadcast_centre'));
    return g;
  },
};
