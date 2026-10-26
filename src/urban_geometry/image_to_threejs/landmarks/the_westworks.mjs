// The WestWorks, 201 Wood Lane, White City Place. Built 1985-90 as BBC White City to
// designs by Scott Brownrigg & Turner - the first building on the Media Village site,
// on the site of the 1908 Olympic stadium. A seven-storey, aluminium-clad, symmetrical
// square block with dark glazing round a formal central atrium/courtyard, with stair and
// service cores expressed as small projections on each face. Refurbished by Allies and
// Morrison for Stanhope / Mitsui Fudosan (2017): improved facade, relocated entrance and a
// new 52 m long dark blue-grey anodised feature facade with bespoke spandrel cladding to
// the courtyard.
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
  id: 'the_westworks',
  name: 'The WestWorks',
  claims: ['46219c96-8da3-47a2-8094-807542e36258'],
  references: [
    {
      title: 'White City Place - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/White_City_Place',
      used_for:
        'BBC White City by Scott Brownrigg & Turner opened 1990 on the 1908 stadium site; renamed WestWorks',
    },
    {
      title: 'Gateway West / Gateway Central - Architecture Today',
      url: 'https://architecturetoday.co.uk/gateway-west-gateway-central/',
      used_for: 'former BBC administrative HQ: seven-storey aluminium-clad building',
    },
    {
      title: 'White City Place - Allies and Morrison',
      url: 'https://www.alliesandmorrison.com/projects/white-city-place',
      used_for:
        'conversion of White City One: original dark glazing, symmetrical plan and formal atrium',
    },
    {
      title: 'OAG facade unveiled at West Works',
      url: 'https://www.oag.uk.com/architectural-glass-specialists/oag-facade-unveiled-west-works-old-bbc-studios-white-city/',
      used_for:
        '52 m courtyard feature facade, dark blue/grey anodised finish beneath bespoke spandrel cladding; new shopfronts',
    },
    {
      title: '6,400 jobs to be created in White City Place - FulhamSW6',
      url: 'https://fulhamsw6.com/page/shepherdsbushw12/info/whitecityplace002.htm',
      used_for: 'WestWorks improved facade and relocated entrance (2016-17)',
    },
  ],
  notes:
    'Seven storeys from the sources; storey split 4.2 m ground + 6 x 2.95 m to the 23.2 m Overture ' +
    'height. Ribbon proportions (spandrel 1.15 m), aluminium colour, the location of the relocated ' +
    'entrance (south-east face, towards the piazza), the courtyard glass roof and its height are ' +
    'assumptions; the 52 m feature facade is placed on the longest courtyard face. Core projections ' +
    'follow the footprint notches and are taken one storey above the roof.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const H = mkHelpers(THREE, kit, batch, 'the_westworks');
    const poly = buildings[0].polys[0];
    const ring = H.ccw(poly[0]);
    const court = H.ccw(poly[1] || []);
    const HT = 23.2,
      G = 4.2,
      NS = 6,
      ST = (HT - 1.1 - G) / NS;
    const z1 = G + NS * ST;
    const glass = H.glassMat('glass', {
      ceil: '#8e9aa0',
      top: '#3e4c56',
      mid: '#222d35',
      bot: '#2b3740',
    });
    const alu = kit.mat('#b7bcbf', { roughness: 0.35, metalness: 0.6 });
    const aluDark = kit.mat('#8f969a', { roughness: 0.4, metalness: 0.55 });
    const anod = kit.mat('#3b4552', { roughness: 0.35, metalness: 0.6 });
    const spandrel = kit.mat('#56606c', { roughness: 0.4, metalness: 0.5 });
    const darkGlass = kit.mat('#1f2a32', { roughness: 0.1, metalness: 0.45 });
    const roofM = kit.mat('#8c8e8b');
    const lite = kit.mat('#9fb7bf', {
      roughness: 0.08,
      metalness: 0.2,
      transparent: true,
      opacity: 0.6,
    });

    // ground floor: dark glazing with aluminium mullions, new shopfronts
    for (const e of H.edges(ring, 0.3)) {
      H.ebox(aluDark, e, 0, e.len, -0.3, 0, 0, 0.5);
      H.quad(darkGlass, H.at(e, 0, -0.3), H.at(e, e.len, -0.3), 0.5, G - 0.5, 0, e.len / 3);
      const n = Math.max(1, Math.round(e.len / 3));
      for (let k = 0; k <= n; k++)
        H.ebox(alu, e, (k * e.len) / n - 0.06, (k * e.len) / n + 0.06, -0.3, 0.05, 0.5, G - 0.5);
      H.ebox(alu, e, 0, e.len, -0.3, 0.1, G - 0.5, G);
    }
    // upper floors: aluminium spandrel ribbons, dark glazing bands
    H.ribbon(ring, G, NS, ST, { wall: alu, glass, sp: 1.15, set: 0.22, mod: 1.8, mull: aluDark });
    kit.walls(batch, alu, [[ring]], z1, HT, { bay: 1e6 });
    // cores: the footprint notches rise above the roof as plant/stair towers
    const fr = kit.ringFrame(ring);
    const cores = [];
    for (const e of H.edges(ring, 4)) if (e.len < 7.5) cores.push(e);
    const used = new Set();
    for (let i = 0; i < ring.length; i++) {
      // a notch = three short edges in a row
      const es = [0, 1, 2].map(
        (d) => H.edges([ring[(i + d) % ring.length], ring[(i + d + 1) % ring.length]], 0)[0],
      );
      if (es.every((e) => e.len < 7.5) && !used.has(i)) {
        const pts = [
          ring[i],
          ring[(i + 1) % ring.length],
          ring[(i + 2) % ring.length],
          ring[(i + 3) % ring.length],
        ];
        const cx = pts.reduce((a, p) => a + p[0], 0) / 4,
          cy = pts.reduce((a, p) => a + p[1], 0) / 4;
        const dx = cx - fr.cx,
          dy = cy - fr.cy,
          dl = Math.hypot(dx, dy);
        const bx = cx - (dx / dl) * 3,
          by = cy - (dy / dl) * 3;
        kit.box(batch, alu, bx, by, HT - 0.2, 7.5, 7.5, 3.6, Math.atan2(dy, dx));
        used
          .add(i)
          .add(i + 1)
          .add(i + 2);
      }
    }
    // roof
    kit.cap(batch, roofM, court.length ? [[ring, court.slice().reverse()]] : [[ring]], z1 + 0.6);
    const pin = kit.offsetRing(ring, -0.4);
    kit.walls(batch, alu, [[pin.slice().reverse()]], z1 + 0.6, HT, { bay: 1e6 });
    kit.cap(batch, alu, [[ring, pin.slice().reverse()]], HT);
    const pr = kit.offsetRing(ring, -11);
    if (court.length) {
      // plant pavilions on the four roof wings, between outer edge and courtyard
      for (const e of H.edges(court, 20)) {
        const pa = H.at(e, e.len * 0.2, 7),
          pb = H.at(e, e.len * 0.8, 7);
        const pl = H.ccw([
          H.at(e, e.len * 0.2, 4),
          H.at(e, e.len * 0.8, 4),
          H.at(e, e.len * 0.8, 10),
          H.at(e, e.len * 0.2, 10),
        ]);
        H.plant(pl, z1 + 0.6, 2.6);
        (void pa, pb);
      }
    } else if (kit.ringArea(pr) > 50) H.plant(pr, z1 + 0.6, 2.6);

    // courtyard: inner ribbon elevations, 52 m anodised feature facade and glass roof
    if (court.length) {
      const cin = court.slice().reverse(); // walls facing into the court
      const ce = H.edges(cin, 0.3);
      const feat = ce.slice().sort((p, q) => q.len - p.len)[0];
      for (const e of ce) {
        if (e === feat) continue;
        for (let k = 0; k < NS; k++) {
          const z = G + k * ST;
          H.ebox(alu, e, 0, e.len, -0.22, 0, z, z + 1.15);
          H.quad(
            glass,
            H.at(e, 0, -0.22),
            H.at(e, e.len, -0.22),
            z + 1.15,
            z + ST,
            0,
            e.len / 3,
            0,
            1,
          );
        }
        H.quad(darkGlass, e.a, e.b, 0, G, 0, e.len / 3);
      }
      // feature facade: full-height glazing, anodised mullion fins, spandrel cladding
      const e = feat;
      H.quad(glass, e.a, e.b, 0, z1, 0, e.len / 3, 0, z1 / ST);
      const n = Math.round(e.len / 1.5);
      for (let k = 0; k <= n; k++)
        H.ebox(anod, e, (k * e.len) / n - 0.07, (k * e.len) / n + 0.07, 0, 0.45, 0, z1);
      for (let f = 0; f <= NS; f++)
        H.ebox(spandrel, e, 0, e.len, 0, 0.3, G + f * ST - 0.55, G + f * ST + 0.15);
      // atrium glass roof (low pitched) at roof level
      kit.cap(batch, kit.mat('#5d6a6e'), [[court]], 0.05);
      const fc = kit.ringFrame(court);
      H.prism(lite, kit.offsetRing(court, -0.05), z1 + 0.6, z1 + 0.9, { top: lite });
      const ex = kit.orientedExtent(court, fc.angle);
      for (let u = ex.u0 + 3; u < ex.u1; u += 3.5) {
        const a = ex.at(u, ex.v0),
          b = ex.at(u, ex.v1);
        kit.box(
          batch,
          aluDark,
          (a[0] + b[0]) / 2,
          (a[1] + b[1]) / 2,
          z1 + 0.6,
          0.2,
          ex.v1 - ex.v0,
          0.45,
          fc.angle,
        );
      }
    }

    // relocated entrance: canopy and signage on the face towards the piazza (south-east)
    const se = H.facing(ring, -Math.PI / 4, 20);
    if (se) {
      const sm = se.len / 2;
      H.ebox(alu, se, sm - 8, sm + 8, 0, 3.5, G - 0.6, G - 0.2);
      H.ebox(darkGlass, se, sm - 5, sm + 5, -0.29, 0.05, 0, 3.2);
      const sign = H.signMat('sign', 'THE WESTWORKS', {
        bg: '#b7bcbf',
        fg: '#1b2128',
        font: 'bold 54px sans-serif',
      });
      H.sign(sign, se, sm, 10, 3.52, G - 0.6, G - 0.2);
    }
    g.add(batch.toGroup('the_westworks'));
    return g;
  },
};
